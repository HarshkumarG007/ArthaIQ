"""Quantile gradient boosted models (LightGBM and CatBoost) for Rung E (ADR-0004).

Adheres to:
- Rule R-MD-01: Benchmark ladder; Rung E quantile models for distribution output.
- Rule R-MD-04: Feature preprocessing fitted inside training folds only.
- Rule R-MD-06: Model log-transformed pay by default, inverting back via exp() to nominal INR LPA.
- Rule R-MD-08: Thin-evidence abstention (THIN_EVIDENCE) for out-of-range professional experience.
- Rule R-MD-10: Seed everything and profile wall-clock fit time and peak heap memory.
- Rule R-UQ-01: No lone numbers; outputs P10, P50, and P90 with transparent metadata.
- Rule R-UQ-05: Detect, report, and repair quantile crossing via monotonic rearrangement projection.
- Rule R-CD-01: Strict typing and full mypy compliance.
- Rule R-CD-02: Pure functions and deterministic inference without hidden mutable state.
- Rule R-CD-03 & Import Linter: Zero imports of evaluation, serving, ingestion, or quality.
"""

from __future__ import annotations

import time
import tracemalloc
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

import catboost as cb
import lightgbm as lgb
import numpy as np
import pandas as pd
import polars as pl

from compintel.models.gbm.config import (
    GBMModelType,
    GBMQuantileConfig,
    TrainingMetrics,
)

FEATURE_COLS_CATEGORICAL = ["role_family", "seniority", "location"]
FEATURE_COLS_CONTINUOUS = ["years_experience"]


@dataclass(frozen=True)
class CrossingDiagnostics:
    """Summary diagnostics of quantile crossing before and after repair.

    Fulfills Rule R-UQ-05 and Task T5.02 Definition of Done:
    'crossing is zero after repair and the raw rate is reported'.
    """

    total_observations: int
    evaluated_observations: int
    raw_crossing_count: int
    raw_crossing_rate: float
    repaired_crossing_count: int
    repaired_crossing_rate: float
    max_raw_crossing_delta_lpa: float

    def to_dict(self) -> dict[str, Any]:
        """Convert diagnostics to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class QuantilePrediction:
    """Structured conditional quantile prediction conforming to Rules R-UQ-01 and R-UQ-05."""

    p10: float | None
    p50: float | None
    p90: float | None
    raw_p10: float | None
    raw_p50: float | None
    raw_p90: float | None
    is_crossing_repaired: bool
    is_abstained: bool
    abstention_reason: str | None = None
    target_measure: str = "guaranteed_cash_annual"
    currency: str = "INR"
    pay_period: str = "annual"
    tax_basis: str = "gross_pretax"
    nominal_basis: bool = True
    model_name: str = "GBMQuantileModel"

    def to_dict(self) -> dict[str, Any]:
        """Convert prediction to dictionary representation."""
        return asdict(self)


def detect_and_repair_quantile_crossings(
    raw_quantiles_lpa: np.ndarray,
    evaluated_mask: np.ndarray | None = None,
    repair: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, CrossingDiagnostics]:
    """Detect non-monotonic quantile crossings and apply monotone rearrangement repair.

    Implements the Chernozhukov, Fernandez-Val, and Galichon (2010) monotone rearrangement
    operator to guarantee monotonicity (p_alpha1 <= p_alpha2 <= ... <= p_alphaK) while
    logging pre-repair crossing counts and violation magnitudes.

    Args:
        raw_quantiles_lpa: 2D array of shape (N, K) containing un-repaired quantile predictions.
        evaluated_mask: Boolean array of shape (N,) where True indicates active non-abstained rows.
            If None, all rows are treated as evaluated.
        repair: Whether to enforce monotonicity via rearrangement sorting (Rule R-UQ-05).

    Returns:
        Tuple of:
        - final_quantiles: (N, K) array (rearranged in non-decreasing order if repair=True).
        - is_repaired_mask: (N,) boolean array indicating which observations crossed in raw.
        - max_violations_lpa: (N,) float array with the maximum crossing violation per row in LPA.
        - diagnostics: CrossingDiagnostics summary report.
    """
    n_obs, n_quantiles = raw_quantiles_lpa.shape
    if n_obs == 0:
        empty_diag = CrossingDiagnostics(
            total_observations=0,
            evaluated_observations=0,
            raw_crossing_count=0,
            raw_crossing_rate=0.0,
            repaired_crossing_count=0,
            repaired_crossing_rate=0.0,
            max_raw_crossing_delta_lpa=0.0,
        )
        return (
            np.empty((0, n_quantiles), dtype=np.float64),
            np.empty(0, dtype=bool),
            np.empty(0, dtype=np.float64),
            empty_diag,
        )

    active_mask = (
        np.ones(n_obs, dtype=bool)
        if evaluated_mask is None
        else np.asarray(evaluated_mask, dtype=bool)
    )

    final_quantiles = np.copy(raw_quantiles_lpa)
    is_crossing_raw = np.zeros(n_obs, dtype=bool)
    max_violations_lpa = np.zeros(n_obs, dtype=np.float64)

    for i in range(n_obs):
        if not active_mask[i]:
            continue

        row = raw_quantiles_lpa[i]
        # Check non-monotonicity across any pair (j < k) where q_j > q_k
        max_delta = 0.0
        crossed = False
        for j in range(n_quantiles):
            for k in range(j + 1, n_quantiles):
                if row[j] > row[k]:
                    crossed = True
                    delta = float(row[j] - row[k])
                    if delta > max_delta:
                        max_delta = delta

        is_crossing_raw[i] = crossed
        max_violations_lpa[i] = max_delta

        if repair and crossed:
            final_quantiles[i] = np.sort(row)

    # Post-repair crossing check
    repaired_crossing_count = 0
    for i in range(n_obs):
        if not active_mask[i]:
            continue
        row = final_quantiles[i]
        if any(row[j] > row[k] for j in range(n_quantiles) for k in range(j + 1, n_quantiles)):
            repaired_crossing_count += 1

    evaluated_count = int(np.sum(active_mask))
    raw_crossing_count = int(np.sum(is_crossing_raw[active_mask]))
    raw_crossing_rate = float(raw_crossing_count / evaluated_count) if evaluated_count > 0 else 0.0
    repaired_crossing_rate = (
        float(repaired_crossing_count / evaluated_count) if evaluated_count > 0 else 0.0
    )
    max_crossing_delta = (
        float(np.max(max_violations_lpa[active_mask])) if evaluated_count > 0 else 0.0
    )

    diagnostics = CrossingDiagnostics(
        total_observations=n_obs,
        evaluated_observations=evaluated_count,
        raw_crossing_count=raw_crossing_count,
        raw_crossing_rate=raw_crossing_rate,
        repaired_crossing_count=repaired_crossing_count,
        repaired_crossing_rate=repaired_crossing_rate,
        max_raw_crossing_delta_lpa=max_crossing_delta,
    )

    return final_quantiles, is_crossing_raw, max_violations_lpa, diagnostics


class BaseGBMQuantileModel(ABC):
    """Abstract base class for Rung E gradient boosted quantile models on log pay."""

    def __init__(self, config: GBMQuantileConfig | None = None) -> None:
        """Initialize base gradient boosted quantile model."""
        self.config: GBMQuantileConfig = config or GBMQuantileConfig()
        self._is_fitted: bool = False
        self._median_yoe: float = 3.0
        self._known_categories: dict[str, list[str]] = {}
        self._metrics: TrainingMetrics | None = None
        self._target_col: str = "guaranteed_cash_annual"
        self._last_diagnostics: CrossingDiagnostics | None = None

    @property
    def is_fitted(self) -> bool:
        """Return True if the model has been fitted on training data."""
        return self._is_fitted

    @property
    def metrics(self) -> TrainingMetrics | None:
        """Return resource profiling and execution metrics after fitting."""
        return self._metrics

    @property
    def last_diagnostics(self) -> CrossingDiagnostics | None:
        """Return crossing diagnostics from the most recent prediction pass."""
        return self._last_diagnostics

    @property
    def quantiles(self) -> tuple[float, ...]:
        """Return target quantiles configured for this model."""
        return self.config.quantiles

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return identifier string of the boosting model family."""

    @abstractmethod
    def _fit_model(self, features_df: pd.DataFrame, y: np.ndarray) -> None:
        """Fit the underlying gradient boosted quantile regressor(s) on preprocessed features."""

    @abstractmethod
    def _predict_raw_quantiles(self, features_df: pd.DataFrame) -> np.ndarray:
        """Produce raw quantile predictions in log space of shape (N, K)."""

    def _prepare_features(
        self,
        df: pl.DataFrame,
        is_training: bool = False,
    ) -> pd.DataFrame:
        """Extract and prepare feature DataFrame with correct types at library boundary.

        Enforces Rule R-MD-04 (preprocessing fitted strictly inside training folds).

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

        p_df = df.select([*FEATURE_COLS_CATEGORICAL, "years_experience"]).to_pandas()

        # Handle continuous experience
        if is_training:
            valid_yoe = p_df["years_experience"].dropna()
            self._median_yoe = float(valid_yoe.median()) if not valid_yoe.empty else 3.0

        p_df["years_experience"] = p_df["years_experience"].fillna(self._median_yoe).astype(float)

        # Handle categorical features
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

        Adheres to Rule R-MD-08.

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

    def fit(self, df: pl.DataFrame) -> BaseGBMQuantileModel:
        """Fit quantile regressors on training observations with resource and memory profiling.

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

    def predict(self, df: pl.DataFrame) -> list[QuantilePrediction]:
        """Generate structured conditional quantile predictions for observations.

        Adheres to Rules R-UQ-01, R-UQ-05, and R-MD-08.

        Args:
            df: Input Polars DataFrame.

        Returns:
            List of QuantilePrediction instances with nominal INR LPA values.
        """
        if not self._is_fitted:
            msg = f"{self.model_name} must be fitted before predict."
            raise RuntimeError(msg)

        n = len(df)
        if n == 0:
            self._last_diagnostics = CrossingDiagnostics(
                total_observations=0,
                evaluated_observations=0,
                raw_crossing_count=0,
                raw_crossing_rate=0.0,
                repaired_crossing_count=0,
                repaired_crossing_rate=0.0,
                max_raw_crossing_delta_lpa=0.0,
            )
            return []

        abstained_mask, reasons = self._check_abstention(df)
        features_df = self._prepare_features(df, is_training=False)

        start_time = time.perf_counter()
        raw_preds_log = self._predict_raw_quantiles(features_df)
        predict_duration_ms = ((time.perf_counter() - start_time) * 1000.0) / max(1, n)

        # Invert log pay to nominal INR LPA per Rule R-MD-06
        raw_preds_lpa = np.exp(raw_preds_log) if self.config.log_target else raw_preds_log

        # Execute crossing detection and monotonic rearrangement repair (Rule R-UQ-05)
        active_mask = ~abstained_mask
        final_preds_lpa, is_repaired_flags, _, diagnostics = detect_and_repair_quantile_crossings(
            raw_quantiles_lpa=raw_preds_lpa,
            evaluated_mask=active_mask,
            repair=self.config.repair_crossing,
        )
        self._last_diagnostics = diagnostics

        # Update predict latency in metrics if available
        if self._metrics is not None:
            self._metrics = self._metrics.model_copy(
                update={"predict_latency_ms": predict_duration_ms}
            )

        # Index mapping for standard quantiles (0.10, 0.50, 0.90)
        q_list = list(self.config.quantiles)
        idx_10 = q_list.index(0.10) if 0.10 in q_list else 0
        idx_50 = q_list.index(0.50) if 0.50 in q_list else (len(q_list) // 2)
        idx_90 = q_list.index(0.90) if 0.90 in q_list else (len(q_list) - 1)

        predictions: list[QuantilePrediction] = []
        for i in range(n):
            if abstained_mask[i]:
                predictions.append(
                    QuantilePrediction(
                        p10=None,
                        p50=None,
                        p90=None,
                        raw_p10=None,
                        raw_p50=None,
                        raw_p90=None,
                        is_crossing_repaired=False,
                        is_abstained=True,
                        abstention_reason=reasons[i],
                        model_name=self.model_name,
                    )
                )
            else:
                predictions.append(
                    QuantilePrediction(
                        p10=round(float(final_preds_lpa[i, idx_10]), 2),
                        p50=round(float(final_preds_lpa[i, idx_50]), 2),
                        p90=round(float(final_preds_lpa[i, idx_90]), 2),
                        raw_p10=round(float(raw_preds_lpa[i, idx_10]), 2),
                        raw_p50=round(float(raw_preds_lpa[i, idx_50]), 2),
                        raw_p90=round(float(raw_preds_lpa[i, idx_90]), 2),
                        is_crossing_repaired=bool(is_repaired_flags[i]),
                        is_abstained=False,
                        abstention_reason=None,
                        model_name=self.model_name,
                    )
                )

        return predictions

    def predict_df(self, df: pl.DataFrame) -> pl.DataFrame:
        """Generate conditional quantile predictions as a Polars DataFrame.

        Args:
            df: Input Polars DataFrame.

        Returns:
            Polars DataFrame with quantile columns (p10, p50, p90, raw counterparts,
            crossing repair flag, abstention flag, and model name).
        """
        preds = self.predict(df)
        if not preds:
            return pl.DataFrame(
                schema={
                    "p10": pl.Float64,
                    "p50": pl.Float64,
                    "p90": pl.Float64,
                    "raw_p10": pl.Float64,
                    "raw_p50": pl.Float64,
                    "raw_p90": pl.Float64,
                    "is_crossing_repaired": pl.Boolean,
                    "is_abstained": pl.Boolean,
                    "abstention_reason": pl.String,
                    "model_name": pl.String,
                }
            )

        return pl.DataFrame(
            {
                "p10": [p.p10 for p in preds],
                "p50": [p.p50 for p in preds],
                "p90": [p.p90 for p in preds],
                "raw_p10": [p.raw_p10 for p in preds],
                "raw_p50": [p.raw_p50 for p in preds],
                "raw_p90": [p.raw_p90 for p in preds],
                "is_crossing_repaired": [p.is_crossing_repaired for p in preds],
                "is_abstained": [p.is_abstained for p in preds],
                "abstention_reason": [p.abstention_reason for p in preds],
                "model_name": [p.model_name for p in preds],
            },
            schema={
                "p10": pl.Float64,
                "p50": pl.Float64,
                "p90": pl.Float64,
                "raw_p10": pl.Float64,
                "raw_p50": pl.Float64,
                "raw_p90": pl.Float64,
                "is_crossing_repaired": pl.Boolean,
                "is_abstained": pl.Boolean,
                "abstention_reason": pl.String,
                "model_name": pl.String,
            },
        )


class LightGBMQuantileModel(BaseGBMQuantileModel):
    """Rung E quantile model using LightGBM pinball loss regressors."""

    def __init__(self, config: GBMQuantileConfig | None = None) -> None:
        """Initialize LightGBM quantile model."""
        cfg = config or GBMQuantileConfig(model_type=GBMModelType.LIGHTGBM)
        super().__init__(cfg)
        self._regressors: dict[float, lgb.LGBMRegressor] = {}

    @property
    def model_name(self) -> str:
        """Return model family identifier."""
        return "LightGBMQuantileModel"

    def _fit_model(self, features_df: pd.DataFrame, y: np.ndarray) -> None:
        """Fit separate LightGBM quantile regressors for each target quantile."""
        n_samples = len(features_df)
        self._regressors.clear()

        for q in self.config.quantiles:
            params: dict[str, Any] = {
                "objective": "quantile",
                "alpha": q,
                "learning_rate": self.config.learning_rate,
                "n_estimators": self.config.n_estimators,
                "max_depth": self.config.max_depth,
                "num_leaves": self.config.num_leaves,
                "reg_lambda": self.config.l2_regularization,
                "subsample": self.config.subsample,
                "subsample_freq": 1 if self.config.subsample < 1.0 else 0,
                "colsample_bytree": self.config.colsample_bytree,
                "min_child_samples": min(self.config.min_child_samples, max(1, n_samples // 2)),
                "random_state": self.config.random_seed,
                "verbose": -1,
                "n_jobs": 1,
            }

            reg = lgb.LGBMRegressor(**params)
            reg.fit(features_df, y)
            self._regressors[q] = reg

    def _predict_raw_quantiles(self, features_df: pd.DataFrame) -> np.ndarray:
        """Produce raw quantile predictions in log space of shape (N, K)."""
        if not self._regressors:
            msg = "LightGBM quantile regressors have not been fitted."
            raise RuntimeError(msg)

        preds_list = [self._regressors[q].predict(features_df) for q in self.config.quantiles]
        return np.column_stack(preds_list).astype(np.float64)


class CatBoostQuantileModel(BaseGBMQuantileModel):
    """Rung E quantile model using CatBoost MultiQuantile loss."""

    def __init__(self, config: GBMQuantileConfig | None = None) -> None:
        """Initialize CatBoost quantile model."""
        cfg = config or GBMQuantileConfig(model_type=GBMModelType.CATBOOST)
        super().__init__(cfg)
        self._regressor: cb.CatBoostRegressor | None = None

    @property
    def model_name(self) -> str:
        """Return model family identifier."""
        return "CatBoostQuantileModel"

    def _fit_model(self, features_df: pd.DataFrame, y: np.ndarray) -> None:
        """Fit CatBoost MultiQuantile regressor on native categorical features."""
        cat_features = FEATURE_COLS_CATEGORICAL
        alpha_str = ",".join(str(q) for q in self.config.quantiles)
        loss_func = f"MultiQuantile:alpha={alpha_str}"

        params: dict[str, Any] = {
            "loss_function": loss_func,
            "learning_rate": self.config.learning_rate,
            "iterations": self.config.n_estimators,
            "depth": self.config.max_depth,
            "l2_leaf_reg": self.config.l2_regularization,
            "random_seed": self.config.random_seed,
            "verbose": 0,
            "allow_writing_files": False,
            "thread_count": 1,
        }

        self._regressor = cb.CatBoostRegressor(**params)
        self._regressor.fit(features_df, y, cat_features=cat_features)

    def _predict_raw_quantiles(self, features_df: pd.DataFrame) -> np.ndarray:
        """Produce raw quantile predictions in log space of shape (N, K)."""
        if self._regressor is None:
            msg = "CatBoost MultiQuantile regressor has not been fitted."
            raise RuntimeError(msg)

        raw = self._regressor.predict(features_df)
        arr = np.asarray(raw, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        return arr


def create_gbm_quantile_model(config: GBMQuantileConfig) -> BaseGBMQuantileModel:
    """Factory creating appropriate Rung E GBM quantile model for given configuration.

    Args:
        config: Model configuration specifying model family, quantiles, and parameters.

    Returns:
        Instantiated BaseGBMQuantileModel subclass.
    """
    if config.model_type == GBMModelType.LIGHTGBM:
        return LightGBMQuantileModel(config)
    if config.model_type == GBMModelType.CATBOOST:
        return CatBoostQuantileModel(config)

    msg = f"Unsupported GBM model family: {config.model_type}"
    raise ValueError(msg)
