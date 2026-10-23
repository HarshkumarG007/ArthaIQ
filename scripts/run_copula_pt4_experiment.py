#!/usr/bin/env python3
"""CLI runner for EXP-PGM-01r: Gaussian Copula Dependency Structure for Multi-Component PT4.

Phase 13, Task T13.07.

Evaluates a Gaussian copula joint dependency structure using non-parametric empirical marginal
probability integral transforms (PIT) as an interactive scenario correlation layer for the
PT4 negotiation engine (compintel.serving.counterfactual).

Governed by:
- PRD Section 5 & FR-05: Personalization hierarchy and negotiation scenario modeling.
- CHARTER-COPULA-PT4 & EXP-PGM-01r: Copula multi-component scenario layer.
- Rule R-MD-01: Orderly ladder climbing & bootstrap confidence intervals.
- Rule R-MD-05: Comprehensive evaluation metrics with bootstrap CIs.
- Rule R-MD-08: Guardrails against lone numbers and uncalibrated point estimates.
- Rule R-MD-09: Pre-registered experiment charter required before implementation.
- Rule R-UQ-01: Uncertainty quantification; zero lone numbers. Calibrated [P10, P50, P90] spans.
- Rule R-UQ-05: Strict monotonic non-crossing quantiles guarantee.
- Rule R-CD-01: Pure typed Python, CPU-only inference, reproducible seeds.

Usage:
    uv run python scripts/run_copula_pt4_experiment.py
        [--output-md <path>]
        [--output-json <path>]
        [--n-cases <int>]
        [--seed <int>]
        [--quiet]
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
from compintel.evaluation.copula_pt4_experiment import (
    MAX_P95_LATENCY_MS,
    MAX_QUANTILE_CROSSING_RATE,
    MAX_SPEARMAN_ERROR_THRESHOLD,
    evaluate_and_save_copula_pt4_experiment,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Gaussian Copula PT4 Dependency Structure Experiment (EXP-PGM-01r, T13.07)."
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/copula-pt4-phase13.md",
        help="Path for publication-grade Markdown research memo.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/copula_pt4_report.json",
        help="Path for machine-readable JSON evaluation report.",
    )
    parser.add_argument(
        "--n-cases",
        type=int,
        default=500,
        help="Target sample size for multi-component empirical evaluation.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic reproducibility.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal summary output.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute copula PT4 experiment CLI workflow."""
    args = parse_args()

    md_path = Path(args.output_md)
    json_path = Path(args.output_json)

    try:
        report = evaluate_and_save_copula_pt4_experiment(
            output_dir=json_path.parent,
            docs_dir=md_path.parent,
            seed=args.seed,
        )

        # Move/ensure exact output filenames if different from default directories
        actual_json = json_path.parent / "copula_pt4_report.json"
        actual_md = md_path.parent / "copula-pt4-phase13.md"

        if actual_json != json_path:
            actual_json.rename(json_path)
        if actual_md != md_path:
            actual_md.rename(md_path)

    except CompIntelError as exc:
        print(f"ERROR: Copula PT4 experiment failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        m = report.metrics
        ds = report.dataset_summary
        print()
        print("=" * 78)
        print("  ArthaIQ -- EXP-PGM-01r: Copula PT4 Dependency Structure (Task T13.07)")
        print("=" * 78)
        print(f"  Report ID            : {report.report_id}")
        print(f"  Charter ID           : {report.charter_id}")
        print(f"  Task ID              : {report.task_id}")
        print(f"  Git Commit           : {report.git_commit[:8]}")
        print(
            f"  Sample Size          : {m.sample_size:,} observations ({ds.get('non_synthetic_count', m.sample_size):,} non-synthetic)"
        )
        print(f"  Components Evaluated : {', '.join(m.components)}")
        print("-" * 78)
        print("  PRE-REGISTERED KEEP CRITERIA AUDIT:")
        print(
            f"  1. Max Spearman Rank Error (|Delta rho|) : {m.max_spearman_error:.4f} "
            f"(threshold <= {MAX_SPEARMAN_ERROR_THRESHOLD:.3f}) -> "
            f"{'PASS' if report.keep_criteria_status['rank_correlation_fidelity'] else 'FAIL'}"
        )
        print(
            f"  2. Zero Point-Estimate Compliance : {'100.0%' if m.zero_lone_number_compliant else '0.0%'} -> "
            f"{'PASS' if report.keep_criteria_status['zero_point_estimate_compliance'] else 'FAIL'}"
        )
        print(
            f"  3. Quantile Crossing Rate        : {m.quantile_crossing_rate:.4f} "
            f"(threshold <= {MAX_QUANTILE_CROSSING_RATE:.3f}) -> "
            f"{'PASS' if report.keep_criteria_status['quantile_crossing_rate'] else 'FAIL'}"
        )
        print(
            f"  4. Scenario Generation (p95)     : {m.p95_latency_ms:.2f} ms "
            f"(threshold <= {MAX_P95_LATENCY_MS:.1f} ms) -> "
            f"{'PASS' if report.keep_criteria_status['simulation_latency'] else 'FAIL'}"
        )
        print(
            f"  5. Empirical Joint Coverage      : {m.empirical_joint_coverage * 100.0:.2f}% "
            f"(target [75.0%, 85.0%]) -> "
            f"{'PASS' if report.keep_criteria_status['empirical_joint_coverage'] else 'FAIL'}"
        )
        print(
            f"  6. Core Model Non-Contamination   : {'ISOLATED' if m.core_model_uncontaminated else 'CONTAMINATED'} -> "
            f"{'PASS' if report.keep_criteria_status['core_model_uncontaminated'] else 'FAIL'}"
        )
        print("-" * 78)
        print(f"  PRE-REGISTERED VERDICT: >>> {report.verdict.value} <<<")
        print(f"  Champion Status       : {report.champion_status}")
        print(f"  Markdown Memo Saved   : {md_path}")
        print(f"  Structured JSON Saved : {json_path}")
        print("=" * 78)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
