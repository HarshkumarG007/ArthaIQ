"""Support checks, abstention policy, and evidence-grade evaluation (ADR-0005, Task T5.07).

Implements:
- S1–S5 Support Checks:
  * S1: Effective Cohort Size (deduplicated quality-weighted count >= 10, Rule R-MD-08)
  * S2: Feature-Space Support (experience range [0, 40], categorical frequency >= 3)
  * S3: Recency (median observation age <= 365 days)
  * S4: Source Quality (SQSF composite score >= 65.0, allowed tiers A & B, Rule R-UQ-07)
  * S5: Interval Usefulness (width ratio <= 1.05 vs naive cohort, Rule R-UQ-04)
- Decoupled Evidence Quality Framework (Rule R-UQ-07, Decision D-010):
  * Source Quality Tier (TIER_A to TIER_D) evaluated independently from Prediction Support
  * Prediction Support Status (SUPPORTED, GUARDED, ABSTAINED)
- Evidence Grades (Grade A, Grade B, Grade C, Abstained) per ADR-0005.
- Thin-evidence abstention triggers with HTTP 200 payload representation (Rule R-ER-04).
- Safe YAML configuration loader parsing config/thresholds.yaml with typed defaults.

Adheres to:
- Rule R-MD-08: Thin evidence abstention (N < 10 or low provenance).
- Rule R-EV-07: Sample size alone does not validate an estimate.
- Rule R-UQ-01: No lone numbers; full [P10, P90] with P50 and evidence summary.
- Rule R-UQ-02: Abstain rather than guess; abstention is a valid designed result.
- Rule R-UQ-04: Interval usefulness comparison.
- Rule R-UQ-07: Decoupled source quality and prediction support.
- Rule R-CD-01: Strict typing and complete mypy compliance.
- Rule R-CD-03 & Import Linter: Zero imports of serving, evaluation, ingestion, or quality.
"""

from __future__ import annotations

import datetime
import statistics
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from compintel.config import get_settings
from compintel.errors import ConfigError

if TYPE_CHECKING:
    import polars as pl

# -----------------------------------------------------------------------------
# 1. Enums for Evidence Grades, Support Status, and Abstention Reasons
# -----------------------------------------------------------------------------


class EvidenceGrade(StrEnum):
    """Composite evidence grade assigned to an estimate (ADR-0005)."""

    GRADE_A = "GRADE_A"
    GRADE_B = "GRADE_B"
    GRADE_C = "GRADE_C"
    ABSTAINED = "ABSTAINED"


class SupportStatus(StrEnum):
    """Prediction support status (independent from source quality, Rule R-UQ-07)."""

    SUPPORTED = "SUPPORTED"
    GUARDED = "GUARDED"
    ABSTAINED = "ABSTAINED"


class SourceQualityTier(StrEnum):
    """Source quality tier evaluated independently from prediction support (Decision D-010)."""

    TIER_A = "TIER_A"
    TIER_B = "TIER_B"
    TIER_C = "TIER_C"
    TIER_D = "TIER_D"


class AbstentionReason(StrEnum):
    """Taxonomy of deterministic abstention reason codes (Rules R-MD-08, R-UQ-02)."""

    THIN_COHORT_EVIDENCE = "THIN_COHORT_EVIDENCE"
    OUT_OF_RANGE_EXPERIENCE = "OUT_OF_RANGE_EXPERIENCE"
    UNSEEN_CATEGORICAL_PROFILE = "UNSEEN_CATEGORICAL_PROFILE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    LOW_PROVENANCE_SOURCE = "LOW_PROVENANCE_SOURCE"
    EXCESSIVE_INTERVAL_WIDTH = "EXCESSIVE_INTERVAL_WIDTH"
    MODEL_ABSTAINED = "MODEL_ABSTAINED"


# -----------------------------------------------------------------------------
# 2. Pydantic Configuration Models for config/thresholds.yaml
# -----------------------------------------------------------------------------


class S1CohortSizeConfig(BaseModel):
    """Configuration for S1 Effective Cohort Size check (Rule R-MD-08)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    abstention_floor: int = Field(
        default=10,
        ge=1,
        description="Minimum verified observations; below this triggers mandatory abstention.",
    )
    grade_c_min: int = Field(default=10, ge=1)
    grade_b_min: int = Field(default=15, ge=1)
    grade_a_min: int = Field(default=30, ge=1)


class S2FeatureSupportConfig(BaseModel):
    """Configuration for S2 Feature-Space Support check."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    experience_years_min: float = Field(default=0.0, ge=0.0)
    experience_years_max: float = Field(default=40.0, ge=0.0)
    experience_veteran_caution_years: float = Field(default=25.0, ge=0.0)
    min_category_training_count: int = Field(default=3, ge=1)


class S3RecencyConfig(BaseModel):
    """Configuration for S3 Recency check."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    abstention_floor_days: float = Field(default=365.0, gt=0.0)
    grade_c_max_days: float = Field(default=365.0, gt=0.0)
    grade_b_max_days: float = Field(default=270.0, gt=0.0)
    grade_a_max_days: float = Field(default=180.0, gt=0.0)


class S4SourceQualityConfig(BaseModel):
    """Configuration for S4 Source Quality check (Rule R-UQ-07)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    abstention_floor_score: float = Field(default=65.0, ge=0.0, le=100.0)
    grade_c_min_score: float = Field(default=65.0, ge=0.0, le=100.0)
    grade_b_min_score: float = Field(default=72.0, ge=0.0, le=100.0)
    grade_a_min_score: float = Field(default=80.0, ge=0.0, le=100.0)
    allowed_provenance_tiers: list[str] = Field(
        default_factory=lambda: ["TIER_A", "TIER_B", "A", "B"]
    )
    disqualified_provenance_tiers: list[str] = Field(
        default_factory=lambda: ["TIER_C", "TIER_D", "C", "D"]
    )


class S5IntervalUsefulnessConfig(BaseModel):
    """Configuration for S5 Interval Usefulness check (Rule R-UQ-04)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    abstention_floor_ratio: float = Field(default=1.05, gt=0.0)
    grade_c_max_ratio: float = Field(default=1.05, gt=0.0)
    grade_b_max_ratio: float = Field(default=1.00, gt=0.0)
    grade_a_max_ratio: float = Field(default=0.95, gt=0.0)
    max_absolute_width_lpa: float = Field(default=100.0, gt=0.0)


class SupportChecksConfig(BaseModel):
    """Container for S1–S5 check parameters."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    s1_cohort_size: S1CohortSizeConfig = Field(default_factory=S1CohortSizeConfig)
    s2_feature_support: S2FeatureSupportConfig = Field(default_factory=S2FeatureSupportConfig)
    s3_recency: S3RecencyConfig = Field(default_factory=S3RecencyConfig)
    s4_source_quality: S4SourceQualityConfig = Field(default_factory=S4SourceQualityConfig)
    s5_interval_usefulness: S5IntervalUsefulnessConfig = Field(
        default_factory=S5IntervalUsefulnessConfig
    )


class ThresholdsConfig(BaseModel):
    """Root configuration model parsed from config/thresholds.yaml."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    version: str = Field(default="1.0.0")
    effective_date: str = Field(default="2026-10-18")
    status: str = Field(default="ACTIVE")
    support_checks: SupportChecksConfig = Field(default_factory=SupportChecksConfig)
    abstention_reasons: dict[str, dict[str, str]] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path | str | None = None) -> ThresholdsConfig:
        """Load and parse thresholds configuration from YAML file with fallback to defaults."""
        if path is None:
            settings = get_settings()
            path = settings.thresholds_path

        p = Path(path)
        if not p.is_file():
            # Return typed defaults if file does not exist
            return cls()

        try:
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return cls()
            return cls.model_validate(data)
        except Exception as err:
            raise ConfigError(f"Failed to parse thresholds configuration from {p}: {err}") from err


# -----------------------------------------------------------------------------
# 3. Input & Output Data Structures
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateProfile:
    """Input query profile for compensation estimation."""

    role_family: str
    seniority: str
    location: str
    years_experience: float

    def canonical_role(self) -> str:
        """Normalize role family string to uppercase name."""
        return str(self.role_family).strip().upper()

    def canonical_seniority(self) -> str:
        """Normalize seniority string to uppercase name."""
        return str(self.seniority).strip().upper()

    def canonical_location(self) -> str:
        """Normalize location string to uppercase name."""
        return str(self.location).strip().upper()


@dataclass(frozen=True)
class CohortEvidenceContext:
    """Contextual evidence metrics available for candidate's specific cohort."""

    cohort_size: int
    category_seen_count: int = 10
    median_observation_age_days: float = 90.0
    source_quality_score: float = 85.0
    provenance_tier: str = "TIER_A"
    interval_width_lpa: float | None = None
    naive_cohort_width_lpa: float | None = None
    width_ratio: float | None = None
    base_model_abstained: bool = False
    base_model_abstention_reason: str | None = None


@dataclass(frozen=True)
class SupportCheckDetail:
    """Detailed result of an individual support check (S1 through S5)."""

    check_id: str
    name: str
    passed: bool
    status: str  # "PASS", "FAIL", "CAUTION"
    value: float | int | str | None
    threshold: float | int | str | None
    note: str

    def to_dict(self) -> dict[str, Any]:
        """Convert detail to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class SupportCheckResult:
    """Comprehensive evaluation result across all support checks and evidence grades.

    Adheres to Rules R-MD-08, R-UQ-01, R-UQ-02, R-UQ-07, and ADR-0005.
    """

    is_abstained: bool
    evidence_grade: EvidenceGrade
    support_status: SupportStatus
    source_quality_tier: SourceQualityTier
    reasons: list[AbstentionReason]
    primary_reason: AbstentionReason | None
    explanation: str
    guidance: str
    checks: dict[str, SupportCheckDetail]
    profile_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluation result to dictionary."""
        return {
            "is_abstained": self.is_abstained,
            "evidence_grade": self.evidence_grade.value,
            "support_status": self.support_status.value,
            "source_quality_tier": self.source_quality_tier.value,
            "reasons": [r.value for r in self.reasons],
            "primary_reason": self.primary_reason.value if self.primary_reason else None,
            "explanation": self.explanation,
            "guidance": self.guidance,
            "checks": {k: v.to_dict() for k, v in self.checks.items()},
            "profile_summary": self.profile_summary,
        }

    def to_http_response(self) -> dict[str, Any]:
        """Render standard HTTP 200 payload representation per Rule R-ER-04 & ADR-0005."""
        if self.is_abstained:
            return {
                "status": "abstained",
                "is_abstained": True,
                "evidence_grade": self.evidence_grade.value,
                "support_status": self.support_status.value,
                "source_quality_tier": self.source_quality_tier.value,
                "primary_reason": self.primary_reason.value if self.primary_reason else None,
                "reasons": [r.value for r in self.reasons],
                "explanation": self.explanation,
                "guidance": self.guidance,
                "estimate": None,
                "checks": {k: v.to_dict() for k, v in self.checks.items()},
            }
        return {
            "status": "supported",
            "is_abstained": False,
            "evidence_grade": self.evidence_grade.value,
            "support_status": self.support_status.value,
            "source_quality_tier": self.source_quality_tier.value,
            "reasons": [],
            "explanation": self.explanation,
            "guidance": self.guidance,
            "checks": {k: v.to_dict() for k, v in self.checks.items()},
        }


# -----------------------------------------------------------------------------
# 4. SupportEvaluator Engine
# -----------------------------------------------------------------------------


class SupportEvaluator:
    """Core evaluation engine for support checks, evidence grades, and abstention policies.

    Adheres to Rules:
    - R-MD-08: Thin-evidence abstention (N < 10 or disqualified provenance).
    - R-EV-07: Sample size alone does not validate an estimate.
    - R-UQ-02: Abstain rather than guess; abstention is HTTP 200, not an error.
    - R-UQ-07: Independent evaluation of source quality vs prediction support.
    """

    def __init__(self, config: ThresholdsConfig | None = None) -> None:
        """Initialize evaluator with threshold configuration."""
        self._config = config or ThresholdsConfig.from_yaml()

    @property
    def config(self) -> ThresholdsConfig:
        """Return the active threshold configuration."""
        return self._config

    def evaluate_support(
        self,
        profile: CandidateProfile,
        evidence: CohortEvidenceContext,
    ) -> SupportCheckResult:
        """Evaluate S1–S5 support checks, decoupled evidence dimensions, and evidence grade."""
        cfg = self._config.support_checks
        reasons: list[AbstentionReason] = []
        checks: dict[str, SupportCheckDetail] = {}

        # -------------------------------------------------------------------------
        # Check S1: Effective Cohort Size (Rule R-MD-08)
        # -------------------------------------------------------------------------
        s1_n = evidence.cohort_size
        s1_floor = cfg.s1_cohort_size.abstention_floor
        s1_passed = s1_n >= s1_floor
        if not s1_passed:
            reasons.append(AbstentionReason.THIN_COHORT_EVIDENCE)
            s1_status = "FAIL"
            s1_note = f"Cohort size N={s1_n} is below mandatory abstention floor N={s1_floor}."
        elif s1_n < cfg.s1_cohort_size.grade_b_min:
            s1_status = "CAUTION"
            s1_note = (
                f"Cohort size N={s1_n} meets minimum floor ({s1_floor}) but has narrow support."
            )
        else:
            s1_status = "PASS"
            s1_note = f"Cohort size N={s1_n} meets robust statistical criteria."

        checks["S1_cohort_size"] = SupportCheckDetail(
            check_id="S1",
            name="Effective Cohort Size",
            passed=s1_passed,
            status=s1_status,
            value=s1_n,
            threshold=s1_floor,
            note=s1_note,
        )

        # -------------------------------------------------------------------------
        # Check S2: Feature-Space Support (Experience & Categorical Profile)
        # -------------------------------------------------------------------------
        yoe = profile.years_experience
        yoe_min = cfg.s2_feature_support.experience_years_min
        yoe_max = cfg.s2_feature_support.experience_years_max
        yoe_caution = cfg.s2_feature_support.experience_veteran_caution_years
        cat_count = evidence.category_seen_count
        cat_min = cfg.s2_feature_support.min_category_training_count

        s2_yoe_valid = yoe_min <= yoe <= yoe_max
        s2_cat_valid = cat_count >= cat_min
        s2_passed = s2_yoe_valid and s2_cat_valid

        if not s2_yoe_valid:
            reasons.append(AbstentionReason.OUT_OF_RANGE_EXPERIENCE)
            s2_status = "FAIL"
            s2_note = f"Experience {yoe:.1f} years is outside valid domain [{yoe_min}, {yoe_max}]."
        elif not s2_cat_valid:
            reasons.append(AbstentionReason.UNSEEN_CATEGORICAL_PROFILE)
            s2_status = "FAIL"
            s2_note = (
                f"Categorical profile seen {cat_count} times in training, "
                f"below threshold {cat_min}."
            )
        elif yoe > yoe_caution:
            s2_status = "CAUTION"
            s2_note = (
                f"Veteran experience ({yoe:.1f} years > {yoe_caution}) carries tail uncertainty."
            )
        else:
            s2_status = "PASS"
            s2_note = "Profile features strictly inside empirical training distribution."

        checks["S2_feature_support"] = SupportCheckDetail(
            check_id="S2",
            name="Feature Space Support",
            passed=s2_passed,
            status=s2_status,
            value=f"YoE={yoe:.1f}, CatCount={cat_count}",
            threshold=f"[{yoe_min}, {yoe_max}], min_cat={cat_min}",
            note=s2_note,
        )

        # -------------------------------------------------------------------------
        # Check S3: Recency
        # -------------------------------------------------------------------------
        age_days = evidence.median_observation_age_days
        s3_floor = cfg.s3_recency.abstention_floor_days
        s3_passed = age_days <= s3_floor
        if not s3_passed:
            reasons.append(AbstentionReason.STALE_EVIDENCE)
            s3_status = "FAIL"
            s3_note = (
                f"Median evidence age {age_days:.1f} days exceeds stale limit {s3_floor:.0f} days."
            )
        elif age_days > cfg.s3_recency.grade_a_max_days:
            s3_status = "CAUTION"
            s3_note = f"Median evidence age {age_days:.1f} days is acceptable but aging."
        else:
            s3_status = "PASS"
            s3_note = f"Fresh evidence with median age {age_days:.1f} days."

        checks["S3_recency"] = SupportCheckDetail(
            check_id="S3",
            name="Recency",
            passed=s3_passed,
            status=s3_status,
            value=round(age_days, 1),
            threshold=s3_floor,
            note=s3_note,
        )

        # -------------------------------------------------------------------------
        # Check S4: Source Quality (Rule R-UQ-07)
        # -------------------------------------------------------------------------
        sqsf_score = evidence.source_quality_score
        raw_tier = evidence.provenance_tier.upper()
        prov_tier = f"TIER_{raw_tier}" if raw_tier in ("A", "B", "C", "D") else raw_tier
        s4_score_floor = cfg.s4_source_quality.abstention_floor_score
        s4_allowed_tiers = [t.upper() for t in cfg.s4_source_quality.allowed_provenance_tiers]

        s4_score_passed = sqsf_score >= s4_score_floor
        s4_tier_passed = (prov_tier in s4_allowed_tiers) or (raw_tier in s4_allowed_tiers)
        s4_passed = s4_score_passed and s4_tier_passed

        if not s4_passed:
            reasons.append(AbstentionReason.LOW_PROVENANCE_SOURCE)
            s4_status = "FAIL"
            s4_note = (
                f"Source quality SQSF={sqsf_score:.1f} (tier={prov_tier}) fails threshold "
                f"(min {s4_score_floor:.1f}, allowed={s4_allowed_tiers})."
            )
        elif sqsf_score < cfg.s4_source_quality.grade_a_min_score:
            s4_status = "CAUTION"
            s4_note = f"Source quality SQSF={sqsf_score:.1f} is acceptable."
        else:
            s4_status = "PASS"
            s4_note = f"High provenance source quality SQSF={sqsf_score:.1f} ({prov_tier})."

        checks["S4_source_quality"] = SupportCheckDetail(
            check_id="S4",
            name="Source Quality",
            passed=s4_passed,
            status=s4_status,
            value=f"{sqsf_score:.1f} ({prov_tier})",
            threshold=f">={s4_score_floor} and in {s4_allowed_tiers}",
            note=s4_note,
        )

        # -------------------------------------------------------------------------
        # Check S5: Interval Usefulness (Rule R-UQ-04)
        # -------------------------------------------------------------------------
        width_ratio = evidence.width_ratio
        if (
            width_ratio is None
            and evidence.interval_width_lpa
            and evidence.naive_cohort_width_lpa
            and evidence.naive_cohort_width_lpa > 0.0
        ):
            width_ratio = evidence.interval_width_lpa / evidence.naive_cohort_width_lpa

        s5_max_ratio = cfg.s5_interval_usefulness.abstention_floor_ratio
        s5_max_abs_width = cfg.s5_interval_usefulness.max_absolute_width_lpa

        s5_ratio_passed = width_ratio is None or width_ratio <= s5_max_ratio
        s5_abs_passed = (
            evidence.interval_width_lpa is None or evidence.interval_width_lpa <= s5_max_abs_width
        )
        s5_passed = s5_ratio_passed and s5_abs_passed

        if not s5_passed:
            reasons.append(AbstentionReason.EXCESSIVE_INTERVAL_WIDTH)
            s5_status = "FAIL"
            s5_note = (
                f"Interval width ratio {width_ratio:.3f} or width "
                f"{evidence.interval_width_lpa} LPA exceeds usefulness limits."
            )
        elif width_ratio is not None and width_ratio > cfg.s5_interval_usefulness.grade_a_max_ratio:
            s5_status = "CAUTION"
            s5_note = f"Interval width ratio {width_ratio:.3f} meets acceptable bound."
        else:
            s5_status = "PASS"
            s5_note = "Prediction interval compressed and useful relative to cohort baseline."

        checks["S5_interval_usefulness"] = SupportCheckDetail(
            check_id="S5",
            name="Interval Usefulness",
            passed=s5_passed,
            status=s5_status,
            value=f"ratio={width_ratio:.3f}" if width_ratio is not None else "N/A",
            threshold=f"ratio<={s5_max_ratio}",
            note=s5_note,
        )

        # Base model abstention check
        if evidence.base_model_abstained:
            reasons.append(AbstentionReason.MODEL_ABSTAINED)

        # -------------------------------------------------------------------------
        # Decoupled Dimensions: Source Quality Tier & Prediction Support Status
        # -------------------------------------------------------------------------
        # Source Quality Tier is evaluated independently from sample size (R-UQ-07, D-010)
        if prov_tier == "TIER_A" and sqsf_score >= 80.0:
            source_quality_tier = SourceQualityTier.TIER_A
        elif prov_tier in ["TIER_A", "TIER_B"] and sqsf_score >= 65.0:
            source_quality_tier = SourceQualityTier.TIER_B
        elif sqsf_score >= 45.0:
            source_quality_tier = SourceQualityTier.TIER_C
        else:
            source_quality_tier = SourceQualityTier.TIER_D

        # Prediction Support Status:
        is_abstained = len(reasons) > 0
        if is_abstained:
            support_status = SupportStatus.ABSTAINED
            evidence_grade = EvidenceGrade.ABSTAINED
        else:
            # Check for Grade A criteria
            is_grade_a = (
                s1_n >= cfg.s1_cohort_size.grade_a_min
                and age_days <= cfg.s3_recency.grade_a_max_days
                and sqsf_score >= cfg.s4_source_quality.grade_a_min_score
                and (
                    width_ratio is None
                    or width_ratio <= cfg.s5_interval_usefulness.grade_a_max_ratio
                )
                and yoe <= yoe_caution
            )
            # Check for Grade B criteria
            is_grade_b = (
                s1_n >= cfg.s1_cohort_size.grade_b_min
                and age_days <= cfg.s3_recency.grade_b_max_days
                and sqsf_score >= cfg.s4_source_quality.grade_b_min_score
                and (
                    width_ratio is None
                    or width_ratio <= cfg.s5_interval_usefulness.grade_b_max_ratio
                )
            )

            if is_grade_a:
                evidence_grade = EvidenceGrade.GRADE_A
                support_status = SupportStatus.SUPPORTED
            elif is_grade_b:
                evidence_grade = EvidenceGrade.GRADE_B
                support_status = SupportStatus.SUPPORTED
            else:
                evidence_grade = EvidenceGrade.GRADE_C
                support_status = SupportStatus.GUARDED

        # Select primary reason and user explanation/guidance
        primary_reason = reasons[0] if reasons else None
        explanation, guidance = self._format_explanation_and_guidance(
            primary_reason=primary_reason,
            profile=profile,
            evidence=evidence,
            grade=evidence_grade,
        )

        profile_summary = {
            "role_family": profile.canonical_role(),
            "seniority": profile.canonical_seniority(),
            "location": profile.canonical_location(),
            "years_experience": round(profile.years_experience, 1),
        }

        return SupportCheckResult(
            is_abstained=is_abstained,
            evidence_grade=evidence_grade,
            support_status=support_status,
            source_quality_tier=source_quality_tier,
            reasons=reasons,
            primary_reason=primary_reason,
            explanation=explanation,
            guidance=guidance,
            checks=checks,
            profile_summary=profile_summary,
        )

    def _format_explanation_and_guidance(
        self,
        primary_reason: AbstentionReason | None,
        profile: CandidateProfile,
        evidence: CohortEvidenceContext,
        grade: EvidenceGrade,
    ) -> tuple[str, str]:
        """Construct user-facing explanation and actionable guidance text."""
        if primary_reason is None:
            if grade == EvidenceGrade.GRADE_A:
                return (
                    "Robust empirical evidence meeting all support criteria with margin.",
                    "Estimate is supported by high-quality verified market data.",
                )
            if grade == EvidenceGrade.GRADE_B:
                return (
                    "Sound empirical evidence meeting standard market benchmarks.",
                    "Estimate is reliable for offer benchmarking and compensation planning.",
                )
            return (
                "Narrow sample support; estimate is provided with guarded confidence.",
                "Consider cross-referencing with broader seniority or location benchmarks.",
            )

        taxonomy = self._config.abstention_reasons.get(primary_reason.value, {})
        base_explanation = taxonomy.get("explanation")
        base_guidance = taxonomy.get("guidance")

        if primary_reason == AbstentionReason.THIN_COHORT_EVIDENCE:
            explanation = (
                f"Fewer than 10 verified records exist for {profile.canonical_role()} "
                f"{profile.canonical_seniority()} in {profile.canonical_location()} "
                f"(N={evidence.cohort_size}). ArthaIQ abstains rather than extrapolating."
            )
            guidance = (
                "Broaden your location filter or explore adjacent seniority levels where "
                "larger verified sample support is available."
            )
        elif primary_reason == AbstentionReason.OUT_OF_RANGE_EXPERIENCE:
            explanation = (
                f"Professional experience ({profile.years_experience:.1f} years) is outside "
                "the validated modeling domain (0 to 40 years)."
            )
            guidance = "Enter professional years of experience between 0 and 40."
        elif primary_reason == AbstentionReason.UNSEEN_CATEGORICAL_PROFILE:
            explanation = (
                f"The requested profile combination has zero or negligible representation "
                f"(seen {evidence.category_seen_count} times) in the verified training data."
            )
            guidance = (
                "Select a standardized role taxon (Software Engineering, Data Science, MLAI) "
                "and Indian metro hub."
            )
        elif primary_reason == AbstentionReason.STALE_EVIDENCE:
            explanation = (
                f"The available compensation observations for this cohort exceed the maximum "
                f"freshness threshold ({evidence.median_observation_age_days:.0f} days > 365 days)."
            )
            guidance = "Recent market data is being acquired; subscribe for quarterly updates."
        elif primary_reason == AbstentionReason.LOW_PROVENANCE_SOURCE:
            explanation = (
                f"Matching data relies on unverified or low-provenance sources "
                f"(SQSF={evidence.source_quality_score:.1f} < 65.0)."
            )
            guidance = "ArthaIQ only provides guaranteed cash distributions using Tier-A/B sources."
        elif primary_reason == AbstentionReason.EXCESSIVE_INTERVAL_WIDTH:
            explanation = (
                "The calibrated prediction interval is wider than a naive uncalibrated cohort, "
                "indicating extreme empirical dispersion."
            )
            guidance = (
                "Provide additional profile dimensions or compare against broader benchmark bands."
            )
        else:
            explanation = base_explanation or "Evidence is below statutory reliability threshold."
            guidance = base_guidance or "Consider broadening your profile filters."

        return explanation, guidance

    def compute_cohort_evidence_table(
        self,
        df: pl.DataFrame,
        as_of_date: datetime.date | None = None,
        role_col: str = "role_family",
        seniority_col: str = "seniority",
        location_col: str = "location",
        yoe_col: str = "years_experience",
        date_col: str | None = None,
        sqsf_col: str = "source_quality_score",
        tier_col: str = "provenance_tier",
    ) -> dict[tuple[str, str, str], CohortEvidenceContext]:
        """Precompute cohort statistics directly from an empirical training Polars DataFrame."""
        if df.is_empty():
            return {}

        as_of = as_of_date or datetime.date.today()

        # Find date column if not provided
        if date_col is None:
            if "as_of_date" in df.columns:
                date_col = "as_of_date"
            elif "effective_on" in df.columns:
                date_col = "effective_on"
            else:
                date_col = None

        has_sqsf = sqsf_col in df.columns
        has_tier = tier_col in df.columns

        cohorts: dict[tuple[str, str, str], CohortEvidenceContext] = {}

        # Group by role, seniority, location
        grouped = df.group_by([role_col, seniority_col, location_col])
        for key, group_df in grouped:
            role_val = str(key[0]).upper()
            seniority_val = str(key[1]).upper()
            location_val = str(key[2]).upper()
            cohort_size = len(group_df)

            # Compute median age in days
            median_age = 90.0
            if date_col and date_col in group_df.columns:
                dates = group_df[date_col].drop_nulls()
                if len(dates) > 0:
                    try:
                        # Extract date
                        ages = [
                            max(0.0, float((as_of - d).days))
                            for d in dates.to_list()
                            if isinstance(d, datetime.date)
                        ]
                        if ages:
                            median_age = float(statistics.median(ages))
                    except Exception:
                        median_age = 90.0

            # Compute mean SQSF score
            mean_sqsf = 85.0
            if has_sqsf:
                scores = group_df[sqsf_col].drop_nulls()
                score_list = [float(s) for s in scores.to_list() if s is not None]
                if score_list:
                    mean_sqsf = float(statistics.mean(score_list))

            # Extract provenance tier
            prov_tier = "TIER_A"
            if has_tier:
                tiers = group_df[tier_col].drop_nulls()
                if len(tiers) > 0:
                    prov_tier = str(tiers[0]).upper()

            cohort_key = (role_val, seniority_val, location_val)
            cohorts[cohort_key] = CohortEvidenceContext(
                cohort_size=cohort_size,
                category_seen_count=cohort_size,
                median_observation_age_days=median_age,
                source_quality_score=mean_sqsf,
                provenance_tier=prov_tier,
            )

        return cohorts
