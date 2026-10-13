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
    "canonical_field_mappings",
]

VALID_STATUSES = {
    "approved",
    "approved_for_design",
    "restricted",
    "rejected",
    "disqualified",
}

MANDATORY_MAPPING_KEYS = [
    "source_field",
    "canonical_measure",
    "comp_type",
    "period",
    "tax_basis",
    "admissible_targets",
    "unbundling_status",
]

VALID_CANONICAL_MEASURES = {
    "guaranteed_cash_annual",
    "basic_salary_annual",
    "fixed_allowances_annual",
    "ctc_annual",
    "total_comp_annual",
    "advertised_min_annual",
    "advertised_max_annual",
    "advertised_range_annual",
    "take_home_annual",
    "variable_cash_annual",
    "equity_annualized_grant",
    "employer_contributions_annual",
    "prevailing_wage_annual",
    "sampling_weight",
    "experience_months",
    "cpi_deflator",
    "spot_fx_rate",
    "skill_taxonomy",
    "non_comp_feature",
    "quarantined",
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

        # Validate canonical field mappings (Task T2.05 / R-MD-07)
        mappings = data.get("canonical_field_mappings")
        if not isinstance(mappings, list) or len(mappings) == 0:
            errors.append(
                f"INVALID MAPPINGS in {path.name} ({source_id}): 'canonical_field_mappings' must be a non-empty list"
            )
        else:
            for idx, mapping in enumerate(mappings):
                if not isinstance(mapping, dict):
                    errors.append(f"MAPPING NOT A DICT in {path.name} ({source_id}) at index {idx}")
                    continue
                for m_key in MANDATORY_MAPPING_KEYS:
                    if m_key not in mapping:
                        errors.append(
                            f"MISSING MAPPING KEY in {path.name} ({source_id}) mapping {idx}: '{m_key}' is required"
                        )
                c_meas = mapping.get("canonical_measure")
                if c_meas not in VALID_CANONICAL_MEASURES:
                    errors.append(
                        f"INVALID CANONICAL MEASURE in {path.name} ({source_id}) mapping {idx}: '{c_meas}'"
                    )

                # Rule R-MD-07 enforcement: Unbundled CTC cannot be admitted to PT1/PT2
                unbundling = mapping.get("unbundling_status")
                targets = mapping.get("admissible_targets", [])
                if (
                    c_meas == "ctc_annual"
                    and unbundling == "unbundled_aggregate"
                    and any(t in {"PT1", "PT2"} for t in targets)
                ):
                    errors.append(
                        f"R-MD-07 VIOLATION in {path.name} ({source_id}): unbundled aggregate CTC admitted to PT1/PT2 targets: {targets}"
                    )
                if c_meas == "quarantined" and not mapping.get("exclusion_reason"):
                    errors.append(
                        f"MISSING EXCLUSION REASON in {path.name} ({source_id}) for quarantined field '{mapping.get('source_field')}'"
                    )

        print(
            f"  [OK] {source_id:<16} | Status: {status:<15} | SQS: {str(sqs):<5} | Mapped: {len(mappings or []):<2} | {path.name}"
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
