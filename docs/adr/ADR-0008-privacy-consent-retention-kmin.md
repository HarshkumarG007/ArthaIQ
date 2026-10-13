# ADR-0008: Privacy, Consent, Retention and k_min

| Field | Value |
|---|---|
| Status | **Proposed** |
| Decided at | T9.10 |
| Relates to | `architecture.md` section 12, PRD section 13, `rules.md` R-FA-01 to R-FA-04, R-DA-07, R-DA-10 |

---

## Context

The system collects voluntarily contributed pay records in the public beta. Personal data and pay records must be handled under privacy law `[U: confirm DPDPA 2023 obligations with qualified counsel at T9.16]`. Identity and pay records must be separated. Small aggregates must be suppressed.

## Key decisions needed

### 1. Identity separation

**Proposed:** contributor identity lives in a separate `identity` schema (separate PostgreSQL schema or database role). Pay records carry only a pseudonymous `contributor_key`. The serving role has no access to the `identity` schema.

### 2. k_min (small-cell suppression)

**Proposed:** no aggregate is shown, exported or logged for fewer than `k_min` distinct persons. Count persons, not rows.

`k_min` value: **[TBD — to be set here before beta, with legal review]**.

Candidates: 5, 10, 15. The value must balance privacy protection against utility. A lower value risks re-identification; a higher value reduces coverage.

### 3. Consent

- Unbundled: one purpose per checkbox.
- Unchecked by default.
- Stores: what is stored, for how long, and how to delete.
- Versioned: `consent_version` recorded with each contribution.

### 4. Retention and deletion

- Retention periods per data class: **[TBD with legal counsel at T9.16]**.
- Deletion cascades to operational stores within the retention window.
- Aggregates recompute at the next data refresh.
- Backups follow the stated retention period.

### 5. Document uploads

No document uploads unless this ADR explicitly approves them. Currently: not approved.

## Database roles

| Role | Access |
|---|---|
| `serving` | Read-only; no `identity` schema; no record-level `compensation_observation` |
| `pipeline` | Read/write `canonical`, `staged`; no `identity` |
| `app` | Read/write `identity` and `contribution`; no raw or canonical |
| `admin` | Full access; audit-logged |

## Decision

**Pending.** Finalized at T9.10 with legal input from T9.16.

## Consequences

- The `k_min` value is written into `config/thresholds.yaml` and enforced in code with a test.
- Any query that could expose a cell below `k_min` raises `PrivacyViolationError`.
- The audit trail records all access to restricted data (R-SC-08).
- If the DPDPA 2023 requires additional obligations `[U]`, this ADR is updated.

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
