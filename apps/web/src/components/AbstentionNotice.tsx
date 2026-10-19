import React from "react";

export interface AbstentionReason {
  code: string;
  detail?: string;
}

export interface AbstentionFallback {
  type: string;
  description: string;
}

export interface AbstentionNoticeProps {
  reasons: AbstentionReason[];
  fallbacks?: AbstentionFallback[];
  nearestSupportedLocation?: string;
  nearestSupportedRole?: string;
  onSelectFallback?: (type: string, value?: string) => void;
  className?: string;
}

const REASON_EXPLANATIONS: Record<string, string> = {
  INSUFFICIENT_SUPPORT: "We have too few comparable records for this combination.",
  OUT_OF_RANGE: "This profile is unusual compared with the records we have.",
  STALE_DATA: "The newest records for this combination are too old.",
  LOW_SOURCE_QUALITY: "The records we have for this combination are not reliable enough.",
  INTERVAL_TOO_WIDE: "The range would be too wide to be useful.",
};

/**
 * AbstentionNotice — Neutral, calm abstention presentation.
 *
 * Implements:
 * - Rule R-UI-03: Abstention is a designed state, not an error.
 * - design.md section 5: "Abstention is neutral: --ink-2 on --sunken. Never caution or alert colours."
 * - design.md section 8 & 9: 3px left rule in --ink-3 on --sunken, info icon, heading, reasons, next options.
 */
export function AbstentionNotice({
  reasons,
  fallbacks = [],
  nearestSupportedLocation = "Bengaluru",
  nearestSupportedRole = "Software Engineering",
  onSelectFallback,
  className = "",
}: AbstentionNoticeProps): React.JSX.Element {
  // Deduplicate and format reasons
  const formattedReasons = reasons.map((r) => {
    const code = r.code.toUpperCase();
    return r.detail || REASON_EXPLANATIONS[code] || "Data support is insufficient for this query.";
  });

  return (
    <div
      data-testid="abstention-notice"
      role="status"
      aria-live="polite"
      className={`w-full p-5 sm:p-6 bg-sunken border-l-[3px] border-ink-3 rounded-r-control text-left ${className}`}
    >
      <div className="flex items-start gap-3 mb-3">
        {/* Info Icon in neutral --ink-2 */}
        <div className="text-ink-2 mt-0.5 shrink-0" aria-hidden="true">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <circle cx="12" cy="12" r="10" strokeWidth="1.75" />
            <path strokeWidth="1.75" strokeLinecap="round" d="M12 16v-4m0-4h.01" />
          </svg>
        </div>

        <div>
          <h3 className="text-base font-serif font-semibold text-ink">
            We can't give a reliable range for this combination yet.
          </h3>
          <div className="text-sm font-sans text-ink-2 mt-1 space-y-1">
            {formattedReasons.map((text, idx) => (
              <p key={idx}>{text}</p>
            ))}
          </div>
        </div>
      </div>

      {/* What you can try */}
      <div className="mt-4 pt-3 border-t border-rule text-xs font-sans">
        <h4 className="font-semibold text-ink mb-2">What you can try</h4>
        <ul className="space-y-2 text-ink-2">
          {fallbacks.length > 0 ? (
            fallbacks.map((fb, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-ink-3">&bull;</span>
                <div className="flex-1">
                  <span>{fb.description}</span>
                  {onSelectFallback && (
                    <button
                      type="button"
                      onClick={() => onSelectFallback(fb.type)}
                      className="ml-2 text-span hover:underline font-medium focus:outline-none focus:ring-1 focus:ring-focus rounded"
                    >
                      Apply &rarr;
                    </button>
                  )}
                </div>
              </li>
            ))
          ) : (
            <>
              <li className="flex items-start gap-2">
                <span className="text-ink-3">&bull;</span>
                <div>
                  Broaden the location.{" "}
                  <button
                    type="button"
                    onClick={() => onSelectFallback?.("location", nearestSupportedLocation)}
                    className="text-span hover:underline font-medium focus:outline-none focus:ring-1 focus:ring-focus rounded"
                  >
                    Try {nearestSupportedLocation} &rarr;
                  </button>
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-ink-3">&bull;</span>
                <div>
                  Broaden the role family.{" "}
                  <button
                    type="button"
                    onClick={() => onSelectFallback?.("role", nearestSupportedRole)}
                    className="text-span hover:underline font-medium focus:outline-none focus:ring-1 focus:ring-focus rounded"
                  >
                    Try {nearestSupportedRole} &rarr;
                  </button>
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-ink-3">&bull;</span>
                <div>
                  See an official benchmark for a wider group (
                  <span className="text-ink-3">not personalized</span>).
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-ink-3">&bull;</span>
                <div>
                  Add your own verified compensation record in the beta to help open this cohort.
                </div>
              </li>
            </>
          )}
        </ul>
      </div>

      <div className="mt-4 pt-3 border-t border-rule text-[11px] font-sans text-ink-3">
        Estimates are calibrated decision support, not employment offers or compensation appraisals.
      </div>
    </div>
  );
}

export default AbstentionNotice;
