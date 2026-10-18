#!/usr/bin/env python3
"""CLI runner to execute missingness study and evaluate indicator features (Rule R-MD-15, T6.06).

Adheres to:
- PRD Section 5 & FR-05: Progressive disclosure and structured profile sparsity.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; locked test set strictly protected.
- Rule R-MD-05: Standard evaluation metrics with bootstrap confidence intervals.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine.
- Rule R-MD-15: Missingness indicators only where justified by T6.06.
  Missing data is NEVER read as a personal trait.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_missingness_study.py
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
from compintel.evaluation.missingness_study import evaluate_and_save_missingness_study


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Missingness Study & Feature Indicator Policy Evaluation (Rule R-MD-15)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/missingness-policy-r-md-15.md",
        help="Output path for publication-grade Markdown policy report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/missingness_study_v1.json",
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
    print("  ArthaIQ -- Missingness Study & Indicator Policy Evaluation (T6.06)")
    print("  PRD Sec 5 | Rules R-MD-01, R-MD-02, R-MD-05, R-MD-11, R-MD-13, R-MD-15")
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
        report = evaluate_and_save_missingness_study(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\nMissingness Study Complete!")
        print(f"Evaluated Observations  : {report.n_eval_observations:,}")
        print(f"Formal Policy Verdict   : {report.verdict.value}")

        print("\nModel Architecture Comparison:")
        n_m = report.native_model_metrics
        i_m = report.indicator_model_metrics
        print(
            f"  Native (No Inds)  : Pinball = {n_m.mean_pinball_loss:.3f} LPA | "
            f"MAE = {n_m.mae:.2f} LPA | "
            f"Coverage = {n_m.empirical_coverage * 100:.1f}% | "
            f"Width = {n_m.mean_interval_width:.2f} LPA"
        )
        print(
            f"  Augmented (+ Inds): Pinball = {i_m.mean_pinball_loss:.3f} LPA | "
            f"MAE = {i_m.mae:.2f} LPA | "
            f"Coverage = {i_m.empirical_coverage * 100:.1f}% | "
            f"Width = {i_m.mean_interval_width:.2f} LPA"
        )

        ci_str = f"[{report.delta_pinball_ci_lower:+.3f}, {report.delta_pinball_ci_upper:+.3f}]"
        print(
            f"\nDelta Pinball Loss (Ind - Native): {report.delta_pinball:+.3f} LPA (95% CI: {ci_str})"
        )
        print(f"Delta Point MAE                  : {report.delta_mae:+.2f} LPA")
        print(f"Delta Interval Width             : {report.delta_width:+.2f} LPA")

        print("\nOptional Features Audited:")
        for fa in report.feature_audits:
            status = "JUSTIFIED" if fa.is_indicator_justified else "NOT JUSTIFIED"
            print(
                f"  - {fa.feature_id:32s}: Missing = {fa.missing_rate * 100:5.1f}% | Status = {status}"
            )

        print("\nFormal Policy Directive:")
        print(f"  {report.formal_policy_statement}")

        print("\nReports successfully saved to:")
        print(f"  - Markdown : {args.output_md}")
        print(f"  - JSON     : {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Missingness study failed: {err}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
