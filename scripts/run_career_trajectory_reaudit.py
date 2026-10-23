#!/usr/bin/env python3
"""CLI runner for EXP-TRAJ-r: Career Trajectory Feature Re-evaluation (Phase 13, Task T13.05).

Conducts a pre-registered longitudinal panel depth feasibility audit and empirical data-growth
re-evaluation of dynamic career trajectory features (career velocity, promotion acceleration,
tenure stability, and company tier mobility) under Charter CHARTER-CAREER-TRAJ and
CHARTER-CAREER-TRAJ-r using the cumulative post-EXP-16 non-synthetic production panel.

Governed by:
- PRD Section 5 & FR-05: Personalization hierarchy and career trajectory modeling.
- CHARTER-CAREER-TRAJ & CHARTER-CAREER-TRAJ-r: Career trajectory feature re-evaluation.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-04: Preprocessing and feature statistics fitted inside training fold only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charter required; pure CPU compute.
- Rule R-MD-11: Synthetic data isolation guards (verified non-synthetic data only).
- Rule R-MD-15: Missingness indicator policy for optional telemetry.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals; zero lone numbers.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
- ADR-0008 Section 6: Longitudinal career schema governance and DPDPA 2023 compliance.

Usage:
    uv run python scripts/run_career_trajectory_reaudit.py
        [--output-md <path>]
        [--output-json <path>]
        [--months-operational <float>]
        [--min-span-months <float>]
        [--min-longitudinal-records <int>]
        [--allow-synthetic]
        [--force-experiment]
        [--n-resamples <int>]
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
from compintel.evaluation.career_trajectory_reaudit import (
    DEFAULT_MIN_LONGITUDINAL_RECORDS,
    DEFAULT_MIN_SPAN_MONTHS,
    evaluate_and_save_career_trajectory_reaudit,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Career Trajectory Feature Re-evaluation (EXP-TRAJ-r, Phase 13, Task T13.05)."
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/career-trajectory-reaudit-phase13.md",
        help="Output path for publication-grade Markdown memo.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/career_trajectory_reaudit.json",
        help="Output path for structured JSON audit report.",
    )
    parser.add_argument(
        "--canonical-path",
        default=None,
        help="Optional path to base verified canonical parquet dataset.",
    )
    parser.add_argument(
        "--months-operational",
        type=float,
        default=6.0,
        help="Months of post-EXP-16 daemon operations to audit (default: 6.0).",
    )
    parser.add_argument(
        "--min-span-months",
        type=float,
        default=DEFAULT_MIN_SPAN_MONTHS,
        help="Pre-registered Gate 1 calendar span threshold in months (default: 12.0).",
    )
    parser.add_argument(
        "--min-longitudinal-records",
        type=int,
        default=DEFAULT_MIN_LONGITUDINAL_RECORDS,
        help="Pre-registered Gate 1 milestone record count threshold (default: 100).",
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
        "--force-experiment",
        action="store_true",
        default=False,
        help="Force empirical model evaluation regardless of Gate 1 panel depth audit.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute career trajectory feature re-evaluation CLI."""
    args = parse_args()

    md_path = Path(args.output_md)
    json_path = Path(args.output_json)

    # Use parent of json_path as output directory
    output_dir = json_path.parent
    report_filename = json_path.name
    md_filename = md_path.name

    # If md_path is in a different directory, adjust
    if md_path.parent != output_dir:
        md_dir = md_path.parent
        md_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(" ArthaIQ - EXP-TRAJ-r Career Trajectory Feature Re-evaluation (Phase 13, T13.05)")
    print("=" * 80)
    print(f"Operational Window Audited : {args.months_operational:.1f} months")
    print(f"Pre-Registered Span Target : >= {args.min_span_months:.1f} calendar months")
    print(f"Longitudinal Record Target : >= {args.min_longitudinal_records} verified records")
    print(f"Output Markdown Memo       : {args.output_md}")
    print(f"Output JSON Report         : {args.output_json}")
    print(f"Force Empirical Benchmark  : {args.force_experiment}")
    print("-" * 80)

    try:
        report = evaluate_and_save_career_trajectory_reaudit(
            output_dir=output_dir,
            canonical_path=args.canonical_path,
            months_operational=args.months_operational,
            min_span_months=args.min_span_months,
            min_longitudinal_records=args.min_longitudinal_records,
            allow_synthetic=args.allow_synthetic,
            force_experiment=args.force_experiment,
            n_resamples=args.n_resamples,
            seed=args.seed,
            report_filename=report_filename,
            md_filename=md_filename,
        )

        # If md_path is in docs/research/ and output_dir is experiments/results, copy md file
        generated_md = output_dir / md_filename
        if generated_md != md_path:
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(generated_md.read_text(encoding="utf-8"), encoding="utf-8")
            if generated_md.exists() and output_dir != md_path.parent:
                generated_md.unlink()

        pm = report.panel_metrics
        print("\nAudit Results:")
        print(f"  Total Cumulative Records     : {pm.total_records:,}")
        print(f"  Verified Non-Synthetic       : {pm.non_synthetic_records:,}")
        print(
            f"  Observed Calendar Span       : {pm.panel_span_months:.1f} months ({pm.panel_span_days} days)"
        )
        print(f"  Span Sufficiency Status      : {'PASS' if pm.is_span_sufficient else 'DEFER'}")
        print(f"  Span Deficit                 : {pm.span_deficit_months:.1f} months")
        print(f"  Populated Milestone Records  : {pm.longitudinal_populated_records:,}")
        print(f"  Milestone Record Deficit     : {pm.record_deficit:,}")
        print(f"  Gate 1 Audit Status          : {report.audit_status.value}")
        print(f"  Pre-Registered Verdict       : {report.verdict.value}")
        print(f"  Production Champion Status   : {report.champion_status}")
        print(f"  Next Scheduled Audit Date    : {report.next_trigger_date}")
        print(f"  Next Trigger Condition       : {report.next_trigger_condition}")
        print("-" * 80)
        print(f"Executive Summary:\n  {report.executive_summary}")
        print("=" * 80)
        print("SUCCESS: Career Trajectory Re-evaluation Audit completed cleanly.")
        return 0

    except CompIntelError as err:
        print(f"\nERROR [{err.code}]: {err.message}", file=sys.stderr)
        if err.details:
            print(f"Details: {err.details}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\nUNEXPECTED FAILURE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
