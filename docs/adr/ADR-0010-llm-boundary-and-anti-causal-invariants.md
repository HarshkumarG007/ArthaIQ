# ADR-0010: LLM Boundary, Serving Isolation, and Anti-Causal Invariants

| Field | Value |
|---|---|
| Status | **Accepted** |
| Decided at | T15.04 (2026-10-24) |
| Relates to | `rules.md` R-SC-07, R-CR-01, R-CR-02, R-CR-15; PRD v1.2 sections 1, 7 (FR-25), 12; `architecture.md` section 4 |

---

## Context

With the introduction of the Career Architect module (Phase 15), ArthaIQ assists tech professionals in identifying competency gaps, generating practice roadmaps, and engaging with realistic engineering scenarios. Generative AI and Large Language Models (LLMs) present compelling capabilities for text synthesis and scenario generation. However, placing an LLM on the runtime serving path introduces grave technical and ethical failure modes:
1. **Unpredictable Latency & High Costs:** LLM inference introduces 500ms–3000ms latency and per-token operating costs, violating ArthaIQ's sub-50ms p95 latency target (NFR-02) and lean hosting budget (NFR-03, Profile B).
2. **Non-Deterministic Hallucination & Fabrication:** LLMs hallucinate salary figures, invent fake employer bands, or confabulate non-existent skills, directly violating Rule `R-AI-01` (Zero Fabrication).
3. **Causal Pay Fallacy:** LLMs readily generate persuasive but empirically unproven causal claims (e.g. "Acquiring Apache Spark will increase your pay by ₹4.5 LPA"), violating PRD Section 1 and Rule `R-CR-01`.
4. **Prompt Injection & Security Vulnerabilities:** Ingesting untrusted job descriptions or résumés into an LLM context creates prompt injection surfaces (OWASP LLM Top 10), violating Rule `R-CR-09`.

## Decisions

### 1. Absolute Prohibition of Runtime LLMs on the Serving Path

**Accepted:** No Large Language Model (remote API or local weights) may be placed on the runtime synchronous request/serving path.
- All real-time API endpoints (compensation estimation, gap analysis, roadmap calculation, rubric scoring) must execute purely deterministic, compiled Python and TypeScript logic.
- Runtime latency remains sub-50ms p95 on CPU-only standard container hosting.

### 2. Quarantined Offline / Batch Model Usage

**Accepted:** If local model acceleration or LLMs are utilized for authoring assistance or offline artifact compilation:
- Model execution is restricted strictly to offline, batch, or developer-in-the-loop workflows on local hardware (e.g. RTX 4060 Laptop on the Lenovo Legion Pro 5i).
- All generated scenarios, taxonomies, or rubrics must be serialized into deterministic static artifacts (YAML/JSON), audited for errors and leakage, human-reviewed, and checked into Git under version control before serving.
- Zero external LLM API calls during user runtime.

### 3. Strict Anti-Causal Pay Invariant

**Accepted:** The compensation engine and career guidance engine remain strictly decoupled.
- The system must **never** claim, imply, calculate, or display a causal relationship between acquiring a skill, earning a credential, or completing a scenario and an increase in compensation.
- Language such as "ROI of learning X", "boost your salary by ₹Y", or "salary unlocked" is permanently prohibited across all UI copy, API documentation, and code docstrings (`Rule R-CR-01`).
- Pay figures may only be rendered as independent market distribution overlays ($P_{10}, P_{50}, P_{90}$) for a role and level, accompanied by the standard decision-support disclaimer.

### 4. Two Streams, Two Places Architecture

**Accepted:** Pay evidence and competency requirements remain completely independent data streams.
- The API must return pay distributions and competency gaps as separate top-level JSON objects.
- The UI must render pay estimates and career roadmaps in separate, decoupled panels (`Rule R-CR-02`).
- Zero composite readiness scores (e.g. "82% compensation readiness") that blend empirical market pay data with subjective competency evaluations.

## Consequences

- **Positive:** Preserves 100% deterministic reproducibility, sub-50ms inference latency, lean infrastructure costs ($28.50/month), zero prompt-injection vectors, and unwavering ethical compliance.
- **Negative:** Requires deterministic algorithms (topological sorting, regex/TF-IDF token matchers) and human-in-the-loop curation of scenario defect catalogs rather than free-form conversational text generation.
