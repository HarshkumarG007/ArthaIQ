"""Conformal prediction intervals and calibration (Rung F, ADR-0004 & ADR-0005).

Implements:
- Split Conformal prediction on point model residuals.
- Conformalized Quantile Regression (CQR; Romano, Patterson, Candes 2019) on base quantile models.
- Explicit documentation of marginal guarantees and exchangeability assumptions (Rule R-UQ-03).
- Monotonicity and non-negativity protection (Rule R-UQ-05).
- Thin-evidence abstention propagation (Rule R-MD-08).

Adheres to:
- Rule R-MD-01: Benchmark ladder Rung F for interval calibration.
- Rule R-MD-03: Temporal calibration set isolation.
- Rule R-UQ-01: No lone numbers; full [P10, P90] interval with P50.
- Rule R-UQ-03: Conformal guarantees are marginal, assume exchangeability, and document limitations.
- Rule R-UQ-05: Crossing detection and monotonic projection repair.
- Rule R-CD-01: Strict typing and full mypy compliance.
- Rule R-CD-03 & Import Linter: Zero imports of serving, evaluation, ingestion, or quality.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import numpy as np
import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from collections.abc import Sequence

    from compintel.models.gbm.point import BaseGBMPointModel
    from compintel.models.gbm.quantile import BaseGBMQuantileModel


class ConformalMethod(StrEnum):
    """Supported conformal prediction calibration methods."""

    CQR = "cqr"
    SPLIT_CONFORMAL = "split_conformal"


class ConformalConfig(BaseModel):
    """Configuration schema for conformal prediction calibrator.

    Adheres to Rules R-UQ-01, R-UQ-03, and R-UQ-05.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    method: ConformalMethod = Field(
        default=ConformalMethod.CQR,
        description="Conformal calibration method (CQR or split_conformal).",
    )
    nominal_coverage: float = Field(
        default=0.80,
        gt=0.50,
        lt=1.00,
        description="Nominal marginal coverage target (1 - alpha), e.g. 0.80 for [P10, P90].",
    )
    min_pay_bound_lpa: float = Field(
        default=0.50,
        ge=0.0,
        description="Statutory non-negativity floor in nominal INR LPA.",
    )
    repair_crossing: bool = Field(
        default=True,
        description="Whether to apply monotonic projection repair if calibrated bounds cross.",
    )

    @field_validator("nominal_coverage")
    @classmethod
    def validate_coverage(cls, v: float) -> float:
        """Validate coverage is strictly inside standard interval bounds."""
        if not (0.50 < v < 1.00):
            raise ValueError(f"nominal_coverage must be in (0.50, 1.00), got {v}.")
        return v


@dataclass(frozen=True)
class ConformalAssumptions:
    """Formal mathematical assumptions underlying conformal coverage guarantees (Rule R-UQ-03)."""

    is_marginal: bool = True
    claims_individual_coverage: bool = False
    requires_exchangeability: bool = True
    temporal_drift_warning: bool = True
    calibration_split: str = "calibrate"
    target_measure: str = "guaranteed_cash_annual"
    description: str = (
        "Conformal prediction intervals guarantee marginal coverage (1 - alpha) "
        "averaged across the population under exchangeability. They do NOT guarantee "
        "conditional coverage for specific individuals or subgroups. Macroeconomic drift, "
        "compensation inflation, and shifting occupational mixes can degrade empirical "
        "coverage over time; calibration sets must be updated on recent temporal windows."
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert assumptions to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class ConformalCalibrationSummary:
    """Structured summary of the fitted conformal calibrator on the calibration set."""

    method: str
    nominal_coverage: float
    n_calibration_samples: int
    conformal_quantile_value: float
    empirical_calibration_coverage: float
    mean_calibration_width: float
    median_calibration_width: float
    min_pay_bound_lpa: float
    assumptions: ConformalAssumptions = field(default_factory=ConformalAssumptions)

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary representation."""
        res = asdict(self)
        res["assumptions"] = self.assumptions.to_dict()
        return res


@dataclass(frozen=True)
class CalibratedPrediction:
    """Structured calibrated interval prediction conforming to Rules R-UQ-01, R-UQ-03, R-UQ-05."""

    p10_calibrated: float | None
    p50: float | None
    p90_calibrated: float | None
    p10_uncalibrated: float | None
    p90_uncalibrated: float | None
    conformal_correction: float
    is_crossing_repaired: bool
    is_abstained: bool
    abstention_reason: str | None = None
    nominal_coverage: float = 0.80
    method: str = "CQR"
    target_measure: str = "guaranteed_cash_annual"
    currency: str = "INR"
    nominal_basis: bool = True
    assumptions: ConformalAssumptions = field(default_factory=ConformalAssumptions)

    def to_dict(self) -> dict[str, Any]:
        """Convert calibrated prediction to dictionary representation."""
        res = asdict(self)
        res["assumptions"] = self.assumptions.to_dict()
        return res


def compute_conformal_quantile(scores: Sequence[float] | np.ndarray, alpha: float) -> float:
    """Compute the finite-sample conformal quantile critical value.

    Calculates the ceil((n + 1)(1 - alpha)) / n empirical quantile over conformity scores.

    Args:
        scores: 1D array of non-conformity scores from the calibration set.
        alpha: Miscoverage rate (alpha = 1 - nominal_coverage, e.g. 0.20 for 80% coverage).

    Returns:
        Critical non-conformity score quantile q_hat.
    """
    arr = np.asarray(scores, dtype=np.float64)
    n = len(arr)
    if n == 0:
        raise ValueError("Cannot compute conformal quantile on empty scores array.")

    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        # Sample size too small for formal finite-sample guarantee without extrapolation;
        # take maximum score as conservative fallback.
        return float(np.max(arr))

    sorted_scores = np.sort(arr)
    # k is 1-indexed rank
    return float(sorted_scores[k - 1])


class ConformalQuantileRegressor:
    """Conformalized Quantile Regression (CQR) calibrator (Romano et al. 2019, Rung F).

    Calibrates a base quantile model using non-conformity scores on a temporal calibration set:
        E_i = max(q_lo(X_i) - Y_i, Y_i - q_hi(X_i))
    Yielding adaptive prediction intervals:
        C(X) = [q_lo(X) - q_hat, q_hi(X) + q_hat]
    with finite-sample marginal coverage guarantees (Rule R-UQ-03).
    """

    def __init__(
        self,
        base_model: BaseGBMQuantileModel,
        config: ConformalConfig | None = None,
    ) -> None:
        """Initialize CQR calibrator with a trained base quantile model.

        Args:
            base_model: Fitted BaseGBMQuantileModel predicting conditional quantiles.
            config: ConformalConfig specifying nominal coverage and boundary parameters.
        """
        if not base_model.is_fitted:
            raise RuntimeError("Base quantile model must be fitted before conformal calibration.")

        self.base_model: BaseGBMQuantileModel = base_model
        if config is None:
            self.config = ConformalConfig(method=ConformalMethod.CQR)
        elif config.method != ConformalMethod.CQR:
            self.config = config.model_copy(update={"method": ConformalMethod.CQR})
        else:
            self.config = config

        self._is_calibrated: bool = False
        self._conformal_quantile: float = 0.0
        self._summary: ConformalCalibrationSummary | None = None
        self._target_col: str = "guaranteed_cash_annual"

    @property
    def is_calibrated(self) -> bool:
        """Return True if calibrator has been fitted on a calibration set."""
        return self._is_calibrated

    @property
    def summary(self) -> ConformalCalibrationSummary | None:
        """Return calibration summary metrics and formal assumptions."""
        return self._summary

    @property
    def conformal_quantile(self) -> float:
        """Return calibrated conformal quantile correction (q_hat)."""
        return self._conformal_quantile

    def calibrate(self, calibration_df: pl.DataFrame) -> ConformalQuantileRegressor:
        """Fit conformal calibration scores on a temporal calibration partition.

        Args:
            calibration_df: Polars DataFrame containing profile features and target pay.

        Returns:
            Self (calibrated regressor instance).
        """
        if self._target_col not in calibration_df.columns:
            msg = f"Target column '{self._target_col}' missing from calibration DataFrame."
            raise ValueError(msg)

        if len(calibration_df) == 0:
            raise ValueError("Cannot calibrate conformal model on empty DataFrame.")

        # Filter out abstained records from calibration set to evaluate on valid cohort
        base_preds = self.base_model.predict(calibration_df)
        y_true = calibration_df.get_column(self._target_col).to_numpy()

        scores: list[float] = []
        covered_count = 0
        widths: list[float] = []

        for i, p in enumerate(base_preds):
            if p.is_abstained or p.p10 is None or p.p90 is None:
                continue

            yt = float(y_true[i])
            # CQR non-conformity score: E_i = max(q10 - y, y - q90)
            score = max(p.p10 - yt, yt - p.p90)
            scores.append(score)

        if not scores:
            raise ValueError("All calibration records were abstained; insufficient support.")

        alpha = 1.0 - self.config.nominal_coverage
        self._conformal_quantile = compute_conformal_quantile(scores, alpha)

        # Compute empirical calibration coverage and interval widths under calibration
        for i, p in enumerate(base_preds):
            if p.is_abstained or p.p10 is None or p.p90 is None:
                continue

            yt = float(y_true[i])
            lo = max(self.config.min_pay_bound_lpa, p.p10 - self._conformal_quantile)
            hi = max(lo, p.p90 + self._conformal_quantile)

            if lo <= yt <= hi:
                covered_count += 1
            widths.append(hi - lo)

        n_cal = len(scores)
        emp_coverage = float(covered_count / n_cal) if n_cal > 0 else 0.0
        mean_w = float(np.mean(widths)) if widths else 0.0
        median_w = float(np.median(widths)) if widths else 0.0

        self._summary = ConformalCalibrationSummary(
            method=self.config.method.value,
            nominal_coverage=self.config.nominal_coverage,
            n_calibration_samples=n_cal,
            conformal_quantile_value=self._conformal_quantile,
            empirical_calibration_coverage=emp_coverage,
            mean_calibration_width=mean_w,
            median_calibration_width=median_w,
            min_pay_bound_lpa=self.config.min_pay_bound_lpa,
            assumptions=ConformalAssumptions(
                calibration_split="calibrate",
                target_measure=self._target_col,
            ),
        )
        self._is_calibrated = True
        return self

    def predict(self, df: pl.DataFrame) -> list[CalibratedPrediction]:
        """Produce calibrated prediction intervals for test observations.

        Adheres to Rules R-UQ-01, R-UQ-03, R-UQ-05, and R-MD-08.

        Args:
            df: Polars DataFrame of query observations.

        Returns:
            List of CalibratedPrediction instances with conformal guarantees.
        """
        if not self._is_calibrated:
            raise RuntimeError("ConformalQuantileRegressor must be calibrated before predict.")

        n = len(df)
        if n == 0:
            return []

        base_preds = self.base_model.predict(df)
        calibrated: list[CalibratedPrediction] = []

        for p in base_preds:
            if p.is_abstained or p.p10 is None or p.p90 is None or p.p50 is None:
                calibrated.append(
                    CalibratedPrediction(
                        p10_calibrated=None,
                        p50=None,
                        p90_calibrated=None,
                        p10_uncalibrated=p.p10,
                        p90_uncalibrated=p.p90,
                        conformal_correction=self._conformal_quantile,
                        is_crossing_repaired=False,
                        is_abstained=True,
                        abstention_reason=p.abstention_reason or "THIN_EVIDENCE",
                        nominal_coverage=self.config.nominal_coverage,
                        method=self.config.method.value,
                    )
                )
                continue

            # Apply conformal quantile adjustment
            raw_lo = p.p10 - self._conformal_quantile
            raw_hi = p.p90 + self._conformal_quantile
            raw_mid = p.p50

            # Statutory non-negativity bound
            lo = max(self.config.min_pay_bound_lpa, raw_lo)
            hi = max(lo, raw_hi)

            # Monotonic ordering check and repair (Rule R-UQ-05)
            is_crossing = lo > raw_mid or raw_mid > hi or lo > hi
            if self.config.repair_crossing and is_crossing:
                sorted_vals = sorted([lo, raw_mid, hi])
                lo_final = sorted_vals[0]
                mid_final = sorted_vals[1]
                hi_final = sorted_vals[2]
            else:
                lo_final = lo
                mid_final = raw_mid
                hi_final = hi

            calibrated.append(
                CalibratedPrediction(
                    p10_calibrated=round(lo_final, 2),
                    p50=round(mid_final, 2),
                    p90_calibrated=round(hi_final, 2),
                    p10_uncalibrated=p.p10,
                    p90_uncalibrated=p.p90,
                    conformal_correction=round(self._conformal_quantile, 4),
                    is_crossing_repaired=is_crossing or p.is_crossing_repaired,
                    is_abstained=False,
                    abstention_reason=None,
                    nominal_coverage=self.config.nominal_coverage,
                    method=self.config.method.value,
                )
            )

        return calibrated

    def predict_df(self, df: pl.DataFrame) -> pl.DataFrame:
        """Generate calibrated prediction intervals as a Polars DataFrame.

        Args:
            df: Input Polars DataFrame.

        Returns:
            Polars DataFrame containing calibrated quantiles, uncalibrated quantiles,
            correction factor, and diagnostics.
        """
        preds = self.predict(df)
        if not preds:
            return pl.DataFrame(
                schema={
                    "p10_calibrated": pl.Float64,
                    "p50": pl.Float64,
                    "p90_calibrated": pl.Float64,
                    "p10_uncalibrated": pl.Float64,
                    "p90_uncalibrated": pl.Float64,
                    "conformal_correction": pl.Float64,
                    "is_crossing_repaired": pl.Boolean,
                    "is_abstained": pl.Boolean,
                    "abstention_reason": pl.String,
                    "nominal_coverage": pl.Float64,
                    "method": pl.String,
                }
            )

        return pl.DataFrame(
            {
                "p10_calibrated": [p.p10_calibrated for p in preds],
                "p50": [p.p50 for p in preds],
                "p90_calibrated": [p.p90_calibrated for p in preds],
                "p10_uncalibrated": [p.p10_uncalibrated for p in preds],
                "p90_uncalibrated": [p.p90_uncalibrated for p in preds],
                "conformal_correction": [p.conformal_correction for p in preds],
                "is_crossing_repaired": [p.is_crossing_repaired for p in preds],
                "is_abstained": [p.is_abstained for p in preds],
                "abstention_reason": [p.abstention_reason for p in preds],
                "nominal_coverage": [p.nominal_coverage for p in preds],
                "method": [p.method for p in preds],
            },
            schema={
                "p10_calibrated": pl.Float64,
                "p50": pl.Float64,
                "p90_calibrated": pl.Float64,
                "p10_uncalibrated": pl.Float64,
                "p90_uncalibrated": pl.Float64,
                "conformal_correction": pl.Float64,
                "is_crossing_repaired": pl.Boolean,
                "is_abstained": pl.Boolean,
                "abstention_reason": pl.String,
                "nominal_coverage": pl.Float64,
                "method": pl.String,
            },
        )


class SplitConformalCalibrator:
    """Split Conformal calibrator on point models (Rung F baseline).

    Computes absolute residuals R_i = |Y_i - y_hat_i| on the calibration partition and forms
    symmetric intervals around point predictions:
        C(X) = [y_hat(X) - r_hat, y_hat(X) + r_hat]
    """

    def __init__(
        self,
        base_model: BaseGBMPointModel,
        config: ConformalConfig | None = None,
    ) -> None:
        """Initialize Split Conformal calibrator with a trained point model."""
        if not base_model.is_fitted:
            raise RuntimeError("Base point model must be fitted before conformal calibration.")

        self.base_model: BaseGBMPointModel = base_model
        if config is None:
            self.config = ConformalConfig(method=ConformalMethod.SPLIT_CONFORMAL)
        elif config.method != ConformalMethod.SPLIT_CONFORMAL:
            self.config = config.model_copy(update={"method": ConformalMethod.SPLIT_CONFORMAL})
        else:
            self.config = config
        self._is_calibrated: bool = False
        self._conformal_radius: float = 0.0
        self._summary: ConformalCalibrationSummary | None = None
        self._target_col: str = "guaranteed_cash_annual"

    @property
    def is_calibrated(self) -> bool:
        """Return True if calibrator has been fitted on a calibration set."""
        return self._is_calibrated

    @property
    def summary(self) -> ConformalCalibrationSummary | None:
        """Return calibration summary metrics and formal assumptions."""
        return self._summary

    @property
    def conformal_radius(self) -> float:
        """Return calibrated conformal radius (r_hat)."""
        return self._conformal_radius

    def calibrate(self, calibration_df: pl.DataFrame) -> SplitConformalCalibrator:
        """Fit conformal radius on a temporal calibration partition.

        Args:
            calibration_df: Polars DataFrame containing features and target pay.

        Returns:
            Self (calibrated instance).
        """
        if self._target_col not in calibration_df.columns:
            msg = f"Target column '{self._target_col}' missing from calibration DataFrame."
            raise ValueError(msg)

        if len(calibration_df) == 0:
            raise ValueError("Cannot calibrate conformal model on empty DataFrame.")

        base_preds = self.base_model.predict(calibration_df)
        y_true = calibration_df.get_column(self._target_col).to_numpy()

        residuals: list[float] = []
        for i, p in enumerate(base_preds):
            if p.is_abstained or math.isnan(p.predicted_pay_lpa):
                continue
            yt = float(y_true[i])
            residuals.append(abs(yt - p.predicted_pay_lpa))

        if not residuals:
            raise ValueError("All calibration records were abstained; insufficient support.")

        alpha = 1.0 - self.config.nominal_coverage
        self._conformal_radius = compute_conformal_quantile(residuals, alpha)

        covered_count = 0
        widths: list[float] = []
        for i, p in enumerate(base_preds):
            if p.is_abstained or math.isnan(p.predicted_pay_lpa):
                continue
            yt = float(y_true[i])
            lo = max(self.config.min_pay_bound_lpa, p.predicted_pay_lpa - self._conformal_radius)
            hi = p.predicted_pay_lpa + self._conformal_radius
            if lo <= yt <= hi:
                covered_count += 1
            widths.append(hi - lo)

        n_cal = len(residuals)
        emp_coverage = float(covered_count / n_cal) if n_cal > 0 else 0.0

        self._summary = ConformalCalibrationSummary(
            method=self.config.method.value,
            nominal_coverage=self.config.nominal_coverage,
            n_calibration_samples=n_cal,
            conformal_quantile_value=self._conformal_radius,
            empirical_calibration_coverage=emp_coverage,
            mean_calibration_width=float(np.mean(widths)) if widths else 0.0,
            median_calibration_width=float(np.median(widths)) if widths else 0.0,
            min_pay_bound_lpa=self.config.min_pay_bound_lpa,
            assumptions=ConformalAssumptions(
                calibration_split="calibrate",
                target_measure=self._target_col,
            ),
        )
        self._is_calibrated = True
        return self

    def predict(self, df: pl.DataFrame) -> list[CalibratedPrediction]:
        """Produce calibrated prediction intervals for test observations.

        Args:
            df: Input Polars DataFrame.

        Returns:
            List of CalibratedPrediction instances with split conformal intervals.
        """
        if not self._is_calibrated:
            raise RuntimeError("SplitConformalCalibrator must be calibrated before predict.")

        n = len(df)
        if n == 0:
            return []

        base_preds = self.base_model.predict(df)
        calibrated: list[CalibratedPrediction] = []

        for p in base_preds:
            if p.is_abstained or math.isnan(p.predicted_pay_lpa):
                calibrated.append(
                    CalibratedPrediction(
                        p10_calibrated=None,
                        p50=None,
                        p90_calibrated=None,
                        p10_uncalibrated=None,
                        p90_uncalibrated=None,
                        conformal_correction=self._conformal_radius,
                        is_crossing_repaired=False,
                        is_abstained=True,
                        abstention_reason=p.abstention_reason or "THIN_EVIDENCE",
                        nominal_coverage=self.config.nominal_coverage,
                        method=self.config.method.value,
                    )
                )
                continue

            point_est = p.predicted_pay_lpa
            lo = max(self.config.min_pay_bound_lpa, point_est - self._conformal_radius)
            hi = max(lo, point_est + self._conformal_radius)

            calibrated.append(
                CalibratedPrediction(
                    p10_calibrated=round(lo, 2),
                    p50=round(point_est, 2),
                    p90_calibrated=round(hi, 2),
                    p10_uncalibrated=None,
                    p90_uncalibrated=None,
                    conformal_correction=round(self._conformal_radius, 4),
                    is_crossing_repaired=False,
                    is_abstained=False,
                    abstention_reason=None,
                    nominal_coverage=self.config.nominal_coverage,
                    method=self.config.method.value,
                )
            )

        return calibrated

    def predict_df(self, df: pl.DataFrame) -> pl.DataFrame:
        """Generate calibrated prediction intervals as a Polars DataFrame.

        Args:
            df: Input Polars DataFrame.

        Returns:
            Polars DataFrame with prediction intervals.
        """
        preds = self.predict(df)
        if not preds:
            return pl.DataFrame(
                schema={
                    "p10_calibrated": pl.Float64,
                    "p50": pl.Float64,
                    "p90_calibrated": pl.Float64,
                    "conformal_correction": pl.Float64,
                    "is_crossing_repaired": pl.Boolean,
                    "is_abstained": pl.Boolean,
                    "abstention_reason": pl.String,
                    "nominal_coverage": pl.Float64,
                    "method": pl.String,
                }
            )

        return pl.DataFrame(
            {
                "p10_calibrated": [p.p10_calibrated for p in preds],
                "p50": [p.p50 for p in preds],
                "p90_calibrated": [p.p90_calibrated for p in preds],
                "conformal_correction": [p.conformal_correction for p in preds],
                "is_crossing_repaired": [p.is_crossing_repaired for p in preds],
                "is_abstained": [p.is_abstained for p in preds],
                "abstention_reason": [p.abstention_reason for p in preds],
                "nominal_coverage": [p.nominal_coverage for p in preds],
                "method": [p.method for p in preds],
            },
            schema={
                "p10_calibrated": pl.Float64,
                "p50": pl.Float64,
                "p90_calibrated": pl.Float64,
                "conformal_correction": pl.Float64,
                "is_crossing_repaired": pl.Boolean,
                "is_abstained": pl.Boolean,
                "abstention_reason": pl.String,
                "nominal_coverage": pl.Float64,
                "method": pl.String,
            },
        )
