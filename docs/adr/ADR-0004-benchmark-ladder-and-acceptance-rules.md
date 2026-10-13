# ADR-0004: Benchmark Ladder and Acceptance Rules

| Field | Value |
|---|---|
| Status | **Proposed** |
| Decided at | G4 (T4.03, T4.09) |
| Relates to | `architecture.md` section 10.1, `rules.md` R-MD-01 |

---

## Context

The benchmark ladder defines the order in which models are evaluated and the rule by which a more complex model replaces a simpler one. The ladder must be climbed in order; no rung is skipped (R-MD-01).

## Proposed ladder

| Rung | Model | Purpose |
|---|---|---|
| A | Empirical conditional quantiles with hierarchical backoff | The baseline every other model must beat |
| B | Regularized linear or GLM on log pay, with interactions; linear quantile regression | Transparent, strong in small data |
| C | Hierarchical partial pooling (empirical Bayes first) | Sparse-cell estimation |
| D | LightGBM and CatBoost point models on log pay | Non-linear structure |
| E | Quantile heads for P10, P50, P90 with crossing repair | Distribution output |
| F | Conformal calibration on a temporal calibration set | Interval calibration |
| Advanced | Embeddings, text, employer graphs, survival models | Only after G6 and an experiment charter |

## Selection rule (R-MD-01)

A rung replaces the next simpler one only if:

1. The improvement on pre-registered metrics has a bootstrap 95% CI **excluding zero**.
2. The improvement **exceeds the pre-registered minimum effect size**.
3. Both conditions hold on **grouped-temporal validation** (not random splits).

Otherwise the simpler model stays champion.

## Pre-registration requirement

Before any final-test run (T4.03, T5.08):

- Metrics: pinball loss at q=0.1, 0.5, 0.9; MAE; median absolute error; coverage; width; calibration error; crossing rate.
- Minimum effect sizes: TBD at T4.03.
- Split specification: temporal + grouped (person, employer, posting, source).
- `make final-eval` lock: prevents re-running against the test set.

## Decision

**Pending.** Finalized at G4 once pre-registration is committed (T4.03) and baselines are reviewed (T4.09).

## Consequences

- Every model PR includes the pre-registration reference and the measured metrics with CIs.
- Rungs D and E compete; neither is predetermined champion.
- SHAP is deferred to Phase 7 (not required for model acceptance).

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
