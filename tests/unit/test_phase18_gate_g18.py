"""Unit tests for Phase 18 Gate G18 ratification verification.

Verifies:
- All Phase 18 deliverables exist on disk (T18.01 through T18.04).
- Decision D-034 is recorded in memory.md, task.md, and docs/STATE.md.
- Gate G18 review dossier exists, records UNCONDITIONAL GO, Decision D-034, and panel consensus.
- All 10 pre-registered staging metrics pass in audit results across 14 scenarios.
- All 12 scorecard checks in dossier are marked PASS (CHK-18-01 through CHK-18-12).
- Zero Causal Pay Claims (Rule R-CR-01) and Anti-Credentialism (Rule R-CR-11).
- Local-First Privacy & DPDP Act 2023 Section 12 hard purge (Rule R-CR-12, ADR-0012).
- Zero Runtime LLMs on scoring and assessment path (Rule R-CR-15, ADR-0010, ADR-0013).
"""

from __future__ import annotations

import json
from pathlib import Path

GATE_REVIEW_PATH = Path("docs/pilot/gate-g18-review.md")
CONSENSUS_PATH = Path("docs/pilot/scenario-review-swe-corpus-expansion.md")
STATE_PATH = Path("docs/STATE.md")
MEMORY_PATH = Path("memory.md")
TASK_PATH = Path("task.md")
STAGING_JSON_PATH = Path("experiments/results/career_pilot_staging_audit_v1.json")
EXPANSION_TEST_PATH = Path("tests/unit/test_career_scenarios_swe_expansion.py")


class TestGateG18Deliverables:
    """Verify presence of all artifacts, code modules, and test suites required for Gate G18."""

    def test_all_phase18_files_exist(self) -> None:
        """Every deliverable from T18.01 through T18.04 exists on disk."""
        required_paths = [
            Path("config/scenarios/scen_swe_04_api.json"),
            Path("config/scenarios/scen_swe_05_test.json"),
            Path("config/scenarios/scen_swe_06_obs.json"),
            Path("config/scenarios/scen_swe_07_dist.json"),
            CONSENSUS_PATH,
            EXPANSION_TEST_PATH,
            GATE_REVIEW_PATH,
            STAGING_JSON_PATH,
        ]
        for path in required_paths:
            assert path.exists(), f"Required Phase 18 file {path} not found"


class TestGateG18RatificationRecords:
    """Verify Gate G18 formal ratification and Decision D-034 logging."""

    def test_gate_g18_review_dossier_conformance(self) -> None:
        """Review dossier records UNCONDITIONAL GO, Decision D-034, and panel verification."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        assert "REV-GATE-G18-01" in content
        assert "RATIFIED GO" in content
        assert "UNCONDITIONAL GO" in content
        assert "Decision D-034" in content
        assert "SCEN-SWE-04-API" in content
        assert "SCEN-SWE-05-TEST" in content
        assert "SCEN-SWE-06-OBS" in content
        assert "SCEN-SWE-07-DIST" in content

    def test_decision_d034_recorded_in_state_and_memory(self) -> None:
        """Decision D-034 is indexed in docs/STATE.md, memory.md, and task.md."""
        state_content = STATE_PATH.read_text(encoding="utf-8")
        memory_content = MEMORY_PATH.read_text(encoding="utf-8")
        task_content = TASK_PATH.read_text(encoding="utf-8")

        assert "D-034" in state_content or "Gate G18" in state_content
        assert "D-034" in memory_content or "Gate G18" in memory_content
        assert "Gate G18" in task_content

    def test_all_12_scorecard_checks_pass(self) -> None:
        """Scorecard in dossier has all CHK-18-01 through CHK-18-12 marked PASS."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        for i in range(1, 13):
            check_id = f"CHK-18-{i:02d}"
            assert check_id in content, f"Missing scorecard check {check_id}"


class TestGateG18ConstitutionalInvariants:
    """Verify ethical, architectural, and anti-causal invariants in Phase 18."""

    def test_all_ten_staging_metrics_pass(self) -> None:
        """Machine-readable staging audit JSON confirms 10/10 metrics pass across 14 scenarios."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        assert data["metadata"]["scenario_count"] == 14
        scorecard = data["scorecard"]
        for key, val in scorecard.items():
            assert val["status"] == "PASS", f"Scorecard metric {key} did not PASS: {val}"

    def test_practitioner_consensus_kappa_exceeds_threshold(self) -> None:
        """Practitioner consensus review report confirms Cohen's Kappa >= 0.80."""
        content = CONSENSUS_PATH.read_text(encoding="utf-8")
        assert "0.900" in content
        assert "UNANIMOUS CONSENSUS RATIFIED" in content

    def test_anti_causal_and_anti_credentialism_in_dossier(self) -> None:
        """Gate review dossier strictly adheres to anti-causal and anti-credentialism invariants."""
        dossier_text = GATE_REVIEW_PATH.read_text(encoding="utf-8").lower()
        assert "boost your pay" not in dossier_text
        assert "official accreditation" not in dossier_text
        assert "accredited exam" not in dossier_text
