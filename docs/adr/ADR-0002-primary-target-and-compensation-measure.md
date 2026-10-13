# ADR-0002: Primary Target and Compensation Measure

| Field | Value |
|---|---|
| Status | **Proposed** |
| Decided at | G2, T2.05 |
| Relates to | PRD section 4, `memory.md` D-004 |

---

## Context

The system must define exactly one primary compensation measure for the initial model. Mixing incomparable measures produces confident nonsense (PRD PB-4, R-DA-04). The measure must be canonical, unambiguous, and supported by the available sources.

**Current hypothesis:** `guaranteed_cash_annual` — fixed cash pay before tax, excluding variable pay, bonuses, equity and benefits.

Alternatives:
- `base_annual`: base salary only (may exclude guaranteed allowances)
- `target_cash_annual`: fixed + target bonus (requires bonus data)
- Total compensation (requires equity data; deferred to Phase 8)

## Options

| Measure | Definition | Advantage | Risk |
|---|---|---|---|
| `guaranteed_cash_annual` (H0) | Fixed committed cash, pre-tax, annual | Most consistently reported across India tech roles `[H]`; not distorted by variable pay targets | CTC convention varies by employer; component mapping needed (T2.05) |
| `base_annual` | Strict base pay | Internationally comparable | Many Indian employers bundle allowances into "base"; may undercount |
| `target_cash_annual` | Fixed + target variable | Closer to "real" cash if bonus is reliable | Bonus data often missing or unreliable; adds selection bias |
| `total_compensation` | All components | Most complete | Equity valuation is unsolved; deferred to Phase 8 |

## Decision

**Measure: `guaranteed_cash_annual` (normalized to nominal INR Lakhs Per Annum / LPA) — confirmed by the user on 2026-10-13 (Q-009, T0.02).**

Field mapping and component reconciliation occur at T2.05, and final sufficiency confirmation is validated at G2 (T2.11). If approved sources cannot reliably isolate guaranteed cash from bundled CTC, the field reconciliation policy is triggered before any modeling.

## Consequences

- The canonical `compensation_observation` schema fixes `measure` and `comp_type` enums.
- The PRD scope table is updated at T2.11.
- API responses always carry the measure name and definition.
- Incomparable measures are never summed without a written normalization policy.

## Evidence

| Claim | Source | Status |
|---|---|---|
| `guaranteed_cash_annual` is the most consistently reported measure in India tech | `[H]` | Unverified; check at T1.02, T2.05 |
| CTC bundles vary by employer | General knowledge | Unverified; document at T1.02 |

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
