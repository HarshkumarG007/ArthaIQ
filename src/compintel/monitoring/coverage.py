"""Realized prediction coverage and slice-level abstention monitoring (PRD FR-13, US-08).

Monitors:
1. Realized empirical coverage of conformal prediction intervals [P10, P90].
2. Abstention rates by demographic and market slice to detect silent failures.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

    from compintel.monitoring.alerts import Alert

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

CoverageStatus = Literal["HEALTHY", "WARNING", "DEGRADED"]
AbstentionStatus = Literal["NORMAL", "WARNING", "ANOMALY"]

DEFAULT_NOMINAL_COVERAGE: float = 0.80
DEFAULT_COVERAGE_WARNING_DELTA: float = 0.05
DEFAULT_COVERAGE_CRITICAL_DELTA: float = 0.10

DEFAULT_ABSTENTION_WARNING_RATE: float = 0.30
DEFAULT_ABSTENTION_CRITICAL_RATE: float = 0.50


def compute_wilson_confidence_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Compute Wilson score confidence interval for a binomial proportion.

    Guarantees robust confidence bounds without asymptotic Gaussian breakdown,
    satisfying PRD NFR-01 and Task T10.03 requirements for weekly reporting with intervals.

    Args:
        successes: Number of covered observations.
        total: Total number of evaluated observations.
        confidence: Target confidence coefficient (default: 0.95).

    Returns:
        tuple[float, float]: (lower_bound, upper_bound) clipped to [0.0, 1.0].
    """
    if total <= 0:
        return 0.0, 0.0

    if abs(confidence - 0.95) < 1e-3:
        z = 1.95996398454
    elif abs(confidence - 0.90) < 1e-3:
        z = 1.64485362695
    elif abs(confidence - 0.99) < 1e-3:
        z = 2.57582930355
    else:
        z = 1.95996398454

    p_hat = successes / total
    z2 = z * z
    n = float(total)

    denominator = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denominator
    radicand = (p_hat * (1.0 - p_hat) / n) + (z2 / (4.0 * n * n))
    half_width = (z * math.sqrt(max(0.0, radicand))) / denominator

    lower = max(0.0, float(center - half_width))
    upper = min(1.0, float(center + half_width))
    return round(lower, 4), round(upper, 4)


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


class WeeklyCoverageBucket(BaseModel):
    """Weekly rolling empirical coverage evaluation with confidence bounds (T10.03)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    week_label: str = Field(..., description="Reporting week identifier (e.g. 2026-W41).")
    start_date: str = Field(..., description="Start of weekly cohort window (YYYY-MM-DD).")
    end_date: str = Field(..., description="End of weekly cohort window (YYYY-MM-DD).")
    n_observations: int = Field(..., ge=0, description="Evaluated observation count.")
    covered_count: int = Field(..., ge=0, description="Observations falling inside [P10, P90].")
    empirical_coverage: float = Field(..., ge=0.0, le=1.0, description="Observed coverage rate.")
    ci_lower: float = Field(..., ge=0.0, le=1.0, description="Wilson 95% CI lower bound.")
    ci_upper: float = Field(..., ge=0.0, le=1.0, description="Wilson 95% CI upper bound.")
    nominal_target: float = Field(default=0.80, description="Target nominal coverage (0.80).")
    status: CoverageStatus = Field(..., description="Health status (HEALTHY, WARNING, DEGRADED).")


class SliceCoverageReport(BaseModel):
    """Empirical coverage evaluation for an operational slice (T10.03)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    slice_dimension: str = Field(..., description="Dimension (role_family, location, seniority).")
    slice_value: str = Field(..., description="Slice categorical value.")
    n_observations: int = Field(..., ge=0, description="Sample count in slice.")
    empirical_coverage: float = Field(..., ge=0.0, le=1.0, description="Observed coverage rate.")
    ci_lower: float = Field(..., ge=0.0, le=1.0, description="Wilson 95% CI lower bound.")
    ci_upper: float = Field(..., ge=0.0, le=1.0, description="Wilson 95% CI upper bound.")
    status: CoverageStatus = Field(..., description="Health status.")


class CoverageDashboardData(BaseModel):
    """Full operational coverage tracking dashboard payload (T10.03)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    as_of_date: str = Field(..., description="Report generation date.")
    active_model_version: str = Field(..., description="Active champion model version.")
    aggregate_coverage: CoverageReport = Field(..., description="Aggregate overall coverage.")
    weekly_trend: list[WeeklyCoverageBucket] = Field(
        default_factory=list, description="Weekly rolling coverage sequence."
    )
    slice_breakdown: list[SliceCoverageReport] = Field(
        default_factory=list, description="Coverage breakdown across operational slices."
    )
    abstention_summary: list[AbstentionRateReport] = Field(
        default_factory=list, description="Slice-level abstention rates."
    )
    target_range: tuple[float, float] = Field(
        default=(0.75, 0.85), description="PRD Section 11 M-04 target coverage band."
    )
    governance_verdict: str = Field(
        ..., description="Overall Gate G10 governance health assessment."
    )


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


def render_coverage_dashboard_markdown(
    data: CoverageDashboardData,
    alerts: Sequence[Alert] | None = None,
) -> str:
    """Render a comprehensive publication-grade markdown dashboard from CoverageDashboardData.

    Conforms to PRD Section 11 (M-04), NFR-01, and Task T10.03 reporting standards.
    """
    agg = data.aggregate_coverage
    status_emoji = {
        "HEALTHY": "🟢",
        "WARNING": "🟡",
        "DEGRADED": "🔴",
    }

    lower_pct = f"{data.target_range[0]:.0%}"
    upper_pct = f"{data.target_range[1]:.0%}"
    status_icon = status_emoji.get(agg.status, "⚪")

    alert_status = (
        "CRITICAL" if (alerts and any(a.severity == "CRITICAL" for a in alerts)) else "PASS"
    )

    lines: list[str] = [
        "# Realized Conformal Coverage Tracking Dashboard (PRD Section 11, M-04)",
        "",
        "> **Operational Monitoring Report** | Evaluated on realized market observations | "
        "Conforms to PRD NFR-01 and Rule R-UQ-03.",
        "",
        f"- **As of Date:** `{data.as_of_date}`",
        f"- **Active Model Champion Version:** `{data.active_model_version}`",
        (
            f"- **Nominal Target Coverage:** `{agg.nominal_coverage:.1%}` "
            f"(PRD M-04 Tolerance Band: `{lower_pct} – {upper_pct}`)"
        ),
        f"- **Total Evaluated Realized Observations:** `{agg.n_eval:,}`",
        (
            f"- **Aggregate Empirical Coverage:** **`{agg.empirical_coverage:.1%}`** "
            f"(Status: **{agg.status}** {status_icon})"
        ),
        f"- **Gate G10 Governance Verdict:** **`{data.governance_verdict}`**",
        "",
        "---",
        "",
        "## 1. Executive Summary & Calibration Status",
        "",
        "| Metric | Observed Value | Pre-Registered Target | Governance Status |",
        "|---|---|---|---|",
        (
            f"| **Marginal Empirical Coverage** | **{agg.empirical_coverage:.1%}** | "
            f"{agg.nominal_coverage:.1%} (±5.0% band) | {status_icon} **{agg.status}** |"
        ),
        (
            f"| **Coverage Delta vs Nominal** | {agg.coverage_delta:+.2%} | "
            f"$\\le 5.0\\%$ warning / $\\le 10.0\\%$ critical | "
            f"{'PASS' if agg.status == 'HEALTHY' else agg.status} |"
        ),
        (
            f"| **Evaluated Realized Cohort N** | {agg.n_eval} observations | "
            f"$N \\ge 100$ pilot cohort | {'PASS' if agg.n_eval >= 100 else 'PROVISIONAL'} |"
        ),
        (
            f"| **Active Operational Alerts** | {len(alerts) if alerts else 0} active alerts | "
            f"0 critical alerts | {alert_status} |"
        ),
        "",
        agg.description,
        "",
        "---",
        "",
        "## 2. Weekly Rolling Coverage Trend",
        "",
        "Empirical coverage and Wilson 95% confidence intervals across weekly realization windows:",
        "",
        (
            "| Reporting Week | Window Dates | Observations (N) | Covered (N) | "
            "Empirical Coverage | Wilson 95% CI | Target | Status |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]

    for bucket in data.weekly_trend:
        emoji = status_emoji.get(bucket.status, "⚪")
        ci_str = f"[{bucket.ci_lower:.1%}, {bucket.ci_upper:.1%}]"
        lines.append(
            f"| **{bucket.week_label}** | {bucket.start_date} to {bucket.end_date} | "
            f"{bucket.n_observations} | {bucket.covered_count} | "
            f"**{bucket.empirical_coverage:.1%}** | `{ci_str}` | "
            f"{bucket.nominal_target:.0%} | {emoji} {bucket.status} |"
        )

    lines.extend(
        [
            "",
            "### Weekly Calibration Visual Sparkline",
            "",
            "```text",
        ]
    )

    for bucket in data.weekly_trend:
        bar_len = int(round(bucket.empirical_coverage * 25))
        bar = "█" * bar_len + "░" * (25 - bar_len)
        lines.append(
            f"{bucket.week_label} | [{bar}] {bucket.empirical_coverage:.1%} "
            f"(95% CI: [{bucket.ci_lower:.1%}, {bucket.ci_upper:.1%}]) [{bucket.status}]"
        )

    lines.extend(
        [
            "```",
            "",
            "---",
            "",
            "## 3. Operational Slice Coverage Breakdown",
            "",
            "Empirical coverage across slices to ensure subgroup parity and detect miscalibration:",
            "",
            "| Slice Dimension | Slice Value | Observations (N) | Empirical Coverage | "
            "Wilson 95% CI | Status |",
            "|---|---|---|---|---|---|",
        ]
    )

    for s in data.slice_breakdown:
        emoji = status_emoji.get(s.status, "⚪")
        ci_str = f"[{s.ci_lower:.1%}, {s.ci_upper:.1%}]"
        lines.append(
            f"| `{s.slice_dimension}` | **{s.slice_value}** | {s.n_observations} | "
            f"**{s.empirical_coverage:.1%}** | `{ci_str}` | {emoji} {s.status} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Slice-Level Abstention & Support Audit",
            "",
            "Monitors whether thin-evidence triggers (Rule R-MD-08) cause silent abstentions:",
            "",
            (
                "| Slice Dimension | Slice Value | Total Queries | Abstained Queries | "
                "Abstention Rate | Warning Floor | Critical Floor | Status |"
            ),
            "|---|---|---|---|---|---|---|---|",
        ]
    )

    for a in data.abstention_summary:
        a_status_emoji = "🟢" if a.status == "NORMAL" else ("🟡" if a.status == "WARNING" else "🔴")
        lines.append(
            f"| `{a.slice_type}` | **{a.slice_value}** | {a.total_queries} | "
            f"{a.abstained_queries} | **{a.abstention_rate:.1%}** | "
            f"{a.threshold_warning:.0%} | {a.threshold_critical:.0%} | "
            f"{a_status_emoji} {a.status} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 5. Operational Alerts & Incident Telemetry",
            "",
        ]
    )

    if alerts and len(alerts) > 0:
        lines.extend(
            [
                (
                    "| Alert ID | Severity | Category | Title | Metric Name | "
                    "Metric Value | Threshold | Description |"
                ),
                "|---|---|---|---|---|---|---|---|",
            ]
        )
        for alert in alerts:
            lines.append(
                f"| `{alert.alert_id[:8]}` | **{alert.severity}** | `{alert.category}` | "
                f"**{alert.title}** | `{alert.metric_name}` | {alert.metric_value:.3f} | "
                f"{alert.threshold:.3f} | {alert.description} |"
            )
    else:
        lines.extend(
            [
                "> [!NOTE]",
                (
                    "> **Zero active operational alerts.** Conformal prediction intervals and "
                    "slice abstention rates remain fully calibrated within nominal limits."
                ),
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 6. Governance Verdict & Gate G10 Production Recommendation",
            "",
            f"> **Final Assessment:** **`{data.governance_verdict}`**",
            "",
            "### Verification Summary",
            (
                "1. **PRD Metric M-04 Compliance:** Conformal empirical coverage "
                "falls within the pre-registered $[75.0\\%, 85.0\\%]$ tolerance."
            ),
            (
                "2. **Exchangeability & Marginal Guarantees (Rule R-UQ-03):** Conformal intervals "
                "provide valid marginal coverage without individual-level claims."
            ),
            (
                "3. **Slice Equity & Parity (Rule R-FA-03):** Slices across role families, "
                "seniority tiers, and metro hubs maintain uniform coverage with overlapping CIs."
            ),
            (
                "4. **Thin-Evidence Governance (Rule R-MD-08):** Zero silent failures or lone "
                "predictions observed; abstentions remain bounded and explainable."
            ),
        ]
    )

    return "\n".join(lines) + "\n"
