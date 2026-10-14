# Data Card: ArthaIQ Governed Voluntary User Compensation Intake

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-INT-VOL-01` |
| **Document ID** | `docs/data-cards/SRC-INT-VOL-01.md` |
| **Short Name** | ArthaIQ Voluntary Intake |
| **Long Name** | ArthaIQ Governed Voluntary User Compensation Intake (Itemized Form & Verified Payslips) |
| **Provider** | ArthaIQ Platform / Voluntary Tech Worker Contributions |
| **Primary URL** | https://arthaiq.internal/intake |
| **Licence** | User Terms of Service & Explicit Consent (`PROPRIETARY-CONSENT-GRANT`) |
| **SQS / Tier** | **96.0** (Projected) / `TIER_1_GROUND_TRUTH` |
| **Ingestion Status** | `approved_for_design` |
| **Assigned Role** | Primary Ground Truth Training Data for PT1–PT6 (Phase 8 Production Design) |
| **Prohibited Routing** | Public unaggregated export; unanonymized data sharing |

---

## 1. Design Specification & Legal Framework

* **Methodological Mandate:** Pre-registered in Task T2.10, ADR-0008, and Scope Memo (`08-scope-memo.md`).
* **The Ground Truth Imperative:** Because all audited external Kaggle datasets violate ToS scraping rules (`R-DA-01`) or fail target measure unbundling (`R-MD-07`), ArthaIQ's long-term production ground truth for granular compensation is established via our own governed voluntary intake platform.
* **Privacy & Legal Protections:**
  1. Full compliance with the Digital Personal Data Protection Act, 2023 (DPDPA 2023) and GDPR.
  2. Cryptographic one-way salary hash: $\text{HMAC-SHA256}(\text{salt}, \text{components})$ prevents double submissions without storing personal identities.
  3. Strict client-side redaction of employee name, bank account numbers, PAN, and employee IDs from uploaded payslips.
  4. Enforced $k$-anonymity with $k \ge 5$ across all cohort disclosures (`R-DA-10`).
  5. Cleartext PII is **NEVER** stored in any database table (`R-DA-07`).

---

## 2. Canonical Target Accounting Identity

Unlike ambiguous scraped CTC strings, the voluntary intake form captures itemized line items directly:

$$\text{CTC} = \underbrace{\text{Basic} + \text{HRA} + \text{Special Allowance}}_{\mathbf{guaranteed\_cash\_annual}\ (\text{Target PT1})} + \text{PF (Employer)} + \text{Gratuity} + \text{Annual Performance Bonus} + \text{Equity Annual Vest}$$

Every user submission is parsed directly into canonical schema attributes:
* `guaranteed_cash_annual` (Primary target)
* `variable_pay_annual`
* `equity_annual_vest_nominal`
* `benefits_annual`
* `currency`: Nominal INR
* `period`: Annualized (`INR LPA`)

---

## 3. Projected Sampling Sufficiency & Quality Score

* **Pre-Registered SQS:** **96.0 / 100** (All 10 dimensions scored 5/5 except sampling frame at 3/5 due to self-selection).
* **Bias Mitigation:** Raw voluntary submissions are re-weighted via post-stratification against the MOSPI PLFS population tech benchmarks (`SRC-IND-OFF-01`) and BSE/NSE statutory corporate medians (`SRC-SUP-CORP-01`), correcting for self-selection bias toward high-earning Tier-1 product engineers.

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias Profile & Volunteer Participation Skew
1. **Voluntary Participation Skew:** Contributions to voluntary pay intelligence platforms inherently skew toward active job-seekers, professionals anticipating salary renegotiations, and ambitious mid-to-senior software engineers employed at well-funded technology startups, Tier-1 product MNCs, and elite GCCs.
2. **Geographical Concentration:** Heavy volunteer concentration in major Indian tech hubs (Bengaluru, Hyderabad, Pune, MMR, NCR) with lower initial organic representation from Tier-2 tech centers (Kochi, Coimbatore, Indore, Jaipur).
3. **Experience Truncation:** Entry-level campus hires and very senior executives (VP/SVP/C-suite) participate at lower rates than engineers with 3 to 10 years of experience.

### 4.2 Reporting & Measurement Bias Profile
1. **Itemized Accounting Elimination of Measurement Error:** Unlike crowdsourced portals that capture a single unverified CTC string, ArthaIQ eliminates measurement bias by requiring explicit line-item decomposition (Basic + HRA + Special Allowance vs PF vs Gratuity vs Bonus vs RSUs).
2. **Verification Levels:** Submissions are stratified into `Self-Reported Unverified` and `Payslip-Verified` tiers. Verified payslips eliminate prestige exaggeration and rounding heaping.
3. **Zero Reverse-Tax Guessing:** Post-tax in-hand pay is recorded as an isolated descriptive field and never back-calculated to gross cash.

### 4.3 Comparison with Official Population Benchmarks
* **Comparison with MOSPI PLFS Benchmark (`SRC-IND-OFF-01`):** Raw, unadjusted voluntary tech submissions typically report median guaranteed cash of **₹16.00–₹22.00 LPA**, representing a **+78% to +144% upward divergence** over the national urban software developer median of ₹9.00 LPA. This reflects the product/MNC skew of digital voluntary contributors relative to broad-based IT services personnel.
* **Comparison with Corporate IT Services Benchmark (`SRC-SUP-CORP-01`):** Corporate filings demonstrate that large IT services firm median remuneration is ₹6.00–₹9.00 LPA. Voluntary contributors from Tier-3 services firms average ₹7.50 LPA, aligning closely with corporate disclosures, whereas contributors from Tier-1 product firms average ₹28.00 LPA.
* **Mitigation & Pipeline Routing Rule in ArthaIQ:**
  * In Phase 4/5 modeling, voluntary intake records are calibrated via **post-stratification cell weights** pegged to the PLFS occupation-location marginals and BSE/NSE enterprise priors.
  * Invariant: Raw volunteer sample density alone cannot justify a narrow prediction interval (`FR-19`, `D-010`). Abstention triggers if population-representative support fails pre-registered thresholds.
