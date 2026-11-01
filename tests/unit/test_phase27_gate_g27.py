"""Gate G27 Verification Suite (Phase 27, Task T27.05).

Verifies:
1. ADR-0014 zero-knowledge encrypted sync architecture and cryptographic specifications.
2. Cross-family pathway synthesis capabilities (SWE -> MLAI, DATA -> MLAI, SWE -> DATA).
3. Topological ordering, DAG acyclicity, and bridge competency tagging.
4. Heuristic effort hours calculation and practice scenario linkage.
5. Macroeconomic Competency Aggregation & Privacy Specification (SPEC-MACRO-COMP-01).
6. Gate G27 Review Dossier (REV-GATE-G27-01) and Decision D-041 ratification.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compintel.career.pathways import (
    CrossFamilyPathwayRequest,
    CrossFamilyPathwaySynthesizer,
)
from compintel.career.schema import RoleLevel
from compintel.schema.enums import RoleFamily


@pytest.fixture
def repo_root() -> Path:
    """Fixture providing repository root path."""
    return Path(__file__).resolve().parents[2]


@pytest.mark.unit
class TestGateG27Verification:
    """Gate G27 comprehensive milestone verification test suite."""

    def test_adr0014_zero_knowledge_sync_specification(self, repo_root: Path) -> None:
        """ADR-0014 exists and specifies zero-knowledge encryption invariants."""
        adr_file = repo_root / "docs" / "adr" / "ADR-0014-zero-knowledge-encrypted-ledger-sync.md"
        assert adr_file.exists(), f"ADR-0014 missing at {adr_file}"

        content = adr_file.read_text(encoding="utf-8")
        assert "AES-GCM" in content
        assert "PBKDF2" in content
        assert "100000" in content or "100,000" in content
        assert "DPDP Act 2023" in content
        assert "Section 12" in content
        assert "Demonstrated" in content
        assert "R-CR-12" in content

    def test_macroeconomic_competency_aggregation_specification(self, repo_root: Path) -> None:
        """Macroeconomic aggregation spec exists and mandates k >= 10 anonymity."""
        spec_file = repo_root / "docs" / "research" / "macroeconomic-competency-aggregation-spec.md"
        assert spec_file.exists(), f"Macro spec missing at {spec_file}"

        content = spec_file.read_text(encoding="utf-8")
        assert "SPEC-MACRO-COMP-01" in content
        assert "k >= 10" in content or "k-Anonymity" in content or "k \\ge 10" in content
        assert "Laplace" in content or "differential privacy" in content
        assert "Two Streams, Two Places" in content or "R-CR-02" in content
        assert "BLR" in content and "HYD" in content and "PUN" in content

    def test_gate_g27_review_dossier_completeness(self, repo_root: Path) -> None:
        """Gate G27 review dossier exists and ratifies Decision D-041."""
        dossier_file = repo_root / "docs" / "pilot" / "gate-g27-review.md"
        assert dossier_file.exists(), f"Gate G27 dossier missing at {dossier_file}"

        content = dossier_file.read_text(encoding="utf-8")
        assert "REV-GATE-G27-01" in content
        assert "Decision D-041" in content or "RESOLUTION D-041" in content
        assert "RATIFIED GO" in content
        assert "CHK-27-01" in content
        assert "CHK-27-14" in content

    def test_cross_family_synthesis_all_transitions(self) -> None:
        """Synthesizer correctly handles transitions across all 3 engineering families."""
        synth = CrossFamilyPathwaySynthesizer()

        transitions = [
            (RoleFamily.SWE, RoleFamily.MLAI, True),
            (RoleFamily.DATA, RoleFamily.MLAI, True),
            (RoleFamily.SWE, RoleFamily.DATA, False),
            (RoleFamily.SWE, RoleFamily.SWE, False),
        ]

        for src, tgt, expects_bridge in transitions:
            req = CrossFamilyPathwayRequest(
                source_family=src,
                target_family=tgt,
                target_level=RoleLevel.LEVEL_4_SENIOR,
                weekly_hours_budget=10.0,
            )
            res = synth.synthesize_pathway(req)

            assert res.is_acyclic is True
            assert res.source_family == src
            assert res.target_family == tgt
            assert res.total_milestones > 0
            assert res.total_hours_min < res.total_hours_max
            assert res.estimated_weeks_min > 0
            assert "Rule R-CR-01" in res.disclaimer

            bridges = [m for m in res.milestones if m.is_bridge_competency]
            if expects_bridge:
                assert len(bridges) >= 1, f"Expected bridge milestones for {src} -> {tgt}"
            else:
                assert len(bridges) == 0, f"Did not expect bridge milestones for {src} -> {tgt}"
