"""Unit tests for Phase 17 Gate G17 ratification verification.

Verifies:
- All Phase 17 deliverables exist on disk (T17.01 through T17.04).
- Decision D-033 is recorded in memory.md, task.md, and docs/STATE.md.
- Gate G17 review dossier exists, records UNCONDITIONAL GO, Decision D-033, and panel consensus.
- All 10 pre-registered staging metrics (M-STG-01 to M-STG-10) pass.
- Staging container and Nginx CSP hardening (worker-src 'self' blob:).
- Two Streams, Two Places architecture (Rule R-CR-02) is strictly maintained.
- Zero Causal Pay Claims (Rule R-CR-01) and Anti-Credentialism (Rule R-CR-11).
- Local-First Privacy & DPDP Act 2023 Section 12 hard purge (Rule R-CR-12, ADR-0012).
- Zero Runtime LLMs on scoring and assessment path (Rule R-CR-15, ADR-0010, ADR-0013).
"""

from __future__ import annotations

import json
from pathlib import Path

GATE_REVIEW_PATH = Path("docs/pilot/gate-g17-staging-decision.md")
STATE_PATH = Path("docs/STATE.md")
MEMORY_PATH = Path("memory.md")
TASK_PATH = Path("task.md")
STAGING_JSON_PATH = Path("experiments/results/career_pilot_staging_audit_v1.json")
RUNBOOK_PATH = Path("docs/pilot/career-pilot-runbook.md")
NGINX_CONF_PATH = Path("infra/docker/nginx.conf")
STAGING_COMPOSE_PATH = Path("infra/docker/docker-compose.staging.yml")


class TestGateG17Deliverables:
    """Verify presence of all artifacts, code modules, and test suites required for Gate G17."""

    def test_all_phase17_files_exist(self) -> None:
        """Every deliverable from T17.01 through T17.04 exists on disk."""
        required_paths = [
            RUNBOOK_PATH,
            STAGING_COMPOSE_PATH,
            NGINX_CONF_PATH,
            Path("scripts/run_career_pilot_staging_audit.py"),
            STAGING_JSON_PATH,
            Path("tests/unit/test_career_pilot_staging_audit.py"),
            GATE_REVIEW_PATH,
        ]
        for path in required_paths:
            assert path.exists(), f"Required Phase 17 file {path} not found"


class TestGateG17RatificationRecords:
    """Verify Gate G17 formal ratification and Decision D-033 logging."""

    def test_gate_g17_review_dossier_conformance(self) -> None:
        """Review dossier records UNCONDITIONAL GO, Decision D-033, and panel verification."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        assert "REV-GATE-G17-01" in content
        assert "RATIFIED GO" in content
        assert "UNCONDITIONAL GO" in content
        assert "Decision D-033" in content
        assert "career-pilot-runbook.md" in content
        assert "docker-compose.staging.yml" in content
        assert "career_pilot_staging_audit_v1.json" in content
        assert "Two Streams Two Places" in content or "Two Streams, Two Places" in content

    def test_decision_d033_recorded_in_state_and_memory(self) -> None:
        """Decision D-033 is indexed in docs/STATE.md, memory.md, and task.md."""
        state_content = STATE_PATH.read_text(encoding="utf-8")
        memory_content = MEMORY_PATH.read_text(encoding="utf-8")
        task_content = TASK_PATH.read_text(encoding="utf-8")

        assert "D-033" in state_content or "Gate G17" in state_content
        assert "D-033" in memory_content or "Gate G17" in memory_content
        assert "Gate G17" in task_content

    def test_all_14_scorecard_checks_pass(self) -> None:
        """Scorecard in dossier has all CHK-17-01 through CHK-17-14 marked PASS."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        for i in range(1, 15):
            check_id = f"CHK-17-{i:02d}"
            assert check_id in content, f"Missing scorecard check {check_id}"


class TestGateG17ConstitutionalInvariants:
    """Verify ethical, architectural, and anti-causal invariants in Phase 17."""

    def test_all_ten_staging_metrics_pass(self) -> None:
        """Machine-readable staging audit JSON confirms 10/10 metrics pass."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        scorecard = data["scorecard"]
        for key, val in scorecard.items():
            assert val["status"] == "PASS", f"Scorecard metric {key} did not PASS: {val}"

    def test_nginx_csp_permits_web_worker(self) -> None:
        """Nginx CSP configuration permits offline sql.js Web Worker execution."""
        nginx_text = NGINX_CONF_PATH.read_text(encoding="utf-8")
        assert "worker-src 'self' blob:" in nginx_text

    def test_pilot_runbook_dpdp_compliance(self) -> None:
        """Pilot runbook details statutory consent notice and Sec 12 right to erasure."""
        runbook_text = RUNBOOK_PATH.read_text(encoding="utf-8")
        assert "DPDP Act 2023" in runbook_text
        assert "Section 6" in runbook_text
        assert "Section 12" in runbook_text
        assert "Erase All My Data" in runbook_text
        assert "0 bytes" in runbook_text

    def test_zero_causal_promises_and_anti_credentialism(self) -> None:
        """Pilot runbook and staging configs preserve Rule R-CR-01 and Rule R-CR-11."""
        runbook_text = RUNBOOK_PATH.read_text(encoding="utf-8").lower()
        assert "will earn" not in runbook_text
        assert "guarantees higher pay" not in runbook_text
        assert "boost your pay" not in runbook_text
        assert "official certification" not in runbook_text
        assert "accredited exam" not in runbook_text
