import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import axe from "axe-core";
import { App } from "../App";
import { EstimateScreen } from "./EstimateScreen";
import { ProfileForm } from "./ProfileForm";
import { RangeSpan } from "./RangeSpan";
import { DefinitionPopover } from "./DefinitionPopover";
import { AbstainedResponseData, EstimateResponseData } from "../lib/types";

// Configure axe rules for jsdom environment (where geometry/canvas calculations are simulated)
const AXE_OPTIONS = {
  rules: {
    // Contrast is verified mathematically by scripts/check_contrast.py in CI
    "color-contrast": { enabled: false },
  },
};

describe("Automated Accessibility Pass (Axe Core — T9.09)", () => {
  const sampleEstimate: EstimateResponseData = {
    request_id: "a11y-est-1",
    status: "ok",
    estimate: {
      p10: 24.5,
      p50: 38.0,
      p90: 55.0,
      currency: "INR",
      period: "annual",
      measure: "guaranteed_cash_annual",
      pre_tax: true,
      nominal: true,
    },
    reliability: {
      grade: "GRADE_A",
      reasons: [],
    },
    evidence: {
      cohort_n: 142,
      source_mix: [
        { source_type: "statutory_filing", share: 0.65 },
        { source_type: "voluntary_intake", share: 0.35 },
      ],
      median_observation_age_days: 72.0,
      data_snapshot_id: "SNAP-CANONICAL-20261018",
      model_version: "0.1.0",
    },
    profile_level_used: 0,
    warnings: [],
    disclaimer_id: "decision_support_v1",
    as_of: "2026-10-19",
    model_version: "0.1.0",
    data_snapshot_id: "SNAP-CANONICAL-20261018",
  };

  it("App root view has 0 axe accessibility violations", async () => {
    const { container } = render(<App />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("EstimateScreen in default result state has 0 axe accessibility violations", async () => {
    const { container } = render(<EstimateScreen initialEstimate={sampleEstimate} />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("EstimateScreen with Refinements disclosure expanded has 0 axe accessibility violations", async () => {
    const { container } = render(<EstimateScreen initialEstimate={sampleEstimate} />);
    
    // Expand details
    const showDetailsBtn = screen.getByRole("button", { name: /show details/i });
    fireEvent.click(showDetailsBtn);

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("EstimateScreen with PayCompare panel open has 0 axe accessibility violations", async () => {
    const { container } = render(<EstimateScreen initialEstimate={sampleEstimate} />);
    
    // Open pay compare
    const compareBtn = screen.getByTestId("compare-pay-btn");
    fireEvent.click(compareBtn);

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("EstimateScreen with Methodology Modal open has 0 axe accessibility violations", async () => {
    const { container } = render(<EstimateScreen initialEstimate={sampleEstimate} />);
    
    // Open modal
    const methodBtn = screen.getByRole("button", { name: /how this was calculated/i });
    fireEvent.click(methodBtn);

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("EstimateScreen in neutral Abstention state has 0 axe accessibility violations", async () => {
    const abstained: AbstainedResponseData = {
      request_id: "a11y-abstain-1",
      status: "abstained",
      reasons: [
        {
          code: "INSUFFICIENT_SUPPORT",
          detail: "We have too few comparable records for this combination.",
        },
      ],
      fallbacks: [
        {
          type: "broaden_location",
          description: "Broaden location to a primary tech hub like Bengaluru or Hyderabad.",
        },
      ],
      disclaimer_id: "decision_support_v1",
      as_of: "2026-10-19",
      model_version: "0.1.0",
      data_snapshot_id: "SNAP-CANONICAL-20261018",
    };

    const { container } = render(<EstimateScreen initialEstimate={abstained} />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("RangeSpan with accessible table view expanded has 0 axe accessibility violations", async () => {
    const { container } = render(
      <RangeSpan
        p10={20}
        p50={32}
        p90={48}
        currency="INR"
        unit="lpa"
        defaultTableView={true}
      />
    );

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("DefinitionPopover when open has 0 axe accessibility violations", async () => {
    const { container } = render(
      <DefinitionPopover
        term="Guaranteed cash"
        definition="Base annual cash allowances paid unconditionally before tax."
      />
    );

    const trigger = screen.getByRole("button", { name: "Guaranteed cash" });
    fireEvent.click(trigger);

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("ProfileForm with validation error summary has 0 axe accessibility violations", async () => {
    const { container } = render(
      <ProfileForm
        initialValues={{
          occupation_id: "SWE",
          location_id: "BENGALURU",
          years_experience: null,
          not_sure_experience: false,
        }}
        onSubmit={() => {}}
      />
    );

    // Trigger validation error by submitting empty experience
    const submitBtn = screen.getByRole("button", { name: /show estimated range/i });
    fireEvent.click(submitBtn);

    // Verify error summary exists
    expect(screen.getByRole("alert")).toBeInTheDocument();

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});
