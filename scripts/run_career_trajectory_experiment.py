#!/usr/bin/env python3
"""CLI runner to execute Career Trajectory Modeling Experiment under Charter EXP-08 / Task T7.03.

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and career trajectory modeling.
- CHARTER-EXP-08: experiments/configs/charters/charter_exp08_career_trajectory.yaml.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-03: Zero lookahead; career velocity computed strictly as-of observation date.
- Rule R-MD-04: Feature transformations fitted inside training folds only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Objective business model tiers and pre-registered experiment charters.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_career_trajectory_experiment.py
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
from compintel.evaluation.career_trajectory_experiment import evaluate_and_save_career_trajectory


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Career Trajectory Modeling Experiment (T7.03): Tenure & Velocity Features vs Baseline."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/career-trajectory.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/career_trajectory_exp_v1.json",
        help="Output path for structured JSON evaluation results.",
    )
    parser.add_argument(
        "--split",
        default="select",
        choices=["select", "calibrate"],
        help="Evaluation split to benchmark ('select' or 'calibrate'). Test set is strictly locked.",
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
        default=False,
        help="Explicitly permit synthetic data execution (Rule R-MD-11).",
    )
    return parser.parse_args()


def main() -> int:
    """Execute career trajectory experiment CLI."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()

    print("================================================================================")
    print(" ArthaIQ -- Career Trajectory Modeling Experiment (EXP-08, Task T7.03)")
    print("================================================================================")
    print(f"Canonical Path:     {args.canonical_path}")
    print(f"Evaluation Split:   {args.split} (Dev partition)")
    print(f"Bootstrap Samples:  {args.n_resamples}")
    print(f"Random Seed:        {args.seed}")
    print(f"Allow Synthetic:    {args.allow_synthetic}")
    print("--------------------------------------------------------------------------------")

    try:
        report = evaluate_and_save_career_trajectory(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\n=== EXPERIMENT EXECUTION COMPLETED SUCCESSFULLY ===")
        print(f"Report ID:          {report.report_id}")
        print(f"Charter ID:         {report.charter_id}")
        print(f"Evaluated Records:  {report.n_eval_observations}")
        print(f"Overall Verdict:    {report.overall_verdict.value}")
        print(f"Markdown Output:    {args.output_md}")
        print(f"JSON Output:        {args.output_json}")
        print("\n--- Summary of Variants vs Baseline ---")
        for delta in report.deltas:
            sig_marker = "**" if delta.is_statistically_significant else "ns"
            print(
                f"- {delta.variant_name}: "
                f"dPinball = {delta.delta_mean_pinball:+.4f} LPA "
                f"(95% CI: [{delta.pinball_ci_lower:+.4f}, {delta.pinball_ci_upper:+.4f}] {sig_marker}), "
                f"dMAE = {delta.delta_mae:+.4f} LPA, "
                f"Width Ratio = {delta.width_ratio:.3f}, "
                f"Verdict = {delta.verdict.value}"
            )

        print("\n=== EXECUTIVE SUMMARY ===")
        print(report.executive_summary)
        print("================================================================================\n")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Domain Exception during experiment execution: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[ERROR] Unexpected failure: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
