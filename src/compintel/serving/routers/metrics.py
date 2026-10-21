"""Prometheus metrics exposition router (Phase 9, Task T9.11a).

Adheres to:
- PRD FR-13 & NFR-07: Internal monitoring, Prometheus metrics exposition.
- Rule R-CD-06 / R-DA-07: Metrics never expose PII or unaggregated individual values.
- Rule R-CD-03: Serving boundary; imports monitoring telemetry engine.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from compintel.monitoring.metrics import get_metrics_registry

router = APIRouter(tags=["Monitoring"])

PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Scrape Prometheus operational metrics",
    response_class=Response,
    responses={
        200: {
            "content": {PROMETHEUS_MEDIA_TYPE: {}},
            "description": "Standard Prometheus text format operational telemetry.",
        }
    },
)
def get_metrics() -> Response:
    """Expose application metrics in standard Prometheus text exposition format (v0.0.4).

    Returns cumulative HTTP traffic counts, latency histograms, estimation outcomes,
    and abstention counters partitioned by reason and macro slice.
    """
    registry = get_metrics_registry()
    payload = registry.generate_latest()
    return Response(content=payload, media_type=PROMETHEUS_MEDIA_TYPE)
