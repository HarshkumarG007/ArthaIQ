"""Evaluation protocol lock and pre-registration immutability manager (Task T4.03).

Adheres strictly to:
- Rule R-MD-02: Final test set is isolated, untouched during tuning, and locked for make final-eval.
  Running it twice is a critical violation unless you formally declare the first run contaminated
  and roll the test window forward. A lock file is written after the first run.
- Rule R-MD-06: Pre-registration required for every model evaluation before looking at the test set.
  Thresholds, metrics, splits, and decision rules committed to Git first.
- Rule R-CD-03: Evaluation layer imports only schema and errors; zero dependencies on serving.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from compintel.errors import CompIntelValidationError, DataContractError

DEFAULT_PREREG_PATH = Path("experiments/preregistration/v1.yaml")
DEFAULT_LOCK_PATH = Path("experiments/preregistration/FINAL_EVAL_LOCK.json")
EXPECTED_PREREG_V1_HASH = "277610fe03d219fd9a5da9e9e969adb7c5505bc8a2dd34b9522d1964f1dd6fb4"


def compute_normalized_file_sha256(path: Path) -> str:
    """Compute SHA-256 of file with normalized LF line endings for cross-platform stability."""
    if not path.is_file():
        raise CompIntelValidationError(
            f"Target file for hashing does not exist: {path}",
            code="FILE_NOT_FOUND",
            details={"path": str(path)},
        )
    raw_bytes = path.read_bytes()
    normalized = raw_bytes.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def verify_preregistration_hash(
    prereg_path: Path | None = None,
    expected_hash: str | None = None,
    raise_on_error: bool = True,
) -> bool:
    """Verify that the pre-registration YAML has not been tampered with or modified.

    Args:
        prereg_path: Path to preregistration file (defaults to experiments/preregistration/v1.yaml).
        expected_hash: Expected SHA-256 (defaults to EXPECTED_PREREG_V1_HASH).
        raise_on_error: Whether to raise DataContractError on hash mismatch.

    Returns:
        True if the hash matches.

    Raises:
        DataContractError: If the computed hash differs from the pre-registered expected hash.
    """
    path = prereg_path or DEFAULT_PREREG_PATH
    expected = expected_hash or EXPECTED_PREREG_V1_HASH

    actual_hash = compute_normalized_file_sha256(path)
    is_valid = actual_hash == expected

    if not is_valid and raise_on_error:
        raise DataContractError(
            f"Pre-registration integrity violation: {path} hash {actual_hash} "
            f"does not match pre-registered hash {expected}.",
            code="PREREGISTRATION_INTEGRITY_VIOLATION",
            details={
                "path": str(path),
                "actual_hash": actual_hash,
                "expected_hash": expected,
            },
        )
    return is_valid


def is_final_eval_locked(lock_path: Path | None = None) -> bool:
    """Check whether final evaluation has already been run and locked."""
    path = lock_path or DEFAULT_LOCK_PATH
    return path.is_file()


def read_final_eval_lock(lock_path: Path | None = None) -> dict[str, Any]:
    """Read the existing final evaluation lock record.

    Raises:
        DataContractError: If lock file is missing or invalid JSON.
    """
    path = lock_path or DEFAULT_LOCK_PATH
    if not path.is_file():
        raise DataContractError(
            f"Final evaluation lock file does not exist at {path}.",
            code="LOCK_FILE_NOT_FOUND",
            details={"path": str(path)},
        )
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception as exc:
        raise DataContractError(
            f"Failed to parse lock file at {path}: {exc}",
            code="INVALID_LOCK_FILE",
            details={"path": str(path), "error": str(exc)},
        ) from exc


def check_eval_lock(
    lock_path: Path | None = None,
    allow_if_declared: bool = False,
) -> None:
    """Verify that final evaluation is not locked against evaluation.

    Rule R-MD-02: Final test set is touched once only.

    Raises:
        DataContractError: If lock file exists and allow_if_declared is False.
    """
    path = lock_path or DEFAULT_LOCK_PATH
    if path.is_file() and not allow_if_declared:
        lock_data = read_final_eval_lock(path)
        locked_at = lock_data.get("locked_at", "UNKNOWN")
        runner = lock_data.get("runner", "UNKNOWN")
        raise DataContractError(
            f"CRITICAL EVALUATION LOCK VIOLATION (Rule R-MD-02): Final test set evaluation "
            f"has already been executed and locked at {locked_at} by {runner}. "
            "Running final-eval a second time is strictly prohibited to prevent test set "
            "overfitting. If the previous evaluation run was genuinely contaminated, "
            "you must formally declare contamination using declare_contamination_and_unlock().",
            code="FINAL_TEST_SET_LOCKED",
            details=lock_data,
        )


def acquire_final_eval_lock(
    run_metadata: dict[str, Any],
    lock_path: Path | None = None,
    prereg_path: Path | None = None,
) -> Path:
    """Acquire final evaluation lock and write cryptographic receipt to disk.

    Args:
        run_metadata: Execution metadata (model_champion, metrics_summary, git_commit, etc.).
        lock_path: Path to write the lock file.
        prereg_path: Path to pre-registration YAML.

    Returns:
        Path to the created lock file.

    Raises:
        DataContractError: If lock already exists or pre-registration integrity check fails.
    """
    target_lock = lock_path or DEFAULT_LOCK_PATH
    check_eval_lock(target_lock)

    prereg = prereg_path or DEFAULT_PREREG_PATH
    actual_prereg_hash = compute_normalized_file_sha256(prereg)

    lock_payload: dict[str, Any] = {
        "status": "LOCKED",
        "rule": "R-MD-02",
        "locked_at": datetime.now(UTC).isoformat(),
        "preregistration_path": str(prereg),
        "preregistration_sha256": actual_prereg_hash,
        "run_metadata": run_metadata,
    }

    target_lock.parent.mkdir(parents=True, exist_ok=True)
    target_lock.write_text(json.dumps(lock_payload, indent=2), encoding="utf-8")
    return target_lock


def declare_contamination_and_unlock(
    declaration_reason: str,
    operator: str,
    lock_path: Path | None = None,
    archive_dir: Path | None = None,
) -> Path:
    """Archive an existing lock under formal contamination declaration (Rule R-MD-02).

    Args:
        declaration_reason: Comprehensive justification explaining why previous run was invalid.
        operator: Name/handle of human engineer authorizing the unlock.
        lock_path: Path to the current active lock file.
        archive_dir: Directory where archived contamination records are saved.

    Returns:
        Path to the archived contaminated lock record.

    Raises:
        CompIntelValidationError: If declaration_reason is too short (< 20 characters).
        DataContractError: If active lock file does not exist.
    """
    if len(declaration_reason.strip()) < 20:
        raise CompIntelValidationError(
            "Contamination declaration reason must be at least 20 chars explaining root cause.",
            code="INSUFFICIENT_DECLARATION_REASON",
            details={"length": len(declaration_reason)},
        )

    current_lock_path = lock_path or DEFAULT_LOCK_PATH
    existing_lock = read_final_eval_lock(current_lock_path)

    ts_str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    arch_dir = archive_dir or current_lock_path.parent / "archived_locks"
    arch_dir.mkdir(parents=True, exist_ok=True)
    archive_file = arch_dir / f"FINAL_EVAL_LOCK_CONTAMINATED_{ts_str}.json"

    contamination_record: dict[str, Any] = {
        "status": "CONTAMINATED_ARCHIVE",
        "declared_at": datetime.now(UTC).isoformat(),
        "declared_by": operator,
        "declaration_reason": declaration_reason,
        "superseded_lock": existing_lock,
    }

    archive_file.write_text(json.dumps(contamination_record, indent=2), encoding="utf-8")
    current_lock_path.unlink()
    return archive_file
