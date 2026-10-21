"""OpenAPI schema contract and drift verification tests (Phase 9, Task T9.03).

Verifies:
- architecture.md Section 11: Statutory REST API contract definition.
- PRD Section 7: OpenAPI / Swagger documentation and schema stability.
- Rule R-ER-01 & R-ER-02: RFC 9457 Problem Details and typed Estimate / Abstained responses.
- Schema parity: Live FastAPI OpenAPI spec matches docs/api/openapi.json snapshot without drift.
"""

from __future__ import annotations

import json
from pathlib import Path

from compintel.serving.app import create_app

OPENAPI_SNAPSHOT_PATH = Path("docs/api/openapi.json")


class TestOpenAPIContract:
    """Verifies OpenAPI schema snapshot existence, validity, and drift protection."""

    def test_openapi_snapshot_exists_and_is_valid_json(self) -> None:
        """The committed openapi.json snapshot must exist and be valid JSON."""
        assert OPENAPI_SNAPSHOT_PATH.exists(), (
            f"Missing OpenAPI snapshot at {OPENAPI_SNAPSHOT_PATH}"
        )
        raw_text = OPENAPI_SNAPSHOT_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw_text)
        assert isinstance(parsed, dict)
        assert "openapi" in parsed
        assert parsed["openapi"].startswith("3.")
        assert "info" in parsed
        assert parsed["info"]["title"] == "ArthaIQ Compensation Intelligence API"
        assert parsed["info"]["version"] == "0.1.0"

    def test_live_app_openapi_matches_snapshot(self) -> None:
        """Live application OpenAPI specification must match the committed snapshot bit-for-bit."""
        app = create_app()
        live_spec = app.openapi()
        snapshot_spec = json.loads(OPENAPI_SNAPSHOT_PATH.read_text(encoding="utf-8"))

        assert live_spec == snapshot_spec, (
            "OpenAPI schema drift detected! If API changes were intentional, update "
            "docs/api/openapi.json and review the contract delta."
        )

    def test_openapi_contains_mandatory_paths(self) -> None:
        """Verify all Phase 9 statutory endpoints are present in OpenAPI spec."""
        spec = json.loads(OPENAPI_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        paths = spec.get("paths", {})

        expected_paths = [
            "/healthz",
            "/livez",
            "/readyz",
            "/v1/estimates",
            "/v1/taxonomy/occupations",
            "/v1/taxonomy/locations",
            "/v1/taxonomy/seniorities",
            "/v1/models/current",
            "/v1/models/current/card",
            "/v1/sources",
            "/v1/evidence/summary",
            "/v1/evidence/cohort",
            "/v1/feedback",
        ]
        for path in expected_paths:
            assert path in paths, f"Mandatory endpoint path '{path}' missing from OpenAPI spec."

    def test_post_estimates_operation_contract(self) -> None:
        """Verify POST /v1/estimates operation metadata, response codes, and schemas."""
        spec = json.loads(OPENAPI_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        estimates_op = spec["paths"]["/v1/estimates"]["post"]

        assert estimates_op["summary"] is not None
        assert "tags" in estimates_op
        assert "Estimates" in estimates_op["tags"]

        responses = estimates_op["responses"]
        # Must document 200 (Success), 422 (Unprocessable Content), 503 (Service Unavailable)
        assert "200" in responses
        assert "422" in responses
        assert "503" in responses

    def test_openapi_components_schemas(self) -> None:
        """Verify core domain models are documented in components/schemas."""
        spec = json.loads(OPENAPI_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        schemas = spec.get("components", {}).get("schemas", {})

        expected_schemas = [
            "Estimate",
            "Abstained",
            "ProblemDetails",
            "ProfileRequest",
            "EstimateRequest",
            "QuantileSpan",
            "ReliabilityInfo",
            "EvidenceInfo",
            "ComparisonInfo",
            "AbstentionReasonItem",
            "FallbackItem",
            "OccupationItem",
            "OccupationsResponse",
            "LocationItem",
            "LocationsResponse",
            "SeniorityItem",
            "SenioritiesResponse",
            "CurrentModelResponse",
            "ModelCardResponse",
            "SourceItem",
            "SourcesResponse",
            "EvidenceSummaryResponse",
            "CohortEvidenceResponse",
            "FeedbackSubmissionRequest",
            "FeedbackSubmissionResponse",
        ]
        for schema_name in expected_schemas:
            assert schema_name in schemas, (
                f"Required schema '{schema_name}' missing from components/schemas."
            )
