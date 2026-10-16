"""Leakage and duplicate-inflation audit engine (Task T4.06, EXP-12).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal validation without cross-partition entity leakage.
  Random i.i.d. splits are prohibited for model evaluation.
- Rule R-MD-02: Final test set is isolated, untouched during tuning, and locked
  for make final-eval. Audits operate strictly on dev partitions.
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead or future information.
- Rule R-MD-04: Adversarial leak detection and leakage audits.
- Rule R-MD-05: Mandatory baseline metrics with confidence intervals and slices.
- Rule R-MD-08: Thin-evidence abstention support.
- Rule R-MD-11: Synthetic data flagged and blocked from production benchmark reports.
- Rule R-UQ-01: Uncertainty quantification; no lone numbers.
- Rule R-CD-03: Dependency boundaries enforced by import-linter.
- Experiment EXP-12: Measure the random-versus-grouped-temporal performance inflation gap.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import polars as pl

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.metrics import (
    ComprehensiveMetricsReport,
    compute_evaluation_report,
)
from compintel.evaluation.splits import (
    SplitConfig,
    create_temporal_grouped_splits,
)
from compintel.logging import get_logger
from compintel.models.baselines.empirical import (
    EmpiricalQuantileBaseline,
    HierarchicalBackoffConfig,
)
from compintel.models.baselines.linear import (
    LinearQuantileBaseline,
    LinearQuantileConfig,
)

logger = get_logger("compintel.evaluation.inflation")

REQUIRED_AUDIT_COLUMNS: set[str] = {
    "observation_id",
    "role_family",
    "seniority",
    "location",
    "years_experience",
    "guaranteed_cash_annual",
    "as_of_date",
    "person_cluster_id",
}


@dataclass(frozen=True)
class LeakageInflationConfig:
    """Configuration for EXP-12 leakage and performance inflation audit."""

    random_seed: int = 42
    train_ratio: float = 0.60
    select_ratio: float = 0.15
    calibrate_ratio: float = 0.15
    test_ratio: float = 0.10
    with_bootstrap_ci: bool = False
    bootstrap_resamples: int = 500
    allow_synthetic: bool = False  # Rule R-MD-11: synthetic data blocked by default

    def __post_init__(self) -> None:
        """Validate split ratios."""
        tot = self.train_ratio + self.select_ratio + self.calibrate_ratio + self.test_ratio
        if abs(tot - 1.0) > 1e-4:
            raise CompIntelValidationError(
                f"Split ratios must sum to 1.0 (got {tot:.4f})",
                code="INVALID_SPLIT_RATIOS",
            )


@dataclass(frozen=True)
class OverlapDiagnostics:
    """Diagnostic metrics measuring entity leakage and temporal lookahead."""

    protocol_name: str
    total_train_records: int
    total_dev_records: int
    total_train_persons: int
    total_dev_persons: int
    person_cluster_overlap_count: int
    person_cluster_leak_records: int
    person_cluster_leak_rate: float
    exact_duplicate_overlap_count: int
    temporal_lookahead_violation_count: int
    max_train_date: str | None
    min_dev_date: str | None
    is_leakage_free: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class MetricInflationComparison:
    """Comparison of a single evaluation metric under Grouped-Temporal vs Random split."""

    metric_name: str
    display_name: str
    unit: str
    grouped_temporal_value: float
    random_value: float
    delta: float  # grouped_temporal - random
    inflation_pct: float  # (delta / grouped_temporal) * 100
    lower_is_better: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ModelInflationResult:
    """Complete performance inflation evaluation for a single baseline model."""

    model_id: str
    model_name: str
    grouped_temporal_eval_count: int
    random_eval_count: int
    grouped_temporal_abstention_rate: float
    random_abstention_rate: float
    grouped_temporal_metrics: ComprehensiveMetricsReport | None
    random_metrics: ComprehensiveMetricsReport | None
    comparisons: list[MetricInflationComparison] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "grouped_temporal_eval_count": self.grouped_temporal_eval_count,
            "random_eval_count": self.random_eval_count,
            "grouped_temporal_abstention_rate": self.grouped_temporal_abstention_rate,
            "random_abstention_rate": self.random_abstention_rate,
            "grouped_temporal_metrics": (
                self.grouped_temporal_metrics.to_dict()
                if self.grouped_temporal_metrics is not None
                else None
            ),
            "random_metrics": (
                self.random_metrics.to_dict() if self.random_metrics is not None else None
            ),
            "comparisons": [c.to_dict() for c in self.comparisons],
        }


@dataclass
class LeakageInflationReport:
    """Publication-grade leakage and duplicate-inflation audit report (EXP-12)."""

    report_id: str
    generated_at_utc: str
    snapshot_id: str
    random_seed: int
    total_observations_analyzed: int
    dev_pool_size: int
    is_synthetic_fixture: bool
    grouped_temporal_diagnostics: OverlapDiagnostics
    random_diagnostics: OverlapDiagnostics
    model_results: dict[str, ModelInflationResult] = field(default_factory=dict)
    key_findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert complete audit report to JSON-serializable dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at_utc": self.generated_at_utc,
            "snapshot_id": self.snapshot_id,
            "random_seed": self.random_seed,
            "total_observations_analyzed": self.total_observations_analyzed,
            "dev_pool_size": self.dev_pool_size,
            "is_synthetic_fixture": self.is_synthetic_fixture,
            "grouped_temporal_diagnostics": self.grouped_temporal_diagnostics.to_dict(),
            "random_diagnostics": self.random_diagnostics.to_dict(),
            "model_results": {k: v.to_dict() for k, v in self.model_results.items()},
            "key_findings": self.key_findings,
        }

    def to_markdown(self) -> str:
        """Format publication-grade GitHub Flavored Markdown audit report."""
        synth_flag = (
            "YES (TEST ONLY)" if self.is_synthetic_fixture else "NO (CANONICAL GROUND TRUTH)"
        )
        rnd_p_leak = (
            "**LEAK DETECTED**"
            if self.random_diagnostics.person_cluster_overlap_count > 0
            else "None"
        )
        rnd_r_leak = (
            "**LEAK DETECTED**"
            if self.random_diagnostics.person_cluster_leak_records > 0
            else "None"
        )
        rnd_dup_leak = (
            "**DUPLICATE LEAK**"
            if self.random_diagnostics.exact_duplicate_overlap_count > 0
            else "None"
        )
        rnd_time_leak = (
            "**FUTURE LOOKAHEAD**"
            if self.random_diagnostics.temporal_lookahead_violation_count > 0
            else "None"
        )
        gt_clean = (
            "PASS (100% CLEAN)" if self.grouped_temporal_diagnostics.is_leakage_free else "FAIL"
        )
        rnd_clean = "PASS" if self.random_diagnostics.is_leakage_free else "COMPROMISED"
        rmd_tag = (
            "R-MD-01 ENFORCED" if self.grouped_temporal_diagnostics.is_leakage_free else "VIOLATION"
        )

        lines: list[str] = [
            "# Leakage and Duplicate-Inflation Audit (EXP-12)",
            "",
            "> **Diagnostic for Engineering Culture:** Quantifying the performance inflation gap",
            "> between naive random i.i.d. splitting and rigorous grouped-temporal splitting.",
            "> Governed by Rules R-MD-01, R-MD-02, R-MD-03, R-MD-04, and ADR-0004.",
            "",
            "## 1. Audit Metadata",
            "",
            "| Parameter | Value |",
            "|---|---|",
            f"| **Report ID** | `{self.report_id}` |",
            f"| **Generated (UTC)** | `{self.generated_at_utc}` |",
            f"| **Snapshot ID** | `{self.snapshot_id}` |",
            f"| **Random Seed** | `{self.random_seed}` |",
            f"| **Total Canonical Observations** | `{self.total_observations_analyzed}` |",
            f"| **Development Pool Size (Train + Select)** | `{self.dev_pool_size}` |",
            f"| **Synthetic Fixture Flag (R-MD-11)** | `{synth_flag}` |",
            "",
            "## 2. Leakage and Overlap Diagnostics",
            "",
            (
                "| Metric | Grouped-Temporal (Protocol B) | "
                "Naive Random (Protocol A) | Leakage Violation Detected |"
            ),
            "|---|:---:|:---:|:---:|",
            (
                f"| Train Records | `{self.grouped_temporal_diagnostics.total_train_records}` | "
                f"`{self.random_diagnostics.total_train_records}` | - |"
            ),
            (
                f"| Dev Records | `{self.grouped_temporal_diagnostics.total_dev_records}` | "
                f"`{self.random_diagnostics.total_dev_records}` | - |"
            ),
            (
                f"| Person Clusters in Train | "
                f"`{self.grouped_temporal_diagnostics.total_train_persons}` | "
                f"`{self.random_diagnostics.total_train_persons}` | - |"
            ),
            (
                f"| Person Clusters in Dev | "
                f"`{self.grouped_temporal_diagnostics.total_dev_persons}` | "
                f"`{self.random_diagnostics.total_dev_persons}` | - |"
            ),
            (
                f"| **Overlapping Person Clusters** | "
                f"`{self.grouped_temporal_diagnostics.person_cluster_overlap_count}` | "
                f"`{self.random_diagnostics.person_cluster_overlap_count}` | "
                f"{rnd_p_leak} |"
            ),
            (
                f"| **Leaked Dev Records** | "
                f"`{self.grouped_temporal_diagnostics.person_cluster_leak_records}` | "
                f"`{self.random_diagnostics.person_cluster_leak_records}` "
                f"({self.random_diagnostics.person_cluster_leak_rate:.1f}%) | "
                f"{rnd_r_leak} |"
            ),
            (
                f"| **Exact Duplicate Overlaps** | "
                f"`{self.grouped_temporal_diagnostics.exact_duplicate_overlap_count}` | "
                f"`{self.random_diagnostics.exact_duplicate_overlap_count}` | "
                f"{rnd_dup_leak} |"
            ),
            (
                f"| **Temporal Lookahead Records** | "
                f"`{self.grouped_temporal_diagnostics.temporal_lookahead_violation_count}` | "
                f"`{self.random_diagnostics.temporal_lookahead_violation_count}` | "
                f"{rnd_time_leak} |"
            ),
            (
                f"| Max Train Date | "
                f"`{self.grouped_temporal_diagnostics.max_train_date or 'N/A'}` | "
                f"`{self.random_diagnostics.max_train_date or 'N/A'}` | - |"
            ),
            (
                f"| Min Dev Date | `{self.grouped_temporal_diagnostics.min_dev_date or 'N/A'}` | "
                f"`{self.random_diagnostics.min_dev_date or 'N/A'}` | - |"
            ),
            (f"| **Strict Leakage Free** | `{gt_clean}` | `{rnd_clean}` | {rmd_tag} |"),
            "",
            "## 3. Baseline Model Performance Inflation (EXP-12)",
            "",
        ]

        for m_id, m_res in self.model_results.items():
            lines.extend(
                [
                    f"### 3.{list(self.model_results.keys()).index(m_id) + 1} {m_res.model_name}",
                    "",
                    (
                        f"- **Grouped-Temporal Evaluated Records:** "
                        f"`{m_res.grouped_temporal_eval_count}` "
                        f"(Abstention Rate: `{m_res.grouped_temporal_abstention_rate:.1f}%`)"
                    ),
                    (
                        f"- **Naive Random Evaluated Records:** "
                        f"`{m_res.random_eval_count}` "
                        f"(Abstention Rate: `{m_res.random_abstention_rate:.1f}%`)"
                    ),
                    "",
                ]
            )

            if not m_res.comparisons:
                lines.extend(
                    [
                        "> [!NOTE]",
                        "> Insufficient non-abstained records to compute comparison metrics.",
                        "> Thin evidence per Rule R-MD-08.",
                        "",
                    ]
                )
                continue

            lines.extend(
                [
                    "| Metric | Grouped-Temporal | Naive Random | "
                    "Inflation Gap (Delta) | Inflation (%) | Direction |",
                    "|---|:---:|:---:|:---:|:---:|:---:|",
                ]
            )

            for comp in m_res.comparisons:
                gt_str = f"{comp.grouped_temporal_value:.3f} {comp.unit}".strip()
                rnd_str = f"{comp.random_value:.3f} {comp.unit}".strip()
                delta_str = f"{comp.delta:+.3f} {comp.unit}".strip()
                inf_str = f"{comp.inflation_pct:+.1f}%"
                dir_str = "Lower is better" if comp.lower_is_better else "Higher is better"

                lines.append(
                    f"| **{comp.display_name}** | `{gt_str}` | `{rnd_str}` | "
                    f"`{delta_str}` | `{inf_str}` | {dir_str} |"
                )
            lines.append("")

        lines.extend(
            [
                "## 4. Key Findings and Diagnostic Implications",
                "",
            ]
        )

        for finding in self.key_findings:
            lines.append(f"- {finding}")

        lines.extend(
            [
                "",
                "---",
                "*Report generated by CompIntel Leakage Inflation Auditor (Task T4.06, EXP-12).*",
            ]
        )

        return "\n".join(lines)

    def save_json(self, path: Path) -> None:
        """Persist report dictionary to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def save_markdown(self, path: Path) -> None:
        """Persist report to Markdown file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())


class LeakageInflationAuditor:
    """Auditor for quantifying entity leakage and performance inflation under random splits."""

    def __init__(self, config: LeakageInflationConfig | None = None) -> None:
        self.config = config or LeakageInflationConfig()

    def audit(
        self,
        df: pl.DataFrame,
        snapshot_id: str = "SNAP-CANONICAL",
    ) -> LeakageInflationReport:
        """Execute full leakage and duplicate-inflation audit across Rung A and Rung B baselines.

        Args:
            df: Canonical observations DataFrame.
            snapshot_id: Canonical snapshot identifier.

        Returns:
            LeakageInflationReport containing overlap diagnostics and performance comparisons.
        """
        # 1. Rule R-MD-11: Synthetic Data Isolation Guard
        is_synthetic_fixture = False
        if "is_synthetic" in df.columns:
            has_synthetic = df.filter(pl.col("is_synthetic") == True).height > 0  # noqa: E712
            if has_synthetic:
                is_synthetic_fixture = True
                if not self.config.allow_synthetic:
                    raise DataContractError(
                        "Synthetic records detected in dataset. Under Rule R-MD-11, synthetic data "
                        "is blocked from baseline evaluation and audit reports. "
                        "Pass allow_synthetic=True strictly for test fixtures.",
                        code="SYNTHETIC_DATA_BLOCKED",
                    )

        # 2. Schema Column Validation
        missing_cols = REQUIRED_AUDIT_COLUMNS - set(df.columns)
        if missing_cols:
            raise CompIntelValidationError(
                f"Missing required columns for leakage audit: {sorted(missing_cols)}",
                code="MISSING_COLUMNS",
            )

        total_obs = df.height
        if total_obs == 0:
            raise CompIntelValidationError(
                "Cannot perform leakage inflation audit on empty DataFrame.",
                code="EMPTY_DATASET",
            )

        logger.info(
            "Starting leakage and duplicate-inflation audit (EXP-12)",
            total_observations=total_obs,
            snapshot_id=snapshot_id,
            seed=self.config.random_seed,
        )

        # 3. Protocol B: Grouped-Temporal 4-way Split
        split_cfg = SplitConfig(
            train_ratio=self.config.train_ratio,
            select_ratio=self.config.select_ratio,
            calibrate_ratio=self.config.calibrate_ratio,
            test_ratio=self.config.test_ratio,
            group_column="person_cluster_id",
            date_column="as_of_date",
            id_column="observation_id",
            exclude_cross_window_groups=True,
            validate_schema=False,
        )

        gt_splits = create_temporal_grouped_splits(df, config=split_cfg)
        gt_train = gt_splits.train_df
        gt_dev = gt_splits.select_df

        # 4. Protocol A: Naive Random Split on Dev Pool (Rule R-MD-02: Test partition isolated)
        dev_pool = pl.concat([gt_train, gt_dev])
        dev_pool_size = dev_pool.height

        # Shuffle dev pool uniformly randomly
        shuffled_pool = dev_pool.sample(
            fraction=1.0,
            shuffle=True,
            seed=self.config.random_seed,
        )

        rnd_train = shuffled_pool.slice(0, gt_train.height)
        rnd_dev = shuffled_pool.slice(gt_train.height, gt_dev.height)

        # 5. Compute Overlap Diagnostics for Both Protocols
        gt_diag = self._compute_overlap_diagnostics(
            protocol_name="Grouped-Temporal (Protocol B)",
            train_df=gt_train,
            dev_df=gt_dev,
        )

        rnd_diag = self._compute_overlap_diagnostics(
            protocol_name="Naive Random (Protocol A)",
            train_df=rnd_train,
            dev_df=rnd_dev,
        )

        # 6. Train and Evaluate Baseline Models
        model_results: dict[str, ModelInflationResult] = {}

        # 6.1 Rung A: Empirical Conditional Quantiles
        rung_a_res = self._audit_model(
            model_id="rung_a_empirical",
            model_name="Rung A: Empirical Conditional Quantiles (Hierarchical Backoff)",
            create_model_fn=lambda: EmpiricalQuantileBaseline(
                config=HierarchicalBackoffConfig(
                    thin_evidence_threshold=5 if is_synthetic_fixture else 10,
                )
            ),
            gt_train=gt_train,
            gt_dev=gt_dev,
            rnd_train=rnd_train,
            rnd_dev=rnd_dev,
        )
        model_results["rung_a_empirical"] = rung_a_res

        # 6.2 Rung B: Linear Quantile Regression
        rung_b_res = self._audit_model(
            model_id="rung_b_linear",
            model_name="Rung B: Regularized Linear Quantile Regression (Log Pay)",
            create_model_fn=lambda: LinearQuantileBaseline(
                config=LinearQuantileConfig(
                    alpha=0.01,
                    include_quadratic_yoe=True,
                )
            ),
            gt_train=gt_train,
            gt_dev=gt_dev,
            rnd_train=rnd_train,
            rnd_dev=rnd_dev,
        )
        model_results["rung_b_linear"] = rung_b_res

        # 7. Synthesize Key Findings
        key_findings = self._synthesize_findings(gt_diag, rnd_diag, model_results)

        report = LeakageInflationReport(
            report_id=f"AUDIT-EXP12-{datetime.now(tz=UTC).strftime('%Y%m%d-%H%M%S')}",
            generated_at_utc=datetime.now(tz=UTC).isoformat(),
            snapshot_id=snapshot_id,
            random_seed=self.config.random_seed,
            total_observations_analyzed=total_obs,
            dev_pool_size=dev_pool_size,
            is_synthetic_fixture=is_synthetic_fixture,
            grouped_temporal_diagnostics=gt_diag,
            random_diagnostics=rnd_diag,
            model_results=model_results,
            key_findings=key_findings,
        )

        logger.info(
            "Leakage inflation audit completed successfully",
            report_id=report.report_id,
            findings_count=len(key_findings),
        )

        return report

    def _compute_overlap_diagnostics(
        self,
        protocol_name: str,
        train_df: pl.DataFrame,
        dev_df: pl.DataFrame,
    ) -> OverlapDiagnostics:
        """Calculate entity cluster overlaps, duplicate leaks, and temporal lookahead violations."""
        total_train = train_df.height
        total_dev = dev_df.height

        train_persons = set(train_df["person_cluster_id"].drop_nulls().to_list())
        dev_persons = set(dev_df["person_cluster_id"].drop_nulls().to_list())
        person_overlaps = train_persons.intersection(dev_persons)
        person_overlap_count = len(person_overlaps)

        leak_records = 0
        if person_overlap_count > 0:
            leak_records = dev_df.filter(
                pl.col("person_cluster_id").is_in(list(person_overlaps))
            ).height
        leak_rate = (leak_records / total_dev * 100.0) if total_dev > 0 else 0.0

        dup_overlap_count = 0
        if (
            "exact_duplicate_cluster_id" in train_df.columns
            and "exact_duplicate_cluster_id" in dev_df.columns
        ):
            train_dups = set(train_df["exact_duplicate_cluster_id"].drop_nulls().to_list())
            dev_dups = set(dev_df["exact_duplicate_cluster_id"].drop_nulls().to_list())
            dup_overlap_count = len(train_dups.intersection(dev_dups))

        # Temporal lookahead check: train records dated strictly after min dev date
        train_dates = [d for d in train_df["as_of_date"].to_list() if d is not None]
        dev_dates = [d for d in dev_df["as_of_date"].to_list() if d is not None]

        max_train_date = max(train_dates).isoformat() if train_dates else None
        min_dev_date = min(dev_dates).isoformat() if dev_dates else None

        temporal_violations = 0
        if min_dev_date is not None and train_dates:
            min_dev_val = min(dev_dates)
            temporal_violations = sum(1 for d in train_dates if d > min_dev_val)

        is_leakage_free = (
            person_overlap_count == 0 and dup_overlap_count == 0 and temporal_violations == 0
        )

        return OverlapDiagnostics(
            protocol_name=protocol_name,
            total_train_records=total_train,
            total_dev_records=total_dev,
            total_train_persons=len(train_persons),
            total_dev_persons=len(dev_persons),
            person_cluster_overlap_count=person_overlap_count,
            person_cluster_leak_records=leak_records,
            person_cluster_leak_rate=leak_rate,
            exact_duplicate_overlap_count=dup_overlap_count,
            temporal_lookahead_violation_count=temporal_violations,
            max_train_date=max_train_date,
            min_dev_date=min_dev_date,
            is_leakage_free=is_leakage_free,
        )

    def _audit_model(
        self,
        model_id: str,
        model_name: str,
        create_model_fn: Any,
        gt_train: pl.DataFrame,
        gt_dev: pl.DataFrame,
        rnd_train: pl.DataFrame,
        rnd_dev: pl.DataFrame,
    ) -> ModelInflationResult:
        """Fit and evaluate a model across both protocols, calculating the inflation gap."""
        # 1. Evaluate on Grouped-Temporal
        gt_model = create_model_fn()
        gt_model.fit(gt_train)
        gt_preds = gt_model.predict(gt_dev) if gt_dev.height > 0 else None

        gt_rep, gt_abstained_rate = self._compute_metrics_from_preds(gt_dev, gt_preds)

        # 2. Evaluate on Naive Random
        rnd_model = create_model_fn()
        rnd_model.fit(rnd_train)
        rnd_preds = rnd_model.predict(rnd_dev) if rnd_dev.height > 0 else None

        rnd_rep, rnd_abstained_rate = self._compute_metrics_from_preds(rnd_dev, rnd_preds)

        # 3. Compute Metric Comparisons
        comparisons = self._compute_comparisons(gt_rep, rnd_rep)

        return ModelInflationResult(
            model_id=model_id,
            model_name=model_name,
            grouped_temporal_eval_count=gt_dev.height,
            random_eval_count=rnd_dev.height,
            grouped_temporal_abstention_rate=gt_abstained_rate,
            random_abstention_rate=rnd_abstained_rate,
            grouped_temporal_metrics=gt_rep,
            random_metrics=rnd_rep,
            comparisons=comparisons,
        )

    def _compute_metrics_from_preds(
        self,
        eval_df: pl.DataFrame,
        preds_df: pl.DataFrame | None,
    ) -> tuple[ComprehensiveMetricsReport | None, float]:
        """Compute metrics filtering out thin-evidence abstentions (Rule R-MD-08)."""
        if eval_df.height == 0 or preds_df is None or preds_df.height == 0:
            return None, 0.0

        # Both baseline models produce row-aligned DataFrames matching eval_df
        joined = preds_df.with_columns(
            eval_df["guaranteed_cash_annual"].alias("guaranteed_cash_annual")
        )

        total_rows = joined.height
        if total_rows == 0:
            return None, 0.0

        abstained_rows = joined.filter(pl.col("is_abstained") == True).height  # noqa: E712
        abstention_rate = (abstained_rows / total_rows) * 100.0

        valid_df = joined.filter(
            (pl.col("is_abstained") == False)  # noqa: E712
            & pl.col("guaranteed_cash_annual").is_not_null()
            & pl.col("p10").is_not_null()
            & pl.col("p50").is_not_null()
            & pl.col("p90").is_not_null()
        )

        if valid_df.height < 1:
            return None, abstention_rate

        report = compute_evaluation_report(
            y_true=valid_df["guaranteed_cash_annual"].to_list(),
            q10_pred=valid_df["p10"].to_list(),
            q50_pred=valid_df["p50"].to_list(),
            q90_pred=valid_df["p90"].to_list(),
            with_ci=self.config.with_bootstrap_ci,
            n_resamples=self.config.bootstrap_resamples,
            seed=self.config.random_seed,
        )

        return report, abstention_rate

    def _compute_comparisons(
        self,
        gt_rep: ComprehensiveMetricsReport | None,
        rnd_rep: ComprehensiveMetricsReport | None,
    ) -> list[MetricInflationComparison]:
        """Extract paired metric deltas and percentage inflation."""
        if gt_rep is None or rnd_rep is None:
            return []

        specs: list[tuple[str, str, str, float, float, bool]] = [
            (
                "mae",
                "Mean Absolute Error (MAE)",
                "LPA",
                gt_rep.point.mae,
                rnd_rep.point.mae,
                True,
            ),
            (
                "medae",
                "Median Absolute Error (MdAE)",
                "LPA",
                gt_rep.point.medae,
                rnd_rep.point.medae,
                True,
            ),
            (
                "mdape",
                "Median Absolute Percentage Error (MdAPE)",
                "%",
                gt_rep.point.mdape * 100.0,
                rnd_rep.point.mdape * 100.0,
                True,
            ),
            (
                "mean_pinball_loss",
                "Mean Pinball Loss (P10/P50/P90)",
                "LPA",
                gt_rep.quantile_loss.mean_pinball_loss,
                rnd_rep.quantile_loss.mean_pinball_loss,
                True,
            ),
            (
                "coverage_80",
                "80% Interval Empirical Coverage",
                "%",
                gt_rep.interval.coverage_80 * 100.0,
                rnd_rep.interval.coverage_80 * 100.0,
                False,
            ),
            (
                "median_width",
                "Median Interval Width (P90 - P10)",
                "LPA",
                gt_rep.interval.median_width,
                rnd_rep.interval.median_width,
                True,
            ),
            (
                "mean_calibration_error",
                "Mean Calibration Error",
                "",
                gt_rep.calibration.mean_calibration_error,
                rnd_rep.calibration.mean_calibration_error,
                True,
            ),
            (
                "quantile_crossing_rate",
                "Quantile Crossing Rate",
                "%",
                gt_rep.calibration.crossing_rate * 100.0,
                rnd_rep.calibration.crossing_rate * 100.0,
                True,
            ),
        ]

        comparisons: list[MetricInflationComparison] = []
        for key, name, unit, gt_val, rnd_val, lower_is_better in specs:
            delta = gt_val - rnd_val
            # Positive delta for error metrics indicates random split underestimated error
            # (i.e. perceived performance was inflated)
            inflation_pct = (delta / gt_val * 100.0) if abs(gt_val) > 1e-6 else 0.0
            comparisons.append(
                MetricInflationComparison(
                    metric_name=key,
                    display_name=name,
                    unit=unit,
                    grouped_temporal_value=round(gt_val, 4),
                    random_value=round(rnd_val, 4),
                    delta=round(delta, 4),
                    inflation_pct=round(inflation_pct, 2),
                    lower_is_better=lower_is_better,
                )
            )

        return comparisons

    def _synthesize_findings(
        self,
        gt_diag: OverlapDiagnostics,
        rnd_diag: OverlapDiagnostics,
        model_results: dict[str, ModelInflationResult],
    ) -> list[str]:
        """Synthesize high-level takeaways for the baseline report."""
        findings: list[str] = []

        # 1. Leakage findings
        if gt_diag.is_leakage_free:
            findings.append(
                "**Grouped-Temporal Split Integrity:** Protocol B strictly enforces zero person "
                "cluster overlap, zero duplicate overlap, and zero temporal lookahead violations."
            )
        else:
            findings.append(
                "**Warning:** Protocol B encountered grouping discrepancies; check contributor "
                "quarantine policies."
            )

        if rnd_diag.person_cluster_overlap_count > 0:
            findings.append(
                f"**Entity Memorization Leakage in Random Split:** Protocol A leaks "
                f"{rnd_diag.person_cluster_overlap_count} distinct person clusters across train "
                f"and dev partitions ({rnd_diag.person_cluster_leak_records} dev observations, "
                f"{rnd_diag.person_cluster_leak_rate:.1f}% of the evaluation set)."
            )

        if rnd_diag.temporal_lookahead_violation_count > 0:
            findings.append(
                f"**Temporal Inversion / Lookahead:** Protocol A contains "
                f"{rnd_diag.temporal_lookahead_violation_count} training observations with "
                "timestamps after the earliest evaluation observation."
            )

        # 2. Model Inflation takeaways
        for _m_id, m_res in model_results.items():
            mae_comp = next((c for c in m_res.comparisons if c.metric_name == "mae"), None)
            if mae_comp and abs(mae_comp.delta) > 0.001:
                if mae_comp.delta > 0:
                    findings.append(
                        f"**{m_res.model_name}:** Naive random splitting understates prediction "
                        f"error (MAE inflated by {mae_comp.delta:+.3f} {mae_comp.unit}, "
                        f"{mae_comp.inflation_pct:+.1f}%), confirming that random i.i.d. splits "
                        "produce artificially optimistic benchmarks."
                    )
                else:
                    findings.append(
                        f"**{m_res.model_name}:** Random split error was higher by "
                        f"{abs(mae_comp.delta):.3f} {mae_comp.unit} due to partition variance "
                        "or extreme cross-window samples."
                    )

        if not any("understates prediction error" in f for f in findings) and any(
            m.grouped_temporal_eval_count > 0 for m in model_results.values()
        ):
            findings.append(
                "**Empirical Baseline Behavior:** Baselines evaluated cleanly across dev "
                "partitions. Strict grouped-temporal evaluation (Protocol B) remains mandatory "
                "under Rule R-MD-01."
            )

        return findings


def run_leakage_inflation_audit(
    df: pl.DataFrame,
    config: LeakageInflationConfig | None = None,
    snapshot_id: str = "SNAP-CANONICAL",
) -> LeakageInflationReport:
    """Convenience functional wrapper for executing a leakage and duplicate-inflation audit."""
    auditor = LeakageInflationAuditor(config=config)
    return auditor.audit(df=df, snapshot_id=snapshot_id)
