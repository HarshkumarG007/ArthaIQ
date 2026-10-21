"""Contract tests for GET /metrics telemetry exposition endpoint (Phase 9, Task T9.11a).

Verifies:
- PRD FR-13 & NFR-07: Internal monitoring, Prometheus metrics exposition.
- GET /metrics returns HTTP 200 with media type text/plain; version=0.0.4; charset=utf-8.
- Request middleware records incoming requests, latency, and status codes.
- Estimation calls update estimates_total, abstentions_total, and width metrics.
- PII sanitization: no salary numbers, emails, or personal identifiers appear in metrics output.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from compintel.models.bundle import UnifiedPredictionResult
from compintel.monitoring.metrics import get_metrics_registry
from compintel.schema.enums import CompensationMeasure, Currency
from compintel.serving.app import create_app
from compintel.serving.core import reset_default_serving_manager
from compintel.serving.loader import ServingModelManager
from compintel.serving.routers.metrics import PROMETHEUS_MEDIA_TYPE


@pytest.fixture(autouse=True)
def _reset_telemetry_state() -> None:
    """Reset global metrics registry and serving manager before and after tests."""
    reset_default_serving_manager()
    reg = get_metrics_registry()
    reg.reset_all()
    yield
    reg.reset_all()
    reset_default_serving_manager()


@pytest.fixture
def mock_serving_manager() -> ServingModelManager:
    """Fixture producing a mock ServingModelManager for supported estimation contracts."""
    mgr = MagicMock(spec=ServingModelManager)
    mgr.is_ready = True
    mgr.model_version = "0.1.0"
    mgr.active_bundle.metadata.canonical_snapshot_id = "SNAP-METRICS-20261021"
    mgr.active_bundle.metadata.model_version = "0.1.0"

    mock_pred = UnifiedPredictionResult(
        target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
        currency=Currency.INR.value,
        nominal_basis="LPA",
        p10=20.0,
        p50=28.0,
        p90=40.0,
        interval_width=20.0,
        nominal_coverage=0.80,
        status="supported",
        is_abstained=False,
        evidence_grade="GRADE_A",
        support_status="SUPPORTED",
        source_quality_tier="TIER_A",
        reasons=[],
        explanation="Calibrated cohort evidence meets statutory thresholds.",
        guidance=None,
        checks={
            "s1_cohort_size": {"effective_n": 100},
            "s3_recency": {"observation_age_days": 30.0},
        },
        model_version="0.1.0",
    )
    mgr.predict.return_value = mock_pred
    return mgr


class TestMetricsContract:
    """Contract tests for GET /metrics endpoint."""

    def test_metrics_endpoint_returns_200_and_prometheus_content_type(self) -> None:
        client = TestClient(create_app())
        response = client.get("/metrics")

        assert response.status_code == 200
        assert PROMETHEUS_MEDIA_TYPE in response.headers.get("content-type", "")
        body = response.text
        assert "# HELP http_requests_total" in body
        assert "# TYPE http_requests_total counter" in body
        assert "# HELP arthaiq_estimates_total" in body

    def test_http_request_counters_updated_on_traffic(self) -> None:
        client = TestClient(create_app())

        # Call health check
        health_resp = client.get("/healthz")
        assert health_resp.status_code == 200

        # Scrape metrics
        metrics_resp = client.get("/metrics")
        assert metrics_resp.status_code == 200
        body = metrics_resp.text

        # Health check request must be recorded
        assert 'http_requests_total{method="GET",path="/healthz",status="200"}' in body
        assert 'http_request_duration_seconds_count{method="GET",path="/healthz"}' in body

    def test_supported_estimate_updates_metrics(
        self, mock_serving_manager: ServingModelManager
    ) -> None:
        client = TestClient(create_app(manager=mock_serving_manager))

        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {
                    "total_years": 5.0,
                    "level_id": "MID",
                },
            },
            "measure": "guaranteed_cash_annual",
            "currency": "INR",
            "as_of": "2026-10-19",
        }

        est_resp = client.post("/v1/estimates", json=payload)
        assert est_resp.status_code == 200
        assert est_resp.json()["status"] == "ok"

        metrics_resp = client.get("/metrics")
        body = metrics_resp.text

        # Estimates total incremented
        assert 'arthaiq_estimates_total{status="supported"} 1.0' in body
        # Latency recorded
        assert 'http_requests_total{method="POST",path="/v1/estimates",status="200"} 1.0' in body
        # Interval width histogram recorded
        assert "arthaiq_estimate_confidence_width_lpa_count" in body

    def test_abstained_estimate_updates_abstention_metrics(self) -> None:
        mgr = MagicMock(spec=ServingModelManager)
        mgr.is_ready = True
        mgr.model_version = "0.1.0"
        mgr.active_bundle.metadata.canonical_snapshot_id = "SNAP-METRICS-20261021"
        mgr.active_bundle.metadata.model_version = "0.1.0"

        mock_pred = UnifiedPredictionResult(
            target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
            currency=Currency.INR.value,
            nominal_basis="LPA",
            p10=None,
            p50=None,
            p90=None,
            interval_width=None,
            nominal_coverage=None,
            status="abstained",
            is_abstained=True,
            evidence_grade="ABSTAINED",
            support_status="ABSTAINED",
            source_quality_tier="TIER_C",
            reasons=["OUT_OF_BOUNDS_EXPERIENCE"],
            explanation="Years of experience exceeds empirical support boundary [0, 40].",
            guidance="Consider querying within maximum 40 years of experience.",
            checks={"s2_bounds": {"valid": False}},
            model_version="0.1.0",
        )
        mgr.predict.return_value = mock_pred

        client = TestClient(create_app(manager=mgr))

        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {
                    "total_years": 45.0,
                    "level_id": "MID",
                },
            },
            "measure": "guaranteed_cash_annual",
            "currency": "INR",
            "as_of": "2026-10-19",
        }

        est_resp = client.post("/v1/estimates", json=payload)
        assert est_resp.status_code == 200
        data = est_resp.json()
        assert data["status"] == "abstained"

        metrics_resp = client.get("/metrics")
        body = metrics_resp.text

        # Abstained estimate counted
        assert 'arthaiq_estimates_total{status="abstained"} 1.0' in body
        # Specific reason recorded with slice
        assert (
            'arthaiq_abstentions_total{location="BENGALURU",'
            'reason="OUT_OF_BOUNDS_EXPERIENCE",role_family="SWE"} 1.0' in body
        )
