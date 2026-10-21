"""Zero-dependency, thread-safe Prometheus/OpenMetrics telemetry engine (NFR-07, PRD FR-13).

Provides in-memory Counter, Gauge, and Histogram metrics with standard
Prometheus text exposition format (v0.0.4). Adheres to:
- Rule R-CD-06 / R-DA-07: Telemetry never records PII or raw free-text inputs.
- Rule R-CD-08: Lightweight implementation without external third-party binary dependencies.
- Rule R-CD-07: Consistent snake_case metric and label naming.
"""

from __future__ import annotations

import math
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_HISTOGRAM_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    10.0,
)

WIDTH_HISTOGRAM_BUCKETS: tuple[float, ...] = (
    2.0,
    5.0,
    8.0,
    10.0,
    15.0,
    20.0,
    25.0,
    30.0,
    40.0,
    50.0,
    75.0,
    100.0,
)


def _escape_label_value(value: str) -> str:
    """Escape label values according to Prometheus text format specification."""
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_labels(labels: dict[str, str]) -> str:
    """Format dictionary of labels into Prometheus syntax `{key="val",...}`."""
    if not labels:
        return ""
    formatted = [f'{key}="{_escape_label_value(labels[key])}"' for key in sorted(labels.keys())]
    return "{" + ",".join(formatted) + "}"


class CounterChild:
    """Child instance of a Counter for a specific label combination."""

    def __init__(self, lock: threading.RLock) -> None:
        self._value: float = 0.0
        self._lock = lock

    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter by a non-negative amount."""
        if amount < 0:
            raise ValueError(f"Counter increment amount must be non-negative: {amount}")
        with self._lock:
            self._value += amount

    @property
    def value(self) -> float:
        """Get current counter value."""
        with self._lock:
            return self._value


class Counter:
    """Prometheus Counter metric: monotonically increasing cumulative counter."""

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = (),
    ) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = tuple(labelnames)
        self._lock = threading.RLock()
        self._children: dict[tuple[tuple[str, str], ...], CounterChild] = {}

        self._default_child: CounterChild | None = None
        if not self.labelnames:
            self._default_child = CounterChild(self._lock)

    def labels(self, **kwargs: str) -> CounterChild:
        """Get or create child counter for given label values."""
        if not self.labelnames:
            raise ValueError(f"Metric {self.name} has no label dimensions defined.")
        if set(kwargs.keys()) != set(self.labelnames):
            raise ValueError(
                f"Metric {self.name} expected labels {self.labelnames}, got {tuple(kwargs.keys())}"
            )
        label_key = tuple(sorted((k, str(kwargs[k])) for k in kwargs))
        with self._lock:
            if label_key not in self._children:
                self._children[label_key] = CounterChild(self._lock)
            return self._children[label_key]

    def inc(self, amount: float = 1.0) -> None:
        """Increment counter without labels."""
        if self._default_child is None:
            raise ValueError(f"Metric {self.name} requires label values.")
        self._default_child.inc(amount)

    def collect(self) -> list[str]:
        """Format metric into Prometheus text format lines."""
        lines = [
            f"# HELP {self.name} {self.documentation}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            if self._default_child is not None:
                lines.append(f"{self.name} {self._default_child.value}")
            for label_key, child in sorted(self._children.items()):
                label_dict = dict(label_key)
                labels_str = _format_labels(label_dict)
                lines.append(f"{self.name}{labels_str} {child.value}")
        return lines

    def reset(self) -> None:
        """Reset all counters (for testing isolation)."""
        with self._lock:
            self._children.clear()
            if self._default_child is not None:
                self._default_child = CounterChild(self._lock)


class GaugeChild:
    """Child instance of a Gauge for a specific label combination."""

    def __init__(self, lock: threading.RLock) -> None:
        self._value: float = 0.0
        self._lock = lock

    def set(self, value: float) -> None:
        """Set gauge to an arbitrary float value."""
        with self._lock:
            self._value = float(value)

    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge by amount."""
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge by amount."""
        with self._lock:
            self._value -= amount

    @property
    def value(self) -> float:
        """Get current gauge value."""
        with self._lock:
            return self._value


class Gauge:
    """Prometheus Gauge metric: numerical value that can arbitrarily go up or down."""

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = (),
    ) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = tuple(labelnames)
        self._lock = threading.RLock()
        self._children: dict[tuple[tuple[str, str], ...], GaugeChild] = {}

        self._default_child: GaugeChild | None = None
        if not self.labelnames:
            self._default_child = GaugeChild(self._lock)

    def labels(self, **kwargs: str) -> GaugeChild:
        """Get or create child gauge for given label values."""
        if not self.labelnames:
            raise ValueError(f"Metric {self.name} has no label dimensions defined.")
        if set(kwargs.keys()) != set(self.labelnames):
            raise ValueError(
                f"Metric {self.name} expected labels {self.labelnames}, got {tuple(kwargs.keys())}"
            )
        label_key = tuple(sorted((k, str(kwargs[k])) for k in kwargs))
        with self._lock:
            if label_key not in self._children:
                self._children[label_key] = GaugeChild(self._lock)
            return self._children[label_key]

    def set(self, value: float) -> None:
        """Set gauge without labels."""
        if self._default_child is None:
            raise ValueError(f"Metric {self.name} requires label values.")
        self._default_child.set(value)

    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge without labels."""
        if self._default_child is None:
            raise ValueError(f"Metric {self.name} requires label values.")
        self._default_child.inc(amount)

    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge without labels."""
        if self._default_child is None:
            raise ValueError(f"Metric {self.name} requires label values.")
        self._default_child.dec(amount)

    def collect(self) -> list[str]:
        """Format metric into Prometheus text format lines."""
        lines = [
            f"# HELP {self.name} {self.documentation}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            if self._default_child is not None:
                lines.append(f"{self.name} {self._default_child.value}")
            for label_key, child in sorted(self._children.items()):
                label_dict = dict(label_key)
                labels_str = _format_labels(label_dict)
                lines.append(f"{self.name}{labels_str} {child.value}")
        return lines

    def reset(self) -> None:
        """Reset all gauges (for testing isolation)."""
        with self._lock:
            self._children.clear()
            if self._default_child is not None:
                self._default_child = GaugeChild(self._lock)


class HistogramChild:
    """Child instance of a Histogram for a specific label combination."""

    def __init__(self, buckets: tuple[float, ...], lock: threading.RLock) -> None:
        self._buckets = buckets
        self._counts: list[int] = [0] * len(buckets)
        self._inf_count: int = 0
        self._sum: float = 0.0
        self._lock = lock

    def observe(self, amount: float) -> None:
        """Observe a single value."""
        with self._lock:
            self._sum += amount
            self._inf_count += 1
            for i, boundary in enumerate(self._buckets):
                if amount <= boundary:
                    self._counts[i] += 1

    def snapshot(self) -> tuple[tuple[float, int], ...]:
        """Return cumulative bucket counts."""
        with self._lock:
            cumulative = []
            for b, c in zip(self._buckets, self._counts, strict=True):
                cumulative.append((b, c))
            cumulative.append((float("inf"), self._inf_count))
            return tuple(cumulative)

    @property
    def sum(self) -> float:
        """Sum of all observed values."""
        with self._lock:
            return self._sum

    @property
    def count(self) -> int:
        """Total count of observations."""
        with self._lock:
            return self._inf_count


class Histogram:
    """Prometheus Histogram metric: samples observations and counts them in buckets."""

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = (),
        buckets: Sequence[float] = DEFAULT_HISTOGRAM_BUCKETS,
    ) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = tuple(labelnames)
        self.buckets = tuple(sorted(buckets))
        self._lock = threading.RLock()
        self._children: dict[tuple[tuple[str, str], ...], HistogramChild] = {}

        self._default_child: HistogramChild | None = None
        if not self.labelnames:
            self._default_child = HistogramChild(self.buckets, self._lock)

    def labels(self, **kwargs: str) -> HistogramChild:
        """Get or create child histogram for given label values."""
        if not self.labelnames:
            raise ValueError(f"Metric {self.name} has no label dimensions defined.")
        if set(kwargs.keys()) != set(self.labelnames):
            raise ValueError(
                f"Metric {self.name} expected labels {self.labelnames}, got {tuple(kwargs.keys())}"
            )
        label_key = tuple(sorted((k, str(kwargs[k])) for k in kwargs))
        with self._lock:
            if label_key not in self._children:
                self._children[label_key] = HistogramChild(self.buckets, self._lock)
            return self._children[label_key]

    def observe(self, amount: float) -> None:
        """Observe value without labels."""
        if self._default_child is None:
            raise ValueError(f"Metric {self.name} requires label values.")
        self._default_child.observe(amount)

    def collect(self) -> list[str]:
        """Format metric into Prometheus text format lines."""
        lines = [
            f"# HELP {self.name} {self.documentation}",
            f"# TYPE {self.name} histogram",
        ]

        def _format_child(child: HistogramChild, base_labels: dict[str, str]) -> list[str]:
            child_lines: list[str] = []
            for upper_bound, count in child.snapshot():
                le_val = "+Inf" if math.isinf(upper_bound) else str(upper_bound)
                bucket_labels = dict(base_labels)
                bucket_labels["le"] = le_val
                child_lines.append(f"{self.name}_bucket{_format_labels(bucket_labels)} {count}")
            child_lines.append(f"{self.name}_sum{_format_labels(base_labels)} {child.sum}")
            child_lines.append(f"{self.name}_count{_format_labels(base_labels)} {child.count}")
            return child_lines

        with self._lock:
            if self._default_child is not None:
                lines.extend(_format_child(self._default_child, {}))
            for label_key, child in sorted(self._children.items()):
                label_dict = dict(label_key)
                lines.extend(_format_child(child, label_dict))

        return lines

    def reset(self) -> None:
        """Reset all histogram buckets (for testing isolation)."""
        with self._lock:
            self._children.clear()
            if self._default_child is not None:
                self._default_child = HistogramChild(self.buckets, self._lock)


class MetricsRegistry:
    """Central Prometheus metrics registry managing all active operational collectors."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._metrics: dict[str, Counter | Gauge | Histogram] = {}

        # ---------------------------------------------------------------------
        # Pre-registered Standard Operational Metrics (NFR-07, PRD FR-13)
        # ---------------------------------------------------------------------
        self.http_requests_total = self.register_counter(
            name="http_requests_total",
            documentation="Total incoming HTTP requests partitioned by method, path, status.",
            labelnames=["method", "path", "status"],
        )

        self.http_request_duration_seconds = self.register_histogram(
            name="http_request_duration_seconds",
            documentation="HTTP request latency in seconds partitioned by method and path.",
            labelnames=["method", "path"],
            buckets=DEFAULT_HISTOGRAM_BUCKETS,
        )

        self.active_requests = self.register_gauge(
            name="http_active_requests",
            documentation="Number of currently in-flight HTTP requests.",
            labelnames=["method"],
        )

        self.estimates_total = self.register_counter(
            name="arthaiq_estimates_total",
            documentation="Total estimation requests by outcome status.",
            labelnames=["status"],
        )

        self.abstentions_total = self.register_counter(
            name="arthaiq_abstentions_total",
            documentation="Total abstained queries partitioned by reason code and macro slice.",
            labelnames=["reason", "role_family", "location"],
        )

        self.estimate_confidence_width_lpa = self.register_histogram(
            name="arthaiq_estimate_confidence_width_lpa",
            documentation="Conformal prediction interval width in LPA by evidence grade.",
            labelnames=["evidence_grade"],
            buckets=WIDTH_HISTOGRAM_BUCKETS,
        )

    def register_counter(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = (),
    ) -> Counter:
        """Register and return a new Counter metric."""
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if not isinstance(metric, Counter):
                    raise TypeError(f"Metric {name} is already registered as {type(metric)}")
                return metric
            counter = Counter(name, documentation, labelnames)
            self._metrics[name] = counter
            return counter

    def register_gauge(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = (),
    ) -> Gauge:
        """Register and return a new Gauge metric."""
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if not isinstance(metric, Gauge):
                    raise TypeError(f"Metric {name} is already registered as {type(metric)}")
                return metric
            gauge = Gauge(name, documentation, labelnames)
            self._metrics[name] = gauge
            return gauge

    def register_histogram(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = (),
        buckets: Sequence[float] = DEFAULT_HISTOGRAM_BUCKETS,
    ) -> Histogram:
        """Register and return a new Histogram metric."""
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if not isinstance(metric, Histogram):
                    raise TypeError(f"Metric {name} is already registered as {type(metric)}")
                return metric
            histogram = Histogram(name, documentation, labelnames, buckets)
            self._metrics[name] = histogram
            return histogram

    def generate_latest(self) -> str:
        """Generate Prometheus exposition format representation (v0.0.4)."""
        output_lines: list[str] = []
        with self._lock:
            for metric in self._metrics.values():
                output_lines.extend(metric.collect())
        return "\n".join(output_lines) + "\n"

    def reset_all(self) -> None:
        """Reset all registered metrics to zero (for test isolation)."""
        with self._lock:
            for metric in self._metrics.values():
                metric.reset()


# Global Singleton Registry
_REGISTRY_LOCK = threading.RLock()
_GLOBAL_REGISTRY: MetricsRegistry | None = None


def get_metrics_registry() -> MetricsRegistry:
    """Obtain or initialize the global operational MetricsRegistry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _GLOBAL_REGISTRY is None:
                _GLOBAL_REGISTRY = MetricsRegistry()
    return _GLOBAL_REGISTRY
