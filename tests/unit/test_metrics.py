"""Unit tests for evaluation metrics module (Task T4.02).

Adheres strictly to:
- Rule R-MD-05: Mandatory baseline evaluation metrics (MAE, MedAE, MAPE, MdAPE,
  pinball loss, interval coverage, widths, calibration error, crossing rate, subgroup slices).
- Rule R-UQ-01: Bootstrap confidence intervals.
- Rule R-TS-01: Deterministic unit tests with hand-computed reference values.
"""

from __future__ import annotations

import math

import numpy as np
import polars as pl
import pytest

from compintel.errors import CompIntelValidationError
from compintel.evaluation.metrics import (
    CalibrationMetrics,
    ComprehensiveMetricsReport,
    IntervalMetrics,
    MetricWithCI,
    PointMetrics,
    QuantileLossMetrics,
    bootstrap_metric_ci,
    compute_evaluation_report,
    evaluate_calibration_metrics,
    evaluate_interval_metrics,
    evaluate_point_metrics,
    evaluate_quantile_metrics,
    interval_coverage,
    interval_underflow_overflow,
    interval_widths,
    mean_absolute_error,
    mean_absolute_percentage_error,
    median_absolute_error,
    median_absolute_percentage_error,
    pinball_loss,
    pinball_loss_array,
    quantile_calibration_error,
    quantile_crossing,
    root_mean_squared_error,
)


@pytest.mark.unit
def test_point_metrics_hand_computed_exact_values() -> None:
    """Verify MAE, MedAE, MAPE, MdAPE, and RMSE match hand-computed analytical values."""
    y_true = [10.0, 20.0, 30.0, 40.0]
    y_pred = [12.0, 18.0, 33.0, 36.0]
    # Residuals: [-2, 2, -3, 4]
    # Absolute errors: [2, 2, 3, 4]
    # MAE = (2 + 2 + 3 + 4) / 4 = 2.75
    # MedAE = (2 + 3) / 2 = 2.5
    # Percentage errors: [2/10, 2/20, 3/30, 4/40] = [0.20, 0.10, 0.10, 0.10]
    # MAPE = (0.20 + 0.10 + 0.10 + 0.10) / 4 = 0.125
    # MdAPE = (0.10 + 0.10) / 2 = 0.10
    # Squared errors: [4, 4, 9, 16] -> MSE = 33 / 4 = 8.25 -> RMSE = sqrt(8.25)
    expected_mae = 2.75
    expected_medae = 2.5
    expected_mape = 0.125
    expected_mdape = 0.10
    expected_rmse = math.sqrt(8.25)

    assert math.isclose(mean_absolute_error(y_true, y_pred), expected_mae)
    assert math.isclose(median_absolute_error(y_true, y_pred), expected_medae)
    assert math.isclose(mean_absolute_percentage_error(y_true, y_pred), expected_mape)
    assert math.isclose(median_absolute_percentage_error(y_true, y_pred), expected_mdape)
    assert math.isclose(root_mean_squared_error(y_true, y_pred), expected_rmse)

    point_res = evaluate_point_metrics(y_true, y_pred)
    assert isinstance(point_res, PointMetrics)
    assert math.isclose(point_res.mae, expected_mae)
    assert math.isclose(point_res.medae, expected_medae)
    assert math.isclose(point_res.mape, expected_mape)
    assert math.isclose(point_res.mdape, expected_mdape)
    assert math.isclose(point_res.rmse, expected_rmse)
    assert point_res.sample_size == 4


@pytest.mark.unit
def test_pinball_loss_hand_computed_asymmetric_penalties() -> None:
    """Verify pinball loss penalizes under-prediction and over-prediction appropriately."""
    # Under-prediction: y=10, y_hat=8 -> diff = 2.0
    # For q=0.10: 0.10 * 2 = 0.20
    # For q=0.50: 0.50 * 2 = 1.00
    # For q=0.90: 0.90 * 2 = 1.80
    assert math.isclose(pinball_loss([10.0], [8.0], q=0.10), 0.20)
    assert math.isclose(pinball_loss([10.0], [8.0], q=0.50), 1.00)
    assert math.isclose(pinball_loss([10.0], [8.0], q=0.90), 1.80)

    # Over-prediction: y=6, y_hat=8 -> diff = -2.0
    # For q=0.10: (1 - 0.10) * 2 = 1.80
    # For q=0.50: (1 - 0.50) * 2 = 1.00
    # For q=0.90: (1 - 0.90) * 2 = 0.20
    assert math.isclose(pinball_loss([6.0], [8.0], q=0.10), 1.80)
    assert math.isclose(pinball_loss([6.0], [8.0], q=0.50), 1.00)
    assert math.isclose(pinball_loss([6.0], [8.0], q=0.90), 0.20)

    # Perfect prediction
    assert math.isclose(pinball_loss([8.0], [8.0], q=0.10), 0.0)
    assert math.isclose(pinball_loss([8.0], [8.0], q=0.90), 0.0)

    # Elementwise array verification
    y_t = [10.0, 6.0]
    y_p = [8.0, 8.0]
    arr_q10 = pinball_loss_array(y_t, y_p, q=0.10)
    np.testing.assert_allclose(arr_q10, [0.20, 1.80])

    q_res = evaluate_quantile_metrics(y_t, [8.0, 8.0], [8.0, 8.0], [8.0, 8.0])
    assert isinstance(q_res, QuantileLossMetrics)
    assert math.isclose(q_res.pinball_q10, 1.00)
    assert math.isclose(q_res.pinball_q50, 1.00)
    assert math.isclose(q_res.pinball_q90, 1.00)
    assert math.isclose(q_res.mean_pinball_loss, 1.00)


@pytest.mark.unit
def test_interval_metrics_coverage_widths_and_tails() -> None:
    """Verify nominal 80% interval coverage, mean/median/relative widths, and tail rates."""
    y_true = [10.0, 20.0, 30.0, 40.0, 50.0]
    q10 = [12.0, 15.0, 25.0, 35.0, 45.0]  # pt 0 underflows: 10 < 12
    q50 = [20.0, 25.0, 30.0, 40.0, 50.0]
    q90 = [25.0, 35.0, 35.0, 38.0, 55.0]  # pt 3 overflows: 40 > 38

    # Covered points: index 1 (20 in [15, 35]), 2 (30 in [25, 35]), 4 (50 in [45, 55]) -> 3/5 = 60%
    assert math.isclose(interval_coverage(y_true, q10, q90), 0.60)

    underflow, overflow = interval_underflow_overflow(y_true, q10, q90)
    assert math.isclose(underflow, 0.20)
    assert math.isclose(overflow, 0.20)

    # Widths: [13.0, 20.0, 10.0, 3.0, 10.0] -> mean = 56 / 5 = 11.2
    # Sorted widths: [3, 10, 10, 13, 20] -> median = 10.0
    # Relative widths: [13/20, 20/25, 10/30, 3/40, 10/50] = [0.65, 0.80, 0.3333333, 0.075, 0.20]
    # Median relative width = 1/3 (approx 0.333333)
    mean_w, median_w, rel_w = interval_widths(q10, q90, q50)
    assert math.isclose(mean_w, 11.2)
    assert math.isclose(median_w, 10.0)
    assert math.isclose(rel_w, 1.0 / 3.0)

    int_res = evaluate_interval_metrics(y_true, q10, q50, q90)
    assert isinstance(int_res, IntervalMetrics)
    assert math.isclose(int_res.coverage_80, 0.60)
    assert math.isclose(int_res.mean_width, 11.2)
    assert math.isclose(int_res.median_width, 10.0)
    assert math.isclose(int_res.relative_median_width, 1.0 / 3.0)
    assert math.isclose(int_res.underflow_rate_q10, 0.20)
    assert math.isclose(int_res.overflow_rate_q90, 0.20)


@pytest.mark.unit
def test_calibration_and_crossing_metrics() -> None:
    """Verify quantile calibration error and quantile crossing rate calculations."""
    y_true = [10.0, 20.0, 30.0, 40.0]
    # For q=0.50: predictions [15, 25, 25, 35]
    # y <= y_pred: 10<=15 (T), 20<=25 (T), 30<=25 (F), 40<=35 (F) -> 2/4 = 0.50
    # Calibration error = |0.50 - 0.50| = 0.0
    obs_freq, cal_err = quantile_calibration_error(y_true, [15.0, 25.0, 25.0, 35.0], q=0.50)
    assert math.isclose(obs_freq, 0.50)
    assert math.isclose(cal_err, 0.0)

    # Inversion crossing test:
    # Point 0: P10=18 > P50=15 (crossing!)
    # Point 1: P50=25 > P90=22 (crossing!)
    # Point 2: P10=10 <= P50=20 <= P90=30 (clean)
    q10 = [18.0, 20.0, 10.0]
    q50 = [15.0, 25.0, 20.0]
    q90 = [20.0, 22.0, 30.0]

    cnt, rate = quantile_crossing(q10, q50, q90)
    assert cnt == 2
    assert math.isclose(rate, 2.0 / 3.0)

    cal_res = evaluate_calibration_metrics(
        y_true=[10.0, 20.0, 30.0],
        q10_pred=q10,
        q50_pred=q50,
        q90_pred=q90,
    )
    assert isinstance(cal_res, CalibrationMetrics)
    assert cal_res.crossing_count == 2
    assert math.isclose(cal_res.crossing_rate, 2.0 / 3.0)


@pytest.mark.unit
def test_bootstrap_metric_ci_determinism_and_properties() -> None:
    """Verify bootstrap confidence intervals are deterministic, bounded, and reproducible."""
    rng = np.random.default_rng(123)
    y_true = rng.normal(loc=30.0, scale=5.0, size=50)
    y_pred = y_true + rng.normal(loc=0.0, scale=2.0, size=50)

    ci1 = bootstrap_metric_ci(
        y_true,
        y_pred,
        metric_fn=mean_absolute_error,
        n_resamples=500,
        confidence_level=0.95,
        seed=42,
    )
    ci2 = bootstrap_metric_ci(
        y_true,
        y_pred,
        metric_fn=mean_absolute_error,
        n_resamples=500,
        confidence_level=0.95,
        seed=42,
    )

    assert isinstance(ci1, MetricWithCI)
    # Determinism across runs with identical seed
    assert math.isclose(ci1.point_estimate, ci2.point_estimate)
    assert math.isclose(ci1.ci_lower, ci2.ci_lower)
    assert math.isclose(ci1.ci_upper, ci2.ci_upper)

    # Valid CI ordering: lower <= point <= upper
    assert ci1.ci_lower <= ci1.point_estimate <= ci1.ci_upper
    assert ci1.ci_lower < ci1.ci_upper

    # Small sample N=1 fallback
    single_ci = bootstrap_metric_ci([10.0], [12.0], mean_absolute_error, seed=42)
    assert single_ci.point_estimate == 2.0
    assert single_ci.ci_lower == 2.0
    assert single_ci.ci_upper == 2.0


@pytest.mark.unit
def test_polars_series_inputs_compatibility() -> None:
    """Verify metric functions support Polars Series directly as inputs."""
    yt_series = pl.Series("yt", [10.0, 20.0, 30.0])
    yp_series = pl.Series("yp", [11.0, 19.0, 32.0])

    mae_val = mean_absolute_error(yt_series, yp_series)
    assert math.isclose(mae_val, 4.0 / 3.0)

    pinball_val = pinball_loss(yt_series, yp_series, q=0.50)
    assert math.isclose(pinball_val, 0.5 * (4.0 / 3.0))


@pytest.mark.unit
def test_compute_evaluation_report_with_subgroups_and_markdown() -> None:
    """Verify complete evaluation report generates dictionary and markdown with subgroup slices."""
    df = pl.DataFrame(
        {
            "y_true": [10.0, 15.0, 25.0, 35.0, 45.0, 60.0],
            "q10": [8.0, 12.0, 20.0, 30.0, 40.0, 50.0],
            "q50": [10.0, 16.0, 24.0, 34.0, 46.0, 58.0],
            "q90": [14.0, 18.0, 28.0, 38.0, 50.0, 65.0],
            "experience_band": ["0-2", "0-2", "3-5", "3-5", "6-10", "6-10"],
        }
    )

    report = compute_evaluation_report(
        y_true=df["y_true"],
        q10_pred=df["q10"],
        q50_pred=df["q50"],
        q90_pred=df["q90"],
        with_ci=True,
        n_resamples=100,
        seed=42,
        df=df,
        slice_columns=["experience_band"],
    )

    assert isinstance(report, ComprehensiveMetricsReport)
    assert report.point.sample_size == 6
    assert "mae" in report.point_ci
    assert "pinball_q50" in report.point_ci
    assert "experience_band" in report.slices
    assert "0-2" in report.slices["experience_band"]

    # Serialization
    report_dict = report.to_dict()
    assert "point" in report_dict
    assert "slices" in report_dict

    # Markdown rendering
    md = report.to_markdown()
    assert "### Model Evaluation Summary (Rule R-MD-05)" in md
    assert "MAE" in md
    assert "80% Coverage" in md
    assert "Subgroup Slices" in md
    assert "experience_band" in md


@pytest.mark.unit
def test_validation_errors_on_invalid_inputs() -> None:
    """Verify metrics module validates lengths, quantiles, and empty inputs."""
    # Empty input
    with pytest.raises(CompIntelValidationError) as exc1:
        mean_absolute_error([], [])
    assert exc1.value.code == "EMPTY_INPUT_ARRAY"

    # Mismatched lengths
    with pytest.raises(CompIntelValidationError) as exc2:
        mean_absolute_error([10.0, 20.0], [10.0])
    assert exc2.value.code == "ARRAY_LENGTH_MISMATCH"

    # Invalid quantiles
    with pytest.raises(CompIntelValidationError) as exc3:
        pinball_loss([10.0], [10.0], q=0.0)
    assert exc3.value.code == "INVALID_QUANTILE"

    with pytest.raises(CompIntelValidationError) as exc4:
        pinball_loss([10.0], [10.0], q=1.0)
    assert exc4.value.code == "INVALID_QUANTILE"

    # NaN / Inf input values
    with pytest.raises(CompIntelValidationError) as exc5:
        mean_absolute_error([10.0, float("nan")], [10.0, 10.0])
    assert exc5.value.code == "INVALID_ARRAY_VALUES"

    # Invalid bootstrap confidence level
    with pytest.raises(CompIntelValidationError) as exc6:
        bootstrap_metric_ci([10.0, 20.0], [10.0, 20.0], mean_absolute_error, confidence_level=1.5)
    assert exc6.value.code == "INVALID_CONFIDENCE_LEVEL"
