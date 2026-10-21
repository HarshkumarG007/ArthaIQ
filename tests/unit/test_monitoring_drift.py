"""Unit tests for drift, freshness, and coverage monitoring engines (Task T9.11b).

Verifies:
1. Population Stability Index (PSI) computation for categorical and continuous data.
2. Kolmogorov-Smirnov (KS) two-sample drift evaluation.
3. Source observation freshness evaluation against SLAs.
4. Conformal coverage and slice-level abstention evaluation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from compintel.monitoring.coverage import (
    evaluate_coverage,
    evaluate_slice_abstentions,
)
from compintel.monitoring.drift import (
    compute_ks,
    compute_psi,
    evaluate_drift,
)
from compintel.monitoring.freshness import (
    evaluate_freshness,
)


class TestDriftComputation:
    """Tests for PSI and KS drift evaluation algorithms."""

    def test_psi_identical_categorical_is_zero(self) -> None:
        base = ["SWE", "DATA", "MLAI"] * 100
        target = ["SWE", "DATA", "MLAI"] * 100
        psi = compute_psi(base, target, is_categorical=True)
        assert psi == 0.0 or psi < 0.001

    def test_psi_significant_categorical_shift(self) -> None:
        base = ["SWE"] * 80 + ["DATA"] * 20
        # Heavily shifted distribution
        target = ["SWE"] * 10 + ["DATA"] * 90
        psi = compute_psi(base, target, is_categorical=True)
        assert psi >= 0.25

    def test_psi_empty_inputs_safe(self) -> None:
        assert compute_psi([], [], is_categorical=True) == 0.0
        assert compute_psi([], [], is_categorical=False) == 0.0

    def test_ks_continuous_identical_distributions(self) -> None:
        base = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0] * 10
        target = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0] * 10
        stat, pval = compute_ks(base, target)
        assert stat == 0.0
        assert pval == 1.0

    def test_ks_continuous_shifted_distributions(self) -> None:
        base = [1.0, 2.0, 3.0, 4.0, 5.0] * 20
        # Clearly shifted values
        target = [10.0, 11.0, 12.0, 13.0, 14.0] * 20
        stat, pval = compute_ks(base, target)
        assert stat == 1.0
        assert pval < 0.001

    def test_evaluate_drift_categorical_stable(self) -> None:
        base = ["BLR", "HYD", "PUN"] * 50
        target = ["BLR", "HYD", "PUN"] * 50
        report = evaluate_drift("location", base, target, is_categorical=True)
        assert report.status == "STABLE"
        assert report.method == "PSI"
        assert report.statistic < 0.10

    def test_evaluate_drift_continuous_critical(self) -> None:
        base = [float(x) for x in range(1, 100)]
        target = [float(x + 50) for x in range(1, 100)]
        report = evaluate_drift("experience_years", base, target, is_categorical=False)
        assert report.status == "SIGNIFICANT_DRIFT"
        assert report.method == "KS"
        assert report.statistic >= 0.12


class TestFreshnessEvaluation:
    """Tests for source freshness monitoring and staleness evaluation."""

    def test_fresh_source(self) -> None:
        now = datetime(2026, 10, 21, tzinfo=UTC)
        latest = now - timedelta(days=60)
        report = evaluate_freshness("SRC-AMB-01", latest_date=latest, sla_days=365.0, as_of=now)
        assert report.status == "FRESH"
        assert report.age_days == 60.0

    def test_warning_source(self) -> None:
        now = datetime(2026, 10, 21, tzinfo=UTC)
        # 300 days old (between 273.75 and 365)
        latest = now - timedelta(days=300)
        report = evaluate_freshness("SRC-EPFO-01", latest_date=latest, sla_days=365.0, as_of=now)
        assert report.status == "WARNING"
        assert report.age_days == 300.0

    def test_stale_source(self) -> None:
        now = datetime(2026, 10, 21, tzinfo=UTC)
        # 400 days old (exceeds 365 days SLA)
        latest = now - timedelta(days=400)
        report = evaluate_freshness("SRC-NASSCOM-01", latest_date=latest, sla_days=365.0, as_of=now)
        assert report.status == "STALE"
        assert report.age_days == 400.0


class TestCoverageEvaluation:
    """Tests for conformal coverage and slice abstention evaluation."""

    def test_healthy_conformal_coverage(self) -> None:
        # 85 out of 100 within [p10, p90]
        y_true = [25.0] * 85 + [10.0] * 15
        p10 = [20.0] * 100
        p90 = [30.0] * 100
        report = evaluate_coverage(y_true, p10, p90, nominal_coverage=0.80)
        assert report.status == "HEALTHY"
        assert report.empirical_coverage == 0.85
        assert report.n_eval == 100

    def test_degraded_conformal_coverage(self) -> None:
        # Only 60 out of 100 covered -> 20% deficit
        y_true = [25.0] * 60 + [5.0] * 40
        p10 = [20.0] * 100
        p90 = [30.0] * 100
        report = evaluate_coverage(y_true, p10, p90, nominal_coverage=0.80)
        assert report.status == "DEGRADED"
        assert report.empirical_coverage == 0.60
        assert report.coverage_delta == 0.20

    def test_slice_abstention_anomaly(self) -> None:
        report = evaluate_slice_abstentions(
            slice_type="location",
            slice_value="HYD",
            total_queries=50,
            abstained_queries=30,  # 60% abstention rate
            critical_rate=0.50,
        )
        assert report.status == "ANOMALY"
        assert report.abstention_rate == 0.60

    def test_slice_abstention_normal(self) -> None:
        report = evaluate_slice_abstentions(
            slice_type="role_family",
            slice_value="SWE",
            total_queries=100,
            abstained_queries=5,  # 5% abstention rate
        )
        assert report.status == "NORMAL"
        assert report.abstention_rate == 0.05
