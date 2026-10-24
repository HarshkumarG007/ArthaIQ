---
name: author-scenario
description: Author a deterministic flaw-finding practice scenario with realistic artifacts, rubrics, and seeded defects
---

# Author Scenario Procedure

Follow this procedure for authoring deterministic flaw-finding scenarios for Career Architect:

1. **Select Competency & Level:** Identify the target competency from the DATA graph and the target seniority level (Junior or Mid).
2. **Draft Seeded Defects:** Create 2–4 realistic, domain-grounded flaws (e.g., metric misalignment, SQL division by zero, experiment lookahead leakage). For each defect, define:
   - Defect type and code line location
   - Real-world technical or business consequence
   - Correct diagnosis explanation
3. **Formulate Rubric:**
   - Full credit for identifying actual seeded defects.
   - Partial credit for correct identification with minor imprecision in justification.
   - Explicit false-flag penalty for flagging correct, intended code/queries.
4. **Draft Seeded Variants:** Create at least 2 parameterized variants with different variable names or metric contexts to prevent memorization.
5. **Enforce Invariants:**
   - Verify `R-CR-08`: Scoring must be 100% deterministic based on rubrics.
   - Verify `R-CR-11`: No badges, credential claims, or "exam" terminology.
   - Verify `R-CR-04`: Include source ID, author, reviewer, date, and version.
6. **Leakage Test:** Author automated test asserting that answer keys and rubric defect locations are not sent to the client ahead of submission.
