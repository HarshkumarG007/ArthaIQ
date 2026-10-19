import React from "react";

export interface EvidenceGaugeProps {
  grade: "GRADE_A" | "GRADE_B" | "GRADE_C" | string;
  className?: string;
}

/**
 * EvidenceGauge — Discrete three-tick evidence meter.
 *
 * Implements:
 * - Rule R-UI-02: Discrete ticks plus word, never a percentage or fake precision.
 * - design.md section 8: "Gauge plus word: three ticks 'Strong', two 'Moderate', one 'Limited'".
 */
export function EvidenceGauge({
  grade,
  className = "",
}: EvidenceGaugeProps): React.JSX.Element {
  const normGrade = grade.toUpperCase();

  let ticks = 3;
  let word = "Strong";
  let tickClass = "bg-span";
  let textClass = "text-ink";

  if (normGrade === "GRADE_B" || normGrade === "MODERATE") {
    ticks = 2;
    word = "Moderate";
    tickClass = "bg-span";
    textClass = "text-ink";
  } else if (normGrade === "GRADE_C" || normGrade === "LIMITED") {
    ticks = 1;
    word = "Limited";
    tickClass = "bg-caution";
    textClass = "text-caution";
  }

  return (
    <div
      data-testid="evidence-gauge"
      role="meter"
      aria-label={`Evidence quality: ${word}`}
      aria-valuenow={ticks}
      aria-valuemin={1}
      aria-valuemax={3}
      aria-valuetext={word}
      className={`inline-flex items-center gap-2 ${className}`}
    >
      <div className="flex items-center gap-1" aria-hidden="true">
        {[1, 2, 3].map((i) => {
          const isFilled = i <= ticks;
          return (
            <div
              key={i}
              data-testid={`gauge-tick-${i}`}
              className={`w-2.5 h-3.5 rounded-sm transition-colors ${
                isFilled ? tickClass : "bg-sunken border border-rule-strong/40"
              }`}
            />
          );
        })}
      </div>
      <span className={`text-xs font-sans font-medium ${textClass}`}>
        {word}
      </span>
    </div>
  );
}

export default EvidenceGauge;
