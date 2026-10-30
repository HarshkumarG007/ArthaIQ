import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import axe from "axe-core";
import { RoadmapView } from "./RoadmapView";
import type { ClientEvidenceRecord } from "../../lib/careerLedger";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Checked independently via check_contrast.py
  },
};

describe("RoadmapView (T15.31 Topological Roadmap & Effort Estimator)", () => {
  it("renders roadmap header, initial pacing selection, and statutory heuristic disclaimers", () => {
    render(<RoadmapView initialWeeklyHours={10} records={[]} />);

    expect(
      screen.getByRole("heading", { name: /Topological Roadmap & Calibrated Effort Estimator/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/10 hours\/week/i)).toBeInTheDocument();
    expect(screen.getByText(/Statutory Heuristic Disclaimer/i)).toBeInTheDocument();
    expect(screen.getByText(/does NOT promise, calculate, or guarantee salary increases/i)).toBeInTheDocument();

    // Verify milestones are present
    const step1 = screen.getByTestId("milestone-step-1");
    expect(step1).toBeInTheDocument();
    expect(within(step1).getByText(/Analytical Reasoning and Problem Decomposition/i)).toBeInTheDocument();

    const step3 = screen.getByTestId("milestone-step-3");
    expect(step3).toBeInTheDocument();
    expect(within(step3).getByText(/Relational SQL Querying and Table Joins/i)).toBeInTheDocument();
  });

  it("verifies dependency-respecting prerequisite ordering", () => {
    render(<RoadmapView records={[]} />);

    // Step 1 & Step 3 have no prerequisites
    const step1 = screen.getByTestId("milestone-step-1");
    expect(step1).toHaveTextContent(/None \(Foundational entry point\)/i);

    const step3 = screen.getByTestId("milestone-step-3");
    expect(step3).toHaveTextContent(/None \(Foundational entry point\)/i);

    // Step 5 (Data Hygiene) requires Step 3
    const step5 = screen.getByTestId("milestone-step-5");
    expect(step5).toHaveTextContent(/Step 3/i);

    // Step 6 (Dashboard) requires Step 3 and Step 4
    const step6 = screen.getByTestId("milestone-step-6");
    expect(step6).toHaveTextContent(/Step 3/i);
    expect(step6).toHaveTextContent(/Step 4/i);
  });

  it("dynamically recalibrates cumulative timeline when pacing options are selected", () => {
    render(<RoadmapView initialWeeklyHours={10} records={[]} />);

    // Initial projection at 10 h/wk
    // Total min hours across 14 nodes: 400h approx -> ~41 weeks
    const timelineAt10 = screen.getByTestId("projected-timeline");
    const text10 = timelineAt10.textContent;
    expect(text10).toMatch(/weeks/i);

    // Switch to 20 hours / week (Intensive)
    const button20 = screen.getByRole("radio", { name: /^20 h \/ week/i });
    fireEvent.click(button20);

    expect(screen.getByText(/20 hours\/week/i)).toBeInTheDocument();
    const timelineAt20 = screen.getByTestId("projected-timeline");
    expect(timelineAt20.textContent).not.toBe(text10);

    // Switch to 5 hours / week (Casual)
    const button5 = screen.getByRole("radio", { name: /^5 h \/ week/i });
    fireEvent.click(button5);

    expect(screen.getByText(/5 hours\/week/i)).toBeInTheDocument();
  });

  it("updates milestone states and deducts hours when competencies are demonstrated", () => {
    const mockRecords: ClientEvidenceRecord[] = [
      {
        competency_id: "data.anl.l2_sql_basic",
        verification_state: "demonstrated",
        evidence_type: "scenario_attempt",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metadata: { scenario_id: "SCEN-DATA-01-SQL", score: 3.0, max_score: 3.0 },
      },
      {
        competency_id: "data.gen.l2_prob_decomp",
        verification_state: "self_reported",
        evidence_type: "self_attestation",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<RoadmapView records={mockRecords} />);

    // Step 3 (SQL basic) should show Demonstrated
    const step3 = screen.getByTestId("milestone-step-3");
    expect(step3).toHaveTextContent(/Demonstrated/i);

    // Step 1 should show Self-Reported
    const step1 = screen.getByTestId("milestone-step-1");
    expect(step1).toHaveTextContent(/Self-Reported/i);

    // Counts badge
    expect(screen.getByText(/1 Demonstrated/i)).toBeInTheDocument();
    expect(screen.getByText(/1 Self-Reported/i)).toBeInTheDocument();
    expect(screen.getByText(/12 Unproven Gaps/i)).toBeInTheDocument();
  });

  it("filters milestones based on status tabs", () => {
    const mockRecords: ClientEvidenceRecord[] = [
      {
        competency_id: "data.anl.l2_sql_basic",
        verification_state: "demonstrated",
        evidence_type: "scenario_attempt",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<RoadmapView records={mockRecords} />);

    // All milestones (14)
    expect(screen.getByRole("tab", { name: /All Milestones \(14\)/i })).toBeInTheDocument();

    // Filter to unproven
    const unprovenTab = screen.getByRole("tab", { name: /Unproven Forward Gaps \(13\)/i });
    fireEvent.click(unprovenTab);

    // Demonstrated step 3 should now be hidden
    expect(screen.queryByTestId("milestone-step-3")).not.toBeInTheDocument();

    // Step 5 (Data Hygiene: unproven, prereq step 3 is satisfied) should be visible
    expect(screen.getByTestId("milestone-step-5")).toBeInTheDocument();

    // Filter to ready to start
    const readyTab = screen.getByRole("tab", { name: /Ready to Start/i });
    fireEvent.click(readyTab);

    // Step 5 should still be present because its prerequisite (step 3) is satisfied
    expect(screen.getByTestId("milestone-step-5")).toBeInTheDocument();
  });

  it("triggers navigation callbacks when practice or skills links are clicked", () => {
    const onNavigatePractice = vi.fn();
    const onNavigateSkills = vi.fn();

    render(
      <RoadmapView
        records={[]}
        onNavigatePractice={onNavigatePractice}
        onNavigateSkills={onNavigateSkills}
      />
    );

    // Click View Full Gap Map
    const gapMapLink = screen.getByRole("button", { name: /view full gap map/i });
    fireEvent.click(gapMapLink);
    expect(onNavigateSkills).toHaveBeenCalledTimes(1);

    // Click Practice Flaw-Finding on step 3 (SCEN-DATA-01-SQL)
    const practiceButtons = screen.getAllByRole("button", { name: /practice flaw-finding/i });
    expect(practiceButtons.length).toBeGreaterThan(0);
    fireEvent.click(practiceButtons[0]!);
    expect(onNavigatePractice).toHaveBeenCalledWith("SCEN-DATA-01-SQL");
  });

  it("passes axe accessibility tests with 0 violations across pacing options and filters", async () => {
    const { container } = render(<RoadmapView records={[]} />);

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);

    // Select pacing radio and re-audit
    const button20 = screen.getByRole("radio", { name: /20 h \/ week/i });
    fireEvent.click(button20);

    const results2 = await axe.run(container, AXE_OPTIONS);
    expect(results2.violations).toEqual([]);
  });
});
