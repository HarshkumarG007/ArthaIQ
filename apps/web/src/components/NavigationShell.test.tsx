import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { NavigationShell } from "./NavigationShell";
import { purgeAllUserData } from "../lib/careerLedger";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Mathematical verification in scripts/check_contrast.py
  },
};

describe("NavigationShell (T15.28 Responsive Layout & Navigation)", () => {
  beforeEach(async () => {
    window.location.hash = "";
    await purgeAllUserData();
  });

  afterEach(async () => {
    await purgeAllUserData();
  });

  it("renders desktop rail and mobile bottom navigation with both modes", () => {
    render(<NavigationShell initialMode="compensation" />);

    // Check desktop rail items
    expect(screen.getByRole("button", { name: /^compensation$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /career architect/i })).toBeInTheDocument();

    // Check mobile buttons
    expect(screen.getByRole("button", { name: /^pay$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^career$/i })).toBeInTheDocument();
  });

  it("switches from compensation to career mode on click", async () => {
    render(<NavigationShell initialMode="compensation" />);

    // Initially shows Compensation Estimate form
    expect(screen.getByRole("button", { name: /show estimated range/i })).toBeInTheDocument();

    // Click Career Architect
    const careerBtn = screen.getByRole("button", { name: /career architect/i });
    fireEvent.click(careerBtn);

    // Now shows Career target / setup
    await waitFor(() => {
      expect(screen.getByText(/local-first storage/i)).toBeInTheDocument();
    });
    expect(window.location.hash).toContain("#career");
  });

  it("synchronizes navigation mode from window.location.hash", async () => {
    window.location.hash = "#career/plan";
    render(<NavigationShell />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /topological roadmap/i })).toBeInTheDocument();
    });
  });

  it("opens and closes share your pay and my data modal dialogs", async () => {
    render(<NavigationShell initialMode="compensation" />);

    // Open contribution modal
    const shareBtn = screen.getByRole("button", { name: /share your pay/i });
    fireEvent.click(shareBtn);

    expect(screen.getByRole("dialog", { name: /contribute your pay data/i })).toBeInTheDocument();

    // Close modal
    const closeBtn = screen.getByRole("button", { name: /close contribution form/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByRole("dialog", { name: /contribute your pay data/i })).not.toBeInTheDocument();

    // Open My Data modal
    const myDataBtns = screen.getAllByRole("button", { name: /^my data$/i });
    expect(myDataBtns.length).toBeGreaterThan(0);
    const myDataBtn = myDataBtns[0];
    if (myDataBtn) {
      fireEvent.click(myDataBtn);
    }

    expect(screen.getByRole("dialog", { name: /delete my data/i })).toBeInTheDocument();
  });

  it("passes axe accessibility tests with 0 violations in compensation mode", async () => {
    const { container } = render(<NavigationShell initialMode="compensation" />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });

  it("passes axe accessibility tests with 0 violations in career mode", async () => {
    const { container } = render(<NavigationShell initialMode="career" />);
    await waitFor(() => {
      expect(screen.getByText(/local-first storage/i)).toBeInTheDocument();
    });
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});

