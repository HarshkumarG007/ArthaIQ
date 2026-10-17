"""Configuration schemas and data contracts for Rung D gradient boosted models.

Adheres to Rules R-MD-04, R-MD-06, R-MD-08, R-CD-01, and R-CD-05.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GBMModelType(StrEnum):
    """Supported gradient boosting model families."""

    LIGHTGBM = "lightgbm"
    CATBOOST = "catboost"


class SearchBudgetPolicy(BaseModel):
    """Bounded search budget policy for hyperparameter optimization on CPU.

    Adheres to Profile B hardware assumptions and Rule R-MD-10.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_evals: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of hyperparameter evaluation trials.",
    )
    timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=300.0,
        description="Total wall-clock time limit for search in seconds.",
    )
    cv_folds: int = Field(
        default=3,
        ge=2,
        le=10,
        description="Number of cross-validation folds during tuning.",
    )
    random_seed: int = Field(
        default=42,
        description="Deterministic random seed for candidate parameter sampling.",
    )
    scoring_metric: Literal["neg_mean_absolute_error", "neg_root_mean_squared_error"] = Field(
        default="neg_mean_absolute_error",
        description="Evaluation metric to optimize during parameter search.",
    )


class TrainingMetrics(BaseModel):
    """Execution and resource profiling metrics for fitted models.

    Fulfills task requirement to log wall-clock time and peak heap memory.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    fit_time_seconds: float = Field(
        ...,
        ge=0.0,
        description="Wall-clock duration of training in seconds.",
    )
    predict_latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Mean prediction latency per observation in milliseconds.",
    )
    peak_memory_mb: float = Field(
        ...,
        ge=0.0,
        description="Peak heap memory consumption in megabytes during fitting.",
    )
    n_train_samples: int = Field(
        ...,
        ge=0,
        description="Number of observations in training partition.",
    )
    n_features: int = Field(
        ...,
        ge=0,
        description="Total number of input features in design matrix.",
    )
    best_iteration: int | None = Field(
        default=None,
        description="Best boosting iteration if early stopping was used.",
    )
    cv_score: float | None = Field(
        default=None,
        description="Best cross-validation score achieved during tuning.",
    )


class PointPrediction(BaseModel):
    """Structured point prediction output for an observation.

    Adheres to Rules R-UQ-01 and R-MD-08.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    predicted_pay_lpa: float = Field(
        ...,
        description="Predicted point compensation in nominal INR LPA.",
    )
    is_abstained: bool = Field(
        default=False,
        description="Whether the model abstained due to thin evidence or out-of-range inputs.",
    )
    abstention_reason: str | None = Field(
        default=None,
        description="Reason code if prediction was abstained (Rule R-MD-08).",
    )
    model_name: str = Field(
        ...,
        description="Identifier of model producing prediction.",
    )


class GBMPointConfig(BaseModel):
    """Hyperparameter and operational configuration for Rung D point models.

    Adheres to Rules R-MD-04, R-MD-06, and R-MD-08.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_type: GBMModelType = Field(
        default=GBMModelType.LIGHTGBM,
        description="Boosting algorithm family (lightgbm or catboost).",
    )
    learning_rate: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description="Boosting shrinkage rate.",
    )
    n_estimators: int = Field(
        default=100,
        ge=1,
        le=2000,
        description="Number of boosting trees.",
    )
    max_depth: int = Field(
        default=4,
        ge=1,
        le=12,
        description="Maximum tree depth for controlling model capacity.",
    )
    num_leaves: int = Field(
        default=15,
        ge=2,
        le=256,
        description="Maximum tree leaves (LightGBM specific).",
    )
    l2_regularization: float = Field(
        default=1.0,
        ge=0.0,
        description="L2 regularization penalty on leaf weights.",
    )
    min_child_samples: int = Field(
        default=5,
        ge=1,
        description="Minimum number of data points required in a leaf.",
    )
    subsample: float = Field(
        default=0.8,
        gt=0.0,
        le=1.0,
        description="Row subsampling ratio per tree.",
    )
    colsample_bytree: float = Field(
        default=0.8,
        gt=0.0,
        le=1.0,
        description="Feature column subsampling ratio per tree.",
    )
    random_seed: int = Field(
        default=42,
        description="Deterministic random seed for reproducibility (Rule R-MD-10).",
    )
    log_target: bool = Field(
        default=True,
        description="Fit on natural log of target compensation (Rule R-MD-06).",
    )
    max_experience_bound: float = Field(
        default=40.0,
        ge=10.0,
        le=60.0,
        description="Maximum plausible professional experience before abstaining (Rule R-MD-08).",
    )
    search_budget: SearchBudgetPolicy | None = Field(
        default=None,
        description="Optional hyperparameter tuning budget policy.",
    )


class GBMQuantileConfig(BaseModel):
    """Hyperparameter and operational configuration for Rung E quantile models.

    Adheres to Rules R-MD-04, R-MD-06, R-MD-08, R-UQ-01, and R-UQ-05.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_type: GBMModelType = Field(
        default=GBMModelType.LIGHTGBM,
        description="Boosting algorithm family (lightgbm or catboost).",
    )
    quantiles: tuple[float, ...] = Field(
        default=(0.10, 0.50, 0.90),
        description="Target quantiles in (0, 1), strictly monotonically increasing.",
    )
    repair_crossing: bool = Field(
        default=True,
        description="Whether to apply monotonic rearrangement repair (Rule R-UQ-05).",
    )
    learning_rate: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description="Boosting shrinkage rate.",
    )
    n_estimators: int = Field(
        default=100,
        ge=1,
        le=2000,
        description="Number of boosting trees.",
    )
    max_depth: int = Field(
        default=4,
        ge=1,
        le=12,
        description="Maximum tree depth for controlling model capacity.",
    )
    num_leaves: int = Field(
        default=15,
        ge=2,
        le=256,
        description="Maximum tree leaves (LightGBM specific).",
    )
    l2_regularization: float = Field(
        default=1.0,
        ge=0.0,
        description="L2 regularization penalty on leaf weights.",
    )
    min_child_samples: int = Field(
        default=5,
        ge=1,
        description="Minimum number of data points required in a leaf.",
    )
    subsample: float = Field(
        default=0.8,
        gt=0.0,
        le=1.0,
        description="Row subsampling ratio per tree.",
    )
    colsample_bytree: float = Field(
        default=0.8,
        gt=0.0,
        le=1.0,
        description="Feature column subsampling ratio per tree.",
    )
    random_seed: int = Field(
        default=42,
        description="Deterministic random seed for reproducibility (Rule R-MD-10).",
    )
    log_target: bool = Field(
        default=True,
        description="Fit on natural log of target compensation (Rule R-MD-06).",
    )
    max_experience_bound: float = Field(
        default=40.0,
        ge=10.0,
        le=60.0,
        description="Maximum plausible professional experience before abstaining (Rule R-MD-08).",
    )

    @field_validator("quantiles")
    @classmethod
    def validate_quantiles(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        """Validate that quantiles are strictly in (0, 1) and monotonically increasing."""
        if len(v) < 2:
            raise ValueError("At least 2 quantiles must be specified.")
        for q in v:
            if not (0.0 < q < 1.0):
                raise ValueError(f"Quantile values must be strictly in (0, 1), got {q}.")
        for i in range(len(v) - 1):
            if v[i] >= v[i + 1]:
                raise ValueError("Quantiles must be strictly monotonically increasing.")
        return v
