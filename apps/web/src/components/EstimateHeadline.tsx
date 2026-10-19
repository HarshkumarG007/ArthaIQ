import React from "react";
import { formatMoney, formatRange } from "../lib/formatMoney";
import { DefinitionPopover } from "./DefinitionPopover";

export interface EstimateHeadlineProps {
  p10: number;
  p50: number;
  p90: number;
  currency?: string;
  unit?: "lpa" | "rupees" | "raw";
  measure?: string;
  date?: string;
  className?: string;
}

/**
 * EstimateHeadline — The statistical headline presentation.
 * Per design.md section 8:
 * 1. Title: "Estimated range" (serif title).
 * 2. Display line: `₹{p10} to ₹{p90} lakh a year` (or USD).
 * 3. Typical line: "Typical: ₹{p50} lakh" in body, --ink-2.
 * 4. Definition sentence: "{Measure}, before tax, in rupees, as of {Month YYYY}."
 *    The measure name is a DefinitionPopover trigger.
 */
export function EstimateHeadline({
  p10,
  p50,
  p90,
  currency = "INR",
  unit = "lpa",
  measure = "Guaranteed cash",
  date = "October 2026",
  className = "",
}: EstimateHeadlineProps): React.JSX.Element {
  const isINR = currency.toUpperCase() === "INR";
  const displayRange = formatRange(p10, p90, { currency, unit });
  const typicalStr = formatMoney(p50, { currency, unit, style: "headline" });

  const currencyWord = isINR ? "in rupees" : "in US dollars";

  return (
    <section
      data-testid="estimate-headline"
      className={`text-left ${className}`}
      aria-labelledby="estimate-headline-title"
    >
      <h2
        id="estimate-headline-title"
        className="text-xs font-sans font-semibold uppercase tracking-wider text-ink-3 mb-1.5"
      >
        Estimated range
      </h2>

      {/* Display Line in Serif 600 */}
      <div
        data-testid="headline-display-range"
        className="text-3xl sm:text-4xl font-serif font-semibold tracking-tight text-ink mb-1.5 tabular-nums"
      >
        {displayRange}
      </div>

      {/* Typical Line in body --ink-2 */}
      <p className="text-sm font-sans text-ink-2">
        Typical:{" "}
        <span
          data-testid="headline-typical-amount"
          className="font-serif font-semibold text-ink tabular-nums"
        >
          {typicalStr}
        </span>
      </p>

      {/* Definition Sentence with Popover Trigger */}
      <p className="text-xs font-sans text-ink-3 mt-2 flex flex-wrap items-center gap-x-1 gap-y-0.5">
        <DefinitionPopover
          term={measure}
          definition="Base salary and contractual cash allowances paid unconditionally before tax, excluding discretionary bonuses or unvested equity (PT1 target measure per ADR-0002)."
        />
        <span>, before tax, {currencyWord}, as of {date}.</span>
      </p>
    </section>
  );
}

export default EstimateHeadline;
