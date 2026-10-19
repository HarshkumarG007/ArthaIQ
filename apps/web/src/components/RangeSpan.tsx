import React, { useState, useId } from "react";
import { formatMoney } from "../lib/formatMoney";

export type RangeSpanState =
  | "default"
  | "limited_evidence"
  | "loading"
  | "abstained"
  | "stale";

export interface PreviousSpan {
  p10: number;
  p50: number;
  p90: number;
}

export interface RangeSpanProps {
  p10?: number | null;
  p50?: number | null;
  p90?: number | null;
  currency?: string; // 'INR' | 'USD'
  unit?: "lpa" | "rupees" | "raw";
  state?: RangeSpanState;
  compareValue?: number | null;
  previous?: PreviousSpan | null;
  measure?: string;
  date?: string;
  className?: string;
  defaultTableView?: boolean;
  onToggleTableView?: (isOpen: boolean) => void;
}

export interface TickInfo {
  value: number;
  label: string;
}

export interface ScaleConfig {
  min: number;
  max: number;
  ticks: TickInfo[];
}

/**
 * Computes a quiet, calibrated scale with 4 to 8 round ticks (1, 2, or 5 * 10^k).
 * Scale bounds extend to include compareValue unless it falls more than 3 span widths outside.
 */
export function computeScaleConfig(
  p10: number,
  p90: number,
  currency: string = "INR",
  compareValue?: number | null,
  previous?: { p10: number; p90: number } | null
): ScaleConfig {
  let low = Math.min(p10, previous?.p10 ?? p10);
  let high = Math.max(p90, previous?.p90 ?? p90);
  const span = Math.max(0.1, p90 - p10);

  // If compareValue is on-scale (within 3 span-widths)
  if (compareValue !== undefined && compareValue !== null && !isNaN(compareValue)) {
    if (compareValue >= low - 3 * span && compareValue <= high + 3 * span) {
      low = Math.min(low, compareValue);
      high = Math.max(high, compareValue);
    }
  }

  // Padding margin: 12% to 15% of total span on each side for labels and end caps
  const currentSpan = high - low;
  const margin = Math.max(currentSpan * 0.12, span * 0.1);
  const rawMin = Math.max(0, low - margin);
  const rawMax = high + margin;
  const rawRange = Math.max(0.1, rawMax - rawMin);

  // Find round step (1, 2, or 5 * 10^k) aiming for ~5 ticks
  const targetTicks = 5;
  const roughStep = rawRange / targetTicks;
  const power = Math.pow(10, Math.floor(Math.log10(roughStep)));
  const normalized = roughStep / power;

  let step: number;
  if (normalized < 1.5) {
    step = 1 * power;
  } else if (normalized < 3.5) {
    step = 2 * power;
  } else if (normalized < 7.5) {
    step = 5 * power;
  } else {
    step = 10 * power;
  }

  let scaleMin = Math.floor(rawMin / step) * step;
  let scaleMax = Math.ceil(rawMax / step) * step;
  let count = Math.round((scaleMax - scaleMin) / step) + 1;

  // Refine if count < 4 or count > 8
  if (count < 4 && step > 0.1) {
    step = step / 2;
    scaleMin = Math.floor(rawMin / step) * step;
    scaleMax = Math.ceil(rawMax / step) * step;
    count = Math.round((scaleMax - scaleMin) / step) + 1;
  } else if (count > 8) {
    step = step * 2;
    scaleMin = Math.floor(rawMin / step) * step;
    scaleMax = Math.ceil(rawMax / step) * step;
    count = Math.round((scaleMax - scaleMin) / step) + 1;
  }

  const ticks: TickInfo[] = [];
  const isINR = currency.toUpperCase() === "INR";

  for (let val = scaleMin; val <= scaleMax + step * 0.001; val += step) {
    const cleanVal = Math.round(val * 1000) / 1000;
    let label = "";
    if (isINR) {
      if (cleanVal >= 100) {
        label = `${(cleanVal / 100).toFixed(1)}Cr`;
      } else {
        label = `${cleanVal}L`;
      }
    } else {
      if (cleanVal >= 1000000) {
        label = `$${(cleanVal / 1000000).toFixed(1)}M`;
      } else if (cleanVal >= 1000) {
        label = `$${Math.round(cleanVal / 1000)}k`;
      } else {
        label = `$${cleanVal}`;
      }
    }
    ticks.push({ value: cleanVal, label });
  }

  return { min: scaleMin, max: scaleMax, ticks };
}

/**
 * RangeSpan — The signature ArthaIQ engineering dimension line component.
 *
 * Implements:
 * - design.md section 4 (The Span: scale, dimension line, wash, median notch, end labels, ghost span)
 * - design.md section 5 (Color tokens: --span, --ink, --ink-2, --ink-3, --caution, --paper, --sheet)
 * - design.md section 8 (Component specifications)
 * - Principle DP-1: Range first. The range is the headline. The typical value is a marker inside it.
 * - Principle DP-3: Abstention is a result (no span drawn, replaced by calm notice).
 * - Principle DP-8: Accessible by construction (role="img", generated label, toggleable table alternative).
 */
export function RangeSpan({
  p10,
  p50,
  p90,
  currency = "INR",
  unit = "lpa",
  state = "default",
  compareValue,
  previous,
  measure = "Guaranteed cash",
  date = "as of October 2026",
  className = "",
  defaultTableView = false,
  onToggleTableView,
}: RangeSpanProps): React.JSX.Element {
  const [showTable, setShowTable] = useState<boolean>(defaultTableView);
  const tableId = useId();

  const handleToggleTable = (): void => {
    const next = !showTable;
    setShowTable(next);
    onToggleTableView?.(next);
  };

  // State 1: Abstained — Never draw the Span with invented numbers (DP-3, section 4 & 8)
  if (state === "abstained") {
    return (
      <div
        data-testid="range-span-abstained"
        role="status"
        aria-live="polite"
        className={`w-full p-6 bg-sunken border-l-[3px] border-ink-3 rounded-r-control text-left ${className}`}
      >
        <div className="flex items-start gap-3">
          <div className="text-ink-2 mt-0.5">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" strokeWidth="2" />
              <path strokeWidth="2" strokeLinecap="round" d="M12 16v-4m0-4h.01" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-sans font-semibold text-ink">
              Estimate abstained
            </h3>
            <p className="text-sm font-sans text-ink-2 mt-1">
              We have too few comparable records to produce a reliable, calibrated
              range for this combination.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // State 2: Loading — Static placeholder line, no shimmer, aria-busy (section 4 & 8)
  if (state === "loading") {
    return (
      <div
        data-testid="range-span-loading"
        role="img"
        aria-busy="true"
        aria-label="Loading salary estimate"
        className={`w-full py-8 flex flex-col items-center justify-center ${className}`}
      >
        <div className="w-full max-w-xl h-[2px] bg-rule-strong/30 rounded-full" />
        <p className="text-xs font-sans text-ink-3 mt-3">Loading estimate...</p>
      </div>
    );
  }

  // Guard against missing quantile inputs in non-abstained states
  if (
    p10 === undefined ||
    p10 === null ||
    p50 === undefined ||
    p50 === null ||
    p90 === undefined ||
    p90 === null ||
    isNaN(p10) ||
    isNaN(p50) ||
    isNaN(p90)
  ) {
    return (
      <div
        data-testid="range-span-invalid"
        role="status"
        className={`w-full p-6 bg-sunken border-l-[3px] border-ink-3 rounded-r-control ${className}`}
      >
        <p className="text-sm font-sans text-ink-2">
          Unable to render estimate: quantile values are unavailable.
        </p>
      </div>
    );
  }

  // Format amounts for labels, table, and accessible description
  const p10Formatted = formatMoney(p10, { currency, unit, style: "headline" });
  const p50Formatted = formatMoney(p50, { currency, unit, style: "headline" });
  const p90Formatted = formatMoney(p90, { currency, unit, style: "headline" });
  const compareFormatted =
    compareValue !== undefined && compareValue !== null && !isNaN(compareValue)
      ? formatMoney(compareValue, { currency, unit, style: "headline" })
      : null;

  // Accessible generated text alternative (design.md section 4)
  const ariaLabel = `Estimated range: from ${p10Formatted} to ${p90Formatted} a year. Typical value ${p50Formatted}. ${measure}, before tax, ${currency}, ${date}.`;

  // Scale bounds & ticks
  const scale = computeScaleConfig(p10, p90, currency, compareValue, previous);

  // SVG Coordinate mapping
  const svgWidth = 640;
  const svgHeight = 180;
  const padLeft = 48;
  const padRight = 48;
  const plotWidth = svgWidth - padLeft - padRight;

  const getX = (val: number): number => {
    if (scale.max <= scale.min) return padLeft + plotWidth / 2;
    const clamped = Math.max(scale.min, Math.min(scale.max, val));
    return padLeft + ((clamped - scale.min) / (scale.max - scale.min)) * plotWidth;
  };

  const xP10 = getX(p10);
  const xP50 = getX(p50);
  const xP90 = getX(p90);

  // Vertical layout coordinates
  const yDim = 82; // Dimension line Y
  const yBase = 126; // Baseline Y
  const capHeight = 12; // 12px tall end caps per section 4

  // Check off-scale conditions for compareValue (falls > 3 span-widths outside)
  const spanWidth = p90 - p10;
  const isOffScaleLow =
    compareValue !== undefined &&
    compareValue !== null &&
    !isNaN(compareValue) &&
    compareValue < p10 - 3 * spanWidth;

  const isOffScaleHigh =
    compareValue !== undefined &&
    compareValue !== null &&
    !isNaN(compareValue) &&
    compareValue > p90 + 3 * spanWidth;

  const xCompare =
    compareValue !== undefined &&
    compareValue !== null &&
    !isNaN(compareValue) &&
    !isOffScaleLow &&
    !isOffScaleHigh
      ? getX(compareValue)
      : null;

  return (
    <div
      data-testid="range-span"
      className={`w-full max-w-2xl mx-auto flex flex-col gap-4 text-left ${className}`}
    >
      {/* State: Stale Data — Caution banner above per section 4 & 8 */}
      {state === "stale" && (
        <div
          data-testid="range-span-stale-banner"
          role="note"
          className="flex items-center gap-2.5 p-3 rounded-control bg-caution-wash border border-caution/30 text-caution text-xs font-sans"
        >
          <svg
            className="w-4 h-4 shrink-0 text-caution"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span>
            This estimate is based on older data snapshots and may not reflect recent market
            adjustments.
          </span>
        </div>
      )}

      {/* Bespoke Engineering Dimension Line SVG */}
      <div className="w-full relative overflow-hidden bg-sheet rounded-control border border-rule p-4">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto select-none"
          role="img"
          aria-label={ariaLabel}
        >
          {/* 1. Ghost Span (Refine view) — 1px line in --ink-3 labeled "Before" */}
          {previous && (
            <g data-testid="ghost-span" className="opacity-90">
              <text
                x={(getX(previous.p10) + getX(previous.p90)) / 2}
                y={18}
                textAnchor="middle"
                fill="var(--ink-3)"
                className="font-sans text-[10px] tracking-wide uppercase font-medium"
              >
                Before
              </text>
              {/* Ghost line */}
              <line
                x1={getX(previous.p10)}
                y1={26}
                x2={getX(previous.p90)}
                y2={26}
                stroke="var(--ink-3)"
                strokeWidth="1"
              />
              {/* Ghost caps */}
              <line
                x1={getX(previous.p10)}
                y1={22}
                x2={getX(previous.p10)}
                y2={30}
                stroke="var(--ink-3)"
                strokeWidth="1"
              />
              <line
                x1={getX(previous.p90)}
                y1={22}
                x2={getX(previous.p90)}
                y2={30}
                stroke="var(--ink-3)"
                strokeWidth="1"
              />
            </g>
          )}

          {/* 2. End Labels (Lower end and Higher end) */}
          <g>
            {/* Lower End */}
            <text
              x={xP10}
              y={44}
              textAnchor="middle"
              fill="var(--ink-2)"
              className="font-sans text-[11px] font-medium transition-all duration-span ease-out motion-reduce:transition-none"
            >
              Lower end
            </text>
            <text
              x={xP10}
              y={62}
              textAnchor="middle"
              fill="var(--ink)"
              className="font-serif text-[15px] font-semibold tabular-nums transition-all duration-span ease-out motion-reduce:transition-none"
            >
              {p10Formatted}
            </text>

            {/* Higher End */}
            <text
              x={xP90}
              y={44}
              textAnchor="middle"
              fill="var(--ink-2)"
              className="font-sans text-[11px] font-medium transition-all duration-span ease-out motion-reduce:transition-none"
            >
              Higher end
            </text>
            <text
              x={xP90}
              y={62}
              textAnchor="middle"
              fill="var(--ink)"
              className="font-serif text-[15px] font-semibold tabular-nums transition-all duration-span ease-out motion-reduce:transition-none"
            >
              {p90Formatted}
            </text>
          </g>

          {/* 3. Wash Fill between extension lines and baseline */}
          <rect
            x={xP10}
            y={yDim}
            width={Math.max(0, xP90 - xP10)}
            height={yBase - yDim}
            fill="var(--span-wash)"
            className="transition-all duration-span ease-out motion-reduce:transition-none"
          />

          {/* 4. Extension Lines down to baseline */}
          <line
            x1={xP10}
            y1={yDim}
            x2={xP10}
            y2={yBase}
            stroke="var(--rule-strong)"
            strokeWidth="1"
            className="transition-all duration-span ease-out motion-reduce:transition-none"
          />
          <line
            x1={xP90}
            y1={yDim}
            x2={xP90}
            y2={yBase}
            stroke="var(--rule-strong)"
            strokeWidth="1"
            className="transition-all duration-span ease-out motion-reduce:transition-none"
          />

          {/* 5. Dimension Line (2px in --span; dashed if limited_evidence) */}
          <line
            data-testid="dimension-line"
            x1={xP10}
            y1={yDim}
            x2={xP90}
            y2={yDim}
            stroke="var(--span)"
            strokeWidth="2"
            strokeDasharray={state === "limited_evidence" ? "6 4" : undefined}
            className="transition-all duration-span ease-out motion-reduce:transition-none"
          />

          {/* 6. End Caps (12px tall in --span at P10 and P90) */}
          <line
            x1={xP10}
            y1={yDim - capHeight / 2}
            x2={xP10}
            y2={yDim + capHeight / 2}
            stroke="var(--span)"
            strokeWidth="2"
            className="transition-all duration-span ease-out motion-reduce:transition-none"
          />
          <line
            x1={xP90}
            y1={yDim - capHeight / 2}
            x2={xP90}
            y2={yDim + capHeight / 2}
            stroke="var(--span)"
            strokeWidth="2"
            className="transition-all duration-span ease-out motion-reduce:transition-none"
          />

          {/* 7. Median Notch (10px triangle in --ink pointing down to baseline, labeled "Typical") */}
          <g className="transition-all duration-span ease-out motion-reduce:transition-none">
            <text
              x={xP50}
              y={44}
              textAnchor="middle"
              fill="var(--ink-2)"
              className="font-sans text-[11px] font-medium"
            >
              Typical
            </text>
            <text
              x={xP50}
              y={62}
              textAnchor="middle"
              fill="var(--ink)"
              className="font-serif text-[15px] font-semibold tabular-nums"
            >
              {p50Formatted}
            </text>
            {/* 10px triangle pointing down to dimension line */}
            <polygon
              points={`${xP50 - 5},${yDim - 10} ${xP50 + 5},${yDim - 10} ${xP50},${yDim}`}
              fill="var(--ink)"
            />
          </g>

          {/* 8. Second Marker (Compare view) — Diamond in --ink labeled "Your figure" */}
          {xCompare !== null && (
            <g data-testid="compare-marker" className="transition-all duration-span ease-out motion-reduce:transition-none">
              {/* Diamond marker */}
              <polygon
                points={`${xCompare},${yDim - 6} ${xCompare + 6},${yDim} ${xCompare},${yDim + 6} ${xCompare - 6},${yDim}`}
                fill="var(--ink)"
              />
              <text
                x={xCompare}
                y={yDim + 22}
                textAnchor="middle"
                fill="var(--ink)"
                className="font-sans text-[11px] font-medium"
              >
                Your figure
              </text>
              {compareFormatted && (
                <text
                  x={xCompare}
                  y={yDim + 36}
                  textAnchor="middle"
                  fill="var(--ink-2)"
                  className="font-serif text-[12px] font-semibold tabular-nums"
                >
                  {compareFormatted}
                </text>
              )}
            </g>
          )}

          {/* Off-scale Chevrons */}
          {isOffScaleLow && (
            <g data-testid="off-scale-low">
              <path
                d={`M ${padLeft - 6} ${yDim - 6} L ${padLeft - 12} ${yDim} L ${padLeft - 6} ${yDim + 6}`}
                fill="none"
                stroke="var(--ink)"
                strokeWidth="2"
              />
              <text
                x={padLeft - 4}
                y={yDim + 20}
                textAnchor="start"
                fill="var(--ink-3)"
                className="font-sans text-[10px]"
              >
                Off-scale low
              </text>
            </g>
          )}

          {isOffScaleHigh && (
            <g data-testid="off-scale-high">
              <path
                d={`M ${svgWidth - padRight + 6} ${yDim - 6} L ${svgWidth - padRight + 12} ${yDim} L ${svgWidth - padRight + 6} ${yDim + 6}`}
                fill="none"
                stroke="var(--ink)"
                strokeWidth="2"
              />
              <text
                x={svgWidth - padRight + 4}
                y={yDim + 20}
                textAnchor="end"
                fill="var(--ink-3)"
                className="font-sans text-[10px]"
              >
                Off-scale high
              </text>
            </g>
          )}

          {/* 9. Hairline Baseline */}
          <line
            x1={padLeft}
            y1={yBase}
            x2={svgWidth - padRight}
            y2={yBase}
            stroke="var(--rule-strong)"
            strokeWidth="1"
          />

          {/* 10. Scale Ticks & Labels */}
          {scale.ticks.map((tick) => {
            const xTick = getX(tick.value);
            return (
              <g key={tick.value}>
                <line
                  x1={xTick}
                  y1={yBase}
                  x2={xTick}
                  y2={yBase + 6}
                  stroke="var(--rule-strong)"
                  strokeWidth="1"
                />
                <text
                  x={xTick}
                  y={yBase + 20}
                  textAnchor="middle"
                  fill="var(--ink-3)"
                  className="font-sans text-[11px] tabular-nums"
                >
                  {tick.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* State: Limited Evidence (Grade C) — Caution sentence beneath in --caution (never red) */}
      {state === "limited_evidence" && (
        <p
          data-testid="range-span-limited-caution"
          className="text-xs font-sans text-caution flex items-center gap-1.5"
        >
          <svg
            className="w-3.5 h-3.5 shrink-0 text-caution"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" strokeWidth="2" />
            <path strokeWidth="2" strokeLinecap="round" d="M12 8v4m0 4h.01" />
          </svg>
          Limited evidence: sample size or source coverage is limited for this combination.
          Interpret with caution.
        </p>
      )}

      {/* Off-scale explanation message */}
      {isOffScaleLow && compareFormatted && (
        <p className="text-xs font-sans text-ink-3">
          Your figure ({compareFormatted}) is more than three span-widths below the estimated range.
        </p>
      )}
      {isOffScaleHigh && compareFormatted && (
        <p className="text-xs font-sans text-ink-3">
          Your figure ({compareFormatted}) is more than three span-widths above the estimated range.
        </p>
      )}

      {/* Accessibility Alternative: "View as table" toggle (design.md section 4) */}
      <div className="flex flex-col items-start gap-3 mt-1">
        <button
          type="button"
          onClick={handleToggleTable}
          aria-expanded={showTable}
          aria-controls={tableId}
          className="inline-flex items-center gap-2 px-3 py-2 text-xs font-sans font-medium text-ink bg-sheet border border-rule-strong rounded-control hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px] transition-colors"
        >
          <svg
            className="w-4 h-4 text-ink-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.75"
              d="M3 10h18M3 14h18m-9-4v8m-8 4h16a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          {showTable ? "Hide table view" : "View as table"}
        </button>

        {showTable && (
          <div
            id={tableId}
            data-testid="range-span-table"
            className="w-full overflow-x-auto border border-rule rounded-control bg-sheet p-4 shadow-sm"
          >
            <table className="w-full text-left text-sm font-sans border-collapse">
              <caption className="sr-only">
                Detailed quantile breakdown for salary estimate
              </caption>
              <thead>
                <tr className="border-b border-rule text-xs font-medium text-ink-2">
                  <th scope="col" className="pb-2.5 font-normal">
                    Metric
                  </th>
                  <th scope="col" className="pb-2.5 font-normal text-right">
                    Amount
                  </th>
                  <th scope="col" className="pb-2.5 font-normal pl-6">
                    Statistical Meaning
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule text-ink">
                <tr>
                  <th scope="row" className="py-2.5 font-medium text-ink whitespace-nowrap">
                    Lower end (P10)
                  </th>
                  <td className="py-2.5 font-serif font-semibold text-right tabular-nums whitespace-nowrap">
                    {p10Formatted}
                    <span className="block text-xs font-sans text-ink-3 font-normal">
                      {formatMoney(p10, { currency, unit, style: "full" })}
                    </span>
                  </td>
                  <td className="py-2.5 pl-6 text-xs text-ink-2">
                    10% of comparable professionals earn below this amount
                  </td>
                </tr>
                <tr>
                  <th scope="row" className="py-2.5 font-medium text-ink whitespace-nowrap">
                    Typical (P50)
                  </th>
                  <td className="py-2.5 font-serif font-semibold text-right tabular-nums whitespace-nowrap">
                    {p50Formatted}
                    <span className="block text-xs font-sans text-ink-3 font-normal">
                      {formatMoney(p50, { currency, unit, style: "full" })}
                    </span>
                  </td>
                  <td className="py-2.5 pl-6 text-xs text-ink-2">
                    Median compensation; 50% earn below and 50% earn above
                  </td>
                </tr>
                <tr>
                  <th scope="row" className="py-2.5 font-medium text-ink whitespace-nowrap">
                    Higher end (P90)
                  </th>
                  <td className="py-2.5 font-serif font-semibold text-right tabular-nums whitespace-nowrap">
                    {p90Formatted}
                    <span className="block text-xs font-sans text-ink-3 font-normal">
                      {formatMoney(p90, { currency, unit, style: "full" })}
                    </span>
                  </td>
                  <td className="py-2.5 pl-6 text-xs text-ink-2">
                    10% of comparable professionals earn above this amount
                  </td>
                </tr>
                {compareFormatted && (
                  <tr className="bg-span-wash/30">
                    <th scope="row" className="py-2.5 font-medium text-ink whitespace-nowrap">
                      Your figure
                    </th>
                    <td className="py-2.5 font-serif font-semibold text-right tabular-nums whitespace-nowrap">
                      {compareFormatted}
                      {compareValue !== null && compareValue !== undefined && (
                        <span className="block text-xs font-sans text-ink-3 font-normal">
                          {formatMoney(compareValue, { currency, unit, style: "full" })}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pl-6 text-xs text-ink-2">
                      Reference figure provided for comparison against cohort
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default RangeSpan;
