"""Unit tests for Software Engineering (SWE) competency graph (Task T16.02).

Verifies DAG validation, topological ordering, prerequisite closure,
and career roadmap generation for the SWE role family.
"""

from __future__ import annotations

from pathlib import Path

from compintel.career.schema import (
    CompetencyCategory,
    RoleLevel,
    TaxonomyLicense,
    TaxonomySource,
)
from compintel.career.swe_graph import (
    DEFAULT_SWE_GRAPH_PATH,
    export_swe_family_graph,
    get_swe_career_roadmap,
    get_swe_prerequisite_closure,
    load_swe_family_graph,
)
from compintel.career.validators import (
    validate_competency_graph,
    validate_graph_acyclicity,
)
from compintel.schema.enums import RoleFamily


def test_canonical_swe_graph_file_exists_and_valid() -> None:
    """Verify that canonical competency_graph_swe.json exists and passes all validators."""
    assert DEFAULT_SWE_GRAPH_PATH.is_file(), f"Missing {DEFAULT_SWE_GRAPH_PATH}"

    manifest = load_swe_family_graph()
    assert manifest.graph_id == "competency-graph-swe-family-v1"
    assert manifest.role_family == RoleFamily.SWE
    assert len(manifest.nodes) == 15

    # Run composite CI validator across all 5 checks
    validate_competency_graph(manifest.nodes)

    # Verify all difficulty rubrics are marked heuristic
    for node in manifest.nodes:
        assert node.difficulty.is_heuristic is True
        assert 1.0 <= node.difficulty.learning_difficulty <= 5.0
        assert 1.0 <= node.difficulty.application_difficulty <= 5.0


def test_swe_prerequisite_closure_traversal() -> None:
    """Verify transitive prerequisite closure is computed in valid topological order."""
    manifest = load_swe_family_graph()
    closure = get_swe_prerequisite_closure("swe.sys.l4_dist_consensus", manifest)

    # Direct prerequisites: swe.core.l3_memory_perf, swe.arch.l3_microservices
    assert "swe.core.l3_memory_perf" in closure
    assert "swe.arch.l3_microservices" in closure
    # Transitive prerequisites:
    assert "swe.core.l2_concurrency" in closure
    assert "swe.core.l2_data_structures" in closure
    assert "swe.arch.l2_api_design" in closure

    # In topological order: data structures must precede concurrency, which precedes memory
    assert closure.index("swe.core.l2_data_structures") < closure.index("swe.core.l2_concurrency")
    assert closure.index("swe.core.l2_concurrency") < closure.index("swe.core.l3_memory_perf")
    # API design must precede microservices
    assert closure.index("swe.arch.l2_api_design") < closure.index("swe.arch.l3_microservices")


def test_swe_career_roadmap_generation() -> None:
    """Verify roadmap towards Mid (Level 3) includes L2 and L3 skills, excluding L4."""
    manifest = load_swe_family_graph()
    roadmap = get_swe_career_roadmap(
        current_skills=set(),
        target_level=RoleLevel.LEVEL_3_MID,
        manifest=manifest,
    )

    # Level 4 skills must NOT be in a Level 3 roadmap
    assert "swe.sys.l4_dist_consensus" not in roadmap
    assert "swe.arch.l4_event_driven" not in roadmap
    assert "swe.sec.l4_crypto_dpdp" not in roadmap

    # Essential Level 2 prerequisites must be included
    assert "swe.gen.l2_git_hygiene" in roadmap
    assert "swe.core.l2_data_structures" in roadmap
    assert "swe.arch.l2_api_design" in roadmap

    # Roadmap order must be topologically valid
    full_order = validate_graph_acyclicity(manifest.nodes)
    filtered_order = [n_id for n_id in full_order if n_id in roadmap]
    assert roadmap == filtered_order


def test_swe_career_roadmap_with_acquired_skills() -> None:
    """Verify that already possessed competencies are excluded from the roadmap."""
    manifest = load_swe_family_graph()
    acquired = {"swe.gen.l2_git_hygiene", "swe.core.l2_data_structures"}

    roadmap = get_swe_career_roadmap(
        current_skills=acquired,
        target_level=RoleLevel.LEVEL_3_MID,
        manifest=manifest,
    )

    assert "swe.gen.l2_git_hygiene" not in roadmap
    assert "swe.core.l2_data_structures" not in roadmap
    # Downstream dependents must still be included
    assert "swe.core.l2_concurrency" in roadmap


def test_deterministic_swe_graph_serialization(tmp_path: Path) -> None:
    """Verify multiple export passes produce bit-for-bit identical manifests."""
    dir1 = tmp_path / "graph1"
    dir2 = tmp_path / "graph2"

    m1, p1 = export_swe_family_graph(dir1)
    m2, p2 = export_swe_family_graph(dir2)

    assert m1.checksum_sha256 == m2.checksum_sha256
    assert p1.read_bytes() == p2.read_bytes()


def test_swe_provenance_and_licensing_compliance() -> None:
    """Verify all 15 nodes possess valid open labour framework provenance."""
    manifest = load_swe_family_graph()

    for node in manifest.nodes:
        prov = node.provenance
        if prov.source_id == TaxonomySource.ONET_28_0:
            assert prov.license == TaxonomyLicense.CC_BY_4_0
            assert "o*net" in prov.attribution_text.lower()
        elif prov.source_id == TaxonomySource.ESCO_1_1_1:
            assert prov.license == TaxonomyLicense.EU_OPEN_REUSE
            assert "european commission" in prov.attribution_text.lower()
        else:
            raise AssertionError(f"Unexpected source {prov.source_id} for node {node.id}")


def test_all_five_categories_represented_in_swe_graph() -> None:
    """Verify all 5 SWE competency categories are represented in the graph."""
    manifest = load_swe_family_graph()
    categories = {node.category for node in manifest.nodes}

    assert CompetencyCategory.SYSTEMS_ARCHITECTURE in categories
    assert CompetencyCategory.APPLICATION_DEVELOPMENT in categories
    assert CompetencyCategory.SECURITY_RELIABILITY in categories
    assert CompetencyCategory.DEV_WORKFLOW in categories
    assert CompetencyCategory.TESTING_QUALITY in categories
