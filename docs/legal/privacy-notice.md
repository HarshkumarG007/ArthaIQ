# ArthaIQ Privacy Notice (DPDPA 2023)

| Field | Value |
|---|---|
| Document Version | 1.0.0 |
| Effective Date | 2026-10-21 |
| Status | **Active (Public Beta)** |
| Governing Statute | Digital Personal Data Protection Act, 2023 (India) |
| Relates to | PRD Section 13, NFR-04, ADR-0008, `rules.md` R-DA-07, R-DA-10, R-MD-13 |

---

## 1. Introduction

ArthaIQ ("we", "us", or "our") is committed to protecting your privacy and handling your personal data with institutional transparency and mathematical safeguards. 

This Privacy Notice outlines how we collect, process, isolate, retain, and erase personal data when you interact with our compensation intelligence application and APIs, in strict compliance with the **Digital Personal Data Protection Act, 2023 ("DPDPA 2023")** of India and international privacy engineering principles.

---

## 2. Data Fiduciary and Grievance Officer

Under the DPDPA 2023, ArthaIQ functions as the **Data Fiduciary** for personal data processed through our Service.

### Data Protection & Grievance Redressal Officer
- **Officer Name:** Privacy Redressal Officer
- **Designation:** Head of Data Governance & Legal Compliance
- **Email:** `privacy@arthaiq.in` / `grievance@arthaiq.in`
- **Location:** Bengaluru, Karnataka, India
- **Response SLA:** Acknowledgment within 24 hours; resolution within 7 working days.

---

## 3. Principles of Data Processing

We operate strictly under the statutory core principles of privacy by design:
1. **Purpose Limitation:** Data is processed solely for explicit, lawful purposes you actively consent to.
2. **Data Minimization:** We collect only the minimum required fields necessary to generate compensation statistics.
3. **Identity Separation (ADR-0008):** Contributor identity is permanently segregated from pay records.
4. **Statistical Anonymization Floor ($k_{\min} \ge 5$):** Aggregates are never displayed for fewer than 5 distinct natural persons.
5. **Storage Limitation:** Operational records are retained for a maximum of 24 months before automatic expiration.

---

## 4. Personal Data Collected and Purpose Specification

We collect personal data only when you voluntarily provide it through query estimation or voluntary compensation contributions.

| Interaction Type | Data Elements Collected | Statutory Purpose | Legal Basis (DPDPA) |
|---|---|---|---|
| **Query Estimation** | Role title, years of experience, primary tech hub/location, optional education/company tier. | Real-time generation of statistical compensation estimates and quantile intervals. | Deemed Consent / Legitimate Use (Section 4) |
| **Compare-Only Entry** | Current guaranteed cash (`feat_l3_current_guaranteed_cash`). | Displaying user's percentile position against market. *Never entered into predictive training matrices (Rule R-MD-13).* | Explicit User Input |
| **Voluntary Contribution (SRC-INT-VOL-01)** | Annual guaranteed cash, optional variable pay/RSUs, role, seniority, location, YoE, pseudonymous contact handle (email/token). | Enriching market calibration cohorts, retraining models, aggregate salary research reports. | Explicit, Unbundled Consent (Section 6) |
| **Technical & Audit Logs** | Anonymized IP hash, User-Agent hash, request duration, HTTP status code, request ID. | Operational security, DDoS protection, rate limiting, and regulatory compliance audit trail. | Legitimate Use & Regulatory Auditability |

### What We NEVER Collect
- **Prohibited Demographics:** Gender, caste, religion, sexual orientation, age, biometric data, or physical disability (`rules.md` Section 16 Rule 11).
- **Physical Documents:** Payslips, Form 16, tax returns, bank statements, or offer letter PDFs are **strictly prohibited** in Public Beta (ADR-0008 Section 5).
- **Third-Party Ad Trackers:** Zero advertising pixels, marketing cookies, or cross-site tracking scripts.

---

## 5. Architectural Safeguards: Identity Separation and k_min

### 5.1 Strict Identity Separation (ADR-0008)
To prevent unauthorized correlation between personal identity and compensation details, our database enforces strict relational schema partitioning:
- **`identity.contributor_identities`**: Stores contributor contact handles, consent state, and cryptographic identity hashes.
- **`app.contributions`**: Stores normalized compensation numbers keyed only by a pseudonymous, randomly generated UUIDv4 (`contributor_key`).
- **Role Isolation:** The operational API serving role (`serving`) possesses **zero SELECT or READ permissions** on the `identity` schema.

```
+------------------------------------+          +------------------------------------+
|   identity.contributor_identities  |          |          app.contributions         |
|------------------------------------|          |------------------------------------|
| id: UUID                           |          | id: UUID                           |
| contributor_key: UUIDv4  --------->|=========>| contributor_key: UUIDv4            |
| contact_handle_hash: VARCHAR       |          | role_family: VARCHAR               |
| consent_version: VARCHAR           |          | guaranteed_cash_annual: NUMERIC    |
+------------------------------------+          +------------------------------------+
            ^                                                     ^
            | (Restricted: app role only)                         | (Read-only: pipeline)
```

### 5.2 Small-Cell Anonymization Floor ($k_{\min} \ge 5$)
Under Rule `R-DA-10` and ADR-0008, no aggregate salary figure, percentile band, histogram bucket, or summary metric is displayed, exported, or logged for cohorts containing fewer than **$5$ distinct natural persons**.
- Slices with $N < 5$ persons are automatically suppressed with HTTP 200 `status: "abstained"` and reason code `INSUFFICIENT_COHORT_SUPPORT`.
- This mathematically protects individual contributors from re-identification via subtraction or intersection attacks.

### 5.3 Compare-Only Current Pay Quarantine (Rule R-MD-13)
Any current salary entered for peer comparison is strictly quarantined in memory for real-time benchmark rendering. It is **never stored in prediction feature matrices** and **never used to estimate market value**, mitigating historical pay discrimination compounding.

---

## 6. Unbundled Consent Framework (DPDPA Section 6)

In compliance with Section 6 of the DPDPA 2023, consent is requested through separate, unbundled checkboxes that are **unchecked by default**:
1. **Benchmarking Consent (Required for contribution):**
   > *"I consent to using my anonymized pay details for market salary benchmarking and public cohort estimates."*
2. **Research Consent (Optional):**
   > *"I consent to including my anonymized submission in aggregate compensation research and industry salary reports."*
3. **Future Contact Consent (Optional):**
   > *"I agree to be contacted occasionally with product updates and compensation insights (optional)."*

Consent state is versioned (`consent_version: "dpdpa_v1"`) and logged in an immutable, append-only audit trail (`app.consent_records`).

---

## 7. Data Retention and Operational Erasure Cascade

### 7.1 Retention Policy
Operational contribution records are retained for a maximum duration of **24 months** from the date of submission. Following this window, records are automatically purged from active databases during scheduled lifecycle maintenance.

### 7.2 Right to Withdraw Consent and Operational Erasure (DPDPA Section 12)
You have the unconditional right to withdraw consent and request the permanent deletion of your data at any time.

When you submit an erasure request via the HTTP DELETE `/v1/me/data` API endpoint using your cryptographic deletion token:
1. **Record Purge:** The associated compensation record in `app.contributions` is permanently and immediately deleted (`DELETE FROM app.contributions WHERE contributor_key = :key`).
2. **Identity Scrubbing:** The contributor identity entry in `identity.contributor_identities` is marked `status = "deleted"` and contact handles are cryptographically overwritten.
3. **Consent Revocation:** Consent records in `app.consent_records` are updated to `status = "withdrawn"`.
4. **Append-Only Audit Log:** A non-PII operational event (`action = "contribution_erased"`) is recorded in `app.audit_log` to prove regulatory compliance (Rule R-SC-08).
5. **Downstream Models:** Derived statistical aggregates recompute during the next regular pipeline cycle; individual erased rows are excluded from all subsequent training snapshots.

---

## 8. Data Principal Rights under DPDPA 2023

You have the following statutory rights regarding your personal data:
- **Right to Access Information (Section 11):** Request a summary of the personal data we hold about you and the processing activities undertaken.
- **Right to Correction and Erasure (Section 12):** Request correction of inaccurate personal data or complete operational erasure of your contributed records.
- **Right of Grievance Redressal (Section 13):** Access readily available mechanisms to address privacy concerns or grievances through our designated Grievance Officer.
- **Right to Nominate (Section 14):** Nominate an individual to exercise your privacy rights in the event of death or incapacity.

To exercise any of these rights, email `privacy@arthaiq.in` or trigger self-service erasure via your deletion token in the web interface.

---

## 9. Security Safeguards

We implement administrative, technical, and physical security measures per OWASP ASVS v4.0.3 User-Facing standards:
- **Encryption at Rest:** All databases and snapshots encrypted using AES-256.
- **Encryption in Transit:** Strict TLS 1.3 encryption across all public web and API endpoints.
- **Zero PII Logging:** Automatic regex filters scrub emails, phone numbers, tokens, and salary figures from log messages and Prometheus metric labels (Rules `R-CD-06`, `R-DA-07`).
- **Container Isolation:** Services execute in non-root Docker containers (`UID 10001`) with read-only root filesystems and minimal kernel privileges.

---

## 10. Updates to this Notice

We may periodically revise this Privacy Notice to reflect statutory updates to DPDPA rules or architectural enhancements. Any material changes will be published here with an updated "Effective Date."

---

## 11. Supervisory Authority

If you are not satisfied with the resolution provided by our Grievance Officer, you have the right to file a complaint with the **Data Protection Board of India** as provided under the Digital Personal Data Protection Act, 2023.
