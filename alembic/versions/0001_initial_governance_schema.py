"""Initial governance and compliance schema migration (Rule R-DA-10, ADR-0008).

Revision ID: 0001_initial_governance
Revises: None
Create Date: 2026-10-19

Creates:
1. Schemas: 'identity' and 'app' (PostgreSQL native multi-schema)
2. Table: identity.contributor_identities (segregated identity store)
3. Table: app.consent_records (unbundled, versioned, timestamped consent)
4. Table: app.contributions (voluntary pay records with pseudonymous key)
5. Table: app.deletion_requests (erasure tracking per PRD US-07)
6. Table: app.audit_log (append-only immutable audit trail per Rule R-SC-08)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_governance"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Create isolated schemas in PostgreSQL
    if is_postgres:
        op.execute("CREATE SCHEMA IF NOT EXISTS identity")
        op.execute("CREATE SCHEMA IF NOT EXISTS app")

    schema_identity = "identity" if is_postgres else None
    schema_app = "app" if is_postgres else None
    consent_table_ref = "app.consent_records.id" if is_postgres else "consent_records.id"

    # 2. Table: identity.contributor_identities
    op.create_table(
        "contributor_identities",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contributor_key", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email_hash", sa.String(length=64), nullable=True),
        sa.Column("email_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "auth_provider", sa.String(length=32), nullable=False, server_default="anonymous_token"
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema=schema_identity,
    )
    op.create_index(
        "ix_contributor_identities_key",
        "contributor_identities",
        ["contributor_key"],
        unique=True,
        schema=schema_identity,
    )
    op.create_index(
        "ix_contributor_identities_email_hash",
        "contributor_identities",
        ["email_hash"],
        unique=False,
        schema=schema_identity,
    )

    # 3. Table: app.consent_records
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contributor_key", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("consent_version", sa.String(length=32), nullable=False),
        sa.Column(
            "purpose_compensation_benchmarking",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "purpose_research_aggregation", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "purpose_future_contact", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="granted"),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
        schema=schema_app,
    )
    op.create_index(
        "ix_consent_records_contributor_key",
        "consent_records",
        ["contributor_key"],
        unique=False,
        schema=schema_app,
    )

    # 4. Table: app.contributions
    op.create_table(
        "contributions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contributor_key", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("consent_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False, server_default="1.0.0"),
        sa.Column("role_family", sa.String(length=64), nullable=False),
        sa.Column("title_raw", sa.String(length=128), nullable=False),
        sa.Column("seniority", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=64), nullable=False),
        sa.Column("years_experience", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column("company_raw", sa.String(length=128), nullable=True),
        sa.Column("company_stage", sa.String(length=32), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("guaranteed_cash_annual", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("base_salary_annual", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("variable_pay_annual", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("equity_grant_annual", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("benefits_annual", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="submitted"),
        sa.Column("quarantine_reasons", sa.JSON(), nullable=True),
        sa.Column(
            "verification_level",
            sa.String(length=32),
            nullable=False,
            server_default="self_attested",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["consent_id"], [consent_table_ref], ondelete="RESTRICT"),
        schema=schema_app,
    )
    op.create_index(
        "ix_contributions_contributor_key",
        "contributions",
        ["contributor_key"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_contributions_role_family",
        "contributions",
        ["role_family"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_contributions_seniority",
        "contributions",
        ["seniority"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_contributions_location",
        "contributions",
        ["location"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_contributions_status",
        "contributions",
        ["status"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_contributions_created_at",
        "contributions",
        ["created_at"],
        unique=False,
        schema=schema_app,
    )

    # 5. Table: app.deletion_requests
    op.create_table(
        "deletion_requests",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contributor_key", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("records_purged_count", sa.Integer(), nullable=False, server_default="0"),
        schema=schema_app,
    )
    op.create_index(
        "ix_deletion_requests_contributor_key",
        "deletion_requests",
        ["contributor_key"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_deletion_requests_status",
        "deletion_requests",
        ["status"],
        unique=False,
        schema=schema_app,
    )

    # 6. Table: app.audit_log
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema=schema_app,
    )
    op.create_index(
        "ix_audit_log_event_type",
        "audit_log",
        ["event_type"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_audit_log_entity_type",
        "audit_log",
        ["entity_type"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_audit_log_entity_id",
        "audit_log",
        ["entity_id"],
        unique=False,
        schema=schema_app,
    )
    op.create_index(
        "ix_audit_log_created_at",
        "audit_log",
        ["created_at"],
        unique=False,
        schema=schema_app,
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    schema_identity = "identity" if is_postgres else None
    schema_app = "app" if is_postgres else None

    # Drop tables in reverse dependency order
    op.drop_table("audit_log", schema=schema_app)
    op.drop_table("deletion_requests", schema=schema_app)
    op.drop_table("contributions", schema=schema_app)
    op.drop_table("consent_records", schema=schema_app)
    op.drop_table("contributor_identities", schema=schema_identity)

    # Drop schemas in PostgreSQL
    if is_postgres:
        op.execute("DROP SCHEMA IF EXISTS app CASCADE")
        op.execute("DROP SCHEMA IF EXISTS identity CASCADE")
