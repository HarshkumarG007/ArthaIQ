"""Unit tests for configuration and settings management (Rule R-CD-05)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from compintel.config import Settings, get_settings
from compintel.errors import ConfigError


@pytest.mark.unit
def test_default_settings() -> None:
    """Verify default settings adhere to project architecture and privacy rules."""
    settings = Settings()

    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"
    assert settings.k_min == 5  # Rule R-DA-10
    assert settings.cpi_deflation_threshold_days == 90  # Criterion C3
    assert settings.observation_window_days == 180  # Criterion C3
    assert settings.champion_model_version == "latest"

    # Verify standard directory structure
    assert settings.data_dir == Path("data")
    assert settings.raw_data_dir == Path("data/raw")
    assert settings.staged_data_dir == Path("data/staged")
    assert settings.canonical_data_dir == Path("data/canonical")
    assert settings.processed_data_dir == Path("data/processed")
    assert settings.artifacts_dir == Path("artifacts")
    assert settings.experiments_dir == Path("experiments")


@pytest.mark.unit
def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify environment variables properly override defaults."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LOG_FORMAT", "console")
    monkeypatch.setenv("K_MIN", "10")
    monkeypatch.setenv("OBSERVATION_WINDOW_DAYS", "365")

    settings = Settings()
    assert settings.app_env == "production"
    assert settings.log_level == "WARNING"
    assert settings.log_format == "console"
    assert settings.k_min == 10
    assert settings.observation_window_days == 365
    assert settings.is_production() is True
    assert settings.is_local() is False


@pytest.mark.unit
def test_k_min_privacy_floor_enforcement() -> None:
    """Verify k_min < 5 is strictly rejected (Rule R-DA-10)."""
    with pytest.raises((ValidationError, ConfigError)):
        Settings(k_min=4)

    with pytest.raises((ValidationError, ConfigError)):
        Settings(k_min=0)


@pytest.mark.unit
def test_invalid_app_env() -> None:
    """Verify unsupported app_env is rejected by pydantic."""
    with pytest.raises(ValidationError):
        Settings(app_env="invalid_env")  # type: ignore[arg-type]


@pytest.mark.unit
def test_ensure_directories(tmp_path: Path) -> None:
    """Verify ensure_directories creates paths when missing."""
    settings = Settings(
        raw_data_dir=tmp_path / "raw",
        staged_data_dir=tmp_path / "staged",
        canonical_data_dir=tmp_path / "canonical",
        processed_data_dir=tmp_path / "processed",
        artifacts_dir=tmp_path / "artifacts",
        experiments_dir=tmp_path / "experiments",
    )
    settings.ensure_directories()

    assert (tmp_path / "raw").is_dir()
    assert (tmp_path / "staged").is_dir()
    assert (tmp_path / "canonical").is_dir()
    assert (tmp_path / "processed").is_dir()
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "experiments").is_dir()


@pytest.mark.unit
def test_get_settings_cached() -> None:
    """Verify get_settings returns cached singleton."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
