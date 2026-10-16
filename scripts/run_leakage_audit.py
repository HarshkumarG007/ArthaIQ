"""Command-line script for running EXP-12 leakage and duplicate-inflation audit.

Governed by:
- Rule R-MD-01: Grouped-temporal split hierarchy; random i.i.d. splits prohibited.
- Rule R-MD-02: Isolated final test set; audits operate strictly on dev partitions.
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-04: Adversarial leak detection and leakage audits.
- Rule R-MD-11: Synthetic data flagged and blocked from production benchmark reports.
- Experiment EXP-12: Measure the random-versus-grouped-temporal performance inflation gap.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from compintel.errors import CompIntelError
from compintel.evaluation.inflation import (
    LeakageInflationAuditor,
    LeakageInflationConfig,
)
from compintel.logging import configure_logging, get_logger

logger = get_logger("scripts.run_leakage_audit")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run CompIntel Leakage and Duplicate-Inflation Audit (EXP-12)."
    )
    parser.add_argument(
        "--canonical-path",
        type=Path,
        default=Path("data/canonical/canonical_observations.parquet"),
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("experiments/results/leakage_inflation_audit.json"),
        help="Destination path for JSON audit metrics.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("experiments/results/leakage_inflation_audit.md"),
        help="Destination path for Markdown audit report.",
    )
    parser.add_argument(
        "--snapshot-id",
        type=str,
        default="SNAP-CANONICAL",
        help="Canonical dataset snapshot identifier.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for audit sampling.",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Allow synthetic fixture data strictly for testing plumbing (Rule R-MD-11).",
    )
    parser.add_argument(
        "--bootstrap-ci",
        action="store_true",
        help="Compute bootstrap confidence intervals for primary metrics.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute leakage inflation audit."""
    configure_logging()
    args = parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    canonical_path = args.canonical_path
    if not canonical_path.is_absolute():
        canonical_path = repo_root / canonical_path

    if not canonical_path.exists():
        logger.error(
            "Canonical dataset not found",
            path=str(canonical_path),
            hint="Run 'make reproduce-data' first or pass --allow-synthetic with synthetic fixtures.",
        )
        return 1

    try:
        df = pl.read_parquet(canonical_path)
    except Exception as exc:
        logger.error("Failed to read canonical parquet", error=str(exc))
        return 1

    config = LeakageInflationConfig(
        random_seed=args.seed,
        with_bootstrap_ci=args.bootstrap_ci,
        allow_synthetic=args.allow_synthetic,
    )

    auditor = LeakageInflationAuditor(config=config)

    try:
        report = auditor.audit(df=df, snapshot_id=args.snapshot_id)
    except CompIntelError as err:
        logger.error("Leakage audit failed with contract error", error=str(err), code=err.code)
        return 2

    # Save artifacts
    out_json = args.output_json
    if not out_json.is_absolute():
        out_json = repo_root / out_json
    report.save_json(out_json)
    logger.info("Saved JSON audit report", path=str(out_json))

    out_md = args.output_md
    if not out_md.is_absolute():
        out_md = repo_root / out_md
    report.save_markdown(out_md)
    logger.info("Saved Markdown audit report", path=str(out_md))

    # Print summary to stdout
    print("\n" + "=" * 80)
    print(report.to_markdown())
    print("=" * 80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
