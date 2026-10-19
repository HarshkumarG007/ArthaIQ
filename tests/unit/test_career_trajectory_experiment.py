"""Unit tests for Career Trajectory Feature Modeling Experiment Engine and CLI (Task T7.03).

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and career trajectory modeling.
- CHARTER-CAREER-TRAJ: experiments/configs/charters/charter_career_trajectory.yaml.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-04: Feature statistics fitted inside training folds only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charters before implementation.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_career_trajectory_experiment import parse_args

from compintel.errors import DataContractError
from compintel.evaluation.career_trajectory_experiment import (
    TrajectoryDecisionVerdict,
    TrajectoryExperimentReport,
    TrajectoryVariant,
    _build_l2_feature_dataframe,
    _compute_career_velocity,
    _compute_cohort_velocity_means,
    _compute_company_tier_mobility,
    _compute_paired_bootstrap_ci,
    _compute_promotion_acceleration,
    _compute_tenure_stability_ratio,
    _get_seniority_rank,
    _get_yoe_band,
    evaluate_and_save_career_trajectory,
    run_career_trajectory_experiment,
)


@pytest.fixture
def career_trajectory_synthetic_df() -> pl.DataFrame:
    """Fixture providing 60 synthetic observations across L0-L2 feature tiers."""
    n_rows = 60
    rng = np.random.default_rng(42)

    roles = ["SWE", "DATA", "MLAI"] * (n_rows // 3)
    seniorities = ["JR", "MID", "SR", "LEAD"] * (n_rows // 4)
    locations = ["BANGALORE", "HYDERABAD", "PUNE", "MUMBAI", "NCR"] * (n_rows // 5)
    yoe = [float(i % 15) + 1.0 for i in range(n_rows)]

    salaries = [
        12.0 + (y * 1.8) + (8.0 if s in ("SR", "LEAD") else 0.0) + (float(rng.uniform(-1.0, 1.0)))
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
            "canonical_title": ["Software Engineer", "Data Scientist", "ML Engineer"]
            * (n_rows // 3),
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "skills_primary": ["PYTHON", "GO", "JAVA"] * (n_rows // 3),
            "is_synthetic": [True] * n_rows,
        }
    )


def test_trajectory_variants_enum() -> None:
    """Test that all three candidate trajectory variants exist with expected enum values."""
    assert TrajectoryVariant.BASELINE_CHAMPION.value == "baseline_champion_l2"
    assert TrajectoryVariant.VARIANT_A_VELOCITY.value == "variant_a_career_velocity"
    assert TrajectoryVariant.VARIANT_B_TRAJECTORY_VECTOR.value == "variant_b_trajectory_vector"
    assert len(TrajectoryVariant) == 3


def test_trajectory_verdicts_enum() -> None:
    """Test that all decision verdicts exist."""
    assert TrajectoryDecisionVerdict.KEEP.value == "KEEP"
    assert TrajectoryDecisionVerdict.DEFER.value == "DEFER"
    assert TrajectoryDecisionVerdict.REJECT.value == "REJECT"
    assert len(TrajectoryDecisionVerdict) == 3


def test_seniority_rank_and_velocity() -> None:
    """Test seniority rank mapping and career velocity calculations."""
    assert _get_seniority_rank("JR") == 1.0
    assert _get_seniority_rank("MID") == 2.0
    assert _get_seniority_rank("SR") == 3.0
    assert _get_seniority_rank("LEAD") == 4.0
    assert _get_seniority_rank("STAFF") == 4.5
    assert _get_seniority_rank("PRINCIPAL") == 5.5
    assert _get_seniority_rank("UNKNOWN_LEVEL") == 2.5  # default

    # Test career velocity
    sen_list = ["SR", "JR"]
    yoe_arr = np.array([2.0, 4.0])
    # SR rank = 3.0 -> velocity = 3.0 / 2.0 = 1.5
    # JR rank = 1.0 -> velocity = 1.0 / 4.0 = 0.25
    vel = _compute_career_velocity(sen_list, yoe_arr)
    assert np.isclose(vel[0], 1.5)
    assert np.isclose(vel[1], 0.25)


def test_tenure_stability_ratio_and_mobility() -> None:
    """Test tenure stability ratio bounds and company tier mobility indicator."""
    yoe = np.array([1.0, 5.0, 10.0])
    ratio = _compute_tenure_stability_ratio(yoe)
    assert (ratio >= 0.0).all() and (ratio <= 1.0).all()
    # At 1.0 YoE: min(1, 3)/1.0 = 1.0
    assert np.isclose(ratio[0], 1.0)
    # At 10.0 YoE: min(10, 3)/10.0 = 0.3
    assert np.isclose(ratio[2], 0.3)

    # Test mobility indicator: SR+ in <= 4 yrs or Staff+ in <= 8 yrs
    mobility = _compute_company_tier_mobility(["SR", "STAFF", "SR"], np.array([3.0, 15.0, 8.0]))
    assert mobility[0] == 1.0  # SR with 3 YoE
    assert mobility[1] == 0.0  # Staff with 15 YoE
    assert mobility[2] == 0.0  # SR with 8 YoE (> 4 yrs)


def test_yoe_band_mapping() -> None:
    """Test YoE band mapping."""
    assert _get_yoe_band(1.5) == "0_2"
    assert _get_yoe_band(4.0) == "3_5"
    assert _get_yoe_band(7.5) == "6_10"
    assert _get_yoe_band(12.0) == "11_15"
    assert _get_yoe_band(20.0) == "16_plus"


def test_cohort_means_and_promotion_acceleration() -> None:
    """Test cohort velocity means fitting inside training fold (Rule R-MD-04)."""
    sen_list = ["JR", "MID", "SR"]
    yoe_arr = np.array([1.0, 4.0, 8.0])

    cohort_means = _compute_cohort_velocity_means(sen_list, yoe_arr)
    assert "0_2" in cohort_means
    assert "3_5" in cohort_means
    assert "6_10" in cohort_means

    # Test acceleration
    accel = _compute_promotion_acceleration(sen_list, yoe_arr, cohort_means)
    assert len(accel) == 3
    # First item velocity matches cohort mean -> accel near 0
    assert np.isclose(accel[0], 0.0, atol=1e-5)


def test_build_l2_feature_dataframe(career_trajectory_synthetic_df: pl.DataFrame) -> None:
    """Test Level 2 feature DataFrame construction."""
    x_df, cat_cols = _build_l2_feature_dataframe(career_trajectory_synthetic_df.slice(0, 10))
    assert x_df.shape[0] == 10
    assert "feat_l0_seniority" in x_df.columns
    assert "feat_l0_location" in x_df.columns
    assert "feat_l0_role_family" in x_df.columns
    assert "feat_l0_years_experience" in x_df.columns
    assert "feat_l0_yoe_squared" in x_df.columns
    assert "feat_l0_seniority" in cat_cols


def test_compute_paired_bootstrap_ci() -> None:
    """Test paired bootstrap confidence intervals and statistical significance."""
    deltas_sig = np.array([-0.10, -0.12, -0.09, -0.15, -0.11, -0.08, -0.14, -0.10])
    ci_l, ci_u, is_sig = _compute_paired_bootstrap_ci(deltas_sig, n_resamples=500, seed=42)
    assert is_sig is True
    assert ci_u < 0.0
    assert ci_l <= ci_u

    deltas_null = np.array([-0.02, 0.03, -0.01, 0.02, -0.03, 0.01])
    ci_l2, ci_u2, is_sig2 = _compute_paired_bootstrap_ci(deltas_null, n_resamples=500, seed=42)
    assert is_sig2 is False
    assert ci_l2 < 0.0 < ci_u2


def test_run_career_trajectory_experiment(career_trajectory_synthetic_df: pl.DataFrame) -> None:
    """Test complete experiment orchestration across training, calibration, and eval splits."""
    train_df = career_trajectory_synthetic_df.slice(0, 30)
    calib_df = career_trajectory_synthetic_df.slice(30, 15)
    eval_df = career_trajectory_synthetic_df.slice(45, 15)

    report = run_career_trajectory_experiment(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name="select",
        n_resamples=100,
        seed=42,
    )

    assert isinstance(report, TrajectoryExperimentReport)
    assert report.charter_id == "CHARTER-CAREER-TRAJ"
    assert report.experiment_id == "EXP-TRAJ-01"
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == 15

    # Check baseline metrics
    b = report.baseline_metrics
    assert b.variant == TrajectoryVariant.BASELINE_CHAMPION
    assert b.mean_pinball_loss > 0.0
    assert 0.0 <= b.empirical_coverage <= 1.0
    assert b.crossing_rate == 0.0  # Monotonic conformal guarantee (R-UQ-05)

    # Check variant metrics
    assert len(report.deltas) == 2
    assert report.overall_verdict in (
        TrajectoryDecisionVerdict.KEEP,
        TrajectoryDecisionVerdict.DEFER,
        TrajectoryDecisionVerdict.REJECT,
    )

    # Check markdown rendering
    md = report.to_markdown()
    assert "# Career Trajectory Features vs Static Baseline" in md
    assert "CHARTER-CAREER-TRAJ" in md
    assert "Champion Baseline" in md

    # Check dictionary serialization
    d = report.to_dict()
    assert d["charter_id"] == "CHARTER-CAREER-TRAJ"
    assert len(d["deltas"]) == 2


def test_test_partition_isolation_contract(career_trajectory_synthetic_df: pl.DataFrame) -> None:
    """Verify that running experiment on locked 'test' split raises DataContractError (R-MD-02)."""
    train_df = career_trajectory_synthetic_df.slice(0, 30)
    calib_df = career_trajectory_synthetic_df.slice(30, 15)
    eval_df = career_trajectory_synthetic_df.slice(45, 15)

    with pytest.raises(DataContractError) as exc_info:
        run_career_trajectory_experiment(
            train_df=train_df,
            eval_df=eval_df,
            calibrate_df=calib_df,
            eval_split_name="test",
        )
    assert "EVALUATION_ISOLATION_VIOLATION" in str(exc_info.value)
    assert exc_info.value.details.get("rule_id") == "R-MD-02"


def test_synthetic_data_isolation_contract(
    tmp_path: Path, career_trajectory_synthetic_df: pl.DataFrame
) -> None:
    """Verify synthetic data in canonical dataset raises DataContractError (R-MD-11)."""
    file_path = tmp_path / "test_canonical.parquet"
    career_trajectory_synthetic_df.write_parquet(file_path)

    with pytest.raises(DataContractError) as exc_info:
        evaluate_and_save_career_trajectory(
            canonical_path=file_path,
            output_md=tmp_path / "out.md",
            output_json=tmp_path / "out.json",
            allow_synthetic=False,
        )
    assert "SYNTHETIC_DATA_BLOCKED" in str(exc_info.value.code)
    assert exc_info.value.details.get("rule_id") == "R-MD-11"


def test_career_trajectory_cli_args() -> None:
    """Test CLI argument parsing and default configurations."""
    test_args = [
        "scripts/run_career_trajectory.py",
        "--canonical-path",
        "custom/path.parquet",
        "--output-md",
        "custom/out.md",
        "--output-json",
        "custom/out.json",
        "--split",
        "calibrate",
        "--n-resamples",
        "500",
        "--seed",
        "123",
        "--allow-synthetic",
    ]
    with patch("sys.argv", test_args):
        args = parse_args()
        assert args.canonical_path == "custom/path.parquet"
        assert args.output_md == "custom/out.md"
        assert args.output_json == "custom/out.json"
        assert args.split == "calibrate"
        assert args.n_resamples == 500
        assert args.seed == 123
        assert args.allow_synthetic is True
