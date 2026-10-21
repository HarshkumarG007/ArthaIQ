"""Unit tests for Phase 10 production deployment and rollback runbook (Task T10.02).

Verifies:
- docs/runbooks/production-deployment-and-rollback.md completeness and ADR-0009 alignment.
- Hot model champion rollback execution, latency SLA, and buffer clearance (Rule R-MD-14).
- Container deployment rollback simulation and CLI rehearsal automation.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_rollback_rehearsal import (
    rehearse_container_rollback,
    rehearse_model_rollback,
    run_full_rehearsal,
)

from compintel.errors import ModelArtifactError
from compintel.serving.loader import ServingModelManager

RUNBOOK_PATH = Path("docs/runbooks/production-deployment-and-rollback.md")


class TestRollbackRunbookSpecification:
    """Validate documentation artifact docs/runbooks/production-deployment-and-rollback.md."""

    def test_runbook_file_exists(self) -> None:
        """Runbook markdown artifact must exist in docs/runbooks/."""
        assert RUNBOOK_PATH.exists(), f"Runbook not found at {RUNBOOK_PATH}"

    def test_runbook_contains_mandatory_sections(self) -> None:
        """Runbook must document topology, deployment protocol, triggers, rollbacks, and PIR."""
        content = RUNBOOK_PATH.read_text(encoding="utf-8")

        # 1. Architecture & Hosting Topology
        assert "Hosting Profile B" in content
        assert "t4g.medium" in content
        assert "ADR-0009" in content
        assert "Nginx" in content

        # 2. Deployment Protocol
        assert "Standard Production Deployment Protocol" in content
        assert "alembic upgrade head" in content
        assert "deploy_preview.py" in content
        assert "/livez" in content and "/readyz" in content

        # 3. Rollback Triggers
        assert "Automated & Human Rollback Triggers" in content
        assert "0.1%" in content or "0.1" in content  # Error rate
        assert "50" in content  # Latency
        assert "Coverage" in content
        assert "Drift" in content
        assert "PII" in content

        # 4. Dual Rollback Topologies
        assert "Application & Container Rollback Protocol" in content
        assert "alembic downgrade -1" in content
        assert "In-Process Model Champion Hot-Rollback Protocol" in content
        assert "R-MD-14" in content

        # 5. Empirical Rehearsal Log & PIR
        assert "Empirical Rollback Rehearsal Execution Log" in content
        assert "Post-Incident Review (PIR) Protocol" in content


class TestRollbackRehearsalExecution:
    """Verify programmatic rollback rehearsal automation and state invariants."""

    def test_rehearse_model_rollback_passes(self) -> None:
        """Model hot-rollback rehearsal must restore champion under sub-second latency SLA."""
        res = rehearse_model_rollback()
        assert res["status"] == "PASSED"
        assert res["initial_version"] == "0.1.0"
        assert res["challenger_version"] == "0.2.0-rc1"
        assert res["restored_version"] == "0.1.0"
        assert res["rollback_latency_ms"] < 1000.0  # Sub-second hot-rollback SLA

        # Check all 6 steps passed
        steps = res["steps"]
        assert len(steps) == 6
        for step in steps:
            assert step["passed"] is True

    def test_rehearse_container_rollback_passes(self) -> None:
        """Container rollback simulation must report simulated pass with revert command sequence."""
        res = rehearse_container_rollback()
        assert res["status"] == "SIMULATED_PASS"
        assert len(res["revert_commands"]) >= 4
        assert any("docker" in cmd for cmd in res["revert_commands"])
        assert any("alembic downgrade" in cmd for cmd in res["revert_commands"])

    def test_run_full_rehearsal_generates_valid_report(self, tmp_path: Path) -> None:
        """Full rehearsal run must write structured JSON report meeting all SLAs."""
        out_file = tmp_path / "rollback_report.json"
        report = run_full_rehearsal(output_path=out_file)

        assert out_file.exists()
        assert report["overall_status"] == "PASSED"
        assert report["rto_sla_met"] is True
        assert report["rpo_sla_met"] is True
        assert report["task_id"] == "T10.02"

        # Verify JSON on disk is identical
        disk_json = json.loads(out_file.read_text(encoding="utf-8"))
        assert disk_json["overall_status"] == "PASSED"
        assert disk_json["model_rollback"]["status"] == "PASSED"

    def test_empty_buffer_rollback_raises_safe_error(self) -> None:
        """Executing rollback on a freshly initialized manager must raise ROLLBACK_UNAVAILABLE."""
        manager = ServingModelManager()
        assert manager.previous_bundle is None
        try:
            manager.rollback()
            raise AssertionError("Should have raised ModelArtifactError")
        except ModelArtifactError as exc:
            assert exc.code == "ROLLBACK_UNAVAILABLE"
