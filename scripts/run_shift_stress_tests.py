#!/usr/bin/env python3
"""CLI script to run shift stress tests across temporal, geographic, and rare cells (EXP-03).

Usage:
    uv run python scripts/run_shift_stress_tests.py
        [--canonical-path <path>]
        [--output-md <path>]
        [--output-json <path>]
        [--split <select|calibrate>]
        [--n-bootstrap <int>]
        [--seed <int>]
        [--allow-synthetic]
"""

from __future__ import annotations

import argparse
import sys

from compintel.errors import CompIntelError
from compintel.evaluation.shift_stress import evaluate_and_save_shift_stress


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run shift stress tests: temporal, geographic, rare cells (EXP-03)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet.",
    )
    parser.add_argument(
        "--output-md",
        default="experiments/results/shift_stress_tests_v1.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/shift_stress_tests_v1.json",
        help="Output JSON summary path.",
    )
    parser.add_argument(
        "--split",
        default="select",
        choices=["select", "calibrate"],
        help="Development split to evaluate on (test is strictly locked).",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=1000,
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
        help="Allow synthetic data (test fixtures only, Rule R-MD-11).",
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI execution routine."""
    args = parse_args()
    print("=" * 70)
    print("  ArthaIQ -- Shift Stress Testing & Hypothesis EXP-03 Evaluation")
    print("  Rule R-UQ-04 | Pre-Registered Hypothesis EXP-03")
    print("=" * 70)
    print(f"Canonical path   : {args.canonical_path}")
    print(f"Evaluation split : {args.split}")
    print(f"Bootstrap rounds : {args.n_bootstrap}")
    print(f"Output MD        : {args.output_md}")
    print(f"Output JSON      : {args.output_json}")
    print(f"Allow synthetic  : {args.allow_synthetic}")
    print("-" * 70)

    try:
        report = evaluate_and_save_shift_stress(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )
        print("\nShift Stress Testing Complete!")
        print(f"EXP-03 Verdict: {report.temporal_shift.exp03_verdict}")
        print(f"Recalibration Cadence: {report.temporal_shift.recommended_recalibration_cadence}")
        print(f"Executive Summary: {report.executive_summary}")
        print("\nReports saved to:")
        print(f"  - {args.output_md}")
        print(f"  - {args.output_json}")
        return 0
    except CompIntelError as err:
        print(f"\n[ERROR] Shift stress evaluation failed: {err}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
