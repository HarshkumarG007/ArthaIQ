#!/usr/bin/env python3
"""Automated data quality and contract verification script (Task T3.14).

Loads canonical observations, quarantine stores, and lineage manifests, computes
comprehensive data quality metrics, verifies data contracts, and persists audit reports.

Governed by:
- Rule R-DA-04: Mandatory provenance metadata attached to every record.
- Rule R-DA-05: Count reconciliation (Total = Valid + Quarantined, Delta = 0).
- Rule R-DA-06: Deduplication and clustering occur before splits.
- Rule R-DA-07: Privacy governance (zero cleartext PII).
- Rule R-MD-07: Anti-heuristic CTC unbundling.
- Rule R-ER-06: Quarantine halt thresholds.

Usage:
    uv run python scripts/generate_data_quality_report.py [--verify-thresholds]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

# Ensure src/ is importable
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root / "src") not in sys.path:
    sys.path.insert(0, str(repo_root / "src"))


from compintel.errors import DataContractError
from compintel.quality.report import (
    DataQualityReport,
    export_data_quality_report,
    generate_data_quality_report,
)


def run_data_quality_report(
    canonical_path: Path,
    quarantine_path: Path,
    lineage_path: Path,
    output_md: Path,
    output_json: Path,
    verify_thresholds: bool = False,
    halt_threshold: float = 0.999,
) -> DataQualityReport:
    """Run data quality analysis and export reports.

    Raises DataContractError if verification fails when verify_thresholds is True.
    """
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical dataset not found at {canonical_path}")
    if not quarantine_path.exists():
        raise FileNotFoundError(f"Quarantine dataset not found at {quarantine_path}")

    print(f"[ArthaIQ] Loading canonical dataset from {canonical_path}...")
    canonical_df = pl.read_parquet(canonical_path)

    print(f"[ArthaIQ] Loading quarantine dataset from {quarantine_path}...")
    quarantine_df = pl.read_parquet(quarantine_path)

    print("[ArthaIQ] Evaluating data quality metrics and contract invariants...")
    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
        lineage_path=lineage_path if lineage_path.exists() else None,
        halt_threshold=halt_threshold,
    )

    print(f"[ArthaIQ] Exporting Markdown audit report to {output_md}...")
    print(f"[ArthaIQ] Exporting JSON metrics to {output_json}...")
    export_data_quality_report(
        report=report,
        output_md_path=output_md,
        output_json_path=output_json,
    )

    print("=" * 70)
    print("ARTHAIQ DATA QUALITY & CONTRACT AUDIT SUMMARY (T3.14)")
    print("=" * 70)
    print(f"Snapshot ID:            {report.snapshot_id}")
    print(f"Total Evaluated:        {report.total_evaluated:,}")
    print(f"Valid Records:          {report.valid_records:,}")
    print(f"Quarantined Records:    {report.quarantined_records:,}")
    print(f"Quarantine Rate:        {report.quarantine_rate * 100:.2f}%")
    print(
        f"Reconciliation Delta:   {report.reconciliation_delta} (Passed: {report.reconciliation_passed})"
    )
    print("-" * 70)
    print("Contract Checks:")
    for rule, passed in report.contract_checks.items():
        symbol = "[PASS]" if passed else "[FAIL]"
        print(f"  {symbol} {rule}")
    print("-" * 70)
    print(f"OVERALL STATUS:         {report.overall_status}")
    print("=" * 70)

    if verify_thresholds and report.overall_status != "PASSED":
        failed_checks = [k for k, v in report.contract_checks.items() if not v]
        raise DataContractError(
            code="CONTRACT_THRESHOLD_BREACH",
            message=f"Data quality contracts breached: {failed_checks}. Overall status: {report.overall_status}",
            details={
                "contract_checks": report.contract_checks,
                "quarantine_rate": report.quarantine_rate,
            },
        )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CompIntel automated data quality reporting and contract verification."
    )
    parser.add_argument(
        "--canonical-path",
        type=Path,
        default=repo_root / "data" / "canonical" / "canonical_observations.parquet",
        help="Path to canonical observations parquet.",
    )
    parser.add_argument(
        "--quarantine-path",
        type=Path,
        default=repo_root / "data" / "quarantine" / "quarantine_records.parquet",
        help="Path to quarantine records parquet.",
    )
    parser.add_argument(
        "--lineage-path",
        type=Path,
        default=repo_root / "data" / "canonical" / "canonical_lineage.json",
        help="Path to canonical lineage JSON.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=repo_root / "docs" / "quality" / "data-quality-report.md",
        help="Path for exported Markdown audit report.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=repo_root / "experiments" / "results" / "data_quality_report.json",
        help="Path for exported JSON report.",
    )
    parser.add_argument(
        "--verify-thresholds",
        action="store_true",
        help="Fail with exit code 1 if any contract or threshold check fails.",
    )
    parser.add_argument(
        "--halt-threshold",
        type=float,
        default=0.999,
        help="Maximum allowed quarantine rate before failure (default 0.999).",
    )

    args = parser.parse_args()

    try:
        run_data_quality_report(
            canonical_path=args.canonical_path,
            quarantine_path=args.quarantine_path,
            lineage_path=args.lineage_path,
            output_md=args.output_md,
            output_json=args.output_json,
            verify_thresholds=args.verify_thresholds,
            halt_threshold=args.halt_threshold,
        )
    except Exception as exc:
        print(f"\n[FATAL] Data contract verification failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
