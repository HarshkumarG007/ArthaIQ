"""Unit tests for conformal coverage and calibration report engine (Task T5.04).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal dataset splitting.
- Rule R-MD-02: Final test set is locked; evaluation on 'test' is prohibited.
- Rule R-MD-05: Mandatory evaluation metrics: coverage, interval width, quantile
  calibration errors, subgroup slices, recent window, and tail analysis.
- Rule R-MD-08: Thin-evidence support checks. Slices below minimum support (N < 10)
  must be flagged, not hidden.
- Rule R-MD-10: Deterministic seeds and reproducibility.
- Rule R-MD-11: Synthetic data blocked by default from canonical reports.
- Rule R-UQ-01: Bootstrap confidence intervals.
- Rule R-UQ-03: Statutory assumptions documented: marginal coverage under exchangeability.
- Rule R-TS-01, R-TS-03: Quality standards and >= 90% test coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
from scripts.generate_conformal_report import main as generate_report_main

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.conformal_report import (
    ConformalCalibrationReport,
    ConformalCalibrationReportGenerator,
    ConformalReportConfig,
    ConformalSliceMetrics,
    ModelConformalEvaluation,
    RecentWindowMetrics,
    TailAnalysisMetrics,
)


@pytest.fixture
def conformal_eval_df() -> pl.DataFrame:
    """Fixture providing a rich multi-slice 48-observation dataset for conformal testing."""
    roles = [
        "SOFTWARE",
        "SOFTWARE",
        "SOFTWARE",
        "SOFTWARE",
        "SOFTWARE",
        "SOFTWARE",
        "DATA",
        "DATA",
        "DATA",
        "DATA",
        "DATA",
        "DATA",
        "MLAI",
        "MLAI",
        "MLAI",
        "MLAI",
        "MLAI",
        "MLAI",
        "SOFTWARE",
        "DATA",
        "MLAI",
        "SOFTWARE",
        "DATA",
        "MLAI",
    ] * 2

    seniorities = [
        "JUNIOR",
        "MID",
        "SENIOR",
        "MID",
        "SENIOR",
        "LEAD",
        "JUNIOR",
        "MID",
        "SENIOR",
        "MID",
        "SENIOR",
        "LEAD",
        "JUNIOR",
        "MID",
        "SENIOR",
        "MID",
        "SENIOR",
        "LEAD",
        "STAFF",
        "PRINCIPAL",
        "STAFF",
        "JUNIOR",
        "MID",
        "SENIOR",
    ] * 2

    locations = [
        "BANGALORE",
        "BANGALORE",
        "HYDERABAD",
        "HYDERABAD",
        "PUNE",
        "DELHI_NCR",
        "BANGALORE",
        "HYDERABAD",
        "BANGALORE",
        "PUNE",
        "DELHI_NCR",
        "MUMBAI",
        "BANGALORE",
        "BANGALORE",
        "HYDERABAD",
        "PUNE",
        "MUMBAI",
        "CHENNAI",
        "REMOTE",
        "BANGALORE",
        "HYDERABAD",
        "BANGALORE",
        "PUNE",
        "DELHI_NCR",
    ] * 2

    yoe = [
        1.5,
        3.5,
        7.0,
        4.0,
        8.5,
        12.0,
        1.0,
        4.0,
        6.5,
        5.0,
        9.0,
        11.5,
        1.2,
        3.8,
        7.5,
        4.5,
        8.0,
        13.0,
        14.0,
        18.0,
        15.0,
        2.0,
        4.5,
        8.0,
    ] * 2

    pay = [
        10.0,
        18.5,
        32.0,
        20.0,
        36.0,
        48.0,
        9.5,
        17.0,
        28.0,
        22.0,
        34.0,
        45.0,
        11.0,
        21.0,
        35.0,
        24.0,
        38.0,
        52.0,
        65.0,
        85.0,
        70.0,
        12.0,
        21.0,
        35.0,
    ] * 2

    dates = [
        f"2023-{(i % 12) + 1:02d}-15" if i < 24 else f"2024-{(i % 12) + 1:02d}-15"
        for i in range(48)
    ]

    tiers = [
        "A",
        "A",
        "B",
        "A",
        "B",
        "A",
        "B",
        "A",
        "A",
        "B",
        "A",
        "B",
        "A",
        "A",
        "B",
        "A",
        "B",
        "A",
        "A",
        "A",
        "B",
        "A",
        "B",
        "A",
    ] * 2

    return pl.DataFrame(
        {
            "observation_id": [f"OBS_{i:04d}" for i in range(48)],
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "guaranteed_cash_annual": pay,
            "as_of_date": dates,
            "person_cluster_id": [f"PER_{i:03d}" for i in range(48)],
            "provenance_tier": tiers,
        }
    )


# ==============================================================================
# 1. Configuration & Governance Contract Tests
# ==============================================================================


@pytest.mark.unit
def test_conformal_report_config_defaults() -> None:
    """Verify default parameters for ConformalReportConfig."""
    cfg = ConformalReportConfig()
    assert cfg.nominal_coverage == 0.80
    assert cfg.min_support_threshold == 10
    assert cfg.min_pay_bound_lpa == 0.50
    assert cfg.random_seed == 42
    assert cfg.evaluation_split == "select"
    assert cfg.train_ratio == 0.60
    assert cfg.select_ratio == 0.15
    assert cfg.calibrate_ratio == 0.15
    assert cfg.test_ratio == 0.10


@pytest.mark.unit
def test_locked_test_partition_rejection() -> None:
    """Verify that attempting to evaluate on 'test' raises CompIntelValidationError (R-MD-02)."""
    with pytest.raises(
        CompIntelValidationError, match="Rule R-MD-02 strictly locks the final test"
    ):
        ConformalCalibrationReportGenerator(ConformalReportConfig(evaluation_split="test"))


@pytest.mark.unit
def test_missing_report_columns_rejection(conformal_eval_df: pl.DataFrame) -> None:
    """Verify generator rejects DataFrame missing required columns."""
    df_missing = conformal_eval_df.drop("observation_id")
    generator = ConformalCalibrationReportGenerator()
    with pytest.raises(CompIntelValidationError, match="missing required report columns"):
        generator.generate_report(df_missing)


@pytest.mark.unit
def test_synthetic_data_isolation_guard(conformal_eval_df: pl.DataFrame) -> None:
    """Verify synthetic data is blocked by default under Rule R-MD-11."""
    synthetic_df = conformal_eval_df.with_columns(pl.lit(True).alias("is_synthetic"))
    generator = ConformalCalibrationReportGenerator(ConformalReportConfig(allow_synthetic=False))

    with pytest.raises(DataContractError, match="Rule R-MD-11 prohibits synthetic data"):
        generator.generate_report(synthetic_df)

    # Allowed when explicitly configured for plumbing/testing
    generator_allowed = ConformalCalibrationReportGenerator(
        ConformalReportConfig(
            allow_synthetic=True,
            n_bootstrap_resamples=20,
            train_ratio=0.50,
            select_ratio=0.25,
            calibrate_ratio=0.15,
            test_ratio=0.10,
        )
    )
    report = generator_allowed.generate_report(synthetic_df)
    assert report is not None


# ==============================================================================
# 2. Report Generation, Slices & Low-Support Flagging Tests
# ==============================================================================


@pytest.mark.unit
def test_conformal_report_generation_and_slices(conformal_eval_df: pl.DataFrame) -> None:
    """Verify full report generation, low support flagging, and slice breakdowns."""
    config = ConformalReportConfig(
        nominal_coverage=0.80,
        min_support_threshold=10,
        n_bootstrap_resamples=30,
        random_seed=42,
        evaluation_split="select",
        train_ratio=0.50,
        select_ratio=0.25,
        calibrate_ratio=0.15,
        test_ratio=0.10,
    )
    generator = ConformalCalibrationReportGenerator(config=config)
    report = generator.generate_report(conformal_eval_df)

    assert isinstance(report, ConformalCalibrationReport)
    assert report.evaluation_split == "select"
    assert report.assumptions.is_marginal is True
    assert report.assumptions.claims_individual_coverage is False

    # Models evaluated
    assert "cqr_catboost" in report.models
    assert "split_conformal_catboost" in report.models
    assert "base_catboost" in report.models

    cqr = report.models["cqr_catboost"]
    assert cqr.method == "cqr"
    assert cqr.nominal_coverage == 0.80
    assert 0.0 <= cqr.overall_coverage <= 1.0
    assert cqr.overall_mean_width_lpa >= 0.0
    assert cqr.crossing_rate == 0.0  # Monotonic ordering enforced

    # Check that bootstrap CI was computed for sample size >= 5
    if cqr.overall_coverage_ci is not None:
        assert cqr.overall_coverage_ci.ci_lower <= cqr.overall_coverage_ci.ci_upper

    # Verify slices are present and low support is FLAGGED, NOT HIDDEN
    assert "role_family" in cqr.slices
    assert "seniority" in cqr.slices
    assert "experience_band" in cqr.slices
    assert "location" in cqr.slices

    for _dim, slice_metrics_list in cqr.slices.items():
        assert len(slice_metrics_list) > 0
        for sm in slice_metrics_list:
            assert isinstance(sm, ConformalSliceMetrics)
            assert sm.sample_size >= 0
            # If sample size < 10, it must be flagged
            if sm.sample_size < 10:
                assert sm.is_low_support is True
                assert sm.support_status == "LOW_SUPPORT_FLAGGED"
            else:
                assert sm.is_low_support is False
                assert sm.support_status == "ADEQUATE"

    # Verify Tail metrics
    assert isinstance(cqr.tails, TailAnalysisMetrics)
    assert 0.0 <= cqr.tails.global_underflow_q10 <= 1.0
    assert 0.0 <= cqr.tails.global_overflow_q90 <= 1.0

    # Verify Recent Window metrics if timestamps present
    if cqr.recent_window is not None:
        assert isinstance(cqr.recent_window, RecentWindowMetrics)
        assert cqr.recent_window.window_sample_size > 0
        assert 0.0 <= cqr.recent_window.recent_coverage <= 1.0

    # Champion verdict
    assert "champion_model" in report.champion_verdict
    assert "status" in report.champion_verdict
    assert "ACCEPTED_AS_RUNG_F_CHAMPION" in report.champion_verdict["status"]


# ==============================================================================
# 3. Serialization and Markdown Formatting Tests
# ==============================================================================


@pytest.mark.unit
def test_conformal_report_serialization_and_markdown(conformal_eval_df: pl.DataFrame) -> None:
    """Verify dictionary serialization and markdown rendering with statutory warnings."""
    config = ConformalReportConfig(
        nominal_coverage=0.80,
        n_bootstrap_resamples=20,
        random_seed=42,
        train_ratio=0.50,
        select_ratio=0.25,
        calibrate_ratio=0.15,
        test_ratio=0.10,
    )
    generator = ConformalCalibrationReportGenerator(config=config)
    report = generator.generate_report(conformal_eval_df)

    # 1. to_dict() test
    d = report.to_dict()
    assert d["report_id"] == report.report_id
    assert d["evaluation_split"] == "select"
    assert "models" in d
    assert "assumptions" in d
    assert d["assumptions"]["is_marginal"] is True

    # Check JSON serializability
    json_str = json.dumps(d)
    assert len(json_str) > 0

    # 2. to_markdown() test
    md = report.to_markdown()
    assert "# ArthaIQ Conformal Coverage & Calibration Report" in md
    assert "FORMAL CONFORMAL ASSUMPTIONS (Rule R-UQ-03)" in md
    assert "LOCKED TEST PARTITION (Rule R-MD-02)" in md
    assert "Global Conformal Performance Comparison" in md
    assert "Tail Error & Boundary Distribution" in md
    assert "Temporal Drift & Recent Window Breakdown" in md
    assert "Subgroup Slice Analysis & Minimum Support Flags" in md
    assert "MINIMUM SUPPORT POLICY (Rule R-MD-08)" in md
    assert "Champion Uncertainty Model Verdict" in md


# ==============================================================================
# 4. Calibration Split & Direct Prediction Evaluation Tests
# ==============================================================================


@pytest.mark.unit
def test_conformal_report_on_calibrate_split(conformal_eval_df: pl.DataFrame) -> None:
    """Verify report can evaluate empirical calibration on 'calibrate' partition."""
    config = ConformalReportConfig(
        nominal_coverage=0.80,
        n_bootstrap_resamples=20,
        evaluation_split="calibrate",
        train_ratio=0.50,
        select_ratio=0.25,
        calibrate_ratio=0.15,
        test_ratio=0.10,
    )
    generator = ConformalCalibrationReportGenerator(config=config)
    report = generator.generate_report(conformal_eval_df)
    assert report.evaluation_split == "calibrate"
    assert report.data_summary["eval_split_name"] == "calibrate"


@pytest.mark.unit
def test_evaluate_predictions_edge_cases(conformal_eval_df: pl.DataFrame) -> None:
    """Test _evaluate_predictions with crossings, tail under/overflow, and abstentions."""
    generator = ConformalCalibrationReportGenerator(ConformalReportConfig(n_bootstrap_resamples=20))
    test_slice = conformal_eval_df.slice(0, 8)

    # Synthetic series including abstentions, None values, crossings, underflows, and overflows
    p10_s = [15.0, None, 25.0, 50.0, 10.0, 5.0, 12.0, 8.0]
    p50_s = [20.0, 30.0, 22.0, 45.0, 20.0, 15.0, 18.0, 14.0]  # note crossing in row 2 (25 > 22)
    p90_s = [30.0, 40.0, 35.0, 40.0, 12.0, 25.0, 28.0, 20.0]  # note underflow in row 4
    abstained_s = [False, True, False, False, False, False, False, False]

    eval_result = generator._evaluate_predictions(
        model_name="Custom Model",
        method="custom",
        nominal_coverage=0.80,
        conformal_correction=2.5,
        eval_df=test_slice,
        p10_series=p10_s,
        p50_series=p50_s,
        p90_series=p90_s,
        abstained_series=abstained_s,
        slice_dims=["role_family", "location"],
    )

    assert isinstance(eval_result, ModelConformalEvaluation)
    assert eval_result.abstention_count >= 1
    assert eval_result.crossing_count >= 1
    assert eval_result.tails.global_underflow_q10 >= 0.0

    # All abstained rejection test
    all_abstained = [True] * len(test_slice)
    with pytest.raises(CompIntelValidationError, match="All records abstained"):
        generator._evaluate_predictions(
            model_name="Abstained Model",
            method="cqr",
            nominal_coverage=0.80,
            conformal_correction=1.0,
            eval_df=test_slice,
            p10_series=[10.0] * 8,
            p50_series=[20.0] * 8,
            p90_series=[30.0] * 8,
            abstained_series=all_abstained,
            slice_dims=[],
        )

    # DataFrame with no dates
    df_no_dates = test_slice.drop("as_of_date")
    no_date_eval = generator._evaluate_predictions(
        model_name="No Date Model",
        method="cqr",
        nominal_coverage=0.80,
        conformal_correction=1.0,
        eval_df=df_no_dates,
        p10_series=[10.0] * 8,
        p50_series=[20.0] * 8,
        p90_series=[30.0] * 8,
        abstained_series=[False] * 8,
        slice_dims=[],
    )
    assert no_date_eval.recent_window is None


# ==============================================================================
# 5. CLI Execution Tests
# ==============================================================================


@pytest.mark.unit
def test_cli_generate_conformal_report(tmp_path: Path, conformal_eval_df: pl.DataFrame) -> None:
    """Verify scripts.generate_conformal_report main CLI execution."""
    canonical_parquet = tmp_path / "canonical.parquet"
    conformal_eval_df.write_parquet(canonical_parquet)

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    test_args = [
        "generate_conformal_report.py",
        "--canonical-path",
        str(canonical_parquet),
        "--output-md",
        str(out_md),
        "--output-json",
        str(out_json),
        "--split",
        "select",
        "--nominal-coverage",
        "0.80",
        "--allow-synthetic",
    ]

    with patch("sys.argv", test_args):
        ret = generate_report_main()
        assert ret == 0

    assert out_md.exists()
    assert out_json.exists()
    assert "# ArthaIQ Conformal Coverage & Calibration Report" in out_md.read_text(encoding="utf-8")
