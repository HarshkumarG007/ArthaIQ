import React, { useState, useEffect, useCallback } from "react";
import {
  getCareerProfile,
  saveCareerProfile,
  getAllLedgerRecords,
  getScenarioAttempts,
  exportLedgerBackup,
  purgeAllUserData,
  type ClientCareerProfile,
  type ClientEvidenceRecord,
  type ClientScenarioAttemptRecord,
  type TargetLevel,
} from "../lib/careerLedger";
import { GapMapView } from "../components/career/GapMapView";
import { PracticeWorkspace } from "../components/career/PracticeWorkspace";
import { RoadmapView } from "../components/career/RoadmapView";
import { NextStepCard } from "../components/career/NextStepCard";
import { PayOverlayPanel } from "../components/career/PayOverlayPanel";

export type CareerSubView = "skills" | "plan" | "practice" | "ledger";

interface CareerRouteProps {
  initialSubView?: CareerSubView;
  onSubViewChange?: (view: CareerSubView) => void;
}

export function CareerRoute({
  initialSubView = "skills",
  onSubViewChange,
}: CareerRouteProps): React.JSX.Element {
  const [subView, setSubView] = useState<CareerSubView>(initialSubView);
  const [profile, setProfile] = useState<ClientCareerProfile | null>(null);
  const [records, setRecords] = useState<ClientEvidenceRecord[]>([]);
  const [attempts, setAttempts] = useState<ClientScenarioAttemptRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditingTarget, setIsEditingTarget] = useState(false);
  const [showPurgeConfirm, setShowPurgeConfirm] = useState(false);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("SCEN-DATA-01-SQL");

  // Form state for profile setup/editing
  const [formFamily, setFormFamily] = useState<string>("DATA");
  const [formRole, setFormRole] = useState("Data Analyst");
  const [formLevel, setFormLevel] = useState<TargetLevel>("L3_mid");
  const [formHours, setFormHours] = useState(10);

  const loadLocalData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [p, r, a] = await Promise.all([
        getCareerProfile(),
        getAllLedgerRecords(),
        getScenarioAttempts(),
      ]);
      setProfile(p);
      setRecords(r);
      setAttempts(a);
      if (p) {
        setFormRole(p.target_role);
        setFormLevel(p.target_level);
        setFormHours(p.available_hours_per_week);
        setFormFamily(p.target_family || "DATA");
      }
    } catch (err) {
      console.error("Failed to load local career data:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLocalData();
  }, [loadLocalData]);

  const handleSubViewSelect = (view: CareerSubView): void => {
    setSubView(view);
    if (onSubViewChange) {
      onSubViewChange(view);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    await saveCareerProfile({
      target_role: formRole,
      target_level: formLevel,
      target_family: formFamily,
      available_hours_per_week: Number(formHours),
      updated_at: new Date().toISOString(),
    });
    setIsEditingTarget(false);
    await loadLocalData();
  };

  const handleExportBackup = async (): Promise<void> => {
    try {
      const backup = await exportLedgerBackup();
      const blob = new Blob([JSON.stringify(backup, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `arthaiq-career-ledger-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export backup:", err);
    }
  };

  const handlePurgeData = async (): Promise<void> => {
    try {
      await purgeAllUserData();
      setShowPurgeConfirm(false);
      await loadLocalData();
    } catch (err) {
      console.error("Failed to purge data:", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Privacy Notice Banner (India DPDP Act 2023, Rule R-CR-12) */}
      <div
        className="p-4 rounded-control border border-rule bg-sheet text-ink text-xs flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3"
        role="region"
        aria-label="Local-first privacy status"
      >
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-ok" aria-hidden="true" />
          <p>
            <strong className="font-semibold text-ink">Local-First Storage:</strong>{" "}
            Career profile and evidence records reside purely on your device in IndexedDB.
            Zero server retention (DPDP Act 2023, ADR-0012).
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleExportBackup}
            className="px-2.5 py-1 rounded-control border border-rule text-ink-2 hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus font-medium transition-colors"
            aria-label="Export JSON backup of career ledger"
          >
            Export JSON
          </button>
          <button
            type="button"
            onClick={() => setShowPurgeConfirm(true)}
            className="px-2.5 py-1 rounded-control border border-alert text-alert hover:bg-alert-wash focus:outline-none focus:ring-2 focus:ring-focus font-medium transition-colors"
            aria-label="Erase All Data from this device"
          >
            Erase All Data
          </button>
        </div>
      </div>

      {/* Target Role & Profile Banner */}
      {isLoading ? (
        <div className="p-6 rounded-control border border-rule bg-sheet animate-pulse text-ink-3 text-sm">
          Loading local career profile...
        </div>
      ) : !profile || isEditingTarget ? (
        <div className="p-6 rounded-control border border-rule bg-sheet">
          <h2 className="text-lg font-serif font-semibold text-ink mb-2">
            {profile ? "Edit Career Target" : "Set Your Target Role"}
          </h2>
          <p className="text-xs text-ink-2 mb-4">
            Select your target specialization and weekly learning budget. The system
            calculates gaps and schedules topological practice milestones deterministically.
          </p>
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div>
                <label htmlFor="target-family" className="block text-xs font-semibold text-ink mb-1">
                  Role Family
                </label>
                <select
                  id="target-family"
                  value={formFamily}
                  onChange={(e) => {
                    const fam = e.target.value;
                    setFormFamily(fam);
                    if (fam === "SWE") {
                      setFormRole("Software Engineer (Backend)");
                    } else if (fam === "MLAI") {
                      setFormRole("Machine Learning Engineer");
                    } else {
                      setFormRole("Data Analyst");
                    }
                  }}
                  className="w-full px-3 py-2 rounded-control border border-rule-strong bg-sheet text-ink text-sm focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  <option value="DATA">Data & Analytics</option>
                  <option value="SWE">Software Engineering</option>
                  <option value="MLAI">Machine Learning & AI</option>
                </select>
              </div>

              <div>
                <label htmlFor="target-role" className="block text-xs font-semibold text-ink mb-1">
                  Target Role
                </label>
                <select
                  id="target-role"
                  value={formRole}
                  onChange={(e) => setFormRole(e.target.value)}
                  className="w-full px-3 py-2 rounded-control border border-rule-strong bg-sheet text-ink text-sm focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  {formFamily === "SWE" ? (
                    <>
                      <option value="Software Engineer (Backend)">Software Engineer (Backend)</option>
                      <option value="Software Engineer (Full-Stack)">Software Engineer (Full-Stack)</option>
                      <option value="Systems & Platform Engineer">Systems & Platform Engineer</option>
                    </>
                  ) : formFamily === "MLAI" ? (
                    <>
                      <option value="Machine Learning Engineer">Machine Learning Engineer</option>
                      <option value="AI Systems / LLM Engineer">AI Systems / LLM Engineer</option>
                      <option value="Applied AI Scientist">Applied AI Scientist</option>
                    </>
                  ) : (
                    <>
                      <option value="Data Analyst">Data Analyst</option>
                      <option value="Data Scientist">Data Scientist</option>
                      <option value="Data Engineer">Data Engineer</option>
                    </>
                  )}
                </select>
              </div>

              <div>
                <label htmlFor="target-level" className="block text-xs font-semibold text-ink mb-1">
                  Seniority Level
                </label>
                <select
                  id="target-level"
                  value={formLevel}
                  onChange={(e) => setFormLevel(e.target.value as TargetLevel)}
                  className="w-full px-3 py-2 rounded-control border border-rule-strong bg-sheet text-ink text-sm focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  <option value="L2_junior">Junior (L2 · 1-3 yrs)</option>
                  <option value="L3_mid">Mid-Level (L3 · 3-6 yrs)</option>
                  <option value="L4_senior">Senior (L4 · 6-10 yrs)</option>
                </select>
              </div>

              <div>
                <label htmlFor="target-hours" className="block text-xs font-semibold text-ink mb-1">
                  Available Study Hours / Week
                </label>
                <select
                  id="target-hours"
                  value={formHours}
                  onChange={(e) => setFormHours(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-control border border-rule-strong bg-sheet text-ink text-sm focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  <option value={5}>5 hours / week (Casual pace)</option>
                  <option value={10}>10 hours / week (Recommended pace)</option>
                  <option value={15}>15 hours / week (Accelerated pace)</option>
                  <option value={20}>20 hours / week (Intensive transition)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                className="px-4 py-2 rounded-control bg-span text-on-span font-semibold text-xs hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
              >
                Save Target Profile
              </button>
              {profile && (
                <button
                  type="button"
                  onClick={() => setIsEditingTarget(false)}
                  className="px-4 py-2 rounded-control border border-rule text-ink-2 font-medium text-xs hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>
      ) : (
        <div className="p-6 rounded-control border border-rule bg-sheet flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs uppercase tracking-wider font-semibold text-span">
                Target Specialization
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-span-wash text-span-strong font-medium">
                {profile.target_family} Family
              </span>
            </div>
            <h2 className="text-xl font-serif font-semibold text-ink">
              {profile.target_role}{" "}
              <span className="text-sm font-sans font-normal text-ink-2">
                ({profile.target_level === "L2_junior" ? "Junior L2" : profile.target_level === "L3_mid" ? "Mid-Level L3" : "Senior L4"})
              </span>
            </h2>
            <p className="text-xs text-ink-3 mt-1">
              Topological roadmap paced for {profile.available_hours_per_week} hours / week · Last updated{" "}
              {new Date(profile.updated_at).toLocaleDateString()}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsEditingTarget(true)}
            className="px-3 py-1.5 rounded-control border border-rule-strong text-ink text-xs font-medium hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
          >
            Change Target
          </button>
        </div>
      )}

      {/* Recommended Priority Next Step Card (T15.32) */}
      {!isLoading && (
        <NextStepCard
          profile={profile}
          records={records}
          onLaunchPractice={(scenarioId) => {
            setSelectedScenarioId(scenarioId);
            handleSubViewSelect("practice");
          }}
          onNavigateTab={(tab) => handleSubViewSelect(tab)}
        />
      )}

      {/* Sub-Navigation Tabs */}
      <div className="border-b border-rule">
        <nav
          className="flex space-x-6 text-sm font-medium"
          role="tablist"
          aria-label="Career Architect sub-views"
        >
          <button
            type="button"
            role="tab"
            id="tab-skills"
            aria-selected={subView === "skills"}
            aria-controls="panel-skills"
            onClick={() => handleSubViewSelect("skills")}
            className={`pb-3 font-semibold text-xs uppercase tracking-wider transition-colors border-b-2 ${
              subView === "skills"
                ? "border-span text-span"
                : "border-transparent text-ink-2 hover:text-ink hover:border-rule-strong"
            }`}
          >
            Skills & Gap Map
          </button>
          <button
            type="button"
            role="tab"
            id="tab-plan"
            aria-selected={subView === "plan"}
            aria-controls="panel-plan"
            onClick={() => handleSubViewSelect("plan")}
            className={`pb-3 font-semibold text-xs uppercase tracking-wider transition-colors border-b-2 ${
              subView === "plan"
                ? "border-span text-span"
                : "border-transparent text-ink-2 hover:text-ink hover:border-rule-strong"
            }`}
          >
            Roadmap Plan
          </button>
          <button
            type="button"
            role="tab"
            id="tab-practice"
            aria-selected={subView === "practice"}
            aria-controls="panel-practice"
            onClick={() => handleSubViewSelect("practice")}
            className={`pb-3 font-semibold text-xs uppercase tracking-wider transition-colors border-b-2 ${
              subView === "practice"
                ? "border-span text-span"
                : "border-transparent text-ink-2 hover:text-ink hover:border-rule-strong"
            }`}
          >
            Practice Workspace
          </button>
          <button
            type="button"
            role="tab"
            id="tab-ledger"
            aria-selected={subView === "ledger"}
            aria-controls="panel-ledger"
            onClick={() => handleSubViewSelect("ledger")}
            className={`pb-3 font-semibold text-xs uppercase tracking-wider transition-colors border-b-2 ${
              subView === "ledger"
                ? "border-span text-span"
                : "border-transparent text-ink-2 hover:text-ink hover:border-rule-strong"
            }`}
          >
            Evidence Ledger
          </button>
        </nav>
      </div>

      {/* Sub-view Panels */}
      {subView === "skills" && (
        <section
          id="panel-skills"
          role="tabpanel"
          aria-labelledby="tab-skills"
          className="space-y-4"
        >
          <GapMapView
            records={records}
            onRecordUpdated={loadLocalData}
            onNavigatePractice={() => handleSubViewSelect("practice")}
            roleFamily={profile?.target_family ?? "DATA"}
          />
        </section>
      )}

      {subView === "plan" && (
        <section
          id="panel-plan"
          role="tabpanel"
          aria-labelledby="tab-plan"
          className="space-y-6"
        >
          <RoadmapView
            initialWeeklyHours={profile?.available_hours_per_week ?? 10}
            records={records}
            onNavigatePractice={() => handleSubViewSelect("practice")}
            onNavigateSkills={() => handleSubViewSelect("skills")}
            roleFamily={profile?.target_family ?? "DATA"}
          />

          {/* Decoupled Market Compensation Context Overlay (T15.33, Rules R-CR-01, R-CR-02) */}
          <PayOverlayPanel
            profile={profile}
            onExploreCompensation={() => {
              window.location.hash = "#compensation";
            }}
          />
        </section>
      )}

      {subView === "practice" && (
        <section
          id="panel-practice"
          role="tabpanel"
          aria-labelledby="tab-practice"
          className="space-y-4"
        >
          <PracticeWorkspace
            key={selectedScenarioId}
            initialScenarioId={selectedScenarioId}
            attempts={attempts}
            onAttemptCompleted={() => loadLocalData()}
            roleFamily={profile?.target_family ?? "DATA"}
          />
        </section>
      )}

      {subView === "ledger" && (
        <section
          id="panel-ledger"
          role="tabpanel"
          aria-labelledby="tab-ledger"
          className="space-y-4"
        >
          <div className="p-6 rounded-control border border-rule bg-sheet">
            <h3 className="text-base font-serif font-semibold text-ink mb-2">
              On-Device Evidence Ledger
            </h3>
            <p className="text-xs text-ink-2 mb-4">
              Stored locally on this device in IndexedDB. All records are exportable and erasable
              under India DPDP Act 2023.
            </p>

            {records.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-rule rounded-control text-ink-3 text-xs">
                No competency evidence records found. Complete a practice scenario or self-attest skills to begin.
              </div>
            ) : (
              <div className="divide-y divide-rule border border-rule rounded-control overflow-hidden">
                {records.map((r) => (
                  <div key={r.competency_id} className="p-3 flex justify-between items-center text-xs">
                    <div>
                      <span className="font-mono font-semibold text-ink">{r.competency_id}</span>
                      <p className="text-ink-3 text-2xs mt-0.5">
                        Evidence: {r.evidence_type} · Updated {new Date(r.updated_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span
                      className={`px-2.5 py-1 rounded-full font-medium ${
                        r.verification_state === "demonstrated"
                          ? "bg-ok-wash text-ok"
                          : r.verification_state === "self_reported"
                          ? "bg-caution-wash text-caution"
                          : "bg-sunken text-ink-2"
                      }`}
                    >
                      {r.verification_state}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Confirmation Modal for Hard Purge (DPDP Act 2023) */}
      {showPurgeConfirm && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="purge-dialog-title"
        >
          <div
            className="modal-backdrop"
            onClick={() => setShowPurgeConfirm(false)}
            aria-hidden="true"
          />
          <div className="modal-panel p-6 max-w-md w-full bg-sheet border border-rule rounded-dialog shadow-xl relative z-50">
            <h3 id="purge-dialog-title" className="text-lg font-serif font-bold text-alert mb-2">
              Erase All Career Data?
            </h3>
            <p className="text-xs text-ink-2 mb-4 leading-relaxed">
              This action executes a single-click hard erasure of your local IndexedDB database
              under Section 12 of the Digital Personal Data Protection Act, 2023. All target
              profiles, evidence records, and practice attempts will be permanently wiped.
            </p>
            <div className="flex justify-end items-center gap-3">
              <button
                type="button"
                onClick={() => setShowPurgeConfirm(false)}
                className="px-3 py-1.5 rounded-control border border-rule text-ink-2 hover:bg-sunken text-xs font-medium focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePurgeData}
                className="px-3 py-1.5 rounded-control bg-alert text-sheet text-xs font-semibold hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
              >
                Permanently Erase
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CareerRoute;

