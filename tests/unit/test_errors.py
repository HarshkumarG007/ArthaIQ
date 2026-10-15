"""Unit tests for exception taxonomy (Rule R-ER-02) and error sanitization (Rule R-DA-07)."""

import pytest

from compintel.errors import (
    CompIntelError,
    CompIntelValidationError,
    ConfigError,
    DataContractError,
    LeakageError,
    LicenceViolationError,
    ModelArtifactError,
    PipelineHaltError,
    UpstreamUnavailableError,
    ValidationError,
    sanitize_error_context,
)


@pytest.mark.unit
def test_exception_inheritance_hierarchy() -> None:
    """Verify all project exceptions inherit from CompIntelError (Rule R-ER-02)."""
    assert issubclass(CompIntelValidationError, CompIntelError)
    assert issubclass(ValidationError, CompIntelError)
    assert issubclass(DataContractError, CompIntelError)
    assert issubclass(LicenceViolationError, CompIntelError)
    assert issubclass(LeakageError, CompIntelError)
    assert issubclass(ConfigError, CompIntelError)
    assert issubclass(ModelArtifactError, CompIntelError)
    assert issubclass(UpstreamUnavailableError, CompIntelError)
    assert issubclass(PipelineHaltError, CompIntelError)


@pytest.mark.unit
def test_error_to_dict_and_str() -> None:
    """Verify error serialization and string formatting."""
    err = DataContractError(
        message="Invalid row count",
        code="INVALID_ROW_COUNT",
        details={"source": "test_src", "rows": 0},
    )

    data = err.to_dict()
    assert data["error"] == "DataContractError"
    assert data["code"] == "INVALID_ROW_COUNT"
    assert data["message"] == "Invalid row count"
    assert data["details"] == {"source": "test_src", "rows": 0}

    err_str = str(err)
    assert "[INVALID_ROW_COUNT] Invalid row count" in err_str
    assert "source" in err_str


@pytest.mark.unit
def test_pii_sanitization_in_error_message() -> None:
    """Verify PII patterns in error messages are masked by construction (Rule R-DA-07)."""
    msg = (
        "Failed processing for user user@example.com with PAN ABCDE1234F "
        "and Aadhaar 2345 6789 0123 phone +91 9876543210"
    )
    err = CompIntelValidationError(msg)

    assert "user@example.com" not in err.message
    assert "[REDACTED_EMAIL]" in err.message
    assert "ABCDE1234F" not in err.message
    assert "[REDACTED_PAN]" in err.message
    assert "2345 6789 0123" not in err.message
    assert "[REDACTED_AADHAAR]" in err.message
    assert "9876543210" not in err.message
    assert "[REDACTED_PHONE]" in err.message


@pytest.mark.unit
def test_sanitize_error_context_recursive() -> None:
    """Verify recursive sanitization of context dictionaries and lists."""
    raw_context = {
        "user_email": "candidate@example.com",
        "phone_number": "9123456789",
        "nested": {
            "full_name": "Jane Doe",
            "safe_metric": 42.0,
            "secret_token": "secret_abc_123",
            "notes": "Contact candidate at test.user@domain.in",
        },
        "records": [
            {"pan_card": "ABCDE5678G"},
            {"valid_key": "Clean info"},
        ],
    }

    sanitized = sanitize_error_context(raw_context)

    # Sensitive keys masked
    assert sanitized["user_email"] == "[REDACTED_PII]"
    assert sanitized["phone_number"] == "[REDACTED_PII]"
    assert sanitized["nested"]["full_name"] == "[REDACTED_PII]"
    assert sanitized["nested"]["secret_token"] == "[REDACTED_PII]"
    assert sanitized["records"][0]["pan_card"] == "[REDACTED_PII]"

    # Safe keys preserved
    assert sanitized["nested"]["safe_metric"] == 42.0
    assert sanitized["records"][1]["valid_key"] == "Clean info"

    # In-text patterns in string values masked
    assert "test.user@domain.in" not in sanitized["nested"]["notes"]
    assert "[REDACTED_EMAIL]" in sanitized["nested"]["notes"]
