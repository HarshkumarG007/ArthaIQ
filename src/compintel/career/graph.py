"""Directed Acyclic Graph (DAG) for DATA family competencies (Task T15.12).

Assembles and manages the competency graph across Junior (Level 2), Mid (Level 3),
and Senior (Level 4) roles for Data Analysts and Data Scientists with full provenance,
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
DEFAULT_GRAPH_PATH = CONFIG_TAXONOMY_DIR / "competency_graph_data.json"

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
        curated_date="2026-10-24",
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
        curated_date="2026-10-24",
    )


_DATA_FAMILY_NODES_DATA: list[dict[str, Any]] = [
    # ------------------ Level 2: Junior / Transversal Foundations ------------------
    {
        "id": "data.gen.l2_prob_decomp",
        "title": "Analytical Reasoning and Problem Decomposition",
        "description": (
            "Deconstruct complex operational or product problems into structured, "
            "verifiable analytical components and hypotheses."
        ),
        "category": CompetencyCategory.CORE_ANALYTICS,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.T.001"),
    },
    {
        "id": "data.gen.l2_ethics",
        "title": "Ethical Data Governance and Privacy Safeguards",
        "description": (
            "Apply statutory data protection principles, pseudonymization methods, "
            "and DPDP compliance checks across processing pipelines."
        ),
        "category": CompetencyCategory.DATA_ENGINEERING,
        "target_levels": [
            RoleLevel.LEVEL_2_JUNIOR,
            RoleLevel.LEVEL_3_MID,
            RoleLevel.LEVEL_4_SENIOR,
        ],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.T.004"),
    },
    {
        "id": "data.anl.l2_sql_basic",
        "title": "Relational SQL Querying and Table Joins",
        "description": (
            "Formulate efficient relational queries, table joins, group-by aggregations, "
            "and filtered views for analytical reporting."
        ),
        "category": CompetencyCategory.CORE_ANALYTICS,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.02.T01"),
    },
    {
        "id": "data.anl.l2_eda",
        "title": "Exploratory Data Analysis and Distributions",
        "description": (
            "Conduct exploratory analysis, assess central tendencies, empirical distributions, "
            "and identify anomalies or skewness."
        ),
        "category": CompetencyCategory.STATISTICAL_MODELING,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.02.T05"),
    },
    {
        "id": "data.anl.l2_hygiene",
        "title": "Data Hygiene and Anomaly Auditing",
        "description": (
            "Inspect raw datasets for schema drift, null rates, duplicated keys, and "
            "distributional outliers prior to aggregation."
        ),
        "category": CompetencyCategory.CORE_ANALYTICS,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": ["data.anl.l2_sql_basic"],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.02.T03"),
    },
    # ------------------ Level 3: Mid-Level Analytics & Data Science ------------------
    {
        "id": "data.anl.l3_sql_adv",
        "title": "Advanced SQL Window Functions and Partitions",
        "description": (
            "Execute analytical window frames, partition-level cumulative metrics, and "
            "sequential ranking for cohorts."
        ),
        "category": CompetencyCategory.CORE_ANALYTICS,
        "target_levels": [RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": ["data.anl.l2_sql_basic"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.02.T02"),
    },
    {
        "id": "data.anl.l3_dashboard",
        "title": "Dashboard Architecture and Business Metric Design",
        "description": (
            "Design responsive dashboards and self-serve reporting views translating business "
            "questions into operational KPIs."
        ),
        "category": CompetencyCategory.BUSINESS_COMMUNICATION,
        "target_levels": [RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": ["data.anl.l2_eda", "data.anl.l2_sql_basic"],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.02.T04"),
    },
    {
        "id": "data.gen.l3_docs",
        "title": "Technical Documentation and Reproducibility Standards",
        "description": (
            "Document analytical methodologies, dataset provenance, pipeline assumptions, "
            "and execution environments."
        ),
        "category": CompetencyCategory.BUSINESS_COMMUNICATION,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["data.gen.l2_prob_decomp"],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.T.002"),
    },
    {
        "id": "data.gen.l3_stakeholder",
        "title": "Stakeholder Uncertainty and Evidence Communication",
        "description": (
            "Communicate probabilistic estimates, confidence intervals, and honest abstentions "
            "to non-technical partners."
        ),
        "category": CompetencyCategory.BUSINESS_COMMUNICATION,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["data.gen.l2_prob_decomp"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 4.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.T.003"),
    },
    {
        "id": "data.sci.l3_exp_design",
        "title": "Statistical Hypothesis Testing and A/B Experimentation",
        "description": (
            "Design randomized online experiments, sample power sizing, hypothesis testing, "
            "and false-positive control."
        ),
        "category": CompetencyCategory.EXPERIMENTATION,
        "target_levels": [RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": ["data.anl.l2_eda"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 4.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.01.T01"),
    },
    {
        "id": "data.sci.l3_ml_supervised",
        "title": "Supervised Predictive Modeling and Cross-Validation",
        "description": (
            "Train and evaluate supervised regression and classification models using "
            "calibrated metrics and rigorous cross-validation."
        ),
        "category": CompetencyCategory.STATISTICAL_MODELING,
        "target_levels": [RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": ["data.anl.l2_eda"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.01.T02"),
    },
    {
        "id": "data.sci.l3_feat_eng",
        "title": "Feature Engineering and Leakage Isolation",
        "description": (
            "Construct predictive features, temporal splitting strategies, and data leakage "
            "guards across tabular datasets."
        ),
        "category": CompetencyCategory.DATA_ENGINEERING,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["data.anl.l2_hygiene", "data.sci.l3_ml_supervised"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 4.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.01.T03"),
    },
    # ------------------ Level 4: Senior / Advanced Analytics & Systems ------------------
    {
        "id": "data.sci.l4_causal",
        "title": "Causal Inference and Observational Study Design",
        "description": (
            "Formulate causal Directed Acyclic Graphs, propensity score adjustments, "
            "and difference-in-differences for observational cohorts."
        ),
        "category": CompetencyCategory.EXPERIMENTATION,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["data.sci.l3_exp_design"],
        "difficulty": {
            "learning_difficulty": 4.0,
            "application_difficulty": 5.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.01.T05"),
    },
    {
        "id": "data.sci.l4_bigdata",
        "title": "Distributed Big Data Processing with Spark",
        "description": (
            "Architect distributed analytical workflows, memory partitioning, shuffle "
            "tuning, and scalable joins using Apache Spark."
        ),
        "category": CompetencyCategory.DATA_ENGINEERING,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["data.anl.l3_sql_adv", "data.sci.l3_feat_eng"],
        "difficulty": {
            "learning_difficulty": 4.0,
            "application_difficulty": 4.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-2051.01.T04"),
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


def build_data_family_graph() -> CompetencyGraphManifest:
    """Construct and validate the canonical DATA family CompetencyGraphManifest.

    Returns:
        CompetencyGraphManifest verified by CI validators.
    """
    nodes: list[CompetencyNode] = []
    for raw in _DATA_FAMILY_NODES_DATA:
        rubric = DifficultyRubric(**raw["difficulty"])
        node = CompetencyNode(
            id=raw["id"],
            title=raw["title"],
            description=raw["description"],
            category=raw["category"],
            role_family=RoleFamily.DATA,
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
        graph_id="competency-graph-data-family-v1",
        version="1.0.0",
        role_family=RoleFamily.DATA,
        created_at="2026-10-24T18:00:00Z",
        checksum_sha256=sha256_hash,
        nodes=nodes,
    )


def export_data_family_graph(
    output_dir: Path | None = None,
) -> tuple[CompetencyGraphManifest, Path]:
    """Build, validate, and serialize the DATA family competency DAG.

    Args:
        output_dir: Optional destination directory (defaults to config/taxonomy).

    Returns:
        Tuple containing the manifest and path to the written JSON file.
    """
    manifest = build_data_family_graph()
    target_dir = output_dir or CONFIG_TAXONOMY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    graph_path = target_dir / "competency_graph_data.json"

    data_json = json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"

    # Atomic write to prevent test race conditions
    tmp_path = graph_path.with_suffix(".tmp")
    tmp_path.write_text(data_json, encoding="utf-8")
    tmp_path.replace(graph_path)

    return manifest, graph_path


def load_data_family_graph(graph_path: Path | None = None) -> CompetencyGraphManifest:
    """Load and validate the DATA family competency DAG from disk.

    Args:
        graph_path: Path to competency_graph_data.json (defaults to canonical path).

    Returns:
        Validated CompetencyGraphManifest.
    """
    target = graph_path or DEFAULT_GRAPH_PATH
    if not target.is_file():
        manifest, _ = export_data_family_graph(target.parent)
        return manifest

    raw = json.loads(target.read_text(encoding="utf-8"))
    manifest = CompetencyGraphManifest.model_validate(raw)
    validate_competency_graph(manifest.nodes)
    return manifest


def get_prerequisite_closure(
    node_id: str,
    manifest: CompetencyGraphManifest | None = None,
) -> list[str]:
    """Retrieve full transitive prerequisite chain for a competency node in topological order.

    Args:
        node_id: Target competency node ID.
        manifest: Optional pre-loaded manifest (loads default if None).

    Returns:
        List of prerequisite node IDs in topological order (earliest prerequisite first).
    """
    graph = manifest or load_data_family_graph()
    node_map = {n.id: n for n in graph.nodes}

    if node_id not in node_map:
        raise KeyError(f"Competency node '{node_id}' not found in manifest.")

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


def get_career_roadmap(
    current_skills: set[str],
    target_level: RoleLevel,
    target_category: CompetencyCategory | None = None,
    manifest: CompetencyGraphManifest | None = None,
) -> list[CompetencyNode]:
    """Generate deterministic topological learning roadmap towards target seniority.

    Args:
        current_skills: Set of already acquired / demonstrated competency node IDs.
        target_level: Desired role level (Junior L2, Mid L3, Senior L4).
        target_category: Optional category filter.
        manifest: Pre-loaded manifest or default.

    Returns:
        Topologically ordered list of unacquired CompetencyNodes required for target.
    """
    graph = manifest or load_data_family_graph()
    node_map = {n.id: n for n in graph.nodes}

    # Identify candidate nodes matching level and category
    target_nodes: set[str] = set()
    for n in graph.nodes:
        if target_level in n.target_levels and (
            target_category is None or n.category == target_category
        ):
            target_nodes.add(n.id)

    # Expand to include transitive prerequisites of target nodes
    required_ids: set[str] = set(target_nodes)
    for t_id in target_nodes:
        for p_id in get_prerequisite_closure(t_id, graph):
            required_ids.add(p_id)

    # Exclude already possessed skills
    gap_ids = required_ids - current_skills

    # Return in valid topological execution sequence
    full_order = validate_graph_acyclicity(graph.nodes)
    return [node_map[n_id] for n_id in full_order if n_id in gap_ids]


if __name__ == "__main__":
    manifest, p = export_data_family_graph()
    print(f"Exported DATA family competency DAG to {p} ({len(manifest.nodes)} nodes).")
    print(f"Checksum SHA-256: {manifest.checksum_sha256}")
