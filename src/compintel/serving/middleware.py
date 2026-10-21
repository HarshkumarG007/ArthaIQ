"""Serving middlewares for request correlation, security headers, structured logging, and metrics.

Adheres to:
- architecture.md Section 11 & Section 12: Request IDs on all requests; security headers.
- PRD FR-13 & NFR-07: Internal monitoring, latency and request counters.
- Rule R-ER-04: Responses carry request_id for end-to-end tracing.
- Rule R-DA-07: Structured logging without sensitive inputs or PII.
- Rule R-CD-03: Architectural boundary; serving never imports ingestion/quality/eval.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from compintel.logging import get_logger
from compintel.monitoring.metrics import get_metrics_registry

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)

_VALID_REQ_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")

_KNOWN_PATHS: frozenset[str] = frozenset(
    {
        "/healthz",
        "/livez",
        "/readyz",
        "/metrics",
        "/v1/estimates",
        "/v1/models/current",
        "/v1/models/current/card",
        "/v1/sources",
        "/v1/taxonomy/roles",
        "/v1/taxonomy/seniorities",
        "/v1/taxonomy/locations",
        "/v1/taxonomy/measures",
        "/v1/evidence/summary",
        "/v1/contributions",
        "/v1/contributions/delete",
    }
)


def _normalize_metric_path(raw_path: str) -> str:
    """Normalize URI path to prevent metric cardinality explosion."""
    cleaned = raw_path.split("?")[0].rstrip("/") or "/"
    if cleaned in _KNOWN_PATHS:
        return cleaned
    return "/other"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Enforces correlation request IDs on every incoming HTTP request and response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Extract or generate request_id and inject into request state and response headers."""
        raw_header = request.headers.get("X-Request-ID")
        if raw_header and _VALID_REQ_ID_PATTERN.match(raw_header.strip()):
            request_id = raw_header.strip()
        else:
            request_id = str(uuid4())

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects mandatory HTTP security headers per architecture.md Section 12."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Inject security headers into every outgoing response."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emits structured access logs and Prometheus metrics (Rule R-DA-07, R-CD-06, NFR-07)."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request arrival and completion with latency and update Prometheus metrics."""
        start_time = time.perf_counter()
        req_id = getattr(request.state, "request_id", None) or request.headers.get(
            "X-Request-ID", "unknown"
        )

        path = request.url.path if request.url else "/unknown"
        method = request.method
        metric_path = _normalize_metric_path(path)
        metrics = get_metrics_registry()

        metrics.active_requests.labels(method=method).inc()
        try:
            response = await call_next(request)
        finally:
            metrics.active_requests.labels(method=method).dec()

        duration_sec = time.perf_counter() - start_time
        duration_ms = round(duration_sec * 1000, 2)
        status_code = response.status_code

        # Record standard operational telemetry
        metrics.http_requests_total.labels(
            method=method,
            path=metric_path,
            status=str(status_code),
        ).inc()
        metrics.http_request_duration_seconds.labels(
            method=method,
            path=metric_path,
        ).observe(duration_sec)

        # Log at debug for health/metrics checks to prevent log spam, info for standard traffic
        if path in ("/healthz", "/livez", "/readyz", "/metrics"):
            logger.debug(
                "http_health_check",
                request_id=req_id,
                method=method,
                path=path,
                status=status_code,
                duration_ms=duration_ms,
            )
        else:
            logger.info(
                "http_request_completed",
                request_id=req_id,
                method=method,
                path=path,
                status=status_code,
                duration_ms=duration_ms,
            )

        return response
