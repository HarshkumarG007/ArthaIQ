"""Unit tests for Practitioner Review and Consensus Report (Task T15.13).

Verifies that the DATA family competency review document exists, satisfies
the two-reviewer protocol, covers all 14 competency nodes, records an acceptable
inter-rater agreement metric (Cohen's Kappa >= 0.80), documents reconciliation,
and marks all clusters as Reviewed.
"""

from __future__ import annotations

import re
from pathlib import Path

from compintel.career.graph import load_data_family_graph
from compintel.career.schema import validate_anti_causal_text

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW_DOC_PATH = REPO_ROOT / "docs" / "pilot" / "competency-review-data-family.md"


def test_review_document_exists_and_identified() -> None:
    """Verify review document exists with correct metadata header and document ID."""
    assert REVIEW_DOC_PATH.is_file(), f"Missing review document at {REVIEW_DOC_PATH}"
    content = REVIEW_DOC_PATH.read_text(encoding="utf-8")

    assert "REV-DATA-FAM-01" in content
    assert "ArthaIQ Career Architect" in content
    assert "Dr. Ananya Sen" in content
    assert "Vikramaditya Joshi" in content


def test_review_covers_all_manifest_competencies() -> None:
    """Verify all 14 nodes from the canonical manifest are evaluated in the report."""
    manifest = load_data_family_graph()
    content = REVIEW_DOC_PATH.read_text(encoding="utf-8")

    for node in manifest.nodes:
        assert node.id in content, f"Node '{node.id}' not evaluated in review report"


def test_cohens_kappa_meets_threshold() -> None:
    """Verify Cohen's Kappa is calculated and meets the >= 0.80 threshold."""
    content = REVIEW_DOC_PATH.read_text(encoding="utf-8")

    # Match kappa value in markdown bold e.g. **0.857**
    match = re.search(r"Cohen's Kappa.*?(\d+\.\d+)", content)
    assert match is not None, "Cohen's Kappa statistic not found in review document"

    kappa = float(match.group(1))
    assert kappa >= 0.80, f"Cohen's Kappa {kappa} does not meet required threshold of 0.80"


def test_all_clusters_marked_reviewed() -> None:
    """Verify that all four clusters are formally marked 'Reviewed'."""
    content = REVIEW_DOC_PATH.read_text(encoding="utf-8")

    clusters = ["CLUSTER-A", "CLUSTER-B", "CLUSTER-C", "CLUSTER-D"]
    for c in clusters:
        assert c in content, f"Cluster {c} missing from review report"

    # Count occurrences of '**Reviewed**'
    reviewed_count = content.count("**Reviewed**")
    assert reviewed_count >= 4, (
        f"Expected at least 4 clusters marked Reviewed, found {reviewed_count}"
    )


def test_disagreement_reconciliation_documented() -> None:
    """Verify that initial discrepancies are explicitly documented and resolved."""
    content = REVIEW_DOC_PATH.read_text(encoding="utf-8")

    assert "Disagreement Reconciliation Log" in content
    assert "Discrepancy 1" in content
    assert "Discrepancy 2" in content
    assert "Panel Consensus" in content


def test_review_document_anti_causal_compliance() -> None:
    """Verify that review document text contains zero causal pay promises."""
    content = REVIEW_DOC_PATH.read_text(encoding="utf-8")
    # Must not raise ValueError
    validate_anti_causal_text(content, "competency-review-data-family.md")
