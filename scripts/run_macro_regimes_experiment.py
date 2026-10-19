#!/usr/bin/env python3
"""CLI runner to execute Macroeconomic & Market-Regime Experiment under Charter EXP-MACRO / Task T7.05.

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and market-regime features.
- CHARTER-MACRO-REGIMES: experiments/configs/charters/charter_macro_regimes.yaml.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-03: Zero lookahead; macro indicators joined strictly via release-date as-of lookup.
- Rule R-MD-04: Feature statistics and preprocessing fitted inside training fold only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charter required; pure CPU compute.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_macro_regimes_experiment.py
        [--canonical-path <path>]
        [--macro-dir <path>]
        [--output-md <path>]
        [--output-json <path>]
        [--split <select|calibrate>]
        [--n-resamples <int>]
        [--seed <int>]
        [--cpi-ref <float>]
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
from compintel.evaluation.macro_regimes_experiment import (
    evaluate_and_save_macro_regimes_experiment,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Macro & Market-Regime Modeling Experiment (T7.05): Release-Time Joins."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--macro-dir",
        default="data/raw/SRC-SUP-MAC-01",
        help="Directory containing CPI and FX raw tables.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/macro-regimes-exp-macro.md",
        help="Output path for publication-grade Markdown report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/macro_regimes_exp_macro.json",
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
        "--cpi-ref",
        type=float,
        default=185.1,
        help="Reference CPI value for real-pay normalization (default: 185.1 for 2024-01-01 base).",
    )
    parser.add_argument(
        "--force-modeling",
        action="store_true",
        default=False,
        help="Force execution of model fitting even if Gate 1 feasibility audit flags insufficient span.",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Explicitly permit synthetic data execution (Rule R-MD-11).",
    )
    return parser.parse_args()


def main() -> int:
    """Execute macro regime feature experiment CLI."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()

    print("================================================================================")
    print(" ArthaIQ -- Macro & Market-Regime Experiment (EXP-MACRO-01, Task T7.05)")
    print("================================================================================")
    print(f"Canonical Path:     {args.canonical_path}")
    print(f"Macro Data Dir:     {args.macro_dir}")
    print(f"Evaluation Split:   {args.split} (Rule R-MD-02: Test set locked)")
    print(f"Bootstrap Resamples: {args.n_resamples:,} (Rule R-UQ-01)")
    print(f"Random Seed:        {args.seed}")
    print(f"Reference CPI:      {args.cpi_ref}")
    print(f"Force Modeling:     {args.force_modeling}")
    print(f"Allow Synthetic:    {args.allow_synthetic}")
    print(f"Markdown Output:    {args.output_md}")
    print(f"JSON Output:        {args.output_json}")
    print("================================================================================")

    try:
        report = evaluate_and_save_macro_regimes_experiment(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            macro_dir=args.macro_dir,
            eval_split_name=args.split,
            n_resamples=args.n_resamples,
            seed=args.seed,
            cpi_ref=args.cpi_ref,
            force_modeling=args.force_modeling,
            allow_synthetic=args.allow_synthetic,
        )

        print(f"\nReport ID:          {report.report_id}")
        print(f"Charter ID:         {report.charter_id}")
        print(f"Generated At:       {report.generated_at}")
        print(f"Git Commit:         {report.git_commit[:8]}")
        print(f"Overall Verdict:    {report.overall_verdict.value}")
        print(f"Modeling Executed:  {report.modeling_executed}")

        print("\nGate 1 Feasibility Audit:")
        print(f"  Status:           {report.feasibility_audit.status.value}")
        print(
            f"  Observation Span: {report.feasibility_audit.observation_span_days} days "
            f"({report.feasibility_audit.observation_span_months:.1f} months) "
            f"[Min Required: {report.feasibility_audit.min_required_months:.0f} months]"
        )
        print(
            f"  Range:            {report.feasibility_audit.observation_start} to {report.feasibility_audit.observation_end}"
        )
        print(f"  Eligible Records: {report.feasibility_audit.n_eligible_records:,}")
        print(f"  CPI Series Rows:  {report.feasibility_audit.cpi_series_rows:,}")
        print(f"  FX Series Rows:   {report.feasibility_audit.fx_series_rows:,}")
        print(f"  Audit Diagnostic: {report.feasibility_audit.summary}")

        if report.modeling_executed and report.baseline_metrics is not None:
            print("\nCandidate Performance Summary:")
            print("-" * 88)
            print(
                f"{'Candidate Variant':<38} | {'Feats':<5} | {'Pinball':<8} | {'MAE':<6} | {'Coverage':<8} | {'Width':<8}"
            )
            print("-" * 88)
            for m in [report.baseline_metrics, report.variant_a_metrics, report.variant_b_metrics]:
                if m is not None:
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
        else:
            print(
                "\n[INFO] Modeling was skipped per Gate 1 Feasibility. Production Champion retained."
            )

        print(f"\n[OK] Markdown report written to: {args.output_md}")
        print(f"[OK] JSON results written to:    {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Macro experiment execution failed: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
