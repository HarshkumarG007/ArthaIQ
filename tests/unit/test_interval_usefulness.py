"""Unit tests for Interval Usefulness Evaluator and Hypothesis EXP-02 (Rule R-UQ-04).

Adheres to Rules:
- Rule R-UQ-01: Bootstrap confidence intervals.
- Rule R-UQ-04: Useful intervals narrower than naive cohort at equal coverage.
- Rule R-MD-01 / R-MD-02: Dev split evaluation; test split strictly locked.
- Rule R-MD-08 / R-EV-07: Slices with N < 10 flagged, never hidden.
- Rule R-MD-11: Synthetic isolation guards.
- Rule R-TS-01 / R-TS-03: Strict test suite coverage >= 90%.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.evaluate_interval_usefulness import main as evaluate_usefulness_main

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.interval_usefulness import (
    IntervalUsefulnessEvaluator,
    IntervalUsefulnessReport,
    _width_ratio_statistic,
    _width_reduction_pct_statistic,
    evaluate_and_save_interval_usefulness,
)


@pytest.fixture
def eval_synthetic_df() -> pl.DataFrame:
    """Fixture providing 48 synthetic observations across multiple roles and seniorities."""
    roles = ["SOFTWARE", "DATA", "MLAI"] * 16
    seniorities = ["JUNIOR", "MID", "SENIOR", "LEAD"] * 12
    locations = ["BANGALORE", "HYDERABAD", "PUNE", "DELHI_NCR"] * 12
    yoe = [float(i % 15) + 1.0 for i in range(48)]
    pay = [
        10.0 + (float(i % 15) * 3.0) + (10.0 if r == "MLAI" else 0.0) for i, r in enumerate(roles)
    ]
    splits = ["train"] * 24 + ["calibrate"] * 12 + ["select"] * 12

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(48)],
            "split": splits,
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "guaranteed_cash_annual": pay,
            "is_synthetic": [False] * 48,
        }
    )


@pytest.mark.unit
def test_statistic_helpers() -> None:
    """Verify width ratio and reduction percentage statistic calculations."""
    m_w = np.array([20.0, 20.0, 20.0], dtype=np.float64)
    n_w = np.array([40.0, 40.0, 40.0], dtype=np.float64)

    assert _width_ratio_statistic(m_w, n_w) == pytest.approx(0.50, rel=1e-4)
    assert _width_reduction_pct_statistic(m_w, n_w) == pytest.approx(50.0, rel=1e-4)

    # Zero denominator fallback
    zero_n = np.zeros(3, dtype=np.float64)
    assert _width_ratio_statistic(m_w, zero_n) == 1.0
    assert _width_reduction_pct_statistic(m_w, zero_n) == 0.0


@pytest.mark.unit
def test_equal_coverage_quantiles() -> None:
    """Verify symmetric equal-coverage quantile calculation."""
    y = np.linspace(10.0, 90.0, 81)  # 10 to 90
    q_lo, q_hi = IntervalUsefulnessEvaluator.compute_equal_coverage_quantiles(
        y, target_coverage=0.80
    )

    # For 80% coverage, alpha = 0.20 -> 10th and 90th percentiles
    assert q_lo == pytest.approx(18.0, rel=1e-2)
    assert q_hi == pytest.approx(82.0, rel=1e-2)

    # Empty pool raises CompIntelValidationError
    with pytest.raises(
        CompIntelValidationError, match="Cannot compute equal-coverage quantiles on empty pool"
    ):
        IntervalUsefulnessEvaluator.compute_equal_coverage_quantiles(np.array([]), 0.80)


@pytest.mark.unit
def test_evaluate_model_usefulness_confirmed() -> None:
    """Verify evaluation where model is strictly narrower (CONFIRMED_USEFUL)."""
    evaluator = IntervalUsefulnessEvaluator(n_bootstrap_resamples=50, seed=42)

    y_eval = np.array([20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0])
    # Model intervals tightly bound y_eval (width = 10 LPA)
    p10_eval = y_eval - 5.0
    p90_eval = y_eval + 5.0
    # Naive cohort pool wide spread (width = 40 LPA)
    y_cohort_pool = np.linspace(5.0, 75.0, 50)
    roles = ["SOFTWARE"] * 8
    roles_pool = ["SOFTWARE"] * 50

    results = evaluator.evaluate_model_usefulness(
        y_eval=y_eval,
        p10_eval=p10_eval,
        p90_eval=p90_eval,
        y_cohort_pool=y_cohort_pool,
        roles_eval=roles,
        roles_cohort_pool=roles_pool,
        model_name="test_cqr",
        eval_split_name="select",
    )

    assert "global_unconditional" in results
    assert "role_family" in results

    global_m = results["global_unconditional"]
    assert global_m.is_useful is True
    assert global_m.verdict == "CONFIRMED_USEFUL"
    assert global_m.width_ratio_mean < 0.50
    assert global_m.width_reduction_pct > 50.0
    assert global_m.width_ratio_ci_upper < 1.0
    assert global_m.model_coverage == 1.0


@pytest.mark.unit
def test_evaluate_model_usefulness_invalidated() -> None:
    """Verify evaluation where model is wider than naive cohort (INVALIDATED)."""
    evaluator = IntervalUsefulnessEvaluator(n_bootstrap_resamples=50, seed=42)

    y_eval = np.array([20.0, 25.0, 30.0, 35.0, 40.0, 45.0])
    # Model interval very wide (width = 60 LPA)
    p10_eval = y_eval - 30.0
    p90_eval = y_eval + 30.0
    # Naive cohort pool narrow (width = 15 LPA)
    y_cohort_pool = np.linspace(20.0, 35.0, 40)

    results = evaluator.evaluate_model_usefulness(
        y_eval=y_eval,
        p10_eval=p10_eval,
        p90_eval=p90_eval,
        y_cohort_pool=y_cohort_pool,
        model_name="wide_model",
        eval_split_name="select",
    )

    m = results["global_unconditional"]
    assert m.is_useful is False
    assert m.verdict == "INVALIDATED"
    assert m.width_ratio_mean > 1.0
    assert m.width_reduction_pct < 0.0


@pytest.mark.unit
def test_locked_test_partition_rejection() -> None:
    """Verify Rule R-MD-02: evaluating on 'test' split raises DataContractError."""
    evaluator = IntervalUsefulnessEvaluator()
    y = np.array([20.0, 30.0])

    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        evaluator.evaluate_model_usefulness(
            y_eval=y,
            p10_eval=y - 5.0,
            p90_eval=y + 5.0,
            y_cohort_pool=y,
            eval_split_name="test",
        )

    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        evaluator.generate_report(
            canonical_df=pl.DataFrame({"a": [1]}),
            eval_split_name="test",
        )


@pytest.mark.unit
def test_all_abstained_rejected() -> None:
    """Verify model with 0 valid predictions raises CompIntelValidationError."""
    evaluator = IntervalUsefulnessEvaluator()
    y = np.array([20.0, 30.0])
    p10 = np.array([np.nan, np.nan])
    p90 = np.array([np.nan, np.nan])

    with pytest.raises(CompIntelValidationError, match="0 valid evaluated predictions"):
        evaluator.evaluate_model_usefulness(
            y_eval=y,
            p10_eval=p10,
            p90_eval=p90,
            y_cohort_pool=y,
            eval_split_name="select",
        )


@pytest.mark.unit
def test_evaluate_slices_low_support_flagged() -> None:
    """Verify slices with N < 10 are explicitly flagged (Rules R-MD-08, R-EV-07)."""
    evaluator = IntervalUsefulnessEvaluator(min_slice_support=10)

    df_eval = pl.DataFrame(
        {
            "guaranteed_cash_annual": [20.0, 25.0, 30.0, 35.0, 40.0],
            "role_family": ["SOFTWARE", "SOFTWARE", "SOFTWARE", "DATA", "DATA"],
            "seniority": ["MID", "MID", "SR", "MID", "SR"],
        }
    )
    p10 = np.array([15.0, 20.0, 25.0, 30.0, 35.0])
    p90 = np.array([25.0, 30.0, 35.0, 40.0, 45.0])
    naive_w = np.full(5, fill_value=20.0)

    slices = evaluator.evaluate_slices(df_eval, p10=p10, p90=p90, naive_widths=naive_w)

    assert len(slices) > 0
    for s in slices:
        # Every slice in this small DataFrame has N <= 3 < 10
        assert s.is_low_support is True
        assert s.n_eval < 10


@pytest.mark.unit
def test_generate_report_end_to_end(eval_synthetic_df: pl.DataFrame) -> None:
    """Verify end-to-end report generation with CatBoost CQR and naive cohorts."""
    evaluator = IntervalUsefulnessEvaluator(n_bootstrap_resamples=20, seed=42)

    report = evaluator.generate_report(
        canonical_df=eval_synthetic_df,
        eval_split_name="select",
    )

    assert isinstance(report, IntervalUsefulnessReport)
    assert report.evaluation_split == "select"
    assert "catboost_cqr" in report.evaluations
    assert "split_conformal" in report.evaluations
    assert "catboost_quantile_uncalibrated" in report.evaluations

    # Verify serialization
    r_dict = report.to_dict()
    assert "exp02_verdict" in r_dict
    assert "evaluations" in r_dict
    assert "slice_evaluations" in r_dict

    # Verify Markdown rendering
    md = report.to_markdown()
    assert "# Interval Usefulness & Hypothesis EXP-02 Report" in md
    assert "EXP-02 VERDICT:" in md
    assert "Statutory Mandate (Rule R-UQ-04)" in md
    assert "FLAGGED (N < 10)" in md


@pytest.mark.unit
def test_cli_runner_and_file_generation(tmp_path: Path, eval_synthetic_df: pl.DataFrame) -> None:
    """Verify CLI execution and report artifact file creation."""
    parquet_path = tmp_path / "canonical.parquet"
    eval_synthetic_df.write_parquet(parquet_path)

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    # 1. Direct evaluate_and_save call
    rep = evaluate_and_save_interval_usefulness(
        canonical_path=parquet_path,
        output_md=out_md,
        output_json=out_json,
        split="select",
        n_bootstrap=20,
        allow_synthetic=True,
    )
    assert rep is not None
    assert out_md.exists()
    assert out_json.exists()

    with open(out_json, encoding="utf-8") as f:
        data = json.load(f)
    assert "exp02_verdict" in data

    # 2. CLI execution via main()
    cli_md = tmp_path / "cli_report.md"
    cli_json = tmp_path / "cli_report.json"
    test_args = [
        "evaluate_interval_usefulness.py",
        "--canonical-path",
        str(parquet_path),
        "--output-md",
        str(cli_md),
        "--output-json",
        str(cli_json),
        "--split",
        "select",
        "--n-bootstrap",
        "20",
        "--allow-synthetic",
    ]

    with patch.object(sys, "argv", test_args):
        ret = evaluate_usefulness_main()
        assert ret == 0

    assert cli_md.exists()
    assert cli_json.exists()
