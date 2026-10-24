"""Unit tests for Taxonomy Licence, Provenance & Attribution (Task T15.06).

Verifies Claim 32 in the evidence register, compliance of statutory attribution
notices, and Pydantic schema validation for taxonomy provenance models.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_CSV = REPO_ROOT / "docs" / "research" / "evidence-register.csv"
SPEC_PATH = REPO_ROOT / "docs" / "research" / "taxonomy-attribution-spec.md"


class TaxonomyProvenance(BaseModel):
    """Pydantic model representing competency node provenance."""

    source_id: Literal["ONET-28.0", "ESCO-1.1.1", "ARTHAIQ-CURATED"]
    source_code: str
    license: Literal["CC-BY-4.0", "EU-OPEN-REUSE", "PROPRIETARY-INTERNAL"]
    attribution_required: bool
    attribution_text: str
    modified_flag: bool
    curator: str
    curated_date: str


def test_claim_32_in_evidence_register() -> None:
    """Verify that Claim 32 is recorded in evidence-register.csv with Tier A audit."""
    assert EVIDENCE_CSV.is_file(), f"Missing evidence register: {EVIDENCE_CSV}"

    with open(EVIDENCE_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 31, f"Expected at least 31 rows, found {len(rows)}"

    claim_32 = next(
        (
            r
            for r in rows
            if "O*NET 28.0" in r["claim_or_decision"] and "ESCO" in r["claim_or_decision"]
        ),
        None,
    )
    assert claim_32 is not None, (
        "Claim 32 for taxonomy licence audit missing from evidence register"
    )
    assert claim_32["evidence_quality"] == "Tier A (Direct Legal & Intellectual Property Audit)"
    assert claim_32["confidence_level"] == "High"
    assert "NQR" in claim_32["claim_or_decision"]


def test_taxonomy_attribution_spec_conformance() -> None:
    """Verify taxonomy attribution spec exists and defines mandatory statutory notices."""
    assert SPEC_PATH.is_file(), f"Missing spec: {SPEC_PATH}"
    content = SPEC_PATH.read_text(encoding="utf-8")

    # Verify O*NET CC BY 4.0 terms and statutory attribution copy
    assert "CC BY 4.0" in content
    assert "U.S. Department of Labor, Employment and Training Administration" in content
    assert "USDOL/ETA" in content
    assert "ArthaIQ has modified all or some of this information" in content

    # Verify ESCO European Commission terms
    assert "ESCO v1.1.1" in content
    assert "Commission Decision 2011/833/EU" in content

    # Verify NQR restriction
    assert "Restricted / Disqualified from Direct Database Redistribution" in content


def test_taxonomy_provenance_schema_validation() -> None:
    """Verify that sample provenance records validate against TaxonomyProvenance contract."""
    onet_prov = TaxonomyProvenance(
        source_id="ONET-28.0",
        source_code="15-2051.01",
        license="CC-BY-4.0",
        attribution_required=True,
        attribution_text="O*NET 28.0 by USDOL/ETA, used under CC BY 4.0; modified by ArthaIQ.",
        modified_flag=True,
        curator="CompIntel Engineering",
        curated_date="2026-10-24",
    )
    assert onet_prov.source_id == "ONET-28.0"
    assert onet_prov.attribution_required is True

    esco_prov = TaxonomyProvenance(
        source_id="ESCO-1.1.1",
        source_code="S1.2.3",
        license="EU-OPEN-REUSE",
        attribution_required=True,
        attribution_text="European Skills, Competences and Occupations (ESCO) v1.1.1.",
        modified_flag=False,
        curator="CompIntel Engineering",
        curated_date="2026-10-24",
    )
    assert esco_prov.source_id == "ESCO-1.1.1"
    assert esco_prov.license == "EU-OPEN-REUSE"
