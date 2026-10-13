# ADR-0005: Uncertainty Method and Abstention Policy

| Field | Value |
|---|---|
| Status | **Proposed** |
| Decided at | G5 (T5.07, T5.09) |
| Relates to | `architecture.md` section 10.3, `rules.md` R-UQ-01 to R-UQ-06 |

---

## Context

The product must output a range (P10, P50, P90) with a stated coverage intent, and must abstain when support criteria fail. Two decisions are needed: (1) the calibration method for the interval, and (2) the support checks and thresholds that trigger abstention.

## Candidate uncertainty methods

| Method | How it works | Advantage | Risk |
|---|---|---|---|
| Split conformal (in-house) | Holdout residuals calibrate a scalar correction | Finite-sample marginal coverage guarantee; simple | Coverage is marginal, not conditional; drift breaks exchangeability |
| CQR (conformalized quantile regression) | Calibrates the quantile model's residuals | Conditionally adaptive widths | Same exchangeability caveat |
| MAPIE | Library wrapper for split conformal and CQR `[U: confirm maintenance]` | Reduces boilerplate | Depends on library maintenance; API may change |
| Residual-quantile intervals (simpler alternative) | Use empirical quantiles of residuals | No exchangeability assumption | Conservative; not adaptive |

**Proposed:** build in-house split conformal and CQR as rung F. Evaluate MAPIE as a shortcut only if in-house is not yet stable. Document assumptions (marginal not individual; exchangeability required).

## Support checks (S1–S5)

| Check | Trigger | Threshold |
|---|---|---|
| S1 Effective cohort size | Deduplicated quality-weighted count | `n_min` [TBD: T5.07] |
| S2 Feature-space support | Categorical level seen ≥ m times; numeric inside training range | `m`, distance threshold [TBD: T5.07] |
| S3 Recency | Median observation age | `a_max` [TBD: T5.07] |
| S4 Source quality | Quality-weighted score | `q_min` [TBD: T5.07] |
| S5 Interval usefulness | Calibrated width vs. naive cohort interval | `w_max` [TBD: T5.07] |

Thresholds live in `config/thresholds.yaml` and are fixed at G5 before they are published.

## Evidence grades

| Grade | Condition |
|---|---|
| A | All support criteria met with margin, recent data, interval narrow relative to the cohort baseline |
| B | Criteria met, with one of recency, source quality or width borderline |
| C | Criteria met only narrowly; shown with explicit caution |
| Abstained | One or more criteria failed below the abstention floor |

## Decision

**Pending.** Finalized at G5 (T5.09) once rung F is evaluated (T5.03) and the abstention policy is audited by group (T5.07).

## Consequences

- Abstention is HTTP 200 `status: "abstained"` — a valid designed result, not an error (R-ER-04).
- Thresholds are versioned in `config/thresholds.yaml` and change only via a PR with justification.
- Conformal guarantees are documented as marginal in the model card and UI; individual-level coverage is never claimed.
- Abstention rates by group are monitored as a fairness metric (T5.07, T6.09).

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
