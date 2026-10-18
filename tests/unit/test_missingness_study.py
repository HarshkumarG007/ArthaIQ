"""Unit tests for Missingness Study & Indicator Policy Engine and CLI (Rule R-MD-15, T6.06).

Adheres to:
- PRD Section 5 & FR-05: Progressive disclosure and structured profile sparsity.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; locked test set strictly protected.
- Rule R-MD-05: Standard evaluation metrics with bootstrap confidence intervals.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine.
- Rule R-MD-15: Missingness indicators only where justified by T6.06.
  Missing data is NEVER read as a personal trait.
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
from scripts.run_missingness_study import main as run_missingness_study_main
from scripts.run_missingness_study import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.missingness_study import (
    MissingnessPolicyVerdict,
    MissingnessStudyReport,
    evaluate_and_save_missingness_study,
    run_missingness_indicator_study,
)


@pytest.fixture
def missingness_synthetic_df() -> pl.DataFrame:
    """Fixture providing 60 synthetic observations with structured missingness for T6.06."""
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

    # Structured missingness in optional fields (50% missing)
    skills = ["Python, Docker" if i % 2 == 0 else None for i in range(n_rows)]
    domain = ["FinTech" if i % 3 == 0 else None for i in range(n_rows)]
    employer_tier = ["TIER_1_PRODUCT" if i % 4 == 0 else None for i in range(n_rows)]

    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 5) for i in range(n_rows)]

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
            "domain_specialization": domain,
            "employer_tier": employer_tier,
            "is_synthetic": [True] * n_rows,
        }
    )


def test_missingness_policy_verdict_values() -> None:
    """Test MissingnessPolicyVerdict enum string values."""
    assert MissingnessPolicyVerdict.PROHIBIT_INDICATORS == "PROHIBIT_INDICATORS"
    assert MissingnessPolicyVerdict.PERMIT_SPECIFIC_INDICATORS == "PERMIT_SPECIFIC_INDICATORS"


def test_run_missingness_test_split_lock_violation(missingness_synthetic_df: pl.DataFrame) -> None:
    """Test running missingness study on 'test' split raises DataContractError (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        run_missingness_indicator_study(
            train_df=missingness_synthetic_df,
            eval_df=missingness_synthetic_df,
            calibrate_df=missingness_synthetic_df,
            eval_split_name="test",
        )


def test_run_missingness_indicator_study_success(missingness_synthetic_df: pl.DataFrame) -> None:
    """Test successful execution of missingness study comparing native vs augmented models."""
    train_df = missingness_synthetic_df[:40]
    eval_df = missingness_synthetic_df[40:]
    calib_df = missingness_synthetic_df[20:40]

    report = run_missingness_indicator_study(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name="select",
        n_resamples=50,
        seed=42,
    )

    assert isinstance(report, MissingnessStudyReport)
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == len(eval_df)
    assert report.verdict == MissingnessPolicyVerdict.PROHIBIT_INDICATORS

    # Verify native vs indicator metrics
    assert report.native_model_metrics.mae > 0.0
    assert report.indicator_model_metrics.mae > 0.0
    assert report.native_model_metrics.crossing_rate == 0.0
    assert report.indicator_model_metrics.crossing_rate == 0.0

    # Verify bootstrap CI
    assert report.delta_pinball_ci_lower <= report.delta_pinball_ci_upper

    # Verify feature audits
    assert len(report.feature_audits) > 0
    for fa in report.feature_audits:
        assert 0.0 <= fa.missing_rate <= 1.0
        assert fa.is_indicator_justified is False

    # Policy statement
    assert "ZERO-INDICATOR INVARIANT" in report.formal_policy_statement

    # Serialization
    d = report.to_dict()
    assert d["report_id"].startswith("MISSINGNESS-RMD15-")
    md = report.to_markdown()
    assert "# Missingness Study & Feature Indicator Policy Report" in md
    assert "Formal Missingness Policy Specification" in md


def test_evaluate_and_save_missingness_study_missing_file(tmp_path: Path) -> None:
    """Test evaluate_and_save_missingness_study with missing file raises validation error."""
    missing = tmp_path / "missing.parquet"
    with pytest.raises(CompIntelValidationError, match="Canonical dataset not found"):
        evaluate_and_save_missingness_study(canonical_path=missing)


def test_evaluate_and_save_missingness_study_synthetic_blocked(
    tmp_path: Path, missingness_synthetic_df: pl.DataFrame
) -> None:
    """Test synthetic data is blocked without allow_synthetic override (Rule R-MD-11)."""
    p = tmp_path / "canonical.parquet"
    missingness_synthetic_df.write_parquet(p)

    with pytest.raises(DataContractError, match="Synthetic data detected"):
        evaluate_and_save_missingness_study(canonical_path=p, allow_synthetic=False)


def test_evaluate_and_save_missingness_study_test_split_blocked() -> None:
    """Test evaluate_and_save_missingness_study rejects locked test split (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        evaluate_and_save_missingness_study(eval_split_name="test")


def test_evaluate_and_save_missingness_study_success(
    tmp_path: Path, missingness_synthetic_df: pl.DataFrame
) -> None:
    """Test evaluate_and_save_missingness_study saves Markdown and JSON report files."""
    canonical_file = tmp_path / "canonical.parquet"
    missingness_synthetic_df.write_parquet(canonical_file)

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    report = evaluate_and_save_missingness_study(
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
    assert report.report_id.startswith("MISSINGNESS-RMD15-")


def test_cli_parse_args_defaults() -> None:
    """Test CLI argument parsing default values."""
    with patch.object(sys, "argv", ["run_missingness_study.py"]):
        args = parse_args()
        assert args.canonical_path == "data/canonical/canonical_observations.parquet"
        assert args.output_md == "docs/research/missingness-policy-r-md-15.md"
        assert args.output_json == "experiments/results/missingness_study_v1.json"
        assert args.split == "select"
        assert args.n_resamples == 1000
        assert args.seed == 42
        assert args.allow_synthetic is False


def test_cli_runner_success(tmp_path: Path, missingness_synthetic_df: pl.DataFrame) -> None:
    """Test successful CLI execution end-to-end."""
    synth_file = tmp_path / "canonical.parquet"
    missingness_synthetic_df.write_parquet(synth_file)

    out_md = tmp_path / "cli_report.md"
    out_json = tmp_path / "cli_report.json"

    test_args = [
        "run_missingness_study.py",
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
        ret_code = run_missingness_study_main()

    assert ret_code == 0
    assert out_md.exists()
    assert out_json.exists()


def test_cli_runner_missing_canonical_file(tmp_path: Path) -> None:
    """Test CLI exit code 1 on missing canonical file."""
    missing_file = tmp_path / "does_not_exist.parquet"
    test_args = [
        "run_missingness_study.py",
        "--canonical-path",
        str(missing_file),
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_missingness_study_main()

    assert ret_code == 1


def test_cli_runner_fatal_exception() -> None:
    """Test CLI exit code 2 on unexpected fatal crash."""
    test_args = ["run_missingness_study.py"]

    with (
        patch.object(sys, "argv", test_args),
        patch(
            "scripts.run_missingness_study.evaluate_and_save_missingness_study",
            side_effect=RuntimeError("Fatal divergence crash"),
        ),
    ):
        ret_code = run_missingness_study_main()

    assert ret_code == 2
