"""Health, liveness, and readiness probe endpoints (architecture.md Section 11)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from compintel.serving.loader import ServingModelManager

router = APIRouter(tags=["Health"])


def _get_manager(request: Request) -> ServingModelManager | None:
    """Safely retrieve ServingModelManager from application state."""
    if hasattr(request.app, "state") and hasattr(request.app.state, "manager"):
        mgr = request.app.state.manager
        if isinstance(mgr, ServingModelManager):
            return mgr
    return None


@router.get("/healthz", summary="Liveness and readiness health check")
async def health_check(request: Request) -> JSONResponse:
    """Perform operational health check on serving bundle and runtime readiness.

    Returns:
    - 200 OK: Manager is initialized with an active, smoke-tested model bundle.
    - 503 Service Unavailable: No bundle is loaded or manager is unpromoted.
    """
    manager = _get_manager(request)
    now_iso = datetime.now(UTC).isoformat()

    if manager is None or not manager.is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "UNHEALTHY",
                "is_ready": False,
                "message": "Serving model manager is not ready. No active model bundle loaded.",
                "timestamp_utc": now_iso,
            },
        )

    health_info = manager.health_check()
    health_info["timestamp_utc"] = now_iso
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=health_info,
    )


@router.get("/livez", summary="Kubernetes liveness probe")
async def liveness() -> dict[str, Any]:
    """Basic process liveness check indicating FastAPI server is responsive."""
    return {
        "status": "LIVE",
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }


@router.get("/readyz", summary="Kubernetes readiness probe")
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe indicating whether API is primed to accept estimation traffic."""
    manager = _get_manager(request)
    if manager is not None and manager.is_ready:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "READY",
                "model_version": manager.model_version,
                "timestamp_utc": datetime.now(UTC).isoformat(),
            },
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "NOT_READY",
            "message": "Model bundle is loading or unavailable.",
            "timestamp_utc": datetime.now(UTC).isoformat(),
        },
    )
