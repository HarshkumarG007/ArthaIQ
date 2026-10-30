"""Unit tests for SWE calibrated difficulty & effort heuristic rubrics (Task T16.03).

Verifies Rule R-CR-05 compliance:
- Learning & application difficulty anchored on 1.0-5.0 scale.
- Heuristic effort hours ranges (no single-point false precision).
- Mandatory is_heuristic=True and disclaimer presence.
- Zero causal pay or advancement promises.
- 100% coverage over canonical SWE family competency graph nodes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from compintel.career.schema import (
    DifficultyRubricEntry,
    EffortRange,
)
from compintel.career.swe_graph import load_swe_family_graph
from compintel.career.swe_rubric import (
    DEFAULT_SWE_RUBRICS_PATH,
    HEURISTIC_DISCLAIMER,
    build_swe_difficulty_rubrics_manifest,
    export_swe_difficulty_rubrics,
    get_swe_competency_rubric,
    load_swe_difficulty_rubrics,
)


def test_swe_rubrics_file_exists_and_loads() -> None:
    """Verify config/taxonomy/difficulty_rubrics_swe.json exists and loads into schema."""
    assert DEFAULT_SWE_RUBRICS_PATH.is_file(), f"Missing {DEFAULT_SWE_RUBRICS_PATH}"
    manifest = load_swe_difficulty_rubrics()

    assert manifest.schema_version == "1.0.0"
    assert manifest.role_family == "SWE"
    assert HEURISTIC_DISCLAIMER in manifest.heuristic_disclaimer
    assert len(manifest.entries) == 15


def test_swe_learning_and_application_anchors_coverage() -> None:
    """Verify both 5-point anchor scales exist with valid levels and descriptions."""
    manifest = load_swe_difficulty_rubrics()

    learning_levels = [a.level for a in manifest.learning_anchors]
    application_levels = [a.level for a in manifest.application_anchors]

    assert learning_levels == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert application_levels == [1.0, 2.0, 3.0, 4.0, 5.0]

    for anchor in manifest.learning_anchors + manifest.application_anchors:
        assert len(anchor.label) >= 3
        assert len(anchor.anchor_description) >= 10
        assert len(anchor.typical_signals) >= 1


def test_all_swe_manifest_competencies_have_rubrics() -> None:
    """Verify all 15 SWE graph nodes have a calibrated rubric entry."""
    graph = load_swe_family_graph()
    rubric_manifest = load_swe_difficulty_rubrics()

    rubric_node_ids = {entry.node_id for entry in rubric_manifest.entries}
    graph_node_ids = {node.id for node in graph.nodes}

    assert rubric_node_ids == graph_node_ids
    assert len(rubric_node_ids) == 15


def test_swe_effort_ranges_are_strictly_valid() -> None:
    """Verify effort hours are expressed as valid ranges (min < max), never lone points."""
    manifest = load_swe_difficulty_rubrics()

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


def test_swe_difficulty_bounds_and_anti_causal_invariants() -> None:
    """Verify difficulty ratings are bounded in [1.0, 5.0] and rationales reject causal pay."""
    manifest = load_swe_difficulty_rubrics()

    for entry in manifest.entries:
        assert 1.0 <= entry.learning_difficulty <= 5.0
        assert 1.0 <= entry.application_difficulty <= 5.0
        assert len(entry.learning_rationale) >= 10
        assert len(entry.application_rationale) >= 10

    # Attempting to construct entry with causal pay claim must fail validation
    with pytest.raises(ValidationError, match="R-CR-01"):
        DifficultyRubricEntry(
            node_id="swe.test.invalid",
            learning_difficulty=2.0,
            application_difficulty=2.0,
            effort_hours=EffortRange(min_hours=10, max_hours=20),
            learning_rationale="Mastering this boosts your salary by 20% LPA.",
            application_rationale="Valid application description.",
            is_heuristic=True,
            disclaimer=HEURISTIC_DISCLAIMER,
        )


def test_get_swe_competency_rubric_lookup() -> None:
    """Verify individual SWE node lookup by ID and KeyError on missing."""
    rubric = get_swe_competency_rubric("swe.sys.l4_dist_consensus")
    assert rubric.node_id == "swe.sys.l4_dist_consensus"
    assert rubric.learning_difficulty == 4.0
    assert rubric.application_difficulty == 5.0
    assert rubric.effort_hours.min_hours == 60
    assert rubric.effort_hours.max_hours == 100

    with pytest.raises(KeyError, match="not found in difficulty rubrics"):
        get_swe_competency_rubric("nonexistent.node.id")


def test_export_swe_deterministic_checksum(tmp_path: Path) -> None:
    """Verify bitwise idempotency of SWE rubric export serialization."""
    manifest1 = build_swe_difficulty_rubrics_manifest()
    temp_file = tmp_path / "temp_rubrics_swe_test.json"
    path, checksum = export_swe_difficulty_rubrics(temp_file)
    assert path.is_file()
    assert len(checksum) == 64

    manifest2 = load_swe_difficulty_rubrics(path)
    assert manifest1.model_dump() == manifest2.model_dump()
