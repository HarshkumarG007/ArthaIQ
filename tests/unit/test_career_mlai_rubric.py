"""Unit tests for MLAI calibrated difficulty & effort heuristic rubrics (Task T19.03).

Verifies Rule R-CR-05 compliance:
- Learning & application difficulty anchored on 1.0-5.0 scale.
- Heuristic effort hours ranges (no single-point false precision).
- Mandatory is_heuristic=True and disclaimer presence.
- Zero causal pay or advancement promises.
- 100% coverage over canonical MLAI family competency graph nodes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from compintel.career.mlai_graph import load_mlai_family_graph
from compintel.career.mlai_rubric import (
    DEFAULT_MLAI_RUBRICS_PATH,
    HEURISTIC_DISCLAIMER,
    build_mlai_difficulty_rubrics_manifest,
    export_mlai_difficulty_rubrics,
    get_mlai_competency_rubric,
    load_mlai_difficulty_rubrics,
)
from compintel.career.schema import (
    DifficultyRubricEntry,
    EffortRange,
)


def test_mlai_rubrics_file_exists_and_loads() -> None:
    """Verify config/taxonomy/difficulty_rubrics_mlai.json exists and loads into schema."""
    assert DEFAULT_MLAI_RUBRICS_PATH.is_file(), f"Missing {DEFAULT_MLAI_RUBRICS_PATH}"
    manifest = load_mlai_difficulty_rubrics()

    assert manifest.schema_version == "1.0.0"
    assert manifest.role_family == "MLAI"
    assert HEURISTIC_DISCLAIMER in manifest.heuristic_disclaimer
    assert len(manifest.entries) == 15


def test_mlai_learning_and_application_anchors_coverage() -> None:
    """Verify both 5-point anchor scales exist with valid levels and descriptions."""
    manifest = load_mlai_difficulty_rubrics()

    learning_levels = [a.level for a in manifest.learning_anchors]
    application_levels = [a.level for a in manifest.application_anchors]

    assert learning_levels == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert application_levels == [1.0, 2.0, 3.0, 4.0, 5.0]

    for anchor in manifest.learning_anchors + manifest.application_anchors:
        assert len(anchor.label) >= 3
        assert len(anchor.anchor_description) >= 10
        assert len(anchor.typical_signals) >= 1


def test_all_mlai_manifest_competencies_have_rubrics() -> None:
    """Verify all 15 MLAI graph nodes have a calibrated rubric entry."""
    graph = load_mlai_family_graph()
    rubric_manifest = load_mlai_difficulty_rubrics()

    rubric_node_ids = {entry.node_id for entry in rubric_manifest.entries}
    graph_node_ids = {node.id for node in graph.nodes}

    assert rubric_node_ids == graph_node_ids
    assert len(rubric_node_ids) == 15


def test_mlai_effort_ranges_are_strictly_valid() -> None:
    """Verify effort hours are expressed as valid ranges (min < max), never lone points."""
    manifest = load_mlai_difficulty_rubrics()

    for entry in manifest.entries:
        assert entry.effort_hours.min_hours < entry.effort_hours.max_hours
        assert entry.effort_hours.min_hours >= 1
        assert entry.effort_hours.max_hours <= 200
        assert entry.is_heuristic is True
        assert HEURISTIC_DISCLAIMER in entry.disclaimer

    # Inverted range must raise ValidationError
    with pytest.raises(ValidationError, match="must be strictly less than max_hours"):
        EffortRange(min_hours=40, max_hours=20)

    # Identical range (single point) must raise ValidationError
    with pytest.raises(ValidationError, match="must be strictly less than max_hours"):
        EffortRange(min_hours=30, max_hours=30)


def test_mlai_difficulty_bounds_and_anti_causal_invariants() -> None:
    """Verify difficulty ratings are bounded in [1.0, 5.0] and rationales reject causal pay."""
    manifest = load_mlai_difficulty_rubrics()

    for entry in manifest.entries:
        assert 1.0 <= entry.learning_difficulty <= 5.0
        assert 1.0 <= entry.application_difficulty <= 5.0
        assert len(entry.learning_rationale) >= 10
        assert len(entry.application_rationale) >= 10

    # Attempting to construct entry with causal pay claim must fail validation
    with pytest.raises(ValidationError, match="R-CR-01"):
        DifficultyRubricEntry(
            node_id="mlai.test.invalid",
            learning_difficulty=2.0,
            application_difficulty=2.0,
            effort_hours=EffortRange(min_hours=10, max_hours=20),
            learning_rationale="Mastering this boosts your salary by 20% LPA.",
            application_rationale="Valid application description.",
            is_heuristic=True,
            disclaimer=HEURISTIC_DISCLAIMER,
        )


def test_get_mlai_competency_rubric_lookup() -> None:
    """Verify individual node lookup returns correct entry or raises KeyError."""
    rubric = get_mlai_competency_rubric("mlai.core.l3_transformer_attn")
    assert rubric.node_id == "mlai.core.l3_transformer_attn"
    assert rubric.learning_difficulty == 3.5
    assert rubric.application_difficulty == 3.5
    assert rubric.effort_hours.min_hours == 35
    assert rubric.effort_hours.max_hours == 60

    with pytest.raises(KeyError, match="not found in difficulty rubrics"):
        get_mlai_competency_rubric("nonexistent_node_id")


def test_export_and_deterministic_serialization(tmp_path: Path) -> None:
    """Verify deterministic JSON serialization and checksum stability."""
    temp_file = tmp_path / "difficulty_rubrics_mlai.json"
    path1, checksum1 = export_mlai_difficulty_rubrics(temp_file)
    path2, checksum2 = export_mlai_difficulty_rubrics(temp_file)

    assert path1 == path2
    assert checksum1 == checksum2
    assert len(checksum1) == 64

    # Direct in-memory build
    manifest = build_mlai_difficulty_rubrics_manifest()
    assert len(manifest.entries) == 15
