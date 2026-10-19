#!/usr/bin/env python3
"""CLI runner to execute Employer Feature Modeling Experiment under Charter EXP-10 / Task T7.04.

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and employer representation.
- CHARTER-EXP-10: experiments/configs/charters/charter_exp10_employer_graphs.yaml.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-03: Zero lookahead; employer mobility graph built as-of training cutoff.
- Rule R-MD-04: Target encoding and graph embeddings fitted inside training folds only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charter required; pure CPU compute.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
- Rule R-DA-10: k_min >= 5 anonymization floor on employer clusters and graph nodes.

Usage:
    uv run python scripts/run_employer_graphs_experiment.py
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
from compintel.evaluation.employer_graphs_experiment import (
    evaluate_and_save_employer_graphs_experiment,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Employer Feature Modeling Experiment (T7.04): Simple vs Graph-Based Features."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/employer-graphs-exp10.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/employer_graphs_exp10.json",
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
    """Execute employer feature modeling experiment CLI."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()

    print("================================================================================")
    print(" ArthaIQ -- Employer Feature Modeling Experiment (EXP-10, Task T7.04)")
    print("================================================================================")
    print(f"Canonical Path:     {args.canonical_path}")
    print(f"Evaluation Split:   {args.split} (Rule R-MD-02: Test set locked)")
    print(f"Bootstrap Resamples: {args.n_resamples:,} (Rule R-UQ-01)")
    print(f"Random Seed:        {args.seed}")
    print(f"Allow Synthetic:    {args.allow_synthetic}")
    print(f"Markdown Output:    {args.output_md}")
    print(f"JSON Output:        {args.output_json}")
    print("================================================================================")

    try:
        report = evaluate_and_save_employer_graphs_experiment(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print(f"\nReport ID:          {report.report_id}")
        print(f"Charter ID:         {report.charter_id}")
        print(f"Generated At:       {report.generated_at}")
        print(f"Git Commit:         {report.git_commit[:8]}")
        print(f"Evaluated Rows:     {report.n_eval_observations:,}")
        print(f"Overall Verdict:    {report.overall_verdict.value}")

        print("\nMobility Graph Audit:")
        print(f"  Total Nodes:      {report.graph_audit.n_nodes}")
        print(f"  Total Edges:      {report.graph_audit.n_edges}")
        print(f"  Qualified (>= 3): {report.graph_audit.n_qualified_nodes}/50")
        print(f"  Is Sparse:        {report.graph_audit.is_sparse}")

        print("\nCandidate Performance Summary:")
        print("-" * 88)
        print(
            f"{'Candidate Variant':<38} | {'Feats':<5} | {'Pinball':<8} | {'MAE':<6} | {'Coverage':<8} | {'Width':<8}"
        )
        print("-" * 88)
        for m in [report.baseline_metrics, report.variant_a_metrics, report.variant_b_metrics]:
            print(
                f"{m.variant_name:<38} | {m.n_features:<5} | {m.mean_pinball_loss:<8.3f} | {m.mae:<6.2f} | "
                f"{m.empirical_coverage * 100:<7.1f}% | {m.mean_interval_width:<8.2f}"
            )
        print("-" * 88)

        print("\nPaired Differences vs Champion Baseline (1,000 Bootstrap Resamples):")
        print("-" * 92)
        print(
            f"{'Candidate Variant':<38} | {'Δ Pinball':<10} | {'95% Bootstrap CI':<18} | {'Ratio':<6} | {'Verdict':<8}"
        )
        print("-" * 92)
        for d in report.deltas:
            ci_str = f"[{d.pinball_ci_lower:+.3f}, {d.pinball_ci_upper:+.3f}]"
            print(
                f"{d.variant_name:<38} | {d.delta_mean_pinball:<+10.3f} | {ci_str:<18} | {d.width_ratio:<6.3f} | {d.verdict.value:<8}"
            )
        print("-" * 92)

        print(f"\n[OK] Markdown report written to: {args.output_md}")
        print(f"[OK] JSON results written to:    {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Employer experiment execution failed: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
