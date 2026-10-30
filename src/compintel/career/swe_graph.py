"""Directed Acyclic Graph (DAG) for Software Engineering (SWE) competencies (Task T16.02).

Assembles and manages the competency graph across Junior (Level 2), Mid (Level 3),
and Senior (Level 4) roles for Software Engineers with full provenance,
heuristic rubrics, and CI validation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from compintel.career.ingestion import ONET_STATUTORY_ATTRIBUTION
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
    validate_competency_graph,
    validate_graph_acyclicity,
)
from compintel.schema.enums import RoleFamily

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_TAXONOMY_DIR = REPO_ROOT / "config" / "taxonomy"
DEFAULT_SWE_GRAPH_PATH = CONFIG_TAXONOMY_DIR / "competency_graph_swe.json"

ESCO_STATUTORY_ATTRIBUTION_ADAPTED = (
    "Source: European Skills, Competences, Qualifications and Occupations "
    "(ESCO v1.1.1), European Commission. Reused and adapted under European "
    "Commission open reuse policy (Decision 2011/833/EU)."
)


def _make_onet_provenance(code: str) -> TaxonomyProvenance:
    return TaxonomyProvenance(
        source_id=TaxonomySource.ONET_28_0,
        source_code=code,
        license=TaxonomyLicense.CC_BY_4_0,
        attribution_required=True,
        attribution_text=ONET_STATUTORY_ATTRIBUTION,
        modified_flag=True,
        curator="ArthaIQ Taxonomy Panel",
        curated_date="2026-10-30",
    )


def _make_esco_provenance(code: str) -> TaxonomyProvenance:
    return TaxonomyProvenance(
        source_id=TaxonomySource.ESCO_1_1_1,
        source_code=code,
        license=TaxonomyLicense.EU_OPEN_REUSE,
        attribution_required=True,
        attribution_text=ESCO_STATUTORY_ATTRIBUTION_ADAPTED,
        modified_flag=True,
        curator="ArthaIQ Taxonomy Panel",
        curated_date="2026-10-30",
    )


_SWE_FAMILY_NODES_DATA: list[dict[str, Any]] = [
    # ------------------ Level 2: Junior / Foundations & Core Skills ------------------
    {
        "id": "swe.gen.l2_git_hygiene",
        "title": "Git Workflow and Trunk-Based Hygiene",
        "description": (
            "Maintain clean trunk-based commit histories, atomic diffs, interactive "
            "rebase conflict resolution, and pull request hygiene."
        ),
        "category": CompetencyCategory.DEV_WORKFLOW,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.SWE.001"),
    },
    {
        "id": "swe.core.l2_data_structures",
        "title": "Algorithmic Complexity and Core Data Structures",
        "description": (
            "Analyze asymptotic time and space complexity, hash collision strategies, "
            "and tree/graph representations for low-latency execution."
        ),
        "category": CompetencyCategory.SYSTEMS_ARCHITECTURE,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1252.00.T01"),
    },
    {
        "id": "swe.core.l2_concurrency",
        "title": "Concurrency Primitives and Thread Safety",
        "description": (
            "Design multithreaded and asynchronous routines using mutexes, read-write "
            "locks, atomic variables, and deadlock detection."
        ),
        "category": CompetencyCategory.SYSTEMS_ARCHITECTURE,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": ["swe.core.l2_data_structures"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1252.00.T02"),
    },
    {
        "id": "swe.arch.l2_api_design",
        "title": "Contract-First API Architecture and Idempotency",
        "description": (
            "Design REST and gRPC API contracts with RFC 9457 problem details, semantic "
            "versioning, and strict idempotency keys for mutative endpoints."
        ),
        "category": CompetencyCategory.APPLICATION_DEVELOPMENT,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1254.00.T01"),
    },
    {
        "id": "swe.test.l2_unit_tdd",
        "title": "Automated Unit Testing and Test Isolation",
        "description": (
            "Author deterministic unit test suites with test doubles, hermetic fixture "
            "isolation, property testing, and high statement coverage."
        ),
        "category": CompetencyCategory.TESTING_QUALITY,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.SWE.002"),
    },
    {
        "id": "swe.ops.l2_container_docker",
        "title": "Container Packaging and Minimal Base Images",
        "description": (
            "Author multi-stage container builds, non-root user execution, minimal attack "
            "surfaces, and reproducible image digest pinning."
        ),
        "category": CompetencyCategory.DEV_WORKFLOW,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.SWE.003"),
    },
    # ------------------ Level 3: Mid / Architecture, Resiliency & Quality ------------------
    {
        "id": "swe.core.l3_memory_perf",
        "title": "Memory Profiling and Resource Management",
        "description": (
            "Profile process heap allocation, identify memory leaks, manage connection "
            "lifecycles, and optimize allocator throughput."
        ),
        "category": CompetencyCategory.SYSTEMS_ARCHITECTURE,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["swe.core.l2_concurrency"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 4.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1252.00.T03"),
    },
    {
        "id": "swe.arch.l3_microservices",
        "title": "Microservice Resiliency and Fault Isolation",
        "description": (
            "Implement circuit breakers, exponential backoff, bulkhead isolation, "
            "and graceful degradation in distributed microservices."
        ),
        "category": CompetencyCategory.APPLICATION_DEVELOPMENT,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["swe.arch.l2_api_design"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 4.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1252.00.T04"),
    },
    {
        "id": "swe.db.l3_query_perf",
        "title": "Relational Indexing and Query Performance",
        "description": (
            "Optimize database query execution plans, design composite B-tree indexes, "
            "resolve table lock contention, and prevent N+1 query patterns."
        ),
        "category": CompetencyCategory.APPLICATION_DEVELOPMENT,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["swe.arch.l2_api_design"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1252.00.T05"),
    },
    {
        "id": "swe.sec.l3_owasp_top10",
        "title": "Web Application Security and Input Sanitization",
        "description": (
            "Enforce OWASP Top 10 defenses including parametrized SQL statements, CSP "
            "headers, CSRF tokens, SSRF protection, and cryptographically secure tokens."
        ),
        "category": CompetencyCategory.SECURITY_RELIABILITY,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["swe.arch.l2_api_design", "swe.test.l2_unit_tdd"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 4.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1254.00.T02"),
    },
    {
        "id": "swe.rel.l3_observability",
        "title": "Telemetry, Structured Logging and Distributed Tracing",
        "description": (
            "Instrument services with OpenTelemetry traces, RED metric collection, "
            "and correlation IDs across asynchronous log streams."
        ),
        "category": CompetencyCategory.SECURITY_RELIABILITY,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["swe.arch.l2_api_design"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.SWE.004"),
    },
    {
        "id": "swe.ops.l3_cicd_pipeline",
        "title": "Hermetic CI/CD Pipelines and Automated Rollback",
        "description": (
            "Configure reproducible deployment pipelines with canary gates, automated "
            "health checks, zero-downtime rollouts, and rollback triggers."
        ),
        "category": CompetencyCategory.DEV_WORKFLOW,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": [
            "swe.gen.l2_git_hygiene",
            "swe.ops.l2_container_docker",
            "swe.test.l2_unit_tdd",
        ],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.SWE.005"),
    },
    # ------------------ Level 4: Senior / Distributed Systems & Compliance ------------------
    {
        "id": "swe.sys.l4_dist_consensus",
        "title": "Distributed Consensus and Replicated State",
        "description": (
            "Evaluate distributed consensus protocols (Raft, Paxos), split-brain scenarios, "
            "leader election timeouts, and linearizable consistency."
        ),
        "category": CompetencyCategory.SYSTEMS_ARCHITECTURE,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["swe.core.l3_memory_perf", "swe.arch.l3_microservices"],
        "difficulty": {
            "learning_difficulty": 4.0,
            "application_difficulty": 5.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1252.00.T06"),
    },
    {
        "id": "swe.arch.l4_event_driven",
        "title": "Event-Driven Architecture and Asynchronous Messaging",
        "description": (
            "Architect transactional outbox patterns, message deduplication, at-least-once "
            "delivery guarantees, and dead-letter queue handling."
        ),
        "category": CompetencyCategory.APPLICATION_DEVELOPMENT,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["swe.arch.l3_microservices", "swe.db.l3_query_perf"],
        "difficulty": {
            "learning_difficulty": 4.0,
            "application_difficulty": 4.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1252.00.T07"),
    },
    {
        "id": "swe.sec.l4_crypto_dpdp",
        "title": "Cryptographic Privacy and Verifiable Purge Operations",
        "description": (
            "Implement envelope encryption, keyed hash message authentication, and "
            "verifiable zero-byte hard deletion under DPDP Act 2023 Sec 12."
        ),
        "category": CompetencyCategory.SECURITY_RELIABILITY,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["swe.sec.l3_owasp_top10"],
        "difficulty": {
            "learning_difficulty": 4.0,
            "application_difficulty": 5.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.SWE.006"),
    },
]


def compute_manifest_sha256(nodes: list[CompetencyNode]) -> str:
    """Compute deterministic SHA-256 hash of sorted competency nodes."""
    hasher = hashlib.sha256()
    sorted_nodes = sorted(nodes, key=lambda n: n.id)
    for n in sorted_nodes:
        dumped = json.dumps(n.model_dump(), sort_keys=True)
        hasher.update(dumped.encode("utf-8"))
    return hasher.hexdigest()


def build_swe_family_graph() -> CompetencyGraphManifest:
    """Construct and validate the canonical SWE family CompetencyGraphManifest.

    Returns:
        CompetencyGraphManifest verified by CI validators.
    """
    nodes: list[CompetencyNode] = []
    for raw in _SWE_FAMILY_NODES_DATA:
        rubric = DifficultyRubric(**raw["difficulty"])
        node = CompetencyNode(
            id=raw["id"],
            title=raw["title"],
            description=raw["description"],
            category=raw["category"],
            role_family=RoleFamily.SWE,
            target_levels=raw["target_levels"],
            prerequisite_ids=raw["prerequisite_ids"],
            difficulty=rubric,
            provenance=raw["provenance"],
        )
        nodes.append(node)

    # Sort nodes by id for deterministic serialization
    nodes.sort(key=lambda n: n.id)

    # Execute all 5 CI validators on nodes
    validate_competency_graph(nodes)

    sha256_hash = compute_manifest_sha256(nodes)

    return CompetencyGraphManifest(
        graph_id="competency-graph-swe-family-v1",
        version="1.0.0",
        role_family=RoleFamily.SWE,
        created_at="2026-10-30T12:00:00Z",
        checksum_sha256=sha256_hash,
        nodes=nodes,
    )


def export_swe_family_graph(
    output_dir: Path | None = None,
) -> tuple[CompetencyGraphManifest, Path]:
    """Build, validate, and serialize the SWE family competency DAG.

    Args:
        output_dir: Optional destination directory (defaults to config/taxonomy).

    Returns:
        Tuple containing the manifest and path to the written JSON file.
    """
    manifest = build_swe_family_graph()
    target_dir = output_dir or CONFIG_TAXONOMY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    graph_path = target_dir / "competency_graph_swe.json"

    data_json = json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"

    # Atomic write to prevent test race conditions
    tmp_path = graph_path.with_suffix(".tmp")
    tmp_path.write_text(data_json, encoding="utf-8")
    tmp_path.replace(graph_path)

    return manifest, graph_path


def load_swe_family_graph(graph_path: Path | None = None) -> CompetencyGraphManifest:
    """Load and validate the SWE family competency DAG from disk.

    Args:
        graph_path: Path to competency_graph_swe.json (defaults to canonical path).

    Returns:
        Validated CompetencyGraphManifest.
    """
    target = graph_path or DEFAULT_SWE_GRAPH_PATH
    if not target.is_file():
        manifest, _ = export_swe_family_graph(target.parent)
        return manifest

    raw = json.loads(target.read_text(encoding="utf-8"))
    manifest = CompetencyGraphManifest.model_validate(raw)
    validate_competency_graph(manifest.nodes)
    return manifest


def get_swe_prerequisite_closure(
    node_id: str,
    manifest: CompetencyGraphManifest | None = None,
) -> list[str]:
    """Retrieve full transitive prerequisite chain for an SWE competency node in topological order.

    Args:
        node_id: Target competency node ID.
        manifest: Optional pre-loaded manifest (loads default if None).

    Returns:
        List of prerequisite node IDs in topological order (earliest prerequisite first).
    """
    graph = manifest or load_swe_family_graph()
    node_map = {n.id: n for n in graph.nodes}

    if node_id not in node_map:
        raise KeyError(f"Competency node '{node_id}' not found in SWE manifest.")

    visited: set[str] = set()

    def _traverse(cur_id: str) -> None:
        for prereq in node_map[cur_id].prerequisite_ids:
            if prereq not in visited:
                visited.add(prereq)
                _traverse(prereq)

    _traverse(node_id)

    # Return topologically sorted prerequisites
    full_order = validate_graph_acyclicity(graph.nodes)
    return [n_id for n_id in full_order if n_id in visited]


def get_swe_career_roadmap(
    current_skills: set[str],
    target_level: RoleLevel,
    manifest: CompetencyGraphManifest | None = None,
) -> list[str]:
    """Compute topologically ordered roadmap of unproven competencies required for target level.

    Args:
        current_skills: Set of already demonstrated competency IDs.
        target_level: Desired engineering seniority level (e.g. LEVEL_3_MID).
        manifest: Optional pre-loaded manifest.

    Returns:
        List of competency node IDs scheduled in topological prerequisite order.
    """
    graph = manifest or load_swe_family_graph()

    # Identify target competency nodes for target_level
    target_node_ids = {n.id for n in graph.nodes if target_level in n.target_levels}

    # Expand required nodes to include all prerequisite closures
    required_ids: set[str] = set()
    for tid in target_node_ids:
        required_ids.add(tid)
        closure = get_swe_prerequisite_closure(tid, graph)
        required_ids.update(closure)

    # Filter out skills already demonstrated
    unproven_ids = required_ids - current_skills

    # Order unproven nodes topologically
    full_order = validate_graph_acyclicity(graph.nodes)
    return [n_id for n_id in full_order if n_id in unproven_ids]


if __name__ == "__main__":
    manifest, path = export_swe_family_graph()
    sha_short = manifest.checksum_sha256[:16]
    print(f"Exported {path.name} with {len(manifest.nodes)} nodes (SHA-256: {sha_short}...)")
