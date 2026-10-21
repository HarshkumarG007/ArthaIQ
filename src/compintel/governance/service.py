"""Governance, privacy, and contribution lifecycle service (Rule R-DA-10, R-SC-08, ADR-0008).

Implements:
1. Small-cell suppression ($k_{\\min} \\ge 5$ distinct persons count per Rule R-DA-10).
2. Unbundled, versioned DPDPA 2023 consent capture (ADR-0008 Section 3).
3. Voluntary contribution intake with anomaly quarantine checks.
4. Cryptographic deletion tokens and complete operational erasure cascade.
5. Append-only immutable audit trail logging.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

from compintel.governance.audit import hash_identifier, log_audit_event
from compintel.governance.models import (
    ConsentRecord,
    Contribution,
    ContributorIdentity,
    DeletionRequest,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

K_MIN_DEFAULT = 5
MAX_EXP_YEARS = Decimal("40.0")
MIN_EXP_YEARS = Decimal("0.0")
MIN_ANNUAL_PAY_INR = Decimal("50000.00")  # 0.5 LPA
MAX_ANNUAL_PAY_INR = Decimal("500000000.00")  # 500.0 LPA


class GovernanceError(Exception):
    """Base exception for all governance and compliance errors."""

    pass


class PrivacyViolationError(GovernanceError):
    """Raised when an aggregate query violates small-cell privacy thresholds (Rule R-DA-10)."""

    pass


class ConsentRequiredError(GovernanceError):
    """Raised when mandatory unbundled consent is missing or denied (ADR-0008 Section 3)."""

    pass


class RecordNotFoundError(GovernanceError):
    """Raised when a contributor or token is not found in operational stores."""

    pass


def check_k_min(distinct_persons: int, k_min: int = K_MIN_DEFAULT) -> None:
    """Enforces small-cell suppression under Rule R-DA-10 and ADR-0008 Section 2.

    No aggregate distribution, percentile, or cohort metric is shown or exported
    if the number of distinct persons is below `k_min`. Counts persons, not rows.

    Args:
        distinct_persons: Number of distinct contributor persons in the aggregation cell.
        k_min: Minimum threshold for reporting (defaults to 5).

    Raises:
        PrivacyViolationError: If distinct_persons < k_min.
    """
    if distinct_persons < k_min:
        raise PrivacyViolationError(
            f"Small-cell aggregate suppressed: distinct persons ({distinct_persons}) "
            f"falls below privacy threshold k_min ({k_min}). Rule R-DA-10."
        )


@dataclass(frozen=True)
class ContributionSubmission:
    """Intake payload for voluntary compensation contributions (SRC-INT-VOL-01)."""

    role_family: str
    title_raw: str
    seniority: str
    location: str
    years_experience: Decimal
    guaranteed_cash_annual: Decimal
    currency: str = "INR"
    base_salary_annual: Decimal | None = None
    variable_pay_annual: Decimal | None = None
    equity_grant_annual: Decimal | None = None
    benefits_annual: Decimal | None = None
    company_raw: str | None = None
    company_stage: str | None = None
    consent_benchmarking: bool = False
    consent_research: bool = False
    consent_future_contact: bool = False
    consent_version: str = "dpdpa_v1"
    email: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class ContributionReceipt:
    """Receipt returned upon successful contribution registration."""

    contribution_id: uuid.UUID
    contributor_key: uuid.UUID
    deletion_token: str
    status: str
    quarantine_reasons: list[str] | None
    created_at: datetime


@dataclass(frozen=True)
class DeletionReceipt:
    """Receipt returned upon confirmed erasure cascade execution."""

    contributor_key: uuid.UUID
    status: str
    records_purged_count: int
    message: str
    timestamp: datetime


def submit_contribution(
    session: Session,
    submission: ContributionSubmission,
) -> ContributionReceipt:
    """Registers a voluntary contribution with unbundled consent and quarantine checks.

    Adheres strictly to:
    - ADR-0008 Section 1: Contributor identity segregated into 'identity' schema.
    - ADR-0008 Section 3: Unbundled, unchecked consent (DPDPA 2023).
    - Rule R-DA-10: Anonymized company and PII isolation.
    - Rule R-SC-08: Append-only audit logging of intake events.
    """
    # 1. Enforce unbundled consent requirement (ADR-0008 Section 3)
    if not submission.consent_benchmarking:
        raise ConsentRequiredError(
            "Explicit unbundled consent for compensation benchmarking is required "
            "to register a contribution under DPDPA 2023."
        )

    # 2. Intake Anomaly & Quarantine Checks (Rule R-DA-03)
    quarantine_reasons: list[str] = []
    if (
        submission.guaranteed_cash_annual < MIN_ANNUAL_PAY_INR
        or submission.guaranteed_cash_annual > MAX_ANNUAL_PAY_INR
    ):
        quarantine_reasons.append("OUT_OF_RANGE_PAY")

    if submission.years_experience < MIN_EXP_YEARS or submission.years_experience > MAX_EXP_YEARS:
        quarantine_reasons.append("OUT_OF_RANGE_EXPERIENCE")

    if submission.currency.upper() != "INR":
        quarantine_reasons.append("UNSUPPORTED_CURRENCY")

    status = "quarantined" if quarantine_reasons else "submitted"

    # 3. Generate Pseudonymous Key & Cryptographic Deletion Token
    contributor_key = uuid.uuid4()
    raw_token = f"del_{secrets.token_hex(16)}"
    token_digest = hash_identifier(raw_token)

    # 4. Insert ContributorIdentity into isolated 'identity' schema
    identity = ContributorIdentity(
        contributor_key=contributor_key,
        email_hash=hash_identifier(submission.email) if submission.email else None,
        email_encrypted=token_digest,  # stores salted verification digest
        auth_provider="anonymous_token",
        status="active",
    )
    session.add(identity)

    # 5. Insert ConsentRecord into 'app' schema
    ip_hash = hash_identifier(submission.ip_address) if submission.ip_address else None
    ua_hash = hash_identifier(submission.user_agent) if submission.user_agent else None

    consent = ConsentRecord(
        contributor_key=contributor_key,
        consent_version=submission.consent_version,
        purpose_compensation_benchmarking=submission.consent_benchmarking,
        purpose_research_aggregation=submission.consent_research,
        purpose_future_contact=submission.consent_future_contact,
        status="granted",
        ip_hash=ip_hash,
        user_agent_hash=ua_hash,
    )
    session.add(consent)
    session.flush()  # populate consent.id

    # 6. Insert Contribution into 'app' schema
    contribution = Contribution(
        contributor_key=contributor_key,
        consent_id=consent.id,
        role_family=submission.role_family,
        title_raw=submission.title_raw,
        seniority=submission.seniority,
        location=submission.location,
        years_experience=submission.years_experience,
        currency=submission.currency.upper(),
        guaranteed_cash_annual=submission.guaranteed_cash_annual,
        base_salary_annual=submission.base_salary_annual,
        variable_pay_annual=submission.variable_pay_annual,
        equity_grant_annual=submission.equity_grant_annual,
        benefits_annual=submission.benefits_annual,
        company_raw=submission.company_raw,
        company_stage=submission.company_stage,
        status=status,
        quarantine_reasons=quarantine_reasons if quarantine_reasons else None,
    )
    session.add(contribution)
    session.flush()

    # 7. Write Append-Only Audit Trail (Rule R-SC-08)
    log_audit_event(
        session=session,
        event_type="CONTRIBUTION_SUBMITTED",
        entity_type="contribution",
        entity_id=contribution.id,
        actor_role="contributor",
        action="CREATE",
        actor_id=contributor_key,
        details={
            "status": status,
            "role_family": submission.role_family,
            "location": submission.location,
            "quarantine_reasons": quarantine_reasons,
            "ip_hash": ip_hash,
        },
    )

    session.commit()

    return ContributionReceipt(
        contribution_id=contribution.id,
        contributor_key=contributor_key,
        deletion_token=raw_token,
        status=status,
        quarantine_reasons=quarantine_reasons if quarantine_reasons else None,
        created_at=contribution.created_at,
    )


def execute_erasure(
    session: Session,
    deletion_token: str | None = None,
    contributor_key: uuid.UUID | None = None,
    reason: str = "user_erasure_request",
) -> DeletionReceipt:
    """Executes statutory erasure cascading across operational stores (PRD US-07, ADR-0008).

    Guarantees:
    1. Operational contribution records are permanently removed from `app.contributions`.
    2. Consent is revoked and timestamped in `app.consent_records`.
    3. Contributor identity handles and hashes are scrubbed in `identity.contributor_identities`.
    4. Erasure request is formally documented in `app.deletion_requests`.
    5. Immutable audit entry is appended to `app.audit_log`.

    Args:
        session: Active SQLAlchemy session.
        deletion_token: Plaintext deletion token supplied by user.
        contributor_key: Optional direct contributor UUID.
        reason: Stated reason for erasure.

    Returns:
        DeletionReceipt confirming complete operational purge.

    Raises:
        RecordNotFoundError: If contributor or token does not exist in operational stores.
    """
    resolved_key: uuid.UUID | None = None

    if deletion_token:
        token_digest = hash_identifier(deletion_token)
        identity = session.scalar(
            select(ContributorIdentity).where(
                ContributorIdentity.email_encrypted == token_digest,
                ContributorIdentity.status != "deleted",
            )
        )
        if identity:
            resolved_key = identity.contributor_key
    elif contributor_key:
        identity = session.scalar(
            select(ContributorIdentity).where(
                ContributorIdentity.contributor_key == contributor_key,
                ContributorIdentity.status != "deleted",
            )
        )
        if identity:
            resolved_key = identity.contributor_key

    if not resolved_key or not identity:
        raise RecordNotFoundError(
            "No active contributor record was found matching the provided deletion credentials."
        )

    # 1. Count and purge operational contribution records
    contributions = session.scalars(
        select(Contribution).where(Contribution.contributor_key == resolved_key)
    ).all()
    records_count = len(contributions)

    session.execute(delete(Contribution).where(Contribution.contributor_key == resolved_key))

    # 2. Revoke consent records
    now_utc = datetime.now(UTC)
    session.execute(
        update(ConsentRecord)
        .where(ConsentRecord.contributor_key == resolved_key)
        .values(
            status="withdrawn",
            withdrawn_at=now_utc,
        )
    )

    # 3. Cryptographically shred identity record
    identity.status = "deleted"
    identity.email_hash = None
    identity.email_encrypted = None

    # 4. Record compliance deletion request
    del_request = DeletionRequest(
        contributor_key=resolved_key,
        status="completed",
        completed_at=now_utc,
        reason=reason,
        records_purged_count=records_count,
    )
    session.add(del_request)

    # 5. Append-only immutable audit trail (Rule R-SC-08)
    log_audit_event(
        session=session,
        event_type="CONTRIBUTION_ERASED",
        entity_type="contributor_identity",
        entity_id=resolved_key,
        actor_role="contributor",
        action="DELETE",
        actor_id=resolved_key,
        details={
            "records_purged_count": records_count,
            "reason": reason,
        },
    )

    session.commit()

    return DeletionReceipt(
        contributor_key=resolved_key,
        status="completed",
        records_purged_count=records_count,
        message=(
            "Your record is permanently removed from operational stores. "
            "Statistics that included it update at the next data refresh."
        ),
        timestamp=now_utc,
    )
