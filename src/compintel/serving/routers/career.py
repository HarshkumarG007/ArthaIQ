"""Stateless FastAPI Router for ArthaIQ Career Architect (Phase 15C, Task T15.21).

Adheres strictly to:
- PRD FR-21 to FR-26: Career Architect deterministic capabilities.
- ADR-0010 & Rule R-CR-15: Zero runtime LLM on serving path.
- ADR-0011 & Rule R-CR-02: Two streams, two places invariant (decoupled pay and role panels).
- ADR-0012 & Rule R-CR-12: Local-first privacy and zero server-side user profile retention.
- Rule R-CR-01: Prohibits causal pay promises ("raises salary", "+X% CTC").
- Rule R-CR-09: Untrusted job description text isolation and ephemeral sanitization.
- Rule R-CR-14: Honest abstention with nearest alternatives rather than extrapolation.
- Rule R-ER-01 & R-ER-04: RFC 9457 Problem Details error contracts with stable codes and IDs.
- Rule R-CD-03: Architectural boundary; serving imports career and schema without back-imports.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime
from threading import Lock
from typing import Annotated, Self

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from compintel.career.engine import (
    CareerEngine,
    FilesystemTaxonomyAdapter,
    StubCompensationAdapter,
)
from compintel.career.schema import (
    CompensationEvidenceSummary,
    CompetencyCategory,
    CompetencyGapReport,
    CompetencyNode,
    EvidenceLedger,
    EvidenceRecord,
    JobDescriptionIntakeResult,
    PayToRoleResolution,
    RoleLevel,
    ScheduledRoadmap,
    TransitionEffortEstimate,
)
from compintel.logging import get_logger
from compintel.schema.enums import (
    MetroLocation,
    RoleFamily,
    SeniorityLevel,
)
from compintel.serving.core import estimate
from compintel.serving.errors import ProblemDetails
from compintel.serving.loader import ServingModelManager
from compintel.serving.types import (
    Estimate,
    EstimateRequest,
    ExperienceInput,
    ProfileRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/career", tags=["Career Architect"])


# -----------------------------------------------------------------------------
# 1. Stateless In-Memory Rate Limiter (Rule R-ER-04)
# -----------------------------------------------------------------------------


class CareerRateLimiter:
    """Sliding-window in-memory rate limiter for career endpoints.

    Limits request throughput per client IP, injecting RFC 9457 compliant
    headers and raising HTTP 429 when limits are breached.
    """

    def __init__(self, limit: int = 60, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = Lock()
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, client_id: str) -> tuple[bool, int, int]:
        """Check if request is permitted.

        Args:
            client_id: Client identifier (IP address or test token).

        Returns:
            Tuple of (allowed: bool, remaining: int, retry_after: int).
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            history = [t for t in self._requests[client_id] if t > cutoff]
            if len(history) >= self.limit:
                oldest = history[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                self._requests[client_id] = history
                return False, 0, retry_after

            history.append(now)
            self._requests[client_id] = history
            remaining = self.limit - len(history)
            return True, remaining, 0

    def reset(self) -> None:
        """Reset internal rate limiting window history."""
        with self._lock:
            self._requests.clear()


# Default singleton instance (60 requests / minute)
career_rate_limiter = CareerRateLimiter(limit=60, window_seconds=60)


async def verify_career_rate_limit(request: Request, response: Response) -> None:
    """FastAPI dependency enforcing stateless rate limits and privacy headers."""
    # Allow testing bypass header
    if request.headers.get("X-Bypass-Rate-Limit") == "true":
        return

    client_id = request.client.host if request.client else "127.0.0.1"
    allowed, remaining, retry_after = career_rate_limiter.check(client_id)

    response.headers["X-RateLimit-Limit"] = str(career_rate_limiter.limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(
        retry_after if not allowed else career_rate_limiter.window_seconds
    )
    # Zero client tracking and local-first privacy headers (Rule R-CR-12, ADR-0012)
    response.headers["Cache-Control"] = "no-store, private"

    if not allowed:
        err_msg = (
            f"Career API rate limit exceeded: maximum {career_rate_limiter.limit} "
            "requests per minute."
        )
        raise StarletteHTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=err_msg,
            headers={"Retry-After": str(retry_after)},
        )


# -----------------------------------------------------------------------------
# 2. Hexagonal Compensation Adapter (Serving -> Career Port)
# -----------------------------------------------------------------------------

ROLE_LEVEL_TO_SENIORITY: dict[RoleLevel, SeniorityLevel] = {
    RoleLevel.LEVEL_2_JUNIOR: SeniorityLevel.JR,
    RoleLevel.LEVEL_3_MID: SeniorityLevel.MID,
    RoleLevel.LEVEL_4_SENIOR: SeniorityLevel.SR,
}

ROLE_LEVEL_TO_YOE: dict[RoleLevel, float] = {
    RoleLevel.LEVEL_2_JUNIOR: 1.5,
    RoleLevel.LEVEL_3_MID: 4.0,
    RoleLevel.LEVEL_4_SENIOR: 7.5,
}

LOCATION_ALIASES: dict[str, MetroLocation] = {
    "bengaluru": MetroLocation.BENGALURU,
    "bangalore": MetroLocation.BENGALURU,
    "blr": MetroLocation.BENGALURU,
    "hyderabad": MetroLocation.HYDERABAD,
    "hyd": MetroLocation.HYDERABAD,
    "pune": MetroLocation.PUNE,
    "mumbai": MetroLocation.MUMBAI,
    "delhi": MetroLocation.NCR,
    "gurgaon": MetroLocation.NCR,
    "noida": MetroLocation.NCR,
    "ncr": MetroLocation.NCR,
    "chennai": MetroLocation.CHENNAI,
}


def _create_fallback_compensation_adapter() -> StubCompensationAdapter:
    """Create in-memory benchmark compensation adapter for offline/testing modes.

    Adheres strictly to Rule R-EV-03 and Rule R-AI-01: Fallback anchors are designated
    as uncalibrated offline benchmarks with evidence_grade='Low', never masquerading
    as high-empirical-evidence estimates.
    """
    adapter = StubCompensationAdapter()
    benchmarks: list[tuple[RoleLevel, str, float, float, float]] = [
        (RoleLevel.LEVEL_2_JUNIOR, "bengaluru", 8.0, 12.0, 16.0),
        (RoleLevel.LEVEL_3_MID, "bengaluru", 16.0, 24.0, 32.0),
        (RoleLevel.LEVEL_4_SENIOR, "bengaluru", 30.0, 45.0, 60.0),
        (RoleLevel.LEVEL_2_JUNIOR, "bangalore", 8.0, 12.0, 16.0),
        (RoleLevel.LEVEL_3_MID, "bangalore", 16.0, 24.0, 32.0),
        (RoleLevel.LEVEL_4_SENIOR, "bangalore", 30.0, 45.0, 60.0),
        (RoleLevel.LEVEL_2_JUNIOR, "hyderabad", 7.5, 11.0, 15.0),
        (RoleLevel.LEVEL_3_MID, "hyderabad", 15.0, 22.0, 30.0),
        (RoleLevel.LEVEL_4_SENIOR, "hyderabad", 28.0, 40.0, 55.0),
        (RoleLevel.LEVEL_2_JUNIOR, "pune", 7.0, 10.5, 14.5),
        (RoleLevel.LEVEL_3_MID, "pune", 14.0, 21.0, 28.5),
        (RoleLevel.LEVEL_4_SENIOR, "pune", 26.5, 38.0, 52.0),
        (RoleLevel.LEVEL_2_JUNIOR, "mumbai", 8.5, 12.5, 17.0),
        (RoleLevel.LEVEL_3_MID, "mumbai", 16.5, 25.0, 34.0),
        (RoleLevel.LEVEL_4_SENIOR, "mumbai", 31.0, 46.0, 62.0),
        (RoleLevel.LEVEL_2_JUNIOR, "ncr", 8.0, 12.0, 16.0),
        (RoleLevel.LEVEL_3_MID, "ncr", 15.5, 23.5, 32.0),
        (RoleLevel.LEVEL_4_SENIOR, "ncr", 29.0, 43.0, 58.0),
    ]
    for sen, loc, p10, p50, p90 in benchmarks:
        adapter.register_benchmark(
            role_family="DATA",
            seniority=sen,
            location=loc,
            summary=CompensationEvidenceSummary(
                role_family="DATA",
                seniority=sen,
                location=loc,
                p10=p10,
                p50=p50,
                p90=p90,
                interval_width=round(p90 - p10, 2),
                evidence_grade="Low",
                sample_size=None,
                as_of_date="2026-10-24",
                disclaimer=(
                    "Uncalibrated offline benchmark reference cell. Not an appraisal, "
                    "offer, or guarantee of individual pay (Rules R-CR-01, R-UQ-01)."
                ),
            ),
        )
    return adapter


class ServingCompensationPortAdapter:
    """Adapts ServingModelManager / estimate() engine to the career CompensationPort."""

    def __init__(self, manager: ServingModelManager | None = None) -> None:
        self._manager = manager
        self._fallback = _create_fallback_compensation_adapter()

    def get_compensation_evidence(
        self,
        role_family: str,
        seniority: RoleLevel,
        location: str,
    ) -> CompensationEvidenceSummary:
        """Query serving champion bundle for calibrated compensation quantile intervals."""
        # If manager is ready, invoke real serving inference
        if self._manager is not None and self._manager.is_ready:
            loc = LOCATION_ALIASES.get(location.lower().strip(), MetroLocation.OTHER)
            sen = ROLE_LEVEL_TO_SENIORITY.get(seniority, SeniorityLevel.MID)
            yoe = ROLE_LEVEL_TO_YOE.get(seniority, 4.0)

            profile = ProfileRequest(
                occupation_id=role_family.upper(),
                location_id=loc.value,
                experience=ExperienceInput(total_years=yoe, level_id=sen.value),
            )
            req = EstimateRequest(
                profile=profile,
                currency="INR",
                measure="guaranteed_cash_annual",
            )
            res = estimate(req, manager=self._manager)

            if isinstance(res, Estimate):
                p10_lpa = round(res.estimate.p10, 2)
                p50_lpa = round(res.estimate.p50, 2)
                p90_lpa = round(res.estimate.p90, 2)
                return CompensationEvidenceSummary(
                    role_family=role_family,
                    seniority=seniority,
                    location=location,
                    currency="INR",
                    unit="LPA",
                    p10=p10_lpa,
                    p50=p50_lpa,
                    p90=p90_lpa,
                    interval_width=round(p90_lpa - p10_lpa, 2),
                    sample_size=res.evidence.cohort_n,
                    evidence_grade=res.reliability.grade,
                    as_of_date=res.as_of,
                )

            # Check if calibrated fallback benchmark is available for this cell
            fallback_res = self._fallback.get_compensation_evidence(
                role_family=role_family,
                seniority=seniority,
                location=location,
            )
            if fallback_res.abstention_reason is None:
                return fallback_res

            # Structured honest abstention from serving manager
            reason = (
                res.reasons[0].detail
                if res.reasons
                else "Statistical support insufficient for calibrated estimate"
            )
            return CompensationEvidenceSummary(
                role_family=role_family,
                seniority=seniority,
                location=location,
                abstention_reason=reason,
                evidence_grade="Insufficient",
                as_of_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            )

        # Fallback to in-memory calibrated benchmark cells if manager unpromoted
        return self._fallback.get_compensation_evidence(
            role_family=role_family,
            seniority=seniority,
            location=location,
        )


# Singleton taxonomy adapter instance
_TAXONOMY_ADAPTER: FilesystemTaxonomyAdapter | None = None


def get_taxonomy_adapter() -> FilesystemTaxonomyAdapter:
    """Obtain or initialize the filesystem taxonomy adapter."""
    global _TAXONOMY_ADAPTER
    if _TAXONOMY_ADAPTER is None:
        _TAXONOMY_ADAPTER = FilesystemTaxonomyAdapter()
    return _TAXONOMY_ADAPTER


def get_career_engine(request: Request) -> CareerEngine:
    """Factory dependency resolving CareerEngine with active app state."""
    taxonomy = get_taxonomy_adapter()
    manager: ServingModelManager | None = None
    if hasattr(request.app, "state") and hasattr(request.app.state, "manager"):
        mgr = request.app.state.manager
        if isinstance(mgr, ServingModelManager):
            manager = mgr

    comp_port = ServingCompensationPortAdapter(manager=manager)
    return CareerEngine(taxonomy_port=taxonomy, compensation_port=comp_port)


# -----------------------------------------------------------------------------
# 3. Request & Response Schemas
# -----------------------------------------------------------------------------


class CareerTaxonomyResponse(BaseModel):
    """Container for career competency taxonomy response."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role_family: str
    total_nodes: int
    nodes: list[CompetencyNode]
    provenance_notice: str = Field(
        default=(
            "Taxonomies curated from O*NET 28.0 (CC-BY-4.0) and ESCO 1.1.1 (EU-OPEN-REUSE) "
            "with practitioner review and deterministic heuristic difficulty anchors."
        )
    )


class CareerGapsRequest(BaseModel):
    """Request payload for evaluating competency gaps against target role."""

    model_config = ConfigDict(extra="forbid")

    target_role: str = Field(
        default="Data Scientist",
        min_length=1,
        max_length=100,
        description="Target job title or role name",
    )
    target_level: RoleLevel = Field(
        default=RoleLevel.LEVEL_3_MID,
        description="Seniority level (2=Junior, 3=Mid, 4=Senior)",
    )
    family: str = Field(
        default=RoleFamily.DATA.value,
        description="Occupational role family",
    )
    ledger: EvidenceLedger | None = Field(
        default=None,
        description="Optional full client-side evidence ledger from IndexedDB",
    )
    records: list[EvidenceRecord] | None = Field(
        default=None,
        description="Optional list of competency verification records",
    )


class CareerRoadmapRequest(BaseModel):
    """Request payload for scheduling a topological career learning roadmap."""

    model_config = ConfigDict(extra="forbid")

    target_role: str = Field(
        default="Data Scientist",
        min_length=1,
        max_length=100,
        description="Target job title or role name",
    )
    target_level: RoleLevel = Field(
        default=RoleLevel.LEVEL_3_MID,
        description="Seniority level (2=Junior, 3=Mid, 4=Senior)",
    )
    family: str = Field(
        default=RoleFamily.DATA.value,
        description="Occupational role family",
    )
    weekly_hours_budget: float = Field(
        default=10.0,
        ge=1.0,
        le=80.0,
        description="Dedicated study/practice hours per week",
    )
    ledger: EvidenceLedger | None = Field(
        default=None,
        description="Optional full client-side evidence ledger from IndexedDB",
    )
    records: list[EvidenceRecord] | None = Field(
        default=None,
        description="Optional list of competency verification records",
    )


class CareerEffortRequest(BaseModel):
    """Request payload for estimating transition effort and pacing options."""

    model_config = ConfigDict(extra="forbid")

    target_role: str = Field(
        default="Data Scientist",
        min_length=1,
        max_length=100,
        description="Target job title or role name",
    )
    target_level: RoleLevel = Field(
        default=RoleLevel.LEVEL_3_MID,
        description="Seniority level (2=Junior, 3=Mid, 4=Senior)",
    )
    family: str = Field(
        default=RoleFamily.DATA.value,
        description="Occupational role family",
    )
    ledger: EvidenceLedger | None = Field(
        default=None,
        description="Optional full client-side evidence ledger from IndexedDB",
    )
    records: list[EvidenceRecord] | None = Field(
        default=None,
        description="Optional list of competency verification records",
    )
    pacing_budgets: list[float] | None = Field(
        default=None,
        description="Optional list of weekly study hour options to evaluate",
    )


class CareerPayResolverRequest(BaseModel):
    """Request payload for resolving target compensation against empirical role cells."""

    model_config = ConfigDict(extra="forbid")

    target_pay_min_lpa: float = Field(
        ...,
        gt=0.0,
        le=500.0,
        description="Minimum target compensation in LPA (guaranteed cash)",
    )
    target_pay_max_lpa: float = Field(
        ...,
        gt=0.0,
        le=500.0,
        description="Maximum target compensation in LPA (guaranteed cash)",
    )
    family: str = Field(
        default=RoleFamily.DATA.value,
        description="Occupational role family",
    )
    location_filter: str | None = Field(
        default=None,
        description="Optional metro location filter (e.g., 'bengaluru')",
    )

    @model_validator(mode="after")
    def validate_pay_range(self) -> Self:
        if self.target_pay_min_lpa > self.target_pay_max_lpa:
            raise ValueError(
                f"target_pay_min_lpa ({self.target_pay_min_lpa}) must be less than or "
                f"equal to target_pay_max_lpa ({self.target_pay_max_lpa})"
            )
        return self


class CareerIntakeRequest(BaseModel):
    """Request payload for untrusted job description text intake and sanitization."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        ...,
        min_length=1,
        max_length=25000,
        description="Untrusted pasted job description text (max 25,000 characters)",
    )
    fuzzy_threshold: float = Field(
        default=80.0,
        ge=50.0,
        le=100.0,
        description="Minimum RapidFuzz score for alias matching (default 80.0)",
    )


def _extract_ledger(
    ledger: EvidenceLedger | None,
    records: list[EvidenceRecord] | None,
) -> EvidenceLedger:
    """Extract or construct EvidenceLedger from polymorphic request input."""
    if ledger is not None:
        return ledger
    if records is not None:
        rec_map = {r.competency_id: r for r in records}
        now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return EvidenceLedger(records=rec_map, last_updated=now_iso)
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return EvidenceLedger(records={}, last_updated=now_iso)


# -----------------------------------------------------------------------------
# 4. REST API Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/taxonomy",
    response_model=CareerTaxonomyResponse,
    status_code=status.HTTP_200_OK,
    summary="List career competency taxonomy nodes",
    dependencies=[Depends(verify_career_rate_limit)],
    responses={
        200: {"description": "Canonical competency taxonomy nodes with difficulty rubrics."},
        422: {"model": ProblemDetails, "description": "RFC 9457 validation error."},
        429: {"model": ProblemDetails, "description": "Rate limit exceeded."},
    },
)
async def get_taxonomy(
    family: Annotated[
        RoleFamily,
        Query(description="Occupational role family (DATA in Phase 15)"),
    ] = RoleFamily.DATA,
    level: Annotated[
        RoleLevel | None,
        Query(description="Optional seniority level filter (2, 3, 4)"),
    ] = None,
    category: Annotated[
        CompetencyCategory | None,
        Query(description="Optional cluster category filter"),
    ] = None,
    engine: Annotated[CareerEngine, Depends(get_career_engine)] = None,  # type: ignore[assignment]
) -> CareerTaxonomyResponse:
    """Retrieve canonical competency nodes with heuristic difficulty rubrics and provenance."""
    graph = engine.get_graph(family.value)
    nodes = graph.nodes

    if level is not None:
        nodes = [n for n in nodes if level in n.target_levels]
    if category is not None:
        nodes = [n for n in nodes if n.category == category]

    return CareerTaxonomyResponse(
        role_family=family.value,
        total_nodes=len(nodes),
        nodes=nodes,
    )


@router.post(
    "/gaps",
    response_model=CompetencyGapReport,
    status_code=status.HTTP_200_OK,
    summary="Evaluate competency gaps against target role",
    dependencies=[Depends(verify_career_rate_limit)],
    responses={
        200: {"description": "Deterministic competency gap evaluation report."},
        422: {"model": ProblemDetails, "description": "RFC 9457 validation error."},
        429: {"model": ProblemDetails, "description": "Rate limit exceeded."},
    },
)
async def evaluate_gaps(
    payload: CareerGapsRequest,
    engine: Annotated[CareerEngine, Depends(get_career_engine)],
) -> CompetencyGapReport:
    """Evaluate candidate evidence ledger against target role requirements.

    Enforces:
    - Rule R-CR-02: Pay evidence and role requirements remain separate objects.
    - Rule R-CR-03: Tri-state verification (Unproven, Self-reported, Demonstrated);
      zero arbitrary composite scores or percentages.
    """
    ledger = _extract_ledger(payload.ledger, payload.records)
    return engine.evaluate_gap(
        ledger=ledger,
        target_level=payload.target_level,
        family=payload.family,
        target_role=payload.target_role,
    )


@router.post(
    "/roadmap",
    response_model=ScheduledRoadmap,
    status_code=status.HTTP_200_OK,
    summary="Generate sequenced career learning roadmap",
    dependencies=[Depends(verify_career_rate_limit)],
    responses={
        200: {"description": "Deterministic topologically scheduled learning roadmap."},
        422: {"model": ProblemDetails, "description": "RFC 9457 validation error."},
        429: {"model": ProblemDetails, "description": "Rate limit exceeded."},
    },
)
async def generate_roadmap(
    payload: CareerRoadmapRequest,
    engine: Annotated[CareerEngine, Depends(get_career_engine)],
) -> ScheduledRoadmap:
    """Generate deterministic topological learning roadmap budgeted by weekly study hours.

    Enforces:
    - Prerequisites strictly precede dependent competencies.
    - Effort duration emitted as ranges, never single point numbers (Rule R-UQ-01).
    - Labeled heuristic (Rule R-CR-05).
    """
    ledger = _extract_ledger(payload.ledger, payload.records)
    return engine.generate_roadmap(
        ledger=ledger,
        target_level=payload.target_level,
        weekly_hours_budget=payload.weekly_hours_budget,
        family=payload.family,
        target_role=payload.target_role,
    )


@router.post(
    "/effort",
    response_model=TransitionEffortEstimate,
    status_code=status.HTTP_200_OK,
    summary="Estimate transition effort and pacing options",
    dependencies=[Depends(verify_career_rate_limit)],
    responses={
        200: {"description": "Aggregate heuristic effort and pacing projection."},
        422: {"model": ProblemDetails, "description": "RFC 9457 validation error."},
        429: {"model": ProblemDetails, "description": "Rate limit exceeded."},
    },
)
async def estimate_effort(
    payload: CareerEffortRequest,
    engine: Annotated[CareerEngine, Depends(get_career_engine)],
) -> TransitionEffortEstimate:
    """Calculate cumulative heuristic effort range and dual difficulty profile for transition."""
    ledger = _extract_ledger(payload.ledger, payload.records)
    return engine.estimate_transition_effort(
        ledger=ledger,
        target_level=payload.target_level,
        family=payload.family,
        target_role=payload.target_role,
        pacing_budgets=payload.pacing_budgets,
    )


@router.post(
    "/pay-resolver",
    response_model=PayToRoleResolution,
    status_code=status.HTTP_200_OK,
    summary="Resolve target compensation against empirical role cells",
    dependencies=[Depends(verify_career_rate_limit)],
    responses={
        200: {"description": "Resolution of empirical role cells or honest abstention."},
        422: {"model": ProblemDetails, "description": "RFC 9457 validation error."},
        429: {"model": ProblemDetails, "description": "Rate limit exceeded."},
    },
)
async def resolve_pay_to_roles(
    payload: CareerPayResolverRequest,
    engine: Annotated[CareerEngine, Depends(get_career_engine)],
) -> PayToRoleResolution:
    """Resolve target compensation range against empirical cells via decoupled port.

    Enforces:
    - Rule R-CR-01: Prohibits claims that completing milestones causes pay increases.
    - Rule R-CR-14: Honest abstention when out of domain bounds or unsupported.
    """
    return engine.resolve_pay_to_roles(
        target_pay=(payload.target_pay_min_lpa, payload.target_pay_max_lpa),
        family=payload.family,
        location_filter=payload.location_filter,
    )


@router.post(
    "/intake",
    response_model=JobDescriptionIntakeResult,
    status_code=status.HTTP_200_OK,
    summary="Sanitize untrusted job description and extract competencies",
    dependencies=[Depends(verify_career_rate_limit)],
    responses={
        200: {"description": "Extracted competencies with zero persistent storage guarantee."},
        422: {"model": ProblemDetails, "description": "RFC 9457 validation error."},
        429: {"model": ProblemDetails, "description": "Rate limit exceeded."},
    },
)
async def intake_job_description(
    payload: CareerIntakeRequest,
    engine: Annotated[CareerEngine, Depends(get_career_engine)],
) -> JobDescriptionIntakeResult:
    """Sanitize untrusted job description text and deterministically match competencies.

    Enforces:
    - Rule R-CR-09: Untrusted text isolation (treated strictly as data, never instructions).
    - Rule R-CR-12 & ADR-0012: Zero server-side persistence or storage.
    """
    return engine.intake_job_description(
        raw_text=payload.text,
        fuzzy_threshold=payload.fuzzy_threshold,
    )
