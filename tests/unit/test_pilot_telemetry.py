"""Unit tests for ArthaIQ Pilot Cohort Privacy-Preserving Telemetry (T20.02).

Verifies:
- k-Anonymity suppression (k >= 5) on demographic stratification cells.
- Cells with count < k have reported_count = None and is_suppressed = True.
- Cells with count >= k report exact count and is_suppressed = False.
- 10 pre-registered quality metrics in PilotTelemetryScorecard.
- Total participants sum invariant across role families (DATA, SWE, MLAI).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from compintel.monitoring.pilot_telemetry import (
    CellStratificationCount,
    PilotCohortTelemetryReport,
    PilotTelemetryScorecard,
    apply_k_anonymity,
    build_default_pilot_scorecard,
)


class TestPilotKAnonymitySuppression:
    """Validate k-anonymity cell threshold enforcement."""

    def test_k_anonymity_suppression_below_k(self) -> None:
        """Cells with raw_count < 5 must be suppressed (reported_count=None, is_suppressed=True)."""
        raw_counts = {
            "DATA_junior_BLR": 2,  # < 5 -> suppressed
            "DATA_mid_BLR": 18,  # >= 5 -> reported
            "SWE_senior_HYD": 4,  # < 5 -> suppressed
            "MLAI_staff_DEL": 1,  # < 5 -> suppressed
            "MLAI_mid_BLR": 12,  # >= 5 -> reported
        }
        cells = apply_k_anonymity(raw_counts, k=5)
        cell_map = {c.cell_key: c for c in cells}

        # Check suppressed cells
        assert cell_map["DATA_junior_BLR"].is_suppressed is True
        assert cell_map["DATA_junior_BLR"].reported_count is None
        assert cell_map["DATA_junior_BLR"].raw_count == 2

        assert cell_map["SWE_senior_HYD"].is_suppressed is True
        assert cell_map["SWE_senior_HYD"].reported_count is None

        assert cell_map["MLAI_staff_DEL"].is_suppressed is True
        assert cell_map["MLAI_staff_DEL"].reported_count is None

        # Check unsuppressed cells
        assert cell_map["DATA_mid_BLR"].is_suppressed is False
        assert cell_map["DATA_mid_BLR"].reported_count == 18

        assert cell_map["MLAI_mid_BLR"].is_suppressed is False
        assert cell_map["MLAI_mid_BLR"].reported_count == 12

    def test_k_anonymity_custom_k_threshold(self) -> None:
        """Custom k threshold (e.g. k=10) correctly suppresses counts under 10."""
        raw_counts = {"SWE_mid_BLR": 8, "SWE_senior_BLR": 15}
        cells = apply_k_anonymity(raw_counts, k=10)
        cell_map = {c.cell_key: c for c in cells}
        assert cell_map["SWE_mid_BLR"].is_suppressed is True
        assert cell_map["SWE_senior_BLR"].is_suppressed is False


class TestPilotTelemetryScorecard:
    """Validate 10/10 M-STG metrics aggregation."""

    def test_default_pilot_scorecard_all_pass(self) -> None:
        """Default scorecard constructed with standard values achieves 10/10 PASS."""
        sc: PilotTelemetryScorecard = build_default_pilot_scorecard()
        assert sc.m_stg_01_calibration_comprehension.status == "PASS"
        assert sc.m_stg_02_task_completion_rate.status == "PASS"
        assert sc.m_stg_03_deterministic_scoring_variance.status == "PASS"
        assert sc.m_stg_04_scoring_latency_p95_ms.status == "PASS"
        assert sc.m_stg_05_local_storage_footprint_kb.status == "PASS"
        assert sc.m_stg_06_dpdp_sec12_purge_residual_bytes.status == "PASS"
        assert sc.m_stg_07_zero_causal_promises.status == "PASS"
        assert sc.m_stg_08_anti_credentialism.status == "PASS"
        assert sc.m_stg_09_two_streams_two_places.status == "PASS"
        assert sc.m_stg_10_cross_family_dag_monotonicity.status == "PASS"

    def test_scorecard_metric_failure_trigger(self) -> None:
        """Scorecard metric triggers FAIL if observed value misses threshold."""
        sc = build_default_pilot_scorecard(comprehension_rate=0.85)  # < 90%
        assert sc.m_stg_01_calibration_comprehension.status == "FAIL"

        sc_lat = build_default_pilot_scorecard(p95_latency_ms=6.2)  # > 5.0ms
        assert sc_lat.m_stg_04_scoring_latency_p95_ms.status == "FAIL"


class TestPilotCohortTelemetryReport:
    """Validate full report assembly and invariants."""

    def test_report_validation_success(self) -> None:
        """Valid report with matching participant counts parses cleanly."""
        sc = build_default_pilot_scorecard()
        report = PilotCohortTelemetryReport(
            report_timestamp="2026-10-31T12:00:00Z",
            total_participants=150,
            data_participants=50,
            swe_participants=50,
            mlai_participants=50,
            scorecard=sc,
            cells=[
                CellStratificationCount(
                    cell_key="DATA_mid_BLR",
                    raw_count=20,
                    reported_count=20,
                    is_suppressed=False,
                )
            ],
        )
        assert report.total_participants == 150
        assert report.document_id == "PILOT-TELEMETRY-COHORT-01"

    def test_report_validation_mismatched_sum_fails(self) -> None:
        """Total participants mismatching family sum raises ValidationError."""
        sc = build_default_pilot_scorecard()
        with pytest.raises(ValidationError, match="Family participant sum"):
            PilotCohortTelemetryReport(
                report_timestamp="2026-10-31T12:00:00Z",
                total_participants=150,
                data_participants=40,
                swe_participants=50,
                mlai_participants=50,  # 40 + 50 + 50 = 140 != 150
                scorecard=sc,
            )

