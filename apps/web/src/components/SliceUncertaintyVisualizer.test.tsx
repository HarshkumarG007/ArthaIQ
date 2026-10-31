import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import axe from "axe-core";
import {
  SliceUncertaintyVisualizer,
  getConformalCoverageMultiplier,
} from "./SliceUncertaintyVisualizer";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Checked via scripts/check_contrast.py
  },
};

describe("SliceUncertaintyVisualizer (UX-18, Task T21.02)", () => {
  it("renders with default 80% coverage and full calibrated interval without lone numbers", () => {
    render(<SliceUncertaintyVisualizer baseP10={18.0} baseP50={28.5} baseP90={42.0} />);

    expect(screen.getByTestId("slice-uncertainty-visualizer")).toBeInTheDocument();
    expect(screen.getByText(/Slice-Adaptive Uncertainty Visualizer/i)).toBeInTheDocument();

    // Verify 80% coverage display
    expect(screen.getAllByText(/80%/i).length).toBeGreaterThan(0);
    // Verify interval headline (P10 - P90)
    expect(screen.getByText(/₹18.0L – ₹42.0L/i)).toBeInTheDocument();
    // Verify median indicator
    expect(screen.getByText(/Median: ₹28.5L/i)).toBeInTheDocument();
    // Verify sharpness
    expect(screen.getByText(/24.0 LPA/i)).toBeInTheDocument();
  });

  it("calculates conformal multipliers correctly", () => {
    expect(getConformalCoverageMultiplier(70)).toBe(0.85);
    expect(getConformalCoverageMultiplier(75)).toBe(0.92);
    expect(getConformalCoverageMultiplier(80)).toBe(1.0);
    expect(getConformalCoverageMultiplier(85)).toBe(1.1);
    expect(getConformalCoverageMultiplier(90)).toBe(1.25);
    expect(getConformalCoverageMultiplier(95)).toBe(1.45);
  });

  it("dynamically adjusts interval width when coverage slider changes", () => {
    const handleCoverageChange = vi.fn();
    render(
      <SliceUncertaintyVisualizer
        baseP10={18.0}
        baseP50={28.5}
        baseP90={42.0}
        onCoverageChange={handleCoverageChange}
      />
    );

    const slider = screen.getByRole("slider", { name: /Nominal confidence coverage percentage/i });

    // Step down to 70%
    fireEvent.change(slider, { target: { value: "70" } });
    expect(handleCoverageChange).toHaveBeenCalledWith(70);

    // At 70%, multiplier is 0.85 -> halfLo = 10.5 * 0.85 = 8.925 -> P10 = 28.5 - 8.9 = 19.6
    // halfHi = 13.5 * 0.85 = 11.475 -> P90 = 28.5 + 11.5 = 40.0
    expect(screen.getByText(/₹19.6L – ₹40.0L/i)).toBeInTheDocument();

    // Step up to 95%
    fireEvent.change(slider, { target: { value: "95" } });
    expect(handleCoverageChange).toHaveBeenCalledWith(95);

    // At 95%, multiplier is 1.45 -> halfLo = 10.5 * 1.45 = 15.225 -> P10 = 28.5 - 15.2 = 13.3
    // halfHi = 13.5 * 1.45 = 19.575 -> P90 = 28.5 + 19.6 = 48.1
    expect(screen.getByText(/₹13.3L – ₹48.1L/i)).toBeInTheDocument();
  });

  it("adjusts coverage using -5% and +5% stepper buttons", () => {
    render(<SliceUncertaintyVisualizer initialCoverage={80} baseP10={18.0} baseP50={28.5} baseP90={42.0} />);

    const decBtn = screen.getByRole("button", { name: /Decrease coverage by 5%/i });
    const incBtn = screen.getByRole("button", { name: /Increase coverage by 5%/i });

    // Click decrease
    fireEvent.click(decBtn);
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "75");

    // Click increase twice -> 85%
    fireEvent.click(incBtn);
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "80");
    fireEvent.click(incBtn);
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "85");
  });

  it("switches tabs between Metro Hubs and Seniority Strata", () => {
    render(<SliceUncertaintyVisualizer />);

    // Initially in Metro tab
    expect(screen.getByTestId("slice-card-blr")).toBeInTheDocument();
    expect(screen.getByTestId("slice-card-hyd")).toBeInTheDocument();
    expect(screen.getByText("Bengaluru")).toBeInTheDocument();
    expect(screen.getByText("Hyderabad")).toBeInTheDocument();

    // Click Seniority tab
    const seniorityTab = screen.getByRole("tab", { name: /Seniority Strata/i });
    fireEvent.click(seniorityTab);

    // Now seniority slices are rendered
    expect(screen.getByTestId("slice-card-jr")).toBeInTheDocument();
    expect(screen.getByTestId("slice-card-mid")).toBeInTheDocument();
    expect(screen.getByText("Junior (0–2 yrs)")).toBeInTheDocument();
    expect(screen.getByText("Mid-Level (3–5 yrs)")).toBeInTheDocument();
  });

  it("toggles accessible data table view", () => {
    render(<SliceUncertaintyVisualizer />);

    expect(screen.queryByRole("table")).toBeNull();

    const toggleBtn = screen.getByRole("button", { name: /View as accessible data table/i });
    fireEvent.click(toggleBtn);

    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
    expect(screen.getByText("Detailed empirical slice diagnostics table", { exact: false })).toBeInTheDocument();
    expect(within(table).getByText("Bengaluru")).toBeInTheDocument();
    expect(within(table).getByText("Hyderabad")).toBeInTheDocument();

    // Toggle off
    fireEvent.click(screen.getByRole("button", { name: /Hide accessible data table/i }));
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("displays statutory anti-causal and zero lone numbers disclaimers", () => {
    render(<SliceUncertaintyVisualizer />);

    expect(screen.getByText(/Statutory Disclaimer \(Rule R-CR-01 & Consumer Protection Act 2019\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Acquiring skills, completing practice scenarios, or relocating carries zero causal pay guarantee/i)).toBeInTheDocument();
    expect(screen.getByText(/Rule R-UQ-01 Enforcement: Solitary salary point estimates are strictly forbidden/i)).toBeInTheDocument();
  });

  it("passes automated accessibility audit with 0 Axe violations", async () => {
    const { container } = render(<SliceUncertaintyVisualizer />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});
