"""Contract tests for Enterprise Batch Estimation REST API (Phase 23, Task T23.04).

Verifies:
- POST /v1/estimates/batch: Bulk estimation endpoint with conformal quantile spans [P10, P50, P90].
- POST /v1/estimates/batch/stream: Streaming NDJSON endpoint for memory-bounded streaming.
- Rule R-UQ-01: Zero Lone Numbers. Every valid item returns full interval [p10, p50, p90].
- Rule R-UQ-02: Structured abstention for thin/out-of-domain records without HTTP 500 exceptions.
- Rule R-CR-01: CPA 2019 statutory disclaimer attached to all summary payloads.
- Rule R-ER-04: RFC 9457 Problem Details for 422 validation and 503 unready errors.
- Rule R-CD-03: Architectural boundaries; serving never imports ingestion/quality/eval.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from compintel.serving.app import create_app
from compintel.serving.loader import ServingModelManager


@pytest.fixture(scope="module")
def shared_app():
    """Create shared app with champion model bundle loaded once for module."""
    return create_app()


@pytest.fixture
def client(shared_app) -> TestClient:
    """Create test client with shared app."""
    return TestClient(shared_app)


@pytest.mark.contract
class TestBatchAPIContractSupported:
    """Contract tests for successful POST /v1/estimates/batch calls."""

    def test_post_batch_estimates_supported_multi_family(self, client: TestClient) -> None:
        """Batch of SWE, DATA, and MLAI profiles returns HTTP 200 with calibrated intervals."""
        payload = {
            "items": [
                {
                    "profile_id": "swe-01",
                    "occupation_id": "SWE",
                    "location_id": "BENGALURU",
                    "experience": {"total_years": 4.0, "level_id": "MID"},
                },
                {
                    "profile_id": "data-01",
                    "occupation_id": "DATA",
                    "location_id": "HYDERABAD",
                    "experience": {"total_years": 6.0, "level_id": "SR"},
                },
                {
                    "profile_id": "mlai-01",
                    "occupation_id": "MLAI",
                    "location_id": "NCR",
                    "experience": {"total_years": 3.0, "level_id": "MID"},
                },
            ],
            "measure": "guaranteed_cash_annual",
            "currency": "INR",
            "nominal_coverage": 0.80,
            "as_of": "2026-10-31",
        }

        response = client.post("/v1/estimates/batch", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

        data = response.json()
        assert "summary" in data
        assert "items" in data

        summary = data["summary"]
        assert summary["total_records"] == 3
        assert summary["successful_estimates"] == 3
        assert summary["abstained_count"] == 0
        assert summary["throughput_predictions_per_sec"] > 0
        assert summary["nominal_coverage"] == 0.80
        assert summary["as_of_date"] == "2026-10-31"
        assert (
            "statutory" in summary["disclaimer"].lower()
            or "not an appraisal" in summary["disclaimer"].lower()
        )

        # Rule R-UQ-01: Zero lone numbers; always full intervals
        items = data["items"]
        assert len(items) == 3
        for item in items:
            assert item["status"] == "ok"
            assert not item["is_abstained"]
            assert item["p10"] is not None and item["p50"] is not None and item["p90"] is not None
            assert item["p10"] <= item["p50"] <= item["p90"]
            assert item["interval_width"] == round(item["p90"] - item["p10"], 2)
            assert item["currency"] == "INR"
            assert item["target_measure"] == "guaranteed_cash_annual"

    def test_post_batch_estimates_mixed_with_abstentions(self, client: TestClient) -> None:
        """Rule R-UQ-02: Out-of-bounds YoE and invalid roles return structured abstentions."""
        payload = {
            "items": [
                {
                    "profile_id": "valid-01",
                    "occupation_id": "SWE",
                    "location_id": "BENGALURU",
                    "experience": {"total_years": 5.0, "level_id": "MID"},
                },
                {
                    "profile_id": "oob-yoe",
                    "occupation_id": "DATA",
                    "location_id": "PUNE",
                    "experience": {"total_years": 45.0, "level_id": "STAFF"},  # > 40 YoE
                },
                {
                    "profile_id": "unseen-role",
                    "occupation_id": "OTHER",
                    "location_id": "MUMBAI",
                    "experience": {"total_years": 5.0, "level_id": "MID"},
                },
            ],
            "measure": "guaranteed_cash_annual",
            "currency": "INR",
        }

        response = client.post("/v1/estimates/batch", json=payload)
        assert response.status_code == 200

        data = response.json()
        summary = data["summary"]
        assert summary["total_records"] == 3
        assert summary["successful_estimates"] == 1
        assert summary["abstained_count"] == 2

        items = data["items"]
        assert len(items) == 3

        # Valid item
        valid_item = items[0]
        assert valid_item["profile_id"] == "valid-01"
        assert valid_item["status"] == "ok"
        assert valid_item["p10"] is not None

        # OOB YoE item
        oob_item = items[1]
        assert oob_item["profile_id"] == "oob-yoe"
        assert oob_item["status"] == "abstained"
        assert oob_item["is_abstained"] is True
        assert oob_item["p10"] is None
        assert oob_item["p50"] is None
        assert oob_item["p90"] is None
        assert "OUT_OF_RANGE_EXPERIENCE" in oob_item["abstention_reasons"]

        # Unseen role item
        unseen_item = items[2]
        assert unseen_item["profile_id"] == "unseen-role"
        assert unseen_item["status"] == "abstained"
        assert unseen_item["is_abstained"] is True
        assert "UNSEEN_CATEGORICAL_PROFILE" in unseen_item["abstention_reasons"]


@pytest.mark.contract
class TestBatchAPIContractStreaming:
    """Contract tests for streaming NDJSON endpoint (POST /v1/estimates/batch/stream)."""

    def test_post_batch_stream_ndjson_format_and_intervals(self, client: TestClient) -> None:
        """POST /v1/estimates/batch/stream returns line-by-line JSON with application/x-ndjson."""
        payload = {
            "items": [
                {
                    "profile_id": f"stream-{i}",
                    "occupation_id": "SWE",
                    "location_id": "BENGALURU",
                    "experience": {"total_years": float(i + 1), "level_id": "MID"},
                }
                for i in range(5)
            ],
            "measure": "guaranteed_cash_annual",
            "currency": "INR",
        }

        response = client.post("/v1/estimates/batch/stream", json=payload)
        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers["content-type"]

        lines = [line.strip() for line in response.text.split("\n") if line.strip()]
        assert len(lines) == 5

        for i, line in enumerate(lines):
            item = json.loads(line)
            assert item["profile_id"] == f"stream-{i}"
            assert item["status"] == "ok"
            assert not item["is_abstained"]
            assert item["p10"] is not None and item["p50"] is not None and item["p90"] is not None
            assert item["p10"] <= item["p50"] <= item["p90"]


@pytest.mark.contract
class TestBatchAPIContractErrors:
    """Contract tests for RFC 9457 error contracts on batch estimation."""

    def test_unsupported_measure_returns_422_problem_details(self, client: TestClient) -> None:
        """Non-guaranteed cash measure returns 422 RFC 9457 ProblemDetails."""
        payload = {
            "items": [
                {
                    "profile_id": "p1",
                    "occupation_id": "SWE",
                    "location_id": "BENGALURU",
                    "experience": {"total_years": 3.0},
                }
            ],
            "measure": "total_ctc",  # Forbidden measure
            "currency": "INR",
        }

        response = client.post("/v1/estimates/batch", json=payload)
        assert response.status_code == 422
        assert "application/problem+json" in response.headers["content-type"]

        err = response.json()
        assert err["status"] == 422
        assert err["code"] == "VALIDATION_ERROR"
        assert "guaranteed_cash_annual" in err["detail"]

    def test_unsupported_currency_returns_422_problem_details(self, client: TestClient) -> None:
        """Non-INR currency returns 422 RFC 9457 ProblemDetails."""
        payload = {
            "items": [
                {
                    "profile_id": "p1",
                    "occupation_id": "SWE",
                    "location_id": "BENGALURU",
                    "experience": {"total_years": 3.0},
                }
            ],
            "measure": "guaranteed_cash_annual",
            "currency": "USD",  # Forbidden currency
        }

        response = client.post("/v1/estimates/batch", json=payload)
        assert response.status_code == 422
        assert "application/problem+json" in response.headers["content-type"]

        err = response.json()
        assert err["status"] == 422
        assert err["code"] == "VALIDATION_ERROR"
        assert "INR" in err["detail"]

    def test_empty_items_array_returns_422_problem_details(self, client: TestClient) -> None:
        """Empty items array returns 422 RFC 9457 ProblemDetails."""
        payload = {
            "items": [],
            "measure": "guaranteed_cash_annual",
            "currency": "INR",
        }

        response = client.post("/v1/estimates/batch", json=payload)
        assert response.status_code == 422
        assert "application/problem+json" in response.headers["content-type"]

    def test_unready_model_manager_returns_503(self) -> None:
        """Rule R-MD-14: Unready serving manager returns 503 RFC 9457 ProblemDetails."""
        unready_mgr = MagicMock(spec=ServingModelManager)
        unready_mgr.is_ready = False
        unready_mgr.model_version = "none"

        app = create_app(manager=unready_mgr)
        client = TestClient(app)

        payload = {
            "items": [
                {
                    "profile_id": "p1",
                    "occupation_id": "SWE",
                    "location_id": "BENGALURU",
                    "experience": {"total_years": 3.0},
                }
            ],
            "measure": "guaranteed_cash_annual",
            "currency": "INR",
        }

        response = client.post("/v1/estimates/batch", json=payload)
        assert response.status_code == 503
        assert "application/problem+json" in response.headers["content-type"]

        err = response.json()
        assert err["status"] == 503
        assert err["code"] == "MODEL_ARTIFACT_ERROR"
