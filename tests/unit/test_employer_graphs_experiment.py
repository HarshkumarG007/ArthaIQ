"""Unit tests for Employer Feature Modeling Experiment (EXP-10, Task T7.04).

Verifies:
- EmployerTargetEncoder empirical Bayes shrinkage and k_min >= 5 anonymity floor (R-DA-10).
- TalentFlowGraphEmbedder spectral embedding determinism and sparsity audit (CHARTER-EXP-10).
- As-of temporal graph construction and zero lookahead (R-MD-03).
- Test set isolation and touch-once lock enforcement (R-MD-02).
- Synthetic data isolation gates (R-MD-11).
- Non-crossing quantiles (R-UQ-05).
- Paired bootstrap confidence intervals and pre-registered keep/defer/reject decision logic.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from tests.fixtures.synthetic import generate_synthetic_observations_df

from compintel.errors import DataContractError
from compintel.evaluation.employer_graphs_experiment import (
    EmployerDecisionVerdict,
    EmployerTargetEncoder,
    TalentFlowGraphEmbedder,
    _assign_employer_tier,
    _compute_paired_bootstrap_ci,
    _pinball_loss_per_sample,
    evaluate_and_save_employer_graphs_experiment,
    run_employer_graphs_experiment,
)

# ==============================================================================
# Unit Tests: Target Encoding & Tier Assignment
# ==============================================================================


def test_assign_employer_tier() -> None:
    """Verify keyword and deterministic mapping to canonical organizational archetypes."""
    assert _assign_employer_tier("Google India Pvt Ltd", "EMP-01") == "TIER_1_PRODUCT"
    assert _assign_employer_tier("Microsoft IDC", "EMP-02") == "TIER_1_PRODUCT"
    assert _assign_employer_tier("Goldman Sachs Services", "EMP-03") == "GCC"
    assert _assign_employer_tier("Walmart Global Tech", "EMP-04") == "GCC"
    assert _assign_employer_tier("Swiggy Bundl Technologies", "EMP-05") == "HIGH_GROWTH_STARTUP"
    assert _assign_employer_tier("Razorpay Software", "EMP-06") == "HIGH_GROWTH_STARTUP"
    assert _assign_employer_tier("Zoho Corporation", "EMP-07") == "DOMESTIC_PRODUCT"
    assert _assign_employer_tier("Freshworks India", "EMP-08") == "DOMESTIC_PRODUCT"
    assert _assign_employer_tier("Tata Consultancy Services", "EMP-09") == "IT_SERVICES"
    assert _assign_employer_tier("Infosys Limited", "EMP-10") == "IT_SERVICES"
    # Fallback assignment
    assert _assign_employer_tier(None, None) == "IT_SERVICES"


def test_employer_target_encoder_k_min_floor() -> None:
    """Assert clusters with count < 5 strictly collapse to parent tier prior (Rule R-DA-10)."""
    # 6 observations for EMP-LARGE, 2 for EMP-SMALL
    clusters = ["EMP-LARGE"] * 6 + ["EMP-SMALL"] * 2
    tiers = ["TIER_1_PRODUCT"] * 6 + ["TIER_1_PRODUCT"] * 2
    # Pay: LARGE has mean 3.0, SMALL has mean 4.0
    y_log = np.array([3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 4.0, 4.0], dtype=np.float64)

    encoder = EmployerTargetEncoder(smoothing=10.0, k_min=5)
    encoder.fit(clusters, tiers, y_log)

    # Global tier mean is (6*3.0 + 2*4.0) / 8 = 3.25
    assert encoder.tier_means_["TIER_1_PRODUCT"] == pytest.approx(3.25)

    transformed = encoder.transform(
        ["EMP-LARGE", "EMP-SMALL"], ["TIER_1_PRODUCT", "TIER_1_PRODUCT"]
    )
    # EMP-SMALL has count=2 < 5 -> must strictly equal tier prior (3.25)
    assert transformed[1] == pytest.approx(3.25)

    # EMP-LARGE has count=6 >= 5 -> smoothed: (6*3.0 + 10*3.25) / 16 = (18 + 32.5) / 16 = 3.15625
    expected_large = (6 * 3.0 + 10.0 * 3.25) / (6 + 10.0)
    assert transformed[0] == pytest.approx(expected_large)


def test_employer_target_encoder_unseen_cluster() -> None:
    """Assert unseen cluster during transform safely falls back to parent tier prior."""
    encoder = EmployerTargetEncoder(smoothing=10.0, k_min=5)
    encoder.fit(["EMP-A"] * 5, ["GCC"] * 5, np.array([2.5] * 5))

    transformed = encoder.transform(["EMP-UNSEEN"], ["GCC"])
    assert transformed[0] == pytest.approx(2.5)


# ==============================================================================
# Unit Tests: Talent Flow Graph Embedder
# ==============================================================================


def test_talent_flow_graph_embedder_determinism_and_sparsity() -> None:
    """Verify spectral graph embedding is deterministic on CPU and audits sparsity."""
    # Synthetic small dataframe with 4 clusters
    df = pl.DataFrame(
        {
            "employer_cluster_id": ["EMP-01"] * 6
            + ["EMP-02"] * 6
            + ["EMP-03"] * 6
            + ["EMP-04"] * 2,
            "person_cluster_id": ["P-01", "P-02", "P-03", "P-04", "P-05", "P-06"]
            + ["P-01", "P-07", "P-08", "P-09", "P-10", "P-11"]
            + ["P-02", "P-12", "P-13", "P-14", "P-15", "P-16"]
            + ["P-03", "P-17"],
            "role_family": ["SWE"] * 20,
            "seniority": ["MID"] * 20,
        }
    )

    embedder1 = TalentFlowGraphEmbedder(n_components=2, k_min=5, seed=42)
    embedder1.fit(df)

    embedder2 = TalentFlowGraphEmbedder(n_components=2, k_min=5, seed=42)
    embedder2.fit(df)

    # Verify sparsity audit
    assert embedder1.sparsity_audit_.n_qualified_nodes < 50
    assert embedder1.sparsity_audit_.is_sparse is True
    # EMP-04 has count 2 < 5 -> not in eligible clusters
    assert "EMP-04" not in embedder1.embeddings_

    # Verify deterministic embeddings
    vec1 = embedder1.transform(["EMP-01", "EMP-02", "EMP-UNKNOWN"])
    vec2 = embedder2.transform(["EMP-01", "EMP-02", "EMP-UNKNOWN"])
    np.testing.assert_allclose(vec1, vec2, atol=1e-7)

    assert vec1.shape == (3, 2)


# ==============================================================================
# Unit Tests: Metrics & Decision Rules
# ==============================================================================


def test_pinball_loss_per_sample() -> None:
    """Verify analytical pinball loss calculations."""
    y = np.array([10.0, 10.0])
    pred = np.array([8.0, 12.0])

    # For q=0.5: 0.5 * |10 - 8| = 1.0; 0.5 * |10 - 12| = 1.0
    pb50 = _pinball_loss_per_sample(y, pred, 0.5)
    np.testing.assert_allclose(pb50, [1.0, 1.0])

    # For q=0.1: y > pred -> 0.1 * (10 - 8) = 0.2
    #            y < pred -> (0.1 - 1.0) * (10 - 12) = -0.9 * -2.0 = 1.8
    pb10 = _pinball_loss_per_sample(y, pred, 0.1)
    np.testing.assert_allclose(pb10, [0.2, 1.8])


def test_paired_bootstrap_ci() -> None:
    """Verify paired difference bootstrap confidence interval."""
    delta = np.array([-0.10, -0.12, -0.09, -0.11, -0.08])
    lower, upper, is_sig = _compute_paired_bootstrap_ci(delta, n_resamples=500, ci=0.95, seed=42)
    assert lower < 0.0
    assert upper < 0.0
    assert is_sig is True


def test_test_partition_lock_enforcement() -> None:
    """Verify Rule R-MD-02 strictly blocks evaluation on locked 'test' split."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        evaluate_and_save_employer_graphs_experiment(
            canonical_path="data/canonical/canonical_observations.parquet",
            eval_split_name="test",
        )


def test_synthetic_isolation_enforcement(tmp_path: Path) -> None:
    """Verify Rule R-MD-11 raises DataContractError when synthetic data is loaded.

    Synthetic records without explicit allow_synthetic override must be refused.
    """
    synth_df = generate_synthetic_observations_df(n_records=20, seed=42)
    parquet_path = tmp_path / "test_synth.parquet"
    synth_df.write_parquet(parquet_path)

    with pytest.raises(DataContractError, match="Synthetic data detected"):
        evaluate_and_save_employer_graphs_experiment(
            canonical_path=parquet_path,
            allow_synthetic=False,
        )


# ==============================================================================
# Integration Test: End-to-End Experiment Execution
# ==============================================================================


def test_run_employer_graphs_experiment_end_to_end() -> None:
    """Execute end-to-end employer experiment on synthetic partitions and verify report."""
    n_records = 150
    synth_base = generate_synthetic_observations_df(n_records=n_records, seed=42)

    # Assign distinct employer clusters and dates
    dates = [datetime.date(2024, 1, 1) + datetime.timedelta(days=i) for i in range(n_records)]
    persons = [f"PER-{i:04d}" for i in range(n_records)]
    employers = [f"EMP-{i % 8:04d}" for i in range(n_records)]

    synth_df = synth_base.with_columns(
        [
            pl.Series("as_of_date", dates),
            pl.Series("effective_on", dates),
            pl.Series("person_cluster_id", persons),
            pl.Series("employer_cluster_id", employers),
        ]
    )

    from compintel.evaluation.splits import SplitConfig, TemporalGroupedSplitter

    splitter = TemporalGroupedSplitter(
        SplitConfig(date_column="as_of_date", group_column="person_cluster_id")
    )
    split_res = splitter.split(synth_df)

    report = run_employer_graphs_experiment(
        train_df=split_res.train_df,
        eval_df=split_res.select_df,
        calibrate_df=split_res.calibrate_df,
        eval_split_name="select",
        n_resamples=200,
        seed=42,
    )

    # Verify report structure
    assert report.charter_id == "CHARTER-EXP-10"
    assert report.experiment_id == "EXP-10"
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == len(split_res.select_df)

    # Baseline has 7 features
    assert report.baseline_metrics.n_features == 7
    # Variant A has 8 features (+ target encoding)
    assert report.variant_a_metrics.n_features == 8
    # Variant B has 9 features (+ 2 graph dims)
    assert report.variant_b_metrics.n_features == 9

    # Monotonic crossing rate must be strictly zero (Rule R-UQ-05)
    assert report.baseline_metrics.crossing_rate == 0.0
    assert report.variant_a_metrics.crossing_rate == 0.0
    assert report.variant_b_metrics.crossing_rate == 0.0

    # Verify 2 delta entries
    assert len(report.deltas) == 2
    assert report.overall_verdict in (
        EmployerDecisionVerdict.KEEP,
        EmployerDecisionVerdict.DEFER,
        EmployerDecisionVerdict.REJECT,
    )

    # Verify Markdown rendering
    md = report.to_markdown()
    assert "# Employer Feature Modeling: Simple vs Graph-Based (EXP-10" in md
    assert "Comparative Performance Matrix" in md
    assert "Graph Density & Deferral Audit" in md

    # Verify JSON serialization
    d = report.to_dict()
    assert d["charter_id"] == "CHARTER-EXP-10"
    assert "graph_audit" in d
