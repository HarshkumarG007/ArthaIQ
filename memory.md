# Project Memory

| Field | Value |
|---|---|
| Purpose | The assistant's starting context and the project's history. Read it first in every session (R-WF-02) |
| Last updated | 2026-10-11 |
| Update rule | Append to the session log after every task. Never delete a decision; supersede it with a new entry |

---

## 1. Read this first

- **What we are building:** a personalized compensation intelligence and decision-support tool. It returns a pay range (P10, P50, P90) with an evidence summary, and abstains when evidence is thin. It is not an appraisal, an offer or a guarantee.
- **Six prediction targets, kept separate:** PT1 market pay for a profile, PT2 comparable cohorts, PT3 offer distribution, PT4 negotiation scenarios, PT5 transition scenarios, PT6 current pay versus benchmark. Only PT1, PT2 and PT6 are in the first release.
- **Where we are:** Step 1 is complete (documents v0.1). Phase 0 is in progress. **NEXT TASK: T0.01.**
- **Scope is a hypothesis (H0):** India, software, data and ML roles, measure `guaranteed_cash_annual`, INR nominal. Nothing is confirmed until gate G2.
- **What exists:** six documents. **No code, no data, no repository, no verified external facts.**
- **Rules that matter most:** R-WF-01 (no skipping ahead), R-EV-03 (never invent facts), R-UQ-01 (no lone numbers), R-DA-01 (licence gate), R-MD-02 (final test set is touched once), R-MD-07 (no hard-coded multipliers).
- **If documents disagree, stop and ask** (R-WF-07).

## 2. Workflow tracker

| Stage | Status | Note |
|---|---|---|
| IDEA | DONE | Master research prompt written |
| RESEARCH | TODO | Phases 1 and 2 |
| DEFINE THE USER | TODO | Personas are hypotheses until T1.03, T1.04 |
| PRD | IN PROGRESS | v0.1 |
| CHOOSE TECH STACK | IN PROGRESS | Proposed in `architecture.md` section 6; ADR-0003 at T3.01 |
| ARCHITECTURE | IN PROGRESS | v0.1 |
| DESIGN | IN PROGRESS | v0.1 |
| PROJECT RULES | IN PROGRESS | v0.1 |
| TASK BREAKDOWN | IN PROGRESS | v0.1 |
| SETUP | TODO | Phase 3 |
| DEVELOPMENT | TODO | Phases 3 to 9 |
| TESTING | TODO | Inside every task; formal pass in Phase 9 |
| SECURITY REVIEW | TODO | T9.12 |
| CODE REVIEW | TODO | T9.13 |
| PREVIEW DEPLOYMENT | TODO | T9.14 |
| QA TESTING | TODO | T9.15 |
| PRODUCTION | TODO | T10.02 |
| MONITORING | TODO | T9.11, T10.03 |
| ITERATION | TODO | T10.06, T10.07 |

## 3. Current status

| Item | Value |
|---|---|
| Phase | 0, Foundation |
| Last completed task | T0.00 |
| Next task | T0.01 |
| Last gate | None yet |
| Document versions | PRD, architecture, rules, design, task, memory: all v0.1 |
| Repository | Not created |
| Code | None |
| Data | None |
| CI | None |

## 4. Gate log

Record GO or NO-GO with the evidence that justified it.

| Gate | Decision | Date | Evidence | Notes |
|---|---|---|---|---|
| G0 | Pending | | | |
| G1 | Pending | | | |
| G2 | Pending | | | Critical: data sufficiency and scope |
| G3 | Pending | | | |
| G4 | Pending | | | Critical |
| G5 | Pending | | | Critical |
| G6 | Pending | | | Critical |
| G7 | Pending | | | Optional branch |
| G8 | Pending | | | Optional branch |
| G9 | Pending | | | Critical |
| G10 | Pending | | | Critical |

## 5. Decisions

| ID | Date | Decision | Status | Reference |
|---|---|---|---|---|
| D-001 | 2026-10-11 | Follow the Vibe Coding Workflow; no skipping from idea to deploy; one gate closes each phase | Accepted | R-WF-01, `task.md` |
| D-002 | 2026-10-11 | The documentation set is six files in `docs/`, plus `docs/research/`, `docs/adr/`, `docs/data-cards/` and `docs/model-cards/` | Accepted | `architecture.md` section 8 |
| D-003 | 2026-10-11 | Prediction targets are named PT1 to PT6 and specified separately | Accepted | PRD section 5 |
| D-004 | 2026-10-11 | Scope hypothesis H0: India, software, data and ML roles, `guaranteed_cash_annual`, INR nominal | Proposed; decided at G2 | ADR-0001, ADR-0002 |
| D-005 | 2026-10-11 | Candidate stack and the benchmark ladder adopted as proposals | Proposed | ADR-0003, ADR-0004 |
| D-006 | 2026-10-11 | Visual direction: the Span, cobalt on cool paper with blue-black ink, IBM Plex pairing | Proposed; confirm at T0.05 | `design.md` |
| D-007 | 2026-10-11 | Evidence grades A, B, C plus abstention; thresholds set at G5 | Proposed | PRD FR-19 |
| D-008 | 2026-10-11 | The research prototype has no web UI; the UI is built in Phase 9 | Proposed | PRD section 6 |

## 6. Open questions

| ID | Question | Why it matters | Blocks | Status |
|---|---|---|---|---|
| Q-001 | Which market first: India, the US, or global? Default H0 is India. | Changes sources, definitions, law and models | G2, ADR-0001 | **Open, blocking** |
| Q-002 | Team size, hours per week, and budget for data and hosting? | Effort estimates, deployment profile | T0.03, ADR-0009 | **Open, blocking** |
| Q-003 | What are your machine's CPU, RAM and GPU? | Chooses deployment profile A, B or C | T3.01 | Open |
| Q-004 | Who is the primary persona, and can you reach some of them for interviews? | Defines the user | T1.03, T1.04 | Open |
| Q-005 | Do you already have licensed or proprietary pay data, partners, or a user base? | The data ceiling | T1.08, T2.02 | Open |
| Q-006 | Is qualified legal counsel available for terms and privacy review, and who signs off? | Licence gate, privacy compliance | T2.02, T9.16 | Open |
| Q-007 | What organizational form and monetization are intended? | Many datasets restrict commercial use `[U]` | T2.02 | Open |
| Q-008 | Confirm the first occupation family (software, data, ML). | Scope | G2 | Open |
| Q-009 | Which pay figure do users think in: fixed, CTC, in-hand or total? | Measure choice | ADR-0002, T1.04 | Open |
| Q-010 | English only at launch? | Localization | After PB | Open, non-blocking |

## 7. Assumptions

| ID | Assumption | Check at |
|---|---|---|
| A-001 | One developer, working with an AI coding assistant | Q-002 |
| A-002 | India first, technology roles | G2 |
| A-003 | Users are mostly on mid-range phones with variable connections | T1.04, T9.15 |
| A-004 | No GPU is available | Q-003 |
| A-005 | Pay data is sensitive; contributions are voluntary and consented | ADR-0008 |
| A-006 | Today is 2026-10-11; all tool versions, laws and source availability must be re-verified | T1.05 to T1.09, T3.01 |
| A-007 | English-only interface in the prototype and beta | Q-010 |

## 8. Known issues and major bugs

| ID | Date | Severity | Description | Status | Workaround | Task |
|---|---|---|---|---|---|---|
| KI-001 | 2026-10-11 | Medium | Every external fact in the v0.1 documents is unverified (`[U]`); no source has been checked | Open | Treat as hypotheses | T1.05 to T1.09 |
| KI-002 | 2026-10-11 | Low | Fonts in `design.md` are not yet tested for the rupee sign or tabular figures | Open | Verify before adoption | T9.07 |
| KI-003 | 2026-10-11 | Low | Time and effort figures in `task.md` are planning assumptions, not estimates from evidence | Open | Re-estimate at each phase start | Phase starts |

Add new rows as `KI-00n`. For a fixed bug, keep the row, set Status to Fixed and add the commit.

## 9. Architectural and document changes

| Date | Change | ADR | Documents touched |
|---|---|---|---|
| 2026-10-11 | Initial architecture and document set, v0.1 | Stubs due at T0.04 | All six |

## 10. Experiment index

One row per run that informs a decision. Hypotheses live in `task.md` Appendix A.

| ID | Date | Hypothesis | Pre-registered | Data snapshot | Commit | Result | Decision |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 11. Data source status

Candidates named in the master research prompt or from general knowledge. **None is verified.** R-EV-03 applies.

| Candidate | Country | Type `[H]` | Verification | Licence status | Next step |
|---|---|---|---|---|---|
| Periodic Labour Force Survey | India | Population benchmark | UNVERIFIED | Not reviewed | T1.06 |
| Labour ministry and Labour Bureau wage sources | India | Population benchmark | UNVERIFIED | Not reviewed | T1.06 |
| BLS occupational wage statistics | US | Population benchmark | UNVERIFIED | Not reviewed | T1.07 |
| Department of Labor wage disclosures | US | Market signal | UNVERIFIED | Not reviewed | T1.07 |
| Job postings with pay ranges | Either | Market signal | Not identified | Not reviewed | T1.08 |
| Licensed salary surveys | Either | Ground truth, if licensed | Not identified | Not reviewed | T1.08 |
| Public developer-survey datasets | Global | Pipeline test data, high selection bias | UNVERIFIED | Not reviewed | T1.08 |
| Voluntary contributions on our own platform | Either | Ground truth, if scale is achieved | Design pending | ADR-0008 | T2.10 |
| Occupation and skill taxonomies | Either | Supplementary | UNVERIFIED | Not reviewed | T1.09 |
| FX, CPI and macro series | Either | Supplementary | UNVERIFIED | Not reviewed | T1.09 |

## 12. Session log

Append-only, newest at the bottom. Archive entries to `docs/memory-archive/` after about fifty entries to keep this file small.

| Date | Task | What happened | Files | Verified | Open items | Next |
|---|---|---|---|---|---|---|
| 2026-10-11 | T0.00 | Generated the six documents from the master research prompt and the workflow template | `docs/PRD.md`, `architecture.md`, `rules.md`, `design.md`, `task.md`, `memory.md` | Contrast ratios and wireframe widths checked by script; cross-references and table structure checked by script (0 problems); both Mermaid diagrams parsed with the Mermaid parser | Q-001 to Q-010; KI-001 to KI-003 | T0.01 |

## 13. How to update this file

1. After each task: add a session-log row, update section 3, and move `NEXT TASK` in `task.md`.
2. After each gate review: fill the gate log row with the decision, date and evidence.
3. Record any decision, assumption, bug or architectural change in its section on the day it happens.
4. Never rewrite history. Supersede a decision with a new row that references the old one.
5. If a rule was bent, cite its id and the reason in the session-log row (R-WF-07).
