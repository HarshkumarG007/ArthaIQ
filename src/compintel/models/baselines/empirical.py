"""Rung A baseline: Empirical conditional quantiles with hierarchical backoff (ADR-0004).

Adheres to:
- Rule R-MD-01: Benchmark ladder foundation; every candidate model must beat Rung A.
- Rule R-MD-08: Thin evidence abstention (THIN_EVIDENCE) when cell support is below threshold.
- Rule R-UQ-01: No lone numbers; outputs P10, P50, P90 with sample sizes and explicit backoff path.
- Rule R-UQ-05: Quantile monotonicity guaranteed (P10 <= P50 <= P90, zero crossing rate).
- Rule R-ER-02: Expected operational outcomes (e.g. abstention) use structured result types.
- Rule R-CD-01: Strict typing and full mypy compliance.
- Rule R-CD-02: Pure functions and deterministic inference without hidden state.
- Rule R-CD-03 & Import Linter: Zero imports of evaluation, serving, ingestion, or quality.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Self

import numpy as np
import polars as pl
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_MIN_SAMPLE_SIZE: int = 5
DEFAULT_GLOBAL_THIN_EVIDENCE_THRESHOLD: int = 5
DEFAULT_QUANTILES: list[float] = [0.10, 0.50, 0.90]


@dataclass(frozen=True)
class BackoffStep:
    """Audit entry recording the evaluation of a specific hierarchical level."""

    level_name: str
    keys: dict[str, str]
    sample_size: int
    is_sufficient: bool
    quantiles: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert step to dictionary."""
        return {
            "level_name": self.level_name,
            "keys": self.keys,
            "sample_size": self.sample_size,
            "is_sufficient": self.is_sufficient,
            "quantiles": self.quantiles,
        }


@dataclass(frozen=True)
class BackoffPath:
    """Complete traversal path and resolution audit for a prediction."""

    steps: list[BackoffStep]
    resolved_level: str | None
    backoff_count: int
    is_fallback: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert path to dictionary."""
        return {
            "steps": [s.to_dict() for s in self.steps],
            "resolved_level": self.resolved_level,
            "backoff_count": self.backoff_count,
            "is_fallback": self.is_fallback,
        }

    def to_json(self) -> str:
        """Serialize backoff path to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass(frozen=True)
class EmpiricalPrediction:
    """Non-parametric conditional quantile prediction conforming to Rule R-UQ-01."""

    p10: float | None
    p50: float | None
    p90: float | None
    sample_size: int
    resolved_level: str | None
    backoff_path: BackoffPath
    is_abstained: bool
    abstention_reason: str | None = None
    target_measure: str = "guaranteed_cash_annual"
    currency: str = "INR"
    pay_period: str = "annual"
    tax_basis: str = "gross_pretax"
    nominal_basis: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert prediction to dictionary."""
        return {
            "p10": self.p10,
            "p50": self.p50,
            "p90": self.p90,
            "sample_size": self.sample_size,
            "resolved_level": self.resolved_level,
            "backoff_path": self.backoff_path.to_dict(),
            "is_abstained": self.is_abstained,
            "abstention_reason": self.abstention_reason,
            "target_measure": self.target_measure,
            "currency": self.currency,
            "pay_period": self.pay_period,
            "tax_basis": self.tax_basis,
            "nominal_basis": self.nominal_basis,
        }


@dataclass(frozen=True)
class HierarchicalLevel:
    """Definition of a single level in the hierarchical backoff ladder."""

    name: str
    columns: list[str]
    min_sample_size: int = DEFAULT_MIN_SAMPLE_SIZE


@dataclass(frozen=True)
class HierarchicalBackoffConfig:
    """Configuration for hierarchical backoff baseline ladder."""

    levels: list[HierarchicalLevel] = field(
        default_factory=lambda: [
            HierarchicalLevel("cell", ["role_family", "seniority", "location"], 5),
            HierarchicalLevel("role_seniority", ["role_family", "seniority"], 5),
            HierarchicalLevel("role_location", ["role_family", "location"], 5),
            HierarchicalLevel("role_family", ["role_family"], 5),
            HierarchicalLevel("global", [], DEFAULT_GLOBAL_THIN_EVIDENCE_THRESHOLD),
        ]
    )
    thin_evidence_threshold: int = DEFAULT_GLOBAL_THIN_EVIDENCE_THRESHOLD
    quantiles: list[float] = field(default_factory=lambda: [0.10, 0.50, 0.90])


class EmpiricalQuantileBaseline:
    """Rung A baseline model computing empirical conditional quantiles with hierarchical backoff.

    Builds pre-aggregated lookup tables across the specified hierarchical backoff ladder.
    For each query profile, evaluates the ladder top-down from finest to coarsest granularity,
    resolving to the most specific level that meets the minimum cohort sample size.
    """

    def __init__(self, config: HierarchicalBackoffConfig | None = None) -> None:
        """Initialize Rung A baseline model."""
        self.config: HierarchicalBackoffConfig = config or HierarchicalBackoffConfig()
        self._is_fitted: bool = False
        self._target_col: str = "guaranteed_cash_annual"
        self._total_records: int = 0
        self._level_tables: dict[str, dict[tuple[str, ...], tuple[int, dict[str, float]]]] = {}
        self._global_stats: tuple[int, dict[str, float]] | None = None

    @property
    def is_fitted(self) -> bool:
        """Return True if model has been fitted on training data."""
        return self._is_fitted

    @property
    def total_records(self) -> int:
        """Return number of training records used in fitting."""
        return self._total_records

    def fit(self, df: pl.DataFrame, target_col: str = "guaranteed_cash_annual") -> Self:
        """Fit empirical quantiles across all levels of the hierarchical ladder.

        Args:
            df: Training DataFrame containing profile dimensions and positive target values.
            target_col: Name of the continuous target column (default: guaranteed_cash_annual).

        Returns:
            Fitted instance of EmpiricalQuantileBaseline.

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

        self._level_tables.clear()
        self._global_stats = None

        # Build lookup tables for each hierarchical level
        for level in self.config.levels:
            if not level.columns:
                # Global level
                target_vals = valid_df.get_column(target_col).to_numpy()
                count = len(target_vals)
                q_dict = {
                    f"p{int(round(q * 100)):02d}": float(np.quantile(target_vals, q))
                    for q in self.config.quantiles
                }
                self._global_stats = (count, q_dict)
                continue

            # Ensure all group columns exist in df
            missing_cols = [c for c in level.columns if c not in valid_df.columns]
            if missing_cols:
                logger.warning(
                    "Skipping hierarchical level due to missing columns",
                    level=level.name,
                    missing=missing_cols,
                )
                continue

            # Group by level columns and compute count and quantiles
            # Cast group columns to string for uniform tuple key indexing
            grouped = (
                valid_df.select([*level.columns, target_col])
                .drop_nulls(subset=level.columns)
                .with_columns([pl.col(c).cast(pl.String).fill_null("") for c in level.columns])
                .group_by(level.columns)
                .agg(
                    [
                        pl.len().alias("sample_size"),
                        pl.col(target_col).alias("target_values"),
                    ]
                )
            )

            level_dict: dict[tuple[str, ...], tuple[int, dict[str, float]]] = {}
            for row in grouped.iter_rows(named=True):
                key = tuple(str(row[c]) for c in level.columns)
                sample_size = int(row["sample_size"])
                vals = np.array(row["target_values"], dtype=np.float64)
                q_dict = {
                    f"p{int(round(q * 100)):02d}": float(np.quantile(vals, q))
                    for q in self.config.quantiles
                }
                level_dict[key] = (sample_size, q_dict)

            self._level_tables[level.name] = level_dict

        self._is_fitted = True
        logger.info(
            "EmpiricalQuantileBaseline fitted successfully",
            total_records=self._total_records,
            levels_fitted=list(self._level_tables.keys()),
            has_global=self._global_stats is not None,
        )
        return self

    def predict_record(self, **kwargs: Any) -> EmpiricalPrediction:
        """Predict empirical conditional quantiles for a single profile query.

        Args:
            **kwargs: Profile dimension values (e.g., role_family="SWE",
                seniority="MID", location="BENGALURU").

        Returns:
            EmpiricalPrediction containing quantiles, backoff path, and abstention status.

        Raises:
            RuntimeError: If model is not fitted.
        """
        if not self._is_fitted:
            msg = "EmpiricalQuantileBaseline must be fitted before predict."
            raise RuntimeError(msg)

        steps: list[BackoffStep] = []
        backoff_count = 0
        resolved_step: BackoffStep | None = None

        for idx, level in enumerate(self.config.levels):
            if not level.columns:
                # Global level
                if self._global_stats is not None:
                    sample_size, q_dict = self._global_stats
                    is_sufficient = sample_size >= level.min_sample_size
                    step = BackoffStep(
                        level_name=level.name,
                        keys={},
                        sample_size=sample_size,
                        is_sufficient=is_sufficient,
                        quantiles=q_dict if is_sufficient else None,
                    )
                    steps.append(step)
                    if is_sufficient:
                        resolved_step = step
                        backoff_count = idx
                        break
                continue

            # Extract keys for this level
            keys = {c: str(kwargs.get(c, "")) for c in level.columns}
            key_tuple = tuple(keys[c] for c in level.columns)

            table = self._level_tables.get(level.name)
            if table is not None and key_tuple in table:
                sample_size, q_dict = table[key_tuple]
                is_sufficient = sample_size >= level.min_sample_size
                step = BackoffStep(
                    level_name=level.name,
                    keys=keys,
                    sample_size=sample_size,
                    is_sufficient=is_sufficient,
                    quantiles=q_dict if is_sufficient else None,
                )
                steps.append(step)
                if is_sufficient:
                    resolved_step = step
                    backoff_count = idx
                    break
            else:
                # Cell not found in training data (sample_size = 0)
                step = BackoffStep(
                    level_name=level.name,
                    keys=keys,
                    sample_size=0,
                    is_sufficient=False,
                    quantiles=None,
                )
                steps.append(step)

        if resolved_step is not None and resolved_step.quantiles is not None:
            path = BackoffPath(
                steps=steps,
                resolved_level=resolved_step.level_name,
                backoff_count=backoff_count,
                is_fallback=backoff_count > 0,
            )
            return EmpiricalPrediction(
                p10=resolved_step.quantiles.get("p10"),
                p50=resolved_step.quantiles.get("p50"),
                p90=resolved_step.quantiles.get("p90"),
                sample_size=resolved_step.sample_size,
                resolved_level=resolved_step.level_name,
                backoff_path=path,
                is_abstained=False,
                abstention_reason=None,
            )

        # If no level satisfied the sufficiency threshold -> Abstain
        path = BackoffPath(
            steps=steps,
            resolved_level=None,
            backoff_count=len(steps),
            is_fallback=True,
        )
        return EmpiricalPrediction(
            p10=None,
            p50=None,
            p90=None,
            sample_size=0,
            resolved_level=None,
            backoff_path=path,
            is_abstained=True,
            abstention_reason="THIN_EVIDENCE",
        )

    def predict_records(self, df: pl.DataFrame) -> list[EmpiricalPrediction]:
        """Predict empirical conditional quantiles for all rows in a DataFrame.

        Args:
            df: Query DataFrame containing profile feature columns.

        Returns:
            List of EmpiricalPrediction objects.
        """
        rows = df.iter_rows(named=True)
        return [self.predict_record(**r) for r in rows]

    def predict(self, df: pl.DataFrame) -> pl.DataFrame:
        """Predict empirical conditional quantiles, returning a Polars DataFrame.

        Outputs schema:
        - p10: Float64 (null if abstained)
        - p50: Float64 (null if abstained)
        - p90: Float64 (null if abstained)
        - sample_size: Int64
        - resolved_level: String (null if abstained)
        - backoff_count: Int64
        - is_fallback: Boolean
        - is_abstained: Boolean
        - abstention_reason: String (null if not abstained)
        - backoff_path_json: String (JSON-serialized audit of backoff resolution)

        Args:
            df: Query DataFrame containing profile feature columns.

        Returns:
            Polars DataFrame containing prediction results and backoff paths.
        """
        preds = self.predict_records(df)

        return pl.DataFrame(
            {
                "p10": [p.p10 for p in preds],
                "p50": [p.p50 for p in preds],
                "p90": [p.p90 for p in preds],
                "sample_size": [p.sample_size for p in preds],
                "resolved_level": [p.resolved_level for p in preds],
                "backoff_count": [p.backoff_path.backoff_count for p in preds],
                "is_fallback": [p.backoff_path.is_fallback for p in preds],
                "is_abstained": [p.is_abstained for p in preds],
                "abstention_reason": [p.abstention_reason for p in preds],
                "backoff_path_json": [p.backoff_path.to_json() for p in preds],
            },
            schema={
                "p10": pl.Float64,
                "p50": pl.Float64,
                "p90": pl.Float64,
                "sample_size": pl.Int64,
                "resolved_level": pl.String,
                "backoff_count": pl.Int64,
                "is_fallback": pl.Boolean,
                "is_abstained": pl.Boolean,
                "abstention_reason": pl.String,
                "backoff_path_json": pl.String,
            },
        )

    def get_cell_summary(self) -> pl.DataFrame:
        """Return diagnostic DataFrame summarizing all fitted cells and quantiles across levels."""
        if not self._is_fitted:
            msg = "EmpiricalQuantileBaseline must be fitted to get cell summary."
            raise RuntimeError(msg)

        records: list[dict[str, Any]] = []

        for level_name, table in self._level_tables.items():
            for key, (sample_size, q_dict) in table.items():
                record: dict[str, Any] = {
                    "level_name": level_name,
                    "key": "/".join(key),
                    "sample_size": sample_size,
                }
                record.update(q_dict)
                records.append(record)

        if self._global_stats is not None:
            sample_size, q_dict = self._global_stats
            record = {
                "level_name": "global",
                "key": "*",
                "sample_size": sample_size,
            }
            record.update(q_dict)
            records.append(record)

        return pl.DataFrame(records)
