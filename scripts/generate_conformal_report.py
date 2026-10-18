"""Command-line script for generating conformal calibration report (Task T5.04).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal dataset splitting.
- Rule R-MD-02: Final test set is isolated, untouched, and locked for make final-eval.
  Conformal calibration report evaluates strictly on dev partitions ('select' or 'calibrate').
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-05: Mandatory evaluation metrics: coverage, width, calibration error, subgroup slices.
- Rule R-MD-08: Thin-evidence support checks. Slices below minimum support (N < 10)
  must be flagged, not hidden.
- Rule R-MD-11: Synthetic test data blocked by default from canonical reports.
- Rule R-UQ-01: Nonparametric percentile bootstrap confidence intervals.
- Rule R-UQ-03: Marginal coverage guarantee under exchangeability.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

from compintel.errors import CompIntelError
from compintel.evaluation.conformal_report import (
    ConformalCalibrationReportGenerator,
    ConformalReportConfig,
)
from compintel.logging import configure_logging, get_logger

logger = get_logger("scripts.generate_conformal_report")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate CompIntel Conformal Calibration Report (Task T5.04, Rules R-MD-05, R-UQ-03)."
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
        default=Path("experiments/results/conformal_report_v1.md"),
        help="Destination path for Markdown conformal calibration report.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("experiments/results/conformal_report_v1.json"),
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
        help="Deterministic random seed for bootstrap and training (Rule R-MD-10).",
    )
    parser.add_argument(
        "--split",
        type=str,
        choices=["select", "calibrate"],
        default="select",
        help="Dev partition to evaluate on (strictly 'select' or 'calibrate'; test is locked).",
    )
    parser.add_argument(
        "--nominal-coverage",
        type=float,
        default=0.80,
        help="Target nominal coverage level in (0.50, 1.00) (default: 0.80).",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Permit synthetic test data (plumbing only; prohibited for production).",
    )
    return parser.parse_args()


def main() -> int:
    """Execute conformal calibration report generation CLI."""
    configure_logging()
    args = parse_args()

    logger.info(
        "starting_conformal_report_generation",
        canonical_path=str(args.canonical_path),
        output_md=str(args.output_md),
        output_json=str(args.output_json),
        split=args.split,
        nominal_coverage=args.nominal_coverage,
    )

    if not args.canonical_path.exists():
        logger.error("canonical_file_not_found", path=str(args.canonical_path))
        print(f"Error: Canonical observations parquet not found at '{args.canonical_path}'.")
        return 1

    try:
        df = pl.read_parquet(args.canonical_path)
    except Exception as e:
        logger.error("failed_to_read_parquet", error=str(e))
        print(f"Error: Failed to read parquet from '{args.canonical_path}': {e}")
        return 1

    config = ConformalReportConfig(
        nominal_coverage=args.nominal_coverage,
        random_seed=args.seed,
        evaluation_split=args.split,
        snapshot_id=args.snapshot_id,
        allow_synthetic=args.allow_synthetic,
    )

    generator = ConformalCalibrationReportGenerator(config=config)

    try:
        report = generator.generate_report(df, snapshot_id=args.snapshot_id)
    except CompIntelError as e:
        logger.error("conformal_report_failed", code=e.code, error=str(e))
        print(f"Evaluation Error ({e.code}): {e}")
        return 1
    except Exception as e:
        logger.error("unexpected_evaluation_error", error=str(e))
        print(f"Unexpected Error: {e}")
        return 1

    # Ensure output directory exists
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    # Render Markdown report
    md_content = report.to_markdown()
    args.output_md.write_text(md_content, encoding="utf-8")
    logger.info("saved_markdown_report", path=str(args.output_md))

    # Serialize JSON report
    json_dict = report.to_dict()
    args.output_json.write_text(json.dumps(json_dict, indent=2), encoding="utf-8")
    logger.info("saved_json_report", path=str(args.output_json))

    cqr_eval = report.models.get("cqr_catboost")
    split_eval = report.models.get("split_conformal_catboost")

    print("\n" + "=" * 78)
    print("  ARTHAIQ CONFORMAL COVERAGE & CALIBRATION REPORT (TASK T5.04)")
    print("=" * 78)
    print(f"Report ID:         {report.report_id}")
    print(f"Evaluation Split:  {report.evaluation_split} (Rule R-MD-02 locked test isolation)")
    print(f"Target Coverage:   {args.nominal_coverage * 100.0:.1f}%")
    if cqr_eval:
        print(
            f"CQR Coverage:      {cqr_eval.overall_coverage * 100.0:.1f}% "
            f"(Mean Width: {cqr_eval.overall_mean_width_lpa:.2f} LPA)"
        )
    if split_eval:
        print(
            f"Split Conformal:   {split_eval.overall_coverage * 100.0:.1f}% "
            f"(Mean Width: {split_eval.overall_mean_width_lpa:.2f} LPA)"
        )
    print(f"Champion Verdict:  {report.champion_verdict.get('champion_model')}")
    print(f"Status:            {report.champion_verdict.get('status')}")
    print(f"Markdown Report:   {args.output_md}")
    print(f"JSON Metrics:      {args.output_json}")
    print("=" * 78 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
