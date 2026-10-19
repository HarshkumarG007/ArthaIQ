"""Audit logging and privacy hashing helpers (Rule R-SC-08, ADR-0008).

Provides:
- hash_identifier: Salted SHA-256 for anonymizing IP addresses and emails
- log_audit_event: Structured append-only audit event recorder
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from compintel.governance.models import AuditLog

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session


def hash_identifier(value: str, salt: str = "compintel_audit_v1") -> str:
    """Compute a deterministic, salted SHA-256 hash for privacy-preserving auditing."""
    normalized = value.strip().lower()
    return hashlib.sha256(f"{salt}:{normalized}".encode()).hexdigest()


def log_audit_event(
    session: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str | uuid.UUID,
    actor_role: str,
    action: str,
    actor_id: str | uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Record an append-only entry in the audit log (Rule R-SC-08)."""
    entity_id_str = str(entity_id)
    actor_id_str = str(actor_id) if actor_id is not None else None

    entry = AuditLog(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id_str,
        actor_role=actor_role,
        actor_id=actor_id_str,
        action=action,
        details=details or {},
    )
    session.add(entry)
    return entry
