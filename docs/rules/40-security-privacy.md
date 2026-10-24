# Security, Privacy & Statutory Compliance Rules (40-security-privacy)

| Field | Value |
|---|---|
| Topic | Information Security, OWASP ASVS, India DPDP Act 2023, and CCI Safe Harbors |
| Governing Rule Families | `R-SC`, `R-DA`, `R-FA`, ADR-0008, ADR-0012 |
| Audience | AI Assistant, Security Engineers, Legal Counsel |

---

## 1. Security Rules (R-SC)

| ID | Rule | Description |
|---|---|---|
| **R-SC-01** | **OWASP ASVS Verification** | Maintain 100% compliance across all 32 controls in the OWASP ASVS v4.0.3 Level 1 checklist. |
| **R-SC-02** | **Zero Hardcoded Secrets** | No API keys, database passwords, HMAC salts, or certificates committed to Git. Enforced by automated secret scans in CI. |
| **R-SC-03** | **Dependency Vulnerability Scans** | Clean `pip-audit` (0 CVEs) and clean `npm audit` required before any merge. |
| **R-SC-04** | **Input Sanitization & CSP** | Enforce strict Content Security Policy (CSP), client-side XSS sanitization (`DOMPurify`), and parameter validation. |
| **R-SC-05** | **Rate Limiting & Abuse Prevention** | Public endpoints enforce rate limits, payload size caps, and request throttling. |
| **R-SC-06** | **Atomic Model Rollbacks** | Serving layer must support atomic model hot-rollbacks ($< 1.0\text{ ms}$) without system restarts or downtime. |
| **R-SC-07** | **LLM Serving Boundary** | No Large Language Model (local or remote) may be placed on the real-time serving path without a formal ADR and security threat model. |
| **R-SC-08** | **CORS & Tenant Isolation** | Restrict CORS to authorized origins. B2B tenant data isolated cryptographically with per-tenant HMAC salts. |

---

## 2. Privacy & Statutory Data Governance (R-DA & R-FA)

| ID | Rule | Description |
|---|---|---|
| **R-DA-01** | **Licence Gate** | Ingestion of external datasets requires approved entries in the evidence register. No unlawful web scraping. |
| **R-DA-07** | **PII Scrubbing** | Absolute prohibition on direct identifiers (Aadhaar, PAN, email, phone, name, bank account). Immediate rejection upon discovery. |
| **R-DA-10** | **Small-Cell Anonymity Floor** | Any aggregate, slice, or reporting group with fewer than $k_{\min} = 5$ distinct individuals is suppressed by construction. |
| **R-FA-01** | **Prohibition on Candidate Ranking** | The platform provides self-directed decision support only. Never rank, sort, or screen candidates for employment. |
| **R-FA-02** | **Demographic Proxy Prohibition** | Protected attributes (gender, caste, religion, age, disability) are permanently banned from feature registries and models. |
| **R-FA-04** | **Anti-Anchoring Isolation** | Current salary is strictly quarantined to `COMPARE_ONLY`. Never use current pay to predict market distributions. |

---

## 3. Statutory Guardrails (India Tech Focus)

1. **Digital Personal Data Protection (DPDP) Act 2023 & Rules 2025:**
   - Standalone, plain-language notices for voluntary contributions.
   - Purpose limitation and client-side unbundled consent.
   - Built-in data export (JSON) and immediate complete local erasure buttons.
   - 18+ user self-declaration in MVP to prevent minors' data processing without verifiable parental consent.
2. **Competition Commission of India (CCI) Wage Benchmarking Safe Harbors:**
   - Minimum 5 distinct employer contributors per reported slice.
   - Maximum single-employer volume concentration cap of 35.0%.
   - Minimum 3-month historical lag to prevent real-time wage coordination.
   - Mathematical wage coarsening to ₹50,000 INR increments and calendar quarter date coarsening.
