#!/usr/bin/env python3
"""CLI script to build, validate, and package the ArthaIQ Champion Model Bundle (T5.08).

Evaluates candidate models along the benchmark ladder (Rung A baseline, Rung B linear,
Rung E quantile, Rung F conformal) against pre-registered thresholds in v1.yaml,
promotes Rung F as Champion, packages the deployable ModelBundle with cryptographic
manifests, and exports audit reports.

Adheres strictly to:
- Rule R-MD-01: Benchmark ladder promotion rules (ADR-0004).
- Rule R-MD-02: Strict isolation of final 'test' partition (locked for make final-eval).
- Rule R-MD-08 / R-EV-07: Mandatory abstention when evidence is thin (N < 10).
- Rule R-MD-11: Strict synthetic data isolation from production artifacts.
- Rule R-MD-14: Model promotion requires pre-registered thresholds met, model card,
  reproducibility, and rollback capability.
- Rule R-UQ-01: No lone numbers; always P10, P50, P90 with definitions.
- Rule R-UQ-02: Abstention is a valid, designed result returning HTTP 200 payload.

Usage:
    uv run python scripts/build_champion_bundle.py
        [--canonical-path <path>]
        [--output-dir <path>]
        [--model-card-path <path>]
        [--report-md <path>]
        [--report-json <path>]
        [--seed <int>]
        [--allow-synthetic]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compintel.errors import CompIntelError
from compintel.evaluation.champion import build_champion_bundle
from compintel.logging import get_logger

logger = get_logger(__name__)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for champion bundle builder."""
    parser = argparse.ArgumentParser(
        description="Build, validate, and package ArthaIQ Champion Model Bundle."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/champion_v0",
        help="Target directory to package the self-contained model bundle.",
    )
    parser.add_argument(
        "--model-card-path",
        default="docs/model-cards/model-card-v0.md",
        help="Path to model card markdown file.",
    )
    parser.add_argument(
        "--report-md",
        default="experiments/results/champion_selection_v1.md",
        help="Path to save champion selection markdown audit report.",
    )
    parser.add_argument(
        "--report-json",
        default="experiments/results/champion_selection_v1.json",
        help="Path to save champion selection JSON summary.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for model training and deterministic splitting.",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Allow synthetic data (strictly for testing, violates R-MD-11 if production).",
    )
    return parser.parse_args(args)


def main(argv: list[str] | None = None) -> int:
    """Execute champion bundle build pipeline."""
    args = parse_args(argv)

    print("================================================================================")
    print(" ArthaIQ Champion Selection & Model Bundle Builder (T5.08)")
    print("================================================================================")
    print(f"  Canonical data:    {args.canonical_path}")
    print(f"  Output directory:  {args.output_dir}")
    print(f"  Model card:        {args.model_card_path}")
    print(f"  Report Markdown:   {args.report_md}")
    print(f"  Report JSON:       {args.report_json}")
    print(f"  Random seed:       {args.seed}")
    print(f"  Allow synthetic:   {args.allow_synthetic}")
    print("================================================================================")

    try:
        report, bundle = build_champion_bundle(
            canonical_path=args.canonical_path,
            output_dir=args.output_dir,
            model_card_path=args.model_card_path,
            report_md_path=args.report_md,
            report_json_path=args.report_json,
            seed=args.seed,
            allow_synthetic=args.allow_synthetic,
        )

        print("\nChampion Selection Completed Successfully:")
        print(f"  Champion Candidate:  {report.champion_candidate_id}")
        print(f"  Rung:                {report.champion_rung}")
        print(f"  Verdict:             {report.promotion_verdict}")
        print(f"  Coverage:            {report.champion_metrics['coverage_80']:.2%}")
        print(f"  Point MAE:           {report.champion_metrics['point_mae_lpa']:.2f} LPA")
        print(f"  Mean Width:          {report.champion_metrics['mean_width_lpa']:.2f} LPA")
        print(f"  Crossing Rate:       {report.champion_metrics['crossing_rate']:.2%}")
        print(f"  Calibration Error:   {report.champion_metrics['mean_calibration_error']:.4f}")
        print(f"  Bundle Hash:         {bundle.metadata.bundle_sha256[:16]}...")
        print(f"  Files Manifest:      {len(bundle.metadata.files_manifest)} artifacts packaged")
        print("\nAudit reports generated:")
        print(f"  - Markdown: {Path(args.report_md).resolve()}")
        print(f"  - JSON:     {Path(args.report_json).resolve()}")
        return 0

    except CompIntelError as exc:
        print(f"\n[ERROR] CompIntel build failed: {exc}", file=sys.stderr)
        logger.exception("champion_bundle_build_failed", error=str(exc))
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        logger.exception("champion_bundle_build_unexpected_error", error=str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
