"""Unit tests for Career Architect competency graph (Task T15.12).

Verifies DAG validation, topological ordering, prerequisite closure,
and career roadmap generation for the DATA role family.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compintel.career.graph import (
    DEFAULT_GRAPH_PATH,
    export_data_family_graph,
    get_career_roadmap,
    get_prerequisite_closure,
    load_data_family_graph,
)
from compintel.career.schema import (
    CompetencyCategory,
    RoleLevel,
)
from compintel.career.validators import (
    validate_competency_graph,
    validate_graph_acyclicity,
)


def test_canonical_graph_file_exists_and_valid() -> None:
    """Verify that canonical competency_graph_data.json exists and passes all validators."""
    assert DEFAULT_GRAPH_PATH.is_file()

    manifest = load_data_family_graph()
    assert manifest.graph_id == "competency-graph-data-family-v1"
    assert manifest.role_family == "DATA"
    assert len(manifest.nodes) == 14

    # Run composite CI validator
    validate_competency_graph(manifest.nodes)

    # Verify all difficulty rubrics are marked heuristic
    for node in manifest.nodes:
        assert node.difficulty.is_heuristic is True
        assert 1.0 <= node.difficulty.learning_difficulty <= 5.0
        assert 1.0 <= node.difficulty.application_difficulty <= 5.0


def test_prerequisite_closure_traversal() -> None:
    """Verify transitive prerequisite closure is computed in valid topological order."""
    manifest = load_data_family_graph()
    closure = get_prerequisite_closure("data.sci.l4_bigdata", manifest)

    # Direct prerequisites: data.anl.l3_sql_adv, data.sci.l3_feat_eng
    assert "data.anl.l3_sql_adv" in closure
    assert "data.sci.l3_feat_eng" in closure
    # Transitive prerequisites:
    assert "data.anl.l2_sql_basic" in closure
    assert "data.anl.l2_hygiene" in closure
    assert "data.sci.l3_ml_supervised" in closure
    assert "data.anl.l2_eda" in closure

    # In topological order: basic SQL must precede advanced SQL
    assert closure.index("data.anl.l2_sql_basic") < closure.index("data.anl.l3_sql_adv")
    # EDA must precede Supervised ML
    assert closure.index("data.anl.l2_eda") < closure.index("data.sci.l3_ml_supervised")


def test_career_roadmap_generation() -> None:
    """Verify roadmap towards Mid (Level 3) includes L2 and L3 skills, excluding L4."""
    manifest = load_data_family_graph()
    roadmap = get_career_roadmap(
        current_skills=set(),
        target_level=RoleLevel.LEVEL_3_MID,
        manifest=manifest,
    )

    roadmap_ids = [n.id for n in roadmap]
    # Level 4 skills must NOT be in a Level 3 roadmap
    assert "data.sci.l4_causal" not in roadmap_ids
    assert "data.sci.l4_bigdata" not in roadmap_ids

    # Essential Level 2 prerequisites must be included
    assert "data.anl.l2_sql_basic" in roadmap_ids
    assert "data.anl.l2_eda" in roadmap_ids

    # Roadmap order must be topologically valid
    full_order = validate_graph_acyclicity(manifest.nodes)
    filtered_order = [n_id for n_id in full_order if n_id in roadmap_ids]
    assert roadmap_ids == filtered_order


def test_career_roadmap_with_acquired_skills() -> None:
    """Verify that already possessed competencies are excluded from the roadmap."""
    manifest = load_data_family_graph()
    acquired = {"data.anl.l2_sql_basic", "data.anl.l2_eda"}

    roadmap = get_career_roadmap(
        current_skills=acquired,
        target_level=RoleLevel.LEVEL_3_MID,
        manifest=manifest,
    )

    roadmap_ids = [n.id for n in roadmap]
    assert "data.anl.l2_sql_basic" not in roadmap_ids
    assert "data.anl.l2_eda" not in roadmap_ids
    assert "data.anl.l3_sql_adv" in roadmap_ids


def test_career_roadmap_category_filter() -> None:
    """Verify filtering roadmap by category."""
    manifest = load_data_family_graph()
    roadmap = get_career_roadmap(
        current_skills=set(),
        target_level=RoleLevel.LEVEL_3_MID,
        target_category=CompetencyCategory.EXPERIMENTATION,
        manifest=manifest,
    )

    roadmap_ids = [n.id for n in roadmap]
    # Target node: data.sci.l3_exp_design (EXPERIMENTATION)
    # Prerequisite: data.anl.l2_eda (STATISTICAL_MODELING)
    assert "data.sci.l3_exp_design" in roadmap_ids
    assert "data.anl.l2_eda" in roadmap_ids
    # Unrelated skill:
    assert "data.anl.l3_sql_adv" not in roadmap_ids


def test_unknown_node_closure_raises_key_error() -> None:
    """Verify querying prerequisite closure for non-existent node raises KeyError."""
    manifest = load_data_family_graph()
    with pytest.raises(KeyError, match="not found in manifest"):
        get_prerequisite_closure("non.existent.node", manifest)


def test_deterministic_graph_export(tmp_path: Path) -> None:
    """Verify export_data_family_graph writes identical bytes across calls."""
    dir1 = tmp_path / "exp1"
    dir2 = tmp_path / "exp2"

    m1, p1 = export_data_family_graph(output_dir=dir1)
    m2, p2 = export_data_family_graph(output_dir=dir2)

    assert m1.checksum_sha256 == m2.checksum_sha256
    assert p1.read_bytes() == p2.read_bytes()
