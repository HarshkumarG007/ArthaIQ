# ADR-0013: Deterministic Scenario Scoring and Flaw-Finding Practice Engine

| Field | Value |
|---|---|
| Status | **Accepted** |
| Decided at | T15.04 (2026-10-24) |
| Relates to | `rules.md` R-CR-08, R-CR-11; PRD v1.2 sections 7 (FR-24), 12; `architecture.md` section 4 |

---

## Context

Most online technical assessment tools rely on either trivial multiple-choice questions (easily memorized or guessed) or subjective open-ended LLM grading (notoriously non-reproducible, prone to hallucination, and sensitive to prompt manipulation). ArthaIQ requires an objective, practical, and deterministic assessment methodology that genuinely tests technical reasoning without gamified credentialism.

## Decisions

### 1. Flaw-Finding Practice Paradigm

**Accepted:** Career Architect replaces multiple-choice questions with realistic, domain-grounded **flaw-finding practice challenges**:
- The user is presented with realistic engineering artifacts: e.g. a SQL aggregation query with subtle lookahead leakage, a pipeline configuration with divide-by-zero vulnerability, or an A/B test analysis with sample ratio mismatch.
- The user navigates the code artifact (using keyboard shortcuts `j`/`k` to move between lines, and `f` to flag a line) and selects the specific flaw category and explains the business or technical risk.

### 2. 100% Deterministic Rubric Scoring

**Accepted:** Scenario scoring is strictly deterministic and rule-based (`Rule R-CR-08`):
- Each scenario has a pre-registered rubric defining exact flaw line numbers, target flaw categories, and valid justification tokens.
- **Scoring Formula:**
  $$\text{Score} = \sum_{\text{seeded flaws}} \text{Credit}(\text{flaw}_i) - \sum_{\text{false flags}} \text{Penalty}(\text{flag}_j)$$
- **False-Flag Penalty:** Flagging correct, non-defective lines incurs a penalty to prevent brute-force guessing or selecting all lines.
- LLM or AI model assistance, if used for qualitative advisory feedback, has zero influence on the numerical score.

### 3. Anti-Leakage Architecture

**Accepted:** To prevent client-side inspection and cheating:
- Scenario practice payloads sent to the client contain only the challenge code, metadata, and task description.
- Rubric answer keys, defect locations, and grading weights are withheld from client payloads and evaluated server-side or revealed only upon final submission.
- Automated tests verify zero rubric leakage in client-facing payloads.

### 4. Practice, Not Certification

**Accepted:** ArthaIQ provides capability practice and self-reflection, not official credentialing (`Rule R-CR-11`):
- Terms such as "certified", "exam", "grade", or "credential" are prohibited.
- Successful completion of a scenario awards a verifiable `Demonstrated` state entry in the user's local evidence ledger with the date and scenario ID.
- No public badges, employer ranking, or shareable credential URLs are issued.

## Consequences

- **Positive:** Objective evaluation, impervious to prompt manipulation, tests actual diagnostic capabilities, and avoids credential inflation.
- **Negative:** Requires careful authoring of realistic scenarios, defect catalogs, and parameter variants to prevent answer sharing.
