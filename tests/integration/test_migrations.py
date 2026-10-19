"""Integration tests for database migrations and governance schema (T9.06, ADR-0008).

Verifies:
1. Full up -> down -> up migration lifecycle execution via Alembic
2. Offline PostgreSQL static DDL generation for CI verification
3. Schema separation between identity and application tables
4. Referential integrity and foreign key constraints
5. Privacy-preserving consent and pseudonymous contribution lifecycle
6. Erasure request and audit log append-only tracking (PRD US-07, Rule R-SC-08)
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from compintel.governance.audit import hash_identifier, log_audit_event
from compintel.governance.db import (
    create_sync_engine,
    get_db_session,
    run_migrations_down,
    run_migrations_up,
)
from compintel.governance.models import (
    AuditLog,
    ConsentRecord,
    Contribution,
    ContributorIdentity,
    DeletionRequest,
)


@pytest.fixture
def temp_sqlite_db() -> str:
    """Provide a path to a temporary SQLite database for migration testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    url = f"sqlite:///{db_path}"
    yield url
    # Clean up file after test with safe error handling on Windows
    with contextlib.suppress(PermissionError):
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.integration
def test_migration_up_and_down_lifecycle(temp_sqlite_db: str) -> None:
    """Verify that up and down migrations run cleanly in a full cycle (Task T9.06)."""
    # 1. Initial upgrade to head
    run_migrations_up(temp_sqlite_db, revision="head")

    engine = create_sync_engine(temp_sqlite_db)
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        expected_tables = {
            "alembic_version",
            "contributor_identities",
            "consent_records",
            "contributions",
            "deletion_requests",
            "audit_log",
        }
        missing = expected_tables - set(table_names)
        assert expected_tables.issubset(set(table_names)), f"Missing tables: {missing}"

        # 2. Downgrade back to base
        run_migrations_down(temp_sqlite_db, revision="base")

        inspector_after_down = inspect(engine)
        remaining_tables = set(inspector_after_down.get_table_names())
        governance_tables = {
            "contributor_identities",
            "consent_records",
            "contributions",
            "deletion_requests",
            "audit_log",
        }
        surviving = governance_tables & remaining_tables
        assert governance_tables.isdisjoint(remaining_tables), f"Tables not dropped: {surviving}"

        # 3. Upgrade back to head to confirm idempotency
        run_migrations_up(temp_sqlite_db, revision="head")
        inspector_after_reup = inspect(engine)
        recreated_tables = set(inspector_after_reup.get_table_names())
        assert expected_tables.issubset(recreated_tables)
    finally:
        engine.dispose()


@pytest.mark.integration
def test_offline_postgresql_ddl_generation() -> None:
    """Verify offline static SQL generation produces valid PostgreSQL DDL with schemas."""
    # Run alembic upgrade head --sql
    result_up = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        capture_output=True,
        text=True,
        check=True,
    )
    sql_up = result_up.stdout

    # Verify PostgreSQL schemas and tables in upgrade script
    assert "CREATE SCHEMA IF NOT EXISTS identity;" in sql_up
    assert "CREATE SCHEMA IF NOT EXISTS app;" in sql_up
    assert "CREATE TABLE identity.contributor_identities" in sql_up
    assert "CREATE TABLE app.consent_records" in sql_up
    assert "CREATE TABLE app.contributions" in sql_up
    assert "CREATE TABLE app.deletion_requests" in sql_up
    assert "CREATE TABLE app.audit_log" in sql_up
    assert "REFERENCES app.consent_records (id)" in sql_up

    # Run alembic downgrade base --sql
    result_down = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "0001_initial_governance:base", "--sql"],
        capture_output=True,
        text=True,
        check=True,
    )
    sql_down = result_down.stdout

    # Verify reverse drop order in downgrade script
    assert "DROP TABLE app.audit_log;" in sql_down
    assert "DROP TABLE app.deletion_requests;" in sql_down
    assert "DROP TABLE app.contributions;" in sql_down
    assert "DROP TABLE app.consent_records;" in sql_down
    assert "DROP TABLE identity.contributor_identities;" in sql_down
    assert "DROP SCHEMA IF EXISTS app CASCADE;" in sql_down
    assert "DROP SCHEMA IF EXISTS identity CASCADE;" in sql_down


@pytest.mark.integration
def test_governance_data_integrity_and_identity_separation(temp_sqlite_db: str) -> None:
    """Verify relational integrity, identity separation, and audit logging (ADR-0008, R-SC-08)."""
    run_migrations_up(temp_sqlite_db, revision="head")
    schema_map = {"identity": None, "app": None}
    engine = create_sync_engine(temp_sqlite_db, schema_translate_map=schema_map)

    contributor_key = uuid.uuid4()
    email_plain = "engineer@example.com"
    email_hash = hash_identifier(email_plain)

    try:
        with get_db_session(engine) as session:
            # 1. Register identity in isolated store
            identity = ContributorIdentity(
                contributor_key=contributor_key,
                email_hash=email_hash,
                auth_provider="email_otp",
                status="active",
            )
            session.add(identity)

            # 2. Record unbundled consent
            consent = ConsentRecord(
                contributor_key=contributor_key,
                consent_version="2026-10-v1",
                purpose_compensation_benchmarking=True,
                purpose_research_aggregation=True,
                purpose_future_contact=False,
                status="granted",
                ip_hash=hash_identifier("127.0.0.1"),
                user_agent_hash=hash_identifier("Mozilla/5.0"),
            )
            session.add(consent)
            session.flush()

            # Log audit trail for consent grant
            log_audit_event(
                session,
                event_type="CONSENT_GRANTED",
                entity_type="consent",
                entity_id=consent.id,
                actor_role="contributor",
                action="INSERT",
                actor_id=contributor_key,
                details={"consent_version": "2026-10-v1", "purposes": ["benchmarking", "research"]},
            )

            # 3. Add voluntary compensation contribution
            contribution = Contribution(
                contributor_key=contributor_key,
                consent_id=consent.id,
                role_family="software_engineer",
                title_raw="Senior Staff Software Engineer",
                seniority="IC4_STAFF",
                location="BLR",
                years_experience=Decimal("8.5"),
                company_raw="Fintech Unicorn",
                company_stage="growth",
                currency="INR",
                guaranteed_cash_annual=Decimal("5200000.00"),
                base_salary_annual=Decimal("4200000.00"),
                variable_pay_annual=Decimal("1000000.00"),
                status="submitted",
                verification_level="self_attested",
            )
            session.add(contribution)
            session.flush()

            # Log audit trail for contribution submission
            log_audit_event(
                session,
                event_type="CONTRIBUTION_CREATED",
                entity_type="contribution",
                entity_id=contribution.id,
                actor_role="contributor",
                action="INSERT",
                actor_id=contributor_key,
                details={"role": "software_engineer", "location": "BLR", "seniority": "IC4_STAFF"},
            )

        # 4. Verify data in new session
        with get_db_session(engine) as session:
            # Check identity
            fetched_identity = session.scalars(
                select(ContributorIdentity).where(
                    ContributorIdentity.contributor_key == contributor_key
                )
            ).one()
            assert fetched_identity.email_hash == email_hash

            # Check contribution has NO email or personal identifier
            fetched_contrib = session.scalars(
                select(Contribution).where(Contribution.contributor_key == contributor_key)
            ).one()
            assert fetched_contrib.role_family == "software_engineer"
            assert fetched_contrib.guaranteed_cash_annual == Decimal("5200000.00")
            assert not hasattr(fetched_contrib, "email")
            assert not hasattr(fetched_contrib, "email_hash")

            # Check audit log entries exist
            audit_events = list(session.scalars(select(AuditLog).order_by(AuditLog.id)).all())
            assert len(audit_events) == 2
            assert audit_events[0].event_type == "CONSENT_GRANTED"
            assert audit_events[1].event_type == "CONTRIBUTION_CREATED"
    finally:
        engine.dispose()


@pytest.mark.integration
def test_erasure_request_workflow(temp_sqlite_db: str) -> None:
    """Verify deletion request tracking and purge cascade (PRD US-07, ADR-0008)."""
    run_migrations_up(temp_sqlite_db, revision="head")
    schema_map = {"identity": None, "app": None}
    engine = create_sync_engine(temp_sqlite_db, schema_translate_map=schema_map)

    contributor_key = uuid.uuid4()

    try:
        with get_db_session(engine) as session:
            identity = ContributorIdentity(contributor_key=contributor_key, email_hash="hash123")
            session.add(identity)

            consent = ConsentRecord(
                contributor_key=contributor_key,
                consent_version="2026-10-v1",
                purpose_compensation_benchmarking=True,
            )
            session.add(consent)
            session.flush()

            contrib = Contribution(
                contributor_key=contributor_key,
                consent_id=consent.id,
                role_family="data_scientist",
                title_raw="Data Scientist",
                seniority="IC2_MID",
                location="HYD",
                years_experience=Decimal("3.0"),
                currency="INR",
                guaranteed_cash_annual=Decimal("1800000.00"),
            )
            session.add(contrib)

        # Contributor submits deletion request
        with get_db_session(engine) as session:
            deletion = DeletionRequest(
                contributor_key=contributor_key,
                status="pending",
                reason="User requested account erasure under privacy terms",
            )
            session.add(deletion)
            session.flush()

            log_audit_event(
                session,
                event_type="DELETION_REQUESTED",
                entity_type="deletion_request",
                entity_id=deletion.id,
                actor_role="contributor",
                action="INSERT",
                actor_id=contributor_key,
            )

            # Simulate deletion execution
            contrib_to_delete = session.scalars(
                select(Contribution).where(Contribution.contributor_key == contributor_key)
            ).all()
            purged_count = len(contrib_to_delete)
            for c in contrib_to_delete:
                session.delete(c)

            # Update deletion status
            deletion.status = "completed"
            deletion.records_purged_count = purged_count

            log_audit_event(
                session,
                event_type="DELETION_EXECUTED",
                entity_type="deletion_request",
                entity_id=deletion.id,
                actor_role="system",
                action="PURGE",
                details={"purged_contributions": purged_count},
            )

        # Verify contribution is gone from operational store
        with get_db_session(engine) as session:
            remaining = session.scalars(
                select(Contribution).where(Contribution.contributor_key == contributor_key)
            ).all()
            assert len(remaining) == 0

            audit_purge = session.scalars(
                select(AuditLog).where(AuditLog.event_type == "DELETION_EXECUTED")
            ).one()
            assert audit_purge.details["purged_contributions"] == 1
    finally:
        engine.dispose()
