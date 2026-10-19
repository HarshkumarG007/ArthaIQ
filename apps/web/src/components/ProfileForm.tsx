import React, { useState } from "react";
import { ProfileFormData } from "../lib/types";

export interface ProfileFormProps {
  initialValues?: Partial<ProfileFormData>;
  onSubmit: (data: ProfileFormData) => void;
  isLoading?: boolean;
  className?: string;
}

export const OCCUPATION_OPTIONS = [
  {
    id: "SWE",
    name: "Software Engineering",
    hint: "Backend, Frontend, Full Stack, Cloud, Systems",
  },
  {
    id: "DATA",
    name: "Data Science & Engineering",
    hint: "Data Scientist, Data Engineer, Analytics, BI",
  },
  {
    id: "MLAI",
    name: "Machine Learning & AI",
    hint: "ML Engineer, AI Researcher, MLOps, NLP/Vision",
  },
  {
    id: "OTHER",
    name: "Other Technical Roles",
    hint: "Architect, Engineering Manager, QA Automation",
  },
];

export const LOCATION_OPTIONS = [
  { id: "BENGALURU", name: "Bengaluru", state: "Karnataka" },
  { id: "HYDERABAD", name: "Hyderabad", state: "Telangana" },
  { id: "PUNE", name: "Pune", state: "Maharashtra" },
  { id: "NCR", name: "National Capital Region (NCR)", state: "Delhi, Gurgaon, Noida" },
  { id: "MUMBAI", name: "Mumbai", state: "Maharashtra" },
  { id: "CHENNAI", name: "Chennai", state: "Tamil Nadu" },
  { id: "REMOTE_INDIA", name: "Remote (India)", state: "All India" },
];

export const SENIORITY_OPTIONS = [
  { id: "ENTRY", label: "Entry / Early Career (0–2 years)" },
  { id: "MID", label: "Mid-Level Professional (3–5 years)" },
  { id: "SENIOR", label: "Senior Professional (6–10 years)" },
  { id: "STAFF", label: "Staff / Lead / Principal (11+ years)" },
];

/**
 * ProfileForm — Core query intake component.
 *
 * Implements:
 * - design.md section 8 & 9 (ProfileForm, OccupationCombobox, LocationSelect, Experience).
 * - Rule R-UI-04: Labels above fields, helper text below, error summary on submit, aria-describedby wiring.
 * - Minimum touch target 44px on primary controls.
 */
export function ProfileForm({
  initialValues,
  onSubmit,
  isLoading = false,
  className = "",
}: ProfileFormProps): React.JSX.Element {
  const [occupationId, setOccupationId] = useState<string>(
    initialValues?.occupation_id || "SWE"
  );
  const [locationId, setLocationId] = useState<string>(
    initialValues?.location_id || "BENGALURU"
  );
  const [yearsExperience, setYearsExperience] = useState<string>(
    initialValues?.years_experience !== null && initialValues?.years_experience !== undefined
      ? String(initialValues.years_experience)
      : "4.0"
  );
  const [notSureExperience, setNotSureExperience] = useState<boolean>(
    initialValues?.not_sure_experience || false
  );
  const [seniorityLevel, setSeniorityLevel] = useState<string>(
    initialValues?.seniority_level || "MID"
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errs: Record<string, string> = {};

    if (!occupationId) {
      errs.occupation = "Please select a role family.";
    }
    if (!locationId) {
      errs.location = "Please select an employment location.";
    }

    if (!notSureExperience) {
      const parsed = parseFloat(yearsExperience);
      if (isNaN(parsed)) {
        errs.experience = "Enter years of relevant experience as a number.";
      } else if (parsed < 0 || parsed > 40) {
        errs.experience = "Experience must be between 0 and 40 years.";
      }
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    if (!validate()) return;

    const parsedYears = notSureExperience ? null : parseFloat(yearsExperience);

    onSubmit({
      occupation_id: occupationId,
      location_id: locationId,
      years_experience: parsedYears,
      not_sure_experience: notSureExperience,
      seniority_level: notSureExperience ? seniorityLevel : undefined,
    });
  };

  return (
    <form
      data-testid="profile-form"
      onSubmit={handleSubmit}
      noValidate
      className={`w-full max-w-xl mx-auto flex flex-col gap-6 text-left ${className}`}
    >
      <div>
        <h2 className="text-base font-serif font-semibold text-ink">
          About the role
        </h2>
        <p className="text-xs font-sans text-ink-3 mt-1">
          Provide your role details to calibrate a compensation range with statistical support.
        </p>
      </div>

      {/* Error summary if validation failed */}
      {Object.keys(errors).length > 0 && (
        <div
          role="alert"
          data-testid="form-error-summary"
          className="p-3 rounded-control bg-alert-wash border border-alert/30 text-alert text-xs font-sans"
        >
          <div className="font-semibold mb-1 flex items-center gap-1.5">
            <svg className="w-4 h-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            Please check the following details:
          </div>
          <ul className="list-disc pl-5 space-y-0.5">
            {Object.values(errors).map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 1. Role / Occupation */}
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="profile-occupation"
          className="text-xs font-sans font-medium text-ink"
        >
          Role family
        </label>
        <select
          id="profile-occupation"
          value={occupationId}
          onChange={(e) => setOccupationId(e.target.value)}
          aria-describedby="profile-occupation-helper"
          className="w-full px-3 py-2.5 bg-sheet border border-rule-strong rounded-control text-sm font-sans text-ink focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
        >
          {OCCUPATION_OPTIONS.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.name}
            </option>
          ))}
        </select>
        <p id="profile-occupation-helper" className="text-[11px] font-sans text-ink-3">
          {OCCUPATION_OPTIONS.find((o) => o.id === occupationId)?.hint}
        </p>
      </div>

      {/* 2. Location */}
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="profile-location"
          className="text-xs font-sans font-medium text-ink"
        >
          Employment location
        </label>
        <select
          id="profile-location"
          value={locationId}
          onChange={(e) => setLocationId(e.target.value)}
          aria-describedby="profile-location-helper"
          className="w-full px-3 py-2.5 bg-sheet border border-rule-strong rounded-control text-sm font-sans text-ink focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
        >
          {LOCATION_OPTIONS.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.name} ({loc.state})
            </option>
          ))}
        </select>
        <p id="profile-location-helper" className="text-[11px] font-sans text-ink-3">
          Geographic calibration aligns with metropolitan tech employment markets.
        </p>
      </div>

      {/* 3. Years of Experience */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="profile-experience"
            className="text-xs font-sans font-medium text-ink"
          >
            Years of relevant experience
          </label>
          <label className="inline-flex items-center gap-1.5 text-xs font-sans text-ink-2 cursor-pointer">
            <input
              type="checkbox"
              id="not-sure-experience-checkbox"
              checked={notSureExperience}
              onChange={(e) => setNotSureExperience(e.target.checked)}
              className="rounded border-rule-strong text-span focus:ring-focus"
            />
            Not sure
          </label>
        </div>

        {!notSureExperience ? (
          <div>
            <input
              id="profile-experience"
              type="number"
              inputMode="decimal"
              step="0.5"
              min="0"
              max="40"
              value={yearsExperience}
              onChange={(e) => setYearsExperience(e.target.value)}
              aria-describedby="profile-experience-helper"
              placeholder="e.g. 4.5"
              className="w-full px-3 py-2.5 bg-sheet border border-rule-strong rounded-control text-sm font-sans text-ink focus:outline-none focus:ring-2 focus:ring-focus tabular-nums min-h-[44px]"
            />
            <p id="profile-experience-helper" className="text-[11px] font-sans text-ink-3 mt-1.5">
              Count time in similar roles. Round to the nearest half year.
            </p>
          </div>
        ) : (
          <div>
            <select
              id="profile-seniority-fallback"
              value={seniorityLevel}
              onChange={(e) => setSeniorityLevel(e.target.value)}
              className="w-full px-3 py-2.5 bg-sheet border border-rule-strong rounded-control text-sm font-sans text-ink focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
            >
              {SENIORITY_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
            <p className="text-[11px] font-sans text-ink-3 mt-1.5">
              We will estimate compensation based on your approximate career tier.
            </p>
          </div>
        )}
      </div>

      {/* Primary Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        aria-busy={isLoading}
        className="w-full mt-2 px-6 py-3 bg-span text-on-span font-sans font-medium text-sm rounded-control hover:bg-span-strong focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px] transition-colors shadow-sm disabled:opacity-60 flex items-center justify-center gap-2 cursor-pointer"
      >
        {isLoading ? (
          <span>Computing calibrated range...</span>
        ) : (
          <span>Show estimated range</span>
        )}
      </button>
    </form>
  );
}

export default ProfileForm;
