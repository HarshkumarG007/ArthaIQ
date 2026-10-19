import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DefinitionPopover } from "./DefinitionPopover";
import { EstimateHeadline } from "./EstimateHeadline";
import { EvidenceGauge } from "./EvidenceGauge";
import { EvidenceList } from "./EvidenceList";
import { AbstentionNotice } from "./AbstentionNotice";
import { DisclaimerLine } from "./DisclaimerLine";
import { ProfileForm } from "./ProfileForm";
import { computeSimulatedEstimate } from "../lib/api";

describe("DefinitionPopover", () => {
  it("opens popover on click and closes on Escape returning focus", () => {
    render(
      <DefinitionPopover
        term="Guaranteed cash"
        definition="Base annual cash pay before tax, excluding discretionary bonuses."
      />
    );

    const trigger = screen.getByRole("button", { name: "Guaranteed cash" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("definition-popover")).not.toBeInTheDocument();

    // Open popover
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    const popover = screen.getByTestId("definition-popover");
    expect(popover).toBeInTheDocument();
    expect(screen.getByText(/Base annual cash pay before tax/i)).toBeInTheDocument();

    // Close on Escape
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByTestId("definition-popover")).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });
});

describe("EstimateHeadline", () => {
  it("renders range, typical amount, and definition sentence per design.md section 8", () => {
    render(
      <EstimateHeadline
        p10={24.5}
        p50={38.0}
        p90={55.0}
        currency="INR"
        measure="Guaranteed cash"
        date="October 2026"
      />
    );

    expect(screen.getByRole("heading", { name: /estimated range/i })).toBeInTheDocument();
    expect(screen.getByTestId("headline-display-range")).toHaveTextContent("₹24.5 to ₹55.0 lakh a year");
    expect(screen.getByTestId("headline-typical-amount")).toHaveTextContent("₹38.0 lakh");
    expect(screen.getByText(/before tax, in rupees, as of October 2026/i)).toBeInTheDocument();
  });
});

describe("EvidenceGauge", () => {
  it("renders 3 discrete ticks for Strong (GRADE_A) per Rule R-UI-02", () => {
    render(<EvidenceGauge grade="GRADE_A" />);
    const meter = screen.getByRole("meter");
    expect(meter).toHaveAttribute("aria-valuenow", "3");
    expect(meter).toHaveAttribute("aria-valuetext", "Strong");
    expect(screen.getByText("Strong")).toBeInTheDocument();
  });

  it("renders 2 discrete ticks for Moderate (GRADE_B)", () => {
    render(<EvidenceGauge grade="GRADE_B" />);
    const meter = screen.getByRole("meter");
    expect(meter).toHaveAttribute("aria-valuenow", "2");
    expect(meter).toHaveAttribute("aria-valuetext", "Moderate");
    expect(screen.getByText("Moderate")).toBeInTheDocument();
  });

  it("renders 1 discrete tick in caution styling for Limited (GRADE_C)", () => {
    render(<EvidenceGauge grade="GRADE_C" />);
    const meter = screen.getByRole("meter");
    expect(meter).toHaveAttribute("aria-valuenow", "1");
    expect(meter).toHaveAttribute("aria-valuetext", "Limited");
    const word = screen.getByText("Limited");
    expect(word).toHaveClass("text-caution");
  });
});

describe("EvidenceList", () => {
  it("renders definition list rows with records, sources, recency, and known limits", () => {
    render(
      <EvidenceList
        grade="GRADE_A"
        cohortN={142}
        sourceMix={[
          { source_type: "statutory_filing", share: 0.65 },
          { source_type: "voluntary_intake", share: 0.35 },
        ]}
        medianAgeDays={72}
        modelVersion="0.1.0"
        dataSnapshotId="SNAP-CANONICAL-20261018"
        newestDate="October 2026"
      />
    );

    expect(screen.getByText("What this is based on")).toBeInTheDocument();
    expect(screen.getByText("142 records from 2 sources")).toBeInTheDocument();
    expect(screen.getByText("statutory filings 65%, verified contributions 35%")).toBeInTheDocument();
    expect(screen.getByText("Median record age 2 months; newest October 2026")).toBeInTheDocument();
    expect(screen.getByText("0.1.0 · SNAP-CANONICAL-20261018")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /read model card/i })).toBeInTheDocument();
  });
});

describe("AbstentionNotice", () => {
  it("renders calm neutral notice on sunken background without error colors per Rule R-UI-03", () => {
    const onFallback = vi.fn();
    render(
      <AbstentionNotice
        reasons={[
          {
            code: "INSUFFICIENT_SUPPORT",
            detail: "We have too few comparable records for this combination.",
          },
        ]}
        nearestSupportedLocation="Bengaluru"
        onSelectFallback={onFallback}
      />
    );

    const notice = screen.getByTestId("abstention-notice");
    expect(notice).toHaveClass("bg-sunken");
    expect(notice).not.toHaveClass("bg-alert");
    expect(notice).not.toHaveClass("bg-caution");
    expect(screen.getByText(/We can't give a reliable range for this combination yet/i)).toBeInTheDocument();
    expect(screen.getByText("What you can try")).toBeInTheDocument();

    // Actionable fallback
    const tryBtn = screen.getByRole("button", { name: /try bengaluru/i });
    fireEvent.click(tryBtn);
    expect(onFallback).toHaveBeenCalledWith("location", "Bengaluru");
  });
});

describe("DisclaimerLine", () => {
  it("renders exact required statutory wording per PRD FR-18", () => {
    render(<DisclaimerLine />);
    const disclaimer = screen.getByTestId("disclaimer-line");
    expect(disclaimer).toHaveTextContent(
      "This range is an estimate from data of varying quality. It is not an offer, appraisal or guarantee."
    );
  });
});

describe("ProfileForm", () => {
  it("submits validated profile parameters", () => {
    const onSubmit = vi.fn();
    render(
      <ProfileForm
        initialValues={{
          occupation_id: "SWE",
          location_id: "BENGALURU",
          years_experience: 5.0,
        }}
        onSubmit={onSubmit}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /show estimated range/i });
    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledWith({
      occupation_id: "SWE",
      location_id: "BENGALURU",
      years_experience: 5.0,
      not_sure_experience: false,
      seniority_level: undefined,
    });
  });

  it("validates out-of-range experience and displays error summary", () => {
    const onSubmit = vi.fn();
    render(
      <ProfileForm
        initialValues={{
          occupation_id: "SWE",
          location_id: "BENGALURU",
          years_experience: 45.0,
        }}
        onSubmit={onSubmit}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /show estimated range/i });
    fireEvent.click(submitBtn);

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("form-error-summary")).toBeInTheDocument();
    expect(screen.getByText(/Experience must be between 0 and 40 years/i)).toBeInTheDocument();
  });

  it("toggles 'Not sure' mode and permits seniority level selection", () => {
    const onSubmit = vi.fn();
    render(<ProfileForm onSubmit={onSubmit} />);

    const notSureCheckbox = screen.getByLabelText(/not sure/i);
    fireEvent.click(notSureCheckbox);

    // Number input should disappear; seniority select appears
    expect(screen.queryByPlaceholderText(/e\.g\. 4\.5/i)).not.toBeInTheDocument();
    expect(screen.getByText(/We will estimate compensation based on your approximate career tier/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /show estimated range/i });
    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        not_sure_experience: true,
        years_experience: null,
      })
    );
  });
});

describe("computeSimulatedEstimate API", () => {
  it("returns calibrated quantiles and evidence for standard query", () => {
    const res = computeSimulatedEstimate({
      occupation_id: "SWE",
      location_id: "BENGALURU",
      years_experience: 4.0,
      not_sure_experience: false,
    });

    expect(res.status).toBe("ok");
    if (res.status === "ok") {
      expect(res.estimate.p10).toBeLessThan(res.estimate.p50);
      expect(res.estimate.p50).toBeLessThan(res.estimate.p90);
      expect(res.evidence.cohort_n).toBeGreaterThan(0);
      expect(res.reliability.grade).toBe("GRADE_A");
    }
  });

  it("abstains on out-of-range experience per Rule R-MD-08", () => {
    const res = computeSimulatedEstimate({
      occupation_id: "SWE",
      location_id: "BENGALURU",
      years_experience: -5.0,
      not_sure_experience: false,
    });

    expect(res.status).toBe("abstained");
    if (res.status === "abstained") {
      expect(res.reasons[0]?.code).toBe("OUT_OF_RANGE");
    }
  });
});
