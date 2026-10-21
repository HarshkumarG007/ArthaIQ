"""Unit tests for Gate G10 Production Decision and General Availability Ratification."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_gate_g10_doc_exists_and_complete() -> None:
    """Verify docs/pilot/gate-g10-production-decision.md exists and is complete."""
    decision_path = REPO_ROOT / "docs" / "pilot" / "gate-g10-production-decision.md"
    assert decision_path.is_file(), f"Missing {decision_path}"
    content = decision_path.read_text(encoding="utf-8")

    required_sections = [
        "# Gate G10 Production Decision & General Availability Ratification",
        "## 1. Executive Determination",
        "## 2. Review Panel Membership & Signatures",
        "## 3. Audit of Pilot Plan Section 6.1 Unconditional GO Criteria",
        "## 4. Audit of Pilot Plan Section 6.2 Mandatory NO-GO Triggers",
        "## 5. Adversarial Review Checklist (Rule R-MD-05, Section 15)",
        "## 6. Release Authorization & Next Steps",
    ]
    for section in required_sections:
        assert section in content, f"Missing section '{section}' in decision doc"

    # Verify all 5 panel roles and their unanimous GO vote
    panel_roles = [
        "Lead Quantitative ML Engineer",
        "India Compensation Economics Specialist",
        "Product & UX Design Lead",
        "Data Protection & Legal Governance Counsel",
        "Platform / SRE Operations Lead",
    ]
    for role in panel_roles:
        assert role in content, f"Missing panel role '{role}' in decision doc"

    assert content.count("| **GO** | 2026-10-21 |") >= 5

    # Verify all 14 adversarial checklist questions are answered
    for q_idx in range(1, 15):
        assert f"{q_idx}. **" in content, f"Checklist question {q_idx} not found in decision doc"


def test_gate_g10_criteria_and_triggers_audited() -> None:
    """Verify that pilot scorecard criteria and no-go triggers are thoroughly audited."""
    decision_path = REPO_ROOT / "docs" / "pilot" / "gate-g10-production-decision.md"
    content = decision_path.read_text(encoding="utf-8")

    # 5 Criteria
    assert "Criterion 1" in content
    assert "Criterion 2" in content
    assert "Criterion 3" in content
    assert "Criterion 4" in content
    assert "Criterion 5" in content

    # 3 No-Go triggers checked
    assert "Coverage Degradation" in content
    assert "Comprehension Collapse" in content
    assert "PII Disclosure or Erasure Cascade Failure" in content
    assert "Trigger did not fire." in content


def test_gate_g10_verdict_and_authorization() -> None:
    """Verify unconditional GO verdict and General Availability release authorization."""
    decision_path = REPO_ROOT / "docs" / "pilot" / "gate-g10-production-decision.md"
    content = decision_path.read_text(encoding="utf-8")

    assert "UNCONDITIONAL GO FOR GENERAL AVAILABILITY (GA)" in content
    assert "ArthaIQ v1.0.0 is cleared for public production serving." in content
    assert "Phase 11 (Production Hardening & Slice Calibration)" in content
    assert "CHARTER-EXP-13" in content
    assert "CHARTER-EXP-16" in content


def test_memory_ratification_and_sync() -> None:
    """Verify memory.md and docs/memory.md are synchronized and reflect G10 GO ratification."""
    root_mem = (REPO_ROOT / "memory.md").read_text(encoding="utf-8")
    docs_mem = (REPO_ROOT / "docs" / "memory.md").read_text(encoding="utf-8")

    assert root_mem == docs_mem, "memory.md and docs/memory.md are out of sync"

    # Section 1 & Section 3
    assert "Gate G10 ratified **GO** (2026-10-21)" in root_mem
    assert "NEXT: Phase 11 Production Hardening & Slice Calibration" in root_mem
    assert "| Last completed task | Gate G10 (critical): production decision |" in root_mem
    expected_next_task = (
        "| Next task | Phase 11 (Production Hardening & Slice Calibration: EXP-13, EXP-16) |"
    )
    assert expected_next_task in root_mem
    assert "G10 — GO: Production Launch Ratified" in root_mem

    # Section 4 Table
    assert "| G10 | **GO** | 2026-10-21 |" in root_mem

    # Section 4.7
    assert "## 4.7 Gate G10 Adversarial Review Checklist (Rule R-MD-05, Section 15)" in root_mem
    for q_idx in range(1, 15):
        assert f"{q_idx}. **" in root_mem, f"Question {q_idx} missing from Section 4.7 in memory.md"

    # Section 5 Decision D-021
    assert "| D-021 | 2026-10-21 | Production Decision & Gate G10 Ratification:" in root_mem
    assert "Accepted" in root_mem

    # Section 12 Session Log
    assert "| 2026-10-21 | Gate G10 |" in root_mem


def test_task_breakdown_g10_and_sync() -> None:
    """Verify task.md and docs/task.md are synchronized and record G10 GO ratification."""
    root_task = (REPO_ROOT / "task.md").read_text(encoding="utf-8")
    docs_task = (REPO_ROOT / "docs" / "task.md").read_text(encoding="utf-8")

    assert root_task == docs_task, "task.md and docs/task.md are out of sync"
    expected_status = (
        "v1.1 (Phases 0-10 complete; Gates G0-G10 ratified; Production Launch Complete)"
    )
    assert expected_status in root_task
    expected_next = "**NEXT TASK: Phase 11: Production Hardening & Slice Calibration"
    assert expected_next in root_task
    assert "**Gate G10 (critical):** production decision. **GO ratified 2026-10-21**" in root_task
    assert "| 2026-10-21 | 1.1     | Phase 10 complete; Gate G10 ratified GO;" in root_task
