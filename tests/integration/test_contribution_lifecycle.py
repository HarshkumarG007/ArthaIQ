"""Integration tests for contribution lifecycle, consent, quarantine, k_min, and erasure (T9.10a).

Covers ADR-0008 invariants: small-cell suppression (R-DA-10), operational erasure proof,
REST endpoint round-trips, and unbundled consent enforcement.
"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from compintel.governance.db import create_sync_engine, get_db
from compintel.governance.models import (
    AuditLog,
    Base,
    ConsentRecord,
    Contribution,
    ContributorIdentity,
    DeletionRequest,
)
from compintel.governance.router import router as governance_router
from compintel.governance.service import (
    ConsentRequiredError,
    ContributionSubmission,
    PrivacyViolationError,
    RecordNotFoundError,
    check_k_min,
    execute_erasure,
    submit_contribution,
)


@pytest.fixture
def sync_db_session() -> Generator[Session, None, None]:
    """Creates an isolated in-memory SQLite database session with translated schemas."""
    engine = create_sync_engine(
        "sqlite:///:memory:",
        schema_translate_map={"identity": None, "app": None},
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def test_client(sync_db_session: Session) -> TestClient:
    """Creates a FastAPI test client wired to the isolated database session."""
    app = FastAPI(title="Governance Test API")
    app.include_router(governance_router)

    def override_get_db() -> Generator[Session, None, None]:
        yield sync_db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. k_min Small-Cell Suppression Tests (Rule R-DA-10, ADR-0008 Section 2)
# -----------------------------------------------------------------------------
@pytest.mark.integration
def test_check_k_min_enforcement() -> None:
    """Verifies that queries with fewer than k_min distinct persons raise PrivacyViolationError."""
    # N >= 5 must pass
    check_k_min(distinct_persons=5, k_min=5)
    check_k_min(distinct_persons=10, k_min=5)
    check_k_min(distinct_persons=142, k_min=5)

    # N < 5 must raise PrivacyViolationError
    with pytest.raises(PrivacyViolationError, match="Small-cell aggregate suppressed"):
        check_k_min(distinct_persons=4, k_min=5)

    with pytest.raises(PrivacyViolationError):
        check_k_min(distinct_persons=1, k_min=5)

    with pytest.raises(PrivacyViolationError):
        check_k_min(distinct_persons=0, k_min=5)


# -----------------------------------------------------------------------------
# 2. Service-Layer Contribution Intake & Consent Tests (ADR-0008 Section 3)
# -----------------------------------------------------------------------------
@pytest.mark.integration
def test_submit_contribution_requires_unbundled_consent(sync_db_session: Session) -> None:
    """Verifies that contribution without explicit benchmarking consent is rejected."""
    submission = ContributionSubmission(
        role_family="software_engineer",
        title_raw="Backend Engineer",
        seniority="IC3_SENIOR",
        location="BLR",
        years_experience=Decimal("4.5"),
        guaranteed_cash_annual=Decimal("3500000.00"),
        consent_benchmarking=False,  # Unchecked consent
    )

    with pytest.raises(ConsentRequiredError, match="Explicit unbundled consent"):
        submit_contribution(sync_db_session, submission)


@pytest.mark.integration
def test_submit_contribution_intake_and_quarantine(sync_db_session: Session) -> None:
    """Verifies normal intake and anomaly quarantine flagging."""
    # 1. Normal valid contribution
    valid_sub = ContributionSubmission(
        role_family="software_engineer",
        title_raw="Senior Staff Engineer",
        seniority="IC4_STAFF",
        location="BLR",
        years_experience=Decimal("8.0"),
        guaranteed_cash_annual=Decimal("6500000.00"),
        consent_benchmarking=True,
        email="contributor@example.com",
    )
    receipt = submit_contribution(sync_db_session, valid_sub)
    assert receipt.status == "submitted"
    assert receipt.quarantine_reasons is None
    assert receipt.deletion_token.startswith("del_")

    # Verify database persistence
    db_contrib = sync_db_session.scalar(
        select(Contribution).where(Contribution.id == receipt.contribution_id)
    )
    assert db_contrib is not None
    assert db_contrib.guaranteed_cash_annual == Decimal("6500000.00")
    assert db_contrib.status == "submitted"

    # Verify audit log entry
    audit = sync_db_session.scalar(
        select(AuditLog).where(AuditLog.actor_id == str(receipt.contributor_key))
    )
    assert audit is not None
    assert audit.event_type == "CONTRIBUTION_SUBMITTED"
    assert audit.action == "CREATE"

    # 2. Anomaly contribution: Pay out of range (< 50,000 INR)
    anom_sub = ContributionSubmission(
        role_family="software_engineer",
        title_raw="Intern",
        seniority="IC1_ENTRY",
        location="BLR",
        years_experience=Decimal("0.5"),
        guaranteed_cash_annual=Decimal("15000.00"),  # Out of range
        consent_benchmarking=True,
    )
    anom_receipt = submit_contribution(sync_db_session, anom_sub)
    assert anom_receipt.status == "quarantined"
    assert anom_receipt.quarantine_reasons == ["OUT_OF_RANGE_PAY"]


# -----------------------------------------------------------------------------
# 3. Operational Store Erasure Cascade Tests (ADR-0008 Section 4, PRD US-07)
# -----------------------------------------------------------------------------
@pytest.mark.integration
def test_execute_operational_erasure_cascade(sync_db_session: Session) -> None:
    """Verifies that deletion permanently deletes the record from operational stores.

    CRITICAL ACCEPTANCE CRITERIA FOR T9.10:
    "Done when: deletion removes the record from operational stores in a test."
    """
    sub = ContributionSubmission(
        role_family="data_scientist",
        title_raw="Lead Data Scientist",
        seniority="IC3_SENIOR",
        location="HYD",
        years_experience=Decimal("6.0"),
        guaranteed_cash_annual=Decimal("4200000.00"),
        consent_benchmarking=True,
        email="test_erasure@example.com",
    )
    receipt = submit_contribution(sync_db_session, sub)
    contributor_key = receipt.contributor_key
    deletion_token = receipt.deletion_token

    # Verify record is in operational store
    assert (
        sync_db_session.scalar(
            select(Contribution).where(Contribution.contributor_key == contributor_key)
        )
        is not None
    )

    # Execute operational erasure via deletion token
    del_receipt = execute_erasure(
        session=sync_db_session,
        deletion_token=deletion_token,
        reason="user_self_erasure",
    )
    assert del_receipt.status == "completed"
    assert del_receipt.records_purged_count == 1

    # PROOF 1: Contribution record is PERMANENTLY REMOVED from operational store
    operational_record = sync_db_session.scalar(
        select(Contribution).where(Contribution.contributor_key == contributor_key)
    )
    assert operational_record is None, "Operational contribution record must be completely deleted!"

    # PROOF 2: Consent is marked withdrawn
    consent = sync_db_session.scalar(
        select(ConsentRecord).where(ConsentRecord.contributor_key == contributor_key)
    )
    assert consent is not None
    assert consent.status == "withdrawn"
    assert consent.withdrawn_at is not None

    # PROOF 3: Identity is scrubbed
    identity = sync_db_session.scalar(
        select(ContributorIdentity).where(ContributorIdentity.contributor_key == contributor_key)
    )
    assert identity is not None
    assert identity.status == "deleted"
    assert identity.email_hash is None
    assert identity.email_encrypted is None

    # PROOF 4: Deletion request is documented
    req = sync_db_session.scalar(
        select(DeletionRequest).where(DeletionRequest.contributor_key == contributor_key)
    )
    assert req is not None
    assert req.status == "completed"
    assert req.records_purged_count == 1

    # PROOF 5: Audit log records erasure
    erasure_audit = sync_db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_id == str(contributor_key),
            AuditLog.event_type == "CONTRIBUTION_ERASED",
        )
    )
    assert erasure_audit is not None
    assert erasure_audit.action == "DELETE"

    # Re-executing deletion on already-deleted record raises RecordNotFoundError
    with pytest.raises(RecordNotFoundError):
        execute_erasure(sync_db_session, deletion_token=deletion_token)


# -----------------------------------------------------------------------------
# 4. REST API Endpoint Tests (POST /v1/contributions & DELETE /v1/me/data)
# -----------------------------------------------------------------------------
@pytest.mark.integration
def test_rest_api_contribution_and_deletion_flow(test_client: TestClient) -> None:
    """Verifies end-to-end REST API contribution and deletion endpoints."""
    # 1. Missing consent returns 422
    res_no_consent = test_client.post(
        "/v1/contributions",
        json={
            "role_family": "software_engineer",
            "title_raw": "DevOps Engineer",
            "seniority": "IC2_MID",
            "location": "PUN",
            "years_experience": 3.0,
            "guaranteed_cash_annual": 2500000.0,
            "consent_benchmarking": False,
        },
    )
    assert res_no_consent.status_code == 422

    # 2. Valid contribution returns 201 Created
    res_valid = test_client.post(
        "/v1/contributions",
        json={
            "role_family": "software_engineer",
            "title_raw": "DevOps Engineer",
            "seniority": "IC2_MID",
            "location": "PUN",
            "years_experience": 3.0,
            "guaranteed_cash_annual": 2500000.0,
            "consent_benchmarking": True,
            "consent_research": True,
        },
    )
    assert res_valid.status_code == 201
    data = res_valid.json()
    assert data["status"] == "submitted"
    assert "deletion_token" in data
    token = data["deletion_token"]

    # 3. Delete via header endpoint (DELETE /v1/me/data per architecture.md Section 11)
    res_delete = test_client.delete(
        "/v1/me/data",
        headers={"X-Deletion-Token": token},
    )
    assert res_delete.status_code == 200
    del_data = res_delete.json()
    assert del_data["status"] == "completed"
    assert del_data["records_purged_count"] == 1

    # 4. Second attempt with now-purged token returns 404
    res_retry = test_client.delete(
        "/v1/me/data",
        headers={"X-Deletion-Token": token},
    )
    assert res_retry.status_code == 404
