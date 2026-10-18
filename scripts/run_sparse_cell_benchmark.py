#!/usr/bin/env python3
"""CLI runner for Hierarchical Bayes vs Conformal GBM sparse cell benchmark (T6.07, EXP-05).

Adheres to:
- PRD Section 5 & FR-04, FR-05: Sparse cell regimes and hierarchical shrinkage.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with bootstrap confidence intervals.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
- Rule R-UQ-06: Prior sensitivity analysis across cell bands.
- Rule R-DA-10: Anonymization floor k_min >= 5.

Usage:
    uv run python scripts/run_sparse_cell_benchmark.py
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
from compintel.evaluation.sparse_cell_benchmark import evaluate_and_save_sparse_cell_benchmark


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Hierarchical Bayes vs Conformal GBM Sparse Cell Benchmark (EXP-05)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/hierarchical-vs-gbm-sparse-cells-exp05.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/hierarchical_vs_gbm_sparse_v1.json",
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
    print("  ArthaIQ -- Hierarchical Bayes vs Conformal GBM Benchmark (T6.07, EXP-05)")
    print("  PRD Sec 5 | Rules R-MD-01, R-MD-02, R-MD-05, R-MD-11, R-UQ-01, R-UQ-05, R-UQ-06")
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
        report = evaluate_and_save_sparse_cell_benchmark(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\nSparse Cell Benchmark Complete!")
        print(f"Evaluated Observations  : {report.n_eval_observations:,}")
        print(f"Architectural Verdict   : {report.verdict.value}")

        print("\nCell Density Regime Comparison (Rung C vs Rung F):")
        for comp in report.band_comparisons:
            ci_str = f"[{comp.delta_pinball_ci_lower:+.3f}, {comp.delta_pinball_ci_upper:+.3f}]"
            print(
                f"\n  Band: {comp.band.value:12s} (N = {comp.n_eval_samples}, "
                f"Unique Cells = {comp.n_unique_cells})"
            )
            print(
                f"    Rung C (Hierarchical) : Pinball = {comp.rung_c_metrics.mean_pinball_loss:.3f} LPA | "
                f"MAE = {comp.rung_c_metrics.mae:.2f} LPA | "
                f"Cov = {comp.rung_c_metrics.empirical_coverage * 100:.1f}% | "
                f"Width = {comp.rung_c_metrics.mean_interval_width:.2f} LPA"
            )
            print(
                f"    Rung F (Conformal GBM): Pinball = {comp.rung_f_metrics.mean_pinball_loss:.3f} LPA | "
                f"MAE = {comp.rung_f_metrics.mae:.2f} LPA | "
                f"Cov = {comp.rung_f_metrics.empirical_coverage * 100:.1f}% | "
                f"Width = {comp.rung_f_metrics.mean_interval_width:.2f} LPA"
            )
            print(
                f"    Delta Pinball (C - F) : {comp.delta_pinball:+.3f} LPA (95% CI: {ci_str}) | "
                f"Width Ratio = {comp.width_ratio:.3f}"
            )
            print(f"    Winner Architecture   : {comp.superior_architecture}")

        print("\nPrior Sensitivity Summary (Rule R-UQ-06):")
        for sens in report.prior_sensitivities:
            status = "ROBUST (PASS)" if sens.is_stable else "FRAGILE (FAIL)"
            print(
                f"  - {sens.band.value:12s}: Max P50 Shift = {sens.max_p50_shift:.2f} LPA | "
                f"Min Rank Rho = {sens.min_rank_correlation:.4f} | Status = {status}"
            )

        print("\nArchitectural Routing Directive:")
        print(f"  {report.routing_directive}")

        print("\nReports successfully saved to:")
        print(f"  - Markdown : {args.output_md}")
        print(f"  - JSON     : {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Sparse cell benchmark failed: {err}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
