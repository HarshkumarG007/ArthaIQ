import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import axe from "axe-core";
import {
  PracticeWorkspace,
} from "./PracticeWorkspace";
import {
  purgeAllUserData,
  getScenarioAttempts,
  getAllLedgerRecords,
} from "../../lib/careerLedger";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Checked independently via check_contrast.py
  },
};

describe("PracticeWorkspace (T15.30 Practice Workspace & Sandbox)", () => {
  beforeEach(async () => {
    await purgeAllUserData();
  });

  afterEach(async () => {
    await purgeAllUserData();
  });

  it("renders initial scenario details, source lines, and anti-credentialism notices", () => {
    render(<PracticeWorkspace initialScenarioId="SCEN-DATA-01-SQL" />);

    expect(screen.getByRole("heading", { name: /Customer Revenue Aggregation/i })).toBeInTheDocument();
    expect(screen.getByText(/Capability self-reflection only/i)).toBeInTheDocument();
    expect(screen.getByText(/Offline Sandbox Active/i)).toBeInTheDocument();

    // Source code artifact lines exist
    expect(screen.getByTestId("code-line-1")).toBeInTheDocument();
    expect(screen.getByTestId("code-line-6")).toBeInTheDocument();
  });

  it("switches scenarios when tab pill is clicked", () => {
    render(<PracticeWorkspace initialScenarioId="SCEN-DATA-01-SQL" />);

    // Switch to EDA scenario
    const edaBtn = screen.getByRole("button", { name: "SCEN-DATA-02-EDA" });
    fireEvent.click(edaBtn);

    expect(screen.getByRole("heading", { name: /Cohort Churn Pre-filtering/i })).toBeInTheDocument();
    expect(screen.getByText(/Source Artifact \(PYTHON/i)).toBeInTheDocument();

    // Switch to EXP scenario
    const expBtn = screen.getByRole("button", { name: "SCEN-DATA-03-EXP" });
    fireEvent.click(expBtn);

    expect(screen.getByRole("heading", { name: /A\/B Test Ratio Mismatch/i })).toBeInTheDocument();

    // Switch to expanded scenarios: DECOMP, ETHICS, FEATENG, BIGDATA
    const decompBtn = screen.getByRole("button", { name: "SCEN-DATA-04-DECOMP" });
    fireEvent.click(decompBtn);
    expect(screen.getByRole("heading", { name: /Product Metric Decomposition/i })).toBeInTheDocument();

    const ethicsBtn = screen.getByRole("button", { name: "SCEN-DATA-05-ETHICS" });
    fireEvent.click(ethicsBtn);
    expect(screen.getByRole("heading", { name: /User Data Ingestion/i })).toBeInTheDocument();

    const featengBtn = screen.getByRole("button", { name: "SCEN-DATA-06-FEATENG" });
    fireEvent.click(featengBtn);
    expect(screen.getByRole("heading", { name: /Tabular Feature Engineering/i })).toBeInTheDocument();

    const bigdataBtn = screen.getByRole("button", { name: "SCEN-DATA-07-BIGDATA" });
    fireEvent.click(bigdataBtn);
    expect(screen.getByRole("heading", { name: /PySpark Pipeline/i })).toBeInTheDocument();
  });

  it("allows selecting a code line and adding/removing defect candidate flags", () => {
    render(<PracticeWorkspace initialScenarioId="SCEN-DATA-01-SQL" />);

    // Select line 6 by clicking on the code line
    const line6 = screen.getByTestId("code-line-6");
    fireEvent.click(line6);

    // Verify input changed to 6
    const lineInput = screen.getByLabelText(/line number/i) as HTMLInputElement;
    expect(lineInput.value).toBe("6");

    // Add rationale
    const rationaleInput = screen.getByLabelText(/diagnostic reasoning/i);
    fireEvent.change(rationaleInput, { target: { value: "Potential division by zero if count is 0" } });

    // Submit flag
    const flagBtn = screen.getByRole("button", { name: /flag line 6 as defect/i });
    fireEvent.click(flagBtn);

    // Verify flag is listed in candidate flags
    expect(screen.getByTestId("flag-item-6")).toBeInTheDocument();
    expect(within(screen.getByTestId("flag-item-6")).getByText(/Line 6/i)).toBeInTheDocument();
    expect(screen.getByText(/Potential division by zero/i)).toBeInTheDocument();

    // Remove flag
    const removeBtn = screen.getByRole("button", { name: /remove flag on line 6/i });
    fireEvent.click(removeBtn);

    expect(screen.queryByTestId("flag-item-6")).not.toBeInTheDocument();
    expect(screen.getByText(/no defects flagged yet/i)).toBeInTheDocument();
  });

  it("toggles the offline sandbox execution preview", () => {
    render(<PracticeWorkspace initialScenarioId="SCEN-DATA-01-SQL" />);

    const runBtn = screen.getByRole("button", { name: /run in sandbox/i });
    fireEvent.click(runBtn);

    expect(screen.getByRole("region", { name: /sandbox runtime output/i })).toBeInTheDocument();
    expect(screen.getByText(/₹3,035.71/i)).toBeInTheDocument();

    // Toggle hide
    fireEvent.click(screen.getByRole("button", { name: /hide sandbox runner/i }));
    expect(screen.queryByRole("region", { name: /sandbox runtime output/i })).not.toBeInTheDocument();
  });

  it("evaluates deterministic score with exact matches, false flag deductions, and unlocks evidence on pass", async () => {
    const onAttemptCompleted = vi.fn();
    render(
      <PracticeWorkspace
        initialScenarioId="SCEN-DATA-01-SQL"
        onAttemptCompleted={onAttemptCompleted}
      />
    );

    // Flag Defect 1 (Exact match on line 6: division_by_zero)
    fireEvent.click(screen.getByTestId("code-line-6"));
    fireEvent.change(screen.getByLabelText(/suspected defect category/i), {
      target: { value: "division_by_zero" },
    });
    fireEvent.click(screen.getByRole("button", { name: /flag line 6 as defect/i }));

    // Flag Defect 2 (Exact match on line 10: lookahead_bias)
    fireEvent.click(screen.getByTestId("code-line-10"));
    fireEvent.change(screen.getByLabelText(/suspected defect category/i), {
      target: { value: "lookahead_bias" },
    });
    fireEvent.click(screen.getByRole("button", { name: /flag line 10 as defect/i }));

    // Flag Defect 3 (Partial match on line 16: aggregation_bias category mismatch with metric_misalignment)
    fireEvent.click(screen.getByTestId("code-line-16"));
    fireEvent.change(screen.getByLabelText(/suspected defect category/i), {
      target: { value: "metric_misalignment" },
    });
    fireEvent.click(screen.getByRole("button", { name: /flag line 16 as defect/i }));

    // Flag false flag (Line 2: division_by_zero)
    fireEvent.click(screen.getByTestId("code-line-2"));
    fireEvent.change(screen.getByLabelText(/suspected defect category/i), {
      target: { value: "division_by_zero" },
    });
    fireEvent.click(screen.getByRole("button", { name: /flag line 2 as defect/i }));

    // Submit attempt
    const submitBtn = screen.getByRole("button", { name: /submit attempt for scoring/i });
    fireEvent.click(submitBtn);

    // Raw score should be 1.0 (exact) + 1.0 (exact) + 0.5 (partial category) = 2.5
    // 1 False flag penalty: -0.5
    // Net score: 2.0 (>= 2.0 threshold -> PASSED)
    await waitFor(() => {
      expect(screen.getByTestId("scoring-report")).toBeInTheDocument();
      expect(screen.getByText(/PASSED THRESHOLD/i)).toBeInTheDocument();
      expect(screen.getByText(/Net Score: 2.0 \/ 3.0 pts/i)).toBeInTheDocument();
      expect(screen.getByText(/Raw: 2.5/i)).toBeInTheDocument();
      expect(screen.getByText(/Penalties: -0.5/i)).toBeInTheDocument();
    });

    // Check IndexedDB persistence
    await waitFor(async () => {
      const attempts = await getScenarioAttempts();
      expect(attempts.length).toBe(1);
      expect(attempts[0]?.passed).toBe(true);
      expect(attempts[0]?.score).toBe(2.0);

      const records = await getAllLedgerRecords();
      const demonstrated = records.filter((r) => r.verification_state === "demonstrated");
      expect(demonstrated.length).toBeGreaterThan(0);
      expect(demonstrated.some((r) => r.competency_id === "data.anl.l2_sql_basic")).toBe(true);
    });

    expect(onAttemptCompleted).toHaveBeenCalledTimes(1);
  });

  it("handles failed threshold with retry and no evidence unlocked", async () => {
    render(<PracticeWorkspace initialScenarioId="SCEN-DATA-01-SQL" />);

    // Only flag 1 defect (Line 6: division_by_zero = 1.0 pt, threshold is 2.0)
    fireEvent.click(screen.getByTestId("code-line-6"));
    fireEvent.change(screen.getByLabelText(/suspected defect category/i), {
      target: { value: "division_by_zero" },
    });
    fireEvent.click(screen.getByRole("button", { name: /flag line 6 as defect/i }));

    // Submit attempt
    fireEvent.click(screen.getByRole("button", { name: /submit attempt for scoring/i }));

    await waitFor(() => {
      expect(screen.getByText(/PRACTICE COMPLETED/i)).toBeInTheDocument();
      expect(screen.getByText(/Net Score: 1.0 \/ 3.0 pts/i)).toBeInTheDocument();
      expect(screen.queryByText(/Demonstrated Evidence Unlocked/i)).not.toBeInTheDocument();
    });

    // Verify ledger has 0 demonstrated records
    const records = await getAllLedgerRecords();
    expect(records.filter((r) => r.verification_state === "demonstrated")).toHaveLength(0);

    // Click retry to dismiss report and try again
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(screen.queryByTestId("scoring-report")).not.toBeInTheDocument();
  });

  it("passes axe accessibility tests with 0 violations in both editing and scored report states", async () => {
    const { container } = render(<PracticeWorkspace initialScenarioId="SCEN-DATA-01-SQL" />);

    // Unscored state accessibility
    const results1 = await axe.run(container, AXE_OPTIONS);
    expect(results1.violations).toEqual([]);

    // Flag lines and submit to test scored state accessibility
    fireEvent.click(screen.getByTestId("code-line-6"));
    fireEvent.click(screen.getByRole("button", { name: /flag line 6 as defect/i }));
    fireEvent.click(screen.getByRole("button", { name: /submit attempt for scoring/i }));

    await waitFor(() => {
      expect(screen.getByTestId("scoring-report")).toBeInTheDocument();
    });

    const results2 = await axe.run(container, AXE_OPTIONS);
    expect(results2.violations).toEqual([]);
  });
});
