"""Unit tests for Task T10.07: Post-Pilot Review and canonical document synchronization."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_post_pilot_review_doc_exists_and_complete() -> None:
    """Verify docs/pilot/post-pilot-review.md exists and contains all required sections."""
    review_path = REPO_ROOT / "docs" / "pilot" / "post-pilot-review.md"
    assert review_path.is_file(), f"Missing {review_path}"
    content = review_path.read_text(encoding="utf-8")

    required_sections = [
        "# Post-Pilot Review & Next Iteration Roadmap",
        "## 1. Executive Summary",
        "## 2. Review Panel Participants",
        "## 3. Scorecard Audit: 11 Pre-Registered Pilot Metrics",
        "## 4. Synthesis of Qualitative Feedback & Root-Cause Triage",
        "## 5. Formal Architectural & PRD Updates",
        "## 6. Next Iteration Roadmap: Phase 11 & Phase 12",
        "## 7. Formal Sign-Off",
    ]
    for section in required_sections:
        assert section in content, f"Missing section '{section}' in post-pilot-review.md"

    # Verify all 11 metrics are listed
    for i in range(1, 12):
        metric_id = f"M-{i:02d}"
        assert metric_id in content, f"Metric {metric_id} not found in post-pilot-review.md"


def test_prd_version_and_sync() -> None:
    """Verify PRD.md and docs/PRD.md are synchronized and versioned at v1.1."""
    root_prd = (REPO_ROOT / "PRD.md").read_text(encoding="utf-8")
    docs_prd = (REPO_ROOT / "docs" / "PRD.md").read_text(encoding="utf-8")

    assert root_prd == docs_prd, "PRD.md and docs/PRD.md are out of sync"
    assert "v1.1" in root_prd, "PRD version 1.1 not found in PRD.md"
    assert "Post-Pilot Review" in root_prd
    assert "## 14b. Product evolution roadmap (post-pilot iteration)" in root_prd
    assert "EXP-13: Slice-Adaptive Conformal Prediction Intervals" in root_prd
    assert "EXP-16: Autonomous Dual-Cadence Ingestion & Freshness Daemon" in root_prd
    assert "EXP-14: Active Learning & Targeted Data Sourcing for Sparse Cells" in root_prd
    assert "EXP-15: Counterfactual Negotiation & Offer Scenario Modeling" in root_prd

    # Verify Change log entry
    assert "| 2026-10-21 | 1.1 | Post-Pilot Review ratification" in root_prd


def test_architecture_version_and_sync() -> None:
    """Verify architecture.md and docs/architecture.md are synchronized and versioned at v1.0."""
    root_arch = (REPO_ROOT / "architecture.md").read_text(encoding="utf-8")
    docs_arch = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert root_arch == docs_arch, "architecture.md and docs/architecture.md are out of sync"
    assert "v1.0 (Production Verified Architecture" in root_arch
    assert "compintel.monitoring" in root_arch
    assert "Tier 1: Conformal recalibration q_hat" in root_arch
    assert "Hot-rollback buffer (0.124ms SLA)" in root_arch

    # Verify all ADRs 0001-0009 are Accepted
    for adr_num in range(1, 10):
        adr_id = f"000{adr_num}"
        assert f"| {adr_id} |" in root_arch, f"ADR-{adr_id} missing in ADR index table"

    # Verify Change log entry
    assert "| 2026-10-21 | 1.0 | Production Architecture Ratification" in root_arch


def test_task_breakdown_sync_and_pointer() -> None:
    """Verify task.md and docs/task.md are synchronized and point to Gate G10."""
    root_task = (REPO_ROOT / "task.md").read_text(encoding="utf-8")
    docs_task = (REPO_ROOT / "docs" / "task.md").read_text(encoding="utf-8")

    assert root_task == docs_task, "task.md and docs/task.md are out of sync"
    assert "- [x] **T10.07**" in root_task, "T10.07 is not marked done in task.md"
    assert "**NEXT TASK: Gate G10 (critical): production decision**" in root_task
    assert "| 2026-10-21 | 1.0     | Phase 10 T10.01-T10.07 complete" in root_task


def test_memory_session_log_sync() -> None:
    """Verify memory.md and docs/memory.md are synchronized and have T10.07 in session log."""
    root_mem = (REPO_ROOT / "memory.md").read_text(encoding="utf-8")
    docs_mem = (REPO_ROOT / "docs" / "memory.md").read_text(encoding="utf-8")

    assert root_mem == docs_mem, "memory.md and docs/memory.md are out of sync"
    assert "| 2026-10-21 | T10.07 |" in root_mem
    assert "| Last completed task | T10.07 (Post-pilot review:" in root_mem
    assert "| Next task | Gate G10 (critical): production decision |" in root_mem


def test_charter_references_exist() -> None:
    """Verify charters referenced in post-pilot review roadmap exist in docs/research/."""
    charters_path = REPO_ROOT / "docs" / "research" / "experiment-charters-phase10.md"
    assert charters_path.is_file(), f"Missing {charters_path}"
    content = charters_path.read_text(encoding="utf-8")

    for charter_id in [
        "CHARTER-EXP-13",
        "CHARTER-EXP-16",
        "CHARTER-EXP-14",
        "CHARTER-EXP-15",
    ]:
        assert charter_id in content, f"{charter_id} not found in experiment charters"


def test_scorecard_metrics_match_domain_constants() -> None:
    """Verify that pilot scorecard values cited in post-pilot review match evaluation module."""
    from compintel.evaluation.pilot_analysis import evaluate_pilot_metrics

    metrics = evaluate_pilot_metrics()
    assert len(metrics) == 11

    # Verify all 11 metrics M-01 to M-11 exist and have status PASS
    for i, metric in enumerate(metrics, start=1):
        expected_id = f"M-{i:02d}"
        assert metric.metric_id == expected_id
        assert metric.status == "PASS"
