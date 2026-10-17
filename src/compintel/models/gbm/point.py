"""Point estimation gradient boosted models on log pay for Rung D.

Adheres to Rules R-MD-04, R-MD-06, R-MD-08, R-CD-01, and Profile B resource profiling.
"""

from __future__ import annotations

import time
import tracemalloc
from abc import ABC, abstractmethod
from typing import Any

import catboost as cb
import lightgbm as lgb
import numpy as np
import pandas as pd
import polars as pl

from compintel.models.gbm.budget import tune_gbm_hyperparameters
from compintel.models.gbm.config import (
    GBMModelType,
    GBMPointConfig,
    PointPrediction,
    TrainingMetrics,
)

FEATURE_COLS_CATEGORICAL = ["role_family", "seniority", "location"]
FEATURE_COLS_CONTINUOUS = ["years_experience"]


class BaseGBMPointModel(ABC):
    """Abstract base class for Rung D gradient boosted point models on log pay."""

    def __init__(self, config: GBMPointConfig | None = None) -> None:
        """Initialize base gradient boosted point model."""
        self.config: GBMPointConfig = config or GBMPointConfig()
        self._is_fitted: bool = False
        self._median_yoe: float = 3.0
        self._known_categories: dict[str, list[str]] = {}
        self._metrics: TrainingMetrics | None = None
        self._target_col: str = "guaranteed_cash_annual"

    @property
    def is_fitted(self) -> bool:
        """Return True if the model has been fitted on training data."""
        return self._is_fitted

    @property
    def metrics(self) -> TrainingMetrics | None:
        """Return resource profiling and execution metrics after fitting."""
        return self._metrics

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return identifier string of the boosting model family."""

    @abstractmethod
    def _fit_model(self, features_df: pd.DataFrame, y: np.ndarray) -> None:
        """Fit the underlying gradient boosted regressor on preprocessed features."""

    @abstractmethod
    def _predict_raw(self, features_df: pd.DataFrame) -> np.ndarray:
        """Produce raw point predictions from underlying model."""

    def _prepare_features(
        self,
        df: pl.DataFrame,
        is_training: bool = False,
    ) -> pd.DataFrame:
        """Extract and prepare feature DataFrame with correct types at library boundary.

        Args:
            df: Polars DataFrame containing observation columns.
            is_training: Whether to learn category vocabularies and continuous medians.

        Returns:
            Pandas DataFrame ready for boosting library ingestion.
        """
        for col in FEATURE_COLS_CATEGORICAL:
            if col not in df.columns:
                msg = f"Missing required categorical column '{col}'."
                raise ValueError(msg)

        if "years_experience" not in df.columns:
            msg = "Missing required continuous column 'years_experience'."
            raise ValueError(msg)

        # Convert to pandas at boundary
        p_df = df.select([*FEATURE_COLS_CATEGORICAL, "years_experience"]).to_pandas()

        # Handle continuous experience
        if is_training:
            valid_yoe = p_df["years_experience"].dropna()
            self._median_yoe = float(valid_yoe.median()) if not valid_yoe.empty else 3.0

        p_df["years_experience"] = p_df["years_experience"].fillna(self._median_yoe).astype(float)

        # Handle categoricals
        for col in FEATURE_COLS_CATEGORICAL:
            raw_s = p_df[col].fillna("OTHER").astype(str)
            if is_training:
                cats = sorted(raw_s.unique().tolist())
                if "OTHER" not in cats:
                    cats.append("OTHER")
                self._known_categories[col] = cats
                clean_s = raw_s
            else:
                known_set = set(self._known_categories.get(col, ["OTHER"]))
                clean_s = raw_s.map(lambda val, k=known_set: val if val in k else "OTHER")

            if self.config.model_type == GBMModelType.LIGHTGBM:
                p_df[col] = pd.Categorical(
                    clean_s,
                    categories=self._known_categories.get(col, ["OTHER"]),
                )
            else:
                p_df[col] = clean_s.astype(str)

        return p_df

    def _check_abstention(self, df: pl.DataFrame) -> tuple[np.ndarray, list[str | None]]:
        """Evaluate thin-evidence and out-of-range abstention flags per observation.

        Args:
            df: Input Polars DataFrame.

        Returns:
            Tuple of boolean mask (True = abstained) and list of reason codes.
        """
        n = len(df)
        if n == 0:
            return np.array([], dtype=bool), []

        yoe = df.get_column("years_experience").to_numpy()
        abstained_mask = np.zeros(n, dtype=bool)
        reasons: list[str | None] = [None] * n

        for i in range(n):
            val = yoe[i]
            if val is None or np.isnan(val):
                continue
            if val < 0.0 or val > self.config.max_experience_bound:
                abstained_mask[i] = True
                reasons[i] = "THIN_EVIDENCE"

        return abstained_mask, reasons

    def fit(self, df: pl.DataFrame) -> BaseGBMPointModel:
        """Fit the model on training observations with resource and memory profiling.

        Args:
            df: Training DataFrame containing features and target pay.

        Returns:
            Self (fitted model instance).
        """
        if self._target_col not in df.columns:
            msg = f"Target column '{self._target_col}' not found in training DataFrame."
            raise ValueError(msg)

        if len(df) == 0:
            msg = "Cannot fit model on empty DataFrame."
            raise ValueError(msg)

        tracemalloc.start()
        start_time = time.perf_counter()

        # Extract target and apply log transform per Rule R-MD-06
        target_series = df.get_column(self._target_col).to_numpy()
        if (target_series <= 0.0).any():
            msg = "Target compensation must be strictly positive (Rule R-MD-06)."
            raise ValueError(msg)

        y = np.log(target_series) if self.config.log_target else target_series
        features_df = self._prepare_features(df, is_training=True)

        self._fit_model(features_df, y)

        fit_duration = time.perf_counter() - start_time
        _, peak_memory_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self._is_fitted = True
        self._metrics = TrainingMetrics(
            fit_time_seconds=fit_duration,
            predict_latency_ms=0.0,
            peak_memory_mb=peak_memory_bytes / (1024 * 1024),
            n_train_samples=len(df),
            n_features=features_df.shape[1],
        )
        return self

    def predict(self, df: pl.DataFrame) -> list[PointPrediction]:
        """Generate structured point predictions for observations.

        Args:
            df: Input Polars DataFrame.

        Returns:
            List of PointPrediction instances with nominal INR LPA values.
        """
        if not self._is_fitted:
            msg = f"{self.model_name} must be fitted before predict."
            raise RuntimeError(msg)

        n = len(df)
        if n == 0:
            return []

        abstained_mask, reasons = self._check_abstention(df)
        features_df = self._prepare_features(df, is_training=False)

        start_time = time.perf_counter()
        raw_preds = self._predict_raw(features_df)
        predict_duration_ms = ((time.perf_counter() - start_time) * 1000.0) / max(1, n)

        # Invert log pay to nominal INR LPA
        lpa_preds = np.exp(raw_preds) if self.config.log_target else raw_preds

        # Update predict latency in metrics if available
        if self._metrics is not None:
            self._metrics = self._metrics.model_copy(
                update={"predict_latency_ms": predict_duration_ms}
            )

        predictions: list[PointPrediction] = []
        for i in range(n):
            if abstained_mask[i]:
                predictions.append(
                    PointPrediction(
                        predicted_pay_lpa=float("nan"),
                        is_abstained=True,
                        abstention_reason=reasons[i],
                        model_name=self.model_name,
                    )
                )
            else:
                predictions.append(
                    PointPrediction(
                        predicted_pay_lpa=float(lpa_preds[i]),
                        is_abstained=False,
                        abstention_reason=None,
                        model_name=self.model_name,
                    )
                )

        return predictions

    def predict_df(self, df: pl.DataFrame) -> pl.DataFrame:
        """Generate point predictions as a Polars DataFrame.

        Args:
            df: Input Polars DataFrame.

        Returns:
            Polars DataFrame with point prediction columns.
        """
        preds = self.predict(df)
        if not preds:
            return pl.DataFrame(
                schema={
                    "predicted_pay_lpa": pl.Float64,
                    "is_abstained": pl.Boolean,
                    "abstention_reason": pl.String,
                    "model_name": pl.String,
                }
            )

        return pl.DataFrame(
            {
                "predicted_pay_lpa": [p.predicted_pay_lpa for p in preds],
                "is_abstained": [p.is_abstained for p in preds],
                "abstention_reason": [p.abstention_reason for p in preds],
                "model_name": [p.model_name for p in preds],
            }
        )


class LightGBMPointModel(BaseGBMPointModel):
    """Rung D point model using LightGBM on log-transformed pay."""

    def __init__(self, config: GBMPointConfig | None = None) -> None:
        """Initialize LightGBM point model."""
        cfg = config or GBMPointConfig(model_type=GBMModelType.LIGHTGBM)
        super().__init__(cfg)
        self._regressor: lgb.LGBMRegressor | None = None

    @property
    def model_name(self) -> str:
        """Return model family identifier."""
        return "LightGBMPointModel"

    def _fit_model(self, features_df: pd.DataFrame, y: np.ndarray) -> None:
        """Fit LightGBM regressor respecting tuning budget and small-sample constraints."""
        n_samples = len(features_df)
        base_params: dict[str, Any] = {
            "objective": "regression",
            "learning_rate": self.config.learning_rate,
            "n_estimators": self.config.n_estimators,
            "max_depth": self.config.max_depth,
            "num_leaves": self.config.num_leaves,
            "reg_lambda": self.config.l2_regularization,
            "subsample": self.config.subsample,
            "colsample_bytree": self.config.colsample_bytree,
            "min_child_samples": min(self.config.min_child_samples, max(1, n_samples // 2)),
            "random_state": self.config.random_seed,
            "verbose": -1,
        }

        # Execute hyperparameter tuning if budget policy is configured
        if self.config.search_budget is not None:
            tuning = tune_gbm_hyperparameters(
                model_type=GBMModelType.LIGHTGBM,
                features_df=features_df,
                y=y,
                budget=self.config.search_budget,
            )
            base_params.update(tuning.best_params)

        self._regressor = lgb.LGBMRegressor(**base_params)
        self._regressor.fit(features_df, y)

    def _predict_raw(self, features_df: pd.DataFrame) -> np.ndarray:
        """Produce point predictions in log space."""
        if self._regressor is None:
            msg = "LightGBM regressor has not been fitted."
            raise RuntimeError(msg)
        return np.asarray(self._regressor.predict(features_df), dtype=np.float64)


class CatBoostPointModel(BaseGBMPointModel):
    """Rung D point model using CatBoost on log-transformed pay."""

    def __init__(self, config: GBMPointConfig | None = None) -> None:
        """Initialize CatBoost point model."""
        cfg = config or GBMPointConfig(model_type=GBMModelType.CATBOOST)
        super().__init__(cfg)
        self._regressor: cb.CatBoostRegressor | None = None

    @property
    def model_name(self) -> str:
        """Return model family identifier."""
        return "CatBoostPointModel"

    def _fit_model(self, features_df: pd.DataFrame, y: np.ndarray) -> None:
        """Fit CatBoost regressor respecting tuning budget and native categorical features."""
        cat_features = FEATURE_COLS_CATEGORICAL

        base_params: dict[str, Any] = {
            "loss_function": "RMSE",
            "learning_rate": self.config.learning_rate,
            "iterations": self.config.n_estimators,
            "depth": self.config.max_depth,
            "l2_leaf_reg": self.config.l2_regularization,
            "random_seed": self.config.random_seed,
            "verbose": 0,
            "allow_writing_files": False,
        }

        if self.config.search_budget is not None:
            tuning = tune_gbm_hyperparameters(
                model_type=GBMModelType.CATBOOST,
                features_df=features_df,
                y=y,
                budget=self.config.search_budget,
                cat_features=cat_features,
            )
            base_params.update(tuning.best_params)

        self._regressor = cb.CatBoostRegressor(**base_params)
        self._regressor.fit(features_df, y, cat_features=cat_features)

    def _predict_raw(self, features_df: pd.DataFrame) -> np.ndarray:
        """Produce point predictions in log space."""
        if self._regressor is None:
            msg = "CatBoost regressor has not been fitted."
            raise RuntimeError(msg)
        return np.asarray(self._regressor.predict(features_df), dtype=np.float64)


def create_gbm_point_model(config: GBMPointConfig) -> BaseGBMPointModel:
    """Factory creating appropriate Rung D GBM point model for given configuration.

    Args:
        config: Model configuration specifying model family and parameters.

    Returns:
        Instantiated BaseGBMPointModel subclass.
    """
    if config.model_type == GBMModelType.LIGHTGBM:
        return LightGBMPointModel(config)
    if config.model_type == GBMModelType.CATBOOST:
        return CatBoostPointModel(config)

    msg = f"Unsupported GBM model family: {config.model_type}"
    raise ValueError(msg)
