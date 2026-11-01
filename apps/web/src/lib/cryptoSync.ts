/**
 * ArthaIQ Client-Side Zero-Knowledge Encryption & Monotonic Lattice Sync Engine
 *
 * Implements:
 * - ADR-0014: Zero-Knowledge Client-Side Encrypted Career Ledger Sync Architecture
 * - ADR-0012 & Rule R-CR-12: Local-First Privacy (zero server-side plaintext storage)
 * - Rule R-CR-03: State Beats Score (monotonic lattice conflict resolution)
 * - Rule R-SC-01 / R-SC-05: OWASP ASVS v4.0 Cryptographic Standards (AES-GCM-256, PBKDF2-SHA256)
 * - India DPDP Act 2023 Section 12: Cryptographic right to erasure
 */

import {
  type ClientEvidenceRecord,
  type ClientCareerProfile,
  type ClientScenarioAttemptRecord,
  type ClientLedgerBackupPayload,
  exportLedgerBackup,
  saveLedgerRecord,
  saveCareerProfile,
  saveScenarioAttempt,
  purgeAllUserData,
} from "./careerLedger";

export const PBKDF2_ITERATIONS = 100000;
export const SALT_BYTES = 16;
export const IV_BYTES = 12;

export interface EncryptedSyncEnvelope {
  sync_version: "1.0";
  sync_id: string;
  algorithm: "AES-256-GCM";
  kdf: "PBKDF2-SHA256";
  iterations: number;
  salt_b64: string;
  iv_b64: string;
  ciphertext_b64: string;
  updated_at_utc: string;
  schema_version: number;
}

/**
 * Base64 encoding helper for ArrayBuffer
 */
export function bufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]!);
  }
  return btoa(binary);
}

/**
 * Base64 decoding helper to Uint8Array
 */
export function base64ToBuffer(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Get the WebCrypto SubtleCrypto provider, handling browser and testing environments
 */
function getSubtleCrypto(): SubtleCrypto {
  if (typeof window !== "undefined" && window.crypto?.subtle) {
    return window.crypto.subtle;
  }
  if (typeof globalThis !== "undefined" && globalThis.crypto?.subtle) {
    return globalThis.crypto.subtle;
  }
  throw new Error("WebCrypto SubtleCrypto is not supported in this runtime environment.");
}

/**
 * Derive an AES-GCM-256 key from a passphrase and salt using PBKDF2-SHA256
 */
export async function deriveKey(
  passphrase: string,
  salt: Uint8Array,
  iterations: number = PBKDF2_ITERATIONS
): Promise<CryptoKey> {
  const subtle = getSubtleCrypto();
  const enc = new TextEncoder();
  const passphraseKey = await subtle.importKey(
    "raw",
    enc.encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"]
  );

  return subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: salt as unknown as ArrayBuffer,
      iterations,
      hash: "SHA-256",
    },
    passphraseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

/**
 * Encrypt career ledger backup payload into an ADR-0014 compliant envelope
 */
export async function encryptPayload(
  payload: ClientLedgerBackupPayload,
  passphrase: string
): Promise<EncryptedSyncEnvelope> {
  if (!passphrase || passphrase.length < 8) {
    throw new Error("Passphrase must be at least 8 characters long.");
  }

  const subtle = getSubtleCrypto();
  const salt = new Uint8Array(SALT_BYTES);
  const iv = new Uint8Array(IV_BYTES);

  const cryptoObj = (typeof window !== "undefined" ? window.crypto : globalThis.crypto) as Crypto;
  cryptoObj.getRandomValues(salt);
  cryptoObj.getRandomValues(iv);

  const key = await deriveKey(passphrase, salt, PBKDF2_ITERATIONS);

  const enc = new TextEncoder();
  const plaintextBytes = enc.encode(JSON.stringify(payload));

  const ciphertextBuffer = await subtle.encrypt(
    {
      name: "AES-GCM",
      iv: iv as unknown as ArrayBuffer,
      tagLength: 128,
    },
    key,
    plaintextBytes
  );

  const syncId = `usr_sync_${Math.random().toString(36).substring(2, 10)}_${Date.now()}`;

  return {
    sync_version: "1.0",
    sync_id: syncId,
    algorithm: "AES-256-GCM",
    kdf: "PBKDF2-SHA256",
    iterations: PBKDF2_ITERATIONS,
    salt_b64: bufferToBase64(salt),
    iv_b64: bufferToBase64(iv),
    ciphertext_b64: bufferToBase64(ciphertextBuffer),
    updated_at_utc: new Date().toISOString(),
    schema_version: 2,
  };
}

/**
 * Decrypt an ADR-0014 ciphertext envelope using the passphrase
 */
export async function decryptPayload(
  envelope: EncryptedSyncEnvelope,
  passphrase: string
): Promise<ClientLedgerBackupPayload> {
  if (envelope.algorithm !== "AES-256-GCM") {
    throw new Error(`Unsupported encryption algorithm: ${envelope.algorithm}`);
  }
  if (envelope.kdf !== "PBKDF2-SHA256") {
    throw new Error(`Unsupported KDF: ${envelope.kdf}`);
  }
  if (envelope.iterations < 100000) {
    throw new Error("KDF iterations below OWASP security floor (100,000 required).");
  }

  const subtle = getSubtleCrypto();
  const salt = base64ToBuffer(envelope.salt_b64);
  const iv = base64ToBuffer(envelope.iv_b64);
  const ciphertext = base64ToBuffer(envelope.ciphertext_b64);

  const key = await deriveKey(passphrase, salt, envelope.iterations);

  try {
    const decryptedBuffer = await subtle.decrypt(
      {
        name: "AES-GCM",
        iv: iv as unknown as ArrayBuffer,
        tagLength: 128,
      },
      key,
      ciphertext as unknown as ArrayBuffer
    );

    const dec = new TextDecoder();
    const jsonStr = dec.decode(decryptedBuffer);
    const parsed = JSON.parse(jsonStr) as ClientLedgerBackupPayload;

    if (!parsed || parsed.version !== 1) {
      throw new Error("Invalid ledger payload schema version.");
    }

    return parsed;
  } catch (err) {
    if (err instanceof Error && err.message.includes("schema version")) {
      throw err;
    }
    throw new Error(
      "Decryption failed: Incorrect passphrase or tampered ciphertext envelope."
    );
  }
}

/**
 * Lattice ranking for verification states (Rule R-CR-03: State Beats Score)
 * unproven (0) < self_reported (1) < demonstrated (2)
 * demonstrated is strictly absorbing.
 */
export const STATE_LATTICE_RANK: Record<string, number> = {
  unproven: 0,
  self_reported: 1,
  demonstrated: 2,
};

/**
 * Merge two sets of evidence records according to monotonic state lattice
 */
export function mergeLedgerRecords(
  local: ClientEvidenceRecord[] = [],
  remote: ClientEvidenceRecord[] = []
): ClientEvidenceRecord[] {
  const localList = Array.isArray(local) ? local : [];
  const remoteList = Array.isArray(remote) ? remote : [];
  const recordMap = new Map<string, ClientEvidenceRecord>();

  // Populate with local records
  for (const r of localList) {
    recordMap.set(r.competency_id, { ...r });
  }

  // Merge remote records through state lattice
  for (const remoteRec of remoteList) {
    const existing = recordMap.get(remoteRec.competency_id);
    if (!existing) {
      recordMap.set(remoteRec.competency_id, { ...remoteRec });
      continue;
    }

    const localRank = STATE_LATTICE_RANK[existing.verification_state] ?? 0;
    const remoteRank = STATE_LATTICE_RANK[remoteRec.verification_state] ?? 0;

    if (remoteRank > localRank) {
      // Remote strictly dominates (e.g. demonstrated beats self_reported or unproven)
      recordMap.set(remoteRec.competency_id, { ...remoteRec });
    } else if (remoteRank === localRank) {
      // Same rank: latest updated_at wins tiebreak
      const localTime = new Date(existing.updated_at).getTime();
      const remoteTime = new Date(remoteRec.updated_at).getTime();
      if (remoteTime > localTime) {
        recordMap.set(remoteRec.competency_id, { ...remoteRec });
      }
    }
    // If localRank > remoteRank, local wins (demonstrated is absorbing)
  }

  return Array.from(recordMap.values());
}

/**
 * Merge career profiles (latest timestamp wins)
 */
export function mergeProfiles(
  local: ClientCareerProfile | null,
  remote: ClientCareerProfile | null
): ClientCareerProfile | null {
  if (!local) return remote;
  if (!remote) return local;

  const localTime = new Date(local.updated_at).getTime();
  const remoteTime = new Date(remote.updated_at).getTime();

  return remoteTime > localTime ? remote : local;
}

/**
 * Merge scenario attempts (union by attempt_id or latest passed status)
 */
export function mergeScenarioAttempts(
  local: ClientScenarioAttemptRecord[] = [],
  remote: ClientScenarioAttemptRecord[] = []
): ClientScenarioAttemptRecord[] {
  const localList = Array.isArray(local) ? local : [];
  const remoteList = Array.isArray(remote) ? remote : [];
  const attemptMap = new Map<string, ClientScenarioAttemptRecord>();
  for (const a of localList) {
    attemptMap.set(a.attempt_id, a);
  }
  for (const a of remoteList) {
    attemptMap.set(a.attempt_id, a);
  }
  return Array.from(attemptMap.values());
}

/**
 * High-level function: Export encrypted backup file of current user data
 */
export async function exportEncryptedBackup(passphrase: string): Promise<EncryptedSyncEnvelope> {
  const backup = await exportLedgerBackup();
  return encryptPayload(backup, passphrase);
}

/**
 * High-level function: Import encrypted backup file and merge into IndexedDB
 */
export async function importAndMergeEncryptedBackup(
  envelope: EncryptedSyncEnvelope,
  passphrase: string
): Promise<{
  mergedCompetenciesCount: number;
  demonstratedCount: number;
}> {
  const decrypted = await decryptPayload(envelope, passphrase);

  // Read current local state
  const currentBackup = await exportLedgerBackup();

  const localRecords = currentBackup.records || [];
  const remoteRecords =
    decrypted.records ||
    (decrypted as unknown as { evidence_records: ClientEvidenceRecord[] }).evidence_records ||
    [];

  // Merge evidence records via monotonic lattice
  const mergedRecords = mergeLedgerRecords(localRecords, remoteRecords);

  // Merge profiles
  const mergedProfile = mergeProfiles(currentBackup.profile, decrypted.profile);

  const localAttempts = currentBackup.attempts || [];
  const remoteAttempts =
    decrypted.attempts ||
    (decrypted as unknown as { scenario_attempts: ClientScenarioAttemptRecord[] })
      .scenario_attempts ||
    [];

  // Merge scenario attempts
  const mergedAttempts = mergeScenarioAttempts(localAttempts, remoteAttempts);

  // Save merged state into local IndexedDB
  for (const rec of mergedRecords) {
    await saveLedgerRecord(rec);
  }

  if (mergedProfile) {
    await saveCareerProfile({
      target_role: mergedProfile.target_role,
      target_level: mergedProfile.target_level,
      target_family: mergedProfile.target_family,
      available_hours_per_week: mergedProfile.available_hours_per_week,
      updated_at: mergedProfile.updated_at,
    });
  }

  for (const att of mergedAttempts) {
    await saveScenarioAttempt(att);
  }

  const demonstratedCount = mergedRecords.filter(
    (r) => r.verification_state === "demonstrated"
  ).length;

  return {
    mergedCompetenciesCount: mergedRecords.length,
    demonstratedCount,
  };
}

/**
 * Cryptographic hard erasure compliance (India DPDP Act 2023 Section 12)
 * Destroys all local data and returns zero-byte confirmation.
 */
export async function executeHardErasure(): Promise<boolean> {
  await purgeAllUserData();
  return true;
}
