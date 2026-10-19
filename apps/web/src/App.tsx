import React, { useState } from "react";
import { ProfileForm } from "./components/ProfileForm";
import { EstimateHeadline } from "./components/EstimateHeadline";
import { RangeSpan } from "./components/RangeSpan";
import { EvidenceList } from "./components/EvidenceList";
import { AbstentionNotice } from "./components/AbstentionNotice";
import { DisclaimerLine } from "./components/DisclaimerLine";
import { fetchSalaryEstimate } from "./lib/api";
import { ProfileFormData, EstimateApiResponse } from "./lib/types";

export function App(): React.JSX.Element {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [currency] = useState<string>("INR");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [profileData, setProfileData] = useState<ProfileFormData>({
    occupation_id: "SWE",
    location_id: "BENGALURU",
    years_experience: 4.0,
    not_sure_experience: false,
  });

  const [estimateResult, setEstimateResult] = useState<EstimateApiResponse | null>(() => {
    // Initial estimate display for first view
    return {
      request_id: "init-est-1",
      status: "ok",
      estimate: {
        p10: 24.5,
        p50: 38.0,
        p90: 55.0,
        currency: "INR",
        period: "annual",
        measure: "guaranteed_cash_annual",
        pre_tax: true,
        nominal: true,
      },
      reliability: {
        grade: "GRADE_A",
        reasons: [],
      },
      evidence: {
        cohort_n: 142,
        source_mix: [
          { source_type: "statutory_filing", share: 0.65 },
          { source_type: "voluntary_intake", share: 0.35 },
        ],
        median_observation_age_days: 72.0,
        data_snapshot_id: "SNAP-CANONICAL-20261018",
        model_version: "0.1.0",
      },
      profile_level_used: 0,
      warnings: [],
      disclaimer_id: "decision_support_v1",
      as_of: "2026-10-19",
      model_version: "0.1.0",
      data_snapshot_id: "SNAP-CANONICAL-20261018",
    };
  });

  const toggleTheme = (): void => {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    if (nextTheme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  };

  const handleProfileSubmit = async (formData: ProfileFormData): Promise<void> => {
    setIsLoading(true);
    setProfileData(formData);
    try {
      const res = await fetchSalaryEstimate(formData, { currency });
      setEstimateResult(res);
    } catch {
      // In case of error
    } finally {
      setIsLoading(false);
    }
  };

  const handleFallback = (type: string, value?: string): void => {
    if (type === "location" && value) {
      const locId = value.toUpperCase() === "BENGALURU" ? "BENGALURU" : "HYDERABAD";
      const updated = { ...profileData, location_id: locId };
      handleProfileSubmit(updated);
    } else if (type === "role" && value) {
      const updated = { ...profileData, occupation_id: "SWE" };
      handleProfileSubmit(updated);
    }
  };

  return (
    <div className="min-h-screen bg-paper text-ink transition-colors selection:bg-span-wash selection:text-span-strong">
      {/* Global Header */}
      <header className="border-b border-rule bg-sheet">
        <div className="max-w-content mx-auto px-4 sm:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-serif font-semibold tracking-tight text-ink">
              ArthaIQ
            </h1>
            <p className="text-xs font-sans text-ink-2">
              India Tech Compensation Intelligence
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-sans text-ink-3">
            <button
              type="button"
              onClick={toggleTheme}
              className="px-2.5 py-1 rounded-control border border-rule-strong text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
            >
              {theme === "light" ? "Dark mode" : "Light mode"}
            </button>
            <span className="font-medium text-ink">INR (₹)</span>
          </div>
        </div>
      </header>

      {/* Main Two-Column Layout per design.md section 9 */}
      <main className="max-w-content mx-auto px-4 sm:px-8 py-8 sm:py-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
          {/* Left Column: Profile Form ("About the role") */}
          <div className="lg:col-span-5 bg-sheet rounded-control border border-rule p-6 sm:p-7 shadow-sm">
            <ProfileForm
              initialValues={profileData}
              onSubmit={handleProfileSubmit}
              isLoading={isLoading}
            />
          </div>

          {/* Right Column: Estimate Result / Abstention Notice */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            {isLoading ? (
              <div className="bg-sheet rounded-control border border-rule p-8 flex flex-col items-center justify-center min-h-[360px]">
                <RangeSpan state="loading" />
              </div>
            ) : estimateResult?.status === "ok" ? (
              <div className="bg-sheet rounded-control border border-rule p-6 sm:p-7 shadow-sm flex flex-col gap-6">
                {/* 1. Headline */}
                <EstimateHeadline
                  p10={estimateResult.estimate.p10}
                  p50={estimateResult.estimate.p50}
                  p90={estimateResult.estimate.p90}
                  currency={estimateResult.estimate.currency}
                  measure="Guaranteed cash"
                  date="October 2026"
                />

                {/* 2. Signature RangeSpan */}
                <div className="py-2">
                  <RangeSpan
                    p10={estimateResult.estimate.p10}
                    p50={estimateResult.estimate.p50}
                    p90={estimateResult.estimate.p90}
                    currency={estimateResult.estimate.currency}
                    unit="lpa"
                    state={
                      estimateResult.reliability.grade === "GRADE_C"
                        ? "limited_evidence"
                        : "default"
                    }
                    measure="Guaranteed cash"
                    date="October 2026"
                  />
                </div>

                {/* 3. Evidence List */}
                <EvidenceList
                  grade={estimateResult.reliability.grade}
                  cohortN={estimateResult.evidence.cohort_n}
                  sourceMix={estimateResult.evidence.source_mix}
                  medianAgeDays={estimateResult.evidence.median_observation_age_days}
                  modelVersion={estimateResult.model_version}
                  dataSnapshotId={estimateResult.data_snapshot_id}
                  newestDate="October 2026"
                />

                {/* 4. Statutory Disclaimer */}
                <DisclaimerLine />
              </div>
            ) : estimateResult?.status === "abstained" ? (
              <div className="bg-sheet rounded-control border border-rule p-6 sm:p-7 shadow-sm flex flex-col gap-6">
                <AbstentionNotice
                  reasons={estimateResult.reasons}
                  fallbacks={estimateResult.fallbacks}
                  nearestSupportedLocation="Bengaluru"
                  nearestSupportedRole="Software Engineering"
                  onSelectFallback={handleFallback}
                />
                <DisclaimerLine />
              </div>
            ) : null}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-12 pt-6 border-t border-rule text-xs font-sans text-ink-3 flex flex-col sm:flex-row justify-between gap-2">
          <p>
            ArthaIQ statistical estimates are calibrated to 80% nominal coverage (ADR-0005).
          </p>
          <p>
            Built for working professionals in India technology hubs.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
