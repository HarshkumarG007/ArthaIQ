"""Unit tests for EXP-09r: Skills TF-IDF Power-Gated Retest (Phase 13, Task T13.03).

Tests:
1. Mathematical precision of paired t-power sample size and achieved power calculations.
2. Empirical power curve generation across standard evaluation grids.
3. Non-synthetic observation panel verification under Rule R-MD-11.
4. Gate 1 power audit: underpowered panel triggers UNDERPOWERED_DEFER.
5. Gate 1 power audit: adequately powered panel passes SUFFICIENT_POWER.
6. Synthetic data quarantine guard under Rule R-MD-11 (SYNTHETIC_DATA_BLOCKED).
7. End-to-end default re-audit execution: Gate 1 power-gated DEFER without empirical modeling.
8. End-to-end forced empirical modeling: executes CatBoost vs TF-IDF SVD on cumulative panel.
9. Report serialization to structured dictionary and publication-grade Markdown rendering.
10. Persistence and CLI runner execution via scripts/run_skills_reaudit.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
from scripts.run_skills_reaudit import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.employer_graph_reaudit import build_post_exp16_cumulative_panel
from compintel.evaluation.skills_reaudit import (
    PowerAuditStatus,
    SkillsReauditVerdict,
    audit_skills_feasibility,
    calculate_achieved_power,
    calculate_required_sample_size,
    evaluate_and_save_skills_reaudit,
    generate_power_curve,
    run_skills_reaudit,
)


@pytest.fixture
def cumulative_panel() -> pl.DataFrame:
    """Build standard 6-month non-synthetic cumulative production panel."""
    return build_post_exp16_cumulative_panel(months_operational=6.0, seed=42)


def test_power_calculation_formulas() -> None:
    """Verify paired difference power calculation formulas and edge cases."""
    # Pre-registered values: delta = -0.050 LPA, sigma = 0.40 LPA, alpha = 0.05, power = 0.80
    n_req = calculate_required_sample_size(
        effect_size=-0.050,
        std_dev=0.40,
        alpha=0.05,
        power=0.80,
    )
    # Exact mathematical formula: ((1.96 + 0.8416) * 0.40 / 0.05) ** 2 = 502.3 -> ceil = 503
    assert 500 <= n_req <= 505

    # Test edge cases
    with pytest.raises(CompIntelValidationError):
        calculate_required_sample_size(effect_size=0.0)

    with pytest.raises(CompIntelValidationError):
        calculate_required_sample_size(std_dev=-0.5)

    # Achieved power at N = 219 (current panel)
    p_219 = calculate_achieved_power(219, effect_size=-0.050, std_dev=0.40, alpha=0.05)
    assert 0.44 <= p_219 <= 0.47  # ~45.6% power

    # Achieved power at N = 500 (target trigger)
    p_500 = calculate_achieved_power(500, effect_size=-0.050, std_dev=0.40, alpha=0.05)
    assert 0.79 <= p_500 <= 0.81  # ~80.0% power

    # Edge cases for power
    assert calculate_achieved_power(0) == 0.0
    assert calculate_achieved_power(1) == 0.0
    assert calculate_achieved_power(100, std_dev=0.0) == 0.0


def test_generate_power_curve() -> None:
    """Verify empirical power curve trajectory generator."""
    sample_sizes = [50, 100, 219, 500, 1000]
    curve = generate_power_curve(
        effect_size=-0.050,
        std_dev=0.40,
        alpha=0.05,
        sample_sizes=sample_sizes,
    )
    assert len(curve) == 5
    # Verify monotonic increasing power
    powers = [pt["power"] for pt in curve]
    assert powers == sorted(powers)
    assert powers[0] < 0.20
    assert powers[-1] > 0.95


def test_non_synthetic_verification(cumulative_panel: pl.DataFrame) -> None:
    """Rule R-MD-11: 100% of observations must be verified non-synthetic."""
    assert len(cumulative_panel) == 219
    assert "is_synthetic" in cumulative_panel.columns
    assert not cumulative_panel["is_synthetic"].any()
    assert (cumulative_panel["is_synthetic"] == False).all()  # noqa: E712


def test_gate1_audit_underpowered_defer(cumulative_panel: pl.DataFrame) -> None:
    """Gate 1: Audit triggers UNDERPOWERED_DEFER when non-synthetic panel size N < 500."""
    audit = audit_skills_feasibility(cumulative_panel, min_required_records=500)
    assert audit.status == PowerAuditStatus.UNDERPOWERED_DEFER
    assert audit.n_total_records == 219
    assert audit.n_non_synthetic == 219
    assert not audit.is_synthetic
    assert audit.power_metrics.required_sample_size == 500
    assert audit.power_metrics.current_sample_size == 219
    assert audit.power_metrics.sample_size_deficit == 281
    assert 0.44 <= audit.power_metrics.achieved_power <= 0.47
    assert "Gate 1 feasibility deferred" in audit.summary


def test_gate1_audit_sufficient_power(cumulative_panel: pl.DataFrame) -> None:
    """Gate 1: Audit passes SUFFICIENT_POWER when non-synthetic panel size N >= 500."""
    # Create large panel by concatenating
    large_panel = pl.concat([cumulative_panel, cumulative_panel, cumulative_panel])
    assert len(large_panel) >= 500

    audit = audit_skills_feasibility(large_panel, min_required_records=500)
    assert audit.status == PowerAuditStatus.SUFFICIENT_POWER
    assert audit.n_non_synthetic >= 500
    assert audit.power_metrics.sample_size_deficit == 0
    assert audit.power_metrics.achieved_power >= 0.80
    assert "Gate 1 feasibility passed" in audit.summary


def test_synthetic_data_quarantine_guard(cumulative_panel: pl.DataFrame) -> None:
    """Rule R-MD-11: Synthetic data must be quarantined and blocked from Gate 1 power audit."""
    synth_df = cumulative_panel.with_columns(pl.lit(True).alias("is_synthetic"))
    audit = audit_skills_feasibility(synth_df, min_required_records=500, allow_synthetic=False)
    assert audit.status == PowerAuditStatus.SYNTHETIC_DATA_BLOCKED
    assert audit.is_synthetic
    assert "blocked under Rule R-MD-11" in audit.summary

    # End-to-end re-audit must raise DataContractError
    with pytest.raises(DataContractError) as exc_info:
        run_skills_reaudit(custom_df=synth_df, min_required_records=500, allow_synthetic=False)
    assert "DATA_CONTRACT_VIOLATION" in str(exc_info.value)


def test_end_to_end_reaudit_defer_without_modeling(cumulative_panel: pl.DataFrame) -> None:
    """Verify standard EXP-09r execution: Gate 1 DEFER strictly preserves Champion CatBoost."""
    report = run_skills_reaudit(
        custom_df=cumulative_panel,
        min_required_records=500,
        seed=42,
    )

    assert report.charter_id == "CHARTER-EXP-09r"
    assert report.task_id == "T13.03"
    assert report.n_total_observations == 219
    assert report.n_non_synthetic == 219
    assert not report.gate1_passed
    assert not report.modeling_executed
    assert report.variant_a_verdict == SkillsReauditVerdict.DEFER
    assert report.variant_b_verdict == SkillsReauditVerdict.REJECT
    assert report.overall_verdict == SkillsReauditVerdict.DEFER
    assert report.champion_status == "RETAINED_UNMODIFIED"
    assert report.baseline_metrics is None
    assert report.variant_a_metrics is None
    assert report.variant_b_metrics is None
    assert report.paired_difference_variant_a is None
    assert "2027" in report.next_scheduled_audit_date
    assert "N >= 500" in report.next_audit_trigger_condition


def test_end_to_end_reaudit_forced_modeling(cumulative_panel: pl.DataFrame) -> None:
    """Verify forced empirical modeling on cumulative panel."""
    report = run_skills_reaudit(
        custom_df=cumulative_panel,
        min_required_records=500,
        force_modeling=True,
        n_resamples=50,
        seed=42,
    )

    assert not report.gate1_passed  # N < 500
    assert report.modeling_executed  # Forced
    assert report.baseline_metrics is not None
    assert report.variant_a_metrics is not None
    assert report.variant_b_metrics is not None
    assert report.paired_difference_variant_a is not None

    # Check metrics structure
    assert report.baseline_metrics.mae > 0.0
    assert report.baseline_metrics.mean_pinball_loss > 0.0
    assert report.variant_a_metrics.n_features > report.baseline_metrics.n_features
    assert report.variant_b_verdict == SkillsReauditVerdict.REJECT

    # Quantile crossing check (Rule R-UQ-05)
    assert report.baseline_metrics.crossing_rate == 0.0
    assert report.variant_a_metrics.crossing_rate == 0.0


def test_report_serialization_and_markdown(cumulative_panel: pl.DataFrame) -> None:
    """Verify report dictionary serialization and Markdown rendering with zero lone numbers."""
    report = run_skills_reaudit(
        custom_df=cumulative_panel,
        min_required_records=500,
        seed=42,
    )

    d = report.to_dict()
    assert d["charter_id"] == "CHARTER-EXP-09r"
    assert d["overall_verdict"] == "DEFER"
    assert d["feasibility_audit"]["power_metrics"]["achieved_power"] > 0.40

    # Ensure JSON serializable
    json_str = json.dumps(d)
    assert len(json_str) > 100

    md = report.to_markdown()
    assert "# Skills TF-IDF Power-Gated Retest" in md
    assert "CHARTER-EXP-09r" in md
    assert "UNDERPOWERED_DEFER" in md
    assert "219" in md
    assert "500" in md
    assert "45.6%" in md
    assert "RETAINED_UNMODIFIED" in md
    assert "Variant B: Sentence-Transformer Embeddings (CPU) Architecture Rejection" in md


def test_evaluate_and_save_skills_reaudit(tmp_path: Path, cumulative_panel: pl.DataFrame) -> None:
    """Verify artifact saving to disk."""
    out_md = tmp_path / "skills-reaudit-test.md"
    out_json = tmp_path / "skills-reaudit-test.json"

    rep = evaluate_and_save_skills_reaudit(
        output_md=out_md,
        output_json=out_json,
        custom_df=cumulative_panel,
        min_required_records=500,
        seed=42,
    )

    assert out_md.exists()
    assert out_json.exists()
    assert out_md.stat().st_size > 500
    assert out_json.stat().st_size > 500

    with open(out_json, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["report_id"] == rep.report_id


def test_cli_argument_parsing() -> None:
    """Verify CLI argument defaults and custom values."""
    with patch(
        "sys.argv", ["scripts/run_skills_reaudit.py", "--min-records", "600", "--force-modeling"]
    ):
        args = parse_args()
        assert args.min_records == 600
        assert args.force_modeling is True
        assert args.allow_synthetic is False
