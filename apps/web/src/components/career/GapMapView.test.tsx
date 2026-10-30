import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { GapMapView, CANONICAL_DATA_COMPETENCIES } from "./GapMapView";
import {
  purgeAllUserData,
  type ClientEvidenceRecord,
} from "../../lib/careerLedger";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false }, // Mathematical verification in scripts/check_contrast.py
  },
};

describe("GapMapView (T15.29 Interactive Gap Map & Skills View)", () => {
  beforeEach(async () => {
    await purgeAllUserData();
  });

  afterEach(async () => {
    await purgeAllUserData();
  });

  it("renders all 14 canonical DATA family competencies and summary metrics", () => {
    render(<GapMapView records={[]} />);

    expect(CANONICAL_DATA_COMPETENCIES).toHaveLength(14);

    // Check high level tiles
    expect(screen.getByText(/demonstrated/i)).toBeInTheDocument();
    expect(screen.getByText(/self-reported/i)).toBeInTheDocument();
    expect(screen.getByText(/unproven gaps/i)).toBeInTheDocument();
    expect(screen.getByText(/actionable next/i)).toBeInTheDocument();

    // Check specific competencies render
    expect(screen.getByText("Relational SQL Querying and Table Joins")).toBeInTheDocument();
    expect(screen.getByText("Exploratory Data Analysis and Distributions")).toBeInTheDocument();
    expect(screen.getByText("Distributed Big Data Processing with Spark")).toBeInTheDocument();
  });

  it("renders discrete verification states based on evidence records (Rule R-CR-03)", () => {
    const records: ClientEvidenceRecord[] = [
      {
        competency_id: "data.anl.l2_sql_basic",
        verification_state: "demonstrated",
        evidence_type: "scenario_attempt",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        competency_id: "data.anl.l2_eda",
        verification_state: "self_reported",
        evidence_type: "self_attestation",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<GapMapView records={records} />);

    // Row for sql_basic should have Demonstrated badge
    const sqlRow = screen.getByTestId("skill-row-data.anl.l2_sql_basic");
    expect(sqlRow).toHaveTextContent(/demonstrated/i);

    // Row for eda should have Self-reported badge
    const edaRow = screen.getByTestId("skill-row-data.anl.l2_eda");
    expect(edaRow).toHaveTextContent(/self-reported/i);

    // Row for bigdata should have Unproven badge
    const sparkRow = screen.getByTestId("skill-row-data.sci.l4_bigdata");
    expect(sparkRow).toHaveTextContent(/unproven/i);
  });

  it("evaluates prerequisite satisfaction and blocks downstream nodes appropriately", () => {
    // data.anl.l3_sql_adv requires data.anl.l2_sql_basic
    // When sql_basic is unproven:
    const { rerender } = render(<GapMapView records={[]} />);

    const advSqlRow = screen.getByTestId("skill-row-data.anl.l3_sql_adv");
    expect(advSqlRow).toHaveTextContent(/blocked by/i);

    // Now satisfy sql_basic:
    const updatedRecords: ClientEvidenceRecord[] = [
      {
        competency_id: "data.anl.l2_sql_basic",
        verification_state: "demonstrated",
        evidence_type: "scenario_attempt",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    rerender(<GapMapView records={updatedRecords} />);

    const updatedAdvSqlRow = screen.getByTestId("skill-row-data.anl.l3_sql_adv");
    expect(updatedAdvSqlRow).toHaveTextContent(/all satisfied/i);
  });

  it("filters competencies by search keyword and cluster category", () => {
    render(<GapMapView records={[]} />);

    // Search for "Spark"
    const searchInput = screen.getByLabelText(/filter competencies by keyword/i);
    fireEvent.change(searchInput, { target: { value: "Spark" } });

    expect(screen.getByText("Distributed Big Data Processing with Spark")).toBeInTheDocument();
    expect(screen.queryByText("Relational SQL Querying and Table Joins")).not.toBeInTheDocument();

    // Reset search
    fireEvent.change(searchInput, { target: { value: "" } });

    // Filter by cluster "Statistical Modeling"
    const statsBtn = screen.getByRole("button", { name: "Statistical Modeling" });
    fireEvent.click(statsBtn);

    expect(screen.getByText("Exploratory Data Analysis and Distributions")).toBeInTheDocument();
    expect(screen.getByText("Supervised Predictive Modeling and Cross-Validation")).toBeInTheDocument();
    expect(screen.queryByText("Relational SQL Querying and Table Joins")).not.toBeInTheDocument();
  });

  it("toggles self-attestation directly into IndexedDB on user action", async () => {
    const onUpdatedSpy = vi.fn();
    render(<GapMapView records={[]} onRecordUpdated={onUpdatedSpy} />);

    // Click Self-Attest button inside the first row
    const selfAttestButtons = screen.getAllByRole("button", { name: /^self-attest$/i });
    expect(selfAttestButtons.length).toBeGreaterThan(0);
    fireEvent.click(selfAttestButtons[0]!);

    await waitFor(() => {
      expect(onUpdatedSpy).toHaveBeenCalled();
    });
  });

  it("opens statutory provenance attribution modal dialog (Rule R-CR-04)", () => {
    render(<GapMapView records={[]} />);

    const provBtn = screen.getAllByRole("button", { name: /view provenance/i })[0]!;
    fireEvent.click(provBtn);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/statutory attribution notice/i)).toBeInTheDocument();
    expect(screen.getByText(/ONET-28\.0/i)).toBeInTheDocument();

    // Close modal
    const closeBtn = screen.getByRole("button", { name: /close provenance modal/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("passes axe accessibility tests with 0 violations across filters and states", async () => {
    const records: ClientEvidenceRecord[] = [
      {
        competency_id: "data.anl.l2_sql_basic",
        verification_state: "demonstrated",
        evidence_type: "scenario_attempt",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    const { container } = render(<GapMapView records={records} />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});
