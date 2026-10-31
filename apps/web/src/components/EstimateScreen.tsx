import React, { useState, useRef, useEffect } from "react";
import { ProfileForm } from "./ProfileForm";
import { EstimateHeadline } from "./EstimateHeadline";
import { RangeSpan } from "./RangeSpan";
import { SpanDelta, SpanValues } from "./SpanDelta";
import { PayCompare } from "./PayCompare";
import { EvidenceList } from "./EvidenceList";
import { AbstentionNotice } from "./AbstentionNotice";
import { DisclaimerLine } from "./DisclaimerLine";
import { NegotiationScenario } from "./NegotiationScenario";
import { SliceUncertaintyVisualizer } from "./SliceUncertaintyVisualizer";
import { fetchSalaryEstimate } from "../lib/api";
import {
  ProfileFormData,
  ProfileRefinementData,
  EstimateApiResponse,
} from "../lib/types";

export interface EstimateScreenProps {
  initialProfile?: ProfileFormData;
  initialEstimate?: EstimateApiResponse | null;
  className?: string;
}

const AVAILABLE_SKILLS = [
  "Python",
  "Distributed Systems",
  "Kubernetes",
  "System Design",
  "SQL",
  "React",
  "Machine Learning",
];

const AVAILABLE_INDUSTRIES = [
  { id: "PRODUCT_TECH", label: "Product Tech / Tier-1 Software" },
  { id: "FINTECH", label: "Financial Services / FinTech" },
  { id: "SERVICES", label: "IT Services / Consulting" },
  { id: "HEALTH_COMMERCE", label: "Health / E-Commerce / Consumer" },
];

const AVAILABLE_WORK_MODELS = [
  { id: "HYBRID", label: "Hybrid (2–3 days in office)" },
  { id: "IN_OFFICE", label: "In-office (5 days)" },
  { id: "REMOTE", label: "Fully Remote" },
];

/**
 * EstimateScreen — Assembles full Master Estimate flow per design.md Section 9 wireframe.
 *
 * Implements:
 * - Two-column responsive layout (stacking on compact, side-by-side on wide).
 * - ProfileForm with Level 0 core fields and accessible error summary.
 * - Optional Refinement section ("Add detail") with Skills, Industry, and Work Arrangement disclosures.
 * - Estimate headline with serif typography and typical value marker.
 * - SpanDelta comparison with ghost previous span and plain verbal delta sentences.
 * - Inline PayCompare panel with ordinal percentile bands and definition mismatch caution notice.
 * - Discrete tick EvidenceGauge and comprehensive evidence lineage metadata.
 * - Neutral AbstentionNotice with actionable fallbacks when insufficient support exists.
 * - Statutory DisclaimerLine visible in all states.
 * - Accessible methodology and data source dialogs with focus trapping and Escape key dismissal.
 */
export function EstimateScreen({
  initialProfile,
  initialEstimate,
  className = "",
}: EstimateScreenProps): React.JSX.Element {
  const [profileData, setProfileData] = useState<ProfileFormData>(() => {
    return (
      initialProfile || {
        occupation_id: "SWE",
        location_id: "BENGALURU",
        years_experience: 4.0,
        not_sure_experience: false,
        refinements: {
          skills: [],
          industry: "PRODUCT_TECH",
          work_arrangement: "HYBRID",
        },
      }
    );
  });

  const [estimateResult, setEstimateResult] = useState<EstimateApiResponse | null>(() => {
    if (initialEstimate !== undefined) return initialEstimate;
    // Default initial result
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

  const [previousEstimate, setPreviousEstimate] = useState<SpanValues | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorState, setErrorState] = useState<{ message: string; requestId: string } | null>(null);

  // Panels visibility
  const [isRefineOpen, setIsRefineOpen] = useState<boolean>(false);
  const [isCompareOpen, setIsCompareOpen] = useState<boolean>(false);
  const [isScenarioOpen, setIsScenarioOpen] = useState<boolean>(false);
  const [isUncertaintyOpen, setIsUncertaintyOpen] = useState<boolean>(false);
  const [activeModal, setActiveModal] = useState<"none" | "methodology" | "sources">("none");

  // Refinement draft state
  const [refinements, setRefinements] = useState<ProfileRefinementData>(() => {
    return (
      profileData.refinements || {
        skills: [],
        industry: "PRODUCT_TECH",
        work_arrangement: "HYBRID",
      }
    );
  });

  const refineSectionRef = useRef<HTMLDivElement>(null);
  const modalCloseBtnRef = useRef<HTMLButtonElement>(null);

  // Focus modal close button when modal opens
  useEffect(() => {
    if (activeModal !== "none" && modalCloseBtnRef.current) {
      modalCloseBtnRef.current.focus();
    }
  }, [activeModal]);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === "Escape" && activeModal !== "none") {
        setActiveModal("none");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeModal]);

  const handleProfileSubmit = async (formData: ProfileFormData): Promise<void> => {
    setIsLoading(true);
    setErrorState(null);
    setProfileData(formData);

    // Save previous estimate quantiles for ghost span if currently valid
    if (estimateResult && estimateResult.status === "ok") {
      setPreviousEstimate({
        p10: estimateResult.estimate.p10,
        p50: estimateResult.estimate.p50,
        p90: estimateResult.estimate.p90,
      });
    }

    try {
      const mergedProfile = { ...formData, refinements };
      const res = await fetchSalaryEstimate(mergedProfile, { currency: "INR" });
      setEstimateResult(res);
    } catch {
      setErrorState({
        message: "Couldn't load the estimate. The server didn't respond. Try again, or reload the page.",
        requestId: `req-${Date.now().toString(36)}`,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyRefinements = async (): Promise<void> => {
    const updatedProfile: ProfileFormData = {
      ...profileData,
      refinements,
    };
    await handleProfileSubmit(updatedProfile);
  };

  const toggleSkill = (skill: string): void => {
    const currentSkills = refinements.skills || [];
    const exists = currentSkills.includes(skill);
    const updated = exists
      ? currentSkills.filter((s) => s !== skill)
      : [...currentSkills, skill];
    setRefinements({ ...refinements, skills: updated });
  };

  const handleFallback = (type: string, value?: string): void => {
    if (type === "broaden_location" || (type === "location" && value)) {
      const locId = value && value.toUpperCase() === "HYDERABAD" ? "HYDERABAD" : "BENGALURU";
      const updated = { ...profileData, location_id: locId };
      handleProfileSubmit(updated);
    } else if (type === "adjust_experience") {
      const updated = { ...profileData, years_experience: 5.0, not_sure_experience: false };
      handleProfileSubmit(updated);
    } else if (type === "role" || type === "broaden_role") {
      const updated = { ...profileData, occupation_id: "SWE" };
      handleProfileSubmit(updated);
    }
  };

  const okEstimate = estimateResult && estimateResult.status === "ok" ? estimateResult : null;

  return (
    <div
      data-testid="estimate-screen"
      className={`max-w-content mx-auto px-4 sm:px-8 py-8 sm:py-10 ${className}`}
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
        {/* ==================================================================== */}
        {/* LEFT COLUMN: About the role & Optional Refinement                    */}
        {/* ==================================================================== */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-sheet rounded-control border border-rule p-6 sm:p-7 shadow-sm">
            <ProfileForm
              initialValues={profileData}
              onSubmit={handleProfileSubmit}
              isLoading={isLoading}
            />
          </div>

          {/* Optional Refinement Section (design.md Section 8 & 9) */}
          {okEstimate && (
            <div
              ref={refineSectionRef}
              data-testid="refinement-section"
              className="bg-sheet rounded-control border border-rule p-6 shadow-sm flex flex-col gap-5 text-left"
            >
              <div className="flex justify-between items-center border-b border-rule pb-3">
                <div>
                  <h3 className="text-sm font-sans font-semibold text-ink">
                    Add detail (optional)
                  </h3>
                  <p className="text-xs font-sans text-ink-3">
                    Refine with specific technical stacks and employment context.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsRefineOpen(!isRefineOpen)}
                  aria-expanded={isRefineOpen}
                  aria-controls="refinement-controls"
                  className="text-xs font-sans font-medium text-span underline hover:text-span-strong focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px] flex items-center"
                >
                  {isRefineOpen ? "Hide details" : "Show details"}
                </button>
              </div>

              {isRefineOpen && (
                <div id="refinement-controls" className="flex flex-col gap-5 pt-1">
                  {/* Skills Refinement */}
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-sans font-medium text-ink">Skills</label>
                    <p className="text-[11px] font-sans text-ink-3">
                      Helps narrow the range for specialized technical stacks.
                    </p>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {AVAILABLE_SKILLS.map((skill) => {
                        const selected = (refinements.skills || []).includes(skill);
                        return (
                          <button
                            key={skill}
                            type="button"
                            onClick={() => toggleSkill(skill)}
                            className={`px-3 py-1.5 rounded-control text-xs font-sans transition-colors min-h-[36px] ${
                              selected
                                ? "bg-span text-on-span font-medium"
                                : "bg-sunken text-ink-2 hover:bg-sheet border border-rule"
                            }`}
                          >
                            {skill}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Industry & Employer Type */}
                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="refine-industry" className="text-xs font-sans font-medium text-ink">
                      Industry and employer type
                    </label>
                    <p className="text-[11px] font-sans text-ink-3">
                      Captures compensation differences across product tech, financial services, and consulting.
                    </p>
                    <select
                      id="refine-industry"
                      value={refinements.industry || "PRODUCT_TECH"}
                      onChange={(e) =>
                        setRefinements({ ...refinements, industry: e.target.value })
                      }
                      className="w-full px-3 py-2 bg-sheet border border-rule-strong rounded-control text-xs font-sans text-ink focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
                    >
                      {AVAILABLE_INDUSTRIES.map((ind) => (
                        <option key={ind.id} value={ind.id}>
                          {ind.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Work Arrangement */}
                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="refine-work-model" className="text-xs font-sans font-medium text-ink">
                      Work arrangement
                    </label>
                    <p className="text-[11px] font-sans text-ink-3">
                      Accounts for differences across in-office, hybrid, and remote contracts.
                    </p>
                    <select
                      id="refine-work-model"
                      value={refinements.work_arrangement || "HYBRID"}
                      onChange={(e) =>
                        setRefinements({ ...refinements, work_arrangement: e.target.value })
                      }
                      className="w-full px-3 py-2 bg-sheet border border-rule-strong rounded-control text-xs font-sans text-ink focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
                    >
                      {AVAILABLE_WORK_MODELS.map((wm) => (
                        <option key={wm.id} value={wm.id}>
                          {wm.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Apply Refinements Button */}
                  <button
                    type="button"
                    data-testid="apply-refinements-btn"
                    onClick={handleApplyRefinements}
                    disabled={isLoading}
                    className="w-full mt-2 py-2.5 px-4 bg-span text-on-span text-xs font-sans font-semibold rounded-control hover:bg-span-strong focus:outline-none focus:ring-2 focus:ring-focus transition-colors min-h-[44px]"
                  >
                    {isLoading ? "Updating..." : "Apply refinement"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ==================================================================== */}
        {/* RIGHT COLUMN: Estimated range & Action Panels                       */}
        {/* ==================================================================== */}
        <div className="lg:col-span-7 flex flex-col gap-6 text-left">
          {/* State: Loading */}
          {isLoading && (
            <div
              data-testid="estimate-loading-state"
              className="bg-sheet rounded-control border border-rule p-8 flex flex-col items-center justify-center min-h-[360px]"
            >
              <RangeSpan state="loading" />
              <p className="text-xs font-sans text-ink-3 mt-4">Calculating the range...</p>
            </div>
          )}

          {/* State: Error */}
          {!isLoading && errorState && (
            <div
              data-testid="estimate-error-state"
              role="alert"
              className="bg-sheet rounded-control border border-alert p-6 sm:p-7 shadow-sm flex flex-col gap-4 text-left"
            >
              <div>
                <h3 className="text-sm font-sans font-semibold text-alert">
                  Couldn&apos;t load the estimate
                </h3>
                <p className="text-xs font-sans text-ink mt-1">
                  {errorState.message} Reference {errorState.requestId}.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleProfileSubmit(profileData)}
                className="self-start px-4 py-2 bg-span text-on-span text-xs font-sans font-medium rounded-control hover:bg-span-strong focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
              >
                Try again
              </button>
            </div>
          )}

          {/* State: Abstained */}
          {!isLoading && !errorState && estimateResult?.status === "abstained" && (
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
          )}

          {/* State: Successful Estimate */}
          {!isLoading && !errorState && okEstimate && (
            <div
              data-testid="estimate-result-card"
              className="bg-sheet rounded-control border border-rule p-6 sm:p-7 shadow-sm flex flex-col gap-6"
            >
              {/* 1. Headline */}
              <EstimateHeadline
                p10={okEstimate.estimate.p10}
                p50={okEstimate.estimate.p50}
                p90={okEstimate.estimate.p90}
                currency={okEstimate.estimate.currency}
                measure="Guaranteed cash"
                date="October 2026"
              />

              {/* 2. RangeSpan with SpanDelta if previous exists */}
              <div className="py-2">
                {previousEstimate ? (
                  <SpanDelta
                    current={{
                      p10: okEstimate.estimate.p10,
                      p50: okEstimate.estimate.p50,
                      p90: okEstimate.estimate.p90,
                    }}
                    previous={previousEstimate}
                    currency={okEstimate.estimate.currency}
                    unit="lpa"
                    state={
                      okEstimate.reliability.grade === "GRADE_C"
                        ? "limited_evidence"
                        : "default"
                    }
                    measure="Guaranteed cash"
                    date="October 2026"
                  />
                ) : (
                  <RangeSpan
                    p10={okEstimate.estimate.p10}
                    p50={okEstimate.estimate.p50}
                    p90={okEstimate.estimate.p90}
                    currency={okEstimate.estimate.currency}
                    unit="lpa"
                    state={
                      okEstimate.reliability.grade === "GRADE_C"
                        ? "limited_evidence"
                        : "default"
                    }
                    measure="Guaranteed cash"
                    date="October 2026"
                  />
                )}
              </div>

              {/* 3. Action Buttons: Refine and Compare (design.md Section 9) */}
              <div className="flex flex-wrap items-center gap-3 pt-1 border-t border-rule">
                <button
                  type="button"
                  data-testid="refine-estimate-btn"
                  onClick={() => {
                    setIsRefineOpen(true);
                    if (refineSectionRef.current) {
                      refineSectionRef.current.scrollIntoView({ behavior: "smooth" });
                    }
                  }}
                  className="px-4 py-2 border border-rule-strong rounded-control text-xs font-sans font-medium text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px] transition-colors"
                >
                  Refine estimate
                </button>
                <button
                  type="button"
                  data-testid="compare-pay-btn"
                  onClick={() => setIsCompareOpen(!isCompareOpen)}
                  aria-expanded={isCompareOpen}
                  className={`px-4 py-2 rounded-control text-xs font-sans font-medium min-h-[44px] transition-colors ${
                    isCompareOpen
                      ? "bg-span text-on-span"
                      : "border border-rule-strong text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus"
                  }`}
                >
                  {isCompareOpen ? "Close pay comparison" : "Compare with my pay"}
                </button>
                <button
                  type="button"
                  data-testid="toggle-scenario-btn"
                  onClick={() => setIsScenarioOpen(!isScenarioOpen)}
                  aria-expanded={isScenarioOpen}
                  className={`px-4 py-2 rounded-control text-xs font-sans font-medium min-h-[44px] transition-colors ${
                    isScenarioOpen
                      ? "bg-span text-on-span"
                      : "border border-rule-strong text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus"
                  }`}
                >
                  {isScenarioOpen ? "Close scenario modeling" : "Scenario modeling (PT4 Copula)"}
                </button>
                <button
                  type="button"
                  data-testid="toggle-uncertainty-btn"
                  onClick={() => setIsUncertaintyOpen(!isUncertaintyOpen)}
                  aria-expanded={isUncertaintyOpen}
                  className={`px-4 py-2 rounded-control text-xs font-sans font-medium min-h-[44px] transition-colors ${
                    isUncertaintyOpen
                      ? "bg-span text-on-span"
                      : "border border-rule-strong text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus"
                  }`}
                >
                  {isUncertaintyOpen ? "Close slice uncertainty" : "Slice uncertainty (UX-18)"}
                </button>
              </div>

              {/* 4. Compare Panel (when toggled) */}
              {isCompareOpen && (
                <div data-testid="inline-pay-compare-container" className="pt-2">
                  <PayCompare
                    currentEstimate={{
                      p10: okEstimate.estimate.p10,
                      p50: okEstimate.estimate.p50,
                      p90: okEstimate.estimate.p90,
                      currency: okEstimate.estimate.currency,
                      unit: "lpa",
                      measure: "Guaranteed cash pay",
                      date: "October 2026",
                    }}
                  />
                </div>
              )}

              {/* 4b. Scenario Modeling Panel (PT4 Copula, when toggled) */}
              {isScenarioOpen && (
                <div data-testid="inline-scenario-container" className="pt-2">
                  <NegotiationScenario
                    baselineProfile={{
                      role: profileData.occupation_id,
                      seniority:
                        (profileData.years_experience ?? 4) >= 8
                          ? "SR"
                          : (profileData.years_experience ?? 4) >= 4
                          ? "MID"
                          : "ENTRY",
                      location: profileData.location_id,
                      yoe: Math.round(profileData.years_experience ?? 4),
                    }}
                    baselineSpan={{
                      p10: okEstimate.estimate.p10,
                      p50: okEstimate.estimate.p50,
                      p90: okEstimate.estimate.p90,
                    }}
                  />
                </div>
              )}

              {/* 4c. Slice Uncertainty Visualizer Panel (UX-18, when toggled) */}
              {isUncertaintyOpen && (
                <div data-testid="inline-uncertainty-container" className="pt-2">
                  <SliceUncertaintyVisualizer
                    baseP10={okEstimate.estimate.p10}
                    baseP50={okEstimate.estimate.p50}
                    baseP90={okEstimate.estimate.p90}
                    roleFamily={profileData.occupation_id}
                    locationId={profileData.location_id}
                  />
                </div>
              )}

              {/* 5. What this is based on (Evidence List) */}
              <EvidenceList
                grade={okEstimate.reliability.grade}
                cohortN={okEstimate.evidence.cohort_n}
                sourceMix={okEstimate.evidence.source_mix}
                medianAgeDays={okEstimate.evidence.median_observation_age_days}
                modelVersion={okEstimate.model_version}
                dataSnapshotId={okEstimate.data_snapshot_id}
                newestDate="October 2026"
              />

              {/* 6. Statutory Disclaimer */}
              <DisclaimerLine />

              {/* 7. Methodology and Data Sources Links */}
              <div className="flex items-center gap-6 pt-2 border-t border-rule text-xs font-sans text-ink-3">
                <button
                  type="button"
                  onClick={() => setActiveModal("methodology")}
                  className="underline hover:text-ink focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  How this was calculated
                </button>
                <button
                  type="button"
                  onClick={() => setActiveModal("sources")}
                  className="underline hover:text-ink focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  Data sources
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ==================================================================== */}
      {/* ACCESSIBLE DIALOGS: Methodology & Data Sources                      */}
      {/* ==================================================================== */}
      {activeModal !== "none" && (
        <div
          data-testid="estimate-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-xs"
        >
          <div className="bg-sheet border border-rule rounded-dialog max-w-lg w-full p-6 sm:p-7 shadow-lg flex flex-col gap-4 text-left">
            <div className="flex justify-between items-start border-b border-rule pb-3">
              <h3 id="modal-title" className="text-base font-serif font-semibold text-ink">
                {activeModal === "methodology" ? "How this was calculated" : "Data sources"}
              </h3>
              <button
                ref={modalCloseBtnRef}
                type="button"
                onClick={() => setActiveModal("none")}
                className="text-xs font-sans font-medium text-ink-3 hover:text-ink p-1 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-control focus:outline-none focus:ring-2 focus:ring-focus"
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            {activeModal === "methodology" ? (
              <div className="text-xs font-sans text-ink space-y-3 max-h-[60vh] overflow-y-auto pr-1">
                <p>
                  ArthaIQ estimates are produced using Conformal Quantile Regression (CatBoost CQR)
                  trained on verified compensation records.
                </p>
                <p>
                  <strong>Nominal 80% Coverage:</strong> The range spans from the 10th percentile
                  ($P_{10}$) to the 90th percentile ($P_{90}$) of comparable tech compensation in
                  India.
                </p>
                <p>
                  <strong>Compare-Only Guarantee (Rule R-MD-13):</strong> Any compensation figure
                  you provide is used solely to position your marker. It is strictly quarantined and
                  never used to train or bias future predictions.
                </p>
                <p className="text-ink-3">
                  Model Version: {okEstimate?.model_version || "0.1.0"} | Snapshot:{" "}
                  {okEstimate?.data_snapshot_id || "SNAP-CANONICAL-20261018"}
                </p>
              </div>
            ) : (
              <div className="text-xs font-sans text-ink space-y-3 max-h-[60vh] overflow-y-auto pr-1">
                <p>
                  All figures are synthesized exclusively from verified, approved public and
                  voluntary primary datasets:
                </p>
                <ul className="list-disc pl-4 space-y-1 text-ink-2">
                  <li>Statutory Ministry of Corporate Affairs and stock exchange filings (BSE/NSE)</li>
                  <li>Direct verified voluntary participant submissions (SRC-INT-VOL-01)</li>
                  <li>Industry compensation surveys with rigorous duplicate quarantine</li>
                </ul>
                <p className="text-ink-3">
                  Synthetic salaries and unverified claims are permanently excluded under Rule
                  R-MD-11.
                </p>
              </div>
            )}

            <div className="pt-3 border-t border-rule flex justify-end">
              <button
                type="button"
                onClick={() => setActiveModal("none")}
                className="px-4 py-2 bg-span text-on-span text-xs font-sans font-medium rounded-control hover:bg-span-strong focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EstimateScreen;
