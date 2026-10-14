#!/usr/bin/env python3
"""Compute effective sample sizes per cell and export coverage map (Task T2.07).

Governed by experiments/preregistration/sufficiency-v1.yaml.
Usage:
    uv run python scripts/compute_coverage_map.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ is importable even without editable install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from compintel.quality.coverage import (
    compute_coverage_map,
    export_coverage_artifacts,
    generate_coverage_table_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute 84-cell coverage map and effective sample sizes (T2.07)."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to repository root.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Path to results directory (defaults to experiments/results/).",
    )
    args = parser.parse_args()

    repo_root = args.repo_root
    output_dir = args.output_dir or (repo_root / "experiments" / "results")

    print("=" * 80)
    print("  ArthaIQ Cell Coverage Map & Effective Sample Size Engine (Task T2.07)")
    print("  Pre-Registration Reference: experiments/preregistration/sufficiency-v1.yaml")
    print("=" * 80)

    # Compute coverage dataframe
    df = compute_coverage_map(repo_root=repo_root)

    # Export artifacts
    artifacts = export_coverage_artifacts(df, output_dir=output_dir)

    # Print summary markdown
    summary_md = generate_coverage_table_markdown(df)
    # Output safely
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    print("\n" + summary_md)
    print("\n" + "=" * 80)
    print("  Artifacts Successfully Exported:")
    for name, path in artifacts.items():
        print(f"    - {name.upper():<10}: {path}")
    print("=" * 80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
