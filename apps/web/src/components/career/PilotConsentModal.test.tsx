import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { PilotConsentModal } from "./PilotConsentModal";
import { getPilotConsent, clearPilotConsent } from "../../lib/pilotConsent";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Checked independently via scripts/check_contrast.py
  },
};

describe("PilotConsentModal (T20.01 Statutory Onboarding & Privacy Gateway)", () => {
  beforeEach(() => {
    clearPilotConsent();
    localStorage.clear();
  });

  it("does not render when isOpen is false", () => {
    const handleConsent = vi.fn();
    render(<PilotConsentModal isOpen={false} onConsent={handleConsent} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders statutory notices and disables submit button initially", () => {
    const handleConsent = vi.fn();
    render(<PilotConsentModal isOpen={true} onConsent={handleConsent} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/ArthaIQ Career Architect — Pilot Consent/i)).toBeInTheDocument();
    expect(screen.getByText(/India DPDP Act 2023 & CPA 2019/i)).toBeInTheDocument();

    // Verify statutory notices
    expect(screen.getByText(/Voluntary Decision Support/i)).toBeInTheDocument();
    expect(screen.getByText(/Local-First Privacy/i)).toBeInTheDocument();
    expect(screen.getByText(/Practice, Not Certification/i)).toBeInTheDocument();
    expect(screen.getByText(/Right to Erasure/i)).toBeInTheDocument();

    // Verify submit button is disabled
    const submitBtn = screen.getByRole("button", { name: /Agree & Begin Pilot/i });
    expect(submitBtn).toBeDisabled();
  });

  it("enables submit button only when all three mandatory declarations are checked", () => {
    const handleConsent = vi.fn();
    render(<PilotConsentModal isOpen={true} onConsent={handleConsent} />);

    const submitBtn = screen.getByRole("button", { name: /Agree & Begin Pilot/i });
    const ageBox = screen.getByLabelText(/Age Verification/i);
    const voluntaryBox = screen.getByLabelText(/Voluntary Participation/i);
    const nonAppraisalBox = screen.getByLabelText(/Non-Appraisal Notice/i);

    expect(submitBtn).toBeDisabled();

    fireEvent.click(ageBox);
    expect(submitBtn).toBeDisabled();

    fireEvent.click(voluntaryBox);
    expect(submitBtn).toBeDisabled();

    fireEvent.click(nonAppraisalBox);
    expect(submitBtn).not.toBeDisabled();

    // Unchecking one should disable again
    fireEvent.click(ageBox);
    expect(submitBtn).toBeDisabled();
  });

  it("submits consent record to local storage and invokes onConsent callback", async () => {
    const handleConsent = vi.fn();
    render(
      <PilotConsentModal
        isOpen={true}
        onConsent={handleConsent}
        initialStratification={{
          role_family: "MLAI",
          seniority_band: "senior",
          geographic_cluster: "HYD",
        }}
      />
    );

    fireEvent.click(screen.getByLabelText(/Age Verification/i));
    fireEvent.click(screen.getByLabelText(/Voluntary Participation/i));
    fireEvent.click(screen.getByLabelText(/Non-Appraisal Notice/i));

    const submitBtn = screen.getByRole("button", { name: /Agree & Begin Pilot/i });
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    expect(handleConsent).toHaveBeenCalledTimes(1);
    const callArgs = handleConsent.mock.calls[0];
    expect(callArgs).toBeDefined();
    const submitted = callArgs![0];
    expect(submitted.consent_version).toBe("2026-10-dpdp-v1");
    expect(submitted.age_confirmed_18_plus).toBe(true);
    expect(submitted.stratification.role_family).toBe("MLAI");
    expect(submitted.stratification.seniority_band).toBe("senior");
    expect(submitted.stratification.geographic_cluster).toBe("HYD");

    // Verify persisted in localStorage
    const stored = getPilotConsent();
    expect(stored).not.toBeNull();
    expect(stored?.stratification.role_family).toBe("MLAI");
  });

  it("calls onPurgeAllData and unchecks form when Erase button is clicked", async () => {
    const handleConsent = vi.fn();
    const handlePurge = vi.fn().mockResolvedValue(undefined);

    render(
      <PilotConsentModal
        isOpen={true}
        onConsent={handleConsent}
        onPurgeAllData={handlePurge}
      />
    );

    const ageBox = screen.getByLabelText(/Age Verification/i);
    fireEvent.click(ageBox);
    expect(ageBox).toBeChecked();

    const purgeBtn = screen.getByRole("button", { name: /Erase All My Data/i });
    fireEvent.click(purgeBtn);

    await waitFor(() => {
      expect(handlePurge).toHaveBeenCalledTimes(1);
    });

    expect(
      screen.getByText(/All on-device user data has been permanently erased. 0 bytes retained./i)
    ).toBeInTheDocument();
    expect(ageBox).not.toBeChecked();
  });

  it("passes axe accessibility tests with 0 violations", async () => {
    const handleConsent = vi.fn();
    const { container } = render(
      <PilotConsentModal
        isOpen={true}
        onConsent={handleConsent}
        onClose={vi.fn()}
        onPurgeAllData={vi.fn().mockResolvedValue(undefined)}
      />
    );

    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});
