#!/usr/bin/env python3
"""CLI runner for Staged versus Joint Modelling Analysis (T6.08, EXP-08).

Adheres to:
- PRD Section 5 & FR-05: Progressive disclosure ladder (L0 -> L1 -> L2 -> L3).
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with bootstrap confidence intervals.
- Rule R-MD-06: Log pay target transformation (log guaranteed_cash_annual).
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
- Decision D-010 & Hypothesis EXP-08: Staged versus joint architecture evaluation.

Usage:
    uv run python scripts/run_staging_analysis.py
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
from compintel.evaluation.staging_analysis import evaluate_and_save_staging_analysis


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Staged versus Joint Modelling and Error Propagation Analysis (EXP-08)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/staged-vs-joint-modelling-exp08.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/staged_vs_joint_modelling_v1.json",
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
    print("  ArthaIQ -- Staged vs Joint Modelling & Error Propagation (T6.08, EXP-08)")
    print("  PRD Sec 5 | Rules R-MD-01, R-MD-02, R-MD-05, R-MD-06, R-MD-11, R-UQ-01, R-UQ-05")
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
        report = evaluate_and_save_staging_analysis(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        ci_str = f"[{report.delta_pinball_ci_lower:+.3f}, {report.delta_pinball_ci_upper:+.3f}]"

        print("\nStaging Analysis Complete!")
        print(f"Evaluated Observations  : {report.n_eval_observations:,}")
        print(f"Architectural Verdict   : {report.verdict.value}")

        print("\nHead-to-Head Performance (Level 1 Personalization):")
        print(
            f"  Joint Direct ($M_1$)   : Pinball = {report.joint_metrics.mean_pinball_loss:.3f} LPA | "
            f"MAE = {report.joint_metrics.mae:.2f} LPA | "
            f"Cov = {report.joint_metrics.empirical_coverage * 100:.1f}% | "
            f"Width = {report.joint_metrics.mean_interval_width:.2f} LPA"
        )
        print(
            f"  Staged Cascaded        : Pinball = {report.staged_metrics.mean_pinball_loss:.3f} LPA | "
            f"MAE = {report.staged_metrics.mae:.2f} LPA | "
            f"Cov = {report.staged_metrics.empirical_coverage * 100:.1f}% | "
            f"Width = {report.staged_metrics.mean_interval_width:.2f} LPA"
        )
        print(
            f"  Delta Pinball (S - J)  : {report.delta_pinball:+.3f} LPA (95% CI: {ci_str}) | "
            f"Width Ratio = {report.width_ratio:.3f}"
        )

        print("\nVariance Accumulation Diagnostics (Rule R-UQ-01):")
        print(f"  Stage 0 Variance       : {report.variance_diagnostics.stage_0_variance:.4f}")
        print(f"  Stage 1 Residual Var   : {report.variance_diagnostics.stage_1_variance:.4f}")
        print(f"  Cross-Stage Covariance : {report.variance_diagnostics.covariance_0_1:.4f}")
        print(
            f"  Total Cascade Variance : {report.variance_diagnostics.total_cascade_variance:.4f}"
        )
        print(
            f"  Variance Inflation Fac : {report.variance_diagnostics.variance_inflation_factor:.3f}x"
        )

        print("\nSeniority Classification Ambiguity Stress Test:")
        for res in report.noise_stress_results:
            print(
                f"  Noise {res.noise_rate * 100:.0f}%: "
                f"Joint MAE = {res.joint_mae:.2f} LPA ({res.joint_amplification:.2f}x) | "
                f"Staged MAE = {res.staged_mae:.2f} LPA ({res.staged_amplification:.2f}x) | "
                f"More Resilient = {res.more_resilient_architecture}"
            )

        print("\nArchitectural Routing Directive:")
        print(f"  {report.architectural_directive}")

        print("\nReports successfully saved to:")
        print(f"  - Markdown : {args.output_md}")
        print(f"  - JSON     : {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Staging analysis failed: {err}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
