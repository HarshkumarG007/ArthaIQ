# ADR-0011: Competency Graph, Taxonomy Provenance, and Evidence Ledger

| Field | Value |
|---|---|
| Status | **Accepted** |
| Decided at | T15.04 (2026-10-24) |
| Relates to | `rules.md` R-CR-03, R-CR-04, R-CR-05, R-CR-07; PRD v1.2 sections 7 (FR-21, FR-22, FR-23), 12; `architecture.md` section 4 |

---

## Context

Career exploration platforms often present users with arbitrary skill lists, opaque percentage progress bars ("73% Python mastery"), and unverified claims of readiness. In contrast, ArthaIQ requires rigorous provenance, auditable taxonomy ingestion, and verifiable capability tracking without misleading pseudo-precision.

## Decisions

### 1. Controlled Taxonomy Ingestion with Strict Attribution

**Accepted:** Competency nodes and relationships are ingested exclusively from vetted, open public labour taxonomies:
- **O*NET 28.0 (US DOL):** Released under Creative Commons Attribution 4.0 International (CC BY 4.0). Used for core skill clusters and task descriptions.
- **ESCO v1.1.1 (European Commission):** Used for standardized occupation definitions under EU open reuse terms.
- **Attribution & Provenance:** Every ingested competency node must persist complete provenance metadata (`source_id`, `original_code`, `reviewer_name`, `review_date`, `version`, and `status`).

### 2. Directed Acyclic Graph (DAG) for the DATA Family

**Accepted:** Competencies are structured as a Directed Acyclic Graph:
- Nodes represent granular competencies (e.g. `SQL Aggregations`, `Window Functions`, `ETL Validation`).
- Edges represent strict prerequisite dependencies (`is_prerequisite_of`). Cycles are mathematically prohibited and validated by graph topological invariants.
- Initial production slice focuses on the **DATA family** (Data Analyst: Junior to Mid levels).

### 3. State Beats Score: Tri-State Verification Model

**Accepted:** Continuous "readiness percentages" or composite competency scores are prohibited (`Rule R-CR-03`).
- Competencies are tracked using an honest, discrete tri-state enum:
  1. `Unproven`: Prerequisite or core requirement with zero recorded evidence.
  2. `Self-reported`: User attests familiarity or past experience (dated self-declaration).
  3. `Demonstrated`: Capability verified by deterministic completion of an ArthaIQ flaw-finding practice scenario, code exercise, or verified artifact.
- The UI displays counts, verification timestamps, and evidence badges rather than arbitrary aggregated percentage bars.

### 4. Dependency-Aware Roadmap Generation

**Accepted:** Learning roadmaps are computed via deterministic topological sort (Kahn's algorithm) constrained by user weekly available hours:
- Prerequisites must always be scheduled before dependent advanced topics.
- Study effort and difficulty estimates must carry an explicit `Heuristic` badge (`Rule R-CR-05`) to prevent users from mistaking empirical estimates for guarantees.
- User interests may reorder parallel branches of exploration but can never remove or bypass prerequisite requirements (`Rule R-CR-07`).

## Consequences

- **Positive:** Full auditability, clear verification state, zero deceptive progress gamification, robust graph integrity.
- **Negative:** Requires rigorous curation of prerequisite graph edges and schema validation for taxonomy updates.
