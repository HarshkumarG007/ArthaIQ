#!/usr/bin/env python3
"""CLI script to evaluate interval usefulness and verify hypothesis EXP-02 (Rule R-UQ-04).

Usage:
    uv run python scripts/evaluate_interval_usefulness.py
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
from compintel.evaluation.interval_usefulness import evaluate_and_save_interval_usefulness


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate interval usefulness against naive cohort at equal coverage (Rule R-UQ-04, EXP-02)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet.",
    )
    parser.add_argument(
        "--output-md",
        default="experiments/results/interval_usefulness_v1.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/interval_usefulness_v1.json",
        help="Output JSON summary path.",
    )
    parser.add_argument(
        "--split",
        default="select",
        choices=["select", "calibrate"],
        help="Development split to evaluate on (test is locked).",
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
    print("  ArthaIQ -- Interval Usefulness & Hypothesis EXP-02 Evaluation")
    print("  Rule R-UQ-04 | Pre-Registered Hypothesis EXP-02")
    print("=" * 70)
    print(f"Canonical path   : {args.canonical_path}")
    print(f"Evaluation split : {args.split}")
    print(f"Bootstrap rounds : {args.n_bootstrap}")
    print(f"Output MD        : {args.output_md}")
    print(f"Output JSON      : {args.output_json}")
    print(f"Allow synthetic  : {args.allow_synthetic}")
    print("-" * 70)

    try:
        report = evaluate_and_save_interval_usefulness(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            split=args.split,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )
        print("\nInterval Usefulness Evaluation Complete!")
        print(f"EXP-02 Verdict: {report.exp02_verdict}")
        print(f"Summary: {report.exp02_summary}\n")
        print(f"Reports saved to:\n  - {args.output_md}\n  - {args.output_json}")
        return 0
    except CompIntelError as err:
        print(f"\n[ERROR] CompIntel evaluation error: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR]: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
