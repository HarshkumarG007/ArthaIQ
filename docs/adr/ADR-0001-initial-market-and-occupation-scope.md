# ADR-0001: Initial Market and Occupation Scope

| Field | Value |
|---|---|
| Status | **Proposed** |
| Decided at | G2 |
| Relates to | PRD section 4 (H0), `memory.md` D-004 |

---

## Context

The system needs a first market and occupation scope. The master research prompt requires a recommendation on the most defensible first market. H0 is a starting hypothesis, not a decision. Phase 2 research (T1.06 to T1.13, T2.09) confirms or replaces it.

**Scope hypothesis H0:**
- Market: India; amounts in INR, nominal
- Occupation family: software, data and ML roles
- Population: salaried full-time employees

Alternatives considered:
- US first (richer public wage disclosures may exist `[U]`)
- Global from day one (rejected for MVP)
- A broader white-collar set
- One occupation only

## Options

| Option | Pros | Cons |
|---|---|---|
| H0: India, software/data/ML | Familiar market; large addressable population; CTC complexity is a solvable research problem | PLFS granularity for tech roles is unknown `[U]`; licensed survey access unclear |
| US first | BLS OEWS and LCA data are well-documented `[U]`; richer public disclosures | Outside the initial target user; different measure conventions |
| Global | Maximum coverage | Representative data almost certainly unavailable everywhere at MVP; increases legal complexity |

## Decision

**Market: India — confirmed by the user on 2026-10-11 (Q-001).**
**Occupation family: Software engineering, data and ML/AI roles (deliberately limited initial scope) — confirmed by the user on 2026-10-13 (Q-008, T0.02).**

This scope remains subject to the G2 data sufficiency gate; if no India tech combination meets the sufficiency criteria (T2.09), the scope is re-opened.

If no combination meets the sufficiency criteria, the answer is **no-go on modelling** and the project switches to the data acquisition programme (T2.10).

## Consequences

- Scope in the PRD is updated from H0 to the decided values at T2.11.
- ADR-0002 is updated at the same time (measure decision).
- All feature specifications and source catalogs are written against the decided scope.

## Evidence

| Claim | Source | Status |
|---|---|---|
| PLFS covers tech occupations at usable granularity | `[U]` | Unverified; check at T1.06 |
| BLS OEWS covers software and ML titles usefully | `[U]` | Unverified; check at T1.07 |

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
