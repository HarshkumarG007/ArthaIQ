"""Contract tests for RFC 9457 Problem Details error responses and HTTP contracts (T9.02).

Adheres to:
- architecture.md Section 11: Errors use RFC 9457 problem details with stable codes and request id.
- Rule R-ER-04: API errors use RFC 9457 problem details with stable codes and request id.
  422 for validation, 429 with Retry-After, 5xx without stack traces or internal paths.
  Abstention is HTTP 200 with status: 'abstained'.
- Rule R-ER-02: Expected outcomes return result types, not exceptions.
- Rule R-CD-03: Architectural boundary; serving never imports ingestion/quality/eval.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from compintel.serving import create_app
from compintel.serving.errors import PROBLEM_MEDIA_TYPE
from compintel.serving.loader import ServingModelManager


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient with a fresh app instance."""
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fault_injection_client() -> TestClient:
    """Create a TestClient with a route deliberately throwing unhandled exceptions."""
    app = create_app()

    test_router = APIRouter()

    @test_router.get("/test/fault-trigger")
    def trigger_internal_fault() -> None:
        msg = "Critical database failure with credentials: postgres://user:secretpass@10.0.0.1/db"
        raise RuntimeError(msg)

    app.include_router(test_router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.contract
class TestRFC9457ErrorContracts:
    """Verify API error payloads comply with RFC 9457 Problem Details standard."""

    def test_404_not_found_returns_rfc9457_problem_details(self, client: TestClient) -> None:
        """Rule R-ER-04: 404 returns RFC 9457 problem details with stable code."""
        res = client.get("/v1/non-existent-endpoint")
        assert res.status_code == 404
        assert PROBLEM_MEDIA_TYPE in res.headers["content-type"]

        body = res.json()
        assert body["status"] == 404
        assert body["code"] == "RESOURCE_NOT_FOUND"
        assert body["type"] == "urn:compintel:problem:resource_not_found"
        assert body["instance"] == "/v1/non-existent-endpoint"
        assert "request_id" in body
        assert UUID(body["request_id"])  # Valid UUID4

        # Response headers must include X-Request-ID matching body
        assert res.headers["X-Request-ID"] == body["request_id"]

    def test_405_method_not_allowed_returns_rfc9457(self, client: TestClient) -> None:
        """Rule R-ER-04: 405 returns RFC 9457 problem details."""
        res = client.post("/healthz")
        assert res.status_code == 405
        assert PROBLEM_MEDIA_TYPE in res.headers["content-type"]

        body = res.json()
        assert body["status"] == 405
        assert body["code"] == "METHOD_NOT_ALLOWED"
        assert body["type"] == "urn:compintel:problem:method_not_allowed"
        assert "request_id" in body

    def test_422_schema_validation_error_returns_rfc9457(self, client: TestClient) -> None:
        """Rule R-ER-04: Request payload validation failure returns 422 with error list."""
        res = client.post("/v1/estimates", json={})
        assert res.status_code == 422
        assert PROBLEM_MEDIA_TYPE in res.headers["content-type"]

        body = res.json()
        assert body["status"] == 422
        assert body["code"] == "VALIDATION_ERROR"
        assert body["title"] == "Unprocessable Entity"
        assert body["instance"] == "/v1/estimates"
        assert "errors" in body
        assert isinstance(body["errors"], list)
        assert len(body["errors"]) > 0

    def test_422_unsupported_measure_rejected(self, client: TestClient) -> None:
        """Rule R-MD-07: Anti-heuristic unbundling; PT1 strictly guaranteed_cash_annual."""
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 5.0},
            },
            "measure": "total_cost_to_company",
        }
        res = client.post("/v1/estimates", json=payload)
        assert res.status_code == 422
        assert PROBLEM_MEDIA_TYPE in res.headers["content-type"]

        body = res.json()
        assert body["status"] == 422
        assert body["code"] == "UNSUPPORTED_MEASURE"
        assert "guaranteed_cash_annual" in body["detail"]

    def test_422_unsupported_currency_rejected(self, client: TestClient) -> None:
        """ArthaIQ strictly prices in INR nominal."""
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 5.0},
            },
            "currency": "USD",
        }
        res = client.post("/v1/estimates", json=payload)
        assert res.status_code == 422
        assert PROBLEM_MEDIA_TYPE in res.headers["content-type"]

        body = res.json()
        assert body["status"] == 422
        assert body["code"] == "UNSUPPORTED_CURRENCY"
        assert "INR" in body["detail"]

    def test_422_out_of_bounds_experience_rejected(self, client: TestClient) -> None:
        """Domain validation: experience years domain [0.0, 50.0]."""
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 65.0},
            },
        }
        res = client.post("/v1/estimates", json=payload)
        assert res.status_code == 422
        assert PROBLEM_MEDIA_TYPE in res.headers["content-type"]

        body = res.json()
        assert body["status"] == 422
        assert body["code"] == "VALIDATION_ERROR"
        assert "errors" in body
        assert any("total_years" in err["location"] for err in body["errors"])

    def test_503_when_no_active_model_bundle_loaded(self) -> None:
        """Rule R-MD-14: Unpromoted/unready manager returns 503 Problem Details."""
        unready_manager = ServingModelManager()
        app = create_app(manager=unready_manager)
        client = TestClient(app, raise_server_exceptions=False)

        # Health endpoint indicates 503
        health_res = client.get("/healthz")
        assert health_res.status_code == 503
        assert health_res.json()["is_ready"] is False

        # Estimates endpoint returns 503 problem details
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 5.0},
            },
        }
        res = client.post("/v1/estimates", json=payload)
        assert res.status_code == 503
        assert PROBLEM_MEDIA_TYPE in res.headers["content-type"]

        body = res.json()
        assert body["status"] == 503
        assert body["code"] == "NO_ACTIVE_BUNDLE"

    def test_500_internal_server_fault_masks_stack_traces_and_secrets(
        self,
        fault_injection_client: TestClient,
    ) -> None:
        """Rule R-ER-04: 5xx without stack traces, secret leaks, or internal paths."""
        res = fault_injection_client.get("/test/fault-trigger")
        assert res.status_code == 500
        assert PROBLEM_MEDIA_TYPE in res.headers["content-type"]

        body = res.json()
        assert body["status"] == 500
        assert body["code"] == "INTERNAL_SERVER_ERROR"
        assert body["title"] == "Internal Server Error"
        assert body["detail"] == "An internal server error occurred while processing the request."

        raw_text = res.text
        # Strict Invariant: Zero leaks of stack traces, internal paths, or credentials
        assert "Traceback" not in raw_text
        assert "secretpass" not in raw_text
        assert "postgres://" not in raw_text
        assert ".py" not in raw_text
        assert "File " not in raw_text


@pytest.mark.contract
class TestRequestCorrelationAndSecurityHeaders:
    """Verify request tracing headers and HTTP security hardening."""

    def test_client_supplied_request_id_is_preserved_and_propagated(
        self, client: TestClient
    ) -> None:
        """Rule R-ER-04: Inbound X-Request-ID is preserved and echoed in headers and payload."""
        custom_id = "test-corr-id-12345"
        res = client.get("/v1/taxonomy/occupations", headers={"X-Request-ID": custom_id})
        assert res.status_code == 200
        assert res.headers["X-Request-ID"] == custom_id

    def test_missing_request_id_generates_valid_uuid(self, client: TestClient) -> None:
        """Rule R-ER-04: Missing request ID auto-generates RFC 4122 UUID4."""
        res = client.get("/v1/taxonomy/occupations")
        assert res.status_code == 200
        req_id = res.headers.get("X-Request-ID")
        assert req_id is not None
        assert UUID(req_id)

    def test_security_headers_present_on_all_responses(self, client: TestClient) -> None:
        """architecture.md Section 12: Mandatory HTTP security headers."""
        res = client.get("/healthz")
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["X-Frame-Options"] == "DENY"
        assert res.headers["X-XSS-Protection"] == "1; mode=block"
        assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_cors_headers_present_on_preflight_and_response(self, client: TestClient) -> None:
        """CORS preflight and expose headers verification."""
        # 1. Preflight OPTIONS request
        preflight_res = client.options(
            "/v1/estimates",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,X-Request-ID",
            },
        )
        assert preflight_res.status_code == 200
        assert preflight_res.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "X-Request-ID" in preflight_res.headers.get("access-control-allow-headers", "")

        # 2. Actual request with Origin header carries exposed headers
        actual_res = client.get(
            "/healthz",
            headers={"Origin": "http://localhost:3000"},
        )
        assert actual_res.status_code == 200
        assert "X-Request-ID" in actual_res.headers.get("access-control-expose-headers", "")
