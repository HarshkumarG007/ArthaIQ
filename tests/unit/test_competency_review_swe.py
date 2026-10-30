"""Unit tests for SWE Practitioner Review & Consensus Report (Task T16.04).

Verifies that the SWE family competency review document exists, satisfies
the two-reviewer protocol, covers all 15 competency nodes, records an acceptable
inter-rater agreement metric (Cohen's Kappa >= 0.80), documents reconciliation,
and marks all clusters as Reviewed.
"""

from __future__ import annotations

import re
from pathlib import Path

from compintel.career.schema import validate_anti_causal_text
from compintel.career.swe_graph import load_swe_family_graph

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SWE_REVIEW_DOC_PATH = REPO_ROOT / "docs" / "pilot" / "competency-review-swe-family.md"


def test_swe_review_document_exists_and_identified() -> None:
    """Verify review document exists with correct metadata header and document ID."""
    assert SWE_REVIEW_DOC_PATH.is_file(), f"Missing review document at {SWE_REVIEW_DOC_PATH}"
    content = SWE_REVIEW_DOC_PATH.read_text(encoding="utf-8")

    assert "REV-SWE-FAM-01" in content
    assert "ArthaIQ Career Architect" in content
    assert "Dr. Ananya Sen" in content
    assert "Vikramaditya Joshi" in content


def test_swe_review_covers_all_manifest_competencies() -> None:
    """Verify all 15 nodes from the canonical manifest are evaluated in the report."""
    manifest = load_swe_family_graph()
    content = SWE_REVIEW_DOC_PATH.read_text(encoding="utf-8")

    for node in manifest.nodes:
        assert node.id in content, f"Node '{node.id}' not evaluated in review report"


def test_swe_cohens_kappa_meets_threshold() -> None:
    """Verify Cohen's Kappa is calculated and meets the >= 0.80 threshold."""
    content = SWE_REVIEW_DOC_PATH.read_text(encoding="utf-8")

    match = re.search(r"Cohen's Kappa.*?(\d+\.\d+)", content)
    assert match is not None, "Cohen's Kappa statistic not found in review document"

    kappa = float(match.group(1))
    assert kappa >= 0.80, f"Cohen's Kappa {kappa} does not meet required threshold of 0.80"


def test_all_swe_clusters_marked_reviewed() -> None:
    """Verify that all five clusters are formally marked 'Reviewed'."""
    content = SWE_REVIEW_DOC_PATH.read_text(encoding="utf-8")

    clusters = [
        "CLUSTER-SWE-A",
        "CLUSTER-SWE-B",
        "CLUSTER-SWE-C",
        "CLUSTER-SWE-D",
        "CLUSTER-SWE-E",
    ]
    for c in clusters:
        assert c in content, f"Cluster {c} missing from review report"

    reviewed_count = content.count("**Reviewed**")
    assert reviewed_count >= 5, (
        f"Expected at least 5 clusters marked Reviewed, found {reviewed_count}"
    )


def test_swe_disagreement_reconciliation_documented() -> None:
    """Verify that initial discrepancies are explicitly documented and resolved."""
    content = SWE_REVIEW_DOC_PATH.read_text(encoding="utf-8")

    assert "Disagreement Reconciliation Log" in content
    assert "Discrepancy 1" in content
    assert "Discrepancy 2" in content
    assert "Panel Consensus" in content


def test_swe_review_document_anti_causal_compliance() -> None:
    """Verify that review document text contains zero causal pay promises."""
    content = SWE_REVIEW_DOC_PATH.read_text(encoding="utf-8")
    validate_anti_causal_text(content, "competency-review-swe-family.md")
