import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import axe from "axe-core";
import { NextStepCard } from "./NextStepCard";
import type {
  ClientEvidenceRecord,
  ClientCareerProfile,
} from "../../lib/careerLedger";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Checked independently via check_contrast.py
  },
};

describe("NextStepCard (T15.32 Single Next-Step Action Card)", () => {
  const mockProfile: ClientCareerProfile = {
    id: "primary",
    target_role: "Data Analyst",
    target_level: "L2_junior",
    target_family: "DATA",
    available_hours_per_week: 10,
    updated_at: new Date().toISOString(),
  };

  const createRecord = (
    competencyId: string,
    state: "demonstrated" | "self_reported" = "demonstrated"
  ): ClientEvidenceRecord => ({
    competency_id: competencyId,
    verification_state: state,
    evidence_type: state === "demonstrated" ? "scenario_attempt" : "self_attestation",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });

  it("identifies first foundational unproven milestone when ledger is empty", () => {
    const handleLaunch = vi.fn();
    const handleNav = vi.fn();

    render(
      <NextStepCard
        profile={mockProfile}
        records={[]}
        onLaunchPractice={handleLaunch}
        onNavigateTab={handleNav}
      />
    );

    // Foundational step 1 is Analytical Reasoning and Problem Decomposition
    expect(screen.getByRole("region", { name: /recommended next step/i })).toBeInTheDocument();
    expect(screen.getByText(/priority next step/i)).toBeInTheDocument();
    expect(screen.getByText(/Analytical Reasoning and Problem Decomposition/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 1 of 14 in DATA Sequence/i)).toBeInTheDocument();

    // Verify calibrated heuristic effort range exists and has Heuristic tag
    expect(screen.getByText(/15–25 hours/i)).toBeInTheDocument();
    expect(screen.getByText(/^heuristic$/i)).toBeInTheDocument();

    // Verify statutory disclaimer exists
    expect(screen.getByText(/statutory disclaimer/i)).toBeInTheDocument();
  });

  it("advances to Relational SQL and renders flaw-finding practice button", () => {
    const handleLaunch = vi.fn();
    const records: ClientEvidenceRecord[] = [
      createRecord("data.gen.l2_prob_decomp", "demonstrated"),
      createRecord("data.gen.l2_ethics", "demonstrated"),
    ];

    render(
      <NextStepCard
        profile={mockProfile}
        records={records}
        onLaunchPractice={handleLaunch}
      />
    );

    // Next should be data.anl.l2_sql_basic
    expect(screen.getByText(/Relational SQL Querying and Table Joins/i)).toBeInTheDocument();
    expect(screen.getByText(/25–40 hours/i)).toBeInTheDocument();

    // Verify Practice Scenario CTA
    const practiceBtn = screen.getByRole("button", {
      name: /launch flaw-finding practice scenario for Relational SQL Querying and Table Joins/i,
    });
    expect(practiceBtn).toBeInTheDocument();

    fireEvent.click(practiceBtn);
    expect(handleLaunch).toHaveBeenCalledWith("SCEN-DATA-01-SQL");
  });

  it("displays downstream unlock chips informing what this milestone enables", () => {
    render(
      <NextStepCard
        profile={mockProfile}
        records={[
          createRecord("data.gen.l2_prob_decomp", "demonstrated"),
          createRecord("data.gen.l2_ethics", "demonstrated"),
        ]}
      />
    );

    // SQL Basic unlocks Hygiene, Dashboard, SQL Adv
    expect(screen.getByText(/unlocks downstream capabilities/i)).toBeInTheDocument();
    expect(screen.getByText(/unlocks prerequisites for/i)).toBeInTheDocument();
  });

  it("shows self-reported badge if user has self-attested but not yet demonstrated", () => {
    const records: ClientEvidenceRecord[] = [
      createRecord("data.gen.l2_prob_decomp", "demonstrated"),
      createRecord("data.gen.l2_ethics", "demonstrated"),
      createRecord("data.anl.l2_sql_basic", "self_reported"),
    ];

    render(
      <NextStepCard
        profile={mockProfile}
        records={records}
      />
    );

    // Step should still be SQL basic (since self_reported is not demonstrated)
    expect(screen.getByText(/Relational SQL Querying and Table Joins/i)).toBeInTheDocument();
    expect(screen.getByText(/Self-Reported \(Ready to Demonstrate\)/i)).toBeInTheDocument();
  });

  it("renders target level mastery state when all target competencies are demonstrated", () => {
    const handleNav = vi.fn();
    // Junior competencies (5 total)
    const records: ClientEvidenceRecord[] = [
      createRecord("data.gen.l2_prob_decomp", "demonstrated"),
      createRecord("data.gen.l2_ethics", "demonstrated"),
      createRecord("data.anl.l2_sql_basic", "demonstrated"),
      createRecord("data.anl.l2_eda", "demonstrated"),
      createRecord("data.anl.l2_hygiene", "demonstrated"),
    ];

    render(
      <NextStepCard
        profile={mockProfile}
        records={records}
        onNavigateTab={handleNav}
      />
    );

    expect(screen.getByText(/target level complete/i)).toBeInTheDocument();
    expect(screen.getByText(/All Junior L2 Competencies Demonstrated/i)).toBeInTheDocument();
    expect(screen.getByText(/5\/5 Demonstrated/i)).toBeInTheDocument();

    const fullRoadmapBtn = screen.getByRole("button", { name: /view full roadmap/i });
    expect(fullRoadmapBtn).toBeInTheDocument();
    fireEvent.click(fullRoadmapBtn);
    expect(handleNav).toHaveBeenCalledWith("plan");
  });

  it("enforces anti-causal rules (Rule R-CR-01): zero salary promises", () => {
    const { container } = render(
      <NextStepCard
        profile={mockProfile}
        records={[]}
      />
    );

    const text = container.textContent || "";
    // Anti-causal invariants
    expect(text).not.toMatch(/guarantee.*salary/i);
    expect(text).not.toMatch(/will earn/i);
    expect(text).not.toMatch(/boost.*pay.*₹/i);
    expect(text).not.toMatch(/exam/i);
    expect(text).not.toMatch(/credential/i);
  });

  it("passes axe accessibility tests with 0 violations across active and completed states", async () => {
    // Active state
    const { container, rerender } = render(
      <NextStepCard
        profile={mockProfile}
        records={[]}
      />
    );

    let results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);

    // Completed state
    const completeRecords: ClientEvidenceRecord[] = [
      createRecord("data.gen.l2_prob_decomp", "demonstrated"),
      createRecord("data.gen.l2_ethics", "demonstrated"),
      createRecord("data.anl.l2_sql_basic", "demonstrated"),
      createRecord("data.anl.l2_eda", "demonstrated"),
      createRecord("data.anl.l2_hygiene", "demonstrated"),
    ];

    rerender(
      <NextStepCard
        profile={mockProfile}
        records={completeRecords}
      />
    );

    results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});
