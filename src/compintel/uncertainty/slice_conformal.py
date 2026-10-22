"""Slice-Adaptive Conformal Prediction Intervals (Phase 11, Task T11.01, CHARTER-EXP-13).

Implements:
- Hierarchical Group-Conditional Conformal Calibration with Empirical Bayes shrinkage.
- Shrinkage formulation: q_hat_g = alpha_g * q_hat_sample_g + (1 - alpha_g) * q_hat_global,
  where alpha_g = n_g / (n_g + m_0) with prior weight m_0 = 30.
- Fallback to global q_hat for thin or unobserved slices (n_g < min_slice_samples).
- Monotonicity, non-negativity clamping, and crossing repair (Rules R-UQ-01, R-UQ-05).
- Drop-in compatibility with the Base ConformalQuantileRegressor serving interface.

Adheres to:
- CHARTER-EXP-13: Slice-Adaptive Conformal Prediction Intervals.
- Rule R-MD-01: Benchmark ladder Rung F.
- Rule R-MD-09: Pre-registered experiment charters and keep criteria.
- Rule R-UQ-01: Full [P10, P90] interval with P50 median.
- Rule R-UQ-03: Marginal and group-conditional guarantees documented.
- Rule R-UQ-05: Crossing detection and monotonic projection repair.
- Rule R-CD-01: Strict type annotations and full mypy compliance.
- Rule R-CD-03 & Import Linter: Zero imports of serving, evaluation, ingestion, or quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import polars as pl  # noqa: TC002
from pydantic import BaseModel, ConfigDict, Field, field_validator

from compintel.errors import ConfigError
from compintel.uncertainty.conformal import (
    CalibratedPrediction,
    ConformalAssumptions,
    compute_conformal_quantile,
)

if TYPE_CHECKING:
    from compintel.models.gbm.quantile import BaseGBMQuantileModel


class SliceConformalConfig(BaseModel):
    """Configuration schema for slice-adaptive conformal prediction calibrator.

    Adheres to CHARTER-EXP-13, Rule R-UQ-01, and Rule R-UQ-03.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    nominal_coverage: float = Field(
        default=0.80,
        gt=0.50,
        lt=1.00,
        description="Nominal coverage target (1 - alpha), e.g. 0.80 for [P10, P90].",
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
    prior_weight_m0: float = Field(
        default=30.0,
        gt=0.0,
        description="Empirical Bayes prior sample weight m_0 governing shrinkage strength.",
    )
    min_slice_samples: int = Field(
        default=15,
        ge=5,
        description="Minimum calibration observations required to compute sample slice quantile.",
    )
    slice_columns: list[str] = Field(
        default_factory=lambda: ["role_family", "seniority"],
        description="Ordered list of column names used to partition calibration observations.",
    )

    @field_validator("nominal_coverage")
    @classmethod
    def validate_coverage(cls, v: float) -> float:
        """Validate coverage is inside standard interval bounds."""
        if not (0.50 < v < 1.00):
            raise ConfigError(
                f"nominal_coverage must be in (0.50, 1.00), got {v}.",
                code="INVALID_COVERAGE",
            )
        return v


@dataclass(frozen=True)
class SliceGroupCalibration:
    """Calibration parameters and metrics for a specific group slice (CHARTER-EXP-13)."""

    group_key: tuple[str, ...]
    n_samples: int
    q_sample: float
    alpha_shrinkage: float
    q_shrunk: float
    empirical_coverage: float
    mean_width: float
    median_width: float

    def to_dict(self) -> dict[str, Any]:
        """Convert group calibration record to dictionary."""
        return {
            "group_key": list(self.group_key),
            "n_samples": self.n_samples,
            "q_sample": round(self.q_sample, 4),
            "alpha_shrinkage": round(self.alpha_shrinkage, 4),
            "q_shrunk": round(self.q_shrunk, 4),
            "empirical_coverage": round(self.empirical_coverage, 4),
            "mean_width": round(self.mean_width, 4),
            "median_width": round(self.median_width, 4),
        }


@dataclass(frozen=True)
class SliceConformalSummary:
    """Comprehensive summary of slice-adaptive conformal calibration run."""

    method: str
    nominal_coverage: float
    n_total_calibration: int
    global_conformal_quantile: float
    n_slices_calibrated: int
    slice_calibrations: dict[str, SliceGroupCalibration]
    aggregate_empirical_coverage: float
    aggregate_mean_width: float
    aggregate_median_width: float
    slice_coverage_variance: float
    min_slice_coverage: float
    max_slice_coverage: float
    min_pay_bound_lpa: float
    assumptions: ConformalAssumptions
    slice_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary format for experiment reports."""
        return {
            "method": self.method,
            "nominal_coverage": self.nominal_coverage,
            "n_total_calibration": self.n_total_calibration,
            "global_conformal_quantile": round(self.global_conformal_quantile, 4),
            "n_slices_calibrated": self.n_slices_calibrated,
            "aggregate_empirical_coverage": round(self.aggregate_empirical_coverage, 4),
            "aggregate_mean_width": round(self.aggregate_mean_width, 4),
            "aggregate_median_width": round(self.aggregate_median_width, 4),
            "slice_coverage_variance": round(self.slice_coverage_variance, 6),
            "min_slice_coverage": round(self.min_slice_coverage, 4),
            "max_slice_coverage": round(self.max_slice_coverage, 4),
            "min_pay_bound_lpa": self.min_pay_bound_lpa,
            "slice_columns": self.slice_columns,
            "slices": {k: v.to_dict() for k, v in self.slice_calibrations.items()},
            "assumptions": self.assumptions.to_dict(),
        }


class SliceAdaptiveConformalRegressor:
    r"""Hierarchical Group-Conditional Conformal Quantile Regressor with Empirical Bayes Shrinkage.

    Provides slice-adaptive prediction intervals satisfying CHARTER-EXP-13:
    $$\hat{q}_g = \alpha_g \hat{q}_{\text{sample}, g} + (1 - \alpha_g) \hat{q}_{\text{global}}$$
    where:
    $$\alpha_g = \frac{n_g}{n_g + m_0}$$

    Adheres to Rules R-MD-01, R-MD-09, R-UQ-01, R-UQ-03, and R-UQ-05.
    """

    def __init__(
        self,
        base_model: BaseGBMQuantileModel,
        config: SliceConformalConfig | None = None,
    ) -> None:
        """Initialize slice-adaptive conformal regressor."""
        if not base_model.is_fitted:
            raise RuntimeError("Base quantile model must be fitted before conformal calibration.")

        self.base_model: BaseGBMQuantileModel = base_model
        self.config: SliceConformalConfig = config or SliceConformalConfig()

        self._is_calibrated: bool = False
        self._global_quantile: float = 0.0
        self._group_calibrations: dict[tuple[str, ...], SliceGroupCalibration] = {}
        self._summary: SliceConformalSummary | None = None
        self._target_col: str = "guaranteed_cash_annual"

    @property
    def is_calibrated(self) -> bool:
        """Return True if calibrator has been fitted on a calibration set."""
        return self._is_calibrated

    @property
    def summary(self) -> SliceConformalSummary | None:
        """Return calibration summary metrics and formal assumptions."""
        return self._summary

    @property
    def conformal_quantile(self) -> float:
        """Return global conformal quantile (q_hat_global) for backward compatibility."""
        return self._global_quantile

    def get_slice_quantile(self, slice_key: tuple[str, ...]) -> float:
        """Return the shrunk conformal quantile for a specific slice key, or global fallback."""
        if not self._is_calibrated:
            raise RuntimeError("Calibrator is not calibrated.")
        if slice_key in self._group_calibrations:
            return self._group_calibrations[slice_key].q_shrunk
        return self._global_quantile

    def calibrate(self, calibration_df: pl.DataFrame) -> SliceAdaptiveConformalRegressor:
        """Fit slice-adaptive conformal calibration scores on a temporal calibration partition.

        Args:
            calibration_df: Polars DataFrame containing profile features, slice columns, and target.

        Returns:
            Self (calibrated regressor instance).
        """
        if self._target_col not in calibration_df.columns:
            msg = f"Target column '{self._target_col}' missing from calibration DataFrame."
            raise ValueError(msg)

        for col in self.config.slice_columns:
            if col not in calibration_df.columns:
                msg = f"Slice column '{col}' missing from calibration DataFrame."
                raise ValueError(msg)

        if len(calibration_df) == 0:
            raise ValueError("Cannot calibrate slice-conformal model on empty DataFrame.")

        # Compute base predictions
        base_preds = self.base_model.predict(calibration_df)
        y_true = calibration_df.get_column(self._target_col).to_numpy()

        all_scores: list[float] = []
        valid_indices: list[int] = []

        # 1. Compute non-conformity scores for all non-abstained records
        for i, p in enumerate(base_preds):
            if p.is_abstained or p.p10 is None or p.p90 is None:
                continue

            yt = float(y_true[i])
            # CQR non-conformity score: E_i = max(q10 - y, y - q90)
            score = max(p.p10 - yt, yt - p.p90)
            all_scores.append(score)
            valid_indices.append(i)

        if not all_scores:
            raise ValueError("All calibration records were abstained; insufficient support.")

        alpha = 1.0 - self.config.nominal_coverage
        self._global_quantile = compute_conformal_quantile(all_scores, alpha)

        # 2. Partition valid calibration observations by slice columns
        valid_df = calibration_df[valid_indices]
        valid_scores_arr = np.array(all_scores, dtype=np.float64)

        # Extract slice keys
        slice_cols = self.config.slice_columns
        group_rows = valid_df.select(slice_cols).to_dicts()

        slice_scores_map: dict[tuple[str, ...], list[float]] = {}
        slice_indices_map: dict[tuple[str, ...], list[int]] = {}

        for local_idx, row in enumerate(group_rows):
            key = tuple(str(row[c]) for c in slice_cols)
            if key not in slice_scores_map:
                slice_scores_map[key] = []
                slice_indices_map[key] = []
            slice_scores_map[key].append(float(valid_scores_arr[local_idx]))
            slice_indices_map[key].append(valid_indices[local_idx])

        # 3. Compute group-conditional quantiles with empirical Bayes shrinkage
        m0 = self.config.prior_weight_m0
        min_samples = self.config.min_slice_samples
        self._group_calibrations = {}

        for key, scores_g in slice_scores_map.items():
            ng = len(scores_g)
            if ng >= min_samples:
                q_sample_g = compute_conformal_quantile(scores_g, alpha)
                alpha_shrink = float(ng / (ng + m0))
                q_shrunk_g = float(
                    alpha_shrink * q_sample_g + (1.0 - alpha_shrink) * self._global_quantile
                )
            else:
                q_sample_g = self._global_quantile
                alpha_shrink = 0.0
                q_shrunk_g = self._global_quantile

            # Evaluate slice calibration metrics under q_shrunk_g
            covered_g = 0
            widths_g: list[float] = []

            for global_idx in slice_indices_map[key]:
                p = base_preds[global_idx]
                if p.p10 is None or p.p90 is None:
                    continue
                yt = float(y_true[global_idx])
                lo = max(self.config.min_pay_bound_lpa, p.p10 - q_shrunk_g)
                hi = max(lo, p.p90 + q_shrunk_g)
                if lo <= yt <= hi:
                    covered_g += 1
                widths_g.append(hi - lo)

            emp_cov_g = float(covered_g / ng) if ng > 0 else 0.0
            mean_w_g = float(np.mean(widths_g)) if widths_g else 0.0
            med_w_g = float(np.median(widths_g)) if widths_g else 0.0

            self._group_calibrations[key] = SliceGroupCalibration(
                group_key=key,
                n_samples=ng,
                q_sample=q_sample_g,
                alpha_shrinkage=alpha_shrink,
                q_shrunk=q_shrunk_g,
                empirical_coverage=emp_cov_g,
                mean_width=mean_w_g,
                median_width=med_w_g,
            )

        # 4. Aggregate evaluation across entire calibration set
        total_covered = 0
        total_widths: list[float] = []
        slice_coverages: list[float] = []

        for local_idx, row in enumerate(group_rows):
            key = tuple(str(row[c]) for c in slice_cols)
            q_applied = self._group_calibrations[key].q_shrunk
            global_idx = valid_indices[local_idx]
            p = base_preds[global_idx]
            if p.p10 is None or p.p90 is None:
                continue

            yt = float(y_true[global_idx])
            lo = max(self.config.min_pay_bound_lpa, p.p10 - q_applied)
            hi = max(lo, p.p90 + q_applied)
            if lo <= yt <= hi:
                total_covered += 1
            total_widths.append(hi - lo)

        for calib in self._group_calibrations.values():
            if calib.n_samples >= min_samples:
                slice_coverages.append(calib.empirical_coverage)

        n_cal = len(all_scores)
        agg_cov = float(total_covered / n_cal) if n_cal > 0 else 0.0
        agg_mean_w = float(np.mean(total_widths)) if total_widths else 0.0
        agg_med_w = float(np.median(total_widths)) if total_widths else 0.0
        cov_var = float(np.var(slice_coverages)) if slice_coverages else 0.0
        min_cov = float(np.min(slice_coverages)) if slice_coverages else agg_cov
        max_cov = float(np.max(slice_coverages)) if slice_coverages else agg_cov

        self._summary = SliceConformalSummary(
            method="slice_adaptive_cqr",
            nominal_coverage=self.config.nominal_coverage,
            n_total_calibration=n_cal,
            global_conformal_quantile=self._global_quantile,
            n_slices_calibrated=len(self._group_calibrations),
            slice_calibrations={":".join(k): v for k, v in self._group_calibrations.items()},
            aggregate_empirical_coverage=agg_cov,
            aggregate_mean_width=agg_mean_w,
            aggregate_median_width=agg_med_w,
            slice_coverage_variance=cov_var,
            min_slice_coverage=min_cov,
            max_slice_coverage=max_cov,
            min_pay_bound_lpa=self.config.min_pay_bound_lpa,
            slice_columns=list(self.config.slice_columns),
            assumptions=ConformalAssumptions(
                calibration_split="calibrate",
                target_measure=self._target_col,
                description=(
                    "Slice-adaptive conformal intervals guarantee marginal coverage (1 - alpha) "
                    "in aggregate while providing enhanced group-conditional calibration coverage "
                    "across pre-registered slices via empirical Bayes shrinkage."
                ),
            ),
        )
        self._is_calibrated = True
        return self

    def predict(self, df: pl.DataFrame) -> list[CalibratedPrediction]:
        """Produce slice-calibrated prediction intervals for query observations.

        Adheres to Rules R-UQ-01, R-UQ-03, R-UQ-05, and R-MD-08.
        Provides 100% drop-in API parity with Base ConformalQuantileRegressor.

        Args:
            df: Polars DataFrame of candidate query observations.

        Returns:
            List of CalibratedPrediction instances with slice-adapted conformal bounds.
        """
        if not self._is_calibrated:
            raise RuntimeError("SliceAdaptiveConformalRegressor must be calibrated before predict.")

        n = len(df)
        if n == 0:
            return []

        base_preds = self.base_model.predict(df)
        slice_cols = self.config.slice_columns

        # Check if slice columns exist in query DataFrame
        has_slice_cols = all(c in df.columns for c in slice_cols)
        query_rows: list[dict[str, Any]] = (
            df.select(slice_cols).to_dicts() if has_slice_cols else []
        )

        calibrated: list[CalibratedPrediction] = []

        for i, p in enumerate(base_preds):
            if p.is_abstained or p.p10 is None or p.p90 is None or p.p50 is None:
                calibrated.append(
                    CalibratedPrediction(
                        p10_calibrated=None,
                        p50=None,
                        p90_calibrated=None,
                        p10_uncalibrated=p.p10,
                        p90_uncalibrated=p.p90,
                        conformal_correction=self._global_quantile,
                        is_crossing_repaired=False,
                        is_abstained=True,
                        abstention_reason=p.abstention_reason or "THIN_EVIDENCE",
                        nominal_coverage=self.config.nominal_coverage,
                        method="slice_adaptive_cqr",
                    )
                )
                continue

            # Determine slice adjustment q_hat_g
            if has_slice_cols:
                row = query_rows[i]
                slice_key = tuple(str(row[c]) for c in slice_cols)
                q_adj = self.get_slice_quantile(slice_key)
            else:
                q_adj = self._global_quantile

            # Apply slice-adapted conformal quantile adjustment
            raw_lo = p.p10 - q_adj
            raw_hi = p.p90 + q_adj
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
                    p10_calibrated=round(lo_final, 4),
                    p50=round(mid_final, 4),
                    p90_calibrated=round(hi_final, 4),
                    p10_uncalibrated=round(p.p10, 4),
                    p90_uncalibrated=round(p.p90, 4),
                    conformal_correction=round(q_adj, 4),
                    is_crossing_repaired=is_crossing or p.is_crossing_repaired,
                    is_abstained=False,
                    abstention_reason=None,
                    nominal_coverage=self.config.nominal_coverage,
                    method="slice_adaptive_cqr",
                )
            )

        return calibrated
