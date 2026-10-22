"""Counterfactual negotiation and scenario modeling router (EXP-15 / Task T12.02).

Adheres to:
- PRD Section 5, FR-02 (PT4 Negotiation & Offer Scenario Modeling).
- CHARTER-EXP-15: Monotonic counterfactual quantile inversion.
- Rule R-UQ-01: Zero lone numbers; every scenario outputs [P10, P50, P90] spans.
- Rule R-MD-08: Transparent uncertainty, zero financial advisory or lone-number promises.
- Rule R-CD-03: Architectural boundary; serving never imports ingestion/quality/eval.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from compintel.serving.counterfactual import (
    CounterfactualQuery,
    CounterfactualScenarioEngine,
    CounterfactualScenarioResponse,
    DualOfferComparisonResponse,
    OfferStructure,
)
from compintel.serving.errors import ProblemDetails
from compintel.serving.loader import ServingModelManager
from compintel.serving.types import ProfileRequest

router = APIRouter(prefix="/v1", tags=["Scenarios"])


def _get_manager(request: Request) -> ServingModelManager | None:
    """Safely retrieve ServingModelManager from application state."""
    if hasattr(request.app, "state") and hasattr(request.app.state, "manager"):
        mgr = request.app.state.manager
        if isinstance(mgr, ServingModelManager):
            return mgr
    return None


class DualOfferComparisonRequest(BaseModel):
    """Request payload comparing competing offer structures against candidate profile."""

    profile: ProfileRequest
    offer_a: OfferStructure = Field(..., description="First competing offer structure.")
    offer_b: OfferStructure = Field(..., description="Second competing offer structure.")


@router.post(
    "/scenarios",
    response_model=CounterfactualScenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute constrained counterfactual scenario frontier (PT4)",
    responses={
        200: {
            "description": "Counterfactual scenario frontier with explicit uncertainty bounds.",
        },
        422: {
            "model": ProblemDetails,
            "description": "RFC 9457 Problem Details for invalid scenario parameters.",
        },
    },
)
async def generate_counterfactual_scenario(
    payload: CounterfactualQuery,
    request: Request,
) -> CounterfactualScenarioResponse:
    """Generate monotonic counterfactual compensation frontier.

    Simulates experience, promotion, or metro relocation parameter perturbations
    under structural monotonicity constraints without emitting lone numbers.
    """
    manager = _get_manager(request)
    engine = CounterfactualScenarioEngine(model_manager=manager)
    return engine.run_query(payload)


@router.post(
    "/scenarios/dual-offer",
    response_model=DualOfferComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate dual offer trade-off analysis (PT4)",
    responses={
        200: {
            "description": "Risk-adjusted multi-component trade-off analysis and tax bounds.",
        },
        422: {
            "model": ProblemDetails,
            "description": "RFC 9457 Problem Details for invalid offer structures.",
        },
    },
)
async def evaluate_dual_offer_scenario(
    payload: DualOfferComparisonRequest,
    request: Request,
) -> DualOfferComparisonResponse:
    """Evaluate trade-off and risk-adjusted positioning between two competing offers.

    Compares fixed guaranteed cash, equity, and variable components against candidate
    market quantile distribution, calculating net in-hand take-home bounds.
    """
    manager = _get_manager(request)
    engine = CounterfactualScenarioEngine(model_manager=manager)
    return engine.evaluate_dual_offer_tradeoff(
        profile=payload.profile,
        offer_a=payload.offer_a,
        offer_b=payload.offer_b,
    )
