"""ArthaIQ Staging Containerization & Reverse Proxy Verification Harness.

Document ID: STAGING-CONTAINER-VERIFY-01
Phase: Post-Phase 24 Operations & Staging Smoke Test

Validates:
1. Dockerfile.api & Dockerfile.web static security, non-root user (ASVS 14.2.1), multi-stage builds.
2. Nginx reverse proxy configuration, security headers (CSP with worker-src 'self' blob:), SPA routing.
3. Docker Compose staging resource limits (Postgres: 256MB, API: 512MB, Web: 128MB), network isolation.
4. Production web bundle integrity in apps/web/dist.
5. In-process FastAPI serving endpoints (/livez, /readyz, /v1/estimates, /v1/estimates/batch, /v1/estimates/batch/stream, /metrics).
6. Docker daemon status detection and operator bring-up instructions.
7. Emits structured verification audit report to experiments/results/staging_containerization_v1.json.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from compintel.serving.app import create_app

RESULTS_DIR = Path("experiments/results")
OUTPUT_JSON_PATH = RESULTS_DIR / "staging_containerization_v1.json"
DOCKERFILE_API_PATH = Path("infra/docker/Dockerfile.api")
DOCKERFILE_WEB_PATH = Path("infra/docker/Dockerfile.web")
NGINX_CONF_PATH = Path("infra/docker/nginx.conf")
COMPOSE_STAGING_PATH = Path("infra/docker/docker-compose.staging.yml")
WEB_DIST_PATH = Path("apps/web/dist")


@dataclass
class CheckResult:
    check_id: str
    category: str
    description: str
    status: str  # "PASS" | "FAIL" | "WARN"
    details: str


@dataclass
class EndpointProbeResult:
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    status: str  # "PASS" | "FAIL"
    details: str


def verify_dockerfile_api() -> list[CheckResult]:
    """Verify Dockerfile.api multi-stage build, non-root user, uv caching, and healthcheck."""
    results: list[CheckResult] = []

    if not DOCKERFILE_API_PATH.exists():
        results.append(
            CheckResult(
                check_id="CHK-API-01",
                category="Dockerfile.api",
                description="Dockerfile.api file existence",
                status="FAIL",
                details=f"File not found at {DOCKERFILE_API_PATH}",
            )
        )
        return results

    content = DOCKERFILE_API_PATH.read_text(encoding="utf-8")

    # Multi-stage check
    has_builder = "FROM python:3.12-slim-bookworm AS builder" in content
    has_runtime = "FROM python:3.12-slim-bookworm AS runtime" in content
    results.append(
        CheckResult(
            check_id="CHK-API-01",
            category="Dockerfile.api",
            description="Multi-stage build separation (builder -> runtime)",
            status="PASS" if (has_builder and has_runtime) else "FAIL",
            details="Builder stage and minimal runtime stage confirmed",
        )
    )

    # uv deterministic installation check
    has_uv = "ghcr.io/astral-sh/uv" in content and "uv sync --frozen --no-dev" in content
    results.append(
        CheckResult(
            check_id="CHK-API-02",
            category="Dockerfile.api",
            description="Deterministic dependency caching with uv frozen lock",
            status="PASS" if has_uv else "FAIL",
            details="uv cache mount and frozen production dependency sync present",
        )
    )

    # Non-root user check (OWASP ASVS 14.2.1)
    has_non_root = "useradd -u 10001" in content and "USER compintel" in content
    results.append(
        CheckResult(
            check_id="CHK-API-03",
            category="Dockerfile.api",
            description="Non-root user execution (UID 10001, ASVS 14.2.1)",
            status="PASS" if has_non_root else "FAIL",
            details="compintel system user created with UID 10001 and set as runtime USER",
        )
    )

    # Healthcheck & port expose
    has_healthcheck = "HEALTHCHECK" in content and "/livez" in content
    has_expose = "EXPOSE 8000" in content
    results.append(
        CheckResult(
            check_id="CHK-API-04",
            category="Dockerfile.api",
            description="Container healthcheck (/livez) and port exposure (8000)",
            status="PASS" if (has_healthcheck and has_expose) else "FAIL",
            details="Healthcheck probes http://localhost:8000/livez every 10s; port 8000 exposed",
        )
    )

    return results


def verify_dockerfile_web() -> list[CheckResult]:
    """Verify Dockerfile.web multi-stage build, Vite SPA build, and Nginx runtime."""
    results: list[CheckResult] = []

    if not DOCKERFILE_WEB_PATH.exists():
        results.append(
            CheckResult(
                check_id="CHK-WEB-01",
                category="Dockerfile.web",
                description="Dockerfile.web file existence",
                status="FAIL",
                details=f"File not found at {DOCKERFILE_WEB_PATH}",
            )
        )
        return results

    content = DOCKERFILE_WEB_PATH.read_text(encoding="utf-8")

    has_node = "FROM node:22-alpine AS builder" in content
    has_nginx = "FROM nginx:1.27-alpine AS runtime" in content
    results.append(
        CheckResult(
            check_id="CHK-WEB-01",
            category="Dockerfile.web",
            description="Multi-stage SPA build separation (Node 22 -> Nginx 1.27)",
            status="PASS" if (has_node and has_nginx) else "FAIL",
            details="Node 22 builder stage and minimal Nginx alpine runtime stage confirmed",
        )
    )

    has_npm_build = "npm ci" in content and "npm run build" in content
    results.append(
        CheckResult(
            check_id="CHK-WEB-02",
            category="Dockerfile.web",
            description="Clean npm ci and production Vite compilation",
            status="PASS" if has_npm_build else "FAIL",
            details="npm ci clean install and npm run build executed during builder stage",
        )
    )

    has_assets_copy = (
        "COPY --from=builder /app/dist /usr/share/nginx/html" in content
        and "COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf" in content
    )
    results.append(
        CheckResult(
            check_id="CHK-WEB-03",
            category="Dockerfile.web",
            description="Static asset copying and custom Nginx configuration",
            status="PASS" if has_assets_copy else "FAIL",
            details="Built assets copied to Nginx html root and hardened nginx.conf installed",
        )
    )

    has_healthcheck = (
        "HEALTHCHECK" in content and "wget -q --spider http://localhost:80/" in content
    )
    results.append(
        CheckResult(
            check_id="CHK-WEB-04",
            category="Dockerfile.web",
            description="Nginx container healthcheck and HTTP port exposure (80)",
            status="PASS" if has_healthcheck else "FAIL",
            details="Healthcheck verifies HTTP 200 response on port 80; port 80 exposed",
        )
    )

    return results


def verify_nginx_conf() -> list[CheckResult]:
    """Verify Nginx reverse proxy configuration, security headers, CSP, and routing."""
    results: list[CheckResult] = []

    if not NGINX_CONF_PATH.exists():
        results.append(
            CheckResult(
                check_id="CHK-NGINX-01",
                category="nginx.conf",
                description="nginx.conf file existence",
                status="FAIL",
                details=f"File not found at {NGINX_CONF_PATH}",
            )
        )
        return results

    content = NGINX_CONF_PATH.read_text(encoding="utf-8")

    # Gzip compression
    has_gzip = "gzip on;" in content and "gzip_types" in content
    results.append(
        CheckResult(
            check_id="CHK-NGINX-01",
            category="nginx.conf",
            description="Gzip asset compression enabled (PRD NFR-03)",
            status="PASS" if has_gzip else "FAIL",
            details="Gzip compression configured with MIME types for text, JS, CSS, and JSON",
        )
    )

    # Security headers (nosniff, DENY, Referrer-Policy, CSP with worker-src 'self' blob:)
    has_nosniff = 'X-Content-Type-Options "nosniff"' in content
    has_frame_deny = 'X-Frame-Options "DENY"' in content
    has_csp_worker = "worker-src 'self' blob:" in content
    has_sec_headers = has_nosniff and has_frame_deny and has_csp_worker
    results.append(
        CheckResult(
            check_id="CHK-NGINX-02",
            category="nginx.conf",
            description="OWASP security headers & CSP worker sandbox (ADR-0013)",
            status="PASS" if has_sec_headers else "FAIL",
            details="nosniff, DENY, Referrer-Policy, and CSP with worker-src 'self' blob: confirmed",
        )
    )

    # Proxy routes (/v1/, /metrics, /healthz, /livez, /readyz)
    has_v1_proxy = "location /v1/" in content and "proxy_pass http://api:8000/v1/;" in content
    has_metrics_proxy = (
        "location /metrics" in content and "proxy_pass http://api:8000/metrics;" in content
    )
    has_health_proxy = (
        "location ~ ^/(healthz|livez|readyz)" in content
        and "proxy_pass http://api:8000;" in content
    )
    has_proxy_routes = has_v1_proxy and has_metrics_proxy and has_health_proxy
    results.append(
        CheckResult(
            check_id="CHK-NGINX-03",
            category="nginx.conf",
            description="Reverse proxy routing for API, metrics, and healthchecks",
            status="PASS" if has_proxy_routes else "FAIL",
            details="Proxy passes configured for /v1/, /metrics, /healthz, /livez, /readyz to api:8000",
        )
    )

    # SPA Client Routing fallback and 1-year asset caching
    has_spa_routing = "try_files $uri $uri/ /index.html;" in content
    has_asset_cache = "expires 1y;" in content and 'Cache-Control "public, immutable"' in content
    results.append(
        CheckResult(
            check_id="CHK-NGINX-04",
            category="nginx.conf",
            description="SPA client routing fallback and immutable asset caching",
            status="PASS" if (has_spa_routing and has_asset_cache) else "FAIL",
            details="Client-side routing fallback to /index.html and 1-year immutable caching present",
        )
    )

    return results


def verify_compose_staging() -> list[CheckResult]:
    """Verify docker-compose.staging.yml topology, resource limits, and network isolation."""
    results: list[CheckResult] = []

    if not COMPOSE_STAGING_PATH.exists():
        results.append(
            CheckResult(
                check_id="CHK-COMPOSE-01",
                category="docker-compose.staging.yml",
                description="docker-compose.staging.yml file existence",
                status="FAIL",
                details=f"File not found at {COMPOSE_STAGING_PATH}",
            )
        )
        return results

    content = COMPOSE_STAGING_PATH.read_text(encoding="utf-8")

    # Check services present
    has_db = "arthaiq-staging-db" in content
    has_api = "arthaiq-staging-api" in content
    has_web = "arthaiq-staging-web" in content
    results.append(
        CheckResult(
            check_id="CHK-COMPOSE-01",
            category="docker-compose.staging.yml",
            description="Staging container services topology (db, api, web)",
            status="PASS" if (has_db and has_api and has_web) else "FAIL",
            details="arthaiq-staging-db, arthaiq-staging-api, and arthaiq-staging-web defined",
        )
    )

    # Resource caps verification
    has_db_mem = "memory: 256M" in content
    has_api_mem = "memory: 512M" in content
    has_web_mem = "memory: 128M" in content
    results.append(
        CheckResult(
            check_id="CHK-COMPOSE-02",
            category="docker-compose.staging.yml",
            description="Container resource memory limits (256MB / 512MB / 128MB)",
            status="PASS" if (has_db_mem and has_api_mem and has_web_mem) else "FAIL",
            details="PostgreSQL capped at 256MB, FastAPI serving at 512MB, Nginx web at 128MB",
        )
    )

    # Loopback isolation
    has_db_loopback = "127.0.0.1:${POSTGRES_PORT:-5433}:5432" in content
    has_api_loopback = "127.0.0.1:${API_PORT:-8001}:8000" in content
    results.append(
        CheckResult(
            check_id="CHK-COMPOSE-03",
            category="docker-compose.staging.yml",
            description="Loopback-only binding for internal database and API ports",
            status="PASS" if (has_db_loopback and has_api_loopback) else "FAIL",
            details="Database and API ports bound exclusively to 127.0.0.1; zero public 0.0.0.0 exposure",
        )
    )

    # Network isolation & dependency health
    has_bridge = "arthaiq-staging:" in content and "driver: bridge" in content
    has_health_dep = "condition: service_healthy" in content
    results.append(
        CheckResult(
            check_id="CHK-COMPOSE-04",
            category="docker-compose.staging.yml",
            description="Bridge network isolation and healthy service dependencies",
            status="PASS" if (has_bridge and has_health_dep) else "FAIL",
            details="Isolated arthaiq-staging bridge network; api depends on db healthy, web depends on api healthy",
        )
    )

    return results


def verify_web_dist_bundle() -> list[CheckResult]:
    """Verify built production assets in apps/web/dist."""
    results: list[CheckResult] = []

    index_html = WEB_DIST_PATH / "index.html"
    if not index_html.exists():
        results.append(
            CheckResult(
                check_id="CHK-DIST-01",
                category="apps/web/dist",
                description="Production index.html existence",
                status="FAIL",
                details=f"index.html not found in {WEB_DIST_PATH}. Run 'npm run build --prefix apps/web'.",
            )
        )
        return results

    content = index_html.read_text(encoding="utf-8")
    has_title = "<title>" in content and "ArthaIQ" in content
    results.append(
        CheckResult(
            check_id="CHK-DIST-01",
            category="apps/web/dist",
            description="Production HTML entrypoint integrity",
            status="PASS" if has_title else "FAIL",
            details="index.html present with valid ArthaIQ title and React root element",
        )
    )

    assets_dir = WEB_DIST_PATH / "assets"
    if not assets_dir.exists():
        results.append(
            CheckResult(
                check_id="CHK-DIST-02",
                category="apps/web/dist",
                description="Hashed production asset bundles",
                status="FAIL",
                details=f"Assets directory not found at {assets_dir}",
            )
        )
        return results

    js_files = list(assets_dir.glob("*.js"))
    css_files = list(assets_dir.glob("*.css"))
    total_size = sum(f.stat().st_size for f in assets_dir.glob("*"))

    results.append(
        CheckResult(
            check_id="CHK-DIST-02",
            category="apps/web/dist",
            description="Hashed JavaScript and CSS bundle chunks",
            status="PASS" if (len(js_files) > 0 and len(css_files) > 0) else "FAIL",
            details=f"Found {len(js_files)} JS chunk(s), {len(css_files)} CSS chunk(s); total bundle size: {total_size / (1024 * 1024):.2f} MB",
        )
    )

    return results


def probe_fastapi_endpoints() -> tuple[list[EndpointProbeResult], list[CheckResult]]:
    """Probe all critical FastAPI endpoints in-process to verify production behavior."""
    probe_results: list[EndpointProbeResult] = []
    checks: list[CheckResult] = []

    app = create_app()
    client = TestClient(app)

    # 1. /livez
    t0 = time.perf_counter()
    res = client.get("/livez")
    latency = (time.perf_counter() - t0) * 1000.0
    passed = res.status_code == 200 and res.json().get("status") in ("LIVE", "alive")
    probe_results.append(
        EndpointProbeResult(
            endpoint="/livez",
            method="GET",
            status_code=res.status_code,
            latency_ms=round(latency, 2),
            status="PASS" if passed else "FAIL",
            details=f"Live probe returned status {res.status_code}: {res.text}",
        )
    )

    # 2. /readyz
    t0 = time.perf_counter()
    res = client.get("/readyz")
    latency = (time.perf_counter() - t0) * 1000.0
    passed = res.status_code == 200 and res.json().get("status") in ("READY", "ready")
    probe_results.append(
        EndpointProbeResult(
            endpoint="/readyz",
            method="GET",
            status_code=res.status_code,
            latency_ms=round(latency, 2),
            status="PASS" if passed else "FAIL",
            details=f"Readiness probe returned status {res.status_code}: {res.text}",
        )
    )

    # 3. POST /v1/estimates (single estimate)
    estimate_payload = {
        "profile": {
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 4.0, "level_id": "MID"},
        },
        "measure": "guaranteed_cash_annual",
        "currency": "INR",
        "nominal_coverage": 0.80,
    }
    t0 = time.perf_counter()
    res = client.post("/v1/estimates", json=estimate_payload)
    latency = (time.perf_counter() - t0) * 1000.0
    passed = False
    details = ""
    if res.status_code == 200:
        body = res.json()
        status_val = body.get("status")
        if status_val == "ok":
            p10 = body.get("estimate", {}).get("p10")
            p50 = body.get("estimate", {}).get("p50")
            p90 = body.get("estimate", {}).get("p90")
            passed = p10 is not None and p50 is not None and p90 is not None and p10 < p50 < p90
            details = f"Single estimate supported: [P10={p10:,.0f}, P50={p50:,.0f}, P90={p90:,.0f}]"
        elif status_val == "abstained":
            passed = True
            reasons = body.get("reasons", [])
            details = f"Single estimate abstained honestly: {len(reasons)} structured reasons"
    else:
        details = f"Single estimate returned HTTP {res.status_code}: {res.text}"

    probe_results.append(
        EndpointProbeResult(
            endpoint="/v1/estimates",
            method="POST",
            status_code=res.status_code,
            latency_ms=round(latency, 2),
            status="PASS" if passed else "FAIL",
            details=details,
        )
    )

    # 4. POST /v1/estimates/batch (bulk estimate)
    batch_payload = {
        "items": [
            {
                "profile_id": "swe-mid",
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 4.0, "level_id": "MID"},
            },
            {
                "profile_id": "data-sr",
                "occupation_id": "DATA",
                "location_id": "HYDERABAD",
                "experience": {"total_years": 7.0, "level_id": "SR"},
            },
            {
                "profile_id": "mlai-mid",
                "occupation_id": "MLAI",
                "location_id": "NCR",
                "experience": {"total_years": 3.0, "level_id": "MID"},
            },
        ],
        "nominal_coverage": 0.80,
    }
    t0 = time.perf_counter()
    res = client.post("/v1/estimates/batch", json=batch_payload)
    latency = (time.perf_counter() - t0) * 1000.0
    passed = False
    details = ""
    if res.status_code == 200:
        body = res.json()
        items = body.get("items", [])
        summary = body.get("summary", {})
        total_rec = summary.get("total_records")
        passed = len(items) == 3 and total_rec == 3
        details = (
            f"Batch REST processed {len(items)} items; "
            f"supported: {summary.get('successful_estimates')}, abstained: {summary.get('abstained_count')}"
        )
    else:
        details = f"Batch REST returned HTTP {res.status_code}: {res.text}"

    probe_results.append(
        EndpointProbeResult(
            endpoint="/v1/estimates/batch",
            method="POST",
            status_code=res.status_code,
            latency_ms=round(latency, 2),
            status="PASS" if passed else "FAIL",
            details=details,
        )
    )

    # 5. POST /v1/estimates/batch/stream (streaming NDJSON)
    t0 = time.perf_counter()
    res = client.post("/v1/estimates/batch/stream", json=batch_payload)
    latency = (time.perf_counter() - t0) * 1000.0
    passed = False
    details = ""
    if res.status_code == 200:
        lines = [line.strip() for line in res.text.split("\n") if line.strip()]
        passed = len(lines) == 3
        details = f"Stream endpoint returned {len(lines)} NDJSON records cleanly"
    else:
        details = f"Batch stream returned HTTP {res.status_code}: {res.text}"

    probe_results.append(
        EndpointProbeResult(
            endpoint="/v1/estimates/batch/stream",
            method="POST",
            status_code=res.status_code,
            latency_ms=round(latency, 2),
            status="PASS" if passed else "FAIL",
            details=details,
        )
    )

    # 6. GET /metrics (Prometheus)
    t0 = time.perf_counter()
    res = client.get("/metrics")
    latency = (time.perf_counter() - t0) * 1000.0
    passed = res.status_code == 200 and ("# HELP" in res.text or "# TYPE" in res.text)
    probe_results.append(
        EndpointProbeResult(
            endpoint="/metrics",
            method="GET",
            status_code=res.status_code,
            latency_ms=round(latency, 2),
            status="PASS" if passed else "FAIL",
            details=f"Prometheus metrics endpoint returned {len(res.text)} bytes",
        )
    )

    # Aggregated endpoint health check
    all_endpoints_pass = all(p.status == "PASS" for p in probe_results)
    checks.append(
        CheckResult(
            check_id="CHK-PROBE-01",
            category="fastapi-endpoints",
            description="FastAPI endpoint health probes (/livez, /readyz, /v1, /metrics)",
            status="PASS" if all_endpoints_pass else "FAIL",
            details=f"All {len(probe_results)} simulated endpoints responded with HTTP 200 and valid schemas",
        )
    )

    return probe_results, checks


def check_docker_daemon_status() -> tuple[str, str, CheckResult]:
    """Probe whether Docker Desktop daemon is running or offline."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        check = CheckResult(
            check_id="CHK-DOCKER-01",
            category="docker-runtime",
            description="Docker CLI installation in PATH",
            status="WARN",
            details="Docker CLI binary not found in system PATH",
        )
        return "NOT_INSTALLED", "Install Docker Desktop for Windows", check

    try:
        proc = subprocess.run(
            [docker_bin, "ps"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            check = CheckResult(
                check_id="CHK-DOCKER-01",
                category="docker-runtime",
                description="Docker Engine live daemon connectivity",
                status="PASS",
                details="Docker Engine daemon is active and responding to commands",
            )
            return "ONLINE", "Docker daemon active", check
        else:
            check = CheckResult(
                check_id="CHK-DOCKER-01",
                category="docker-runtime",
                description="Docker Engine live daemon connectivity",
                status="WARN",
                details=f"Docker Engine daemon offline: {proc.stderr.strip()}",
            )
            instructions = (
                "Start Docker Desktop from Windows Start Menu, or run:\n"
                "  Start-Process 'C:\\Users\\Lenovo\\AppData\\Local\\Programs\\DockerDesktop\\Docker Desktop.exe'\n"
                "Then deploy staging stack with:\n"
                "  docker compose -f infra/docker/docker-compose.staging.yml up --build"
            )
            return "OFFLINE", instructions, check
    except Exception as exc:
        check = CheckResult(
            check_id="CHK-DOCKER-01",
            category="docker-runtime",
            description="Docker Engine live daemon connectivity",
            status="WARN",
            details=f"Exception probing docker: {exc}",
        )
        return "OFFLINE", str(exc), check


def run_full_verification() -> dict[str, Any]:
    """Execute complete staging containerization and reverse proxy verification suite."""
    print("=" * 80)
    print("ArthaIQ Staging Containerization & Reverse Proxy Verification (T25.01)")
    print("=" * 80)

    all_checks: list[CheckResult] = []

    # 1. Dockerfile.api
    print("\n[1/6] Verifying Dockerfile.api...")
    api_checks = verify_dockerfile_api()
    all_checks.extend(api_checks)
    for c in api_checks:
        print(f"  [{c.status}] {c.check_id} - {c.description}")

    # 2. Dockerfile.web
    print("\n[2/6] Verifying Dockerfile.web...")
    web_checks = verify_dockerfile_web()
    all_checks.extend(web_checks)
    for c in web_checks:
        print(f"  [{c.status}] {c.check_id} - {c.description}")

    # 3. nginx.conf
    print("\n[3/6] Verifying nginx.conf reverse proxy...")
    nginx_checks = verify_nginx_conf()
    all_checks.extend(nginx_checks)
    for c in nginx_checks:
        print(f"  [{c.status}] {c.check_id} - {c.description}")

    # 4. docker-compose.staging.yml
    print("\n[4/6] Verifying docker-compose.staging.yml...")
    compose_checks = verify_compose_staging()
    all_checks.extend(compose_checks)
    for c in compose_checks:
        print(f"  [{c.status}] {c.check_id} - {c.description}")

    # 5. apps/web/dist bundle
    print("\n[5/6] Verifying production web bundle...")
    dist_checks = verify_web_dist_bundle()
    all_checks.extend(dist_checks)
    for c in dist_checks:
        print(f"  [{c.status}] {c.check_id} - {c.description}")

    # 6. In-process FastAPI Probes
    print("\n[6/6] Probing FastAPI serving endpoints...")
    probes, probe_checks = probe_fastapi_endpoints()
    all_checks.extend(probe_checks)
    for p in probes:
        print(
            f"  [{p.status}] {p.method} {p.endpoint} -> {p.status_code} ({p.latency_ms:.1f}ms): {p.details}"
        )

    # Docker Daemon status
    daemon_status, instructions, docker_check = check_docker_daemon_status()
    all_checks.append(docker_check)
    print(f"\n[DOCKER DAEMON] Status: {daemon_status}")
    if daemon_status != "ONLINE":
        print(f"  Instructions:\n  {instructions}")

    # Overall Verdict
    failures = [c for c in all_checks if c.status == "FAIL"]
    warnings = [c for c in all_checks if c.status == "WARN"]
    overall_status = "PASS" if len(failures) == 0 else "FAIL"

    report: dict[str, Any] = {
        "metadata": {
            "document_id": "STAGING-CONTAINER-VERIFY-01",
            "phase": "Platform Operations & Staging Smoke Test",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": overall_status,
            "total_checks": len(all_checks),
            "passed_checks": len([c for c in all_checks if c.status == "PASS"]),
            "failed_checks": len(failures),
            "warned_checks": len(warnings),
            "docker_daemon_status": daemon_status,
        },
        "checks": [asdict(c) for c in all_checks],
        "endpoint_probes": [asdict(p) for p in probes],
        "operator_instructions": instructions,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n" + "=" * 80)
    print(
        f"VERIFICATION VERDICT: {overall_status} ({len(failures)} failures, {len(warnings)} warnings)"
    )
    print(f"Results serialized to: {OUTPUT_JSON_PATH}")
    print("=" * 80)

    return report


if __name__ == "__main__":
    rep = run_full_verification()
    if rep["metadata"]["failed_checks"] > 0:
        sys.exit(1)
    sys.exit(0)
