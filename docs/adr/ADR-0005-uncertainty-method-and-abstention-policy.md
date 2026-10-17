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

**Drafted / In-Progress (T5.03).** Built in-house split conformal and CQR in `src/compintel/uncertainty/conformal.py` as Rung F. Evaluated on temporal calibration set (`calibrate` partition). In-house implementation is self-contained (<600 LoC, zero external heavy dependencies, zero import-linter boundary violations). Formally documented mathematical assumptions (marginal not individual coverage; exchangeability requirement). Final ratification pending support thresholds (T5.07) at Gate G5.

## Formal Specification of Rung F Conformal Calibration

### 1. Split Conformal (Point Prediction Baseline)
- Calibration set: $(X_i, Y_i)_{i=1}^n$ from the temporal `calibrate` partition.
- Non-conformity score: Absolute residual $R_i = |Y_i - \hat{f}(X_i)|$, where $\hat{f}(X)$ is the fitted Rung D point model (`CatBoostPointModel` or `LightGBMPointModel`).
- Conformal radius: $\hat{r} = R_{(k)}$ where $k = \lceil (n + 1)(1 - \alpha) \rceil$.
- Prediction interval: $\hat{C}(X) = [\max(0.50, \hat{f}(X) - \hat{r}), \hat{f}(X) + \hat{r}]$.

### 2. Conformalized Quantile Regression (CQR; Romano, Patterson, Candès 2019)
- Base model: Rung E quantile model (`CatBoostQuantileModel` or `LightGBMQuantileModel`) predicting conditional quantiles $\hat{q}_{\alpha_{\text{lo}}}(X)$ and $\hat{q}_{\alpha_{\text{hi}}}(X)$ (nominally $\alpha_{\text{lo}} = 0.10, \alpha_{\text{hi}} = 0.90$ for 80% coverage).
- Non-conformity score: Signed boundary violation:
  $$E_i = \max(\hat{q}_{\alpha_{\text{lo}}}(X_i) - Y_i, Y_i - \hat{q}_{\alpha_{\text{hi}}}(X_i))$$
- Conformal critical value: $\hat{q} = E_{(k)}$ where $k = \lceil (n + 1)(1 - \alpha) \rceil$.
- Adaptive prediction interval:
  $$\hat{C}(X) = [\max(0.50, \hat{q}_{\alpha_{\text{lo}}}(X) - \hat{q}), \hat{q}_{\alpha_{\text{hi}}}(X) + \hat{q}]$$
- Crossing and Monotonicity Repair (Rule R-UQ-05): If calibrated bounds cross ($\text{lo} > \text{mid}$ or $\text{mid} > \text{hi}$), monotonic rearrangement projection sorts values to guarantee $\text{P10} \le \text{P50} \le \text{P90}$.

### 3. Statutory Assumptions and Method Limitations (Rule R-UQ-03)
1. **Marginal, Not Conditional Coverage:** The finite-sample theoretical guarantee $P(Y_{n+1} \in \hat{C}(X_{n+1})) \ge 1 - \alpha$ is marginal (averaged over the population). Conformal calibration does NOT guarantee $(1 - \alpha)$ coverage conditionally for every specific individual, narrow employer cluster, or fine-grained experience slice.
2. **Exchangeability:** Requires that the calibration observations and test observations are exchangeable. In compensation intelligence, macroeconomic inflation, skill demand shifts, and wage drift violate exchangeability across time. Therefore, calibration sets MUST use recent temporal windows (`calibrate` partition) and be refreshed continuously.
3. **Finite-Sample Validity Floor:** Guaranteed validity requires $n_{\text{cal}} \ge \lceil (n_{\text{cal}} + 1)(1 - \alpha) \rceil$. For $\alpha = 0.20$ (80% coverage), $n_{\text{cal}} \ge 4$. If $n_{\text{cal}}$ is below this threshold, conservative maximum score fallback is applied and flagged.

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

**Drafted at T5.03; Pending Final Ratification at G5 (T5.09).** Rung F (Split Conformal and CQR) implemented in `src/compintel/uncertainty/conformal.py` with 100% CI compliance. Conformal guarantees are documented as marginal in code, test suites, and model documentation.

## Consequences

- Abstention is HTTP 200 `status: "abstained"` — a valid designed result, not an error (R-ER-04).
- Thresholds are versioned in `config/thresholds.yaml` and change only via a PR with justification.
- Conformal guarantees are documented as marginal in the model card and UI; individual-level coverage is never claimed (R-UQ-03).
- Abstention rates by group are monitored as a fairness metric (T5.07, T6.09).
- Rung F CQR adapts interval widths dynamically to local quantile spread, while Split Conformal provides fixed-radius symmetric intervals.

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
| 2026-10-18 | Drafted Rung F formal specification at T5.03: implemented CQR and Split Conformal in `src/compintel/uncertainty/conformal.py`, defined finite-sample equations, non-conformity scores, and Rule R-UQ-03 statutory assumptions. |
