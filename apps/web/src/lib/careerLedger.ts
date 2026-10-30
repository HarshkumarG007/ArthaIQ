/**
 * ArthaIQ Local-First Career Evidence Ledger (IndexedDB)
 *
 * Implements client-side local-first privacy architecture:
 * - ADR-0011: Competency Graph & Evidence Ledger Schema
 * - ADR-0012 & Rule R-CR-12: Zero server-side user career profile storage in MVP.
 * - Rule R-CR-03: State beats score (discrete verification states).
 * - Rule R-CR-14: Independent offline utility.
 * - India DPDP Act 2023: Single-click hard erasure and portable JSON export.
 */

export const DB_NAME = "arthaiq_career_ledger";
export const DB_VERSION = 1;

export const STORE_EVIDENCE = "evidence_records";
export const STORE_PROFILE = "career_profile";
export const STORE_ATTEMPTS = "scenario_attempts";

export type VerificationState = "unproven" | "self_reported" | "demonstrated";

export type EvidenceType =
  | "portfolio"
  | "code_review"
  | "scenario_attempt"
  | "work_artifact"
  | "self_attestation";

export type TargetLevel = "L2_junior" | "L3_mid" | "L4_senior";

export interface ClientEvidenceRecord {
  competency_id: string;
  verification_state: VerificationState;
  evidence_type: EvidenceType;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
  recheck_suggested?: boolean;
}

export interface ClientCareerProfile {
  id: "primary";
  target_role: string;
  target_level: TargetLevel;
  target_family: string;
  available_hours_per_week: number;
  updated_at: string;
}

export interface ClientScenarioAttemptRecord {
  attempt_id: string;
  scenario_id: string;
  score: number;
  max_possible_score: number;
  passed: boolean;
  completed_at: string;
  demonstrated_competencies: string[];
}

export interface ClientLedgerBackupPayload {
  version: 1;
  exported_at: string;
  profile: ClientCareerProfile | null;
  records: ClientEvidenceRecord[];
  attempts: ClientScenarioAttemptRecord[];
}

export interface StorageQuotaEstimate {
  usedBytes: number;
  quotaBytes: number;
  percentage: number;
}

let cachedDb: IDBDatabase | null = null;

/**
 * Open or upgrade connection to the IndexedDB career ledger.
 */
export function openLedgerDB(): Promise<IDBDatabase> {
  if (cachedDb) {
    return Promise.resolve(cachedDb);
  }

  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB is not supported in this environment"));
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;

      if (!db.objectStoreNames.contains(STORE_EVIDENCE)) {
        db.createObjectStore(STORE_EVIDENCE, { keyPath: "competency_id" });
      }

      if (!db.objectStoreNames.contains(STORE_PROFILE)) {
        db.createObjectStore(STORE_PROFILE, { keyPath: "id" });
      }

      if (!db.objectStoreNames.contains(STORE_ATTEMPTS)) {
        const attemptStore = db.createObjectStore(STORE_ATTEMPTS, {
          keyPath: "attempt_id",
        });
        attemptStore.createIndex("by_scenario", "scenario_id", { unique: false });
      }
    };

    request.onsuccess = () => {
      cachedDb = request.result;
      cachedDb.onclose = () => {
        cachedDb = null;
      };
      cachedDb.onerror = () => {
        // If database error occurs, clear cached reference
        cachedDb = null;
      };
      resolve(cachedDb);
    };

    request.onerror = () => {
      reject(request.error || new Error("Failed to open IndexedDB"));
    };
  });
}

/**
 * Close cached database instance if open.
 */
export function closeLedgerDB(): void {
  if (cachedDb) {
    try {
      cachedDb.close();
    } catch {
      // Ignore close errors
    }
    cachedDb = null;
  }
}

/**
 * Retrieve single evidence record by competency ID.
 */
export async function getLedgerRecord(
  competencyId: string
): Promise<ClientEvidenceRecord | null> {
  const db = await openLedgerDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_EVIDENCE, "readonly");
    const store = tx.objectStore(STORE_EVIDENCE);
    const request = store.get(competencyId);

    request.onsuccess = () => {
      resolve(request.result || null);
    };
    request.onerror = () => {
      reject(request.error || new Error(`Failed to get record: ${competencyId}`));
    };
  });
}

/**
 * Retrieve all evidence records in ledger.
 */
export async function getAllLedgerRecords(): Promise<ClientEvidenceRecord[]> {
  const db = await openLedgerDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_EVIDENCE, "readonly");
    const store = tx.objectStore(STORE_EVIDENCE);
    const request = store.getAll();

    request.onsuccess = () => {
      resolve(request.result || []);
    };
    request.onerror = () => {
      reject(request.error || new Error("Failed to retrieve all evidence records"));
    };
  });
}

/**
 * Upsert a single evidence record.
 */
export async function saveLedgerRecord(
  record: ClientEvidenceRecord
): Promise<void> {
  const db = await openLedgerDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_EVIDENCE, "readwrite");
    const store = tx.objectStore(STORE_EVIDENCE);
    const request = store.put(record);

    request.onsuccess = () => resolve();
    request.onerror = () => {
      reject(request.error || new Error(`Failed to save record: ${record.competency_id}`));
    };
  });
}

/**
 * Batch upsert multiple evidence records atomically.
 */
export async function batchUpdateRecords(
  records: ClientEvidenceRecord[]
): Promise<void> {
  if (records.length === 0) return;
  const db = await openLedgerDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_EVIDENCE, "readwrite");
    const store = tx.objectStore(STORE_EVIDENCE);

    for (const record of records) {
      store.put(record);
    }

    tx.oncomplete = () => resolve();
    tx.onerror = () => {
      reject(tx.error || new Error("Failed to batch update evidence records"));
    };
  });
}

/**
 * Delete a single evidence record by competency ID.
 */
export async function deleteLedgerRecord(competencyId: string): Promise<void> {
  const db = await openLedgerDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_EVIDENCE, "readwrite");
    const store = tx.objectStore(STORE_EVIDENCE);
    const request = store.delete(competencyId);

    request.onsuccess = () => resolve();
    request.onerror = () => {
      reject(request.error || new Error(`Failed to delete record: ${competencyId}`));
    };
  });
}

/**
 * Retrieve primary career profile (singleton).
 */
export async function getCareerProfile(): Promise<ClientCareerProfile | null> {
  const db = await openLedgerDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_PROFILE, "readonly");
    const store = tx.objectStore(STORE_PROFILE);
    const request = store.get("primary");

    request.onsuccess = () => {
      resolve(request.result || null);
    };
    request.onerror = () => {
      reject(request.error || new Error("Failed to get career profile"));
    };
  });
}

/**
 * Upsert primary career profile.
 */
export async function saveCareerProfile(
  profile: Omit<ClientCareerProfile, "id"> | ClientCareerProfile
): Promise<void> {
  const db = await openLedgerDB();
  const completeProfile: ClientCareerProfile = {
    ...profile,
    id: "primary",
    updated_at: profile.updated_at || new Date().toISOString(),
  };

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_PROFILE, "readwrite");
    const store = tx.objectStore(STORE_PROFILE);
    const request = store.put(completeProfile);

    request.onsuccess = () => resolve();
    request.onerror = () => {
      reject(request.error || new Error("Failed to save career profile"));
    };
  });
}

/**
 * Save practice scenario attempt.
 * When syncDemonstratedToLedger is true and attempt passed, unlocks demonstrated competencies in evidence ledger.
 */
export async function saveScenarioAttempt(
  attempt: ClientScenarioAttemptRecord,
  syncDemonstratedToLedger = true
): Promise<void> {
  const db = await openLedgerDB();

  // If syncing demonstrated competencies, use a multi-store transaction
  if (
    syncDemonstratedToLedger &&
    attempt.passed &&
    attempt.demonstrated_competencies.length > 0
  ) {
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_ATTEMPTS, STORE_EVIDENCE], "readwrite");
      const attemptStore = tx.objectStore(STORE_ATTEMPTS);
      const evidenceStore = tx.objectStore(STORE_EVIDENCE);

      attemptStore.put(attempt);

      const now = new Date().toISOString();
      for (const compId of attempt.demonstrated_competencies) {
        const record: ClientEvidenceRecord = {
          competency_id: compId,
          verification_state: "demonstrated",
          evidence_type: "scenario_attempt",
          created_at: now,
          updated_at: now,
          metadata: {
            scenario_id: attempt.scenario_id,
            attempt_id: attempt.attempt_id,
            score: attempt.score,
          },
          recheck_suggested: false,
        };
        evidenceStore.put(record);
      }

      tx.oncomplete = () => resolve();
      tx.onerror = () => {
        reject(tx.error || new Error("Failed to save scenario attempt and sync ledger"));
      };
    });
  }

  // Otherwise single-store transaction
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_ATTEMPTS, "readwrite");
    const store = tx.objectStore(STORE_ATTEMPTS);
    const request = store.put(attempt);

    request.onsuccess = () => resolve();
    request.onerror = () => {
      reject(request.error || new Error("Failed to save scenario attempt"));
    };
  });
}

/**
 * Retrieve scenario attempts, optionally filtered by scenario_id.
 */
export async function getScenarioAttempts(
  scenarioId?: string
): Promise<ClientScenarioAttemptRecord[]> {
  const db = await openLedgerDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_ATTEMPTS, "readonly");
    const store = tx.objectStore(STORE_ATTEMPTS);

    let request: IDBRequest<ClientScenarioAttemptRecord[]>;
    if (scenarioId) {
      const index = store.index("by_scenario");
      request = index.getAll(scenarioId);
    } else {
      request = store.getAll();
    }

    request.onsuccess = () => {
      resolve(request.result || []);
    };
    request.onerror = () => {
      reject(request.error || new Error("Failed to retrieve scenario attempts"));
    };
  });
}

/**
 * Export full career profile and evidence ledger as portable JSON (India DPDP Act 2023).
 */
export async function exportLedgerBackup(): Promise<ClientLedgerBackupPayload> {
  const [profile, records, attempts] = await Promise.all([
    getCareerProfile(),
    getAllLedgerRecords(),
    getScenarioAttempts(),
  ]);

  return {
    version: 1,
    exported_at: new Date().toISOString(),
    profile,
    records,
    attempts,
  };
}

/**
 * Restore career ledger from portable JSON backup payload.
 */
export async function importLedgerBackup(
  payload: ClientLedgerBackupPayload,
  clearExisting = true
): Promise<void> {
  if (
    !payload ||
    payload.version !== 1 ||
    !Array.isArray(payload.records) ||
    !Array.isArray(payload.attempts)
  ) {
    throw new Error("Invalid ledger backup payload: expected version 1 schema");
  }

  const db = await openLedgerDB();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(
      [STORE_EVIDENCE, STORE_PROFILE, STORE_ATTEMPTS],
      "readwrite"
    );
    const evidenceStore = tx.objectStore(STORE_EVIDENCE);
    const profileStore = tx.objectStore(STORE_PROFILE);
    const attemptStore = tx.objectStore(STORE_ATTEMPTS);

    if (clearExisting) {
      evidenceStore.clear();
      profileStore.clear();
      attemptStore.clear();
    }

    if (payload.profile) {
      profileStore.put(payload.profile);
    }

    for (const record of payload.records) {
      evidenceStore.put(record);
    }

    for (const attempt of payload.attempts) {
      attemptStore.put(attempt);
    }

    tx.oncomplete = () => resolve();
    tx.onerror = () => {
      reject(tx.error || new Error("Failed to import ledger backup"));
    };
  });
}

/**
 * Single-click hard erasure of all career ledger data (India DPDP Act 2023).
 * Closes connections and deletes the IndexedDB database.
 */
export async function purgeAllUserData(): Promise<void> {
  closeLedgerDB();

  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      resolve();
      return;
    }

    const request = indexedDB.deleteDatabase(DB_NAME);

    request.onsuccess = () => {
      resolve();
    };
    request.onerror = () => {
      reject(request.error || new Error("Failed to purge career ledger database"));
    };
    request.onblocked = () => {
      // In case another tab held connection, resolve once unblocked
      resolve();
    };
  });
}

/**
 * Report storage quota and consumption for local device.
 */
export async function estimateStorageQuota(): Promise<StorageQuotaEstimate> {
  if (
    typeof navigator !== "undefined" &&
    navigator.storage &&
    typeof navigator.storage.estimate === "function"
  ) {
    try {
      const estimate = await navigator.storage.estimate();
      const usedBytes = estimate.usage ?? 0;
      const quotaBytes = estimate.quota ?? 0;
      const percentage = quotaBytes > 0 ? (usedBytes / quotaBytes) * 100 : 0;
      return { usedBytes, quotaBytes, percentage };
    } catch {
      // Fallback on estimate error
    }
  }

  return { usedBytes: 0, quotaBytes: 0, percentage: 0 };
}
