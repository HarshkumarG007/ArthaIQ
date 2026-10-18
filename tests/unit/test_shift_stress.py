"""Unit tests for Shift Stress Tests and Hypothesis EXP-03 (Rule R-UQ-04).

Adheres to Rules:
- Rule R-UQ-01: Bootstrap confidence intervals for shift degradation metrics.
- Rule R-UQ-03: Conformal exchangeability tested under temporal shift.
- Hypothesis EXP-03: Temporal coverage degradation and rolling recalibration efficacy.
- Rule R-MD-01 / R-MD-02: Dev split evaluation; test split strictly locked.
- Rule R-MD-08 / R-EV-07: Slices with N < 10 flagged, never hidden.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-TS-01 / R-TS-03: Quality standards and strict test coverage >= 90%.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_shift_stress_tests import main as run_shift_stress_main

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.shift_stress import (
    GeographicShiftSummary,
    RareCellShiftSummary,
    ShiftStressEvaluator,
    ShiftStressReport,
    _coverage_diff_statistic,
    _coverage_statistic,
    evaluate_and_save_shift_stress,
)


@pytest.fixture
def shift_eval_synthetic_df() -> pl.DataFrame:
    """Fixture providing 48 synthetic observations across diverse locations and roles."""
    roles = ["SOFTWARE", "DATA", "MLAI"] * 16
    seniorities = ["JUNIOR", "MID", "SENIOR", "LEAD"] * 12
    locations = ["BANGALORE", "HYDERABAD", "PUNE", "DELHI_NCR", "KOLKATA", "REMOTE"] * 8
    yoe = [float(i % 16) + 1.0 for i in range(48)]
    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 7) for i in range(48)]

    # Realistic salary values
    salaries = [
        15.0 + (y * 2.0) + (10.0 if "LEAD" in s else 0.0)
        for y, s in zip(yoe, seniorities, strict=False)
    ]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(48)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "guaranteed_cash_annual": salaries,
            "person_cluster_id": [f"PCLUST-{i:03d}" for i in range(48)],
            "employer_cluster_id": [f"ECLUST-{i % 6:02d}" for i in range(48)],
            "is_synthetic": [True] * 48,
        }
    )


def test_coverage_statistics_helpers() -> None:
    """Test coverage and difference statistics helper functions."""
    y_true = np.array([20.0, 30.0, 40.0])
    cov_binary = np.array([1.0, 0.0, 1.0])
    cov = _coverage_statistic(y_true, cov_binary)
    assert abs(cov - (2.0 / 3.0)) < 1e-6

    # Empty array
    assert _coverage_statistic(np.array([]), np.array([])) == 0.0

    # Coverage diff
    recent_cov = np.array([1.0, 1.0, 1.0])
    hist_cov = np.array([0.0, 1.0, 0.0])
    diff = _coverage_diff_statistic(recent_cov, hist_cov)
    assert abs(diff - (1.0 - 1.0 / 3.0)) < 1e-6


def test_temporal_shift_verdict_recalibration_restores() -> None:
    """Test EXP-03 verdict when rolling recalibration restores degraded coverage."""
    evaluator = ShiftStressEvaluator(n_bootstrap_resamples=50, seed=42)

    # 20 items: 15 historical, 5 recent
    # Historical: 12 covered (25 to 35), 3 uncovered (35 to 40)
    # Recent: 5 uncovered under static (35 to 40), 5 covered under recal (25 to 35)
    y_eval = np.full(20, 30.0)
    p10_static = np.array([25.0] * 12 + [35.0] * 3 + [35.0] * 5)
    p90_static = np.array([35.0] * 12 + [40.0] * 3 + [40.0] * 5)

    p10_recal = np.array([25.0] * 20)
    p90_recal = np.array([35.0] * 20)

    dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i) for i in range(20)]

    metrics = evaluator.evaluate_temporal_shift(
        y_eval=y_eval,
        p10_static=p10_static,
        p90_static=p90_static,
        p10_recal=p10_recal,
        p90_recal=p90_recal,
        timestamps_eval=dates,
    )

    assert metrics.exp03_verdict == "RECALIBRATION_RESTORES_COVERAGE"
    assert "Monthly" in metrics.recommended_recalibration_cadence
    assert metrics.recalibration_coverage_gain > 0.0


def test_temporal_shift_verdict_drift_negligible() -> None:
    """Test EXP-03 verdict when coverage remains stable across windows."""
    evaluator = ShiftStressEvaluator(n_bootstrap_resamples=50, seed=42)

    # All items covered
    y_eval = np.full(20, 30.0)
    p10_static = np.full(20, 25.0)
    p90_static = np.full(20, 35.0)
    p10_recal = np.full(20, 25.0)
    p90_recal = np.full(20, 35.0)

    dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i) for i in range(20)]

    metrics = evaluator.evaluate_temporal_shift(
        y_eval=y_eval,
        p10_static=p10_static,
        p90_static=p90_static,
        p10_recal=p10_recal,
        p90_recal=p90_recal,
        timestamps_eval=dates,
    )

    assert metrics.exp03_verdict == "DRIFT_NEGLIGIBLE"
    assert "Quarterly" in metrics.recommended_recalibration_cadence
    assert abs(metrics.coverage_drift_static) <= 0.05


def test_temporal_shift_verdict_unstable_under_shift() -> None:
    """Test EXP-03 verdict when both static and recalibrated fail target coverage."""
    evaluator = ShiftStressEvaluator(n_bootstrap_resamples=50, seed=42)

    # Target 30, bounds completely miss [40, 50]
    y_eval = np.full(20, 30.0)
    p10_static = np.full(20, 40.0)
    p90_static = np.full(20, 50.0)
    p10_recal = np.full(20, 40.0)
    p90_recal = np.full(20, 50.0)

    dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i) for i in range(20)]

    metrics = evaluator.evaluate_temporal_shift(
        y_eval=y_eval,
        p10_static=p10_static,
        p90_static=p90_static,
        p10_recal=p10_recal,
        p90_recal=p90_recal,
        timestamps_eval=dates,
    )

    assert metrics.exp03_verdict == "UNSTABLE_UNDER_SHIFT"
    assert "URGENT" in metrics.recommended_recalibration_cadence


def test_temporal_shift_empty_raises() -> None:
    """Test validation error when empty evaluation array is passed."""
    evaluator = ShiftStressEvaluator()
    with pytest.raises(CompIntelValidationError, match="empty evaluation array"):
        evaluator.evaluate_temporal_shift(
            y_eval=np.array([]),
            p10_static=np.array([]),
            p90_static=np.array([]),
            p10_recal=np.array([]),
            p90_recal=np.array([]),
        )


def test_geographic_shift_evaluation_and_flagging(shift_eval_synthetic_df: pl.DataFrame) -> None:
    """Test geographic shift slice aggregation and low-support flagging (Rules R-MD-08, R-EV-07)."""
    evaluator = ShiftStressEvaluator(min_slice_support=10)
    y = shift_eval_synthetic_df["guaranteed_cash_annual"].to_numpy()
    p10 = y - 5.0
    p90 = y + 5.0
    p50 = y

    summary = evaluator.evaluate_geographic_shift(
        df_eval=shift_eval_synthetic_df,
        p10=p10,
        p90=p90,
        p50=p50,
    )

    assert isinstance(summary, GeographicShiftSummary)
    assert summary.primary_hubs_coverage == 1.0
    assert summary.regional_hubs_coverage == 1.0
    assert summary.primary_obs_count > 0
    assert summary.regional_obs_count > 0

    # In 48 rows across 6 locations, each has 8 observations (< 10)
    # Every slice should be explicitly flagged (**FLAGGED (N < 10)**)
    for s in summary.slices:
        assert s.is_low_support is True
        assert s.flag_label == "**FLAGGED (N < 10)**"

    # Missing location column validation
    with pytest.raises(CompIntelValidationError, match="Missing 'location' column"):
        evaluator.evaluate_geographic_shift(
            df_eval=shift_eval_synthetic_df.drop("location"),
            p10=p10,
            p90=p90,
            p50=p50,
        )


def test_rare_cells_shift_evaluation(shift_eval_synthetic_df: pl.DataFrame) -> None:
    """Test rare cells evaluation on role_seniority and experience tail."""
    evaluator = ShiftStressEvaluator(min_slice_support=10)
    y = shift_eval_synthetic_df["guaranteed_cash_annual"].to_numpy()
    p10 = y - 5.0
    p90 = y + 5.0
    p50 = y

    summary = evaluator.evaluate_rare_cells_shift(
        df_eval=shift_eval_synthetic_df,
        p10=p10,
        p90=p90,
        p50=p50,
    )

    assert isinstance(summary, RareCellShiftSummary)
    assert summary.total_cell_count > 0
    assert summary.flagged_cell_count > 0
    assert any(s.cell_dimension == "experience_tail" for s in summary.slices)


def test_locked_test_partition_isolation(tmp_path: Path) -> None:
    """Test Rule R-MD-02: evaluating on 'test' partition is strictly rejected."""
    fake_parquet = tmp_path / "test_data.parquet"
    pl.DataFrame({"x": [1]}).write_parquet(fake_parquet)

    with pytest.raises(
        DataContractError, match="Evaluation on 'test' partition is strictly forbidden"
    ) as exc:
        evaluate_and_save_shift_stress(
            canonical_path=str(fake_parquet),
            eval_split_name="test",
        )
    assert exc.value.code == "FINAL_TEST_PARTITION_LOCKED"
    assert exc.value.details.get("rule_id") == "R-MD-02"


def test_synthetic_data_blocking(tmp_path: Path) -> None:
    """Test Rule R-MD-11: synthetic data blocked without explicit override."""
    synth_parquet = tmp_path / "synth_data.parquet"
    pl.DataFrame({"is_synthetic": [True, True]}).write_parquet(synth_parquet)

    with pytest.raises(
        DataContractError, match="Synthetic data detected in canonical evaluation pool"
    ) as exc:
        evaluate_and_save_shift_stress(
            canonical_path=str(synth_parquet),
            allow_synthetic=False,
        )
    assert exc.value.code == "SYNTHETIC_DATA_BLOCKED"


def test_end_to_end_shift_stress_report(
    tmp_path: Path, shift_eval_synthetic_df: pl.DataFrame
) -> None:
    """Test complete end-to-end shift stress evaluation on synthetic data."""
    synth_file = tmp_path / "synthetic_canonical.parquet"
    shift_eval_synthetic_df.write_parquet(synth_file)

    out_md = tmp_path / "shift_stress.md"
    out_json = tmp_path / "shift_stress.json"

    report = evaluate_and_save_shift_stress(
        canonical_path=str(synth_file),
        output_md=str(out_md),
        output_json=str(out_json),
        eval_split_name="select",
        n_bootstrap=100,
        seed=42,
        allow_synthetic=True,
    )

    assert isinstance(report, ShiftStressReport)
    assert report.overall_degradation_quantified is True
    assert report.temporal_shift.exp03_verdict in [
        "RECALIBRATION_RESTORES_COVERAGE",
        "DRIFT_NEGLIGIBLE",
        "UNSTABLE_UNDER_SHIFT",
    ]
    assert out_md.exists()
    assert out_json.exists()

    md_content = out_md.read_text(encoding="utf-8")
    assert "# ArthaIQ -- Shift Stress Testing & Hypothesis EXP-03 Report" in md_content
    assert "## 2. Temporal Shift & Rolling Recalibration (Hypothesis EXP-03)" in md_content
    assert "## 3. Geographic Shift Stress Test" in md_content
    assert "## 4. Rare Cells & Thin-Support Slices Stress Test" in md_content
    assert "**FLAGGED (N < 10)**" in md_content

    json_dict = json.loads(out_json.read_text(encoding="utf-8"))
    assert json_dict["overall_degradation_quantified"] is True
    assert "temporal_shift" in json_dict
    assert "geographic_shift" in json_dict
    assert "rare_cell_shift" in json_dict


def test_cli_runner_execution(tmp_path: Path, shift_eval_synthetic_df: pl.DataFrame) -> None:
    """Test CLI script execution for shift stress testing."""
    synth_file = tmp_path / "cli_synth.parquet"
    shift_eval_synthetic_df.write_parquet(synth_file)

    out_md = tmp_path / "cli_report.md"
    out_json = tmp_path / "cli_report.json"

    test_args = [
        "run_shift_stress_tests.py",
        "--canonical-path",
        str(synth_file),
        "--output-md",
        str(out_md),
        "--output-json",
        str(out_json),
        "--split",
        "select",
        "--n-bootstrap",
        "50",
        "--seed",
        "42",
        "--allow-synthetic",
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_shift_stress_main()

    assert ret_code == 0
    assert out_md.exists()
    assert out_json.exists()
