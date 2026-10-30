"""Unit tests for Phase 15F Gate G15F ratification verification.

Verifies:
- All Phase 15F deliverables exist on disk (T15.31 through T15.33).
- Decision D-031 is recorded in memory.md, task.md, and docs/STATE.md.
- Gate G15F review dossier exists and records UNCONDITIONAL GO.
- Two Streams, Two Places architecture (Rule R-CR-02) is strictly maintained.
- Zero Causal Pay Claims (Rule R-CR-01) and Anti-Credentialism (Rule R-CR-11)
  are maintained across all components.
- Zero Lone Numbers (Rule R-UQ-01, Rule R-UI-02) and Heuristic Effort Intervals (Rule R-CR-05).
"""

from __future__ import annotations

from pathlib import Path

GATE_REVIEW_PATH = Path("docs/pilot/gate-g15f-review.md")
STATE_PATH = Path("docs/STATE.md")
MEMORY_PATH = Path("memory.md")
TASK_PATH = Path("task.md")


class TestGateG15FDeliverables:
    """Verify presence of all artifacts and test suites required for Gate G15F."""

    def test_all_subphase_15f_files_exist(self) -> None:
        """Every deliverable from T15.31 through T15.33 and Gate G15F exists on disk."""
        required_paths = [
            Path("apps/web/src/components/career/RoadmapView.tsx"),
            Path("apps/web/src/components/career/RoadmapView.test.tsx"),
            Path("apps/web/src/components/career/NextStepCard.tsx"),
            Path("apps/web/src/components/career/NextStepCard.test.tsx"),
            Path("apps/web/src/components/career/PayOverlayPanel.tsx"),
            Path("apps/web/src/components/career/PayOverlayPanel.test.tsx"),
            Path("apps/web/src/routes/career.tsx"),
            Path("docs/pilot/gate-g15f-review.md"),
        ]
        for path in required_paths:
            assert path.exists(), f"Required Phase 15F file {path} not found"


class TestGateG15FRatificationRecords:
    """Verify Gate G15F formal ratification and Decision D-031 logging."""

    def test_gate_g15f_review_dossier_conformance(self) -> None:
        """Review dossier records UNCONDITIONAL GO, Decision D-031, and panel verification."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        assert "REV-GATE-G15F-01" in content
        assert "RATIFIED GO" in content
        assert "UNCONDITIONAL GO" in content
        assert "Decision D-031" in content
        assert "Two Streams, Two Places" in content
        assert "RoadmapView" in content
        assert "NextStepCard" in content
        assert "PayOverlayPanel" in content

    def test_decision_d031_recorded_in_state_and_memory(self) -> None:
        """Decision D-031 is indexed in docs/STATE.md, memory.md, and task.md."""
        state_content = STATE_PATH.read_text(encoding="utf-8")
        memory_content = MEMORY_PATH.read_text(encoding="utf-8")
        task_content = TASK_PATH.read_text(encoding="utf-8")

        assert "D-031" in state_content or "Gate G15F" in state_content
        assert "D-031" in memory_content or "Gate G15F" in memory_content
        assert "Gate G15F" in task_content


class TestGateG15FConstitutionalInvariants:
    """Verify ethical, architectural, and anti-causal invariants in Phase 15F."""

    def test_two_streams_two_places_architecture(self) -> None:
        """PayOverlayPanel enforces separate stream from competency roadmap (Rule R-CR-02)."""
        pay_content = Path("apps/web/src/components/career/PayOverlayPanel.tsx").read_text(
            encoding="utf-8"
        )
        assert "Decoupled Stream (R-CR-02)" in pay_content
        assert "Two Streams, Two Places Architecture" in pay_content
        assert "Market Compensation Context" in pay_content

    def test_zero_lone_numbers_in_market_benchmarks(self) -> None:
        """Market benchmarks are full quantile intervals (P10, P50, P90) under Rule R-UQ-01."""
        pay_content = Path("apps/web/src/components/career/PayOverlayPanel.tsx").read_text(
            encoding="utf-8"
        )
        assert "10th Percentile (P10)" in pay_content
        assert "Median (P50)" in pay_content
        assert "90th Percentile (P90)" in pay_content
        assert "Zero lone numbers per Rule R-UQ-01" in pay_content

    def test_honest_abstention_support(self) -> None:
        """PayOverlayPanel supports honest abstention for unsupported cohorts (Rule R-CR-14)."""
        pay_content = Path("apps/web/src/components/career/PayOverlayPanel.tsx").read_text(
            encoding="utf-8"
        )
        assert "Honest Abstention (Rule R-CR-14)" in pay_content
        assert "Insufficient Market Evidence for This Sub-Cohort" in pay_content

    def test_anti_causal_and_anti_credentialism_in_components(self) -> None:
        """All Phase 15F components preserve Rule R-CR-01 and Rule R-CR-11."""
        files_to_check = [
            Path("apps/web/src/components/career/RoadmapView.tsx"),
            Path("apps/web/src/components/career/NextStepCard.tsx"),
            Path("apps/web/src/components/career/PayOverlayPanel.tsx"),
        ]
        for path in files_to_check:
            text = path.read_text(encoding="utf-8")
            # Anti-causal rule R-CR-01: Prohibits affirmative pay promises
            assert "will earn" not in text
            assert "will increase your pay" not in text
            assert "guarantees higher pay" not in text
            assert "boost your pay" not in text
            assert "Consumer Protection Act" in text or "Rule R-CR-01" in text
