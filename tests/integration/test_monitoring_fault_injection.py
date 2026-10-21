"""Integration test suite for fault-injected monitoring alerts (Task T9.11b).

Verifies the Definition of Done requirement:
"Done when: alerts fire on injected faults in preview."

Simulates operational faults:
1. Fault A (Stale Data): Injected stale source dataset exceeding freshness SLA.
2. Fault B (Distribution Drift): Injected sudden categorical query drift (PSI >= 0.25).
3. Fault C (Abnormal Abstentions): Injected spike in slice-level abstentions.
4. Fault D (Coverage Degradation): Injected conformal prediction coverage breakdown.
5. Invariant E (Healthy Traffic): Confirms no false positive alerts trigger on nominal data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from compintel.monitoring.alerts import AlertManager
from compintel.monitoring.coverage import evaluate_coverage, evaluate_slice_abstentions
from compintel.monitoring.drift import evaluate_drift
from compintel.monitoring.freshness import evaluate_freshness


@pytest.fixture
def alert_manager() -> AlertManager:
    """Fixture providing a fresh AlertManager instance for test isolation."""
    mgr = AlertManager()
    mgr.clear()
    return mgr


class TestMonitoringFaultInjection:
    """Verifies that alerts fire deterministically on simulated operational anomalies."""

    def test_fault_injection_stale_source_fires_critical_freshness_alert(
        self,
        alert_manager: AlertManager,
    ) -> None:
        """Injecting a dataset 450 days old against a 365-day SLA must fire a CRITICAL alert."""
        evaluation_time = datetime(2026, 10, 21, tzinfo=UTC)
        # Injected stale source (450 days old)
        injected_stale_date = evaluation_time - timedelta(days=450)

        freshness_report = evaluate_freshness(
            source_id="SRC-EPFO-STALE-FAULT",
            latest_date=injected_stale_date,
            sla_days=365.0,
            as_of=evaluation_time,
        )
        assert freshness_report.status == "STALE"

        alerts = alert_manager.process_and_dispatch(freshness_reports=[freshness_report])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.category == "FRESHNESS"
        assert alert.severity == "CRITICAL"
        assert "SRC-EPFO-STALE-FAULT" in alert.title
        assert alert.metric_value == 450.0
        assert alert.threshold == 365.0

    def test_fault_injection_distribution_drift_fires_critical_drift_alert(
        self,
        alert_manager: AlertManager,
    ) -> None:
        """Injecting a severe categorical distribution shift must trigger a CRITICAL drift alert."""
        # Baseline training mix
        baseline_roles = ["SWE"] * 60 + ["DATA"] * 30 + ["MLAI"] * 10
        # Injected operational shift (e.g. scrapers flooded with unexpected categories)
        injected_drifted_roles = ["SECURITY"] * 80 + ["SWE"] * 15 + ["DATA"] * 5

        drift_report = evaluate_drift(
            feature_name="role_family",
            baseline=baseline_roles,
            target=injected_drifted_roles,
            is_categorical=True,
        )
        assert drift_report.status == "SIGNIFICANT_DRIFT"
        assert drift_report.statistic >= 0.25

        alerts = alert_manager.process_and_dispatch(drift_reports=[drift_report])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.category == "DRIFT"
        assert alert.severity == "CRITICAL"
        assert "role_family" in alert.title
        assert alert.metric_value >= 0.25

    def test_fault_injection_abstention_spike_fires_critical_abstention_alert(
        self,
        alert_manager: AlertManager,
    ) -> None:
        """Injecting an 80% abstention rate in a primary metro must trigger a CRITICAL alert."""
        # Injected traffic: 80 out of 100 queries abstaining due to thin support
        abstention_report = evaluate_slice_abstentions(
            slice_type="location",
            slice_value="BENGALURU",
            total_queries=100,
            abstained_queries=80,
            critical_rate=0.50,
        )
        assert abstention_report.status == "ANOMALY"

        alerts = alert_manager.process_and_dispatch(abstention_reports=[abstention_report])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.category == "ABSTENTION"
        assert alert.severity == "CRITICAL"
        assert "BENGALURU" in alert.title
        assert alert.metric_value == 0.80

    def test_fault_injection_coverage_degradation_fires_critical_coverage_alert(
        self,
        alert_manager: AlertManager,
    ) -> None:
        """Injecting predictions where only 55% falls in [P10, P90] must trigger CRITICAL alert."""
        # Injected ground truth vs narrow intervals (under-coverage)
        y_true = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0] * 10
        # Model predicted overly tight bounds around median 30 (fails coverage on extreme ends)
        p10 = [25.0] * 100
        p90 = [35.0] * 100

        coverage_report = evaluate_coverage(
            y_true=y_true,
            y_p10=p10,
            y_p90=p90,
            nominal_coverage=0.80,
        )
        assert coverage_report.status == "DEGRADED"

        alerts = alert_manager.process_and_dispatch(coverage_reports=[coverage_report])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.category == "COVERAGE"
        assert alert.severity == "CRITICAL"
        assert "coverage" in alert.title.lower()

    def test_healthy_operational_conditions_generate_zero_alerts(
        self,
        alert_manager: AlertManager,
    ) -> None:
        """Nominal traffic under all thresholds must produce zero false-positive alerts."""
        now = datetime(2026, 10, 21, tzinfo=UTC)

        freshness = evaluate_freshness("SRC-01", latest_date=now - timedelta(days=30), as_of=now)
        drift = evaluate_drift(
            "role", ["SWE", "DATA"] * 50, ["SWE", "DATA"] * 50, is_categorical=True
        )
        abstentions = evaluate_slice_abstentions(
            "loc", "BLR", total_queries=100, abstained_queries=4
        )
        coverage = evaluate_coverage([25.0] * 82 + [5.0] * 18, [20.0] * 100, [30.0] * 100)

        alerts = alert_manager.process_and_dispatch(
            freshness_reports=[freshness],
            drift_reports=[drift],
            abstention_reports=[abstentions],
            coverage_reports=[coverage],
        )

        assert len(alerts) == 0
        assert len(alert_manager.active_alerts) == 0
