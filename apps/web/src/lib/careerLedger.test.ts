import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  closeLedgerDB,
  getLedgerRecord,
  getAllLedgerRecords,
  saveLedgerRecord,
  batchUpdateRecords,
  deleteLedgerRecord,
  getCareerProfile,
  saveCareerProfile,
  saveScenarioAttempt,
  getScenarioAttempts,
  exportLedgerBackup,
  importLedgerBackup,
  purgeAllUserData,
  estimateStorageQuota,
  type ClientEvidenceRecord,
  type ClientScenarioAttemptRecord,
} from "./careerLedger";

describe("CareerLedger (Local-First IndexedDB Store)", () => {
  beforeEach(async () => {
    await purgeAllUserData();
  });

  afterEach(async () => {
    closeLedgerDB();
    await purgeAllUserData();
  });

  describe("Evidence Records CRUD", () => {
    it("saves and retrieves a single evidence record", async () => {
      const record: ClientEvidenceRecord = {
        competency_id: "sql_core",
        verification_state: "self_reported",
        evidence_type: "self_attestation",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metadata: { notes: "3 years writing production queries" },
      };

      await saveLedgerRecord(record);
      const retrieved = await getLedgerRecord("sql_core");

      expect(retrieved).not.toBeNull();
      expect(retrieved?.competency_id).toBe("sql_core");
      expect(retrieved?.verification_state).toBe("self_reported");
      expect(retrieved?.evidence_type).toBe("self_attestation");
      expect(retrieved?.metadata?.notes).toBe("3 years writing production queries");
    });

    it("returns null when competency is not found", async () => {
      const nonExistent = await getLedgerRecord("non_existent_comp");
      expect(nonExistent).toBeNull();
    });

    it("batch updates multiple evidence records atomically", async () => {
      const records: ClientEvidenceRecord[] = [
        {
          competency_id: "comp_a",
          verification_state: "unproven",
          evidence_type: "self_attestation",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          competency_id: "comp_b",
          verification_state: "demonstrated",
          evidence_type: "portfolio",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ];

      await batchUpdateRecords(records);
      const all = await getAllLedgerRecords();

      expect(all).toHaveLength(2);
      expect(all.map((r) => r.competency_id).sort()).toEqual(["comp_a", "comp_b"]);
    });

    it("deletes an evidence record by competency ID", async () => {
      const record: ClientEvidenceRecord = {
        competency_id: "to_delete",
        verification_state: "unproven",
        evidence_type: "self_attestation",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      await saveLedgerRecord(record);
      expect(await getLedgerRecord("to_delete")).not.toBeNull();

      await deleteLedgerRecord("to_delete");
      expect(await getLedgerRecord("to_delete")).toBeNull();
    });
  });

  describe("Career Profile Singleton", () => {
    it("returns null when no profile has been saved yet", async () => {
      const profile = await getCareerProfile();
      expect(profile).toBeNull();
    });

    it("persists and updates primary career profile", async () => {
      await saveCareerProfile({
        target_role: "Data Analyst",
        target_level: "L3_mid",
        target_family: "DATA",
        available_hours_per_week: 10,
        updated_at: new Date().toISOString(),
      });

      const profile = await getCareerProfile();
      expect(profile).not.toBeNull();
      expect(profile?.id).toBe("primary");
      expect(profile?.target_role).toBe("Data Analyst");
      expect(profile?.target_level).toBe("L3_mid");
      expect(profile?.target_family).toBe("DATA");
      expect(profile?.available_hours_per_week).toBe(10);

      // Update profile
      await saveCareerProfile({
        target_role: "Senior Data Analyst",
        target_level: "L4_senior",
        target_family: "DATA",
        available_hours_per_week: 15,
        updated_at: new Date().toISOString(),
      });

      const updated = await getCareerProfile();
      expect(updated?.target_role).toBe("Senior Data Analyst");
      expect(updated?.target_level).toBe("L4_senior");
      expect(updated?.available_hours_per_week).toBe(15);
    });
  });

  describe("Scenario Attempts Tracking & Evidence Unlocking (R-CR-08, ADR-0011)", () => {
    it("persists scenario attempts and allows filtering by scenario_id", async () => {
      const attempt1: ClientScenarioAttemptRecord = {
        attempt_id: "att_01",
        scenario_id: "scen_data_01_sql",
        score: 30,
        max_possible_score: 30,
        passed: true,
        completed_at: new Date().toISOString(),
        demonstrated_competencies: ["sql_null_semantics", "sql_window_functions"],
      };

      const attempt2: ClientScenarioAttemptRecord = {
        attempt_id: "att_02",
        scenario_id: "scen_data_02_eda",
        score: 15,
        max_possible_score: 30,
        passed: false,
        completed_at: new Date().toISOString(),
        demonstrated_competencies: [],
      };

      await saveScenarioAttempt(attempt1);
      await saveScenarioAttempt(attempt2);

      const allAttempts = await getScenarioAttempts();
      expect(allAttempts).toHaveLength(2);

      const sqlAttempts = await getScenarioAttempts("scen_data_01_sql");
      expect(sqlAttempts).toHaveLength(1);
      expect(sqlAttempts[0]?.attempt_id).toBe("att_01");

      const edaAttempts = await getScenarioAttempts("scen_data_02_eda");
      expect(edaAttempts).toHaveLength(1);
      expect(edaAttempts[0]?.attempt_id).toBe("att_02");
    });

    it("automatically unlocks demonstrated competencies in ledger on passed attempt", async () => {
      const attempt: ClientScenarioAttemptRecord = {
        attempt_id: "att_pass",
        scenario_id: "scen_data_01_sql",
        score: 25,
        max_possible_score: 30,
        passed: true,
        completed_at: new Date().toISOString(),
        demonstrated_competencies: ["sql_null_semantics", "sql_aggregations"],
      };

      await saveScenarioAttempt(attempt, true);

      const comp1 = await getLedgerRecord("sql_null_semantics");
      expect(comp1).not.toBeNull();
      expect(comp1?.verification_state).toBe("demonstrated");
      expect(comp1?.evidence_type).toBe("scenario_attempt");
      expect(comp1?.metadata?.scenario_id).toBe("scen_data_01_sql");

      const comp2 = await getLedgerRecord("sql_aggregations");
      expect(comp2).not.toBeNull();
      expect(comp2?.verification_state).toBe("demonstrated");
    });

    it("does not unlock competencies when attempt is not passed", async () => {
      const attempt: ClientScenarioAttemptRecord = {
        attempt_id: "att_fail",
        scenario_id: "scen_data_01_sql",
        score: 10,
        max_possible_score: 30,
        passed: false,
        completed_at: new Date().toISOString(),
        demonstrated_competencies: ["sql_null_semantics"],
      };

      await saveScenarioAttempt(attempt, true);

      const comp = await getLedgerRecord("sql_null_semantics");
      expect(comp).toBeNull();
    });
  });

  describe("India DPDP Act 2023: Backup Export & Import", () => {
    it("exports and imports complete ledger backup round-trip", async () => {
      // Setup profile
      await saveCareerProfile({
        target_role: "Data Analyst",
        target_level: "L3_mid",
        target_family: "DATA",
        available_hours_per_week: 12,
        updated_at: new Date().toISOString(),
      });

      // Setup records
      await saveLedgerRecord({
        competency_id: "comp_1",
        verification_state: "self_reported",
        evidence_type: "portfolio",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      // Setup attempt
      await saveScenarioAttempt({
        attempt_id: "att_test",
        scenario_id: "scen_data_01_sql",
        score: 28,
        max_possible_score: 30,
        passed: true,
        completed_at: new Date().toISOString(),
        demonstrated_competencies: ["comp_demonstrated"],
      });

      // Export backup
      const backup = await exportLedgerBackup();
      expect(backup.version).toBe(1);
      expect(backup.profile?.target_role).toBe("Data Analyst");
      expect(backup.records.length).toBeGreaterThanOrEqual(2); // comp_1 and comp_demonstrated
      expect(backup.attempts).toHaveLength(1);

      // Wipe everything
      await purgeAllUserData();
      expect(await getCareerProfile()).toBeNull();
      expect(await getAllLedgerRecords()).toHaveLength(0);
      expect(await getScenarioAttempts()).toHaveLength(0);

      // Restore from backup
      await importLedgerBackup(backup);

      const restoredProfile = await getCareerProfile();
      expect(restoredProfile?.target_role).toBe("Data Analyst");

      const restoredRecords = await getAllLedgerRecords();
      expect(restoredRecords).toHaveLength(backup.records.length);

      const restoredAttempts = await getScenarioAttempts();
      expect(restoredAttempts).toHaveLength(1);
      expect(restoredAttempts[0]?.attempt_id).toBe("att_test");
    });

    it("rejects invalid backup payloads", async () => {
      // @ts-expect-error Testing runtime payload validation
      await expect(importLedgerBackup({ version: 2 })).rejects.toThrow(
        "Invalid ledger backup payload"
      );
      // @ts-expect-error Testing null payload
      await expect(importLedgerBackup(null)).rejects.toThrow(
        "Invalid ledger backup payload"
      );
    });
  });

  describe("India DPDP Act 2023: Hard Erasure (purgeAllUserData)", () => {
    it("completely wipes all stores and resets database footprint", async () => {
      await saveCareerProfile({
        target_role: "ML Engineer",
        target_level: "L3_mid",
        target_family: "DATA",
        available_hours_per_week: 8,
        updated_at: new Date().toISOString(),
      });

      await saveLedgerRecord({
        competency_id: "ml_feature_store",
        verification_state: "demonstrated",
        evidence_type: "portfolio",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      await saveScenarioAttempt({
        attempt_id: "attempt_purge",
        scenario_id: "scen_data_03_exp",
        score: 30,
        max_possible_score: 30,
        passed: true,
        completed_at: new Date().toISOString(),
        demonstrated_competencies: [],
      });

      // Execute single-click purge
      await purgeAllUserData();

      // Database should reopen fresh and empty
      const profile = await getCareerProfile();
      expect(profile).toBeNull();

      const records = await getAllLedgerRecords();
      expect(records).toHaveLength(0);

      const attempts = await getScenarioAttempts();
      expect(attempts).toHaveLength(0);
    });
  });

  describe("Storage Quota Estimation", () => {
    it("returns storage estimate when navigator.storage is available", async () => {
      const originalStorage = navigator.storage;
      // Mock navigator.storage.estimate
      Object.defineProperty(navigator, "storage", {
        value: {
          estimate: vi.fn().mockResolvedValue({
            usage: 2048,
            quota: 1048576,
          }),
        },
        configurable: true,
      });

      const estimate = await estimateStorageQuota();
      expect(estimate.usedBytes).toBe(2048);
      expect(estimate.quotaBytes).toBe(1048576);
      expect(estimate.percentage).toBeCloseTo((2048 / 1048576) * 100);

      // Restore
      Object.defineProperty(navigator, "storage", {
        value: originalStorage,
        configurable: true,
      });
    });

    it("gracefully falls back when navigator.storage is undefined or throws", async () => {
      const originalStorage = navigator.storage;
      Object.defineProperty(navigator, "storage", {
        value: {
          estimate: vi.fn().mockRejectedValue(new Error("Permission denied")),
        },
        configurable: true,
      });

      const estimate = await estimateStorageQuota();
      expect(estimate.usedBytes).toBe(0);
      expect(estimate.quotaBytes).toBe(0);
      expect(estimate.percentage).toBe(0);

      Object.defineProperty(navigator, "storage", {
        value: originalStorage,
        configurable: true,
      });
    });
  });
});
