# Career Architect Honesty, Evidence & Invariant Rules (30-career-honesty)

| Field | Value |
|---|---|
| Topic | Career Architect Principles, Competency Graph, Evidence Ledger, and Anti-Causal Invariants |
| Governing Rule Families | `R-CR` (R-CR-01 to R-CR-15), PRD Section 12, ADR-0010 |
| Audience | AI Assistant, Engineers, Content Reviewers, Data Scientists |

---

## The Career Architect Invariants (R-CR)

| ID | Rule | Description |
|---|---|---|
| **R-CR-01** | **No Causal Pay Language** | Outputs never state or imply that learning a skill, earning a certificate, or finishing a scenario raises pay or guarantees job placement. "Associated with" is allowed only when citing verified empirical research. |
| **R-CR-02** | **Two Separate Streams** | Pay evidence and role competency requirements remain separate objects in the API and separate panels in the UI. No composite score ever fuses them. |
| **R-CR-03** | **State Beats Score** | Show ledger states (`Unproven`, `Self-reported`, `Demonstrated`), counts, and verification dates. Never emit readiness percentages or composite ability scores. |
| **R-CR-04** | **Provenance on Every Item** | Every skill, prerequisite, level requirement, scenario, and rubric carries source ID, reviewer name, review date, version, and review status. Unreviewed items are hidden or labelled `Draft`. |
| **R-CR-05** | **Heuristics Explicitly Labelled** | Difficulty and effort estimates must be visibly labelled `Heuristic` until a pre-registered volume of empirical attempts supports calibration. |
| **R-CR-06** | **Pay Overlay Obeys Engine** | Queries compensation port only; preserves $k_{\min} \ge 5$, conformal prediction intervals, and honest abstention. Never extrapolates to roles the engine cannot support. |
| **R-CR-07** | **Interests Only Reorder** | User interests only reorder exploration paths; they never modify required competency bars or imply candidate ability. |
| **R-CR-08** | **Deterministic Scoring** | Scenario scores are derived deterministically from rubrics and expected findings. Any model-written feedback is advisory, labelled, behind a feature flag, and cannot alter scores. |
| **R-CR-09** | **Pasted Text is Untrusted Data** | Job descriptions and resumes are length-capped, sanitized, rendered safely, and never placed in privileged system instructions. |
| **R-CR-10** | **Approved Taxonomies Only** | Taxonomies load only from approved sources: O*NET (CC BY 4.0 attribution), ESCO (EU Commission reuse acknowledgment). Unverified registries (NQR) remain restricted. |
| **R-CR-11** | **Practice, Not Certification** | UI copy and visuals never imply a credential, badge, official certificate, or employer endorsement. |
| **R-CR-12** | **Local-First Personal Data** | Profiles, skill ledgers, and roadmaps reside on the user's device via IndexedDB by default. No user accounts or server storage in MVP. |
| **R-CR-13** | **Zero Dark Patterns** | No streaks, countdowns, false urgency, or gating roadmaps behind salary data contribution. |
| **R-CR-14** | **Decoupled Fallback Utility** | The user journey remains 100% useful when the pay engine abstains or when the user is offline. |
| **R-CR-15** | **LLM Boundary (ADR-0010)** | Zero runtime LLM on serving path. Offline authoring assistance only; forbidden from the runtime request path. |
