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
def test_canonical_field_mappings_and_rmd07_compliance() -> None:
    """Verify that all source mappings follow canonical schemas and obey Rule R-MD-07."""
    sources_dir = Path(__file__).resolve().parent.parent.parent / "config" / "sources"
    yaml_files = list(sources_dir.glob("*.yaml"))

    for yf in yaml_files:
        with open(yf, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        mappings = data.get("canonical_field_mappings")
        assert isinstance(mappings, list) and len(mappings) > 0, f"No valid mappings in {yf.name}"

        for m in mappings:
            for k in MANDATORY_MAPPING_KEYS:
                assert k in m, f"Missing key '{k}' in mapping in {yf.name}"

            c_meas = m["canonical_measure"]
            assert c_meas in VALID_CANONICAL_MEASURES, f"Invalid measure '{c_meas}' in {yf.name}"

            # R-MD-07 invariant: Unbundled aggregate CTC must NEVER be admitted to PT1 or PT2
            if c_meas == "ctc_annual" and m.get("unbundling_status") == "unbundled_aggregate":
                targets = m.get("admissible_targets", [])
                assert "PT1" not in targets and "PT2" not in targets, (
                    f"R-MD-07 violation in {yf.name}: unbundled aggregate CTC admitted to PT1/PT2"
                )


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
