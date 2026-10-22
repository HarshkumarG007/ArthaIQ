"""Application configuration and settings management (Rule R-CD-05).

Uses pydantic-settings for type-safe environment variable parsing,
validation, and default configurations across environments.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from compintel.errors import ConfigError

Environment = Literal["local", "test", "preview", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "console"]


class Settings(BaseSettings):
    """Central settings for CompIntel services and pipeline."""

    # Application environment
    app_env: Environment = Field(
        default="local",
        description="Deployment environment (local, test, preview, production).",
    )

    # Logging settings (Rules R-CD-06, R-DA-07)
    log_level: LogLevel = Field(
        default="INFO",
        description="Structured logging verbosity level.",
    )
    log_format: LogFormat = Field(
        default="json",
        description="Format of log output: 'json' for production, 'console' for human CLI.",
    )

    # Database connection (Rule R-SC-02)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/compintel",
        description="Asynchronous PostgreSQL connection URI.",
    )

    # Cryptographic secrets
    secret_key: SecretStr | None = Field(
        default=None,
        description="Application secret key for session/token cryptographic signatures.",
    )

    # Storage paths
    data_dir: Path = Field(
        default=Path("data"),
        description="Root data directory.",
    )
    raw_data_dir: Path = Field(
        default=Path("data/raw"),
        description="Immutable raw ingestion zone (Rule R-DA-02).",
    )
    staged_data_dir: Path = Field(
        default=Path("data/staged"),
        description="Staged source-conforming data zone.",
    )
    canonical_data_dir: Path = Field(
        default=Path("data/canonical"),
        description="Canonical schema observations zone.",
    )
    processed_data_dir: Path = Field(
        default=Path("data/processed"),
        description="Processed and normalized target outputs.",
    )
    quarantine_data_dir: Path = Field(
        default=Path("data/quarantine"),
        description="Quarantine storage zone for excluded observations (Rule R-DA-05).",
    )
    artifacts_dir: Path = Field(
        default=Path("artifacts"),
        description="Model artifact bundles and registry manifests.",
    )
    experiments_dir: Path = Field(
        default=Path("experiments"),
        description="Pre-registration configs and evaluation results.",
    )
    thresholds_path: Path = Field(
        default=Path("config/thresholds.yaml"),
        description="Path to pre-registered evaluation and abstention thresholds.",
    )

    # Serving & ML parameters
    champion_model_version: str = Field(
        default="latest",
        description="Identifier of champion model bundle to load in serving.",
    )

    # Privacy & Quality statutory thresholds (Rules R-DA-10, C3, R-ER-06)
    k_min: int = Field(
        default=5,
        ge=5,
        description="Rule R-DA-10: Small-cell privacy suppression floor (minimum cohort size).",
    )
    max_quarantine_rate: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Rule R-ER-06: Configured pipeline halt threshold for quarantine rate.",
    )
    observation_window_days: int = Field(
        default=180,
        gt=0,
        description="Sufficiency Criterion C3: Maximum observation freshness window.",
    )
    cpi_deflation_threshold_days: int = Field(
        default=90,
        gt=0,
        description="Sufficiency Criterion C3: Staleness threshold triggering CPI deflation.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("k_min")
    @classmethod
    def validate_k_min(cls, v: int) -> int:
        """Enforce strict statutory privacy floor (Rule R-DA-10)."""
        if v < 5:
            raise ConfigError(
                f"k_min must be at least 5 for privacy preservation (Rule R-DA-10), got {v}",
                code="INVALID_K_MIN",
            )
        return v

    @model_validator(mode="after")
    def validate_production_configuration(self) -> Self:
        """Enforce production security controls (OWASP ASVS & Rule R-CD-05)."""
        if self.app_env == "production":
            # 1. Require strong, non-empty secret_key
            if self.secret_key is None or len(self.secret_key.get_secret_value().strip()) < 32:
                msg = (
                    "Production deployment requires a secure secret_key of at least 32 characters."
                )
                raise ConfigError(msg, code="INSECURE_SECRET_KEY")

            # 2. Reject default/placeholder credentials in database_url
            db_url = self.database_url.lower()
            insecure_patterns = ("compintel_preview_secret", "postgres:postgres@", "localhost")
            if any(pattern in db_url for pattern in insecure_patterns):
                msg = (
                    "Production deployment cannot use default/local database credentials "
                    "in database_url."
                )
                raise ConfigError(msg, code="INSECURE_DATABASE_URL")
        return self

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    def is_local(self) -> bool:
        """Check if running in local development mode."""
        return self.app_env in ("local", "test")

    def ensure_directories(self) -> None:
        """Create standard directory structure if missing."""
        for path in (
            self.raw_data_dir,
            self.staged_data_dir,
            self.canonical_data_dir,
            self.processed_data_dir,
            self.quarantine_data_dir,
            self.artifacts_dir,
            self.experiments_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached singleton Settings instance."""
    return Settings()
