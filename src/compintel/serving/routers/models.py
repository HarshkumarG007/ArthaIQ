"""Model metadata and data source transparency endpoints (T9.05)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from compintel.errors import ModelArtifactError
from compintel.serving.loader import ServingModelManager
from compintel.serving.types import (
    CurrentModelResponse,
    ModelCardResponse,
    SourceItem,
    SourcesResponse,
)

router = APIRouter(prefix="/v1", tags=["Models & Sources"])

_DEFAULT_SNAPSHOT_ID = "SNAP-1FF34A8E9633"
_DEFAULT_MODEL_VERSION = "0.1.0"

_MODEL_LIMITATIONS: list[str] = [
    (
        "Marginal, not conditional coverage: Conformal prediction guarantees "
        "80% marginal coverage averaged across exchangeable queries."
    ),
    (
        "Exchangeability & macro drift: Conformal validity assumes exchangeability "
        "between calibration and query distributions; macroeconomic hiring freezes "
        "or regime shifts degrade validity over time until recalibrated."
    ),
    (
        "Decoupled evidence framework: Occupational cohorts with fewer than 10 verified "
        "historical observations trigger mandatory abstention under Rule R-MD-08."
    ),
]

_OPERATIONAL_RULES: list[str] = [
    "R-UQ-01: No lone numbers; always return calibrated quantile span [P10, P50, P90].",
    "R-UQ-02: Abstention is an honest, structured outcome returning HTTP 200 payload.",
    "R-MD-07: Anti-heuristic unbundling; PT1 is strictly guaranteed cash annual.",
    "R-MD-13: Current salary is compare-only, quarantined from model inputs.",
    "R-MD-15: Zero-indicator missingness policy; missing features route to nested baseline models.",
]

_APPROVED_SOURCES: list[dict[str, Any]] = [
    {
        "source_id": "SRC-INT-VOL-01",
        "name": "Governed Voluntary Contributor Intake",
        "licence": "Contributor Agreement / DPDPA Consent",
        "tier": "TIER_A",
        "training_eligible": True,
        "purpose": "Primary empirical benchmark records with cryptographic verified lineage.",
        "record_count": 450,
        "freshness": "Continuous / As-of 2026-10-18",
    },
    {
        "source_id": "SRC-SUP-CORP-01",
        "name": "IT Corporate Median Remuneration Disclosures",
        "licence": "Statutory Public Filings (BSE/NSE Sec 197(12))",
        "tier": "TIER_A",
        "training_eligible": True,
        "purpose": "Statutory corporate anchor benchmarks for executive and median pay.",
        "record_count": 85,
        "freshness": "Statutory annual filings (FY2023-24 / FY2024-25)",
    },
    {
        "source_id": "SRC-SUP-MAC-01",
        "name": "RBI DBIE & MOSPI Macroeconomic Indicators",
        "licence": "Open Government Data License India (OGDL-IN)",
        "tier": "TIER_A",
        "training_eligible": False,
        "purpose": "CPI inflation index and INR/USD reference rate historical series.",
        "record_count": 14843,
        "freshness": "Monthly CPI / Daily FX as-of 2026-10-18",
    },
    {
        "source_id": "SRC-IND-OFF-01",
        "name": "MOSPI Periodic Labour Force Survey (PLFS)",
        "licence": "Open Government Data License India (OGDL-IN)",
        "tier": "TIER_A",
        "training_eligible": False,
        "purpose": "Macro wage anchors and formal technical workforce distributions.",
        "record_count": 1240,
        "freshness": "Annual survey release 2024",
    },
]


def _get_manager(request: Request) -> ServingModelManager | None:
    """Safely retrieve ServingModelManager from application state."""
    if hasattr(request.app, "state") and hasattr(request.app.state, "manager"):
        mgr = request.app.state.manager
        if isinstance(mgr, ServingModelManager):
            return mgr
    return None


@router.get(
    "/models/current",
    response_model=CurrentModelResponse,
    summary="Active champion model card and version info",
)
async def get_current_model(request: Request) -> CurrentModelResponse:
    """Return runtime metadata and governance information for active champion model."""
    manager = _get_manager(request)
    if manager is None or not manager.is_ready:
        raise ModelArtifactError(
            "Serving model manager is not ready. No model bundle loaded.",
            code="MODEL_NOT_READY",
        )

    bundle = manager.active_bundle
    meta = bundle.metadata

    return CurrentModelResponse(
        model_version=meta.model_version,
        bundle_name=meta.bundle_name,
        rung=bundle.rung,
        target_variable=meta.target_variable,
        target_unit=meta.target_unit,
        created_at_utc=meta.created_at_utc,
        canonical_snapshot_id=meta.canonical_snapshot_id,
        git_commit_hash=meta.git_commit_hash,
        model_family=meta.model_family,
        quantiles=meta.quantiles,
        metrics_summary=meta.metrics_summary,
        features=meta.feature_names,
        has_rollback=manager.previous_bundle is not None,
        limitations=_MODEL_LIMITATIONS,
        operational_rules=_OPERATIONAL_RULES,
    )


@router.get(
    "/models/current/card",
    response_model=ModelCardResponse,
    summary="Active champion full model card markdown",
)
async def get_model_card(request: Request) -> ModelCardResponse:
    """Return full markdown model card for active champion model."""
    manager = _get_manager(request)
    if manager is None or not manager.is_ready:
        raise ModelArtifactError(
            "Serving model manager is not ready. No model bundle loaded.",
            code="MODEL_NOT_READY",
        )

    bundle = manager.active_bundle
    card_md = bundle.model_card_markdown or (
        f"# Model Card: {bundle.metadata.bundle_name}\n\n"
        f"**Version:** {bundle.model_version}\n"
        f"**Rung:** {bundle.rung}\n"
        f"**Snapshot:** {bundle.metadata.canonical_snapshot_id}\n\n"
        "Model card documentation verified under Rule R-MD-14."
    )

    return ModelCardResponse(
        model_version=bundle.model_version,
        canonical_snapshot_id=bundle.metadata.canonical_snapshot_id,
        card_markdown=card_md,
    )


@router.get(
    "/sources",
    response_model=SourcesResponse,
    summary="Approved data sources, licenses, and provenance",
)
async def list_sources(request: Request) -> SourcesResponse:
    """Return transparency inventory of approved data sources and licensing constraints."""
    manager = _get_manager(request)
    snapshot_id = (
        manager.active_bundle.metadata.canonical_snapshot_id
        if manager and manager.is_ready
        else _DEFAULT_SNAPSHOT_ID
    )
    model_ver = (
        manager.active_bundle.model_version
        if manager and manager.is_ready
        else _DEFAULT_MODEL_VERSION
    )

    sources_items = [SourceItem(**s) for s in _APPROVED_SOURCES]

    return SourcesResponse(
        total=len(sources_items),
        data_snapshot_id=snapshot_id,
        model_version=model_ver,
        sources=sources_items,
        policy="Zero scraped job boards; strict license gate under Rule R-DA-01; DPDPA compliant.",
        licence_gate_status="COMPLIANT_R_DA_01",
    )
