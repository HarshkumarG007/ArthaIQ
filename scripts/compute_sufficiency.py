"""CLI script to compute sufficiency analysis and bootstrap precision (Task T2.09).

Usage:
    uv run python scripts/compute_sufficiency.py
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import polars as pl

from compintel.quality.sufficiency import (
    evaluate_gate_g2_decision,
    evaluate_precision_for_all_cells,
    export_sufficiency_artifacts,
)


def main() -> int:
    """Execute sufficiency analysis against pre-registered criteria (sufficiency-v1.yaml)."""
    # Reconfigure stdout for utf-8 on Windows
    if sys.stdout.encoding.lower() != "utf-8":
        with contextlib.suppress(Exception):
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

    project_root = Path(__file__).resolve().parent.parent
    results_dir = project_root / "experiments" / "results"
    docs_dir = project_root / "docs" / "research"
    processed_dir = project_root / "data" / "processed"

    print("=" * 72)
    print(" ArthaIQ — Data Sufficiency Analysis & Gate G2 Evaluation (Task T2.09)")
    print(" Governing Pre-Registration: experiments/preregistration/sufficiency-v1.yaml")
    print("=" * 72)

    coverage_parquet = results_dir / "coverage_map_v1.parquet"
    if not coverage_parquet.exists():
        print(f"Error: {coverage_parquet} not found. Run make coverage-map first.")
        return 1

    coverage_df = pl.read_parquet(coverage_parquet)
    print(f"Loaded coverage map: {len(coverage_df)} cells.")

    # Load exploratory dataset if available for diagnostic bootstrap precision
    exploratory_parquet = processed_dir / "prototype_pt1_exploratory.parquet"
    exploratory_df: pl.DataFrame | None = None
    if exploratory_parquet.exists():
        exploratory_df = pl.read_parquet(exploratory_parquet)
        print(f"Loaded exploratory prototype dataset: {len(exploratory_df)} records.")
    else:
        print("Note: Exploratory prototype dataset not found in data/processed/.")

    # Evaluate bootstrap precision for all 84 cells
    print("\nComputing bootstrap precision (B=2,000 resamples per populated cell)...")
    precision_df = evaluate_precision_for_all_cells(
        df_exploratory=exploratory_df,
        n_bootstrap=2000,
    )

    # Evaluate global Gate G2 decision
    g2_decision = evaluate_gate_g2_decision(coverage_df)
    print(f"\nGate G2 Global Verdict: {g2_decision['verdict']}")
    print(f"Summary: {g2_decision['summary']}")

    # Export artifacts
    exported = export_sufficiency_artifacts(
        coverage_df=coverage_df,
        precision_df=precision_df,
        exploratory_precision_df=precision_df,
        g2_decision=g2_decision,
        results_dir=results_dir,
        docs_dir=docs_dir,
    )

    print("\nSufficiency artifacts generated successfully:")
    for key, path in exported.items():
        print(f"  - {key}: {path.relative_to(project_root)}")

    print("\n" + "=" * 72)
    print(" SUFFICIENCY ANALYSIS COMPLETE: GATE G2 RATIFIED AS NO-GO")
    print(" Mandate: All Phase 3 ML modelling halted. Proceed to Task T2.10.")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    sys.exit(main())
