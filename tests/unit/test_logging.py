"""Unit tests for structured logging and PII masking (Rules R-CD-06, R-DA-07)."""

import pytest

from compintel.logging import (
    configure_logging,
    get_logger,
    mask_pii_processor,
)


@pytest.mark.unit
def test_mask_pii_processor_sensitive_keys() -> None:
    """Verify sensitive keys in event dictionary are replaced with [REDACTED_PII]."""
    event_dict = {
        "event": "user_action",
        "email": "employee@techcorp.in",
        "phone": "+91 9876543210",
        "pan": "ABCDE1234F",
        "full_name": "Arun Kumar",
        "nested": {
            "user_name": "arunk",
            "password": "supersecretpassword",
            "safe_counter": 100,
        },
    }

    processed = mask_pii_processor(None, "info", event_dict)

    assert processed["email"] == "[REDACTED_PII]"
    assert processed["phone"] == "[REDACTED_PII]"
    assert processed["pan"] == "[REDACTED_PII]"
    assert processed["full_name"] == "[REDACTED_PII]"
    assert processed["nested"]["user_name"] == "[REDACTED_PII]"
    assert processed["nested"]["password"] == "[REDACTED_PII]"
    assert processed["nested"]["safe_counter"] == 100


@pytest.mark.unit
def test_mask_pii_processor_in_event_string() -> None:
    """Verify PII regex patterns within event log messages are masked."""
    event_dict = {
        "event": (
            "Processed submission for engineer.john@sub.domain.co with PAN PQRST9876Z "
            "and Aadhaar 3456 7890 1234, reach out on 9876501234."
        ),
        "status": "success",
    }

    processed = mask_pii_processor(None, "info", event_dict)

    message = str(processed["event"])
    assert "engineer.john@sub.domain.co" not in message
    assert "[REDACTED_EMAIL]" in message
    assert "PQRST9876Z" not in message
    assert "[REDACTED_PAN]" in message
    assert "3456 7890 1234" not in message
    assert "[REDACTED_AADHAAR]" in message
    assert "9876501234" not in message
    assert "[REDACTED_PHONE]" in message
    assert processed["status"] == "success"


@pytest.mark.unit
def test_mask_pii_processor_nested_lists_and_tuples() -> None:
    """Verify masking inside lists and tuples."""
    event_dict = {
        "event": "batch_run",
        "records": [
            {"candidate_email": "a@b.com", "score": 95},
            {"contact": "8765432109", "score": 88},
        ],
        "tags": ("test", "email_in_tag: dev@company.com"),
    }

    processed = mask_pii_processor(None, "info", event_dict)

    assert processed["records"][0]["candidate_email"] == "[REDACTED_PII]"
    assert processed["records"][0]["score"] == 95
    assert processed["records"][1]["contact"] == "[REDACTED_PII]"
    assert processed["tags"][0] == "test"
    assert "dev@company.com" not in processed["tags"][1]
    assert "[REDACTED_EMAIL]" in processed["tags"][1]


@pytest.mark.unit
def test_get_logger_and_logging_execution(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify get_logger produces structured output and protects PII in capsys."""
    configure_logging()
    logger = get_logger("test_compintel_logger")

    logger.info(
        "Ingested test observation",
        source="SRC-TEST-01",
        email="test_user@example.com",
        count=42,
    )

    captured = capsys.readouterr()
    # PII must never appear in raw output string
    assert "test_user@example.com" not in captured.out
    assert "test_user@example.com" not in captured.err
    assert "SRC-TEST-01" in captured.out
    assert "[REDACTED_PII]" in captured.out
