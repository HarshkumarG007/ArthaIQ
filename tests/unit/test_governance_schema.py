"""Unit tests for governance models, schema definitions, and audit helpers (T9.06, ADR-0008)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from compintel.governance.audit import hash_identifier
from compintel.governance.db import (
    create_sync_engine,
    get_alembic_config,
    get_db_session,
    get_sync_database_url,
)
from compintel.governance.models import (
    AuditLog,
    Base,
    ConsentRecord,
    Contribution,
    ContributorIdentity,
    DeletionRequest,
)


@pytest.mark.unit
def test_governance_model_table_names_and_schemas() -> None:
    """Verify that models specify appropriate tables and PostgreSQL schemas (ADR-0008)."""
    assert ContributorIdentity.__tablename__ == "contributor_identities"
    assert ContributorIdentity.__table_args__["schema"] == "identity"

    assert ConsentRecord.__tablename__ == "consent_records"
    assert ConsentRecord.__table_args__["schema"] == "app"

    assert Contribution.__tablename__ == "contributions"
    assert Contribution.__table_args__["schema"] == "app"

    assert DeletionRequest.__tablename__ == "deletion_requests"
    assert DeletionRequest.__table_args__["schema"] == "app"

    assert AuditLog.__tablename__ == "audit_log"
    assert AuditLog.__table_args__["schema"] == "app"


@pytest.mark.unit
def test_hash_identifier_properties() -> None:
    """Verify deterministic, salted hashing for sensitive identifier privacy."""
    val1 = "user@example.com"
    val2 = "USER@EXAMPLE.COM  "
    val3 = "other@example.com"

    hash1 = hash_identifier(val1)
    hash2 = hash_identifier(val2)
    hash3 = hash_identifier(val3)

    # Must normalize case and whitespace
    assert hash1 == hash2
    assert len(hash1) == 64
    # Different input yields different hash
    assert hash1 != hash3

    # Salt changes hash output
    hash_custom_salt = hash_identifier(val1, salt="custom_salt_2026")
    assert hash1 != hash_custom_salt


@pytest.mark.unit
def test_contributor_identity_instantiation() -> None:
    """Verify ContributorIdentity model initialization."""
    key = uuid.uuid4()
    ident = ContributorIdentity(
        contributor_key=key,
        email_hash="abc123hash",
        auth_provider="anonymous_token",
        status="active",
    )
    assert ident.contributor_key == key
    assert ident.email_hash == "abc123hash"
    assert ident.auth_provider == "anonymous_token"
    assert ident.status == "active"


@pytest.mark.unit
def test_consent_record_defaults() -> None:
    """Verify unbundled consent defaults to unchecked/false (Rules R-FA-01, ADR-0008)."""
    key = uuid.uuid4()
    consent = ConsentRecord(
        contributor_key=key,
        consent_version="2026-10-v1",
    )
    assert consent.purpose_compensation_benchmarking is False
    assert consent.purpose_research_aggregation is False
    assert consent.purpose_future_contact is False
    assert consent.status == "granted"


@pytest.mark.unit
def test_contribution_instantiation() -> None:
    """Verify Contribution fields and types."""
    key = uuid.uuid4()
    consent_id = uuid.uuid4()
    contrib = Contribution(
        contributor_key=key,
        consent_id=consent_id,
        role_family="software_engineer",
        title_raw="Backend Engineer",
        seniority="IC3_SENIOR",
        location="BLR",
        years_experience=Decimal("5.0"),
        currency="INR",
        guaranteed_cash_annual=Decimal("3500000.00"),
        base_salary_annual=Decimal("2800000.00"),
        variable_pay_annual=Decimal("700000.00"),
        status="submitted",
        verification_level="self_attested",
    )
    assert contrib.role_family == "software_engineer"
    assert contrib.guaranteed_cash_annual == Decimal("3500000.00")
    assert contrib.currency == "INR"
    assert contrib.status == "submitted"


@pytest.mark.unit
def test_deletion_request_defaults() -> None:
    """Verify DeletionRequest default attributes."""
    key = uuid.uuid4()
    req = DeletionRequest(contributor_key=key)
    assert req.contributor_key == key
    assert req.status == "pending"
    assert req.records_purged_count == 0


@pytest.mark.unit
def test_audit_log_instantiation() -> None:
    """Verify AuditLog fields."""
    log = AuditLog(
        event_type="TEST_EVENT",
        entity_type="contribution",
        entity_id="test-id",
        actor_role="admin",
        action="ACCESS",
        details={"ip_hash": "hash_ip"},
    )
    assert log.event_type == "TEST_EVENT"
    assert log.action == "ACCESS"
    assert log.details == {"ip_hash": "hash_ip"}


@pytest.mark.unit
def test_get_sync_database_url_drivers() -> None:
    """Verify database URL conversion for async drivers."""
    assert (
        get_sync_database_url("postgresql+asyncpg://user:pass@host:5432/db")
        == "postgresql://user:pass@host:5432/db"
    )
    assert get_sync_database_url("sqlite+aiosqlite:///local.db") == "sqlite:///local.db"
    assert get_sync_database_url("sqlite:///standard.db") == "sqlite:///standard.db"
    # None defaults to configured URL
    resolved = get_sync_database_url(None)
    assert resolved.startswith("postgresql://") or resolved.startswith("sqlite://")


@pytest.mark.unit
def test_get_alembic_config_resolution() -> None:
    """Verify Alembic config resolution with custom and default URLs."""
    cfg_custom = get_alembic_config("sqlite:///custom.db")
    assert cfg_custom.get_main_option("sqlalchemy.url") == "sqlite:///custom.db"

    cfg_default = get_alembic_config(None)
    assert cfg_default.get_main_option("sqlalchemy.url") is not None

    with (
        patch("pathlib.Path.exists", return_value=False),
        pytest.raises(FileNotFoundError, match="alembic.ini not found"),
    ):
        get_alembic_config()


@pytest.mark.unit
def test_get_db_session_rollback() -> None:
    """Verify get_db_session rolls back on exception."""
    engine = create_sync_engine(
        "sqlite:///:memory:",
        schema_translate_map={"identity": None, "app": None},
    )
    Base.metadata.create_all(engine)

    with pytest.raises(ValueError, match="Simulated failure"), get_db_session(engine) as session:
        ident = ContributorIdentity(contributor_key=uuid.uuid4(), email_hash="hash_test")
        session.add(ident)
        raise ValueError("Simulated failure")

    with get_db_session(engine) as session:
        count = len(session.query(ContributorIdentity).all())
        assert count == 0
    engine.dispose()
