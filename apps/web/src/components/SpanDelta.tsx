import React from "react";
import { RangeSpan, RangeSpanState } from "./RangeSpan";

export interface SpanValues {
  p10: number;
  p50: number;
  p90: number;
}

export interface SpanDeltaProps {
  current: SpanValues;
  previous?: SpanValues | null;
  currency?: string;
  unit?: "lpa" | "rupees" | "raw";
  state?: RangeSpanState;
  compareValue?: number | null;
  measure?: string;
  date?: string;
  className?: string;
}

/**
 * SpanDelta — Wraps RangeSpan with ghost comparison and plain verbal delta statements.
 *
 * Implements:
 * - design.md section 8:
 *   "Wraps RangeSpan with the ghost. Beneath it, one sentence in plain words:
 *    'The range got narrower.', 'The range got wider.', or 'The range did not change much.'
 *    Followed by: 'This reflects patterns in the data, not what you would earn by changing this detail.'
 *    Never celebrate narrowing."
 */
export function SpanDelta({
  current,
  previous,
  currency = "INR",
  unit = "lpa",
  state = "default",
  compareValue,
  measure = "Guaranteed cash",
  date = "October 2026",
  className = "",
}: SpanDeltaProps): React.JSX.Element {
  let deltaText: string | null = null;

  if (previous) {
    const prevWidth = Math.max(0.01, previous.p90 - previous.p10);
    const currWidth = Math.max(0.01, current.p90 - current.p10);
    const ratio = currWidth / prevWidth;

    if (ratio < 0.95) {
      deltaText = "The range got narrower.";
    } else if (ratio > 1.05) {
      deltaText = "The range got wider.";
    } else {
      deltaText = "The range did not change much.";
    }
  }

  return (
    <div data-testid="span-delta" className={`flex flex-col gap-4 text-left ${className}`}>
      {/* RangeSpan with ghost previous */}
      <RangeSpan
        p10={current.p10}
        p50={current.p50}
        p90={current.p90}
        currency={currency}
        unit={unit}
        state={state}
        compareValue={compareValue}
        previous={previous}
        measure={measure}
        date={date}
      />

      {/* Delta explanation sentence */}
      {deltaText && (
        <div
          data-testid="span-delta-explanation"
          className="p-3.5 bg-sunken rounded-control border border-rule text-xs font-sans text-ink space-y-1"
        >
          <p className="font-semibold text-ink">{deltaText}</p>
          <p className="text-ink-2">
            This reflects patterns in the data, not what you would earn by changing this detail.
          </p>
        </div>
      )}
    </div>
  );
}

export default SpanDelta;
