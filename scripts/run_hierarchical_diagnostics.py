#!/usr/bin/env python3
"""CLI runner to execute Rung C hierarchical model diagnostics (Rules R-UQ-06, EXP-05).

Usage:
    uv run python scripts/run_hierarchical_diagnostics.py
        [--canonical-path <path>]
        [--output-md <path>]
        [--output-json <path>]
        [--split <select|calibrate>]
        [--n-prior-simulations <int>]
        [--n-posterior-replications <int>]
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
from compintel.evaluation.hierarchical_diagnostics import (
    evaluate_and_save_hierarchical_diagnostics,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Rung C Hierarchical Model Diagnostics (Rule R-UQ-06, Hypothesis EXP-05)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/rung-c-diagnostics.md",
        help="Output path for Markdown diagnostic report.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/hierarchical_diagnostics_v1.json",
        help="Output path for JSON diagnostic results.",
    )
    parser.add_argument(
        "--split",
        default="select",
        choices=["select", "calibrate"],
        help="Development split to evaluate on (locked test partition prohibited per R-MD-02).",
    )
    parser.add_argument(
        "--n-prior-simulations",
        type=int,
        default=1000,
        help="Number of simulations for prior predictive checks.",
    )
    parser.add_argument(
        "--n-posterior-replications",
        type=int,
        default=500,
        help="Number of replicated datasets for posterior predictive checks.",
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

    print("=" * 70)
    print("  ArthaIQ -- Rung C Hierarchical Diagnostics & Calibration Checks")
    print("  Rule R-UQ-06 | Rule R-UQ-05 | Pre-Registered Hypothesis EXP-05")
    print("=" * 70)
    print(f"Canonical path          : {args.canonical_path}")
    print(f"Evaluation split        : {args.split}")
    print(f"Prior simulations       : {args.n_prior_simulations}")
    print(f"Posterior replications  : {args.n_posterior_replications}")
    print(f"Random seed             : {args.seed}")
    print(f"Output Markdown         : {args.output_md}")
    print(f"Output JSON             : {args.output_json}")
    print(f"Allow synthetic         : {args.allow_synthetic}")
    print("-" * 70)

    try:
        report = evaluate_and_save_hierarchical_diagnostics(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            split=args.split,
            n_prior_simulations=args.n_prior_simulations,
            n_posterior_replications=args.n_posterior_replications,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\nHierarchical Diagnostics Evaluation Complete!")
        print(f"Overall Verdict: {report.overall_verdict}")
        print(f"Prior Plausible: {report.prior_checks.is_physically_plausible}")
        print(f"Posterior Calib: {report.posterior_checks.all_statistics_calibrated}")
        print(f"Prior Robust   : {report.prior_sensitivity.robustness_verdict}")
        print(f"\nArtifacts generated:\n  - {args.output_md}\n  - {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] CompIntel evaluation failure: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
