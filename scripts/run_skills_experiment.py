#!/usr/bin/env python3
"""CLI runner to execute Skills Feature Modeling Experiment under EXP-09 (Task T7.02).

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and skills capability modeling.
- CHARTER-EXP-09: experiments/configs/charters/charter_exp09_skills_embeddings.yaml.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-04: Pipelines fitted inside training folds only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Objective business model tiers and pre-registered experiment charters.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_skills_experiment.py
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
from compintel.evaluation.skills_embeddings_experiment import evaluate_and_save_skills_experiment


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Skills Feature Modeling Experiment (EXP-09): Taxonomy & TF-IDF vs Sentence Embeddings on CPU."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/skills-embeddings-exp09.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/skills_embeddings_exp09.json",
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
    """Execute skills modeling experiment CLI."""
    args = parse_args()

    print("================================================================================")
    print(" ArthaIQ -- Skills Feature Modeling Experiment (EXP-09, Task T7.02)")
    print("================================================================================")
    print(f"Canonical Path:     {args.canonical_path}")
    print(f"Evaluation Split:   {args.split} (Dev partition)")
    print(f"Bootstrap Samples:  {args.n_resamples}")
    print(f"Random Seed:        {args.seed}")
    print(f"Allow Synthetic:    {args.allow_synthetic}")
    print("--------------------------------------------------------------------------------")

    try:
        report = evaluate_and_save_skills_experiment(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\n[+] Skills Experiment EXP-09 Completed Successfully!")
        print(f"    Report ID:           {report.report_id}")
        print(f"    Evaluated Rows:      {report.n_eval_observations}")
        print(f"    Overall Verdict:     {report.overall_verdict.value}")
        print(f"    Markdown Output:     {args.output_md}")
        print(f"    JSON Output:         {args.output_json}")

        print("\n--- Comparative Matrix ---")
        base_pb = report.baseline_metrics.mean_pinball_loss
        print(
            f"Baseline Champion:      Pinball = {base_pb:.3f} LPA, p95 Latency = {report.baseline_metrics.p95_latency_ms:.2f} ms"
        )
        for d in report.deltas:
            sig_flag = "SIGNIFICANT" if d.is_statistically_significant else "NOT_SIGNIFICANT"
            print(
                f"{d.variant_name:30s}: Delta = {d.delta_mean_pinball:+.3f} LPA "
                f"[{d.pinball_ci_lower:+.3f}, {d.pinball_ci_upper:+.3f}] ({sig_flag}) -> {d.verdict.value}"
            )

        return 0

    except CompIntelError as e:
        print(f"\n[!] COMPINTEL ERROR: {e.message}", file=sys.stderr)
        if e.details:
            print(f"    Details: {e.details}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[!] UNEXPECTED FATAL ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
