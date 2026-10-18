"""Unit tests for Feature-Family Ablation Engine and CLI (EXP-06, Task T6.04).

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and feature family evaluation.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Objective business model tiers without proprietary black-box ranks.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine (EXP-07).
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
from scripts.run_family_ablation import main as run_family_ablation_main
from scripts.run_family_ablation import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.family_ablation import (
    EXP06_FAMILY_SPECS,
    FamilyAblationReport,
    FamilyDispositionVerdict,
    evaluate_and_save_family_ablation,
    run_family_ablation_study,
)
from compintel.features.spec import get_feature


@pytest.fixture
def family_ablation_synthetic_df() -> pl.DataFrame:
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
            "person_cluster_id": [f"PER-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "guaranteed_cash_annual": salaries,
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "skills_primary": ["PYTHON", "GO", "JAVA"] * (n_rows // 3),
            "skills_depth": ["COMMODITY", "INTERMEDIATE", "HIGH_DEPTH"] * (n_rows // 3),
            "domain_specialization": ["FINTECH", "ECOMMERCE", "AI_INFRA"] * (n_rows // 3),
            "employer_tier": ["TIER_1_PRODUCT", "GCC", "IT_SERVICES"] * (n_rows // 3),
            "work_arrangement": ["HYBRID", "FULL_REMOTE", "ON_SITE"] * (n_rows // 3),
            "career_velocity": [1.0, 1.2, 0.9] * (n_rows // 3),
            "leadership_scope": ["IC_INDIVIDUAL", "TEAM_LEAD_MGR"] * (n_rows // 2),
            "macro_market_regime": ["EXPANSIONARY", "STABLE"] * (n_rows // 2),
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


def test_family_specs_registry_integrity() -> None:
    """Test that all feature IDs in EXP06_FAMILY_SPECS exist in the official FEATURE_REGISTRY."""
    assert len(EXP06_FAMILY_SPECS) == 7
    for fam in EXP06_FAMILY_SPECS:
        assert fam["threshold_pinball"] < 0.0
        assert fam["default_action"] in (
            FamilyDispositionVerdict.KEEP,
            FamilyDispositionVerdict.DEFER,
            FamilyDispositionVerdict.REJECT,
        )
        for fid in fam["feature_ids"]:
            spec = get_feature(fid)
            assert spec is not None
            assert spec.is_input_feature is True


def test_run_family_ablation_test_split_lock_violation(
    family_ablation_synthetic_df: pl.DataFrame,
) -> None:
    """Test that running family ablation on 'test' split raises DataContractError (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        run_family_ablation_study(
            train_df=family_ablation_synthetic_df,
            eval_df=family_ablation_synthetic_df,
            calibrate_df=family_ablation_synthetic_df,
            eval_split_name="test",
        )


def test_run_family_ablation_study_success(family_ablation_synthetic_df: pl.DataFrame) -> None:
    """Test end-to-end family ablation study execution on synthetic partitions."""
    train_df = family_ablation_synthetic_df[:40]
    eval_df = family_ablation_synthetic_df[40:]
    calib_df = family_ablation_synthetic_df[20:40]

    report = run_family_ablation_study(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name="select",
        n_resamples=50,  # Fast bootstrap for testing
        seed=42,
    )

    assert isinstance(report, FamilyAblationReport)
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == len(eval_df)
    assert len(report.family_results) == 7

    # Check baseline metrics
    assert report.l0_baseline_metrics.mae > 0.0
    assert report.l0_baseline_metrics.mean_pinball_loss > 0.0
    assert 0.0 <= report.l0_baseline_metrics.empirical_coverage <= 1.0
    assert report.l0_baseline_metrics.crossing_rate == 0.0

    # Check each family result
    for fam_item in report.family_results:
        assert fam_item.forward_addition_metrics.n_features > report.l0_baseline_metrics.n_features
        assert fam_item.forward_delta.width_ratio > 0.0
        assert fam_item.verdict in (
            FamilyDispositionVerdict.KEEP,
            FamilyDispositionVerdict.DEFER,
            FamilyDispositionVerdict.REJECT,
        )
        assert len(fam_item.decision_rationale) > 0

    # Serialization checks
    d = report.to_dict()
    assert d["report_id"].startswith("EXP06-ABLATION-")
    assert len(d["family_results"]) == 7

    md = report.to_markdown()
    assert "# Feature-Family Ablation Study Report (EXP-06)" in md
    assert "Skills & Depth (Family A)" in md
    assert "Employer Archetype Tier (Family C)" in md


def test_evaluate_and_save_family_ablation_missing_file(tmp_path: Path) -> None:
    """Test evaluate_and_save_family_ablation with non-existent canonical path."""
    missing_path = tmp_path / "not_there.parquet"
    with pytest.raises(CompIntelValidationError, match="Canonical dataset not found"):
        evaluate_and_save_family_ablation(canonical_path=missing_path)


def test_evaluate_and_save_family_ablation_synthetic_blocked(
    tmp_path: Path, family_ablation_synthetic_df: pl.DataFrame
) -> None:
    """Test that synthetic data is rejected without explicit override (Rule R-MD-11)."""
    p = tmp_path / "canonical_with_synth.parquet"
    family_ablation_synthetic_df.write_parquet(p)

    with pytest.raises(DataContractError, match="Synthetic data detected"):
        evaluate_and_save_family_ablation(canonical_path=p, allow_synthetic=False)


def test_evaluate_and_save_family_ablation_test_split_blocked() -> None:
    """Test that evaluate_and_save_family_ablation rejects test split (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        evaluate_and_save_family_ablation(eval_split_name="test")


def test_evaluate_and_save_family_ablation_success(
    tmp_path: Path, family_ablation_synthetic_df: pl.DataFrame
) -> None:
    """Test evaluate_and_save_family_ablation produces valid report files."""
    canonical_file = tmp_path / "canonical.parquet"
    family_ablation_synthetic_df.write_parquet(canonical_file)

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    report = evaluate_and_save_family_ablation(
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
    assert report.report_id.startswith("EXP06-ABLATION-")


def test_cli_parse_args_defaults() -> None:
    """Test CLI argument parsing defaults."""
    with patch.object(sys, "argv", ["run_family_ablation.py"]):
        args = parse_args()
        assert args.canonical_path == "data/canonical/canonical_observations.parquet"
        assert args.output_md == "docs/research/feature-family-ablations.md"
        assert args.output_json == "experiments/results/feature_family_ablations_v1.json"
        assert args.split == "select"
        assert args.n_resamples == 1000
        assert args.seed == 42
        assert args.allow_synthetic is False


def test_cli_runner_success(tmp_path: Path, family_ablation_synthetic_df: pl.DataFrame) -> None:
    """Test successful CLI runner execution end-to-end."""
    synth_file = tmp_path / "canonical.parquet"
    family_ablation_synthetic_df.write_parquet(synth_file)

    out_md = tmp_path / "cli_report.md"
    out_json = tmp_path / "cli_report.json"

    test_args = [
        "run_family_ablation.py",
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
        ret_code = run_family_ablation_main()

    assert ret_code == 0
    assert out_md.exists()
    assert out_json.exists()


def test_cli_runner_missing_canonical_file(tmp_path: Path) -> None:
    """Test CLI error handling on missing canonical file."""
    missing_file = tmp_path / "does_not_exist.parquet"
    test_args = [
        "run_family_ablation.py",
        "--canonical-path",
        str(missing_file),
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_family_ablation_main()

    assert ret_code == 1


def test_cli_runner_fatal_exception() -> None:
    """Test CLI exit code 2 on unexpected fatal exception."""
    test_args = ["run_family_ablation.py"]

    with (
        patch.object(sys, "argv", test_args),
        patch(
            "scripts.run_family_ablation.evaluate_and_save_family_ablation",
            side_effect=RuntimeError("Unrecoverable runtime crash"),
        ),
    ):
        ret_code = run_family_ablation_main()

    assert ret_code == 2
