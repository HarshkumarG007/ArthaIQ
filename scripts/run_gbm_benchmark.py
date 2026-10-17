"""Command-line script for executing Rung D benchmark and baseline comparison (Task T5.01b).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal dataset splitting.
- Rule R-MD-02: Final test set is isolated, untouched, and locked for make final-eval.
  Rung D evaluation evaluates strictly on dev pool partitions ('select' or 'calibrate').
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-05: Mandatory evaluation metrics: MAE, MdAE, MAPE, MdAPE, RMSE, bootstrap CIs,
  slices, and abstention rates.
- Rule R-MD-06: Log-pay target transformation and nominal INR LPA output.
- Rule R-MD-08: Thin-evidence abstention reporting per model and per slice.
- Rule R-MD-10: Detailed execution logging of timings, seeds, and peak memory.
- Rule R-MD-11: Synthetic test data blocked by default from canonical reports.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from compintel.errors import CompIntelError
from compintel.evaluation.gbm_report import (
    GBMBenchmarkReportConfig,
    GBMBenchmarkReportGenerator,
)
from compintel.logging import configure_logging, get_logger

logger = get_logger("scripts.run_gbm_benchmark")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for Rung D benchmark."""
    parser = argparse.ArgumentParser(
        description="Run CompIntel Rung D GBM Benchmark and Baseline Comparison (Task T5.01b)."
    )
    parser.add_argument(
        "--canonical-path",
        type=Path,
        default=Path("data/canonical/canonical_observations.parquet"),
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("experiments/results/rung_d_report_v1.md"),
        help="Destination path for Markdown Rung D benchmark report.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("experiments/results/rung_d_report_v1.json"),
        help="Destination path for JSON structured metrics.",
    )
    parser.add_argument(
        "--snapshot-id",
        type=str,
        default="SNAP-1FF34A8E9633",
        help="Canonical dataset snapshot identifier.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic evaluation and bootstrap.",
    )
    parser.add_argument(
        "--split",
        type=str,
        choices=["select", "calibrate"],
        default="select",
        help="Dev partition to evaluate ('select' or 'calibrate'). Locked 'test' is prohibited.",
    )
    parser.add_argument(
        "--n-cv-folds",
        type=int,
        default=3,
        help="Number of grouped-temporal expanding-window cross-validation folds on dev pool.",
    )
    parser.add_argument(
        "--bootstrap-resamples",
        type=int,
        default=500,
        help="Number of bootstrap resamples for confidence intervals (Rule R-UQ-01).",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Allow evaluation on synthetic fixture data (Rule R-MD-11).",
    )
    return parser.parse_args()


def main() -> int:
    """Execute Rung D benchmark evaluation."""
    configure_logging()
    args = parse_args()

    logger.info(
        "Starting Rung D GBM benchmark execution",
        canonical_path=str(args.canonical_path),
        output_md=str(args.output_md),
        output_json=str(args.output_json),
        split=args.split,
        seed=args.seed,
        n_cv_folds=args.n_cv_folds,
    )

    if not args.canonical_path.exists():
        logger.error(
            "Canonical observations file not found",
            canonical_path=str(args.canonical_path),
        )
        print(
            f"ERROR: Canonical observations not found at '{args.canonical_path}'.\n"
            "Run 'make reproduce-data' first or pass --canonical-path.",
            file=sys.stderr,
        )
        return 1

    try:
        df = pl.read_parquet(args.canonical_path)
    except Exception as exc:
        logger.error(
            "Failed to read canonical observations",
            path=str(args.canonical_path),
            error=str(exc),
        )
        print(f"ERROR: Failed to read parquet file: {exc}", file=sys.stderr)
        return 1

    config = GBMBenchmarkReportConfig(
        snapshot_id=args.snapshot_id,
        random_seed=args.seed,
        evaluation_split=args.split,
        n_cv_folds=args.n_cv_folds,
        bootstrap_resamples=args.bootstrap_resamples,
        allow_synthetic=args.allow_synthetic,
    )

    generator = GBMBenchmarkReportGenerator(config=config)

    try:
        report = generator.generate(df, snapshot_id=args.snapshot_id)
        report.save(output_md=args.output_md, output_json=args.output_json)
    except CompIntelError as exc:
        logger.error("Rung D evaluation failed with CompIntel error", error=str(exc))
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error during Rung D benchmark execution")
        print(f"FAILED (Unexpected): {exc}", file=sys.stderr)
        return 1

    print("\n" + "=" * 80)
    print(report.to_markdown())
    print("=" * 80 + "\n")

    logger.info(
        "Rung D benchmark execution completed successfully",
        report_id=report.report_id,
        designated_model=report.champion_recommendation.get("designated_model"),
        verdict=report.champion_recommendation.get("verdict"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
