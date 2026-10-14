"""Structured logging configuration with automated PII masking (Rules R-CD-06, R-DA-07).

Ensures all log events are structured (JSON in production, console in local dev)
and strips all personal identifiers, secrets, and statutory Indian PII
(PAN, Aadhaar, email, phone) by construction before writing to stdout.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import TYPE_CHECKING, Any

import structlog

from compintel.config import Settings, get_settings

if TYPE_CHECKING:
    from structlog.types import EventDict, WrappedLogger


# Statutory and common PII regex patterns
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
_AADHAAR_RE = re.compile(r"\b[2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b")

# Sensitive key substrings in log event dictionaries
_SENSITIVE_KEYS: tuple[str, ...] = (
    "email",
    "phone",
    "mobile",
    "contact",
    "name",
    "first_name",
    "last_name",
    "full_name",
    "employee_name",
    "user_name",
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
    "street",
    "bank_account",
    "salary_slip",
)


def _is_sensitive_key(k: str) -> bool:
    """Check if key represents sensitive PII or credentials."""
    k_lower = k.lower()
    return k_lower == "key" or any(sensitive in k_lower for sensitive in _SENSITIVE_KEYS)


def _mask_string(value: str) -> str:
    """Mask email, PAN, Aadhaar, and phone patterns in text (Rule R-DA-07)."""
    value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = _PAN_RE.sub("[REDACTED_PAN]", value)
    value = _AADHAAR_RE.sub("[REDACTED_AADHAAR]", value)
    value = _PHONE_RE.sub("[REDACTED_PHONE]", value)
    return value


def _mask_pii_value(val: Any) -> Any:
    """Recursively mask PII in nested dictionary, list, or string structures."""
    if isinstance(val, dict):
        cleaned: dict[str, Any] = {}
        for k, v in val.items():
            if _is_sensitive_key(str(k)):
                cleaned[str(k)] = "[REDACTED_PII]"
            else:
                cleaned[str(k)] = _mask_pii_value(v)
        return cleaned
    if isinstance(val, list | tuple | set):
        items = [_mask_pii_value(elem) for elem in val]
        return type(val)(items) if not isinstance(val, set) else set(items)
    if isinstance(val, str):
        return _mask_string(val)
    return val


def mask_pii_processor(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """Structlog processor that masks PII across all event keys and strings.

    By placing this processor before the final renderer in the logging pipeline,
    no sensitive personal data can enter log output by construction.
    """
    for key in list(event_dict.keys()):
        val = event_dict[key]
        if _is_sensitive_key(key):
            event_dict[key] = "[REDACTED_PII]"
        else:
            event_dict[key] = _mask_pii_value(val)
    return event_dict


_CONFIGURED = False


def configure_logging(settings: Settings | None = None) -> None:
    """Configure structlog and standard library logging pipeline.

    Idempotent. Uses settings or default cached settings.
    """
    global _CONFIGURED
    cfg = settings or get_settings()

    log_level = getattr(logging, cfg.log_level.upper(), logging.INFO)

    # Common processors before rendering
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        mask_pii_processor,  # Automated PII Redaction
    ]

    if cfg.log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence verbose third-party loggers
    for third_party in ("urllib3", "asyncio", "httpx", "botocore"):
        logging.getLogger(third_party).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Retrieve structured logger instance with automatic PII protection.

    Configures logging on first call if not already configured.
    """
    if not _CONFIGURED:
        configure_logging()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
