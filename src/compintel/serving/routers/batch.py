"""Batch compensation estimation router (Phase 23, Task T23.02, T23.03, ENG-17).

Provides enterprise-grade bulk compensation estimation with:
- Synchronous batch endpoint (POST /v1/estimates/batch) with structured JSON results.
- Streaming NDJSON endpoint (POST /v1/estimates/batch/stream) with memory bounds (heap <= 128MB).
- Finite-sample split conformal prediction intervals ([P10, P50, P90]) adhering to Rule R-UQ-01.
- Honest, structured abstentions without HTTP 500 exceptions adhering to Rule R-UQ-02 and R-ER-02.
- CPA 2019 statutory disclaimers adhering to Rule R-CR-01.
- Strict architectural boundary: serving never imports ingestion/quality/eval (Rule R-CD-03).
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

from compintel.errors import ModelArtifactError, ValidationError
from compintel.monitoring.metrics import get_metrics_registry
from compintel.serving.batch_pipeline import (
    STATUTORY_DISCLAIMER,
    BatchInferencePipeline,
)
from compintel.serving.errors import ProblemDetails
from compintel.serving.loader import ServingModelManager
from compintel.serving.types import (
    BatchEstimateItem,
    BatchEstimateRequest,
    BatchEstimateResponse,
    BatchEstimateSummary,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

router = APIRouter(prefix="/v1/estimates", tags=["Estimates", "Batch"])


def _get_manager(request: Request) -> ServingModelManager | None:
    """Safely retrieve ServingModelManager from application state."""
    if hasattr(request.app, "state") and hasattr(request.app.state, "manager"):
        mgr = request.app.state.manager
        if isinstance(mgr, ServingModelManager):
            return mgr
    return None


def _validate_batch_request(payload: BatchEstimateRequest) -> None:
    """Validate measure, currency, and payload constraints."""
    if payload.measure != "guaranteed_cash_annual":
        raise ValidationError(
            f"Unsupported compensation measure '{payload.measure}'. "
            "Batch estimation strictly prices 'guaranteed_cash_annual' (PT1)."
        )
    if payload.currency != "INR":
        raise ValidationError(
            f"Unsupported currency '{payload.currency}'. "
            "ArthaIQ batch estimation strictly prices in Indian Rupees ('INR')."
        )


def _prepare_profile_records(payload: BatchEstimateRequest) -> list[dict[str, Any]]:
    """Convert Pydantic profile items to raw record dictionaries."""
    records: list[dict[str, Any]] = []
    for item in payload.items:
        rec = {
            "profile_id": item.profile_id,
            "occupation_id": item.occupation_id,
            "location_id": item.location_id,
            "experience": {
                "total_years": item.experience.total_years,
                "level_id": item.experience.level_id,
            },
            "extras": item.extras,
        }
        records.append(rec)
    return records


@router.post(
    "/batch",
    response_model=BatchEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute high-throughput batch compensation estimates",
    responses={
        200: {
            "description": (
                "Batch prediction results with summary telemetry, "
                "split conformal prediction intervals, and structured abstentions."
            ),
        },
        422: {
            "model": ProblemDetails,
            "description": (
                "RFC 9457 Problem Details for invalid payload or unsupported parameters."
            ),
        },
        503: {
            "model": ProblemDetails,
            "description": "RFC 9457 Problem Details when no champion model bundle is loaded.",
        },
    },
)
async def create_batch_estimates(
    payload: BatchEstimateRequest,
    request: Request,
) -> BatchEstimateResponse:
    """Serve high-throughput batch compensation estimates.

    Accepts an array of up to 500 candidate profiles and returns itemized
    conformal prediction intervals ([P10, P50, P90]) or honest abstentions.
    """
    _validate_batch_request(payload)

    manager = _get_manager(request)
    if manager is None or not manager.is_ready:
        raise ModelArtifactError("No champion model bundle is loaded; batch serving unavailable.")

    pipeline = BatchInferencePipeline(manager=manager)
    records = _prepare_profile_records(payload)

    t0 = time.perf_counter()
    results = pipeline.predict_batch(records, as_of=payload.as_of)
    t1 = time.perf_counter()

    duration = t1 - t0
    total = len(results)
    throughput = round(total / max(duration, 1e-6), 1)

    items: list[BatchEstimateItem] = [BatchEstimateItem(**r.to_dict()) for r in results]
    successful = sum(1 for it in items if not it.is_abstained)
    abstained = total - successful

    # Telemetry registration
    metrics = get_metrics_registry()
    if successful > 0:
        metrics.estimates_total.labels(status="supported").inc(successful)
    if abstained > 0:
        metrics.estimates_total.labels(status="abstained").inc(abstained)

    as_of_date = payload.as_of or datetime.now(UTC).strftime("%Y-%m-%d")

    summary = BatchEstimateSummary(
        total_records=total,
        successful_estimates=successful,
        abstained_count=abstained,
        duration_seconds=round(duration, 4),
        throughput_predictions_per_sec=throughput,
        model_version=pipeline.model_version,
        nominal_coverage=payload.nominal_coverage,
        as_of_date=as_of_date,
        disclaimer=STATUTORY_DISCLAIMER,
    )

    return BatchEstimateResponse(
        summary=summary,
        items=items,
    )


@router.post(
    "/batch/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream batch compensation estimates as newline-delimited JSON (NDJSON)",
    responses={
        200: {
            "description": (
                "Newline-delimited stream of JSON prediction objects (application/x-ndjson)."
            ),
            "content": {"application/x-ndjson": {}},
        },
        422: {
            "model": ProblemDetails,
            "description": (
                "RFC 9457 Problem Details for invalid payload or unsupported parameters."
            ),
        },
        503: {
            "model": ProblemDetails,
            "description": "RFC 9457 Problem Details when no champion model bundle is loaded.",
        },
    },
)
async def stream_batch_estimates(
    payload: BatchEstimateRequest,
    request: Request,
) -> StreamingResponse:
    """Stream batch compensation estimates item-by-item in NDJSON format.

    Guarantees memory-safe streaming (heap <= 128MB) for bulk integrations.
    """
    _validate_batch_request(payload)

    manager = _get_manager(request)
    if manager is None or not manager.is_ready:
        raise ModelArtifactError("No champion model bundle is loaded; batch streaming unavailable.")

    pipeline = BatchInferencePipeline(manager=manager)
    records = _prepare_profile_records(payload)

    def ndjson_generator() -> Iterator[str]:
        # Process in chunks and yield line by line
        for chunk in pipeline.predict_streaming(records, chunk_size=50):
            for item in chunk:
                yield json.dumps(item.to_dict()) + "\n"

    return StreamingResponse(
        ndjson_generator(),
        media_type="application/x-ndjson",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        },
    )
