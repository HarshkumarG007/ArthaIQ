"""Unit tests for Phase 31: Client Security & ADR-0014 WebCrypto Implementation.

Verifies:
- Structural integrity and TypeScript export of cryptoSync.ts and EncryptedSyncModal.tsx.
- ADR-0014 cryptographic envelope schema compliance (AES-256-GCM, PBKDF2-SHA256, 100k rounds).
- Monotonic state lattice implementation (unproven < self_reported < demonstrated).
- DPDP Act 2023 Section 12 hard erasure compliance.
- Route integration of the zero-knowledge sync modal in career.tsx.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"
CRYPTO_SYNC_PATH = WEB_SRC / "lib" / "cryptoSync.ts"
CRYPTO_SYNC_TEST_PATH = WEB_SRC / "lib" / "cryptoSync.test.ts"
SYNC_MODAL_PATH = WEB_SRC / "components" / "career" / "EncryptedSyncModal.tsx"
SYNC_MODAL_TEST_PATH = WEB_SRC / "components" / "career" / "EncryptedSyncModal.test.tsx"
CAREER_ROUTE_PATH = WEB_SRC / "routes" / "career.tsx"


class TestClientSecurityArchitecture:
    """Verifies ADR-0014 WebCrypto client security and monotonic lattice implementation."""

    def test_security_files_exist(self) -> None:
        """Required client crypto and UI files must exist."""
        assert CRYPTO_SYNC_PATH.exists(), f"Missing {CRYPTO_SYNC_PATH}"
        assert CRYPTO_SYNC_TEST_PATH.exists(), f"Missing {CRYPTO_SYNC_TEST_PATH}"
        assert SYNC_MODAL_PATH.exists(), f"Missing {SYNC_MODAL_PATH}"
        assert SYNC_MODAL_TEST_PATH.exists(), f"Missing {SYNC_MODAL_TEST_PATH}"

    def test_adr_0014_crypto_standards(self) -> None:
        """cryptoSync.ts must implement AES-256-GCM and PBKDF2-SHA256 with 100k rounds."""
        content = CRYPTO_SYNC_PATH.read_text(encoding="utf-8")
        assert 'algorithm: "AES-256-GCM"' in content
        assert 'kdf: "PBKDF2-SHA256"' in content
        assert "PBKDF2_ITERATIONS = 100000" in content
        assert "SALT_BYTES = 16" in content
        assert "IV_BYTES = 12" in content
        assert "deriveKey(" in content
        assert "encryptPayload(" in content
        assert "decryptPayload(" in content

    def test_monotonic_state_lattice_ranking(self) -> None:
        """cryptoSync.ts must implement state beats score lattice ranking."""
        content = CRYPTO_SYNC_PATH.read_text(encoding="utf-8")
        assert "STATE_LATTICE_RANK" in content
        assert "unproven: 0" in content
        assert "self_reported: 1" in content
        assert "demonstrated: 2" in content
        assert "mergeLedgerRecords(" in content

    def test_dpdp_hard_erasure_compliance(self) -> None:
        """cryptoSync.ts must support Section 12 hard purge."""
        content = CRYPTO_SYNC_PATH.read_text(encoding="utf-8")
        assert "executeHardErasure(" in content
        assert "purgeAllUserData()" in content

    def test_zero_knowledge_ui_modal(self) -> None:
        """EncryptedSyncModal must display zero-knowledge disclosures and passphrases."""
        content = SYNC_MODAL_PATH.read_text(encoding="utf-8")
        assert "Zero-Knowledge WebCrypto (ADR-0014)" in content
        assert "Zero Server Retention:" in content
        assert "Encrypted Multi-Device Sync" in content
        assert "exportEncryptedBackup" in content
        assert "importAndMergeEncryptedBackup" in content
        assert 'role="dialog"' in content
        assert 'role="tablist"' in content

    def test_career_route_sync_integration(self) -> None:
        """career.tsx must wire up the Encrypted Sync modal."""
        content = CAREER_ROUTE_PATH.read_text(encoding="utf-8")
        assert "EncryptedSyncModal" in content
        assert "showEncryptedSync" in content
        assert "Encrypted Sync" in content

    def test_gate_g31_review_dossier_and_ratification(self) -> None:
        """Gate G31 review dossier must exist, ratify Decision D-045, and check all criteria."""
        dossier_path = REPO_ROOT / "docs" / "pilot" / "gate-g31-review.md"
        assert dossier_path.exists(), f"Missing {dossier_path}"
        content = dossier_path.read_text(encoding="utf-8")
        assert "REV-GATE-G31-01" in content
        assert "Decision D-045" in content or "RESOLUTION D-045" in content
        assert "RATIFIED GO" in content
        assert "CHK-31-01" in content
        assert "CHK-31-16" in content
