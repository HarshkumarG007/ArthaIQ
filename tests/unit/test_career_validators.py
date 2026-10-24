"""Unit tests and failing fixtures for Career Architect CI DAG validators (Task T15.10).

Verifies that every validation invariant has a verified failing test fixture:
1. Graph acyclicity & self-reference detection
2. Referential integrity & dangling prerequisite detection
3. Seniority level bound ordering
4. Statutory provenance & licensing compliance
5. Anti-causal copy linting
"""

from __future__ import annotations

import pytest

from compintel.career.schema import (
    CompetencyCategory,
    CompetencyGraphManifest,
    CompetencyNode,
    DifficultyRubric,
    RoleLevel,
    TaxonomyLicense,
    TaxonomyProvenance,
    TaxonomySource,
)
from compintel.career.validators import (
    AntiCausalCopyError,
    DanglingReferenceError,
    GraphCycleError,
    LevelOrderError,
    ProvenanceComplianceError,
    validate_anti_causal_copy,
    validate_competency_graph,
    validate_graph_acyclicity,
    validate_level_bounds,
    validate_provenance_compliance,
    validate_referential_integrity,
)
from compintel.schema.enums import RoleFamily


def make_test_node(
    node_id: str,
    levels: list[RoleLevel],
    prereqs: list[str] | None = None,
    source: TaxonomySource = TaxonomySource.ONET_28_0,
    license_type: TaxonomyLicense = TaxonomyLicense.CC_BY_4_0,
    attribution: str = "Source: O*NET 28.0 (USDOL/ETA), adapted under CC BY 4.0.",
    modified: bool = True,
    title: str = "Standard Competency",
    description: str = "Valid descriptive text about analytics concepts and applications.",
) -> CompetencyNode:
    """Helper factory for valid competency nodes."""
    return CompetencyNode(
        id=node_id,
        title=title,
        description=description,
        category=CompetencyCategory.CORE_ANALYTICS,
        role_family=RoleFamily.DATA,
        target_levels=levels,
        prerequisite_ids=prereqs or [],
        provenance=TaxonomyProvenance(
            source_id=source,
            source_code="15-2051.01",
            license=license_type,
            attribution_required=True,
            attribution_text=attribution,
            modified_flag=modified,
            curator="Lead Reviewer",
            curated_date="2026-10-24",
        ),
        difficulty=DifficultyRubric(
            learning_difficulty=2.5,
            application_difficulty=2.5,
            is_heuristic=True,
        ),
    )


def test_dangling_prerequisite_detected() -> None:
    """Fixture: Node referencing non-existent prerequisite must raise DanglingReferenceError."""
    node1 = make_test_node("data.sql.basics", [RoleLevel.LEVEL_2_JUNIOR])
    node2 = make_test_node(
        "data.sql.advanced",
        [RoleLevel.LEVEL_3_MID],
        prereqs=["data.sql.basics", "data.unknown.phantom_skill"],
    )

    with pytest.raises(DanglingReferenceError, match="references non-existent prerequisite"):
        validate_referential_integrity([node1, node2])


def test_self_referential_cycle_detected() -> None:
    """Fixture: Node depending on itself must raise GraphCycleError."""
    node = make_test_node(
        "data.sql.basics", [RoleLevel.LEVEL_2_JUNIOR], prereqs=["data.sql.basics"]
    )

    with pytest.raises(GraphCycleError, match="Self-referential cyclic dependency"):
        validate_graph_acyclicity([node])


def test_transitive_cycle_detected() -> None:
    """Fixture: Multi-node cyclic loop (A -> B -> C -> A) must raise GraphCycleError."""
    node_a = make_test_node("data.sql.a", [RoleLevel.LEVEL_2_JUNIOR], prereqs=["data.sql.c"])
    node_b = make_test_node("data.sql.b", [RoleLevel.LEVEL_2_JUNIOR], prereqs=["data.sql.a"])
    node_c = make_test_node("data.sql.c", [RoleLevel.LEVEL_2_JUNIOR], prereqs=["data.sql.b"])

    with pytest.raises(GraphCycleError, match="Cyclic dependency detected"):
        validate_graph_acyclicity([node_a, node_b, node_c])


def test_inverted_level_order_detected() -> None:
    """Fixture: Senior Level 4 skill as mandatory prerequisite for Junior Level 2 skill."""
    senior_node = make_test_node("data.arch.distributed", [RoleLevel.LEVEL_4_SENIOR])
    junior_node = make_test_node(
        "data.sql.basics",
        [RoleLevel.LEVEL_2_JUNIOR],
        prereqs=["data.arch.distributed"],
    )

    with pytest.raises(LevelOrderError, match="Inverted level hierarchy"):
        validate_level_bounds([senior_node, junior_node])


def test_provenance_license_mismatch_onet() -> None:
    """Fixture: O*NET source paired with non-CC-BY-4.0 license must fail."""
    invalid_node = make_test_node(
        "data.onet.skill",
        [RoleLevel.LEVEL_2_JUNIOR],
        source=TaxonomySource.ONET_28_0,
        license_type=TaxonomyLicense.EU_OPEN_REUSE,
    )

    with pytest.raises(
        ProvenanceComplianceError, match="O\\*NET source must have license CC-BY-4.0"
    ):
        validate_provenance_compliance([invalid_node])


def test_provenance_license_mismatch_esco() -> None:
    """Fixture: ESCO source paired with non-EU-OPEN-REUSE license must fail."""
    invalid_node = make_test_node(
        "data.esco.skill",
        [RoleLevel.LEVEL_2_JUNIOR],
        source=TaxonomySource.ESCO_1_1_1,
        license_type=TaxonomyLicense.CC_BY_4_0,
    )

    with pytest.raises(
        ProvenanceComplianceError, match="ESCO source must have license EU-OPEN-REUSE"
    ):
        validate_provenance_compliance([invalid_node])


def test_provenance_missing_adaptation_statement() -> None:
    """Fixture: modified_flag=True but attribution lacks adaptation disclosure."""
    node = make_test_node(
        "data.adapted.skill",
        [RoleLevel.LEVEL_2_JUNIOR],
        modified=True,
        attribution="O*NET 28.0 dataset, used under CC BY 4.0 without changes.",
    )

    with pytest.raises(
        ProvenanceComplianceError, match="lacks mandatory adaptation or modification"
    ):
        validate_provenance_compliance([node])


def test_anti_causal_copy_detected() -> None:
    """Fixture: Node containing causal pay promises must fail copy lint."""
    # Create node bypassing field_validator by setting a permissible description then mutating
    raw_node = make_test_node(
        "data.sql.joins",
        [RoleLevel.LEVEL_2_JUNIOR],
        description="Understanding relational joins and foreign key constraints.",
    )
    # Reconstruct with causal description to test the graph-wide copy validator
    causal_node = raw_node.model_copy(
        update={"description": "Master relational joins and earn ₹25 LPA as a data analyst."}
    )

    with pytest.raises(AntiCausalCopyError, match="forbidden causal phrase"):
        validate_anti_causal_copy([causal_node])


def test_valid_dag_manifest_passes_all_checks() -> None:
    """Verify that a valid multi-level DATA family DAG passes all checks and resolves order."""
    n1 = make_test_node("data.math.stats", [RoleLevel.LEVEL_2_JUNIOR])
    n2 = make_test_node(
        "data.sql.aggregations",
        [RoleLevel.LEVEL_2_JUNIOR],
        prereqs=["data.math.stats"],
    )
    n3 = make_test_node(
        "data.sql.window_functions",
        [RoleLevel.LEVEL_3_MID],
        prereqs=["data.sql.aggregations"],
    )
    n4 = make_test_node(
        "data.experiments.ab_testing",
        [RoleLevel.LEVEL_3_MID],
        prereqs=["data.math.stats"],
    )
    n5 = make_test_node(
        "data.ml.causal_inference",
        [RoleLevel.LEVEL_4_SENIOR],
        prereqs=["data.experiments.ab_testing", "data.sql.window_functions"],
    )

    manifest = CompetencyGraphManifest(
        graph_id="graph-data-family-v1",
        version="1.0.0",
        role_family=RoleFamily.DATA,
        nodes=[n5, n4, n3, n2, n1],  # intentionally unordered
        created_at="2026-10-24T18:00:00Z",
        checksum_sha256="c" * 64,
    )

    topological_order = validate_competency_graph(manifest)

    # Invariants on topological order:
    # 1. n1 must precede n2, n3, n4, n5
    # 2. n2 must precede n3
    # 3. n3 and n4 must precede n5
    assert topological_order.index("data.math.stats") < topological_order.index(
        "data.sql.aggregations"
    )
    assert topological_order.index("data.sql.aggregations") < topological_order.index(
        "data.sql.window_functions"
    )
    assert topological_order.index("data.experiments.ab_testing") < topological_order.index(
        "data.ml.causal_inference"
    )
    assert topological_order.index("data.sql.window_functions") < topological_order.index(
        "data.ml.causal_inference"
    )
