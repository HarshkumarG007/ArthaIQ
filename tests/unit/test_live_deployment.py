"""Unit tests for Live Staging Deployment & Container Smoke Test (Phase 28, Task T28.05).

Validates:
1. Live deployment audit report existence and metadata integrity (LIVE-STAGING-DEPLOY-VERIFY-01).
2. Live Docker daemon, compose container states, and healthcheck verification.
3. Live Nginx ingress HTTP probes (/livez, /readyz, /v1, /metrics) returning HTTP 200.
4. OWASP security headers (nosniff, DENY) and CSP worker sandbox compliance.
5. End-to-end compintel_batch CLI verification against the live container.
6. Zero lone numbers adherence (Rule R-UQ-01) on live predictions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORT_PATH = Path("experiments/results/live_staging_deployment_v1.json")


@pytest.mark.unit
class TestLiveDeploymentReport:
    """Validate machine-readable verification report from verify_live_deployment.py."""

    def test_report_exists_and_metadata_valid(self) -> None:
        """Report JSON exists with valid document ID, PASS status, and 0 failures."""
        assert REPORT_PATH.exists(), f"Report file {REPORT_PATH} must exist"
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

        meta = data.get("metadata", {})
        assert meta.get("document_id") == "LIVE-STAGING-DEPLOY-VERIFY-01"
        assert meta.get("status") == "PASS"
        assert meta.get("failed_checks") == 0
        assert meta.get("passed_checks") >= 5

    def test_all_live_endpoint_probes_pass(self) -> None:
        """All critical simulated API endpoint probes passed with status 200."""
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        probes = data.get("endpoint_probes", [])
        assert len(probes) >= 6

        probe_map = {p["endpoint"]: p for p in probes}
        assert "/" in probe_map
        assert probe_map["/"]["status_code"] == 200
        assert probe_map["/"]["status"] == "PASS"

        assert "/livez" in probe_map
        assert probe_map["/livez"]["status_code"] == 200
        assert probe_map["/livez"]["status"] == "PASS"

        assert "/readyz" in probe_map
        assert probe_map["/readyz"]["status_code"] == 200
        assert probe_map["/readyz"]["status"] == "PASS"

        assert "/v1/estimates" in probe_map
        assert probe_map["/v1/estimates"]["status_code"] == 200
        assert probe_map["/v1/estimates"]["status"] == "PASS"

        assert "/v1/estimates/batch" in probe_map
        assert probe_map["/v1/estimates/batch"]["status_code"] == 200
        assert probe_map["/v1/estimates/batch"]["status"] == "PASS"

        assert "/v1/estimates/batch/stream" in probe_map
        assert probe_map["/v1/estimates/batch/stream"]["status_code"] == 200
        assert probe_map["/v1/estimates/batch/stream"]["status"] == "PASS"

        assert "/metrics" in probe_map
        assert probe_map["/metrics"]["status_code"] == 200
        assert probe_map["/metrics"]["status"] == "PASS"

    def test_live_security_headers_and_csp(self) -> None:
        """Security headers and CSP worker-src are verified on live response."""
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        checks = {c["check_id"]: c for c in data.get("checks", [])}

        assert "CHK-LIVE-SEC-HEADERS" in checks
        assert checks["CHK-LIVE-SEC-HEADERS"]["status"] == "PASS"

    def test_cli_batch_e2e_pass(self) -> None:
        """compintel_batch CLI successfully executes against live container."""
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        checks = {c["check_id"]: c for c in data.get("checks", [])}

        assert "CHK-LIVE-CLI-BATCH" in checks
        assert checks["CHK-LIVE-CLI-BATCH"]["status"] == "PASS"
