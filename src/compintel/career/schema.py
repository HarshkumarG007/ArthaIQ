"""Domain schema contracts for ArthaIQ Career Architect (Phase 15).

Defines Pydantic v2 data models, enums, provenance tracking, tri-state
verification, and anti-causal validators (Rules R-CR-01 to R-CR-15).
"""

from __future__ import annotations

import re
from enum import IntEnum, StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from compintel.schema.enums import RoleFamily

# Forbidden causal pay phrases under Rule R-CR-01 and Consumer Protection Act 2019
FORBIDDEN_CAUSAL_PATTERNS = [
    r"raises?\s+compensation",
    r"boosts?\s+(your\s+)?salary",
    r"salary\s+bump",
    r"earn\s+[₹\$]",
    r"[₹\$]\s*[\d,]+(\s*LPA|\s*INR)?\s+increase",
    r"higher\s+pay",
    r"increase\s+(your\s+)?pay",
    r"\+[\d.]+%\s*CTC",
    r"promotes?\s+to\s+pay\s+band",
    r"guaranteed?\s+compensation",
]
_COMPILED_CAUSAL_RE = re.compile("|".join(FORBIDDEN_CAUSAL_PATTERNS), re.IGNORECASE)


def validate_anti_causal_text(text: str, field_name: str) -> str:
    """Validate that text does not contain causal compensation promises (Rule R-CR-01).

    Args:
        text: Input string to validate.
        field_name: Name of the model field for error diagnostics.

    Returns:
        The validated text if no prohibited patterns are found.

    Raises:
        ValueError: If a causal compensation phrase is detected.
    """
    match = _COMPILED_CAUSAL_RE.search(text)
    if match:
        raise ValueError(
            f"Prohibited causal compensation phrase detected in '{field_name}': "
            f"'{match.group(0)}'. Rule R-CR-01 and CPA 2019 strictly prohibit claiming "
            "that acquiring skills or credentials causes compensation increases."
        )
    return text


class VerificationState(StrEnum):
    """Tri-state competency verification model (Rule R-CR-03, ADR-0011).

    State beats score: arbitrary continuous percentage progress bars are prohibited.
    """

    UNPROVEN = "Unproven"
    SELF_REPORTED = "Self-reported"
    DEMONSTRATED = "Demonstrated"


class EvidenceType(StrEnum):
    """Taxonomy of admissible capability evidence."""

    SELF_ATTESTATION = "self_attestation"
    FLAW_SCENARIO = "flaw_scenario"
    CODE_EXERCISE = "code_exercise"
    PORTFOLIO_ARTIFACT = "portfolio_artifact"


class RoleLevel(IntEnum):
    """Standard occupational levels within a role family (PRD FR-21)."""

    LEVEL_2_JUNIOR = 2
    LEVEL_3_MID = 3
    LEVEL_4_SENIOR = 4


class CompetencyCategory(StrEnum):
    """Taxonomy clusters for the DATA role family."""

    CORE_ANALYTICS = "core_analytics"
    DATA_ENGINEERING = "data_engineering"
    STATISTICAL_MODELING = "statistical_modeling"
    EXPERIMENTATION = "experimentation"
    BUSINESS_COMMUNICATION = "business_communication"


class TaxonomySource(StrEnum):
    """Approved external labour taxonomy sources (ADR-0011)."""

    ONET_28_0 = "ONET-28.0"
    ESCO_1_1_1 = "ESCO-1.1.1"
    ARTHAIQ_CURATED = "ARTHAIQ-CURATED"


class TaxonomyLicense(StrEnum):
    """Approved licence classes for ingested taxonomies."""

    CC_BY_4_0 = "CC-BY-4.0"
    EU_OPEN_REUSE = "EU-OPEN-REUSE"
    PROPRIETARY_INTERNAL = "PROPRIETARY-INTERNAL"


class TaxonomyProvenance(BaseModel):
    """Attribution and provenance record for taxonomy elements (Rule R-CR-04)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: TaxonomySource
    source_code: str = Field(..., min_length=1, description="Origin code in parent taxonomy")
    license: TaxonomyLicense
    attribution_required: bool = True
    attribution_text: str = Field(..., min_length=5, description="Statutory attribution notice")
    modified_flag: bool = Field(default=False, description="True if adapted or re-anchored")
    curator: str = Field(..., min_length=2, description="Name or role of reviewing curator")
    curated_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")


class EffortRange(BaseModel):
    """Heuristic effort hours range for a competency (Rule R-CR-05)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_hours: int = Field(..., ge=1, le=500, description="Minimum heuristic effort in hours")
    max_hours: int = Field(..., ge=2, le=1000, description="Maximum heuristic effort in hours")

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.min_hours >= self.max_hours:
            raise ValueError(
                f"min_hours ({self.min_hours}) must be strictly less than "
                f"max_hours ({self.max_hours})"
            )
        return self


class DifficultyRubric(BaseModel):
    """Calibrated difficulty anchors for a competency (Rule R-CR-05)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    learning_difficulty: float = Field(..., ge=1.0, le=5.0)
    application_difficulty: float = Field(..., ge=1.0, le=5.0)
    is_heuristic: Literal[True] = Field(
        default=True, description="Must remain True: difficulty is heuristic, not empirical fact"
    )
    effort_hours: EffortRange | None = Field(
        default=None, description="Heuristic effort hours range (Rule R-CR-05)"
    )
    rationale: str | None = Field(
        default=None, description="Practitioner justification for difficulty anchors"
    )


class DifficultyAnchorDefinition(BaseModel):
    """Definition of an anchor point on a 1.0-5.0 difficulty scale (Rule R-CR-05)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scale: str = Field(
        ..., pattern=r"^(learning|application)$", description="'learning' or 'application'"
    )
    level: float = Field(..., ge=1.0, le=5.0, description="Anchor level (1.0 to 5.0)")
    label: str = Field(..., min_length=3, max_length=50, description="Short human-readable label")
    anchor_description: str = Field(
        ..., min_length=10, max_length=500, description="Description of criteria"
    )
    typical_signals: list[str] = Field(
        ..., min_length=1, description="Observable signals/indicators"
    )


class DifficultyRubricEntry(BaseModel):
    """Full rubric calibration entry for a single competency (Rule R-CR-05)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str = Field(
        ..., pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)+$", description="Dot-separated ID"
    )
    learning_difficulty: float = Field(..., ge=1.0, le=5.0)
    application_difficulty: float = Field(..., ge=1.0, le=5.0)
    effort_hours: EffortRange
    learning_rationale: str = Field(..., min_length=10, max_length=500)
    application_rationale: str = Field(..., min_length=10, max_length=500)
    is_heuristic: Literal[True] = Field(default=True)
    disclaimer: str = Field(
        default=(
            "Estimated based on practitioner consensus. "
            "Individual effort varies with prior background."
        ),
        min_length=20,
        max_length=300,
    )

    @field_validator("learning_rationale", "application_rationale")
    @classmethod
    def check_anti_causal(cls, v: str, info: object) -> str:
        field_name = getattr(info, "field_name", "rationale")
        return validate_anti_causal_text(v, field_name)


class DifficultyRubricsManifest(BaseModel):
    """Manifest containing all calibrated difficulty rubrics and anchors for a role family."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(default="1.0.0")
    role_family: str = Field(default="DATA")
    heuristic_disclaimer: str = Field(
        default=(
            "Estimated based on practitioner consensus. "
            "Individual effort varies with prior background."
        )
    )
    learning_anchors: list[DifficultyAnchorDefinition] = Field(..., min_length=5)
    application_anchors: list[DifficultyAnchorDefinition] = Field(..., min_length=5)
    entries: list[DifficultyRubricEntry] = Field(..., min_length=1)


class CompetencyNode(BaseModel):
    """Atomic competency node within the Directed Acyclic Graph (DAG)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)+$", description="Dot-separated ID")
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    category: CompetencyCategory
    role_family: Literal[RoleFamily.DATA] = Field(
        default=RoleFamily.DATA, description="Scoped to DATA family in Phase 15"
    )
    target_levels: list[RoleLevel] = Field(..., min_length=1)
    prerequisite_ids: list[str] = Field(default_factory=list)
    provenance: TaxonomyProvenance
    difficulty: DifficultyRubric

    @field_validator("title", "description", mode="after")
    @classmethod
    def check_anti_causal_invariants(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "unknown")
        return validate_anti_causal_text(value, field_name)


class CompetencyGraphManifest(BaseModel):
    """Versioned container manifest for a competency graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    graph_id: str
    version: str
    role_family: Literal[RoleFamily.DATA] = RoleFamily.DATA
    nodes: list[CompetencyNode]
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T.*Z$")
    checksum_sha256: str = Field(..., min_length=64, max_length=64)


class EvidenceRecord(BaseModel):
    """User competency verification record within the local evidence ledger."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    competency_id: str
    state: VerificationState
    evidence_type: EvidenceType
    recorded_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T.*Z$")
    verification_artifact_ref: str | None = None


class EvidenceLedger(BaseModel):
    """Client-side career evidence ledger (stored in IndexedDB)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ledger_version: str = "v1.0"
    records: dict[str, EvidenceRecord] = Field(default_factory=dict)
    last_updated: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T.*Z$")


class CompetencyGap(BaseModel):
    """Individual gap diagnostic for a target role requirement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    competency_id: str
    required_level: RoleLevel
    current_state: VerificationState
    is_satisfied: bool
    prerequisites_satisfied: bool
    missing_prerequisites: list[str] = Field(default_factory=list)
    recheck_suggested: bool = False


class CompetencyGapReport(BaseModel):
    """Comprehensive gap analysis report for a candidate and target role."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_role: str
    target_level: RoleLevel
    total_required: int
    demonstrated_count: int
    self_reported_count: int
    unproven_count: int
    recheck_suggested_count: int = 0
    gap_nodes: list[str] = Field(default_factory=list)
    actionable_gap_nodes: list[str] = Field(default_factory=list)
    blocked_gap_nodes: list[str] = Field(default_factory=list)
    gaps: list[CompetencyGap] = Field(default_factory=list)


class CompensationEvidenceSummary(BaseModel):
    """Independent compensation distribution summary returned via CompensationPort.

    Strictly isolated from competency scores and skill graphs (Rule R-CR-02).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    role_family: str
    seniority: RoleLevel
    location: str
    currency: str = "INR"
    unit: str = "LPA"
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    interval_width: float | None = None
    evidence_grade: str | None = None  # High, Moderate, Low, Insufficient
    abstention_reason: str | None = None
    sample_size: int | None = None
    as_of_date: str | None = None
    disclaimer: str = Field(
        default=(
            "Conditional statistical distribution benchmark. Not an appraisal, offer, "
            "or guarantee of individual pay (Rules R-CR-01, R-UQ-01)."
        )
    )

    @field_validator("disclaimer")
    @classmethod
    def check_disclaimer_anti_causal(cls, v: str) -> str:
        return validate_anti_causal_text(v, "disclaimer")

    @model_validator(mode="after")
    def validate_quantiles_or_abstention(self) -> Self:
        if self.abstention_reason is not None:
            return self
        if (
            self.p10 is not None
            and self.p50 is not None
            and self.p90 is not None
            and not (self.p10 <= self.p50 <= self.p90)
        ):
            raise ValueError(
                f"Quantiles must be monotonically ordered P10 <= P50 <= P90, got "
                f"P10={self.p10}, P50={self.p50}, P90={self.p90}"
            )
        return self
