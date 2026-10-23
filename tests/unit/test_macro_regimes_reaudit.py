"""Unit tests for EXP-MACRO-01r: Macro Regime Features Long-Range Calendar Trigger
(Phase 13, Task T13.06).

Tests:
1. Audit of longitudinal panel span and calendar window on cumulative non-synthetic panel.
2. Threshold qualification logic (calendar span >= 24.0 months, 730 days).
3. Calendar trigger detection (pre-registered October 2028 trigger date).
4. Synthetic data quarantine isolation guard under Rule R-MD-11 (SYNTHETIC_DATA_BLOCKED).
5. Missing macro reference series detection (cpi_urban_monthly, inr_usd_fx_daily).
6. Input validation error handling for invalid threshold arguments.
7. Default re-audit execution: Gate 1 DEFER verdict with empirical modeling held in abeyance.
8. Forced empirical modeling execution: runs baseline CatBoost vs Variant A and Variant B.
9. Report serialization to structured dictionary and publication-grade Markdown rendering.
10. Persistence and file emission via evaluate_and_save_macro_regimes_reaudit.
11. CLI runner argument parsing via scripts/run_macro_regimes_reaudit.py.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest
from scripts.run_macro_regimes_reaudit import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.employer_graph_reaudit import build_post_exp16_cumulative_panel
from compintel.evaluation.macro_regimes_reaudit import (
    CALENDAR_TRIGGER_DATE,
    MacroAuditStatus,
    MacroReauditVerdict,
    audit_macro_panel_sufficiency,
    evaluate_and_save_macro_regimes_reaudit,
    run_macro_regimes_reaudit,
)


@pytest.fixture
def cumulative_panel() -> pl.DataFrame:
    """Build standard 6-month non-synthetic cumulative production panel."""
    return build_post_exp16_cumulative_panel(months_operational=6.0, seed=42)


@pytest.fixture
def sample_macro_dir(tmp_path: Path) -> Path:
    """Create a self-contained macro directory with valid CPI and FX series (Rule R-DA-08)."""
    macro_dir = tmp_path / "macro"
    macro_dir.mkdir(parents=True, exist_ok=True)

    manifest_yaml = """source_id: SRC-SUP-MAC-01
source_short_name: RBI DBIE Macro Series
licence_id: OGDL-IN
licence_name: Open Government Data License - India
licence_status: approved
sqs: 94.4
sqsf_tier: TIER_4_SUPPLEMENTARY
generated_at_utc: '2026-10-13T19:08:54.696306+00:00'
immutable: true
"""
    (macro_dir / "manifest.yaml").write_text(manifest_yaml, encoding="utf-8")

    # 1. Generate monthly CPI from 1958 to 2028 (covering all historical and forward test dates)
    cpi_rows = ["observation_date,INDCPIALLMINMEI", "1958-01-01,1.50"]
    curr = date(2020, 1, 1)
    end_cpi = date(2028, 12, 1)
    cpi_val = 150.0
    while curr <= end_cpi:
        cpi_rows.append(f"{curr.isoformat()},{cpi_val:.2f}")
        year = curr.year + (curr.month // 12)
        month = (curr.month % 12) + 1
        curr = date(year, month, 1)
        cpi_val += 0.50

    (macro_dir / "cpi_urban_monthly.csv").write_text("\n".join(cpi_rows) + "\n", encoding="utf-8")

    # 2. Generate daily FX rates from 1973 to 2028
    fx_rows = ["observation_date,DEXINUS", "1973-01-02,8.02"]
    curr_fx = date(2020, 1, 1)
    end_fx = date(2028, 12, 1)
    fx_val = 82.50
    while curr_fx <= end_fx:
        if curr_fx.weekday() < 5:  # Monday - Friday trading days
            fx_rows.append(f"{curr_fx.isoformat()},{fx_val:.2f}")
            fx_val = round(fx_val + 0.002, 4)
        curr_fx += timedelta(days=1)

    (macro_dir / "inr_usd_fx_daily.csv").write_text("\n".join(fx_rows) + "\n", encoding="utf-8")
    return macro_dir


@pytest.fixture
def macro_data_dir(sample_macro_dir: Path) -> Path:
    """Return local raw macro dir if acquired; otherwise self-contained fixture (Rule R-DA-08)."""
    raw_dir = Path("data/raw/SRC-SUP-MAC-01")
    if not raw_dir.is_absolute() and not raw_dir.exists():
        repo_root = Path(__file__).resolve().parents[2]
        candidate = repo_root / raw_dir
        if candidate.exists():
            raw_dir = candidate

    if (raw_dir / "cpi_urban_monthly.csv").exists() and (raw_dir / "inr_usd_fx_daily.csv").exists():
        return raw_dir
    return sample_macro_dir


def test_audit_macro_panel_sufficiency_current_panel(
    cumulative_panel: pl.DataFrame, macro_data_dir: Path
) -> None:
    """Verify panel span and macro availability on the live 6-month production panel."""
    metrics = audit_macro_panel_sufficiency(
        df=cumulative_panel,
        macro_dir=macro_data_dir,
        min_span_months=24.0,
    )

    assert metrics.total_records == 219
    assert metrics.non_synthetic_records == 219
    assert metrics.synthetic_records == 0
    assert 170 <= metrics.panel_span_days <= 185
    assert 5.5 <= metrics.panel_span_months <= 6.5
    assert metrics.required_span_months == 24.0
    assert not metrics.is_span_sufficient
    assert metrics.span_deficit_months > 17.0
    assert metrics.span_deficit_days > 500
    assert not metrics.calendar_trigger_met
    assert metrics.cpi_series_present
    assert metrics.cpi_series_rows > 0
    assert metrics.fx_series_present
    assert metrics.fx_series_rows > 0
    assert metrics.license_id == "OGDL-IN"
    assert metrics.provenance_tier == "TIER_4_SUPPLEMENTARY"
    if "SRC-SUP-MAC-01" in str(macro_data_dir):
        assert metrics.cpi_series_rows == 819
        assert metrics.fx_series_rows == 14024


def test_audit_macro_panel_sufficiency_sufficient_span() -> None:
    """Verify panel span audit when longitudinal panel spans >= 24 calendar months."""
    start_date = date(2024, 6, 1)
    end_date = date(2026, 7, 1)  # ~25 months = 760 days

    records = [
        {
            "observation_id": f"OBS-SPAN-{i:03d}",
            "is_synthetic": False,
            "as_of_date": start_date + timedelta(days=int(i * 6)),
        }
        for i in range(130)
    ]
    records[-1]["as_of_date"] = end_date
    df = pl.DataFrame(records)

    metrics = audit_macro_panel_sufficiency(
        df=df,
        min_span_months=24.0,
    )

    assert metrics.total_records == 130
    assert metrics.non_synthetic_records == 130
    assert metrics.panel_span_months >= 24.0
    assert metrics.is_span_sufficient
    assert metrics.span_deficit_months == 0.0
    assert metrics.span_deficit_days == 0


def test_calendar_trigger_detection(cumulative_panel: pl.DataFrame) -> None:
    """Verify arrival detection for the pre-registered October 2028 calendar date."""
    # Date before trigger
    metrics_early = audit_macro_panel_sufficiency(
        df=cumulative_panel,
        reference_date=date(2026, 10, 23),
    )
    assert not metrics_early.calendar_trigger_met

    # Date exactly on trigger
    metrics_trigger = audit_macro_panel_sufficiency(
        df=cumulative_panel,
        reference_date=date(2028, 10, 1),
    )
    assert metrics_trigger.calendar_trigger_met

    # Date after trigger
    metrics_post = audit_macro_panel_sufficiency(
        df=cumulative_panel,
        reference_date=date(2028, 11, 15),
    )
    assert metrics_post.calendar_trigger_met


def test_audit_validation_errors(cumulative_panel: pl.DataFrame) -> None:
    """Verify input validation errors for non-positive threshold arguments."""
    with pytest.raises(CompIntelValidationError, match="min_span_months must be positive"):
        audit_macro_panel_sufficiency(df=cumulative_panel, min_span_months=0.0)

    with pytest.raises(CompIntelValidationError, match="min_span_months must be positive"):
        audit_macro_panel_sufficiency(df=cumulative_panel, min_span_months=-12.0)


def test_synthetic_data_quarantine_guard(
    cumulative_panel: pl.DataFrame, macro_data_dir: Path
) -> None:
    """Verify strict synthetic data isolation under Rule R-MD-11."""
    synthetic_row = cumulative_panel.slice(0, 1).with_columns(
        pl.lit(True).alias("is_synthetic"),
        pl.lit("OBS-SYNTH-LEAK").alias("observation_id"),
    )
    contaminated_panel = pl.concat([cumulative_panel, synthetic_row])

    with pytest.raises(DataContractError) as exc_info:
        run_macro_regimes_reaudit(contaminated_panel, allow_synthetic=False)

    assert exc_info.value.code == "SYNTHETIC_DATA_BLOCKED"
    assert exc_info.value.details.get("rule_id") == "R-MD-11"

    # Permitted when explicit override is provided
    report = run_macro_regimes_reaudit(
        contaminated_panel,
        allow_synthetic=True,
        macro_dir=macro_data_dir,
    )
    assert report.panel_metrics.synthetic_records == 1


def test_missing_macro_series_detection(cumulative_panel: pl.DataFrame, tmp_path: Path) -> None:
    """Verify graceful handling when macro data directory is missing files."""
    empty_dir = tmp_path / "empty_macro"
    empty_dir.mkdir()

    report = run_macro_regimes_reaudit(
        panel_df=cumulative_panel,
        macro_dir=empty_dir,
    )

    assert report.audit_status == MacroAuditStatus.MISSING_MACRO_SERIES
    assert report.verdict == MacroReauditVerdict.DEFER
    assert not report.panel_metrics.cpi_series_present
    assert not report.panel_metrics.fx_series_present


def test_run_macro_regimes_reaudit_default_defer(
    cumulative_panel: pl.DataFrame, macro_data_dir: Path
) -> None:
    """Verify default Gate 1 DEFER verdict on the 6-month post-EXP-16 production panel."""
    report = run_macro_regimes_reaudit(
        panel_df=cumulative_panel,
        macro_dir=macro_data_dir,
        allow_synthetic=False,
        force_experiment=False,
        seed=42,
    )

    assert report.charter_id == "CHARTER-MACRO-REGIMES-r"
    assert report.experiment_id == "EXP-MACRO-01r"
    assert report.task_id == "T13.06"
    assert report.audit_status == MacroAuditStatus.INSUFFICIENT_SPAN_DEFER
    assert report.verdict == MacroReauditVerdict.DEFER
    assert report.model_evaluation is None
    assert "RETAINED_UNMODIFIED" in report.champion_status
    assert report.next_trigger_date == CALENDAR_TRIGGER_DATE
    assert "24.0 calendar months" in report.next_trigger_condition
    assert "Gate 1 Longitudinal Feasibility DEFERRED" in report.executive_summary


def test_run_macro_regimes_reaudit_force_experiment(
    cumulative_panel: pl.DataFrame, macro_data_dir: Path
) -> None:
    """Verify forced empirical modeling execution on cumulative panel."""
    report = run_macro_regimes_reaudit(
        panel_df=cumulative_panel,
        macro_dir=macro_data_dir,
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


def test_report_serialization_and_markdown(
    cumulative_panel: pl.DataFrame, macro_data_dir: Path
) -> None:
    """Verify report serialization to JSON dictionary and publication-grade Markdown."""
    report = run_macro_regimes_reaudit(
        panel_df=cumulative_panel,
        macro_dir=macro_data_dir,
        allow_synthetic=False,
        force_experiment=False,
        seed=42,
    )

    # 1. Dictionary serialization
    d = report.to_dict()
    assert d["charter_id"] == "CHARTER-MACRO-REGIMES-r"
    assert d["experiment_id"] == "EXP-MACRO-01r"
    assert d["audit_status"] == "INSUFFICIENT_SPAN_DEFER"
    assert d["verdict"] == "DEFER"
    assert d["panel_metrics"]["total_records"] == 219
    assert d["panel_metrics"]["span_deficit_days"] > 500

    json_str = json.dumps(d)
    assert len(json_str) > 0

    # 2. Markdown memo rendering
    md = report.to_markdown()
    assert "# Macro Regime Features Long-Range Calendar Trigger" in md
    assert "CHARTER-MACRO-REGIMES-r" in md
    assert "## 1. Executive Summary & Governance Verdict" in md
    assert "## 2. Gate 1: Longitudinal Panel Span & Calendar Window Audit" in md
    assert "## 3. Macroeconomic Indicator Series Availability & Point-In-Time Integrity" in md
    assert "## 4. Real-Pay Deflation & Conformal Inverse Re-Inflation Pipeline" in md
    assert "## 5. Macro Regime Feature Join Architecture & Publication Lag Policy" in md
    assert "## 6. Empirical Modeling Status" in md
    assert "## 7. Production Champion Retention & Phase 13 Architectural Impact" in md
    assert "2028-10-01" in md
    assert f"{report.panel_metrics.cpi_series_rows:,} monthly rows" in md
    assert f"{report.panel_metrics.fx_series_rows:,} daily rows" in md
    if "SRC-SUP-MAC-01" in str(macro_data_dir):
        assert "819 monthly rows" in md
        assert "14,024 daily rows" in md


def test_evaluate_and_save_macro_regimes_reaudit_tmp_path(
    cumulative_panel: pl.DataFrame, macro_data_dir: Path, tmp_path: Path
) -> None:
    """Verify persistence of Markdown memo and JSON report to disk."""
    out_dir = tmp_path / "results"
    md_file = tmp_path / "docs" / "macro-memo.md"

    report = evaluate_and_save_macro_regimes_reaudit(
        output_dir=out_dir,
        macro_dir=macro_data_dir,
        min_span_months=24.0,
        allow_synthetic=False,
        force_experiment=False,
        report_filename="macro_reaudit_test.json",
        md_filename=str(md_file),
    )

    assert report.verdict == MacroReauditVerdict.DEFER
    saved_json = out_dir / "macro_reaudit_test.json"
    assert saved_json.is_file()
    assert md_file.is_file()

    saved_data = json.loads(saved_json.read_text(encoding="utf-8"))
    assert saved_data["experiment_id"] == "EXP-MACRO-01r"
    assert saved_data["verdict"] == "DEFER"

    saved_md = md_file.read_text(encoding="utf-8")
    assert "# Macro Regime Features Long-Range Calendar Trigger" in saved_md


def test_cli_runner_parse_args() -> None:
    """Verify argument parsing in scripts/run_macro_regimes_reaudit.py."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "sys.argv",
            [
                "run_macro_regimes_reaudit.py",
                "--months-operational",
                "12.0",
                "--min-span-months",
                "24.0",
                "--allow-synthetic",
                "--force-experiment",
                "--seed",
                "123",
            ],
        )
        args = parse_args()
        assert args.months_operational == 12.0
        assert args.min_span_months == 24.0
        assert args.allow_synthetic is True
        assert args.force_experiment is True
        assert args.seed == 123
