#!/usr/bin/env python3
"""CLI runner for EXP-09r: Skills TF-IDF Power-Gated Re-audit (Phase 13, Task T13.03).

Conducts a pre-registered statistical power analysis and empirical data-growth re-evaluation
of EXP-09 Variant A (curated taxonomy and TF-IDF bag-of-skills representation) and Variant B
(sentence-transformers on CPU) under Charter CHARTER-EXP-09 and CHARTER-EXP-09r using the
cumulative post-EXP-16 non-synthetic production panel.

Governed by:
- PRD Section 5 & FR-05: Personalization hierarchy and skills capability modeling.
- CHARTER-EXP-09 & CHARTER-EXP-09r: Skills feature modeling re-evaluation.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-04: Preprocessing and SVD fitted inside training fold only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charter required; pure CPU compute.
- Rule R-MD-11: Synthetic data isolation guards (verified non-synthetic data only).
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences; zero lone numbers.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).

Usage:
    uv run python scripts/run_skills_reaudit.py
        [--output-md <path>]
        [--output-json <path>]
        [--months-operational <float>]
        [--min-records <int>]
        [--allow-synthetic]
        [--force-modeling]
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
from compintel.evaluation.skills_reaudit import (
    DEFAULT_MIN_REQUIRED_RECORDS,
    evaluate_and_save_skills_reaudit,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Skills TF-IDF Power-Gated Re-audit (EXP-09r, Phase 13, Task T13.03)."
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/skills-reaudit-phase13.md",
        help="Output path for publication-grade Markdown memo.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/skills_reaudit.json",
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
        "--min-records",
        type=int,
        default=DEFAULT_MIN_REQUIRED_RECORDS,
        help="Pre-registered Gate 1 record threshold (default: 500).",
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
        "--force-modeling",
        action="store_true",
        default=False,
        help="Force empirical model evaluation regardless of Gate 1 power audit.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute skills TF-IDF power-gated re-audit CLI."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()

    print("================================================================================")
    print(" ArthaIQ - EXP-09r Skills TF-IDF Power-Gated Re-audit Runner (Phase 13, T13.03)")
    print("================================================================================")
    print(f"Output Markdown Memo : {args.output_md}")
    print(f"Output JSON Report   : {args.output_json}")
    print(f"Operational Window   : {args.months_operational:.1f} months post-EXP-16")
    print(f"Required Sample Size : {args.min_records} non-synthetic records")
    print(f"Allow Synthetic Data : {args.allow_synthetic}")
    print(f"Force Model Training : {args.force_modeling}")
    print(f"Bootstrap Resamples  : {args.n_resamples}")
    print(f"Random Seed          : {args.seed}")
    print("--------------------------------------------------------------------------------")

    try:
        report = evaluate_and_save_skills_reaudit(
            output_md=args.output_md,
            output_json=args.output_json,
            canonical_path=args.canonical_path,
            months_operational=args.months_operational,
            min_required_records=args.min_records,
            allow_synthetic=args.allow_synthetic,
            force_modeling=args.force_modeling,
            n_resamples=args.n_resamples,
            seed=args.seed,
        )

        pm = report.feasibility_audit.power_metrics
        print("\n================================================================================")
        print(" EXP-09r SKILLS TF-IDF POWER-GATED RE-AUDIT RESULTS SUMMARY")
        print("================================================================================")
        print(f"Report ID              : {report.report_id}")
        print(f"Total Observations     : {report.n_total_observations}")
        print(f"Non-Synthetic Records  : {report.n_non_synthetic} / {report.n_total_observations}")
        print(f"Required Sample Size   : {pm.required_sample_size}")
        print(
            f"Achieved Power         : {pm.achieved_power * 100:.1f}% (target: {pm.target_power * 100:.1f}%)"
        )
        print(f"Sample Size Deficit    : {pm.sample_size_deficit} records")
        print(f"Gate 1 Power Status    : {report.feasibility_audit.status.value}")
        print(f"Gate 1 Passed          : {report.gate1_passed}")
        print(f"Modeling Executed      : {report.modeling_executed}")
        print(f"Variant A Verdict      : {report.variant_a_verdict.value}")
        print(f"Variant B Verdict      : {report.variant_b_verdict.value}")
        print(f"Overall Re-audit Verdict: {report.overall_verdict.value}")
        print(f"Champion Status        : {report.champion_status}")
        print(f"Next Scheduled Audit   : {report.next_scheduled_audit_date}")
        print(f"Next Audit Trigger     : {report.next_audit_trigger_condition}")
        print("--------------------------------------------------------------------------------")
        print("Executive Summary:")
        print(f"  {report.executive_summary}")
        print("Governance Decision:")
        print(f"  {report.governance_decision}")
        print("================================================================================")
        print(
            f"[OK] Report successfully written to:\n  - {args.output_md}\n  - {args.output_json}\n"
        )
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] CompIntel audit contract violation: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
