"""Contract tests for API Key Authentication and Security Controls (Phase 15C, Gap 11).

Adheres to:
- Rule R-ER-01: RFC 9457 Problem Details for 401 and 403 HTTP error contracts.
- Rule R-CR-12 & ADR-0012: Stateless authentication without persistent user tracking.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from compintel.serving.app import create_app
from compintel.serving.routers.career import career_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Reset career API sliding window rate limiter between test cases."""
    career_rate_limiter.reset()


@pytest.fixture
def base_client() -> TestClient:
    """Create test client with default settings (auth optional in test environment)."""
    app = create_app()
    return TestClient(app)


@pytest.mark.contract
class TestAuthenticationContracts:
    """Verify stateless API key authentication behavior and RFC 9457 error contracts."""

    def test_health_probes_always_exempt_from_auth(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Health and telemetry endpoints must remain accessible without credentials."""
        monkeypatch.setenv("ARTHAIQ_AUTH_REQUIRED", "true")
        monkeypatch.setenv("ARTHAIQ_API_KEYS", "secret-test-key-1,secret-test-key-2")
        app = create_app()
        client = TestClient(app)

        res_healthz = client.get("/healthz")
        assert res_healthz.status_code == 200

        res_livez = client.get("/livez")
        assert res_livez.status_code == 200

        res_readyz = client.get("/readyz")
        assert res_readyz.status_code == 200

        res_metrics = client.get("/metrics")
        assert res_metrics.status_code == 200

    def test_protected_endpoint_returns_401_when_key_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Rule R-ER-01: Missing API key returns 401 RFC 9457 ProblemDetails."""
        monkeypatch.setenv("ARTHAIQ_AUTH_REQUIRED", "true")
        monkeypatch.setenv("ARTHAIQ_API_KEYS", "secret-test-key-1")
        app = create_app()
        client = TestClient(app)

        res = client.get("/v1/career/taxonomy")
        assert res.status_code == 401
        assert res.headers["Content-Type"] == "application/problem+json"
        assert "ApiKey" in res.headers.get("WWW-Authenticate", "")

        problem = res.json()
        assert problem["status"] == 401
        assert problem["code"] == "AUTHENTICATION_REQUIRED"
        assert "Authentication Required" in problem["title"]
        assert "request_id" in problem

    def test_protected_endpoint_returns_403_when_key_invalid(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Rule R-ER-01: Invalid API key returns 403 RFC 9457 ProblemDetails."""
        monkeypatch.setenv("ARTHAIQ_AUTH_REQUIRED", "true")
        monkeypatch.setenv("ARTHAIQ_API_KEYS", "secret-test-key-1")
        app = create_app()
        client = TestClient(app)

        res = client.get("/v1/career/taxonomy", headers={"X-API-Key": "wrong-key"})
        assert res.status_code == 403
        assert res.headers["Content-Type"] == "application/problem+json"

        problem = res.json()
        assert problem["status"] == 403
        assert problem["code"] == "INVALID_API_KEY"
        assert "Forbidden" in problem["title"]
        assert "request_id" in problem

    def test_protected_endpoint_succeeds_with_valid_x_api_key(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Valid X-API-Key header permits authorized API requests."""
        monkeypatch.setenv("ARTHAIQ_AUTH_REQUIRED", "true")
        monkeypatch.setenv("ARTHAIQ_API_KEYS", "secret-test-key-1,secret-test-key-2")
        app = create_app()
        client = TestClient(app)

        res = client.get("/v1/career/taxonomy", headers={"X-API-Key": "secret-test-key-1"})
        assert res.status_code == 200
        assert res.json()["role_family"] == "DATA"

    def test_protected_endpoint_succeeds_with_bearer_token(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Valid Authorization: Bearer <key> header permits authorized API requests."""
        monkeypatch.setenv("ARTHAIQ_AUTH_REQUIRED", "true")
        monkeypatch.setenv("ARTHAIQ_API_KEYS", "secret-test-key-1")
        app = create_app()
        client = TestClient(app)

        res = client.get(
            "/v1/career/taxonomy",
            headers={"Authorization": "Bearer secret-test-key-1"},
        )
        assert res.status_code == 200
        assert res.json()["role_family"] == "DATA"

    def test_protected_endpoint_succeeds_with_test_bypass_header(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test bypass header allows internal testing fixtures without credentials."""
        monkeypatch.setenv("ARTHAIQ_AUTH_REQUIRED", "true")
        monkeypatch.setenv("ARTHAIQ_API_KEYS", "secret-test-key-1")
        app = create_app()
        client = TestClient(app)

        res = client.get("/v1/career/taxonomy", headers={"X-Bypass-Auth": "true"})
        assert res.status_code == 200
        assert res.json()["role_family"] == "DATA"
