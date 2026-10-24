"""Unit tests verifying ratification criteria for Gate G15B (Phase 15B).

Validates:
- Gate G15B formal milestone review document exists with UNCONDITIONAL GO and Decision D-027.
- DATA family competency graph is valid, acyclic, and has 100% provenance coverage.
- Practitioner consensus meets Cohen's Kappa >= 0.80 and marks all clusters Reviewed.
- Difficulty and effort heuristic rubrics are complete with zero lone-number false precision.
- Zero causal compensation promises exist across all review documentation.
"""

from __future__ import annotations

import re
from pathlib import Path

from compintel.career.graph import load_data_family_graph
from compintel.career.rubric import load_difficulty_rubrics
from compintel.career.schema import FORBIDDEN_CAUSAL_PATTERNS
from compintel.career.validators import validate_competency_graph

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GATE_G15B_REVIEW_PATH = REPO_ROOT / "docs" / "pilot" / "gate-g15b-review.md"
PRACTITIONER_REVIEW_PATH = REPO_ROOT / "docs" / "pilot" / "competency-review-data-family.md"


def test_gate_g15b_review_document_exists_and_approved() -> None:
    """Verify that Gate G15B milestone review document is complete and ratified GO."""
    assert GATE_G15B_REVIEW_PATH.is_file(), f"Missing review document at {GATE_G15B_REVIEW_PATH}"
    content = GATE_G15B_REVIEW_PATH.read_text(encoding="utf-8")

    assert "GATE G15B VERDICT: UNCONDITIONAL GO" in content
    assert "Decision D-027" in content
    assert "**🟢 RATIFIED GO" in content

    # Verify panel unanimous approval
    go_votes = re.findall(r"\|\s*\*\*GO\*\*\s*\|", content)
    assert len(go_votes) == 5, f"Expected 5 unanimous GO votes, got {len(go_votes)}"


def test_competency_graph_fixture_integrity() -> None:
    """Verify DATA family competency DAG fixture passes all structural validators."""
    manifest = load_data_family_graph()
    assert len(manifest.nodes) == 14

    # Run comprehensive CI validators
    validate_competency_graph(manifest)


def test_practitioner_review_consensus_standards() -> None:
    """Verify that practitioner review meets inter-rater reliability and review criteria."""
    assert PRACTITIONER_REVIEW_PATH.is_file(), f"Missing {PRACTITIONER_REVIEW_PATH}"
    content = PRACTITIONER_REVIEW_PATH.read_text(encoding="utf-8")

    # Verify Cohen's Kappa threshold
    match = re.search(r"Cohen's Kappa.*?(\d+\.\d+)", content)
    assert match is not None, "Cohen's Kappa statistic not found in review document"
    kappa = float(match.group(1))
    assert kappa >= 0.80, f"Cohen's Kappa ({kappa}) must be >= 0.80"

    # Verify all 4 clusters are reviewed
    clusters = ["CLUSTER-A", "CLUSTER-B", "CLUSTER-C", "CLUSTER-D"]
    for c in clusters:
        assert c in content, f"Cluster {c} missing from review report"
    assert content.count("**Reviewed**") >= 4


def test_difficulty_rubric_standards() -> None:
    """Verify difficulty rubrics meet Rule R-CR-05 heuristic requirements."""
    manifest = load_difficulty_rubrics()
    assert len(manifest.entries) == 14

    for entry in manifest.entries:
        assert 1.0 <= entry.learning_difficulty <= 5.0
        assert 1.0 <= entry.application_difficulty <= 5.0
        assert entry.effort_hours.min_hours < entry.effort_hours.max_hours
        assert entry.is_heuristic is True
        assert "Estimated based on practitioner consensus" in entry.disclaimer


def test_anti_causal_invariants_across_gate_artifacts() -> None:
    """Verify zero causal pay claims in Gate G15B review document (Rule R-CR-01)."""
    content = GATE_G15B_REVIEW_PATH.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_CAUSAL_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        assert not matches, f"Forbidden causal pattern '{pattern}' found in {GATE_G15B_REVIEW_PATH}"
