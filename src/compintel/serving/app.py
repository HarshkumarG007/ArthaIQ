"""FastAPI application factory and server entry point (Phase 9, Task T9.02, T9.11a).

Adheres to:
- architecture.md Section 11: Pure function wrapped by FastAPI.
- PRD FR-13 & NFR-07: Structured logs, Prometheus /metrics endpoint.
- Rule R-ER-04: RFC 9457 problem details, request IDs, security headers, clean 5xx handling.
- Rule R-MD-14: Serving bundle loader with startup validation and rollback support.
- Rule R-CD-03: Architectural boundary; serving never imports ingestion/quality/eval.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compintel.logging import get_logger
from compintel.serving.core import get_default_serving_manager
from compintel.serving.errors import setup_exception_handlers
from compintel.serving.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from compintel.serving.routers.estimates import router as estimates_router
from compintel.serving.routers.evidence import router as evidence_router
from compintel.serving.routers.health import router as health_router
from compintel.serving.routers.metrics import router as metrics_router
from compintel.serving.routers.models import router as models_router
from compintel.serving.routers.taxonomy import router as taxonomy_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from compintel.serving.loader import ServingModelManager

logger = get_logger(__name__)


def create_app(manager: ServingModelManager | None = None) -> FastAPI:
    """Create and configure FastAPI application for compensation intelligence serving."""

    active_manager = manager or get_default_serving_manager()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Manage runtime lifespan: load champion bundle at startup and manage resources."""
        app.state.manager = active_manager

        if active_manager.is_ready:
            logger.info(
                "serving_app_started",
                model_version=active_manager.model_version,
                rung=active_manager.rung,
            )
        else:
            logger.warn(
                "serving_app_started_unpromoted",
                msg="Manager started without an active model bundle.",
            )

        yield

        logger.info("serving_app_shutdown")

    app = FastAPI(
        title="ArthaIQ Compensation Intelligence API",
        description="India Tech Compensation Intelligence Serving Engine (Decision Support v1).",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    # Eagerly attach manager to state so testing without lifespan context works seamlessly
    app.state.manager = active_manager

    # 1. Register RFC 9457 exception handlers
    setup_exception_handlers(app)

    # 2. Register middlewares (outermost to innermost order)
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request ID correlation
    app.add_middleware(RequestIDMiddleware)

    # Access logging & metrics recording
    app.add_middleware(RequestLoggingMiddleware)

    # CORS allowlist
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 3. Mount Routers
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(estimates_router)
    app.include_router(taxonomy_router)
    app.include_router(models_router)
    app.include_router(evidence_router)

    return app


# Module-level default application instance for ASGI servers (Uvicorn)
app: FastAPI = create_app()
