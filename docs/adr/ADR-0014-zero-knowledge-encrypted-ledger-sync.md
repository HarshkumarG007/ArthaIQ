# ADR-0014: Zero-Knowledge Client-Side Encrypted Career Ledger Sync Architecture

| Field | Value |
|---|---|
| Status | **Accepted** |
| Decided at | T27.01 (2026-11-01) |
| Relates to | `rules.md` R-CR-09, R-CR-12, R-CR-14, R-SC-01, R-SC-05; ADR-0008, ADR-0012; India DPDP Act 2023 Section 6 & 12 |

---

## Context

Under `ADR-0012` and Rule `R-CR-12`, ArthaIQ established a radical local-first privacy architecture: user career profiles, evidence ledgers, and practice attempts reside strictly in on-device IndexedDB storage. While this eliminates central database breach risks and ensures instant offline performance, users navigating career journeys across multiple devices (e.g., developer workstation, laptop, mobile browser) require a mechanism to synchronize progress without compromising local-first privacy or violating the India DPDP Act 2023.

Storing plaintext career profiles or credentials on an application server would violate Rule `R-CR-12` and create an unnecessary compliance honey pot.

---

## Decisions

### 1. Zero-Knowledge Client-Side Encryption via WebCrypto

**Accepted:** When opt-in cross-device synchronization is enabled, all serialization and encryption occur client-side in the browser before any network transmission:
- **Algorithm:** Authenticated AES-GCM with a 256-bit key (`AES-GCM-256`).
- **Key Derivation:** Keys are derived client-side from a user passphrase or WebAuthn/Passkey using PBKDF2 (SHA-256, minimum 100,000 iterations) and a cryptographically random 16-byte salt (`crypto.getRandomValues`).
- **Zero Server Knowledge:** The decryption key and plaintext passphrase are never transmitted to, logged by, or stored on the backend serving stack. The server receives only opaque ciphertext blobs.

### 2. Standardized Ciphertext Sync Envelope

**Accepted:** Encrypted sync payloads conform to a strict schema envelope:
```json
{
  "sync_version": "1.0",
  "sync_id": "usr_sync_<uuid>",
  "algorithm": "AES-256-GCM",
  "kdf": "PBKDF2-SHA256",
  "iterations": 100000,
  "salt_b64": "<base64-salt-16-bytes>",
  "iv_b64": "<base64-iv-12-bytes>",
  "ciphertext_b64": "<base64-ciphertext-with-tag>",
  "updated_at_utc": "2026-11-01T08:00:00Z",
  "schema_version": 2
}
```

### 3. Monotonic State Conflict Resolution (State Beats Score)

**Accepted:** In accordance with Rule `R-CR-03` (*State beats score*), concurrent updates across devices are resolved deterministically using a monotonic state lattice:
- $\text{Unproven} \prec \text{Self-reported} \prec \text{Demonstrated}$
- The `Demonstrated` state is an **absorbing element**: once a competency has been proven via passing a deterministic practice scenario, no offline device update can demote it back to `Self-reported` or `Unproven`.
- For identical states, the record with the most recent `verified_at` timestamp takes precedence.

### 4. DPDP Act 2023 Section 12 Hard Wipe Compliance

**Accepted:** In adherence to the right to erasure:
- A user can issue a single-click purge request from the client UI.
- The server permanently deletes the ciphertext envelope and all associated sync tombstones within $< 50\text{ ms}$, returning a cryptographic zero-byte confirmation.

---

## Consequences

- **Positive:** Enables multi-device ledger continuity without violating Rule `R-CR-12` or storing plaintext career data; backend breach yields only unreadable ciphertext; preserves 100% offline functionality.
- **Negative:** If a user loses both their device data and their encryption passphrase, the encrypted backup cannot be recovered by ArthaIQ administrators (by design). Clear UI warnings must accompany sync setup.
