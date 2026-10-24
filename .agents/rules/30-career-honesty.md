---
trigger: glob
description: Career Architect invariants, anti-causal pay rules, deterministic scoring, and provenance standards
globs: src/compintel/career/**
---

# Career Architect Invariant Rules (R-CR)

Consult canonical specification in `docs/rules/30-career-honesty.md`.

## Key Invariants
1. **R-CR-01:** No causal pay claims. Never claim learning skill X raises salary by ₹Y.
2. **R-CR-02:** Two separate streams. Pay evidence and competency requirements are separate objects and panels. Zero composite scores.
3. **R-CR-03:** State beats score. Ledger states (`Unproven`, `Self-reported`, `Demonstrated`), counts, and dates replace percentages.
4. **R-CR-04:** Provenance on every item (source ID, reviewer, review date, version, status).
5. **R-CR-05:** Heuristics explicitly labelled (`Heuristic` tag on effort/difficulty estimates).
6. **R-CR-06:** Pay overlay obeys compensation engine ($k_{\min} \ge 5$, conformal bounds, honest abstention).
7. **R-CR-07:** Interests only reorder exploration paths, never alter requirements.
8. **R-CR-08:** Deterministic scoring from rubrics and expected findings. Model feedback is advisory only.
9. **R-CR-09:** Pasted job descriptions and résumés are untrusted data, length-capped and sanitized.
10. **R-CR-11:** Practice, not certification. No badges, credentials, or employer recognition claims.
11. **R-CR-12:** Local-first personal data. IndexedDB on-device; zero server profiles in MVP.
12. **R-CR-14:** 100% useful when pay engine abstains or when offline.
13. **R-CR-15:** LLM boundary (ADR-0010): zero runtime LLM on serving path.
