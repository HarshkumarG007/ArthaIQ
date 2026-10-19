"""Contract tests for model card, sources, and evidence endpoints (PRD FR-19, Task T9.05).

Verifies:
1. GET /v1/models/current returns active champion metadata, snapshot ID, and model ID.
2. GET /v1/models/current returns RFC 9457 Problem Details (HTTP 503) when manager is unready.
3. GET /v1/models/current/card returns full markdown model card with snapshot and model IDs.
4. GET /v1/sources returns approved sources, licences, training eligibility, snapshot and model IDs.
5. GET /v1/evidence/summary returns global evidence base distributions, snapshot and model IDs.
6. GET /v1/evidence/cohort returns cohort sample size, support status, snapshot and model IDs.
7. GET /v1/evidence/cohort validates required parameters and returns RFC 9457 422 on missing fields.
8. GET /v1/evidence/cohort returns RFC 9457 503 when manager is unready.
9. X-Request-ID propagation and security headers across all endpoints.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from compintel.serving.app import create_app
from compintel.serving.core import get_default_serving_manager
from compintel.serving.loader import ServingModelManager


@pytest.fixture(scope="module")
def ready_client() -> TestClient:
    """Test client initialized with default ready champion serving manager."""
    mgr = get_default_serving_manager()
    app = create_app(manager=mgr)
    return TestClient(app)


@pytest.fixture(scope="module")
def unready_client() -> TestClient:
    """Test client initialized with unpromoted (unready) serving manager."""
    unready_mgr = ServingModelManager(initial_bundle=None)
    app = create_app(manager=unready_mgr)
    return TestClient(app)


@pytest.fixture
def mock_supported_client() -> TestClient:
    """Test client initialized with a mock manager returning supported cohort evidence."""
    mgr = MagicMock(spec=ServingModelManager)
    mgr.is_ready = True
    mgr.model_version = "0.1.0"
    mgr.active_bundle.model_version = "0.1.0"
    mgr.active_bundle.metadata.canonical_snapshot_id = "SNAP-1FF34A8E9633"
    mgr.active_bundle.metadata.model_version = "0.1.0"

    mock_evidence = MagicMock()
    mock_evidence.cohort_size = 45
    mock_evidence.median_observation_age_days = 28.0
    mgr.active_bundle._lookup_cohort_evidence.return_value = mock_evidence

    app = create_app(manager=mgr)
    return TestClient(app)


@pytest.mark.contract
class TestModelMetadataContract:
    """Contract verification for GET /v1/models/current and /v1/models/current/card."""

    def test_get_current_model_success(self, ready_client: TestClient) -> None:
        """GET /v1/models/current returns HTTP 200 with complete champion metadata."""
        resp = ready_client.get("/v1/models/current")
        assert resp.status_code == 200
        data = resp.json()

        # Invariant: Responses carry snapshot and model IDs (T9.05 criteria)
        assert "model_version" in data
        assert "canonical_snapshot_id" in data
        assert data["model_version"] == "0.1.0"
        assert data["canonical_snapshot_id"].startswith("SNAP-")

        # Invariant: Champion metadata integrity
        assert data["bundle_name"] == "arthaiq-champion-v0"
        assert "Rung F" in data["rung"]
        assert data["target_variable"] == "guaranteed_cash_annual"
        assert data["target_unit"] == "nominal INR LPA"
        assert data["quantiles"] == [0.1, 0.5, 0.9]
        assert data["model_family"] == "CatBoostQuantileModel"
        assert isinstance(data["metrics_summary"], dict)
        assert "point_mae_lpa" in data["metrics_summary"]
        assert isinstance(data["features"], list)
        assert "role_family" in data["features"]
        assert "years_experience" in data["features"]
        assert isinstance(data["limitations"], list)
        assert len(data["limitations"]) >= 2
        assert isinstance(data["operational_rules"], list)
        assert len(data["operational_rules"]) >= 3

    def test_get_current_model_unready_returns_rfc9457_503(
        self, unready_client: TestClient
    ) -> None:
        """GET /v1/models/current returns RFC 9457 Problem Details when unready."""
        resp = unready_client.get("/v1/models/current")
        assert resp.status_code == 503
        assert resp.headers["content-type"].startswith("application/problem+json")

        problem = resp.json()
        assert problem["status"] == 503
        assert problem["code"] == "MODEL_NOT_READY"
        assert "request_id" in problem
        assert "unready" in problem["detail"].lower() or "not ready" in problem["detail"].lower()

    def test_get_model_card_markdown_success(self, ready_client: TestClient) -> None:
        """GET /v1/models/current/card returns full model card markdown."""
        resp = ready_client.get("/v1/models/current/card")
        assert resp.status_code == 200
        data = resp.json()

        assert "model_version" in data
        assert "canonical_snapshot_id" in data
        assert "card_markdown" in data
        assert data["model_version"] == "0.1.0"
        assert "# " in data["card_markdown"]
        assert "guaranteed_cash_annual" in data["card_markdown"]

    def test_get_model_card_unready_returns_rfc9457_503(self, unready_client: TestClient) -> None:
        """GET /v1/models/current/card returns RFC 9457 503 when unready."""
        resp = unready_client.get("/v1/models/current/card")
        assert resp.status_code == 503
        assert resp.headers["content-type"].startswith("application/problem+json")
        problem = resp.json()
        assert problem["status"] == 503
        assert problem["code"] == "MODEL_NOT_READY"


@pytest.mark.contract
class TestSourcesTransparencyContract:
    """Contract verification for GET /v1/sources."""

    def test_get_sources_success(self, ready_client: TestClient) -> None:
        """GET /v1/sources returns approved inventory with snapshot and model IDs."""
        resp = ready_client.get("/v1/sources")
        assert resp.status_code == 200
        data = resp.json()

        # Invariant: Responses carry snapshot and model IDs (T9.05 criteria)
        assert "data_snapshot_id" in data
        assert "model_version" in data
        assert data["data_snapshot_id"].startswith("SNAP-")
        assert data["model_version"] == "0.1.0"

        # Invariant: Source inventory content and policy
        assert data["total"] >= 4
        assert len(data["sources"]) == data["total"]
        assert data["licence_gate_status"] == "COMPLIANT_R_DA_01"
        assert "Zero scraped job boards" in data["policy"]

        source_ids = {s["source_id"] for s in data["sources"]}
        assert "SRC-INT-VOL-01" in source_ids
        assert "SRC-SUP-CORP-01" in source_ids
        assert "SRC-SUP-MAC-01" in source_ids
        assert "SRC-IND-OFF-01" in source_ids

        # Verify voluntary intake source properties
        vol_src = next(s for s in data["sources"] if s["source_id"] == "SRC-INT-VOL-01")
        assert vol_src["tier"] == "TIER_A"
        assert vol_src["training_eligible"] is True
        assert "DPDPA" in vol_src["licence"] or "Contributor" in vol_src["licence"]

        # Verify corporate disclosures source properties
        corp_src = next(s for s in data["sources"] if s["source_id"] == "SRC-SUP-CORP-01")
        assert corp_src["tier"] == "TIER_A"
        assert corp_src["training_eligible"] is True
        assert "197(12)" in corp_src["licence"]


@pytest.mark.contract
class TestEvidenceTransparencyContract:
    """Contract verification for GET /v1/evidence/summary and /v1/evidence/cohort."""

    def test_get_evidence_summary_success(self, ready_client: TestClient) -> None:
        """GET /v1/evidence/summary returns evidence base metrics and snapshot/model IDs."""
        resp = ready_client.get("/v1/evidence/summary")
        assert resp.status_code == 200
        data = resp.json()

        # Invariant: Responses carry snapshot and model IDs (T9.05 criteria)
        assert "data_snapshot_id" in data
        assert "model_version" in data
        assert data["data_snapshot_id"].startswith("SNAP-")
        assert data["model_version"] == "0.1.0"

        assert data["total_verified_observations"] > 0
        assert "SWE" in data["occupations_covered"]
        assert "DATA" in data["occupations_covered"]
        assert "MLAI" in data["occupations_covered"]
        assert "BENGALURU" in data["locations_covered"]
        assert "HYDERABAD" in data["locations_covered"]

        assert len(data["source_distribution"]) >= 2
        total_share = sum(s["share"] for s in data["source_distribution"])
        assert abs(total_share - 1.0) < 0.01

        assert "GRADE_A" in data["evidence_grades_policy"]
        assert "GRADE_B" in data["evidence_grades_policy"]
        assert "GRADE_C" in data["evidence_grades_policy"]
        assert "n_min" in data["abstention_thresholds"]

    def test_get_cohort_evidence_supported(self, mock_supported_client: TestClient) -> None:
        """GET /v1/evidence/cohort for supported profile returns sample density and support."""
        resp = mock_supported_client.get(
            "/v1/evidence/cohort",
            params={"occupation_id": "SWE", "location_id": "BENGALURU"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Invariant: Responses carry snapshot and model IDs (T9.05 criteria)
        assert "data_snapshot_id" in data
        assert "model_version" in data
        assert data["data_snapshot_id"].startswith("SNAP-")
        assert data["model_version"] == "0.1.0"

        assert data["occupation_id"] == "SWE"
        assert data["location_id"] == "BENGALURU"
        assert data["cohort_n"] >= 10
        assert data["is_supported"] is True
        assert data["support_status"] == "SUPPORTED"
        assert data["evidence_grade"] in ("GRADE_A", "GRADE_B")
        assert len(data["source_mix"]) >= 1
        assert "Not an appraisal" in data["disclaimer"]

    def test_get_cohort_evidence_real_bundle(self, ready_client: TestClient) -> None:
        """GET /v1/evidence/cohort on real champion bundle reflects true cell evidence."""
        resp = ready_client.get(
            "/v1/evidence/cohort",
            params={"occupation_id": "SWE", "location_id": "BENGALURU"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_snapshot_id"].startswith("SNAP-")
        assert data["model_version"] == "0.1.0"
        assert data["occupation_id"] == "SWE"
        assert data["location_id"] == "BENGALURU"
        assert data["cohort_n"] >= 1
        assert "evidence_grade" in data

    def test_get_cohort_evidence_with_seniority(self, ready_client: TestClient) -> None:
        """GET /v1/evidence/cohort accepts seniority parameter."""
        resp = ready_client.get(
            "/v1/evidence/cohort",
            params={"occupation_id": "DATA", "location_id": "HYDERABAD", "seniority": "SR"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["occupation_id"] == "DATA"
        assert data["location_id"] == "HYDERABAD"
        assert data["seniority"] == "SR"
        assert "data_snapshot_id" in data
        assert "model_version" in data

    def test_get_cohort_evidence_thin_unseen_role(self, ready_client: TestClient) -> None:
        """GET /v1/evidence/cohort for unseen profile returns honest thin status."""
        resp = ready_client.get(
            "/v1/evidence/cohort",
            params={"occupation_id": "AGRICULTURE", "location_id": "REMOTE_VILLAGE"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["is_supported"] is False
        assert data["support_status"] == "UNSEEN_CATEGORICAL_PROFILE"
        assert data["evidence_grade"] == "GRADE_C"
        assert data["cohort_n"] == 1
        assert "data_snapshot_id" in data
        assert "model_version" in data

    def test_get_cohort_evidence_missing_params_returns_rfc9457_422(
        self, ready_client: TestClient
    ) -> None:
        """GET /v1/evidence/cohort with missing required parameters returns RFC 9457 422."""
        resp = ready_client.get("/v1/evidence/cohort")
        assert resp.status_code == 422
        assert resp.headers["content-type"].startswith("application/problem+json")
        problem = resp.json()
        assert problem["status"] == 422
        assert problem["code"] == "VALIDATION_ERROR"
        assert "occupation_id" in str(problem) or "location_id" in str(problem)

    def test_get_cohort_evidence_unready_returns_rfc9457_503(
        self, unready_client: TestClient
    ) -> None:
        """GET /v1/evidence/cohort returns RFC 9457 503 when manager is unready."""
        resp = unready_client.get(
            "/v1/evidence/cohort",
            params={"occupation_id": "SWE", "location_id": "BENGALURU"},
        )
        assert resp.status_code == 503
        assert resp.headers["content-type"].startswith("application/problem+json")
        problem = resp.json()
        assert problem["status"] == 503
        assert problem["code"] == "MODEL_NOT_READY"


@pytest.mark.contract
class TestCorrelationAndSecurityHeadersContract:
    """Contract verification for X-Request-ID propagation and security headers."""

    def test_models_and_evidence_correlation_id_echoed(self, ready_client: TestClient) -> None:
        """X-Request-ID header is echoed back on all model and evidence endpoints."""
        endpoints = [
            "/v1/models/current",
            "/v1/models/current/card",
            "/v1/sources",
            "/v1/evidence/summary",
            "/v1/evidence/cohort?occupation_id=SWE&location_id=BENGALURU",
        ]
        test_trace_id = "test-model-evidence-trace-98765"

        for ep in endpoints:
            resp = ready_client.get(ep, headers={"X-Request-ID": test_trace_id})
            assert resp.status_code == 200, f"Failed on endpoint {ep}"
            assert resp.headers.get("x-request-id") == test_trace_id
            assert resp.headers.get("x-content-type-options") == "nosniff"
            assert resp.headers.get("x-frame-options") == "DENY"
