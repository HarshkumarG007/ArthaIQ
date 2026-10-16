"""CompIntel evaluation package (Tasks T4.01 - T4.09).

Provides:
- Temporal and grouped dataset splitting (Rule R-MD-01, R-MD-02, R-MD-03, R-DA-06).
- Leakage detection and adversarial verification (Rule R-MD-04).
- Standard metrics and bootstrap uncertainty quantification.
- Baselines and benchmark comparison.
"""

from compintel.evaluation.leakage import (
    LeakageAuditReport,
    audit_split_leakage,
    seed_exact_duplicate_leak,
    seed_group_leak,
    seed_observation_id_leak,
    seed_temporal_lookahead_leak,
)
from compintel.evaluation.metrics import (
    CalibrationMetrics,
    ComprehensiveMetricsReport,
    IntervalMetrics,
    MetricWithCI,
    PointMetrics,
    QuantileLossMetrics,
    bootstrap_metric_ci,
    compute_evaluation_report,
    evaluate_calibration_metrics,
    evaluate_interval_metrics,
    evaluate_point_metrics,
    evaluate_quantile_metrics,
    interval_coverage,
    interval_underflow_overflow,
    interval_widths,
    mean_absolute_error,
    mean_absolute_percentage_error,
    median_absolute_error,
    median_absolute_percentage_error,
    pinball_loss,
    pinball_loss_array,
    quantile_calibration_error,
    quantile_crossing,
    root_mean_squared_error,
)
from compintel.evaluation.splits import (
    DatasetSplits,
    SplitConfig,
    SplitSummary,
    SplitType,
    TemporalGroupedSplitter,
    create_temporal_grouped_splits,
)

__all__ = [
    "CalibrationMetrics",
    "ComprehensiveMetricsReport",
    "DatasetSplits",
    "IntervalMetrics",
    "LeakageAuditReport",
    "MetricWithCI",
    "PointMetrics",
    "QuantileLossMetrics",
    "SplitConfig",
    "SplitSummary",
    "SplitType",
    "TemporalGroupedSplitter",
    "audit_split_leakage",
    "bootstrap_metric_ci",
    "compute_evaluation_report",
    "create_temporal_grouped_splits",
    "evaluate_calibration_metrics",
    "evaluate_interval_metrics",
    "evaluate_point_metrics",
    "evaluate_quantile_metrics",
    "interval_coverage",
    "interval_underflow_overflow",
    "interval_widths",
    "mean_absolute_error",
    "mean_absolute_percentage_error",
    "median_absolute_error",
    "median_absolute_percentage_error",
    "pinball_loss",
    "pinball_loss_array",
    "quantile_calibration_error",
    "quantile_crossing",
    "root_mean_squared_error",
    "seed_exact_duplicate_leak",
    "seed_group_leak",
    "seed_observation_id_leak",
    "seed_temporal_lookahead_leak",
]
