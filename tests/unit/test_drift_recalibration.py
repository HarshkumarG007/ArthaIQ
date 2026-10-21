"""Unit tests for automated drift triggers, recalibration, and challenger (Task T10.05).

Verifies the Definition of Done requirement:
"Done when: a simulated drift triggers the documented action."
And tests:
1. Multi-tier distribution drift evaluation (PSI, KS distance).
2. Tier 1 trigger (Moderate drift): automated conformal recalibration (Rule R-UQ-03).
3. Tier 2 trigger (Severe drift): challenger shadow evaluation & 5 promotion gates (Rule R-MD-14).
4. Full scheduled drift job execution under nominal, moderate, and severe conditions.
5. Operational alert generation and dispatch via AlertManager.
6. Prometheus telemetry metric updates.
7. Markdown dashboard rendering.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from compintel.monitoring.alerts import AlertManager
from compintel.monitoring.metrics import get_metrics_registry
from compintel.monitoring.recalibration import (
    ChallengerEvaluationResult,
    ConformalRecalibrationResult,
    evaluate_challenger_shadow,
    evaluate_cohort_drift,
    execute_drift_recalibration_job,
    recalibrate_conformal_bounds,
    render_drift_recalibration_markdown,
)


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


class TestDriftEvaluation:
    """Tests for multi-tier drift detection across feature cohorts."""

    def test_evaluate_cohort_drift_stable(self) -> None:
        """Verify identical cohorts yield STABLE tier with near-zero divergence."""
        baseline: dict[str, list[Any]] = {
            "role_family": ["SWE", "DATA", "MLAI"] * 40,
            "yoe_total": [2.0, 5.0, 8.0, 12.0] * 30,
        }
        target: dict[str, list[Any]] = {
            "role_family": ["SWE", "DATA", "MLAI"] * 40,
            "yoe_total": [2.0, 5.0, 8.0, 12.0] * 30,
        }
        reports, trigger_level = evaluate_cohort_drift(baseline, target)
        assert trigger_level == "STABLE"
        assert len(reports) == 2
        for r in reports:
            assert r.status == "STABLE"

    def test_evaluate_cohort_drift_moderate_trigger(self) -> None:
        """Verify moderate shift in role distribution triggers Tier 1 RECALIBRATE."""
        baseline: dict[str, list[Any]] = {
            "role_family": ["SWE"] * 60 + ["DATA"] * 40 + ["MLAI"] * 20,
            "yoe_total": [5.0] * 120,
        }
        # Moderate shift
        target: dict[str, list[Any]] = {
            "role_family": ["SWE"] * 40 + ["DATA"] * 55 + ["MLAI"] * 25,
            "yoe_total": [5.0] * 120,
        }
        reports, trigger_level = evaluate_cohort_drift(baseline, target)
        assert trigger_level == "RECALIBRATE"
        role_rep = next(r for r in reports if r.feature_name == "role_family")
        assert role_rep.status == "MODERATE_DRIFT"
        assert 0.10 <= role_rep.statistic < 0.25

    def test_evaluate_cohort_drift_severe_trigger(self) -> None:
        """Verify severe shift triggers Tier 2 RETRAIN_CHALLENGER."""
        baseline: dict[str, list[Any]] = {
            "role_family": ["SWE"] * 80 + ["DATA"] * 30 + ["MLAI"] * 10,
        }
        # Severe shift: MLAI surge
        target: dict[str, list[Any]] = {
            "role_family": ["SWE"] * 15 + ["DATA"] * 25 + ["MLAI"] * 80,
        }
        reports, trigger_level = evaluate_cohort_drift(baseline, target)
        assert trigger_level == "RETRAIN_CHALLENGER"
        role_rep = next(r for r in reports if r.feature_name == "role_family")
        assert role_rep.status == "SIGNIFICANT_DRIFT"
        assert role_rep.statistic >= 0.25


class TestConformalRecalibration:
    """Tests for automated conformal prediction interval recalibration (Rule R-UQ-03)."""

    def test_recalibrate_restores_nominal_coverage(self) -> None:
        """Verify recomputing q_hat restores empirical coverage to target 80%."""
        rng = np.random.default_rng(123)
        n = 200
        residuals = rng.normal(0, 2.0, size=n)
        y_true = 20.0 + residuals
        y_pred = np.full(n, 20.0)

        # Prior bounds that under-cover (only covering ~45% due to narrow bounds)
        p10_decayed = y_pred - 1.2
        p90_decayed = y_pred + 1.2

        result = recalibrate_conformal_bounds(
            y_true=y_true,
            p10_uncalibrated=p10_decayed,
            p90_uncalibrated=p90_decayed,
            prior_q_hat=0.5,
            nominal_coverage=0.80,
        )

        assert isinstance(result, ConformalRecalibrationResult)
        assert result.recalibration_status == "SUCCESS"
        assert result.updated_conformal_quantile > result.prior_conformal_quantile
        assert result.post_recalibration_coverage >= 0.78
        assert result.post_recalibration_coverage <= 0.85
        assert result.n_calibration_samples == n

    def test_recalibrate_empty_cohort_raises_error(self) -> None:
        """Verify empty realization cohort raises ValueError."""
        with pytest.raises(ValueError, match="Cannot recalibrate on empty realization cohort"):
            recalibrate_conformal_bounds(
                y_true=np.array([]),
                p10_uncalibrated=np.array([]),
                p90_uncalibrated=np.array([]),
            )


class TestChallengerEvaluation:
    """Tests for Challenger model shadow evaluation against 5 promotion gates (Rule R-MD-14)."""

    def test_challenger_promotion_when_passing_all_gates(self) -> None:
        """Verify Challenger is recommended for PROMOTE when strictly outperforming Champion."""
        rng = np.random.default_rng(42)
        n = 200
        residuals = rng.normal(0, 2.0, size=n)
        y_true = 25.0 + residuals
        y_pred = np.full(n, 25.0)

        # Champion: wider intervals (half-width 3.6 -> ~93% coverage)
        champ_p10 = y_pred - 3.6
        champ_p50 = y_pred - 0.2
        champ_p90 = y_pred + 3.6

        # Challenger: tighter calibrated intervals (half-width 2.56 -> ~80% coverage)
        chall_p10 = y_pred - 2.56
        chall_p50 = y_pred
        chall_p90 = y_pred + 2.56

        result = evaluate_challenger_shadow(
            y_true=y_true,
            champ_p10=champ_p10,
            champ_p50=champ_p50,
            champ_p90=champ_p90,
            chall_p10=chall_p10,
            chall_p50=chall_p50,
            chall_p90=chall_p90,
            champion_version="v0.1.0",
            challenger_version="v0.2.0-rc1",
        )

        assert isinstance(result, ChallengerEvaluationResult)
        assert result.promotion_recommendation == "PROMOTE"
        assert result.pinball_improvement_pct > 0.0
        assert result.crossing_rate == 0.0
        assert result.fairness_parity_passed is True

    def test_challenger_keep_champion_when_pinball_worse(self) -> None:
        """Verify Challenger is KEEP_CHAMPION when pinball loss does not improve."""
        n = 50
        y_true = np.linspace(15.0, 35.0, n)
        champ_p10 = y_true - 3.0
        champ_p50 = y_true
        champ_p90 = y_true + 3.0

        # Challenger has worse pinball (shifted median)
        chall_p10 = y_true - 3.0
        chall_p50 = y_true + 2.5
        chall_p90 = y_true + 3.0

        result = evaluate_challenger_shadow(
            y_true=y_true,
            champ_p10=champ_p10,
            champ_p50=champ_p50,
            champ_p90=champ_p90,
            chall_p10=chall_p10,
            chall_p50=chall_p50,
            chall_p90=chall_p90,
        )

        assert result.promotion_recommendation in ["KEEP_CHAMPION", "REJECT"]

    def test_challenger_rejected_on_excessive_crossings(self) -> None:
        """Verify Challenger is rejected if quantile crossing violates Rule R-UQ-05."""
        n = 100
        y_true = np.linspace(10.0, 40.0, n)
        champ_p10 = y_true - 4.0
        champ_p50 = y_true
        champ_p90 = y_true + 4.0

        # Challenger with inverted bounds (crossings)
        chall_p10 = y_true + 1.0  # p10 > p50 violation!
        chall_p50 = y_true
        chall_p90 = y_true + 4.0

        result = evaluate_challenger_shadow(
            y_true=y_true,
            champ_p10=champ_p10,
            champ_p50=champ_p50,
            champ_p90=champ_p90,
            chall_p10=chall_p10,
            chall_p50=chall_p50,
            chall_p90=chall_p90,
        )

        assert result.promotion_recommendation == "REJECT"
        assert result.crossing_rate > 0.05


class TestDriftRecalibrationJob:
    """Full execution tests for scheduled drift and recalibration jobs (verifies DoD)."""

    def test_execute_job_nominal_stable(self, repo_root: Path, alert_manager: AlertManager) -> None:
        """Verify nominal run completes in Tier 0 STABLE with 0 alerts."""
        result = execute_drift_recalibration_job(
            repo_root=repo_root,
            as_of=datetime(2026, 10, 21, 12, 0, tzinfo=UTC),
            induce_drift_feature=None,
            alert_manager=alert_manager,
            sample_size=100,
        )

        assert result.overall_trigger_level == "STABLE"
        assert result.overall_status == "HEALTHY"
        assert result.recalibration_result is None
        assert result.challenger_result is None
        assert len(result.alerts_triggered) == 0
        assert "Nominal Monitoring" in result.action_executed

    def test_simulated_moderate_drift_triggers_recalibration(
        self, repo_root: Path, alert_manager: AlertManager
    ) -> None:
        """Verify DoD: simulated moderate drift triggers automated Conformal Recalibration."""
        result = execute_drift_recalibration_job(
            repo_root=repo_root,
            as_of=datetime(2026, 10, 21, 12, 0, tzinfo=UTC),
            induce_drift_feature="role_family",
            drift_severity="moderate",
            alert_manager=alert_manager,
            sample_size=150,
        )

        # 1. Evaluated Tier is RECALIBRATE
        assert result.overall_trigger_level == "RECALIBRATE"
        assert result.overall_status == "WARNING"

        # 2. Conformal recalibration action was automatically executed
        assert result.recalibration_result is not None
        assert result.recalibration_result.recalibration_status == "SUCCESS"
        assert result.recalibration_result.post_recalibration_coverage >= 0.75
        assert "Automated Conformal Recalibration" in result.action_executed

        # 3. Operational WARNING alert was dispatched
        assert len(result.alerts_triggered) >= 1
        warning_alerts = [a for a in result.alerts_triggered if a["severity"] == "WARNING"]
        assert len(warning_alerts) >= 1
        assert warning_alerts[0]["category"] == "DRIFT"
        assert "Moderate" in warning_alerts[0]["title"]

    def test_simulated_severe_drift_triggers_challenger_retraining(
        self, repo_root: Path, alert_manager: AlertManager
    ) -> None:
        """Verify DoD: simulated severe drift triggers Challenger Shadow Evaluation (Tier 2)."""
        result = execute_drift_recalibration_job(
            repo_root=repo_root,
            as_of=datetime(2026, 10, 21, 12, 0, tzinfo=UTC),
            induce_drift_feature="role_family",
            drift_severity="severe",
            alert_manager=alert_manager,
            sample_size=150,
        )

        # 1. Evaluated Tier is RETRAIN_CHALLENGER
        assert result.overall_trigger_level == "RETRAIN_CHALLENGER"
        assert result.overall_status == "CRITICAL"

        # 2. Challenger shadow evaluation action was automatically executed
        assert result.challenger_result is not None
        assert result.challenger_result.promotion_recommendation == "PROMOTE"
        assert "Challenger Shadow Evaluation" in result.action_executed

        # 3. Operational CRITICAL alert was dispatched
        assert len(result.alerts_triggered) >= 1
        critical_alerts = [a for a in result.alerts_triggered if a["severity"] == "CRITICAL"]
        assert len(critical_alerts) >= 1
        assert critical_alerts[0]["category"] == "DRIFT"
        assert "Critical" in critical_alerts[0]["title"]


class TestTelemetryAndDashboard:
    """Tests for Prometheus metrics and markdown dashboard rendering."""

    def test_prometheus_telemetry_gauges_updated(self, repo_root: Path) -> None:
        """Verify Prometheus telemetry gauges are updated during drift execution."""
        registry = get_metrics_registry()

        execute_drift_recalibration_job(
            repo_root=repo_root,
            induce_drift_feature="role_family",
            drift_severity="moderate",
            update_metrics=True,
            sample_size=100,
        )

        # Tier gauge must be 1.0 (RECALIBRATE)
        assert registry.drift_trigger_tier.value == 1.0

        # Conformal quantile gauge must be non-zero
        quantile_val = registry.conformal_quantile_value.labels(method="CQR").value
        assert quantile_val > 0.0

    def test_render_drift_recalibration_markdown(self, repo_root: Path) -> None:
        """Verify generated markdown dashboard contains required operational sections."""
        result = execute_drift_recalibration_job(
            repo_root=repo_root,
            induce_drift_feature="role_family",
            drift_severity="moderate",
            sample_size=100,
        )

        md = render_drift_recalibration_markdown(result)
        assert "# ArthaIQ Distribution Drift & Recalibration Status" in md
        assert "## 1. Executive Summary" in md
        assert "## 2. Feature Distribution Drift Matrix" in md
        assert "## 3. Conformal Recalibration Execution Audit (Tier 1 Action)" in md
        assert "## 5. Dispatched Operational Alerts" in md
        assert "WARNING" in md
