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
from compintel.evaluation.splits import (
    DatasetSplits,
    SplitConfig,
    SplitSummary,
    SplitType,
    TemporalGroupedSplitter,
    create_temporal_grouped_splits,
)

__all__ = [
    "DatasetSplits",
    "LeakageAuditReport",
    "SplitConfig",
    "SplitSummary",
    "SplitType",
    "TemporalGroupedSplitter",
    "audit_split_leakage",
    "create_temporal_grouped_splits",
    "seed_exact_duplicate_leak",
    "seed_group_leak",
    "seed_observation_id_leak",
    "seed_temporal_lookahead_leak",
]
