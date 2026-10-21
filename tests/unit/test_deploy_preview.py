"""Unit tests for preview deployment containerization, compose config,
and orchestration harness (T9.14a).

Validates:
1. Dockerfile.api multi-stage build, non-root user (ASVS 14.2.1), uv caching, and healthcheck.
2. Dockerfile.web multi-stage build, static bundle copying, and healthcheck.
3. Nginx reverse proxy configuration, security headers, and proxy directives.
4. Docker Compose service topology, dependencies, volumes, and networks.
5. scripts/deploy_preview.py CLI commands, dry-run simulation, and HTTP health probes.
"""

from __future__ import annotations

import argparse
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from scripts.deploy_preview import (
    DEFAULT_COMPOSE_PATH,
    build_parser,
    check_docker_available,
    check_endpoint_health,
    cmd_down,
    cmd_health,
    cmd_up,
    main,
    verify_stack_health,
)


# -----------------------------------------------------------------------------
# 1. Dockerfile & Nginx Static Configuration Tests
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_dockerfile_api_structure() -> None:
    """Verifies that Dockerfile.api adheres to production multi-stage security standards."""
    api_dockerfile = Path("infra/docker/Dockerfile.api")
    assert api_dockerfile.exists(), "Dockerfile.api must exist"

    content = api_dockerfile.read_text(encoding="utf-8")

    # Multi-stage validation
    assert "FROM python:3.12-slim-bookworm AS builder" in content
    assert "FROM python:3.12-slim-bookworm AS runtime" in content

    # uv build tool validation
    assert "ghcr.io/astral-sh/uv" in content
    assert "uv sync --frozen --no-dev" in content

    # Security: Non-root user (OWASP ASVS 14.2.1)
    assert "useradd -u 10001 -g compintel" in content
    assert "USER compintel" in content

    # Healthcheck & Expose
    assert "HEALTHCHECK" in content
    assert "/livez" in content
    assert "EXPOSE 8000" in content


@pytest.mark.unit
def test_dockerfile_web_structure() -> None:
    """Verifies that Dockerfile.web adheres to multi-stage SPA compilation standards."""
    web_dockerfile = Path("infra/docker/Dockerfile.web")
    assert web_dockerfile.exists(), "Dockerfile.web must exist"

    content = web_dockerfile.read_text(encoding="utf-8")

    # Multi-stage validation
    assert "FROM node:22-alpine AS builder" in content
    assert "FROM nginx:1.27-alpine AS runtime" in content

    # Node build steps
    assert "npm ci" in content
    assert "npm run build" in content

    # Nginx configuration and static assets copy
    assert "COPY --from=builder /app/dist /usr/share/nginx/html" in content
    assert "COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf" in content

    # Healthcheck & Expose
    assert "HEALTHCHECK" in content
    assert "EXPOSE 80" in content


@pytest.mark.unit
def test_nginx_configuration_security_headers_and_routes() -> None:
    """Verifies that nginx.conf configures required security headers and proxy targets."""
    nginx_conf = Path("infra/docker/nginx.conf")
    assert nginx_conf.exists(), "nginx.conf must exist"

    content = nginx_conf.read_text(encoding="utf-8")

    # Security headers
    assert 'X-Content-Type-Options "nosniff"' in content
    assert 'X-Frame-Options "DENY"' in content
    assert "Content-Security-Policy" in content
    assert "Referrer-Policy" in content

    # Proxy locations
    assert "location /v1/ {" in content
    assert "proxy_pass http://api:8000/v1/;" in content
    assert "location /metrics {" in content
    assert "proxy_pass http://api:8000/metrics;" in content
    assert "location ~ ^/(healthz|livez|readyz)" in content

    # SPA client routing fallback
    assert "try_files $uri $uri/ /index.html;" in content


# -----------------------------------------------------------------------------
# 2. Docker Compose Topology & Syntax Tests
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_docker_compose_valid_yaml_and_topology() -> None:
    """Verifies that docker-compose.yml parses correctly and declares all required services."""
    compose_path = DEFAULT_COMPOSE_PATH
    assert compose_path.exists(), f"Compose file {compose_path} must exist"

    with compose_path.open(encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    assert "db" in services, "PostgreSQL database service must be defined"
    assert "api" in services, "FastAPI backend service must be defined"
    assert "web" in services, "React / Nginx frontend service must be defined"

    # Database service assertions
    db = services["db"]
    assert "postgres" in db["image"]
    assert "healthcheck" in db
    assert "pg_isready" in " ".join(db["healthcheck"]["test"])

    # API backend service assertions
    api = services["api"]
    assert api["build"]["dockerfile"] == "infra/docker/Dockerfile.api"
    assert "db" in api["depends_on"]
    assert api["depends_on"]["db"]["condition"] == "service_healthy"
    assert "healthcheck" in api
    assert "/livez" in " ".join(api["healthcheck"]["test"])

    # Web frontend service assertions
    web = services["web"]
    assert web["build"]["dockerfile"] == "infra/docker/Dockerfile.web"
    assert "api" in web["depends_on"]
    assert web["depends_on"]["api"]["condition"] == "service_healthy"

    # Network and volume assertions
    assert "compintel-preview" in compose_data.get("networks", {})
    assert "pgdata" in compose_data.get("volumes", {})


# -----------------------------------------------------------------------------
# 3. deploy_preview.py CLI & Harness Logic Tests
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_cli_parser_commands() -> None:
    """Tests CLI argument parsing across all subcommands."""
    parser = build_parser()

    # up subcommand
    args_up = parser.parse_args(["up", "--timeout", "45", "--api-url", "http://127.0.0.1:8000"])
    assert args_up.subcommand == "up"
    assert args_up.timeout == 45.0
    assert args_up.api_url == "http://127.0.0.1:8000"
    assert args_up.build is True
    assert args_up.wait is True

    # down subcommand
    args_down = parser.parse_args(["down", "-v"])
    assert args_down.subcommand == "down"
    assert args_down.volumes is True

    # health subcommand
    args_health = parser.parse_args(["health", "--timeout", "10"])
    assert args_health.subcommand == "health"
    assert args_health.timeout == 10.0

    # logs subcommand
    args_logs = parser.parse_args(["logs", "--tail", "50", "api"])
    assert args_logs.subcommand == "logs"
    assert args_logs.tail == 50
    assert args_logs.service == "api"


@pytest.mark.unit
def test_docker_available_dry_run() -> None:
    """Dry run should report Docker as available without invoking system commands."""
    assert check_docker_available(dry_run=True) is True


@pytest.mark.unit
@patch("shutil.which")
@patch("subprocess.run")
def test_check_docker_available_real(mock_run: MagicMock, mock_which: MagicMock) -> None:
    """Tests real check_docker_available logic with mock subprocess."""
    mock_which.return_value = "/usr/bin/docker"
    mock_run.return_value = MagicMock(returncode=0)

    assert check_docker_available(dry_run=False) is True
    mock_run.assert_called_once()

    # When docker binary is missing
    mock_which.return_value = None
    assert check_docker_available(dry_run=False) is False


@pytest.mark.unit
def test_endpoint_health_success() -> None:
    """Tests check_endpoint_health with simulated 200 HTTP response."""
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        healthy, code, msg = check_endpoint_health("http://localhost:8000/livez")
        assert healthy is True
        assert code == 200
        assert msg == "Healthy"


@pytest.mark.unit
def test_endpoint_health_http_error() -> None:
    """Tests check_endpoint_health with simulated 503 HTTP error."""
    mock_error = urllib.error.HTTPError(
        url="http://localhost:8000/readyz",
        code=503,
        msg="Service Unavailable",
        hdrs=MagicMock(),
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=mock_error):
        healthy, code, msg = check_endpoint_health("http://localhost:8000/readyz")
        assert healthy is False
        assert code == 503
        assert "HTTP Error 503" in msg


@pytest.mark.unit
def test_verify_stack_health_dry_run() -> None:
    """Tests verify_stack_health in dry-run mode."""
    results = verify_stack_health(dry_run=True)
    assert len(results) == 4
    assert all(r.healthy for r in results)


@pytest.mark.unit
def test_cmd_up_dry_run() -> None:
    """Tests cmd_up execution with dry_run=True."""
    args = argparse.Namespace(
        dry_run=True,
        build=True,
        wait=True,
        compose_file=str(DEFAULT_COMPOSE_PATH),
        api_url="http://localhost:8000",
        web_url="http://localhost:8080",
        timeout=10.0,
    )
    exit_code = cmd_up(args)
    assert exit_code == 0


@pytest.mark.unit
def test_cmd_down_dry_run() -> None:
    """Tests cmd_down execution with dry_run=True."""
    args = argparse.Namespace(
        dry_run=True,
        volumes=True,
        compose_file=str(DEFAULT_COMPOSE_PATH),
    )
    exit_code = cmd_down(args)
    assert exit_code == 0


@pytest.mark.unit
def test_cmd_health_dry_run() -> None:
    """Tests cmd_health execution with dry_run=True."""
    args = argparse.Namespace(
        dry_run=True,
        api_url="http://localhost:8000",
        web_url="http://localhost:8080",
        timeout=5.0,
    )
    exit_code = cmd_health(args)
    assert exit_code == 0


@pytest.mark.unit
def test_main_entrypoint_up_dry_run() -> None:
    """Tests main entry point with dry-run arguments."""
    exit_code = main(["--dry-run", "up", "--no-wait"])
    assert exit_code == 0


# -----------------------------------------------------------------------------
# 4. Preview Environment IaC & ADR-0009 Ratification Tests (T9.14b)
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_preview_env_iac_specification() -> None:
    """Verifies that infra/deploy/preview-env.yaml contains valid Profile B declarations."""
    iac_path = Path("infra/deploy/preview-env.yaml")
    assert iac_path.exists(), "infra/deploy/preview-env.yaml must exist"

    with iac_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Top-level sections
    assert "environment" in config
    assert "host" in config
    assert "network" in config
    assert "services" in config
    assert "backup_and_retention" in config
    assert "monitoring_and_alerts" in config

    # Profile B specification
    assert config["environment"]["profile"] == "B"
    assert config["environment"]["name"] == "preview"
    assert "t4g.medium" in config["host"]["instance_type"]

    # Services
    services = config["services"]
    assert "nginx" in services
    assert "api" in services
    assert "database" in services
    assert services["api"]["healthcheck"]["path"] == "/livez"


@pytest.mark.unit
def test_adr_0009_ratification_status() -> None:
    """Verifies that ADR-0009 is accepted and documents Profile B decision."""
    adr_path = Path("docs/adr/ADR-0009-hosting-profile-and-operations.md")
    assert adr_path.exists(), "ADR-0009 must exist"

    content = adr_path.read_text(encoding="utf-8")
    assert "| Status | **Accepted** |" in content
    assert "Adopt Profile B as the ratified hosting profile" in content
    assert "4.32 ms" in content
    assert "$28.50" in content


@pytest.mark.unit
def test_deployment_cost_model_report_structure() -> None:
    """Verifies that deployment-cost-model-t914.md exists and documents benchmarks."""
    report_path = Path("docs/research/deployment-cost-model-t914.md")
    assert report_path.exists(), "Cost model report must exist"

    content = report_path.read_text(encoding="utf-8")
    assert "Profile B vs Profile C" in content
    assert "4.32 ms" in content
    assert "Cold-Start" in content
    assert "Throughput Capacity" in content
    assert "Graduation Triggers" in content
