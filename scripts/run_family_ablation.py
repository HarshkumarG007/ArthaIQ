#!/usr/bin/env python3
"""CLI runner to execute feature-family ablation study under EXP-06.

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and feature family evaluation.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Objective business model tiers without proprietary black-box ranks.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine (EXP-07).
- Rule R-MD-15: Missingness invariant.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_family_ablation.py
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
from compintel.evaluation.family_ablation import evaluate_and_save_family_ablation


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Feature-Family Ablation Study (EXP-06) across candidate personalization tiers."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/feature-family-ablations.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/feature_family_ablations_v1.json",
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

    print("=" * 80)
    print("  ArthaIQ -- Feature-Family Ablation Study (EXP-06)")
    print("  PRD Sec 5 | Rules R-MD-01, R-MD-02, R-MD-05, R-MD-09, R-MD-11, R-MD-13, R-MD-15")
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
        report = evaluate_and_save_family_ablation(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\nFeature-Family Ablation Study Complete!")
        print(f"Evaluated Observations  : {report.n_eval_observations:,}")
        l0_m = report.l0_baseline_metrics
        l1_m = report.l1_full_metrics
        print(
            f"  L0 Core Baseline : Pinball = {l0_m.mean_pinball_loss:.3f} LPA | "
            f"Coverage = {l0_m.empirical_coverage * 100:.1f}% | "
            f"Width = {l0_m.mean_interval_width:.2f} LPA"
        )
        print(
            f"  L1 Full Profile  : Pinball = {l1_m.mean_pinball_loss:.3f} LPA | "
            f"Coverage = {l1_m.empirical_coverage * 100:.1f}% | "
            f"Width = {l1_m.mean_interval_width:.2f} LPA"
        )

        print("\nPre-Registered Family Ablation Decisions (EXP-06):")
        print(
            f"{'Family':<32} | {'Keep Thresh':<14} | {'Fwd Delta Pinball (95% CI)':<30} | "
            f"{'Width Ratio':<12} | {'Verdict':<10}"
        )
        print("-" * 106)
        for item in report.family_results:
            ci_str = f"[{item.forward_delta.pinball_ci_lower:+.3f}, {item.forward_delta.pinball_ci_upper:+.3f}]"
            dp_str = f"{item.forward_delta.delta_mean_pinball:+.3f} {ci_str}"
            t_str = f"<= {item.keep_threshold_pinball:+.3f}"
            print(
                f"{item.family_name:<32} | {t_str:<14} | {dp_str:<30} | "
                f"{item.forward_delta.width_ratio:<12.3f} | {item.verdict.value:<10}"
            )

        print("\nExecutive Summary:")
        print(report.overall_summary)

        print("\nReports successfully saved to:")
        print(f"  - Markdown : {args.output_md}")
        print(f"  - JSON     : {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Family ablation evaluation failed: {err}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
