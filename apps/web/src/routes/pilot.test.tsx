import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { PilotRoute } from "./pilot";
import { savePilotConsent, type PilotConsentRecord } from "../lib/pilotConsent";
import { recordPilotTelemetryEvent } from "../lib/pilotTelemetry";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Mathematical verification in scripts/check_contrast.py
  },
};

const mockConsent: PilotConsentRecord = {
  consent_id: "test-consent-uuid",
  consent_version: "2026.1",
  consented_at: "2026-10-31T10:00:00Z",
  age_confirmed_18_plus: true,
  voluntary_research_acknowledged: true,
  non_appraisal_acknowledged: true,
  right_to_erasure_acknowledged: true,
  stratification: {
    role_family: "SWE",
    seniority_band: "mid",
    geographic_cluster: "BLR",
  },
};

describe("PilotRoute & PilotDashboard (T20.03)", () => {
  beforeEach(() => {
    localStorage.clear();
    window.location.hash = "#pilot";
  });

  it("renders the pilot cohort header and overview metrics", () => {
    render(<PilotRoute />);

    expect(
      screen.getByRole("heading", { name: /Live Pilot Cohort & Telemetry Dashboard/i, level: 1 })
    ).toBeInTheDocument();
    expect(screen.getByText(/Phase 20 Active/i)).toBeInTheDocument();
    expect(screen.getByText(/Target Allocation/i)).toBeInTheDocument();
    expect(screen.getAllByText(/N=150/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Comprehension Rate/i)).toBeInTheDocument();
    expect(screen.getByText(/Completion Rate/i)).toBeInTheDocument();
    expect(screen.getByText(/Scoring p95 Latency/i)).toBeInTheDocument();
  });

  it("renders the three canonical role family allocations (DATA, SWE, MLAI)", () => {
    render(<PilotRoute />);

    expect(screen.getByText(/Data Science \(DATA\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Software Eng \(SWE\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Machine Learning \(MLAI\)/i)).toBeInTheDocument();
  });

  it("switches to the Pre-Registered Scorecard tab and displays Stream A and Stream B panels", async () => {
    render(<PilotRoute />);

    const scorecardTab = screen.getByRole("tab", {
      name: /Pre-Registered Scorecard \(10 Metrics\)/i,
    });
    fireEvent.click(scorecardTab);

    expect(
      screen.getByRole("heading", {
        name: /Pre-Registered Staging & Pilot Evaluation Metrics/i,
      })
    ).toBeInTheDocument();

    // Stream A Panel
    expect(
      screen.getByRole("heading", { name: /Stream A: Compensation Evidence & Calibration/i })
    ).toBeInTheDocument();
    expect(screen.getAllByText(/M-STG-01/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M-STG-07/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M-STG-09/i).length).toBeGreaterThan(0);

    // Stream B Panel
    expect(
      screen.getByRole("heading", {
        name: /Stream B: Competency Practice & Technical Execution/i,
      })
    ).toBeInTheDocument();
    expect(screen.getAllByText(/M-STG-02/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M-STG-03/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M-STG-04/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M-STG-05/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M-STG-06/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M-STG-08/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M-STG-10/i).length).toBeGreaterThan(0);
  });

  it("switches to Demographic Stratification tab and enforces k-anonymity", () => {
    savePilotConsent(mockConsent);
    render(<PilotRoute />);

    const stratTab = screen.getByRole("tab", {
      name: /Demographic Stratification \(k ≥ 5\)/i,
    });
    fireEvent.click(stratTab);

    expect(
      screen.getByRole("heading", {
        name: /Demographic Stratification \(k-Anonymity k ≥ 5\)/i,
      })
    ).toBeInTheDocument();

    // Cell with 1 participant should be suppressed
    expect(screen.getByText("SWE_mid_BLR")).toBeInTheDocument();
    expect(screen.getByText(/< 5 \(Suppressed\)/i)).toBeInTheDocument();
    expect(screen.getByText(/k < 5 Suppressed/i)).toBeInTheDocument();
  });

  it("executes DPDP Act Sec 12 hard purge when 'Erase All My Data' is clicked", async () => {
    savePilotConsent(mockConsent);
    recordPilotTelemetryEvent({ eventType: "scenario_started" });

    render(<PilotRoute />);

    const purgeBtn = screen.getByRole("button", { name: /Erase All My Data/i });
    fireEvent.click(purgeBtn);

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        /Hard purge completed under DPDP Act 2023 Sec 12/i
      );
    });

    expect(localStorage.length).toBe(0);
  });

  it("allows recording synthetic cohort activity", async () => {
    render(<PilotRoute />);

    const recordBtn = screen.getByRole("button", { name: /Record Activity/i });
    fireEvent.click(recordBtn);

    // Refresh should keep the view reactive
    const refreshBtn = screen.getByRole("button", { name: /Refresh/i });
    fireEvent.click(refreshBtn);

    expect(screen.getByText(/Live Pilot Cohort & Telemetry Dashboard/i)).toBeInTheDocument();
  });

  it("passes axe accessibility tests with 0 violations across all tabs", async () => {
    const { container } = render(<PilotRoute />);

    // Test Overview Tab
    let results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);

    // Test Scorecard Tab
    fireEvent.click(
      screen.getByRole("tab", { name: /Pre-Registered Scorecard \(10 Metrics\)/i })
    );
    results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);

    // Test Stratification Tab
    fireEvent.click(
      screen.getByRole("tab", { name: /Demographic Stratification \(k ≥ 5\)/i })
    );
    results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});
