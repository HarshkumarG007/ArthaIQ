"""Unit tests for EXP-ENSEMBLE-01r: Quantile Ensembling Re-audit (Phase 13, Task T13.02).

Tests:
1. Non-synthetic observation panel verification under Rule R-MD-11.
2. Gate 1 feasibility audit: sample sufficiency threshold (N >= 100) vs insufficient sample size.
3. QuantileEnsembleBlender convex combination weights validation and statutory floor.
4. Monotone rearrangement operator (Chernozhukov et al., 2010) zero crossings (Rule R-UQ-05).
5. Paired bootstrap confidence intervals for pinball loss delta (Rule R-UQ-01).
6. End-to-end empirical re-audit verdict evaluation and Champion preservation.
7. Synthetic data quarantine guard under Rule R-MD-11 (SYNTHETIC_DATA_BLOCKED).
8. Report serialization to structured dictionary and publication-grade Markdown rendering.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from compintel.errors import CompIntelValidationError
from compintel.evaluation.employer_graph_reaudit import build_post_exp16_cumulative_panel
from compintel.evaluation.ensemble_reaudit import (
    ReauditOutcomeVerdict,
    evaluate_and_save_ensemble_reaudit,
    run_ensemble_reaudit,
)
from compintel.evaluation.ensembling_experiment import (
    EnsembleFeasibilityStatus,
    QuantileEnsembleBlender,
    _compute_paired_bootstrap_difference,
    audit_ensemble_feasibility,
)


@pytest.fixture
def cumulative_panel() -> pl.DataFrame:
    """Build standard 6-month non-synthetic cumulative production panel."""
    return build_post_exp16_cumulative_panel(months_operational=6.0, seed=42)


def test_non_synthetic_verification(cumulative_panel: pl.DataFrame) -> None:
    """Rule R-MD-11: 100% of observations must be verified non-synthetic."""
    assert len(cumulative_panel) >= 100
    assert "is_synthetic" in cumulative_panel.columns
    # Zero synthetic rows allowed
    assert not cumulative_panel["is_synthetic"].any()
    assert (cumulative_panel["is_synthetic"] == False).all()  # noqa: E712


def test_gate1_feasibility_audit_passed(cumulative_panel: pl.DataFrame) -> None:
    """Gate 1: Audit passes when non-synthetic panel size N >= 100."""
    audit = audit_ensemble_feasibility(cumulative_panel, min_required_records=100)
    assert audit.status == EnsembleFeasibilityStatus.FEASIBLE
    assert audit.n_total_records == len(cumulative_panel)
    assert audit.n_total_records >= 100
    assert not audit.is_synthetic
    assert "Gate 1 feasibility passed" in audit.summary


def test_gate1_feasibility_insufficient_sample(cumulative_panel: pl.DataFrame) -> None:
    """Gate 1: When panel N < 100, status is INSUFFICIENT_SAMPLE_SIZE triggering DEFER."""
    small_df = cumulative_panel.slice(0, 50)
    audit = audit_ensemble_feasibility(small_df, min_required_records=100)
    assert audit.status == EnsembleFeasibilityStatus.INSUFFICIENT_SAMPLE_SIZE
    assert audit.n_total_records == 50
    assert "failing the required sufficiency threshold" in audit.summary

    # End-to-end run on small panel yields DEFER without modeling
    report = run_ensemble_reaudit(
        custom_df=small_df,
        min_required_records=100,
        n_resamples=100,
        seed=42,
    )
    assert not report.gate1_passed
    assert not report.modeling_executed
    assert report.verdict == ReauditOutcomeVerdict.DEFER
    assert report.champion_status == "RETAINED_UNMODIFIED"
    assert report.baseline_metrics is None
    assert report.ensemble_metrics is None


def test_synthetic_data_quarantine_guard(cumulative_panel: pl.DataFrame) -> None:
    """Rule R-MD-11: Synthetic data must be quarantined and blocked from Gate 1 feasibility."""
    synth_df = cumulative_panel.with_columns(pl.lit(True).alias("is_synthetic"))
    audit = audit_ensemble_feasibility(synth_df, min_required_records=100, allow_synthetic=False)
    assert audit.status == EnsembleFeasibilityStatus.SYNTHETIC_DATA_BLOCKED
    assert audit.is_synthetic
    assert "blocked under Rule R-MD-11" in audit.summary


def test_quantile_ensemble_blender_weights() -> None:
    """Test convex combination weights validation and normalization."""
    # Default weights equal split
    blender = QuantileEnsembleBlender()
    assert blender.weights == {"catboost": 0.50, "lightgbm": 0.50}

    # Custom weights normalized to 1.0
    blender_custom = QuantileEnsembleBlender(weights={"catboost": 3.0, "lightgbm": 1.0})
    assert blender_custom.weights["catboost"] == pytest.approx(0.75)
    assert blender_custom.weights["lightgbm"] == pytest.approx(0.25)

    # Empty weights rejected
    with pytest.raises(CompIntelValidationError) as exc_info:
        QuantileEnsembleBlender(weights={})
    assert exc_info.value.code == "EMPTY_ENSEMBLE_WEIGHTS"

    # Negative weights rejected
    with pytest.raises(CompIntelValidationError) as exc_neg:
        QuantileEnsembleBlender(weights={"catboost": -0.5, "lightgbm": 1.5})
    assert exc_neg.value.code == "INVALID_ENSEMBLE_WEIGHT"


def test_quantile_ensemble_blender_monotone_guarantee() -> None:
    """Rule R-UQ-05: Blender applies Chernozhukov sorting to guarantee P10 <= P50 <= P90."""
    blender = QuantileEnsembleBlender(weights={"catboost": 0.50, "lightgbm": 0.50})

    # Intentionally inverted quantiles (severe crossing violations)
    cb_inverted = (
        np.array([45.0, 30.0, 60.0]),  # P10 > P50
        np.array([25.0, 40.0, 50.0]),
        np.array([10.0, 50.0, 70.0]),  # P90 < P10
    )
    lgb_inverted = (
        np.array([40.0, 35.0, 65.0]),
        np.array([20.0, 38.0, 55.0]),
        np.array([15.0, 48.0, 75.0]),
    )

    p10_clean, p50_clean, p90_clean, pre_crossing_rate = blender.blend(
        {"catboost": cb_inverted, "lightgbm": lgb_inverted}
    )

    # Prior to repair, crossings existed
    assert pre_crossing_rate > 0.0

    # Post-repair: strict monotonicity across every single row
    assert np.all(p10_clean <= p50_clean)
    assert np.all(p50_clean <= p90_clean)
    assert np.all(p10_clean >= 0.50)  # Statutory non-negativity floor


def test_paired_bootstrap_difference_ci() -> None:
    """Rule R-UQ-01: Bootstrap paired difference produces calibrated 95% confidence intervals."""
    rng = np.random.default_rng(42)
    n = 100
    y_true = rng.uniform(10.0, 50.0, size=n)

    base_p10 = y_true - 5.0
    base_p50 = y_true
    base_p90 = y_true + 5.0

    # Candidate with row-level variation in errors
    noise = rng.normal(1.0, 1.5, size=n)
    cand_p10 = y_true - 7.0 + noise
    cand_p50 = y_true + 1.0 + noise
    cand_p90 = y_true + 7.0 + noise

    diff = _compute_paired_bootstrap_difference(
        y_true=y_true,
        base_p10=base_p10,
        base_p50=base_p50,
        base_p90=base_p90,
        cand_p10=cand_p10,
        cand_p50=cand_p50,
        cand_p90=cand_p90,
        variant_name="Variant A",
        n_resamples=500,
        seed=42,
    )

    assert diff.ci_lower <= diff.delta_mean_pinball <= diff.ci_upper
    assert diff.ci_lower < diff.ci_upper
    assert diff.width_ratio > 1.0  # Candidate is wider


def test_empirical_reaudit_verdict_reject(cumulative_panel: pl.DataFrame) -> None:
    """Task T13.02: Realized empirical re-audit on 219 non-synthetic panel yields REJECT."""
    report = run_ensemble_reaudit(
        custom_df=cumulative_panel,
        min_required_records=100,
        eval_split_name="select",
        n_resamples=500,
        seed=42,
    )

    assert report.gate1_passed
    assert report.modeling_executed
    assert report.verdict == ReauditOutcomeVerdict.REJECT
    assert report.champion_status == "RETAINED_UNMODIFIED"

    assert report.baseline_metrics is not None
    assert report.ensemble_metrics is not None
    assert report.paired_difference is not None

    # Verify ensembling fails primary keep criterion (delta pinball <= -0.050 LPA)
    assert report.paired_difference.delta_mean_pinball > -0.050
    # CI upper bound is positive, showing ensembling degrades loss
    assert report.paired_difference.ci_upper > 0.0

    # Rule R-UQ-05: 0 crossings in both baseline and ensemble
    assert report.baseline_metrics.crossing_rate == 0.0
    assert report.ensemble_metrics.crossing_rate == 0.0


def test_report_artifacts_serialization(tmp_path: Path, cumulative_panel: pl.DataFrame) -> None:
    """Test JSON report and Markdown memo generation and schema validation."""
    json_path = tmp_path / "ensemble_reaudit.json"
    memo_path = tmp_path / "ensemble-reaudit-phase13.md"

    report = evaluate_and_save_ensemble_reaudit(
        output_json_path=json_path,
        output_memo_path=memo_path,
        min_required_records=100,
        n_resamples=200,
        seed=42,
        custom_df=cumulative_panel,
    )

    assert report.verdict == ReauditOutcomeVerdict.REJECT
    assert json_path.exists()
    assert memo_path.exists()

    # Validate JSON structure
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["report_id"].startswith("EXP-ENSEMBLE-R-")
    assert data["charter_id"] == "CHARTER-ENSEMBLING-STACKING"
    assert data["task_id"] == "T13.02"
    assert data["verdict"] == "REJECT"
    assert data["gate1_passed"] is True
    assert data["modeling_executed"] is True
    assert "baseline_metrics" in data
    assert "ensemble_metrics" in data
    assert "paired_difference" in data

    # Validate Markdown publication-grade memo
    md_text = memo_path.read_text(encoding="utf-8")
    assert "# Quantile Ensembling Feasibility Re-audit" in md_text
    assert "CHARTER-ENSEMBLING-STACKING" in md_text
    assert "REJECT" in md_text
    assert "Champion Baseline (Rung F CatBoost)" in md_text
    assert "Variant A (Convex Blend)" in md_text
    assert "Chernozhukov et al. (2010)" in md_text
    # Zero lone numbers: intervals presented with context
    assert "LPA" in md_text
    assert "95% CI" in md_text
