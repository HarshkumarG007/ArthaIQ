"""Governance and compliance relational database models (Rule R-DA-10, ADR-0008).

Defines SQLAlchemy ORM models for:
1. ContributorIdentity (schema: identity) - segregated identity storage
2. ConsentRecord (schema: app) - unbundled, versioned, timestamped consent
3. Contribution (schema: app) - voluntary pay submissions with pseudonymous key
4. DeletionRequest (schema: app) - erasure workflow tracking (PRD US-07)
5. AuditLog (schema: app) - append-only immutable audit trail (Rule R-SC-08)

Strictly adheres to identity separation: the contributor identity is stored
apart from pay records, linked only via the pseudonymous contributor_key.
Serving and pipeline database roles have no access to the identity schema.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base class for all CompIntel governance tables."""

    pass


class ContributorIdentity(Base):
    """Segregated contributor identity store (ADR-0008 Section 1).

    Resides in the isolated 'identity' schema. The serving role has NO access
    to this schema. Contributor identities are linked to compensation records
    solely through the pseudonymous `contributor_key`.
    """

    __tablename__ = "contributor_identities"
    __table_args__ = {"schema": "identity"}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Internal primary key.",
    )
    contributor_key: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        index=True,
        nullable=False,
        default=uuid.uuid4,
        doc="Pseudonymous key exposed to other tables and services.",
    )
    email_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Salted SHA-256 hash of normalized email for deduplication.",
    )
    email_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Encrypted contact handle for deletion tokens (optional).",
    )
    auth_provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="anonymous_token",
        doc="Authentication provider or token type.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        doc="Identity state: 'active', 'suspended', 'deleted'.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="UTC registration timestamp.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="UTC last update timestamp.",
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("auth_provider", "anonymous_token")
        kwargs.setdefault("status", "active")
        super().__init__(**kwargs)


class ConsentRecord(Base):
    """Unbundled, versioned, timestamped consent record (ADR-0008 Section 3).

    Stores explicit consent checkboxes (unchecked by default per design.md),
    the active consent version, and client verification hashes.
    """

    __tablename__ = "consent_records"
    __table_args__ = {"schema": "app"}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Consent record unique identifier.",
    )
    contributor_key: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
        doc="Pseudonymous contributor key.",
    )
    consent_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Consent terms version, e.g., '2026-10-v1'.",
    )
    purpose_compensation_benchmarking: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Consent to benchmark compensation and publish aggregate cohort distributions.",
    )
    purpose_research_aggregation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Consent to include record in research and macroeconomic analyses.",
    )
    purpose_future_contact: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Consent to receive longitudinal compensation update prompts.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="granted",
        doc="Status: 'granted', 'withdrawn'.",
    )
    ip_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Salted SHA-256 hash of client IP for consent audit proof.",
    )
    user_agent_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Salted SHA-256 hash of client User-Agent.",
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="UTC timestamp when consent was granted.",
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when consent was withdrawn (if applicable).",
    )
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Scheduled data retention expiration date.",
    )

    # Relationships
    contributions: Mapped[list[Contribution]] = relationship(
        "Contribution",
        back_populates="consent",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("purpose_compensation_benchmarking", False)
        kwargs.setdefault("purpose_research_aggregation", False)
        kwargs.setdefault("purpose_future_contact", False)
        kwargs.setdefault("status", "granted")
        super().__init__(**kwargs)


class Contribution(Base):
    """Voluntary compensation contribution record (ADR-0008, SRC-INT-VOL-01).

    Carries the pseudonymous `contributor_key`, canonicalized job context,
    itemized compensation components, and intake quarantine status.
    """

    __tablename__ = "contributions"
    __table_args__ = {"schema": "app"}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique contribution observation ID.",
    )
    contributor_key: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
        doc="Pseudonymous key linking to identity schema.",
    )
    consent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("app.consent_records.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Reference to corresponding granted consent record.",
    )
    schema_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="1.0.0",
        doc="Contribution payload schema version.",
    )
    role_family: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Canonical role family: 'software_engineer', 'data_scientist', etc.",
    )
    title_raw: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Raw user-submitted job title.",
    )
    seniority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Canonical seniority tier: 'IC1_ENTRY' to 'M2_DIRECTOR'.",
    )
    location: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Canonical metro location: 'BLR', 'HYD', 'NCR', 'PUN', 'MUM', 'CHE'.",
    )
    years_experience: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        nullable=False,
        doc="Years of professional technology experience.",
    )
    company_raw: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        doc="Raw employer name (quarantined/anonymized per Rule R-DA-10).",
    )
    company_stage: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        doc="Company stage: 'early_stage', 'growth', 'public_tech', 'it_services'.",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        doc="Currency code (strictly 'INR' for Phase 9).",
    )
    guaranteed_cash_annual: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Target PT1: Contractual guaranteed annual cash compensation in nominal INR.",
    )
    base_salary_annual: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Statutory basic pay portion.",
    )
    variable_pay_annual: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Target annual incentive / variable performance bonus.",
    )
    equity_grant_annual: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Annualized equity / RSU grant value.",
    )
    benefits_annual: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Statutory retiral / EPF / gratuity benefits.",
    )
    career_start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        doc="Optional date contributor began professional technology career (ADR-0008).",
    )
    last_promotion_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        doc="Optional date of contributor's last level change or promotion (ADR-0008).",
    )
    right_censored_exit_flag: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        doc="Optional flag: True if record marks role exit, False/None if continuing.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="submitted",
        index=True,
        doc="Lifecycle state: 'submitted', 'quarantined', 'verified', 'canonicalized', 'deleted'.",
    )
    quarantine_reasons: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Array of quarantine reason codes if flagged during intake.",
    )
    verification_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="self_attested",
        doc="Verification status: 'self_attested', 'payslip_redacted', 'corporate_email_verified'.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="UTC intake submission timestamp.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="UTC last updated timestamp.",
    )

    # Relationships
    consent: Mapped[ConsentRecord] = relationship(
        "ConsentRecord",
        back_populates="contributions",
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("currency", "INR")
        kwargs.setdefault("status", "submitted")
        kwargs.setdefault("schema_version", "1.0.0")
        kwargs.setdefault("verification_level", "self_attested")
        super().__init__(**kwargs)


class DeletionRequest(Base):
    """Contributor erasure request tracking (PRD US-07, ADR-0008 Section 4).

    Coordinates the cascading deletion of voluntary records from operational
    stores within the statutory compliance window.
    """

    __tablename__ = "deletion_requests"
    __table_args__ = {"schema": "app"}

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique deletion request tracking identifier.",
    )
    contributor_key: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
        doc="Pseudonymous contributor key requesting erasure.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        doc="Status: 'pending', 'processing', 'completed', 'rejected'.",
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="UTC timestamp when erasure was requested.",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when erasure cascade was executed.",
    )
    reason: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        doc="Optional user-provided reason for erasure.",
    )
    records_purged_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total contribution and consent records purged.",
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", "pending")
        kwargs.setdefault("records_purged_count", 0)
        super().__init__(**kwargs)


class AuditLog(Base):
    """Append-only immutable audit trail (Rule R-SC-08, architecture.md Section 12).

    Records every sensitive administrative action, consent grant/withdrawal,
    contribution submission, deletion cascade, and restricted data query.
    """

    __tablename__ = "audit_log"
    __table_args__ = {"schema": "app"}

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        doc="Monotonically increasing sequence identifier.",
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Event code: 'CONSENT_GRANTED', 'CONTRIBUTION_CREATED', 'DELETION_REQUESTED', etc.",
    )
    entity_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Entity type: 'identity', 'consent', 'contribution', 'deletion_request'.",
    )
    entity_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="UUID string of affected primary entity.",
    )
    actor_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Role performing action: 'contributor', 'admin', 'pipeline', 'serving', 'system'.",
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Actor identifier or pseudonymous key.",
    )
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Operation: 'INSERT', 'UPDATE', 'SOFT_DELETE', 'PURGE', 'ACCESS'.",
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Structured change details, IP hash, user agent hash, and audit metadata.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="UTC append-only timestamp.",
    )
