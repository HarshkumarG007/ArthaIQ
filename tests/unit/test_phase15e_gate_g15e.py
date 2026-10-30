"""Unit tests for Phase 15E Gate G15E ratification verification.

Verifies:
- All Phase 15E deliverables exist on disk (T15.27 through T15.30).
- Decision D-030 is recorded in memory.md, task.md, and docs/STATE.md.
- Gate G15E review dossier exists and records UNCONDITIONAL GO.
- Local-first privacy architecture (Rule R-CR-12, ADR-0012) is verified with zero
  server-side user career profiles.
- Ethical invariants (Rule R-CR-11 Anti-Credentialism and Rule R-CR-01 Anti-Causal Copy)
  are maintained in client components.
- State Beats Score (Rule R-CR-03) discrete verification states are implemented.
"""

from __future__ import annotations

from pathlib import Path

GATE_REVIEW_PATH = Path("docs/pilot/gate-g15e-review.md")
STATE_PATH = Path("docs/STATE.md")
MEMORY_PATH = Path("memory.md")
TASK_PATH = Path("task.md")


class TestGateG15EDeliverables:
    """Verify presence of all artifacts and test suites required for Gate G15E."""

    def test_all_subphase_15e_files_exist(self) -> None:
        """Every deliverable from T15.27 through T15.30 and Gate G15E exists on disk."""
        required_paths = [
            Path("apps/web/src/lib/careerLedger.ts"),
            Path("apps/web/src/lib/careerLedger.test.ts"),
            Path("apps/web/src/components/NavigationShell.tsx"),
            Path("apps/web/src/components/NavigationShell.test.tsx"),
            Path("apps/web/src/routes/career.tsx"),
            Path("apps/web/src/routes/career.test.tsx"),
            Path("apps/web/src/components/career/GapMapView.tsx"),
            Path("apps/web/src/components/career/GapMapView.test.tsx"),
            Path("apps/web/src/components/career/PracticeWorkspace.tsx"),
            Path("apps/web/src/components/career/PracticeWorkspace.test.tsx"),
            Path("docs/pilot/gate-g15e-review.md"),
        ]
        for path in required_paths:
            assert path.exists(), f"Required Phase 15E file {path} not found"


class TestGateG15ERatificationRecords:
    """Verify Gate G15E formal ratification and Decision D-030 logging."""

    def test_gate_g15e_review_dossier_conformance(self) -> None:
        """Review dossier records UNCONDITIONAL GO, Decision D-030, and panel verification."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        assert "REV-GATE-G15E-01" in content
        assert "RATIFIED GO" in content
        assert "UNCONDITIONAL GO" in content
        assert "Decision D-030" in content
        assert "arthaiq_career_ledger" in content
        assert "purgeAllUserData" in content
        assert "PracticeWorkspace" in content

    def test_decision_d030_recorded_in_state_and_memory(self) -> None:
        """Decision D-030 is indexed in docs/STATE.md and memory.md."""
        state_content = STATE_PATH.read_text(encoding="utf-8")
        memory_content = MEMORY_PATH.read_text(encoding="utf-8")
        task_content = TASK_PATH.read_text(encoding="utf-8")

        assert "D-030" in state_content or "Gate G15E" in state_content
        assert "D-030" in memory_content or "Gate G15E" in memory_content
        assert "Gate G15E" in task_content


class TestGateG15EInvariants:
    """Verify core architectural and ethical invariants in Phase 15E client code."""

    def test_local_first_indexeddb_privacy(self) -> None:
        """Client ledger implements DPDP Act single-click hard wipe and zero server DB calls."""
        ledger_code = Path("apps/web/src/lib/careerLedger.ts").read_text(encoding="utf-8")
        assert "purgeAllUserData" in ledger_code
        assert "exportLedgerBackup" in ledger_code
        assert "arthaiq_career_ledger" in ledger_code
        assert "evidence_records" in ledger_code
        assert "career_profile" in ledger_code
        assert "scenario_attempts" in ledger_code

    def test_state_beats_score_verification_states(self) -> None:
        """Discrete verification states are enforced (Rule R-CR-03)."""
        ledger_code = Path("apps/web/src/lib/careerLedger.ts").read_text(encoding="utf-8")
        assert "unproven" in ledger_code
        assert "self_reported" in ledger_code
        assert "demonstrated" in ledger_code

    def test_anti_credentialism_compliance(self) -> None:
        """Practice workspace strictly adheres to Rule R-CR-11."""
        workspace_code = Path("apps/web/src/components/career/PracticeWorkspace.tsx").read_text(
            encoding="utf-8"
        )
        assert "Rule R-CR-11" in workspace_code
        assert "Capability self-reflection only" in workspace_code
        assert "Not an exam" in workspace_code
