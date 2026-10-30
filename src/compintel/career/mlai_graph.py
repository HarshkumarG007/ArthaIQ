"""Directed Acyclic Graph (DAG) for Machine Learning & AI (MLAI) competencies (Task T19.02).

Assembles and manages the competency graph across Junior (Level 2), Mid (Level 3),
and Senior (Level 4) roles for ML/AI Engineers with full provenance,
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
DEFAULT_MLAI_GRAPH_PATH = CONFIG_TAXONOMY_DIR / "competency_graph_mlai.json"

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
        curator="ArthaIQ MLAI Review Panel",
        curated_date="2026-10-31",
    )


def _make_esco_provenance(code: str) -> TaxonomyProvenance:
    return TaxonomyProvenance(
        source_id=TaxonomySource.ESCO_1_1_1,
        source_code=code,
        license=TaxonomyLicense.EU_OPEN_REUSE,
        attribution_required=True,
        attribution_text=ESCO_STATUTORY_ATTRIBUTION_ADAPTED,
        modified_flag=True,
        curator="ArthaIQ MLAI Review Panel",
        curated_date="2026-10-31",
    )


_MLAI_FAMILY_NODES_DATA: list[dict[str, Any]] = [
    # ------------------ Level 2: Junior / Foundations & Core Skills ------------------
    {
        "id": "mlai.math.l2_linear_algebra",
        "title": "Linear Algebra and High-Dimensional Matrix Operations",
        "description": (
            "Formulate matrix decompositions (SVD, eigendecomposition), tensor contractions, "
            "and vector spaces for neural representation learning."
        ),
        "category": CompetencyCategory.MATH_OPTIMIZATION,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.09.T01"),
    },
    {
        "id": "mlai.math.l2_convex_opt",
        "title": "Convex Optimization and Loss Landscape Analysis",
        "description": (
            "Analyze objective function convexity, gradient dynamics, Lipschitz continuity, "
            "and conditioning of high-dimensional loss landscapes."
        ),
        "category": CompetencyCategory.MATH_OPTIMIZATION,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.5,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.09.T02"),
    },
    {
        "id": "mlai.core.l2_neural_backprop",
        "title": "Deep Neural Architectures and Backpropagation Dynamics",
        "description": (
            "Implement feedforward, convolutional, and recurrent computational graphs with "
            "automatic differentiation, layer normalization, and residual connections."
        ),
        "category": CompetencyCategory.DEEP_LEARNING,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": ["mlai.math.l2_linear_algebra"],
        "difficulty": {
            "learning_difficulty": 2.5,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.09.T04"),
    },
    {
        "id": "mlai.ops.l2_model_registry",
        "title": "Model Registry, Lineage and Artifact Versioning",
        "description": (
            "Track model weights, training checkpoints, hyperparameter manifests, and "
            "dataset lineage using immutable cryptographic hashes."
        ),
        "category": CompetencyCategory.MLOPS_INFRASTRUCTURE,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.MLAI.001"),
    },
    {
        "id": "mlai.eval.l2_leakage_audit",
        "title": "Sliced Evaluation, Data Leakage and Disparate Performance Auditing",
        "description": (
            "Audit model evaluations across operational demographic slices, temporal "
            "boundaries, and verify complete test partition leakage isolation."
        ),
        "category": CompetencyCategory.EVALUATION_GOVERNANCE,
        "target_levels": [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        "prerequisite_ids": [],
        "difficulty": {
            "learning_difficulty": 2.0,
            "application_difficulty": 2.5,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.08.T02"),
    },
    # ------------------ Level 3: Mid-Level Applied ML / Modeling ------------------
    {
        "id": "mlai.math.l3_stochastic_opt",
        "title": "Stochastic Optimization and Adaptive Learning Rates",
        "description": (
            "Tune first- and second-order stochastic gradient optimizers (SGD with momentum, "
            "AdamW, Lion), learning rate schedules, and gradient clipping."
        ),
        "category": CompetencyCategory.MATH_OPTIMIZATION,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.math.l2_convex_opt"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.5,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.09.T03"),
    },
    {
        "id": "mlai.core.l3_transformer_attn",
        "title": "Self-Attention Mechanics and Transformer Architectures",
        "description": (
            "Construct scaled dot-product attention, multi-head attention blocks, rotary "
            "position embeddings (RoPE), and KV-cache mechanisms."
        ),
        "category": CompetencyCategory.DEEP_LEARNING,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.core.l2_neural_backprop"],
        "difficulty": {
            "learning_difficulty": 3.5,
            "application_difficulty": 3.5,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.09.T05"),
    },
    {
        "id": "mlai.core.l3_repr_learning",
        "title": "Representation Learning and Contrastive Embeddings",
        "description": (
            "Train dense embedding representations using contrastive loss, InfoNCE, "
            "cosine margin losses, and vector indexing for similarity search."
        ),
        "category": CompetencyCategory.DEEP_LEARNING,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.core.l2_neural_backprop"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.5,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.09.T06"),
    },
    {
        "id": "mlai.core.l3_peft_finetune",
        "title": "Transfer Learning and Parameter-Efficient Fine-Tuning",
        "description": (
            "Adapt foundation models using parameter-efficient fine-tuning (LoRA, QLoRA, "
            "prefix tuning) and task-specific projection heads."
        ),
        "category": CompetencyCategory.DEEP_LEARNING,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.core.l3_transformer_attn"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.09.T07"),
    },
    {
        "id": "mlai.eval.l3_conformal_calib",
        "title": "Calibration and Split Conformal Uncertainty Estimation",
        "description": (
            "Quantify predictive uncertainty via split conformal prediction intervals, "
            "expected calibration error (ECE), and reliability diagrams."
        ),
        "category": CompetencyCategory.EVALUATION_GOVERNANCE,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.eval.l2_leakage_audit"],
        "difficulty": {
            "learning_difficulty": 3.5,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.08.T01"),
    },
    {
        "id": "mlai.gen.l3_guardrails",
        "title": "Hallucination Mitigation and Output Guardrails",
        "description": (
            "Engineer retrieval-augmented grounding (RAG), structured JSON schema "
            "constraints, and deterministic verification filters."
        ),
        "category": CompetencyCategory.GENERATIVE_ALIGNMENT,
        "target_levels": [RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.core.l3_transformer_attn"],
        "difficulty": {
            "learning_difficulty": 3.0,
            "application_difficulty": 3.0,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.MLAI.005"),
    },
    # ------------------ Level 4: Senior / Advanced Systems & Governance ------------------
    {
        "id": "mlai.ops.l4_dist_training",
        "title": "Distributed Training and Tensor Sharding",
        "description": (
            "Configure data parallel (DDP), tensor parallel (Megatron-LM), and pipeline "
            "parallel (DeepSpeed ZeRO) training clusters."
        ),
        "category": CompetencyCategory.MLOPS_INFRASTRUCTURE,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.ops.l2_model_registry", "mlai.math.l3_stochastic_opt"],
        "difficulty": {
            "learning_difficulty": 4.5,
            "application_difficulty": 4.5,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.MLAI.002"),
    },
    {
        "id": "mlai.ops.l4_quant_serving",
        "title": "Model Quantization and Low-Latency Serving",
        "description": (
            "Apply post-training quantization (INT8, FP8, AWQ), KV cache compression, "
            "continuous batching, and tensor compilation for serving."
        ),
        "category": CompetencyCategory.MLOPS_INFRASTRUCTURE,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.core.l3_transformer_attn"],
        "difficulty": {
            "learning_difficulty": 4.0,
            "application_difficulty": 4.5,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.MLAI.003"),
    },
    {
        "id": "mlai.gen.l4_preference_dpo",
        "title": "Preference Optimization and Alignment Algorithms",
        "description": (
            "Implement reward modeling, Direct Preference Optimization (DPO), and RLHF "
            "alignment pipelines to steer generation dynamics."
        ),
        "category": CompetencyCategory.GENERATIVE_ALIGNMENT,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.core.l3_peft_finetune", "mlai.gen.l3_guardrails"],
        "difficulty": {
            "learning_difficulty": 4.5,
            "application_difficulty": 4.5,
            "is_heuristic": True,
        },
        "provenance": _make_onet_provenance("15-1299.09.T08"),
    },
    {
        "id": "mlai.eval.l4_dpdp_privacy",
        "title": "Privacy-Preserving Machine Learning and Verifiable Erasure",
        "description": (
            "Implement differential privacy, machine unlearning techniques, and verifiable "
            "training data deletion under DPDP Act 2023 Sec 12."
        ),
        "category": CompetencyCategory.EVALUATION_GOVERNANCE,
        "target_levels": [RoleLevel.LEVEL_4_SENIOR],
        "prerequisite_ids": ["mlai.eval.l3_conformal_calib"],
        "difficulty": {
            "learning_difficulty": 4.0,
            "application_difficulty": 4.5,
            "is_heuristic": True,
        },
        "provenance": _make_esco_provenance("ESCO.MLAI.004"),
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


def build_mlai_family_graph() -> CompetencyGraphManifest:
    """Construct and validate the canonical MLAI family CompetencyGraphManifest.

    Returns:
        CompetencyGraphManifest verified by CI validators.
    """
    nodes: list[CompetencyNode] = []
    for raw in _MLAI_FAMILY_NODES_DATA:
        rubric = DifficultyRubric(**raw["difficulty"])
        node = CompetencyNode(
            id=raw["id"],
            title=raw["title"],
            description=raw["description"],
            category=raw["category"],
            role_family=RoleFamily.MLAI,
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
        graph_id="competency-graph-mlai-family-v1",
        version="1.0.0",
        role_family=RoleFamily.MLAI,
        created_at="2026-10-31T12:00:00Z",
        checksum_sha256=sha256_hash,
        nodes=nodes,
    )


def export_mlai_family_graph(
    output_dir: Path | None = None,
) -> tuple[CompetencyGraphManifest, Path]:
    """Build, validate, and serialize the MLAI family competency DAG.

    Args:
        output_dir: Optional destination directory (defaults to config/taxonomy).

    Returns:
        Tuple containing the manifest and path to the written JSON file.
    """
    manifest = build_mlai_family_graph()
    target_dir = output_dir or CONFIG_TAXONOMY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    graph_path = target_dir / "competency_graph_mlai.json"

    data_json = json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"

    # Atomic write to prevent test race conditions
    tmp_path = graph_path.with_suffix(".tmp")
    tmp_path.write_text(data_json, encoding="utf-8")
    tmp_path.replace(graph_path)

    return manifest, graph_path


def load_mlai_family_graph(graph_path: Path | None = None) -> CompetencyGraphManifest:
    """Load and validate the MLAI family competency DAG from disk.

    Args:
        graph_path: Path to competency_graph_mlai.json (defaults to canonical path).

    Returns:
        Validated CompetencyGraphManifest.
    """
    target = graph_path or DEFAULT_MLAI_GRAPH_PATH
    if not target.is_file():
        manifest, _ = export_mlai_family_graph(target.parent)
        return manifest

    raw = json.loads(target.read_text(encoding="utf-8"))
    manifest = CompetencyGraphManifest.model_validate(raw)
    validate_competency_graph(manifest.nodes)
    return manifest


def get_mlai_prerequisite_closure(
    node_id: str,
    manifest: CompetencyGraphManifest | None = None,
) -> list[str]:
    """Retrieve full transitive prerequisite chain for an MLAI competency node.

    Args:
        node_id: Target competency node ID.
        manifest: Optional pre-loaded manifest (loads default if None).

    Returns:
        List of prerequisite node IDs in topological order (earliest prerequisite first).
    """
    graph = manifest or load_mlai_family_graph()
    node_map = {n.id: n for n in graph.nodes}

    if node_id not in node_map:
        raise KeyError(f"Competency node '{node_id}' not found in MLAI manifest.")

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


def get_mlai_career_roadmap(
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
    graph = manifest or load_mlai_family_graph()

    # Identify target competency nodes for target_level
    target_node_ids = {n.id for n in graph.nodes if target_level in n.target_levels}

    # Expand required nodes to include all prerequisite closures
    required_ids: set[str] = set()
    for tid in target_node_ids:
        required_ids.add(tid)
        closure = get_mlai_prerequisite_closure(tid, graph)
        required_ids.update(closure)

    # Filter out skills already demonstrated
    unproven_ids = required_ids - current_skills

    # Order unproven nodes topologically
    full_order = validate_graph_acyclicity(graph.nodes)
    return [n_id for n_id in full_order if n_id in unproven_ids]


if __name__ == "__main__":
    manifest, path = export_mlai_family_graph()
    sha_short = manifest.checksum_sha256[:16]
    print(f"Serialized {len(manifest.nodes)} MLAI nodes to {path.name} (SHA-256: {sha_short}...)")
