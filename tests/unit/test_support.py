"""Unit tests for Support Checks, Abstention Policy, and Evidence Grades (ADR-0005, Task T5.07a).

Adheres to Rules:
- Rule R-MD-08: Thin-evidence abstention (N < 10 or disqualified provenance).
- Rule R-EV-07: Sample size alone does not validate an estimate.
- Rule R-UQ-01: No lone numbers; structured uncertainty outputs.
- Rule R-UQ-02: Abstain rather than guess; abstention is designed result.
- Rule R-UQ-04: Interval usefulness comparison.
- Rule R-UQ-07: Decoupled source quality and prediction support.
- Rule R-CD-01: Strict typing and full mypy compliance.
- Rule R-TS-01 / R-TS-03: Quality standards and strict test coverage >= 90%.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import polars as pl
import pytest

from compintel.errors import ConfigError
from compintel.uncertainty.support import (
    AbstentionReason,
    CandidateProfile,
    CohortEvidenceContext,
    EvidenceGrade,
    SourceQualityTier,
    SupportEvaluator,
    SupportStatus,
    ThresholdsConfig,
)


@pytest.fixture
def evaluator() -> SupportEvaluator:
    """Fixture providing SupportEvaluator loaded from config/thresholds.yaml."""
    return SupportEvaluator()


@pytest.fixture
def standard_profile() -> CandidateProfile:
    """Fixture providing a standard mid-level SWE profile in Bangalore."""
    return CandidateProfile(
        role_family="SOFTWARE",
        seniority="MID",
        location="BANGALORE",
        years_experience=4.5,
    )


def test_thresholds_config_load_and_defaults() -> None:
    """Verify ThresholdsConfig parses config/thresholds.yaml and handles defaults."""
    cfg = ThresholdsConfig.from_yaml()
    assert cfg.version == "1.0.0"
    assert cfg.status == "ACTIVE"
    assert cfg.support_checks.s1_cohort_size.abstention_floor == 10
    assert cfg.support_checks.s1_cohort_size.grade_a_min == 30
    assert cfg.support_checks.s2_feature_support.experience_years_max == 40.0
    assert cfg.support_checks.s3_recency.abstention_floor_days == 365.0
    assert cfg.support_checks.s4_source_quality.abstention_floor_score == 65.0
    assert cfg.support_checks.s5_interval_usefulness.abstention_floor_ratio == 1.05

    # Fallback to defaults when file does not exist
    fallback_cfg = ThresholdsConfig.from_yaml(Path("non_existent_thresholds.yaml"))
    assert fallback_cfg.support_checks.s1_cohort_size.abstention_floor == 10

    # Error handling on invalid YAML
    with pytest.raises(ConfigError):
        ThresholdsConfig.from_yaml(Path("src/compintel/uncertainty/support.py"))


def test_s1_cohort_size_abstention_and_caution(
    evaluator: SupportEvaluator, standard_profile: CandidateProfile
) -> None:
    """Verify S1 Effective Cohort Size enforces Rule R-MD-08 thin evidence abstention."""
    # N < 10: Mandatory Abstention
    thin_evidence = CohortEvidenceContext(
        cohort_size=4,
        category_seen_count=10,
        median_observation_age_days=90.0,
        source_quality_score=85.0,
        provenance_tier="TIER_A",
        width_ratio=0.90,
    )
    res_thin = evaluator.evaluate_support(standard_profile, thin_evidence)
    assert res_thin.is_abstained is True
    assert res_thin.support_status == SupportStatus.ABSTAINED
    assert res_thin.evidence_grade == EvidenceGrade.ABSTAINED
    assert AbstentionReason.THIN_COHORT_EVIDENCE in res_thin.reasons
    assert res_thin.primary_reason == AbstentionReason.THIN_COHORT_EVIDENCE
    assert res_thin.checks["S1_cohort_size"].passed is False
    assert res_thin.checks["S1_cohort_size"].status == "FAIL"

    # 10 <= N < 15: Passes minimum floor but marked Guarded / Grade C
    guarded_evidence = CohortEvidenceContext(
        cohort_size=12,
        category_seen_count=12,
        median_observation_age_days=90.0,
        source_quality_score=85.0,
        provenance_tier="TIER_A",
        width_ratio=0.92,
    )
    res_guarded = evaluator.evaluate_support(standard_profile, guarded_evidence)
    assert res_guarded.is_abstained is False
    assert res_guarded.support_status == SupportStatus.GUARDED
    assert res_guarded.evidence_grade == EvidenceGrade.GRADE_C
    assert res_guarded.checks["S1_cohort_size"].passed is True
    assert res_guarded.checks["S1_cohort_size"].status == "CAUTION"

    # 15 <= N < 30: Passes with Grade B
    moderate_evidence = CohortEvidenceContext(
        cohort_size=20,
        category_seen_count=20,
        median_observation_age_days=90.0,
        source_quality_score=85.0,
        provenance_tier="TIER_A",
        width_ratio=0.92,
    )
    res_mod = evaluator.evaluate_support(standard_profile, moderate_evidence)
    assert res_mod.is_abstained is False
    assert res_mod.support_status == SupportStatus.SUPPORTED
    assert res_mod.evidence_grade == EvidenceGrade.GRADE_B

    # N >= 30: Passes with Grade A
    robust_evidence = CohortEvidenceContext(
        cohort_size=45,
        category_seen_count=45,
        median_observation_age_days=60.0,
        source_quality_score=85.0,
        provenance_tier="TIER_A",
        width_ratio=0.88,
    )
    res_robust = evaluator.evaluate_support(standard_profile, robust_evidence)
    assert res_robust.is_abstained is False
    assert res_robust.support_status == SupportStatus.SUPPORTED
    assert res_robust.evidence_grade == EvidenceGrade.GRADE_A


def test_s2_experience_domain_bounds(evaluator: SupportEvaluator) -> None:
    """Verify S2 enforces valid professional experience range [0, 40] and veteran caution."""
    valid_evidence = CohortEvidenceContext(cohort_size=35, category_seen_count=35)

    # Negative experience: Hard abstention
    neg_profile = CandidateProfile("SOFTWARE", "MID", "BANGALORE", -1.0)
    res_neg = evaluator.evaluate_support(neg_profile, valid_evidence)
    assert res_neg.is_abstained is True
    assert AbstentionReason.OUT_OF_RANGE_EXPERIENCE in res_neg.reasons
    assert res_neg.checks["S2_feature_support"].passed is False

    # Out-of-bounds experience (> 40 years): Hard abstention
    excess_profile = CandidateProfile("SOFTWARE", "MID", "BANGALORE", 45.0)
    res_excess = evaluator.evaluate_support(excess_profile, valid_evidence)
    assert res_excess.is_abstained is True
    assert AbstentionReason.OUT_OF_RANGE_EXPERIENCE in res_excess.reasons

    # Veteran experience tail (> 25 years): Caution status, downgraded from Grade A
    veteran_profile = CandidateProfile("SOFTWARE", "STAFF", "BANGALORE", 28.0)
    res_veteran = evaluator.evaluate_support(veteran_profile, valid_evidence)
    assert res_veteran.is_abstained is False
    assert res_veteran.checks["S2_feature_support"].status == "CAUTION"
    # Even with N=35 and fresh data, veteran caution caps at Grade B
    assert res_veteran.evidence_grade in [EvidenceGrade.GRADE_B, EvidenceGrade.GRADE_C]


def test_s2_categorical_profile_support(
    evaluator: SupportEvaluator, standard_profile: CandidateProfile
) -> None:
    """Verify S2 flags unseen or sparse categorical profiles."""
    unseen_evidence = CohortEvidenceContext(
        cohort_size=15,
        category_seen_count=1,  # below min 3
    )
    res = evaluator.evaluate_support(standard_profile, unseen_evidence)
    assert res.is_abstained is True
    assert AbstentionReason.UNSEEN_CATEGORICAL_PROFILE in res.reasons
    assert res.checks["S2_feature_support"].passed is False


def test_s3_recency_check(evaluator: SupportEvaluator, standard_profile: CandidateProfile) -> None:
    """Verify S3 flags stale data exceeding 365 days."""
    # Stale evidence (> 365 days): Hard abstention
    stale_evidence = CohortEvidenceContext(
        cohort_size=35,
        category_seen_count=35,
        median_observation_age_days=420.0,
    )
    res_stale = evaluator.evaluate_support(standard_profile, stale_evidence)
    assert res_stale.is_abstained is True
    assert AbstentionReason.STALE_EVIDENCE in res_stale.reasons
    assert res_stale.checks["S3_recency"].passed is False

    # Borderline recency (between 180 and 270 days)
    aging_evidence = CohortEvidenceContext(
        cohort_size=35,
        category_seen_count=35,
        median_observation_age_days=220.0,
    )
    res_aging = evaluator.evaluate_support(standard_profile, aging_evidence)
    assert res_aging.is_abstained is False
    assert res_aging.checks["S3_recency"].status == "CAUTION"
    assert res_aging.evidence_grade == EvidenceGrade.GRADE_B


def test_s4_source_quality_and_provenance_tier(
    evaluator: SupportEvaluator, standard_profile: CandidateProfile
) -> None:
    """Verify S4 enforces SQSF score >= 65.0 and disqualifies Tier C/D sources."""
    # Low SQSF score (< 65.0)
    low_sqsf = CohortEvidenceContext(
        cohort_size=35,
        category_seen_count=35,
        source_quality_score=55.0,
        provenance_tier="TIER_B",
    )
    res_low = evaluator.evaluate_support(standard_profile, low_sqsf)
    assert res_low.is_abstained is True
    assert AbstentionReason.LOW_PROVENANCE_SOURCE in res_low.reasons

    # Disqualified provenance tier (TIER_C)
    disqualified_tier = CohortEvidenceContext(
        cohort_size=35,
        category_seen_count=35,
        source_quality_score=75.0,
        provenance_tier="TIER_C",
    )
    res_disq = evaluator.evaluate_support(standard_profile, disqualified_tier)
    assert res_disq.is_abstained is True
    assert AbstentionReason.LOW_PROVENANCE_SOURCE in res_disq.reasons


def test_s5_interval_usefulness(
    evaluator: SupportEvaluator, standard_profile: CandidateProfile
) -> None:
    """Verify S5 enforces interval usefulness relative to naive cohort baseline (Rule R-UQ-04)."""
    # Excessive width ratio (> 1.05)
    wide_evidence = CohortEvidenceContext(
        cohort_size=35,
        category_seen_count=35,
        interval_width_lpa=45.0,
        naive_cohort_width_lpa=35.0,  # ratio = 1.285
    )
    res_wide = evaluator.evaluate_support(standard_profile, wide_evidence)
    assert res_wide.is_abstained is True
    assert AbstentionReason.EXCESSIVE_INTERVAL_WIDTH in res_wide.reasons
    assert res_wide.checks["S5_interval_usefulness"].passed is False

    # Excessive absolute width (> 100 LPA)
    extreme_width = CohortEvidenceContext(
        cohort_size=35,
        category_seen_count=35,
        interval_width_lpa=125.0,
        naive_cohort_width_lpa=150.0,
    )
    res_extreme = evaluator.evaluate_support(standard_profile, extreme_width)
    assert res_extreme.is_abstained is True
    assert AbstentionReason.EXCESSIVE_INTERVAL_WIDTH in res_extreme.reasons

    # Compressed interval (ratio <= 0.95): Passes with Grade A
    compressed_evidence = CohortEvidenceContext(
        cohort_size=35,
        category_seen_count=35,
        median_observation_age_days=60.0,
        source_quality_score=85.0,
        interval_width_lpa=32.0,
        naive_cohort_width_lpa=36.0,  # ratio = 0.888
    )
    res_comp = evaluator.evaluate_support(standard_profile, compressed_evidence)
    assert res_comp.is_abstained is False
    assert res_comp.evidence_grade == EvidenceGrade.GRADE_A


def test_decoupled_evidence_quality_framework(evaluator: SupportEvaluator) -> None:
    """Verify Rule R-UQ-07 and Decision D-010:
    Source Quality is decoupled from Prediction Support.
    """
    profile = CandidateProfile("DATA", "SENIOR", "HYDERABAD", 7.0)

    # Case 1: High source quality (Tier A, SQSF 92.0) but thin prediction support (N = 3)
    # The source pedigree remains Tier A, but the prediction status MUST abstain.
    evidence_case1 = CohortEvidenceContext(
        cohort_size=3,
        source_quality_score=92.0,
        provenance_tier="TIER_A",
    )
    res1 = evaluator.evaluate_support(profile, evidence_case1)
    assert res1.source_quality_tier == SourceQualityTier.TIER_A
    assert res1.support_status == SupportStatus.ABSTAINED
    assert res1.is_abstained is True

    # Case 2: Moderate source quality (Tier B, SQSF 75.0) with large cohort (N = 60)
    # The source pedigree remains Tier B, and prediction support is SUPPORTED (Grade B).
    evidence_case2 = CohortEvidenceContext(
        cohort_size=60,
        category_seen_count=60,
        source_quality_score=75.0,
        provenance_tier="TIER_B",
        median_observation_age_days=100.0,
        width_ratio=0.92,
    )
    res2 = evaluator.evaluate_support(profile, evidence_case2)
    assert res2.source_quality_tier == SourceQualityTier.TIER_B
    assert res2.support_status == SupportStatus.SUPPORTED
    assert res2.evidence_grade == EvidenceGrade.GRADE_B
    assert res2.is_abstained is False

    # Case 3: Borderline source quality (Tier B, SQSF 68.0) with large cohort (N = 60)
    # Source tier is Tier B, but prediction support is GUARDED (Grade C) due to borderline SQSF.
    evidence_case3 = CohortEvidenceContext(
        cohort_size=60,
        category_seen_count=60,
        source_quality_score=68.0,
        provenance_tier="TIER_B",
        median_observation_age_days=100.0,
        width_ratio=0.92,
    )
    res3 = evaluator.evaluate_support(profile, evidence_case3)
    assert res3.source_quality_tier == SourceQualityTier.TIER_B
    assert res3.support_status == SupportStatus.GUARDED
    assert res3.evidence_grade == EvidenceGrade.GRADE_C
    assert res3.is_abstained is False


def test_http_200_abstention_payload(
    evaluator: SupportEvaluator, standard_profile: CandidateProfile
) -> None:
    """Verify HTTP 200 payload rendering conforms to Rule R-ER-04 and ADR-0005."""
    thin_evidence = CohortEvidenceContext(
        cohort_size=4,
        source_quality_score=85.0,
        provenance_tier="TIER_A",
    )
    res = evaluator.evaluate_support(standard_profile, thin_evidence)
    http_payload = res.to_http_response()

    assert http_payload["status"] == "abstained"
    assert http_payload["is_abstained"] is True
    assert http_payload["estimate"] is None
    assert http_payload["evidence_grade"] == "ABSTAINED"
    assert "Fewer than 10 verified records" in http_payload["explanation"]
    assert "Broaden your location filter" in http_payload["guidance"]
    assert "S1_cohort_size" in http_payload["checks"]
    assert http_payload["checks"]["S1_cohort_size"]["passed"] is False

    # Supported payload check
    supported_evidence = CohortEvidenceContext(
        cohort_size=35,
        category_seen_count=35,
        median_observation_age_days=60.0,
        source_quality_score=85.0,
        width_ratio=0.90,
    )
    res_sup = evaluator.evaluate_support(standard_profile, supported_evidence)
    http_sup = res_sup.to_http_response()
    assert http_sup["status"] == "supported"
    assert http_sup["is_abstained"] is False
    assert http_sup["reasons"] == []


def test_base_model_abstained_propagation(
    evaluator: SupportEvaluator, standard_profile: CandidateProfile
) -> None:
    """Verify evaluator propagates base model or conformal calibrator abstentions."""
    abstained_model_evidence = CohortEvidenceContext(
        cohort_size=30,
        category_seen_count=30,
        base_model_abstained=True,
        base_model_abstention_reason="CALIBRATION_SET_EMPTY",
    )
    res = evaluator.evaluate_support(standard_profile, abstained_model_evidence)
    assert res.is_abstained is True
    assert AbstentionReason.MODEL_ABSTAINED in res.reasons


def test_compute_cohort_evidence_table(evaluator: SupportEvaluator) -> None:
    """Verify precomputing cohort statistics from a Polars DataFrame."""
    today = datetime.date(2026, 10, 18)
    records = [
        {
            "role_family": "SOFTWARE",
            "seniority": "MID",
            "location": "BANGALORE",
            "years_experience": 4.0,
            "effective_on": datetime.date(2026, 8, 1),
            "source_quality_score": 88.0,
            "provenance_tier": "TIER_A",
        },
        {
            "role_family": "SOFTWARE",
            "seniority": "MID",
            "location": "BANGALORE",
            "years_experience": 5.0,
            "effective_on": datetime.date(2026, 9, 1),
            "source_quality_score": 86.0,
            "provenance_tier": "TIER_A",
        },
        {
            "role_family": "DATA",
            "seniority": "SENIOR",
            "location": "HYDERABAD",
            "years_experience": 8.0,
            "effective_on": datetime.date(2025, 5, 1),
            "source_quality_score": 75.0,
            "provenance_tier": "TIER_B",
        },
    ]
    df = pl.DataFrame(records)
    cohorts = evaluator.compute_cohort_evidence_table(df, as_of_date=today)

    assert len(cohorts) == 2
    swe_mid_blr = cohorts[("SOFTWARE", "MID", "BANGALORE")]
    assert swe_mid_blr.cohort_size == 2
    assert swe_mid_blr.source_quality_score == 87.0
    assert swe_mid_blr.provenance_tier == "TIER_A"
    assert swe_mid_blr.median_observation_age_days > 0.0

    data_sr_hyd = cohorts[("DATA", "SENIOR", "HYDERABAD")]
    assert data_sr_hyd.cohort_size == 1
    assert data_sr_hyd.provenance_tier == "TIER_B"
    assert data_sr_hyd.median_observation_age_days > 365.0  # from 2025-05-01 to 2026-10-18
