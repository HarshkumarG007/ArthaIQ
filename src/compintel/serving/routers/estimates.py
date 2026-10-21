"""Compensation estimation router (Phase 9, Task T9.02, T9.11a).

Adheres to:
- architecture.md Section 11: POST /v1/estimates returns Estimate | Abstained.
- PRD FR-13 & NFR-07: Telemetry tracking for estimates, abstentions, and confidence interval widths.
- Rule R-ER-02: Expected outcomes (abstention) return HTTP 200 result types, not errors.
- Rule R-UQ-01: Calibrated P10, P50, P90 quantile spans.
- Rule R-MD-13: Current pay compare-only positioning quarantine.
- Rule R-CD-03: Architectural boundary; serving never imports ingestion/quality/eval.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from compintel.monitoring.metrics import get_metrics_registry
from compintel.serving.core import estimate
from compintel.serving.errors import ProblemDetails
from compintel.serving.loader import ServingModelManager
from compintel.serving.types import Abstained, Estimate, EstimateRequest

router = APIRouter(prefix="/v1", tags=["Estimates"])


def _get_manager(request: Request) -> ServingModelManager | None:
    """Safely retrieve ServingModelManager from application state."""
    if hasattr(request.app, "state") and hasattr(request.app.state, "manager"):
        mgr = request.app.state.manager
        if isinstance(mgr, ServingModelManager):
            return mgr
    return None


@router.post(
    "/estimates",
    response_model=Estimate | Abstained,
    status_code=status.HTTP_200_OK,
    summary="Compute compensation estimate or statistically defensible abstention",
    responses={
        200: {
            "description": "Prediction result (either supported Estimate or structured Abstained).",
        },
        422: {
            "model": ProblemDetails,
            "description": "RFC 9457 Problem Details for invalid payload or measure/currency.",
        },
        503: {
            "model": ProblemDetails,
            "description": "RFC 9457 Problem Details when no champion model bundle is loaded.",
        },
    },
)
async def create_estimate(
    payload: EstimateRequest,
    request: Request,
) -> Estimate | Abstained:
    """Serve point-in-time calibrated compensation intelligence.

    Evaluates candidate profile against active champion model bundle with support checks.
    Returns:
    - Estimate: Full P10, P50, P90 quantile span when statistical support criteria pass.
    - Abstained: Structured abstention with reasons and alternative fallback suggestions
      when empirical support is thin or out of bounds (Rule R-UQ-02 / R-ER-04).
    """
    manager = _get_manager(request)
    req_id = getattr(request.state, "request_id", None)

    result = estimate(
        payload,
        request_id=req_id,
        manager=manager,
    )

    metrics = get_metrics_registry()
    if isinstance(result, Abstained):
        metrics.estimates_total.labels(status="abstained").inc()
        role = getattr(payload.profile, "occupation_id", "UNKNOWN")
        loc = getattr(payload.profile, "location_id", "UNKNOWN")
        for reason in result.reasons:
            metrics.abstentions_total.labels(
                reason=reason.code,
                role_family=role,
                location=loc,
            ).inc()
    elif isinstance(result, Estimate):
        grade = result.reliability.grade
        status_label = "guarded" if grade == "GRADE_C" else "supported"
        metrics.estimates_total.labels(status=status_label).inc()
        width = result.estimate.p90 - result.estimate.p10
        if width >= 0:
            metrics.estimate_confidence_width_lpa.labels(evidence_grade=grade).observe(width)

    return result
