"""Unit tests for Current Pay Anchoring & Selection Analysis Engine and CLI (EXP-07, T6.05).

Adheres to:
- PRD Section 5 & FR-05: Separation of PT1 (Market) and PT6 (Current Pay Benchmark).
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine until justified by EXP-07.
- Rule R-MD-15: Missingness invariant.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_anchoring_analysis import main as run_anchoring_analysis_main
from scripts.run_anchoring_analysis import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.anchoring_analysis import (
    AnchoringDecisionVerdict,
    CurrentPayAnchoringReport,
    _estimate_anchoring_decomposition,
    evaluate_and_save_anchoring_analysis,
    run_current_pay_anchoring_analysis,
)


@pytest.fixture
def anchoring_synthetic_df() -> pl.DataFrame:
    """Fixture providing 60 synthetic observations with current pay for anchoring analysis."""
    n_rows = 60
    rng = np.random.default_rng(42)

    roles = ["SOFTWARE", "DATA", "MLAI"] * (n_rows // 3)
    seniorities = ["JUNIOR", "MID", "SENIOR", "LEAD"] * (n_rows // 4)
    locations = ["BANGALORE", "HYDERABAD", "PUNE", "DELHI_NCR", "MUMBAI"] * (n_rows // 5)
    yoe = [float(i % 15) + 1.0 for i in range(n_rows)]

    # Canonical market pay
    salaries = [
        12.0
        + (y * 1.8)
        + (8.0 if s in ("SENIOR", "LEAD") else 0.0)
        + (float(rng.uniform(-1.0, 1.0)))
        for y, s in zip(yoe, seniorities, strict=False)
    ]

    # Current pay: highly correlated with salary (modal 15% hike)
    current_pay = [s * 0.85 for s in salaries]

    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 5) for i in range(n_rows)]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n_rows)],
            "person_cluster_id": [f"PER-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "guaranteed_cash_annual": salaries,
            "current_guaranteed_cash": current_pay,
            "feat_l3_current_guaranteed_cash": current_pay,
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "is_synthetic": [True] * n_rows,
        }
    )


def test_estimate_anchoring_decomposition() -> None:
    """Test anchoring decomposition estimation produces valid normalized weights."""
    n = 50
    rng = np.random.default_rng(42)
    y_eval = np.linspace(15.0, 50.0, n)
    current_pay = y_eval * 0.85 + rng.normal(0, 0.5, n)
    p50_profile = y_eval + rng.normal(0, 2.0, n)
    p50_anchored = 0.7 * current_pay + 0.3 * p50_profile

    alpha, beta, ci_l, ci_u = _estimate_anchoring_decomposition(
        y_eval=y_eval,
        p50_profile=p50_profile,
        p50_anchored=p50_anchored,
        current_pay=current_pay,
        n_resamples=50,
        seed=42,
    )

    assert 0.0 <= alpha <= 1.0
    assert 0.0 <= beta <= 1.0
    assert ci_l <= ci_u


def test_run_anchoring_test_split_lock_violation(anchoring_synthetic_df: pl.DataFrame) -> None:
    """Test running anchoring analysis on 'test' split raises DataContractError (R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        run_current_pay_anchoring_analysis(
            train_df=anchoring_synthetic_df,
            eval_df=anchoring_synthetic_df,
            calibrate_df=anchoring_synthetic_df,
            eval_split_name="test",
        )


def test_run_anchoring_analysis_success(anchoring_synthetic_df: pl.DataFrame) -> None:
    """Test successful end-to-end execution of current pay anchoring analysis."""
    train_df = anchoring_synthetic_df[:40]
    eval_df = anchoring_synthetic_df[40:]
    calib_df = anchoring_synthetic_df[20:40]

    report = run_current_pay_anchoring_analysis(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name="select",
        n_resamples=50,
        seed=42,
    )

    assert isinstance(report, CurrentPayAnchoringReport)
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == len(eval_df)
    assert report.verdict in (
        AnchoringDecisionVerdict.COMPARE_ONLY,
        AnchoringDecisionVerdict.INPUT_FEATURE,
    )

    # Performance metrics
    assert report.unanchored_metrics.mae > 0.0
    assert report.anchored_metrics.mae > 0.0
    assert report.unanchored_metrics.crossing_rate == 0.0
    assert report.anchored_metrics.crossing_rate == 0.0

    # Anchoring regression metrics
    assert 0.0 <= report.anchoring_regression.anchoring_weight_alpha <= 1.0
    assert 0.0 <= report.anchoring_regression.profile_weight_beta <= 1.0

    # Disparity metrics
    assert report.cohort_disparity.underpaid_cohort_size > 0
    assert report.cohort_disparity.baseline_cohort_size > 0

    # Governance directive
    assert "COMPARE_ONLY" in report.governance_directive or "input" in report.governance_directive

    # Serialization
    d = report.to_dict()
    assert d["report_id"].startswith("EXP07-ANCHORING-")
    md = report.to_markdown()
    assert "# Current Pay Anchoring & Selection Analysis Report (EXP-07)" in md
    assert "The Anchoring Pathology Decomposition" in md
    assert "Underpayment Compounding & Disparity Audit" in md


def test_evaluate_and_save_anchoring_analysis_missing_file(tmp_path: Path) -> None:
    """Test evaluate_and_save_anchoring_analysis with missing file raises error."""
    missing = tmp_path / "missing.parquet"
    with pytest.raises(CompIntelValidationError, match="Canonical dataset not found"):
        evaluate_and_save_anchoring_analysis(canonical_path=missing)


def test_evaluate_and_save_anchoring_analysis_synthetic_blocked(
    tmp_path: Path, anchoring_synthetic_df: pl.DataFrame
) -> None:
    """Test that synthetic data is blocked without allow_synthetic override (Rule R-MD-11)."""
    p = tmp_path / "canonical_with_synth.parquet"
    anchoring_synthetic_df.write_parquet(p)

    with pytest.raises(DataContractError, match="Synthetic data detected"):
        evaluate_and_save_anchoring_analysis(canonical_path=p, allow_synthetic=False)


def test_evaluate_and_save_anchoring_analysis_test_split_blocked() -> None:
    """Test that evaluate_and_save_anchoring_analysis rejects test split (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        evaluate_and_save_anchoring_analysis(eval_split_name="test")


def test_evaluate_and_save_anchoring_analysis_success(
    tmp_path: Path, anchoring_synthetic_df: pl.DataFrame
) -> None:
    """Test evaluate_and_save_anchoring_analysis saves Markdown and JSON report files."""
    canonical_file = tmp_path / "canonical.parquet"
    anchoring_synthetic_df.write_parquet(canonical_file)

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    report = evaluate_and_save_anchoring_analysis(
        canonical_path=canonical_file,
        output_md=out_md,
        output_json=out_json,
        eval_split_name="select",
        n_resamples=50,
        seed=42,
        allow_synthetic=True,
    )

    assert out_md.exists()
    assert out_json.exists()
    assert report.report_id.startswith("EXP07-ANCHORING-")


def test_cli_parse_args_defaults() -> None:
    """Test CLI argument parsing default values."""
    with patch.object(sys, "argv", ["run_anchoring_analysis.py"]):
        args = parse_args()
        assert args.canonical_path == "data/canonical/canonical_observations.parquet"
        assert args.output_md == "docs/research/current-pay-anchoring-exp07.md"
        assert args.output_json == "experiments/results/current_pay_anchoring_v1.json"
        assert args.split == "select"
        assert args.n_resamples == 1000
        assert args.seed == 42
        assert args.allow_synthetic is False


def test_cli_runner_success(tmp_path: Path, anchoring_synthetic_df: pl.DataFrame) -> None:
    """Test successful CLI execution end-to-end."""
    synth_file = tmp_path / "canonical.parquet"
    anchoring_synthetic_df.write_parquet(synth_file)

    out_md = tmp_path / "cli_report.md"
    out_json = tmp_path / "cli_report.json"

    test_args = [
        "run_anchoring_analysis.py",
        "--canonical-path",
        str(synth_file),
        "--output-md",
        str(out_md),
        "--output-json",
        str(out_json),
        "--split",
        "select",
        "--n-resamples",
        "50",
        "--seed",
        "42",
        "--allow-synthetic",
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_anchoring_analysis_main()

    assert ret_code == 0
    assert out_md.exists()
    assert out_json.exists()


def test_cli_runner_missing_canonical_file(tmp_path: Path) -> None:
    """Test CLI exit code 1 on missing canonical file."""
    missing_file = tmp_path / "does_not_exist.parquet"
    test_args = [
        "run_anchoring_analysis.py",
        "--canonical-path",
        str(missing_file),
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_anchoring_analysis_main()

    assert ret_code == 1


def test_cli_runner_fatal_exception() -> None:
    """Test CLI exit code 2 on unexpected fatal crash."""
    test_args = ["run_anchoring_analysis.py"]

    with (
        patch.object(sys, "argv", test_args),
        patch(
            "scripts.run_anchoring_analysis.evaluate_and_save_anchoring_analysis",
            side_effect=RuntimeError("Fatal model divergence crash"),
        ),
    ):
        ret_code = run_anchoring_analysis_main()

    assert ret_code == 2
