"""Unit tests for Staged versus Joint Modelling Analysis Engine and CLI (T6.08, EXP-08).

Adheres to:
- PRD Section 5 & FR-05: Progressive disclosure ladder (L0 -> L1 -> L2 -> L3).
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with bootstrap confidence intervals.
- Rule R-MD-06: Log pay target transformation (log guaranteed_cash_annual).
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
- Decision D-010 & Hypothesis EXP-08: Staged versus joint architecture evaluation.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_staging_analysis import main as run_staging_analysis_main
from scripts.run_staging_analysis import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.staging_analysis import (
    StagingAnalysisReport,
    StagingModelType,
    StagingVerdict,
    evaluate_and_save_staging_analysis,
    run_staging_analysis,
)


@pytest.fixture
def staging_synthetic_df() -> pl.DataFrame:
    """Fixture providing 80 synthetic observations with progressive L0 and L1 features."""
    n_rows = 80
    rng = np.random.default_rng(42)

    roles = ["SOFTWARE"] * 30 + ["DATA"] * 30 + ["MLAI"] * 20
    seniorities = ["MID"] * 40 + ["SENIOR"] * 40
    locations = ["BANGALORE"] * 40 + ["HYDERABAD"] * 40

    yoe = [float(i % 12) + 1.0 for i in range(n_rows)]
    skills = ["PYTHON,FASTAPI" if i % 2 == 0 else "GO,KUBERNETES" for i in range(n_rows)]
    depths = ["SPECIALIZED" if i % 2 == 0 else "GENERALIST" for i in range(n_rows)]
    domains = ["FINTECH" if i % 3 == 0 else "ECOMMERCE" for i in range(n_rows)]

    salaries = [
        14.0
        + (y * 1.8)
        + (10.0 if s == "SENIOR" else 0.0)
        + (3.0 if "SPECIALIZED" in d else 0.0)
        + float(rng.uniform(-1.0, 1.0))
        for y, s, d in zip(yoe, seniorities, depths, strict=False)
    ]

    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 4) for i in range(n_rows)]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n_rows)],
            "person_cluster_id": [f"PER-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "guaranteed_cash_annual": salaries,
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "skills_primary": skills,
            "skills_depth": depths,
            "domain_specialization": domains,
            "employer_tier": [
                "TIER_1_PRODUCT" if i % 2 == 0 else "TIER_2_GROWTH" for i in range(n_rows)
            ],
            "is_synthetic": [True] * n_rows,
        }
    )


def test_staging_enums() -> None:
    """Test StagingModelType and StagingVerdict enum string values."""
    assert StagingModelType.JOINT_DIRECT == "JOINT_DIRECT"
    assert StagingModelType.STAGED_CASCADED == "STAGED_CASCADED"

    assert StagingVerdict.JOINT_NESTED_ROUTING == "JOINT_NESTED_ROUTING"
    assert StagingVerdict.CASCADED_RESIDUAL_STAGING == "CASCADED_RESIDUAL_STAGING"


def test_run_staging_analysis_test_split_lock_violation(
    staging_synthetic_df: pl.DataFrame,
) -> None:
    """Test evaluating on 'test' split raises DataContractError (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        run_staging_analysis(
            train_df=staging_synthetic_df,
            eval_df=staging_synthetic_df,
            calibrate_df=staging_synthetic_df,
            eval_split_name="test",
        )


def test_run_staging_analysis_success(staging_synthetic_df: pl.DataFrame) -> None:
    """Test successful execution of staging analysis comparing Joint Direct vs Staged Cascaded."""
    train_df = staging_synthetic_df[:50]
    eval_df = staging_synthetic_df[50:]
    calib_df = staging_synthetic_df[25:50]

    report = run_staging_analysis(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name="select",
        n_resamples=50,
        seed=42,
    )

    assert isinstance(report, StagingAnalysisReport)
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == len(eval_df)
    assert report.verdict in (
        StagingVerdict.JOINT_NESTED_ROUTING,
        StagingVerdict.CASCADED_RESIDUAL_STAGING,
    )

    # Verify metrics
    assert report.joint_metrics.mae > 0.0
    assert report.staged_metrics.mae > 0.0
    assert report.joint_metrics.crossing_rate == 0.0
    assert report.staged_metrics.crossing_rate == 0.0
    assert report.delta_pinball_ci_lower <= report.delta_pinball_ci_upper
    assert report.width_ratio > 0.0

    # Verify variance diagnostics
    diag = report.variance_diagnostics
    assert diag.stage_0_variance >= 0.0
    assert diag.stage_1_variance >= 0.0
    assert diag.total_cascade_variance >= 0.0
    assert diag.variance_inflation_factor > 0.0

    # Verify noise stress test results
    assert len(report.noise_stress_results) == 4
    for res in report.noise_stress_results:
        assert res.noise_rate in (0.0, 0.10, 0.20, 0.30)
        assert res.joint_amplification >= 1.0 or res.noise_rate == 0.0
        assert res.staged_amplification >= 1.0 or res.noise_rate == 0.0

    # Serialization
    d = report.to_dict()
    assert d["report_id"].startswith("EXP08-STAGING-")
    md = report.to_markdown()
    assert "# Staged versus Joint Modelling Analysis" in md
    assert "Error Propagation & Variance Accumulation" in md
    assert "Seniority Classification Ambiguity Stress Test" in md


def test_evaluate_and_save_staging_analysis_missing_file(tmp_path: Path) -> None:
    """Test evaluate_and_save_staging_analysis raises validation error on missing file."""
    missing = tmp_path / "missing.parquet"
    with pytest.raises(CompIntelValidationError, match="Canonical dataset not found"):
        evaluate_and_save_staging_analysis(canonical_path=missing)


def test_evaluate_and_save_staging_analysis_synthetic_blocked(
    tmp_path: Path, staging_synthetic_df: pl.DataFrame
) -> None:
    """Test synthetic data is blocked without explicit allow_synthetic override (Rule R-MD-11)."""
    p = tmp_path / "canonical.parquet"
    staging_synthetic_df.write_parquet(p)

    with pytest.raises(DataContractError, match="Synthetic data detected"):
        evaluate_and_save_staging_analysis(canonical_path=p, allow_synthetic=False)


def test_evaluate_and_save_staging_analysis_test_split_blocked() -> None:
    """Test evaluate_and_save_staging_analysis rejects locked test split (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        evaluate_and_save_staging_analysis(eval_split_name="test")


def test_evaluate_and_save_staging_analysis_success(
    tmp_path: Path, staging_synthetic_df: pl.DataFrame
) -> None:
    """Test evaluate_and_save_staging_analysis persists Markdown and JSON report files."""
    canonical_file = tmp_path / "canonical.parquet"
    staging_synthetic_df.write_parquet(canonical_file)

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    report = evaluate_and_save_staging_analysis(
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
    assert report.report_id.startswith("EXP08-STAGING-")


def test_cli_parse_args_defaults() -> None:
    """Test CLI argument parsing default values."""
    with patch.object(sys, "argv", ["run_staging_analysis.py"]):
        args = parse_args()
        assert args.canonical_path == "data/canonical/canonical_observations.parquet"
        assert args.output_md == "docs/research/staged-vs-joint-modelling-exp08.md"
        assert args.output_json == "experiments/results/staged_vs_joint_modelling_v1.json"
        assert args.split == "select"
        assert args.n_resamples == 1000
        assert args.seed == 42
        assert args.allow_synthetic is False


def test_cli_runner_success(tmp_path: Path, staging_synthetic_df: pl.DataFrame) -> None:
    """Test successful CLI execution end-to-end."""
    synth_file = tmp_path / "canonical.parquet"
    staging_synthetic_df.write_parquet(synth_file)

    out_md = tmp_path / "cli_report.md"
    out_json = tmp_path / "cli_report.json"

    test_args = [
        "run_staging_analysis.py",
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
        ret_code = run_staging_analysis_main()

    assert ret_code == 0
    assert out_md.exists()
    assert out_json.exists()


def test_cli_runner_missing_canonical_file(tmp_path: Path) -> None:
    """Test CLI exit code 1 on missing canonical file."""
    missing_file = tmp_path / "does_not_exist.parquet"
    test_args = [
        "run_staging_analysis.py",
        "--canonical-path",
        str(missing_file),
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_staging_analysis_main()

    assert ret_code == 1


def test_cli_runner_fatal_exception() -> None:
    """Test CLI exit code 2 on unexpected fatal crash."""
    test_args = ["run_staging_analysis.py"]

    with (
        patch.object(sys, "argv", test_args),
        patch(
            "scripts.run_staging_analysis.evaluate_and_save_staging_analysis",
            side_effect=RuntimeError("Fatal divergence crash"),
        ),
    ):
        ret_code = run_staging_analysis_main()

    assert ret_code == 2
