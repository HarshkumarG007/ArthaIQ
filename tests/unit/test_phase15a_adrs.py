"""Unit tests for Phase 15A Foundational ADRs (Task T15.04).

Verifies ADR-0010, ADR-0011, ADR-0012, and ADR-0013 existence, accepted status,
canonical indexing in architecture.md, and core invariant coverage.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ADR_DIR = REPO_ROOT / "docs" / "adr"

EXPECTED_ADRS = {
    "ADR-0010": ("ADR-0010-llm-boundary-and-anti-causal-invariants.md", "R-CR-01", "R-SC-07"),
    "ADR-0011": ("ADR-0011-competency-graph-and-evidence-ledger.md", "R-CR-03", "R-CR-04"),
    "ADR-0012": (
        "ADR-0012-local-first-profile-and-privacy-architecture.md",
        "R-CR-12",
        "IndexedDB",
    ),
    "ADR-0013": ("ADR-0013-deterministic-scenario-scoring.md", "R-CR-08", "R-CR-11"),
}


def test_phase15a_adrs_exist_and_accepted() -> None:
    """Verify that all Phase 15A ADR files exist and have status 'Accepted'."""
    assert ADR_DIR.is_dir(), f"Missing ADR directory: {ADR_DIR}"

    for _adr_id, (filename, rule1, rule2) in EXPECTED_ADRS.items():
        adr_file = ADR_DIR / filename
        assert adr_file.is_file(), f"Missing ADR file: {filename}"

        content = adr_file.read_text(encoding="utf-8")
        assert "| Status | **Accepted** |" in content, f"{filename} is not Accepted"
        assert rule1 in content, f"{filename} missing expected rule/term '{rule1}'"
        assert rule2 in content, f"{filename} missing expected rule/term '{rule2}'"


def test_phase15a_adrs_indexed_in_architecture() -> None:
    """Verify ADR-0010 through ADR-0013 are indexed in architecture.md."""
    arch_file = REPO_ROOT / "architecture.md"
    assert arch_file.is_file()
    content = arch_file.read_text(encoding="utf-8")

    for adr_num in ["0010", "0011", "0012", "0013"]:
        assert f"| {adr_num} |" in content, f"ADR-{adr_num} missing in architecture.md index table"
