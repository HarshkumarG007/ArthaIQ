# Data Card: ArthaIQ Governed B2B Enterprise Syndication Consortium

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-B2B-01` |
| **Document ID** | `docs/data-cards/SRC-B2B-01.md` |
| **Short Name** | B2B Syndication Consortium |
| **Long Name** | ArthaIQ Governed B2B Enterprise HRIS & Payroll Syndication Consortium |
| **Provider** | Enterprise Employer Consortium / HRIS API Tranches |
| **Primary URL** | https://arthaiq.internal/b2b-syndication |
| **Licence** | Enterprise Bilateral Consortium Data Sharing Agreement (`PROPRIETARY-B2B-CONSORTIUM-GRANT`) |
| **SQS / Tier** | **98.0** / `TIER_1_GROUND_TRUTH` |
| **Ingestion Status** | `approved_for_design` |
| **Assigned Role** | Primary Enterprise Ground Truth for PT1–PT6, Talent Flow Mobility Graphs, and Longitudinal Tenure Trajectories |
| **Prohibited Routing** | Public unaggregated export; unanonymized data sharing; deanonymization reverse lookups |

---

## 1. Design Specification & Legal Framework

* **Methodological Mandate:** Authored under Phase 14 Architecture, ADR-0008, PRD Section 5, FR-05, and Rules `R-DA-01`, `R-DA-02`, `R-DA-10`.
* **The Ground Truth Imperative:** Enterprise HRIS payroll tranches supply verified, itemized compensation components with zero self-reporting ambiguity or voluntary recall errors.
* **Privacy & Legal Protections:**
  1. Full compliance with the Digital Personal Data Protection Act, 2023 (DPDPA 2023) and Competition Commission of India (CCI) anti-collusion safe harbor standards.
  2. Cryptographic tenant-salted one-way pseudonym tokenization: $\text{HMAC-SHA256}(\text{tenant\_salt}, \text{raw\_emp\_id})$ strictly prevents cross-tenant linkage without storing cleartext identifiers.
  3. Strict exclusion of cleartext PII: names, personal emails, PAN, Aadhaar, phone numbers, and bank account details are permanently blocked and rejected at connector intake (`R-DA-07`).
  4. Enforced $k$-anonymity floor with $k_{\min} \ge 5$ across all cohort disclosures and employer clusters (`R-DA-10`). Any employer cluster with $< 5$ observations collapses to `EMP-ANONYMOUS`.
  5. Wage coarsening to nearest ₹50,000 steps to prevent exact decimal salary fingerprinting.
  6. Temporal quarterly date coarsening (`YYYY-Qn`) with mandatory 3-month historical lag.

---

## 2. Canonical Target Accounting Identity

The B2B enterprise syndication schema captures granular accounting line items verified by payroll systems:

$$\text{CTC} = \underbrace{\text{Basic} + \text{HRA} + \text{Fixed Allowances}}_{\mathbf{guaranteed\_cash\_annual}\ (\text{Target PT1})} + \text{PF (Employer)} + \text{Gratuity} + \text{Variable Performance Bonus} + \text{Annualized Equity Grant}$$

Every ingested payroll record enforces strict accounting consistency:
$$|\text{guaranteed\_cash\_annual} - (\text{basic\_salary\_annual} + \text{fixed\_allowances\_annual})| \le 100.0\text{ INR}$$

Canonical schema attributes:
* `guaranteed_cash_annual` (Primary target)
* `basic_salary_annual`
* `fixed_allowances_annual`
* `variable_bonus_annual`
* `equity_annualized_grant`
* `statutory_overhead_annual`
* `ctc_annual`
* `currency`: Nominal INR
* `period`: Annualized (`INR LPA`)

---

## 3. Sampling Sufficiency & Quality Score

* **Pre-Registered SQS:** **98.0 / 100** (Highest-tier ground truth with audited enterprise payroll verification).
* **Bias Mitigation:** Multi-employer pooling across enterprise tiers (Tier-1 global product MNCs, domestic tech leaders, high-growth startups, GCCs) balanced against MOSPI PLFS population benchmarks (`SRC-IND-OFF-01`).
* **CCI Anti-Collusion Safe Harbor:** Enforces multi-employer cell pooling ($\ge 5$ distinct employers per reporting cell) with non-dominance constraint (no single tenant contributes $> 35.0\%$ of records in any cohort cell).

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias Profile
1. **Consortium Member Skew:** Initial syndication tranches originate predominantly from mature Tier-1 technology product firms, established GCCs, and high-growth venture-backed enterprises with formal HRIS infrastructure (e.g. Workday, Darwinbox).
2. **Early-Stage Truncation:** Early-stage pre-seed startups using informal or unitemized payroll may be under-represented, balanced via primary voluntary intake (`SRC-INT-VOL-01`).
3. **Regional Distribution:** Dense coverage across major tech corridors (Bengaluru, Hyderabad, Pune, NCR, MMR) with growing coverage in emerging tech hubs.

### 4.2 Reporting and Measurement Fidelity
1. **Zero Recall Error:** Compensation amounts are extracted directly from payroll systems with 0 recall error.
2. **Accounting Identity Verification:** Every ingested record verifies that guaranteed cash equals basic plus allowances within ₹100 tolerance.


