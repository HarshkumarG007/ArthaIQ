"""Calibrated difficulty and effort heuristic rubric engine for SWE family (Task T16.03).

Enforces Rule R-CR-05:
1. Difficulty ratings (learning and application) anchored on 1.0-5.0 scales.
2. Labelled heuristic with statutory non-guarantee disclaimers.
3. Effort expressed strictly as ranges in hours, never single-point false precision.
4. Zero causal pay or career advancement promises.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from compintel.career.schema import (
    DifficultyAnchorDefinition,
    DifficultyRubricEntry,
    DifficultyRubricsManifest,
    EffortRange,
    validate_anti_causal_text,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_SWE_RUBRICS_PATH = REPO_ROOT / "config" / "taxonomy" / "difficulty_rubrics_swe.json"

HEURISTIC_DISCLAIMER = (
    "Estimated based on practitioner consensus. Individual effort varies with prior background."
)

SWE_LEARNING_ANCHORS: list[dict[str, Any]] = [
    {
        "scale": "learning",
        "level": 1.0,
        "label": "Introductory / Declarative",
        "anchor_description": (
            "Syntax-level understanding self-teachable in under 15 hours "
            "without formal prerequisites."
        ),
        "typical_signals": [
            "Follows basic documentation tutorials without debugging",
            "Understands basic control flow, variables, and primitive data types",
        ],
    },
    {
        "scale": "learning",
        "level": 2.0,
        "label": "Foundational Practical",
        "anchor_description": (
            "Standard tooling workflows, unit testing, and modular coding "
            "mastered in 15 to 40 hours with basic programming prerequisites."
        ),
        "typical_signals": [
            "Uses git commands for branching, committing, and rebasing",
            "Writes structured unit test cases and basic HTTP API endpoints",
        ],
    },
    {
        "scale": "learning",
        "level": 3.0,
        "label": "Intermediate Systemic",
        "anchor_description": (
            "Requires multi-step architectural reasoning, concurrency primitives, "
            "and resilience patterns (25 to 60 hours)."
        ),
        "typical_signals": [
            "Implements thread-safe data access and circuit breakers",
            "Optimizes database indexes and constructs automated CI/CD pipelines",
        ],
    },
    {
        "scale": "learning",
        "level": 4.0,
        "label": "Advanced Methodological / Architectural",
        "anchor_description": (
            "Distributed consensus theory, event streaming semantics, and cryptographic "
            "storage standards demanding deep technical foundations (45 to 100 hours)."
        ),
        "typical_signals": [
            "Evaluates state machine replication and quorum tradeoffs",
            "Designs transactional outbox patterns and verifiable deletion protocols",
        ],
    },
    {
        "scale": "learning",
        "level": 5.0,
        "label": "Expert Frontier",
        "anchor_description": (
            "Novel distributed systems protocols, kernel-level zero-copy optimizations, "
            "and global high-availability architectures (>100 hours)."
        ),
        "typical_signals": [
            "Designs Byzantine fault tolerant consensus algorithms",
            "Architects multi-region active-active partitionable cloud topologies",
        ],
    },
]

SWE_APPLICATION_ANCHORS: list[dict[str, Any]] = [
    {
        "scale": "application",
        "level": 1.0,
        "label": "Isolated Templated",
        "anchor_description": (
            "Execution within clean sandbox environments against scripted expectations."
        ),
        "typical_signals": [
            "Clones repository and runs established test suites cleanly",
            "Implements boilerplate endpoint functions matching existing patterns",
        ],
    },
    {
        "scale": "application",
        "level": 2.0,
        "label": "Guided Production",
        "anchor_description": (
            "Applied to production codebases with established peer review, CI, and standards."
        ),
        "typical_signals": [
            "Submits atomic pull requests with passing automated test fixtures",
            "Builds standardized REST/gRPC endpoints with schema validation",
        ],
    },
    {
        "scale": "application",
        "level": 3.0,
        "label": "Unconstrained Real-World",
        "anchor_description": (
            "Navigates messy legacy codebases, asynchronous race hazards, "
            "and intermittent operational failures."
        ),
        "typical_signals": [
            "Debugs intermittent race conditions and memory leaks under load",
            "Restructures slow database queries and handles service timeouts",
        ],
    },
    {
        "scale": "application",
        "level": 4.0,
        "label": "High-Stakes Production",
        "anchor_description": (
            "Mission-critical applications where mistakes compromise live service availability, "
            "data consistency, or system security."
        ),
        "typical_signals": [
            "Architects zero-downtime database migrations on high-traffic tables",
            "Hardens multi-tenant services against OWASP Top 10 vulnerabilities",
        ],
    },
    {
        "scale": "application",
        "level": 5.0,
        "label": "Strategic Enterprise Architecture",
        "anchor_description": (
            "Organizational-level impact involving distributed cluster survivability, "
            "statutory data protection compliance, and mission-critical failover."
        ),
        "typical_signals": [
            "Resolves split-brain network partition anomalies in consensus clusters",
            "Implements end-to-end cryptographic erasure satisfying DPDP Act Sec 12",
        ],
    },
]

SWE_FAMILY_RUBRIC_ENTRIES: list[dict[str, Any]] = [
    # ------------------ Level 2: Junior / Foundations & Core Skills ------------------
    {
        "node_id": "swe.gen.l2_git_hygiene",
        "learning_difficulty": 2.0,
        "application_difficulty": 2.0,
        "effort_hours": {"min_hours": 15, "max_hours": 25},
        "learning_rationale": (
            "Trunk-based development, commit atomicity, branch workflows, and rebase "
            "strategies covered in standard version control curricula."
        ),
        "application_rationale": (
            "Resolving complex merge conflicts and maintaining clean linear git history "
            "across multi-developer repositories."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.core.l2_data_structures",
        "learning_difficulty": 2.0,
        "application_difficulty": 2.0,
        "effort_hours": {"min_hours": 25, "max_hours": 40},
        "learning_rationale": (
            "Asymptotic time and space complexity analysis, hash tables, balanced trees, "
            "and graph representations taught in core computer science curricula."
        ),
        "application_rationale": (
            "Selecting optimal data structures and minimizing algorithmic bottlenecks "
            "in production application logic."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.core.l2_concurrency",
        "learning_difficulty": 3.0,
        "application_difficulty": 3.0,
        "effort_hours": {"min_hours": 25, "max_hours": 45},
        "learning_rationale": (
            "Multithreaded execution, async event loops, race conditions, mutexes, "
            "and deadlocks require rigorous mental models."
        ),
        "application_rationale": (
            "Designing thread-safe in-memory state mutations and preventing "
            "asynchronous race hazards in production services."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.arch.l2_api_design",
        "learning_difficulty": 2.0,
        "application_difficulty": 3.0,
        "effort_hours": {"min_hours": 20, "max_hours": 35},
        "learning_rationale": (
            "HTTP semantics, REST conventions, gRPC protobuf schemas, and RFC 9457 "
            "error contracts follow established industry specifications."
        ),
        "application_rationale": (
            "Authoring backward-compatible API contracts, idempotency key validation, "
            "and resilient error contracts in distributed environments."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.test.l2_unit_tdd",
        "learning_difficulty": 2.0,
        "application_difficulty": 2.0,
        "effort_hours": {"min_hours": 15, "max_hours": 30},
        "learning_rationale": (
            "Automated test structure, test doubles, assertions, and property-based "
            "testing principles are standard engineering disciplines."
        ),
        "application_rationale": (
            "Writing deterministic unit tests with isolated test doubles and mutation "
            "testing coverage without flaky execution."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.ops.l2_container_docker",
        "learning_difficulty": 2.0,
        "application_difficulty": 2.0,
        "effort_hours": {"min_hours": 15, "max_hours": 25},
        "learning_rationale": (
            "OCI container standards, multi-stage Dockerfiles, filesystem layers, "
            "and Linux cgroup isolation concepts."
        ),
        "application_rationale": (
            "Building minimal-footprint, non-root container images with pinned digest "
            "dependencies and zero unneeded build tools."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    # ------------------ Level 3: Mid / Architecture, Resiliency & Quality ------------------
    {
        "node_id": "swe.core.l3_memory_perf",
        "learning_difficulty": 3.0,
        "application_difficulty": 4.0,
        "effort_hours": {"min_hours": 30, "max_hours": 50},
        "learning_rationale": (
            "Runtime memory layouts, heap and stack escape analysis, garbage collection "
            "pauses, and allocator internals."
        ),
        "application_rationale": (
            "Diagnosing silent memory leaks, object retention cycles, and thread "
            "heap churn under high-throughput production load."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.arch.l3_microservices",
        "learning_difficulty": 3.0,
        "application_difficulty": 4.0,
        "effort_hours": {"min_hours": 35, "max_hours": 60},
        "learning_rationale": (
            "Distributed systems failure patterns, network partitions, bulkhead "
            "patterns, circuit breakers, and load shedding theory."
        ),
        "application_rationale": (
            "Implementing bounded retries with jitter, graceful degradation fallbacks, "
            "and preventing cascading failures across interconnected services."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.db.l3_query_perf",
        "learning_difficulty": 3.0,
        "application_difficulty": 3.0,
        "effort_hours": {"min_hours": 25, "max_hours": 45},
        "learning_rationale": (
            "Relational database engine internals, B-tree index structures, join "
            "algorithms, and execution plan operators."
        ),
        "application_rationale": (
            "Analyzing EXPLAIN query plans, eliminating N+1 query antipatterns, "
            "resolving table lock contention, and optimizing composite indexes."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.sec.l3_owasp_top10",
        "learning_difficulty": 3.0,
        "application_difficulty": 4.0,
        "effort_hours": {"min_hours": 30, "max_hours": 50},
        "learning_rationale": (
            "OWASP vulnerability taxonomies including injection flaws, broken access "
            "controls, SSRF, and cryptographic failures."
        ),
        "application_rationale": (
            "Enforcing parameterized queries, secure session lifecycles, defense-in-depth "
            "sanitization, and automated security scans in CI."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.rel.l3_observability",
        "learning_difficulty": 3.0,
        "application_difficulty": 3.0,
        "effort_hours": {"min_hours": 20, "max_hours": 40},
        "learning_rationale": (
            "Telemetry signals (logs, metrics, traces), OpenTelemetry standards, "
            "RED and USE monitoring methodologies."
        ),
        "application_rationale": (
            "Correlating distributed spans across asynchronous microservices, "
            "authoring structured JSON logs, and defining actionable alert thresholds."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.ops.l3_cicd_pipeline",
        "learning_difficulty": 3.0,
        "application_difficulty": 3.0,
        "effort_hours": {"min_hours": 25, "max_hours": 45},
        "learning_rationale": (
            "Continuous delivery theory, immutable release artifacts, deployment "
            "topologies (blue-green, canary), and pipeline hermeticity."
        ),
        "application_rationale": (
            "Authoring automated deployment pipelines with health check gates, "
            "zero-downtime rolling updates, and automated rollback."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    # ------------------ Level 4: Senior / Distributed Systems & Compliance ------------------
    {
        "node_id": "swe.sys.l4_dist_consensus",
        "learning_difficulty": 4.0,
        "application_difficulty": 5.0,
        "effort_hours": {"min_hours": 60, "max_hours": 100},
        "learning_rationale": (
            "Formal distributed consensus proofs, Raft/Paxos state machine replication, "
            "split-brain scenarios, and CAP/PACELC tradeoffs."
        ),
        "application_rationale": (
            "Diagnosing split-brain quorum failures, lease expiration bugs, and "
            "linearizable consistency violations in distributed stateful clusters."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.arch.l4_event_driven",
        "learning_difficulty": 4.0,
        "application_difficulty": 4.0,
        "effort_hours": {"min_hours": 45, "max_hours": 75},
        "learning_rationale": (
            "Event-driven messaging architectures, log-structured event brokers, "
            "exactly-once processing semantics, and eventual consistency models."
        ),
        "application_rationale": (
            "Implementing transactional outbox patterns, idempotent event consumers, "
            "poison pill dead-letter queues, and schema evolution."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
    {
        "node_id": "swe.sec.l4_crypto_dpdp",
        "learning_difficulty": 4.0,
        "application_difficulty": 5.0,
        "effort_hours": {"min_hours": 50, "max_hours": 85},
        "learning_rationale": (
            "Modern cryptography primitives (envelope encryption, HMAC, AEAD), "
            "zero-knowledge verification, and India DPDP Act 2023 statutory obligations."
        ),
        "application_rationale": (
            "Engineering provable cryptographic erasure, verifiable cold storage "
            "hard-delete pipelines (DPDP Act Sec 12), and key rotation without downtime."
        ),
        "is_heuristic": True,
        "disclaimer": HEURISTIC_DISCLAIMER,
    },
]


def build_swe_difficulty_rubrics_manifest() -> DifficultyRubricsManifest:
    """Build the canonical DifficultyRubricsManifest for the SWE role family."""
    learning_anchors = [
        DifficultyAnchorDefinition.model_validate(anchor) for anchor in SWE_LEARNING_ANCHORS
    ]
    application_anchors = [
        DifficultyAnchorDefinition.model_validate(anchor) for anchor in SWE_APPLICATION_ANCHORS
    ]
    entries = [
        DifficultyRubricEntry(
            node_id=item["node_id"],
            learning_difficulty=item["learning_difficulty"],
            application_difficulty=item["application_difficulty"],
            effort_hours=EffortRange.model_validate(item["effort_hours"]),
            learning_rationale=item["learning_rationale"],
            application_rationale=item["application_rationale"],
            is_heuristic=True,
            disclaimer=item["disclaimer"],
        )
        for item in SWE_FAMILY_RUBRIC_ENTRIES
    ]

    # Rule R-CR-01 anti-causal copy validation
    for entry in entries:
        validate_anti_causal_text(entry.learning_rationale, "learning_rationale")
        validate_anti_causal_text(entry.application_rationale, "application_rationale")

    return DifficultyRubricsManifest(
        schema_version="1.0.0",
        role_family="SWE",
        heuristic_disclaimer=HEURISTIC_DISCLAIMER,
        learning_anchors=learning_anchors,
        application_anchors=application_anchors,
        entries=entries,
    )


def export_swe_difficulty_rubrics(output_path: Path | None = None) -> tuple[Path, str]:
    """Deterministically serialize the SWE rubrics manifest to JSON with SHA-256."""
    target_path = output_path or DEFAULT_SWE_RUBRICS_PATH
    manifest = build_swe_difficulty_rubrics_manifest()

    target_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = manifest.model_dump_json(indent=2) + "\n"
    target_path.write_text(serialized, encoding="utf-8")

    checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return target_path, checksum


def load_swe_difficulty_rubrics(input_path: Path | None = None) -> DifficultyRubricsManifest:
    """Load and validate the SWE difficulty rubrics manifest from JSON."""
    target_path = input_path or DEFAULT_SWE_RUBRICS_PATH
    if not target_path.is_file():
        raise FileNotFoundError(f"SWE rubrics file not found at {target_path}")

    raw_data = json.loads(target_path.read_text(encoding="utf-8"))
    return DifficultyRubricsManifest.model_validate(raw_data)


def get_swe_competency_rubric(
    node_id: str, manifest: DifficultyRubricsManifest | None = None
) -> DifficultyRubricEntry:
    """Retrieve rubric calibration entry for a specific SWE competency node."""
    active_manifest = manifest or load_swe_difficulty_rubrics()
    for entry in active_manifest.entries:
        if entry.node_id == node_id:
            return entry
    raise KeyError(f"SWE competency node '{node_id}' not found in difficulty rubrics")
