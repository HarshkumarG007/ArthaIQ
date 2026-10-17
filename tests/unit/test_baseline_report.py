"""Unit tests for baseline evaluation reporting engine (Task T4.08, Rule R-MD-05).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal dataset splitting.
- Rule R-MD-02: Isolated final test set; evaluating on 'test' split is strictly prohibited.
- Rule R-MD-05: Mandatory baseline evaluation metrics with bootstrap intervals and slices.
- Rule R-MD-08: Thin-evidence abstention reporting.
- Rule R-MD-11: Synthetic data blocked by default; highlighted with cautionary banner when allowed.
- Rule R-TS-01 & R-TS-03: >= 90% test coverage floor.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest
from tests.fixtures.synthetic import generate_synthetic_observations_df

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.baseline_report import (
    BaselineReport,
    BaselineReportConfig,
    BaselineReportGenerator,
    add_experience_band_column,
    run_baseline_evaluation_report,
)


@pytest.fixture
def repo_root() -> Path:
    """Return repository root path."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def rich_synthetic_df() -> pl.DataFrame:
    """Generate deterministic synthetic cohort with diverse roles, seniorities, and dates."""
    df = generate_synthetic_observations_df(n_records=100, seed=42)
    dates = [date(2025, 1, 1) + timedelta(days=i * 3) for i in range(100)]
    persons = [f"PER-{i:04d}" for i in range(100)]
    return df.with_columns(
        [
            pl.Series("as_of_date", dates),
            pl.Series("person_cluster_id", persons),
        ]
    )


def test_baseline_report_config_validations() -> None:
    """Validate BaselineReportConfig split ratios, test partition lockout, and confidence."""
    # Valid config
    cfg = BaselineReportConfig(
        train_ratio=0.60,
        select_ratio=0.15,
        calibrate_ratio=0.15,
        test_ratio=0.10,
        evaluation_split="select",
    )
    assert cfg.evaluation_split == "select"

    # Split ratios sum != 1.0
    with pytest.raises(CompIntelValidationError) as exc_ratio:
        BaselineReportConfig(
            train_ratio=0.50,
            select_ratio=0.20,
            calibrate_ratio=0.10,
            test_ratio=0.10,
        )
    assert exc_ratio.value.code == "INVALID_SPLIT_RATIOS"

    # Attempting to evaluate on locked test set (Rule R-MD-02)
    with pytest.raises(CompIntelValidationError) as exc_test:
        BaselineReportConfig(
            evaluation_split="test",  # type: ignore[arg-type]
        )
    assert exc_test.value.code == "FORBIDDEN_SPLIT_EVALUATION"
    assert "Locked final test set cannot be evaluated" in str(exc_test.value)

    # Invalid confidence level
    with pytest.raises(CompIntelValidationError) as exc_ci:
        BaselineReportConfig(confidence_level=1.5)
    assert exc_ci.value.code == "INVALID_CONFIDENCE_LEVEL"


def test_add_experience_band_column() -> None:
    """Verify standardized binning into experience bands."""
    df = pl.DataFrame({"years_experience": [0.5, 2.0, 3.5, 5.0, 8.0, 10.0, 12.5, 15.0, 20.0, None]})
    res = add_experience_band_column(df)
    bands = res["experience_band"].to_list()
    assert bands == [
        "0-2",
        "0-2",
        "3-5",
        "3-5",
        "6-10",
        "6-10",
        "11-15",
        "11-15",
        "16+",
        "UNKNOWN",
    ]

    # Without years_experience column
    df_no_exp = pl.DataFrame({"role": ["SWE"]})
    res_no = add_experience_band_column(df_no_exp)
    assert res_no["experience_band"].to_list() == ["UNKNOWN"]


def test_missing_required_columns_validation(rich_synthetic_df: pl.DataFrame) -> None:
    """Report generator raises CompIntelValidationError when required columns are missing."""
    invalid_df = rich_synthetic_df.drop(["years_experience"])
    generator = BaselineReportGenerator(BaselineReportConfig(allow_synthetic=True))

    with pytest.raises(CompIntelValidationError) as exc:
        generator.generate(invalid_df)
    assert exc.value.code == "MISSING_REPORT_COLUMNS"


def test_synthetic_data_isolation_guard(rich_synthetic_df: pl.DataFrame) -> None:
    """Synthetic observations are rejected by default unless allow_synthetic=True (Rule R-MD-11)."""
    # By default, allow_synthetic is False
    generator_strict = BaselineReportGenerator(BaselineReportConfig(allow_synthetic=False))
    with pytest.raises(DataContractError) as exc:
        generator_strict.generate(rich_synthetic_df)
    assert exc.value.code == "SYNTHETIC_DATA_PROHIBITED"
    assert "Rule R-MD-11" in str(exc.value)

    # When allow_synthetic is True, execution proceeds and sets is_synthetic=True
    generator_synth = BaselineReportGenerator(BaselineReportConfig(allow_synthetic=True))
    report = generator_synth.generate(rich_synthetic_df)
    assert report.is_synthetic is True
    md_text = report.to_markdown()
    assert "SYNTHETIC TEST FIXTURE DATA DETECTED" in md_text


def test_baseline_report_comprehensive_generation(rich_synthetic_df: pl.DataFrame) -> None:
    """Verify that all Rule R-MD-05 metrics, slices, and threshold checks are generated."""
    cfg = BaselineReportConfig(
        train_ratio=0.60,
        select_ratio=0.20,
        calibrate_ratio=0.10,
        test_ratio=0.10,
        evaluation_split="select",
        with_bootstrap_ci=True,
        bootstrap_resamples=100,
        allow_synthetic=True,
    )
    generator = BaselineReportGenerator(cfg)
    report = generator.generate(rich_synthetic_df, snapshot_id="SNAP-TEST-RICH")

    assert isinstance(report, BaselineReport)
    assert report.snapshot_id == "SNAP-TEST-RICH"
    assert report.evaluation_split == "select"
    assert report.data_summary["total_observations"] == rich_synthetic_df.height
    assert report.data_summary["eval_count"] > 0

    # Both models evaluated
    assert "rung_a" in report.models
    assert "rung_b" in report.models
    rung_a = report.models["rung_a"]
    rung_b = report.models["rung_b"]

    assert "abstention_rate" in rung_a
    assert "abstention_rate" in rung_b

    # Verify R-MD-05 metrics presence on models that did not abstain
    for m_info in [rung_a, rung_b]:
        if m_info["metrics"] is not None:
            met = m_info["metrics"]
            # Point metrics
            assert "mae" in met["point"]
            assert "medae" in met["point"]
            assert "mape" in met["point"]
            assert "mdape" in met["point"]
            assert "rmse" in met["point"]

            # Quantile loss
            assert "pinball_q10" in met["quantile_loss"]
            assert "pinball_q50" in met["quantile_loss"]
            assert "pinball_q90" in met["quantile_loss"]
            assert "mean_pinball_loss" in met["quantile_loss"]

            # Interval metrics
            assert "coverage_80" in met["interval"]
            assert "mean_width" in met["interval"]
            assert "median_width" in met["interval"]
            assert "relative_median_width" in met["interval"]
            assert "underflow_rate_q10" in met["interval"]
            assert "overflow_rate_q90" in met["interval"]

            # Calibration metrics
            assert "mean_calibration_error" in met["calibration"]
            assert "crossing_rate" in met["calibration"]

            # Bootstrap CIs
            assert "mae" in met["point_ci"]
            assert "mdape" in met["point_ci"]

    # Threshold checks
    assert len(report.threshold_checks) >= 5
    metrics_checked = {c["metric"] for c in report.threshold_checks}
    assert "80% Interval Coverage" in metrics_checked
    assert "Mean Calibration Error" in metrics_checked
    assert "Quantile Crossing Rate" in metrics_checked
    assert "Point MAE" in metrics_checked
    assert "Point MdAPE" in metrics_checked

    # Comparison and champion recommendation
    assert "champion_model" in report.champion_recommendation
    assert "rationale" in report.champion_recommendation
    assert "report_id" in report.leakage_audit_reference

    # Markdown format check
    md_text = report.to_markdown()
    assert "# Baseline Evaluation Report:" in md_text
    assert "## 1. Provenance and Partition Metadata" in md_text
    assert "## 2. Overall Model Performance (Rule R-MD-05)" in md_text
    assert "## 3. Pre-Registered Acceptance Thresholds (v1.yaml)" in md_text
    assert "## 5. Model Comparison & Minimum Effect Sizes" in md_text
    assert "## 6. Champion Recommendation" in md_text
    assert "## 7. Leakage and Duplicate Inflation Audit Cross-Reference" in md_text


def test_baseline_report_save_and_json_serialization(
    rich_synthetic_df: pl.DataFrame, tmp_path: Path
) -> None:
    """Verify report persistence as valid Markdown and JSON files."""
    cfg = BaselineReportConfig(
        with_bootstrap_ci=False,
        allow_synthetic=True,
    )
    report = run_baseline_evaluation_report(
        df=rich_synthetic_df,
        config=cfg,
        output_md=tmp_path / "test_report.md",
        output_json=tmp_path / "test_report.json",
    )

    out_md = tmp_path / "test_report.md"
    out_json = tmp_path / "test_report.json"

    assert out_md.exists()
    assert out_json.exists()

    md_content = out_md.read_text(encoding="utf-8")
    assert report.report_id in md_content

    with open(out_json, encoding="utf-8") as f:
        json_data = json.load(f)
    assert json_data["report_id"] == report.report_id
    assert json_data["is_synthetic"] is True
    assert "models" in json_data


def test_baseline_report_on_calibrate_partition(rich_synthetic_df: pl.DataFrame) -> None:
    """Evaluation on 'calibrate' dev partition is supported."""
    cfg = BaselineReportConfig(
        evaluation_split="calibrate",
        with_bootstrap_ci=False,
        allow_synthetic=True,
    )
    generator = BaselineReportGenerator(cfg)
    report = generator.generate(rich_synthetic_df)
    assert report.evaluation_split == "calibrate"
    assert report.data_summary["eval_split_name"] == "calibrate"


def test_generate_baseline_report_cli(repo_root: Path, tmp_path: Path) -> None:
    """Verify scripts/generate_baseline_report.py CLI runs cleanly on canonical observations."""
    canonical_parquet = repo_root / "data" / "canonical" / "canonical_observations.parquet"
    if not canonical_parquet.exists():
        pytest.skip("Canonical observations parquet not present in clean checkout (Rule R-DA-08).")

    script_path = repo_root / "scripts" / "generate_baseline_report.py"
    out_md = tmp_path / "cli_report.md"
    out_json = tmp_path / "cli_report.json"

    cmd = [
        sys.executable,
        str(script_path),
        "--canonical-path",
        str(canonical_parquet),
        "--output-md",
        str(out_md),
        "--output-json",
        str(out_json),
        "--seed",
        "42",
        "--split",
        "select",
        "--bootstrap-resamples",
        "50",
    ]

    res = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert res.returncode == 0, f"CLI command failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "Baseline Evaluation Report" in res.stdout
    assert out_md.exists()
    assert out_json.exists()

    # Verify JSON content
    with open(out_json, encoding="utf-8") as f:
        data = json.load(f)
    assert data["evaluation_split"] == "select"
    assert "models" in data
