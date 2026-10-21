"""FastAPI router for voluntary contributions and statutory erasure (PRD US-07, ADR-0008).

Exposes:
- POST /v1/contributions (Submit voluntary compensation record with unbundled consent)
- DELETE /v1/me/data (Statutory erasure cascading across operational stores)
- POST /v1/contributions/delete (Alternative erasure endpoint using deletion token)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from compintel.governance.db import get_db
from compintel.governance.service import (
    ConsentRequiredError,
    ContributionSubmission,
    RecordNotFoundError,
    execute_erasure,
    submit_contribution,
)

router = APIRouter(prefix="/v1", tags=["contributions"])


class ContributionCreateRequest(BaseModel):
    """Payload for voluntary pay intake per ADR-0008."""

    role_family: str = Field(..., description="Canonical role family (e.g. 'software_engineer').")
    title_raw: str = Field(..., max_length=128, description="Raw job title.")
    seniority: str = Field(..., description="Seniority tier (e.g. 'IC3_SENIOR').")
    location: str = Field(..., description="Employment location (e.g. 'BLR', 'HYD').")
    years_experience: Decimal = Field(
        ..., ge=0, le=40, description="Years of professional experience."
    )
    guaranteed_cash_annual: Decimal = Field(..., gt=0, description="Annual guaranteed cash in INR.")
    currency: str = Field("INR", description="Currency code (strictly 'INR' for Phase 9).")
    base_salary_annual: Decimal | None = Field(None, description="Basic pay portion.")
    variable_pay_annual: Decimal | None = Field(None, description="Annual target variable bonus.")
    equity_grant_annual: Decimal | None = Field(None, description="Annualized RSU/equity grant.")
    benefits_annual: Decimal | None = Field(None, description="Statutory retiral benefits.")
    company_raw: str | None = Field(
        None, max_length=128, description="Employer name (anonymized per R-DA-10)."
    )
    company_stage: str | None = Field(None, description="Company category/stage.")
    consent_benchmarking: bool = Field(
        False, description="Unbundled consent for benchmarking (must be True)."
    )
    consent_research: bool = Field(False, description="Optional consent for research aggregation.")
    consent_future_contact: bool = Field(False, description="Optional consent for future contact.")
    consent_version: str = Field("dpdpa_v1", description="Active consent terms version.")
    email: str | None = Field(None, description="Optional email for receiving deletion token.")


class ContributionCreateResponse(BaseModel):
    """Confirmation receipt returned upon voluntary contribution."""

    contribution_id: str
    contributor_key: str
    deletion_token: str
    status: str
    quarantine_reasons: list[str] | None = None
    message: str
    created_at: str


class ContributionDeleteRequest(BaseModel):
    """Credentials required to trigger operational erasure."""

    deletion_token: str | None = Field(
        None, description="Cryptographic deletion token provided at intake."
    )
    contributor_key: str | None = Field(None, description="Pseudonymous contributor UUID.")
    reason: str = Field("user_erasure_request", description="Stated reason for erasure.")


class ContributionDeleteResponse(BaseModel):
    """Confirmation receipt returned upon operational erasure purge."""

    contributor_key: str
    status: str
    records_purged_count: int
    message: str
    timestamp: str


@router.post(
    "/contributions",
    response_model=ContributionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a voluntary compensation record",
)
def create_contribution(
    payload: ContributionCreateRequest,
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> ContributionCreateResponse:
    """Registers a voluntary compensation record with unbundled consent and intake quarantine."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    submission = ContributionSubmission(
        role_family=payload.role_family,
        title_raw=payload.title_raw,
        seniority=payload.seniority,
        location=payload.location,
        years_experience=payload.years_experience,
        guaranteed_cash_annual=payload.guaranteed_cash_annual,
        currency=payload.currency,
        base_salary_annual=payload.base_salary_annual,
        variable_pay_annual=payload.variable_pay_annual,
        equity_grant_annual=payload.equity_grant_annual,
        benefits_annual=payload.benefits_annual,
        company_raw=payload.company_raw,
        company_stage=payload.company_stage,
        consent_benchmarking=payload.consent_benchmarking,
        consent_research=payload.consent_research,
        consent_future_contact=payload.consent_future_contact,
        consent_version=payload.consent_version,
        email=payload.email,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    try:
        receipt = submit_contribution(session=session, submission=submission)
    except ConsentRequiredError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err

    message = (
        "Your contribution has been received and verified."
        if receipt.status == "submitted"
        else "Your contribution was received and quarantined for manual review."
    )

    return ContributionCreateResponse(
        contribution_id=str(receipt.contribution_id),
        contributor_key=str(receipt.contributor_key),
        deletion_token=receipt.deletion_token,
        status=receipt.status,
        quarantine_reasons=receipt.quarantine_reasons,
        message=message,
        created_at=receipt.created_at.isoformat(),
    )


@router.post(
    "/contributions/delete",
    response_model=ContributionDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete voluntary contribution using deletion token",
)
def delete_contribution_by_token(
    payload: ContributionDeleteRequest,
    session: Session = Depends(get_db),  # noqa: B008
) -> ContributionDeleteResponse:
    """Permanently purges contributor records from operational stores using deletion token."""
    if not payload.deletion_token and not payload.contributor_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either deletion_token or contributor_key must be supplied.",
        )

    key_uuid: uuid.UUID | None = None
    if payload.contributor_key:
        try:
            key_uuid = uuid.UUID(payload.contributor_key)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid contributor_key format. Expected UUID.",
            ) from err

    try:
        receipt = execute_erasure(
            session=session,
            deletion_token=payload.deletion_token,
            contributor_key=key_uuid,
            reason=payload.reason,
        )
    except RecordNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err

    return ContributionDeleteResponse(
        contributor_key=str(receipt.contributor_key),
        status=receipt.status,
        records_purged_count=receipt.records_purged_count,
        message=receipt.message,
        timestamp=receipt.timestamp.isoformat(),
    )


@router.delete(
    "/me/data",
    response_model=ContributionDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete contributor data via X-Deletion-Token header (architecture.md Section 11)",
)
def delete_my_data(
    x_deletion_token: str | None = Header(None, alias="X-Deletion-Token"),
    session: Session = Depends(get_db),  # noqa: B008
) -> ContributionDeleteResponse:
    """Executes statutory erasure using token in X-Deletion-Token header."""
    if not x_deletion_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Deletion-Token header for authenticated erasure.",
        )

    try:
        receipt = execute_erasure(
            session=session,
            deletion_token=x_deletion_token,
            reason="user_header_erasure_request",
        )
    except RecordNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err

    return ContributionDeleteResponse(
        contributor_key=str(receipt.contributor_key),
        status=receipt.status,
        records_purged_count=receipt.records_purged_count,
        message=receipt.message,
        timestamp=receipt.timestamp.isoformat(),
    )
