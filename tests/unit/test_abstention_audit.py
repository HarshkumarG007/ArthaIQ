"""Unit tests for Support Checks, Abstention Policy, and Disparity Audit (EXP-11).

Adheres to:
- Rule R-UQ-01: 95% bootstrap confidence intervals for abstention and coverage metrics.
- Rule R-UQ-02: Designed abstention semantics with explicit reason without guesses.
- Rule R-UQ-07 / Decision D-010: Decoupled Evidence Quality framework.
- Rule R-MD-01 / R-MD-03: Temporal and grouped dataset splitting.
- Rule R-MD-02: Final test set is strictly locked and isolated (dev split only).
- Rule R-MD-08 / R-EV-07: Slices with low support (N < 10) flagged (**FLAGGED (N < 10)**).
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
from scripts.audit_abstention import main as audit_abstention_main
from scripts.audit_abstention import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.abstention_audit import (
    AbstentionAuditEvaluator,
    AbstentionAuditReport,
    AbstentionTradeoffSummary,
    GroupAbstentionMetrics,
    _coverage_statistic,
    _diff_statistic,
    _rate_statistic,
    evaluate_and_save_abstention_audit,
)

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def synthetic_audit_df() -> pl.DataFrame:
    """Fixture providing 120 synthetic observations across diverse locations, roles, and dates."""
    n_rows = 120
    roles = ["SOFTWARE", "DATA", "MLAI"] * 40
    seniorities = ["JUNIOR", "MID", "SENIOR", "LEAD"] * 30
    locations = ["BANGALORE", "HYDERABAD", "PUNE", "DELHI_NCR", "MUMBAI", "CHENNAI"] * 20
    yoe = [float(i % 16) + 1.0 for i in range(n_rows)]
    base_dates = [datetime.date(2024, 1, 1) + datetime.timedelta(days=i * 3) for i in range(n_rows)]
    provenance = ["TIER_A", "TIER_B", "TIER_C"] * 40

    # Salaries with realistic variance
    salaries = [
        12.0 + (y * 2.5) + (8.0 if "LEAD" in s else 0.0)
        for y, s in zip(yoe, seniorities, strict=False)
    ]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "guaranteed_cash_annual": salaries,
            "person_cluster_id": [f"PCLUST-{i:03d}" for i in range(n_rows)],
            "employer_cluster_id": [f"ECLUST-{i % 8:02d}" for i in range(n_rows)],
            "provenance_tier": provenance,
            "is_synthetic": [True] * n_rows,
        }
    )


# -----------------------------------------------------------------------------
# 1. Statistical Helpers
# -----------------------------------------------------------------------------


def test_statistical_helpers() -> None:
    """Test bootstrap helper functions with normal and empty arrays."""
    # Coverage statistic
    arr = np.array([1.0, 0.0, 1.0, 1.0])
    assert abs(_coverage_statistic(arr) - 0.75) < 1e-6
    assert _coverage_statistic(np.array([])) == 0.0

    # Rate statistic
    assert abs(_rate_statistic(arr) - 0.75) < 1e-6
    assert _rate_statistic(np.array([])) == 0.0

    # Diff statistic
    diffs = np.array([2.0, -1.0, 5.0])
    assert abs(_diff_statistic(diffs) - 2.0) < 1e-6
    assert _diff_statistic(np.array([])) == 0.0


# -----------------------------------------------------------------------------
# 2. Dataclass Serialization and Markdown
# -----------------------------------------------------------------------------


def test_dataclasses_serialization_and_markdown() -> None:
    """Test to_dict() and to_markdown() across report dataclasses."""
    group_metric = GroupAbstentionMetrics(
        slice_dimension="role_family",
        slice_value="MLAI",
        total_requests=25,
        abstained_count=5,
        abstention_rate=20.0,
        abstention_rate_ci=(10.0, 32.0),
        answered_count=20,
        answered_rate=80.0,
        answered_coverage=85.0,
        answered_coverage_ci=(70.0, 95.0),
        unconstrained_coverage=80.0,
        unconstrained_coverage_ci=(65.0, 90.0),
        coverage_gain_pp=5.0,
        mean_answered_width_lpa=8.5,
        median_answered_width_lpa=8.2,
        grade_distribution={"GRADE_A": 15, "GRADE_B": 5, "ABSTAINED": 5},
        reason_distribution={"THIN_COHORT_SAMPLE": 5},
        is_flagged_low_support=False,
    )
    d = group_metric.to_dict()
    assert d["slice_value"] == "MLAI"
    assert d["is_flagged_low_support"] is False

    summary = AbstentionTradeoffSummary(
        total_requests=100,
        overall_abstained_count=15,
        overall_abstention_rate=15.0,
        overall_abstention_rate_ci=(9.0, 22.0),
        overall_answered_count=85,
        overall_answered_rate=85.0,
        overall_answered_coverage=82.4,
        overall_answered_coverage_ci=(74.0, 90.0),
        overall_unconstrained_coverage=78.0,
        overall_unconstrained_coverage_ci=(70.0, 85.0),
        coverage_gain_pp=4.4,
        max_location_disparity_pp=12.5,
        max_role_disparity_pp=8.0,
        max_seniority_disparity_pp=10.0,
        max_experience_disparity_pp=6.0,
        primary_abstention_reason="THIN_COHORT_SAMPLE",
        exp11_verdict="ACCEPTABLE_TRADEOFF",
        verdict_explanation=(
            "Abstention policy protects coverage without excessive demographic skew."
        ),
        support_threshold_recommendation="MAINTAIN_CURRENT_THRESHOLDS",
    )
    sd = summary.to_dict()
    assert sd["exp11_verdict"] == "ACCEPTABLE_TRADEOFF"

    flagged_metric = GroupAbstentionMetrics(
        slice_dimension="location",
        slice_value="KOLKATA",
        total_requests=6,
        abstained_count=6,
        abstention_rate=100.0,
        abstention_rate_ci=(100.0, 100.0),
        answered_count=0,
        answered_rate=0.0,
        answered_coverage=0.0,
        answered_coverage_ci=(0.0, 0.0),
        unconstrained_coverage=50.0,
        unconstrained_coverage_ci=(20.0, 80.0),
        coverage_gain_pp=-50.0,
        mean_answered_width_lpa=0.0,
        median_answered_width_lpa=0.0,
        grade_distribution={"ABSTAINED": 6},
        reason_distribution={"THIN_COHORT_SAMPLE": 6},
        is_flagged_low_support=True,
    )

    report = AbstentionAuditReport(
        run_id="test_run_001",
        evaluated_at_utc="2026-10-18T10:00:00Z",
        split_evaluated="select",
        total_observations=100,
        tradeoff_summary=summary,
        role_slices=[group_metric],
        seniority_slices=[group_metric],
        location_slices=[flagged_metric],
        experience_slices=[group_metric],
        provenance_slices=[group_metric],
    )

    rep_dict = report.to_dict()
    assert rep_dict["run_id"] == "test_run_001"
    assert len(rep_dict["location_slices"]) == 1

    md = report.to_markdown()
    assert "# ArthaIQ Compensation Intelligence -- Abstention & Coverage Audit (EXP-11)" in md
    assert "ACCEPTABLE_TRADEOFF" in md
    assert "MAINTAIN_CURRENT_THRESHOLDS" in md
    assert "**FLAGGED (N < 10)**" in md
    assert "KOLKATA" in md


# -----------------------------------------------------------------------------
# 3. Evaluator Isolation Guards & Validations
# -----------------------------------------------------------------------------


def test_synthetic_data_blocking(synthetic_audit_df: pl.DataFrame) -> None:
    """Test Rule R-MD-11: synthetic data without allow_synthetic=True is rejected."""
    evaluator = AbstentionAuditEvaluator()
    with pytest.raises(
        DataContractError, match="Synthetic data detected in canonical evaluation pool"
    ) as exc:
        evaluator.evaluate(synthetic_audit_df, allow_synthetic=False)
    assert exc.value.code == "SYNTHETIC_DATA_BLOCKED"


def test_locked_test_split_isolation(synthetic_audit_df: pl.DataFrame) -> None:
    """Test Rule R-MD-02: evaluating on 'test' partition is strictly rejected."""
    evaluator = AbstentionAuditEvaluator()
    with pytest.raises(
        DataContractError, match="Evaluation on 'test' partition is strictly forbidden"
    ) as exc:
        evaluator.evaluate(synthetic_audit_df, eval_split="test", allow_synthetic=True)
    assert exc.value.code == "FINAL_TEST_PARTITION_LOCKED"
    assert exc.value.details.get("rule_id") == "R-MD-02"


def test_missing_date_column_raises() -> None:
    """Test DataContractError when date column is absent."""
    df = pl.DataFrame(
        {
            "role_family": ["SOFTWARE", "DATA"],
            "seniority": ["MID", "SENIOR"],
            "location": ["BANGALORE", "PUNE"],
            "years_experience": [3.0, 5.0],
            "guaranteed_cash_annual": [20.0, 30.0],
            "is_synthetic": [False, False],
        }
    )
    evaluator = AbstentionAuditEvaluator()
    with pytest.raises(DataContractError, match="Missing date column"):
        evaluator.evaluate(df, allow_synthetic=True)


def test_missing_required_features_raises(synthetic_audit_df: pl.DataFrame) -> None:
    """Test CompIntelValidationError when required features are missing."""
    df_missing = synthetic_audit_df.drop("role_family")
    evaluator = AbstentionAuditEvaluator()
    with pytest.raises(
        CompIntelValidationError, match="Evaluation dataframe missing required columns"
    ):
        evaluator.evaluate(df_missing, allow_synthetic=True)


# -----------------------------------------------------------------------------
# 4. End-to-End Evaluation & Hypothesis EXP-11 Verifications
# -----------------------------------------------------------------------------


def test_end_to_end_evaluation(synthetic_audit_df: pl.DataFrame) -> None:
    """Test complete end-to-end evaluation with fast bootstrap resamples."""
    evaluator = AbstentionAuditEvaluator(
        n_bootstrap=50,
        random_seed=42,
    )
    report = evaluator.evaluate(
        synthetic_audit_df,
        eval_split="select",
        allow_synthetic=True,
    )

    assert isinstance(report, AbstentionAuditReport)
    assert report.total_observations > 0
    assert report.split_evaluated == "select"

    summary = report.tradeoff_summary
    assert summary.total_requests == report.total_observations
    assert (
        summary.overall_abstained_count + summary.overall_answered_count == summary.total_requests
    )
    assert 0.0 <= summary.overall_abstention_rate <= 100.0
    assert summary.exp11_verdict in [
        "ACCEPTABLE_TRADEOFF",
        "INSUFFICIENT_COVERAGE_GAIN",
        "EXCESSIVE_DISPARITY",
    ]

    # Verify slices
    assert len(report.role_slices) > 0
    assert len(report.seniority_slices) > 0
    assert len(report.location_slices) > 0
    assert len(report.experience_slices) > 0
    assert len(report.provenance_slices) > 0

    # Verify low-support flagging rule R-MD-08 / R-EV-07
    for slice_list in [
        report.role_slices,
        report.seniority_slices,
        report.location_slices,
        report.experience_slices,
        report.provenance_slices,
    ]:
        for s in slice_list:
            if s.total_requests < 10:
                assert s.is_flagged_low_support is True
            else:
                assert s.is_flagged_low_support is False


def test_exp11_verdict_branches() -> None:
    """Test all branches of hypothesis EXP-11 verdict logic."""
    evaluator = AbstentionAuditEvaluator(n_bootstrap=50, random_seed=42)

    # Base slice helper
    def make_slice(val: str, rate: float, n: int = 20) -> GroupAbstentionMetrics:
        return GroupAbstentionMetrics(
            slice_dimension="location",
            slice_value=val,
            total_requests=n,
            abstained_count=int(n * rate / 100.0),
            abstention_rate=rate,
            abstention_rate_ci=(rate - 2.0, rate + 2.0),
            answered_count=n - int(n * rate / 100.0),
            answered_rate=100.0 - rate,
            answered_coverage=85.0,
            answered_coverage_ci=(75.0, 95.0),
            unconstrained_coverage=80.0,
            unconstrained_coverage_ci=(70.0, 90.0),
            coverage_gain_pp=5.0,
            mean_answered_width_lpa=6.0,
            median_answered_width_lpa=5.8,
            grade_distribution={"GRADE_A": 15, "ABSTAINED": 5},
            reason_distribution={"THIN_COHORT_SAMPLE": 5},
            is_flagged_low_support=False,
        )

    # Case 1: ACCEPTABLE_TRADEOFF (gain > 0, disparity <= 25 pp)
    df1 = pl.DataFrame(
        {
            "is_abstained": [False] * 80 + [True] * 20,
            "covered_unconstrained": [True] * 75 + [False] * 5 + [False] * 20,
            "width": [5.0] * 100,
            "evidence_grade": ["GRADE_A"] * 80 + ["ABSTAINED"] * 20,
            "primary_reason": ["NONE"] * 80 + ["THIN_COHORT_SAMPLE"] * 20,
        }
    )
    slices_normal = [make_slice("BLR", 10.0), make_slice("HYD", 20.0)]
    res1 = evaluator._compute_tradeoff_summary(
        df=df1,
        location_slices=slices_normal,
        role_slices=slices_normal,
        seniority_slices=slices_normal,
        experience_slices=slices_normal,
    )
    assert res1.exp11_verdict == "ACCEPTABLE_TRADEOFF"
    assert "MAINTAIN_CURRENT_THRESHOLDS" in res1.support_threshold_recommendation

    # Case 2: INSUFFICIENT_COVERAGE_GAIN (gain < 0)
    df2 = pl.DataFrame(
        {
            "is_abstained": [False] * 80 + [True] * 20,
            "covered_unconstrained": [True] * 50 + [False] * 30 + [True] * 20,
            "width": [5.0] * 100,
            "evidence_grade": ["GRADE_A"] * 80 + ["ABSTAINED"] * 20,
            "primary_reason": ["NONE"] * 80 + ["THIN_COHORT_SAMPLE"] * 20,
        }
    )
    res2 = evaluator._compute_tradeoff_summary(
        df=df2,
        location_slices=slices_normal,
        role_slices=slices_normal,
        seniority_slices=slices_normal,
        experience_slices=slices_normal,
    )
    assert res2.exp11_verdict == "INSUFFICIENT_COVERAGE_GAIN"
    assert "CALIBRATE_CONFORMAL_WIDTHS" in res2.support_threshold_recommendation

    # Case 3: EXCESSIVE_DISPARITY (disparity > 25 pp)
    slices_skewed = [make_slice("BLR", 5.0), make_slice("KOLKATA", 35.0)]
    res3 = evaluator._compute_tradeoff_summary(
        df=df1,
        location_slices=slices_skewed,
        role_slices=slices_normal,
        seniority_slices=slices_normal,
        experience_slices=slices_normal,
    )
    assert res3.exp11_verdict == "EXCESSIVE_DISPARITY"
    assert "ADAPT_HIERARCHICAL_PARTIAL_POOLING" in res3.support_threshold_recommendation


def test_slice_metrics_edge_cases() -> None:
    """Test slice metrics calculation with zero answered items and low support flagging."""
    evaluator = AbstentionAuditEvaluator(n_bootstrap=50, random_seed=42)

    df_slice = pl.DataFrame(
        {
            "location": ["REMOTE_ISLAND", "BANGALORE"],
            "is_abstained": [True, False],
            "covered_unconstrained": [False, True],
            "width": [5.0, 4.0],
            "evidence_grade": ["ABSTAINED", "GRADE_A"],
            "primary_reason": ["EXTREME_EXPERIENCE_OUTLIER", "NONE"],
        }
    )

    metrics_list = evaluator._compute_slice_metrics(df_slice, "location")
    assert len(metrics_list) == 2

    by_val = {m.slice_value: m for m in metrics_list}
    island = by_val["REMOTE_ISLAND"]
    assert island.total_requests == 1
    assert island.abstained_count == 1
    assert island.answered_count == 0
    assert island.answered_coverage == 0.0
    assert island.is_flagged_low_support is True

    blr = by_val["BANGALORE"]
    assert blr.total_requests == 1
    assert blr.abstained_count == 0
    assert blr.answered_count == 1
    assert blr.answered_coverage == 100.0
    assert blr.is_flagged_low_support is True


# -----------------------------------------------------------------------------
# 5. evaluate_and_save_abstention_audit & Runner CLI
# -----------------------------------------------------------------------------


def test_evaluate_and_save_abstention_audit(
    tmp_path: Path, synthetic_audit_df: pl.DataFrame
) -> None:
    """Test saving Markdown and JSON artifacts from audit function."""
    parquet_path = tmp_path / "canonical.parquet"
    synthetic_audit_df.write_parquet(parquet_path)

    out_md = tmp_path / "audit_report.md"
    out_json = tmp_path / "audit_report.json"

    # Non-existent path raises CompIntelValidationError
    with pytest.raises(CompIntelValidationError, match="Canonical dataset not found"):
        evaluate_and_save_abstention_audit(
            canonical_path=str(tmp_path / "non_existent.parquet"),
        )

    # Valid run
    rep = evaluate_and_save_abstention_audit(
        canonical_path=str(parquet_path),
        output_md=str(out_md),
        output_json=str(out_json),
        eval_split="select",
        n_bootstrap=50,
        seed=42,
        allow_synthetic=True,
    )
    assert isinstance(rep, AbstentionAuditReport)
    assert out_md.exists()
    assert out_json.exists()

    md_text = out_md.read_text(encoding="utf-8")
    assert "# ArthaIQ Compensation Intelligence -- Abstention & Coverage Audit (EXP-11)" in md_text
    assert "Overall Abstention Rate" in md_text

    json_dict = json.loads(out_json.read_text(encoding="utf-8"))
    assert "tradeoff_summary" in json_dict
    assert "role_slices" in json_dict


def test_cli_runner_success(tmp_path: Path, synthetic_audit_df: pl.DataFrame) -> None:
    """Test CLI script execution successfully returns 0 and writes outputs."""
    parquet_path = tmp_path / "canonical.parquet"
    synthetic_audit_df.write_parquet(parquet_path)

    out_md = tmp_path / "cli_audit.md"
    out_json = tmp_path / "cli_audit.json"

    test_args = [
        "audit_abstention.py",
        "--canonical-path",
        str(parquet_path),
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
        ret_code = audit_abstention_main()

    assert ret_code == 0
    assert out_md.exists()
    assert out_json.exists()


def test_cli_runner_compintel_error(tmp_path: Path) -> None:
    """Test CLI script exits with code 1 upon CompIntelError."""
    test_args = [
        "audit_abstention.py",
        "--canonical-path",
        str(tmp_path / "missing.parquet"),
    ]
    with patch.object(sys, "argv", test_args):
        ret_code = audit_abstention_main()
    assert ret_code == 1


def test_cli_runner_fatal_error() -> None:
    """Test CLI script exits with code 2 upon unexpected Exception."""
    with (
        patch(
            "scripts.audit_abstention.evaluate_and_save_abstention_audit",
            side_effect=RuntimeError("Unexpected OS fatal error"),
        ),
        patch.object(sys, "argv", ["audit_abstention.py"]),
    ):
        ret_code = audit_abstention_main()
    assert ret_code == 2


def test_cli_parse_args() -> None:
    """Test default argument parsing in CLI script."""
    with patch.object(sys, "argv", ["audit_abstention.py"]):
        args = parse_args()
    assert args.canonical_path == "data/canonical/canonical_observations.parquet"
    assert args.output_md == "experiments/results/abstention_audit_v1.md"
    assert args.output_json == "experiments/results/abstention_audit_v1.json"
    assert args.split == "select"
    assert args.n_bootstrap == 1000
    assert args.seed == 42
    assert args.allow_synthetic is False
