"""Unit tests for evaluation lock and pre-registration immutability (Task T4.03).

Adheres strictly to:
- Rule R-MD-02: Final test set is isolated, untouched during tuning, and locked for make final-eval.
- Rule R-MD-06: Pre-registration committed before looking at the test set.
- Rule R-TS-01: Deterministic unit tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.lock import (
    DEFAULT_LOCK_PATH,
    DEFAULT_PREREG_PATH,
    EXPECTED_PREREG_V1_HASH,
    acquire_final_eval_lock,
    check_eval_lock,
    compute_normalized_file_sha256,
    declare_contamination_and_unlock,
    is_final_eval_locked,
    read_final_eval_lock,
    verify_preregistration_hash,
)


@pytest.mark.unit
def test_preregistration_v1_yaml_structure_and_schema() -> None:
    """Verify v1.yaml exists, parses as valid YAML, and contains all required sections."""
    assert DEFAULT_PREREG_PATH.is_file(), f"Pre-registration file missing at {DEFAULT_PREREG_PATH}"

    data = yaml.safe_load(DEFAULT_PREREG_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)

    required_sections = [
        "metadata",
        "canonical_data",
        "split_protocol",
        "metrics_specification",
        "decision_rules_and_thresholds",
        "subgroup_slices",
        "final_evaluation_lock",
    ]
    for section in required_sections:
        assert section in data, f"Required section {section} missing from v1.yaml"

    assert data["metadata"]["document_id"] == "experiments/preregistration/v1.yaml"
    assert data["metadata"]["version"] == "1.0.0"
    assert data["metadata"]["primary_target"] == "guaranteed_cash_annual"
    assert data["canonical_data"]["snapshot_id"] == "SNAP-1FF34A8E9633"


@pytest.mark.unit
def test_preregistration_v1_hash_integrity() -> None:
    """Verify pre-registration hash matches the expected pre-registered constant."""
    computed_hash = compute_normalized_file_sha256(DEFAULT_PREREG_PATH)
    assert computed_hash == EXPECTED_PREREG_V1_HASH
    assert verify_preregistration_hash(DEFAULT_PREREG_PATH, EXPECTED_PREREG_V1_HASH) is True


@pytest.mark.unit
def test_preregistration_tamper_detection(tmp_path: Path) -> None:
    """Verify any modification to pre-registration YAML raises DataContractError."""
    tampered_file = tmp_path / "tampered_v1.yaml"
    tampered_file.write_text("metadata:\n  document_id: tampered\n", encoding="utf-8")

    with pytest.raises(DataContractError) as exc_info:
        verify_preregistration_hash(tampered_file, EXPECTED_PREREG_V1_HASH, raise_on_error=True)

    assert exc_info.value.code == "PREREGISTRATION_INTEGRITY_VIOLATION"


@pytest.mark.unit
def test_acquire_final_eval_lock_and_collision_rejection(tmp_path: Path) -> None:
    """Rule R-MD-02: Acquiring lock creates file; second evaluation attempt raises error."""
    temp_lock = tmp_path / "FINAL_EVAL_LOCK.json"
    assert is_final_eval_locked(temp_lock) is False
    check_eval_lock(temp_lock)

    # Acquire lock
    meta = {"model_champion": "RUNG_A_EMPIRICAL", "metric_mae": 3.85}
    written_path = acquire_final_eval_lock(meta, lock_path=temp_lock)
    assert written_path.is_file()
    assert is_final_eval_locked(temp_lock) is True

    lock_record = read_final_eval_lock(temp_lock)
    assert lock_record["status"] == "LOCKED"
    assert lock_record["rule"] == "R-MD-02"
    assert lock_record["run_metadata"]["model_champion"] == "RUNG_A_EMPIRICAL"

    # Attempting to check lock now must fail
    with pytest.raises(DataContractError) as exc1:
        check_eval_lock(temp_lock)
    assert exc1.value.code == "FINAL_TEST_SET_LOCKED"

    # Attempting to acquire lock again must fail
    with pytest.raises(DataContractError) as exc2:
        acquire_final_eval_lock({"another": "run"}, lock_path=temp_lock)
    assert exc2.value.code == "FINAL_TEST_SET_LOCKED"


@pytest.mark.unit
def test_declare_contamination_and_unlock(tmp_path: Path) -> None:
    """Rule R-MD-02: Formal contamination declaration archives lock and unlocks test evaluation."""
    temp_lock = tmp_path / "FINAL_EVAL_LOCK.json"
    arch_dir = tmp_path / "archived"

    acquire_final_eval_lock({"initial": "run"}, lock_path=temp_lock)
    assert temp_lock.is_file()

    # Reject short reason (< 20 chars)
    with pytest.raises(CompIntelValidationError) as exc1:
        declare_contamination_and_unlock(
            "Too short", "dev", lock_path=temp_lock, archive_dir=arch_dir
        )
    assert exc1.value.code == "INSUFFICIENT_DECLARATION_REASON"

    # Valid declaration
    archive_file = declare_contamination_and_unlock(
        declaration_reason="Test partition features were inadvertently leaked into training set.",
        operator="lead_maintainer",
        lock_path=temp_lock,
        archive_dir=arch_dir,
    )

    assert not temp_lock.is_file()
    assert is_final_eval_locked(temp_lock) is False
    assert archive_file.is_file()

    # Now check_eval_lock passes again
    check_eval_lock(temp_lock)


@pytest.mark.unit
def test_read_lock_error_handling(tmp_path: Path) -> None:
    """Verify invalid or missing lock files raise DataContractError."""
    missing_lock = tmp_path / "nonexistent.json"
    with pytest.raises(DataContractError) as exc1:
        read_final_eval_lock(missing_lock)
    assert exc1.value.code == "LOCK_FILE_NOT_FOUND"

    corrupted_lock = tmp_path / "corrupted.json"
    corrupted_lock.write_text("{not-valid-json", encoding="utf-8")
    with pytest.raises(DataContractError) as exc2:
        read_final_eval_lock(corrupted_lock)
    assert exc2.value.code == "INVALID_LOCK_FILE"


@pytest.mark.unit
def test_repository_eval_lock_is_currently_clean() -> None:
    """Ensure active repo test set is currently unlocked before baseline phase starts."""
    assert not DEFAULT_LOCK_PATH.is_file(), (
        f"Active evaluation lock exists at {DEFAULT_LOCK_PATH}. Test set is already contaminated!"
    )
    assert is_final_eval_locked() is False
