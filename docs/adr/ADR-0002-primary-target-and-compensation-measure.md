# ADR-0002: Primary Target and Compensation Measure

| Field | Value |
|---|---|
| Status | **Accepted / Ratified at Gate G1** (Operational field reconciliation at Task T2.05) |
| Decided at | Phase 1 Gate G1 (2026-10-13) |
| Relates to | PRD section 4, `memory.md` D-004, `docs/research/01-targets.md`, `docs/research/02-comp-definitions.md`, `docs/research/08-scope-memo.md` |

---

## Context

ArthaIQ must define exactly one canonical primary compensation measure for its core prediction targets (PT1, PT2, and PT6). Mixing incomparable compensation measures (such as Total Cost to Company, gross monthly cash, hourly wage, advertised job vacancy budgets, and post-tax in-hand pay) introduces fatal measurement error and violates project rules `R-DA-04` and `R-MD-07`. The primary measure must represent contractually committed, realized employee cash compensation and be mathematically isolable from statutory employer overhead and speculative equity.

## Evaluated Options

| Measure | Definition | Advantage | Risk / Disadvantage | Disposition |
|---|---|---|---|---|
| **Option 1: `guaranteed_cash_annual`** | Fixed contractual cash before tax (`Basic` + `HRA` + `Special Allowance` + recurring cash allowances). | Contractually committed; zero equity speculation; reliable budgeting metric for candidates. | Requires unbundling headline CTC; unreconciled records must be quarantined (`R-MD-07`). | **ADOPTED AS CANONICAL MEASURE** |
| **Option 2: `base_annual`** | Strict basic salary alone. | Standard international definition; directly reported in US BLS. | Indian employers heavily depress basic salary (often 30–40% of CTC) to minimize PF liability, channeling cash into HRA and allowances; would severely understate actual fixed cash. | **REJECTED** |
| **Option 3: `ctc_annual` (Total Cost to Company)** | Headline CTC inclusive of employer PF, gratuity, performance bonus, and paper equity. | Widely cited in Indian offer letters and campus placements. | Misleading; includes non-cash overhead (employer PF, gratuity), variable bonuses that may not pay out, and unvested 4-year equity. Fails comparability across employers. | **REJECTED AS TARGET** (Quarantined or unbundled only) |
| **Option 4: `total_comp_annual`** | Realized cash plus annual vesting value of equity and realized bonuses. | Most comprehensive total reward measure. | Illiquid private startup equity is unpriced; introduces wild valuation volatility. | **DEFERRED TO PHASE 8** (Isolated target branch) |

## Decision

1. **Canonical Primary Target Measure:** **`guaranteed_cash_annual`**, defined as the annual nominal cash compensation that an employer is contractually obligated to pay an employee before individual income taxes, conditional solely on standard full-time employment and independent of personal performance metrics, company EBITDA gates, or vesting schedules.
2. **Accounting Unbundling Equation:** Enforced by rule `R-MD-07` and defined in `docs/research/02-comp-definitions.md`:
   $$\text{guaranteed\_cash\_annual} = \text{basic} + \text{hra} + \text{special\_allowance} + \sum \text{recurring\_cash\_allowances}$$
   $$\text{guaranteed\_cash\_annual} = \text{CTC} - (\text{statutory\_employer\_pf} + \text{gratuity\_provision} + \text{target\_variable\_bonus} + \text{annualized\_equity\_grant} + \text{perks\_insurance})$$
3. **The Anti-Heuristic Rule (`R-MD-07`):** Stated CTC without itemized line items must **never** be converted to guaranteed cash via uniform percentages (e.g. `0.80 * CTC`). Unreconciled observations are strictly quarantined from PT1 training tables.
4. **Unit and Horizon:** Nominal **INR Lakhs Per Annum (LPA)**, normalized to annual pay, measured at prediction timestamp $t_0$ and temporally deflated via RBI CPI-Urban (`SRC-SUP-MAC-01`).

## Consequences

- The canonical Pydantic/pandera data contracts (`src/compintel/schema/`) enforce `measure_id: "guaranteed_cash_annual"`.
- Ingestion pipelines must validate itemized line items or quarantine observations into a segregated table (`data/staged/quarantine/`).
- User interfaces (`design.md`) prominently state: *"Amounts represent guaranteed annual pre-tax cash compensation (Basic + HRA + Special Allowance), excluding variable bonuses, employer PF, gratuity, and equity grants."*

## Evidence & Verification

| Claim | Source / Document | Status |
|---|---|---|
| Basic salary in India is artificially depressed (30-50% of CTC) for PF optimization | Employees' Provident Funds Act 1952; `02-comp-definitions.md` | **VERIFIED** |
| Employer PF (12%) and Gratuity (4.81%) are statutory costs, not take-home pay | Payment of Gratuity Act 1972; `02-comp-definitions.md` | **VERIFIED** |
| Kaggle datasets bundle CTC and variable bonuses | `docs/research/kaggle-dataset-audit-v0.1.md` | **VERIFIED** |
| Test suite verifies unbundling and quarantine logic (`T1.02-TEST-01..08`) | `docs/research/02-comp-definitions.md` Section 5 | **VERIFIED** |

## Change Log

| Date | Author | Change |
|---|---|---|
| 2026-10-13 | AI / Human | Stub created at T0.04 |
| 2026-10-13 | AI / Human | Updated to Ratified at Gate G1 with canonical unbundling equation and R-MD-07 anti-heuristic rule |
