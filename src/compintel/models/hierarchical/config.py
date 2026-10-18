"""Configuration dataclass for Rung C hierarchical partial pooling model (Phase 6, T6.02a).

Adheres to:
- Rule R-MD-04: Feature scaling and transformation parameters fit inside training folds.
- Rule R-MD-06: Log pay target transformation (log guaranteed_cash_annual).
- Rule R-MD-08: Thin evidence abstention (THIN_EVIDENCE) for extreme inputs.
- Rule R-MD-10: Pinned dependencies and reproducible random seed.
- Rule R-UQ-05: Quantile monotonicity enforcement (P10 <= P50 <= P90).
- Rule R-CD-01: Strict typing and complete mypy compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HierarchicalConfig:
    """Hyperparameters and architectural settings for Rung C hierarchical partial pooling."""

    min_cell_sample_size: int = 5
    global_thin_evidence_threshold: int = 5
    max_experience_bound: float = 40.0
    quantiles: list[float] = field(default_factory=lambda: [0.10, 0.50, 0.90])
    experience_polynomial_degree: int = 2
    prior_variance_damping: float = 1e-4
    k_min_employer: int = 5
    enable_employer_tier: bool = True
    enable_employer_cluster: bool = True
    random_seed: int = 42

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.min_cell_sample_size < 1:
            msg = f"min_cell_sample_size must be >= 1, got {self.min_cell_sample_size}"
            raise ValueError(msg)
        if self.global_thin_evidence_threshold < 1:
            msg = (
                f"global_thin_evidence_threshold must be >= 1, "
                f"got {self.global_thin_evidence_threshold}"
            )
            raise ValueError(msg)
        if self.max_experience_bound <= 0.0:
            msg = f"max_experience_bound must be > 0.0, got {self.max_experience_bound}"
            raise ValueError(msg)
        if not self.quantiles or not all(0.0 < q < 1.0 for q in self.quantiles):
            msg = f"quantiles must be non-empty list of values in (0, 1), got {self.quantiles}"
            raise ValueError(msg)
        if sorted(self.quantiles) != list(self.quantiles):
            msg = f"quantiles must be sorted in ascending order, got {self.quantiles}"
            raise ValueError(msg)
        if self.experience_polynomial_degree not in (1, 2):
            msg = (
                f"experience_polynomial_degree must be 1 (linear) or 2 (Mincerian quadratic), "
                f"got {self.experience_polynomial_degree}"
            )
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "min_cell_sample_size": self.min_cell_sample_size,
            "global_thin_evidence_threshold": self.global_thin_evidence_threshold,
            "max_experience_bound": self.max_experience_bound,
            "quantiles": list(self.quantiles),
            "experience_polynomial_degree": self.experience_polynomial_degree,
            "prior_variance_damping": self.prior_variance_damping,
            "k_min_employer": self.k_min_employer,
            "enable_employer_tier": self.enable_employer_tier,
            "enable_employer_cluster": self.enable_employer_cluster,
            "random_seed": self.random_seed,
        }
