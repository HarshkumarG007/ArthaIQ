"""Unit tests for scheduled data refresh jobs and source freshness SLA monitoring (Task T10.04).

Verifies the Definition of Done requirement:
"Done when: a stale source raises an alert."
And tests:
1. Loading and parsing source freshness SLAs from YAML and default registry.
2. Raw manifest inspection and timestamp extraction.
3. Execution of scheduled data refresh job on nominal sources.
4. Alert generation and dispatch via AlertManager when a source is stale (CRITICAL alert).
5. Alert generation when a source approaches staleness (WARNING alert).
6. Prometheus telemetry metrics updating and exposition.
7. Markdown dashboard rendering.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from compintel.monitoring.alerts import AlertManager
from compintel.monitoring.freshness import (
    DEFAULT_SOURCE_SLAS,
    execute_data_refresh_job,
    inspect_source_observation_dates,
    load_source_freshness_slas,
    render_data_refresh_markdown,
)
from compintel.monitoring.metrics import MetricsRegistry, get_metrics_registry


@pytest.fixture
def repo_root() -> Path:
    """Fixture pointing to repository root."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def alert_manager() -> AlertManager:
    """Fixture providing isolated AlertManager instance."""
    mgr = AlertManager()
    mgr.clear()
    return mgr


class TestSourceFreshnessSLAs:
    """Tests for SLA registry and configuration parsing."""

    def test_default_slas_contain_all_approved_sources(self) -> None:
        """Verify all core approved sources have calibrated SLAs."""
        expected_sources = [
            "SRC-INT-VOL-01",
            "SRC-SUP-MAC-01",
            "SRC-IND-OFF-03",
            "SRC-USA-DOL-01",
            "SRC-USA-DOL-02",
            "SRC-SUP-CORP-01",
            "SRC-IND-OFF-01",
            "SRC-USA-BLS-01",
            "SRC-KAG-SO-01",
            "SRC-KAG-SO-02",
            "SRC-KAG-AIJ-01",
            "SRC-KAG-AIJ-02",
            "SRC-SUP-TAX-01",
            "SRC-SUP-TAX-02",
        ]
        for sid in expected_sources:
            assert sid in DEFAULT_SOURCE_SLAS
            sla = DEFAULT_SOURCE_SLAS[sid]
            assert sla.sla_days > 0.0
            assert sla.refresh_cadence in ["daily", "monthly", "quarterly", "annual"]

    def test_load_source_freshness_slas_from_repo_config(self, repo_root: Path) -> None:
        """Verify loading from config/freshness_slas.yaml."""
        cfg_path = repo_root / "config" / "freshness_slas.yaml"
        assert cfg_path.exists()

        slas = load_source_freshness_slas(cfg_path)
        assert len(slas) >= 14
        assert slas["SRC-INT-VOL-01"].sla_days == 30.0
        assert slas["SRC-SUP-MAC-01"].sla_days == 45.0
        assert slas["SRC-IND-OFF-03"].sla_days == 60.0
        assert slas["SRC-IND-OFF-01"].sla_days == 365.0

    def test_load_source_freshness_slas_fallback_on_missing_file(self) -> None:
        """Verify fallback to defaults when config path does not exist."""
        slas = load_source_freshness_slas(Path("/nonexistent/slas.yaml"))
        assert len(slas) == len(DEFAULT_SOURCE_SLAS)
        assert "SRC-INT-VOL-01" in slas


class TestManifestInspection:
    """Tests for manifest inspection and timestamp extraction."""

    def test_inspect_source_observation_dates(self, repo_root: Path) -> None:
        """Verify reading generated_at_utc timestamps from data/raw/*/manifest.yaml."""
        dates = inspect_source_observation_dates(repo_root)
        assert len(dates) > 0
        assert "SRC-INT-VOL-01" in dates
        assert "SRC-IND-OFF-01" in dates
        # All timestamps must be timezone-aware UTC
        for _sid, dt in dates.items():
            assert dt.tzinfo is not None
            assert dt.year >= 2024


class TestDataRefreshExecution:
    """Tests for scheduled data refresh execution and alert triggers."""

    def test_execute_data_refresh_job_nominal(
        self,
        repo_root: Path,
        alert_manager: AlertManager,
    ) -> None:
        """Nominal run on current manifests produces HEALTHY verdict and zero alerts."""
        as_of = datetime(2026, 10, 21, tzinfo=UTC)
        result = execute_data_refresh_job(
            repo_root=repo_root,
            as_of=as_of,
            alert_manager=alert_manager,
            update_metrics=True,
        )

        assert result.overall_status == "HEALTHY"
        assert result.stale_count == 0
        assert result.warning_count == 0
        assert result.fresh_count == result.total_sources_evaluated
        assert len(result.alerts_triggered) == 0
        assert len(alert_manager.active_alerts) == 0

    def test_stale_source_raises_critical_alert(
        self,
        repo_root: Path,
        alert_manager: AlertManager,
    ) -> None:
        """DONE WHEN: A stale source raises an alert (Task T10.04 DoD)."""
        as_of = datetime(2026, 10, 21, tzinfo=UTC)
        # Induce staleness on SRC-INT-VOL-01 (SLA: 30 days) by simulating an age of 45 days
        result = execute_data_refresh_job(
            repo_root=repo_root,
            as_of=as_of,
            induce_staleness={"SRC-INT-VOL-01": 45.0},
            alert_manager=alert_manager,
            update_metrics=True,
        )

        assert result.overall_status == "CRITICAL"
        assert result.stale_count == 1
        assert len(result.alerts_triggered) == 1

        alert = result.alerts_triggered[0]
        assert alert["category"] == "FRESHNESS"
        assert alert["severity"] == "CRITICAL"
        assert alert["metric_name"] == "SRC-INT-VOL-01_age_days"
        assert alert["metric_value"] == 45.0
        assert alert["threshold"] == 30.0
        assert "SRC-INT-VOL-01 is stale" in alert["title"]

        # Alert manager must have recorded the critical alert
        assert len(alert_manager.active_alerts) == 1
        active = alert_manager.active_alerts[0]
        assert active.severity == "CRITICAL"
        assert active.metric_name == "SRC-INT-VOL-01_age_days"

    def test_warning_source_raises_warning_alert(
        self,
        repo_root: Path,
        alert_manager: AlertManager,
    ) -> None:
        """Approaching staleness (between 75% and 100% of SLA) raises a WARNING alert."""
        as_of = datetime(2026, 10, 21, tzinfo=UTC)
        # SRC-SUP-MAC-01 has 45-day SLA; 75% warning threshold is 33.75 days.
        # Simulate 38.0 days (in warning zone).
        result = execute_data_refresh_job(
            repo_root=repo_root,
            as_of=as_of,
            induce_staleness={"SRC-SUP-MAC-01": 38.0},
            alert_manager=alert_manager,
            update_metrics=False,
        )

        assert result.overall_status == "WARNING"
        assert result.warning_count == 1
        assert result.stale_count == 0
        assert len(result.alerts_triggered) == 1

        alert = result.alerts_triggered[0]
        assert alert["category"] == "FRESHNESS"
        assert alert["severity"] == "WARNING"
        assert alert["metric_name"] == "SRC-SUP-MAC-01_age_days"
        assert alert["metric_value"] == 38.0
        assert "approaching staleness" in alert["title"]

    def test_multiple_faults_prioritize_critical_verdict(
        self,
        repo_root: Path,
        alert_manager: AlertManager,
    ) -> None:
        """System verdict is CRITICAL when both warning and stale sources exist."""
        as_of = datetime(2026, 10, 21, tzinfo=UTC)
        result = execute_data_refresh_job(
            repo_root=repo_root,
            as_of=as_of,
            induce_staleness={
                "SRC-SUP-MAC-01": 38.0,  # Warning (SLA 45d, 75% = 33.75d)
                "SRC-INT-VOL-01": 50.0,  # Stale (SLA 30d)
                "SRC-IND-OFF-01": 400.0,  # Stale (SLA 365d)
            },
            alert_manager=alert_manager,
            update_metrics=False,
        )

        assert result.overall_status == "CRITICAL"
        assert result.stale_count == 2
        assert result.warning_count == 1
        assert len(result.alerts_triggered) == 3


class TestMarkdownDashboardAndMetrics:
    """Tests for markdown status rendering and Prometheus telemetry integration."""

    def test_render_data_refresh_markdown_healthy(
        self,
        repo_root: Path,
        alert_manager: AlertManager,
    ) -> None:
        """Markdown dashboard includes status badges, table, and protocol."""
        as_of = datetime(2026, 10, 21, tzinfo=UTC)
        result = execute_data_refresh_job(
            repo_root=repo_root,
            as_of=as_of,
            alert_manager=alert_manager,
            update_metrics=False,
        )
        md = render_data_refresh_markdown(result)
        assert "# ArthaIQ Data Freshness & Scheduled Refresh Status" in md
        assert "🟢 PASS / HEALTHY" in md
        assert "SRC-INT-VOL-01" in md
        assert "SRC-IND-OFF-01" in md
        assert "No active freshness alerts" in md

    def test_render_data_refresh_markdown_with_alerts(
        self,
        repo_root: Path,
        alert_manager: AlertManager,
    ) -> None:
        """Markdown dashboard properly formats critical alert table."""
        as_of = datetime(2026, 10, 21, tzinfo=UTC)
        result = execute_data_refresh_job(
            repo_root=repo_root,
            as_of=as_of,
            induce_staleness={"SRC-INT-VOL-01": 40.0},
            alert_manager=alert_manager,
            update_metrics=False,
        )
        md = render_data_refresh_markdown(result)
        assert "🔴 CRITICAL" in md
        assert "SRC-INT-VOL-01_age_days" in md
        assert "Source SRC-INT-VOL-01 is stale" in md

    def test_prometheus_metrics_updated_correctly(
        self,
        repo_root: Path,
        alert_manager: AlertManager,
    ) -> None:
        """Verify that Prometheus registry receives gauges for staleness days and SLAs."""
        MetricsRegistry()
        as_of = datetime(2026, 10, 21, tzinfo=UTC)

        execute_data_refresh_job(
            repo_root=repo_root,
            as_of=as_of,
            induce_staleness={"SRC-INT-VOL-01": 50.0},
            alert_manager=alert_manager,
            update_metrics=True,
        )

        metrics = get_metrics_registry()
        exposition = metrics.generate_latest()

        assert "arthaiq_source_staleness_days" in exposition
        assert "arthaiq_source_freshness_sla_days" in exposition
        assert 'arthaiq_source_staleness_days{source_id="SRC-INT-VOL-01"} 50.0' in exposition
        assert 'arthaiq_source_freshness_sla_days{source_id="SRC-INT-VOL-01"} 30.0' in exposition
        assert "arthaiq_data_refresh_stale_sources_total 1.0" in exposition
