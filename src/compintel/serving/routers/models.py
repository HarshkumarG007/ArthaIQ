"""Model metadata and data source transparency endpoints (architecture.md Section 11)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from compintel.serving.loader import ServingModelManager

router = APIRouter(prefix="/v1", tags=["Models & Sources"])

_APPROVED_SOURCES: list[dict[str, Any]] = [
    {
        "source_id": "SRC-INT-VOL-01",
        "name": "Governed Voluntary Contributor Intake",
        "licence": "Contributor Agreement / DPDPA Consent",
        "tier": "TIER_A",
        "training_eligible": True,
        "purpose": "Primary empirical benchmark records with cryptographic verified lineage.",
    },
    {
        "source_id": "SRC-SUP-CORP-01",
        "name": "IT Corporate Median Remuneration Disclosures",
        "licence": "Statutory Public Filings (BSE/NSE Sec 197(12))",
        "tier": "TIER_A",
        "training_eligible": True,
        "purpose": "Statutory corporate anchor benchmarks for executive and median pay.",
    },
    {
        "source_id": "SRC-SUP-MAC-01",
        "name": "RBI DBIE & MOSPI Macroeconomic Indicators",
        "licence": "Open Government Data License India (OGDL-IN)",
        "tier": "TIER_A",
        "training_eligible": False,
        "purpose": "CPI inflation index and INR/USD reference rate historical series.",
    },
    {
        "source_id": "SRC-IND-OFF-01",
        "name": "MOSPI Periodic Labour Force Survey (PLFS)",
        "licence": "Open Government Data License India (OGDL-IN)",
        "tier": "TIER_A",
        "training_eligible": False,
        "purpose": "Macro wage anchors and formal technical workforce distributions.",
    },
]


def _get_manager(request: Request) -> ServingModelManager | None:
    """Safely retrieve ServingModelManager from application state."""
    if hasattr(request.app, "state") and hasattr(request.app.state, "manager"):
        mgr = request.app.state.manager
        if isinstance(mgr, ServingModelManager):
            return mgr
    return None


@router.get("/models/current", summary="Active champion model card and version info")
async def get_current_model(request: Request) -> JSONResponse:
    """Return runtime metadata and governance information for active champion model."""
    manager = _get_manager(request)
    if manager is None or not manager.is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "UNAVAILABLE",
                "message": "Serving model manager is not ready. No model bundle loaded.",
            },
        )

    bundle = manager.active_bundle
    meta = bundle.metadata

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "model_version": meta.model_version,
            "bundle_name": meta.bundle_name,
            "rung": bundle.rung,
            "target_variable": meta.target_variable,
            "target_unit": meta.target_unit,
            "created_at_utc": meta.created_at_utc,
            "canonical_snapshot_id": meta.canonical_snapshot_id,
            "git_commit_hash": meta.git_commit_hash,
            "model_family": meta.model_family,
            "quantiles": meta.quantiles,
            "metrics_summary": meta.metrics_summary,
            "has_rollback": manager.previous_bundle is not None,
        },
    )


@router.get("/sources", summary="Approved data sources, licenses, and provenance")
async def list_sources() -> dict[str, Any]:
    """Return transparency inventory of approved data sources and licensing constraints."""
    return {
        "total": len(_APPROVED_SOURCES),
        "sources": _APPROVED_SOURCES,
        "policy": "Zero scraped job boards; strict license gate under Rule R-DA-01.",
    }
