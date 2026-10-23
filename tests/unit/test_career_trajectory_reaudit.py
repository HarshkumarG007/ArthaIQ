"""Unit tests for EXP-TRAJ-r: Career Trajectory Feature Re-evaluation (Phase 13, Task T13.05).

Tests:
1. Audit of longitudinal panel depth and observation span on cumulative non-synthetic panel.
2. Threshold qualification logic (calendar span >= 12.0 months, milestone records >= 100).
3. Synthetic data quarantine isolation guard under Rule R-MD-11 (SYNTHETIC_DATA_BLOCKED).
4. Gate 1 feasibility audit: under-spanned 6-month panel triggers INSUFFICIENT_SPAN_DEFER.
5. Gate 1 feasibility audit: qualified multi-year panel passes SUFFICIENT_PANEL_DEPTH.
6. Default re-audit execution: Gate 1 DEFER verdict with empirical modeling held in abeyance.
7. Forced empirical modeling execution: runs CatBoost L2 baseline vs Variant A and Variant B.
8. Report serialization to structured dictionary and publication-grade Markdown rendering.
9. Persistence and directory file emission via evaluate_and_save_career_trajectory_reaudit.
10. CLI runner argument parsing and execution via scripts/run_career_trajectory_reaudit.py.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
from scripts.run_career_trajectory_reaudit import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.career_trajectory_reaudit import (
    CareerTrajectoryReauditVerdict,
    LongitudinalAuditStatus,
    audit_longitudinal_panel_depth,
    evaluate_and_save_career_trajectory_reaudit,
    run_career_trajectory_reaudit,
)
from compintel.evaluation.employer_graph_reaudit import build_post_exp16_cumulative_panel


@pytest.fixture
def cumulative_panel() -> pl.DataFrame:
    """Build standard 6-month non-synthetic cumulative production panel."""
    return build_post_exp16_cumulative_panel(months_operational=6.0, seed=42)


def test_audit_longitudinal_panel_depth_current_panel(cumulative_panel: pl.DataFrame) -> None:
    """Verify panel depth and observation span on the live 6-month production panel."""
    metrics = audit_longitudinal_panel_depth(
        df=cumulative_panel,
        min_span_months=12.0,
        min_longitudinal_records=100,
    )

    assert metrics.total_records == 219
    assert metrics.non_synthetic_records == 219
    assert metrics.synthetic_records == 0
    assert 170 <= metrics.panel_span_days <= 185
    assert 5.5 <= metrics.panel_span_months <= 6.5
    assert metrics.required_span_months == 12.0
    assert not metrics.is_span_sufficient
    assert metrics.span_deficit_months > 5.0
    assert metrics.longitudinal_populated_records == 0
    assert not metrics.is_depth_sufficient
    assert metrics.record_deficit == 100


def test_audit_longitudinal_panel_depth_sufficient() -> None:
    """Verify panel depth audit when longitudinal panel meets and exceeds thresholds."""
    start_date = date(2025, 1, 1)
    end_date = date(2026, 4, 1)  # ~15 months = 455 days

    records = [
        {
            "observation_id": f"OBS-LONG-{i:03d}",
            "is_synthetic": False,
            "as_of_date": start_date + timedelta(days=int(i * 3)),
            "career_start_date": date(2020, 1, 1),
            "last_promotion_date": date(2024, 6, 1),
            "right_censored_exit_flag": False,
        }
        for i in range(120)
    ]
    # Set final date to end_date
    records[-1]["as_of_date"] = end_date
    df = pl.DataFrame(records)

    metrics = audit_longitudinal_panel_depth(
        df=df,
        min_span_months=12.0,
        min_longitudinal_records=100,
    )

    assert metrics.total_records == 120
    assert metrics.non_synthetic_records == 120
    assert metrics.panel_span_months >= 12.0
    assert metrics.is_span_sufficient
    assert metrics.span_deficit_months == 0.0
    assert metrics.longitudinal_populated_records == 120
    assert metrics.is_depth_sufficient
    assert metrics.record_deficit == 0


def test_audit_validation_errors(cumulative_panel: pl.DataFrame) -> None:
    """Verify input validation errors for invalid threshold arguments."""
    with pytest.raises(CompIntelValidationError, match="min_span_months must be positive"):
        audit_longitudinal_panel_depth(df=cumulative_panel, min_span_months=0.0)

    with pytest.raises(CompIntelValidationError, match="min_span_months must be positive"):
        audit_longitudinal_panel_depth(df=cumulative_panel, min_span_months=-5.0)

    with pytest.raises(
        CompIntelValidationError, match="min_longitudinal_records must be non-negative"
    ):
        audit_longitudinal_panel_depth(df=cumulative_panel, min_longitudinal_records=-1)


def test_synthetic_data_quarantine_guard(cumulative_panel: pl.DataFrame) -> None:
    """Verify strict synthetic data isolation under Rule R-MD-11."""
    synthetic_row = cumulative_panel.slice(0, 1).with_columns(
        pl.lit(True).alias("is_synthetic"),
        pl.lit("OBS-SYNTH-LEAK").alias("observation_id"),
    )
    contaminated_panel = pl.concat([cumulative_panel, synthetic_row])

    with pytest.raises(DataContractError) as exc_info:
        run_career_trajectory_reaudit(contaminated_panel, allow_synthetic=False)

    assert exc_info.value.code == "SYNTHETIC_DATA_BLOCKED"
    assert exc_info.value.details.get("rule_id") == "R-MD-11"

    # Permitted when explicit override is provided
    report = run_career_trajectory_reaudit(contaminated_panel, allow_synthetic=True)
    assert report.panel_metrics.synthetic_records == 1


def test_run_career_trajectory_reaudit_default_defer(cumulative_panel: pl.DataFrame) -> None:
    """Verify default Gate 1 DEFER verdict on the 6-month post-EXP-16 production panel."""
    report = run_career_trajectory_reaudit(
        panel_df=cumulative_panel,
        allow_synthetic=False,
        force_experiment=False,
        seed=42,
    )

    assert report.charter_id == "CHARTER-CAREER-TRAJ-r"
    assert report.experiment_id == "EXP-TRAJ-r"
    assert report.task_id == "T13.05"
    assert report.audit_status == LongitudinalAuditStatus.INSUFFICIENT_SPAN_DEFER
    assert report.verdict == CareerTrajectoryReauditVerdict.DEFER
    assert report.model_evaluation is None
    assert "RETAINED_UNMODIFIED" in report.champion_status
    assert "2028-06-30" in report.next_trigger_date
    assert "12.0 calendar months" in report.next_trigger_condition
    assert "100" in report.next_trigger_condition
    assert "Gate 1 Longitudinal Feasibility DEFERRED" in report.executive_summary


def test_run_career_trajectory_reaudit_force_experiment(cumulative_panel: pl.DataFrame) -> None:
    """Verify forced empirical modeling execution on cumulative panel."""
    report = run_career_trajectory_reaudit(
        panel_df=cumulative_panel,
        allow_synthetic=False,
        force_experiment=True,
        n_resamples=50,
        seed=42,
    )

    assert report.model_evaluation is not None
    assert "baseline_metrics" in report.model_evaluation
    assert "variant_a_metrics" in report.model_evaluation
    assert "variant_b_metrics" in report.model_evaluation
    assert "deltas" in report.model_evaluation
    assert len(report.model_evaluation["deltas"]) == 2


def test_report_serialization_and_markdown(cumulative_panel: pl.DataFrame) -> None:
    """Verify report serialization to JSON dictionary and publication-grade Markdown."""
    report = run_career_trajectory_reaudit(
        panel_df=cumulative_panel,
        allow_synthetic=False,
        force_experiment=False,
        seed=42,
    )

    # 1. Dictionary serialization
    d = report.to_dict()
    assert d["charter_id"] == "CHARTER-CAREER-TRAJ-r"
    assert d["experiment_id"] == "EXP-TRAJ-r"
    assert d["audit_status"] == "INSUFFICIENT_SPAN_DEFER"
    assert d["verdict"] == "DEFER"
    assert d["panel_metrics"]["total_records"] == 219
    assert d["panel_metrics"]["longitudinal_populated_records"] == 0

    json_str = json.dumps(d)
    assert len(json_str) > 0

    # 2. Markdown memo rendering
    md = report.to_markdown()
    assert (
        "# Career Trajectory Feature Re-evaluation (Phase 13, EXP-TRAJ-r, CHARTER-CAREER-TRAJ-r)"
        in md
    )
    assert "## 1. Executive Summary & Governance Verdict" in md
    assert "## 2. Gate 1: Longitudinal Panel Depth & Milestone Telemetry Audit" in md
    assert "## 3. Candidate Trajectory Feature Specifications & Abeyance Status" in md
    assert "## 4. Production Champion Invariance & Operational Assessment" in md
    assert "## 5. Governance, Privacy & DPDPA 2023 Compliance" in md
    assert "## 6. Pre-Registered Next Audit Triggers & Phase 14 Roadmap" in md
    assert "INSUFFICIENT_SPAN_DEFER" in md
    assert "RETAINED_UNMODIFIED" in md


def test_evaluate_and_save_career_trajectory_reaudit(tmp_path: Path) -> None:
    """Verify end-to-end file persistence for JSON report and Markdown memo."""
    report = evaluate_and_save_career_trajectory_reaudit(
        output_dir=tmp_path,
        months_operational=6.0,
        min_span_months=12.0,
        min_longitudinal_records=100,
        allow_synthetic=False,
        force_experiment=False,
        seed=42,
        report_filename="test_report.json",
        md_filename="test_memo.md",
    )

    json_path = tmp_path / "test_report.json"
    md_path = tmp_path / "test_memo.md"

    assert json_path.is_file()
    assert md_path.is_file()

    saved_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved_json["report_id"] == report.report_id
    assert saved_json["verdict"] == "DEFER"

    saved_md = md_path.read_text(encoding="utf-8")
    assert report.report_id in saved_md
    assert "CHARTER-CAREER-TRAJ-r" in saved_md


def test_cli_runner_args() -> None:
    """Verify CLI runner argument parser defaults and overrides."""
    with patch("sys.argv", ["run_career_trajectory_reaudit.py"]):
        args = parse_args()
        assert args.output_md == "docs/research/career-trajectory-reaudit-phase13.md"
        assert args.output_json == "experiments/results/career_trajectory_reaudit.json"
        assert args.months_operational == 6.0
        assert args.min_span_months == 12.0
        assert args.min_longitudinal_records == 100
        assert not args.allow_synthetic
        assert not args.force_experiment
        assert args.seed == 42

    custom_args = [
        "run_career_trajectory_reaudit.py",
        "--months-operational",
        "18.0",
        "--min-span-months",
        "24.0",
        "--min-longitudinal-records",
        "250",
        "--force-experiment",
        "--allow-synthetic",
        "--seed",
        "99",
    ]
    with patch("sys.argv", custom_args):
        args = parse_args()
        assert args.months_operational == 18.0
        assert args.min_span_months == 24.0
        assert args.min_longitudinal_records == 250
        assert args.force_experiment
        assert args.allow_synthetic
        assert args.seed == 99


def test_champion_invariance_and_baseline_integrity() -> None:
    """Verify that Champion Rung F Level 2 Conformal CatBoost baseline remains unmodified."""
    from compintel.evaluation.career_trajectory_experiment import TrajectoryVariant

    # Baseline variant must be Rung F Level 2 Conformal CatBoost
    assert TrajectoryVariant.BASELINE_CHAMPION.value == "baseline_champion_l2"
    assert TrajectoryVariant.VARIANT_A_VELOCITY.value == "variant_a_career_velocity"
    assert TrajectoryVariant.VARIANT_B_TRAJECTORY_VECTOR.value == "variant_b_trajectory_vector"
