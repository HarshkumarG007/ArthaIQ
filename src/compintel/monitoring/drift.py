"""Feature and prediction distribution drift detection engine (PRD FR-13, US-08).

Implements:
1. Population Stability Index (PSI) for categorical features and binned continuous distributions.
2. Kolmogorov-Smirnov (KS) two-sample non-parametric test for continuous variables.
3. Standardized DriftReport model with calibrated statistical thresholds (Rule R-CD-05).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

import numpy as np
import scipy.stats  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

DriftStatus = Literal["STABLE", "MODERATE_DRIFT", "SIGNIFICANT_DRIFT"]
DriftMethod = Literal["PSI", "KS"]

# Standard production thresholds for Population Stability Index (PSI)
DEFAULT_PSI_WARNING_THRESHOLD: float = 0.10
DEFAULT_PSI_CRITICAL_THRESHOLD: float = 0.25

# Standard thresholds for Kolmogorov-Smirnov (KS) statistic
DEFAULT_KS_WARNING_THRESHOLD: float = 0.05
DEFAULT_KS_CRITICAL_THRESHOLD: float = 0.12


class DriftReport(BaseModel):
    """Evaluation result for distribution drift on a single feature or target."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    feature_name: str = Field(..., description="Name of the evaluated feature or metric.")
    method: DriftMethod = Field(..., description="Statistical test method (PSI or KS).")
    statistic: float = Field(..., description="Computed test statistic (PSI value or KS distance).")
    p_value: float | None = Field(default=None, description="P-value if applicable (KS test).")
    threshold_warning: float = Field(..., description="Threshold for MODERATE_DRIFT.")
    threshold_critical: float = Field(..., description="Threshold for SIGNIFICANT_DRIFT.")
    status: DriftStatus = Field(..., description="Categorical drift status assessment.")
    description: str = Field(..., description="Human-readable plain-language interpretation.")


def compute_psi(
    baseline: Sequence[Any],
    target: Sequence[Any],
    bins: int = 10,
    is_categorical: bool = False,
    epsilon: float = 1e-4,
) -> float:
    """Compute Population Stability Index (PSI) between baseline and target distributions.

    Formula:
        PSI = sum((target_pct - baseline_pct) * ln(target_pct / baseline_pct))

    Args:
        baseline: Reference baseline sample (e.g., training or calibration distribution).
        target: Operational sample to evaluate for drift (e.g., rolling 30-day queries).
        bins: Number of quantiles for continuous binning (ignored if is_categorical).
        is_categorical: True if inputs represent discrete categories.
        epsilon: Smoothing parameter to prevent division by zero or log(0).

    Returns:
        float: Non-negative PSI value.
    """
    if len(baseline) == 0 or len(target) == 0:
        return 0.0

    if is_categorical:
        categories = sorted(set(baseline).union(set(target)))
        if not categories:
            return 0.0

        base_counts = dict.fromkeys(categories, 0)
        for item in baseline:
            base_counts[item] += 1

        target_counts = dict.fromkeys(categories, 0)
        for item in target:
            target_counts[item] += 1

        n_base = float(len(baseline))
        n_target = float(len(target))

        psi = 0.0
        for cat in categories:
            p = max((target_counts[cat] / n_target), epsilon)
            q = max((base_counts[cat] / n_base), epsilon)
            psi += (p - q) * math.log(p / q)

        return float(max(0.0, psi))

    # Continuous binning using baseline quantiles
    base_arr = np.asarray(baseline, dtype=float)
    target_arr = np.asarray(target, dtype=float)

    # Remove non-finite values
    base_arr = base_arr[np.isfinite(base_arr)]
    target_arr = target_arr[np.isfinite(target_arr)]

    if len(base_arr) == 0 or len(target_arr) == 0:
        return 0.0

    quantiles = np.linspace(0.0, 1.0, bins + 1)
    raw_edges = np.percentile(base_arr, quantiles * 100.0)
    unique_edges = np.unique(raw_edges)

    if len(unique_edges) <= 1:
        return 0.0

    # Expand boundaries slightly to cover all points
    bin_list = [float(x) for x in unique_edges]
    bin_list[0] -= 1e-5
    bin_list[-1] += 1e-5
    bin_edges = np.asarray(bin_list, dtype=float)

    base_hist, _ = np.histogram(base_arr, bins=bin_edges)
    target_hist, _ = np.histogram(target_arr, bins=bin_edges)

    n_base = float(len(base_arr))
    n_target = float(len(target_arr))

    psi = 0.0
    for b_count, t_count in zip(base_hist, target_hist, strict=True):
        p = float(max(float(t_count) / n_target, epsilon))
        q = float(max(float(b_count) / n_base, epsilon))
        psi += (p - q) * math.log(p / q)

    return float(max(0.0, psi))


def compute_ks(
    baseline: Sequence[float],
    target: Sequence[float],
) -> tuple[float, float]:
    """Compute two-sample Kolmogorov-Smirnov statistic and p-value.

    Args:
        baseline: Reference continuous distribution.
        target: Operational continuous distribution.

    Returns:
        tuple[float, float]: (KS statistic D, asymptotic p-value).
    """
    base_clean = np.asarray(baseline, dtype=float)
    target_clean = np.asarray(target, dtype=float)

    base_clean = base_clean[np.isfinite(base_clean)]
    target_clean = target_clean[np.isfinite(target_clean)]

    if len(base_clean) == 0 or len(target_clean) == 0:
        return 0.0, 1.0

    result = scipy.stats.ks_2samp(base_clean, target_clean)
    return float(result.statistic), float(result.pvalue)


def evaluate_drift(
    feature_name: str,
    baseline: Sequence[Any],
    target: Sequence[Any],
    is_categorical: bool = False,
    psi_warning: float = DEFAULT_PSI_WARNING_THRESHOLD,
    psi_critical: float = DEFAULT_PSI_CRITICAL_THRESHOLD,
    ks_warning: float = DEFAULT_KS_WARNING_THRESHOLD,
    ks_critical: float = DEFAULT_KS_CRITICAL_THRESHOLD,
) -> DriftReport:
    """Evaluate distribution drift using PSI for categorical or KS for continuous data."""
    if is_categorical:
        psi_val = compute_psi(baseline, target, is_categorical=True)
        if psi_val >= psi_critical:
            status: DriftStatus = "SIGNIFICANT_DRIFT"
            desc = f"Significant categorical drift (PSI={psi_val:.3f} >= {psi_critical})."
        elif psi_val >= psi_warning:
            status = "MODERATE_DRIFT"
            desc = f"Moderate categorical drift detected (PSI={psi_val:.3f} >= {psi_warning})."
        else:
            status = "STABLE"
            desc = f"Distribution is stable (PSI={psi_val:.3f} < {psi_warning})."

        return DriftReport(
            feature_name=feature_name,
            method="PSI",
            statistic=round(psi_val, 4),
            p_value=None,
            threshold_warning=psi_warning,
            threshold_critical=psi_critical,
            status=status,
            description=desc,
        )

    # For continuous variables, evaluate Kolmogorov-Smirnov test
    base_floats = [float(x) for x in baseline if x is not None]
    target_floats = [float(x) for x in target if x is not None]

    ks_stat, p_val = compute_ks(base_floats, target_floats)
    if ks_stat >= ks_critical:
        status = "SIGNIFICANT_DRIFT"
        desc = f"Significant continuous drift (KS={ks_stat:.3f} >= {ks_critical}, p={p_val:.4f})."
    elif ks_stat >= ks_warning:
        status = "MODERATE_DRIFT"
        desc = f"Moderate continuous drift (KS={ks_stat:.3f} >= {ks_warning}, p={p_val:.4f})."
    else:
        status = "STABLE"
        desc = f"Distribution is stable (KS={ks_stat:.3f} < {ks_warning}, p={p_val:.4f})."

    return DriftReport(
        feature_name=feature_name,
        method="KS",
        statistic=round(ks_stat, 4),
        p_value=round(p_val, 5),
        threshold_warning=ks_warning,
        threshold_critical=ks_critical,
        status=status,
        description=desc,
    )
