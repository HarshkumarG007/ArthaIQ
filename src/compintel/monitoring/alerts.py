"""Operational alert management and dispatch engine (PRD FR-13, US-08).

Evaluates telemetry, drift, coverage, and freshness reports, generates structured
alerts with calibrated severities (WARNING, CRITICAL), and dispatches notifications
via structured logging (Rule R-CD-06, R-ER-07).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from compintel.logging import get_logger

if TYPE_CHECKING:
    from compintel.monitoring.coverage import AbstentionRateReport, CoverageReport
    from compintel.monitoring.drift import DriftReport
    from compintel.monitoring.freshness import FreshnessReport

logger = get_logger(__name__)

AlertSeverity = Literal["WARNING", "CRITICAL"]
AlertCategory = Literal["DRIFT", "COVERAGE", "FRESHNESS", "ABSTENTION"]


class Alert(BaseModel):
    """Structured operational alert event."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    alert_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique alert UUID.")
    category: AlertCategory = Field(..., description="Operational area of concern.")
    severity: AlertSeverity = Field(..., description="Alert urgency tier (WARNING or CRITICAL).")
    title: str = Field(..., description="Concise human-readable alert title.")
    description: str = Field(..., description="Full descriptive diagnostic detail.")
    metric_name: str = Field(..., description="Triggering metric or feature identifier.")
    metric_value: float = Field(..., description="Observed metric value.")
    threshold: float = Field(..., description="Exceeded operational threshold.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Trigger timestamp."
    )


class AlertManager:
    """Manages alert rules, evaluation against reports, and structured dispatch."""

    def __init__(self) -> None:
        self._active_alerts: list[Alert] = []

    def evaluate_drift_reports(self, reports: list[DriftReport]) -> list[Alert]:
        """Convert drift reports exceeding thresholds into active alerts."""
        alerts: list[Alert] = []
        for r in reports:
            if r.status == "SIGNIFICANT_DRIFT":
                alerts.append(
                    Alert(
                        category="DRIFT",
                        severity="CRITICAL",
                        title=f"Critical distribution drift in {r.feature_name}",
                        description=r.description,
                        metric_name=f"{r.feature_name}_{r.method.lower()}",
                        metric_value=r.statistic,
                        threshold=r.threshold_critical,
                    )
                )
            elif r.status == "MODERATE_DRIFT":
                alerts.append(
                    Alert(
                        category="DRIFT",
                        severity="WARNING",
                        title=f"Moderate distribution drift in {r.feature_name}",
                        description=r.description,
                        metric_name=f"{r.feature_name}_{r.method.lower()}",
                        metric_value=r.statistic,
                        threshold=r.threshold_warning,
                    )
                )
        return alerts

    def evaluate_freshness_reports(self, reports: list[FreshnessReport]) -> list[Alert]:
        """Convert freshness reports exceeding SLAs into active alerts."""
        alerts: list[Alert] = []
        for r in reports:
            if r.status == "STALE":
                alerts.append(
                    Alert(
                        category="FRESHNESS",
                        severity="CRITICAL",
                        title=f"Source {r.source_id} is stale",
                        description=r.description,
                        metric_name=f"{r.source_id}_age_days",
                        metric_value=r.age_days,
                        threshold=r.sla_days,
                    )
                )
            elif r.status == "WARNING":
                alerts.append(
                    Alert(
                        category="FRESHNESS",
                        severity="WARNING",
                        title=f"Source {r.source_id} approaching staleness",
                        description=r.description,
                        metric_name=f"{r.source_id}_age_days",
                        metric_value=r.age_days,
                        threshold=r.sla_days * 0.75,
                    )
                )
        return alerts

    def evaluate_coverage_reports(self, reports: list[CoverageReport]) -> list[Alert]:
        """Convert coverage degradation reports into active alerts."""
        alerts: list[Alert] = []
        for r in reports:
            if r.status == "DEGRADED":
                alerts.append(
                    Alert(
                        category="COVERAGE",
                        severity="CRITICAL",
                        title="Conformal interval coverage severely degraded",
                        description=r.description,
                        metric_name="empirical_coverage_deficit",
                        metric_value=r.coverage_delta,
                        threshold=0.10,
                    )
                )
            elif r.status == "WARNING":
                alerts.append(
                    Alert(
                        category="COVERAGE",
                        severity="WARNING",
                        title="Conformal interval coverage warning",
                        description=r.description,
                        metric_name="empirical_coverage_deficit",
                        metric_value=r.coverage_delta,
                        threshold=0.05,
                    )
                )
        return alerts

    def evaluate_abstention_reports(self, reports: list[AbstentionRateReport]) -> list[Alert]:
        """Convert abnormal slice abstention rates into active alerts."""
        alerts: list[Alert] = []
        for r in reports:
            if r.status == "ANOMALY":
                alerts.append(
                    Alert(
                        category="ABSTENTION",
                        severity="CRITICAL",
                        title=f"Abnormal abstention spike in {r.slice_type}={r.slice_value}",
                        description=r.description,
                        metric_name=f"abstention_rate_{r.slice_value}",
                        metric_value=r.abstention_rate,
                        threshold=r.threshold_critical,
                    )
                )
            elif r.status == "WARNING":
                alerts.append(
                    Alert(
                        category="ABSTENTION",
                        severity="WARNING",
                        title=f"Elevated abstentions in {r.slice_type}={r.slice_value}",
                        description=r.description,
                        metric_name=f"abstention_rate_{r.slice_value}",
                        metric_value=r.abstention_rate,
                        threshold=r.threshold_warning,
                    )
                )
        return alerts

    def process_and_dispatch(
        self,
        drift_reports: list[DriftReport] | None = None,
        freshness_reports: list[FreshnessReport] | None = None,
        coverage_reports: list[CoverageReport] | None = None,
        abstention_reports: list[AbstentionRateReport] | None = None,
    ) -> list[Alert]:
        """Evaluate all reports, update active alerts, and emit structured logs."""
        new_alerts: list[Alert] = []

        if drift_reports:
            new_alerts.extend(self.evaluate_drift_reports(drift_reports))
        if freshness_reports:
            new_alerts.extend(self.evaluate_freshness_reports(freshness_reports))
        if coverage_reports:
            new_alerts.extend(self.evaluate_coverage_reports(coverage_reports))
        if abstention_reports:
            new_alerts.extend(self.evaluate_abstention_reports(abstention_reports))

        for alert in new_alerts:
            self._dispatch_single_alert(alert)

        self._active_alerts.extend(new_alerts)
        return new_alerts

    def _dispatch_single_alert(self, alert: Alert) -> None:
        """Emit structured alert log event (Rules R-CD-06, R-ER-07)."""
        log_payload = {
            "alert_id": alert.alert_id,
            "category": alert.category,
            "severity": alert.severity,
            "title": alert.title,
            "metric_name": alert.metric_name,
            "metric_value": alert.metric_value,
            "threshold": alert.threshold,
        }
        if alert.severity == "CRITICAL":
            logger.error("operational_alert_critical", **log_payload)
        else:
            logger.warning("operational_alert_warning", **log_payload)

    @property
    def active_alerts(self) -> list[Alert]:
        """Return list of all currently active alerts."""
        return list(self._active_alerts)

    def clear(self) -> None:
        """Clear active alerts (for test isolation)."""
        self._active_alerts.clear()
