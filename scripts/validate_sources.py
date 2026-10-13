#!/usr/bin/env python3
"""Validation script for source licence configs in config/sources/*.yaml.

Verifies:
1. Every YAML file parses cleanly.
2. Mandatory fields exist.
3. Ingestion statuses and licence terms are recorded.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

MANDATORY_FIELDS = [
    "source_id",
    "short_name",
    "long_name",
    "provider",
    "primary_url",
    "country",
    "licence",
    "ingestion_status",
    "pipeline_routing",
    "sqs",
    "sqsf_tier",
]

VALID_STATUSES = {
    "approved",
    "approved_for_design",
    "restricted",
    "rejected",
    "disqualified",
}


def validate_sources(sources_dir: Path) -> int:
    yaml_files = sorted(sources_dir.glob("*.yaml"))
    if not yaml_files:
        print(f"Error: No YAML files found in {sources_dir}")
        return 1

    print(f"Found {len(yaml_files)} source configuration files in {sources_dir}:\n")
    errors: list[str] = []
    status_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}

    for path in yaml_files:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            errors.append(f"PARSE ERROR: {path.name}: {e}")
            continue

        if not isinstance(data, dict):
            errors.append(f"FORMAT ERROR: {path.name}: Root is not a YAML mapping")
            continue

        source_id = data.get("source_id", path.stem)
        status = data.get("ingestion_status", "UNKNOWN")
        tier = data.get("sqsf_tier", "UNKNOWN")
        sqs = data.get("sqs", "UNKNOWN")

        status_counts[status] = status_counts.get(status, 0) + 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        # Check mandatory fields
        for field in MANDATORY_FIELDS:
            if field not in data:
                errors.append(f"MISSING FIELD in {path.name} ({source_id}): '{field}' is required")

        if status not in VALID_STATUSES:
            errors.append(
                f"INVALID STATUS in {path.name} ({source_id}): '{status}' not in {VALID_STATUSES}"
            )

        # Check licence sub-fields
        licence = data.get("licence")
        if isinstance(licence, dict):
            for lic_field in ["spdx_id", "name", "is_open", "permits_research_use"]:
                if lic_field not in licence:
                    errors.append(
                        f"MISSING LICENCE FIELD in {path.name} ({source_id}): 'licence.{lic_field}'"
                    )
        else:
            errors.append(f"INVALID LICENCE in {path.name} ({source_id}): 'licence' must be a dict")

        print(
            f"  [OK] {source_id:<16} | Status: {status:<15} | SQS: {str(sqs):<5} | {path.name}"
        )

    print("\n" + "=" * 80)
    print("INGESTION STATUS BREAKDOWN:")
    for st, count in sorted(status_counts.items()):
        print(f"  - {st:<22}: {count:>2} sources")

    print("\nSQSF TIER BREAKDOWN:")
    for tr, count in sorted(tier_counts.items()):
        print(f"  - {tr:<30}: {count:>2} sources")
    print("=" * 80)

    if errors:
        print(f"\nVALIDATION FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"  ERROR: {err}")
        return 1

    print(f"\nALL {len(yaml_files)} SOURCE CONFIGURATIONS VALIDATED SUCCESSFULLY.")
    return 0


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    sources_dir = base_dir / "config" / "sources"
    sys.exit(validate_sources(sources_dir))
