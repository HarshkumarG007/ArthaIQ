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
function calculateNetTakeHomeLpa(grossLpa: number): number {
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
  const netOfferACash = calculateNetTakeHomeLpa(offerA.guaranteedCashLpa);
  const netOfferBCash = calculateNetTakeHomeLpa(offerB.guaranteedCashLpa);
  const oteA = offerA.guaranteedCashLpa + offerA.equityLpa + offerA.variableBonusLpa;
  const oteB = offerB.guaranteedCashLpa + offerB.equityLpa + offerB.variableBonusLpa;

  return (
    <section
      className={`negotiation-scenario-container bg-surface border border-border rounded-xl p-6 shadow-sm ${className}`}
      aria-labelledby="scenario-heading"
      data-testid="negotiation-scenario"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-border mb-6">
        <div>
          <span className="text-xs uppercase tracking-wider font-semibold text-secondary mb-1 block">
            Decision Support (PT4 Prototype)
          </span>
          <h2 id="scenario-heading" className="text-xl font-bold text-foreground">
            Counterfactual Scenario & Offer Modeling
          </h2>
          <p className="text-sm text-secondary mt-1">
            Explore constrained pay bounds across career moves, promotions, and competing offers.
          </p>
        </div>
        <div className="mt-4 md:mt-0 flex flex-wrap gap-2" role="tablist" aria-label="Scenario Dimensions">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "experience"}
            onClick={() => handleTabClick("experience")}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeTab === "experience"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-surface-subtle text-secondary hover:text-foreground"
            }`}
          >
            Experience
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "promotion"}
            onClick={() => handleTabClick("promotion")}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeTab === "promotion"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-surface-subtle text-secondary hover:text-foreground"
            }`}
          >
            Promotion
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "relocation"}
            onClick={() => handleTabClick("relocation")}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeTab === "relocation"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-surface-subtle text-secondary hover:text-foreground"
            }`}
          >
            Relocation
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "dual_offer"}
            onClick={() => handleTabClick("dual_offer")}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              activeTab === "dual_offer"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-surface-subtle text-secondary hover:text-foreground"
            }`}
          >
            Dual Offers
          </button>
        </div>
      </div>

      {/* Baseline Context Card */}
      <div className="bg-surface-subtle border border-border/60 rounded-lg p-4 mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <span className="text-xs font-semibold uppercase text-secondary">Factual Baseline Profile</span>
          <div className="text-sm font-medium text-foreground mt-0.5">
            {baselineProfile.role} • {baselineProfile.seniority} • {baselineProfile.location} • {baselineProfile.yoe} YoE
          </div>
        </div>
        <div className="text-right sm:text-right">
          <span className="text-xs text-secondary block">Calibrated 80% Pay Span</span>
          <span className="font-semibold text-foreground text-sm">
            {formatMoney(baselineSpan.p10, { currency: "INR", unit: "lpa" })} – {formatMoney(baselineSpan.p90, { currency: "INR", unit: "lpa" })}
          </span>
          <span className="text-xs text-secondary block mt-0.5">
            (Median: {formatMoney(baselineSpan.p50, { currency: "INR", unit: "lpa" })} | Net in-hand: ~{formatMoney(netBaseP50, { currency: "INR", unit: "lpa" })})
          </span>
        </div>
      </div>

      {/* Tab 1: Experience Progression */}
      {activeTab === "experience" && (
        <div className="space-y-4" role="tabpanel" aria-label="Experience Trajectory">
          <div className="text-xs text-secondary mb-2">
            Simulated trajectory assuming sustained professional growth within current occupational cohort:
          </div>
          <div className="grid grid-cols-1 gap-3">
            {experiencePoints.map((pt, idx) => (
              <div
                key={idx}
                className="p-4 rounded-lg border border-border bg-surface hover:border-primary/40 transition-colors"
                data-testid="scenario-point-experience"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-sm text-foreground">{pt.label}</span>
                  <span className="text-xs font-medium text-primary">
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
                <div className="mt-2 text-xs text-secondary flex justify-between">
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
          <div className="text-xs text-secondary mb-2">
            Simulated compensation step-up upon advancing to higher responsibility tiers:
          </div>
          <div className="grid grid-cols-1 gap-3">
            {promotionPoints.map((pt, idx) => (
              <div
                key={idx}
                className="p-4 rounded-lg border border-border bg-surface hover:border-primary/40 transition-colors"
                data-testid="scenario-point-promotion"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-sm text-foreground">{pt.label}</span>
                  <span className="text-xs font-medium text-primary">
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
                <div className="mt-2 text-xs text-secondary flex justify-between">
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
          <div className="text-xs text-secondary mb-2">
            Calibrated market compensation benchmarks across other Indian technology hubs:
          </div>
          <div className="grid grid-cols-1 gap-3">
            {relocationPoints.map((pt, idx) => (
              <div
                key={idx}
                className="p-4 rounded-lg border border-border bg-surface hover:border-primary/40 transition-colors"
                data-testid="scenario-point-relocation"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-sm text-foreground">{pt.label}</span>
                  <span className={`text-xs font-medium ${(pt.deltaP50 || 0) >= 0 ? "text-primary" : "text-secondary"}`}>
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
                <div className="mt-2 text-xs text-secondary flex justify-between">
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
          <div className="text-xs text-secondary">
            Compare competing compensation structures side-by-side against your market benchmark:
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Offer A */}
            <div className="p-4 rounded-lg border border-border bg-surface-subtle" data-testid="offer-a-card">
              <div className="font-semibold text-sm text-foreground mb-3">{offerA.label}</div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-secondary">Guaranteed Cash (Annual):</span>
                  <input
                    type="number"
                    step="0.5"
                    value={offerA.guaranteedCashLpa}
                    onChange={(e) =>
                      setOfferA({ ...offerA, guaranteedCashLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 border border-border rounded text-right font-medium"
                    aria-label="Offer A Guaranteed Cash LPA"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-secondary">Annualized Equity (RSU/ESOP):</span>
                  <input
                    type="number"
                    step="0.5"
                    value={offerA.equityLpa}
                    onChange={(e) =>
                      setOfferA({ ...offerA, equityLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 border border-border rounded text-right font-medium"
                    aria-label="Offer A Annualized Equity LPA"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-secondary">Performance Bonus (Annual):</span>
                  <input
                    type="number"
                    step="0.5"
                    value={offerA.variableBonusLpa}
                    onChange={(e) =>
                      setOfferA({ ...offerA, variableBonusLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 border border-border rounded text-right font-medium"
                    aria-label="Offer A Performance Bonus LPA"
                  />
                </div>
                <div className="pt-2 border-t border-border mt-3">
                  <div className="flex justify-between font-semibold text-foreground">
                    <span>Total Target Earnings:</span>
                    <span>₹{oteA.toFixed(1)} LPA</span>
                  </div>
                  <div className="flex justify-between text-secondary mt-1">
                    <span>Net Cash In-Hand:</span>
                    <span>~₹{netOfferACash.toFixed(1)} LPA</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Offer B */}
            <div className="p-4 rounded-lg border border-border bg-surface-subtle" data-testid="offer-b-card">
              <div className="font-semibold text-sm text-foreground mb-3">{offerB.label}</div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-secondary">Guaranteed Cash (Annual):</span>
                  <input
                    type="number"
                    step="0.5"
                    value={offerB.guaranteedCashLpa}
                    onChange={(e) =>
                      setOfferB({ ...offerB, guaranteedCashLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 border border-border rounded text-right font-medium"
                    aria-label="Offer B Guaranteed Cash LPA"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-secondary">Annualized Equity (RSU/ESOP):</span>
                  <input
                    type="number"
                    step="0.5"
                    value={offerB.equityLpa}
                    onChange={(e) =>
                      setOfferB({ ...offerB, equityLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 border border-border rounded text-right font-medium"
                    aria-label="Offer B Annualized Equity LPA"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-secondary">Performance Bonus (Annual):</span>
                  <input
                    type="number"
                    step="0.5"
                    value={offerB.variableBonusLpa}
                    onChange={(e) =>
                      setOfferB({ ...offerB, variableBonusLpa: parseFloat(e.target.value) || 0 })
                    }
                    className="w-24 px-2 py-1 border border-border rounded text-right font-medium"
                    aria-label="Offer B Performance Bonus LPA"
                  />
                </div>
                <div className="pt-2 border-t border-border mt-3">
                  <div className="flex justify-between font-semibold text-foreground">
                    <span>Total Target Earnings:</span>
                    <span>₹{oteB.toFixed(1)} LPA</span>
                  </div>
                  <div className="flex justify-between text-secondary mt-1">
                    <span>Net Cash In-Hand:</span>
                    <span>~₹{netOfferBCash.toFixed(1)} LPA</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Trade-off summary */}
          <div className="p-4 rounded-lg bg-surface border border-primary/20 text-xs text-foreground space-y-1">
            <div className="font-semibold text-primary">Trade-Off Analysis & Certainty Index:</div>
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
          </div>
        </div>
      )}

      {/* Mandatory Statutory Disclaimer (Rule R-MD-08) */}
      <div className="mt-6 pt-4 border-t border-border text-xs text-secondary leading-relaxed">
        <p>
          <strong>Statutory Notice:</strong> Counterfactual scenario estimates are mathematical quantile projections
          under empirical distributions, not an appraisal, legal offer, or financial advisory guarantee. Net take-home
          figures reflect standard salaried deductions under Section 115BAC (India New Tax Regime) for planning purposes.
        </p>
      </div>
    </section>
  );
}
