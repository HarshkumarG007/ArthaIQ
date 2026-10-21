/**
 * ContributionFlow — Multi-step voluntary pay intake (PRD US-07, ADR-0008, Rule R-FA-01).
 *
 * Step 1: Unbundled, unchecked consent checkboxes (DPDPA 2023).
 * Step 2: Role, location, tenure, and compensation input using MoneyField.
 * Step 3: Confirmation with summary, copyable cryptographic deletion token.
 *
 * Invariants:
 * - Consent checkboxes are unchecked by default; benchmarking is required to proceed.
 * - No "overpaid" / "underpaid" language anywhere (Rule R-MD-13).
 * - Zero document uploads.
 * - Deletion token is presented once and must be copied by the user.
 */
import { useCallback, useId, useRef, useState } from "react";
import { MoneyField, PayPeriod, CompensationMeasureType } from "./MoneyField";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface ContributionConsentState {
  benchmarking: boolean;
  research: boolean;
  futureContact: boolean;
}

export interface ContributionPayload {
  roleFamilyRaw: string;
  titleRaw: string;
  seniority: string;
  location: string;
  yearsExperience: string;
  guaranteedCashAnnualLpa: number | null;
  measureType: CompensationMeasureType;
  payPeriod: PayPeriod;
}

export interface ContributionFlowProps {
  /** Called when the form is dismissed without submitting. */
  onClose: () => void;
  /** Called when the flow is completed and a deletion token has been issued. */
  onComplete?: (deletionToken: string) => void;
  /** Override API endpoint for testing. Defaults to /v1/contributions. */
  apiEndpoint?: string;
}

type Step = "consent" | "pay" | "confirm";

interface ApiReceipt {
  contribution_id: string;
  contributor_key: string;
  deletion_token: string;
  status: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const SENIORITY_OPTIONS = [
  { value: "IC1_ENTRY", label: "Entry / Fresher (0-2 yrs)" },
  { value: "IC2_MID", label: "Mid-level (3-5 yrs)" },
  { value: "IC3_SENIOR", label: "Senior (6-9 yrs)" },
  { value: "IC4_STAFF", label: "Staff / Principal (10+ yrs)" },
  { value: "IC5_DIRECTOR", label: "Director / VP" },
  { value: "M1_MANAGER", label: "Engineering Manager" },
];

const LOCATION_OPTIONS = [
  { value: "BLR", label: "Bengaluru" },
  { value: "HYD", label: "Hyderabad" },
  { value: "MUM", label: "Mumbai" },
  { value: "DEL", label: "Delhi / NCR" },
  { value: "CHN", label: "Chennai" },
  { value: "PUN", label: "Pune" },
  { value: "OTHER", label: "Other" },
];

function isValidYears(raw: string): boolean {
  const n = parseFloat(raw);
  return !isNaN(n) && n >= 0 && n <= 40;
}

// ---------------------------------------------------------------------------
// Step 1: Consent
// ---------------------------------------------------------------------------
interface ConsentStepProps {
  consent: ContributionConsentState;
  onChange: (next: ContributionConsentState) => void;
  onNext: () => void;
  onClose: () => void;
}

function ConsentStep({ consent, onChange, onNext, onClose }: ConsentStepProps) {
  const benchId = useId();
  const researchId = useId();
  const contactId = useId();

  return (
    <div className="cf-step" role="group" aria-labelledby="cf-consent-heading">
      <h2 id="cf-consent-heading" className="cf-step-heading">
        Before you share your pay
      </h2>
      <p className="cf-step-description">
        Your contribution improves salary estimates for others. We collect only
        what you choose to share, and we never link your data to your identity
        without your permission.
      </p>

      <div className="cf-consent-box" role="group" aria-label="Consent options">
        <p className="cf-consent-note">
          Please read and tick each purpose you agree to. These consents are
          independent and all are <strong>unchecked</strong> by default.
        </p>

        <label className="cf-consent-item cf-consent-required" htmlFor={benchId}>
          <input
            id={benchId}
            type="checkbox"
            checked={consent.benchmarking}
            onChange={(e) =>
              onChange({ ...consent, benchmarking: e.target.checked })
            }
            aria-required="true"
          />
          <span className="cf-consent-label">
            <strong>Use my pay data for salary range estimates</strong>
            <span className="cf-consent-required-badge" aria-label="required">
              Required
            </span>
          </span>
          <span className="cf-consent-hint">
            Your anonymised compensation will be included in aggregate salary
            range calculations. We never publish individual records. You can
            delete your contribution at any time using your deletion token.
          </span>
        </label>

        <label className="cf-consent-item" htmlFor={researchId}>
          <input
            id={researchId}
            type="checkbox"
            checked={consent.research}
            onChange={(e) =>
              onChange({ ...consent, research: e.target.checked })
            }
          />
          <span className="cf-consent-label">
            Use my data for anonymised research and trend reports (optional)
          </span>
          <span className="cf-consent-hint">
            We may publish aggregate, non-identifying findings such as
            compensation trends by sector or city.
          </span>
        </label>

        <label className="cf-consent-item" htmlFor={contactId}>
          <input
            id={contactId}
            type="checkbox"
            checked={consent.futureContact}
            onChange={(e) =>
              onChange({ ...consent, futureContact: e.target.checked })
            }
          />
          <span className="cf-consent-label">
            Contact me if my contribution is queried for quality review (optional)
          </span>
          <span className="cf-consent-hint">
            We may reach out via the email you provide in the next step if a
            data quality issue is detected.
          </span>
        </label>
      </div>

      <p className="cf-legal-notice">
        By proceeding you confirm that this information reflects your own
        compensation. Under DPDPA 2023, you have the right to withdraw consent
        and request deletion at any time using your deletion token.
      </p>

      <div className="cf-actions">
        <button
          type="button"
          className="cf-btn cf-btn-ghost"
          onClick={onClose}
          aria-label="Cancel contribution"
        >
          Cancel
        </button>
        <button
          type="button"
          className="cf-btn cf-btn-primary"
          onClick={onNext}
          disabled={!consent.benchmarking}
          aria-disabled={!consent.benchmarking}
        >
          Continue
        </button>
      </div>
      {!consent.benchmarking && (
        <p className="cf-field-error" role="alert">
          You must tick "Use my pay data for salary range estimates" to continue.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 2: Pay Entry
// ---------------------------------------------------------------------------
interface PayStepProps {
  payload: ContributionPayload;
  onChange: (next: Partial<ContributionPayload>) => void;
  onNext: () => void;
  onBack: () => void;
  submitError: string | null;
}

function PayStep({ payload, onChange, onNext, onBack, submitError }: PayStepProps) {
  const roleId = useId();
  const titleId = useId();
  const seniorityId = useId();
  const locationId = useId();
  const yearsId = useId();
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validate = useCallback((): boolean => {
    const errors: Record<string, string> = {};
    if (!payload.roleFamilyRaw.trim())
      errors.role = "Role / function is required.";
    if (!payload.seniority) errors.seniority = "Please select a seniority level.";
    if (!payload.location) errors.location = "Please select a location.";
    if (!payload.yearsExperience || !isValidYears(payload.yearsExperience))
      errors.years = "Enter years of experience (0-40).";
    if (!payload.guaranteedCashAnnualLpa || payload.guaranteedCashAnnualLpa <= 0)
      errors.pay = "Enter your compensation.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }, [payload]);

  const handleNext = () => {
    if (validate()) onNext();
  };

  return (
    <div className="cf-step" role="group" aria-labelledby="cf-pay-heading">
      <h2 id="cf-pay-heading" className="cf-step-heading">
        Your role and compensation
      </h2>
      <p className="cf-step-description">
        Only the fields marked * are required. All data is anonymised before
        any aggregation.
      </p>

      {submitError && (
        <div className="cf-error-banner" role="alert" aria-live="assertive">
          {submitError}
        </div>
      )}

      <div className="cf-form-grid">
        <div className="cf-field">
          <label htmlFor={roleId} className="cf-label">
            Role / function <span aria-hidden="true">*</span>
          </label>
          <input
            id={roleId}
            type="text"
            className={`cf-input${fieldErrors.role ? " cf-input-error" : ""}`}
            placeholder="e.g. Software Engineer, Product Manager"
            value={payload.roleFamilyRaw}
            onChange={(e) => onChange({ roleFamilyRaw: e.target.value })}
            aria-required="true"
            aria-describedby={fieldErrors.role ? `${roleId}-err` : undefined}
          />
          {fieldErrors.role && (
            <span id={`${roleId}-err`} className="cf-field-error" role="alert">
              {fieldErrors.role}
            </span>
          )}
        </div>

        <div className="cf-field">
          <label htmlFor={titleId} className="cf-label">
            Job title (optional)
          </label>
          <input
            id={titleId}
            type="text"
            className="cf-input"
            placeholder="e.g. Senior Backend Engineer"
            value={payload.titleRaw}
            onChange={(e) => onChange({ titleRaw: e.target.value })}
          />
        </div>

        <div className="cf-field">
          <label htmlFor={seniorityId} className="cf-label">
            Seniority level <span aria-hidden="true">*</span>
          </label>
          <select
            id={seniorityId}
            className={`cf-select${fieldErrors.seniority ? " cf-input-error" : ""}`}
            value={payload.seniority}
            onChange={(e) => onChange({ seniority: e.target.value })}
            aria-required="true"
            aria-describedby={fieldErrors.seniority ? `${seniorityId}-err` : undefined}
          >
            <option value="">Select seniority...</option>
            {SENIORITY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          {fieldErrors.seniority && (
            <span id={`${seniorityId}-err`} className="cf-field-error" role="alert">
              {fieldErrors.seniority}
            </span>
          )}
        </div>

        <div className="cf-field">
          <label htmlFor={locationId} className="cf-label">
            Primary work location <span aria-hidden="true">*</span>
          </label>
          <select
            id={locationId}
            className={`cf-select${fieldErrors.location ? " cf-input-error" : ""}`}
            value={payload.location}
            onChange={(e) => onChange({ location: e.target.value })}
            aria-required="true"
            aria-describedby={fieldErrors.location ? `${locationId}-err` : undefined}
          >
            <option value="">Select city...</option>
            {LOCATION_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          {fieldErrors.location && (
            <span id={`${locationId}-err`} className="cf-field-error" role="alert">
              {fieldErrors.location}
            </span>
          )}
        </div>

        <div className="cf-field">
          <label htmlFor={yearsId} className="cf-label">
            Total years of professional experience <span aria-hidden="true">*</span>
          </label>
          <input
            id={yearsId}
            type="number"
            className={`cf-input${fieldErrors.years ? " cf-input-error" : ""}`}
            min={0}
            max={40}
            step={0.5}
            placeholder="e.g. 6"
            value={payload.yearsExperience}
            onChange={(e) => onChange({ yearsExperience: e.target.value })}
            aria-required="true"
            aria-describedby={fieldErrors.years ? `${yearsId}-err` : undefined}
          />
          {fieldErrors.years && (
            <span id={`${yearsId}-err`} className="cf-field-error" role="alert">
              {fieldErrors.years}
            </span>
          )}
        </div>

        <div className="cf-field cf-field-full">
          <MoneyField
            label="Your compensation *"
            helperText="We accept any figure; choose the type that matches what you know."
            value={payload.guaranteedCashAnnualLpa}
            onChange={(lpa, period, measure) =>
              onChange({
                guaranteedCashAnnualLpa: lpa,
                payPeriod: period,
                measureType: measure,
              })
            }
          />
          {fieldErrors.pay && (
            <span className="cf-field-error" role="alert">
              {fieldErrors.pay}
            </span>
          )}
          <p className="cf-definitional-note">
            <strong>Which figure should I enter?</strong> The estimate uses
            annual fixed cash (base salary + fixed allowances, pre-tax). If you
            enter CTC, monthly, or bonus-inclusive figures, we normalise them
            using EPFO-calibrated rates.
          </p>
        </div>
      </div>

      <div className="cf-actions">
        <button type="button" className="cf-btn cf-btn-ghost" onClick={onBack}>
          Back
        </button>
        <button type="button" className="cf-btn cf-btn-primary" onClick={handleNext}>
          Review and submit
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 3: Confirmation
// ---------------------------------------------------------------------------
interface ConfirmStepProps {
  receipt: ApiReceipt;
  onClose: () => void;
}

function ConfirmStep({ receipt, onClose }: ConfirmStepProps) {
  const [copied, setCopied] = useState(false);
  const tokenRef = useRef<HTMLElement>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(receipt.deletion_token);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      tokenRef.current?.focus();
    }
  };

  return (
    <div className="cf-step cf-step-confirm" aria-labelledby="cf-confirm-heading">
      <div className="cf-confirm-icon" aria-hidden="true">checkmark</div>
      <h2 id="cf-confirm-heading" className="cf-step-heading">
        Thank you for contributing
      </h2>
      <p className="cf-step-description">
        {receipt.status === "quarantined"
          ? "Your contribution was received and is being reviewed before it is included in the aggregate."
          : "Your contribution has been included in the anonymised aggregate. It will be reflected in the next scheduled data refresh."}
      </p>

      <div
        className="cf-token-box"
        role="region"
        aria-label="Deletion token - save this"
      >
        <p className="cf-token-heading">
          <strong>Save your deletion token</strong>
        </p>
        <p className="cf-token-description">
          This token lets you permanently delete your contribution at any time.
          We cannot recover it - store it somewhere safe.
        </p>
        <code
          ref={tokenRef}
          className="cf-token-value"
          aria-label="Deletion token"
          tabIndex={0}
        >
          {receipt.deletion_token}
        </code>
        <button
          type="button"
          className="cf-btn cf-btn-secondary cf-copy-btn"
          onClick={handleCopy}
          aria-label={copied ? "Token copied to clipboard" : "Copy deletion token to clipboard"}
          aria-live="polite"
        >
          {copied ? "Copied!" : "Copy token"}
        </button>
      </div>

      <p className="cf-token-footer">
        To delete your contribution in the future, click "My Data" and enter
        this token, or contact us with your token and we will complete the
        erasure within 72 hours.
      </p>

      <div className="cf-actions">
        <button
          type="button"
          className="cf-btn cf-btn-primary"
          onClick={onClose}
        >
          Close
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main: ContributionFlow
// ---------------------------------------------------------------------------
export function ContributionFlow({
  onClose,
  onComplete,
  apiEndpoint = "/v1/contributions",
}: ContributionFlowProps) {
  const [step, setStep] = useState<Step>("consent");
  const [consent, setConsent] = useState<ContributionConsentState>({
    benchmarking: false,
    research: false,
    futureContact: false,
  });
  const [payload, setPayload] = useState<ContributionPayload>({
    roleFamilyRaw: "",
    titleRaw: "",
    seniority: "",
    location: "",
    yearsExperience: "",
    guaranteedCashAnnualLpa: null,
    measureType: "guaranteed_cash",
    payPeriod: "annual",
  });
  const [receipt, setReceipt] = useState<ApiReceipt | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const body = {
        role_family: payload.roleFamilyRaw.trim().toLowerCase().replace(/\s+/g, "_"),
        title_raw: payload.titleRaw.trim() || payload.roleFamilyRaw.trim(),
        seniority: payload.seniority,
        location: payload.location,
        years_experience: parseFloat(payload.yearsExperience),
        guaranteed_cash_annual: payload.guaranteedCashAnnualLpa
          ? payload.guaranteedCashAnnualLpa * 100_000
          : 0,
        currency: "INR",
        consent_benchmarking: consent.benchmarking,
        consent_research: consent.research,
        consent_future_contact: consent.futureContact,
        consent_version: "dpdpa_v1",
      };
      const res = await fetch(apiEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(
          data.detail ?? `Submission failed (HTTP ${res.status}). Please try again.`
        );
      }
      const data = (await res.json()) as ApiReceipt;
      setReceipt(data);
      setStep("confirm");
      onComplete?.(data.deletion_token);
    } catch (err: unknown) {
      setSubmitError(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const STEP_LABELS: Record<Step, string> = {
    consent: "Step 1 of 3: Consent",
    pay: "Step 2 of 3: Compensation",
    confirm: "Step 3 of 3: Confirmation",
  };

  return (
    <section
      className="contribution-flow"
      aria-label="Voluntary pay contribution"
      role="region"
    >
      <div className="cf-progress" aria-label={STEP_LABELS[step]} role="status">
        {(["consent", "pay", "confirm"] as Step[]).map((s, i) => (
          <div
            key={s}
            className={[
              "cf-progress-step",
              step === s ? "cf-progress-active" : "",
              (step === "pay" && s === "consent") ||
              (step === "confirm" && s !== "confirm")
                ? "cf-progress-done"
                : "",
            ]
              .filter(Boolean)
              .join(" ")}
            aria-current={step === s ? "step" : undefined}
          >
            <span className="cf-progress-number">{i + 1}</span>
          </div>
        ))}
      </div>

      {step === "consent" && (
        <ConsentStep
          consent={consent}
          onChange={setConsent}
          onNext={() => setStep("pay")}
          onClose={onClose}
        />
      )}

      {step === "pay" && (
        <>
          {isSubmitting ? (
            <div className="cf-loading" role="status" aria-live="polite">
              Submitting your contribution...
            </div>
          ) : (
            <PayStep
              payload={payload}
              onChange={(partial) => setPayload((p) => ({ ...p, ...partial }))}
              onNext={handleSubmit}
              onBack={() => setStep("consent")}
              submitError={submitError}
            />
          )}
        </>
      )}

      {step === "confirm" && receipt && (
        <ConfirmStep receipt={receipt} onClose={onClose} />
      )}
    </section>
  );
}
