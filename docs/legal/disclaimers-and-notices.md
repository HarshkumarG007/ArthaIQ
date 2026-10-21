# ArthaIQ Statutory Disclaimers and In-Product Copy Register

| Field | Value |
|---|---|
| Document Version | 1.0.0 |
| Effective Date | 2026-10-21 |
| Status | **Active (Public Beta)** |
| Relates to | PRD FR-18, `design.md` Section 8, ADR-0005, ADR-0008, Rules `R-UI-05`, `R-MD-13`, `R-UQ-07`, `R-DA-10` |

---

## 1. Overview and Purpose

This document serves as the **Single Source of Truth (SSOT)** for all statutory legal notices, user disclosures, consent statements, and disclaimers displayed within the ArthaIQ web application and emitted by API endpoints.

To maintain strict regulatory compliance under India's Digital Personal Data Protection Act, 2023 (DPDPA) and consumer protection principles:
1. Every in-product disclaimer is cataloged with its exact string literal, placement rule, and statutory justification.
2. Code components in `apps/web/` must synchronize verbatim with this register.
3. Automated integration and unit tests enforce string equivalence in CI to prevent accidental copy regressions.

---

## 2. In-Product Legal Copy Catalog

### 2.1 Primary Decision-Support Disclaimer

- **Component:** `apps/web/src/components/DisclaimerLine.tsx` (`data-testid="disclaimer-line"`)
- **API Field:** `disclaimer_id: "decision_support_v1"`
- **Display Location:** Rendered directly below the primary estimate display and evidence breakdown on both `EstimateScreen` and `RefinementAndCompare`.
- **Visibility Requirement:** Always visible; never collapsed, tucked behind an accordion, or relegated to an external footer link (PRD FR-18, `design.md` Section 8).
- **Exact Registered Copy:**
  ```text
  This range is an estimate from data of varying quality. It is not an offer, appraisal or guarantee.
  ```

---

### 2.2 Compare-Only Current Pay Quarantine Notice

- **Component:** `apps/web/src/components/PayCompare.tsx` (`data-testid="pay-compare"`)
- **Rule Reference:** Rule `R-MD-13`, Decision `D-010`, EXP-07
- **Display Location:** Displayed directly on the comparison control header and results container.
- **Purpose:** Informs the user that their current salary will never enter predictive models or anchor future calculations, ensuring transparency around pay-equity protection.
- **Exact Registered Header Copy:**
  ```text
  See how your compensation compares against the conditional market cohort. Your figure is never stored or used to train models.
  ```
- **Exact Registered Contextual Caveat:**
  ```text
  Your pay may reflect things this estimate does not include, such as scope, employer or timing.
  ```

---

### 2.3 Unbundled DPDPA Consent Checkboxes (Contribution Flow)

- **Component:** `apps/web/src/components/ContributionFlow.tsx` (`ConsentStep`)
- **API Version:** `consent_version: "dpdpa_v1"`
- **Statute:** Section 6, Digital Personal Data Protection Act, 2023
- **Behavioral Requirement:** Unbundled, separate checkboxes; **unchecked by default**; affirmative action required. Benchmarking consent is mandatory to proceed with contribution; research and future contact consents are strictly optional.

#### 1. Benchmarking Consent (Required)
- **Field:** `consent_benchmarking`
- **Exact Registered Label:**
  ```text
  Use my pay data for salary range estimates
  ```
- **Hint Text:**
  ```text
  Your anonymised compensation will be included in aggregate salary range calculations. We never publish individual records. You can delete your contribution at any time using your deletion token.
  ```

#### 2. Research Consent (Optional)
- **Field:** `consent_research`
- **Exact Registered Label:**
  ```text
  Use my data for anonymised research and trend reports (optional)
  ```
- **Hint Text:**
  ```text
  We may publish aggregate, non-identifying findings such as compensation trends by sector or city.
  ```

#### 3. Future Contact Consent (Optional)
- **Field:** `consent_future_contact`
- **Exact Registered Label:**
  ```text
  Contact me if my contribution is queried for quality review (optional)
  ```
- **Hint Text:**
  ```text
  We may reach out via the email you provide in the next step if a data quality issue is detected.
  ```

#### 4. Statutory Withdrawal Notice
- **Display Location:** Displayed below the consent checkboxes prior to submission.
- **Exact Registered Copy:**
  ```text
  By proceeding you confirm that this information reflects your own compensation. Under DPDPA 2023, you have the right to withdraw consent and request deletion at any time using your deletion token.
  ```

---

### 2.4 Decoupled Evidence Grade Disclaimers

- **Component:** `apps/web/src/components/EvidenceBadge.tsx`
- **Rule Reference:** Rule `R-UQ-07`, ADR-0005, Decision `D-010`
- **Display Location:** Displayed prominently as a badge adjacent to the central compensation range.

| Evidence Grade | Status | Exact In-Product Label & Tooltip Copy |
|---|---|---|
| **Grade A** | Robust | `Grade A — Robust Evidence`: High-density cohort ($N \ge 30$), Tier A verified sources, narrow interval width, high predictive support. |
| **Grade B** | Moderate | `Grade B — Moderate Evidence`: Sufficient cohort ($N \ge 10$), Tier B/C sources, informative directional market estimate. |
| **Grade C** | Guarded | `Grade C — Guarded Evidence`: Thin evidence cohort; wider uncertainty interval; interpret with caution. |
| **Abstained** | Abstained | `Estimation Withheld`: Insufficient statistical support to provide a reliable estimate without hallucinating. |

---

### 2.5 Calibrated Abstention Notice

- **Component:** `apps/web/src/components/AbstentionNotice.tsx` (`data-testid="abstention-notice"`)
- **API Status:** HTTP 200 with `status: "abstained"`
- **Rule Reference:** Rule `R-UQ-02`, Rule `R-MD-08`, ADR-0005, Rule `R-UI-03`
- **Display Location:** Displayed in place of numeric salary bands when the query profile falls outside reliable model support.
- **Tone:** Neutral presentation (`--ink-2` on `--sunken`, never alert/danger colors).
- **Exact Registered Headline:**
  ```text
  We can't give a reliable range for this combination yet.
  ```
- **Registered Reason Explanations:**
  - `INSUFFICIENT_SUPPORT`: *"We have too few comparable records for this combination."*
  - `OUT_OF_RANGE`: *"This profile is unusual compared with the records we have."*
  - `STALE_DATA`: *"The newest records for this combination are too old."*
  - `LOW_SOURCE_QUALITY`: *"The records we have for this combination are not reliable enough."*
  - `INTERVAL_TOO_WIDE`: *"The range would be too wide to be useful."*

---

### 2.6 Small-Cell Suppression ($k_{\min} \ge 5$) Notice

- **API Endpoint:** `/v1/evidence/cohort`, `/v1/estimates`
- **Rule Reference:** Rule `R-DA-10`, ADR-0008
- **Exact Registered Copy:**
  ```text
  In compliance with statistical privacy safeguards, compensation distributions and percentiles are withheld for cohorts with fewer than 5 distinct natural persons.
  ```

---

### 2.7 Document Upload Prohibition Notice

- **Component:** `apps/web/src/components/ContributionFlow.tsx`
- **Rule Reference:** ADR-0008 Section 5
- **Exact Registered Copy:**
  ```text
  Do not upload payslips, offer letters, tax returns, or PDF documents. Only self-attested numeric entries are accepted to safeguard personal data.
  ```

---

### 2.8 Non-Causal Explanation Caveat

- **Rule Reference:** Rule `R-MD-08`, PRD Section 12
- **Display Location:** Alongside feature attribution charts and percentile breakdown cards.
- **Exact Registered Copy:**
  ```text
  Feature attributions represent descriptive statistical associations in historical data. They do not represent causal factors, career requirements, or salary guarantees.
  ```

---

## 3. Compliance Verification Matrix

| Copy Item | Code File | Verification Test |
|---|---|---|
| Decision Support Disclaimer | `apps/web/src/components/DisclaimerLine.tsx` | `tests/unit/test_legal_sign_off.py::test_disclaimer_line_exact_match` |
| Compare-Only Notice | `apps/web/src/components/RefinementAndCompare.tsx` | `tests/unit/test_legal_sign_off.py::test_compare_only_copy_match` |
| Benchmarking Consent | `apps/web/src/components/ContributionFlow.tsx` | `tests/unit/test_legal_sign_off.py::test_consent_benchmarking_exact_match` |
| Research Consent | `apps/web/src/components/ContributionFlow.tsx` | `tests/unit/test_legal_sign_off.py::test_consent_research_exact_match` |
| Contact Consent | `apps/web/src/components/ContributionFlow.tsx` | `tests/unit/test_legal_sign_off.py::test_consent_contact_exact_match` |
| Abstention Copy | `apps/web/src/components/EstimateScreen.tsx` | `tests/unit/test_legal_sign_off.py::test_abstention_copy_match` |
| $k_{\min} \ge 5$ Suppression | `src/compintel/governance/service.py` | `tests/unit/test_governance_service.py` |
