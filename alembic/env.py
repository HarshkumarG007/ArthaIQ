"""Alembic migration environment configuration (ADR-0003, ADR-0008).

Supports:
- PostgreSQL native multi-schema architecture ('identity', 'app')
- Offline SQL generation (--sql) for CI/CD inspection
- Asyncpg database URLs with automatic sync driver resolution
- SQLite compatibility for zero-dependency local and CI test execution
"""

from __future__ import annotations

import os
from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy import engine_from_config, pool

from compintel.config import get_settings
from compintel.governance.models import Base

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# Alembic Config object
config = context.config

# Interpret logging configuration if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate and migrations
target_metadata = Base.metadata


def get_resolved_sync_url() -> str:
    """Resolve database URL and convert async drivers to sync drivers."""
    url = config.get_main_option("sqlalchemy.url")
    if not url or url.startswith("driver://") or "user:pass@localhost" in url:
        settings = get_settings()
        url = os.environ.get("DATABASE_URL", settings.database_url)

    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite+aiosqlite://", "sqlite://", 1)

    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode emitting SQL statements."""
    url = get_resolved_sync_url()
    is_sqlite = "sqlite" in url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=not is_sqlite,
        version_table_schema="app" if not is_sqlite else None,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations on an established connection."""
    is_sqlite = connection.dialect.name == "sqlite"

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=not is_sqlite,
        version_table_schema="app" if not is_sqlite else None,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using synchronous engine connection."""
    # If connection was already passed in config attributes (e.g. from pytest fixtures)
    connectable_connection = config.attributes.get("connection", None)
    if connectable_connection is not None:
        do_run_migrations(connectable_connection)
        return

    url = get_resolved_sync_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
