"""Pilot feedback and user comprehension instrumentation router (Phase 10, Task T10.01).

Adheres to:
- PRD Section 11 & architecture.md Section 11: Quantitative pilot success metrics & feedback cards.
- Rule R-CD-06 & R-DA-07: Zero PII in logs, telemetry, or structured feedback storage.
- Rule R-UI-05: Non-gamified comprehension verification.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, status

from compintel.logging import get_logger
from compintel.monitoring.metrics import get_metrics_registry
from compintel.serving.types import (
    FeedbackSubmissionRequest,
    FeedbackSubmissionResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["Pilot Feedback"])

# -----------------------------------------------------------------------------
# Automated PII Redaction Regexes (Rule R-CD-06, R-DA-07)
# -----------------------------------------------------------------------------
_EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    re.IGNORECASE,
)
_PHONE_REGEX = re.compile(
    r"(?:\+?91[\-\s]?)?[6-9]\d{9}\b",
)
_PAN_REGEX = re.compile(
    r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b",
)
_AADHAAR_REGEX = re.compile(
    r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
)


def scrub_pii(text: str | None) -> str | None:
    """Scrub potential personally identifiable information (PII) from user feedback text.

    Replaces:
    - Emails with [REDACTED_EMAIL]
    - Indian Mobile numbers with [REDACTED_PHONE]
    - PAN identifiers with [REDACTED_PAN]
    - Aadhaar sequences with [REDACTED_AADHAAR]
    """
    if not text:
        return text

    sanitized = _EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
    sanitized = _PAN_REGEX.sub("[REDACTED_PAN]", sanitized)
    sanitized = _AADHAAR_REGEX.sub("[REDACTED_AADHAAR]", sanitized)
    sanitized = _PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized)
    return sanitized


@router.post(
    "/feedback",
    response_model=FeedbackSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit anonymous pilot feedback and comprehension validation",
    responses={
        200: {
            "description": "Feedback successfully sanitized, instrumented, and acknowledged.",
        },
        422: {
            "description": "Validation error (Likert bounds 1-5 violated, comment > 500 chars).",
        },
    },
)
async def submit_feedback(payload: FeedbackSubmissionRequest) -> FeedbackSubmissionResponse:
    """Ingest anonymous user feedback from pilot cohort sessions.

    Enforces:
    - Automated server-side PII scrubbing on qualitative feedback comments.
    - Zero raw feedback text emitted to logs (Rule R-CD-06).
    - Prometheus telemetry tracking on comprehension confirmations.
    """
    feedback_id = f"FB-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:8]}"
    sanitized_text = scrub_pii(payload.feedback_text) if payload.feedback_text else None

    # Track operational telemetry
    metrics = get_metrics_registry()
    comprehension_label = "confirmed" if payload.comprehension_confirmed else "unconfirmed"
    metrics.pilot_feedback_total.labels(comprehension=comprehension_label).inc()

    # Emit structured audit event (strictly zero free-form PII text logged)
    logger.info(
        "pilot_feedback_received",
        feedback_id=feedback_id,
        rating_clarity=payload.rating_clarity,
        rating_usefulness=payload.rating_usefulness,
        comprehension_confirmed=payload.comprehension_confirmed,
        has_text=bool(sanitized_text),
        text_length=len(sanitized_text) if sanitized_text else 0,
        surface=payload.surface,
        correlation_id=payload.request_id,
    )

    return FeedbackSubmissionResponse(
        status="received",
        feedback_id=feedback_id,
        sanitized=True,
        received_at_utc=datetime.now(UTC).isoformat(),
    )
