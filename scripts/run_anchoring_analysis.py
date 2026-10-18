#!/usr/bin/env python3
"""CLI runner to execute current pay anchoring and selection analysis (EXP-07).

Adheres to:
- PRD Section 5 & FR-05: Separation of PT1 (Market) and PT6 (Current Pay Benchmark).
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine until justified by EXP-07.
- Rule R-MD-15: Missingness invariant.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_anchoring_analysis.py
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
from compintel.evaluation.anchoring_analysis import evaluate_and_save_anchoring_analysis


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Current Pay Anchoring & Selection Analysis (EXP-07, Rule R-MD-13)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/current-pay-anchoring-exp07.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/current_pay_anchoring_v1.json",
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
    print("  ArthaIQ -- Current Pay Anchoring & Selection Analysis (EXP-07)")
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
        report = evaluate_and_save_anchoring_analysis(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\nCurrent Pay Anchoring Analysis Complete!")
        print(f"Evaluated Observations  : {report.n_eval_observations:,}")
        print(f"Pre-Registered Verdict  : {report.verdict.value}")

        print("\nModel Performance Reference:")
        u_m = report.unanchored_metrics
        a_m = report.anchored_metrics
        print(
            f"  $M_{{profile}}$  : Pinball = {u_m.mean_pinball_loss:.3f} LPA | "
            f"Coverage = {u_m.empirical_coverage * 100:.1f}% | "
            f"Width = {u_m.mean_interval_width:.2f} LPA"
        )
        print(
            f"  $M_{{anchored}}$ : Pinball = {a_m.mean_pinball_loss:.3f} LPA | "
            f"Coverage = {a_m.empirical_coverage * 100:.1f}% | "
            f"Width = {a_m.mean_interval_width:.2f} LPA"
        )

        print("\nAnchoring Decomposition:")
        reg = report.anchoring_regression
        ci_str = f"[{reg.alpha_ci_lower:.3f}, {reg.alpha_ci_upper:.3f}]"
        print(
            f"  Anchoring Weight (alpha)   : {reg.anchoring_weight_alpha:.3f} (95% CI: {ci_str}) "
            f"(Threshold: < {reg.threshold_alpha:.2f}) -> "
            f"{'FAIL (EXCESSIVE)' if reg.is_excessively_anchored else 'PASS'}"
        )
        print(f"  Profile Weight (beta)      : {reg.profile_weight_beta:.3f}")

        print("\nCohort Disparity Audit:")
        disp = report.cohort_disparity
        print(
            f"  Underpaid Cohort (N={disp.underpaid_cohort_size}) Mean Current Pay: "
            f"{disp.underpaid_mean_current_pay:.2f} LPA"
        )
        print(
            f"  Baseline Cohort  (N={disp.baseline_cohort_size}) Mean Current Pay: "
            f"{disp.baseline_mean_current_pay:.2f} LPA"
        )
        print(f"  Unanchored Disparity Gap   : {disp.unanchored_disparity_ratio * 100:.1f}%")
        print(f"  Anchored Disparity Gap     : {disp.anchored_disparity_ratio * 100:.1f}%")
        print(
            f"  Delta Disparity            : {disp.delta_disparity * 100:+.2f}% "
            f"(Threshold: <= {disp.threshold_delta_disparity * 100:.1f}%) -> "
            f"{'VIOLATION' if disp.is_disparity_compounded else 'ACCEPTABLE'}"
        )

        print("\nGovernance Directive:")
        print(f"  {report.governance_directive}")

        print("\nReports successfully saved to:")
        print(f"  - Markdown : {args.output_md}")
        print(f"  - JSON     : {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Anchoring analysis failed: {err}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
