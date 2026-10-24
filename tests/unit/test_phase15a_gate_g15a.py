"""Unit test for Phase 15A Gate G15A Milestone Review and Ratification.

Verifies that Gate G15A review document is complete, ratified GO, satisfies all
prerequisites T15.00 through T15.08, and confirms developer loop acceleration.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GATE_REVIEW = REPO_ROOT / "docs" / "pilot" / "gate-g15a-review.md"
MAKEFILE = REPO_ROOT / "Makefile"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_gate_g15a_review_document_exists_and_ratified() -> None:
    """Verify that Gate G15A milestone review exists and is ratified GO."""
    assert GATE_REVIEW.is_file(), f"Missing Gate G15A review document: {GATE_REVIEW}"
    content = GATE_REVIEW.read_text(encoding="utf-8")

    assert "GATE G15A VERDICT: UNCONDITIONAL GO" in content
    assert "Decision `D-026`" in content or "Decision D-026" in content
    assert "Phase 15B" in content


def test_gate_g15a_prerequisites_referenced() -> None:
    """Verify all 9 foundation tasks (T15.00 through T15.08) are recorded."""
    content = GATE_REVIEW.read_text(encoding="utf-8")

    tasks = [
        "T15.00",
        "T15.01",
        "T15.02",
        "T15.03",
        "T15.04",
        "T15.05",
        "T15.06",
        "T15.07",
        "T15.08",
    ]
    for task in tasks:
        assert task in content, f"Prerequisite {task} missing from Gate G15A review"


def test_parallel_loop_acceleration_configured() -> None:
    """Verify pytest-xdist is in pyproject.toml and check-fast in Makefile."""
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    assert "pytest-xdist" in pyproject_text

    makefile_text = MAKEFILE.read_text(encoding="utf-8")
    assert "check-fast:" in makefile_text
    assert "test-fast:" in makefile_text
    assert "pytest -n 4" in makefile_text
