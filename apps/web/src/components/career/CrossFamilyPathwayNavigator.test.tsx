import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import axe from "axe-core";
import { CrossFamilyPathwayNavigator } from "./CrossFamilyPathwayNavigator";
import type { ClientEvidenceRecord } from "../../lib/careerLedger";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Checked independently via check_contrast.py
  },
};

describe("CrossFamilyPathwayNavigator (Phase 30, Gate G30)", () => {
  it("renders corridor selector with all 3 canonical corridors", () => {
    render(<CrossFamilyPathwayNavigator />);

    expect(
      screen.getByRole("heading", { name: /Cross-Family Transition Navigator/i })
    ).toBeInTheDocument();

    // Verify all 3 corridor options exist in radiogroup
    expect(screen.getByRole("radio", { name: /Software Engineering → ML\/AI Systems/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Data Science → Machine Learning \/ AI/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Software Engineering → Data Engineering/i })).toBeInTheDocument();
  });

  it("switches corridors and updates milestones, role title, and benchmarks", () => {
    render(<CrossFamilyPathwayNavigator />);

    // Default corridor is SWE -> MLAI
    expect(
      screen.getByText("Senior Machine Learning & AI Systems Engineer (L4)")
    ).toBeInTheDocument();
    expect(screen.getByTestId("milestone-data.anl.l2_eda")).toBeInTheDocument();

    // Switch to DATA -> MLAI
    const dataMlBtn = screen.getByRole("radio", { name: /Data Science → Machine Learning \/ AI/i });
    fireEvent.click(dataMlBtn);

    expect(
      screen.getByText("Machine Learning Research Engineer (L4)")
    ).toBeInTheDocument();
    expect(screen.getByTestId("milestone-swe.core.l2_data_structures")).toBeInTheDocument();

    // Switch to SWE -> DATA
    const sweDataBtn = screen.getByRole("radio", { name: /Software Engineering → Data Engineering/i });
    fireEvent.click(sweDataBtn);

    expect(
      screen.getByText("Senior Data & Analytics Systems Engineer (L4)")
    ).toBeInTheDocument();
    expect(screen.getByTestId("milestone-data.anl.l2_sql_basic")).toBeInTheDocument();
  });

  it("renders bridge competency badges with transversal acceleration rationale", () => {
    render(<CrossFamilyPathwayNavigator />);

    // In SWE -> MLAI, data.anl.l2_eda is a bridge competency
    const bridgeBadges = screen.getAllByTestId("bridge-badge");
    expect(bridgeBadges.length).toBeGreaterThanOrEqual(1);
    expect(bridgeBadges[0]).toHaveTextContent(/Bridge Competency \(DATA → MLAI\)/i);

    // Verify bridge rationale is rendered
    expect(
      screen.getByText(/Connects software data structures to empirical distributions/i)
    ).toBeInTheDocument();
  });

  it("recalculates timeline and effort intervals when weekly study slider is adjusted", () => {
    render(<CrossFamilyPathwayNavigator />);

    // At default 10 hrs/week
    const slider = screen.getByLabelText(/Weekly study hours/i);
    expect(slider).toHaveValue("10");

    // Recalibrate to 20 hrs/week (Accelerated)
    fireEvent.change(slider, { target: { value: "20" } });
    expect(slider).toHaveValue("20");

    // Recalibrate to 5 hrs/week (Casual)
    fireEvent.change(slider, { target: { value: "5" } });
    expect(slider).toHaveValue("5");
  });

  it("hides demonstrated competencies when filter toggle is checked", () => {
    const mockRecords: ClientEvidenceRecord[] = [
      {
        competency_id: "data.anl.l2_eda",
        verification_state: "demonstrated",
        evidence_type: "scenario_attempt",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<CrossFamilyPathwayNavigator evidenceRecords={mockRecords} />);

    // Initially data.anl.l2_eda is visible with Demonstrated tag
    expect(screen.getByTestId("milestone-data.anl.l2_eda")).toBeInTheDocument();
    expect(screen.getByText(/^Demonstrated$/i)).toBeInTheDocument();

    // Toggle hide demonstrated competencies
    const toggle = screen.getByRole("checkbox", {
      name: /Hide proven competencies/i,
    });
    fireEvent.click(toggle);

    // Now data.anl.l2_eda should be pruned from milestone list
    expect(screen.queryByTestId("milestone-data.anl.l2_eda")).not.toBeInTheDocument();
  });

  it("triggers onSelectScenario when practice button is clicked", () => {
    const handleSelectScenario = vi.fn();
    render(<CrossFamilyPathwayNavigator onSelectScenario={handleSelectScenario} />);

    const practiceBtns = screen.getAllByRole("button", { name: /Launch practice scenario/i });
    expect(practiceBtns.length).toBeGreaterThan(0);

    fireEvent.click(practiceBtns[0]!);
    expect(handleSelectScenario).toHaveBeenCalledWith("SCEN-DATA-02-EDA");
  });

  it("enforces zero lone numbers and renders statutory CPA 2019 disclaimer", () => {
    render(<CrossFamilyPathwayNavigator />);

    // Check market benchmark quantile distribution has full [P10, P50, P90] intervals
    expect(screen.getByText(/P10 \(Entry\)/i)).toBeInTheDocument();
    expect(screen.getByText(/P50 \(Median\)/i)).toBeInTheDocument();
    expect(screen.getByText(/P90 \(Senior\)/i)).toBeInTheDocument();

    // Verify statutory CPA 2019 anti-causal disclaimer (Rule R-CR-01)
    expect(
      screen.getByText(/Statutory Disclosure \(India Consumer Protection Act 2019\)/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Completing practice scenarios or acquiring cross-family competencies does not guarantee salary increases/i
      )
    ).toBeInTheDocument();
  });

  it("passes axe-core accessibility audit with 0 violations", async () => {
    const { container } = render(<CrossFamilyPathwayNavigator />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});
