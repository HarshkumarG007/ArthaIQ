/**
 * ArthaIQ Career Architect Pilot Consent & Privacy Gateway (T20.01)
 *
 * Implements statutory informed consent and age verification under:
 * - India Digital Personal Data Protection Act, 2023 (DPDP Act):
 *   - Section 6: Notice and informed consent for voluntary pilot research
 *   - Section 9: Age verification gate (18+ declaration)
 *   - Section 12: Right to erasure (single-click hard purge)
 * - Consumer Protection Act, 2019 (CPA 2019):
 *   - Rule R-CR-01: Zero causal compensation promises
 *   - Rule R-CR-11: Practice, not certification
 * - Local-First Architecture:
 *   - Rule R-CR-12 / ADR-0012: On-device persistence, zero server-side profiles
 */

export interface PilotStratification {
  role_family: "DATA" | "SWE" | "MLAI";
  seniority_band: "junior" | "mid" | "senior" | "staff_plus";
  geographic_cluster: "BLR" | "DEL_NCR" | "HYD" | "PUN_MUM_CHE" | "OTHER";
}

export interface PilotConsentRecord {
  consent_id: string;
  consent_version: string;
  consented_at: string;
  age_confirmed_18_plus: boolean;
  voluntary_research_acknowledged: boolean;
  non_appraisal_acknowledged: boolean;
  right_to_erasure_acknowledged: boolean;
  stratification: PilotStratification;
  notes?: string;
}

export const PILOT_CONSENT_KEY = "arthaiq_pilot_consent_v1";

export const STATUTORY_NOTICES = {
  PURPOSE:
    "ArthaIQ Career Architect is a self-reflection and career decision-support tool. It is not an employer appraisal, compensation guarantee, or legal employment advice platform (Consumer Protection Act 2019, Rule R-CR-01).",
  LOCAL_FIRST:
    "All career profile data, competency gap states, and practice attempt records reside exclusively on your device in browser local storage (IndexedDB). Zero server-side user career profiles (India DPDP Act 2023, Rule R-CR-12).",
  PRACTICE_NOT_CERTIFICATION:
    "Practice scenarios provide technical flaw-finding practice and self-reflection; no certification, credential, accredited exam, or guaranteed salary is issued (Rule R-CR-11).",
  RIGHT_TO_ERASURE:
    "You may delete all locally stored data at any time by clicking 'Erase All My Data'. Erasure is immediate and irreversible; 0 bytes of your data is retained (India DPDP Act 2023 Section 12).",
  AGE_GATE:
    "In accordance with Section 9 of the DPDP Act 2023, pilot participants must be 18 years of age or older.",
} as const;

export function hasPilotConsent(): boolean {
  if (typeof window === "undefined" || !window.localStorage) {
    return false;
  }
  const item = window.localStorage.getItem(PILOT_CONSENT_KEY);
  if (!item) return false;
  try {
    const record = JSON.parse(item) as PilotConsentRecord;
    return Boolean(
      record &&
        record.age_confirmed_18_plus &&
        record.voluntary_research_acknowledged &&
        record.non_appraisal_acknowledged &&
        record.right_to_erasure_acknowledged
    );
  } catch {
    return false;
  }
}

export function getPilotConsent(): PilotConsentRecord | null {
  if (typeof window === "undefined" || !window.localStorage) {
    return null;
  }
  const item = window.localStorage.getItem(PILOT_CONSENT_KEY);
  if (!item) return null;
  try {
    return JSON.parse(item) as PilotConsentRecord;
  } catch {
    return null;
  }
}

export function savePilotConsent(record: PilotConsentRecord): void {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  window.localStorage.setItem(PILOT_CONSENT_KEY, JSON.stringify(record));
}

export function clearPilotConsent(): void {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  window.localStorage.removeItem(PILOT_CONSENT_KEY);
}
