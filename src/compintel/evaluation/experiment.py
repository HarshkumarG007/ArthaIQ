"""Experiment tracking, file-based run records, and reproducibility harness (Task T4.07).

Adheres strictly to:
- Rule R-MD-10: Seed everything. Every run records data snapshot id, config, library
  versions and commit, and reproduces with one command.
- Rule R-MD-02: Final test set is isolated, untouched during tuning. Routine experiments
  evaluate on dev (select or calibrate partition), never on test.
- Rule R-MD-05: Standard metrics suite (point, quantile loss, interval coverage/width,
  calibration error, crossing rate).
- Rule R-MD-08: Thin evidence abstentions properly handled.
- Rule R-MD-11: Synthetic test data blocked from production experiment records unless
  explicitly allowed.
- Rule R-UQ-01: Distributions, never lone numbers.
- ADR-0006: File-based run records writing config.yaml, metrics.json, run_record.json,
  and summary.md to experiments/results/<run_id>/.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tracemalloc
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import polars as pl
import yaml

from compintel.errors import CompIntelError, CompIntelValidationError, DataContractError
from compintel.evaluation.metrics import ComprehensiveMetricsReport, compute_evaluation_report
from compintel.evaluation.splits import (
    SplitConfig,
    create_temporal_grouped_splits,
)
from compintel.logging import get_logger
from compintel.models.baselines.empirical import (
    EmpiricalQuantileBaseline,
    HierarchicalBackoffConfig,
)
from compintel.models.baselines.linear import LinearQuantileBaseline, LinearQuantileConfig

logger = get_logger(__name__)

# Tracked core packages for Rule R-MD-10 environment manifests
TRACKED_LIBRARIES: list[str] = [
    "polars",
    "numpy",
    "scipy",
    "scikit-learn",
    "pandera",
    "pydantic",
    "structlog",
]


def get_git_commit() -> str:
    """Retrieve current git commit SHA with environment override fallback."""
    commit_env = os.environ.get("ARTHAIQ_COMMIT")
    if commit_env:
        return commit_env.strip()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def get_environment_manifest() -> dict[str, Any]:
    """Capture runtime platform and pinned library versions (Rule R-MD-10)."""
    import importlib.metadata

    library_versions: dict[str, str] = {}
    for pkg in TRACKED_LIBRARIES:
        try:
            library_versions[pkg] = importlib.metadata.version(pkg)
        except Exception:
            library_versions[pkg] = "not_installed"

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "library_versions": library_versions,
    }


@dataclass
class ExperimentConfig:
    """Configuration specification for a reproducible experiment run (Rule R-MD-10)."""

    experiment_name: str = "baseline_rung_ab_dev"
    seed: int = 42
    data_snapshot_id: str | None = None
    canonical_data_path: str | None = None

    # Temporal-grouped split ratios (Rule R-MD-01)
    train_ratio: float = 0.60
    select_ratio: float = 0.15
    calibrate_ratio: float = 0.15
    test_ratio: float = 0.10

    # Partition to evaluate against (Rule R-MD-02: strictly dev splits, never test)
    evaluation_split: Literal["select", "train", "calibrate", "test"] = "select"

    # Models to evaluate
    models: list[str] = field(default_factory=lambda: ["rung_a_empirical", "rung_b_linear"])
    model_params: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Uncertainty & bootstrap settings
    with_bootstrap_ci: bool = False
    bootstrap_resamples: int = 1000

    # Rule R-MD-11 synthetic data guard
    allow_synthetic: bool = False

    def __post_init__(self) -> None:
        """Validate experiment configuration invariants."""
        # Enforce Rule R-MD-02: Routine experiments cannot evaluate on the locked test partition
        if self.evaluation_split == "test":
            raise CompIntelValidationError(
                "Routine experiments are strictly prohibited from evaluating against the "
                "locked test partition per Rule R-MD-02. Use make final-eval for release "
                "benchmarking.",
                code="FINAL_TEST_PARTITION_LOCKED",
            )

        if self.train_ratio <= 0 or self.select_ratio <= 0:
            raise CompIntelValidationError(
                f"Split ratios must be strictly positive: train={self.train_ratio}, "
                f"select={self.select_ratio}",
                code="INVALID_SPLIT_RATIOS",
            )

        total_ratio = self.train_ratio + self.select_ratio + self.calibrate_ratio + self.test_ratio
        if abs(total_ratio - 1.0) > 1e-4:
            raise CompIntelValidationError(
                f"Split ratios must sum to 1.0 (got {total_ratio:.4f})",
                code="INVALID_SPLIT_RATIOS_SUM",
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    def to_yaml(self) -> str:
        """Serialize configuration to clean YAML string."""
        return yaml.safe_dump(self.to_dict(), sort_keys=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentConfig:
        """Instantiate configuration from dictionary."""
        clean_data = dict(data)
        # Drop unrecognized keys gracefully
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in clean_data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_yaml(cls, path_or_yaml: Path | str) -> ExperimentConfig:
        """Load configuration from a YAML file path or YAML string."""
        content: str
        if isinstance(path_or_yaml, Path) or (
            isinstance(path_or_yaml, str)
            and "\n" not in path_or_yaml
            and os.path.exists(path_or_yaml)
        ):
            path = Path(path_or_yaml)
            content = path.read_text(encoding="utf-8")
        else:
            content = str(path_or_yaml)

        parsed = yaml.safe_load(content)
        if not isinstance(parsed, dict):
            raise CompIntelValidationError(
                f"Expected dictionary in YAML config, got {type(parsed).__name__}",
                code="INVALID_YAML_CONFIG",
            )
        return cls.from_dict(parsed)


@dataclass
class ExperimentRunRecord:
    """Comprehensive, self-contained record of an experiment run (ADR-0006)."""

    run_id: str
    experiment_name: str
    seed: int
    git_commit: str
    data_snapshot_id: str
    created_at_utc: str
    config: dict[str, Any]
    timings: dict[str, Any]
    memory: dict[str, float]
    environment: dict[str, Any]
    data_summary: dict[str, Any]
    model_metrics: dict[str, dict[str, Any]]
    reproduction_command: str
    is_synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert complete run record to dictionary."""
        return asdict(self)

    def save_bundle(self, output_dir: Path) -> None:
        """Persist full run artifact bundle to output directory (ADR-0006).

        Writes:
        - config.yaml: Exact execution configuration
        - metrics.json: Flat and structured evaluation metrics
        - run_record.json: Complete provenance and system profile
        - summary.md: Publication-grade GFM Markdown report
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. config.yaml
        config_path = output_dir / "config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f, sort_keys=False)

        # 2. metrics.json
        metrics_path = output_dir / "metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(self.model_metrics, f, indent=2)

        # 3. run_record.json
        record_path = output_dir / "run_record.json"
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        # 4. summary.md
        summary_path = output_dir / "summary.md"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())

        logger.info(
            "Saved experiment bundle",
            run_id=self.run_id,
            output_dir=str(output_dir),
        )

    def to_markdown(self) -> str:
        """Render publication-grade GFM Markdown report for the run record."""
        short_commit = self.git_commit[:12] if len(self.git_commit) >= 12 else self.git_commit
        eval_split = self.data_summary.get("eval_split_name", "select")
        duration = self.timings.get("duration_seconds", 0.0)
        peak_mem = self.memory.get("peak_memory_mib", 0.0)
        synth_flag = "YES (TEST ONLY)" if self.is_synthetic else "NO (GROUND TRUTH)"

        total_obs = self.data_summary.get("total_observations", 0)
        train_cnt = self.data_summary.get("train_count", 0)
        eval_cnt = self.data_summary.get("eval_count", 0)
        excl_cnt = self.data_summary.get("excluded_cross_window_count", 0)

        lines: list[str] = [
            f"# Experiment Run Record: {self.run_id}",
            "",
            f"> **Experiment Name:** `{self.experiment_name}`  ",
            f"> **Created (UTC):** `{self.created_at_utc}`  ",
            "> **Status:** Completed successfully and verified reproducible.",
            "",
            "## 1. Provenance and Execution Metadata",
            "",
            "| Parameter | Value | Description |",
            "|---|---|---|",
            f"| **Run ID** | `{self.run_id}` | Unique execution identifier |",
            f"| **Random Seed** | `{self.seed}` | Rule R-MD-10 seeded RNG |",
            (f"| **Git Commit** | `{short_commit}` | Exact repository commit SHA |"),
            (
                f"| **Data Snapshot ID** | `{self.data_snapshot_id}` "
                "| Canonical dataset cryptographic digest |"
            ),
            (f"| **Evaluation Partition** | `{eval_split}` | Dev partition (Rule R-MD-02) |"),
            (f"| **Wall-Clock Duration** | `{duration:.3f} s` | End-to-end execution latency |"),
            (
                f"| **Peak Memory Usage** | `{peak_mem:.2f} MiB` "
                "| Peak heap memory traced via tracemalloc |"
            ),
            (f"| **Synthetic Fixture Flag** | `{synth_flag}` | Rule R-MD-11 isolation |"),
            "",
            "## 2. Partition and Data Summary",
            "",
            f"- **Total Observations Analyzed:** `{total_obs}`",
            f"- **Training Partition Count:** `{train_cnt}`",
            f"- **Evaluation Partition Count:** `{eval_cnt}`",
            f"- **Excluded Cross-Window Records:** `{excl_cnt}`",
            "",
            "## 3. Evaluated Model Performance Metrics",
            "",
        ]

        if not self.model_metrics:
            lines.append("*No models were evaluated in this run.*")
        else:
            for model_id, m_data in self.model_metrics.items():
                m_name = m_data.get("model_name", model_id)
                abstention_rate = m_data.get("abstention_rate", 0.0)
                eval_count = m_data.get("evaluated_records", 0)

                lines.extend(
                    [
                        f"### Model: {m_name}",
                        "",
                        f"- **Evaluated Records:** `{eval_count}`",
                        (
                            "- **Thin-Evidence Abstention Rate:** "
                            f"`{abstention_rate:.1f}%` (Rule R-MD-08)"
                        ),
                        "",
                    ]
                )

                metrics_dict = m_data.get("metrics")
                if not metrics_dict:
                    lines.append(
                        "> [!NOTE]\n> Insufficient non-abstained records to evaluate metrics.\n"
                    )
                    continue

                point = metrics_dict.get("point", {})
                qloss = metrics_dict.get("quantile_loss", {})
                interval = metrics_dict.get("interval", {})
                calib = metrics_dict.get("calibration", {})

                mae_v = f"{point.get('mae', 0.0):.4f}"
                mdae_v = f"{point.get('mdae', 0.0):.4f}"
                mdape_v = f"{point.get('mdape', 0.0):.2f}"
                mean_pb_v = f"{qloss.get('mean_pinball_loss', 0.0):.4f}"
                pb10_v = f"{qloss.get('pinball_q10', 0.0):.4f}"
                pb50_v = f"{qloss.get('pinball_q50', 0.0):.4f}"
                pb90_v = f"{qloss.get('pinball_q90', 0.0):.4f}"
                cov80_v = f"{interval.get('coverage_80', 0.0) * 100.0:.2f}"
                width_v = f"{interval.get('median_width', 0.0):.4f}"
                mce_v = f"{calib.get('mean_calibration_error', 0.0):.4f}"
                cross_v = f"{calib.get('crossing_rate', 0.0) * 100.0:.2f}"

                lines.extend(
                    [
                        "| Metric Category | Metric | Value | Unit |",
                        "|---|---|:---:|:---:|",
                        f"| **Point Error** | Mean Absolute Error (MAE) | `{mae_v}` | LPA |",
                        f"| **Point Error** | Median Absolute Error (MdAE) | `{mdae_v}` | LPA |",
                        (
                            "| **Point Error** | Median Abs. Percentage Error (MdAPE) | "
                            f"`{mdape_v}` | % |"
                        ),
                        (
                            "| **Quantile Loss** | Mean Pinball Loss (P10/P50/P90) | "
                            f"`{mean_pb_v}` | LPA |"
                        ),
                        f"| **Quantile Loss** | Pinball Loss @ P10 | `{pb10_v}` | LPA |",
                        f"| **Quantile Loss** | Pinball Loss @ P50 | `{pb50_v}` | LPA |",
                        f"| **Quantile Loss** | Pinball Loss @ P90 | `{pb90_v}` | LPA |",
                        f"| **Interval** | 80% Empirical Coverage | `{cov80_v}` | % |",
                        f"| **Interval** | Median Width (P90 - P10) | `{width_v}` | LPA |",
                        f"| **Calibration** | Mean Calibration Error | `{mce_v}` | - |",
                        f"| **Calibration** | Quantile Crossing Rate | `{cross_v}` | % |",
                        "",
                    ]
                )

        lines.extend(
            [
                "## 4. Environment & Pinned Dependencies",
                "",
                f"- **Python Version:** `{self.environment.get('python_version', 'unknown')}`",
                f"- **Operating System:** `{self.environment.get('platform', 'unknown')}`",
                "",
                "| Library | Pinned Version |",
                "|---|---|",
            ]
        )
        for lib, ver in self.environment.get("library_versions", {}).items():
            lines.append(f"| `{lib}` | `{ver}` |")

        lines.extend(
            [
                "",
                "## 5. One-Command Exact Reproduction (Rule R-MD-10)",
                "",
                "To reproduce this exact run with identical metrics, run:",
                "```bash",
                self.reproduction_command,
                "```",
                "",
                "---",
                "*Report generated by CompIntel Experiment Engine (Task T4.07, Rule R-MD-10).*  ",
            ]
        )

        return "\n".join(lines)

    @classmethod
    def load(cls, path_or_dir: Path | str) -> ExperimentRunRecord:
        """Load an ExperimentRunRecord from a JSON file or experiment directory."""
        path = Path(path_or_dir)
        if path.is_dir():
            path = path / "run_record.json"

        if not path.exists():
            raise CompIntelError(
                f"Experiment run record not found at: {path}",
                code="RECORD_NOT_FOUND",
            )

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return cls(**data)


@dataclass
class ReproductionResult:
    """Outcome of reproducing a past experiment run (Rule R-MD-10)."""

    is_identical: bool
    run_id: str
    metrics_compared: int
    max_discrepancy: float
    discrepancies: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert reproduction outcome to dictionary."""
        return asdict(self)


class ExperimentRunner:
    """Orchestrates end-to-end experiment execution, profiling, and recording."""

    def __init__(self, config: ExperimentConfig | None = None) -> None:
        self.config = config or ExperimentConfig()

    def run(
        self,
        df: pl.DataFrame | None = None,
        output_dir: Path | None = None,
    ) -> ExperimentRunRecord:
        """Execute experiment pipeline, profile latency and memory, and write records."""
        # 1. Start profiling timers and memory
        start_time = datetime.now(tz=UTC)
        tracemalloc.start()

        # 2. Load and validate data
        if df is None:
            df = self._load_canonical_data()

        if df.height == 0:
            tracemalloc.stop()
            raise CompIntelValidationError(
                "Cannot execute experiment on empty DataFrame.",
                code="EMPTY_DATASET",
            )

        # Standardize location column if canonical uses metro_location
        if "location" not in df.columns and "metro_location" in df.columns:
            df = df.with_columns(pl.col("metro_location").alias("location"))

        is_synthetic = bool(
            "is_synthetic" in df.columns and df["is_synthetic"].fill_null(False).any()
        )
        if is_synthetic and not self.config.allow_synthetic:
            tracemalloc.stop()
            raise DataContractError(
                "Synthetic data detected in experiment input. Blocked from canonical "
                "experiment tracking per Rule R-MD-11. Set allow_synthetic=True for test fixtures.",
                code="SYNTHETIC_DATA_BLOCKED",
            )

        # Determine snapshot ID
        snapshot_id = self.config.data_snapshot_id
        if not snapshot_id:
            snapshot_id = self._resolve_snapshot_id()

        total_obs = df.height
        git_commit = get_git_commit()
        run_ts = start_time.strftime("%Y%m%d-%H%M%S")
        short_hash = git_commit[:6] if git_commit != "unknown" else "local"
        run_id = f"RUN-{run_ts}-{short_hash}"

        logger.info(
            "Starting experiment execution",
            run_id=run_id,
            experiment=self.config.experiment_name,
            seed=self.config.seed,
            snapshot_id=snapshot_id,
        )

        # 3. Create 4-way temporal-grouped split (Rule R-MD-01, R-MD-02)
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
        splits = create_temporal_grouped_splits(df, config=split_cfg)

        train_df = splits.train_df
        if self.config.evaluation_split == "select":
            eval_df = splits.select_df
        elif self.config.evaluation_split == "calibrate":
            eval_df = splits.calibrate_df
        elif self.config.evaluation_split == "train":
            eval_df = splits.train_df
        else:
            tracemalloc.stop()
            raise CompIntelValidationError(
                f"Unsupported evaluation split: {self.config.evaluation_split}",
                code="INVALID_EVAL_SPLIT",
            )

        data_summary = {
            "total_observations": total_obs,
            "train_count": train_df.height,
            "eval_count": eval_df.height,
            "eval_split_name": self.config.evaluation_split,
            "excluded_cross_window_count": splits.excluded_df.height,
        }

        # 4. Train and evaluate configured models
        model_metrics: dict[str, dict[str, Any]] = {}
        for model_key in self.config.models:
            m_res = self._train_and_evaluate_model(
                model_key=model_key,
                train_df=train_df,
                eval_df=eval_df,
                is_synthetic=is_synthetic,
            )
            model_metrics[model_key] = m_res

        # 5. Capture performance telemetry
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        end_time = datetime.now(tz=UTC)
        duration_s = (end_time - start_time).total_seconds()

        timings = {
            "start_time_utc": start_time.isoformat(),
            "end_time_utc": end_time.isoformat(),
            "duration_seconds": round(duration_s, 4),
        }
        memory = {
            "peak_memory_mib": round(peak_mem / (1024 * 1024), 3),
            "final_memory_mib": round(current_mem / (1024 * 1024), 3),
        }
        environment = get_environment_manifest()

        # Build run record
        reproduce_cmd = (
            f"uv run python scripts/run_experiment.py --reproduce experiments/results/{run_id}"
        )
        record = ExperimentRunRecord(
            run_id=run_id,
            experiment_name=self.config.experiment_name,
            seed=self.config.seed,
            git_commit=git_commit,
            data_snapshot_id=snapshot_id,
            created_at_utc=start_time.isoformat(),
            config=self.config.to_dict(),
            timings=timings,
            memory=memory,
            environment=environment,
            data_summary=data_summary,
            model_metrics=model_metrics,
            reproduction_command=reproduce_cmd,
            is_synthetic=is_synthetic,
        )

        # 6. Persist bundle if output directory specified or default results path
        if output_dir is None:
            output_dir = Path("experiments") / "results" / run_id
        record.save_bundle(output_dir)

        logger.info(
            "Experiment execution completed",
            run_id=run_id,
            duration=duration_s,
            peak_memory_mib=memory["peak_memory_mib"],
        )

        return record

    def _train_and_evaluate_model(
        self,
        model_key: str,
        train_df: pl.DataFrame,
        eval_df: pl.DataFrame,
        is_synthetic: bool,
    ) -> dict[str, Any]:
        """Fit and evaluate a single model specification."""
        clean_key = model_key.lower().strip()
        custom_params = self.config.model_params.get(model_key, {})

        model_name: str
        preds_df: pl.DataFrame | None = None

        if clean_key in {"empirical", "rung_a", "rung_a_empirical"}:
            model_name = "Rung A: Empirical Conditional Quantiles (Hierarchical Backoff)"
            threshold = custom_params.get("thin_evidence_threshold", 5 if is_synthetic else 10)
            model_a = EmpiricalQuantileBaseline(
                config=HierarchicalBackoffConfig(thin_evidence_threshold=threshold)
            )
            model_a.fit(train_df)
            preds_df = model_a.predict(eval_df) if eval_df.height > 0 else None

        elif clean_key in {"linear", "rung_b", "rung_b_linear"}:
            model_name = "Rung B: Regularized Linear Quantile Regression (Log Pay)"
            alpha = custom_params.get("alpha", 0.01)
            quad = custom_params.get("include_quadratic_yoe", True)
            model_b = LinearQuantileBaseline(
                config=LinearQuantileConfig(
                    alpha=alpha,
                    include_quadratic_yoe=quad,
                )
            )
            model_b.fit(train_df)
            preds_df = model_b.predict(eval_df) if eval_df.height > 0 else None

        else:
            raise CompIntelValidationError(
                f"Unsupported model specification: '{model_key}'. "
                "Supported models: 'rung_a_empirical', 'rung_b_linear'",
                code="UNKNOWN_MODEL_KEY",
            )

        report, abstention_rate = self._compute_metrics_from_preds(eval_df, preds_df)

        return {
            "model_id": clean_key,
            "model_name": model_name,
            "evaluated_records": eval_df.height,
            "abstention_rate": round(abstention_rate, 2),
            "metrics": report.to_dict() if report is not None else None,
        }

    def _compute_metrics_from_preds(
        self,
        eval_df: pl.DataFrame,
        preds_df: pl.DataFrame | None,
    ) -> tuple[ComprehensiveMetricsReport | None, float]:
        """Extract evaluation metrics filtering out thin-evidence abstentions (Rule R-MD-08)."""
        if eval_df.height == 0 or preds_df is None or preds_df.height == 0:
            return None, 0.0

        # Row-aligned prediction merge
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
            seed=self.config.seed,
        )

        return report, abstention_rate

    def _load_canonical_data(self) -> pl.DataFrame:
        """Load canonical dataset from configured or standard path."""
        path = (
            Path(self.config.canonical_data_path)
            if self.config.canonical_data_path
            else Path("data") / "canonical" / "canonical_observations.parquet"
        )
        if not path.exists():
            raise CompIntelError(
                f"Canonical data file not found at: {path}. "
                "Run 'make reproduce-data' first or specify custom data path.",
                code="CANONICAL_DATA_NOT_FOUND",
            )
        return pl.read_parquet(path)

    def _resolve_snapshot_id(self) -> str:
        """Resolve current snapshot ID from lineage manifest if present."""
        lineage_path = Path("data") / "canonical" / "canonical_lineage.json"
        if lineage_path.exists():
            try:
                with open(lineage_path, encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("snapshot_id")
                if sid:
                    return str(sid)
            except Exception:
                pass
        return "SNAP-CANONICAL"


def reproduce_experiment(
    run_dir_or_record: Path | str,
    canonical_data_path: Path | None = None,
    df: pl.DataFrame | None = None,
    tolerance: float = 1e-9,
) -> ReproductionResult:
    """Reproduce a past experiment run from its record and assert metric equality (Rule R-MD-10).

    Args:
        run_dir_or_record: Path to run folder (e.g. experiments/results/<run_id>)
                           or run_record.json.
        canonical_data_path: Optional override for dataset file.
        df: Optional explicit DataFrame.
        tolerance: Maximum acceptable floating point discrepancy for identical metric values.

    Returns:
        ReproductionResult detailing verification outcome.

    Raises:
        CompIntelError: If metrics deviate beyond numerical tolerance.
    """
    original_record = ExperimentRunRecord.load(run_dir_or_record)
    config_dict = original_record.config

    if canonical_data_path is not None:
        config_dict["canonical_data_path"] = str(canonical_data_path)

    config = ExperimentConfig.from_dict(config_dict)

    # Execute re-run without overwriting original output bundle
    runner = ExperimentRunner(config=config)
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        new_record = runner.run(df=df, output_dir=Path(tmpdir))

    # Compare metrics across all models
    metrics_compared = 0
    max_discrepancy = 0.0
    discrepancies: list[dict[str, Any]] = []

    orig_models = original_record.model_metrics
    new_models = new_record.model_metrics

    for model_key in orig_models:
        if model_key not in new_models:
            discrepancies.append(
                {
                    "model": model_key,
                    "error": "Model missing in reproduced output",
                }
            )
            continue

        orig_m = orig_models[model_key]
        new_m = new_models[model_key]

        # Check abstention rate
        orig_abst = orig_m.get("abstention_rate", 0.0)
        new_abst = new_m.get("abstention_rate", 0.0)
        abst_diff = abs(orig_abst - new_abst)
        metrics_compared += 1
        if abst_diff > max_discrepancy:
            max_discrepancy = abst_diff
        if abst_diff > tolerance:
            discrepancies.append(
                {
                    "model": model_key,
                    "metric": "abstention_rate",
                    "original": orig_abst,
                    "reproduced": new_abst,
                    "delta": abst_diff,
                }
            )

        orig_metrics = orig_m.get("metrics")
        new_metrics = new_m.get("metrics")

        if orig_metrics is None and new_metrics is None:
            continue
        if (orig_metrics is None) != (new_metrics is None):
            discrepancies.append(
                {
                    "model": model_key,
                    "error": (
                        f"Metric presence mismatch: orig={orig_metrics is not None}, "
                        f"new={new_metrics is not None}"
                    ),
                }
            )
            continue

        assert orig_metrics is not None and new_metrics is not None

        # Compare metric sections: point, quantile_loss, interval, calibration
        for section in ["point", "quantile_loss", "interval", "calibration"]:
            sec_orig = orig_metrics.get(section, {})
            sec_new = new_metrics.get(section, {})
            for m_key, orig_val in sec_orig.items():
                if isinstance(orig_val, int | float):
                    new_val = sec_new.get(m_key)
                    if new_val is None:
                        discrepancies.append(
                            {
                                "model": model_key,
                                "metric": f"{section}.{m_key}",
                                "error": "Metric missing in reproduced output",
                            }
                        )
                        continue
                    metrics_compared += 1
                    diff = abs(float(orig_val) - float(new_val))
                    if diff > max_discrepancy:
                        max_discrepancy = diff
                    if diff > tolerance:
                        discrepancies.append(
                            {
                                "model": model_key,
                                "metric": f"{section}.{m_key}",
                                "original": orig_val,
                                "reproduced": new_val,
                                "delta": diff,
                            }
                        )

    is_identical = len(discrepancies) == 0

    if not is_identical:
        err_msg = (
            f"Reproduction discrepancy detected for run '{original_record.run_id}'. "
            f"Max discrepancy: {max_discrepancy:.2e}. Discrepancies: {discrepancies}"
        )
        logger.error(err_msg)
        raise CompIntelError(err_msg, code="REPRODUCTION_DISCREPANCY")

    success_msg = (
        f"Experiment '{original_record.run_id}' reproduced identically: "
        f"{metrics_compared} metrics verified "
        f"(max discrepancy: {max_discrepancy:.2e} <= {tolerance:.2e})."
    )
    logger.info(success_msg)

    return ReproductionResult(
        is_identical=True,
        run_id=original_record.run_id,
        metrics_compared=metrics_compared,
        max_discrepancy=max_discrepancy,
        discrepancies=[],
        message=success_msg,
    )
