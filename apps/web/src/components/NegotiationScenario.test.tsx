import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  NegotiationScenario,
  calculateCopulaRealization,
  calculateNetTakeHomeLpa,
} from "./NegotiationScenario";

describe("NegotiationScenario Component (PT4 Prototype / EXP-15)", () => {
  const mockBaselineProfile = {
    role: "SWE",
    seniority: "SR",
    location: "BENGALURU",
    yoe: 6,
  };

  const mockBaselineSpan = {
    p10: 22.0,
    p50: 28.5,
    p90: 36.0,
  };

  it("renders baseline profile and calibrated pay span correctly", () => {
    render(
      <NegotiationScenario
        baselineProfile={mockBaselineProfile}
        baselineSpan={mockBaselineSpan}
      />
    );

    expect(screen.getByText(/Counterfactual Scenario & Offer Modeling/i)).toBeInTheDocument();
    expect(screen.getByText(/PT4 Copula Engine/i)).toBeInTheDocument();
    expect(screen.getByText(/SWE • SR • BENGALURU • 6 YoE/i)).toBeInTheDocument();
    expect(screen.getByText(/Calibrated 80% Pay Span/i)).toBeInTheDocument();
  });

  it("switches tabs between experience, promotion, relocation, and dual offers", () => {
    const handleSelect = vi.fn();
    render(
      <NegotiationScenario
        baselineProfile={mockBaselineProfile}
        baselineSpan={mockBaselineSpan}
        onScenarioSelect={handleSelect}
      />
    );

    // Default is experience tab
    expect(screen.getByRole("tab", { name: "Experience" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/\+1 Year/i)).toBeInTheDocument();

    // Click Promotion tab
    const promoBtn = screen.getByRole("tab", { name: "Promotion" });
    fireEvent.click(promoBtn);
    expect(handleSelect).toHaveBeenCalledWith("promotion");
    expect(promoBtn).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/Promotion to STAFF/i)).toBeInTheDocument();

    // Click Relocation tab
    const relocBtn = screen.getByRole("tab", { name: "Relocation" });
    fireEvent.click(relocBtn);
    expect(handleSelect).toHaveBeenCalledWith("relocation");
    expect(screen.getByText(/Relocation to NCR/i)).toBeInTheDocument();

    // Click Dual Offers tab
    const dualBtn = screen.getByRole("tab", { name: "Dual Offers" });
    fireEvent.click(dualBtn);
    expect(handleSelect).toHaveBeenCalledWith("dual_offer");
    expect(screen.getByTestId("offer-a-card")).toBeInTheDocument();
    expect(screen.getByTestId("offer-b-card")).toBeInTheDocument();
  });

  it("calculates dual offer trade-off and copula joint realization without lone numbers", () => {
    render(
      <NegotiationScenario
        baselineProfile={mockBaselineProfile}
        baselineSpan={mockBaselineSpan}
      />
    );

    // Switch to Dual Offers tab
    fireEvent.click(screen.getByRole("tab", { name: "Dual Offers" }));

    // Verify both offers exist and calculate total OTE
    expect(screen.getByTestId("offer-a-card")).toHaveTextContent("Offer A (Higher Base)");
    expect(screen.getByTestId("offer-b-card")).toHaveTextContent("Offer B (High Equity)");
    expect(screen.getByText(/Gaussian Copula Joint Distribution:/i)).toBeInTheDocument();
    expect(screen.getByText(/Trade-Off Analysis & Certainty Index:/i)).toBeInTheDocument();

    // Change Offer A guaranteed cash
    const cashInputA = screen.getByLabelText(/Offer A Guaranteed Cash LPA/i);
    fireEvent.change(cashInputA, { target: { value: "32.0" } });
    expect(screen.getByText(/offers ₹/i)).toBeInTheDocument();

    // Verify Copula Realization range is rendered
    expect(screen.getAllByText(/Copula Realization \(P10–P90\):/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Certainty:/i).length).toBe(3);
  });

  it("always displays mandatory statutory disclaimer notice", () => {
    render(
      <NegotiationScenario
        baselineProfile={mockBaselineProfile}
        baselineSpan={mockBaselineSpan}
      />
    );

    expect(
      screen.getByText(/Counterfactual scenario estimates are mathematical quantile projections/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Section 115BAC/i)).toBeInTheDocument();
  });

  it("guarantees monotonic non-crossing quantiles for copula multi-component realization", () => {
    const realization = calculateCopulaRealization(25.0, 10.0, 5.0);
    expect(realization.p10).toBeLessThanOrEqual(realization.p50);
    expect(realization.p50).toBeLessThanOrEqual(realization.p90);

    // Exact expected bounds
    // P10: 25 + 6.0 + 3.5 = 34.5
    // P50: 25 + 10.0 + 5.0 = 40.0
    // P90: 25 + 15.0 + 6.5 = 46.5
    expect(realization.p10).toBe(34.5);
    expect(realization.p50).toBe(40.0);
    expect(realization.p90).toBe(46.5);
  });

  it("correctly computes Section 115BAC net in-hand take-home", () => {
    expect(calculateNetTakeHomeLpa(0)).toBe(0);
    // Under 7 LPA rebate:
    expect(calculateNetTakeHomeLpa(6.5)).toBe(6.5);
    // Above rebate:
    const net15 = calculateNetTakeHomeLpa(15.0);
    expect(net15).toBeGreaterThan(12.0);
    expect(net15).toBeLessThan(15.0);
  });
});
