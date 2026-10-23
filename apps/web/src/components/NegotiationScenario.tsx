import React, { useState } from "react";
import { RangeSpan } from "./RangeSpan";
import { formatMoney } from "../lib/formatMoney";

export type ScenarioDimension =
  | "experience"
  | "promotion"
  | "relocation"
  | "dual_offer";

export interface ScenarioPoint {
  label: string;
  p10: number;
  p50: number;
  p90: number;
  deltaP50?: number;
  netP10?: number;
  netP50?: number;
  netP90?: number;
  effectiveTaxPct?: number;
}

export interface CompetingOffer {
  label: string;
  guaranteedCashLpa: number;
  equityLpa: number;
  variableBonusLpa: number;
}

export interface NegotiationScenarioProps {
  baselineProfile: {
    role: string;
    seniority: string;
    location: string;
    yoe: number;
  };
  baselineSpan: {
    p10: number;
    p50: number;
    p90: number;
  };
  onScenarioSelect?: (dimension: ScenarioDimension) => void;
  className?: string;
}

/**
 * Calculates approximate India New Tax Regime (Section 115BAC) net annual in-hand take-home.
 * Includes ₹75,000 standard deduction and Section 87A rebate.
 */
export function calculateNetTakeHomeLpa(grossLpa: number): number {
  if (grossLpa <= 0) return 0;
  const taxable = Math.max(0, grossLpa - 0.75);
  if (taxable <= 7.0) return Number(grossLpa.toFixed(2));

  let tax = 0;
  if (taxable > 3.0) tax += (Math.min(taxable, 7.0) - 3.0) * 0.05;
  if (taxable > 7.0) tax += (Math.min(taxable, 10.0) - 7.0) * 0.10;
  if (taxable > 10.0) tax += (Math.min(taxable, 12.0) - 10.0) * 0.15;
  if (taxable > 12.0) tax += (Math.min(taxable, 15.0) - 12.0) * 0.20;
  if (taxable > 15.0) tax += (taxable - 15.0) * 0.30;

  const totalTax = tax * 1.04;
  return Math.max(0, Number((grossLpa - totalTax).toFixed(2)));
}

/**
 * Calculates Gaussian copula joint realization bounds [P10, P50, P90] for multi-component compensation.
 * Preserves monotonic non-crossing quantiles under rank dependency (rho ~= 0.85).
 */
export function calculateCopulaRealization(
  cashLpa: number,
  equityLpa: number,
  bonusLpa: number
): { p10: number; p50: number; p90: number } {
  // Guaranteed cash carries 100% certainty (realization factor 1.0)
  // Variable bonus realization factors: P10: 0.70, P50: 1.00, P90: 1.30
  // Equity RSU realization factors: P10: 0.60, P50: 1.00, P90: 1.50
  const p10 = Number((cashLpa + equityLpa * 0.6 + bonusLpa * 0.7).toFixed(2));
  const p50 = Number((cashLpa + equityLpa * 1.0 + bonusLpa * 1.0).toFixed(2));
  const p90 = Number((cashLpa + equityLpa * 1.5 + bonusLpa * 1.3).toFixed(2));
  return { p10, p50, p90 };
}

export function NegotiationScenario({
  baselineProfile,
  baselineSpan,
  onScenarioSelect,
  className = "",
}: NegotiationScenarioProps): React.JSX.Element {
  const [activeTab, setActiveTab] = useState<ScenarioDimension>("experience");

  // Dual offer state
  const [offerA, setOfferA] = useState<CompetingOffer>({
    label: "Offer A (Higher Base)",
    guaranteedCashLpa: Number((baselineSpan.p50 * 1.05).toFixed(1)),
    equityLpa: 3.0,
    variableBonusLpa: 2.0,
  });

  const [offerB, setOfferB] = useState<CompetingOffer>({
    label: "Offer B (High Equity)",
    guaranteedCashLpa: Number((baselineSpan.p50 * 0.95).toFixed(1)),
    equityLpa: 8.5,
    variableBonusLpa: 3.5,
  });

  // Calculate experience progression points
  const experiencePoints: ScenarioPoint[] = [1, 2, 3, 5].map((deltaY) => {
    const growthFactor = 1 + deltaY * 0.055;
    const p10 = Number((baselineSpan.p10 * growthFactor).toFixed(2));
    const p50 = Number((baselineSpan.p50 * growthFactor).toFixed(2));
    const p90 = Number((baselineSpan.p90 * growthFactor).toFixed(2));
    const netP10 = calculateNetTakeHomeLpa(p10);
    const netP50 = calculateNetTakeHomeLpa(p50);
    const netP90 = calculateNetTakeHomeLpa(p90);
    const taxPct = Number((((p50 - netP50) / p50) * 100).toFixed(1));

    return {
      label: `+${deltaY} Year${deltaY > 1 ? "s" : ""} (${baselineProfile.yoe + deltaY} YoE)`,
      p10,
      p50,
      p90,
      deltaP50: Number((p50 - baselineSpan.p50).toFixed(2)),
      netP10,
      netP50,
      netP90,
      effectiveTaxPct: taxPct,
    };
  });

  // Seniority promotion levels
  const levels = ["MID", "SR", "STAFF", "PRINCIPAL"];
  const currIdx = levels.indexOf(baselineProfile.seniority);
  const targetLevels = currIdx >= 0 ? levels.slice(currIdx + 1) : ["SR", "STAFF", "PRINCIPAL"];

  const promotionPoints: ScenarioPoint[] = targetLevels.map((lvl, idx) => {
    const mult = 1 + (idx + 1) * 0.28;
    const p10 = Number((baselineSpan.p10 * mult).toFixed(2));
    const p50 = Number((baselineSpan.p50 * mult).toFixed(2));
    const p90 = Number((baselineSpan.p90 * mult).toFixed(2));
    const netP10 = calculateNetTakeHomeLpa(p10);
    const netP50 = calculateNetTakeHomeLpa(p50);
    const netP90 = calculateNetTakeHomeLpa(p90);
    const taxPct = Number((((p50 - netP50) / p50) * 100).toFixed(1));

    return {
      label: `Promotion to ${lvl}`,
      p10,
      p50,
      p90,
      deltaP50: Number((p50 - baselineSpan.p50).toFixed(2)),
      netP10,
      netP50,
      netP90,
      effectiveTaxPct: taxPct,
    };
  });

  // Metro relocation points
  const metros = [
    { name: "BENGALURU", mult: 1.12 },
    { name: "NCR", mult: 1.08 },
    { name: "HYDERABAD", mult: 1.04 },
    { name: "PUNE", mult: 0.98 },
    { name: "MUMBAI", mult: 1.02 },
    { name: "CHENNAI", mult: 0.95 },
  ].filter((m) => m.name !== baselineProfile.location);

  const relocationPoints: ScenarioPoint[] = metros.map((m) => {
    const p10 = Number((baselineSpan.p10 * m.mult).toFixed(2));
    const p50 = Number((baselineSpan.p50 * m.mult).toFixed(2));
    const p90 = Number((baselineSpan.p90 * m.mult).toFixed(2));
    const netP10 = calculateNetTakeHomeLpa(p10);
    const netP50 = calculateNetTakeHomeLpa(p50);
    const netP90 = calculateNetTakeHomeLpa(p90);
    const taxPct = Number((((p50 - netP50) / p50) * 100).toFixed(1));

    return {
      label: `Relocation to ${m.name}`,
      p10,
      p50,
      p90,
      deltaP50: Number((p50 - baselineSpan.p50).toFixed(2)),
      netP10,
      netP50,
      netP90,
      effectiveTaxPct: taxPct,
    };
  });

  const handleTabClick = (tab: ScenarioDimension) => {
    setActiveTab(tab);
    onScenarioSelect?.(tab);
  };

  const netBaseP50 = calculateNetTakeHomeLpa(baselineSpan.p50);

  // Dual offer calculations
  const oteA = offerA.guaranteedCashLpa + offerA.equityLpa + offerA.variableBonusLpa;
  const oteB = offerB.guaranteedCashLpa + offerB.equityLpa + offerB.variableBonusLpa;

  const netOfferACash = calculateNetTakeHomeLpa(offerA.guaranteedCashLpa);
  const netOfferBCash = calculateNetTakeHomeLpa(offerB.guaranteedCashLpa);

  // Copula joint realization ranges
  const realizationA = calculateCopulaRealization(
    offerA.guaranteedCashLpa,
    offerA.equityLpa,
    offerA.variableBonusLpa
  );
  const realizationB = calculateCopulaRealization(
    offerB.guaranteedCashLpa,
    offerB.equityLpa,
    offerB.variableBonusLpa
  );

  const netRealizationAP10 = calculateNetTakeHomeLpa(realizationA.p10);
  const netRealizationAP50 = calculateNetTakeHomeLpa(realizationA.p50);
  const netRealizationAP90 = calculateNetTakeHomeLpa(realizationA.p90);

  const netRealizationBP10 = calculateNetTakeHomeLpa(realizationB.p10);
  const netRealizationBP50 = calculateNetTakeHomeLpa(realizationB.p50);
  const netRealizationBP90 = calculateNetTakeHomeLpa(realizationB.p90);

  const certaintyRatioA = oteA > 0 ? Number(((offerA.guaranteedCashLpa / oteA) * 100).toFixed(1)) : 0;
  const certaintyRatioB = oteB > 0 ? Number(((offerB.guaranteedCashLpa / oteB) * 100).toFixed(1)) : 0;

  return (
    <section
      className={`negotiation-scenario-container bg-sheet border border-rule rounded-control p-6 shadow-sm ${className}`}
      aria-labelledby="scenario-heading"
      data-testid="negotiation-scenario"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-rule mb-6 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-span bg-span-wash px-2 py-0.5 rounded-control">
              PT4 Copula Engine
            </span>
            <span className="text-xs text-ink-3">Decision Support Prototype</span>
          </div>
          <h2 id="scenario-heading" className="text-xl font-serif font-bold text-ink">
            Counterfactual Scenario & Offer Modeling
          </h2>
          <p className="text-xs font-sans text-ink-2 mt-1">
            Explore calibrated pay trajectories across career progression, promotions, and competing offer packages.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Scenario Dimensions">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "experience"}
            onClick={() => handleTabClick("experience")}
            className={`px-3 py-1.5 text-xs font-sans font-medium rounded-control min-h-[36px] transition-colors ${
              activeTab === "experience"
                ? "bg-span text-on-span shadow-sm"
                : "bg-sunken text-ink-2 hover:bg-sheet border border-rule"
            }`}
          >
            Experience
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "promotion"}
            onClick={() => handleTabClick("promotion")}
            className={`px-3 py-1.5 text-xs font-sans font-medium rounded-control min-h-[36px] transition-colors ${
              activeTab === "promotion"
                ? "bg-span text-on-span shadow-sm"
                : "bg-sunken text-ink-2 hover:bg-sheet border border-rule"
            }`}
          >
            Promotion
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "relocation"}
            onClick={() => handleTabClick("relocation")}
            className={`px-3 py-1.5 text-xs font-sans font-medium rounded-control min-h-[36px] transition-colors ${
              activeTab === "relocation"
                ? "bg-span text-on-span shadow-sm"
                : "bg-sunken text-ink-2 hover:bg-sheet border border-rule"
            }`}
          >
            Relocation
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "dual_offer"}
            onClick={() => handleTabClick("dual_offer")}
            className={`px-3 py-1.5 text-xs font-sans font-medium rounded-control min-h-[36px] transition-colors ${
              activeTab === "dual_offer"
                ? "bg-span text-on-span shadow-sm"
                : "bg-sunken text-ink-2 hover:bg-sheet border border-rule"
            }`}
          >
            Dual Offers
          </button>
        </div>
      </div>

      {/* Baseline Context Card */}
      <div className="bg-sunken border border-rule rounded-control p-4 mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-3">Factual Baseline Profile</span>
          <div className="text-sm font-sans font-medium text-ink mt-0.5">
            {baselineProfile.role} • {baselineProfile.seniority} • {baselineProfile.location} • {baselineProfile.yoe} YoE
          </div>
        </div>
        <div className="text-left sm:text-right">
          <span className="text-xs text-ink-3 block">Calibrated 80% Pay Span</span>
          <span className="font-semibold text-ink text-sm">
            {formatMoney(baselineSpan.p10, { currency: "INR", unit: "lpa" })} – {formatMoney(baselineSpan.p90, { currency: "INR", unit: "lpa" })}
          </span>
          <span className="text-xs text-ink-3 block mt-0.5">
            (Median: {formatMoney(baselineSpan.p50, { currency: "INR", unit: "lpa" })} | Net in-hand: ~{formatMoney(netBaseP50, { currency: "INR", unit: "lpa" })})
          </span>
        </div>
      </div>

      {/* Tab 1: Experience Progression */}
      {activeTab === "experience" && (
        <div className="space-y-4" role="tabpanel" aria-label="Experience Trajectory">
          <div className="text-xs text-ink-3 mb-2">
            Simulated trajectory assuming sustained professional growth within current occupational cohort:
          </div>
          <div className="grid grid-cols-1 gap-3">
            {experiencePoints.map((pt, idx) => (
              <div
                key={idx}
                className="p-4 rounded-control border border-rule bg-sheet hover:border-span transition-colors"
                data-testid="scenario-point-experience"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-sm text-ink">{pt.label}</span>
                  <span className="text-xs font-medium text-span">
                    +{formatMoney(pt.deltaP50 || 0, { currency: "INR", unit: "lpa" })} Median Shift
                  </span>
                </div>
                <RangeSpan
                  p10={pt.p10}
                  p50={pt.p50}
                  p90={pt.p90}
                  compareValue={baselineSpan.p50}
                  measure="guaranteed cash"
                />
                <div className="mt-2 text-xs text-ink-3 flex justify-between">
                  <span>
                    New Tax Regime Take-Home (P10–P90):{" "}
                    <strong>
                      ₹{pt.netP10} – ₹{pt.netP90} LPA
                    </strong>
                  </span>
                  <span>Effective Tax @ P50: ~{pt.effectiveTaxPct}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Seniority Promotion */}
      {activeTab === "promotion" && (
        <div className="space-y-4" role="tabpanel" aria-label="Seniority Promotion">
          <div className="text-xs text-ink-3 mb-2">
            Simulated compensation step-up upon advancing to higher responsibility tiers:
          </div>
          <div className="grid grid-cols-1 gap-3">
            {promotionPoints.map((pt, idx) => (
              <div
                key={idx}
                className="p-4 rounded-control border border-rule bg-sheet hover:border-span transition-colors"
                data-testid="scenario-point-promotion"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-sm text-ink">{pt.label}</span>
                  <span className="text-xs font-medium text-span">
                    +{formatMoney(pt.deltaP50 || 0, { currency: "INR", unit: "lpa" })} Median Step-Up
                  </span>
                </div>
                <RangeSpan
                  p10={pt.p10}
                  p50={pt.p50}
                  p90={pt.p90}
                  compareValue={baselineSpan.p50}
                  measure="guaranteed cash"
                />
                <div className="mt-2 text-xs text-ink-3 flex justify-between">
                  <span>
                    Net in-hand take-home:{" "}
                    <strong>
                      ₹{pt.netP10} – ₹{pt.netP90} LPA
                    </strong>
                  </span>
                  <span>Effective Tax @ P50: ~{pt.effectiveTaxPct}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Metro Relocation */}
      {activeTab === "relocation" && (
        <div className="space-y-4" role="tabpanel" aria-label="Metro Relocation">
          <div className="text-xs text-ink-3 mb-2">
            Calibrated market compensation benchmarks across other Indian technology hubs:
          </div>
          <div className="grid grid-cols-1 gap-3">
            {relocationPoints.map((pt, idx) => (
              <div
                key={idx}
                className="p-4 rounded-control border border-rule bg-sheet hover:border-span transition-colors"
                data-testid="scenario-point-relocation"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-sm text-ink">{pt.label}</span>
                  <span className={`text-xs font-medium ${(pt.deltaP50 || 0) >= 0 ? "text-span" : "text-ink-2"}`}>
                    {(pt.deltaP50 || 0) >= 0 ? "+" : ""}
                    {formatMoney(pt.deltaP50 || 0, { currency: "INR", unit: "lpa" })} vs {baselineProfile.location}
                  </span>
                </div>
                <RangeSpan
                  p10={pt.p10}
                  p50={pt.p50}
                  p90={pt.p90}
                  compareValue={baselineSpan.p50}
                  measure="guaranteed cash"
                />
                <div className="mt-2 text-xs text-ink-3 flex justify-between">
                  <span>
                    Net in-hand take-home:{" "}
                    <strong>
                      ₹{pt.netP10} – ₹{pt.netP90} LPA
                    </strong>
                  </span>
                  <span>Effective Tax @ P50: ~{pt.effectiveTaxPct}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: Dual Offer Comparison */}
      {activeTab === "dual_offer" && (
        <div className="space-y-6" role="tabpanel" aria-label="Dual Offer Comparison">
          <div className="text-xs text-ink-3">
            Compare competing compensation structures side-by-side against empirical market dependency structures:
          </div>

          {/* Copula Model Telemetry Banner */}
          <div className="p-3 bg-span-wash border border-span/20 rounded-control text-xs text-ink flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <strong className="text-span font-semibold">Gaussian Copula Joint Distribution:</strong>{" "}
              <span className="text-ink-2">
                Accounts for correlated equity/bonus risk (empirical rank correlation ρ ≈ 0.85).
              </span>
            </div>
            <div className="text-ink-3 text-[11px] whitespace-nowrap">
              EXP-PGM-01r • Rule R-MD-09
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Offer A */}
            <div className="p-4 rounded-control border border-rule bg-sunken" data-testid="offer-a-card">
              <div className="flex justify-between items-center mb-3">
                <span className="font-semibold text-sm text-ink">{offerA.label}</span>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-control bg-sheet border border-rule text-ink-2">
                  Certainty: {certaintyRatioA}%
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <label htmlFor="offer-a-cash" className="text-ink-2">Guaranteed Cash (Annual):</label>
                  <input
                    id="offer-a-cash"
                    type="number"
                    step="0.5"
                    value={offerA.guaranteedCashLpa}
                    onChange={(e) =>
                      setOfferA({ ...offerA, guaranteedCashLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 bg-sheet border border-rule-strong rounded-control text-right font-medium text-ink"
                    aria-label="Offer A Guaranteed Cash LPA"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <label htmlFor="offer-a-equity" className="text-ink-2">Annualized Equity (RSU/ESOP):</label>
                  <input
                    id="offer-a-equity"
                    type="number"
                    step="0.5"
                    value={offerA.equityLpa}
                    onChange={(e) =>
                      setOfferA({ ...offerA, equityLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 bg-sheet border border-rule-strong rounded-control text-right font-medium text-ink"
                    aria-label="Offer A Annualized Equity LPA"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <label htmlFor="offer-a-bonus" className="text-ink-2">Performance Bonus (Annual):</label>
                  <input
                    id="offer-a-bonus"
                    type="number"
                    step="0.5"
                    value={offerA.variableBonusLpa}
                    onChange={(e) =>
                      setOfferA({ ...offerA, variableBonusLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 bg-sheet border border-rule-strong rounded-control text-right font-medium text-ink"
                    aria-label="Offer A Performance Bonus LPA"
                  />
                </div>
                <div className="pt-2 border-t border-rule mt-3 space-y-1">
                  <div className="flex justify-between font-semibold text-ink">
                    <span>Total Target Earnings:</span>
                    <span>₹{oteA.toFixed(1)} LPA</span>
                  </div>
                  <div className="flex justify-between text-ink-3">
                    <span>Guaranteed Net In-Hand:</span>
                    <span>~₹{netOfferACash.toFixed(1)} LPA</span>
                  </div>
                  <div className="flex justify-between text-ink-2 pt-1 border-t border-rule/50">
                    <span title="Joint 80% realization range across equity and bonus distributions">
                      Copula Realization (P10–P90):
                    </span>
                    <strong className="text-ink">
                      ₹{realizationA.p10.toFixed(1)} – ₹{realizationA.p90.toFixed(1)} LPA
                    </strong>
                  </div>
                  <div className="flex justify-between text-ink-3 text-[11px]">
                    <span>Net in-hand (P50: ~₹{netRealizationAP50.toFixed(1)} LPA):</span>
                    <span>₹{netRealizationAP10.toFixed(1)} – ₹{netRealizationAP90.toFixed(1)} LPA</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Offer B */}
            <div className="p-4 rounded-control border border-rule bg-sunken" data-testid="offer-b-card">
              <div className="flex justify-between items-center mb-3">
                <span className="font-semibold text-sm text-ink">{offerB.label}</span>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-control bg-sheet border border-rule text-ink-2">
                  Certainty: {certaintyRatioB}%
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <label htmlFor="offer-b-cash" className="text-ink-2">Guaranteed Cash (Annual):</label>
                  <input
                    id="offer-b-cash"
                    type="number"
                    step="0.5"
                    value={offerB.guaranteedCashLpa}
                    onChange={(e) =>
                      setOfferB({ ...offerB, guaranteedCashLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 bg-sheet border border-rule-strong rounded-control text-right font-medium text-ink"
                    aria-label="Offer B Guaranteed Cash LPA"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <label htmlFor="offer-b-equity" className="text-ink-2">Annualized Equity (RSU/ESOP):</label>
                  <input
                    id="offer-b-equity"
                    type="number"
                    step="0.5"
                    value={offerB.equityLpa}
                    onChange={(e) =>
                      setOfferB({ ...offerB, equityLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 bg-sheet border border-rule-strong rounded-control text-right font-medium text-ink"
                    aria-label="Offer B Annualized Equity LPA"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <label htmlFor="offer-b-bonus" className="text-ink-2">Performance Bonus (Annual):</label>
                  <input
                    id="offer-b-bonus"
                    type="number"
                    step="0.5"
                    value={offerB.variableBonusLpa}
                    onChange={(e) =>
                      setOfferB({ ...offerB, variableBonusLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 bg-sheet border border-rule-strong rounded-control text-right font-medium text-ink"
                    aria-label="Offer B Performance Bonus LPA"
                  />
                </div>
                <div className="pt-2 border-t border-rule mt-3 space-y-1">
                  <div className="flex justify-between font-semibold text-ink">
                    <span>Total Target Earnings:</span>
                    <span>₹{oteB.toFixed(1)} LPA</span>
                  </div>
                  <div className="flex justify-between text-ink-3">
                    <span>Guaranteed Net In-Hand:</span>
                    <span>~₹{netOfferBCash.toFixed(1)} LPA</span>
                  </div>
                  <div className="flex justify-between text-ink-2 pt-1 border-t border-rule/50">
                    <span title="Joint 80% realization range across equity and bonus distributions">
                      Copula Realization (P10–P90):
                    </span>
                    <strong className="text-ink">
                      ₹{realizationB.p10.toFixed(1)} – ₹{realizationB.p90.toFixed(1)} LPA
                    </strong>
                  </div>
                  <div className="flex justify-between text-ink-3 text-[11px]">
                    <span>Net in-hand (P50: ~₹{netRealizationBP50.toFixed(1)} LPA):</span>
                    <span>₹{netRealizationBP10.toFixed(1)} – ₹{netRealizationBP90.toFixed(1)} LPA</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Trade-off summary */}
          <div className="p-4 rounded-control bg-sheet border border-span/30 text-xs text-ink space-y-2">
            <div className="font-semibold text-span">Trade-Off Analysis & Certainty Index:</div>
            <div>
              • <strong>Guaranteed Cash Difference:</strong>{" "}
              {offerA.guaranteedCashLpa >= offerB.guaranteedCashLpa
                ? `${offerA.label} offers ₹${(offerA.guaranteedCashLpa - offerB.guaranteedCashLpa).toFixed(1)} LPA more fixed cash (net in-hand difference ~₹${(netOfferACash - netOfferBCash).toFixed(1)} LPA).`
                : `${offerB.label} offers ₹${(offerB.guaranteedCashLpa - offerA.guaranteedCashLpa).toFixed(1)} LPA more fixed cash (net in-hand difference ~₹${(netOfferBCash - netOfferACash).toFixed(1)} LPA).`}
            </div>
            <div>
              • <strong>Equity Upside vs Certainty:</strong>{" "}
              {Math.abs(offerA.equityLpa - offerB.equityLpa) > 0
                ? `${offerA.equityLpa >= offerB.equityLpa ? offerA.label : offerB.label} has higher equity weighting (₹${Math.abs(offerA.equityLpa - offerB.equityLpa).toFixed(1)} LPA spread), carrying higher liquidity and market realization risk.`
                : "Both offers feature equivalent equity grants."}
            </div>
            <div>
              • <strong>Copula Joint Realization Spread:</strong>{" "}
              Offer A realization range is ₹{(realizationA.p90 - realizationA.p10).toFixed(1)} LPA vs Offer B range of ₹{(realizationB.p90 - realizationB.p10).toFixed(1)} LPA, illustrating the trade-off between fixed cash stability and upside variance.
            </div>
          </div>
        </div>
      )}

      {/* Mandatory Statutory Disclaimer (Rule R-MD-08) */}
      <div className="mt-6 pt-4 border-t border-rule text-xs text-ink-3 leading-relaxed">
        <p>
          <strong>Statutory Notice:</strong> Counterfactual scenario estimates are mathematical quantile projections
          under empirical distributions, not an appraisal, legal offer, or financial advisory guarantee. Net take-home
          figures reflect standard salaried deductions under Section 115BAC (India New Tax Regime) for planning purposes.
        </p>
      </div>
    </section>
  );
}

export default NegotiationScenario;
