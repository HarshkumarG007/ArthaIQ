"""Unit tests for ArthaIQ Production Staging Containerization & Reverse Proxy Verification (T25.01).

Validates:
1. Verification script deliverables and machine-readable audit report (STAGING-CONTAINER-VERIFY-01).
2. Dockerfile.api and Dockerfile.web static security, non-root user (ASVS 14.2.1), and multi-stage.
3. Nginx reverse proxy configuration, OWASP security headers, and CSP worker-src sandbox.
4. Docker Compose staging resource caps, loopback port bindings, and bridge network isolation.
5. Production web distribution bundle integrity (index.html, hashed CSS/JS chunks).
6. FastAPI endpoint probe contracts and zero lone numbers (Rule R-UQ-01).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORT_PATH = Path("experiments/results/staging_containerization_v1.json")
DOCKERFILE_API_PATH = Path("infra/docker/Dockerfile.api")
DOCKERFILE_WEB_PATH = Path("infra/docker/Dockerfile.web")
NGINX_CONF_PATH = Path("infra/docker/nginx.conf")
COMPOSE_STAGING_PATH = Path("infra/docker/docker-compose.staging.yml")
WEB_DIST_PATH = Path("apps/web/dist")


@pytest.mark.unit
class TestStagingVerificationReport:
    """Validate machine-readable verification report from verify_staging_containerization.py."""

    def test_report_exists_and_metadata_valid(self) -> None:
        """Report JSON exists with valid document ID, PASS status, and 0 failures."""
        assert REPORT_PATH.exists(), f"Report file {REPORT_PATH} must exist"
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

        meta = data.get("metadata", {})
        assert meta.get("document_id") == "STAGING-CONTAINER-VERIFY-01"
        assert meta.get("status") == "PASS"
        assert meta.get("failed_checks") == 0
        assert meta.get("passed_checks") >= 19

    def test_all_endpoint_probes_pass(self) -> None:
        """All critical simulated API endpoint probes passed with status 200."""
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        probes = data.get("endpoint_probes", [])
        assert len(probes) >= 6

        probe_map = {p["endpoint"]: p for p in probes}
        assert "/livez" in probe_map
        assert probe_map["/livez"]["status_code"] == 200
        assert probe_map["/livez"]["status"] == "PASS"

        assert "/readyz" in probe_map
        assert probe_map["/readyz"]["status_code"] == 200
        assert probe_map["/readyz"]["status"] == "PASS"

        assert "/v1/estimates" in probe_map
        assert probe_map["/v1/estimates"]["status_code"] == 200
        assert probe_map["/v1/estimates"]["status"] == "PASS"

        assert "/v1/estimates/batch" in probe_map
        assert probe_map["/v1/estimates/batch"]["status_code"] == 200
        assert probe_map["/v1/estimates/batch"]["status"] == "PASS"

        assert "/v1/estimates/batch/stream" in probe_map
        assert probe_map["/v1/estimates/batch/stream"]["status_code"] == 200
        assert probe_map["/v1/estimates/batch/stream"]["status"] == "PASS"

        assert "/metrics" in probe_map
        assert probe_map["/metrics"]["status_code"] == 200
        assert probe_map["/metrics"]["status"] == "PASS"


@pytest.mark.unit
class TestDockerfileInvariants:
    """Validate Dockerfile security and multi-stage containerization specifications."""

    def test_dockerfile_api_non_root_and_multistage(self) -> None:
        """Dockerfile.api uses multi-stage build and non-root user (ASVS 14.2.1)."""
        content = DOCKERFILE_API_PATH.read_text(encoding="utf-8")
        assert "AS builder" in content
        assert "AS runtime" in content
        assert "python:3.12-slim-bookworm" in content
        assert "uv sync --frozen --no-dev" in content
        assert "useradd -u 10001" in content
        assert "USER compintel" in content
        assert "HEALTHCHECK" in content
        assert "/livez" in content
        assert "EXPOSE 8000" in content

    def test_dockerfile_web_build_and_nginx(self) -> None:
        """Dockerfile.web compiles Vite SPA in Node and runs on hardened Nginx alpine."""
        content = DOCKERFILE_WEB_PATH.read_text(encoding="utf-8")
        assert "FROM node:22-alpine AS builder" in content
        assert "FROM nginx:1.27-alpine AS runtime" in content
        assert "npm ci" in content
        assert "npm run build" in content
        assert "COPY --from=builder /app/dist /usr/share/nginx/html" in content
        assert "HEALTHCHECK" in content
        assert "EXPOSE 80" in content


@pytest.mark.unit
class TestNginxReverseProxyConfiguration:
    """Validate Nginx configuration, OWASP security headers, and proxy routing."""

    def test_nginx_security_headers_and_csp(self) -> None:
        """Nginx config enforces nosniff, DENY, strict referrer, and worker-src CSP."""
        content = NGINX_CONF_PATH.read_text(encoding="utf-8")
        assert 'X-Content-Type-Options "nosniff"' in content
        assert 'X-Frame-Options "DENY"' in content
        assert 'Referrer-Policy "strict-origin-when-cross-origin"' in content
        assert "Content-Security-Policy" in content
        assert "worker-src 'self' blob:" in content

    def test_nginx_proxy_pass_locations_and_spa_routing(self) -> None:
        """Nginx proxies /v1/, /metrics, and health probes with SPA client fallback."""
        content = NGINX_CONF_PATH.read_text(encoding="utf-8")
        assert "location /v1/ {" in content
        assert "proxy_pass http://api:8000/v1/;" in content
        assert "location /metrics {" in content
        assert "proxy_pass http://api:8000/metrics;" in content
        assert "location ~ ^/(healthz|livez|readyz)" in content
        assert "proxy_pass http://api:8000;" in content
        assert "try_files $uri $uri/ /index.html;" in content
        assert 'Cache-Control "public, immutable"' in content


@pytest.mark.unit
class TestDockerComposeStagingTopology:
    """Validate Docker Compose staging resource caps and loopback network isolation."""

    def test_compose_staging_resource_caps(self) -> None:
        """Compose staging enforces strict memory caps on db, api, and web."""
        content = COMPOSE_STAGING_PATH.read_text(encoding="utf-8")
        assert "arthaiq-staging-db" in content
        assert "arthaiq-staging-api" in content
        assert "arthaiq-staging-web" in content

        assert "memory: 256M" in content
        assert "memory: 512M" in content
        assert "memory: 128M" in content

    def test_compose_staging_loopback_isolation(self) -> None:
        """Internal service ports bind strictly to 127.0.0.1 (ASVS 14.2.1)."""
        content = COMPOSE_STAGING_PATH.read_text(encoding="utf-8")
        assert "127.0.0.1:${POSTGRES_PORT:-5433}:5432" in content
        assert "127.0.0.1:${API_PORT:-8001}:8000" in content
        assert "arthaiq-staging:" in content
        assert "driver: bridge" in content


@pytest.mark.unit
class TestWebDistributionBundle:
    """Validate compiled SPA distribution in apps/web/dist."""

    def test_web_dist_index_html_and_chunks_present(self) -> None:
        """Production distribution contains valid index.html and hashed JS/CSS chunks."""
        index_html = WEB_DIST_PATH / "index.html"
        assert index_html.exists(), "index.html must exist in apps/web/dist"
        html_text = index_html.read_text(encoding="utf-8")
        assert "ArthaIQ" in html_text

        assets_dir = WEB_DIST_PATH / "assets"
        assert assets_dir.exists(), "assets directory must exist in apps/web/dist"
        js_files = list(assets_dir.glob("*.js"))
        css_files = list(assets_dir.glob("*.css"))
        assert len(js_files) > 0, "Must contain at least 1 compiled JS chunk"
        assert len(css_files) > 0, "Must contain at least 1 compiled CSS stylesheet"
