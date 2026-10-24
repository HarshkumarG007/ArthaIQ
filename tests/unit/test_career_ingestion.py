"""Unit tests for Career Architect taxonomy ingestion and crosswalk (Task T15.11).

Verifies deterministic ingestion, SHA-256 checksum manifests, licence gating,
and canonical taxonomy integrity for the DATA role family.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compintel.career.ingestion import (
    TaxonomyBundle,
    TaxonomyManifest,
    build_taxonomy_element,
    enforce_taxonomy_licence_gate,
    generate_data_family_taxonomy,
)
from compintel.career.schema import (
    CompetencyCategory,
    TaxonomyLicense,
    TaxonomySource,
)
from compintel.career.validators import ProvenanceComplianceError

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_TAXONOMY_DIR = REPO_ROOT / "config" / "taxonomy"


def test_deterministic_ingestion_and_sha256(tmp_path: Path) -> None:
    """Verify that multiple ingestion passes produce identical SHA-256 checksums."""
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"
    bundle1, p1, m1 = generate_data_family_taxonomy(output_dir=dir1)
    bundle2, p2, m2 = generate_data_family_taxonomy(output_dir=dir2)

    assert bundle1.manifest.bundle_sha256 == bundle2.manifest.bundle_sha256
    assert p1.read_bytes() == p2.read_bytes()
    assert m1.read_bytes() == m2.read_bytes()


def test_licence_gate_rejects_unapproved_source() -> None:
    """Verify that attempting to ingest an unapproved taxonomy source raises error."""
    with pytest.raises(ProvenanceComplianceError, match="not an approved open labour framework"):
        enforce_taxonomy_licence_gate(
            source_id="NQR-INDIA",  # type: ignore[arg-type]
            license_type=TaxonomyLicense.PROPRIETARY_INTERNAL,
            attribution_text="National Qualifications Register",
        )


def test_licence_gate_rejects_mismatched_license() -> None:
    """Verify that mismatched licences for approved sources raise error."""
    with pytest.raises(ProvenanceComplianceError, match="Invalid licence for O\\*NET"):
        enforce_taxonomy_licence_gate(
            source_id=TaxonomySource.ONET_28_0,
            license_type=TaxonomyLicense.EU_OPEN_REUSE,
            attribution_text="Source: O*NET 28.0 (USDOL/ETA).",
        )

    with pytest.raises(ProvenanceComplianceError, match="Invalid licence for ESCO"):
        enforce_taxonomy_licence_gate(
            source_id=TaxonomySource.ESCO_1_1_1,
            license_type=TaxonomyLicense.CC_BY_4_0,
            attribution_text="Source: ESCO v1.1.1",
        )


def test_licence_gate_rejects_missing_onet_trademark() -> None:
    """Verify O*NET attribution text requires trademark notice."""
    with pytest.raises(ProvenanceComplianceError, match="missing mandatory trademark notice"):
        enforce_taxonomy_licence_gate(
            source_id=TaxonomySource.ONET_28_0,
            license_type=TaxonomyLicense.CC_BY_4_0,
            attribution_text="Source: USDOL dataset without required mark.",
        )


def test_taxonomy_element_anti_causal_enforcement() -> None:
    """Verify that attempting to build an element with causal pay promises fails."""
    raw_causal = {
        "code": "15-2051.01.T99",
        "title": "Machine Learning",
        "description": "Learning this raises compensation by ₹5 LPA immediately.",
        "category": CompetencyCategory.STATISTICAL_MODELING,
    }

    with pytest.raises(ValueError, match="Rule R-CR-01 and CPA 2019"):
        build_taxonomy_element(
            raw_record=raw_causal,
            source_id=TaxonomySource.ONET_28_0,
            license_type=TaxonomyLicense.CC_BY_4_0,
            attribution_text="Source: O*NET 28.0. O*NET® is a trademark.",
        )


def test_ingested_data_family_json_structure() -> None:
    """Verify config/taxonomy/data_family.json matches schema and manifest."""
    bundle_path = CONFIG_TAXONOMY_DIR / "data_family.json"
    manifest_path = CONFIG_TAXONOMY_DIR / "manifest.json"

    assert bundle_path.is_file()
    assert manifest_path.is_file()

    bundle_dict = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle = TaxonomyBundle.model_validate(bundle_dict)

    manifest_dict = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = TaxonomyManifest.model_validate(manifest_dict)

    assert bundle.manifest.bundle_sha256 == manifest.bundle_sha256
    assert bundle.manifest.total_elements == len(bundle.elements)
    assert len(bundle.elements) >= 14

    # Verify both sources are present
    sources = {el.provenance.source_id for el in bundle.elements}
    assert TaxonomySource.ONET_28_0 in sources
    assert TaxonomySource.ESCO_1_1_1 in sources
