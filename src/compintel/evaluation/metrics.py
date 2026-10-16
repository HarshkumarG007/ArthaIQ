"""Comprehensive evaluation metrics and bootstrap intervals (Task T4.02).

Adheres strictly to:
- Rule R-MD-05: Mandatory baseline evaluation metrics:
  - Point metrics: MAE, median absolute error (MedAE), relative error (MAPE, MdAPE).
    RMSE or R2 alone is never sufficient evidence.
  - Quantile loss: Pinball loss at q in {0.10, 0.50, 0.90}, mean pinball loss.
  - Interval metrics: 80% interval coverage ([P10, P90]), mean width, median width,
    relative median width ((P90 - P10) / P50), underflow rate, overflow rate.
  - Calibration: Quantile coverage error (|freq(y <= q_hat) - q|) across quantiles.
  - Crossing rate: Non-monotonic quantile rate (P10 > P50 or P50 > P90 or P10 > P90).
  - Subgroup slices and confidence intervals.
- Rule R-UQ-01: Uncertainty quantification. No lone numbers; evaluation metrics must report
  bootstrap confidence intervals.
- Rule R-CD-03: Evaluation layer imports only schema and errors; zero dependencies on serving,
  ingestion, or model training.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

import numpy as np
import numpy.typing as npt
import polars as pl

from compintel.errors import CompIntelValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

FloatArray: TypeAlias = npt.NDArray[np.float64]


@dataclass(frozen=True)
class MetricWithCI:
    """Scalar metric estimate paired with a nonparametric bootstrap confidence interval."""

    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence_level: float = 0.95
    n_resamples: int = 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert metric with CI to dictionary."""
        return {
            "point_estimate": self.point_estimate,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "confidence_level": self.confidence_level,
            "n_resamples": self.n_resamples,
        }


@dataclass(frozen=True)
class PointMetrics:
    """Standard point prediction metrics (Rule R-MD-05)."""

    mae: float
    medae: float
    mape: float
    mdape: float
    rmse: float
    sample_size: int

    def to_dict(self) -> dict[str, Any]:
        """Convert point metrics to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class QuantileLossMetrics:
    """Pinball (quantile) loss metrics across target percentiles (Rule R-MD-05)."""

    pinball_q10: float
    pinball_q50: float
    pinball_q90: float
    mean_pinball_loss: float

    def to_dict(self) -> dict[str, Any]:
        """Convert quantile loss metrics to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class IntervalMetrics:
    """Prediction interval metrics for nominal 80% coverage [P10, P90] (Rule R-MD-05)."""

    coverage_80: float
    mean_width: float
    median_width: float
    relative_median_width: float
    underflow_rate_q10: float
    overflow_rate_q90: float

    def to_dict(self) -> dict[str, Any]:
        """Convert interval metrics to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class CalibrationMetrics:
    """Quantile calibration and crossing metrics (Rule R-MD-05)."""

    observed_freq_q10: float
    observed_freq_q50: float
    observed_freq_q90: float
    calibration_error_q10: float
    calibration_error_q50: float
    calibration_error_q90: float
    mean_calibration_error: float
    crossing_count: int
    crossing_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Convert calibration metrics to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class ComprehensiveMetricsReport:
    """Full evaluation metrics report fulfilling Rule R-MD-05 requirements."""

    point: PointMetrics
    quantile_loss: QuantileLossMetrics
    interval: IntervalMetrics
    calibration: CalibrationMetrics
    point_ci: dict[str, MetricWithCI] = field(default_factory=dict)
    slices: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert full report to nested structured dictionary."""
        return {
            "point": self.point.to_dict(),
            "quantile_loss": self.quantile_loss.to_dict(),
            "interval": self.interval.to_dict(),
            "calibration": self.calibration.to_dict(),
            "point_ci": {k: v.to_dict() for k, v in self.point_ci.items()},
            "slices": self.slices,
        }

    def to_markdown(self) -> str:
        """Render report as a GitHub Flavored Markdown table summary."""
        lines: list[str] = [
            "### Model Evaluation Summary (Rule R-MD-05)",
            "",
            "#### Point & Quantile Metrics",
            "| Metric | Value | CI (95%) | Description |",
            "|---|---|---|---|",
        ]

        def format_ci(key: str) -> str:
            if key in self.point_ci:
                ci = self.point_ci[key]
                return f"[{ci.ci_lower:.4f}, {ci.ci_upper:.4f}]"
            return "N/A"

        lines.extend(
            [
                f"| MAE | {self.point.mae:.4f} | {format_ci('mae')} | Mean Absolute Error (LPA) |",
                f"| MedAE | {self.point.medae:.4f} | {format_ci('medae')} | "
                "Median Absolute Error (LPA) |",
                f"| MAPE | {self.point.mape:.4%} | {format_ci('mape')} | "
                "Mean Absolute Percentage Error |",
                f"| MdAPE | {self.point.mdape:.4%} | {format_ci('mdape')} | "
                "Median Absolute Percentage Error |",
                f"| RMSE | {self.point.rmse:.4f} | {format_ci('rmse')} | "
                "Root Mean Squared Error (LPA) |",
                f"| Pinball Q10 | {self.quantile_loss.pinball_q10:.4f} | "
                f"{format_ci('pinball_q10')} | Quantile loss at q=0.10 |",
                f"| Pinball Q50 | {self.quantile_loss.pinball_q50:.4f} | "
                f"{format_ci('pinball_q50')} | Quantile loss at q=0.50 |",
                f"| Pinball Q90 | {self.quantile_loss.pinball_q90:.4f} | "
                f"{format_ci('pinball_q90')} | Quantile loss at q=0.90 |",
                f"| Mean Pinball | {self.quantile_loss.mean_pinball_loss:.4f} | N/A | "
                "Average pinball loss across quantiles |",
                "",
                "#### Interval & Calibration Metrics (Nominal 80% Interval [P10, P90])",
                "| Metric | Value | Target | Evaluation Status |",
                "|---|---|---|---|",
            ]
        )
        cov_status = "PASS" if abs(self.interval.coverage_80 - 0.8) <= 0.05 else "WARN"
        cross_status = "PASS" if self.calibration.crossing_count == 0 else "FAIL"
        cross_desc = f"{cross_status} ({self.calibration.crossing_count} crosses)"
        lines.extend(
            [
                f"| 80% Coverage | {self.interval.coverage_80:.2%} | 80.00% | {cov_status} |",
                f"| Mean Width | {self.interval.mean_width:.4f} LPA | - | Expected dispersion |",
                f"| Median Width | {self.interval.median_width:.4f} LPA | - | Central dispersion |",
                f"| Relative Median Width | {self.interval.relative_median_width:.4f} | - | "
                "(P90 - P10) / P50 |",
                f"| Underflow Rate (y < P10) | {self.interval.underflow_rate_q10:.2%} | 10.00% | "
                "Under-prediction tail |",
                f"| Overflow Rate (y > P90) | {self.interval.overflow_rate_q90:.2%} | 10.00% | "
                "Over-prediction tail |",
                f"| Mean Calibration Error | {self.calibration.mean_calibration_error:.4f} | "
                "0.0000 | Average absolute quantile deviation |",
                f"| Quantile Crossing Rate | {self.calibration.crossing_rate:.2%} | 0.00% | "
                f"{cross_desc} |",
            ]
        )

        if self.slices:
            lines.extend(
                [
                    "",
                    "#### Subgroup Slices",
                    "| Slice Key | Group | Sample Size | MAE | 80% Coverage | Mean Width |",
                    "|---|---|---|---|---|---|",
                ]
            )
            for slice_col, grp_dict in self.slices.items():
                for grp_val, met in grp_dict.items():
                    n_val = met.get("sample_size", "N/A")
                    mae_val = f"{met.get('mae', 0.0):.4f}" if "mae" in met else "N/A"
                    cov_val = (
                        f"{met.get('coverage_80', 0.0):.2%}" if "coverage_80" in met else "N/A"
                    )
                    wid_val = f"{met.get('mean_width', 0.0):.4f}" if "mean_width" in met else "N/A"
                    lines.append(
                        f"| {slice_col} | {grp_val} | {n_val} | {mae_val} | {cov_val} | {wid_val} |"
                    )

        return "\n".join(lines)


# ==============================================================================
# Helper Conversions & Input Validation
# ==============================================================================


def _to_float_array(
    arr: Sequence[float] | FloatArray | pl.Series,
    name: str = "array",
) -> FloatArray:
    """Convert input sequence, series, or array to a 1D float64 NumPy array with validation."""
    if isinstance(arr, pl.Series):
        py_list = arr.to_list()
        res = np.asarray(py_list, dtype=np.float64)
    elif isinstance(arr, np.ndarray):
        res = arr.astype(np.float64)
    else:
        res = np.asarray(list(arr), dtype=np.float64)

    if res.ndim != 1:
        res = res.ravel()

    if len(res) == 0:
        raise CompIntelValidationError(
            f"Input {name} is empty.",
            code="EMPTY_INPUT_ARRAY",
            details={"name": name, "length": 0},
        )

    if np.any(np.isnan(res)) or np.any(np.isinf(res)):
        raise CompIntelValidationError(
            f"Input {name} contains NaN or Inf values.",
            code="INVALID_ARRAY_VALUES",
            details={"name": name},
        )

    return res


def _validate_same_length(*arrays: tuple[FloatArray, str]) -> int:
    """Validate that all provided arrays have identical non-zero lengths."""
    n = len(arrays[0][0])
    for arr, name in arrays[1:]:
        if len(arr) != n:
            raise CompIntelValidationError(
                f"Array length mismatch: {arrays[0][1]} has length {n}, "
                f"but {name} has length {len(arr)}.",
                code="ARRAY_LENGTH_MISMATCH",
                details={
                    "expected_length": n,
                    "array_name": name,
                    "actual_length": len(arr),
                },
            )
    return n


# ==============================================================================
# Point Prediction Metrics
# ==============================================================================


def mean_absolute_error(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
) -> float:
    """Compute Mean Absolute Error (MAE).

    MAE = (1 / N) * sum(|y_true - y_pred|)
    """
    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    _validate_same_length((yt, "y_true"), (yp, "y_pred"))
    return float(np.mean(np.abs(yt - yp)))


def median_absolute_error(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
) -> float:
    """Compute Median Absolute Error (MedAE).

    MedAE = median(|y_true - y_pred|)
    """
    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    _validate_same_length((yt, "y_true"), (yp, "y_pred"))
    return float(np.median(np.abs(yt - yp)))


def mean_absolute_percentage_error(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
    epsilon: float = 1e-8,
) -> float:
    """Compute Mean Absolute Percentage Error (MAPE).

    MAPE = (1 / N) * sum(|y_true - y_pred| / max(|y_true|, epsilon))
    """
    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    _validate_same_length((yt, "y_true"), (yp, "y_pred"))
    denom = np.maximum(np.abs(yt), epsilon)
    return float(np.mean(np.abs(yt - yp) / denom))


def median_absolute_percentage_error(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
    epsilon: float = 1e-8,
) -> float:
    """Compute Median Absolute Percentage Error (MdAPE).

    MdAPE = median(|y_true - y_pred| / max(|y_true|, epsilon))
    """
    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    _validate_same_length((yt, "y_true"), (yp, "y_pred"))
    denom = np.maximum(np.abs(yt), epsilon)
    return float(np.median(np.abs(yt - yp) / denom))


def root_mean_squared_error(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
) -> float:
    """Compute Root Mean Squared Error (RMSE).

    RMSE = sqrt((1 / N) * sum((y_true - y_pred)^2))
    """
    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    _validate_same_length((yt, "y_true"), (yp, "y_pred"))
    return float(math.sqrt(float(np.mean((yt - yp) ** 2))))


def evaluate_point_metrics(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
) -> PointMetrics:
    """Compute comprehensive suite of point prediction metrics."""
    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    n = _validate_same_length((yt, "y_true"), (yp, "y_pred"))
    return PointMetrics(
        mae=mean_absolute_error(yt, yp),
        medae=median_absolute_error(yt, yp),
        mape=mean_absolute_percentage_error(yt, yp),
        mdape=median_absolute_percentage_error(yt, yp),
        rmse=root_mean_squared_error(yt, yp),
        sample_size=n,
    )


# ==============================================================================
# Quantile Loss (Pinball Loss)
# ==============================================================================


def pinball_loss_array(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
    q: float,
) -> FloatArray:
    """Compute elementwise pinball (quantile) loss array for quantile q.

    L_q(y, y_hat) = max(q * (y - y_hat), (q - 1) * (y - y_hat))
    """
    if not (0.0 < q < 1.0):
        raise CompIntelValidationError(
            f"Quantile q must be strictly between 0 and 1, got {q}.",
            code="INVALID_QUANTILE",
            details={"q": q},
        )
    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    _validate_same_length((yt, "y_true"), (yp, "y_pred"))

    diff = yt - yp
    return np.maximum(q * diff, (q - 1.0) * diff)


def pinball_loss(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
    q: float,
) -> float:
    """Compute mean pinball (quantile) loss for quantile q in (0, 1)."""
    return float(np.mean(pinball_loss_array(y_true, y_pred, q)))


def evaluate_quantile_metrics(
    y_true: Sequence[float] | FloatArray | pl.Series,
    q10_pred: Sequence[float] | FloatArray | pl.Series,
    q50_pred: Sequence[float] | FloatArray | pl.Series,
    q90_pred: Sequence[float] | FloatArray | pl.Series,
) -> QuantileLossMetrics:
    """Compute pinball losses across {0.10, 0.50, 0.90} and average pinball loss."""
    l10 = pinball_loss(y_true, q10_pred, q=0.10)
    l50 = pinball_loss(y_true, q50_pred, q=0.50)
    l90 = pinball_loss(y_true, q90_pred, q=0.90)
    mean_l = (l10 + l50 + l90) / 3.0
    return QuantileLossMetrics(
        pinball_q10=l10,
        pinball_q50=l50,
        pinball_q90=l90,
        mean_pinball_loss=mean_l,
    )


# ==============================================================================
# Interval Metrics (Coverage & Widths)
# ==============================================================================


def interval_coverage(
    y_true: Sequence[float] | FloatArray | pl.Series,
    q_lower: Sequence[float] | FloatArray | pl.Series,
    q_upper: Sequence[float] | FloatArray | pl.Series,
) -> float:
    """Compute empirical coverage rate: proportion where q_lower <= y_true <= q_upper."""
    yt = _to_float_array(y_true, "y_true")
    ql = _to_float_array(q_lower, "q_lower")
    qu = _to_float_array(q_upper, "q_upper")
    _validate_same_length((yt, "y_true"), (ql, "q_lower"), (qu, "q_upper"))
    covered = (yt >= ql) & (yt <= qu)
    return float(np.mean(covered))


def interval_underflow_overflow(
    y_true: Sequence[float] | FloatArray | pl.Series,
    q_lower: Sequence[float] | FloatArray | pl.Series,
    q_upper: Sequence[float] | FloatArray | pl.Series,
) -> tuple[float, float]:
    """Compute tail underflow rate (y < q_lower) and overflow rate (y > q_upper)."""
    yt = _to_float_array(y_true, "y_true")
    ql = _to_float_array(q_lower, "q_lower")
    qu = _to_float_array(q_upper, "q_upper")
    _validate_same_length((yt, "y_true"), (ql, "q_lower"), (qu, "q_upper"))
    underflow = float(np.mean(yt < ql))
    overflow = float(np.mean(yt > qu))
    return underflow, overflow


def interval_widths(
    q_lower: Sequence[float] | FloatArray | pl.Series,
    q_upper: Sequence[float] | FloatArray | pl.Series,
    q_central: Sequence[float] | FloatArray | pl.Series | None = None,
    epsilon: float = 1e-8,
) -> tuple[float, float, float]:
    """Compute mean width, median width, and relative median width.

    Returns:
        (mean_width, median_width, relative_median_width)
    """
    ql = _to_float_array(q_lower, "q_lower")
    qu = _to_float_array(q_upper, "q_upper")
    _validate_same_length((ql, "q_lower"), (qu, "q_upper"))

    widths = qu - ql
    mean_w = float(np.mean(widths))
    median_w = float(np.median(widths))

    if q_central is not None:
        qc = _to_float_array(q_central, "q_central")
        _validate_same_length((widths, "widths"), (qc, "q_central"))
        rel_median_w = float(np.median(widths / np.maximum(np.abs(qc), epsilon)))
    else:
        rel_median_w = 0.0

    return mean_w, median_w, rel_median_w


def evaluate_interval_metrics(
    y_true: Sequence[float] | FloatArray | pl.Series,
    q10_pred: Sequence[float] | FloatArray | pl.Series,
    q50_pred: Sequence[float] | FloatArray | pl.Series,
    q90_pred: Sequence[float] | FloatArray | pl.Series,
) -> IntervalMetrics:
    """Compute full set of prediction interval metrics for nominal 80% interval [P10, P90]."""
    cov = interval_coverage(y_true, q10_pred, q90_pred)
    underflow, overflow = interval_underflow_overflow(y_true, q10_pred, q90_pred)
    mean_w, median_w, rel_median_w = interval_widths(q10_pred, q90_pred, q50_pred)
    return IntervalMetrics(
        coverage_80=cov,
        mean_width=mean_w,
        median_width=median_w,
        relative_median_width=rel_median_w,
        underflow_rate_q10=underflow,
        overflow_rate_q90=overflow,
    )


# ==============================================================================
# Calibration & Quantile Crossing Metrics
# ==============================================================================


def quantile_calibration_error(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
    q: float,
) -> tuple[float, float]:
    """Compute observed coverage frequency and absolute calibration error for quantile q.

    Returns:
        (observed_frequency, calibration_error) where:
        observed_frequency = (1 / N) * sum(I(y_true <= y_pred))
        calibration_error = |observed_frequency - q|
    """
    if not (0.0 < q < 1.0):
        raise CompIntelValidationError(
            f"Quantile q must be strictly between 0 and 1, got {q}.",
            code="INVALID_QUANTILE",
            details={"q": q},
        )
    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    _validate_same_length((yt, "y_true"), (yp, "y_pred"))

    obs_freq = float(np.mean(yt <= yp))
    cal_err = float(abs(obs_freq - q))
    return obs_freq, cal_err


def quantile_crossing(
    q10_pred: Sequence[float] | FloatArray | pl.Series,
    q50_pred: Sequence[float] | FloatArray | pl.Series,
    q90_pred: Sequence[float] | FloatArray | pl.Series,
) -> tuple[int, float]:
    """Detect quantile crossings: instances where P10 > P50, P50 > P90, or P10 > P90.

    Returns:
        (crossing_count, crossing_rate)
    """
    q10 = _to_float_array(q10_pred, "q10_pred")
    q50 = _to_float_array(q50_pred, "q50_pred")
    q90 = _to_float_array(q90_pred, "q90_pred")
    _validate_same_length((q10, "q10_pred"), (q50, "q50_pred"), (q90, "q90_pred"))

    is_crossed = (q10 > q50) | (q50 > q90) | (q10 > q90)
    count = int(np.sum(is_crossed))
    rate = float(count / len(q10))
    return count, rate


def evaluate_calibration_metrics(
    y_true: Sequence[float] | FloatArray | pl.Series,
    q10_pred: Sequence[float] | FloatArray | pl.Series,
    q50_pred: Sequence[float] | FloatArray | pl.Series,
    q90_pred: Sequence[float] | FloatArray | pl.Series,
) -> CalibrationMetrics:
    """Compute calibration errors for {0.10, 0.50, 0.90} and crossing rate."""
    f10, e10 = quantile_calibration_error(y_true, q10_pred, q=0.10)
    f50, e50 = quantile_calibration_error(y_true, q50_pred, q=0.50)
    f90, e90 = quantile_calibration_error(y_true, q90_pred, q=0.90)
    mean_cal_err = (e10 + e50 + e90) / 3.0

    cross_cnt, cross_rate = quantile_crossing(q10_pred, q50_pred, q90_pred)

    return CalibrationMetrics(
        observed_freq_q10=f10,
        observed_freq_q50=f50,
        observed_freq_q90=f90,
        calibration_error_q10=e10,
        calibration_error_q50=e50,
        calibration_error_q90=e90,
        mean_calibration_error=mean_cal_err,
        crossing_count=cross_cnt,
        crossing_rate=cross_rate,
    )


# ==============================================================================
# Nonparametric Bootstrap Confidence Intervals (Rule R-UQ-01)
# ==============================================================================


def bootstrap_metric_ci(
    y_true: Sequence[float] | FloatArray | pl.Series,
    y_pred: Sequence[float] | FloatArray | pl.Series,
    metric_fn: Callable[[FloatArray, FloatArray], float],
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> MetricWithCI:
    """Compute nonparametric percentile bootstrap confidence interval for a metric function.

    Args:
        y_true: Ground truth target values.
        y_pred: Model predictions.
        metric_fn: Function mapping (y_true_subset, y_pred_subset) -> scalar float metric.
        n_resamples: Number of bootstrap iterations (default 1000).
        confidence_level: Nominal confidence level (e.g., 0.95 for 95% CI).
        seed: Random seed for deterministic reproducibility.

    Returns:
        MetricWithCI containing point estimate and (ci_lower, ci_upper) bounds.
    """
    if not (0.0 < confidence_level < 1.0):
        raise CompIntelValidationError(
            f"confidence_level must be between 0 and 1, got {confidence_level}.",
            code="INVALID_CONFIDENCE_LEVEL",
            details={"confidence_level": confidence_level},
        )
    if n_resamples <= 0:
        raise CompIntelValidationError(
            f"n_resamples must be positive, got {n_resamples}.",
            code="INVALID_RESAMPLES",
            details={"n_resamples": n_resamples},
        )

    yt = _to_float_array(y_true, "y_true")
    yp = _to_float_array(y_pred, "y_pred")
    n = _validate_same_length((yt, "y_true"), (yp, "y_pred"))

    point_est = float(metric_fn(yt, yp))

    if n < 2:
        return MetricWithCI(
            point_estimate=point_est,
            ci_lower=point_est,
            ci_upper=point_est,
            confidence_level=confidence_level,
            n_resamples=n_resamples,
        )

    rng = np.random.default_rng(seed)
    boot_metrics = np.empty(n_resamples, dtype=np.float64)

    for b in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        boot_metrics[b] = metric_fn(yt[idx], yp[idx])

    alpha = 1.0 - confidence_level
    lower_pct = 100.0 * (alpha / 2.0)
    upper_pct = 100.0 * (1.0 - alpha / 2.0)

    ci_lower = float(np.percentile(boot_metrics, lower_pct))
    ci_upper = float(np.percentile(boot_metrics, upper_pct))

    return MetricWithCI(
        point_estimate=point_est,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        confidence_level=confidence_level,
        n_resamples=n_resamples,
    )


# ==============================================================================
# Comprehensive Evaluation & Subgroup Slicing
# ==============================================================================


def compute_evaluation_report(
    y_true: Sequence[float] | FloatArray | pl.Series,
    q10_pred: Sequence[float] | FloatArray | pl.Series,
    q50_pred: Sequence[float] | FloatArray | pl.Series,
    q90_pred: Sequence[float] | FloatArray | pl.Series,
    with_ci: bool = True,
    n_resamples: int = 500,
    confidence_level: float = 0.95,
    seed: int = 42,
    df: pl.DataFrame | None = None,
    slice_columns: Sequence[str] | None = None,
) -> ComprehensiveMetricsReport:
    """Compute complete evaluation metrics report meeting Rule R-MD-05.

    Args:
        y_true: Ground truth actual compensation.
        q10_pred: P10 quantile prediction.
        q50_pred: P50 (median) quantile / point prediction.
        q90_pred: P90 quantile prediction.
        with_ci: Whether to compute bootstrap confidence intervals for primary metrics.
        n_resamples: Number of bootstrap iterations for CI.
        confidence_level: Nominal confidence level (default 0.95).
        seed: Random seed for bootstrap.
        df: Optional Polars DataFrame containing observation records for subgroup slicing.
        slice_columns: Column names in df to compute subgroup slices for.

    Returns:
        ComprehensiveMetricsReport with point, quantile, interval, calibration, and sliced metrics.
    """
    yt = _to_float_array(y_true, "y_true")
    q10 = _to_float_array(q10_pred, "q10_pred")
    q50 = _to_float_array(q50_pred, "q50_pred")
    q90 = _to_float_array(q90_pred, "q90_pred")
    _validate_same_length(
        (yt, "y_true"),
        (q10, "q10_pred"),
        (q50, "q50_pred"),
        (q90, "q90_pred"),
    )

    point_met = evaluate_point_metrics(yt, q50)
    q_met = evaluate_quantile_metrics(yt, q10, q50, q90)
    int_met = evaluate_interval_metrics(yt, q10, q50, q90)
    cal_met = evaluate_calibration_metrics(yt, q10, q50, q90)

    point_cis: dict[str, MetricWithCI] = {}
    if with_ci:
        point_cis["mae"] = bootstrap_metric_ci(
            yt, q50, mean_absolute_error, n_resamples, confidence_level, seed
        )
        point_cis["medae"] = bootstrap_metric_ci(
            yt, q50, median_absolute_error, n_resamples, confidence_level, seed + 1
        )
        point_cis["mape"] = bootstrap_metric_ci(
            yt, q50, mean_absolute_percentage_error, n_resamples, confidence_level, seed + 2
        )
        point_cis["mdape"] = bootstrap_metric_ci(
            yt, q50, median_absolute_percentage_error, n_resamples, confidence_level, seed + 3
        )
        point_cis["rmse"] = bootstrap_metric_ci(
            yt, q50, root_mean_squared_error, n_resamples, confidence_level, seed + 4
        )
        point_cis["pinball_q10"] = bootstrap_metric_ci(
            yt,
            q10,
            lambda y, p: pinball_loss(y, p, q=0.10),
            n_resamples,
            confidence_level,
            seed + 5,
        )
        point_cis["pinball_q50"] = bootstrap_metric_ci(
            yt,
            q50,
            lambda y, p: pinball_loss(y, p, q=0.50),
            n_resamples,
            confidence_level,
            seed + 6,
        )
        point_cis["pinball_q90"] = bootstrap_metric_ci(
            yt,
            q90,
            lambda y, p: pinball_loss(y, p, q=0.90),
            n_resamples,
            confidence_level,
            seed + 7,
        )

    slices_res: dict[str, dict[str, Any]] = {}
    if df is not None and slice_columns is not None:
        if df.height != len(yt):
            raise CompIntelValidationError(
                f"DataFrame height ({df.height}) does not match metric sample size ({len(yt)}).",
                code="DATAFRAME_LENGTH_MISMATCH",
            )
        eval_df = df.with_columns(
            pl.Series("__yt", yt),
            pl.Series("__q10", q10),
            pl.Series("__q50", q50),
            pl.Series("__q90", q90),
        )

        for col in slice_columns:
            if col not in eval_df.columns:
                continue
            col_slices: dict[str, Any] = {}
            unique_vals = eval_df[col].drop_nulls().unique().to_list()
            for uval in unique_vals:
                sub_df = eval_df.filter(pl.col(col) == uval)
                if sub_df.height < 2:
                    continue
                sub_yt = sub_df["__yt"]
                sub_q10 = sub_df["__q10"]
                sub_q50 = sub_df["__q50"]
                sub_q90 = sub_df["__q90"]
                sub_mae = mean_absolute_error(sub_yt, sub_q50)
                sub_cov = interval_coverage(sub_yt, sub_q10, sub_q90)
                sub_w, _, _ = interval_widths(sub_q10, sub_q90, sub_q50)
                col_slices[str(uval)] = {
                    "sample_size": sub_df.height,
                    "mae": sub_mae,
                    "coverage_80": sub_cov,
                    "mean_width": sub_w,
                }
            if col_slices:
                slices_res[col] = col_slices

    return ComprehensiveMetricsReport(
        point=point_met,
        quantile_loss=q_met,
        interval=int_met,
        calibration=cal_met,
        point_ci=point_cis,
        slices=slices_res,
    )
