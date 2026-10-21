"""CompIntel Preview Deployment & Orchestration Harness (Phase 9, Task T9.14a).

Provides unified CLI commands to build, start, stop, and verify the health of the
local/preview Docker Compose stack (PostgreSQL + FastAPI serving + React Nginx SPA).

Usage:
    uv run python scripts/deploy_preview.py up [--build] [--wait] [--timeout SECONDS]
    uv run python scripts/deploy_preview.py down [--volumes]
    uv run python scripts/deploy_preview.py health [--timeout SECONDS]
    uv run python scripts/deploy_preview.py logs [--service SERVICE_NAME]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_COMPOSE_PATH = Path("infra/docker/docker-compose.yml")
DEFAULT_API_URL = os.environ.get("PREVIEW_API_URL", "http://localhost:8000")
DEFAULT_WEB_URL = os.environ.get("PREVIEW_WEB_URL", "http://localhost:8080")


@dataclass
class ServiceHealth:
    service: str
    target: str
    healthy: bool
    status_code: int | None
    message: str


def check_docker_available(dry_run: bool = False) -> bool:
    """Verifies that Docker CLI and Docker Compose are installed and operational."""
    if dry_run:
        return True

    docker_bin = shutil.which("docker")
    if not docker_bin:
        print(
            "[ERROR] Docker executable not found in PATH. Please install Docker.", file=sys.stderr
        )
        return False

    try:
        res = subprocess.run(
            [docker_bin, "compose", "version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if res.returncode != 0:
            print(f"[ERROR] 'docker compose' check failed: {res.stderr.strip()}", file=sys.stderr)
            return False
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"[ERROR] Failed to execute docker compose: {exc}", file=sys.stderr)
        return False

    return True


def run_compose_command(
    args: Sequence[str],
    compose_path: Path = DEFAULT_COMPOSE_PATH,
    dry_run: bool = False,
) -> int:
    """Runs a docker compose command with the specified compose file."""
    docker_bin = shutil.which("docker") or "docker"
    cmd = [docker_bin, "compose", "-f", str(compose_path), *args]

    print(f"[COMPOSE] Running: {' '.join(cmd)}")
    if dry_run:
        print("[DRY-RUN] Command execution skipped.")
        return 0

    try:
        res = subprocess.run(cmd, check=False)
        return res.returncode
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"[ERROR] Failed to run compose command: {exc}", file=sys.stderr)
        return 1


def check_endpoint_health(url: str, timeout_sec: float = 3.0) -> tuple[bool, int | None, str]:
    """Probes an HTTP health endpoint using standard library urllib."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CompIntel-DeployPreviewHarness/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            status = response.getcode()
            if 200 <= status < 400:
                return True, status, "Healthy"
            return False, status, f"Unexpected HTTP status {status}"
    except urllib.error.HTTPError as exc:
        return False, exc.code, f"HTTP Error {exc.code}"
    except urllib.error.URLError as exc:
        return False, None, f"Connection failed: {exc.reason}"
    except TimeoutError:
        return False, None, "Request timed out"
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


def verify_stack_health(
    api_base_url: str = DEFAULT_API_URL,
    web_base_url: str = DEFAULT_WEB_URL,
    timeout_sec: float = 30.0,
    poll_interval_sec: float = 2.0,
    dry_run: bool = False,
) -> list[ServiceHealth]:
    """Polls stack health endpoints until all are healthy or timeout expires."""
    if dry_run:
        return [
            ServiceHealth("db", "PostgreSQL pg_isready", True, None, "Simulated healthy (dry-run)"),
            ServiceHealth("api", f"{api_base_url}/livez", True, 200, "Simulated healthy (dry-run)"),
            ServiceHealth(
                "api", f"{api_base_url}/readyz", True, 200, "Simulated healthy (dry-run)"
            ),
            ServiceHealth("web", f"{web_base_url}/", True, 200, "Simulated healthy (dry-run)"),
        ]

    endpoints = [
        ("api-livez", f"{api_base_url.rstrip('/')}/livez"),
        ("api-readyz", f"{api_base_url.rstrip('/')}/readyz"),
        ("web-root", f"{web_base_url.rstrip('/')}/"),
    ]

    print(f"[HEALTH] Verifying preview stack health at API={api_base_url}, Web={web_base_url}...")
    start_time = time.monotonic()
    results: dict[str, ServiceHealth] = {}

    while time.monotonic() - start_time < timeout_sec:
        all_passed = True
        for name, url in endpoints:
            is_healthy, status_code, msg = check_endpoint_health(url)
            results[name] = ServiceHealth(
                service=name,
                target=url,
                healthy=is_healthy,
                status_code=status_code,
                message=msg,
            )
            if not is_healthy:
                all_passed = False

        if all_passed:
            print("[HEALTH] All preview endpoints responded successfully!")
            return list(results.values())

        time.sleep(poll_interval_sec)

    print("[HEALTH] Timed out waiting for stack endpoints to become healthy.", file=sys.stderr)
    return list(results.values())


def cmd_up(args: argparse.Namespace) -> int:
    """Starts the Docker Compose preview stack."""
    if not check_docker_available(dry_run=args.dry_run):
        return 1

    compose_args = ["up", "-d"]
    if args.build:
        compose_args.append("--build")

    exit_code = run_compose_command(
        compose_args,
        compose_path=Path(args.compose_file),
        dry_run=args.dry_run,
    )
    if exit_code != 0:
        return exit_code

    if args.wait:
        print("[UP] Waiting for preview stack endpoints to be healthy...")
        health_results = verify_stack_health(
            api_base_url=args.api_url,
            web_base_url=args.web_url,
            timeout_sec=args.timeout,
            dry_run=args.dry_run,
        )
        all_healthy = all(r.healthy for r in health_results)
        print_health_summary(health_results)
        return 0 if all_healthy else 1

    return 0


def cmd_down(args: argparse.Namespace) -> int:
    """Tears down the Docker Compose preview stack."""
    if not check_docker_available(dry_run=args.dry_run):
        return 1

    compose_args = ["down"]
    if args.volumes:
        compose_args.append("-v")

    return run_compose_command(
        compose_args,
        compose_path=Path(args.compose_file),
        dry_run=args.dry_run,
    )


def cmd_health(args: argparse.Namespace) -> int:
    """Checks the health of the running preview stack."""
    health_results = verify_stack_health(
        api_base_url=args.api_url,
        web_base_url=args.web_url,
        timeout_sec=args.timeout,
        dry_run=args.dry_run,
    )
    print_health_summary(health_results)
    all_healthy = all(r.healthy for r in health_results)
    return 0 if all_healthy else 1


def cmd_logs(args: argparse.Namespace) -> int:
    """Fetches container logs for preview services."""
    if not check_docker_available(dry_run=args.dry_run):
        return 1

    compose_args = ["logs"]
    if args.follow:
        compose_args.append("-f")
    if args.tail:
        compose_args.extend(["--tail", str(args.tail)])
    if args.service:
        compose_args.append(args.service)

    return run_compose_command(
        compose_args,
        compose_path=Path(args.compose_file),
        dry_run=args.dry_run,
    )


def print_health_summary(results: Sequence[ServiceHealth]) -> None:
    """Prints a formatted health table summary."""
    print("\n" + "=" * 70)
    print("COMPINTEL PREVIEW STACK HEALTH STATUS")
    print("=" * 70)
    for res in results:
        status_tag = "[PASS]" if res.healthy else "[FAIL]"
        code_tag = f"HTTP {res.status_code}" if res.status_code else "N/A"
        print(f" {status_tag} {res.service:<15} {res.target:<35} {code_tag:<10} ({res.message})")
    print("=" * 70 + "\n")


def build_parser() -> argparse.ArgumentParser:
    """Constructs command line argument parser for deploy harness."""
    parser = argparse.ArgumentParser(
        description="CompIntel Preview Deployment & Orchestration Harness",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--compose-file",
        default=str(DEFAULT_COMPOSE_PATH),
        help="Path to docker-compose.yml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate actions without invoking docker daemon",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Subcommand: up
    parser_up = subparsers.add_parser("up", help="Start the preview stack")
    parser_up.add_argument(
        "--build", action="store_true", default=True, help="Build container images"
    )
    parser_up.add_argument(
        "--no-build", action="store_false", dest="build", help="Skip container build"
    )
    parser_up.add_argument(
        "--wait", action="store_true", default=True, help="Wait for services to be healthy"
    )
    parser_up.add_argument(
        "--no-wait", action="store_false", dest="wait", help="Do not wait for health"
    )
    parser_up.add_argument(
        "--timeout", type=float, default=60.0, help="Healthcheck timeout in seconds"
    )
    parser_up.add_argument("--api-url", default=DEFAULT_API_URL, help="Preview API base URL")
    parser_up.add_argument("--web-url", default=DEFAULT_WEB_URL, help="Preview Web base URL")
    parser_up.set_defaults(func=cmd_up)

    # Subcommand: down
    parser_down = subparsers.add_parser("down", help="Stop and remove the preview stack")
    parser_down.add_argument("-v", "--volumes", action="store_true", help="Remove named volumes")
    parser_down.set_defaults(func=cmd_down)

    # Subcommand: health
    parser_health = subparsers.add_parser("health", help="Check preview stack health")
    parser_health.add_argument(
        "--timeout", type=float, default=5.0, help="Probe timeout in seconds"
    )
    parser_health.add_argument("--api-url", default=DEFAULT_API_URL, help="Preview API base URL")
    parser_health.add_argument("--web-url", default=DEFAULT_WEB_URL, help="Preview Web base URL")
    parser_health.set_defaults(func=cmd_health)

    # Subcommand: logs
    parser_logs = subparsers.add_parser("logs", help="View preview stack logs")
    parser_logs.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    parser_logs.add_argument(
        "--tail", type=int, default=100, help="Number of lines to show from each container"
    )
    parser_logs.add_argument(
        "service", nargs="?", default=None, help="Optional service name (db, api, web)"
    )
    parser_logs.set_defaults(func=cmd_logs)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
