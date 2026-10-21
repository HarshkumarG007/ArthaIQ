"""Unit tests for in-memory Prometheus/OpenMetrics telemetry engine (Task T9.11a).

Verifies:
1. Counter semantics (monotonic inc, label partitioning, format validation).
2. Gauge semantics (set, inc, dec, label partitioning).
3. Histogram semantics (bucket distribution, cumulative le counts, sum and count).
4. MetricsRegistry singleton, registration, reset, and exposition output format.
5. Thread-safety under concurrent updates.
6. PII absence and label value escaping.
"""

from __future__ import annotations

import concurrent.futures
import re

import pytest

from compintel.monitoring.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    _escape_label_value,
)


class TestCounter:
    """Tests for Prometheus Counter metric."""

    def test_counter_inc_and_collect(self) -> None:
        c = Counter("test_counter_total", "Test counter help")
        c.inc()
        c.inc(2.5)

        lines = c.collect()
        assert "# HELP test_counter_total Test counter help" in lines
        assert "# TYPE test_counter_total counter" in lines
        assert "test_counter_total 3.5" in lines

    def test_counter_negative_inc_raises(self) -> None:
        c = Counter("test_neg", "Help")
        with pytest.raises(ValueError, match="must be non-negative"):
            c.inc(-1.0)

    def test_counter_with_labels(self) -> None:
        c = Counter("test_labeled", "Help", labelnames=["method", "status"])
        c.labels(method="GET", status="200").inc(1)
        c.labels(method="POST", status="200").inc(3)
        c.labels(method="GET", status="200").inc(2)

        lines = c.collect()
        assert 'test_labeled{method="GET",status="200"} 3.0' in lines
        assert 'test_labeled{method="POST",status="200"} 3.0' in lines

    def test_counter_invalid_labels(self) -> None:
        c = Counter("test_err", "Help", labelnames=["code"])
        with pytest.raises(ValueError, match="expected labels"):
            c.labels(wrong="val")

    def test_counter_reset(self) -> None:
        c = Counter("test_reset", "Help")
        c.inc(5)
        c.reset()
        lines = c.collect()
        assert "test_reset 0.0" in lines


class TestGauge:
    """Tests for Prometheus Gauge metric."""

    def test_gauge_set_inc_dec(self) -> None:
        g = Gauge("test_gauge", "Test gauge help")
        g.set(10.0)
        g.inc(5.0)
        g.dec(2.0)

        lines = g.collect()
        assert "# HELP test_gauge Test gauge help" in lines
        assert "# TYPE test_gauge gauge" in lines
        assert "test_gauge 13.0" in lines

    def test_gauge_with_labels(self) -> None:
        g = Gauge("active_tasks", "Active tasks", labelnames=["queue"])
        g.labels(queue="priority").set(4)
        g.labels(queue="batch").set(12)

        lines = g.collect()
        assert 'active_tasks{queue="batch"} 12.0' in lines
        assert 'active_tasks{queue="priority"} 4.0' in lines


class TestHistogram:
    """Tests for Prometheus Histogram metric."""

    def test_histogram_observation_and_buckets(self) -> None:
        buckets = (1.0, 5.0, 10.0)
        h = Histogram("test_hist_seconds", "Help", buckets=buckets)

        h.observe(0.5)
        h.observe(2.0)
        h.observe(7.5)
        h.observe(15.0)

        lines = h.collect()
        assert "# HELP test_hist_seconds Help" in lines
        assert "# TYPE test_hist_seconds histogram" in lines
        # <= 1.0: 1 (0.5)
        assert 'test_hist_seconds_bucket{le="1.0"} 1' in lines
        # <= 5.0: 2 (0.5, 2.0)
        assert 'test_hist_seconds_bucket{le="5.0"} 2' in lines
        # <= 10.0: 3 (0.5, 2.0, 7.5)
        assert 'test_hist_seconds_bucket{le="10.0"} 3' in lines
        # +Inf: 4 total
        assert 'test_hist_seconds_bucket{le="+Inf"} 4' in lines
        assert "test_hist_seconds_sum 25.0" in lines
        assert "test_hist_seconds_count 4" in lines

    def test_histogram_with_labels(self) -> None:
        h = Histogram("req_dur", "Help", labelnames=["endpoint"], buckets=(0.1, 1.0))
        h.labels(endpoint="/api").observe(0.05)
        h.labels(endpoint="/api").observe(0.5)

        lines = h.collect()
        assert 'req_dur_bucket{endpoint="/api",le="0.1"} 1' in lines
        assert 'req_dur_bucket{endpoint="/api",le="1.0"} 2' in lines
        assert 'req_dur_bucket{endpoint="/api",le="+Inf"} 2' in lines
        assert 'req_dur_count{endpoint="/api"} 2' in lines


class TestMetricsRegistry:
    """Tests for central Prometheus MetricsRegistry."""

    def test_default_operational_metrics_registered(self) -> None:
        reg = MetricsRegistry()
        assert reg.http_requests_total is not None
        assert reg.http_request_duration_seconds is not None
        assert reg.active_requests is not None
        assert reg.estimates_total is not None
        assert reg.abstentions_total is not None
        assert reg.estimate_confidence_width_lpa is not None

    def test_generate_latest_output(self) -> None:
        reg = MetricsRegistry()
        reg.http_requests_total.labels(method="GET", path="/v1/estimates", status="200").inc(4)
        reg.estimates_total.labels(status="supported").inc(3)
        reg.estimates_total.labels(status="abstained").inc(1)
        reg.abstentions_total.labels(
            reason="THIN_COHORT_EVIDENCE",
            role_family="Data Science",
            location="BLR",
        ).inc(1)

        output = reg.generate_latest()
        assert "# HELP http_requests_total" in output
        assert "# TYPE http_requests_total counter" in output
        assert 'http_requests_total{method="GET",path="/v1/estimates",status="200"} 4.0' in output
        assert 'arthaiq_estimates_total{status="supported"} 3.0' in output
        assert 'arthaiq_estimates_total{status="abstained"} 1.0' in output
        assert (
            'arthaiq_abstentions_total{location="BLR",'
            'reason="THIN_COHORT_EVIDENCE",role_family="Data Science"} 1.0' in output
        )

    def test_thread_safety(self) -> None:
        reg = MetricsRegistry()
        num_threads = 8
        increments_per_thread = 500

        def worker() -> None:
            for _ in range(increments_per_thread):
                counter = reg.http_requests_total.labels(
                    method="POST", path="/v1/estimates", status="200"
                )
                counter.inc(1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        output = reg.generate_latest()
        expected_total = float(num_threads * increments_per_thread)
        expected_metric = (
            f'http_requests_total{{method="POST",path="/v1/estimates",status="200"}} '
            f"{expected_total}"
        )
        assert expected_metric in output

    def test_reset_all(self) -> None:
        reg = MetricsRegistry()
        reg.estimates_total.labels(status="supported").inc(10)
        reg.reset_all()
        output = reg.generate_latest()
        assert 'arthaiq_estimates_total{status="supported"}' not in output

    def test_label_value_escaping(self) -> None:
        escaped = _escape_label_value('line1\nline2 "quoted" and \\backslash\\')
        assert escaped == 'line1\\nline2 \\"quoted\\" and \\\\backslash\\\\'

    def test_no_pii_patterns_in_metrics(self) -> None:
        reg = MetricsRegistry()
        reg.estimates_total.labels(status="supported").inc(1)
        reg.abstentions_total.labels(
            reason="THIN_COHORT_EVIDENCE",
            role_family="Software Engineer",
            location="BLR",
        ).inc(1)

        output = reg.generate_latest()

        # Audit against common PII formats
        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        pan_pattern = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
        phone_pattern = re.compile(r"\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b")

        assert not email_pattern.search(output)
        assert not pan_pattern.search(output)
        assert not phone_pattern.search(output)
