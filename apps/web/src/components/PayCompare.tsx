import React, { useState } from "react";
import { RangeSpan } from "./RangeSpan";
import { MoneyField, CompensationMeasureType, PayPeriod, MEASURE_OPTIONS } from "./MoneyField";

export interface PayCompareEstimate {
  p10: number;
  p50: number;
  p90: number;
  currency?: string;
  unit?: "lpa" | "rupees" | "raw";
  measure?: string;
  date?: string;
}

export interface PayCompareProps {
  currentEstimate: PayCompareEstimate;
  initialValue?: number | null;
  onCompareChange?: (
    valLpa: number | null,
    period: PayPeriod,
    measureType: CompensationMeasureType
  ) => void;
  className?: string;
}

/**
 * Returns ordinal string e.g. 1st, 2nd, 3rd, 10th, 25th, etc.
 */
function getOrdinal(n: number): string {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 13) {
    return `${n}th`;
  }
  const mod10 = n % 10;
  if (mod10 === 1) return `${n}st`;
  if (mod10 === 2) return `${n}nd`;
  if (mod10 === 3) return `${n}rd`;
  return `${n}th`;
}

/**
 * PayCompare — Compare-only positioning view adhering to design.md section 8 and Rule R-MD-13.
 *
 * Invariants:
 * - Current pay is strictly compare-only; never feeds back into model estimates (R-MD-13).
 * - Never use "underpaid" or "overpaid".
 * - Always includes: "Your pay may reflect things this estimate does not include, such as scope, employer or timing."
 * - When measure differs from guaranteed cash, shows definition mismatch caution banner.
 */
export function PayCompare({
  currentEstimate,
  initialValue = null,
  onCompareChange,
  className = "",
}: PayCompareProps): React.JSX.Element {
  const [userLpa, setUserLpa] = useState<number | null>(initialValue);
  const [, setUserPeriod] = useState<PayPeriod>("annual");
  const [userMeasure, setUserMeasure] = useState<CompensationMeasureType>("guaranteed_cash");

  const estimateMeasure = currentEstimate.measure || "guaranteed cash pay";

  const handleMoneyChange = (
    valLpa: number | null,
    period: PayPeriod,
    measure: CompensationMeasureType
  ): void => {
    setUserLpa(valLpa);
    setUserPeriod(period);
    setUserMeasure(measure);
    if (onCompareChange) {
      onCompareChange(valLpa, period, measure);
    }
  };

  // Compute position sentence and percentile band
  let positionSentence: string | null = null;
  let percentileSentence: string | null = null;

  if (userLpa !== null && !isNaN(userLpa) && userLpa > 0) {
    const { p10, p50, p90 } = currentEstimate;

    if (userLpa < p10) {
      positionSentence = "Your figure is below the estimated range.";
      percentileSentence =
        "It sits around the 1st to 10th percentile of comparable pay. The band is wide because the estimate itself is uncertain.";
    } else if (userLpa > p90) {
      positionSentence = "Your figure is above the estimated range.";
      percentileSentence =
        "It sits around the 90th to 99th percentile of comparable pay. The band is wide because the estimate itself is uncertain.";
    } else {
      positionSentence = "Your figure is inside the estimated range.";

      // Interpolate approximate percentile with uncertainty band
      let pointPercentile: number;
      if (userLpa <= p50) {
        const spanLower = Math.max(0.01, p50 - p10);
        const frac = (userLpa - p10) / spanLower;
        pointPercentile = 10 + frac * 40; // 10 to 50
      } else {
        const spanUpper = Math.max(0.01, p90 - p50);
        const frac = (userLpa - p50) / spanUpper;
        pointPercentile = 50 + frac * 40; // 50 to 90
      }

      // Round to clean uncertainty band of ~15-20 points
      const lower = Math.max(5, Math.floor((pointPercentile - 8) / 5) * 5);
      const upper = Math.min(95, Math.ceil((pointPercentile + 8) / 5) * 5);

      percentileSentence = `It sits around the ${getOrdinal(lower)} to ${getOrdinal(
        upper
      )} percentile of comparable pay. The band is wide because the estimate itself is uncertain.`;
    }
  }

  // Definition mismatch check
  const isDefinitionMismatch = userMeasure !== "guaranteed_cash";
  const selectedMeasureLabel =
    MEASURE_OPTIONS.find((m) => m.id === userMeasure)?.label.split(" (")[0] || userMeasure;

  return (
    <div
      data-testid="pay-compare"
      className={`flex flex-col gap-6 p-5 sm:p-6 bg-sheet rounded-control border border-rule text-left ${className}`}
    >
      <div className="flex flex-col gap-1 border-b border-rule pb-3">
        <h3 className="text-base font-serif font-semibold text-ink">Compare with my pay</h3>
        <p className="text-xs font-sans text-ink-3">
          See how your compensation compares against the conditional market cohort. Your figure is
          never stored or used to train models.
        </p>
      </div>

      {/* Input component */}
      <MoneyField
        label="Enter your current compensation"
        helperText="Enter either annual pay or monthly take-home."
        value={userLpa}
        currency={currentEstimate.currency || "INR"}
        onChange={handleMoneyChange}
      />

      {/* Definition mismatch caution banner per design.md section 10 */}
      {isDefinitionMismatch && userLpa !== null && (
        <div
          data-testid="definition-mismatch-banner"
          role="note"
          className="flex items-start gap-2.5 p-3.5 bg-caution-wash border border-caution rounded-control text-xs font-sans text-caution"
        >
          <svg
            className="w-4 h-4 shrink-0 mt-0.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <p>
            You chose <span className="font-semibold">{selectedMeasureLabel}</span>, but this range
            is for <span className="font-semibold">{estimateMeasure}</span>. The comparison may be
            off.
          </p>
        </div>
      )}

      {/* Result Statements and Marker */}
      {userLpa !== null && (
        <div data-testid="pay-compare-results" className="flex flex-col gap-4">
          <div className="flex flex-col gap-1 p-3.5 bg-sunken rounded-control border border-rule text-xs font-sans">
            <p className="font-semibold text-ink" data-testid="position-sentence">
              {positionSentence}
            </p>
            <p className="text-ink-2" data-testid="percentile-sentence">
              {percentileSentence}
            </p>
            <p className="text-ink-3 pt-1 border-t border-rule mt-1 font-sans text-[11px]">
              Your pay may reflect things this estimate does not include, such as scope, employer or
              timing.
            </p>
          </div>

          {/* RangeSpan with compareValue marker */}
          <div className="pt-2">
            <RangeSpan
              p10={currentEstimate.p10}
              p50={currentEstimate.p50}
              p90={currentEstimate.p90}
              currency={currentEstimate.currency || "INR"}
              unit={currentEstimate.unit || "lpa"}
              compareValue={userLpa}
              measure={estimateMeasure}
              date={currentEstimate.date}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default PayCompare;
