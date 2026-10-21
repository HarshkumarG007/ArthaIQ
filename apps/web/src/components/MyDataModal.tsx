/**
 * MyDataModal — Allows contributor to enter their deletion token and trigger
 * statutory operational erasure (PRD US-07, ADR-0008, DPDPA 2023 Right to Erasure).
 *
 * Invariants:
 * - No identity information collected during erasure flow.
 * - Deletion token is the sole credential for erasure.
 * - Confirmation receipt is shown after successful erasure.
 */
import { useId, useRef, useState } from "react";

export interface MyDataModalProps {
  /** Called to close the modal. */
  onClose: () => void;
  /** Override API endpoint for testing. Defaults to /v1/contributions/delete */
  apiEndpoint?: string;
}

interface ErasureReceipt {
  contributor_key: string;
  status: string;
  records_purged_count: number;
  message: string;
  timestamp: string;
}

export function MyDataModal({
  onClose,
  apiEndpoint = "/v1/contributions/delete",
}: MyDataModalProps) {
  const tokenFieldId = useId();
  const [token, setToken] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<ErasureReceipt | null>(null);
  const tokenInputRef = useRef<HTMLInputElement>(null);

  const handleErase = async () => {
    if (!token.trim()) {
      setError("Please enter your deletion token.");
      tokenInputRef.current?.focus();
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await fetch(apiEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deletion_token: token.trim() }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(
          data.detail ??
            `Erasure request failed (HTTP ${res.status}). Check your token and try again.`
        );
      }
      const data = (await res.json()) as ErasureReceipt;
      setReceipt(data);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="my-data-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="my-data-heading"
    >
      <div className="my-data-modal-backdrop" onClick={onClose} aria-hidden="true" />
      <div className="my-data-modal-panel">
        <button
          type="button"
          className="my-data-close-btn"
          onClick={onClose}
          aria-label="Close My Data modal"
        >
          X
        </button>

        {receipt ? (
          // --- Confirmation screen ---
          <div className="my-data-confirm" aria-live="assertive">
            <div className="my-data-confirm-icon" aria-hidden="true">Deleted</div>
            <h2 id="my-data-heading" className="my-data-heading">
              Your data has been permanently deleted
            </h2>
            <p className="my-data-description">
              {receipt.records_purged_count} contribution record
              {receipt.records_purged_count !== 1 ? "s" : ""} have been
              permanently removed from our operational stores.
            </p>
            <p className="my-data-description">
              {receipt.message}
            </p>
            <dl className="my-data-receipt-dl">
              <dt>Reference</dt>
              <dd>
                <code>{receipt.contributor_key.slice(0, 8)}…</code>
              </dd>
              <dt>Completed at</dt>
              <dd>
                {new Date(receipt.timestamp).toLocaleString("en-IN", {
                  timeZone: "Asia/Kolkata",
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </dd>
            </dl>
            <div className="my-data-actions">
              <button
                type="button"
                className="cf-btn cf-btn-primary"
                onClick={onClose}
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          // --- Erasure request form ---
          <div>
            <h2 id="my-data-heading" className="my-data-heading">
              Delete my data
            </h2>
            <p className="my-data-description">
              Enter the deletion token you received when you submitted your
              contribution. This action permanently removes your record from our
              operational stores and cannot be undone.
            </p>

            {error && (
              <div
                className="cf-error-banner"
                role="alert"
                aria-live="assertive"
              >
                {error}
              </div>
            )}

            <div className="cf-field">
              <label htmlFor={tokenFieldId} className="cf-label">
                Deletion token <span aria-hidden="true">*</span>
              </label>
              <input
                id={tokenFieldId}
                ref={tokenInputRef}
                type="text"
                className="cf-input my-data-token-input"
                placeholder="del_..."
                value={token}
                onChange={(e) => setToken(e.target.value)}
                aria-required="true"
                autoComplete="off"
                spellCheck="false"
              />
              <p className="cf-hint">
                Your token begins with <code>del_</code> and was shown after
                you submitted your contribution.
              </p>
            </div>

            <div className="cf-warning-box" role="note">
              <strong>This action is permanent.</strong> Once deleted, your
              contribution cannot be recovered. Statistics that included your
              data will be updated at the next scheduled data refresh.
            </div>

            <div className="my-data-actions">
              <button
                type="button"
                className="cf-btn cf-btn-ghost"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="cf-btn cf-btn-danger"
                onClick={handleErase}
                disabled={isSubmitting || !token.trim()}
                aria-disabled={isSubmitting || !token.trim()}
                aria-busy={isSubmitting}
              >
                {isSubmitting ? "Deleting..." : "Permanently delete my data"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
