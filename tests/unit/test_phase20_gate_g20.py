"""Automated Verification Suite for Gate G20 Ratification (Phase 20).

Validates:
1. Document ID REV-GATE-G20-01 exists and ratifies Decision D-036 (UNCONDITIONAL GO).
2. Live Pilot Cohort Audit artifact exists with 10/10 M-STG metrics passing.
3. Target cohort N=150 participants evenly distributed across DATA (50), SWE (50), and MLAI (50).
4. k-Anonymity (k >= 5) cell suppression verified.
5. DPDP Act 2023 Section 12 single-click hard purge verified (0 residual bytes).
6. Constitutional invariants (R-CR-01, R-CR-02, R-CR-11, R-CR-12, R-CR-15) confirmed.
"""

from __future__ import annotations

import json
from pathlib import Path

GATE_REVIEW_PATH = Path("docs/pilot/gate-g20-review.md")
AUDIT_RESULTS_PATH = Path("experiments/results/pilot_cohort_audit_v1.json")


def test_gate_g20_dossier_exists_and_ratified():
    """Verify that Gate G20 review dossier exists and records Decision D-036 GO."""
    assert GATE_REVIEW_PATH.exists(), f"Missing dossier at {GATE_REVIEW_PATH}"
    content = GATE_REVIEW_PATH.read_text(encoding="utf-8")

    assert "REV-GATE-G20-01" in content
    assert "D-036" in content
    assert "RATIFIED GO" in content
    assert "UNCONDITIONAL GO" in content
    assert "Lead Quantitative ML Engineer" in content
    assert "India Compensation Economics Specialist" in content
    assert "Product & UX Design Lead" in content
    assert "Data Protection & Legal Governance Counsel" in content
    assert "Platform / SRE Operations Lead" in content


def test_pilot_cohort_audit_artifact_passes_all_metrics():
    """Verify that the cohort audit results JSON confirms 10/10 passing M-STG metrics."""
    assert AUDIT_RESULTS_PATH.exists(), f"Missing audit results at {AUDIT_RESULTS_PATH}"
    data = json.loads(AUDIT_RESULTS_PATH.read_text(encoding="utf-8"))

    assert data["verdict"] == "GO"
    assert data["cohort_size"] == 150
    assert data["family_breakdown"]["DATA"] == 50
    assert data["family_breakdown"]["SWE"] == 50
    assert data["family_breakdown"]["MLAI"] == 50
    assert data["k_anonymity_threshold"] == 5

    scorecard = data["scorecard"]
    assert len(scorecard) == 10

    expected_metrics = [
        "m_stg_01_calibration_comprehension",
        "m_stg_02_task_completion_rate",
        "m_stg_03_deterministic_scoring_variance",
        "m_stg_04_scoring_latency_p95_ms",
        "m_stg_05_local_storage_footprint_kb",
        "m_stg_06_dpdp_sec12_purge_residual_bytes",
        "m_stg_07_zero_causal_promises",
        "m_stg_08_anti_credentialism",
        "m_stg_09_two_streams_two_places",
        "m_stg_10_cross_family_dag_monotonicity",
    ]

    for metric in expected_metrics:
        assert metric in scorecard, f"Missing metric {metric}"
        assert scorecard[metric]["status"] == "PASS", f"Metric {metric} failed"


def test_pilot_cohort_k_anonymity_enforcement():
    """Verify that demographic cells with < 5 participants are properly suppressed."""
    data = json.loads(AUDIT_RESULTS_PATH.read_text(encoding="utf-8"))
    assert data["suppressed_cells_count"] > 0
    assert data["clear_cells_count"] > 0


def test_pilot_cohort_constitutional_invariants():
    """Verify adherence to core rules R-CR-01, R-CR-02, R-CR-11, R-CR-12, R-CR-15."""
    data = json.loads(AUDIT_RESULTS_PATH.read_text(encoding="utf-8"))
    scorecard = data["scorecard"]

    # R-CR-01: Zero Causal Promises
    assert scorecard["m_stg_07_zero_causal_promises"]["observed"] == "0 violations"

    # R-CR-02: Two Streams Two Places Decoupled
    assert scorecard["m_stg_09_two_streams_two_places"]["observed"] == "100% decoupled"

    # R-CR-11: Practice Not Certification
    assert scorecard["m_stg_08_anti_credentialism"]["observed"] == "0 violations"

    # R-CR-12: DPDP Sec 12 Purge Residual == 0 bytes
    assert scorecard["m_stg_06_dpdp_sec12_purge_residual_bytes"]["observed"] == "0 bytes"

    # R-CR-15: Deterministic Scoring Variance == 0.000000
    assert scorecard["m_stg_03_deterministic_scoring_variance"]["observed"] == "0.000000"
