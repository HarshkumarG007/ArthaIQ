#!/usr/bin/env python3
"""CLI runner for Fairness Audit v1: errors, coverage, abstention and data availability (T6.09, EXP-09).

Adheres to:
- PRD Section 16 & Rule 11: Demographic proxy prohibition.
- Rules R-FA-01, R-FA-02, R-FA-03, R-FA-04: Fairness evaluation & legal framing.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with bootstrap confidence intervals.
- Rule R-MD-08: No causal language; statistical associations only.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-12: Zero protected demographic inputs or proxies.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on all metrics.
- Rule R-UQ-02: Abstention is a valid designed outcome.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_fairness_audit.py
        [--canonical-path <path>]
        [--output-md <path>]
        [--output-json <path>]
        [--split <select|calibrate>]
        [--n-resamples <int>]
        [--seed <int>]
        [--allow-synthetic]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from compintel.errors import CompIntelError
from compintel.evaluation.fairness_audit import (
    ParityStatus,
    evaluate_and_save_fairness_audit,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Fairness Audit v1: Prediction parity and data availability across operational groups."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/fairness-audit-v1.md",
        help="Output path for publication-grade Markdown fairness audit report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/fairness_audit_v1.json",
        help="Output path for structured JSON evaluation results.",
    )
    parser.add_argument(
        "--split",
        default="select",
        choices=["select", "calibrate"],
        help="Development split to evaluate on (locked test partition prohibited per R-MD-02).",
    )
    parser.add_argument(
        "--n-resamples",
        type=int,
        default=500,
        help="Number of bootstrap resamples for confidence intervals.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Permit synthetic test data (test fixtures only, Rule R-MD-11).",
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI execution entrypoint."""
    args = parse_args()

    print("=" * 80)
    print("  ArthaIQ -- Fairness Audit v1 (T6.09, EXP-09)")
    print("  PRD Sec 16 | Rules R-FA-01..04, R-MD-01, R-MD-02, R-MD-08, R-MD-11, R-MD-12, R-UQ-01")
    print("=" * 80)
    print(f"Canonical path          : {args.canonical_path}")
    print(f"Evaluation split        : {args.split}")
    print(f"Bootstrap resamples     : {args.n_resamples}")
    print(f"Random seed             : {args.seed}")
    print(f"Output Markdown         : {args.output_md}")
    print(f"Output JSON             : {args.output_json}")
    print(f"Allow synthetic         : {args.allow_synthetic}")
    print("-" * 80)

    try:
        report = evaluate_and_save_fairness_audit(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\nFairness Audit v1 Complete!")
        print(f"Report ID               : {report.report_id}")
        print(f"Total Observations      : {report.n_total_observations:,}")
        print(f"Overall Verdict         : {report.overall_verdict.value}")
        print(
            f"Global Baseline         : Pinball = {report.global_pinball_loss:.3f} LPA | "
            f"MAE = {report.global_mae:.2f} LPA | "
            f"Cov = {report.global_empirical_coverage * 100:.1f}% | "
            f"Abstention = {report.global_abstention_rate * 100:.1f}%"
        )
        print(
            f"Demographic Compliance  : {'PASS (0 prohibited columns)' if report.proxy_compliance.is_compliant else 'FAIL'}"
        )

        print("\nSlice Parity Summary:")
        for audit in report.slice_audits:
            status_icon = (
                "PASS"
                if audit.parity_status == ParityStatus.PASS
                else ("WARN" if audit.parity_status == ParityStatus.WARN else "FAIL")
            )
            print(
                f"  {audit.dimension.value:<18}: {status_icon:<5} | "
                f"Max MAE Ratio = {audit.max_mae_ratio:.3f} | "
                f"Max Cov Gap = {audit.max_coverage_gap:.3f} | "
                f"Max Abs Gap = {audit.max_abstention_gap:.3f} | "
                f"Low-Support = {audit.n_slices_low_support}"
            )
            if audit.failing_slices:
                print(f"    Failing slices: {audit.failing_slices}")

        print(f"\nTotal Gaps & Mitigations: {len(report.gaps_and_mitigations)}")
        for gap in report.gaps_and_mitigations[:5]:
            print(f"  - {gap}")
        if len(report.gaps_and_mitigations) > 5:
            print(f"  ... and {len(report.gaps_and_mitigations) - 5} more (see full report).")

        print("\nReports saved:")
        print(f"  Markdown: {args.output_md}")
        print(f"  JSON    : {args.output_json}")
        print("=" * 80)
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Domain contract failure: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
