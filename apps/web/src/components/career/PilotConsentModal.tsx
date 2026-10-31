import React, { useState } from "react";
import {
  savePilotConsent,
  STATUTORY_NOTICES,
  type PilotConsentRecord,
  type PilotStratification,
} from "../../lib/pilotConsent";
import { Shield, Trash2, CheckCircle2 } from "lucide-react";

export interface PilotConsentModalProps {
  isOpen: boolean;
  onConsent: (record: PilotConsentRecord) => void;
  onClose?: () => void;
  onPurgeAllData?: () => Promise<void>;
  initialStratification?: Partial<PilotStratification>;
}

export function PilotConsentModal({
  isOpen,
  onConsent,
  onClose,
  onPurgeAllData,
  initialStratification,
}: PilotConsentModalProps): React.JSX.Element | null {
  const [ageConfirmed, setAgeConfirmed] = useState(false);
  const [voluntaryConfirmed, setVoluntaryConfirmed] = useState(false);
  const [nonAppraisalConfirmed, setNonAppraisalConfirmed] = useState(false);

  const [roleFamily, setRoleFamily] = useState<"DATA" | "SWE" | "MLAI">(
    initialStratification?.role_family || "DATA"
  );
  const [seniorityBand, setSeniorityBand] = useState<
    "junior" | "mid" | "senior" | "staff_plus"
  >(initialStratification?.seniority_band || "mid");
  const [geographicCluster, setGeographicCluster] = useState<
    "BLR" | "DEL_NCR" | "HYD" | "PUN_MUM_CHE" | "OTHER"
  >(initialStratification?.geographic_cluster || "BLR");

  const [isPurging, setIsPurging] = useState(false);
  const [purgeSuccess, setPurgeSuccess] = useState(false);

  if (!isOpen) {
    return null;
  }

  const isFormValid = ageConfirmed && voluntaryConfirmed && nonAppraisalConfirmed;

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    if (!isFormValid) return;

    const record: PilotConsentRecord = {
      consent_id: `CONSENT-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
      consent_version: "2026-10-dpdp-v1",
      consented_at: new Date().toISOString(),
      age_confirmed_18_plus: true,
      voluntary_research_acknowledged: true,
      non_appraisal_acknowledged: true,
      right_to_erasure_acknowledged: true,
      stratification: {
        role_family: roleFamily,
        seniority_band: seniorityBand,
        geographic_cluster: geographicCluster,
      },
    };

    savePilotConsent(record);
    onConsent(record);
  };

  const handleHardPurge = async (): Promise<void> => {
    if (onPurgeAllData) {
      setIsPurging(true);
      try {
        await onPurgeAllData();
        setPurgeSuccess(true);
        setAgeConfirmed(false);
        setVoluntaryConfirmed(false);
        setNonAppraisalConfirmed(false);
      } finally {
        setIsPurging(false);
      }
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pilot-consent-title"
      aria-describedby="pilot-consent-desc"
    >
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-sheet border border-rule rounded-modal shadow-float p-6 text-ink space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-rule pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-control bg-accent-soft text-accent" aria-hidden="true">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h2 id="pilot-consent-title" className="text-lg font-bold text-ink">
                ArthaIQ Career Architect — Pilot Consent
              </h2>
              <p id="pilot-consent-desc" className="text-xs text-ink-2">
                Statutory Participant Notice under India DPDP Act 2023 & CPA 2019
              </p>
            </div>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-ink-3 hover:text-ink p-1 rounded-control focus:outline-none focus:ring-2 focus:ring-focus"
              aria-label="Close consent modal"
            >
              ✕
            </button>
          )}
        </div>

        {/* Purge Success Banner */}
        {purgeSuccess && (
          <div
            className="p-3 bg-ok-soft border border-ok/30 rounded-control text-xs text-ok flex items-center gap-2"
            role="alert"
          >
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>
              All on-device user data has been permanently erased. 0 bytes retained.
            </span>
          </div>
        )}

        {/* Statutory Notices Block */}
        <div className="space-y-3 text-xs bg-sunken p-4 rounded-control border border-rule">
          <div>
            <strong className="text-ink font-semibold">1. Voluntary Decision Support:</strong>{" "}
            <span className="text-ink-2">{STATUTORY_NOTICES.PURPOSE}</span>
          </div>
          <div>
            <strong className="text-ink font-semibold">2. Local-First Privacy (DPDP Act Sec 6):</strong>{" "}
            <span className="text-ink-2">{STATUTORY_NOTICES.LOCAL_FIRST}</span>
          </div>
          <div>
            <strong className="text-ink font-semibold">3. Practice, Not Certification:</strong>{" "}
            <span className="text-ink-2">{STATUTORY_NOTICES.PRACTICE_NOT_CERTIFICATION}</span>
          </div>
          <div>
            <strong className="text-ink font-semibold">4. Right to Erasure (DPDP Act Sec 12):</strong>{" "}
            <span className="text-ink-2">{STATUTORY_NOTICES.RIGHT_TO_ERASURE}</span>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Stratification Selectors */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-ink uppercase tracking-wider">
              Pilot Cohort Stratification
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label
                  htmlFor="strat-role-family"
                  className="block text-xs font-medium text-ink-2 mb-1"
                >
                  Role Family
                </label>
                <select
                  id="strat-role-family"
                  value={roleFamily}
                  onChange={(e) => setRoleFamily(e.target.value as "DATA" | "SWE" | "MLAI")}
                  className="w-full text-xs p-2 rounded-control border border-rule bg-sheet text-ink focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  <option value="DATA">Data & AI</option>
                  <option value="SWE">Software Engineering</option>
                  <option value="MLAI">Machine Learning & AI</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="strat-seniority-band"
                  className="block text-xs font-medium text-ink-2 mb-1"
                >
                  Seniority Band
                </label>
                <select
                  id="strat-seniority-band"
                  value={seniorityBand}
                  onChange={(e) =>
                    setSeniorityBand(
                      e.target.value as "junior" | "mid" | "senior" | "staff_plus"
                    )
                  }
                  className="w-full text-xs p-2 rounded-control border border-rule bg-sheet text-ink focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  <option value="junior">Junior (0–2 YoE)</option>
                  <option value="mid">Mid-Level (3–5 YoE)</option>
                  <option value="senior">Senior (6–9 YoE)</option>
                  <option value="staff_plus">Staff / Principal (10+ YoE)</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="strat-geo-cluster"
                  className="block text-xs font-medium text-ink-2 mb-1"
                >
                  Metro Location
                </label>
                <select
                  id="strat-geo-cluster"
                  value={geographicCluster}
                  onChange={(e) =>
                    setGeographicCluster(
                      e.target.value as "BLR" | "DEL_NCR" | "HYD" | "PUN_MUM_CHE" | "OTHER"
                    )
                  }
                  className="w-full text-xs p-2 rounded-control border border-rule bg-sheet text-ink focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  <option value="BLR">Bengaluru Metro</option>
                  <option value="DEL_NCR">Delhi NCR</option>
                  <option value="HYD">Hyderabad</option>
                  <option value="PUN_MUM_CHE">Pune / Mumbai / Chennai</option>
                  <option value="OTHER">Other / Tier-2/3</option>
                </select>
              </div>
            </div>
          </div>

          {/* Acknowledgments */}
          <div className="space-y-3 pt-2 border-t border-rule">
            <h3 className="text-xs font-bold text-ink uppercase tracking-wider">
              Mandatory Statutory Declarations
            </h3>

            <div className="space-y-2">
              <label className="flex items-start gap-2.5 text-xs text-ink cursor-pointer">
                <input
                  type="checkbox"
                  id="pilot-age-gate"
                  checked={ageConfirmed}
                  onChange={(e) => setAgeConfirmed(e.target.checked)}
                  className="mt-0.5 rounded border-rule text-accent focus:ring-focus"
                />
                <span>
                  <strong>Age Verification (DPDP Act Sec 9):</strong> I confirm that I am 18 years
                  of age or older.
                </span>
              </label>

              <label className="flex items-start gap-2.5 text-xs text-ink cursor-pointer">
                <input
                  type="checkbox"
                  id="pilot-voluntary-gate"
                  checked={voluntaryConfirmed}
                  onChange={(e) => setVoluntaryConfirmed(e.target.checked)}
                  className="mt-0.5 rounded border-rule text-accent focus:ring-focus"
                />
                <span>
                  <strong>Voluntary Participation (DPDP Act Sec 6):</strong> I acknowledge that
                  all my data resides exclusively on this device and consent to participating in
                  this voluntary study.
                </span>
              </label>

              <label className="flex items-start gap-2.5 text-xs text-ink cursor-pointer">
                <input
                  type="checkbox"
                  id="pilot-non-appraisal-gate"
                  checked={nonAppraisalConfirmed}
                  onChange={(e) => setNonAppraisalConfirmed(e.target.checked)}
                  className="mt-0.5 rounded border-rule text-accent focus:ring-focus"
                />
                <span>
                  <strong>Non-Appraisal Notice (CPA 2019 / R-CR-01):</strong> I understand that
                  ArthaIQ does NOT guarantee salary increases, promotions, employment offers, or
                  formal certifications.
                </span>
              </label>
            </div>
          </div>

          {/* Action Footer */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-rule">
            {onPurgeAllData && (
              <button
                type="button"
                onClick={handleHardPurge}
                disabled={isPurging}
                className="w-full sm:w-auto px-3 py-1.5 text-xs font-medium text-alert border border-alert/30 hover:bg-alert-soft rounded-control transition-colors flex items-center justify-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-focus"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{isPurging ? "Erasing..." : "Erase All My Data (Sec 12)"}</span>
              </button>
            )}

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              {onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-ink-2 hover:text-ink hover:bg-sunken rounded-control transition-colors focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                disabled={!isFormValid}
                className="w-full sm:w-auto px-5 py-2 text-xs font-semibold rounded-control bg-accent text-white hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-subtle focus:outline-none focus:ring-2 focus:ring-focus"
              >
                Agree & Begin Pilot
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
