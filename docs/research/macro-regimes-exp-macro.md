# Macroeconomic & Market-Regime Features Experiment Memo (T7.05, EXP-MACRO-01)

> **Document ID:** `docs/research/macro-regimes-exp-macro.md`  
> **Report ID:** `EXP-MACRO-20261019-060926`  
> **Generated At:** `2026-10-19T06:09:26.712355+00:00`  
> **Git Commit:** `96b46594`  
> **Charter:** `experiments/configs/charters/charter_macro_regimes.yaml` (`CHARTER-MACRO-REGIMES`)  
> **Overall Decision Verdict:** **`DEFER`**  

---

## 1. Executive Summary

Feasibility Gate 1 DEFERRAL: Eligible development observation panel spans 5 days (0.2 months), failing the pre-registered 24.0-month longitudinal threshold. Macro indicators (CPI inflation, FX rate volatility) exhibit negligible cross-sectional variance over this window and are collinear with time trends. In accordance with repository governance protocol and user instruction, expensive model fitting was skipped. The Rung F L2 Conformal CatBoost production champion remains strictly retained.

---

## 2. Gate 1 Feasibility & Longitudinal Sufficiency Audit

Under **Rule `R-MD-09`** and **`CHARTER-MACRO-REGIMES`**, macroeconomic feature
evaluation requires a multi-year observation panel (minimum 24 months) to separate
secular macro index variation from high-frequency noise or collinear time trends.
Evaluating macro regressors on short panels creates false identification and overfits
to batch effects.

| Audit Field | Audit Result | Requirement / Governance Standard |
| :--- | :--- | :--- |
| **Feasibility Status** | **`INSUFFICIENT_SPAN`** | `FEASIBLE` required to proceed |
| **Observation Date Span** | `5` days (`0.2` months) | $\ge 24.0$ months ($730$ days) |
| **Observation Range** | `2024-06-15` to `2024-06-20` | Multi-year longitudinal coverage |
| **Eligible Records** | `3` non-synthetic rows | Real canonical data (Rule `R-MD-11`) |
| **Is Synthetic Fixture** | `False` | Must be `False` for production validity |
| **MOSPI CPI Urban Series** | `819` rows present | `SRC-SUP-MAC-01` (`OGDL-IN` approved) |
| **RBI INR/USD FX Series** | `14,024` rows present | `SRC-SUP-MAC-01` (`OGDL-IN` approved) |
| **Data Provenance Tier** | `TIER_4_SUPPLEMENTARY` | Tier 4 Supplementary (`SQS: 94.4`) |

> **Audit Diagnostic:** Observation panel spans 5 days (0.2 months), failing the pre-registered 24-month sufficiency threshold in CHARTER-MACRO-REGIMES. Macro indicators exhibit near-zero longitudinal variance over this horizon and are collinear with time trends. Preregistered DEFER enforced.

---

## 3. Gate 2 Point-in-Time Publication Lag & Leakage Prevention

1. **MOSPI CPI Release Calendar**: CPI figures are indexed by reference month start
   (e.g. `2024-05-01`), but published strictly on day 12 of month $M+1$ (`2024-06-12`),
   rolling forward to Monday if falling on a weekend. Salary observations at date $T$
   can only join CPI records where $\text{release\_date} \le T$.
2. **Real-Pay Inversion**: Variant A uses fixed reference $CPI_{\mathrm{ref}} = 185.1$ (2024-01-01 base):
   $$y_{\mathrm{real}, i} = y_{\mathrm{nominal}, i} \cdot \frac{CPI_{\mathrm{ref}}}{CPI_{\mathrm{asof}}(T_i)}$$
   Re-inflation at query time inverts this transformation exactly ($|y - \hat{y}| < 10^{-9}$), and conformal
   calibration is strictly executed in the nominal target space to guarantee product-level coverage.
3. **FX Lookbacks**: INR/USD daily exchange rates are queried strictly $\le T$,
   forward-filling trading holidays and computing trailing 30-day realized volatility.

---

## 4. Modeling Execution Status

**Expensive model fitting was SKIPPED.** In compliance with repository governance and user instructions,
when the observation panel fails the 24-month longitudinal sufficiency gate, models are not fit on
underpowered data. No claims of predictive gain or empirical rejection are reported.

---

## 5. Governance & Production Impact

1. **Production Champion Retention**: The **Rung F Conformal CatBoost** Level 2 model is strictly retained
   as the production champion. Macro features are neither deployed nor included in serving pipelines.
2. **Preregistered Outcome**: **`DEFER`** under `CHARTER-MACRO-REGIMES`.
3. **Trigger for Re-evaluation**: Macro features will be re-audited only when a multi-year panel spanning
   $\ge 24$ months of longitudinal salary observations is assembled.
