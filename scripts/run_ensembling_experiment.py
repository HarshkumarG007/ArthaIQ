#!/usr/bin/env python3
"""CLI runner to execute Ensembling & Stacking Experiment under Charter EXP-ENSEMBLE / Task T7.06.

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and quantile calibration.
- CHARTER-ENSEMBLING-STACKING: experiments/configs/charters/charter_ensembling_stacking.yaml.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-04: Feature statistics and preprocessing fitted inside training fold only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charter required; pure CPU compute.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_ensembling_experiment.py
        [--canonical-path <path>]
        [--output-md <path>]
        [--output-json <path>]
        [--split <select|calibrate>]
        [--n-resamples <int>]
        [--seed <int>]
        [--force-modeling]
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
from compintel.evaluation.ensembling_experiment import (
    evaluate_and_save_ensembling_experiment,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Quantile Model Ensembling & Stacking Experiment (T7.06)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/ensembling-stacking-exp-ensemble.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/ensembling_exp_v1.json",
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
        "--force-modeling",
        action="store_true",
        default=False,
        help="Force execution of model fitting even if Gate 1 feasibility flags insufficient sample.",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Explicitly permit synthetic observations under Rule R-MD-11.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute ensembling experiment CLI."""
    args = parse_args()

    print("=" * 80)
    print(" ArthaIQ -- Quantile Model Ensembling & Stacking (EXP-ENSEMBLE-01, Task T7.06)")
    print("=" * 80)
    print(f"Canonical Path:     {args.canonical_path}")
    print(f"Evaluation Split:   {args.split} (Rule R-MD-02: Test set locked)")
    print(f"Bootstrap Resamples: {args.n_resamples:,} (Rule R-UQ-01)")
    print(f"Random Seed:        {args.seed}")
    print(f"Force Modeling:     {args.force_modeling}")
    print(f"Allow Synthetic:    {args.allow_synthetic}")
    print(f"Markdown Output:    {args.output_md}")
    print(f"JSON Output:        {args.output_json}")
    print("=" * 80)

    try:
        report = evaluate_and_save_ensembling_experiment(
            canonical_path=args.canonical_path,
            output_md_path=args.output_md,
            output_json_path=args.output_json,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            force_modeling=args.force_modeling,
            allow_synthetic=args.allow_synthetic,
        )

        print(f"\nReport ID:          {report.report_id}")
        print(f"Charter ID:         {report.charter_id}")
        print(f"Generated At:       {report.generated_at}")
        print(f"Git Commit:         {report.git_commit}")
        print(f"Overall Verdict:    {report.overall_verdict.value}")
        print(f"Modeling Executed:  {report.modeling_executed}")

        print("\nGate 1 Feasibility Audit:")
        print(f"  Status:           {report.feasibility_audit.status.value}")
        print(
            f"  Total Records:    {report.feasibility_audit.n_total_records} "
            f"[Min Required: {report.feasibility_audit.min_required_records}]"
        )
        print(f"  Train Records:    {report.feasibility_audit.n_train_records}")
        print(f"  Audit Diagnostic: {report.feasibility_audit.summary}")

        if report.modeling_executed and report.baseline_metrics and report.variant_a_metrics:
            print("\nCandidate Performance Metrics:")
            print(f"  Champion Pinball Loss: {report.baseline_metrics.mean_pinball_loss:.4f} LPA")
            print(
                f"  Champion Coverage:     {report.baseline_metrics.empirical_coverage * 100:.1f}%"
            )
            print(f"  Variant A Pinball:     {report.variant_a_metrics.mean_pinball_loss:.4f} LPA")
            print(
                f"  Variant A Coverage:    {report.variant_a_metrics.empirical_coverage * 100:.1f}%"
            )
            if report.deltas:
                d = report.deltas[0]
                print(
                    f"  Delta Pinball Loss:    {d.delta_mean_pinball:+.4f} LPA "
                    f"(95% CI: [{d.ci_lower:+.4f}, {d.ci_upper:+.4f}])"
                )
                print(f"  Width Ratio:           {d.width_ratio:.3f}")
        else:
            print(
                "\n[INFO] Modeling was skipped per Gate 1 Feasibility. Production Champion retained."
            )

        print(f"\n[OK] Markdown report written to: {args.output_md}")
        print(f"[OK] JSON results written to:    {args.output_json}")
        return 0

    except CompIntelError as err:
        print(
            f"\n[ERROR] Domain contract violation: {err.message} (Code: {err.code})",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error executing experiment: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
