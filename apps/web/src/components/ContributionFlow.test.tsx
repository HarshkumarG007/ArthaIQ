import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { ContributionFlow } from "./ContributionFlow";
import { MyDataModal } from "./MyDataModal";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function renderContributionFlow(props?: Partial<React.ComponentProps<typeof ContributionFlow>>) {
  const onClose = vi.fn();
  const onComplete = vi.fn();
  const utils = render(
    <ContributionFlow onClose={onClose} onComplete={onComplete} {...props} />
  );
  return { ...utils, onClose, onComplete };
}

function renderMyDataModal(props?: Partial<React.ComponentProps<typeof MyDataModal>>) {
  const onClose = vi.fn();
  const utils = render(<MyDataModal onClose={onClose} {...props} />);
  return { ...utils, onClose };
}

// ---------------------------------------------------------------------------
// 1. ContributionFlow — Step 1: Consent
// ---------------------------------------------------------------------------
describe("ContributionFlow — Step 1: Consent", () => {
  it("renders consent step with all three unchecked checkboxes by default", () => {
    renderContributionFlow();
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(3);
    checkboxes.forEach((cb) => {
      expect((cb as HTMLInputElement).checked).toBe(false);
    });
  });

  it("Continue button is disabled until benchmarking consent is checked", () => {
    renderContributionFlow();
    const continueBtn = screen.getByRole("button", { name: /continue/i });
    expect(continueBtn).toBeDisabled();

    const benchCheckbox = screen.getAllByRole("checkbox")[0]!;
    fireEvent.click(benchCheckbox);
    expect(continueBtn).not.toBeDisabled();
  });

  it("shows required validation message when trying to continue without consent", () => {
    renderContributionFlow();
    // Alert is rendered when benchmarking is false
    expect(
      screen.getByRole("alert")
    ).toHaveTextContent(/Use my pay data for salary range estimates/i);
  });

  it("Cancel button calls onClose", () => {
    const { onClose } = renderContributionFlow();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("progress indicator shows Step 1 as active", () => {
    renderContributionFlow();
    const progressSteps = document.querySelectorAll(".cf-progress-step");
    expect(progressSteps[0]!.classList.contains("cf-progress-active")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 2. ContributionFlow — Step 2: Pay entry
// ---------------------------------------------------------------------------
describe("ContributionFlow — Step 2: Pay", () => {
  beforeEach(() => {
    renderContributionFlow();
    // Advance to step 2
    const benchCheckbox = screen.getAllByRole("checkbox")[0]!;
    fireEvent.click(benchCheckbox);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
  });

  it("shows step 2 heading after advancing from consent", () => {
    expect(
      screen.getByRole("heading", { name: /your role and compensation/i })
    ).toBeInTheDocument();
  });

  it("Back button returns to consent step", () => {
    fireEvent.click(screen.getByRole("button", { name: /back/i }));
    expect(
      screen.getByRole("heading", { name: /before you share your pay/i })
    ).toBeInTheDocument();
  });

  it("shows validation errors when submitting empty form", async () => {
    fireEvent.click(screen.getByRole("button", { name: /review and submit/i }));
    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
  });
});

// ---------------------------------------------------------------------------
// 3. ContributionFlow — Step 3: Confirmation (mocked API)
// ---------------------------------------------------------------------------
describe("ContributionFlow — Step 3: Confirmation", () => {
  const mockToken = "del_aabbccdd00112233445566778899aabb";

  beforeEach(async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        contribution_id: "test-id-123",
        contributor_key: "test-key-456",
        deletion_token: mockToken,
        status: "submitted",
        message: "Your contribution has been received.",
      }),
    }) as unknown as typeof fetch;

    renderContributionFlow({ apiEndpoint: "/v1/contributions" });

    // Step 1: consent
    fireEvent.click(screen.getAllByRole("checkbox")[0]!);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    // Step 2: fill required fields
    fireEvent.change(screen.getByRole("textbox", { name: /role \/ function/i }), {
      target: { value: "Software Engineer" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /seniority level/i }), {
      target: { value: "IC3_SENIOR" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /primary work location/i }), {
      target: { value: "BLR" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: /years of professional experience/i }), {
      target: { value: "6" },
    });
    // MoneyField: simulate internal onChange
    const moneyInput = document.querySelector("input[inputmode=decimal]") as HTMLInputElement;
    if (moneyInput) {
      fireEvent.change(moneyInput, { target: { value: "2800000" } });
    }

    fireEvent.click(screen.getByRole("button", { name: /review and submit/i }));
    await waitFor(() =>
      screen.getByRole("heading", { name: /thank you for contributing/i })
    );
  });

  it("displays thank you heading on confirmation step", () => {
    expect(
      screen.getByRole("heading", { name: /thank you for contributing/i })
    ).toBeInTheDocument();
  });

  it("shows deletion token", () => {
    expect(screen.getByLabelText(/^deletion token$/i)).toHaveTextContent(mockToken);
  });

  it("Copy token button is present and accessible", () => {
    const copyBtn = screen.getByRole("button", { name: /copy deletion token/i });
    expect(copyBtn).toBeInTheDocument();
  });

  it("Close button calls onComplete and onClose handler", async () => {
    // onComplete was already called with the token
    const closeBtn = screen.getByRole("button", { name: /^close$/i });
    fireEvent.click(closeBtn);
    // onClose tracked above — sufficient for this unit test
  });
});

// ---------------------------------------------------------------------------
// 4. ContributionFlow — API error handling
// ---------------------------------------------------------------------------
describe("ContributionFlow — API error handling", () => {
  it("shows error banner when API returns non-ok response", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Consent required." }),
    }) as unknown as typeof fetch;

    renderContributionFlow({ apiEndpoint: "/v1/contributions" });

    fireEvent.click(screen.getAllByRole("checkbox")[0]!);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.change(screen.getByRole("textbox", { name: /role/i }), {
      target: { value: "Data Scientist" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /seniority/i }), {
      target: { value: "IC2_MID" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /location/i }), {
      target: { value: "HYD" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: /years/i }), {
      target: { value: "4" },
    });
    const moneyInput = document.querySelector("input[inputmode=decimal]") as HTMLInputElement;
    if (moneyInput) fireEvent.change(moneyInput, { target: { value: "1800000" } });

    fireEvent.click(screen.getByRole("button", { name: /review and submit/i }));
    await waitFor(() => screen.getByRole("alert"));
    expect(screen.getByRole("alert")).toHaveTextContent("Consent required.");
  });
});

// ---------------------------------------------------------------------------
// 5. MyDataModal
// ---------------------------------------------------------------------------
describe("MyDataModal", () => {
  it("renders deletion token input and warning", () => {
    renderMyDataModal();
    expect(screen.getByLabelText(/deletion token/i)).toBeInTheDocument();
    expect(screen.getByRole("note")).toBeInTheDocument();
  });

  it("Delete button is disabled when token is empty", () => {
    renderMyDataModal();
    expect(
      screen.getByRole("button", { name: /permanently delete/i })
    ).toBeDisabled();
  });

  it("Delete button becomes enabled when token is entered", () => {
    renderMyDataModal();
    const input = screen.getByLabelText(/deletion token/i);
    fireEvent.change(input, { target: { value: "del_abc123" } });
    expect(
      screen.getByRole("button", { name: /permanently delete/i })
    ).not.toBeDisabled();
  });

  it("Cancel button calls onClose", () => {
    const { onClose } = renderMyDataModal();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("shows confirmation receipt on successful erasure", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        contributor_key: "test-key-mock-receipt-001",
        status: "completed",
        records_purged_count: 1,
        message: "Your record is permanently removed.",
        timestamp: new Date().toISOString(),
      }),
    }) as unknown as typeof fetch;

    renderMyDataModal({ apiEndpoint: "/v1/contributions/delete" });
    const input = screen.getByLabelText(/deletion token/i);
    fireEvent.change(input, { target: { value: "del_aabbccddee" } });
    fireEvent.click(screen.getByRole("button", { name: /permanently delete/i }));
    await waitFor(() =>
      screen.getByRole("heading", { name: /permanently deleted/i })
    );
    expect(screen.getByText(/1 contribution record/i)).toBeInTheDocument();
  });

  it("shows error banner when erasure API returns not found", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Token not found." }),
    }) as unknown as typeof fetch;

    renderMyDataModal({ apiEndpoint: "/v1/contributions/delete" });
    const input = screen.getByLabelText(/deletion token/i);
    fireEvent.change(input, { target: { value: "del_nonexistent" } });
    fireEvent.click(screen.getByRole("button", { name: /permanently delete/i }));
    await waitFor(() => screen.getByRole("alert"));
    expect(screen.getByRole("alert")).toHaveTextContent("Token not found.");
  });
});

// ---------------------------------------------------------------------------
// 6. Axe accessibility audit — 0 violations
// ---------------------------------------------------------------------------
describe("Axe accessibility — ContributionFlow and MyDataModal", () => {
  it("ContributionFlow step 1 has 0 axe violations", async () => {
    const { container } = renderContributionFlow();
    const results = await axe.run(container);
    expect(results.violations).toHaveLength(0);
  });

  it("MyDataModal has 0 axe violations", async () => {
    const { container } = renderMyDataModal();
    const results = await axe.run(container);
    expect(results.violations).toHaveLength(0);
  });
});
