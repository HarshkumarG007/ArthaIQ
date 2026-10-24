# ADR-0012: Local-First Career Profile, IndexedDB Storage, and Privacy Architecture

| Field | Value |
|---|---|
| Status | **Accepted** |
| Decided at | T15.04 (2026-10-24) |
| Relates to | `rules.md` R-CR-09, R-CR-12, R-CR-14, R-DA-07, R-SC-01; PRD v1.2 sections 7 (FR-22, FR-26), 13; India DPDP Act 2023 |

---

## Context

Career exploration involves highly sensitive personal data: unannounced job transitions, skill deficiencies, employer dissatisfaction, and confidential résumés. Storing such data in a centralized backend database creates a high-value honey pot, increases compliance liability under the India Digital Personal Data Protection (DPDP) Act 2023, and requires complex account architectures.

## Decisions

### 1. Local-First Architecture via Browser IndexedDB

**Accepted:** In MVP and initial production, all user career profiles, competency ledgers, learning progress, and practice exercise attempts reside strictly on the user's local device in browser `IndexedDB` (`Rule R-CR-12`).
- Zero server-side career profile database in MVP.
- No user sign-in or account creation is required to use the Career Architect dashboard, gap analysis, or practice scenarios.
- The web application loads static taxonomy data and scenario bundles, executing graph evaluations and roadmap generation client-side.

### 2. Complete Offline Functionality & Decoupled Resilience

**Accepted:** Career Architect features must remain 100% operational when the device is offline or when the compensation estimation engine abstains due to thin data (`Rule R-CR-14`).
- All core competency models, gap matrices, and scenario rubrics are packaged as static client assets.
- If the user requests compensation data, a decoupled query is made to the compensation engine. If the compensation engine abstains, the career dashboard displays the standard `AbstentionNotice` while preserving full access to skill gaps and roadmaps (`Rule R-CR-06`).

### 3. Local Data Sovereignty & Single-Click Erasure

**Accepted:** Users maintain complete control over their career data:
- **Instant JSON Export:** The user can export their complete evidence ledger and progress at any time as a portable JSON artifact.
- **Single-Click Hard Erasure:** The UI provides a prominent "Reset All Career Data" button that completely clears the local `IndexedDB` store in $< 200\text{ ms}$, satisfying DPDP 2023 right to erasure without network dependencies.

### 4. Sanitized, Untrusted Intake for External Text

**Accepted:** Pasted job descriptions and résumé text are treated as untrusted data (`Rule R-CR-09`):
- Intake is strictly length-capped (maximum 32 KB / 32,000 characters).
- Sanitized client-side using DOMPurify; HTML tags and script elements are stripped.
- Parsed locally using regex tokenization and TF-IDF matching against the controlled taxonomy.
- Pasted text is never transmitted to the server or incorporated into any LLM prompt.

## Consequences

- **Positive:** Radical privacy protection, zero cloud database risk, automatic DPDP 2023 compliance for career data, instant offline loading, and zero backend infrastructure operational cost for user profiles.
- **Negative:** Progress does not automatically synchronize across multiple devices unless the user manually exports and imports their JSON profile artifact. (Cross-device encrypted sync deferred to a future phase with explicit opt-in).
