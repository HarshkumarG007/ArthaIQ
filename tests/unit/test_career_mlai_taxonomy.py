"""Unit tests for MLAI family taxonomy ingestion and crosswalk (Task T19.01).

Verifies deterministic ingestion, SHA-256 checksum manifests, licence gating,
and canonical taxonomy integrity for the Machine Learning & AI (MLAI) role family.
"""

from __future__ import annotations

import json
from pathlib import Path

from compintel.career.ingestion import (
    TaxonomyBundle,
    TaxonomyManifest,
    generate_mlai_family_taxonomy,
)
from compintel.career.schema import (
    CompetencyCategory,
    TaxonomyLicense,
    TaxonomySource,
    validate_anti_causal_text,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_TAXONOMY_DIR = REPO_ROOT / "config" / "taxonomy"


def test_deterministic_mlai_ingestion_and_sha256(tmp_path: Path) -> None:
    """Verify that multiple MLAI ingestion passes produce identical SHA-256 checksums."""
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"
    bundle1, p1, m1 = generate_mlai_family_taxonomy(output_dir=dir1)
    bundle2, p2, m2 = generate_mlai_family_taxonomy(output_dir=dir2)

    assert bundle1.manifest.bundle_sha256 == bundle2.manifest.bundle_sha256
    assert p1.read_bytes() == p2.read_bytes()
    assert m1.read_bytes() == m2.read_bytes()


def test_mlai_elements_count_and_categories() -> None:
    """Verify MLAI bundle contains 15 elements spanning all 5 MLAI competency categories."""
    bundle_path = CONFIG_TAXONOMY_DIR / "mlai_family.json"
    manifest_path = CONFIG_TAXONOMY_DIR / "manifest_mlai.json"

    assert bundle_path.is_file(), f"Missing {bundle_path}"
    assert manifest_path.is_file(), f"Missing {manifest_path}"

    bundle_dict = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle = TaxonomyBundle.model_validate(bundle_dict)

    assert bundle.role_family == "MLAI"
    assert len(bundle.elements) == 15

    categories = {el.category for el in bundle.elements}
    assert CompetencyCategory.MATH_OPTIMIZATION in categories
    assert CompetencyCategory.DEEP_LEARNING in categories
    assert CompetencyCategory.MLOPS_INFRASTRUCTURE in categories
    assert CompetencyCategory.EVALUATION_GOVERNANCE in categories
    assert CompetencyCategory.GENERATIVE_ALIGNMENT in categories


def test_mlai_licence_classes_and_attributions() -> None:
    """Verify O*NET elements have CC-BY-4.0 and ESCO elements have EU-OPEN-REUSE."""
    bundle_path = CONFIG_TAXONOMY_DIR / "mlai_family.json"
    bundle_dict = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle = TaxonomyBundle.model_validate(bundle_dict)

    for el in bundle.elements:
        prov = el.provenance
        if prov.source_id == TaxonomySource.ONET_28_0:
            assert prov.license == TaxonomyLicense.CC_BY_4_0
            assert "o*net" in prov.attribution_text.lower()
            assert "trademark" in prov.attribution_text.lower()
        elif prov.source_id == TaxonomySource.ESCO_1_1_1:
            assert prov.license == TaxonomyLicense.EU_OPEN_REUSE
            assert "european commission" in prov.attribution_text.lower()
        else:
            raise AssertionError(f"Unexpected source {prov.source_id}")


def test_mlai_anti_causal_compliance() -> None:
    """Verify that all MLAI taxonomy titles and descriptions satisfy Rule R-CR-01."""
    bundle_path = CONFIG_TAXONOMY_DIR / "mlai_family.json"
    bundle_dict = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle = TaxonomyBundle.model_validate(bundle_dict)

    for el in bundle.elements:
        validate_anti_causal_text(el.title, "title")
        validate_anti_causal_text(el.description, "description")


def test_mlai_manifest_matches_bundle_checksum() -> None:
    """Verify manifest_mlai.json checksum matches bundle checksum exactly."""
    manifest_path = CONFIG_TAXONOMY_DIR / "manifest_mlai.json"
    bundle_path = CONFIG_TAXONOMY_DIR / "mlai_family.json"

    manifest_dict = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = TaxonomyManifest.model_validate(manifest_dict)

    bundle_dict = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle = TaxonomyBundle.model_validate(bundle_dict)

    assert manifest.bundle_sha256 == bundle.manifest.bundle_sha256
    assert manifest.total_elements == 15
    assert bundle.role_family == "MLAI"
