import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { CareerRoute } from "./career";
import {
  saveCareerProfile,
  saveLedgerRecord,
  saveScenarioAttempt,
  purgeAllUserData,
  getCareerProfile,
} from "../lib/careerLedger";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false },
  },
};

describe("CareerRoute (T15.28 Career Architect View)", () => {
  beforeEach(async () => {
    await purgeAllUserData();
  });

  afterEach(async () => {
    await purgeAllUserData();
  });

  it("renders setup target form when no profile exists, and saves new profile", async () => {
    render(<CareerRoute />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /set your target role/i })).toBeInTheDocument();
    });

    // Fill form and save
    const submitBtn = screen.getByRole("button", { name: /save target profile/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/target specialization/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /change target/i })).toBeInTheDocument();
    });

    const saved = await getCareerProfile();
    expect(saved?.target_role).toBe("Data Analyst");
    expect(saved?.target_level).toBe("L3_mid");
  });

  it("renders existing profile details directly when profile exists", async () => {
    await saveCareerProfile({
      target_role: "Data Scientist",
      target_level: "L4_senior",
      target_family: "DATA",
      available_hours_per_week: 15,
      updated_at: new Date().toISOString(),
    });

    render(<CareerRoute />);

    await waitFor(() => {
      expect(screen.getByText(/data scientist/i)).toBeInTheDocument();
      expect(screen.getByText(/senior l4/i)).toBeInTheDocument();
    });
  });

  it("navigates across sub-views via tabs", async () => {
    render(<CareerRoute initialSubView="skills" />);

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /skills & gap map/i })).toHaveAttribute(
        "aria-selected",
        "true"
      );
    });

    // Switch to Plan
    const planTab = screen.getByRole("tab", { name: /roadmap plan/i });
    fireEvent.click(planTab);

    expect(screen.getByText(/topological roadmap & calibrated effort estimator/i)).toBeInTheDocument();
    expect(planTab).toHaveAttribute("aria-selected", "true");

    // Switch to Practice
    const practiceTab = screen.getByRole("tab", { name: /practice workspace/i });
    fireEvent.click(practiceTab);

    expect(screen.getByText(/technical practice scenarios/i)).toBeInTheDocument();
    expect(screen.getByText(/scen-data-01-sql/i)).toBeInTheDocument();

    // Switch to Ledger
    const ledgerTab = screen.getByRole("tab", { name: /evidence ledger/i });
    fireEvent.click(ledgerTab);

    expect(screen.getByText(/on-device evidence ledger/i)).toBeInTheDocument();
  });

  it("displays completed practice scenario scores and unlocked competencies", async () => {
    await saveScenarioAttempt({
      attempt_id: "att_sql_passed",
      scenario_id: "scen_data_01_sql",
      score: 30,
      max_possible_score: 30,
      passed: true,
      completed_at: new Date().toISOString(),
      demonstrated_competencies: ["sql_window_functions"],
    });

    render(<CareerRoute initialSubView="practice" />);

    await waitFor(() => {
      expect(screen.getByText(/completed \(score: 30\/30\)/i)).toBeInTheDocument();
    });

    // In ledger tab, competency is demonstrated
    const ledgerTab = screen.getByRole("tab", { name: /evidence ledger/i });
    fireEvent.click(ledgerTab);

    await waitFor(() => {
      expect(screen.getByText("sql_window_functions")).toBeInTheDocument();
      expect(screen.getByText("demonstrated")).toBeInTheDocument();
    });
  });

  it("triggers JSON export backup download without crashing", async () => {
    render(<CareerRoute />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /export json/i })).toBeInTheDocument();
    });

    const originalCreate = URL.createObjectURL;
    const originalRevoke = URL.revokeObjectURL;
    const mockCreate = vi.fn().mockReturnValue("blob:test");
    const mockRevoke = vi.fn();
    URL.createObjectURL = mockCreate;
    URL.revokeObjectURL = mockRevoke;

    const exportBtn = screen.getByRole("button", { name: /export json/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled();
      expect(mockRevoke).toHaveBeenCalled();
    });

    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
  });

  it("opens erase data confirmation dialog and purges all local data", async () => {
    await saveLedgerRecord({
      competency_id: "to_purge",
      verification_state: "demonstrated",
      evidence_type: "portfolio",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<CareerRoute initialSubView="ledger" />);

    await waitFor(() => {
      expect(screen.getByText("to_purge")).toBeInTheDocument();
    });

    // Open purge confirmation
    const purgeBtn = screen.getByRole("button", { name: /erase all data/i });
    fireEvent.click(purgeBtn);

    expect(screen.getByRole("dialog", { name: /erase all career data\?/i })).toBeInTheDocument();

    // Confirm purge
    const confirmBtn = screen.getByRole("button", { name: /permanently erase/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.queryByText("to_purge")).not.toBeInTheDocument();
    });
  });

  it("passes axe accessibility tests with 0 violations across sub-views", async () => {
    const { container } = render(<CareerRoute initialSubView="skills" />);

    await waitFor(() => {
      expect(screen.getByTestId("gap-map-view")).toBeInTheDocument();
    });

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});

