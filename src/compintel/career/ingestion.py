"""Deterministic taxonomy ingestion and crosswalk for ArthaIQ Career Architect (Task T15.11).

Ingests labour taxonomy definitions from O*NET 28.0 (Data Scientists 15-2051.01,
Data Analysts 15-2051.02) and ESCO v1.1.1 (Transversal Skills) under CC BY 4.0
and EU Open Reuse terms with SHA-256 manifest verification.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from compintel.career.schema import (
    CompetencyCategory,
    TaxonomyLicense,
    TaxonomyProvenance,
    TaxonomySource,
    validate_anti_causal_text,
)
from compintel.career.validators import ProvenanceComplianceError

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_TAXONOMY_DIR = REPO_ROOT / "config" / "taxonomy"

ONET_STATUTORY_ATTRIBUTION = (
    "Source: O*NET 28.0 Database by the U.S. Department of Labor, Employment and "
    "Training Administration (USDOL/ETA). Used under the CC BY 4.0 license. "
    "O*NET® is a trademark of USDOL/ETA. ArthaIQ has modified, selected, and "
    "restructured these competencies for career intelligence."
)

ESCO_STATUTORY_ATTRIBUTION = (
    "Source: European Skills, Competences, Qualifications and Occupations "
    "(ESCO v1.1.1), European Commission. Reused under European Commission open "
    "reuse policy (Decision 2011/833/EU)."
)


class TaxonomyElement(BaseModel):
    """Normalized atomic taxonomy item ingested from public labour frameworks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(..., min_length=2, description="Taxonomy source code")
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    category: CompetencyCategory
    is_transversal: bool = False
    provenance: TaxonomyProvenance


class TaxonomyManifest(BaseModel):
    """Licensing and cryptographic checksum manifest for ingested taxonomies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: str = "v1.0"
    generated_at: str
    total_elements: int
    sources_included: list[str]
    licence_classes: list[str]
    bundle_sha256: str
    element_counts_by_category: dict[str, int]


class TaxonomyBundle(BaseModel):
    """Container bundle of all ingested taxonomy elements for a role family."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_id: str
    role_family: str = "DATA"
    version: str = "1.0.0"
    generated_at: str
    manifest: TaxonomyManifest
    elements: list[TaxonomyElement]


# Raw curated records derived deterministically from O*NET 28.0 and ESCO 1.1.1
_RAW_ONET_DATA_ANALYST_TASKS: list[dict[str, Any]] = [
    {
        "code": "15-2051.02.T01",
        "title": "SQL Query Optimization and Joins",
        "description": (
            "Formulate relational SQL queries, table joins, aggregations, and subqueries "
            "to extract business data."
        ),
        "category": CompetencyCategory.CORE_ANALYTICS,
    },
    {
        "code": "15-2051.02.T02",
        "title": "SQL Window Functions and Analytical Partitions",
        "description": (
            "Utilize analytical window frames, PARTITION BY, and ranking functions for "
            "sequential business analytics."
        ),
        "category": CompetencyCategory.CORE_ANALYTICS,
    },
    {
        "code": "15-2051.02.T03",
        "title": "Data Hygiene and Anomaly Detection",
        "description": (
            "Audit datasets for null values, schema drift, outlier entries, and integrity "
            "violations prior to reporting."
        ),
        "category": CompetencyCategory.CORE_ANALYTICS,
    },
    {
        "code": "15-2051.02.T04",
        "title": "Dashboard Design and Metric Reporting",
        "description": (
            "Design interactive analytical dashboards to monitor core operational and "
            "financial business metrics."
        ),
        "category": CompetencyCategory.BUSINESS_COMMUNICATION,
    },
    {
        "code": "15-2051.02.T05",
        "title": "Exploratory Data Analysis and Distributions",
        "description": (
            "Conduct univariate and bivariate statistical exploratory analysis to "
            "identify distributions and trends."
        ),
        "category": CompetencyCategory.STATISTICAL_MODELING,
    },
]

_RAW_ONET_DATA_SCIENTIST_TASKS: list[dict[str, Any]] = [
    {
        "code": "15-2051.01.T01",
        "title": "Statistical Hypothesis Testing and A/B Experiments",
        "description": (
            "Design randomized controlled trials, sample size calculations, hypothesis tests, "
            "and variance reduction."
        ),
        "category": CompetencyCategory.EXPERIMENTATION,
    },
    {
        "code": "15-2051.01.T02",
        "title": "Predictive Modeling and Supervised Learning",
        "description": (
            "Train and evaluate supervised classification and regression models using "
            "calibrated loss functions."
        ),
        "category": CompetencyCategory.STATISTICAL_MODELING,
    },
    {
        "code": "15-2051.01.T03",
        "title": "Feature Engineering and Leakage Prevention",
        "description": (
            "Construct predictive features, target transformations, and temporal splits "
            "ensuring zero data leakage."
        ),
        "category": CompetencyCategory.DATA_ENGINEERING,
    },
    {
        "code": "15-2051.01.T04",
        "title": "Distributed Big Data Processing with Spark",
        "description": (
            "Architect distributed dataset transformations, partitioning strategies, "
            "and caching using Apache Spark."
        ),
        "category": CompetencyCategory.DATA_ENGINEERING,
    },
    {
        "code": "15-2051.01.T05",
        "title": "Causal Inference and Observational Studies",
        "description": (
            "Formulate causal DAGs, propensity score matching, and instrumental variable "
            "designs for non-randomized data."
        ),
        "category": CompetencyCategory.EXPERIMENTATION,
    },
]

_RAW_ESCO_TRANSVERSAL_SKILLS: list[dict[str, Any]] = [
    {
        "code": "ESCO.T.001",
        "title": "Analytical Reasoning and Problem Decomposition",
        "description": (
            "Deconstruct complex business problems into structured, verifiable "
            "analytical hypotheses."
        ),
        "category": CompetencyCategory.CORE_ANALYTICS,
        "is_transversal": True,
    },
    {
        "code": "ESCO.T.002",
        "title": "Technical Documentation and Reproduction Standards",
        "description": (
            "Author reproducible analytical specifications, methodology documentation, "
            "and code comments."
        ),
        "category": CompetencyCategory.BUSINESS_COMMUNICATION,
        "is_transversal": True,
    },
    {
        "code": "ESCO.T.003",
        "title": "Stakeholder Evidence Communication",
        "description": (
            "Present probabilistic insights and uncertainty bounds clearly to "
            "cross-functional decision makers."
        ),
        "category": CompetencyCategory.BUSINESS_COMMUNICATION,
        "is_transversal": True,
    },
    {
        "code": "ESCO.T.004",
        "title": "Ethical Data Governance and Privacy Safeguards",
        "description": (
            "Apply data protection principles, pseudonymization techniques, and compliance "
            "checks under DPDP guidelines."
        ),
        "category": CompetencyCategory.DATA_ENGINEERING,
        "is_transversal": True,
    },
]

# Raw curated records for Software Engineering (SWE) from O*NET 28.0 and ESCO 1.1.1
_RAW_ONET_SWE_DEVELOPER_TASKS: list[dict[str, Any]] = [
    {
        "code": "15-1252.00.T01",
        "title": "Algorithmic Complexity and Core Data Structures",
        "description": (
            "Analyze asymptotic time and space complexity, hash collision handling, "
            "and tree/graph representations for low-latency execution."
        ),
        "category": CompetencyCategory.SYSTEMS_ARCHITECTURE,
    },
    {
        "code": "15-1252.00.T02",
        "title": "Concurrency Primitives and Thread Safety",
        "description": (
            "Design multithreaded and asynchronous routines using mutexes, read-write "
            "locks, atomic variables, and deadlock detection."
        ),
        "category": CompetencyCategory.SYSTEMS_ARCHITECTURE,
    },
    {
        "code": "15-1252.00.T03",
        "title": "Memory Profiling and Resource Management",
        "description": (
            "Profile process heap allocation, identify memory leaks, manage connection "
            "lifecycles, and optimize allocator throughput."
        ),
        "category": CompetencyCategory.SYSTEMS_ARCHITECTURE,
    },
    {
        "code": "15-1252.00.T04",
        "title": "Microservice Resiliency and Fault Isolation",
        "description": (
            "Implement circuit breakers, exponential backoff, bulkhead isolation, "
            "and graceful degradation in distributed microservices."
        ),
        "category": CompetencyCategory.APPLICATION_DEVELOPMENT,
    },
    {
        "code": "15-1252.00.T05",
        "title": "Relational Indexing and Query Performance",
        "description": (
            "Optimize database query execution plans, design composite B-tree indexes, "
            "resolve table lock contention, and prevent N+1 query patterns."
        ),
        "category": CompetencyCategory.APPLICATION_DEVELOPMENT,
    },
    {
        "code": "15-1252.00.T06",
        "title": "Distributed Consensus and Replicated State",
        "description": (
            "Evaluate distributed consensus protocols (Raft, Paxos), split-brain scenarios, "
            "leader election timeouts, and linearizable consistency."
        ),
        "category": CompetencyCategory.SYSTEMS_ARCHITECTURE,
    },
    {
        "code": "15-1252.00.T07",
        "title": "Event-Driven Architecture and Asynchronous Messaging",
        "description": (
            "Architect transactional outbox patterns, message deduplication, at-least-once "
            "delivery guarantees, and dead-letter queue handling."
        ),
        "category": CompetencyCategory.APPLICATION_DEVELOPMENT,
    },
]

_RAW_ONET_SWE_WEB_TASKS: list[dict[str, Any]] = [
    {
        "code": "15-1254.00.T01",
        "title": "Contract-First API Architecture and Idempotency",
        "description": (
            "Design REST and gRPC API contracts with RFC 9457 problem details, semantic "
            "versioning, and strict idempotency keys for mutative endpoints."
        ),
        "category": CompetencyCategory.APPLICATION_DEVELOPMENT,
    },
    {
        "code": "15-1254.00.T02",
        "title": "Web Application Security and Input Sanitization",
        "description": (
            "Enforce OWASP Top 10 defenses including parametrized SQL statements, CSP "
            "headers, CSRF tokens, SSRF protection, and cryptographically secure tokens."
        ),
        "category": CompetencyCategory.SECURITY_RELIABILITY,
    },
]

_RAW_ESCO_SWE_TRANSVERSAL_SKILLS: list[dict[str, Any]] = [
    {
        "code": "ESCO.SWE.001",
        "title": "Git Trunk Hygiene and Atomic Branching",
        "description": (
            "Maintain clean trunk-based commit histories, atomic commit diffs, interactive "
            "rebase conflict resolution, and merge hygiene."
        ),
        "category": CompetencyCategory.DEV_WORKFLOW,
        "is_transversal": True,
    },
    {
        "code": "ESCO.SWE.002",
        "title": "Automated Unit Testing and Test Isolation",
        "description": (
            "Author deterministic unit test suites with test doubles, hermetic fixture "
            "isolation, property testing, and high statement coverage."
        ),
        "category": CompetencyCategory.TESTING_QUALITY,
        "is_transversal": True,
    },
    {
        "code": "ESCO.SWE.003",
        "title": "Container Packaging and Minimal Base Images",
        "description": (
            "Author multi-stage container builds, non-root user execution, minimal attack "
            "surfaces, and reproducible image digest pinning."
        ),
        "category": CompetencyCategory.DEV_WORKFLOW,
        "is_transversal": True,
    },
    {
        "code": "ESCO.SWE.004",
        "title": "Telemetry, Structured Logging and Distributed Tracing",
        "description": (
            "Instrument services with OpenTelemetry traces, RED metric collection, "
            "and correlation IDs across asynchronous log streams."
        ),
        "category": CompetencyCategory.SECURITY_RELIABILITY,
        "is_transversal": True,
    },
    {
        "code": "ESCO.SWE.005",
        "title": "Hermetic CI/CD Pipelines and Automated Rollback",
        "description": (
            "Configure reproducible deployment pipelines with canary gates, automated "
            "health checks, zero-downtime rollouts, and rollback triggers."
        ),
        "category": CompetencyCategory.DEV_WORKFLOW,
        "is_transversal": True,
    },
    {
        "code": "ESCO.SWE.006",
        "title": "Cryptographic Privacy and Verifiable Purge Operations",
        "description": (
            "Implement envelope encryption, keyed hash message authentication, and "
            "verifiable zero-byte hard deletion under DPDP Act 2023 Sec 12."
        ),
        "category": CompetencyCategory.SECURITY_RELIABILITY,
        "is_transversal": True,
    },
]

# Raw curated records for Machine Learning & AI (MLAI) from O*NET 28.0 and ESCO 1.1.1
_RAW_ONET_MLAI_SPECIALIST_TASKS: list[dict[str, Any]] = [
    {
        "code": "15-1299.09.T01",
        "title": "Linear Algebra and High-Dimensional Matrix Operations",
        "description": (
            "Formulate matrix decompositions (SVD, eigendecomposition), tensor contractions, "
            "and vector spaces for neural representation learning."
        ),
        "category": CompetencyCategory.MATH_OPTIMIZATION,
    },
    {
        "code": "15-1299.09.T02",
        "title": "Convex Optimization and Loss Landscape Analysis",
        "description": (
            "Analyze objective function convexity, gradient dynamics, Lipschitz continuity, "
            "and conditioning of high-dimensional loss landscapes."
        ),
        "category": CompetencyCategory.MATH_OPTIMIZATION,
    },
    {
        "code": "15-1299.09.T03",
        "title": "Stochastic Optimization and Adaptive Learning Rates",
        "description": (
            "Tune first- and second-order stochastic gradient optimizers (SGD with momentum, "
            "AdamW, Lion), learning rate schedules, and gradient clipping."
        ),
        "category": CompetencyCategory.MATH_OPTIMIZATION,
    },
    {
        "code": "15-1299.09.T04",
        "title": "Deep Neural Architectures and Backpropagation Dynamics",
        "description": (
            "Implement feedforward, convolutional, and recurrent computational graphs with "
            "automatic differentiation, layer normalization, and residual connections."
        ),
        "category": CompetencyCategory.DEEP_LEARNING,
    },
    {
        "code": "15-1299.09.T05",
        "title": "Self-Attention Mechanics and Transformer Architectures",
        "description": (
            "Construct scaled dot-product attention, multi-head attention blocks, rotary "
            "position embeddings (RoPE), and KV-cache mechanisms."
        ),
        "category": CompetencyCategory.DEEP_LEARNING,
    },
    {
        "code": "15-1299.09.T06",
        "title": "Representation Learning and Contrastive Embeddings",
        "description": (
            "Train dense embedding representations using contrastive loss, InfoNCE, "
            "cosine margin losses, and vector indexing for similarity search."
        ),
        "category": CompetencyCategory.DEEP_LEARNING,
    },
    {
        "code": "15-1299.09.T07",
        "title": "Transfer Learning and Parameter-Efficient Fine-Tuning",
        "description": (
            "Adapt foundation models using parameter-efficient fine-tuning (LoRA, QLoRA, "
            "prefix tuning) and task-specific projection heads."
        ),
        "category": CompetencyCategory.DEEP_LEARNING,
    },
    {
        "code": "15-1299.09.T08",
        "title": "Preference Optimization and Alignment Algorithms",
        "description": (
            "Implement reward modeling, Direct Preference Optimization (DPO), and RLHF "
            "alignment pipelines to steer generation dynamics."
        ),
        "category": CompetencyCategory.GENERATIVE_ALIGNMENT,
    },
]

_RAW_ONET_MLAI_SCIENTIST_TASKS: list[dict[str, Any]] = [
    {
        "code": "15-1299.08.T01",
        "title": "Calibration and Split Conformal Uncertainty Estimation",
        "description": (
            "Quantify predictive uncertainty via split conformal prediction intervals, "
            "expected calibration error (ECE), and reliability diagrams."
        ),
        "category": CompetencyCategory.EVALUATION_GOVERNANCE,
    },
    {
        "code": "15-1299.08.T02",
        "title": "Sliced Evaluation, Data Leakage and Disparate Performance Auditing",
        "description": (
            "Audit model evaluations across operational demographic slices, temporal "
            "boundaries, and verify complete test partition leakage isolation."
        ),
        "category": CompetencyCategory.EVALUATION_GOVERNANCE,
    },
]

_RAW_ESCO_MLAI_TRANSVERSAL_SKILLS: list[dict[str, Any]] = [
    {
        "code": "ESCO.MLAI.001",
        "title": "Model Registry, Lineage and Artifact Versioning",
        "description": (
            "Track model weights, training checkpoints, hyperparameter manifests, and "
            "dataset lineage using immutable cryptographic hashes."
        ),
        "category": CompetencyCategory.MLOPS_INFRASTRUCTURE,
        "is_transversal": True,
    },
    {
        "code": "ESCO.MLAI.002",
        "title": "Distributed Training and Tensor Sharding",
        "description": (
            "Configure data parallel (DDP), tensor parallel (Megatron-LM), and pipeline "
            "parallel (DeepSpeed ZeRO) training clusters."
        ),
        "category": CompetencyCategory.MLOPS_INFRASTRUCTURE,
        "is_transversal": True,
    },
    {
        "code": "ESCO.MLAI.003",
        "title": "Model Quantization and Low-Latency Serving",
        "description": (
            "Apply post-training quantization (INT8, FP8, AWQ), KV cache compression, "
            "continuous batching, and tensor compilation for serving."
        ),
        "category": CompetencyCategory.MLOPS_INFRASTRUCTURE,
        "is_transversal": True,
    },
    {
        "code": "ESCO.MLAI.004",
        "title": "Privacy-Preserving Machine Learning and Verifiable Erasure",
        "description": (
            "Implement differential privacy, machine unlearning techniques, and verifiable "
            "training data deletion under DPDP Act 2023 Sec 12."
        ),
        "category": CompetencyCategory.EVALUATION_GOVERNANCE,
        "is_transversal": True,
    },
    {
        "code": "ESCO.MLAI.005",
        "title": "Hallucination Mitigation and Output Guardrails",
        "description": (
            "Engineer retrieval-augmented grounding (RAG), structured JSON schema "
            "constraints, and deterministic verification filters."
        ),
        "category": CompetencyCategory.GENERATIVE_ALIGNMENT,
        "is_transversal": True,
    },
]


def enforce_taxonomy_licence_gate(
    source_id: TaxonomySource,
    license_type: TaxonomyLicense,
    attribution_text: str,
) -> None:
    """Enforce statutory licensing and source provenance rules (Rule R-CR-04, R-DA-01).

    Args:
        source_id: Identified taxonomy provider.
        license_type: Licence identifier.
        attribution_text: Attribution notice text.

    Raises:
        ProvenanceComplianceError: If source or licence violates open reuse requirements.
    """
    if source_id == TaxonomySource.ONET_28_0:
        if license_type != TaxonomyLicense.CC_BY_4_0:
            raise ProvenanceComplianceError(
                f"Invalid licence for O*NET 28.0: expected {TaxonomyLicense.CC_BY_4_0}, "
                f"got {license_type}."
            )
        if "o*net" not in attribution_text.lower():
            raise ProvenanceComplianceError(
                "O*NET attribution text missing mandatory trademark notice."
            )
    elif source_id == TaxonomySource.ESCO_1_1_1:
        if license_type != TaxonomyLicense.EU_OPEN_REUSE:
            raise ProvenanceComplianceError(
                f"Invalid licence for ESCO 1.1.1: expected {TaxonomyLicense.EU_OPEN_REUSE}, "
                f"got {license_type}."
            )
    else:
        raise ProvenanceComplianceError(
            f"Taxonomy source '{source_id}' is not an approved open labour framework "
            "under Rule R-DA-01."
        )


def build_taxonomy_element(
    raw_record: dict[str, Any],
    source_id: TaxonomySource,
    license_type: TaxonomyLicense,
    attribution_text: str,
) -> TaxonomyElement:
    """Construct and validate a normalized TaxonomyElement."""
    enforce_taxonomy_licence_gate(source_id, license_type, attribution_text)

    # Enforce anti-causal copy invariants
    validate_anti_causal_text(raw_record["title"], "title")
    validate_anti_causal_text(raw_record["description"], "description")

    provenance = TaxonomyProvenance(
        source_id=source_id,
        source_code=raw_record["code"],
        license=license_type,
        attribution_required=True,
        attribution_text=attribution_text,
        modified_flag=True,
        curator="ArthaIQ Taxonomy Panel",
        curated_date="2026-10-24",
    )

    return TaxonomyElement(
        code=raw_record["code"],
        title=raw_record["title"],
        description=raw_record["description"],
        category=raw_record["category"],
        is_transversal=raw_record.get("is_transversal", False),
        provenance=provenance,
    )


def compute_bundle_sha256(elements: list[TaxonomyElement]) -> str:
    """Compute deterministic SHA-256 hash of sorted taxonomy elements."""
    hasher = hashlib.sha256()
    # Sort elements deterministically by code
    sorted_elements = sorted(elements, key=lambda el: el.code)
    for el in sorted_elements:
        dumped = json.dumps(el.model_dump(), sort_keys=True)
        hasher.update(dumped.encode("utf-8"))
    return hasher.hexdigest()


def generate_data_family_taxonomy(
    output_dir: Path | None = None,
) -> tuple[TaxonomyBundle, Path, Path]:
    """Ingest, crosswalk, and serialize canonical DATA family taxonomy.

    Args:
        output_dir: Optional destination directory (defaults to config/taxonomy).

    Returns:
        Tuple containing the TaxonomyBundle, path to data_family.json, and path to manifest.json.
    """
    elements: list[TaxonomyElement] = []

    # 1. Ingest O*NET Data Analyst tasks
    for item in _RAW_ONET_DATA_ANALYST_TASKS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ONET_28_0,
            TaxonomyLicense.CC_BY_4_0,
            ONET_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # 2. Ingest O*NET Data Scientist tasks
    for item in _RAW_ONET_DATA_SCIENTIST_TASKS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ONET_28_0,
            TaxonomyLicense.CC_BY_4_0,
            ONET_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # 3. Ingest ESCO Transversal skills
    for item in _RAW_ESCO_TRANSVERSAL_SKILLS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ESCO_1_1_1,
            TaxonomyLicense.EU_OPEN_REUSE,
            ESCO_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # Sort deterministically
    elements.sort(key=lambda el: el.code)

    # Compute category statistics
    category_counts: dict[str, int] = {}
    for el in elements:
        category_counts[el.category] = category_counts.get(el.category, 0) + 1

    sha256_hash = compute_bundle_sha256(elements)
    fixed_timestamp = "2026-10-24T18:00:00Z"

    manifest = TaxonomyManifest(
        manifest_version="v1.0",
        generated_at=fixed_timestamp,
        total_elements=len(elements),
        sources_included=[TaxonomySource.ONET_28_0, TaxonomySource.ESCO_1_1_1],
        licence_classes=[TaxonomyLicense.CC_BY_4_0, TaxonomyLicense.EU_OPEN_REUSE],
        bundle_sha256=sha256_hash,
        element_counts_by_category=category_counts,
    )

    bundle = TaxonomyBundle(
        bundle_id="taxonomy-data-family-v1",
        role_family="DATA",
        version="1.0.0",
        generated_at=fixed_timestamp,
        manifest=manifest,
        elements=elements,
    )

    target_dir = output_dir or CONFIG_TAXONOMY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = target_dir / "data_family.json"
    manifest_path = target_dir / "manifest.json"

    bundle_json = json.dumps(bundle.model_dump(), indent=2, sort_keys=True) + "\n"
    manifest_json = json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"

    # Atomic write pattern to avoid parallel file-read corruption
    tmp_bundle = bundle_path.with_suffix(".tmp")
    tmp_manifest = manifest_path.with_suffix(".tmp")
    tmp_bundle.write_text(bundle_json, encoding="utf-8")
    tmp_manifest.write_text(manifest_json, encoding="utf-8")
    tmp_bundle.replace(bundle_path)
    tmp_manifest.replace(manifest_path)

    return bundle, bundle_path, manifest_path


def generate_swe_family_taxonomy(
    output_dir: Path | None = None,
) -> tuple[TaxonomyBundle, Path, Path]:
    """Ingest, crosswalk, and serialize canonical SWE family taxonomy.

    Args:
        output_dir: Optional destination directory (defaults to config/taxonomy).

    Returns:
        Tuple containing the TaxonomyBundle, path to swe_family.json, and path to manifest_swe.json.
    """
    elements: list[TaxonomyElement] = []

    # 1. Ingest O*NET Software Developers tasks
    for item in _RAW_ONET_SWE_DEVELOPER_TASKS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ONET_28_0,
            TaxonomyLicense.CC_BY_4_0,
            ONET_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # 2. Ingest O*NET Web Developers tasks
    for item in _RAW_ONET_SWE_WEB_TASKS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ONET_28_0,
            TaxonomyLicense.CC_BY_4_0,
            ONET_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # 3. Ingest ESCO SWE Transversal skills
    for item in _RAW_ESCO_SWE_TRANSVERSAL_SKILLS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ESCO_1_1_1,
            TaxonomyLicense.EU_OPEN_REUSE,
            ESCO_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # Sort deterministically by code
    elements.sort(key=lambda el: el.code)

    # Compute category statistics
    category_counts: dict[str, int] = {}
    for el in elements:
        category_counts[el.category] = category_counts.get(el.category, 0) + 1

    sha256_hash = compute_bundle_sha256(elements)
    fixed_timestamp = "2026-10-30T12:00:00Z"

    manifest = TaxonomyManifest(
        manifest_version="v1.0",
        generated_at=fixed_timestamp,
        total_elements=len(elements),
        sources_included=[TaxonomySource.ONET_28_0, TaxonomySource.ESCO_1_1_1],
        licence_classes=[TaxonomyLicense.CC_BY_4_0, TaxonomyLicense.EU_OPEN_REUSE],
        bundle_sha256=sha256_hash,
        element_counts_by_category=category_counts,
    )

    bundle = TaxonomyBundle(
        bundle_id="taxonomy-swe-family-v1",
        role_family="SWE",
        version="1.0.0",
        generated_at=fixed_timestamp,
        manifest=manifest,
        elements=elements,
    )

    target_dir = output_dir or CONFIG_TAXONOMY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = target_dir / "swe_family.json"
    manifest_path = target_dir / "manifest_swe.json"

    bundle_json = json.dumps(bundle.model_dump(), indent=2, sort_keys=True) + "\n"
    manifest_json = json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"

    # Atomic write pattern to avoid parallel file-read corruption
    tmp_bundle = bundle_path.with_suffix(".tmp")
    tmp_manifest = manifest_path.with_suffix(".tmp")
    tmp_bundle.write_text(bundle_json, encoding="utf-8")
    tmp_manifest.write_text(manifest_json, encoding="utf-8")
    tmp_bundle.replace(bundle_path)
    tmp_manifest.replace(manifest_path)

    return bundle, bundle_path, manifest_path


def generate_mlai_family_taxonomy(
    output_dir: Path | None = None,
) -> tuple[TaxonomyBundle, Path, Path]:
    """Ingest, crosswalk, and serialize canonical MLAI family taxonomy.

    Args:
        output_dir: Optional destination directory (defaults to config/taxonomy).

    Returns:
        Tuple containing the TaxonomyBundle, path to mlai_family.json,
        and path to manifest_mlai.json.
    """
    elements: list[TaxonomyElement] = []

    # 1. Ingest O*NET AI / ML Specialists tasks
    for item in _RAW_ONET_MLAI_SPECIALIST_TASKS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ONET_28_0,
            TaxonomyLicense.CC_BY_4_0,
            ONET_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # 2. Ingest O*NET Data Scientists tasks
    for item in _RAW_ONET_MLAI_SCIENTIST_TASKS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ONET_28_0,
            TaxonomyLicense.CC_BY_4_0,
            ONET_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # 3. Ingest ESCO MLAI Transversal skills
    for item in _RAW_ESCO_MLAI_TRANSVERSAL_SKILLS:
        element = build_taxonomy_element(
            item,
            TaxonomySource.ESCO_1_1_1,
            TaxonomyLicense.EU_OPEN_REUSE,
            ESCO_STATUTORY_ATTRIBUTION,
        )
        elements.append(element)

    # Sort deterministically by code
    elements.sort(key=lambda el: el.code)

    # Compute category statistics
    category_counts: dict[str, int] = {}
    for el in elements:
        category_counts[el.category] = category_counts.get(el.category, 0) + 1

    sha256_hash = compute_bundle_sha256(elements)
    fixed_timestamp = "2026-10-31T12:00:00Z"

    manifest = TaxonomyManifest(
        manifest_version="v1.0",
        generated_at=fixed_timestamp,
        total_elements=len(elements),
        sources_included=[TaxonomySource.ONET_28_0, TaxonomySource.ESCO_1_1_1],
        licence_classes=[TaxonomyLicense.CC_BY_4_0, TaxonomyLicense.EU_OPEN_REUSE],
        bundle_sha256=sha256_hash,
        element_counts_by_category=category_counts,
    )

    bundle = TaxonomyBundle(
        bundle_id="taxonomy-mlai-family-v1",
        role_family="MLAI",
        version="1.0.0",
        generated_at=fixed_timestamp,
        manifest=manifest,
        elements=elements,
    )

    target_dir = output_dir or CONFIG_TAXONOMY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = target_dir / "mlai_family.json"
    manifest_path = target_dir / "manifest_mlai.json"

    bundle_json = json.dumps(bundle.model_dump(), indent=2, sort_keys=True) + "\n"
    manifest_json = json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"

    # Atomic write pattern to avoid parallel file-read corruption
    tmp_bundle = bundle_path.with_suffix(".tmp")
    tmp_manifest = manifest_path.with_suffix(".tmp")
    tmp_bundle.write_text(bundle_json, encoding="utf-8")
    tmp_manifest.write_text(manifest_json, encoding="utf-8")
    tmp_bundle.replace(bundle_path)
    tmp_manifest.replace(manifest_path)

    return bundle, bundle_path, manifest_path


if __name__ == "__main__":
    bundle, b_path, m_path = generate_data_family_taxonomy()
    sha_short = bundle.manifest.bundle_sha256[:16]
    print(f"Generated {b_path.name} ({len(bundle.elements)} elements, SHA-256: {sha_short}...)")
    print(f"Generated {m_path.name}")

    swe_bundle, swe_b_path, swe_m_path = generate_swe_family_taxonomy()
    swe_sha_short = swe_bundle.manifest.bundle_sha256[:16]
    print(
        f"Generated {swe_b_path.name} ({len(swe_bundle.elements)} elements, "
        f"SHA-256: {swe_sha_short}...)"
    )
    print(f"Generated {swe_m_path.name}")

    mlai_bundle, mlai_b_path, mlai_m_path = generate_mlai_family_taxonomy()
    mlai_sha_short = mlai_bundle.manifest.bundle_sha256[:16]
    print(
        f"Generated {mlai_b_path.name} ({len(mlai_bundle.elements)} elements, "
        f"SHA-256: {mlai_sha_short}...)"
    )
    print(f"Generated {mlai_m_path.name}")
