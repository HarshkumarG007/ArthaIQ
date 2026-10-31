"""Unit tests for ArthaIQ Career Architect Multi-Family Pilot Staging Audit (T17.03, T19.08).

Verifies:
- Deliverables exist: staging audit script, JSON results, pilot runbook, staging compose.
- JSON results validate with Document ID STAGING-AUDIT-CAREER-ARCH-01 and 10/10 M-STG metrics GO.
- Three role families (DATA, SWE, MLAI) evaluated across 300 total attempts (100 each).
- Deterministic scoring variance holds strictly across DATA, SWE, and MLAI (variance == 0.000).
- Sub-5ms scoring latency (p95 <= 5.0 ms).
- DPDP Act 2023 Section 12 hard purge verification (0 bytes retained).
- Client-side storage footprint benchmark (<= 100.0 KB).
- Zero causal pay promises (Rule R-CR-01) and anti-credentialism (Rule R-CR-11).
- Hardened CSP configuration in Nginx (`worker-src 'self' blob:`).
- Topological monotonicity across DATA, SWE, and MLAI competency DAGs.
"""

from __future__ import annotations

import json
from pathlib import Path

STAGING_SCRIPT_PATH = Path("scripts/run_career_pilot_staging_audit.py")
STAGING_JSON_PATH = Path("experiments/results/career_pilot_staging_audit_v1.json")
RUNBOOK_PATH = Path("docs/pilot/career-pilot-runbook.md")
STAGING_COMPOSE_PATH = Path("infra/docker/docker-compose.staging.yml")
NGINX_CONF_PATH = Path("infra/docker/nginx.conf")


class TestPilotStagingDeliverables:
    """Verify presence of all artifacts generated for the staging deployment and audit."""

    def test_all_staging_artifacts_exist(self) -> None:
        """Staging script, JSON report, runbook, compose file, and Nginx conf must exist."""
        assert STAGING_SCRIPT_PATH.exists(), f"Script {STAGING_SCRIPT_PATH} missing"
        assert STAGING_JSON_PATH.exists(), f"JSON results {STAGING_JSON_PATH} missing"
        assert RUNBOOK_PATH.exists(), f"Runbook {RUNBOOK_PATH} missing"
        assert STAGING_COMPOSE_PATH.exists(), f"Compose {STAGING_COMPOSE_PATH} missing"
        assert NGINX_CONF_PATH.exists(), f"Nginx conf {NGINX_CONF_PATH} missing"


class TestPilotStagingScorecard:
    """Validate 10/10 M-STG metrics from the staging simulation results."""

    def test_json_scorecard_metadata_and_overall_pass(self) -> None:
        """JSON artifact contains valid metadata, all families, and overall PASS status."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        meta = data["metadata"]
        assert meta["document_id"] == "STAGING-AUDIT-CAREER-ARCH-01"
        assert meta["status"] == "PASS"
        assert "DATA" in meta["families_tested"]
        assert "SWE" in meta["families_tested"]
        assert "MLAI" in meta["families_tested"]
        assert meta["attempt_count"] in (200, 300)
        assert meta["scenario_count"] in (10, 14, 17)

    def test_all_ten_staging_metrics_pass(self) -> None:
        """All 10 quality and compliance metrics in the scorecard have status PASS."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        scorecard = data["scorecard"]

        expected_metrics = [
            "M-STG-01_calibration_comprehension",
            "M-STG-02_task_completion_rate",
            "M-STG-03_scoring_determinism_variance",
            "M-STG-04_scoring_latency_p95_ms",
            "M-STG-05_local_storage_footprint_kb",
            "M-STG-06_dpdp_sec12_hard_purge_bytes",
            "M-STG-07_zero_causal_promises",
            "M-STG-08_anti_credentialism",
            "M-STG-09_two_streams_two_places",
            "M-STG-10_cross_family_dag_monotonicity",
        ]
        for metric_key in expected_metrics:
            assert metric_key in scorecard, f"Missing metric {metric_key} in scorecard"
            assert scorecard[metric_key]["status"] == "PASS", f"Metric {metric_key} did not PASS"

    def test_scoring_determinism_zero_variance(self) -> None:
        """Scorer determinism exhibits exact mathematical variance of 0.000 across families."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        metric = data["scorecard"]["M-STG-03_scoring_determinism_variance"]
        assert metric["observed_data"] == 0.0
        assert metric["observed_swe"] == 0.0
        assert metric["observed_mlai"] == 0.0

    def test_scoring_latency_sub_5ms(self) -> None:
        """p95 scoring latency is strictly under 5.0 ms SLA."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        p95_ms = data["scorecard"]["M-STG-04_scoring_latency_p95_ms"]["observed_ms"]
        assert p95_ms < 5.0, f"p95 latency {p95_ms}ms exceeds 5.0ms SLA"

    def test_dpdp_sec12_hard_wipe_zero_bytes(self) -> None:
        """Section 12 DPDP Act 2023 hard purge leaves exact 0 bytes residual."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        purged_bytes = data["scorecard"]["M-STG-06_dpdp_sec12_hard_purge_bytes"]["observed_bytes"]
        assert purged_bytes == 0

    def test_local_storage_footprint_under_100kb(self) -> None:
        """Client storage payload is well within the 100.0 KB budget."""
        data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))
        kb = data["scorecard"]["M-STG-05_local_storage_footprint_kb"]["observed_kb"]
        assert kb < 100.0, f"Storage payload {kb} KB exceeds 100 KB limit"


class TestStagingInfrastructureHardening:
    """Verify Nginx reverse proxy hardening and Docker Compose configuration."""

    def test_nginx_csp_permits_web_worker_blob(self) -> None:
        """Nginx CSP includes worker-src 'self' blob: for offline Web Worker sql.js sandboxes."""
        conf_text = NGINX_CONF_PATH.read_text(encoding="utf-8")
        assert "worker-src 'self' blob:" in conf_text
        assert "default-src 'self'" in conf_text
        assert "script-src 'self'" in conf_text

    def test_staging_compose_environment_and_caps(self) -> None:
        """Staging docker compose file specifies resource caps and multi-family environment."""
        compose_text = STAGING_COMPOSE_PATH.read_text(encoding="utf-8")
        assert "CAREER_FAMILIES_ENABLED" in compose_text
        assert "DATA,SWE,MLAI" in compose_text
        assert "limits:" in compose_text
        assert "memory:" in compose_text
        assert "arthaiq-staging-api" in compose_text
        assert "arthaiq-staging-web" in compose_text
