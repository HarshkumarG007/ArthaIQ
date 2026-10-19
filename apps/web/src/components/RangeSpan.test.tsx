import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RangeSpan, computeScaleConfig } from "./RangeSpan";

describe("computeScaleConfig", () => {
  it("produces between 4 and 8 round ticks for typical INR compensation ranges", () => {
    const scale = computeScaleConfig(24.5, 55.0, "INR");
    expect(scale.ticks.length).toBeGreaterThanOrEqual(4);
    expect(scale.ticks.length).toBeLessThanOrEqual(8);
    expect(scale.min).toBeLessThanOrEqual(24.5);
    expect(scale.max).toBeGreaterThanOrEqual(55.0);

    // Each tick should have a clean label ending in L or Cr
    for (const tick of scale.ticks) {
      expect(tick.label).toMatch(/^[0-9.]+(L|Cr)$/);
    }
  });

  it("produces between 4 and 8 round ticks for compact INR ranges", () => {
    const scale = computeScaleConfig(12.0, 18.0, "INR");
    expect(scale.ticks.length).toBeGreaterThanOrEqual(4);
    expect(scale.ticks.length).toBeLessThanOrEqual(8);
  });

  it("produces between 4 and 8 round ticks for USD ranges", () => {
    const scale = computeScaleConfig(120000, 180000, "USD");
    expect(scale.ticks.length).toBeGreaterThanOrEqual(4);
    expect(scale.ticks.length).toBeLessThanOrEqual(8);
    for (const tick of scale.ticks) {
      expect(tick.label).toMatch(/^\$[0-9.]+[kM]?$/);
    }
  });

  it("extends scale to include on-scale compareValue", () => {
    const scale = computeScaleConfig(20.0, 40.0, "INR", 50.0);
    expect(scale.max).toBeGreaterThanOrEqual(50.0);
  });
});

describe("RangeSpan component", () => {
  it("renders default engineering dimension line with accessible label and percentiles", () => {
    render(
      <RangeSpan
        p10={24.5}
        p50={38.0}
        p90={55.0}
        currency="INR"
        measure="Guaranteed cash"
        date="as of October 2026"
      />
    );

    // role="img" with generated label per design.md section 4
    const svgImg = screen.getByRole("img");
    expect(svgImg).toBeInTheDocument();
    expect(svgImg).toHaveAttribute(
      "aria-label",
      "Estimated range: from ₹24.5 lakh to ₹55.0 lakh a year. Typical value ₹38.0 lakh. Guaranteed cash, before tax, INR, as of October 2026."
    );

    // Quantile labels
    expect(screen.getAllByText("Lower end").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Typical").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Higher end").length).toBeGreaterThanOrEqual(1);

    // Dimension line exists with solid stroke
    const dimLine = screen.getByTestId("dimension-line");
    expect(dimLine).toBeInTheDocument();
    expect(dimLine).not.toHaveAttribute("stroke-dasharray");
  });

  it("renders toggleable table view alternative per design.md section 4", () => {
    const onToggle = vi.fn();
    render(
      <RangeSpan
        p10={24.5}
        p50={38.0}
        p90={55.0}
        currency="INR"
        onToggleTableView={onToggle}
      />
    );

    const toggleBtn = screen.getByRole("button", { name: /view as table/i });
    expect(toggleBtn).toBeInTheDocument();
    expect(toggleBtn).toHaveAttribute("aria-expanded", "false");

    // Table is not initially shown
    expect(screen.queryByTestId("range-span-table")).not.toBeInTheDocument();

    // Click to open table
    fireEvent.click(toggleBtn);
    expect(toggleBtn).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/hide table view/i)).toBeInTheDocument();
    expect(onToggle).toHaveBeenCalledWith(true);

    const table = screen.getByTestId("range-span-table");
    expect(table).toBeInTheDocument();

    // Verify 3 rows with definitions per design.md section 4
    expect(screen.getByText("Lower end (P10)")).toBeInTheDocument();
    expect(screen.getByText("10% of comparable professionals earn below this amount")).toBeInTheDocument();
    expect(screen.getByText("Typical (P50)")).toBeInTheDocument();
    expect(screen.getByText("Higher end (P90)")).toBeInTheDocument();

    // Verify full Indian grouping in table cell
    expect(screen.getAllByText("₹24,50,000").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("₹38,00,000").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("₹55,00,000").length).toBeGreaterThanOrEqual(1);

    // Click to close table
    fireEvent.click(toggleBtn);
    expect(screen.queryByTestId("range-span-table")).not.toBeInTheDocument();
    expect(onToggle).toHaveBeenCalledWith(false);
  });

  it("renders limited_evidence state with dashed dimension line and caution notice", () => {
    render(
      <RangeSpan
        p10={20.0}
        p50={30.0}
        p90={40.0}
        state="limited_evidence"
      />
    );

    const dimLine = screen.getByTestId("dimension-line");
    expect(dimLine).toHaveAttribute("stroke-dasharray", "6 4");

    const caution = screen.getByTestId("range-span-limited-caution");
    expect(caution).toBeInTheDocument();
    expect(caution).toHaveTextContent(/limited evidence/i);
    expect(caution).toHaveClass("text-caution");
  });

  it("renders loading state with aria-busy and static placeholder line", () => {
    render(<RangeSpan state="loading" />);

    const loadingElem = screen.getByTestId("range-span-loading");
    expect(loadingElem).toBeInTheDocument();
    expect(loadingElem).toHaveAttribute("aria-busy", "true");
    expect(loadingElem).toHaveAttribute("aria-label", "Loading salary estimate");
    expect(screen.getByText(/loading estimate/i)).toBeInTheDocument();

    // Dimension line must not be drawn
    expect(screen.queryByTestId("dimension-line")).not.toBeInTheDocument();
  });

  it("renders abstained state with calm neutral notice and NO dimension line", () => {
    render(<RangeSpan state="abstained" />);

    const abstainedElem = screen.getByTestId("range-span-abstained");
    expect(abstainedElem).toBeInTheDocument();
    expect(abstainedElem).toHaveAttribute("role", "status");
    expect(screen.getByText(/estimate abstained/i)).toBeInTheDocument();
    expect(abstainedElem).toHaveClass("bg-sunken");

    // Dimension line must never be drawn with invented numbers (DP-3, R-UI-03)
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByTestId("dimension-line")).not.toBeInTheDocument();
  });

  it("renders stale state with caution banner above dimension line", () => {
    render(
      <RangeSpan
        p10={15.0}
        p50={22.0}
        p90={32.0}
        state="stale"
      />
    );

    const banner = screen.getByTestId("range-span-stale-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/older data snapshots/i);

    // Dimension line still renders
    expect(screen.getByTestId("dimension-line")).toBeInTheDocument();
  });

  it("renders ghost span when previous prop is provided", () => {
    render(
      <RangeSpan
        p10={25.0}
        p50={35.0}
        p90={50.0}
        previous={{ p10: 20.0, p50: 30.0, p90: 45.0 }}
      />
    );

    const ghost = screen.getByTestId("ghost-span");
    expect(ghost).toBeInTheDocument();
    expect(screen.getByText("Before")).toBeInTheDocument();
  });

  it("renders compareValue diamond marker when on-scale", () => {
    render(
      <RangeSpan
        p10={20.0}
        p50={30.0}
        p90={45.0}
        compareValue={28.0}
        defaultTableView={true}
      />
    );

    const marker = screen.getByTestId("compare-marker");
    expect(marker).toBeInTheDocument();
    expect(screen.getAllByText("Your figure").length).toBeGreaterThanOrEqual(1);

    // Table view also includes "Your figure" row
    expect(screen.getByTestId("range-span-table")).toBeInTheDocument();
    expect(screen.getByText("Reference figure provided for comparison against cohort")).toBeInTheDocument();
  });

  it("renders off-scale chevrons when compareValue is far outside range", () => {
    // Span width is 20 (30 to 50). 3 * span is 60.
    // Low: < 30 - 60 = -30.
    const { rerender } = render(
      <RangeSpan
        p10={30.0}
        p50={40.0}
        p90={50.0}
        compareValue={-50.0}
      />
    );

    expect(screen.getByTestId("off-scale-low")).toBeInTheDocument();

    // High: > 50 + 60 = 110.
    rerender(
      <RangeSpan
        p10={30.0}
        p50={40.0}
        p90={50.0}
        compareValue={150.0}
      />
    );

    expect(screen.getByTestId("off-scale-high")).toBeInTheDocument();
  });

  it("renders USD estimates correctly", () => {
    render(
      <RangeSpan
        p10={120000}
        p50={150000}
        p90={180000}
        currency="USD"
        measure="Total guaranteed pay"
      />
    );

    const svgImg = screen.getByRole("img");
    expect(svgImg).toHaveAttribute(
      "aria-label",
      expect.stringContaining("$120,000 to $180,000 a year")
    );
    expect(svgImg).toHaveAttribute(
      "aria-label",
      expect.stringContaining("USD")
    );
  });
});
