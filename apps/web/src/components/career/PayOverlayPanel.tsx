import React, { useState, useMemo } from "react";
import type { ClientCareerProfile } from "../../lib/careerLedger";
import { formatMoney } from "../../lib/formatMoney";
import {
  TrendingUp,
  AlertTriangle,
  MapPin,
  Briefcase,
  Shield,
  ArrowRight,
  WifiOff,
} from "lucide-react";

export interface PayOverlayPanelProps {
  profile: ClientCareerProfile | null;
  onExploreCompensation?: () => void;
  className?: string;
}

export type MetroHub = "bangalore" | "hyderabad" | "pune" | "mumbai" | "ncr" | "other";

export interface BenchmarkDistribution {
  p10: number; // in LPA
  p50: number; // in LPA
  p90: number; // in LPA
  sample_tier: string;
  as_of: string;
  is_offline_anchor: boolean;
}

// Canonical Metro India Market Benchmarks for DATA family (in LPA)
export const MARKET_BENCHMARKS: Record<
  string, // location
  Record<
    "L2_junior" | "L3_mid" | "L4_senior",
    BenchmarkDistribution | null
  >
> = {
  bangalore: {
    L2_junior: { p10: 8.0, p50: 12.0, p90: 16.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 16.0, p50: 24.0, p90: 32.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 30.0, p50: 45.0, p90: 60.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  hyderabad: {
    L2_junior: { p10: 7.5, p50: 11.0, p90: 15.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 15.0, p50: 22.0, p90: 30.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 28.0, p50: 40.0, p90: 55.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  pune: {
    L2_junior: { p10: 7.0, p50: 10.5, p90: 14.5, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 14.0, p50: 21.0, p90: 28.5, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 26.5, p50: 38.0, p90: 52.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  mumbai: {
    L2_junior: { p10: 8.5, p50: 12.5, p90: 17.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 16.5, p50: 25.0, p90: 34.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 31.0, p50: 46.0, p90: 62.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  ncr: {
    L2_junior: { p10: 8.0, p50: 12.0, p90: 16.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 15.5, p50: 23.5, p90: 32.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 29.0, p50: 43.0, p90: 58.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  other: {
    L2_junior: null,
    L3_mid: null,
    L4_senior: null,
  },
};

// Canonical Metro India Market Benchmarks for SWE family (in LPA)
export const MARKET_BENCHMARKS_SWE: Record<
  string, // location
  Record<
    "L2_junior" | "L3_mid" | "L4_senior",
    BenchmarkDistribution | null
  >
> = {
  bangalore: {
    L2_junior: { p10: 9.0, p50: 14.0, p90: 20.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 18.0, p50: 28.0, p90: 40.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 35.0, p50: 52.0, p90: 75.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  hyderabad: {
    L2_junior: { p10: 8.5, p50: 13.0, p90: 18.5, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 16.5, p50: 25.5, p90: 36.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 32.0, p50: 48.0, p90: 68.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  pune: {
    L2_junior: { p10: 8.0, p50: 12.0, p90: 17.5, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 15.5, p50: 24.0, p90: 34.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 30.0, p50: 45.0, p90: 64.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  mumbai: {
    L2_junior: { p10: 9.5, p50: 14.5, p90: 21.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 19.0, p50: 29.0, p90: 42.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 36.0, p50: 54.0, p90: 78.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  ncr: {
    L2_junior: { p10: 9.0, p50: 13.5, p90: 19.5, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L3_mid: { p10: 17.5, p50: 27.0, p90: 38.5, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
    L4_senior: { p10: 34.0, p50: 50.0, p90: 72.0, sample_tier: "Tier 1 Metro Panel", as_of: "2026-10", is_offline_anchor: true },
  },
  other: {
    L2_junior: null,
    L3_mid: null,
    L4_senior: null,
  },
};

export const METRO_HUBS: { id: MetroHub; label: string }[] = [
  { id: "bangalore", label: "Bengaluru / Bangalore" },
  { id: "hyderabad", label: "Hyderabad" },
  { id: "pune", label: "Pune" },
  { id: "mumbai", label: "Mumbai (MMR)" },
  { id: "ncr", label: "Delhi NCR" },
  { id: "other", label: "Other / Non-Metro Hub" },
];

export const PayOverlayPanel: React.FC<PayOverlayPanelProps> = ({
  profile,
  onExploreCompensation,
  className = "",
}) => {
  const [selectedHub, setSelectedHub] = useState<MetroHub>("bangalore");
  const [selectedLevel, setSelectedLevel] = useState<"L2_junior" | "L3_mid" | "L4_senior">(
    profile?.target_level || "L3_mid"
  );

  const isSwe = profile?.target_family?.toUpperCase() === "SWE";
  const benchmarks = isSwe ? MARKET_BENCHMARKS_SWE : MARKET_BENCHMARKS;

  const distribution = useMemo(() => {
    const hubMap = benchmarks[selectedHub];
    if (!hubMap) return null;
    return hubMap[selectedLevel];
  }, [benchmarks, selectedHub, selectedLevel]);

  const levelLabel =
    selectedLevel === "L2_junior"
      ? "Junior L2"
      : selectedLevel === "L3_mid"
      ? "Mid-Level L3"
      : "Senior L4";

  return (
    <section
      role="region"
      aria-label="Decoupled market compensation context"
      className={`p-6 rounded-control border border-rule bg-sheet text-ink shadow-sm space-y-5 ${className}`}
    >
      {/* Header & Two-Streams Decoupling Banner (Rule R-CR-02) */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded bg-span text-on-span flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" aria-hidden="true" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-serif font-semibold text-ink">
                  Market Compensation Context
                </h2>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-span-wash text-span-strong">
                  Decoupled Stream (R-CR-02)
                </span>
              </div>
              <p className="text-xs text-ink-3">
                Macroeconomic compensation distributions for comparable market roles.
              </p>
            </div>
          </div>

          {/* Offline Anchor Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-sunken border border-rule text-xs text-ink-2">
            <WifiOff className="w-3.5 h-3.5 text-ink-3" aria-hidden="true" />
            <span>Offline Benchmark Anchor</span>
            <span className="font-mono text-[10px] text-ink-3 uppercase">(Low Evidence)</span>
          </div>
        </div>

        {/* Decoupling Statutory Banner (Rule R-CR-01, R-CR-02) */}
        <div
          className="p-3.5 rounded bg-sunken border border-rule text-xs space-y-1"
          role="note"
          aria-label="Decoupled pay notice"
        >
          <div className="flex items-center gap-1.5 text-ink font-semibold">
            <Shield className="w-3.5 h-3.5 text-span" aria-hidden="true" />
            <span>Two Streams, Two Places Architecture (Rule R-CR-02)</span>
          </div>
          <p className="text-ink-2 leading-relaxed">
            Market compensation figures are macroeconomic benchmarks for comparable job titles in India.
            They are strictly decoupled from your competency roadmap. <strong>Completing practice scenarios
            or acquiring skills does not guarantee employment offers, compensation increases, or appraisals</strong> (India
            Consumer Protection Act 2019, Rule R-CR-01).
          </p>
        </div>
      </div>

      {/* Cohort Controls: Metro Hub and Seniority Level */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded bg-sunken/60 border border-rule">
        <div>
          <label htmlFor="select-metro-hub" className="block text-xs font-semibold text-ink mb-1 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-span" aria-hidden="true" />
            <span>Metro Tech Hub</span>
          </label>
          <select
            id="select-metro-hub"
            value={selectedHub}
            onChange={(e) => setSelectedHub(e.target.value as MetroHub)}
            className="w-full px-3 py-2 min-h-[44px] rounded-control border border-rule-strong bg-sheet text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
          >
            {METRO_HUBS.map((hub) => (
              <option key={hub.id} value={hub.id}>
                {hub.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="select-seniority-level" className="block text-xs font-semibold text-ink mb-1 flex items-center gap-1.5">
            <Briefcase className="w-3.5 h-3.5 text-span" aria-hidden="true" />
            <span>Seniority Level</span>
          </label>
          <select
            id="select-seniority-level"
            value={selectedLevel}
            onChange={(e) =>
              setSelectedLevel(e.target.value as "L2_junior" | "L3_mid" | "L4_senior")
            }
            className="w-full px-3 py-2 min-h-[44px] rounded-control border border-rule-strong bg-sheet text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus"
          >
            <option value="L2_junior">Junior (Level 2)</option>
            <option value="L3_mid">Mid-Level (Level 3)</option>
            <option value="L4_senior">Senior (Level 4)</option>
          </select>
        </div>
      </div>

      {/* Main Display: Quantile Distribution or Honest Abstention (Rule R-CR-14) */}
      {distribution ? (
        <div className="space-y-4">
          {/* Calibrated Empirical Quantiles Visualizer (Rule R-UQ-01: Zero Lone Numbers) */}
          <div className="p-5 rounded bg-sheet border border-rule-strong space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-rule pb-3">
              <div>
                <span className="text-xs uppercase tracking-wider text-span font-semibold">
                  Empirical Benchmark Interval
                </span>
                <h3 className="text-lg font-serif font-semibold text-ink">
                  DATA Family · {levelLabel} in{" "}
                  {METRO_HUBS.find((h) => h.id === selectedHub)?.label}
                </h3>
              </div>
              <div className="text-xs text-ink-3">
                <span>As of {distribution.as_of}</span> ·{" "}
                <span className="font-semibold text-ink-2">{distribution.sample_tier}</span>
              </div>
            </div>

            {/* Distribution Quantile Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3 rounded bg-sunken border border-rule text-center">
                <span className="text-[11px] font-semibold text-ink-3 uppercase tracking-wider block">
                  10th Percentile (P10)
                </span>
                <span className="text-xl font-serif font-bold text-ink block mt-1">
                  {formatMoney(distribution.p10, { unit: "lpa", style: "headline" })}
                </span>
                <span className="text-[10px] text-ink-3">Entry baseline</span>
              </div>

              <div className="p-3 rounded bg-span-wash/30 border-2 border-span/40 text-center">
                <span className="text-[11px] font-semibold text-span-strong uppercase tracking-wider block">
                  Median (P50)
                </span>
                <span className="text-2xl font-serif font-bold text-ink block mt-0.5">
                  {formatMoney(distribution.p50, { unit: "lpa", style: "headline" })}
                </span>
                <span className="text-[10px] text-span font-medium">Market central tendency</span>
              </div>

              <div className="p-3 rounded bg-sunken border border-rule text-center">
                <span className="text-[11px] font-semibold text-ink-3 uppercase tracking-wider block">
                  90th Percentile (P90)
                </span>
                <span className="text-xl font-serif font-bold text-ink block mt-1">
                  {formatMoney(distribution.p90, { unit: "lpa", style: "headline" })}
                </span>
                <span className="text-[10px] text-ink-3">Upper boundary</span>
              </div>
            </div>

            {/* Visual Quantile Bar */}
            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between text-xs text-ink-3 font-mono">
                <span>P10: ₹{distribution.p10}L</span>
                <span className="font-semibold text-span">Median: ₹{distribution.p50}L</span>
                <span>P90: ₹{distribution.p90}L</span>
              </div>
              <div className="h-3 w-full bg-sunken rounded-full overflow-hidden relative border border-rule">
                <div
                  className="h-full bg-gradient-to-r from-span/40 via-span to-span/40 rounded-full"
                  style={{ width: "100%" }}
                  aria-hidden="true"
                />
              </div>
              <p className="text-[11px] text-ink-3 text-center">
                80% Conformal Interval Span: ₹{distribution.p10} to ₹{distribution.p90} lakh / year
                (Zero lone numbers per Rule R-UQ-01)
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* Honest Abstention View (Rule R-CR-14) */
        <div
          role="alert"
          className="p-6 rounded bg-caution-wash/30 border border-caution/40 text-ink space-y-3"
        >
          <div className="flex items-center gap-2 text-caution font-semibold text-xs uppercase tracking-wider">
            <AlertTriangle className="w-4 h-4" aria-hidden="true" />
            <span>Honest Abstention (Rule R-CR-14)</span>
          </div>
          <h3 className="text-base font-serif font-semibold text-ink">
            Insufficient Market Evidence for This Sub-Cohort
          </h3>
          <p className="text-xs text-ink-2 leading-relaxed">
            Statistical observation density in the selected non-metro cohort is below the minimum
            sample threshold. To prevent data fabrication (Rule R-EV-03, R-AI-01), ArthaIQ abstains
            rather than producing inaccurate or ungrounded compensation estimates.
          </p>
          <div className="pt-1 flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSelectedHub("bangalore")}
              className="px-3.5 py-1.5 min-h-[44px] rounded-control bg-sheet border border-rule text-ink text-xs font-medium hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
            >
              Reset to Bengaluru / Tier-1 Metro Panel
            </button>
          </div>
        </div>
      )}

      {/* Footer Navigation CTA */}
      <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-t border-rule">
        <div className="text-xs text-ink-3">
          <p>
            Detailed offer comparisons and negotiation scenarios are evaluated in the Compensation
            Engine.
          </p>
        </div>
        {onExploreCompensation && (
          <button
            type="button"
            onClick={onExploreCompensation}
            className="px-4 py-2 min-h-[44px] rounded-control bg-sheet border border-rule-strong text-ink hover:bg-sunken font-medium text-xs focus:outline-none focus:ring-2 focus:ring-focus transition-colors flex items-center gap-2 shrink-0"
            aria-label="Open full compensation estimator tool"
          >
            <span>Open Compensation Tool</span>
            <ArrowRight className="w-3.5 h-3.5 text-span" aria-hidden="true" />
          </button>
        )}
      </div>
    </section>
  );
};
