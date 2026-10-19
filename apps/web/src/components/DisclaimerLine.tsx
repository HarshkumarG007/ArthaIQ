import React from "react";

export interface DisclaimerLineProps {
  className?: string;
}

/**
 * DisclaimerLine — Statutory decision support disclaimer.
 * Per design.md section 8 and PRD FR-18:
 * "In small size, --ink-2, directly under the evidence list.
 * Always visible; never collapsed or moved to a footer."
 */
export function DisclaimerLine({
  className = "",
}: DisclaimerLineProps): React.JSX.Element {
  return (
    <p
      data-testid="disclaimer-line"
      className={`text-xs font-sans text-ink-2 leading-relaxed text-left ${className}`}
    >
      This range is an estimate from data of varying quality. It is not an offer,
      appraisal or guarantee.
    </p>
  );
}

export default DisclaimerLine;
