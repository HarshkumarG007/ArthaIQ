import { describe, it, expect, beforeEach } from "vitest";
import {
  recordPilotTelemetryEvent,
  getPilotTelemetryEvents,
  clearPilotTelemetryEvents,
  applyKAnonymityToCounts,
  computeClientPilotScorecard,
  generateClientCohortReport,
  PILOT_TELEMETRY_STORAGE_KEY,
} from "./pilotTelemetry";

describe("PilotTelemetry Engine (T20.02)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("records and retrieves telemetry events with automatic timestamping", () => {
    expect(getPilotTelemetryEvents()).toEqual([]);

    recordPilotTelemetryEvent({
      eventType: "scenario_started",
      scenarioId: "SCEN-SWE-01-AUTH",
      roleFamily: "SWE",
    });

    const events = getPilotTelemetryEvents();
    expect(events).toHaveLength(1);
    expect(events[0]!.eventType).toBe("scenario_started");
    expect(events[0]!.scenarioId).toBe("SCEN-SWE-01-AUTH");
    expect(events[0]!.roleFamily).toBe("SWE");
    expect(typeof events[0]!.timestampMs).toBe("number");
  });

  it("caps event log history at 500 items to protect client storage", () => {
    for (let i = 0; i < 520; i++) {
      recordPilotTelemetryEvent({
        eventType: "navigation",
        metadata: { index: i },
      });
    }

    const events = getPilotTelemetryEvents();
    expect(events).toHaveLength(500);
    expect(events[499]!.metadata?.index).toBe(519);
  });

  it("clears telemetry events completely on hard purge (DPDP Act Sec 12)", () => {
    recordPilotTelemetryEvent({ eventType: "scenario_started" });
    expect(getPilotTelemetryEvents()).toHaveLength(1);

    clearPilotTelemetryEvents();
    expect(getPilotTelemetryEvents()).toEqual([]);
    expect(localStorage.getItem(PILOT_TELEMETRY_STORAGE_KEY)).toBeNull();
  });

  it("enforces k-anonymity (k >= 5) cell suppression", () => {
    const rawCounts: Record<string, number> = {
      DATA_mid_BLR: 12,
      SWE_junior_DEL_NCR: 4, // Below k=5 -> suppress
      MLAI_senior_HYD: 7,
      DATA_senior_OTHER: 2, // Below k=5 -> suppress
    };

    const cells = applyKAnonymityToCounts(rawCounts, 5);

    expect(cells).toHaveLength(4);

    const dataMidBlr = cells.find((c) => c.cellKey === "DATA_mid_BLR");
    expect(dataMidBlr?.rawCount).toBe(12);
    expect(dataMidBlr?.reportedCount).toBe(12);
    expect(dataMidBlr?.isSuppressed).toBe(false);

    const sweJuniorDel = cells.find((c) => c.cellKey === "SWE_junior_DEL_NCR");
    expect(sweJuniorDel?.rawCount).toBe(4);
    expect(sweJuniorDel?.reportedCount).toBeNull();
    expect(sweJuniorDel?.isSuppressed).toBe(true);

    const dataSeniorOther = cells.find((c) => c.cellKey === "DATA_senior_OTHER");
    expect(dataSeniorOther?.rawCount).toBe(2);
    expect(dataSeniorOther?.reportedCount).toBeNull();
    expect(dataSeniorOther?.isSuppressed).toBe(true);
  });

  it("computes scorecard metrics accurately from telemetry event stream", () => {
    const events = [
      { eventType: "calibration_comprehended" as const, timestampMs: 1 },
      { eventType: "calibration_comprehended" as const, timestampMs: 2 },
      { eventType: "calibration_misunderstood" as const, timestampMs: 3 }, // 2/3 = 66.7% -> FAIL (< 90%)
      { eventType: "scenario_started" as const, timestampMs: 4 },
      { eventType: "scenario_started" as const, timestampMs: 5 },
      { eventType: "scenario_completed" as const, timestampMs: 6 }, // 1/2 = 50.0% -> FAIL (< 95%)
      { eventType: "rubric_evaluated" as const, timestampMs: 7, durationMs: 0.045 },
      { eventType: "storage_measured" as const, timestampMs: 8, bytesUsed: 12288 }, // 12 KB
    ];

    const scorecard = computeClientPilotScorecard(events);

    expect(scorecard.m_stg_01_calibration_comprehension.observed).toBe("66.7%");
    expect(scorecard.m_stg_01_calibration_comprehension.status).toBe("FAIL");

    expect(scorecard.m_stg_02_task_completion_rate.observed).toBe("50.0%");
    expect(scorecard.m_stg_02_task_completion_rate.status).toBe("FAIL");

    expect(scorecard.m_stg_04_scoring_latency_p95_ms.observed).toBe("0.045 ms");
    expect(scorecard.m_stg_04_scoring_latency_p95_ms.status).toBe("PASS");

    expect(scorecard.m_stg_05_local_storage_footprint_kb.observed).toBe("12.00 KB");
    expect(scorecard.m_stg_05_local_storage_footprint_kb.status).toBe("PASS");
  });

  it("generates full cohort report with stratification breakdown", () => {
    const strata = [
      { role_family: "DATA" as const, seniority_band: "mid", geographic_cluster: "BLR" },
      { role_family: "DATA" as const, seniority_band: "mid", geographic_cluster: "BLR" },
      { role_family: "SWE" as const, seniority_band: "senior", geographic_cluster: "HYD" },
      { role_family: "MLAI" as const, seniority_band: "junior", geographic_cluster: "DEL_NCR" },
    ];

    const report = generateClientCohortReport([], strata);

    expect(report.totalParticipants).toBe(4);
    expect(report.dataParticipants).toBe(2);
    expect(report.sweParticipants).toBe(1);
    expect(report.mlaiParticipants).toBe(1);
    expect(report.kThreshold).toBe(5);

    // All cells < 5, so all are suppressed in reported counts
    expect(report.cells.every((c) => c.isSuppressed && c.reportedCount === null)).toBe(true);
    expect(report.scorecard.m_stg_01_calibration_comprehension.status).toBe("PASS");
  });
});
