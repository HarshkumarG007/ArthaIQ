# B2B Employer Syndication Intake Protocol (Phase 14, SRC-B2B-01)

> **Scope:** Operational Architecture, Cryptographic Isolation, Differential Privacy Floor, and Automated Intake Specification for B2B Enterprise Employer Compensation Feeds.
> **Governing Standards:** PRD Sec 5, FR-05 · Rules R-MD-01, R-MD-02, R-MD-03, R-MD-04, R-MD-05, R-MD-07, R-MD-09, R-MD-11, R-MD-15, R-UQ-01, R-UQ-05, R-DA-10 · ADR-0008 Section 6 · India DPDPA 2023 · CCI Anti-Trust Wage Benchmarking Guidelines.
> **Source Identifier:** `SRC-B2B-01` · **Pre-Registered SQS:** `98.0 / 100.0` (Tier 1 Ground Truth) · **Task:** Phase 14 Architecture & Planning.

| Metadata Attribute | Specification Value |
|:---|:---|
| **Document ID** | `docs/research/b2b-syndication-protocol-phase14.md` |
| **Source Identifier** | `SRC-B2B-01` (`config/sources/SRC-B2B-01.yaml`) |
| **Protocol Status** | **APPROVED OPERATIONAL SPECIFICATION** |
| **Effective Target Phase** | Phase 14 (H2 2027 – H1 2028) |
| **Primary Ingestion Target** | Bulk Enterprise Longitudinal Compensation & Career Transitions |
| **Minimum Required Volume ($N$)** | $\ge 500$ verified non-synthetic transitions across $\ge 50$ clusters |
| **Privacy Safeguards** | Zero Raw PII · Tenant-Salted HMAC-SHA256 · $k_{\min} \ge 5$ Anonymization Floor |
| **Statutory Compliance** | Digital Personal Data Protection Act (DPDPA 2023) · CCI Safe Harbor |

---

## 1. Executive Summary & Strategic Rationale

During the **Phase 13 Gate G13 Review** (ratified **GO** under Decision `D-024`), production health telemetry and the PT4 Gaussian Copula scenario layer were successfully promoted. However, two high-value longitudinal experiments were formally deferred:
1. **`EXP-10r` (Longitudinal Career Transition Network):** Deferred due to network sparsity (`16/50` qualified clusters, $N=48$ empirical transition edges vs $N \ge 150$ power threshold).
2. **`EXP-TRAJ-r` (Dynamic Career Trajectory Features):** Deferred due to observation window truncation (`5.9 months` vs $\ge 12.0$ calendar months threshold; 0 multi-cycle promotion records).

Individual voluntary user submissions (`SRC-INT-VOL-01`) arrive incrementally and organically, but cannot bridge the sample-size deficit required for dense network graph topology within a single operational quarter. 

**`SRC-B2B-01` (B2B Enterprise Syndication)** is engineered to solve this deficit. Under bilateral enterprise benchmarking agreements, participating employers contribute anonymized, verified payroll and milestone extracts in structured quarterly batches. This protocol delivers the required depth ($\ge 500$ verified records, $\ge 50$ qualified employer clusters, $\ge 12$ months historical milestone span) while maintaining unconditional adherence to zero-knowledge privacy and antitrust safe harbors.

---

## 2. Invariant Architectural Boundaries

In accordance with ArthaIQ core governance, `SRC-B2B-01` operates under strict invariant boundaries:

1. **Rule `R-MD-09` & `R-MD-11` (Non-Synthetic Verification & Champion Invariance):**
   - 100.0% of syndicated records must originate from genuine enterprise payroll registries. Synthetic generation or simulated employee records are strictly barred.
   - Core point estimation remains 100% anchored on the Champion Rung F Level 2 Conformal CatBoost model. B2B data enriches calibration panels and unlocks longitudinal re-audits without destabilizing core production scoring.
2. **Rule `R-DA-10` ($k_{\min} \ge 5$ Organization Floor):**
   - Any cell, reporting bucket, or transition edge with fewer than 5 unique records collapses to `EMP-ANONYMOUS` or `OTHER`.
   - Single-employer identification is cryptographically and statistically prohibited.
3. **Rule `R-UQ-01` & `R-UQ-05` (Zero Lone Numbers & Monotonic Quantiles):**
   - Every metric, summary, or report derived from B2B intake must pair point statistics with calibrated 80% conformal bounds ($[P_{10}, P_{50}, P_{90}]$) and complete currency/period units.
   - Strict monotonic non-crossing quantiles ($P_{10} \le P_{50} \le P_{90}$) are mathematically guaranteed.
4. **Rule `R-MD-07` (Component Unbundling & Deductive Accounting):**
   - Gross CTC packages must be unbundled into basic salary, fixed allowances, performance bonus, and equity RSUs/ESOPs before pipeline entry. Statutory employer overhead (EPF, gratuity provisions) is excluded from employee guaranteed cash.

---

## 3. Cryptographic Isolation & Zero-Knowledge Architecture

To prevent employee re-identification, tenant snooping, or competitive wage surveillance, `SRC-B2B-01` implements an end-to-end zero-knowledge pipeline:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      B2B SYNDICATION CRYPTOGRAPHIC PIPELINE                            │
│                                                                                        │
│  [ Enterprise HRIS / Payroll Extract ]                                                 │
│             │                                                                          │
│             ▼                                                                          │
│  [ Client-Side Sanitization & PII Scrubbing ]                                          │
│  • Strip: Employee Name, Personal Email, Phone, PAN, Aadhaar, UAN, Bank Account.       │
│  • Coarsen: Dates to Quarter (YYYY-Qn); Compensation to nearest ₹50,000.              │
│             │                                                                          │
│             ▼                                                                          │
│  [ Cryptographic Tokenization Engine ]                                                 │
│  • Pseudonymize ID = HMAC-SHA256(KMS_Tenant_Salt_A, Raw_Emp_ID)                       │
│  • Rotating Enterprise Salt per Tenant (Zero Cross-Tenant Correlation)                 │
│             │                                                                          │
│             ▼                                                                          │
│  [ TLS 1.3 Transport to ArthaIQ Ingestion Daemon ]                                     │
│  • Ingest to Quarantined Landing Zone (S3 / GCS with KMS Envelope Encryption)          │
│             │                                                                          │
│             ▼                                                                          │
│  [ Automated Gatekeeper & Canary Quarantine ]                                          │
│  • Regex Scan for PII Leakage (Fail = Immediate Hard Reject)                           │
│  • Cell Aggregation Check: k_min >= 5 Enforcement                                     │
│  • Accounting Identity Validation (CTC = Cash + Bonus + Equity + Overhead)             │
│             │                                                                          │
│             ▼                                                                          │
│  [ Multi-Tenant Differential Privacy Pooling (Canonical Staging) ]                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 PII Prohibition & Ingestion Redaction
The following data attributes are strictly classified as **PROHIBITED_PII**. The client-side connector and the ingestion gateway immediately reject any batch containing these keys or values matching their regex signatures:

| Prohibited Dimension | Pattern / Signature | Rejection Action |
|:---|:---|:---|
| **Employee Legal Name** | Alphanumeric person names | Immediate batch quarantine |
| **Personal Email** | `^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$` | Immediate batch quarantine |
| **Permanent Account Number (PAN)** | `^[A-Z]{5}[0-9]{4}[A-Z]{1}$` | Immediate batch quarantine |
| **Aadhaar Number** | `^[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}$` | Immediate batch quarantine |
| **Universal Account Number (UAN)** | `^10[0-9]{10}$` | Immediate batch quarantine |
| **Precise Bank Account Number** | 9–18 digit account numbers | Immediate batch quarantine |
| **Exact IP Address / GPS** | IPv4/IPv6 address strings | Immediate batch quarantine |

### 3.2 Tenant Salted Tokenization
Raw internal employee IDs (`EMP-94821`) must never leave the enterprise perimeter in plain text.
- Each enterprise tenant is provisioned an isolated 256-bit cryptographic salt ($S_{\text{tenant}}$) stored in an enterprise Key Management Service (AWS KMS, GCP Cloud KMS, or HashiCorp Vault).
- The synthetic record token is computed as:
  $$\tau_{\text{emp}} = \text{HMAC-SHA256}\left(S_{\text{tenant}}, \text{Raw\_Emp\_ID} \parallel \text{Tenant\_UUID}\right)$$
- Because salts are disjoint across enterprises ($S_A \ne S_B$), Employer A cannot query or trace an employee’s historical pseudonym in Employer B’s historical records without an explicit, cryptographically signed mobility transit event.

---

## 4. Anti-Trust & Statutory Compliance Safe Harbors

Wage and compensation benchmarking among corporate employers is subject to competition law scrutiny. `SRC-B2B-01` incorporates the **Competition Commission of India (CCI)** antitrust safe harbor standards:

1. **Mandatory Historical Lag (Minimum 3 Calendar Months):**
   - Real-time or prospective wage disclosures are strictly prohibited.
   - All syndicated tranches represent concluded, historical compensation quarters. Forward-looking salary budgets or hiring rate cards are strictly rejected.
2. **Multi-Employer Cell Pooling:**
   - No benchmark, cell summary, or transition coefficient is published or trained if fewer than 5 independent employers contribute to that reporting cell.
   - Single-employer dominance check: No single employer may represent more than 35.0% of the observations in any canonical training slice.
3. **Purpose Limitation (DPDPA 2023 Sec 4 & 5):**
   - Syndicated records are ingested under explicit bilateral data contribution agreements restricted exclusively to statistical wage estimation and academic career mobility modeling. Secondary marketing or recruiter candidate search is contractually and technologically prevented.

---

## 5. Canonical Data Contract & Batch Schema

Syndicated tranches must be formatted as Apache Parquet or CSV with strict adherence to the Pydantic data contract below:

```python
from enum import StrEnum
from pydantic import BaseModel, Field, field_validator
import re


class CanonicalRole(StrEnum):
    SWE = "SWE"
    DATA_SCIENTIST = "DATA_SCIENTIST"
    PRODUCT_MANAGER = "PRODUCT_MANAGER"
    DEVOPS_SRE = "DEVOPS_SRE"
    QA_SDET = "QA_SDET"
    SYSENG = "SYSENG"


class CanonicalSeniority(StrEnum):
    ENTRY = "ENTRY"
    MID = "MID"
    SR = "SR"
    STAFF = "STAFF"
    PRINCIPAL = "PRINCIPAL"


class CanonicalLocation(StrEnum):
    BENGALURU = "BENGALURU"
    NCR = "NCR"
    HYDERABAD = "HYDERABAD"
    PUNE = "PUNE"
    MUMBAI = "MUMBAI"
    CHENNAI = "CHENNAI"


class B2BSyndicationRecord(BaseModel):
    batch_id: str = Field(..., regex=r"^BATCH-B2B-[0-9]{8}-[0-9]{3}$")
    tenant_token: str = Field(..., min_length=16, max_length=64)
    employee_token: str = Field(..., min_length=32, max_length=64)
    quarter_effective: str = Field(..., regex=r"^[2-9][0-9]{3}-Q[1-4]$")

    # Occupational taxonomy
    role: CanonicalRole
    seniority: CanonicalSeniority
    location: CanonicalLocation
    years_experience: float = Field(..., ge=0.0, le=45.0)

    # Financial line items (Gross INR)
    basic_salary_annual: float = Field(..., ge=100_000.0, le=50_000_000.0)
    fixed_allowances_annual: float = Field(..., ge=0.0, le=50_000_000.0)
    guaranteed_cash_annual: float = Field(..., ge=100_000.0, le=50_000_000.0)
    variable_bonus_annual: float = Field(default=0.0, ge=0.0, le=50_000_000.0)
    equity_annualized_grant: float = Field(default=0.0, ge=0.0, le=100_000_000.0)
    statutory_overhead_annual: float = Field(default=0.0, ge=0.0)
    ctc_annual: float = Field(..., ge=100_000.0, le=200_000_000.0)

    # Longitudinal mobility markers
    is_career_transition: bool = Field(default=False)
    prior_employer_cluster: str | None = Field(default=None)
    tenure_in_prior_role_months: int | None = Field(default=None, ge=0, le=360)

    @field_validator("guaranteed_cash_annual")
    def validate_accounting_identity(cls, v, values):
        basic = values.data.get("basic_salary_annual", 0.0)
        allowances = values.data.get("fixed_allowances_annual", 0.0)
        computed = basic + allowances
        if abs(v - computed) > 100.0:
            raise ValueError(
                f"Accounting mismatch: guaranteed cash {v} != basic {basic} + allowances {allowances}"
            )
        return v
```

---

## 6. Integration with Ingestion Daemon (`compintel.ingestion.daemon`)

Batch ingestion for `SRC-B2B-01` is orchestrated through the pre-existing production ingestion daemon (`compintel.ingestion.daemon`), which ran 30 days with zero staleness violations and p95 intake latency $11.35\text{ min} \le 15.0\text{ min}$ during `EXP-16`:

1. **Automated Polling Schedule:** Ingestion daemon checks the designated secure drop bucket `s3://arthaiq-b2b-syndication-vault/` on a quarterly schedule (every 90 days) with a 7-day ingestion intake window.
2. **Canary Quarantine Execution:**
   - 10% canary slice is parsed through the strict Pydantic validation suite.
   - PII pattern scanning (PAN, Aadhaar, email regex) is executed across 100% of rows.
   - Any violation triggers an immediate circuit break: the entire batch is moved to `quarantine/failed-batches/` and an alert is logged with zero partial data leakage.
3. **Differential Privacy Floor Enforcement ($k_{\min} \ge 5$):**
   - Records are grouped by `(role, seniority, location, prior_employer_cluster)`.
   - Cohorts with count $< 5$ have their `prior_employer_cluster` overwritten with `EMP-ANONYMOUS`.
4. **Data Refresh & Lineage Reporting:**
   - Ingestion daemon generates a signed manifest `experiments/results/b2b_syndication_manifest_{batch_id}.json` documenting non-synthetic provenance, row counts, and checksum hashes.

---

## 7. Next Audit Triggers: Unblocking Phase 14 Experiments

The arrival of `SRC-B2B-01` tranches directly governs the unblocking of deferred Phase 13 experiments:

| Experiment / Charter | Pre-Registered Trigger Standard | Target Metric | Action Upon Fulfillment |
|:---|:---|:---|:---|
| **`EXP-10r` (Transition Network)** | $\ge 500$ verified transition records across $\ge 50$ clusters | $f_{\text{giant}} \ge 0.85$, mean degree $\ge 3$ | Re-audit Node2Vec / Graph Embedding layer. |
| **`EXP-TRAJ-r` (Career Trajectory)** | $\ge 12.0$ calendar months span with $\ge 100$ verified promotions | $\Delta\text{Pinball} \ge +0.015$, coverage within $[75\%, 85\%]$ | Train dynamic velocity features. |

---

## 8. Summary Governance Ratification

This protocol establishes the complete operational architecture for `SRC-B2B-01` under strict mathematical and statutory guarantees:
- **Zero Raw PII & Zero Cross-Tenant Snooping:** Cryptographic tenant-salted HMAC tokens.
- **Strict Privacy Floor:** $k_{\min} \ge 5$ cell collapse, ₹50,000 rounding noise, 3-month historical lag.
- **Zero Point Overrides:** Core compensation estimation remains strictly governed by Champion Rung F Level 2 Conformal CatBoost.
- **Audit-Ready:** Seamless integration with `compintel.ingestion.daemon` and Pydantic validation suite.
