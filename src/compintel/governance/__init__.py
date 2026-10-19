"""Governance, compliance, and privacy package (Rules R-DA-10, R-SC-08, ADR-0008).

Exports:
- SQLAlchemy ORM models: ContributorIdentity, ConsentRecord, Contribution, DeletionRequest, AuditLog
- Audit helpers: log_audit_event, hash_identifier
- Database & migration utilities: create_sync_engine, run_migrations_up,
  run_migrations_down, get_db_session
"""

from __future__ import annotations

from compintel.governance.audit import hash_identifier, log_audit_event
from compintel.governance.db import (
    create_sync_engine,
    get_alembic_config,
    get_db_session,
    get_sync_database_url,
    run_migrations_down,
    run_migrations_up,
)
from compintel.governance.models import (
    AuditLog,
    Base,
    ConsentRecord,
    Contribution,
    ContributorIdentity,
    DeletionRequest,
)

__all__ = [
    "AuditLog",
    "Base",
    "ConsentRecord",
    "Contribution",
    "ContributorIdentity",
    "DeletionRequest",
    "create_sync_engine",
    "get_alembic_config",
    "get_db_session",
    "get_sync_database_url",
    "hash_identifier",
    "log_audit_event",
    "run_migrations_down",
    "run_migrations_up",
]
