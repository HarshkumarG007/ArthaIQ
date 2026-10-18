#!/usr/bin/env python3
"""CLI script to audit abstention policy trade-offs, group disparity, and hypothesis EXP-11.

Usage:
    uv run python scripts/audit_abstention.py
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
from compintel.evaluation.abstention_audit import evaluate_and_save_abstention_audit


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Audit abstention policy trade-offs, group disparity, and evaluate EXP-11."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet.",
    )
    parser.add_argument(
        "--output-md",
        default="experiments/results/abstention_audit_v1.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/abstention_audit_v1.json",
        help="Output JSON summary path.",
    )
    parser.add_argument(
        "--split",
        default="select",
        choices=["select", "calibrate"],
        help="Development split to evaluate on (test is strictly locked per R-MD-02).",
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
    print("  ArthaIQ -- Abstention Policy & Group Disparity Audit (EXP-11)")
    print("  Rule R-UQ-02 / R-UQ-07 | Pre-Registered Hypothesis EXP-11")
    print("=" * 70)
    print(f"Canonical path   : {args.canonical_path}")
    print(f"Evaluation split : {args.split}")
    print(f"Bootstrap rounds : {args.n_bootstrap}")
    print(f"Output MD        : {args.output_md}")
    print(f"Output JSON      : {args.output_json}")
    print(f"Allow synthetic  : {args.allow_synthetic}")
    print("-" * 70)

    try:
        report = evaluate_and_save_abstention_audit(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split=args.split,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )
        s = report.tradeoff_summary
        print("\nAbstention Audit Complete!")
        print(
            f"Overall Abstention Rate  : {s.overall_abstention_rate:.1f}% [{s.overall_abstention_rate_ci[0]:.1f}%, {s.overall_abstention_rate_ci[1]:.1f}%]"
        )
        print(
            f"Answered Requests Coverage: {s.overall_answered_coverage:.1f}% [{s.overall_answered_coverage_ci[0]:.1f}%, {s.overall_answered_coverage_ci[1]:.1f}%]"
        )
        print(
            f"Unconstrained Coverage    : {s.overall_unconstrained_coverage:.1f}% [{s.overall_unconstrained_coverage_ci[0]:.1f}%, {s.overall_unconstrained_coverage_ci[1]:.1f}%]"
        )
        gain_str = (
            f"+{s.coverage_gain_pp:.1f} pp"
            if s.coverage_gain_pp > 0
            else f"{s.coverage_gain_pp:.1f} pp"
        )
        print(f"Coverage Protection Gain  : {gain_str}")
        print(f"EXP-11 Verdict            : {s.exp11_verdict}")
        print(f"Threshold Recommendation  : {s.support_threshold_recommendation}")
        print("\nReports saved to:")
        print(f"  - {args.output_md}")
        print(f"  - {args.output_json}")
        return 0
    except CompIntelError as err:
        print(f"\n[ERROR] Abstention audit evaluation failed: {err}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
