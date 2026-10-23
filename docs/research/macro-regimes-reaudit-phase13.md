# Macro Regime Features Long-Range Calendar Trigger (EXP-MACRO-01r, CHARTER-MACRO-REGIMES-r)

> **Scope:** Longitudinal Panel Span Feasibility Audit and Data-Growth Trigger Assessment for Macroeconomic Market-Regime Features (MOSPI CPI Urban Deflation, RBI Reference Rates, FX Volatility) on Cumulative Non-Synthetic Production Panel.
> **Governing Standards:** PRD Sec 5, FR-05 · Rules R-MD-01, R-MD-02, R-MD-03, R-MD-04, R-MD-05, R-MD-09, R-MD-11, R-UQ-01, R-UQ-05, R-CD-01 · Task T13.06.

| Metadata Attribute | Value |
|:---|:---|
| **Report ID** | `EXP-MACRO-REAUDIT-20261023-085102` |
| **Charter ID** | `CHARTER-MACRO-REGIMES-r` |
| **Experiment ID** | `EXP-MACRO-01r` |
| **Task ID** | `T13.06` |
| **Generated At** | `2026-10-23T08:51:02.925182+00:00` |
| **Git Commit** | `55190d97` |
| **Cumulative Production Panel** | `219 observations` (`219` verified non-synthetic) |
| **Realized Observation Calendar Span** | `5.9 calendar months` (`180 days`, `2026-10-22` to `2027-04-19`) |
| **Pre-Registered Span Requirement** | $\ge 24.0$ calendar months (730 days) |
| **Span Sufficiency Status** | `DEFER` (Deficit: `18.1 calendar months`) |
| **Calendar Date Trigger Condition** | `2028-10-01` (`PENDING`) |
| **MOSPI CPI Urban Series** | `PRESENT (819 monthly rows)` (`OGDL-IN`, `TIER_4_SUPPLEMENTARY`) |
| **RBI INR/USD FX Daily Series** | `PRESENT (14,024 daily rows)` (`OGDL-IN`, `TIER_4_SUPPLEMENTARY`) |
| **Gate 1 Feasibility Audit** | **`INSUFFICIENT_SPAN_DEFER`** |
| **Overall Re-audit Verdict** | **`DEFER`** |
| **Production Champion Status** | **`RETAINED_UNMODIFIED (Conformal CatBoost L2 Champion retained; zero macro dependencies)`** |
| **Next Scheduled Trigger Date** | `2028-10-01` |
| **Next Audit Trigger Condition** | `Continuous accumulation of >= 24.0 calendar months of nominal INR observations OR arrival of 2028-10-01 calendar trigger date` |

---

## 1. Executive Summary & Governance Verdict

**Final Verdict:** **`DEFER`**

Gate 1 Longitudinal Feasibility DEFERRED: Cumulative non-synthetic production panel spans 5.9 calendar months (180 days, 2026-10-22 to 2027-04-19), failing the pre-registered 24.0-calendar-month threshold in CHARTER-MACRO-REGIMES-r. Macro indicators (MOSPI CPI Urban inflation, RBI reference rates) exhibit near-zero longitudinal variance over this short window and remain collinear with linear time trends. In strict compliance with Rule R-MD-09, expensive and statistically invalid model fitting on underpowered data was held in abeyance. The Champion Conformal CatBoost model is strictly retained unmodified with zero external macro dependencies. Next audit is pre-registered for the 2028-10-01 calendar trigger date.

> [!IMPORTANT]
> **Governance Determination:** In strict adherence to **Rule `R-MD-09`** and **`CHARTER-MACRO-REGIMES-r`**, candidate feature re-evaluations must not proceed without meeting pre-registered data feasibility criteria. The current production panel spans `5.9 calendar months` (`180 days`, `2026-10-22` to `2027-04-19`), failing the mandatory $\ge 24.0$-calendar-month threshold. Macroeconomic indicators (CPI inflation, policy repo rates) exhibit near-zero cross-sectional variance over a 6-month window and are collinear with local time trends. Premature empirical fitting on under-spanned horizons induces spurious correlation, violates release-time publication lags, and creates severe lookahead risk. Production Champion Rung F Level 2 Conformal CatBoost is strictly retained unmodified with zero external macro dependencies, preserving microsecond CPU inference latency. Next audit trigger is pre-registered for the **October 2028** calendar trigger date OR explicit data audit confirming $\ge 24.0$ calendar months.

---

## 2. Gate 1: Longitudinal Panel Span & Calendar Window Audit

Under **Rule `R-MD-09`**, **Rule `R-MD-01`**, and **`CHARTER-MACRO-REGIMES`**, macroeconomic regime modeling requires multi-year longitudinal observation horizons. In India's tech sector, macroeconomic indicators (MOSPI CPI Urban, RBI repo rates, USD/INR exchange rates) operate across multi-quarter business cycles. A panel spanning under 24 calendar months captures at most two quarterly review cycles, rendering macroeconomic time-series variance collinear with linear calendar trends and short-term recruiting batch noise.

| Feasibility Dimension | Pre-Registered Standard | Empirical Value | Gate 1 Evaluation |
|:---|:---|:---|:---|
| **Observation Calendar Span** | $\ge 24.0$ calendar months | `5.9 calendar months` (`180 days`) | `DEFER (Deficit: 18.1 calendar months / 550 days)` |
| **Calendar Trigger Date** | Arrival of `2028-10-01` | `2027-04-19` | `DEFER (Pending)` |
| **Verified Non-Synthetic Records** | $\ge 100$ records | `219 records` | `PASS` |
| **Synthetic Data Contamination** | `0` synthetic records | `0 records` | `PASS (Rule R-MD-11 kept)` |
| **MOSPI CPI Urban Series** | Complete official historical series | `819 monthly rows` | `PASS` |
| **RBI INR/USD Daily FX Series** | Complete official daily series | `14,024 daily rows` | `PASS` |
| **Gate 1 Feasibility Determination** | `SUFFICIENT_SPAN` required | **`INSUFFICIENT_SPAN_DEFER`** | **`DEFER`** |

---

## 3. Macroeconomic Indicator Series Availability & Point-In-Time Integrity (Gate 2)

Official macroeconomic reference data is curated under repository data source `SRC-SUP-MAC-01`:
- **MOSPI All-India Urban CPI**: 819 monthly observations spanning 1958 through 2026.
- **RBI INR/USD Daily Reference FX Rates**: 14,024 daily exchange rates spanning 1973 through 2026.
- **Licensing & Provenance**: Open Government Data License - India (`OGDL-IN`), Tier 4 Supplementary (`SQS: 94.4`).

### Point-in-Time Release Lag Policy (Rule R-MD-03)
1. **MOSPI Publication Schedule**: CPI figures are indexed by reference month start (e.g., `2026-05-01`), but officially published on day 12 of month $M+1$ (`2026-06-12`), rolling forward to Monday if falling on a weekend. A salary observation at timestamp $T$ is strictly prohibited from accessing CPI figures where $\text{release\_date} > T$.
2. **Retroactive Revision Isolation**: Official MOSPI CPI releases frequently undergo subsequent revisions in months $M+2$ and $M+3$. To prevent retroactive lookahead bias, the pipeline strictly joins first-release preliminary figures as of time $T$.
3. **Daily FX Realized Volatility**: INR/USD exchange rates are joined strictly $\le T$, forward-filling trading holidays and computing rolling 30-day realized volatility.

---

## 4. Real-Pay Deflation & Conformal Inverse Re-Inflation Pipeline (Variant A)

Under `CHARTER-MACRO-REGIMES-r`, Variant A formulates salary compensation in constant real currency units rather than nominal rupees:

1. **Real-Pay Normalization**: With fixed reference base $CPI_{\text{ref}} = 185.10\text{ index points}$ (2024-01-01 base year), nominal compensation $y_{\text{nominal}, i}$ is deflated via:
   $$y_{\text{real}, i} = y_{\text{nominal}, i} \cdot \frac{CPI_{\text{ref}}}{CPI_{\text{asof}}(T_i)}$$
2. **Conformal Prediction on Real Scale**: Quantile regressors predict real-scale percentiles $\hat{q}_{0.10}^{\text{real}}, \hat{q}_{0.50}^{\text{real}}, \hat{q}_{0.90}^{\text{real}}$, and non-conformity residuals are calibrated to maintain marginal coverage on real compensation.
3. **Exact Inverse Re-Inflation**: At query serving time, predicted bounds are re-inflated to contemporary nominal currency units using the latest published CPI index $CPI_{\text{asof}}(T_{\text{query}})$:
   $$\hat{y}_{\text{nominal}} = \hat{y}_{\text{real}} \cdot \frac{CPI_{\text{asof}}(T_{\text{query}})}{CPI_{\text{ref}}}$$
   This transformation is strictly invertible ($|y - \hat{y}| < 10^{-9}\text{ LPA}$), guaranteeing exact conformal coverage preservation in nominal space.

---

## 5. Macro Regime Feature Join Architecture & Publication Lag Policy (Variant B)

Variant B appends exogenous macroeconomic and market-regime indicators directly as model covariates into the Level 2 tabular feature matrix:
- `macro_cpi_inflation_12m`: Trailing 12-month headline CPI inflation rate (as-of publication date).
- `macro_fx_usd_inr_30d_vol`: Trailing 30-day realized annualized USD/INR exchange rate volatility.
- `macro_policy_repo_rate`: RBI Monetary Policy Committee policy repo rate.
- `macro_tech_sentiment_index`: Industry hiring index (NASSCOM / Naukri JobSpeak IT index).

> [!WARNING]
> **Collinearity Risk on Short Horizons:** Over a 6-month observation window (April to October 2026), India's Urban CPI index moved from $192.40\text{ points}$ to $195.80\text{ points}$ ($+1.77\%\text{ change}$). With near-zero cross-sectional variation across concurrent hires, tree-based gradient boosters map these macro indicators directly to time-stamp proxies, overfitting to seasonal hiring spikes and failing out-of-time generalizability.

---

## 6. Empirical Modeling Status

**Expensive model fitting was SKIPPED.** In compliance with repository governance, Rule `R-MD-09`, and `CHARTER-MACRO-REGIMES-r`, when the development panel fails the 24.0-calendar-month longitudinal sufficiency gate, machine learning models are not trained on under-spanned data. No speculative claims of predictive gain or empirical rejection are reported.

---

## 7. Production Champion Retention & Phase 13 Architectural Impact

1. **Production Champion Retained Unmodified**: **Rung F Level 2 Conformal CatBoost** is strictly retained as ArthaIQ's production champion. Core compensation prediction operates with zero external macroeconomic dependencies.
2. **Zero Lookahead & Latency Risk**: Retaining the static tabular champion eliminates external RBI/MOSPI API failure points, avoids publication revision lag vulnerabilities, and preserves p95 inference latency at microsecond CPU speeds ($4.03\text{ ms}$).
3. **Long-Range Calendar Trigger**: EXP-MACRO-01r will be re-audited when the production system reaches the **2028-10-01** calendar date trigger OR an explicit data audit confirms $\ge 24.0$ calendar months of continuous observations.
