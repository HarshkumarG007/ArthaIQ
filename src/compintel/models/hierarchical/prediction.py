"""Prediction data structures and crossing diagnostics for Rung C hierarchical models (T6.02a).

Adheres to:
- Rule R-UQ-01: No lone numbers; outputs P10, P50, P90 with sample sizes and shrinkage metadata.
- Rule R-UQ-05: Quantile monotonicity guaranteed (zero crossing rate after monotone repair).
- Rule R-ER-02: Structured result types for operational outcomes (e.g. abstention).
- Rule R-CD-01: Strict typing and full mypy compliance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class HierarchicalPrediction:
    """Parametric conditional quantile prediction from Rung C hierarchical partial pooling."""

    p10: float | None
    p50: float | None
    p90: float | None
    point_estimate: float | None
    log_mean: float | None
    log_std: float | None
    shrinkage_weights: dict[str, float] = field(default_factory=dict)
    shrunk_components: dict[str, float] = field(default_factory=dict)
    effective_sample_sizes: dict[str, int] = field(default_factory=dict)
    is_crossing_repaired: bool = False
    is_abstained: bool = False
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
class HierarchicalCrossingDiagnostics:
    """Audit diagnostics for quantile crossing detection and monotone rearrangement repair."""

    pre_repair_crossing_count: int
    pre_repair_crossing_rate: float
    max_crossing_magnitude_lpa: float
    post_repair_crossing_rate: float
    is_crossing_free: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert diagnostics to dictionary representation."""
        return asdict(self)
