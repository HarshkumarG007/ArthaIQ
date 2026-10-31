"""Automated Unit Tests for Live Pilot Field Run (Phase 24, Tasks T24.02-T24.04).

Verifies:
1. Cohort field run audit JSON exists and contains N=150 participants.
2. Even stratification across DATA (50), SWE (50), and MLAI (50).
3. Evaluation across all 21 canonical scenarios.
4. k-Anonymity suppression (k >= 5) applied to demographic cells.
5. 10/10 pre-registered M-STG staging scorecard metrics pass with status PASS.
6. DPDP Act 2023 Section 12 right to erasure hard wipe verification yields 0 residual bytes.
7. Zero causal promises (Rule R-CR-01) and anti-credentialism (Rule R-CR-11) confirmed.
8. Decoupled Two Streams, Two Places architecture (Rule R-CR-02).
"""

from __future__ import annotations

import json
from pathlib import Path

FIELD_RUN_JSON_PATH = Path("experiments/results/pilot_field_run_v1.json")


def test_field_run_audit_results_exist_and_validate() -> None:
    """Verify field run audit results file exists and has valid structure."""
    assert FIELD_RUN_JSON_PATH.exists(), f"Missing audit file at {FIELD_RUN_JSON_PATH}"
    data = json.loads(FIELD_RUN_JSON_PATH.read_text(encoding="utf-8"))

    assert data["run_id"] == "RUN-PILOT-FIELD-01"
    assert data["verdict"] == "GO"
    assert data["all_metrics_pass"] is True
    assert data["total_participants"] == 150
    assert data["active_scenarios_evaluated"] == 21


def test_cohort_demographic_stratification_and_k_anonymity() -> None:
    """Verify N=150 cohort stratification across families and k-anonymity (k >= 5)."""
    data = json.loads(FIELD_RUN_JSON_PATH.read_text(encoding="utf-8"))

    family_breakdown = data["family_breakdown"]
    assert family_breakdown["DATA"] == 50
    assert family_breakdown["SWE"] == 50
    assert family_breakdown["MLAI"] == 50

    assert data["k_anonymity_threshold"] == 5
    assert data["clear_cells_count"] > 0
    assert data["suppressed_cells_count"] > 0


def test_ten_m_stg_scorecard_metrics_all_pass() -> None:
    """Verify all 10 pre-registered M-STG metrics evaluated and status == 'PASS'."""
    data = json.loads(FIELD_RUN_JSON_PATH.read_text(encoding="utf-8"))
    scorecard = data["scorecard"]

    expected_keys = [
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

    for k in expected_keys:
        assert k in scorecard, f"Missing scorecard metric: {k}"
        metric = scorecard[k]
        assert metric["status"] == "PASS", f"Metric {k} did not pass: {metric}"


def test_dpdp_act_sec12_right_to_erasure_zero_residual_bytes() -> None:
    """Verify Section 12 right to erasure hard wipe results in exactly 0 residual bytes."""
    data = json.loads(FIELD_RUN_JSON_PATH.read_text(encoding="utf-8"))

    assert data["purge_residual_bytes"] == 0
    purge_metric = data["scorecard"]["m_stg_06_dpdp_sec12_purge_residual_bytes"]
    assert purge_metric["observed"] == "0 bytes"
    assert purge_metric["status"] == "PASS"


def test_constitutional_invariants_preserved() -> None:
    """Verify constitutional rules R-CR-01, R-CR-02, R-CR-11, R-CR-15."""
    data = json.loads(FIELD_RUN_JSON_PATH.read_text(encoding="utf-8"))

    # Rule R-CR-01: Zero causal promises
    assert data["causal_violations"] == 0

    # Rule R-CR-11: Anti-credentialism
    assert data["credential_violations"] == 0

    # Rule R-CR-02: Two Streams Two Places decoupled
    assert data["two_streams_decoupled"] is True

    # Competency DAG monotonicity
    assert data["dag_monotonicity"] is True
