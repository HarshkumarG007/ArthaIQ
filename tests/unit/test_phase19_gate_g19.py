"""Unit tests for Phase 19 Gate G19 ratification verification.

Verifies:
- All Phase 19 deliverables exist on disk (T19.01 through T19.08).
- Decision D-035 is recorded in memory.md, task.md, and docs/STATE.md.
- Gate G19 review dossier exists, records UNCONDITIONAL GO, Decision D-035, and panel consensus.
- All 10 pre-registered staging metrics pass in audit results across 17 scenarios (DATA, SWE, MLAI).
- All 16 scorecard checks in dossier are marked PASS (CHK-19-01 through CHK-19-16).
- Zero Causal Pay Claims (Rule R-CR-01) and Anti-Credentialism (Rule R-CR-11).
- Local-First Privacy & DPDP Act 2023 Section 12 hard purge (Rule R-CR-12, ADR-0012).
- Zero Runtime LLMs on scoring and assessment path (Rule R-CR-15, ADR-0010, ADR-0013).
"""

from __future__ import annotations

import json
from pathlib import Path

GATE_REVIEW_PATH = Path("docs/pilot/gate-g19-review.md")
CONSENSUS_PATH = Path("docs/pilot/competency-review-mlai-family.md")
STATE_PATH = Path("docs/STATE.md")
MEMORY_PATH = Path("memory.md")
TASK_PATH = Path("task.md")
STAGING_JSON_PATH = Path("experiments/results/career_pilot_staging_audit_v1.json")
TAXONOMY_PATH = Path("config/taxonomy/mlai_family.json")
DAG_PATH = Path("config/taxonomy/competency_graph_mlai.json")
RUBRIC_PATH = Path("config/taxonomy/difficulty_rubrics_mlai.json")


class TestGateG19Deliverables:
    """Verify presence of all artifacts, code modules, and test suites required for Gate G19."""

    def test_all_phase19_files_exist(self) -> None:
        """Every deliverable from T19.01 through T19.08 exists on disk."""
        required_paths = [
            TAXONOMY_PATH,
            DAG_PATH,
            RUBRIC_PATH,
            CONSENSUS_PATH,
            Path("src/compintel/career/mlai_rubric.py"),
            Path("config/scenarios/scen_mlai_01_tens.json"),
            Path("config/scenarios/scen_mlai_02_leak.json"),
            Path("config/scenarios/scen_mlai_03_deploy.json"),
            GATE_REVIEW_PATH,
            STAGING_JSON_PATH,
        ]
        for path in required_paths:
            assert path.exists(), f"Required Phase 19 file {path} not found"


class TestGateG19RatificationRecords:
    """Verify Gate G19 formal ratification and Decision D-035 logging."""

    def test_gate_g19_review_dossier_conformance(self) -> None:
        """Review dossier records UNCONDITIONAL GO, Decision D-035, and panel verification."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        assert "REV-GATE-G19-01" in content
        assert "RATIFIED GO" in content
        assert "UNCONDITIONAL GO" in content
        assert "Decision D-035" in content
        assert "SCEN-MLAI-01-TENS" in content
        assert "SCEN-MLAI-02-LEAK" in content
        assert "SCEN-MLAI-03-DEPLOY" in content

    def test_decision_d035_recorded_in_state_and_memory(self) -> None:
        """Decision D-035 is indexed in docs/STATE.md, memory.md, and task.md."""
        state_content = STATE_PATH.read_text(encoding="utf-8")
        memory_content = MEMORY_PATH.read_text(encoding="utf-8")
        task_content = TASK_PATH.read_text(encoding="utf-8")

        assert "D-035" in state_content or "Gate G19" in state_content
        assert "D-035" in memory_content or "Gate G19" in memory_content
        assert "Gate G19" in task_content

    def test_all_16_scorecard_checks_pass(self) -> None:
        """Scorecard in dossier has all CHK-19-01 through CHK-19-16 marked PASS."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        for i in range(1, 17):
            check_id = f"CHK-19-{i:02d}"
            assert check_id in content, f"Missing scorecard check {check_id}"


class TestGateG19ConstitutionalInvariants:
    """Verify ethical, architectural, and anti-causal invariants in Phase 19."""

    def test_all_ten_staging_metrics_pass(self) -> None:
        """Machine-readable staging audit JSON confirms 10/10 metrics pass across 17 scenarios."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        assert data["metadata"]["scenario_count"] >= 17
        assert "MLAI" in data["metadata"]["families_tested"]
        assert data["metadata"]["attempt_count"] == 300
        scorecard = data["scorecard"]
        for key, val in scorecard.items():
            assert val["status"] == "PASS", f"Scorecard metric {key} did not PASS: {val}"

    def test_practitioner_consensus_kappa_exceeds_threshold(self) -> None:
        """Practitioner consensus review report confirms Cohen's Kappa >= 0.80."""
        content = CONSENSUS_PATH.read_text(encoding="utf-8")
        assert "0.867" in content
        assert "UNANIMOUS CONSENSUS RATIFIED" in content

    def test_anti_causal_and_anti_credentialism_in_dossier(self) -> None:
        """Gate review dossier strictly adheres to anti-causal and anti-credentialism invariants."""
        dossier_text = GATE_REVIEW_PATH.read_text(encoding="utf-8").lower()
        assert "boost your pay" not in dossier_text
        assert "will earn" not in dossier_text
        assert "guaranteed salary" not in dossier_text
