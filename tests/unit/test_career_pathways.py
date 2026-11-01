"""Unit tests for Cross-Family Career Pathway Synthesizer (Phase 27, Task T27.03).

Validates:
1. Cross-family transition pathways (SWE -> MLAI, DATA -> MLAI, SWE -> DATA).
2. Mathematical DAG acyclicity and topological ordering across multi-family boundaries.
3. Bridge competency identification (e.g., stats bridge for SWE, systems bridge for DATA).
4. Pruning of pre-demonstrated competencies from the pathway.
5. Calibrated heuristic effort range accumulation and pacing calculations.
6. Practice scenario linkage for deterministic flaw-finding verification.
7. Strict anti-causal compliance (Rule R-CR-01) and CPA 2019 disclaimer presence.
"""

from __future__ import annotations

import math

import pytest

from compintel.career.pathways import (
    CrossFamilyPathwayRequest,
    CrossFamilyPathwayResult,
    CrossFamilyPathwaySynthesizer,
)
from compintel.career.schema import RoleLevel
from compintel.schema.enums import RoleFamily


@pytest.fixture
def synthesizer() -> CrossFamilyPathwaySynthesizer:
    """Fixture providing initialized CrossFamilyPathwaySynthesizer."""
    return CrossFamilyPathwaySynthesizer()


@pytest.mark.unit
class TestCrossFamilyPathways:
    """Comprehensive test suite for cross-family career pathways."""

    def test_swe_to_mlai_transition_pathway(
        self, synthesizer: CrossFamilyPathwaySynthesizer
    ) -> None:
        """SWE to MLAI transition generates valid acyclic pathway with statistical bridges."""
        req = CrossFamilyPathwayRequest(
            source_family=RoleFamily.SWE,
            source_level=RoleLevel.LEVEL_3_MID,
            target_family=RoleFamily.MLAI,
            target_level=RoleLevel.LEVEL_4_SENIOR,
            weekly_hours_budget=10.0,
        )
        res = synthesizer.synthesize_pathway(req)

        assert isinstance(res, CrossFamilyPathwayResult)
        assert res.source_family == RoleFamily.SWE
        assert res.target_family == RoleFamily.MLAI
        assert res.target_level == RoleLevel.LEVEL_4_SENIOR
        assert res.is_acyclic is True
        assert res.total_milestones > 0

        # Verify bridge competencies are identified
        bridge_milestones = [m for m in res.milestones if m.is_bridge_competency]
        assert len(bridge_milestones) >= 1
        for b in bridge_milestones:
            assert b.role_family == RoleFamily.DATA

        # Verify topological monotonicity: prerequisites must appear before dependents
        seen_ids: set[str] = set()
        for m in res.milestones:
            for p in m.prerequisites:
                assert p in seen_ids, f"Prerequisite {p} must precede {m.competency_id}"
            seen_ids.add(m.competency_id)

        # Anti-causal disclaimer check
        assert "Rule R-CR-01" in res.disclaimer
        assert "guarantee" in res.disclaimer

    def test_data_to_mlai_transition_pathway(
        self, synthesizer: CrossFamilyPathwaySynthesizer
    ) -> None:
        """DATA to MLAI transition generates valid acyclic pathway with systems bridges."""
        req = CrossFamilyPathwayRequest(
            source_family=RoleFamily.DATA,
            source_level=RoleLevel.LEVEL_3_MID,
            target_family=RoleFamily.MLAI,
            target_level=RoleLevel.LEVEL_4_SENIOR,
            weekly_hours_budget=15.0,
        )
        res = synthesizer.synthesize_pathway(req)

        assert res.is_acyclic is True
        bridge_milestones = [m for m in res.milestones if m.is_bridge_competency]
        assert len(bridge_milestones) >= 1
        for b in bridge_milestones:
            assert b.role_family == RoleFamily.SWE

        # Verify step numbers are sequential 1..N
        for idx, m in enumerate(res.milestones, start=1):
            assert m.step_number == idx

    def test_swe_to_data_transition_pathway(
        self, synthesizer: CrossFamilyPathwaySynthesizer
    ) -> None:
        """SWE to DATA transition generates valid acyclic pathway."""
        req = CrossFamilyPathwayRequest(
            source_family=RoleFamily.SWE,
            source_level=RoleLevel.LEVEL_3_MID,
            target_family=RoleFamily.DATA,
            target_level=RoleLevel.LEVEL_4_SENIOR,
            weekly_hours_budget=10.0,
        )
        res = synthesizer.synthesize_pathway(req)
        assert res.is_acyclic is True
        assert res.target_family == RoleFamily.DATA
        assert res.total_milestones >= 5

    def test_intra_family_progression(self, synthesizer: CrossFamilyPathwaySynthesizer) -> None:
        """Intra-family progression (SWE -> SWE) has zero bridge competencies."""
        req = CrossFamilyPathwayRequest(
            source_family=RoleFamily.SWE,
            source_level=RoleLevel.LEVEL_2_JUNIOR,
            target_family=RoleFamily.SWE,
            target_level=RoleLevel.LEVEL_4_SENIOR,
        )
        res = synthesizer.synthesize_pathway(req)
        assert res.is_acyclic is True
        bridge_milestones = [m for m in res.milestones if m.is_bridge_competency]
        assert len(bridge_milestones) == 0

    def test_pruning_demonstrated_competencies(
        self, synthesizer: CrossFamilyPathwaySynthesizer
    ) -> None:
        """Already demonstrated competencies are pruned from the synthesized pathway."""
        demonstrated = [
            "mlai.core.l2_neural_backprop",
            "mlai.math.l2_linear_algebra",
            "data.anl.l2_eda",
        ]
        req = CrossFamilyPathwayRequest(
            source_family=RoleFamily.SWE,
            target_family=RoleFamily.MLAI,
            demonstrated_competency_ids=demonstrated,
        )
        res = synthesizer.synthesize_pathway(req)

        res_ids = {m.competency_id for m in res.milestones}
        for d_id in demonstrated:
            assert d_id not in res_ids, f"Demonstrated {d_id} should be pruned"

    def test_effort_and_pacing_calculations(
        self, synthesizer: CrossFamilyPathwaySynthesizer
    ) -> None:
        """Pathway accurately calculates hours and pacing weeks according to budget."""
        budget = 12.0
        req = CrossFamilyPathwayRequest(
            source_family=RoleFamily.DATA,
            target_family=RoleFamily.MLAI,
            weekly_hours_budget=budget,
        )
        res = synthesizer.synthesize_pathway(req)

        assert res.total_hours_min < res.total_hours_max
        assert res.estimated_weeks_min == math.ceil(res.total_hours_min / budget)
        assert res.estimated_weeks_max == math.ceil(res.total_hours_max / budget)

    def test_scenario_linkage(self, synthesizer: CrossFamilyPathwaySynthesizer) -> None:
        """Milestones with canonical flaw-finding practice scenarios have scenario IDs."""
        req = CrossFamilyPathwayRequest(
            source_family=RoleFamily.SWE,
            target_family=RoleFamily.MLAI,
            target_level=RoleLevel.LEVEL_4_SENIOR,
        )
        res = synthesizer.synthesize_pathway(req)

        scenario_linked = [m for m in res.milestones if m.supported_scenario_id is not None]
        assert len(scenario_linked) >= 5
        linked_scens = {m.supported_scenario_id for m in scenario_linked}
        assert any("SCEN-MLAI" in str(s) for s in linked_scens)
