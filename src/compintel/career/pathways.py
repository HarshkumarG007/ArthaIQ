"""Cross-Family Career Pathway Synthesizer (Phase 27, Task T27.02).

Synthesizes topologically ordered, acyclic cross-family learning pathways
(e.g., SWE -> MLAI, DATA -> MLAI, SWE -> DATA) with calibrated heuristic effort
ranges, discrete verification states, and strict anti-causal guardrails.

Adheres to:
- Rule R-CR-01: No causal compensation promises (CPA 2019 disclaimer).
- Rule R-CR-02: Two Streams, Two Places. Separation from pay evidence.
- Rule R-CR-03: State beats score. Discrete verification states only.
- Rule R-CR-05: Calibrated heuristic effort ranges [H_min, H_max].
- Rule R-CR-11: Anti-credentialism. Focus on demonstrated capability over certificates.
- Rule R-CD-03: Import boundaries. Career only imports schema.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from compintel.career.engine import FilesystemTaxonomyAdapter
from compintel.career.schema import (
    CompetencyNode,
    RoleLevel,
    validate_anti_causal_text,
)
from compintel.schema.enums import RoleFamily


class PathwayMilestone(BaseModel):
    """Single milestone in a cross-family career transition pathway."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_number: int = Field(..., ge=1, description="Topological sequence step.")
    competency_id: str = Field(..., description="Canonical competency identifier.")
    title: str = Field(..., description="Competency title.")
    role_family: RoleFamily = Field(..., description="Source or target role family.")
    cluster: str = Field(..., description="Competency cluster category.")
    level: RoleLevel = Field(..., description="Associated occupational seniority level.")
    prerequisites: list[str] = Field(
        default_factory=list, description="Immediate prerequisite competency IDs."
    )
    min_hours: int = Field(..., ge=1, description="Calibrated minimum heuristic effort hours.")
    max_hours: int = Field(..., ge=2, description="Calibrated maximum heuristic effort hours.")
    is_bridge_competency: bool = Field(
        default=False,
        description="True if this competency bridges foundational gaps from another role family.",
    )
    supported_scenario_id: str | None = Field(
        default=None, description="Practice scenario ID for deterministic proof if available."
    )


class CrossFamilyPathwayRequest(BaseModel):
    """Specification for synthesizing a cross-family career pathway."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_family: RoleFamily = Field(..., description="User's primary/current role family.")
    source_level: RoleLevel = Field(default=RoleLevel.LEVEL_3_MID, description="Current seniority.")
    target_family: RoleFamily = Field(..., description="Aspirational target role family.")
    target_level: RoleLevel = Field(
        default=RoleLevel.LEVEL_4_SENIOR, description="Target seniority tier."
    )
    demonstrated_competency_ids: list[str] = Field(
        default_factory=list, description="Already proven competency IDs to exclude."
    )
    weekly_hours_budget: float = Field(
        default=10.0, ge=1.0, le=40.0, description="Weekly hours dedicated to skill acquisition."
    )


class CrossFamilyPathwayResult(BaseModel):
    """Synthesized cross-family career transition pathway."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_family: RoleFamily = Field(..., description="Source role family.")
    target_family: RoleFamily = Field(..., description="Target role family.")
    target_level: RoleLevel = Field(..., description="Target seniority tier.")
    total_milestones: int = Field(..., ge=0, description="Total learning milestones.")
    total_hours_min: int = Field(..., ge=0, description="Cumulative minimum heuristic hours.")
    total_hours_max: int = Field(..., ge=0, description="Cumulative maximum heuristic hours.")
    estimated_weeks_min: int = Field(..., ge=0, description="Minimum estimated weeks at budget.")
    estimated_weeks_max: int = Field(..., ge=0, description="Maximum estimated weeks at budget.")
    milestones: list[PathwayMilestone] = Field(
        default_factory=list, description="Sequenced milestones."
    )
    is_acyclic: bool = Field(
        default=True, description="Mathematical verification that the pathway DAG has 0 cycles."
    )
    disclaimer: str = Field(
        ...,
        description="Mandatory CPA 2019 statutory disclaimer (Rule R-CR-01).",
    )


# Canonical practice scenario mappings for deterministic flaw-finding verification
_SCENARIO_MAP: dict[str, str] = {
    # DATA Family Scenarios
    "data.anl.l2_sql_basic": "SCEN-DATA-01-SQL",
    "data.anl.l2_eda": "SCEN-DATA-02-EDA",
    "data.sci.l3_exp_design": "SCEN-DATA-03-EXP",
    "data.gen.l2_prob_decomp": "SCEN-DATA-04-DECOMP",
    "data.gen.l2_ethics": "SCEN-DATA-05-ETHICS",
    "data.sci.l3_feat_eng": "SCEN-DATA-06-FEATENG",
    "data.sci.l4_bigdata": "SCEN-DATA-07-BIGDATA",
    # SWE Family Scenarios
    "swe.core.l2_concurrency": "SCEN-SWE-01-CONCUR",
    "swe.sec.l3_owasp_top10": "SCEN-SWE-02-SEC",
    "swe.db.l3_query_perf": "SCEN-SWE-03-DB",
    "swe.arch.l2_api_design": "SCEN-SWE-04-API",
    "swe.test.l2_unit_tdd": "SCEN-SWE-05-TEST",
    "swe.rel.l3_observability": "SCEN-SWE-06-OBS",
    "swe.arch.l4_event_driven": "SCEN-SWE-07-DIST",
    "swe.sys.l4_dist_consensus": "SCEN-SWE-07-DIST",
    # MLAI Family Scenarios
    "mlai.core.l2_neural_backprop": "SCEN-MLAI-01-TENS",
    "mlai.core.l3_transformer_attn": "SCEN-MLAI-02-LEAK",
    "mlai.eval.l2_leakage_audit": "SCEN-MLAI-02-LEAK",
    "mlai.ops.l4_quant_serving": "SCEN-MLAI-03-DEPLOY",
    "mlai.core.l3_repr_learning": "SCEN-MLAI-04-VEC",
    "mlai.ops.l4_dist_training": "SCEN-MLAI-05-DIST",
    "mlai.eval.l3_conformal_calib": "SCEN-MLAI-06-DRIFT",
    "mlai.gen.l3_guardrails": "SCEN-MLAI-07-GUARD",
}


class CrossFamilyPathwaySynthesizer:
    """Synthesizes cross-family learning pathways with topological monotonicity."""

    def __init__(self, adapter: FilesystemTaxonomyAdapter | None = None) -> None:
        """Initialize synthesizer with taxonomy adapter."""
        self.adapter = adapter or FilesystemTaxonomyAdapter()

    def synthesize_pathway(self, request: CrossFamilyPathwayRequest) -> CrossFamilyPathwayResult:
        """Synthesize a topologically ordered cross-family learning pathway."""
        demonstrated = set(request.demonstrated_competency_ids)
        src_fam = request.source_family
        tgt_fam = request.target_family

        # 1. Load target family graph and rubrics
        tgt_graph = self.adapter.get_competency_graph(family=tgt_fam.value)
        tgt_rubric_map = self.adapter.get_all_rubrics(family=tgt_fam.value)

        # 2. Select target nodes at or below target level
        required_nodes: dict[str, CompetencyNode] = {}
        for node in tgt_graph.nodes:
            min_target_level = min(lvl.value for lvl in node.target_levels)
            if min_target_level <= request.target_level.value and node.id not in demonstrated:
                required_nodes[node.id] = node

        # 3. Handle cross-family bridge dependencies
        # When transitioning SWE -> MLAI, engineers bridge via exploratory data & exp design
        # When transitioning DATA -> MLAI, practitioners bridge via structures & concurrency
        bridge_nodes: dict[str, CompetencyNode] = {}
        bridge_rubric_map: dict[str, Any] = {}

        if src_fam == RoleFamily.SWE and tgt_fam == RoleFamily.MLAI:
            data_graph = self.adapter.get_competency_graph(family="DATA")
            d_map = {n.id: n for n in data_graph.nodes}
            r_map = self.adapter.get_all_rubrics(family="DATA")

            foundational_bridge_ids = ["data.anl.l2_eda", "data.sci.l3_exp_design"]
            for f_id in foundational_bridge_ids:
                if f_id in d_map and f_id not in demonstrated:
                    bridge_nodes[f_id] = d_map[f_id]
                    if f_id in r_map:
                        bridge_rubric_map[f_id] = r_map[f_id]

        elif src_fam == RoleFamily.DATA and tgt_fam == RoleFamily.MLAI:
            swe_graph = self.adapter.get_competency_graph(family="SWE")
            s_map = {n.id: n for n in swe_graph.nodes}
            r_map = self.adapter.get_all_rubrics(family="SWE")

            foundational_bridge_ids = [
                "swe.core.l2_data_structures",
                "swe.core.l2_concurrency",
            ]
            for f_id in foundational_bridge_ids:
                if f_id in s_map and f_id not in demonstrated:
                    bridge_nodes[f_id] = s_map[f_id]
                    if f_id in r_map:
                        bridge_rubric_map[f_id] = r_map[f_id]

        # Combine candidate nodes
        all_candidate_nodes: dict[str, CompetencyNode] = {**bridge_nodes, **required_nodes}
        combined_rubrics = {**tgt_rubric_map, **bridge_rubric_map}

        # 4. Topological sort with Kahn's algorithm and priority queue
        in_degree: dict[str, int] = dict.fromkeys(all_candidate_nodes, 0)
        adj_list: dict[str, list[str]] = defaultdict(list)

        for nid, node in all_candidate_nodes.items():
            for prereq in node.prerequisite_ids:
                if prereq in all_candidate_nodes:
                    adj_list[prereq].append(nid)
                    in_degree[nid] += 1

        # Priority queue elements: (bridge_rank, min_level_val, node_id)
        # bridge_rank=0 for bridge competencies so foundations are prioritized
        pq: list[tuple[int, int, str]] = []
        for nid, deg in in_degree.items():
            if deg == 0:
                node = all_candidate_nodes[nid]
                bridge_rank = 0 if nid in bridge_nodes else 1
                min_lvl = min(lvl.value for lvl in node.target_levels)
                heapq.heappush(pq, (bridge_rank, min_lvl, nid))

        sorted_node_ids: list[str] = []
        while pq:
            _, _, curr = heapq.heappop(pq)
            sorted_node_ids.append(curr)

            for neighbor in sorted(adj_list[curr]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    nb_node = all_candidate_nodes[neighbor]
                    b_rank = 0 if neighbor in bridge_nodes else 1
                    n_min_lvl = min(lvl.value for lvl in nb_node.target_levels)
                    heapq.heappush(pq, (b_rank, n_min_lvl, neighbor))

        is_acyclic = len(sorted_node_ids) == len(all_candidate_nodes)

        # 5. Build PathwayMilestones and accumulate heuristic effort
        milestones: list[PathwayMilestone] = []
        total_h_min = 0
        total_h_max = 0

        for step_idx, nid in enumerate(sorted_node_ids, start=1):
            node = all_candidate_nodes[nid]
            rubric = combined_rubrics.get(nid)

            min_h = rubric.effort_hours.min_hours if rubric and rubric.effort_hours else 20
            max_h = rubric.effort_hours.max_hours if rubric and rubric.effort_hours else 60

            total_h_min += min_h
            total_h_max += max_h

            milestone_level = min(node.target_levels, key=lambda lvl: lvl.value)

            milestones.append(
                PathwayMilestone(
                    step_number=step_idx,
                    competency_id=node.id,
                    title=node.title,
                    role_family=node.role_family,
                    cluster=node.category.value,
                    level=milestone_level,
                    prerequisites=[p for p in node.prerequisite_ids if p in all_candidate_nodes],
                    min_hours=min_h,
                    max_hours=max_h,
                    is_bridge_competency=(nid in bridge_nodes),
                    supported_scenario_id=_SCENARIO_MAP.get(node.id),
                )
            )

        budget = max(1.0, request.weekly_hours_budget)
        weeks_min = math.ceil(total_h_min / budget)
        weeks_max = math.ceil(total_h_max / budget)

        disclaimer = validate_anti_causal_text(
            "Empirical transition pathway based on labour market taxonomy. "
            "Completing milestones does not constitute an appraisal, employment guarantee, "
            "or promise of compensation increase (Rule R-CR-01).",
            "disclaimer",
        )

        return CrossFamilyPathwayResult(
            source_family=src_fam,
            target_family=tgt_fam,
            target_level=request.target_level,
            total_milestones=len(milestones),
            total_hours_min=total_h_min,
            total_hours_max=total_h_max,
            estimated_weeks_min=weeks_min,
            estimated_weeks_max=weeks_max,
            milestones=milestones,
            is_acyclic=is_acyclic,
            disclaimer=disclaimer,
        )
