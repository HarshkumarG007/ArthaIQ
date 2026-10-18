#!/usr/bin/env python3
"""CLI runner to execute stage-wise progressive personalization evaluation (L0 to L3).

Adheres to:
- PRD Section 5 & FR-05: Progressive disclosure across feature personalization tiers.
- Rule R-MD-01 / R-MD-02: Dev split evaluation ('select' or 'calibrate'); test set strictly locked.
- Rule R-MD-05: Mandatory evaluation metrics reporting.
- Rule R-MD-13: Compare-Only current pay quarantine (EXP-07).
- Rule R-MD-15: Masked-missingness simulation audit.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_stagewise_evaluation.py
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
from compintel.evaluation.stagewise_evaluation import evaluate_and_save_stagewise_evaluation


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Stage-Wise Progressive Personalization Evaluation across L0 to L3 tiers."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/stagewise-evaluation-l0-l3.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/stagewise_evaluation_v1.json",
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
        default=1000,
        help="Number of bootstrap resamples for paired difference confidence intervals.",
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

    print("=" * 75)
    print("  ArthaIQ -- Stage-Wise Progressive Personalization Evaluation (L0 to L3)")
    print("  PRD Sec 5 | Rules R-MD-01, R-MD-02, R-MD-05, R-MD-13, R-MD-15, R-UQ-01, R-UQ-05")
    print("=" * 75)
    print(f"Canonical path          : {args.canonical_path}")
    print(f"Evaluation split        : {args.split}")
    print(f"Bootstrap resamples     : {args.n_resamples}")
    print(f"Random seed             : {args.seed}")
    print(f"Output Markdown         : {args.output_md}")
    print(f"Output JSON             : {args.output_json}")
    print(f"Allow synthetic         : {args.allow_synthetic}")
    print("-" * 75)

    try:
        report = evaluate_and_save_stagewise_evaluation(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\nStage-Wise Evaluation Complete!")
        print(f"Overall Verdict         : {report.overall_verdict}")
        print(f"Evaluated Observations  : {report.n_eval_observations:,}")
        print("\nPersonalization Level Summary:")
        print(
            f"{'Level':<30} | {'Features':<8} | {'MAE (LPA)':<10} | {'Pinball':<10} | "
            f"{'80% Coverage':<12} | {'Width (LPA)':<12}"
        )
        print("-" * 92)
        for s in report.level_summaries:
            print(
                f"{s.level_name:<30} | {s.n_features:<8} | {s.mae:<10.2f} | "
                f"{s.mean_pinball_loss:<10.3f} | {s.empirical_coverage * 100.0:<11.1f}% | "
                f"{s.mean_interval_width:<12.2f}"
            )

        print("\nPairwise Increment Transitions:")
        print(
            f"{'Transition':<25} | {'Delta Mean Pinball (95% CI)':<30} | "
            f"{'Width Ratio':<12} | {'Verdict':<20}"
        )
        print("-" * 95)
        for inc in report.increment_summaries:
            ci_str = (
                f"[{inc.delta_mean_pinball.ci_lower:+.3f}, {inc.delta_mean_pinball.ci_upper:+.3f}]"
            )
            dp_str = f"{inc.delta_mean_pinball.delta:+.3f} {ci_str}"
            print(
                f"{inc.transition_name:<25} | {dp_str:<30} | "
                f"{inc.width_ratio:<12.3f} | {inc.verdict:<20}"
            )

        print("\nMasked-Missingness Audit (Rule R-MD-15):")
        print(f"Recommendation: {report.masked_missingness_summary.overall_recommendation}")
        print(f"Rationale     : {report.masked_missingness_summary.rationale}")

        print("\nReports successfully saved to:")
        print(f"  - Markdown : {args.output_md}")
        print(f"  - JSON     : {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Stage-wise evaluation failed: {err}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
