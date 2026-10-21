"""Unit tests for Phase 10 pilot plan and feedback instrumentation (Task T10.01).

Verifies:
- docs/pilot/pilot-plan.md specification completeness and PRD Section 11 alignment.
- Privacy-preserving PII scrubber regexes (Rule R-CD-06, R-DA-07).
- POST /v1/feedback endpoint behavior, schema validation, and Prometheus metrics.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from compintel.monitoring.metrics import get_metrics_registry
from compintel.serving.app import create_app
from compintel.serving.routers.feedback import scrub_pii

PILOT_PLAN_PATH = Path("docs/pilot/pilot-plan.md")


class TestPilotPlanSpecification:
    """Validate documentation artifact docs/pilot/pilot-plan.md."""

    def test_pilot_plan_document_exists(self) -> None:
        """Pilot plan markdown artifact must exist in docs/pilot/."""
        assert PILOT_PLAN_PATH.exists(), f"Pilot plan not found at {PILOT_PLAN_PATH}"

    def test_pilot_plan_contains_mandatory_sections(self) -> None:
        """Plan must document cohort, 10 success metrics, privacy safeguards, and exit criteria."""
        content = PILOT_PLAN_PATH.read_text(encoding="utf-8")

        # 1. Cohort definitions
        assert "Cohort Stratification" in content
        assert "100" in content and "250" in content
        assert "BLR" in content or "Bengaluru" in content
        assert "HYD" in content or "Hyderabad" in content
        assert "NCR" in content

        # 2. PRD Section 11 pre-registered success metrics
        assert "Pre-Registered Success Metrics (PRD Section 11)" in content
        assert "Comprehension Rate" in content
        assert "90.0" in content
        assert "Task Completion Rate" in content
        assert "95.0" in content
        assert "Abstention" in content
        assert "100.0" in content
        assert "Conformal Coverage" in content
        assert "75.0" in content
        assert "Latency" in content
        assert "50" in content

        # 3. Privacy & PII scrubbing
        assert "R-CD-06" in content
        assert "R-DA-07" in content
        assert "[REDACTED_EMAIL]" in content
        assert "[REDACTED_PHONE]" in content
        assert "[REDACTED_PAN]" in content
        assert "[REDACTED_AADHAAR]" in content

        # 4. Phased rollout & Gate G10 exit criteria
        assert "Phased Pilot Rollout" in content
        assert "Gate G10" in content


class TestPIIScrubber:
    """Test regex sanitization of user feedback text."""

    def test_scrub_pii_with_empty_or_none(self) -> None:
        """Empty string or None should return as-is without raising error."""
        assert scrub_pii(None) is None
        assert scrub_pii("") == ""

    def test_scrub_pii_redacts_email(self) -> None:
        """Email addresses must be replaced with [REDACTED_EMAIL]."""
        raw = "Please email me at dev_candidate+test@example.co.in regarding my band."
        sanitized = scrub_pii(raw)
        assert sanitized is not None
        assert "[REDACTED_EMAIL]" in sanitized
        assert "dev_candidate+test@example.co.in" not in sanitized

    def test_scrub_pii_redacts_indian_mobile(self) -> None:
        """10-digit Indian phone numbers with or without +91 must be redacted."""
        raw1 = "You can call me on +91 9876543210 tomorrow."
        raw2 = "My number is 8765432109 for clarification."
        sanitized1 = scrub_pii(raw1)
        sanitized2 = scrub_pii(raw2)
        assert sanitized1 is not None and "[REDACTED_PHONE]" in sanitized1
        assert "+91 9876543210" not in sanitized1
        assert sanitized2 is not None and "[REDACTED_PHONE]" in sanitized2
        assert "8765432109" not in sanitized2

    def test_scrub_pii_redacts_pan_card(self) -> None:
        """Indian PAN card numbers (5 letters, 4 digits, 1 letter) must be redacted."""
        raw = "My PAN ABCDE1234F was used for TDS verification."
        sanitized = scrub_pii(raw)
        assert sanitized is not None
        assert "[REDACTED_PAN]" in sanitized
        assert "ABCDE1234F" not in sanitized

    def test_scrub_pii_redacts_aadhaar(self) -> None:
        """12-digit Aadhaar sequences (with or without spaces/dashes) must be redacted."""
        raw = "Identity sequence 1234 5678 9012 should not leak."
        sanitized = scrub_pii(raw)
        assert sanitized is not None
        assert "[REDACTED_AADHAAR]" in sanitized
        assert "1234 5678 9012" not in sanitized

    def test_scrub_pii_preserves_clean_text(self) -> None:
        """Domain compensation commentary without PII must remain intact."""
        clean = "The P10-P90 spread for Staff SWE in Bengaluru accurately reflects equity variance."
        assert scrub_pii(clean) == clean


class TestFeedbackEndpoint:
    """Test POST /v1/feedback router behavior and validation."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client for ArthaIQ serving app."""
        app = create_app()
        return TestClient(app)

    def test_post_feedback_success(self, client: TestClient) -> None:
        """Valid feedback submission returns 200 with receipt ID and updates metrics."""
        metrics = get_metrics_registry()
        before_count = metrics.pilot_feedback_total.labels(comprehension="confirmed").value

        payload = {
            "rating_clarity": 5,
            "rating_usefulness": 4,
            "comprehension_confirmed": True,
            "feedback_text": "Call me at +91 9876543210 if salary band changes.",
            "request_id": "REQ-TEST-12345",
            "surface": "estimate_screen",
        }
        response = client.post("/v1/feedback", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["feedback_id"].startswith("FB-")
        assert data["sanitized"] is True
        assert "received_at_utc" in data

        after_count = metrics.pilot_feedback_total.labels(comprehension="confirmed").value
        assert after_count == before_count + 1

    def test_post_feedback_validation_likert_bounds(self, client: TestClient) -> None:
        """Ratings must be between 1 and 5 (ge=1, le=5)."""
        bad_payload = {
            "rating_clarity": 6,  # Invalid: > 5
            "rating_usefulness": 0,  # Invalid: < 1
            "comprehension_confirmed": True,
        }
        response = client.post("/v1/feedback", json=bad_payload)
        assert response.status_code == 422

    def test_post_feedback_validation_text_length(self, client: TestClient) -> None:
        """Feedback text exceeding 500 characters must be rejected with 422."""
        excessive_text = "A" * 501
        payload = {
            "rating_clarity": 4,
            "rating_usefulness": 4,
            "comprehension_confirmed": True,
            "feedback_text": excessive_text,
        }
        response = client.post("/v1/feedback", json=payload)
        assert response.status_code == 422

    def test_post_feedback_minimal_payload(self, client: TestClient) -> None:
        """Minimal valid payload with only required Likert ratings must succeed."""
        payload = {
            "rating_clarity": 3,
            "rating_usefulness": 3,
        }
        response = client.post("/v1/feedback", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["feedback_id"].startswith("FB-")
