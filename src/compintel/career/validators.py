"""CI DAG and Content Validators for ArthaIQ Career Architect (Task T15.10).

Enforces graph topological acyclicity, referential integrity, level bound
consistency, statutory taxonomy provenance, and anti-causal copy linting.
"""

from __future__ import annotations

from graphlib import CycleError, TopologicalSorter
from typing import TYPE_CHECKING

from compintel.career.schema import (
    _COMPILED_CAUSAL_RE,
    CompetencyGraphManifest,
    CompetencyNode,
    TaxonomyLicense,
    TaxonomySource,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class CareerValidationError(ValueError):
    """Base exception for all Career Architect validation failures."""


class GraphCycleError(CareerValidationError):
    """Raised when cyclic prerequisite dependencies are detected in the graph."""


class DanglingReferenceError(CareerValidationError):
    """Raised when a prerequisite node ID does not exist in the graph manifest."""


class LevelOrderError(CareerValidationError):
    """Raised when prerequisite level exceeds dependent competency level."""


class ProvenanceComplianceError(CareerValidationError):
    """Raised when statutory taxonomy provenance metadata is invalid or missing."""


class AntiCausalCopyError(CareerValidationError):
    """Raised when prohibited causal compensation promises are detected in text."""


def validate_referential_integrity(nodes: Sequence[CompetencyNode]) -> None:
    """Validate that all prerequisite node IDs exist in the node set.

    Args:
        nodes: Sequence of competency nodes in the graph.

    Raises:
        DanglingReferenceError: If any prerequisite ID does not exist.
    """
    node_ids = {node.id for node in nodes}
    for node in nodes:
        for prereq_id in node.prerequisite_ids:
            if prereq_id not in node_ids:
                raise DanglingReferenceError(
                    f"Node '{node.id}' references non-existent prerequisite '{prereq_id}'."
                )


def validate_graph_acyclicity(nodes: Sequence[CompetencyNode]) -> list[str]:
    """Validate that the prerequisite dependency graph is acyclic and return topological order.

    Uses standard library `graphlib.TopologicalSorter` to detect cycles and compute
    the valid linear prerequisite scheduling order.

    Args:
        nodes: Sequence of competency nodes in the graph.

    Returns:
        List of node IDs in valid topological order (prerequisites before dependents).

    Raises:
        GraphCycleError: If any cyclic dependency or self-reference exists.
    """
    # Check for direct self-references first
    for node in nodes:
        if node.id in node.prerequisite_ids:
            raise GraphCycleError(
                f"Self-referential cyclic dependency detected on node '{node.id}'."
            )

    # TopologicalSorter expects mapping: node -> set of predecessors (prerequisites)
    graph: dict[str, set[str]] = {node.id: set(node.prerequisite_ids) for node in nodes}
    sorter = TopologicalSorter(graph)

    try:
        topological_order = list(sorter.static_order())
    except CycleError as err:
        cycle_nodes = err.args[1] if len(err.args) > 1 else ()
        cycle_str = " -> ".join(cycle_nodes) if cycle_nodes else "cyclic loop"
        raise GraphCycleError(
            f"Cyclic dependency detected in competency graph: {cycle_str}. "
            "Competency prerequisites must form a strict Directed Acyclic Graph (DAG)."
        ) from err

    return topological_order


def validate_level_bounds(nodes: Sequence[CompetencyNode]) -> None:
    """Validate that prerequisite relationships are logically ordered by seniority level.

    An advanced competency (e.g., Level 4 Senior) cannot be a mandatory prerequisite
    for an entry-level competency (e.g., Level 2 Junior).

    Args:
        nodes: Sequence of competency nodes in the graph.

    Raises:
        LevelOrderError: If prerequisite min level exceeds dependent min level.
    """
    node_map = {node.id: node for node in nodes}
    for node in nodes:
        dependent_min_level = min(node.target_levels)
        for prereq_id in node.prerequisite_ids:
            if prereq_id in node_map:
                prereq_node = node_map[prereq_id]
                prereq_min_level = min(prereq_node.target_levels)
                if prereq_min_level > dependent_min_level:
                    raise LevelOrderError(
                        f"Inverted level hierarchy: Node '{node.id}' (min level "
                        f"{dependent_min_level}) depends on higher-level prerequisite "
                        f"'{prereq_id}' (min level {prereq_min_level}). Prerequisites must "
                        "be at or below the dependent competency level."
                    )


def validate_provenance_compliance(nodes: Sequence[CompetencyNode]) -> None:
    """Validate statutory taxonomy provenance and licensing requirements (Rule R-CR-04).

    Enforces:
    - O*NET 28.0 must use CC-BY-4.0 licence.
    - ESCO 1.1.1 must use EU-OPEN-REUSE licence.
    - If modified_flag is True, attribution text must explicitly state adaptation.

    Args:
        nodes: Sequence of competency nodes in the graph.

    Raises:
        ProvenanceComplianceError: If any provenance rule is violated.
    """
    for node in nodes:
        prov = node.provenance

        if prov.source_id == TaxonomySource.ONET_28_0 and prov.license != TaxonomyLicense.CC_BY_4_0:
            raise ProvenanceComplianceError(
                f"Node '{node.id}': O*NET source must have license CC-BY-4.0, found {prov.license}."
            )
        if (
            prov.source_id == TaxonomySource.ESCO_1_1_1
            and prov.license != TaxonomyLicense.EU_OPEN_REUSE
        ):
            raise ProvenanceComplianceError(
                f"Node '{node.id}': ESCO source must have license EU-OPEN-REUSE, "
                f"found {prov.license}."
            )

        if prov.modified_flag:
            text_lower = prov.attribution_text.lower()
            if "adapt" not in text_lower and "modif" not in text_lower:
                raise ProvenanceComplianceError(
                    f"Node '{node.id}': modified_flag is True, but attribution_text lacks "
                    "mandatory adaptation or modification statement."
                )


def validate_anti_causal_copy(nodes: Sequence[CompetencyNode]) -> None:
    """Verify that no user-facing text contains causal compensation promises (Rule R-CR-01).

    Args:
        nodes: Sequence of competency nodes in the graph.

    Raises:
        AntiCausalCopyError: If forbidden causal pay phrases are detected.
    """
    for node in nodes:
        for field_name, value in [("title", node.title), ("description", node.description)]:
            match = _COMPILED_CAUSAL_RE.search(value)
            if match:
                raise AntiCausalCopyError(
                    f"Node '{node.id}' contains forbidden causal phrase in {field_name}: "
                    f"'{match.group(0)}'. Rule R-CR-01 strictly prohibits causal pay claims."
                )


def validate_competency_graph(
    manifest_or_nodes: CompetencyGraphManifest | Sequence[CompetencyNode],
) -> list[str]:
    """Execute all CI validation checks across a competency graph.

    Args:
        manifest_or_nodes: CompetencyGraphManifest or Sequence of CompetencyNodes.

    Returns:
        List of node IDs in valid topological order.

    Raises:
        CareerValidationError: If any graph or content validation check fails.
    """
    nodes = (
        manifest_or_nodes.nodes
        if isinstance(manifest_or_nodes, CompetencyGraphManifest)
        else list(manifest_or_nodes)
    )

    validate_referential_integrity(nodes)
    topological_order = validate_graph_acyclicity(nodes)
    validate_level_bounds(nodes)
    validate_provenance_compliance(nodes)
    validate_anti_causal_copy(nodes)

    return topological_order
