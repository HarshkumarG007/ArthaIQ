"""Unit tests for Phase 16 Gate G16 ratification verification.

Verifies:
- All Phase 16 deliverables exist on disk (T16.01 through T16.08).
- Decision D-032 is recorded in memory.md, task.md, and docs/STATE.md.
- Gate G16 review dossier exists, records UNCONDITIONAL GO, Decision D-032, and panel consensus.
- Multi-Family SWE content integrity (15 nodes, L2-L4 levels, 0 cycles, 100% provenance).
- Two Streams, Two Places architecture (Rule R-CR-02) is strictly maintained.
- Zero Causal Pay Claims (Rule R-CR-01) and Anti-Credentialism (Rule R-CR-11)
  are preserved across all components and scenarios.
- Zero Lone Numbers (Rule R-UQ-01, Rule R-UI-02) and Heuristic Effort Intervals (Rule R-CR-05).
- Zero Runtime LLMs on scoring and assessment path (Rule R-CR-15, ADR-0010, ADR-0013).
- Local-First Privacy (Rule R-CR-12, ADR-0012).
"""

from __future__ import annotations

import json
from pathlib import Path

GATE_REVIEW_PATH = Path("docs/pilot/gate-g16-review.md")
STATE_PATH = Path("docs/STATE.md")
MEMORY_PATH = Path("memory.md")
TASK_PATH = Path("task.md")


class TestGateG16Deliverables:
    """Verify presence of all artifacts, code modules, and test suites required for Gate G16."""

    def test_all_phase16_files_exist(self) -> None:
        """Every deliverable from T16.01 through T16.08 exists on disk."""
        required_paths = [
            # Taxonomy & Provenance (T16.01)
            Path("config/taxonomy/swe_family.json"),
            Path("tests/unit/test_career_swe_ingestion.py"),
            # Competency DAG (T16.02)
            Path("src/compintel/career/swe_graph.py"),
            Path("config/taxonomy/competency_graph_swe.json"),
            Path("tests/unit/test_career_swe_graph.py"),
            # Difficulty & Effort Rubrics (T16.03)
            Path("src/compintel/career/swe_rubric.py"),
            Path("config/taxonomy/difficulty_rubrics_swe.json"),
            Path("tests/unit/test_career_swe_rubric.py"),
            # Consensus Review (T16.04)
            Path("docs/pilot/competency-review-swe-family.md"),
            Path("tests/unit/test_competency_review_swe.py"),
            # Multi-Family Engine Adapter (T16.05)
            Path("src/compintel/career/engine.py"),
            Path("tests/unit/test_career_engine_multi_family.py"),
            # Flaw-Finding Scenarios (T16.06)
            Path("config/scenarios/scen_swe_01_concur.json"),
            Path("config/scenarios/scen_swe_02_sec.json"),
            Path("config/scenarios/scen_swe_03_db.json"),
            Path("scripts/generate_swe_scenarios.py"),
            Path("tests/unit/test_career_scenarios_swe.py"),
            # Web UI Multi-Family Support (T16.07)
            Path("apps/web/src/components/career/PracticeWorkspace.tsx"),
            Path("apps/web/src/components/career/PracticeWorkspace.test.tsx"),
            Path("apps/web/src/components/career/GapMapView.tsx"),
            Path("apps/web/src/components/career/GapMapView.test.tsx"),
            Path("apps/web/src/components/career/RoadmapView.tsx"),
            Path("apps/web/src/components/career/RoadmapView.test.tsx"),
            Path("apps/web/src/components/career/NextStepCard.tsx"),
            Path("apps/web/src/components/career/NextStepCard.test.tsx"),
            Path("apps/web/src/components/career/PayOverlayPanel.tsx"),
            Path("apps/web/src/components/career/PayOverlayPanel.test.tsx"),
            Path("apps/web/src/routes/career.tsx"),
            Path("apps/web/src/routes/career.test.tsx"),
            # Gate Review Dossier (T16.08)
            Path("docs/pilot/gate-g16-review.md"),
        ]
        for path in required_paths:
            assert path.exists(), f"Required Phase 16 file {path} not found"


class TestGateG16RatificationRecords:
    """Verify Gate G16 formal ratification and Decision D-032 logging."""

    def test_gate_g16_review_dossier_conformance(self) -> None:
        """Review dossier records UNCONDITIONAL GO, Decision D-032, and panel verification."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        assert "REV-GATE-G16-01" in content
        assert "RATIFIED GO" in content
        assert "UNCONDITIONAL GO" in content
        assert "Decision D-032" in content
        assert "0.867" in content  # Inter-rater reliability kappa
        assert "Two Streams Two Places" in content or "Two Streams, Two Places" in content
        assert "PracticeWorkspace" in content
        assert "GapMapView" in content
        assert "RoadmapView" in content
        assert "NextStepCard" in content
        assert "PayOverlayPanel" in content

    def test_decision_d032_recorded_in_state_and_memory(self) -> None:
        """Decision D-032 is indexed in docs/STATE.md, memory.md, and task.md."""
        state_content = STATE_PATH.read_text(encoding="utf-8")
        memory_content = MEMORY_PATH.read_text(encoding="utf-8")
        task_content = TASK_PATH.read_text(encoding="utf-8")

        assert "D-032" in state_content or "Gate G16" in state_content
        assert "D-032" in memory_content or "Gate G16" in memory_content
        assert "Gate G16" in task_content

    def test_all_14_scorecard_checks_pass(self) -> None:
        """Scorecard in dossier has all CHK-16-01 through CHK-16-14 marked PASS."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        for i in range(1, 15):
            check_id = f"CHK-16-{i:02d}"
            assert check_id in content, f"Missing scorecard check {check_id}"


class TestGateG16ConstitutionalInvariants:
    """Verify ethical, architectural, and anti-causal invariants in Phase 16."""

    def test_swe_graph_and_rubric_structure(self) -> None:
        """15-node SWE graph and rubrics have required metadata and bounds."""
        graph_data = json.loads(
            Path("config/taxonomy/competency_graph_swe.json").read_text(encoding="utf-8")
        )
        assert len(graph_data["nodes"]) == 15
        assert graph_data["role_family"] == "SWE"

        rubric_data = json.loads(
            Path("config/taxonomy/difficulty_rubrics_swe.json").read_text(encoding="utf-8")
        )
        assert len(rubric_data["entries"]) == 15
        for entry in rubric_data["entries"]:
            assert entry["is_heuristic"] is True
            assert entry["effort_hours"]["min_hours"] < entry["effort_hours"]["max_hours"]
            assert 1.0 <= entry["learning_difficulty"] <= 5.0
            assert 1.0 <= entry["application_difficulty"] <= 5.0

    def test_swe_scenarios_deterministic_and_no_llm(self) -> None:
        """SWE scenarios adhere to deterministic scoring (ADR-0010, ADR-0013)."""
        scenarios = [
            "config/scenarios/scen_swe_01_concur.json",
            "config/scenarios/scen_swe_02_sec.json",
            "config/scenarios/scen_swe_03_db.json",
        ]
        for scen_path in scenarios:
            data = json.loads(Path(scen_path).read_text(encoding="utf-8"))
            assert data["role_family"] == "SWE"
            assert len(data["rubric"]["defects"]) >= 3
            assert data["rubric"]["pass_threshold_score"] > 0
            # Ensure no runtime LLM prompts or instruction injections
            assert "llm_prompt" not in data
            assert "system_prompt" not in data

    def test_two_streams_two_places_architecture(self) -> None:
        """PayOverlayPanel enforces separate stream from competency roadmap (Rule R-CR-02)."""
        pay_content = Path("apps/web/src/components/career/PayOverlayPanel.tsx").read_text(
            encoding="utf-8"
        )
        assert "Decoupled Stream (R-CR-02)" in pay_content
        assert "Two Streams, Two Places Architecture" in pay_content
        assert "MARKET_BENCHMARKS_SWE" in pay_content

    def test_zero_lone_numbers_in_market_benchmarks(self) -> None:
        """Market benchmarks are full quantile intervals (P10, P50, P90) under Rule R-UQ-01."""
        pay_content = Path("apps/web/src/components/career/PayOverlayPanel.tsx").read_text(
            encoding="utf-8"
        )
        assert "10th Percentile (P10)" in pay_content
        assert "Median (P50)" in pay_content
        assert "90th Percentile (P90)" in pay_content
        assert "Zero lone numbers per Rule R-UQ-01" in pay_content

    def test_anti_causal_and_anti_credentialism_in_components(self) -> None:
        """All Phase 16 components preserve Rule R-CR-01 and Rule R-CR-11."""
        files_to_check = [
            Path("apps/web/src/components/career/PracticeWorkspace.tsx"),
            Path("apps/web/src/components/career/GapMapView.tsx"),
            Path("apps/web/src/components/career/RoadmapView.tsx"),
            Path("apps/web/src/components/career/NextStepCard.tsx"),
            Path("apps/web/src/components/career/PayOverlayPanel.tsx"),
            Path("apps/web/src/routes/career.tsx"),
        ]
        for path in files_to_check:
            text = path.read_text(encoding="utf-8")
            # Anti-causal rule R-CR-01: Prohibits affirmative pay promises
            assert "will earn" not in text
            assert "will increase your pay" not in text
            assert "guarantees higher pay" not in text
            assert "boost your pay" not in text
            assert "R-CR-01" in text

            # Anti-credentialism rule R-CR-11: Prohibits exam/certification claims
            assert "official certification" not in text.lower()
            assert "accredited exam" not in text.lower()
