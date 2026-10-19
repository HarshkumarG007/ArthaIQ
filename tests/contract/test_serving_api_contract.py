"""Contract tests for serving API routes and payloads (Phase 9, Task T9.02).

Adheres to:
- architecture.md Section 11: Endpoints specifications.
- Rule R-ER-02: Expected outcomes return HTTP 200 result types, not exceptions.
- Rule R-UQ-01: Calibrated intervals [P10, P50, P90] in nominal INR LPA.
- Rule R-UQ-02: Abstention returns HTTP 200 payload with reasons.
- Rule R-MD-13: Current compensation compare-only quarantine.
- Rule R-CD-03: Architectural boundary; serving never imports ingestion/quality/eval.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from compintel.models.bundle import UnifiedPredictionResult
from compintel.schema.enums import CompensationMeasure, Currency
from compintel.serving import create_app
from compintel.serving.loader import ServingModelManager


@pytest.fixture
def client() -> TestClient:
    """Create test client with default champion model."""
    app = create_app()
    return TestClient(app)


@pytest.mark.contract
class TestServingAPIEndpointsContract:
    """Verify standard routes and schema contracts across serving API."""

    def test_healthz_and_probes(self, client: TestClient) -> None:
        """Verify healthz, livez, and readyz contracts."""
        live_res = client.get("/livez")
        assert live_res.status_code == 200
        assert live_res.json()["status"] == "LIVE"

        ready_res = client.get("/readyz")
        assert ready_res.status_code == 200
        assert ready_res.json()["status"] == "READY"

        health_res = client.get("/healthz")
        assert health_res.status_code == 200
        body = health_res.json()
        assert body["status"] == "HEALTHY"
        assert body["is_ready"] is True
        assert body["model_version"] == "0.1.0"
        assert "timestamp_utc" in body

    def test_taxonomy_occupations_endpoint(self, client: TestClient) -> None:
        """GET /v1/taxonomy/occupations lists canonical roles and supports filtering."""
        res = client.get("/v1/taxonomy/occupations")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 4
        ids = [item["id"] for item in data["items"]]
        assert "SWE" in ids
        assert "DATA" in ids
        assert "MLAI" in ids

        # Search filter
        filtered = client.get("/v1/taxonomy/occupations?q=backend")
        assert filtered.status_code == 200
        filtered_data = filtered.json()
        assert filtered_data["total"] >= 1
        assert filtered_data["items"][0]["id"] == "SWE"

    def test_taxonomy_locations_endpoint(self, client: TestClient) -> None:
        """GET /v1/taxonomy/locations lists canonical metro tech hubs."""
        res = client.get("/v1/taxonomy/locations")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 7
        ids = [item["id"] for item in data["items"]]
        assert "BENGALURU" in ids
        assert "HYDERABAD" in ids
        assert "PUNE" in ids

        # Search filter
        filtered = client.get("/v1/taxonomy/locations?q=bangalore")
        assert filtered.status_code == 200
        filtered_data = filtered.json()
        assert filtered_data["total"] == 1
        assert filtered_data["items"][0]["id"] == "BENGALURU"

    def test_models_current_endpoint(self, client: TestClient) -> None:
        """GET /v1/models/current returns active model bundle governance card."""
        res = client.get("/v1/models/current")
        assert res.status_code == 200
        data = res.json()
        assert data["model_version"] == "0.1.0"
        assert "Rung F" in data["rung"]
        assert data["target_variable"] == "guaranteed_cash_annual"
        assert data["target_unit"] == "nominal INR LPA"
        assert "canonical_snapshot_id" in data

    def test_sources_endpoint(self, client: TestClient) -> None:
        """GET /v1/sources returns approved data sources and licensing constraints."""
        res = client.get("/v1/sources")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 4
        source_ids = [s["source_id"] for s in data["sources"]]
        assert "SRC-INT-VOL-01" in source_ids
        assert "SRC-SUP-CORP-01" in source_ids

    def test_estimates_endpoint_abstention_flow(self, client: TestClient) -> None:
        """POST /v1/estimates returns HTTP 200 with status='abstained' under thin evidence."""
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 5.0, "level_id": "MID"},
            },
            "as_of": "2026-03-31",
        }
        res = client.post("/v1/estimates", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "abstained"
        assert body["as_of"] == "2026-03-31"
        assert body["disclaimer_id"] == "decision_support_v1"
        assert "request_id" in body
        assert len(body["reasons"]) > 0
        assert len(body["fallbacks"]) > 0

    def test_estimates_endpoint_supported_flow_with_comparison(self) -> None:
        """POST /v1/estimates returns HTTP 200 with status='ok' and comparison positioning."""
        mock_mgr = MagicMock(spec=ServingModelManager)
        mock_mgr.is_ready = True
        mock_mgr.model_version = "0.1.0"
        mock_mgr.active_bundle.metadata.canonical_snapshot_id = "test-snap-005"

        mock_pred = UnifiedPredictionResult(
            target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
            currency=Currency.INR.value,
            nominal_basis="LPA",
            p10=24.0,
            p50=36.0,
            p90=54.0,
            interval_width=30.0,
            nominal_coverage=0.80,
            status="supported",
            is_abstained=False,
            evidence_grade="GRADE_A",
            support_status="SUPPORTED",
            source_quality_tier="TIER_A",
            reasons=[],
            explanation="Supported cohort evidence.",
            guidance=None,
            checks={"s1_cohort_size": {"effective_n": 65}},
            model_version="0.1.0",
        )
        mock_mgr.predict.return_value = mock_pred

        app = create_app(manager=mock_mgr)
        test_client = TestClient(app)

        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 6.0},
            },
            "current_compensation": 40.0,
            "as_of": "2026-04-15",
        }

        res = test_client.post("/v1/estimates", json=payload)
        assert res.status_code == 200
        body = res.json()

        assert body["status"] == "ok"
        assert body["as_of"] == "2026-04-15"
        assert body["estimate"]["p10"] == 24.0
        assert body["estimate"]["p50"] == 36.0
        assert body["estimate"]["p90"] == 54.0
        assert body["reliability"]["grade"] == "GRADE_A"
        assert body["evidence"]["cohort_n"] == 65

        # Compare-Only Positioning (Rule R-MD-13)
        assert "comparison" in body
        comp = body["comparison"]
        assert comp["current_compensation"] == 40.0
        assert comp["delta_to_median_lpa"] == 4.0
        assert comp["position_category"] == "above_median"
        assert comp["percentile_band"] == "P50-P90"
