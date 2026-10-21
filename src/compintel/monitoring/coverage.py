"""Realized prediction coverage and slice-level abstention monitoring (PRD FR-13, US-08).

Monitors:
1. Realized empirical coverage of conformal prediction intervals [P10, P90].
2. Abstention rates by demographic and market slice to detect silent failures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

CoverageStatus = Literal["HEALTHY", "WARNING", "DEGRADED"]
AbstentionStatus = Literal["NORMAL", "WARNING", "ANOMALY"]

DEFAULT_NOMINAL_COVERAGE: float = 0.80
DEFAULT_COVERAGE_WARNING_DELTA: float = 0.05
DEFAULT_COVERAGE_CRITICAL_DELTA: float = 0.10

DEFAULT_ABSTENTION_WARNING_RATE: float = 0.30
DEFAULT_ABSTENTION_CRITICAL_RATE: float = 0.50


class CoverageReport(BaseModel):
    """Evaluation result for empirical interval coverage against nominal guarantee."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    nominal_coverage: float = Field(..., description="Expected nominal coverage rate (e.g. 0.80).")
    empirical_coverage: float = Field(
        ..., description="Observed proportion of true pay falling in [P10, P90]."
    )
    n_eval: int = Field(..., description="Sample size of evaluated observations.")
    coverage_delta: float = Field(..., description="Coverage deficit below nominal guarantee.")
    status: CoverageStatus = Field(..., description="Coverage health status assessment.")
    description: str = Field(..., description="Human-readable summary of interval calibration.")


class AbstentionRateReport(BaseModel):
    """Evaluation result for abstention rate in a specific macro slice."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    slice_type: str = Field(..., description="Dimension type (e.g. role_family, location).")
    slice_value: str = Field(..., description="Dimension value (e.g. SWE, BLR).")
    total_queries: int = Field(..., description="Total queries received for this slice.")
    abstained_queries: int = Field(..., description="Number of abstained queries for this slice.")
    abstention_rate: float = Field(..., description="Observed abstention rate (abstained / total).")
    threshold_warning: float = Field(..., description="Warning abstention threshold.")
    threshold_critical: float = Field(..., description="Critical anomaly abstention threshold.")
    status: AbstentionStatus = Field(..., description="Abstention status assessment.")
    description: str = Field(..., description="Human-readable explanation of abstention behavior.")


def evaluate_coverage(
    y_true: Sequence[float],
    y_p10: Sequence[float],
    y_p90: Sequence[float],
    nominal_coverage: float = DEFAULT_NOMINAL_COVERAGE,
    warning_delta: float = DEFAULT_COVERAGE_WARNING_DELTA,
    critical_delta: float = DEFAULT_COVERAGE_CRITICAL_DELTA,
) -> CoverageReport:
    """Evaluate empirical coverage of conformal prediction intervals [P10, P90].

    Args:
        y_true: Actual observed compensation figures.
        y_p10: Predicted P10 lower bounds.
        y_p90: Predicted P90 upper bounds.
        nominal_coverage: Expected coverage guarantee (default: 0.80).
        warning_delta: Allowed coverage deficit before warning (default: 0.05).
        critical_delta: Allowed coverage deficit before critical degradation (default: 0.10).

    Returns:
        CoverageReport: Structured report assessing calibration health.
    """
    y_t = np.asarray(y_true, dtype=float)
    p10 = np.asarray(y_p10, dtype=float)
    p90 = np.asarray(y_p90, dtype=float)

    valid_mask = np.isfinite(y_t) & np.isfinite(p10) & np.isfinite(p90)
    y_t = y_t[valid_mask]
    p10 = p10[valid_mask]
    p90 = p90[valid_mask]

    n_eval = len(y_t)
    if n_eval == 0:
        return CoverageReport(
            nominal_coverage=nominal_coverage,
            empirical_coverage=0.0,
            n_eval=0,
            coverage_delta=nominal_coverage,
            status="DEGRADED",
            description="Zero valid observation pairs available for coverage evaluation.",
        )

    covered = (y_t >= p10) & (y_t <= p90)
    empirical_cov = float(np.mean(covered))
    deficit = max(0.0, nominal_coverage - empirical_cov)

    if deficit >= critical_delta:
        status: CoverageStatus = "DEGRADED"
        desc = (
            f"Coverage degraded: empirical coverage {empirical_cov:.1%} falls "
            f"{deficit:.1%} below nominal {nominal_coverage:.1%} "
            f"(critical limit: {critical_delta:.1%})."
        )
    elif deficit >= warning_delta:
        status = "WARNING"
        desc = (
            f"Coverage warning: empirical coverage {empirical_cov:.1%} is "
            f"{deficit:.1%} below nominal {nominal_coverage:.1%}."
        )
    else:
        status = "HEALTHY"
        desc = (
            f"Coverage healthy: empirical coverage {empirical_cov:.1%} matches "
            f"nominal {nominal_coverage:.1%} guarantee (n={n_eval})."
        )

    return CoverageReport(
        nominal_coverage=nominal_coverage,
        empirical_coverage=round(empirical_cov, 4),
        n_eval=n_eval,
        coverage_delta=round(deficit, 4),
        status=status,
        description=desc,
    )


def evaluate_slice_abstentions(
    slice_type: str,
    slice_value: str,
    total_queries: int,
    abstained_queries: int,
    warning_rate: float = DEFAULT_ABSTENTION_WARNING_RATE,
    critical_rate: float = DEFAULT_ABSTENTION_CRITICAL_RATE,
) -> AbstentionRateReport:
    """Evaluate whether abstention rate in a given slice represents an operational anomaly."""
    rate = 0.0 if total_queries <= 0 else float(abstained_queries) / float(total_queries)

    if rate >= critical_rate and total_queries >= 10:
        status: AbstentionStatus = "ANOMALY"
        desc = (
            f"Severe abstention anomaly in {slice_type}={slice_value}: "
            f"{rate:.1%} of {total_queries} queries abstained (limit: {critical_rate:.1%})."
        )
    elif rate >= warning_rate and total_queries >= 10:
        status = "WARNING"
        desc = (
            f"Elevated abstentions in {slice_type}={slice_value}: "
            f"{rate:.1%} of {total_queries} queries abstained (warning: {warning_rate:.1%})."
        )
    else:
        status = "NORMAL"
        desc = (
            f"Abstention rate in {slice_type}={slice_value} is normal "
            f"({rate:.1%}, n={total_queries})."
        )

    return AbstentionRateReport(
        slice_type=slice_type,
        slice_value=slice_value,
        total_queries=total_queries,
        abstained_queries=abstained_queries,
        abstention_rate=round(rate, 4),
        threshold_warning=warning_rate,
        threshold_critical=critical_rate,
        status=status,
        description=desc,
    )
