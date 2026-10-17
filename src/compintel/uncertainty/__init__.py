"""Uncertainty quantification and calibration for compensation intelligence."""

from compintel.uncertainty.conformal import (
    CalibratedPrediction,
    ConformalAssumptions,
    ConformalCalibrationSummary,
    ConformalConfig,
    ConformalMethod,
    ConformalQuantileRegressor,
    SplitConformalCalibrator,
    compute_conformal_quantile,
)

__all__ = [
    "CalibratedPrediction",
    "ConformalAssumptions",
    "ConformalCalibrationSummary",
    "ConformalConfig",
    "ConformalMethod",
    "ConformalQuantileRegressor",
    "SplitConformalCalibrator",
    "compute_conformal_quantile",
]
