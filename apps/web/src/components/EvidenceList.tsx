import React from "react";
import { EvidenceGauge } from "./EvidenceGauge";

export interface SourceMixItem {
  source_type: string;
  share: number;
}

export interface EvidenceListProps {
  grade: string;
  cohortN: number;
  sourceMix: SourceMixItem[];
  medianAgeDays?: number;
  modelVersion: string;
  dataSnapshotId: string;
  newestDate?: string;
  knownLimits?: string;
  modelCardUrl?: string;
  className?: string;
}

function formatSourceTypeName(type: string): string {
  switch (type.toLowerCase()) {
    case "statutory_filing":
    case "corporate_filing":
      return "statutory filings";
    case "voluntary_intake":
    case "verified_intake":
      return "verified contributions";
    case "community_reported":
      return "community reports";
    default:
      return type.replace(/_/g, " ");
  }
}

/**
 * EvidenceList — Accessible definition list detailing empirical cohort evidence.
 * Per design.md section 8:
 * "A definition list with hairline rules between rows. Not cards, not chips."
 */
export function EvidenceList({
  grade,
  cohortN,
  sourceMix,
  medianAgeDays = 60,
  modelVersion,
  dataSnapshotId,
  newestDate = "October 2026",
  knownLimits,
  modelCardUrl = "#model-card",
  className = "",
}: EvidenceListProps): React.JSX.Element {
  const sourceCount = Math.max(1, sourceMix.length);
  const sourceMixText =
    sourceMix.length > 0
      ? sourceMix
          .map((s) => `${formatSourceTypeName(s.source_type)} ${Math.round(s.share * 100)}%`)
          .join(", ")
      : "Single verified source 100%";

  const medianMonths = Math.max(1, Math.round(medianAgeDays / 30.4));
  const limitsText =
    knownLimits ||
    "Calibrated to 80% nominal coverage for guaranteed annual cash. Does not predict unvested equity or discretionary bonuses.";

  return (
    <div
      data-testid="evidence-list"
      className={`w-full text-left font-sans ${className}`}
    >
      <h3 className="text-xs font-sans font-semibold uppercase tracking-wider text-ink-3 mb-2">
        What this is based on
      </h3>

      <dl className="divide-y divide-rule border-y border-rule text-xs">
        {/* Row 1: Evidence Gauge */}
        <div className="py-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <dt className="text-ink-2 font-medium">Evidence</dt>
          <dd className="text-ink">
            <EvidenceGauge grade={grade} />
          </dd>
        </div>

        {/* Row 2: Comparable records */}
        <div className="py-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <dt className="text-ink-2 font-medium">Comparable records</dt>
          <dd className="text-ink font-serif font-medium tabular-nums">
            {cohortN} records from {sourceCount} {sourceCount === 1 ? "source" : "sources"}
          </dd>
        </div>

        {/* Row 3: Source types */}
        <div className="py-2.5 flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
          <dt className="text-ink-2 font-medium shrink-0">Source types</dt>
          <dd className="text-ink text-left sm:text-right">{sourceMixText}</dd>
        </div>

        {/* Row 4: Recency */}
        <div className="py-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <dt className="text-ink-2 font-medium">Recency</dt>
          <dd className="text-ink font-serif font-medium tabular-nums">
            Median record age {medianMonths} {medianMonths === 1 ? "month" : "months"}; newest {newestDate}
          </dd>
        </div>

        {/* Row 5: Model and data */}
        <div className="py-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <dt className="text-ink-2 font-medium">Model and data</dt>
          <dd className="text-ink-3 font-mono text-[11px]">
            {modelVersion} &middot; {dataSnapshotId}
          </dd>
        </div>

        {/* Row 6: Known limits */}
        <div className="py-2.5 flex flex-col gap-1">
          <dt className="text-ink-2 font-medium">Known limits</dt>
          <dd className="text-ink-2 leading-relaxed">
            {limitsText}{" "}
            <a
              href={modelCardUrl}
              className="text-span hover:underline font-medium inline-flex items-center gap-0.5"
            >
              Read model card &rarr;
            </a>
          </dd>
        </div>
      </dl>
    </div>
  );
}

export default EvidenceList;
