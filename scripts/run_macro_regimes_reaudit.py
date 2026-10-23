#!/usr/bin/env python3
"""CLI runner for EXP-MACRO-01r: Macro Regime Features Long-Range Calendar Trigger (Phase 13, T13.06).

Conducts a pre-registered longitudinal panel span feasibility audit and empirical data-growth
re-evaluation of macroeconomic market-regime features (MOSPI CPI Urban real-pay deflation,
RBI reference rates, and trailing FX volatility) under Charter CHARTER-MACRO-REGIMES and
CHARTER-MACRO-REGIMES-r using the cumulative post-EXP-16 non-synthetic production panel.

Governed by:
- PRD Section 5 & FR-05: Personalization hierarchy and market-regime adjustment.
- CHARTER-MACRO-REGIMES & CHARTER-MACRO-REGIMES-r: Macro regime feature re-evaluation.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-03: Release-time lag enforcement; zero lookahead.
- Rule R-MD-04: Preprocessing and feature statistics fitted inside training fold only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charter required; pure CPU compute.
- Rule R-MD-11: Synthetic data isolation guards (verified non-synthetic data only).
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals; zero lone numbers.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_macro_regimes_reaudit.py
        [--output-md <path>]
        [--output-json <path>]
        [--canonical-path <path>]
        [--months-operational <float>]
        [--min-span-months <float>]
        [--macro-dir <path>]
        [--allow-synthetic]
        [--force-experiment]
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
from compintel.evaluation.macro_regimes_reaudit import (
    CALENDAR_TRIGGER_DATE,
    DEFAULT_MIN_SPAN_MONTHS,
    evaluate_and_save_macro_regimes_reaudit,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Macro Regime Features Long-Range Calendar Trigger Re-audit (EXP-MACRO-01r, Phase 13, T13.06)."
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/macro-regimes-reaudit-phase13.md",
        help="Output path for publication-grade Markdown memo.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/macro_regimes_reaudit.json",
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
        help="Pre-registered Gate 1 calendar span threshold in months (default: 24.0).",
    )
    parser.add_argument(
        "--macro-dir",
        default="data/raw/SRC-SUP-MAC-01",
        help="Directory containing official MOSPI CPI and RBI FX series.",
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
        help="Force empirical model evaluation regardless of Gate 1 panel span audit.",
    )
    parser.add_argument(
        "--n-resamples",
        type=int,
        default=1000,
        help="Number of bootstrap resamples for paired difference (default: 1000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute macro regime feature re-evaluation CLI."""
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
    print(" ArthaIQ - EXP-MACRO-01r Macro Regimes Long-Range Calendar Trigger (Phase 13, T13.06)")
    print("=" * 80)
    print(f"Operational Window Audited : {args.months_operational:.1f} months")
    print(f"Pre-Registered Span Target : >= {args.min_span_months:.1f} calendar months")
    print(f"Calendar Trigger Target    : {CALENDAR_TRIGGER_DATE}")
    print(f"Macro Data Directory       : {args.macro_dir}")
    print(f"Output Markdown Memo       : {args.output_md}")
    print(f"Output JSON Report         : {args.output_json}")
    print(f"Force Empirical Benchmark  : {args.force_experiment}")
    print("-" * 80)

    try:
        report = evaluate_and_save_macro_regimes_reaudit(
            output_dir=output_dir,
            canonical_path=args.canonical_path,
            months_operational=args.months_operational,
            min_span_months=args.min_span_months,
            allow_synthetic=args.allow_synthetic,
            force_experiment=args.force_experiment,
            macro_dir=args.macro_dir,
            n_resamples=args.n_resamples,
            seed=args.seed,
            report_filename=report_filename,
            md_filename=md_filename,
        )

        pm = report.panel_metrics
        print("Gate 1 Longitudinal Span Audit Results:")
        print(f"  Verified Non-Synthetic Records : {pm.non_synthetic_records:,}")
        print(
            f"  Realized Observation Span      : {pm.panel_span_months:.1f} months ({pm.panel_span_days} days)"
        )
        print(
            f"  Required Span Threshold        : >= {pm.required_span_months:.1f} calendar months"
        )
        print(
            f"  Span Deficit                   : {pm.span_deficit_months:.1f} months ({pm.span_deficit_days} days)"
        )
        print(f"  Span Sufficiency Status        : {'PASS' if pm.is_span_sufficient else 'DEFER'}")
        print(
            f"  Calendar Trigger Status        : {'MET' if pm.calendar_trigger_met else 'PENDING'}"
        )
        print(f"  MOSPI CPI Urban Rows           : {pm.cpi_series_rows:,}")
        print(f"  RBI Daily FX Rows              : {pm.fx_series_rows:,}")
        print("-" * 80)
        print(f"Gate 1 Feasibility Status      : {report.audit_status.value}")
        print(f"Overall Re-audit Verdict       : {report.verdict.value}")
        print(f"Production Champion Status     : {report.champion_status}")
        print(f"Next Scheduled Trigger Date    : {report.next_trigger_date}")
        print(f"Next Audit Trigger Condition   : {report.next_trigger_condition}")
        print("=" * 80)
        print("Audit memo and results successfully written.")
        return 0

    except CompIntelError as err:
        print(f"ERROR [{err.__class__.__name__}]: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
