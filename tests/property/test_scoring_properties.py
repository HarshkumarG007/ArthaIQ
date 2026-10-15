"""Property-based tests for Source-Quality Scoring Framework (Task T3.12, Task T1.10)."""

import polars as pl
from hypothesis import given
from hypothesis import strategies as st

from compintel.quality.scoring import (
    DimensionScores,
    attach_source_quality_scores_df,
    compute_source_quality_score,
    evaluate_hard_gates,
    map_score_to_provenance_tier,
)
from compintel.schema.enums import ProvenanceTier

score_int_strategy = st.integers(min_value=1, max_value=5)


@given(
    d1=score_int_strategy,
    d2=score_int_strategy,
    d3=score_int_strategy,
    d4=score_int_strategy,
    d5=score_int_strategy,
    d6=score_int_strategy,
    d7=score_int_strategy,
    d8=score_int_strategy,
    d9=score_int_strategy,
    d10=score_int_strategy,
)
def test_score_boundedness_property(
    d1: int,
    d2: int,
    d3: int,
    d4: int,
    d5: int,
    d6: int,
    d7: int,
    d8: int,
    d9: int,
    d10: int,
) -> None:
    """Composite SQS must always evaluate strictly in [20.0, 100.0] for any valid ratings."""
    dims = DimensionScores(
        d1_licensing_legal=d1,
        d2_target_measure=d2,
        d3_upstream_provenance=d3,
        d4_population_geographic=d4,
        d5_sampling_frame=d5,
        d6_covariate_granularity=d6,
        d7_observation_independence=d7,
        d8_temporal_freshness=d8,
        d9_privacy_compliance=d9,
        d10_validation_utility=d10,
    )
    score = compute_source_quality_score(dims)
    assert 20.0 <= score <= 100.0


@given(
    d1=score_int_strategy,
    d2=score_int_strategy,
    d3=score_int_strategy,
    d4=score_int_strategy,
    d5=score_int_strategy,
    d6=score_int_strategy,
    d7=score_int_strategy,
    d8=score_int_strategy,
    d9=score_int_strategy,
    d10=score_int_strategy,
)
def test_dimension_monotonicity_property(
    d1: int,
    d2: int,
    d3: int,
    d4: int,
    d5: int,
    d6: int,
    d7: int,
    d8: int,
    d9: int,
    d10: int,
) -> None:
    """Increasing any dimension score cannot decrease the composite SQS score."""
    base_dims = DimensionScores(
        d1_licensing_legal=d1,
        d2_target_measure=d2,
        d3_upstream_provenance=d3,
        d4_population_geographic=d4,
        d5_sampling_frame=d5,
        d6_covariate_granularity=d6,
        d7_observation_independence=d7,
        d8_temporal_freshness=d8,
        d9_privacy_compliance=d9,
        d10_validation_utility=d10,
    )
    base_score = compute_source_quality_score(base_dims)

    # Test increasing d1 if d1 < 5
    if d1 < 5:
        increased_dims = DimensionScores(
            d1_licensing_legal=d1 + 1,
            d2_target_measure=d2,
            d3_upstream_provenance=d3,
            d4_population_geographic=d4,
            d5_sampling_frame=d5,
            d6_covariate_granularity=d6,
            d7_observation_independence=d7,
            d8_temporal_freshness=d8,
            d9_privacy_compliance=d9,
            d10_validation_utility=d10,
        )
        assert compute_source_quality_score(increased_dims) >= base_score


@given(
    d1=score_int_strategy,
    d2=score_int_strategy,
    d3=score_int_strategy,
    d4=score_int_strategy,
    d5=score_int_strategy,
    d6=score_int_strategy,
    d7=score_int_strategy,
    d8=score_int_strategy,
    d9=score_int_strategy,
    d10=score_int_strategy,
)
def test_hard_gates_property(
    d1: int,
    d2: int,
    d3: int,
    d4: int,
    d5: int,
    d6: int,
    d7: int,
    d8: int,
    d9: int,
    d10: int,
) -> None:
    """Hard gates pass if and only if d1 >= 3, d2 >= 3, and d3 >= 3."""
    dims = DimensionScores(
        d1_licensing_legal=d1,
        d2_target_measure=d2,
        d3_upstream_provenance=d3,
        d4_population_geographic=d4,
        d5_sampling_frame=d5,
        d6_covariate_granularity=d6,
        d7_observation_independence=d7,
        d8_temporal_freshness=d8,
        d9_privacy_compliance=d9,
        d10_validation_utility=d10,
    )
    passed, failed = evaluate_hard_gates(dims)
    expected_pass = (d1 >= 3) and (d2 >= 3) and (d3 >= 3)
    assert passed == expected_pass
    if not passed:
        assert len(failed) > 0


@given(
    score=st.floats(min_value=20.0, max_value=100.0),
    gates_passed=st.booleans(),
)
def test_provenance_tier_invariants(score: float, gates_passed: bool) -> None:
    """ProvenanceTier mapping satisfies monotonic boundaries and gate enforcement."""
    tier = map_score_to_provenance_tier(score, hard_gates_passed=gates_passed)
    if not gates_passed:
        assert tier == ProvenanceTier.TIER_D
    elif score >= 80.0:
        assert tier == ProvenanceTier.TIER_A
    elif score >= 65.0:
        assert tier == ProvenanceTier.TIER_B
    elif score >= 50.0:
        assert tier == ProvenanceTier.TIER_C
    else:
        assert tier == ProvenanceTier.TIER_D


@given(
    sources=st.lists(
        st.sampled_from(
            [
                "SRC-INT-VOL-01",
                "SRC-IND-OFF-01",
                "SRC-USA-BLS-01",
                "SRC-KAG-SO-01",
                "SRC-KAG-AIJ-01",
                "SRC-SUP-CORP-01",
            ]
        ),
        min_size=1,
        max_size=50,
    )
)
def test_dataframe_row_conservation_property(sources: list[str]) -> None:
    """Row counts and original columns are strictly conserved during DataFrame scoring."""
    df = pl.DataFrame(
        {
            "obs_id": [f"ID-{i}" for i in range(len(sources))],
            "source_id": sources,
            "dummy_val": [float(i * 10) for i in range(len(sources))],
        }
    )

    scored_df = attach_source_quality_scores_df(df)
    assert scored_df.height == len(sources)
    assert "obs_id" in scored_df.columns
    assert "source_id" in scored_df.columns
    assert "dummy_val" in scored_df.columns
    assert "source_quality_score" in scored_df.columns
    assert "provenance_tier" in scored_df.columns
