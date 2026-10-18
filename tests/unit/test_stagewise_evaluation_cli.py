"""Unit tests for Stage-Wise Progressive Personalization Evaluation CLI runner (Task T6.03b).

Adheres to:
- PRD Section 5 & FR-05: Progressive disclosure across feature tiers L0 to L3.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test split locked.
- Rule R-MD-05: Standard metrics reporting with paired differences.
- Rule R-MD-11: Synthetic data isolation enforcement.
- Rule R-MD-15: Masked-missingness simulation audit.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_stagewise_evaluation import main as run_stagewise_main
from scripts.run_stagewise_evaluation import parse_args


@pytest.fixture
def cli_synthetic_df() -> pl.DataFrame:
    """Fixture providing 60 synthetic observations across L0-L3 tiers."""
    n_rows = 60
    rng = np.random.default_rng(42)

    roles = ["SOFTWARE", "DATA", "MLAI"] * (n_rows // 3)
    seniorities = ["JUNIOR", "MID", "SENIOR", "LEAD"] * (n_rows // 4)
    locations = ["BANGALORE", "HYDERABAD", "PUNE", "DELHI_NCR", "MUMBAI"] * (n_rows // 5)
    yoe = [float(i % 15) + 1.0 for i in range(n_rows)]

    salaries = [
        12.0
        + (y * 1.8)
        + (8.0 if s in ("SENIOR", "LEAD") else 0.0)
        + (float(rng.uniform(-1.0, 1.0)))
        for y, s in zip(yoe, seniorities, strict=False)
    ]

    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 5) for i in range(n_rows)]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "guaranteed_cash_annual": salaries,
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "skills_primary": ["PYTHON", "GO", "JAVA"] * (n_rows // 3),
            "skills_depth": [3, 4, 5] * (n_rows // 3),
            "domain_specialization": ["FINTECH", "ECOMMERCE", "AI_INFRA"] * (n_rows // 3),
            "employer_tier": ["TIER_1", "TIER_2", "TIER_3"] * (n_rows // 3),
            "work_arrangement": ["HYBRID", "REMOTE", "ONSITE"] * (n_rows // 3),
            "career_velocity": [1.0, 1.2, 0.9] * (n_rows // 3),
            "leadership_scope": ["INDIVIDUAL_CONTRIBUTOR", "TEAM_LEAD"] * (n_rows // 2),
            "macro_market_regime": ["EXPANSION", "NORMAL"] * (n_rows // 2),
            "target_employer_id": [f"ECLUST-{i % 5:02d}" for i in range(n_rows)],
            "target_level_code": ["L5", "SDE2", "MTS-3"] * (n_rows // 3),
            "competing_offers_count": [0, 1, 2] * (n_rows // 3),
            "notice_period_days": [30, 60, 90] * (n_rows // 3),
            "verified_payslip_level": [
                "SELF_REPORTED",
                "DOCUMENT_VERIFIED",
                "ENTERPRISE_CONFIRMED",
            ]
            * (n_rows // 3),
            "fixed_allowance_ratio": [0.35, 0.45, 0.55] * (n_rows // 3),
            "project_scale_tier": ["SCALE_MODEST", "SCALE_MEDIUM", "HYPERSCALE"] * (n_rows // 3),
            "tenure_stability_index": [2.0, 3.5, 1.5] * (n_rows // 3),
            "current_guaranteed_cash": [s * 0.85 for s in salaries],
            "is_synthetic": [True] * n_rows,
        }
    )


def test_parse_args_defaults() -> None:
    """Test CLI argument parsing defaults."""
    with patch.object(sys, "argv", ["run_stagewise_evaluation.py"]):
        args = parse_args()
        assert args.canonical_path == "data/canonical/canonical_observations.parquet"
        assert args.output_md == "docs/research/stagewise-evaluation-l0-l3.md"
        assert args.output_json == "experiments/results/stagewise_evaluation_v1.json"
        assert args.split == "select"
        assert args.n_resamples == 1000
        assert args.seed == 42
        assert args.allow_synthetic is False


def test_cli_runner_success(tmp_path: Path, cli_synthetic_df: pl.DataFrame) -> None:
    """Test successful CLI runner execution end-to-end."""
    synth_file = tmp_path / "canonical.parquet"
    cli_synthetic_df.write_parquet(synth_file)

    out_md = tmp_path / "output.md"
    out_json = tmp_path / "output.json"

    test_args = [
        "run_stagewise_evaluation.py",
        "--canonical-path",
        str(synth_file),
        "--output-md",
        str(out_md),
        "--output-json",
        str(out_json),
        "--split",
        "select",
        "--n-resamples",
        "50",  # Fast bootstrap for testing
        "--seed",
        "42",
        "--allow-synthetic",
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_stagewise_main()

    assert ret_code == 0
    assert out_md.exists()
    assert out_json.exists()
    md_content = out_md.read_text(encoding="utf-8")
    assert "Stage-Wise Progressive Personalization Evaluation Report" in md_content
    assert "Level 0: Core Baseline" in md_content


def test_cli_runner_missing_canonical_file(tmp_path: Path) -> None:
    """Test CLI error handling when canonical file does not exist."""
    missing_file = tmp_path / "non_existent.parquet"
    test_args = [
        "run_stagewise_evaluation.py",
        "--canonical-path",
        str(missing_file),
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_stagewise_main()

    assert ret_code == 1


def test_cli_runner_synthetic_blocked(tmp_path: Path, cli_synthetic_df: pl.DataFrame) -> None:
    """Test that synthetic data is rejected when --allow-synthetic is omitted (Rule R-MD-11)."""
    synth_file = tmp_path / "canonical_with_synth.parquet"
    cli_synthetic_df.write_parquet(synth_file)

    test_args = [
        "run_stagewise_evaluation.py",
        "--canonical-path",
        str(synth_file),
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_stagewise_main()

    assert ret_code == 1


def test_cli_runner_fatal_exception() -> None:
    """Test CLI exit code 2 on unexpected fatal exception."""
    test_args = ["run_stagewise_evaluation.py"]

    with (
        patch.object(sys, "argv", test_args),
        patch(
            "scripts.run_stagewise_evaluation.evaluate_and_save_stagewise_evaluation",
            side_effect=RuntimeError("Unrecoverable runtime crash"),
        ),
    ):
        ret_code = run_stagewise_main()

    assert ret_code == 2
