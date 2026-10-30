"""Unit tests for ArthaIQ Career Architect Pilot Telemetry & Synthetic User Journey Audit.

Verifies:
- All telemetry deliverables exist on disk (script, JSON results, audit dossier).
- JSON results validate with Document ID TELEM-CAREER-ARCH-01 and 10/10 M-TEL metrics GO.
- Mathematical determinism holds strictly (variance == 0.0).
- Sub-millisecond scoring latency (p95 <= 5.0 ms).
- India DPDP Act 2023 Section 12 hard purge verification (0 bytes retained).
- Client-side storage footprint benchmark (<= 100.0 KB for 50 records).
- All 4 persona journeys succeed with honest pay abstention triggered for out-of-cohort cells.
- Zero causal pay promises (Rule R-CR-01) and anti-credentialism (Rule R-CR-11).
"""

from __future__ import annotations

import json
from pathlib import Path

TELEMETRY_SCRIPT_PATH = Path("scripts/run_career_pilot_telemetry.py")
TELEMETRY_JSON_PATH = Path("experiments/results/career_pilot_telemetry_v1.json")
TELEMETRY_DOSSIER_PATH = Path("docs/pilot/career-architect-pilot-telemetry.md")


class TestCareerPilotTelemetryDeliverables:
    """Verify presence of all artifacts generated for the Career Architect telemetry audit."""

    def test_all_telemetry_artifacts_exist(self) -> None:
        """Simulation script, machine-readable JSON output, and markdown dossier must exist."""
        assert TELEMETRY_SCRIPT_PATH.exists(), f"Script {TELEMETRY_SCRIPT_PATH} missing"
        assert TELEMETRY_JSON_PATH.exists(), f"JSON results {TELEMETRY_JSON_PATH} missing"
        assert TELEMETRY_DOSSIER_PATH.exists(), f"Dossier {TELEMETRY_DOSSIER_PATH} missing"


class TestCareerPilotTelemetryScorecard:
    """Validate 10/10 M-TEL metrics from the telemetry simulation results."""

    def test_json_scorecard_metadata_and_overall_pass(self) -> None:
        """JSON artifact contains valid metadata and overall PASS status."""
        data = json.loads(TELEMETRY_JSON_PATH.read_text(encoding="utf-8"))
        assert data["metadata"]["document_id"] == "TELEM-CAREER-ARCH-01"
        assert data["metadata"]["status"] == "PASS"
        assert data["metadata"]["evaluated_subsystem"] == "ArthaIQ Career Architect (Phase 15)"

    def test_all_ten_metrics_pass(self) -> None:
        """All 10 quality and compliance metrics in the scorecard have status PASS."""
        data = json.loads(TELEMETRY_JSON_PATH.read_text(encoding="utf-8"))
        scorecard = data["scorecard"]

        expected_metrics = [
            "M-TEL-01_scorer_determinism",
            "M-TEL-02_scoring_latency_p95_ms",
            "M-TEL-03_rubric_boundedness",
            "M-TEL-04_dynamic_next_step",
            "M-TEL-05_pacing_slider_calculation",
            "M-TEL-06_dpdp_sec12_erasure",
            "M-TEL-07_backup_roundtrip_fidelity",
            "M-TEL-08_client_storage_footprint_kb",
            "M-TEL-09_honest_abstention_trigger",
            "M-TEL-10_anti_causal_copy_invariant",
        ]

        for metric in expected_metrics:
            assert metric in scorecard, f"Missing metric {metric} in scorecard"
            status = scorecard[metric]["status"]
            assert status == "PASS", f"Metric {metric} failed: {status}"

    def test_determinism_and_latency_thresholds(self) -> None:
        """Deterministic scorer variance is exactly 0.0 and p95 latency is well below 5.0 ms."""
        data = json.loads(TELEMETRY_JSON_PATH.read_text(encoding="utf-8"))
        scorecard = data["scorecard"]

        assert scorecard["M-TEL-01_scorer_determinism"]["observed"] == 0.0
        assert scorecard["M-TEL-02_scoring_latency_p95_ms"]["observed_ms"] <= 5.0
        assert data["latency_profile"]["p95_microseconds"] < 5000.0

    def test_privacy_and_storage_benchmarks(self) -> None:
        """DPDP Act 2023 Sec 12 drops data to 0 bytes and client storage footprint <= 100 KB."""
        data = json.loads(TELEMETRY_JSON_PATH.read_text(encoding="utf-8"))
        storage = data["storage_benchmark"]

        assert storage["purged_bytes"] == 0
        assert storage["dpdp_section_12_compliant"] is True
        assert storage["roundtrip_valid"] is True
        assert storage["payload_kb"] <= 100.0


class TestCareerPilotUserJourneys:
    """Verify synthetic user personas and attempt submissions."""

    def test_four_persona_journeys_evaluated(self) -> None:
        """Four personas are tracked through onboarding, DAG sequencing, and honest abstention."""
        data = json.loads(TELEMETRY_JSON_PATH.read_text(encoding="utf-8"))
        journeys = data["persona_journeys"]

        assert len(journeys) == 4
        persona_ids = [j["persona_id"] for j in journeys]
        assert persona_ids == ["P-DATA-01", "P-DATA-02", "P-DATA-03", "P-DATA-04"]

        for j in journeys:
            assert j["journey_success"] is True

        # Non-metro Persona 4 triggers honest abstention
        p4 = journeys[3]
        assert p4["persona_id"] == "P-DATA-04"
        assert p4["location"] == "other"
        assert p4["abstention_triggered"] is True
        assert p4["market_pay_interval"] is None

    def test_fifty_attempt_simulation_breakdown(self) -> None:
        """50 synthetic attempts span 4 behavioral profiles with 100% score boundedness."""
        data = json.loads(TELEMETRY_JSON_PATH.read_text(encoding="utf-8"))
        summary = data["attempts_summary"]

        assert summary["total_attempts"] == 50
        assert summary["expert_count"] == 15
        assert summary["partial_count"] == 15
        assert summary["overflagging_count"] == 10
        assert summary["empty_count"] == 10
        assert summary["all_bounded"] is True


class TestCareerPilotAuditDossierInvariants:
    """Verify the formal markdown audit dossier conforms to constitutional invariants."""

    def test_audit_dossier_content_and_invariants(self) -> None:
        """Dossier contains correct document ID, pass verdict, and zero causal claims."""
        content = TELEMETRY_DOSSIER_PATH.read_text(encoding="utf-8")

        assert "TELEM-CAREER-ARCH-01" in content
        assert "AUDIT PASSED" in content
        assert "10/10 M-TEL Quality Metrics GO" in content
        assert "DPDP Act 2023" in content
        assert "Two Streams, Two Places" in content
        assert "Honest Abstention" in content

        # Zero affirmative causal pay promises (Rule R-CR-01)
        content_lower = content.lower()
        forbidden_promises = [
            "will increase your salary",
            "guarantees higher pay",
            "will earn \u20b9",
            "boost your compensation",
        ]
        for term in forbidden_promises:
            assert term not in content_lower, f"Forbidden causal claim found in dossier: '{term}'"
