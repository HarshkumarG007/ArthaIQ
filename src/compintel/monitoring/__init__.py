"""ArthaIQ compensation intelligence operational monitoring and telemetry package."""

from __future__ import annotations

from compintel.monitoring.alerts import (
    Alert,
    AlertCategory,
    AlertManager,
    AlertSeverity,
)
from compintel.monitoring.coverage import (
    AbstentionRateReport,
    AbstentionStatus,
    CoverageDashboardData,
    CoverageReport,
    CoverageStatus,
    SliceCoverageReport,
    WeeklyCoverageBucket,
    compute_wilson_confidence_interval,
    evaluate_coverage,
    evaluate_slice_abstentions,
    render_coverage_dashboard_markdown,
)
from compintel.monitoring.drift import (
    DriftMethod,
    DriftReport,
    DriftStatus,
    compute_ks,
    compute_psi,
    evaluate_drift,
)
from compintel.monitoring.freshness import (
    FreshnessReport,
    FreshnessStatus,
    evaluate_freshness,
)
from compintel.monitoring.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    get_metrics_registry,
)

__all__ = [
    "AbstentionRateReport",
    "AbstentionStatus",
    "Alert",
    "AlertCategory",
    "AlertManager",
    "AlertSeverity",
    "Counter",
    "CoverageDashboardData",
    "CoverageReport",
    "CoverageStatus",
    "DriftMethod",
    "DriftReport",
    "DriftStatus",
    "FreshnessReport",
    "FreshnessStatus",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "SliceCoverageReport",
    "WeeklyCoverageBucket",
    "compute_ks",
    "compute_psi",
    "compute_wilson_confidence_interval",
    "evaluate_coverage",
    "evaluate_drift",
    "evaluate_freshness",
    "evaluate_slice_abstentions",
    "get_metrics_registry",
    "render_coverage_dashboard_markdown",
]
