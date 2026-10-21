"""Unit tests for online coverage tracking, Wilson confidence intervals, and dashboards (T10.03).

Adheres to:
- PRD Section 11 Metric M-04: Realized conformal coverage [75%, 85%].
- PRD NFR-01 & Rule R-UQ-03: Marginal coverage guarantees with Wilson confidence intervals.
- Rules R-UQ-01, R-UQ-02, R-MD-08: Thin-evidence abstention governance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.run_coverage_tracking import run_coverage_tracking

from compintel.monitoring.alerts import Alert
from compintel.monitoring.coverage import (
    CoverageDashboardData,
    CoverageReport,
    SliceCoverageReport,
    WeeklyCoverageBucket,
    compute_wilson_confidence_interval,
    evaluate_slice_abstentions,
    render_coverage_dashboard_markdown,
)


@pytest.mark.unit
class TestWilsonConfidenceInterval:
    """Tests for compute_wilson_confidence_interval."""

    def test_zero_total_returns_zero(self) -> None:
        low, high = compute_wilson_confidence_interval(0, 0)
        assert low == 0.0
        assert high == 0.0

    def test_negative_total_returns_zero(self) -> None:
        low, high = compute_wilson_confidence_interval(0, -5)
        assert low == 0.0
        assert high == 0.0

    def test_zero_successes_bounded_above_zero(self) -> None:
        low, high = compute_wilson_confidence_interval(0, 100)
        assert low == 0.0
        assert 0.0 < high <= 0.05

    def test_all_successes_bounded_below_one(self) -> None:
        low, high = compute_wilson_confidence_interval(100, 100)
        assert 0.95 <= low < 1.0
        assert high == 1.0

    def test_nominal_eighty_percent_coverage(self) -> None:
        low, high = compute_wilson_confidence_interval(80, 100, confidence=0.95)
        assert low < 0.80 < high
        assert 0.70 <= low <= 0.75
        assert 0.85 <= high <= 0.90

    def test_different_confidence_coefficients(self) -> None:
        low_90, high_90 = compute_wilson_confidence_interval(80, 100, confidence=0.90)
        low_95, high_95 = compute_wilson_confidence_interval(80, 100, confidence=0.95)
        low_99, high_99 = compute_wilson_confidence_interval(80, 100, confidence=0.99)

        # Higher confidence implies wider interval
        assert low_99 <= low_95 <= low_90
        assert high_90 <= high_95 <= high_99


@pytest.mark.unit
class TestCoverageDashboardRendering:
    """Tests for dashboard rendering and serialization."""

    def test_render_empty_alerts_dashboard(self) -> None:
        agg = CoverageReport(
            nominal_coverage=0.80,
            empirical_coverage=0.805,
            n_eval=150,
            coverage_delta=0.0,
            status="HEALTHY",
            description="Coverage healthy: empirical coverage matches nominal.",
        )
        bucket = WeeklyCoverageBucket(
            week_label="2026-W41",
            start_date="2026-10-05",
            end_date="2026-10-11",
            n_observations=50,
            covered_count=40,
            empirical_coverage=0.80,
            ci_lower=0.67,
            ci_upper=0.89,
            nominal_target=0.80,
            status="HEALTHY",
        )
        slice_rep = SliceCoverageReport(
            slice_dimension="role_family",
            slice_value="SWE",
            n_observations=80,
            empirical_coverage=0.8125,
            ci_lower=0.71,
            ci_upper=0.88,
            status="HEALTHY",
        )
        abst_rep = evaluate_slice_abstentions(
            slice_type="role_family",
            slice_value="SWE",
            total_queries=80,
            abstained_queries=0,
        )

        data = CoverageDashboardData(
            as_of_date="2026-10-21",
            active_model_version="0.1.0",
            aggregate_coverage=agg,
            weekly_trend=[bucket],
            slice_breakdown=[slice_rep],
            abstention_summary=[abst_rep],
            target_range=(0.75, 0.85),
            governance_verdict="PASS_GO: Calibrated within pre-registered thresholds.",
        )

        md = render_coverage_dashboard_markdown(data, alerts=[])
        assert "# Realized Conformal Coverage Tracking Dashboard" in md
        assert "2026-W41" in md
        assert "SWE" in md
        assert "PASS_GO" in md
        assert "Zero active operational alerts" in md

    def test_render_with_active_alerts(self) -> None:
        agg = CoverageReport(
            nominal_coverage=0.80,
            empirical_coverage=0.55,
            n_eval=100,
            coverage_delta=0.25,
            status="DEGRADED",
            description="Coverage degraded below critical limit.",
        )
        alert = Alert(
            category="COVERAGE",
            severity="CRITICAL",
            title="Conformal interval coverage severely degraded",
            description="Empirical coverage 55.0% falls 25.0% below nominal 80.0%.",
            metric_name="empirical_coverage_deficit",
            metric_value=0.25,
            threshold=0.10,
        )
        data = CoverageDashboardData(
            as_of_date="2026-10-21",
            active_model_version="0.1.0",
            aggregate_coverage=agg,
            weekly_trend=[],
            slice_breakdown=[],
            abstention_summary=[],
            target_range=(0.75, 0.85),
            governance_verdict="CRITICAL_DEGRADED: Operational coverage threshold breach.",
        )

        md = render_coverage_dashboard_markdown(data, alerts=[alert])
        assert "CRITICAL" in md
        assert "Conformal interval coverage severely degraded" in md


@pytest.mark.unit
class TestOnlineCoverageTrackingRunner:
    """End-to-end integration tests for run_coverage_tracking script."""

    def test_nominal_coverage_tracking_execution(self, tmp_path: Path) -> None:
        out_json = tmp_path / "coverage_report.json"
        out_md = tmp_path / "coverage_dashboard.md"

        data = run_coverage_tracking(
            champion_dir=Path("artifacts/champion_v0"),
            output_json=out_json,
            output_dashboard=out_md,
            allow_synthetic=True,
            target_coverage=0.80,
            coverage_min=0.75,
            coverage_max=0.85,
            induce_fault="none",
            seed=42,
        )

        # Governance assertion
        assert data.governance_verdict.startswith("PASS_GO")
        assert 0.75 <= data.aggregate_coverage.empirical_coverage <= 0.85
        assert data.aggregate_coverage.status == "HEALTHY"
        assert data.aggregate_coverage.n_eval >= 100

        # Weekly buckets assertion
        assert len(data.weekly_trend) == 6
        for bucket in data.weekly_trend:
            assert bucket.n_observations > 0
            assert bucket.ci_lower <= bucket.empirical_coverage <= bucket.ci_upper
            assert bucket.status == "HEALTHY"

        # Artifacts written assertion
        assert out_json.is_file()
        assert out_md.is_file()

        parsed_json = json.loads(out_json.read_text(encoding="utf-8"))
        assert parsed_json["active_model_version"] == "0.1.0"
        assert len(parsed_json["alerts"]) == 0

    def test_fault_injection_undercoverage(self, tmp_path: Path) -> None:
        out_json = tmp_path / "coverage_report_fault.json"
        out_md = tmp_path / "coverage_dashboard_fault.md"

        data = run_coverage_tracking(
            champion_dir=Path("artifacts/champion_v0"),
            output_json=out_json,
            output_dashboard=out_md,
            allow_synthetic=True,
            induce_fault="undercoverage",
            seed=42,
        )

        assert data.governance_verdict.startswith("CRITICAL_DEGRADED")
        assert data.aggregate_coverage.status == "DEGRADED"
        assert data.aggregate_coverage.empirical_coverage < 0.65

        parsed_json = json.loads(out_json.read_text(encoding="utf-8"))
        assert len(parsed_json["alerts"]) >= 1
        assert any(a["severity"] == "CRITICAL" for a in parsed_json["alerts"])

    def test_fault_injection_abstention_spike(self, tmp_path: Path) -> None:
        out_json = tmp_path / "coverage_report_abst.json"
        out_md = tmp_path / "coverage_dashboard_abst.md"

        data = run_coverage_tracking(
            champion_dir=Path("artifacts/champion_v0"),
            output_json=out_json,
            output_dashboard=out_md,
            allow_synthetic=True,
            induce_fault="abstention_spike",
            seed=42,
        )

        assert data.governance_verdict.startswith("CRITICAL_DEGRADED")
        data_slice_abstention = next(a for a in data.abstention_summary if a.slice_value == "DATA")
        assert data_slice_abstention.status in ("ANOMALY", "WARNING")
        assert data_slice_abstention.abstention_rate > 0.30
