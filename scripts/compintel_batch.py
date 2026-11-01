"""ArthaIQ Enterprise Batch CLI Tool (Phase 26, Task T26.02).

Command-line tool for bulk compensation estimation across Software Engineering,
Data Science, and ML/AI engineering profiles.

Usage:
  python scripts/compintel_batch.py --input profiles.csv --output results.json
  python scripts/compintel_batch.py -i candidates.json -o evaluated.csv --stream
  python scripts/compintel_batch.py --input large_roster.csv --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from compintel.client.batch import (
    BatchClient,
    export_results_to_csv,
    export_results_to_json,
    load_profiles_from_csv,
    load_profiles_from_json,
)
from compintel.serving.types import (
    BatchEstimateItem,
    BatchEstimateResponse,
    BatchEstimateSummary,
)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for compintel-batch."""
    parser = argparse.ArgumentParser(
        prog="compintel-batch",
        description="ArthaIQ Enterprise Batch Compensation Estimation CLI Tool.",
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Path to input file containing candidate profiles (.csv, .json, or .ndjson).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional destination path for enriched results (.json or .csv).",
    )
    parser.add_argument(
        "-u",
        "--url",
        default="http://localhost:8000",
        help="Base URL for the ArthaIQ serving endpoint (default: http://localhost:8000).",
    )
    parser.add_argument(
        "-k",
        "--api-key",
        default=None,
        help="Optional API key for authenticated endpoints (X-API-Key).",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Use memory-efficient NDJSON streaming mode.",
    )
    parser.add_argument(
        "--coverage",
        type=float,
        default=0.80,
        help="Conformal nominal coverage probability (default: 0.80).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Maximum profiles per HTTP batch request (default: 500).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and display summary without executing HTTP inference.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute compintel-batch CLI workflow."""
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = args.input
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1

    print("=" * 80)
    print("ArthaIQ Enterprise Batch Compensation Estimation CLI")
    print("=" * 80)
    print(f"Loading input: {input_path}...")

    # Load profiles
    try:
        if input_path.suffix.lower() == ".csv":
            profiles = load_profiles_from_csv(input_path)
        else:
            profiles = load_profiles_from_json(input_path)
    except Exception as exc:
        print(f"[ERROR] Failed to parse input file: {exc}", file=sys.stderr)
        return 1

    print(f"Successfully loaded {len(profiles):,} candidate profile(s).")

    if args.dry_run:
        print("\n[DRY RUN] Input validation passed.")
        print(f"Sample Profile 1: {profiles[0].model_dump_json() if profiles else 'None'}")
        print("Dry run complete; 0 HTTP requests sent.")
        return 0

    client = BatchClient(
        base_url=args.url,
        api_key=args.api_key,
        timeout=120.0,
    )

    t_start = time.perf_counter()

    try:
        if args.stream:
            print(f"\nExecuting NDJSON streaming batch inference (coverage={args.coverage:.2f})...")
            items: list[BatchEstimateItem] = []
            for item in client.stream_batch(
                profiles, nominal_coverage=args.coverage, chunk_size=args.chunk_size
            ):
                items.append(item)
                if len(items) % 100 == 0 or len(items) == len(profiles):
                    print(f"  Processed {len(items):,} / {len(profiles):,} items...", end="\r")
            print()

            elapsed = max(time.perf_counter() - t_start, 0.0001)
            successful = sum(1 for it in items if it.support_status == "SUPPORTED")
            abstained = len(items) - successful
            throughput = len(items) / elapsed

            summary = BatchEstimateSummary(
                total_records=len(items),
                successful_estimates=successful,
                abstained_count=abstained,
                duration_seconds=round(elapsed, 4),
                throughput_predictions_per_sec=round(throughput, 2),
                nominal_coverage=args.coverage,
                as_of_date=time.strftime("%Y-%m-%d"),
                disclaimer="Empirical statistical distribution. Not an appraisal, offer, or guarantee (CPA 2019).",
            )
            response = BatchEstimateResponse(summary=summary, items=items)
        else:
            print(
                f"\nExecuting bulk REST batch inference in chunks of {args.chunk_size} (coverage={args.coverage:.2f})..."
            )
            response = client.estimate_batch(
                profiles, nominal_coverage=args.coverage, chunk_size=args.chunk_size
            )
    except Exception as exc:
        print(f"\n[ERROR] Batch estimation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()

    # Print summary
    print("\n" + "-" * 80)
    print("Execution Summary:")
    print(f"  Total Records:      {response.summary.total_records:,}")
    print(f"  Supported Profiles: {response.summary.successful_estimates:,}")
    print(f"  Abstained Profiles: {response.summary.abstained_count:,}")
    print(f"  Duration:           {response.summary.duration_seconds:.3f} seconds")
    print(f"  Throughput:         {response.summary.throughput_predictions_per_sec:,.1f} pred/sec")
    print(f"  Nominal Coverage:   {response.summary.nominal_coverage * 100:.0f}%")
    print("-" * 80)

    # Export output if requested
    if args.output:
        out_path = args.output
        if out_path.suffix.lower() == ".csv":
            export_results_to_csv(response.items, out_path)
            print(f"Results exported to CSV: {out_path}")
        else:
            export_results_to_json(response, out_path)
            print(f"Results exported to JSON: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
