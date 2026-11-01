import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  encryptPayload,
  decryptPayload,
  mergeLedgerRecords,
  mergeProfiles,
  exportEncryptedBackup,
  importAndMergeEncryptedBackup,
  executeHardErasure,
  type EncryptedSyncEnvelope,
} from "./cryptoSync";
import {
  saveCareerProfile,
  saveLedgerRecord,
  getAllLedgerRecords,
  getCareerProfile,
  purgeAllUserData,
  type ClientLedgerBackupPayload,
  type ClientEvidenceRecord,
  type ClientCareerProfile,
} from "./careerLedger";

describe("cryptoSync (Phase 31, ADR-0014 WebCrypto & Monotonic Lattice)", () => {
  const samplePayload: ClientLedgerBackupPayload = {
    version: 1,
    exported_at: new Date().toISOString(),
    profile: {
      id: "primary",
      target_role: "Machine Learning Engineer",
      target_level: "L4_senior",
      target_family: "MLAI",
      available_hours_per_week: 15,
      updated_at: "2026-11-01T08:00:00Z",
    },
    records: [
      {
        competency_id: "mlai.core.l2_neural_backprop",
        verification_state: "demonstrated",
        evidence_type: "scenario_attempt",
        created_at: "2026-11-01T08:00:00Z",
        updated_at: "2026-11-01T08:30:00Z",
      },
      {
        competency_id: "swe.core.l2_concurrency",
        verification_state: "self_reported",
        evidence_type: "self_attestation",
        created_at: "2026-11-01T08:00:00Z",
        updated_at: "2026-11-01T08:15:00Z",
      },
    ],
    attempts: [
      {
        attempt_id: "att_001",
        scenario_id: "SCEN-MLAI-01-TENS",
        score: 30,
        max_possible_score: 30,
        passed: true,
        completed_at: "2026-11-01T08:30:00Z",
        demonstrated_competencies: ["mlai.core.l2_neural_backprop"],
      },
    ],
  };

  const testPassphrase = "ArthaIQ#SuperSecret2026!";

  beforeEach(async () => {
    await purgeAllUserData();
  });

  afterEach(async () => {
    await purgeAllUserData();
  });

  it("encrypts and decrypts payload successfully (roundtrip)", async () => {
    const envelope = await encryptPayload(samplePayload, testPassphrase);

    expect(envelope.sync_version).toBe("1.0");
    expect(envelope.algorithm).toBe("AES-256-GCM");
    expect(envelope.kdf).toBe("PBKDF2-SHA256");
    expect(envelope.iterations).toBe(100000);
    expect(envelope.salt_b64).toBeDefined();
    expect(envelope.iv_b64).toBeDefined();
    expect(envelope.ciphertext_b64).toBeDefined();

    const decrypted = await decryptPayload(envelope, testPassphrase);

    expect(decrypted.version).toBe(1);
    expect(decrypted.profile?.target_role).toBe("Machine Learning Engineer");
    expect(decrypted.records.length).toBe(2);
    expect(decrypted.attempts.length).toBe(1);
  });

  it("rejects short passphrases (< 8 characters)", async () => {
    await expect(encryptPayload(samplePayload, "short")).rejects.toThrow(
      "Passphrase must be at least 8 characters long."
    );
  });

  it("fails to decrypt with incorrect passphrase", async () => {
    const envelope = await encryptPayload(samplePayload, testPassphrase);

    await expect(
      decryptPayload(envelope, "WrongPassword123!")
    ).rejects.toThrow(/Decryption failed/i);
  });

  it("detects tampered ciphertext and aborts decryption safely", async () => {
    const envelope = await encryptPayload(samplePayload, testPassphrase);

    // Tamper with ciphertext by flipping last characters
    const tamperedEnvelope: EncryptedSyncEnvelope = {
      ...envelope,
      ciphertext_b64: envelope.ciphertext_b64.slice(0, -4) + "AAAA",
    };

    await expect(
      decryptPayload(tamperedEnvelope, testPassphrase)
    ).rejects.toThrow(/Decryption failed/i);
  });

  it("detects altered IV and fails authentication", async () => {
    const envelope = await encryptPayload(samplePayload, testPassphrase);

    const tamperedEnvelope: EncryptedSyncEnvelope = {
      ...envelope,
      iv_b64: "AAAAAAAAAAAAAAAA", // Zeroed IV
    };

    await expect(
      decryptPayload(tamperedEnvelope, testPassphrase)
    ).rejects.toThrow(/Decryption failed/i);
  });

  it("resolves concurrent evidence records via monotonic state lattice (State Beats Score)", () => {
    const localRecords: ClientEvidenceRecord[] = [
      {
        competency_id: "comp_1",
        verification_state: "self_reported",
        evidence_type: "self_attestation",
        created_at: "2026-11-01T08:00:00Z",
        updated_at: "2026-11-01T08:00:00Z",
      },
      {
        competency_id: "comp_2",
        verification_state: "demonstrated", // Absorbing
        evidence_type: "scenario_attempt",
        created_at: "2026-11-01T08:00:00Z",
        updated_at: "2026-11-01T08:00:00Z",
      },
      {
        competency_id: "comp_3",
        verification_state: "unproven",
        evidence_type: "self_attestation",
        created_at: "2026-11-01T08:00:00Z",
        updated_at: "2026-11-01T08:00:00Z",
      },
    ];

    const remoteRecords: ClientEvidenceRecord[] = [
      {
        competency_id: "comp_1",
        verification_state: "demonstrated", // Should dominate self_reported
        evidence_type: "scenario_attempt",
        created_at: "2026-11-01T09:00:00Z",
        updated_at: "2026-11-01T09:00:00Z",
      },
      {
        competency_id: "comp_2",
        verification_state: "self_reported", // Should NOT demote local demonstrated
        evidence_type: "self_attestation",
        created_at: "2026-11-01T09:30:00Z",
        updated_at: "2026-11-01T09:30:00Z",
      },
      {
        competency_id: "comp_3",
        verification_state: "self_reported", // Should dominate unproven
        evidence_type: "self_attestation",
        created_at: "2026-11-01T09:00:00Z",
        updated_at: "2026-11-01T09:00:00Z",
      },
      {
        competency_id: "comp_4",
        verification_state: "self_reported", // Brand new from remote
        evidence_type: "self_attestation",
        created_at: "2026-11-01T09:00:00Z",
        updated_at: "2026-11-01T09:00:00Z",
      },
    ];

    const merged = mergeLedgerRecords(localRecords, remoteRecords);

    const comp1 = merged.find((r) => r.competency_id === "comp_1");
    expect(comp1?.verification_state).toBe("demonstrated");

    const comp2 = merged.find((r) => r.competency_id === "comp_2");
    expect(comp2?.verification_state).toBe("demonstrated"); // Remained demonstrated!

    const comp3 = merged.find((r) => r.competency_id === "comp_3");
    expect(comp3?.verification_state).toBe("self_reported");

    const comp4 = merged.find((r) => r.competency_id === "comp_4");
    expect(comp4?.verification_state).toBe("self_reported");
  });

  it("breaks ties between identical states using latest updated_at timestamp", () => {
    const localRecords: ClientEvidenceRecord[] = [
      {
        competency_id: "comp_tie",
        verification_state: "self_reported",
        evidence_type: "self_attestation",
        created_at: "2026-11-01T08:00:00Z",
        updated_at: "2026-11-01T08:00:00Z",
        metadata: { version: "v1_older" },
      },
    ];

    const remoteRecords: ClientEvidenceRecord[] = [
      {
        competency_id: "comp_tie",
        verification_state: "self_reported",
        evidence_type: "self_attestation",
        created_at: "2026-11-01T08:00:00Z",
        updated_at: "2026-11-01T09:00:00Z", // Newer
        metadata: { version: "v2_newer" },
      },
    ];

    const merged = mergeLedgerRecords(localRecords, remoteRecords);
    expect(merged[0]?.metadata?.version).toBe("v2_newer");
  });

  it("merges career profiles using latest timestamp", () => {
    const localProfile: ClientCareerProfile = {
      id: "primary",
      target_role: "Data Analyst",
      target_level: "L2_junior",
      target_family: "DATA",
      available_hours_per_week: 10,
      updated_at: "2026-11-01T08:00:00Z",
    };

    const remoteProfile: ClientCareerProfile = {
      id: "primary",
      target_role: "Data Scientist",
      target_level: "L3_mid",
      target_family: "DATA",
      available_hours_per_week: 15,
      updated_at: "2026-11-01T09:00:00Z", // Newer
    };

    const merged = mergeProfiles(localProfile, remoteProfile);
    expect(merged?.target_role).toBe("Data Scientist");
    expect(merged?.target_level).toBe("L3_mid");
  });

  it("executes exportEncryptedBackup and importAndMergeEncryptedBackup into IndexedDB", async () => {
    // Seed local database with initial competency
    await saveCareerProfile({
      target_role: "Software Engineer",
      target_level: "L3_mid",
      target_family: "SWE",
      available_hours_per_week: 10,
      updated_at: "2026-11-01T08:00:00Z",
    });

    await saveLedgerRecord({
      competency_id: "swe.core.l2_concurrency",
      verification_state: "self_reported",
      evidence_type: "self_attestation",
      created_at: "2026-11-01T08:00:00Z",
      updated_at: "2026-11-01T08:00:00Z",
    });

    // Export encrypted backup
    const envelope = await exportEncryptedBackup(testPassphrase);
    expect(envelope.algorithm).toBe("AES-256-GCM");

    // Modify local database to an unproven state
    await saveLedgerRecord({
      competency_id: "swe.core.l2_concurrency",
      verification_state: "unproven",
      evidence_type: "self_attestation",
      created_at: "2026-11-01T08:00:00Z",
      updated_at: "2026-11-01T08:00:00Z",
    });

    // Also add another competency demonstrated in local
    await saveLedgerRecord({
      competency_id: "swe.db.l3_query_perf",
      verification_state: "demonstrated",
      evidence_type: "scenario_attempt",
      created_at: "2026-11-01T08:00:00Z",
      updated_at: "2026-11-01T08:30:00Z",
    });

    // Import and merge the encrypted backup
    const result = await importAndMergeEncryptedBackup(envelope, testPassphrase);
    expect(result.mergedCompetenciesCount).toBe(2);

    // Verify merged state in IndexedDB:
    // swe.core.l2_concurrency was self_reported in backup -> upgraded from unproven
    // swe.db.l3_query_perf remained demonstrated
    const records = await getAllLedgerRecords();
    const conc = records.find((r) => r.competency_id === "swe.core.l2_concurrency");
    expect(conc?.verification_state).toBe("self_reported");

    const dbPerf = records.find((r) => r.competency_id === "swe.db.l3_query_perf");
    expect(dbPerf?.verification_state).toBe("demonstrated");
  });

  it("executes cryptographic hard erasure (DPDP Act 2023 Section 12)", async () => {
    await saveCareerProfile({
      target_role: "Software Engineer",
      target_level: "L3_mid",
      target_family: "SWE",
      available_hours_per_week: 10,
      updated_at: new Date().toISOString(),
    });

    const confirmed = await executeHardErasure();
    expect(confirmed).toBe(true);

    const profile = await getCareerProfile();
    expect(profile).toBeNull();

    const records = await getAllLedgerRecords();
    expect(records.length).toBe(0);
  });
});
