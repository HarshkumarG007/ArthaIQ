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
from compintel.uncertainty.support import (
    AbstentionReason,
    CandidateProfile,
    CohortEvidenceContext,
    EvidenceGrade,
    SourceQualityTier,
    SupportCheckDetail,
    SupportCheckResult,
    SupportChecksConfig,
    SupportEvaluator,
    SupportStatus,
    ThresholdsConfig,
)

__all__ = [
    "AbstentionReason",
    "CalibratedPrediction",
    "CandidateProfile",
    "CohortEvidenceContext",
    "ConformalAssumptions",
    "ConformalCalibrationSummary",
    "ConformalConfig",
    "ConformalMethod",
    "ConformalQuantileRegressor",
    "EvidenceGrade",
    "SourceQualityTier",
    "SplitConformalCalibrator",
    "SupportCheckDetail",
    "SupportCheckResult",
    "SupportChecksConfig",
    "SupportEvaluator",
    "SupportStatus",
    "ThresholdsConfig",
    "compute_conformal_quantile",
]
