"""Rung B baseline: Regularized linear on log pay & linear quantile regression (ADR-0004).

Adheres to:
- Rule R-MD-01: Benchmark ladder; parametric baseline competing against Rung A.
- Rule R-MD-04: Preprocessing (encoding, scaling, imputation) fit inside training folds only.
- Rule R-MD-06: Log pay target transformation (log guaranteed_cash_annual).
- Rule R-MD-08: Thin evidence abstention (THIN_EVIDENCE) for severe out-of-distribution inputs.
- Rule R-UQ-01: No lone numbers; outputs P10, P50, P90 with definitions and nominal basis.
- Rule R-UQ-05: Detect, report, and repair quantile crossing via monotonic projection.
- Rule R-ER-02: Expected operational outcomes use result types, not exceptions.
- Rule R-CD-01: Strict typing and full mypy compliance.
- Rule R-CD-02: Pure functions and deterministic inference without hidden state.
- Rule R-CD-03 & Import Linter: Zero imports of evaluation, serving, ingestion, or quality.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Self, TypeAlias

import numpy as np
import numpy.typing as npt
import polars as pl
import structlog
from sklearn.linear_model import QuantileRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logger = structlog.get_logger(__name__)

DEFAULT_ALPHA: float = 0.01
DEFAULT_MAX_EXPERIENCE_BOUND: float = 40.0
DEFAULT_QUANTILES: list[float] = [0.10, 0.50, 0.90]

FloatArray: TypeAlias = npt.NDArray[np.float64]


@dataclass(frozen=True)
class LinearPrediction:
    """Parametric conditional quantile prediction conforming to Rules R-UQ-01 & R-UQ-05."""

    p10: float | None
    p50: float | None
    p90: float | None
    is_crossing_repaired: bool
    is_abstained: bool
    abstention_reason: str | None = None
    target_measure: str = "guaranteed_cash_annual"
    currency: str = "INR"
    pay_period: str = "annual"
    tax_basis: str = "gross_pretax"
    nominal_basis: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert prediction to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class LinearQuantileConfig:
    """Configuration for Rung B linear quantile baseline."""

    alpha: float = DEFAULT_ALPHA
    include_quadratic_yoe: bool = True
    max_experience_bound: float = DEFAULT_MAX_EXPERIENCE_BOUND
    quantiles: list[float] = field(default_factory=lambda: [0.10, 0.50, 0.90])
    solver: str = "highs"


class LinearQuantileBaseline:
    """Rung B baseline model: regularized linear quantile regression on log pay.

    Transforms positive target pay to natural log space, encodes categorical dimensions
    (role_family, seniority, location), standardizes professional experience with optional
    Mincerian quadratic curvature, fits independent regularized quantile regressors for
    P10, P50, and P90, exponentiates back to nominal INR LPA, and applies monotonic crossing
    repair (Rule R-UQ-05).
    """

    def __init__(self, config: LinearQuantileConfig | None = None) -> None:
        """Initialize Rung B linear baseline model."""
        self.config: LinearQuantileConfig = config or LinearQuantileConfig()
        self._is_fitted: bool = False
        self._target_col: str = "guaranteed_cash_annual"
        self._total_records: int = 0
        self._encoder: OneHotEncoder | None = None
        self._scaler: StandardScaler | None = None
        self._median_yoe: float = 3.0
        self._quantile_models: dict[float, QuantileRegressor] = {}

    @property
    def is_fitted(self) -> bool:
        """Return True if model has been fitted on training data."""
        return self._is_fitted

    @property
    def total_records(self) -> int:
        """Return number of training records used in fitting."""
        return self._total_records

    def _prepare_feature_matrix(
        self,
        df: pl.DataFrame,
        is_training: bool = False,
    ) -> FloatArray:
        """Extract and transform profile features into a numeric design matrix.

        Args:
            df: DataFrame containing profile columns.
            is_training: Whether to fit encoders/scalers or transform using fitted parameters.

        Returns:
            2D numpy array design matrix X.
        """
        # Categorical columns
        cat_cols = ["role_family", "seniority", "location"]
        for c in cat_cols:
            if c not in df.columns:
                msg = f"Required categorical column '{c}' missing from input DataFrame."
                raise ValueError(msg)

        cat_matrix = (
            df.select(cat_cols)
            .with_columns([pl.col(c).cast(pl.String).fill_null("OTHER") for c in cat_cols])
            .to_numpy()
        )

        if is_training:
            self._encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
            cat_encoded = np.asarray(self._encoder.fit_transform(cat_matrix), dtype=np.float64)
        else:
            if self._encoder is None:
                msg = "Encoder is not fitted."
                raise RuntimeError(msg)
            cat_encoded = np.asarray(self._encoder.transform(cat_matrix), dtype=np.float64)

        # Experience column
        if "years_experience" in df.columns:
            yoe_series = df.get_column("years_experience").to_numpy()
            # Impute missing values with training median
            if is_training:
                valid_yoe = yoe_series[~np.isnan(yoe_series)]
                self._median_yoe = float(np.median(valid_yoe)) if len(valid_yoe) > 0 else 3.0

            clean_yoe = np.where(np.isnan(yoe_series), self._median_yoe, yoe_series).astype(
                np.float64
            )
        else:
            clean_yoe = np.full(len(df), self._median_yoe, dtype=np.float64)

        num_features = [clean_yoe]
        if self.config.include_quadratic_yoe:
            num_features.append(clean_yoe**2)

        num_matrix = np.column_stack(num_features)

        if is_training:
            self._scaler = StandardScaler()
            num_scaled = np.asarray(self._scaler.fit_transform(num_matrix), dtype=np.float64)
        else:
            if self._scaler is None:
                msg = "Scaler is not fitted."
                raise RuntimeError(msg)
            num_scaled = np.asarray(self._scaler.transform(num_matrix), dtype=np.float64)

        return np.asarray(np.hstack([cat_encoded, num_scaled]), dtype=np.float64)

    def fit(self, df: pl.DataFrame, target_col: str = "guaranteed_cash_annual") -> Self:
        """Fit regularized linear quantile models on log target pay.

        Args:
            df: Training DataFrame containing profile dimensions and positive target values.
            target_col: Name of the continuous target column (default: guaranteed_cash_annual).

        Returns:
            Fitted instance of LinearQuantileBaseline.

        Raises:
            ValueError: If target_col is missing or contains no valid positive observations.
        """
        if target_col not in df.columns:
            msg = f"Target column '{target_col}' not found in training DataFrame."
            raise ValueError(msg)

        # Filter to valid positive target observations
        valid_df = df.filter(pl.col(target_col).is_not_null() & (pl.col(target_col) > 0.0))
        self._total_records = len(valid_df)
        self._target_col = target_col

        if self._total_records == 0:
            msg = f"No valid positive observations found in column '{target_col}'."
            raise ValueError(msg)

        # Build design matrix inside training partition (Rule R-MD-04)
        x_mat = self._prepare_feature_matrix(valid_df, is_training=True)

        # Target transformation to log space (Rule R-MD-06)
        y_vals = valid_df.get_column(target_col).to_numpy()
        y_log: FloatArray = np.asarray(np.log(y_vals), dtype=np.float64)

        # Fit independent regularized quantile models for target quantiles
        self._quantile_models.clear()
        for q in self.config.quantiles:
            model = QuantileRegressor(
                quantile=q,
                alpha=self.config.alpha,
                solver=self.config.solver,
            )
            model.fit(x_mat, y_log)
            self._quantile_models[q] = model

        self._is_fitted = True
        logger.info(
            "LinearQuantileBaseline fitted successfully",
            total_records=self._total_records,
            quantiles=self.config.quantiles,
            alpha=self.config.alpha,
        )
        return self

    def predict_record(
        self,
        role_family: str,
        seniority: str,
        location: str,
        years_experience: float | None = None,
    ) -> LinearPrediction:
        """Predict conditional quantiles for a single candidate profile.

        Args:
            role_family: Canonical role family (e.g. 'SWE', 'DATA', 'MLAI').
            seniority: Standardized seniority level (e.g. 'JR', 'MID', 'SR', 'STAFF').
            location: Metro tech hub location (e.g. 'BENGALURU', 'HYDERABAD').
            years_experience: Professional experience in years (optional).

        Returns:
            LinearPrediction containing P10, P50, P90 with crossing repair status.

        Raises:
            RuntimeError: If model is not fitted.
        """
        if not self._is_fitted:
            msg = "LinearQuantileBaseline must be fitted before predict."
            raise RuntimeError(msg)

        # Support check: Out-of-bounds experience trigger abstention (Rule R-MD-08)
        if years_experience is not None and (
            years_experience < 0.0 or years_experience > self.config.max_experience_bound
        ):
            return LinearPrediction(
                p10=None,
                p50=None,
                p90=None,
                is_crossing_repaired=False,
                is_abstained=True,
                abstention_reason="THIN_EVIDENCE",
            )

        single_df = pl.DataFrame(
            [
                {
                    "role_family": role_family,
                    "seniority": seniority,
                    "location": location,
                    "years_experience": years_experience,
                }
            ]
        )

        x_row = self._prepare_feature_matrix(single_df, is_training=False)

        # Evaluate models in log space
        p10_log = float(self._quantile_models[0.10].predict(x_row)[0])
        p50_log = float(self._quantile_models[0.50].predict(x_row)[0])
        p90_log = float(self._quantile_models[0.90].predict(x_row)[0])

        # Exponentiate back to nominal INR LPA (Rule R-MD-06)
        raw_p10 = float(np.exp(p10_log))
        raw_p50 = float(np.exp(p50_log))
        raw_p90 = float(np.exp(p90_log))

        # Quantile crossing check & repair (Rule R-UQ-05)
        is_crossing = raw_p10 > raw_p50 or raw_p50 > raw_p90 or raw_p10 > raw_p90
        sorted_vals = sorted([raw_p10, raw_p50, raw_p90])

        return LinearPrediction(
            p10=round(sorted_vals[0], 2),
            p50=round(sorted_vals[1], 2),
            p90=round(sorted_vals[2], 2),
            is_crossing_repaired=is_crossing,
            is_abstained=False,
            abstention_reason=None,
        )

    def predict(self, df: pl.DataFrame) -> pl.DataFrame:
        """Batch predict conditional quantiles for a DataFrame of profiles.

        Args:
            df: Query DataFrame containing role_family, seniority, location, years_experience.

        Returns:
            Polars DataFrame containing p10, p50, p90, is_crossing_repaired, is_abstained,
            and abstention_reason.
        """
        if not self._is_fitted:
            msg = "LinearQuantileBaseline must be fitted before predict."
            raise RuntimeError(msg)

        n_rows = len(df)
        if n_rows == 0:
            return pl.DataFrame(
                schema={
                    "p10": pl.Float64,
                    "p50": pl.Float64,
                    "p90": pl.Float64,
                    "is_crossing_repaired": pl.Boolean,
                    "is_abstained": pl.Boolean,
                    "abstention_reason": pl.String,
                }
            )

        # Check for out-of-distribution experience support per row
        yoe_col = (
            df.get_column("years_experience").to_numpy()
            if "years_experience" in df.columns
            else np.full(n_rows, self._median_yoe)
        )
        is_unsupported = (yoe_col < 0.0) | (yoe_col > self.config.max_experience_bound)

        x_mat = self._prepare_feature_matrix(df, is_training=False)

        # Predict log quantiles
        p10_log = self._quantile_models[0.10].predict(x_mat)
        p50_log = self._quantile_models[0.50].predict(x_mat)
        p90_log = self._quantile_models[0.90].predict(x_mat)

        # Exponentiate to nominal INR LPA
        p10_raw = np.exp(p10_log)
        p50_raw = np.exp(p50_log)
        p90_raw = np.exp(p90_log)

        # Monotonic sorting / crossing repair row by row (Rule R-UQ-05)
        raw_stack = np.column_stack([p10_raw, p50_raw, p90_raw])
        crossings = (p10_raw > p50_raw) | (p50_raw > p90_raw) | (p10_raw > p90_raw)
        sorted_stack = np.sort(raw_stack, axis=1)

        p10_final: list[float | None] = []
        p50_final: list[float | None] = []
        p90_final: list[float | None] = []
        repaired_flags: list[bool] = []
        abstained_flags: list[bool] = []
        reasons: list[str | None] = []

        for i in range(n_rows):
            if is_unsupported[i]:
                p10_final.append(None)
                p50_final.append(None)
                p90_final.append(None)
                repaired_flags.append(False)
                abstained_flags.append(True)
                reasons.append("THIN_EVIDENCE")
            else:
                p10_final.append(round(float(sorted_stack[i, 0]), 2))
                p50_final.append(round(float(sorted_stack[i, 1]), 2))
                p90_final.append(round(float(sorted_stack[i, 2]), 2))
                repaired_flags.append(bool(crossings[i]))
                abstained_flags.append(False)
                reasons.append(None)

        return pl.DataFrame(
            {
                "p10": p10_final,
                "p50": p50_final,
                "p90": p90_final,
                "is_crossing_repaired": repaired_flags,
                "is_abstained": abstained_flags,
                "abstention_reason": reasons,
            },
            schema={
                "p10": pl.Float64,
                "p50": pl.Float64,
                "p90": pl.Float64,
                "is_crossing_repaired": pl.Boolean,
                "is_abstained": pl.Boolean,
                "abstention_reason": pl.String,
            },
        )
