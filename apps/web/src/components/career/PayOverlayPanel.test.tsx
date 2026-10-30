import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import axe from "axe-core";
import { PayOverlayPanel } from "./PayOverlayPanel";
import type { ClientCareerProfile } from "../../lib/careerLedger";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Checked independently via check_contrast.py
  },
};

describe("PayOverlayPanel (T15.33 Decoupled Pay Overlay & Abstention Panel)", () => {
  const mockProfile: ClientCareerProfile = {
    id: "primary",
    target_role: "Data Analyst",
    target_level: "L3_mid",
    target_family: "DATA",
    available_hours_per_week: 10,
    updated_at: new Date().toISOString(),
  };

  it("renders empirical quantile interval (P10, P50, P90) with zero lone numbers (Rule R-UQ-01)", () => {
    render(<PayOverlayPanel profile={mockProfile} />);

    // Check region and heading
    expect(
      screen.getByRole("region", { name: /decoupled market compensation context/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/Market Compensation Context/i)).toBeInTheDocument();

    // Verify all 3 empirical quantiles are rendered
    expect(screen.getByText(/10th Percentile \(P10\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Median \(P50\)/i)).toBeInTheDocument();
    expect(screen.getByText(/90th Percentile \(P90\)/i)).toBeInTheDocument();

    // Check Mid-Level Bangalore values: P10 = 16.0, P50 = 24.0, P90 = 32.0 lakh
    expect(screen.getByText(/₹16.0 lakh/i)).toBeInTheDocument();
    expect(screen.getByText(/₹24.0 lakh/i)).toBeInTheDocument();
    expect(screen.getByText(/₹32.0 lakh/i)).toBeInTheDocument();

    // Check interval span summary
    expect(screen.getByText(/80% Conformal Interval Span/i)).toBeInTheDocument();
  });

  it("enforces Two Streams Two Places (Rule R-CR-02): explicit decoupling banner and no composite scores", () => {
    const { container } = render(<PayOverlayPanel profile={mockProfile} />);

    // Decoupling banner
    expect(screen.getByText(/Two Streams, Two Places Architecture \(Rule R-CR-02\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Decoupled Stream \(R-CR-02\)/i)).toBeInTheDocument();

    // Verify absence of composite readiness / skill-pay scores
    const text = container.textContent || "";
    expect(text).not.toMatch(/readiness score/i);
    expect(text).not.toMatch(/skill score.*₹/i);
    expect(text).not.toMatch(/composite score/i);
  });

  it("renders honest abstention when unsupported cohort is selected (Rule R-CR-14)", () => {
    render(<PayOverlayPanel profile={mockProfile} />);

    const hubSelect = screen.getByLabelText(/Metro Tech Hub/i);
    fireEvent.change(hubSelect, { target: { value: "other" } });

    // Verify honest abstention message
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Honest Abstention \(Rule R-CR-14\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Insufficient Market Evidence for This Sub-Cohort/i)).toBeInTheDocument();

    // Reset button restores to Bangalore
    const resetBtn = screen.getByRole("button", {
      name: /Reset to Bengaluru \/ Tier-1 Metro Panel/i,
    });
    fireEvent.click(resetBtn);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(/₹24.0 lakh/i)).toBeInTheDocument();
  });

  it("updates quantile intervals when switching hub or seniority level", () => {
    render(<PayOverlayPanel profile={mockProfile} />);

    // Switch to Junior L2
    const levelSelect = screen.getByLabelText(/Seniority Level/i);
    fireEvent.change(levelSelect, { target: { value: "L2_junior" } });

    // Bangalore Junior: P10 = 8.0, P50 = 12.0, P90 = 16.0
    expect(screen.getByText(/₹8.0 lakh/i)).toBeInTheDocument();
    expect(screen.getByText(/₹12.0 lakh/i)).toBeInTheDocument();
    expect(screen.getByText(/₹16.0 lakh/i)).toBeInTheDocument();
  });

  it("displays offline reference anchor indicator", () => {
    render(<PayOverlayPanel profile={mockProfile} />);

    expect(screen.getByText(/Offline Benchmark Anchor/i)).toBeInTheDocument();
    expect(screen.getByText(/\(Low Evidence\)/i)).toBeInTheDocument();
  });

  it("enforces anti-causal rules (Rule R-CR-01): zero wage guarantees or skill premiums", () => {
    const { container } = render(<PayOverlayPanel profile={mockProfile} />);

    const text = container.textContent || "";
    expect(text).not.toMatch(/guarantee.*salary/i);
    expect(text).not.toMatch(/will earn/i);
    expect(text).not.toMatch(/boost.*pay.*₹/i);
  });

  it("passes axe accessibility tests with 0 violations across benchmark and abstention views", async () => {
    const { container } = render(<PayOverlayPanel profile={mockProfile} />);

    // Active benchmark distribution view
    let results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);

    // Trigger honest abstention view
    const hubSelect = screen.getByLabelText(/Metro Tech Hub/i);
    fireEvent.change(hubSelect, { target: { value: "other" } });

    results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});

