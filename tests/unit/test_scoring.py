"""Unit tests for Source-Quality Scoring Framework (SQSF) Engine (Task T3.12, Task T1.10)."""

from pathlib import Path

import polars as pl
import pytest
from pydantic import ValidationError

from compintel.errors import DataContractError
from compintel.quality.scoring import (
    DEFAULT_SOURCE_QUALITY_REGISTRY,
    DIMENSION_WEIGHTS,
    DimensionScores,
    SourceQualityEvaluation,
    SQSFClassificationTier,
    attach_source_quality_scores_df,
    classify_sqsf_tier,
    compute_source_quality_score,
    evaluate_hard_gates,
    evaluate_source,
    generate_source_quality_report,
    get_source_quality_evaluation,
    load_source_scoring_from_yaml,
    map_score_to_provenance_tier,
    score_observation,
)
from compintel.schema.enums import ProvenanceTier


def test_dimension_weights_sum_to_one() -> None:
    """Dimension weights must sum to exactly 1.00 (Rule R-EV-07, T1.10)."""
    assert sum(DIMENSION_WEIGHTS.values()) == pytest.approx(1.00, abs=1e-6)
    assert len(DIMENSION_WEIGHTS) == 10


def test_dimension_scores_validation() -> None:
    """Dimension scores must be integers strictly in [1, 5]."""
    # Valid instance
    valid = DimensionScores(
        d1_licensing_legal=5,
        d2_target_measure=4,
        d3_upstream_provenance=5,
        d4_population_geographic=3,
        d5_sampling_frame=5,
        d6_covariate_granularity=4,
        d7_observation_independence=5,
        d8_temporal_freshness=4,
        d9_privacy_compliance=5,
        d10_validation_utility=4,
    )
    assert valid.d1_licensing_legal == 5

    # Out of bounds (< 1)
    with pytest.raises(ValidationError):
        DimensionScores(
            d1_licensing_legal=0,
            d2_target_measure=4,
            d3_upstream_provenance=5,
            d4_population_geographic=3,
            d5_sampling_frame=5,
            d6_covariate_granularity=4,
            d7_observation_independence=5,
            d8_temporal_freshness=4,
            d9_privacy_compliance=5,
            d10_validation_utility=4,
        )

    # Out of bounds (> 5)
    with pytest.raises(ValidationError):
        DimensionScores(
            d1_licensing_legal=6,
            d2_target_measure=4,
            d3_upstream_provenance=5,
            d4_population_geographic=3,
            d5_sampling_frame=5,
            d6_covariate_granularity=4,
            d7_observation_independence=5,
            d8_temporal_freshness=4,
            d9_privacy_compliance=5,
            d10_validation_utility=4,
        )


def test_compute_source_quality_score_extremes() -> None:
    """Extreme dimension score vectors must evaluate to 20.0 and 100.0."""
    all_min = DimensionScores(
        d1_licensing_legal=1,
        d2_target_measure=1,
        d3_upstream_provenance=1,
        d4_population_geographic=1,
        d5_sampling_frame=1,
        d6_covariate_granularity=1,
        d7_observation_independence=1,
        d8_temporal_freshness=1,
        d9_privacy_compliance=1,
        d10_validation_utility=1,
    )
    assert compute_source_quality_score(all_min) == 20.0

    all_max = DimensionScores(
        d1_licensing_legal=5,
        d2_target_measure=5,
        d3_upstream_provenance=5,
        d4_population_geographic=5,
        d5_sampling_frame=5,
        d6_covariate_granularity=5,
        d7_observation_independence=5,
        d8_temporal_freshness=5,
        d9_privacy_compliance=5,
        d10_validation_utility=5,
    )
    assert compute_source_quality_score(all_max) == 100.0


def test_compute_source_quality_score_audited_anchors() -> None:
    """Test audited scores from 05-source-scoring.md."""
    # MOSPI PLFS 2023-24 (SRC-IND-OFF-01): Q = 82.6
    plfs_dims = DimensionScores(
        d1_licensing_legal=5,
        d2_target_measure=3,
        d3_upstream_provenance=5,
        d4_population_geographic=3,
        d5_sampling_frame=5,
        d6_covariate_granularity=3,
        d7_observation_independence=5,
        d8_temporal_freshness=4,
        d9_privacy_compliance=5,
        d10_validation_utility=4,
    )
    assert compute_source_quality_score(plfs_dims) == 82.6

    # ArthaIQ Voluntary (SRC-INT-VOL-01): Q = 96.0
    vol_dims = DimensionScores(
        d1_licensing_legal=5,
        d2_target_measure=5,
        d3_upstream_provenance=5,
        d4_population_geographic=5,
        d5_sampling_frame=3,
        d6_covariate_granularity=5,
        d7_observation_independence=5,
        d8_temporal_freshness=5,
        d9_privacy_compliance=5,
        d10_validation_utility=5,
    )
    assert compute_source_quality_score(vol_dims) == 96.0

    # BSE / NSE (SRC-SUP-CORP-01 dimensions: 20 * 4.42 = 88.4)
    corp_dims = DimensionScores(
        d1_licensing_legal=5,
        d2_target_measure=4,
        d3_upstream_provenance=5,
        d4_population_geographic=5,
        d5_sampling_frame=5,
        d6_covariate_granularity=2,
        d7_observation_independence=5,
        d8_temporal_freshness=4,
        d9_privacy_compliance=5,
        d10_validation_utility=4,
    )
    assert compute_source_quality_score(corp_dims) == 88.4


def test_evaluate_hard_gates() -> None:
    """Non-compensatory hard gates must disqualify sources failing D1, D2, or D3."""
    # All pass
    dims_pass = DimensionScores(
        d1_licensing_legal=3,
        d2_target_measure=3,
        d3_upstream_provenance=3,
        d4_population_geographic=1,
        d5_sampling_frame=1,
        d6_covariate_granularity=1,
        d7_observation_independence=1,
        d8_temporal_freshness=1,
        d9_privacy_compliance=1,
        d10_validation_utility=1,
    )
    passed, failed = evaluate_hard_gates(dims_pass)
    assert passed is True
    assert len(failed) == 0

    # D1 fail (scraping breach)
    dims_d1_fail = DimensionScores(
        d1_licensing_legal=1,
        d2_target_measure=5,
        d3_upstream_provenance=5,
        d4_population_geographic=5,
        d5_sampling_frame=5,
        d6_covariate_granularity=5,
        d7_observation_independence=5,
        d8_temporal_freshness=5,
        d9_privacy_compliance=5,
        d10_validation_utility=5,
    )
    passed, failed = evaluate_hard_gates(dims_d1_fail)
    assert passed is False
    assert any("Gate 1 (Legal)" in msg for msg in failed)

    # D2 fail (target measure mismatch)
    dims_d2_fail = DimensionScores(
        d1_licensing_legal=5,
        d2_target_measure=2,
        d3_upstream_provenance=5,
        d4_population_geographic=5,
        d5_sampling_frame=5,
        d6_covariate_granularity=5,
        d7_observation_independence=5,
        d8_temporal_freshness=5,
        d9_privacy_compliance=5,
        d10_validation_utility=5,
    )
    passed, failed = evaluate_hard_gates(dims_d2_fail)
    assert passed is False
    assert any("Gate 2 (Target)" in msg for msg in failed)

    # D3 fail (unverified provenance)
    dims_d3_fail = DimensionScores(
        d1_licensing_legal=5,
        d2_target_measure=5,
        d3_upstream_provenance=1,
        d4_population_geographic=5,
        d5_sampling_frame=5,
        d6_covariate_granularity=5,
        d7_observation_independence=5,
        d8_temporal_freshness=5,
        d9_privacy_compliance=5,
        d10_validation_utility=5,
    )
    passed, failed = evaluate_hard_gates(dims_d3_fail)
    assert passed is False
    assert any("Gate 3 (Provenance)" in msg for msg in failed)


def test_map_score_to_provenance_tier() -> None:
    """ProvenanceTier mapping must follow strict SQS thresholds and gate compliance."""
    assert map_score_to_provenance_tier(90.0, hard_gates_passed=True) == ProvenanceTier.TIER_A
    assert map_score_to_provenance_tier(80.0, hard_gates_passed=True) == ProvenanceTier.TIER_A
    assert map_score_to_provenance_tier(79.9, hard_gates_passed=True) == ProvenanceTier.TIER_B
    assert map_score_to_provenance_tier(65.0, hard_gates_passed=True) == ProvenanceTier.TIER_B
    assert map_score_to_provenance_tier(64.9, hard_gates_passed=True) == ProvenanceTier.TIER_C
    assert map_score_to_provenance_tier(50.0, hard_gates_passed=True) == ProvenanceTier.TIER_C
    assert map_score_to_provenance_tier(49.9, hard_gates_passed=True) == ProvenanceTier.TIER_D
    assert map_score_to_provenance_tier(20.0, hard_gates_passed=True) == ProvenanceTier.TIER_D

    # Hard gate failure forces Tier D regardless of SQS
    assert map_score_to_provenance_tier(95.0, hard_gates_passed=False) == ProvenanceTier.TIER_D


def test_classify_sqsf_tier() -> None:
    """Operational tier classification must reflect score and gate criteria."""
    assert (
        classify_sqsf_tier(90.0, hard_gates_passed=True)
        == SQSFClassificationTier.TIER_1_GROUND_TRUTH
    )
    assert (
        classify_sqsf_tier(80.0, hard_gates_passed=True)
        == SQSFClassificationTier.TIER_2_POPULATION_BENCHMARK
    )
    assert (
        classify_sqsf_tier(70.0, hard_gates_passed=True)
        == SQSFClassificationTier.TIER_3_MARKET_SIGNAL
    )
    assert (
        classify_sqsf_tier(62.0, hard_gates_passed=True)
        == SQSFClassificationTier.TIER_4_SUPPLEMENTARY
    )
    assert (
        classify_sqsf_tier(55.0, hard_gates_passed=True)
        == SQSFClassificationTier.TIER_6_DISQUALIFIED
    )

    # Gate failures
    assert (
        classify_sqsf_tier(50.0, hard_gates_passed=False, d1_score=2, d2_score=2, d3_score=3)
        == SQSFClassificationTier.TIER_5_TEST_FIXTURE
    )
    assert (
        classify_sqsf_tier(50.0, hard_gates_passed=False, d1_score=1, d2_score=5, d3_score=5)
        == SQSFClassificationTier.TIER_6_DISQUALIFIED
    )


def test_evaluate_source_integration() -> None:
    """evaluate_source must synthesize score, gates, tiers, and PT1 eligibility."""
    vol_dims = DimensionScores(
        d1_licensing_legal=5,
        d2_target_measure=5,
        d3_upstream_provenance=5,
        d4_population_geographic=5,
        d5_sampling_frame=3,
        d6_covariate_granularity=5,
        d7_observation_independence=5,
        d8_temporal_freshness=5,
        d9_privacy_compliance=5,
        d10_validation_utility=5,
    )
    eval_res = evaluate_source("SRC-INT-VOL-01", vol_dims, notes="Primary intake")
    assert eval_res.score == 96.0
    assert eval_res.hard_gates_passed is True
    assert eval_res.provenance_tier == ProvenanceTier.TIER_A
    assert eval_res.sqsf_tier == SQSFClassificationTier.TIER_1_GROUND_TRUTH
    assert eval_res.is_pt1_training_eligible is True


def test_default_source_registry_completeness() -> None:
    """DEFAULT_SOURCE_QUALITY_REGISTRY must contain all ratified candidate and approved sources."""
    expected_sources = [
        "SRC-INT-VOL-01",
        "SRC-IND-OFF-01",
        "SRC-IND-OFF-02",
        "SRC-IND-OFF-03",
        "SRC-IND-OFF-04",
        "SRC-USA-BLS-01",
        "SRC-USA-DOL-01",
        "SRC-USA-DOL-02",
        "SRC-SUP-MAC-01",
        "SRC-SUP-TAX-01",
        "SRC-SUP-TAX-02",
        "SRC-SUP-CORP-01",
        "SRC-KAG-AIJ-01",
        "SRC-KAG-AIJ-02",
        "SRC-KAG-SO-01",
        "SRC-KAG-SO-02",
        "SRC-KAG-FIX-01",
        "SRC-KAG-FIX-02",
        "SRC-KAG-FIX-03",
        "SRC-KAG-REJ-01",
        "SRC-KAG-REJ-02",
        "SRC-KAG-REJ-03",
    ]
    for sid in expected_sources:
        assert sid in DEFAULT_SOURCE_QUALITY_REGISTRY, f"Missing source {sid} in registry"
        eval_item = DEFAULT_SOURCE_QUALITY_REGISTRY[sid]
        assert 20.0 <= eval_item.score <= 100.0

    # Only SRC-INT-VOL-01 is PT1 eligible in initial Phase 3 state
    pt1_eligible = [
        sid
        for sid, item in DEFAULT_SOURCE_QUALITY_REGISTRY.items()
        if item.is_pt1_training_eligible
    ]
    assert pt1_eligible == ["SRC-INT-VOL-01"]


def test_load_source_scoring_from_yaml(tmp_path: Path) -> None:
    """load_source_scoring_from_yaml must correctly parse configuration files."""
    # Test on real config file if present
    real_file = Path("config/sources/SRC-IND-OFF-01.yaml")
    if real_file.exists():
        eval_res = load_source_scoring_from_yaml(real_file)
        assert eval_res.source_id == "SRC-IND-OFF-01"
        assert eval_res.score == 82.6
        assert eval_res.provenance_tier == ProvenanceTier.TIER_A
        assert eval_res.sqsf_tier == SQSFClassificationTier.TIER_2_POPULATION_BENCHMARK
        assert eval_res.hard_gates_passed is True
        assert eval_res.is_pt1_training_eligible is False

    # Test error handling on missing file
    with pytest.raises(DataContractError) as exc_info:
        load_source_scoring_from_yaml(tmp_path / "non_existent.yaml")
    assert "SOURCE_CONFIG_NOT_FOUND" in str(exc_info.value.code)

    # Test error handling on file missing sqs field
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("source_id: BAD-01\nnotes: test", encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        load_source_scoring_from_yaml(bad_yaml)
    assert "MISSING_SQS_FIELD" in str(exc_info.value.code)


def test_get_source_quality_evaluation() -> None:
    """get_source_quality_evaluation must resolve registry, files, and fallback cleanly."""
    # Default registry lookup
    eval_vol = get_source_quality_evaluation("SRC-INT-VOL-01")
    assert eval_vol.score == 96.0
    assert eval_vol.provenance_tier == ProvenanceTier.TIER_A

    # Unknown source fallback
    eval_unknown = get_source_quality_evaluation("SRC-UNKNOWN-999")
    assert eval_unknown.score == 20.0
    assert eval_unknown.provenance_tier == ProvenanceTier.TIER_D
    assert eval_unknown.hard_gates_passed is False
    assert eval_unknown.is_pt1_training_eligible is False

    # Custom registry override
    custom_eval = SourceQualityEvaluation(
        source_id="CUSTOM-01",
        score=88.0,
        provenance_tier=ProvenanceTier.TIER_A,
        sqsf_tier=SQSFClassificationTier.TIER_1_GROUND_TRUTH,
        hard_gates_passed=True,
        is_pt1_training_eligible=True,
    )
    eval_custom = get_source_quality_evaluation("CUSTOM-01", registry={"CUSTOM-01": custom_eval})
    assert eval_custom.score == 88.0


def test_score_observation_dict() -> None:
    """score_observation must attach required scoring metadata to observation dictionary."""
    record = {
        "observation_id": "OBS-001",
        "source_id": "SRC-IND-OFF-01",
        "guaranteed_cash_annual": 18.5,
    }
    enriched = score_observation(record)
    assert enriched["source_quality_score"] == 82.6
    assert enriched["provenance_tier"] == "A"
    assert enriched["sqsf_tier"] == "TIER_2_POPULATION_BENCHMARK"
    assert enriched["hard_gates_passed"] is True
    assert enriched["is_pt1_eligible"] is False

    # Strict mode on unknown source
    unknown_record = {"observation_id": "OBS-002", "source_id": "SRC-UNKNOWN-01"}
    with pytest.raises(DataContractError) as exc_info:
        score_observation(unknown_record, strict=True)
    assert "UNVERIFIED_SOURCE_ERROR" in str(exc_info.value.code)


def test_attach_source_quality_scores_df_multi_source() -> None:
    """attach_source_quality_scores_df must attach scores to DataFrame with zero silent drops."""
    df = pl.DataFrame(
        {
            "observation_id": ["OBS-1", "OBS-2", "OBS-3", "OBS-4"],
            "source_id": ["SRC-INT-VOL-01", "SRC-IND-OFF-01", "SRC-USA-BLS-01", "SRC-KAG-FIX-01"],
            "raw_pay": [25.0, 15.0, 120000.0, 12.0],
        }
    )

    scored_df = attach_source_quality_scores_df(df)
    assert scored_df.height == 4
    assert "source_quality_score" in scored_df.columns
    assert "provenance_tier" in scored_df.columns
    assert "sqsf_tier" in scored_df.columns
    assert "hard_gates_passed" in scored_df.columns
    assert "is_pt1_eligible" in scored_df.columns

    # Verify individual scores
    scores = scored_df["source_quality_score"].to_list()
    assert scores == [96.0, 82.6, 78.2, 38.0]

    tiers = scored_df["provenance_tier"].to_list()
    assert tiers == ["A", "A", "B", "D"]

    pt1_elig = scored_df["is_pt1_eligible"].to_list()
    assert pt1_elig == [True, False, False, False]


def test_attach_source_quality_scores_df_empty() -> None:
    """Empty DataFrame must be enriched with empty typed scoring columns."""
    df = pl.DataFrame({"source_id": pl.Series([], dtype=pl.String)})
    scored_df = attach_source_quality_scores_df(df)
    assert scored_df.height == 0
    assert "source_quality_score" in scored_df.columns
    assert scored_df.schema["source_quality_score"] == pl.Float64
    assert scored_df.schema["provenance_tier"] == pl.String


def test_attach_source_quality_scores_df_missing_column() -> None:
    """Missing 'source_id' column must raise DataContractError."""
    df = pl.DataFrame({"wrong_col": [1, 2, 3]})
    with pytest.raises(DataContractError) as exc_info:
        attach_source_quality_scores_df(df)
    assert "MISSING_SOURCE_ID_COLUMN" in str(exc_info.value.code)


def test_attach_source_quality_scores_df_strict_mode() -> None:
    """strict=True must raise DataContractError if unverified sources are present."""
    df = pl.DataFrame(
        {
            "source_id": ["SRC-INT-VOL-01", "SRC-UNVERIFIED-XYZ"],
            "val": [10.0, 20.0],
        }
    )
    with pytest.raises(DataContractError) as exc_info:
        attach_source_quality_scores_df(df, strict=True)
    assert "UNVERIFIED_SOURCE_ERROR" in str(exc_info.value.code)

    # Under strict=False, unknown source receives fallback defaults
    non_strict_df = attach_source_quality_scores_df(df, strict=False)
    assert non_strict_df.height == 2
    row_unverified = non_strict_df.filter(pl.col("source_id") == "SRC-UNVERIFIED-XYZ").to_dicts()[0]
    assert row_unverified["source_quality_score"] == 20.0
    assert row_unverified["provenance_tier"] == "D"
    assert row_unverified["hard_gates_passed"] is False


def test_source_quality_report_generation() -> None:
    """generate_source_quality_report must summarize scoring metrics accurately."""
    df = pl.DataFrame(
        {
            "source_id": [
                "SRC-INT-VOL-01",
                "SRC-INT-VOL-01",
                "SRC-IND-OFF-01",
                "SRC-USA-BLS-01",
                "SRC-KAG-FIX-01",
            ],
            "val": [1, 2, 3, 4, 5],
        }
    )

    report = generate_source_quality_report(df)
    assert report.total_observations == 5
    assert report.distinct_sources == 4
    assert report.pt1_eligible_count == 2
    assert report.pt1_ineligible_count == 3
    assert report.provenance_tier_counts["A"] == 3  # 2 voluntary + 1 PLFS
    assert report.provenance_tier_counts["B"] == 1  # 1 BLS
    assert report.provenance_tier_counts["D"] == 1  # 1 test fixture

    md = report.to_markdown()
    assert "# Source-Quality Scoring Audit Report" in md
    assert "SRC-INT-VOL-01" in md
    assert "Tier A" in md

    # Empty report handling
    empty_df = pl.DataFrame({"source_id": pl.Series([], dtype=pl.String)})
    empty_report = generate_source_quality_report(empty_df)
    assert empty_report.total_observations == 0
    assert empty_report.mean_sqs == 0.0


def test_load_source_scoring_corrupted_yaml(tmp_path: Path) -> None:
    """Corrupted YAML content must raise DataContractError with SOURCE_CONFIG_PARSE_ERROR."""
    corrupted_yaml = tmp_path / "corrupted.yaml"
    corrupted_yaml.write_text(":\n  - [unbalanced: {{", encoding="utf-8")
    with pytest.raises(DataContractError) as exc_info:
        load_source_scoring_from_yaml(corrupted_yaml)
    assert "SOURCE_CONFIG_PARSE_ERROR" in str(exc_info.value.code)


def test_load_source_scoring_all_tier_variations(tmp_path: Path) -> None:
    """load_source_scoring_from_yaml must normalize all tier string variants."""
    tiers_to_test = [
        ("TIER_1_GROUND_TRUTH", SQSFClassificationTier.TIER_1_GROUND_TRUTH),
        ("TIER_3_MARKET_SIGNAL", SQSFClassificationTier.TIER_3_MARKET_SIGNAL),
        ("TIER_4_SUPPLEMENTARY", SQSFClassificationTier.TIER_4_SUPPLEMENTARY),
        ("TIER_5_TEST_FIXTURE", SQSFClassificationTier.TIER_5_TEST_FIXTURE),
        ("TIER_6_DISQUALIFIED", SQSFClassificationTier.TIER_6_DISQUALIFIED),
    ]
    for tier_str, expected_enum in tiers_to_test:
        f = tmp_path / f"{tier_str}.yaml"
        f.write_text(f"source_id: {tier_str}\nsqs: 70.0\nsqsf_tier: {tier_str}\n", encoding="utf-8")
        eval_res = load_source_scoring_from_yaml(f)
        assert eval_res.sqsf_tier == expected_enum


def test_get_source_quality_evaluation_with_config_dir(tmp_path: Path) -> None:
    """get_source_quality_evaluation must resolve YAML from provided config_dir."""
    src_file = tmp_path / "SRC-CUSTOM-CFG.yaml"
    src_file.write_text(
        "source_id: SRC-CUSTOM-CFG\nsqs: 85.0\nsqsf_tier: TIER_1_GROUND_TRUTH\n",
        encoding="utf-8",
    )
    eval_res = get_source_quality_evaluation("SRC-CUSTOM-CFG", config_dir=tmp_path)
    assert eval_res.source_id == "SRC-CUSTOM-CFG"
    assert eval_res.score == 85.0
    assert eval_res.sqsf_tier == SQSFClassificationTier.TIER_1_GROUND_TRUTH


def test_classify_sqsf_tier_d2_failures() -> None:
    """classify_sqsf_tier must handle D2 target failure branches properly."""
    # D2 failed (< 3), D3 >= 2 -> Tier 5 Test Fixture
    t5 = classify_sqsf_tier(score=50.0, hard_gates_passed=False, d1_score=5, d2_score=2, d3_score=4)
    assert t5 == SQSFClassificationTier.TIER_5_TEST_FIXTURE

    # D2 failed (< 3), D3 < 2 -> Tier 6 Disqualified
    t6 = classify_sqsf_tier(score=50.0, hard_gates_passed=False, d1_score=5, d2_score=2, d3_score=1)
    assert t6 == SQSFClassificationTier.TIER_6_DISQUALIFIED
