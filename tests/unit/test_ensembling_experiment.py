"""Unit and regression tests for Quantile Model Ensembling & Stacking (T7.06, EXP-ENSEMBLE-01).

Validates:
- Gate 1 data feasibility: audits non-synthetic observation count (< 100 triggers DEFER).
- Gate 2 algorithmic correctness: verifies convex quantile combination and monotone rearrangement.
- Rule R-UQ-05: strict non-crossing guarantee (P10 <= P50 <= P90, 0.0% crossing rate).
- Rule R-MD-11: synthetic data isolation guards.
- Preregistered DEFER outcome and production champion preservation.
- Clean-checkout independence from gitignored data (Rule R-DA-08).
"""

from __future__ import annotations

import datetime
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from compintel.errors import CompIntelValidationError
from compintel.evaluation.ensembling_experiment import (
    EnsembleDecisionVerdict,
    EnsembleFeasibilityStatus,
    QuantileEnsembleBlender,
    audit_ensemble_feasibility,
    run_ensembling_experiment,
)

# ==============================================================================
# Gate 1: Feasibility Audit Tests
# ==============================================================================


def test_gate1_feasibility_fails_on_canonical_short_sample() -> None:
    """Verify that canonical observations (5 records) fail Gate 1 (< 100) and defer."""
    canonical_path = Path("data/canonical/canonical_observations.parquet")
    if not canonical_path.exists():
        pytest.skip("Canonical dataset missing on clean checkout (gitignored per R-DA-08)")

    df = pl.read_parquet(canonical_path)
    audit = audit_ensemble_feasibility(
        df,
        min_required_records=100,
        allow_synthetic=False,
    )

    assert audit.status == EnsembleFeasibilityStatus.INSUFFICIENT_SAMPLE_SIZE
    assert audit.n_total_records < 100
    assert "defer" in audit.summary.lower()


def test_gate1_skips_modeling_and_records_defer_on_canonical_data() -> None:
    """Verify that Gate 1 skips expensive model fitting and records DEFER on canonical data."""
    canonical_path = Path("data/canonical/canonical_observations.parquet")
    if not canonical_path.exists():
        pytest.skip("Canonical dataset missing on clean checkout (gitignored per R-DA-08)")

    df = pl.read_parquet(canonical_path)
    report = run_ensembling_experiment(
        train_df=df,
        eval_df=df,
        calibrate_df=df,
        force_modeling=False,
        allow_synthetic=False,
    )

    assert report.overall_verdict == EnsembleDecisionVerdict.DEFER
    assert report.modeling_executed is False
    assert report.baseline_metrics is None
    assert report.variant_a_metrics is None
    assert len(report.deltas) == 0
    assert report.production_champion_retained is True
    assert "Gate 1 Feasibility DEFERRAL" in report.executive_summary


def test_gate1_feasibility_passes_on_sufficient_sample() -> None:
    """Verify that an observation panel with >= 100 records passes Gate 1."""
    n = 120
    df = pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n)],
            "guaranteed_cash_annual": [15.0 + (i % 25) for i in range(n)],
            "is_synthetic": [False] * n,
        }
    )

    audit = audit_ensemble_feasibility(df, min_required_records=100, allow_synthetic=False)
    assert audit.status == EnsembleFeasibilityStatus.FEASIBLE
    assert audit.n_total_records >= 100
    assert "Gate 1 feasibility passed" in audit.summary


def test_gate1_synthetic_data_blocked_without_override() -> None:
    """Verify that synthetic observations are rejected without explicit override (R-MD-11)."""
    df = pl.DataFrame(
        {
            "observation_id": ["S1", "S2"],
            "is_synthetic": [True, True],
        }
    )
    audit = audit_ensemble_feasibility(df, min_required_records=100, allow_synthetic=False)
    assert audit.status == EnsembleFeasibilityStatus.SYNTHETIC_DATA_BLOCKED
    assert audit.is_synthetic is True


# ==============================================================================
# Gate 2: Algorithmic Blender & Monotone Rearrangement Tests
# ==============================================================================


def test_quantile_ensemble_blender_convex_weights_and_projection() -> None:
    """Test convex combination and Chernozhukov monotone sorting projection (Rule R-UQ-05)."""
    # Create artificial inputs with intentional crossing quantiles
    # Model A: [P10=25.0, P50=20.0, P90=30.0] -> crossings present
    # Model B: [P10=22.0, P50=28.0, P90=26.0] -> crossings present
    model_a_p10 = np.array([25.0, 10.0])
    model_a_p50 = np.array([20.0, 15.0])
    model_a_p90 = np.array([30.0, 20.0])

    model_b_p10 = np.array([22.0, 8.0])
    model_b_p50 = np.array([28.0, 14.0])
    model_b_p90 = np.array([26.0, 22.0])

    blender = QuantileEnsembleBlender(weights={"catboost": 0.60, "lightgbm": 0.40})
    p10_clean, p50_clean, p90_clean, pre_crossing = blender.blend(
        {
            "catboost": (model_a_p10, model_a_p50, model_a_p90),
            "lightgbm": (model_b_p10, model_b_p50, model_b_p90),
        }
    )

    # Pre-repair crossings should be detected (> 0.0)
    assert pre_crossing > 0.0

    # Post-repair quantiles must strictly satisfy P10 <= P50 <= P90 (0.00% crossings)
    assert np.all(p10_clean <= p50_clean)
    assert np.all(p50_clean <= p90_clean)

    # First row check:
    # raw_p10 = 0.6*25 + 0.4*22 = 15.0 + 8.8 = 23.8
    # raw_p50 = 0.6*20 + 0.4*28 = 12.0 + 11.2 = 23.2
    # raw_p90 = 0.6*30 + 0.4*26 = 18.0 + 10.4 = 28.4
    # Raw values: [23.8, 23.2, 28.4] (P10 > P50 crossing!)
    # After sorting: [23.2, 23.8, 28.4]
    assert p10_clean[0] == pytest.approx(23.2, abs=1e-5)
    assert p50_clean[0] == pytest.approx(23.8, abs=1e-5)
    assert p90_clean[0] == pytest.approx(28.4, abs=1e-5)


def test_quantile_ensemble_blender_normalizes_weights() -> None:
    """Verify that unnormalized weights are safely normalized to sum to 1.0."""
    blender = QuantileEnsembleBlender(weights={"cat": 2.0, "lgb": 2.0})
    assert blender.weights["cat"] == pytest.approx(0.50)
    assert blender.weights["lgb"] == pytest.approx(0.50)


def test_quantile_ensemble_blender_validation_errors() -> None:
    """Verify input validation errors for weights and array dimensions."""
    # Empty weights
    with pytest.raises(CompIntelValidationError, match="cannot be empty"):
        QuantileEnsembleBlender(weights={})

    # Negative weight
    with pytest.raises(CompIntelValidationError, match="must be non-negative"):
        QuantileEnsembleBlender(weights={"cat": -0.5, "lgb": 1.5})

    # Empty predictions dict
    blender = QuantileEnsembleBlender()
    with pytest.raises(CompIntelValidationError, match="No model predictions"):
        blender.blend({})

    # Mismatched array length
    with pytest.raises(CompIntelValidationError, match="Mismatched prediction array"):
        blender.blend(
            {
                "catboost": (np.array([1.0, 2.0]), np.array([2.0, 3.0]), np.array([3.0, 4.0])),
                "lightgbm": (np.array([1.0]), np.array([2.0]), np.array([3.0])),
            }
        )


# ==============================================================================
# End-to-End Simulation Test (Forced Modeling on Synthetic Fixture)
# ==============================================================================


def test_ensembling_experiment_pipeline_when_modeling_forced() -> None:
    """Test that when modeling is forced, CatBoost and LightGBM train and blend."""
    from tests.fixtures.synthetic import generate_synthetic_observations_df

    n = 60
    base_df = generate_synthetic_observations_df(n_records=n, seed=42)
    dates = [datetime.date(2024, 1, 1) + datetime.timedelta(days=i) for i in range(n)]
    df = base_df.with_columns(
        [
            pl.Series("as_of_date", dates),
            pl.Series("person_cluster_id", [f"PER-{i:03d}" for i in range(n)]),
        ]
    )

    train_df = df.slice(0, 35)
    calib_df = df.slice(35, 12)
    eval_df = df.slice(47, 13)

    report = run_ensembling_experiment(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name="select",
        n_resamples=50,
        seed=42,
        force_modeling=True,
        allow_synthetic=True,
    )

    assert report.modeling_executed is True
    assert report.baseline_metrics is not None
    assert report.variant_a_metrics is not None
    assert len(report.deltas) == 1

    # Verify monotonic non-crossing quantiles (Rule R-UQ-05)
    assert report.baseline_metrics.crossing_rate == 0.0
    assert report.variant_a_metrics.crossing_rate == 0.0
    assert report.production_champion_retained is True
