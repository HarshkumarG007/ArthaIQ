"""Unit tests for Cloud CI/CD Pipeline & Registry Automation (Phase 29, Task T29.04).

Validates:
1. Machine-readable audit report integrity (CICD-PIPELINE-VERIFY-01).
2. GitHub Actions workflow triggers, permissions, and job topology.
3. Multi-architecture QEMU/Buildx and Aqua Security Trivy scan configurations.
4. Hadolint Dockerfile linting integration.
5. Dockerfile security postures (non-root execution per OWASP ASVS 14.2.1).
6. Compose staging specification validation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = REPO_ROOT / "experiments" / "results" / "cicd_pipeline_verification_v1.json"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "docker-publish.yml"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DOCKERFILE_API = REPO_ROOT / "infra" / "docker" / "Dockerfile.api"
DOCKERFILE_WEB = REPO_ROOT / "infra" / "docker" / "Dockerfile.web"


@pytest.mark.unit
class TestCICDPipelineWorkflow:
    """Validate GitHub Actions Docker publish and security scan workflow."""

    def test_report_exists_and_status_pass(self) -> None:
        """Audit report exists, status is PASS, and failed_checks is 0."""
        assert REPORT_PATH.exists(), f"Report file {REPORT_PATH} must exist"
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

        meta = data.get("metadata", {})
        assert meta.get("document_id") == "CICD-PIPELINE-VERIFY-01"
        assert meta.get("status") == "PASS"
        assert meta.get("failed_checks") == 0
        assert meta.get("passed_checks") >= 7

    def test_workflow_triggers_and_least_privilege(self) -> None:
        """Workflow triggers on push to main, v* tags, and specifies least-privilege permissions."""
        assert WORKFLOW_PATH.exists()
        raw = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        triggers = raw.get("on") or raw.get(True) or {}

        assert "main" in triggers.get("push", {}).get("branches", [])
        assert any("v*" in tag for tag in triggers.get("push", {}).get("tags", []))
        assert "pull_request" in triggers
        assert "workflow_dispatch" in triggers

        perms = raw.get("permissions", {})
        assert perms.get("contents") == "read"
        assert perms.get("packages") == "write"
        assert perms.get("security-events") == "write"

    def test_hadolint_and_compose_validation_jobs(self) -> None:
        """Workflow defines hadolint linting and compose validation jobs."""
        raw = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        jobs = raw.get("jobs", {})

        assert "hadolint" in jobs
        hl_steps = jobs["hadolint"].get("steps", [])
        assert any("hadolint/hadolint-action" in str(s.get("uses", "")) for s in hl_steps)

        assert "validate-compose" in jobs
        vc_steps = jobs["validate-compose"].get("steps", [])
        assert any("docker compose" in str(s.get("run", "")) for s in vc_steps)

    def test_multiarch_buildx_and_trivy_scanning(self) -> None:
        """API and Web build jobs configure multi-arch QEMU, Buildx, and Trivy scanning."""
        raw = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        jobs = raw.get("jobs", {})

        for svc in ["api", "web"]:
            job_key = f"build-{svc}"
            assert job_key in jobs
            steps = jobs[job_key].get("steps", [])

            # QEMU multi-arch
            qemu_step = next(
                (s for s in steps if "docker/setup-qemu-action" in str(s.get("uses", ""))), None
            )
            assert qemu_step is not None
            assert "linux/amd64,linux/arm64" in qemu_step.get("with", {}).get("platforms", "")

            # Buildx
            assert any("docker/setup-buildx-action" in str(s.get("uses", "")) for s in steps)

            # Trivy scanner
            trivy_step = next(
                (s for s in steps if "aquasecurity/trivy-action" in str(s.get("uses", ""))), None
            )
            assert trivy_step is not None
            assert trivy_step.get("with", {}).get("format") == "sarif"
            assert "CRITICAL" in trivy_step.get("with", {}).get("severity", "")
            assert trivy_step.get("with", {}).get("ignore-unfixed") is True

            # SARIF upload
            assert any("codeql-action/upload-sarif" in str(s.get("uses", "")) for s in steps)

    def test_dockerfile_security_posture(self) -> None:
        """Dockerfiles enforce multi-stage builds and non-root execution (ASVS 14.2.1)."""
        api_txt = DOCKERFILE_API.read_text(encoding="utf-8")
        assert "FROM python:3.12-slim-bookworm AS builder" in api_txt
        assert "FROM python:3.12-slim-bookworm AS runtime" in api_txt
        assert "USER compintel" in api_txt
        assert "HEALTHCHECK" in api_txt

        web_txt = DOCKERFILE_WEB.read_text(encoding="utf-8")
        assert "FROM node:22-alpine AS builder" in web_txt
        assert "FROM nginx:1.27-alpine AS runtime" in web_txt
        assert "HEALTHCHECK" in web_txt

    def test_ci_build_artifact_passing(self) -> None:
        """ci.yml coordinates web distribution bundle upload from frontend to tests."""
        ci_txt = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "name: web-dist" in ci_txt
        assert "actions/upload-artifact" in ci_txt
        assert "actions/download-artifact" in ci_txt
        assert "needs: [static, contracts, frontend]" in ci_txt
