"""Unit tests verifying source configuration validity in config/sources/*.yaml."""

from pathlib import Path

import pytest
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


@pytest.mark.unit
def test_all_sources_parse_and_have_mandatory_fields() -> None:
    """Verify that every config/sources/*.yaml file parses and includes mandatory fields."""
    sources_dir = Path(__file__).resolve().parent.parent.parent / "config" / "sources"
    assert sources_dir.exists(), f"Directory not found: {sources_dir}"

    yaml_files = list(sources_dir.glob("*.yaml"))
    assert len(yaml_files) >= 20, f"Expected >= 20 configs, found {len(yaml_files)}"

    for yf in yaml_files:
        with open(yf, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict), f"{yf.name} root is not a mapping"

        for field in MANDATORY_FIELDS:
            assert field in data, f"Missing '{field}' in {yf.name}"

        status = data.get("ingestion_status")
        assert status in VALID_STATUSES, f"Invalid status '{status}' in {yf.name}"

        licence = data.get("licence")
        assert isinstance(licence, dict), f"Licence must be dict in {yf.name}"
        for lic_field in ["spdx_id", "name", "is_open", "permits_research_use"]:
            assert lic_field in licence, f"Missing '{lic_field}' in licence for {yf.name}"


@pytest.mark.unit
def test_source_configs_distribution() -> None:
    """Verify that source configs have expected distribution across statuses."""
    sources_dir = Path(__file__).resolve().parent.parent.parent / "config" / "sources"
    yaml_files = list(sources_dir.glob("*.yaml"))

    statuses = set()
    for yf in yaml_files:
        with open(yf, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            statuses.add(data.get("ingestion_status"))

    assert "approved" in statuses
    assert "rejected" in statuses
    assert "restricted" in statuses
