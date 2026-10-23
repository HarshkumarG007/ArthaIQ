# ArthaIQ DPDPA 2023 Regulatory Impact Note: Longitudinal Schema Extension

| Field | Value |
|---|---|
| Document ID | `DPDPA-AMEND-T1304-20261023` |
| Review Date | 2026-10-23 |
| Status | **APPROVED & RATIFIED** |
| Governing Statute | Digital Personal Data Protection Act, 2023 (DPDPA, Act No. 22 of 2023, India) |
| Relates to | ADR-0008 Section 6, Task T13.04, Phase 13.D, PRD Section 13, Rules R-DA-07, R-DA-10 |
| Applicable Component | `compintel.schema.canonical`, `compintel.governance`, `app.contributions` |

---

## 1. Executive Summary

This Data Protection Impact Note documents the regulatory, privacy, and architectural review of the **Longitudinal Career Schema Extension** introduced under Task T13.04 (Phase 13.D).

The extension introduces three optional career-event attributes to the voluntary intake schema:
1. `career_start_date` (`Date | None`)
2. `last_promotion_date` (`Date | None`)
3. `right_censored_exit_flag` (`Boolean | None`)

**Legal Determination:** The extension strictly complies with all provisions of the Digital Personal Data Protection Act, 2023 ("DPDPA 2023"). All three attributes are 100% voluntary, default to `null`, operate under explicit unbundled consent (`purpose_research_aggregation`), and maintain strict zero-dependency isolation from core compensation prediction serving.

---

## 2. Telemetry Scope and Technical Definition

The schema extension expands the voluntary compensation record structure (`app.contributions` in the relational store and `CompensationObservation` in canonical Python models) with the following attributes:

| Field Name | Type | Nullable | Default | Description & Privacy Classification |
|---|---|---|---|---|
| `career_start_date` | `Date` (ISO-8601 `YYYY-MM-DD`) | `True` | `null` | Approximate date when data principal commenced professional technology employment. Low-sensitivity career milestone. |
| `last_promotion_date` | `Date` (ISO-8601 `YYYY-MM-DD`) | `True` | `null` | Effective date of contributor's most recent title, band, or internal level advancement. Low-sensitivity career milestone. |
| `right_censored_exit_flag` | `Boolean` | `True` | `null` | Indicator where `True` denotes a completed role tenure (exit event), and `False` or `None` denotes continuing active tenure. Binary event flag. |

### Technical Invariants Enforced in Code
1. **Ordering Invariant:** `last_promotion_date >= career_start_date` enforced deterministically at ingestion in both Pydantic schema validation (`DataContractError: INVALID_LONGITUDINAL_DATES`) and service intake (`GovernanceError`).
2. **Non-Mandatory:** Absence of these fields never triggers validation errors, HTTP 422 rejections, or intake quarantine.
3. **No Granular History:** No company identifiers, project notes, supervisor names, or performance appraisal scores are collected.

---

## 3. Statutory Analysis Under DPDPA 2023

### 3.1 Section 4: Grounds for Processing and Purpose Limitation
- **Processing Purpose:** Telemetry is gathered strictly for statistical aggregation, macro cohort tenure analysis, and long-range research into career velocity dynamics (`EXP-TRAJ-r`, Task T13.05) and survival modeling (`EXP-SURV-r`).
- **Limitation:** Processing is strictly confined to statistical research. Under no circumstances are milestone dates used for individual profiling, automated decision-making regarding employment eligibility, or candidate screening (PRD Section 12).

### 3.2 Section 6: Notice and Unbundled Consent Architecture
- **Unbundled Processing Ground:** Collection of longitudinal event fields is governed by the independent `purpose_research_aggregation` consent checkbox codified in ADR-0008 Section 3.
- **Unchecked by Default:** In strict adherence to Rule R-FA-01, the checkbox is unchecked by default. If a contributor grants benchmarking consent (`purpose_compensation_benchmarking`) but unchecks research consent, any longitudinal fields submitted are stripped before persistence.
- **Notice:** Contributor intake flows explicitly state that career milestone dates are completely optional and intended solely for open research cohorts.

### 3.3 Section 8: Obligations of Data Fiduciary (Data Minimization & Retention)
- **Data Minimization:** Only broad dates are collected. No documentary evidence (e.g. appointment letters, promotion letters, reliving letters) is permitted. Document upload remains strictly prohibited in beta (ADR-0008 Section 5).
- **Storage Limitation:** Longitudinal records are bound to the existing 24-month retention schedule. Scheduled retention purges automatically scrub expired intake rows.

### 3.4 Section 12: Rights of Data Principal (Statutory Erasure Cascade)
- **Self-Service Erasure:** Data principals retain the unconditioned right to revoke consent and demand erasure at any time via the cryptographic deletion token (`DELETE /v1/me/data` or `POST /v1/contributions/delete`).
- **Complete Purge:** Deletion cascades execute immediate hard deletion of the `app.contributions` row, eliminating all associated milestone dates from operational stores.

---

## 4. Re-Identification Risk Assessment & Privacy Mitigations

| Risk Vector | Likelihood | Impact | Applied Mitigation | Residual Risk |
|---|---|---|---|---|
| **Thin-Cohort Re-identification** (Cross-referencing exact milestone dates with LinkedIn profiles) | Low | Low | Enforced $k_{\min} \ge 5$ distinct persons suppression floor (Rule R-DA-10). No query returns distributions for cohorts under 5 persons. Furthermore, exact dates are never exposed in external API endpoints; only annualized derivative metrics (e.g. tenure years, annualized promotion velocity) are computed. | Negligible |
| **Identity Linkage** | Negligible | Critical | Schema separation: identity store resides in isolated `identity` schema, accessible only through pseudonymous `contributor_key` UUIDv4. Database serving role has zero access to identity schema. | Negligible |
| **Pipeline Drift / Leakage** | Negligible | Low | Telemetry logging sanitization filters (Rule R-CD-06) redact dates and PII from application logs and metrics. | Negligible |

---

## 5. Architectural Non-Interference Guarantee

A primary requirement of Task T13.04 is zero interference with existing production serving:
1. **Model Bundle Independence:** The production champion model (Rung F Level 2 Conformal CatBoost, serialized in `artifacts/champion_v0/`) has zero feature dependency on longitudinal fields. Its feature matrix strictly consists of canonicalized role family, seniority, metro location, normalized years of experience, and quadratic Mincerian tenure terms.
2. **Serving Endpoint Invariance:** The core estimation endpoint `POST /v1/estimates` and scenario engine `POST /v1/scenarios/negotiation` do not accept, require, or process longitudinal milestone dates.
3. **Database Migration Safety:** Alembic migration `0002_longitudinal_career_schema` introduces nullable columns with default `null`, ensuring zero downtime and 100% backward compatibility with all existing database queries.

---

## 6. Audit Verdict and Sign-Off

The Longitudinal Career Schema Extension has been verified against the statutory requirements of India's DPDPA 2023, ADR-0008 privacy invariants, and Rule R-DA-10 small-cell suppression standards.

| Review Dimension | Standard | Audit Result | Sign-Off Date |
|---|---|---|---|
| DPDPA 2023 Purpose Limitation | Sec 4 | **COMPLIANT** | 2026-10-23 |
| Unbundled Voluntary Consent | Sec 6 | **COMPLIANT** | 2026-10-23 |
| Data Minimization & Retention | Sec 8 | **COMPLIANT** | 2026-10-23 |
| Operational Erasure Cascade | Sec 12 | **COMPLIANT** | 2026-10-23 |
| Identity Schema Separation | ADR-0008 | **COMPLIANT** | 2026-10-23 |
| Core Model Non-Interference | Rule R-MD-01 | **COMPLIANT** | 2026-10-23 |

**Verdict:** **APPROVED FOR PRODUCTION MIGRATION & SCHEMATIC INTEGRATION.**
