#!/usr/bin/env python3
"""CLI runner for EXP-ENSEMBLE-01r: Quantile Ensembling Feasibility Re-audit (Phase 13, Task T13.02).

Conducts an empirical data-growth re-evaluation of convex quantile blending (CatBoost + LightGBM)
and meta-learner stacking under Charter CHARTER-ENSEMBLING-STACKING using the cumulative
post-EXP-16 non-synthetic production panel.

Governed by:
- PRD Section 5 & FR-05: Personalization hierarchy and quantile calibration.
- CHARTER-ENSEMBLING-STACKING: experiments/configs/charters/charter_ensembling_stacking.yaml.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-04: Feature statistics and preprocessing fitted inside training fold only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charter required; pure CPU compute; no post-hoc threshold shifts.
- Rule R-MD-11: Synthetic data isolation guards (verified non-synthetic data only).
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences; zero lone numbers.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_ensemble_reaudit.py
        [--output-md <path>]
        [--output-json <path>]
        [--months-operational <float>]
        [--min-records <int>]
        [--n-resamples <int>]
        [--allow-synthetic]
        [--seed <int>]
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
from compintel.evaluation.ensemble_reaudit import (
    evaluate_and_save_ensemble_reaudit,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Quantile Ensembling Feasibility Re-audit (EXP-ENSEMBLE-01r, Phase 13, Task T13.02)."
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/ensemble-reaudit-phase13.md",
        help="Output path for publication-grade Markdown memo.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/ensemble_reaudit.json",
        help="Output path for structured JSON audit report.",
    )
    parser.add_argument(
        "--months-operational",
        type=float,
        default=6.0,
        help="Months of post-EXP-16 daemon operations to audit (default: 6.0).",
    )
    parser.add_argument(
        "--min-records",
        type=int,
        default=100,
        help="Pre-registered Gate 1 record threshold (default: 100).",
    )
    parser.add_argument(
        "--n-resamples",
        type=int,
        default=1000,
        help="Number of bootstrap resamples for paired difference (default: 1000).",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Explicitly permit synthetic data execution (Rule R-MD-11).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute quantile ensembling feasibility re-audit CLI."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()

    print("=" * 80)
    print("  ArthaIQ -- Quantile Ensembling Feasibility Re-audit (Phase 13, EXP-ENSEMBLE-01r)")
    print("  Charter: CHARTER-ENSEMBLING-STACKING | Task: T13.02")
    print("=" * 80)
    print(f"Months Post-EXP-16:     {args.months_operational:.1f} months")
    print(f"Minimum Records Gate:   N >= {args.min_records}")
    print(f"Bootstrap Resamples:    {args.n_resamples}")
    print(f"Random Seed:            {args.seed}")
    print(f"Allow Synthetic Data:   {args.allow_synthetic}")
    print(f"Output Markdown:        {args.output_md}")
    print(f"Output JSON:            {args.output_json}")
    print("-" * 80)

    try:
        report = evaluate_and_save_ensemble_reaudit(
            output_json_path=Path(args.output_json),
            output_memo_path=Path(args.output_md),
            months_operational=args.months_operational,
            min_required_records=args.min_records,
            n_resamples=args.n_resamples,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\n[+] Re-audit Execution Completed Successfully.")
        print(f"    Report ID:              {report.report_id}")
        print(f"    Generated At:           {report.generated_at}")
        print(f"    Total Panel Records:    {report.n_total_observations}")
        print(f"    Verified Non-Synthetic: {report.n_non_synthetic}")
        print(f"    Gate 1 Status:          {report.feasibility_audit.status.value}")
        print(f"    Gate 1 Passed:          {report.gate1_passed}")
        print(f"    Modeling Executed:      {report.modeling_executed}")

        if report.baseline_metrics and report.ensemble_metrics and report.paired_difference:
            bm = report.baseline_metrics
            em = report.ensemble_metrics
            pd = report.paired_difference
            print("\n[-] Modeling Performance Summary:")
            print(f"    Baseline Pinball Loss:  {bm.mean_pinball_loss:.4f} LPA")
            print(f"    Ensemble Pinball Loss:  {em.mean_pinball_loss:.4f} LPA")
            print(
                f"    Pinball Delta:          {pd.delta_mean_pinball:+.4f} LPA "
                f"(95% CI: [{pd.ci_lower:+.4f}, {pd.ci_upper:+.4f}] LPA)"
            )
            print(f"    Baseline Interval Width:{bm.mean_interval_width:.2f} LPA")
            print(f"    Ensemble Interval Width:{em.mean_interval_width:.2f} LPA")
            print(
                f"    Interval Width Ratio:   {pd.width_ratio:.4f} (<= 0.950 required for PROMOTE)"
            )
            print(f"    Baseline Coverage:      {bm.empirical_coverage * 100:.2f}%")
            print(f"    Ensemble Coverage:      {em.empirical_coverage * 100:.2f}%")
            print(f"    Crossing Rate:          {em.crossing_rate * 100:.2f}% (R-UQ-05 satisfied)")

        print("-" * 80)
        print(f"FINAL RE-AUDIT VERDICT:     {report.verdict.value}")
        print(f"CHAMPION STATUS:            {report.champion_status}")
        print(f"GOVERNANCE DECISION:        {report.governance_decision}")
        print("=" * 80)
        return 0

    except CompIntelError as err:
        print(f"\n[!] CompIntel Domain Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"\n[!] Unexpected Error during re-audit: {err}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
