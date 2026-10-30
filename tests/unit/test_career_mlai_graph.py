"""Unit tests for Machine Learning & AI (MLAI) competency graph (Task T19.02).

Verifies DAG validation, topological ordering, prerequisite closure,
and career roadmap generation for the MLAI role family.
"""

from __future__ import annotations

from compintel.career.mlai_graph import (
    DEFAULT_MLAI_GRAPH_PATH,
    get_mlai_career_roadmap,
    get_mlai_prerequisite_closure,
    load_mlai_family_graph,
)
from compintel.career.schema import (
    CompetencyCategory,
    RoleLevel,
    TaxonomyLicense,
    TaxonomySource,
    validate_anti_causal_text,
)
from compintel.career.validators import (
    validate_competency_graph,
    validate_graph_acyclicity,
)
from compintel.schema.enums import RoleFamily


def test_canonical_mlai_graph_file_exists_and_valid() -> None:
    """Verify that canonical competency_graph_mlai.json exists and passes all validators."""
    assert DEFAULT_MLAI_GRAPH_PATH.is_file(), f"Missing {DEFAULT_MLAI_GRAPH_PATH}"

    manifest = load_mlai_family_graph()
    assert manifest.graph_id == "competency-graph-mlai-family-v1"
    assert manifest.role_family == RoleFamily.MLAI
    assert len(manifest.nodes) == 15

    # Run composite CI validator across all 5 checks
    validate_competency_graph(manifest.nodes)

    # Verify all difficulty rubrics are marked heuristic
    for node in manifest.nodes:
        assert node.difficulty.is_heuristic is True
        assert 1.0 <= node.difficulty.learning_difficulty <= 5.0
        assert 1.0 <= node.difficulty.application_difficulty <= 5.0


def test_mlai_graph_spans_all_categories() -> None:
    """Verify nodes cover all 5 MLAI categories."""
    manifest = load_mlai_family_graph()
    categories = {n.category for n in manifest.nodes}

    assert CompetencyCategory.MATH_OPTIMIZATION in categories
    assert CompetencyCategory.DEEP_LEARNING in categories
    assert CompetencyCategory.MLOPS_INFRASTRUCTURE in categories
    assert CompetencyCategory.EVALUATION_GOVERNANCE in categories
    assert CompetencyCategory.GENERATIVE_ALIGNMENT in categories


def test_mlai_prerequisite_closure_traversal() -> None:
    """Verify transitive prerequisite closure is computed in valid topological order."""
    manifest = load_mlai_family_graph()
    closure = get_mlai_prerequisite_closure("mlai.gen.l4_preference_dpo", manifest)

    # Direct prerequisites: mlai.core.l3_peft_finetune, mlai.gen.l3_guardrails
    assert "mlai.core.l3_peft_finetune" in closure
    assert "mlai.gen.l3_guardrails" in closure
    # Transitive prerequisites:
    assert "mlai.core.l3_transformer_attn" in closure
    assert "mlai.core.l2_neural_backprop" in closure
    assert "mlai.math.l2_linear_algebra" in closure

    # In topological order: linear algebra precedes backprop, which precedes transformer attention
    assert closure.index("mlai.math.l2_linear_algebra") < closure.index(
        "mlai.core.l2_neural_backprop"
    )
    assert closure.index("mlai.core.l2_neural_backprop") < closure.index(
        "mlai.core.l3_transformer_attn"
    )


def test_mlai_career_roadmap_generation() -> None:
    """Verify roadmap towards Mid (Level 3) includes L2 and L3 skills, excluding L4."""
    manifest = load_mlai_family_graph()
    roadmap = get_mlai_career_roadmap(
        current_skills=set(),
        target_level=RoleLevel.LEVEL_3_MID,
        manifest=manifest,
    )

    # Level 4 skills must NOT be in a Level 3 roadmap
    assert "mlai.ops.l4_dist_training" not in roadmap
    assert "mlai.ops.l4_quant_serving" not in roadmap
    assert "mlai.gen.l4_preference_dpo" not in roadmap
    assert "mlai.eval.l4_dpdp_privacy" not in roadmap

    # Essential Level 2 prerequisites must be included
    assert "mlai.math.l2_linear_algebra" in roadmap
    assert "mlai.core.l2_neural_backprop" in roadmap

    # Roadmap order must be topologically valid
    full_order = validate_graph_acyclicity(manifest.nodes)
    filtered_order = [n_id for n_id in full_order if n_id in roadmap]
    assert roadmap == filtered_order


def test_mlai_career_roadmap_with_acquired_skills() -> None:
    """Verify that already possessed competencies are excluded from the roadmap."""
    manifest = load_mlai_family_graph()
    acquired = {"mlai.math.l2_linear_algebra", "mlai.core.l2_neural_backprop"}

    roadmap = get_mlai_career_roadmap(
        current_skills=acquired,
        target_level=RoleLevel.LEVEL_3_MID,
        manifest=manifest,
    )

    for skill in acquired:
        assert skill not in roadmap


def test_mlai_provenance_and_licence_integrity() -> None:
    """Verify all nodes link to valid O*NET or ESCO provenance with required attributes."""
    manifest = load_mlai_family_graph()
    for node in manifest.nodes:
        prov = node.provenance
        if prov.source_id == TaxonomySource.ONET_28_0:
            assert prov.license == TaxonomyLicense.CC_BY_4_0
            assert "o*net" in prov.attribution_text.lower()
        elif prov.source_id == TaxonomySource.ESCO_1_1_1:
            assert prov.license == TaxonomyLicense.EU_OPEN_REUSE
            assert "european commission" in prov.attribution_text.lower()
        else:
            raise AssertionError(f"Unexpected source {prov.source_id}")


def test_mlai_anti_causal_invariants() -> None:
    """Verify that no MLAI node contains causal compensation claims (Rule R-CR-01)."""
    manifest = load_mlai_family_graph()
    for node in manifest.nodes:
        validate_anti_causal_text(node.title, "title")
        validate_anti_causal_text(node.description, "description")
