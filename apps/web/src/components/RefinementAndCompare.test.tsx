import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MoneyField } from "./MoneyField";
import { SpanDelta } from "./SpanDelta";
import { PayCompare } from "./PayCompare";
import { EstimateScreen } from "./EstimateScreen";
import { EstimateResponseData, AbstainedResponseData } from "../lib/types";

describe("MoneyField", () => {
  it("formats input with Indian grouping as user types and converts to LPA", () => {
    const handleChange = vi.fn();
    render(<MoneyField onChange={handleChange} />);

    const input = screen.getByLabelText(/your compensation figure/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "2800000" } });

    expect(input.value).toBe("28,00,000");
    expect(handleChange).toHaveBeenCalledWith(28.0, "annual", "guaranteed_cash");
  });

  it("handles annual and monthly toggle converting to annualized LPA", () => {
    const handleChange = vi.fn();
    render(<MoneyField value={24.0} onChange={handleChange} />);

    // Toggle to monthly
    const monthlyBtn = screen.getByRole("button", { name: "/ month" });
    fireEvent.click(monthlyBtn);

    expect(handleChange).toHaveBeenCalledWith(expect.any(Number), "monthly", "guaranteed_cash");

    // Toggle back to annual
    const annualBtn = screen.getByRole("button", { name: "/ year" });
    fireEvent.click(annualBtn);

    expect(handleChange).toHaveBeenCalledWith(expect.any(Number), "annual", "guaranteed_cash");
  });

  it("handles 'Which figure is this?' measure selection and hint update", () => {
    const handleChange = vi.fn();
    render(<MoneyField onChange={handleChange} />);

    const select = screen.getByLabelText(/which figure is this\?/i);
    fireEvent.change(select, { target: { value: "ctc" } });

    expect(handleChange).toHaveBeenCalledWith(null, "annual", "ctc");
    expect(
      screen.getByText(/includes employer pf, gratuity, insurance/i)
    ).toBeInTheDocument();
  });
});

describe("SpanDelta", () => {
  it("renders narrower delta sentence when new width is smaller without celebrating", () => {
    render(
      <SpanDelta
        current={{ p10: 20, p50: 30, p90: 40 }} // width = 20
        previous={{ p10: 15, p50: 30, p90: 45 }} // width = 30
      />
    );

    const explanation = screen.getByTestId("span-delta-explanation");
    expect(explanation).toHaveTextContent("The range got narrower.");
    expect(explanation).toHaveTextContent(
      "This reflects patterns in the data, not what you would earn by changing this detail."
    );
    // Invariant: Never celebrate narrowing
    expect(explanation).not.toHaveTextContent("better");
    expect(explanation).not.toHaveTextContent("improved");
    expect(explanation).not.toHaveTextContent("congratulations");
  });

  it("renders wider delta sentence when new width is larger", () => {
    render(
      <SpanDelta
        current={{ p10: 10, p50: 30, p90: 50 }} // width = 40
        previous={{ p10: 20, p50: 30, p90: 40 }} // width = 20
      />
    );

    const explanation = screen.getByTestId("span-delta-explanation");
    expect(explanation).toHaveTextContent("The range got wider.");
    expect(explanation).toHaveTextContent(
      "This reflects patterns in the data, not what you would earn by changing this detail."
    );
  });

  it("renders 'did not change much' when widths are within 5%", () => {
    render(
      <SpanDelta
        current={{ p10: 20, p50: 30, p90: 40 }} // width = 20
        previous={{ p10: 20.2, p50: 30.1, p90: 40.1 }} // width = 19.9
      />
    );

    const explanation = screen.getByTestId("span-delta-explanation");
    expect(explanation).toHaveTextContent("The range did not change much.");
  });
});

describe("PayCompare", () => {
  const mockEstimate = {
    p10: 20.0,
    p50: 30.0,
    p90: 45.0,
    currency: "INR",
    unit: "lpa" as const,
    measure: "guaranteed cash pay",
    date: "October 2026",
  };

  it("displays inside range and ordinal percentile band when figure is within range", () => {
    render(<PayCompare currentEstimate={mockEstimate} initialValue={25.0} />);

    expect(screen.getByTestId("position-sentence")).toHaveTextContent(
      "Your figure is inside the estimated range."
    );
    expect(screen.getByTestId("percentile-sentence").textContent).toMatch(
      /It sits around the \d+(st|nd|rd|th) to \d+(st|nd|rd|th) percentile of comparable pay/i
    );
    expect(screen.getByText(/Your pay may reflect things this estimate does not include/i)).toBeInTheDocument();

    // Invariant check: never say underpaid or overpaid (Rule R-MD-13)
    const cardText = screen.getByTestId("pay-compare").textContent || "";
    expect(cardText.toLowerCase()).not.toContain("underpaid");
    expect(cardText.toLowerCase()).not.toContain("overpaid");
  });

  it("displays below range when figure is less than p10", () => {
    render(<PayCompare currentEstimate={mockEstimate} initialValue={15.0} />);

    expect(screen.getByTestId("position-sentence")).toHaveTextContent(
      "Your figure is below the estimated range."
    );
    expect(screen.getByTestId("percentile-sentence")).toHaveTextContent(
      "It sits around the 1st to 10th percentile of comparable pay."
    );
  });

  it("displays above range when figure is greater than p90", () => {
    render(<PayCompare currentEstimate={mockEstimate} initialValue={60.0} />);

    expect(screen.getByTestId("position-sentence")).toHaveTextContent(
      "Your figure is above the estimated range."
    );
    expect(screen.getByTestId("percentile-sentence")).toHaveTextContent(
      "It sits around the 90th to 99th percentile of comparable pay."
    );
  });

  it("shows definition mismatch caution notice when user selects CTC instead of guaranteed cash", () => {
    render(<PayCompare currentEstimate={mockEstimate} initialValue={25.0} />);

    // Select CTC
    const measureSelect = screen.getByLabelText(/which figure is this\?/i);
    fireEvent.change(measureSelect, { target: { value: "ctc" } });

    const banner = screen.getByTestId("definition-mismatch-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(
      "You chose Total CTC, but this range is for guaranteed cash pay. The comparison may be off."
    );
  });
});

describe("EstimateScreen Integration", () => {
  const sampleEstimate: EstimateResponseData = {
    request_id: "test-est-1",
    status: "ok",
    estimate: {
      p10: 22.0,
      p50: 35.0,
      p90: 50.0,
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

  it("renders profile form and estimate headline, and toggles refinement disclosures", async () => {
    render(<EstimateScreen initialEstimate={sampleEstimate} />);

    // Headline and form present
    expect(screen.getByRole("heading", { name: /estimated range/i })).toBeInTheDocument();
    expect(screen.getByTestId("headline-display-range")).toHaveTextContent("₹22.0 to ₹50.0 lakh a year");

    // Optional refinement toggle
    const toggleDetailsBtn = screen.getByRole("button", { name: /show details/i });
    fireEvent.click(toggleDetailsBtn);

    // Skills refinement pills visible
    expect(screen.getByText("Distributed Systems")).toBeInTheDocument();
    expect(screen.getByLabelText(/industry and employer type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/work arrangement/i)).toBeInTheDocument();

    // Select skill
    fireEvent.click(screen.getByRole("button", { name: "Distributed Systems" }));

    // Click refine estimate button
    const refineSubmitBtn = screen.getByTestId("apply-refinements-btn");
    fireEvent.click(refineSubmitBtn);

    // Verify loading and result update
    await waitFor(() => {
      expect(screen.getByTestId("estimate-result-card")).toBeInTheDocument();
    });
  });

  it("toggles inline PayCompare panel on clicking 'Compare with my pay'", () => {
    render(<EstimateScreen initialEstimate={sampleEstimate} />);

    const compareBtn = screen.getByTestId("compare-pay-btn");
    expect(compareBtn).toHaveTextContent("Compare with my pay");

    // Open Compare panel
    fireEvent.click(compareBtn);
    expect(screen.getByTestId("inline-pay-compare-container")).toBeInTheDocument();
    expect(compareBtn).toHaveTextContent("Close pay comparison");

    // Close Compare panel
    fireEvent.click(compareBtn);
    expect(screen.queryByTestId("inline-pay-compare-container")).not.toBeInTheDocument();
  });

  it("opens and closes accessible methodology modal on Escape", () => {
    render(<EstimateScreen initialEstimate={sampleEstimate} />);

    const methodBtn = screen.getByRole("button", { name: /how this was calculated/i });
    fireEvent.click(methodBtn);

    const modal = screen.getByTestId("estimate-modal");
    expect(modal).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "How this was calculated" })).toBeInTheDocument();
    expect(screen.getByText(/CatBoost CQR/i)).toBeInTheDocument();

    // Dismiss with Escape key
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("estimate-modal")).not.toBeInTheDocument();
  });

  it("handles abstention state gracefully with neutral alert and fallback action", async () => {
    const abstained: AbstainedResponseData = {
      request_id: "test-abstain",
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

    render(<EstimateScreen initialEstimate={abstained} />);

    expect(screen.getByTestId("abstention-notice")).toBeInTheDocument();
    expect(screen.getByText(/We can't give a reliable range for this combination yet/i)).toBeInTheDocument();

    // Click fallback button
    await waitFor(() => {
      const fallbackBtn = screen.getByRole("button", { name: /apply/i });
      fireEvent.click(fallbackBtn);
    });

    // Form submission triggered
    expect(screen.getByTestId("profile-form")).toBeInTheDocument();
  });
});
