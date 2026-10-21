# ADR-0008: Privacy, Consent, Retention and k_min

| Field | Value |
|---|---|
| Status | **Accepted** |
| Decided at | T9.10 (2026-10-20) |
| Relates to | `architecture.md` section 12, PRD section 13, `rules.md` R-FA-01 to R-FA-04, R-DA-07, R-DA-10 |

---

## Context

The system collects voluntarily contributed compensation records (SRC-INT-VOL-01) in the public beta to enrich market calibration cohorts. Personal data and compensation records must be handled under India's Digital Personal Data Protection Act (DPDPA) 2023 and privacy best practices. Contributor identity must be strictly segregated from pay records, and thin aggregation cohorts must be suppressed to avoid re-identification.

## Key Decisions

### 1. Identity Separation

**Accepted:** Contributor identity is strictly isolated within the `identity` PostgreSQL schema (`identity.contributor_identities`). Compensation records in `app.contributions` carry only a pseudonymous `contributor_key` (UUIDv4). The serving database role has zero access to the `identity` schema.

### 2. k_min (Small-Cell Suppression)

**Accepted:** $k_{\min} = 5$ distinct persons. No aggregate distribution, percentile, or summary metric is displayed, exported, or logged for fewer than $k_{\min}$ distinct persons.
- Cell counts count **persons**, not rows.
- Codified in `config/thresholds.yaml` under `governance.k_min_persons: 5`.
- Enforced programmatically in code via `check_k_min()`, raising `PrivacyViolationError` on violation.

### 3. Consent Framework (DPDPA 2023)

**Accepted:**
- **Unbundled:** One explicit purpose per checkbox (`purpose_compensation_benchmarking`, `purpose_research_aggregation`, `purpose_future_contact`).
- **Unchecked by default:** Zero pre-ticked consent boxes.
- **Explicit and versioned:** Active version `dpdpa_v1` recorded with client IP and User-Agent hashes for audit verification.
- **Revocable:** Contributor can request erasure at any time using a cryptographic deletion token or authenticated session.

### 4. Retention and Operational Erasure

**Accepted:**
- **Retention window:** 24 months maximum retention for operational intake records.
- **Operational erasure:** Upon user deletion request, records in `app.contributions` are permanently hard-deleted from operational stores.
- **Identity scrubbing:** Associated `identity.contributor_identities` handles and hashes are cryptographically scrubbed (`status="deleted"`).
- **Consent revocation:** `app.consent_records` marked `status="withdrawn"` with timestamp.
- **Audit trail:** Append-only log in `app.audit_log` records the erasure event (`action="contribution_erased"`) without retaining personal data (Rule R-SC-08).
- **Statistical aggregates:** Derived aggregates recompute at the next scheduled pipeline refresh.

### 5. Document Uploads

**Accepted:** Document uploads (e.g. unredacted payslips, offer letters, Form 16 PDFs) are **strictly prohibited** in public beta. All voluntary contributions rely on self-attested numeric entry verified against statistical consistency filters and duplicate quarantine.

## Database Roles & Access Matrix

| Role | Access Permissions |
|---|---|
| `serving` | Read-only; no access to `identity` schema; no access to record-level `contributions` |
| `pipeline` | Read/write `canonical`, `staged`; read-only `app.contributions`; no access to `identity` |
| `app` | Read/write `identity` and `app` (`consent_records`, `contributions`, `deletion_requests`, `audit_log`) |
| `admin` | Restricted maintenance role; all queries and migrations audit-logged |

## Consequences

- The `k_min` threshold is enforced across all reporting pipelines and API endpoints.
- Deletion requests execute an immediate operational purge verified by automated integration test suites.
- The append-only audit trail preserves compliance proof for DPDPA regulatory auditability.

## Evidence

- `src/compintel/governance/models.py`: Relational schemas for identity, consent, contributions, deletion requests, and audit trail.
- `src/compintel/governance/service.py`: Intake validation, quarantine filters, $k_{\min}$ enforcement, and operational erasure cascade.
- `src/compintel/governance/router.py`: REST endpoints (`POST /v1/contributions`, `DELETE /v1/me/data`).
- `tests/integration/test_contribution_lifecycle.py`: End-to-end integration test verifying operational erasure.

## Change Log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
| 2026-10-20 | Ratified as Accepted with $k_{\min} = 5$, unbundled DPDPA consent, 24m retention, operational erasure cascade (T9.10a) |
