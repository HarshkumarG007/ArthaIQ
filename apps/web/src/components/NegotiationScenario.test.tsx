import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NegotiationScenario } from "./NegotiationScenario";

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

  it("calculates dual offer trade-off and statutory net in-hand without lone numbers", () => {
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
    expect(screen.getByText(/Trade-Off Analysis & Certainty Index:/i)).toBeInTheDocument();

    // Change Offer A guaranteed cash
    const cashInputA = screen.getByLabelText(/Offer A Guaranteed Cash LPA/i);
    fireEvent.change(cashInputA, { target: { value: "32.0" } });
    expect(screen.getByText(/offers ₹/i)).toBeInTheDocument();
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
});
