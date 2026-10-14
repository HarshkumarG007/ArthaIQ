"""Standard exception taxonomy for CompIntel (Rule R-ER-02).

All exceptions derive from CompIntelError. Expected outcomes (such as
abstention) use result types, never exceptions.
"""

from __future__ import annotations

import re
from typing import Any

# PII redaction patterns for error messages and context
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
_AADHAAR_RE = re.compile(r"\b[2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b")

_SENSITIVE_KEY_SUBSTRINGS = (
    "email",
    "phone",
    "mobile",
    "contact",
    "name",
    "pan",
    "aadhaar",
    "ssn",
    "password",
    "secret",
    "token",
    "api_key",
    "secret_key",
    "access_key",
    "private_key",
    "auth",
    "address",
    "salary_slip",
)


def _is_sensitive_key(k: str) -> bool:
    """Check if dictionary key represents sensitive PII or credentials."""
    k_lower = k.lower()
    return k_lower == "key" or any(sub in k_lower for sub in _SENSITIVE_KEY_SUBSTRINGS)


def _sanitize_string(val: str) -> str:
    """Mask known PII patterns in error strings (Rule R-DA-07)."""
    val = _EMAIL_RE.sub("[REDACTED_EMAIL]", val)
    val = _PAN_RE.sub("[REDACTED_PAN]", val)
    val = _AADHAAR_RE.sub("[REDACTED_AADHAAR]", val)
    val = _PHONE_RE.sub("[REDACTED_PHONE]", val)
    return val


def sanitize_error_context(obj: Any) -> Any:
    """Recursively sanitize context objects attached to exceptions."""
    if isinstance(obj, dict):
        sanitized: dict[str, Any] = {}
        for k, v in obj.items():
            if _is_sensitive_key(str(k)):
                sanitized[str(k)] = "[REDACTED_PII]"
            else:
                sanitized[str(k)] = sanitize_error_context(v)
        return sanitized
    if isinstance(obj, list | tuple):
        sanitized_list = [sanitize_error_context(item) for item in obj]
        return type(obj)(sanitized_list)
    if isinstance(obj, str):
        return _sanitize_string(obj)
    return obj


class CompIntelError(Exception):
    """Base exception for all CompIntel errors (Rule R-ER-02)."""

    default_code: str = "COMPINTEL_ERROR"

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        sanitized_msg = _sanitize_string(message)
        super().__init__(sanitized_msg)
        self.message = sanitized_msg
        self.code = code or self.default_code
        self.details: dict[str, Any] = sanitize_error_context(details or {})

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to structured dictionary for logging or API responses."""
        payload: dict[str, Any] = {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} (details={self.details})"
        return f"[{self.code}] {self.message}"


class CompIntelValidationError(CompIntelError):
    """Raised when data input or parameters fail schema/domain validation."""

    default_code: str = "VALIDATION_ERROR"


# Alias per Rule R-ER-02 specification
ValidationError = CompIntelValidationError


class DataContractError(CompIntelError):
    """Raised when a data contract between pipeline stages is violated."""

    default_code: str = "DATA_CONTRACT_ERROR"


class LicenceViolationError(CompIntelError):
    """Raised when a data source or usage violates legal licence terms (Rule R-DA-01)."""

    default_code: str = "LICENCE_VIOLATION_ERROR"


class LeakageError(CompIntelError):
    """Raised when future information or target leakage is detected across splits."""

    default_code: str = "LEAKAGE_ERROR"


class ConfigError(CompIntelError):
    """Raised when environment or application configuration is invalid or missing."""

    default_code: str = "CONFIG_ERROR"


class ModelArtifactError(CompIntelError):
    """Raised when model weights, bundles, or manifests cannot be loaded or verified."""

    default_code: str = "MODEL_ARTIFACT_ERROR"


class UpstreamUnavailableError(CompIntelError):
    """Raised when an external or upstream service dependency is unreachable."""

    default_code: str = "UPSTREAM_UNAVAILABLE_ERROR"
