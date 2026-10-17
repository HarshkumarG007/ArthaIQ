"""Unit tests for Rung D cross-validation, resource profiling, and benchmark report (Task T5.01b).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal dataset splitting.
- Rule R-MD-02: Isolated final test set; evaluating on 'test' split is strictly prohibited.
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-04: Group disjointness and leak-free validation.
- Rule R-MD-05: Mandatory evaluation metrics: MAE, MdAE, MAPE, MdAPE, RMSE, bootstrap CIs, slices.
- Rule R-MD-08: Thin-evidence abstention reporting.
- Rule R-MD-11: Synthetic data blocked by default; cautioned when allowed.
- Rule R-TS-01 & R-TS-03: >= 90% test coverage floor.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from tests.fixtures.synthetic import generate_synthetic_observations_df

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.gbm_report import (
    GBMBenchmarkReport,
    GBMBenchmarkReportConfig,
    GBMBenchmarkReportGenerator,
    _compute_paired_comparison,
    run_gbm_benchmark_report,
)
from compintel.models.gbm.config import GBMModelType, GBMPointConfig
from compintel.models.gbm.cv import (
    GBMCVResult,
    GroupedTemporalCVSplitter,
    _compute_point_metrics,
    run_gbm_cv,
)


@pytest.fixture
def repo_root() -> Path:
    """Return repository root path."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def rich_synthetic_df() -> pl.DataFrame:
    """Generate deterministic synthetic cohort with diverse roles, seniorities, and dates."""
    df = generate_synthetic_observations_df(n_records=80, seed=42)
    dates = [date(2025, 1, 1) + timedelta(days=i * 4) for i in range(80)]
    persons = [f"PER-{i:04d}" for i in range(80)]
    return df.with_columns(
        [
            pl.Series("as_of_date", dates),
            pl.Series("person_cluster_id", persons),
        ]
    )


# ==============================================================================
# 1. GroupedTemporalCVSplitter Tests
# ==============================================================================


@pytest.mark.unit
def test_cv_splitter_validation() -> None:
    """Verify input validation rules on GroupedTemporalCVSplitter."""
    # n_folds < 2
    with pytest.raises(CompIntelValidationError) as exc:
        GroupedTemporalCVSplitter(n_folds=1)
    assert exc.value.code == "INVALID_CV_FOLDS"

    splitter = GroupedTemporalCVSplitter(n_folds=3)

    # Missing date column
    df_no_date = pl.DataFrame({"person_cluster_id": ["P1", "P2", "P3"]})
    with pytest.raises(CompIntelValidationError) as exc_date:
        splitter.split(df_no_date)
    assert exc_date.value.code == "MISSING_DATE_COLUMN"

    # Missing group column
    df_no_grp = pl.DataFrame({"as_of_date": [date(2025, 1, 1), date(2025, 1, 2)]})
    with pytest.raises(CompIntelValidationError) as exc_grp:
        splitter.split(df_no_grp)
    assert exc_grp.value.code == "MISSING_GROUP_COLUMN"

    # Insufficient records
    df_tiny = pl.DataFrame(
        {
            "as_of_date": [date(2025, 1, 1), date(2025, 1, 2)],
            "person_cluster_id": ["P1", "P2"],
        }
    )
    with pytest.raises(CompIntelValidationError) as exc_rec:
        splitter.split(df_tiny)
    assert exc_rec.value.code == "INSUFFICIENT_CV_RECORDS"


@pytest.mark.unit
def test_cv_splitter_temporal_and_group_invariants(rich_synthetic_df: pl.DataFrame) -> None:
    """Verify temporal monotonicity and zero group leakage across all CV folds."""
    splitter = GroupedTemporalCVSplitter(n_folds=3, min_train_size=10, min_val_size=5)
    folds = splitter.split(rich_synthetic_df)

    assert len(folds) == 3

    for fold in folds:
        train_sub = rich_synthetic_df[fold.train_indices]
        val_sub = rich_synthetic_df[fold.val_indices]

        assert len(train_sub) >= 10
        assert len(val_sub) >= 5

        # Rule R-MD-03: Temporal monotonicity (train dates <= val dates)
        max_train_date = train_sub["as_of_date"].max()
        min_val_date = val_sub["as_of_date"].min()
        assert max_train_date <= min_val_date

        # Rule R-DA-06: Group disjointness (zero person_cluster_id overlap)
        train_persons = set(train_sub["person_cluster_id"].to_list())
        val_persons = set(val_sub["person_cluster_id"].to_list())
        assert train_persons.isdisjoint(val_persons)


@pytest.mark.unit
def test_cv_splitter_cross_window_quarantine() -> None:
    """Verify that multi-record entities spanning cutoffs are quarantined from val folds."""
    # Person P1 appears in both earliest window and later window
    dates = [
        date(2025, 1, 1),
        date(2025, 1, 2),
        date(2025, 1, 3),
        date(2025, 1, 4),
        date(2025, 1, 5),
        date(2025, 1, 6),
    ]
    persons = ["P1", "P2", "P3", "P1", "P4", "P5"]
    df = pl.DataFrame({"as_of_date": dates, "person_cluster_id": persons})

    splitter = GroupedTemporalCVSplitter(n_folds=2, min_train_size=2, min_val_size=1)
    folds = splitter.split(df)

    for fold in folds:
        train_p = set(df[fold.train_indices]["person_cluster_id"].to_list())
        val_p = set(df[fold.val_indices]["person_cluster_id"].to_list())
        assert train_p.isdisjoint(val_p)


# ==============================================================================
# 2. Point Metrics & Profiling Helper Tests
# ==============================================================================


@pytest.mark.unit
def test_compute_point_metrics_normal() -> None:
    """Verify _compute_point_metrics numerical computations."""
    y_true = np.array([20.0, 30.0, 50.0], dtype=np.float64)
    y_pred = np.array([22.0, 27.0, 55.0], dtype=np.float64)
    abstained = np.array([False, False, False], dtype=bool)

    metrics = _compute_point_metrics(y_true, y_pred, abstained)

    # MAE = (|2| + |3| + |5|) / 3 = 10 / 3 = 3.3333...
    assert pytest.approx(metrics.mae, rel=1e-4) == 10.0 / 3.0
    # MedAE = median(2, 3, 5) = 3.0
    assert pytest.approx(metrics.medae, rel=1e-4) == 3.0
    # RMSE = sqrt((4 + 9 + 25) / 3) = sqrt(38 / 3) = 3.5590
    assert pytest.approx(metrics.rmse, rel=1e-4) == np.sqrt(38.0 / 3.0)
    assert metrics.abstention_rate == 0.0
    assert metrics.valid_sample_size == 3


@pytest.mark.unit
def test_compute_point_metrics_all_abstained() -> None:
    """Verify _compute_point_metrics when all observations abstain."""
    y_true = np.array([20.0, 30.0], dtype=np.float64)
    y_pred = np.array([20.0, 30.0], dtype=np.float64)
    abstained = np.array([True, True], dtype=bool)

    metrics = _compute_point_metrics(y_true, y_pred, abstained)
    assert np.isnan(metrics.mae)
    assert np.isnan(metrics.mdape)
    assert metrics.abstention_rate == 100.0
    assert metrics.valid_sample_size == 0


# ==============================================================================
# 3. run_gbm_cv Execution Tests
# ==============================================================================


@pytest.mark.unit
def test_run_gbm_cv_lightgbm(rich_synthetic_df: pl.DataFrame) -> None:
    """Execute grouped-temporal CV with LightGBM on synthetic data."""
    cfg = GBMPointConfig(
        model_type=GBMModelType.LIGHTGBM,
        n_estimators=10,
        random_seed=42,
    )
    result = run_gbm_cv(
        df=rich_synthetic_df,
        model_type=GBMModelType.LIGHTGBM,
        config=cfg,
        n_folds=2,
    )

    assert isinstance(result, GBMCVResult)
    assert result.model_type == GBMModelType.LIGHTGBM
    assert result.n_folds == 2
    assert len(result.folds) == 2
    assert result.overall_metrics.valid_sample_size > 0
    assert result.overall_metrics.mae > 0.0

    # Resource profile checks
    res = result.aggregate_resource_profile
    assert res.wall_clock_train_seconds > 0.0
    assert res.inference_latency_ms >= 0.0
    assert res.n_val_samples > 0

    # Serialization
    res_dict = result.to_dict()
    assert res_dict["model_name"] == "LIGHTGBM"
    assert "overall_metrics" in res_dict


@pytest.mark.unit
def test_run_gbm_cv_catboost(rich_synthetic_df: pl.DataFrame) -> None:
    """Execute grouped-temporal CV with CatBoost on synthetic data."""
    cfg = GBMPointConfig(
        model_type=GBMModelType.CATBOOST,
        n_estimators=10,
        random_seed=42,
    )
    result = run_gbm_cv(
        df=rich_synthetic_df,
        model_type=GBMModelType.CATBOOST,
        config=cfg,
        n_folds=2,
    )

    assert isinstance(result, GBMCVResult)
    assert result.model_type == GBMModelType.CATBOOST
    assert len(result.folds) == 2
    assert result.overall_metrics.valid_sample_size > 0
    assert result.overall_metrics.mdape > 0.0


# ==============================================================================
# 4. GBMBenchmarkReportConfig Validations
# ==============================================================================


@pytest.mark.unit
def test_benchmark_config_validation() -> None:
    """Verify input validation rules in GBMBenchmarkReportConfig."""
    # Valid
    cfg = GBMBenchmarkReportConfig(evaluation_split="select")
    assert cfg.evaluation_split == "select"

    # Split ratios sum != 1.0
    with pytest.raises(CompIntelValidationError) as exc_ratio:
        GBMBenchmarkReportConfig(train_ratio=0.50, select_ratio=0.10)
    assert exc_ratio.value.code == "INVALID_SPLIT_RATIOS"

    # Attempting to evaluate on locked test set (Rule R-MD-02)
    with pytest.raises(CompIntelValidationError) as exc_test:
        GBMBenchmarkReportConfig(evaluation_split="test")  # type: ignore[arg-type]
    assert exc_test.value.code == "FORBIDDEN_SPLIT_EVALUATION"

    # Invalid confidence level
    with pytest.raises(CompIntelValidationError) as exc_ci:
        GBMBenchmarkReportConfig(confidence_level=1.2)
    assert exc_ci.value.code == "INVALID_CONFIDENCE_LEVEL"

    # Invalid bootstrap resamples
    with pytest.raises(CompIntelValidationError) as exc_boot:
        GBMBenchmarkReportConfig(bootstrap_resamples=0)
    assert exc_boot.value.code == "INVALID_BOOTSTRAP_RESAMPLES"


# ==============================================================================
# 5. GBMBenchmarkReportGenerator Tests
# ==============================================================================


@pytest.mark.unit
def test_synthetic_data_isolation_guard(rich_synthetic_df: pl.DataFrame) -> None:
    """Synthetic observations are rejected by default unless allow_synthetic=True (Rule R-MD-11)."""
    generator_strict = GBMBenchmarkReportGenerator(GBMBenchmarkReportConfig(allow_synthetic=False))
    with pytest.raises(DataContractError) as exc:
        generator_strict.generate(rich_synthetic_df)
    assert exc.value.code == "SYNTHETIC_DATA_PROHIBITED"
    assert "Rule R-MD-11" in str(exc.value)


@pytest.mark.unit
def test_missing_report_columns_guard(rich_synthetic_df: pl.DataFrame) -> None:
    """Report generator raises CompIntelValidationError when required columns are missing."""
    df_invalid = rich_synthetic_df.drop(["years_experience"])
    generator = GBMBenchmarkReportGenerator(GBMBenchmarkReportConfig(allow_synthetic=True))
    with pytest.raises(CompIntelValidationError) as exc:
        generator.generate(df_invalid)
    assert exc.value.code == "MISSING_REPORT_COLUMNS"


@pytest.mark.unit
def test_full_benchmark_report_generation(
    rich_synthetic_df: pl.DataFrame,
    tmp_path: Path,
) -> None:
    """Verify full benchmark report generation, metrics, slices, CIs, and file serialization."""
    cfg = GBMBenchmarkReportConfig(
        train_ratio=0.60,
        select_ratio=0.20,
        calibrate_ratio=0.10,
        test_ratio=0.10,
        evaluation_split="select",
        n_cv_folds=2,
        with_bootstrap_ci=True,
        bootstrap_resamples=50,
        allow_synthetic=True,
        random_seed=42,
    )

    out_md = tmp_path / "test_report.md"
    out_json = tmp_path / "test_report.json"

    report = run_gbm_benchmark_report(
        df=rich_synthetic_df,
        config=cfg,
        output_md_path=out_md,
        output_json_path=out_json,
    )

    assert isinstance(report, GBMBenchmarkReport)
    assert report.is_synthetic is True
    assert report.evaluation_split == "select"
    assert out_md.exists()
    assert out_json.exists()

    # Verify all 4 models evaluated
    assert "rung_a_empirical" in report.models
    assert "rung_b_linear" in report.models
    assert "rung_d_lightgbm" in report.models
    assert "rung_d_catboost" in report.models

    # Verify point metrics and CIs on non-abstained model
    cb_summary = report.models["rung_d_catboost"]
    assert cb_summary.mae > 0.0
    assert cb_summary.mdape > 0.0
    assert "mae" in cb_summary.point_ci
    assert "mdape" in cb_summary.point_ci

    # Verify CV results
    assert "lightgbm" in report.cv_results
    assert "catboost" in report.cv_results

    # Verify threshold checks
    assert len(report.threshold_checks) > 0

    # Verify paired comparisons
    assert len(report.paired_comparisons) >= 4

    # Markdown rendering check
    md_content = report.to_markdown()
    assert "# Rung D Benchmark Evaluation Report:" in md_content
    assert "SYNTHETIC TEST FIXTURE DATA DETECTED" in md_content
    assert "Hardware Resource Profiling" in md_content
    assert "Grouped-Temporal Cross-Validation" in md_content

    # JSON loading check
    saved_json = json.loads(out_json.read_text(encoding="utf-8"))
    assert saved_json["report_id"] == report.report_id
    assert "models" in saved_json


@pytest.mark.unit
def test_paired_comparison_insufficient_samples() -> None:
    """Verify _compute_paired_comparison handles insufficient joint samples cleanly."""
    comp = _compute_paired_comparison(
        cand_id="Cand",
        base_id="Base",
        cand_preds=np.array([10.0]),
        base_preds=np.array([10.0]),
        cand_abstained=np.array([False]),
        base_abstained=np.array([True]),
        y_true=np.array([10.0]),
    )
    assert comp.comparison_valid is False
    assert comp.is_statistically_significant is False


# ==============================================================================
# 6. CLI Runner Script Tests
# ==============================================================================


@pytest.mark.unit
def test_cli_missing_canonical_file(tmp_path: Path) -> None:
    """CLI exits with code 1 when canonical dataset is not found."""
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_gbm_benchmark.py"
    missing_path = tmp_path / "nonexistent.parquet"

    res = subprocess.run(
        [sys.executable, str(script_path), "--canonical-path", str(missing_path)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "Canonical observations not found" in res.stderr or "ERROR" in res.stderr
