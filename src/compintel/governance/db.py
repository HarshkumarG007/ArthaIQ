"""Database engine management and migration execution helpers (ADR-0003, ADR-0008).

Provides:
- Synchronous and asynchronous SQLAlchemy engine factories
- Session factory configuration
- Programmatic Alembic migration runners for CI and automated tests
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from compintel.config import get_settings

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine


def get_alembic_config(db_url: str | None = None) -> Config:
    """Create an Alembic Config object pointing to the repository's alembic setup."""
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    ini_path = root_dir / "alembic.ini"

    if not ini_path.exists():
        raise FileNotFoundError(f"alembic.ini not found at {ini_path}")

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(root_dir / "alembic"))

    if db_url:
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    else:
        settings = get_settings()
        url = os.environ.get("DATABASE_URL", settings.database_url)
        alembic_cfg.set_main_option("sqlalchemy.url", url)

    return alembic_cfg


def get_sync_database_url(url: str | None = None) -> str:
    """Resolve database URL and convert async drivers to sync drivers if needed."""
    if url is None:
        settings = get_settings()
        url = os.environ.get("DATABASE_URL", settings.database_url)

    # Convert asyncpg to standard sync driver for sync operations/migrations
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return url


def create_sync_engine(
    url: str | None = None,
    echo: bool = False,
    schema_translate_map: dict[str | None, str | None] | None = None,
    **kwargs: Any,
) -> Engine:
    """Create a synchronous SQLAlchemy engine.

    For SQLite test engines, schema_translate_map={'identity': None, 'app': None}
    can be passed to collapse PostgreSQL schemas into the default SQLite database.
    """
    resolved_url = get_sync_database_url(url)
    execution_options = kwargs.pop("execution_options", {})
    if schema_translate_map is not None:
        execution_options["schema_translate_map"] = schema_translate_map

    return create_engine(resolved_url, echo=echo, execution_options=execution_options, **kwargs)


def run_migrations_up(db_url: str | None = None, revision: str = "head") -> None:
    """Execute Alembic upgrade migrations programmatically up to revision."""
    cfg = get_alembic_config(db_url)
    command.upgrade(cfg, revision)


def run_migrations_down(db_url: str | None = None, revision: str = "base") -> None:
    """Execute Alembic downgrade migrations programmatically down to revision."""
    cfg = get_alembic_config(db_url)
    command.downgrade(cfg, revision)


def get_db(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Provide a transactional database session for FastAPI dependencies or manual usage."""
    if engine is None:
        engine = create_sync_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_db_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Provide a transactional database session context manager."""
    if engine is None:
        engine = create_sync_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
