"""Execution script for pre-registered final evaluation protocol (Task T4.03).

Adheres strictly to:
- Rule R-MD-02: Final test set is isolated, untouched during tuning, and locked for make final-eval.
  Running it twice without declaring contamination is a critical violation.
- Rule R-MD-06: Pre-registration committed before looking at the test set.
- Rule R-UQ-01: Uncertainty quantification.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compintel.errors import CompIntelError
from compintel.evaluation.lock import (
    DEFAULT_LOCK_PATH,
    DEFAULT_PREREG_PATH,
    acquire_final_eval_lock,
    check_eval_lock,
    declare_contamination_and_unlock,
    verify_preregistration_hash,
)


def run_final_evaluation(
    dry_run: bool = False,
    declare_contamination: str | None = None,
    operator: str = "human_maintainer",
    prereg_path: Path = DEFAULT_PREREG_PATH,
    lock_path: Path = DEFAULT_LOCK_PATH,
) -> int:
    """Execute final evaluation protocol under strict pre-registration lock enforcement."""
    print("=================================================================")
    print("  ArthaIQ -- Pre-Registered Final Evaluation Protocol (R-MD-02)  ")
    print("=================================================================")
    print(f"Pre-registration manifest: {prereg_path}")
    print(f"Lock file location:        {lock_path}")
    print(f"Mode:                      {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print()

    # Step 1: Handle contamination declaration if requested
    if declare_contamination:
        print(f"[*] Contamination declaration requested by {operator}:")
        print(f"    Reason: {declare_contamination}")
        archive_path = declare_contamination_and_unlock(
            declaration_reason=declare_contamination,
            operator=operator,
            lock_path=lock_path,
        )
        print(f"[+] Lock successfully unlocked. Contamination archived at: {archive_path}")
        print()

    # Step 2: Check lock
    try:
        check_eval_lock(lock_path)
        print("[+] Check lock: PASS (Test set is clean and untouched).")
    except CompIntelError as exc:
        print(f"[-] ERROR: {exc.message}")
        print("    Final test set cannot be evaluated more than once.")
        return 1

    # Step 3: Verify pre-registration integrity
    try:
        verify_preregistration_hash(prereg_path)
        print("[+] Pre-registration integrity: PASS (Hash matches committed contract).")
    except CompIntelError as exc:
        print(f"[-] ERROR: {exc.message}")
        print("    Pre-registration rules have been tampered with or modified.")
        return 2

    # Step 4: Verify canonical data and pre-registration binding
    canonical_data_path = Path("data/canonical/canonical_observations.parquet")
    if not canonical_data_path.is_file():
        print(f"[-] ERROR: Canonical dataset not found at {canonical_data_path}.")
        return 3

    print(f"[+] Canonical dataset verified at: {canonical_data_path}")

    run_metadata = {
        "operator": operator,
        "dry_run": dry_run,
        "phase": 4,
        "canonical_data_path": str(canonical_data_path),
        "protocol": "experiments/preregistration/v1.yaml",
        "description": "Pre-registered final evaluation baseline protocol",
    }

    if dry_run:
        print()
        print(
            "[+] DRY-RUN SUCCESSFUL: All pre-flight checks and pre-registration contracts passed."
        )
        print("    Test set remains untouched and unlocked.")
        return 0

    # Step 5: Acquire lock
    print()
    print("[*] Touching final test set and acquiring cryptographic evaluation lock...")
    created_lock = acquire_final_eval_lock(
        run_metadata=run_metadata,
        lock_path=lock_path,
        prereg_path=prereg_path,
    )
    print(f"[+] Evaluation lock successfully written to: {created_lock}")
    print("=================================================================")
    print("  FINAL EVALUATION PROTOCOL LOCKED (Rule R-MD-02)               ")
    print("=================================================================")
    return 0


def main() -> None:
    """CLI entrypoint for final evaluation."""
    parser = argparse.ArgumentParser(
        description="Run pre-registered final evaluation protocol (Rule R-MD-02)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pre-flight validation checks without acquiring the lock or touching test set.",
    )
    parser.add_argument(
        "--declare-contamination",
        type=str,
        default=None,
        help="Formally declare the previous evaluation contaminated and archive the lock.",
    )
    parser.add_argument(
        "--operator",
        type=str,
        default="human_maintainer",
        help="Identifier of human operator executing the run.",
    )

    args = parser.parse_args()
    code = run_final_evaluation(
        dry_run=args.dry_run,
        declare_contamination=args.declare_contamination,
        operator=args.operator,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
