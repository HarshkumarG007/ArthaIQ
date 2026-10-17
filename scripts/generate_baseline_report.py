"""Command-line script for generating baseline evaluation report (Task T4.08, Rule R-MD-05).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal dataset splitting.
- Rule R-MD-02: Final test set is isolated, untouched, and locked for make final-eval.
  Baseline report evaluates strictly on dev partitions ('select' or 'calibrate').
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-05: Mandatory baseline evaluation metrics with bootstrap intervals and slices.
- Rule R-MD-08: Thin-evidence abstention reporting per model and per slice.
- Rule R-MD-11: Synthetic test data blocked by default from canonical reports.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from compintel.errors import CompIntelError
from compintel.evaluation.baseline_report import (
    BaselineReportConfig,
    BaselineReportGenerator,
)
from compintel.logging import configure_logging, get_logger

logger = get_logger("scripts.generate_baseline_report")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate CompIntel Baseline Evaluation Report (Task T4.08, Rule R-MD-05)."
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
        default=Path("experiments/results/baseline_report_v1.md"),
        help="Destination path for Markdown baseline report.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("experiments/results/baseline_report_v1.json"),
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
    """Execute baseline evaluation report generation."""
    configure_logging()
    args = parse_args()

    logger.info(
        "Starting baseline evaluation report generation",
        canonical_path=str(args.canonical_path),
        output_md=str(args.output_md),
        output_json=str(args.output_json),
        split=args.split,
        seed=args.seed,
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

    config = BaselineReportConfig(
        snapshot_id=args.snapshot_id,
        random_seed=args.seed,
        evaluation_split=args.split,
        bootstrap_resamples=args.bootstrap_resamples,
        allow_synthetic=args.allow_synthetic,
    )

    generator = BaselineReportGenerator(config=config)

    try:
        report = generator.generate(df, snapshot_id=args.snapshot_id)
        report.save(output_md=args.output_md, output_json=args.output_json)
    except CompIntelError as exc:
        logger.error("Baseline evaluation failed with CompIntel error", error=str(exc))
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error during baseline report generation")
        print(f"FAILED (Unexpected): {exc}", file=sys.stderr)
        return 1

    print("\n" + "=" * 80)
    print(report.to_markdown())
    print("=" * 80 + "\n")

    logger.info(
        "Baseline evaluation report generation completed successfully",
        report_id=report.report_id,
        champion=report.champion_recommendation.get("champion_model"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
