#!/usr/bin/env python3
"""Construct PT1 prototype target datasets and documented exclusion audit (Task T2.08).

Governed by rules.md (R-DA-05 No silent drops, R-MD-07 Anti-heuristic unbundling).
Usage:
    uv run python scripts/construct_pt1_prototype.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from compintel.quality.target_prototype import (
    build_pt1_prototype,
    export_prototype_artifacts,
    generate_exclusion_report_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Construct PT1 prototype dataset and documented exclusion report (T2.08)."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to repository root.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root
    output_data_dir = repo_root / "data" / "processed"
    output_results_dir = repo_root / "experiments" / "results"
    research_docs_dir = repo_root / "docs" / "research"

    print("=" * 80)
    print("  ArthaIQ PT1 Prototype Target Construction & Exclusion Engine (Task T2.08)")
    print("  Policy Reference: rules.md (R-DA-05 No silent drops, R-MD-07 Unbundling)")
    print("=" * 80)

    result = build_pt1_prototype(repo_root=repo_root)
    artifacts = export_prototype_artifacts(
        result, output_data_dir=output_data_dir, output_results_dir=output_results_dir
    )

    # Also synchronize copy to docs/research/pt1-prototype-exclusion-report.md
    if research_docs_dir.exists():
        dest = research_docs_dir / "pt1-prototype-exclusion-report.md"
        shutil.copyfile(artifacts["exclusion_report"], dest)
        artifacts["research_doc"] = dest

    summary_md = generate_exclusion_report_markdown(result)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    print("\n" + summary_md)
    print("\n" + "=" * 80)
    print("  Artifacts Successfully Exported:")
    for name, path in artifacts.items():
        print(f"    - {name.upper():<22}: {path}")
    print("=" * 80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
