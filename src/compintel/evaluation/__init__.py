"""CompIntel evaluation package (Tasks T4.01 - T4.09).

Provides:
- Temporal and grouped dataset splitting (Rule R-MD-01, R-MD-02, R-MD-03, R-DA-06).
- Leakage detection and adversarial verification.
- Standard metrics and bootstrap uncertainty quantification.
- Baselines and benchmark comparison.
"""

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
    "SplitConfig",
    "SplitSummary",
    "SplitType",
    "TemporalGroupedSplitter",
    "create_temporal_grouped_splits",
]
