"""Contract tests for POST /v1/estimates endpoint (Phase 9, Task T9.03).

Verifies:
- architecture.md Section 11: POST /v1/estimates contract.
- PRD Section 5 & FR-02/FR-19: Six targets, quantile spans (P10, P50, P90), decoupled evidence.
- Rule R-ER-02: Expected outcomes (abstention) return HTTP 200 result types, never exceptions.
- Rule R-UQ-01: Calibrated P10, P50, P90 quantile spans with no lone numbers.
- Rule R-UQ-02: Structured abstention with explicit reason codes and actionable fallbacks.
- Rule R-MD-13: Current pay compare-only positioning quarantine (never alters base quantiles).
- Rule R-MD-07: Guaranteed annual cash measure isolation (rejects other measures).
- RFC 9457 error contracts on validation failure (422) and uninitialized manager (503).
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from compintel.models.bundle import UnifiedPredictionResult
from compintel.schema.enums import CompensationMeasure, Currency
from compintel.serving.app import create_app
from compintel.serving.core import reset_default_serving_manager
from compintel.serving.loader import ServingModelManager


@pytest.fixture(autouse=True)
def _reset_serving_state() -> None:
    """Reset module-level default manager before and after tests."""
    reset_default_serving_manager()
    yield
    reset_default_serving_manager()


@pytest.fixture
def mock_supported_manager() -> ServingModelManager:
    """Fixture producing a mock ServingModelManager that returns supported predictions."""
    mgr = MagicMock(spec=ServingModelManager)
    mgr.is_ready = True
    mgr.model_version = "0.1.0"
    mgr.active_bundle.metadata.canonical_snapshot_id = "SNAP-CONTRACT-20261019"
    mgr.active_bundle.metadata.model_version = "0.1.0"

    mock_pred = UnifiedPredictionResult(
        target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
        currency=Currency.INR.value,
        nominal_basis="LPA",
        p10=24.50,
        p50=38.00,
        p90=55.00,
        interval_width=30.50,
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
            "s1_cohort_size": {"effective_n": 142},
            "s3_recency": {"observation_age_days": 35.0},
        },
        model_version="0.1.0",
    )
    mgr.predict.return_value = mock_pred
    return mgr


class TestEstimatesContractSupported:
    """Contract tests for supported POST /v1/estimates responses."""

    def test_post_estimates_supported_full_schema(
        self,
        mock_supported_manager: ServingModelManager,
    ) -> None:
        """Supported profile returns HTTP 200 with Estimate payload."""
        app = create_app(manager=mock_supported_manager)
        client = TestClient(app)

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

        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        # Correlation tracing header
        assert "X-Request-ID" in response.headers
        req_id_header = response.headers["X-Request-ID"]

        data = response.json()
        assert data["status"] == "ok"
        assert data["request_id"] == req_id_header
        assert UUID(data["request_id"])  # Valid UUID4

        # Model and Snapshot metadata
        assert data["model_version"] == "0.1.0"
        assert data["data_snapshot_id"] == "SNAP-CONTRACT-20261019"
        assert data["as_of"] == "2026-10-19"
        assert data["disclaimer_id"] == "decision_support_v1"

        # Quantile span verification (Rule R-UQ-01: P10 <= P50 <= P90)
        span = data["estimate"]
        assert span["p10"] == 24.50
        assert span["p50"] == 38.00
        assert span["p90"] == 55.00
        assert span["p10"] <= span["p50"] <= span["p90"]
        assert span["currency"] == "INR"
        assert span["period"] == "annual"
        assert span["measure"] == "guaranteed_cash_annual"
        assert span["pre_tax"] is True
        assert span["nominal"] is True

        # Reliability info (Rule R-UQ-07: decoupled evidence)
        rel = data["reliability"]
        assert rel["grade"] == "GRADE_A"
        assert rel["reasons"] == []

        # Evidence info
        ev = data["evidence"]
        assert ev["cohort_n"] == 142
        assert ev["median_observation_age_days"] == 35.0
        assert ev["data_snapshot_id"] == "SNAP-CONTRACT-20261019"
        assert ev["model_version"] == "0.1.0"

        # Comparison is null when current pay omitted
        assert data["comparison"] is None

    def test_post_estimates_compare_only_quarantine(
        self,
        mock_supported_manager: ServingModelManager,
    ) -> None:
        """Rule R-MD-13: Current pay sets ComparisonInfo without altering base quantiles."""
        app = create_app(manager=mock_supported_manager)
        client = TestClient(app)

        payload_with_current = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {
                    "total_years": 5.0,
                    "level_id": "MID",
                },
            },
            "current_compensation": 32.0,  # 32 LPA
        }

        response = client.post("/v1/estimates", json=payload_with_current)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"

        # Base quantiles remain identical to mock model outputs
        assert data["estimate"]["p10"] == 24.50
        assert data["estimate"]["p50"] == 38.00
        assert data["estimate"]["p90"] == 55.00

        # Comparison info must be populated and calculated accurately
        comp = data["comparison"]
        assert comp is not None
        assert comp["current_compensation"] == 32.0
        assert comp["delta_to_median_lpa"] == round(32.0 - 38.00, 2)  # -6.00 LPA
        assert comp["position_category"] in ("below_median", "below_floor")
        assert comp["percentile_band"] == "P10-P50"

    def test_post_estimates_progressive_personalization_levels(
        self,
        mock_supported_manager: ServingModelManager,
    ) -> None:
        """PRD Section 5: Accepts progressive personalization fields across L0, L1, and L2."""
        app = create_app(manager=mock_supported_manager)
        client = TestClient(app)

        # L2 query with extras
        payload = {
            "profile": {
                "occupation_id": "DATA",
                "location_id": "HYDERABAD",
                "experience": {
                    "total_years": 8.0,
                    "level_id": "SR",
                },
                "extras": {
                    "skills_primary": "python, spark, pytorch",
                    "domain_specialization": "fintech",
                    "target_employer_tier": "tier_1_unicorn",
                    "work_arrangement": "hybrid",
                },
            },
        }

        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestEstimatesContractAbstained:
    """Contract tests for abstained POST /v1/estimates responses."""

    def test_post_estimates_abstained_live_champion_v0(self) -> None:
        """Rule R-UQ-02 & R-ER-02: Thin evidence abstains with HTTP 200 and structured reasons."""
        # Using the real champion bundle in artifacts/champion_v0/
        app = create_app()
        client = TestClient(app)

        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {
                    "total_years": 4.0,
                    "level_id": "MID",
                },
            },
            "as_of": "2026-10-19",
        }

        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        assert data["status"] == "abstained"
        assert "estimate" not in data  # No point estimate numbers exposed

        # Reasons list
        assert len(data["reasons"]) > 0
        for reason in data["reasons"]:
            assert "code" in reason
            assert "detail" in reason

        # Fallbacks list (Rule R-UQ-02: must offer actionable next steps)
        assert len(data["fallbacks"]) > 0
        fallback_types = [fb["type"] for fb in data["fallbacks"]]
        assert "broader_cohort" in fallback_types

        # Required statutory metadata
        assert data["disclaimer_id"] == "decision_support_v1"
        assert data["as_of"] == "2026-10-19"
        assert data["model_version"] == "0.1.0"
        assert data["data_snapshot_id"] is not None

    def test_post_estimates_abstained_custom_mock_reasons(self) -> None:
        """Verify custom abstention reasons propagate cleanly to HTTP 200 response."""
        mgr = MagicMock(spec=ServingModelManager)
        mgr.is_ready = True
        mgr.model_version = "0.1.0"
        mgr.active_bundle.metadata.canonical_snapshot_id = "SNAP-ABSTAIN-001"

        mgr.predict.return_value = UnifiedPredictionResult(
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

        app = create_app(manager=mgr)
        client = TestClient(app)

        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "PUNE",
                "experience": {
                    "total_years": 45.0,
                    "level_id": "PRINCIPAL",
                },
            },
        }

        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "abstained"
        assert data["reasons"][0]["code"] == "OUT_OF_BOUNDS_EXPERIENCE"
        assert "40" in data["reasons"][0]["detail"]


class TestEstimatesContractValidationErrors:
    """Contract tests for RFC 9457 Problem Details on invalid requests (HTTP 422 & 503)."""

    def test_post_estimates_empty_body_returns_rfc9457_422(self) -> None:
        """Empty payload returns RFC 9457 422 problem details."""
        client = TestClient(create_app())
        response = client.post("/v1/estimates", json={})
        assert response.status_code == 422
        assert response.headers["content-type"] == "application/problem+json"

        body = response.json()
        assert body["type"] == "urn:compintel:problem:validation-error"
        assert body["status"] == 422
        assert body["code"] == "VALIDATION_ERROR"
        assert "X-Request-ID" in response.headers
        assert body["request_id"] == response.headers["X-Request-ID"]

    def test_post_estimates_missing_required_profile_fields_rfc9457(self) -> None:
        """Missing occupation_id and location_id returns 422 with structured error pointers."""
        client = TestClient(create_app())
        payload = {
            "profile": {
                "experience": {"total_years": 3.0},
            }
        }
        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 422
        body = response.json()
        error_locs = [e["location"] for e in body["errors"]]
        assert any("occupation_id" in loc for loc in error_locs)
        assert any("location_id" in loc for loc in error_locs)

    def test_post_estimates_unsupported_measure_returns_rfc9457_422(self) -> None:
        """Rule R-MD-07: Non-guaranteed cash measure rejected with RFC 9457 422."""
        client = TestClient(create_app())
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
            },
            "measure": "total_ctc",  # Forbidden Indian CTC illusion measure
        }
        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "UNSUPPORTED_MEASURE"
        assert "guaranteed_cash_annual" in body["detail"]

    def test_post_estimates_unsupported_currency_returns_rfc9457_422(self) -> None:
        """Non-INR currency rejected with RFC 9457 422."""
        client = TestClient(create_app())
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
            },
            "currency": "USD",
        }
        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "UNSUPPORTED_CURRENCY"

    def test_post_estimates_invalid_experience_bounds_rfc9457_422(self) -> None:
        """Out of bounds experience (years > 50) rejected with RFC 9457 422."""
        client = TestClient(create_app())
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {
                    "total_years": 80.0,
                },
            },
        }
        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert any("total_years" in e["location"] for e in body["errors"])

    def test_post_estimates_unready_manager_returns_rfc9457_503(self) -> None:
        """When manager has no active bundle loaded, returns RFC 9457 503 Service Unavailable."""
        unready_mgr = ServingModelManager()
        app = create_app(manager=unready_mgr)
        client = TestClient(app)

        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
            },
        }

        response = client.post("/v1/estimates", json=payload)
        assert response.status_code == 503
        assert response.headers["content-type"] == "application/problem+json"

        body = response.json()
        assert body["status"] == 503
        assert body["code"] == "NO_ACTIVE_BUNDLE"
        assert "not ready" in body["detail"]
