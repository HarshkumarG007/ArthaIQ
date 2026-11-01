import React, { useState, useRef } from "react";
import {
  Shield,
  Lock,
  Download,
  Upload,
  Key,
  AlertCircle,
  CheckCircle2,
  X,
  FileCheck,
  Eye,
  EyeOff,
} from "lucide-react";
import {
  exportEncryptedBackup,
  importAndMergeEncryptedBackup,
  type EncryptedSyncEnvelope,
} from "../../lib/cryptoSync";

interface EncryptedSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSyncSuccess?: () => void;
}

/**
 * Safe file reader supporting browser environments and jsdom test runtimes
 */
async function readFileContent(file: File): Promise<string> {
  if (typeof file.text === "function") {
    try {
      return await file.text();
    } catch {
      // Fallback to FileReader
    }
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error || new Error("Failed to read file"));
    reader.readAsText(file);
  });
}

export function EncryptedSyncModal({
  isOpen,
  onClose,
  onSyncSuccess,
}: EncryptedSyncModalProps): React.JSX.Element | null {
  const [mode, setMode] = useState<"export" | "import">("export");
  const [passphrase, setPassphrase] = useState("");
  const [confirmPassphrase, setConfirmPassphrase] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleExport = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (passphrase.length < 8) {
      setError("Passphrase must be at least 8 characters long.");
      return;
    }

    if (passphrase !== confirmPassphrase) {
      setError("Passphrases do not match.");
      return;
    }

    try {
      setIsProcessing(true);
      const envelope = await exportEncryptedBackup(passphrase);
      const jsonStr = JSON.stringify(envelope, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `arthaiq-career-encrypted-${new Date().toISOString().slice(0, 10)}.enc`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setSuccessMessage(
        "Encrypted backup file generated and downloaded successfully. Keep your passphrase secure!"
      );
      setPassphrase("");
      setConfirmPassphrase("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Encryption failed.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    setError(null);
    if (e.target.files && e.target.files.length > 0) {
      setImportFile(e.target.files[0]!);
    }
  };

  const handleImport = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (!importFile) {
      setError("Please select an encrypted backup file (.enc or .json).");
      return;
    }

    if (!passphrase) {
      setError("Please enter the decryption passphrase.");
      return;
    }

    try {
      setIsProcessing(true);
      const text = await readFileContent(importFile);
      let envelope: EncryptedSyncEnvelope;
      try {
        envelope = JSON.parse(text) as EncryptedSyncEnvelope;
      } catch {
        throw new Error("Invalid file format: file must contain valid JSON.");
      }

      const result = await importAndMergeEncryptedBackup(envelope, passphrase);

      setSuccessMessage(
        `Decryption successful! Merged ${result.mergedCompetenciesCount} competencies (${result.demonstratedCount} demonstrated) into your local browser ledger.`
      );
      setPassphrase("");
      setImportFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      if (onSyncSuccess) {
        onSyncSuccess();
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to decrypt backup. Verify your passphrase and file integrity."
      );
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sync-modal-title"
    >
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-6 bg-slate-900 text-white flex justify-between items-start">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-semibold uppercase tracking-wider border border-indigo-500/30">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>Zero-Knowledge WebCrypto (ADR-0014)</span>
            </div>
            <h3 id="sync-modal-title" className="text-xl font-bold tracking-tight">
              Encrypted Multi-Device Sync
            </h3>
            <p className="text-xs text-slate-300">
              Passphrase-protected client-side AES-GCM-256 backup and monotonic lattice merge.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label="Close sync modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Selector Tabs */}
        <div
          className="flex border-b border-slate-200 bg-slate-50"
          role="tablist"
          aria-label="Encrypted sync mode tabs"
        >
          <button
            type="button"
            role="tab"
            aria-selected={mode === "export"}
            onClick={() => {
              setMode("export");
              setError(null);
              setSuccessMessage(null);
            }}
            className={`flex-1 py-3 px-4 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 border-b-2 transition-colors ${
              mode === "export"
                ? "border-indigo-600 text-indigo-700 bg-white"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Download className="w-4 h-4" />
            <span>Export Encrypted Backup</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "import"}
            onClick={() => {
              setMode("import");
              setError(null);
              setSuccessMessage(null);
            }}
            className={`flex-1 py-3 px-4 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 border-b-2 transition-colors ${
              mode === "import"
                ? "border-indigo-600 text-indigo-700 bg-white"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Import & Merge Backup</span>
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          {/* Statutory Zero-Knowledge Notice */}
          <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Zero Server Retention:</strong> Cryptographic keys and plaintexts never touch
              the server. If you forget your passphrase, encrypted backups cannot be recovered by
              ArthaIQ.
            </p>
          </div>

          {error && (
            <div
              className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-start gap-2"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMessage && (
            <div
              className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-start gap-2"
              role="alert"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>{successMessage}</span>
            </div>
          )}

          {mode === "export" ? (
            <form onSubmit={handleExport} className="space-y-4">
              <div className="space-y-1">
                <label
                  htmlFor="export-passphrase"
                  className="block text-xs font-bold text-slate-800 uppercase tracking-wider"
                >
                  Encryption Passphrase
                </label>
                <div className="relative">
                  <input
                    id="export-passphrase"
                    type={showPassword ? "text" : "password"}
                    value={passphrase}
                    onChange={(e) => setPassphrase(e.target.value)}
                    placeholder="Enter passphrase (min 8 characters)"
                    required
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                    aria-label={showPassword ? "Hide passphrase" : "Show passphrase"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1">
                <label
                  htmlFor="confirm-passphrase"
                  className="block text-xs font-bold text-slate-800 uppercase tracking-wider"
                >
                  Confirm Passphrase
                </label>
                <input
                  id="confirm-passphrase"
                  type={showPassword ? "text" : "password"}
                  value={confirmPassphrase}
                  onChange={(e) => setConfirmPassphrase(e.target.value)}
                  placeholder="Re-enter passphrase"
                  required
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="text-xs text-slate-500 flex items-center gap-1.5 pt-1">
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                <span>Protected by PBKDF2-SHA256 (100k rounds) & AES-GCM-256</span>
              </div>

              <button
                type="submit"
                disabled={isProcessing}
                className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold text-sm flex items-center justify-center gap-2 transition-colors shadow-sm"
              >
                <Download className="w-4 h-4" />
                <span>{isProcessing ? "Encrypting..." : "Encrypt & Download Backup"}</span>
              </button>
            </form>
          ) : (
            <form onSubmit={handleImport} className="space-y-4">
              <div className="space-y-1">
                <label
                  htmlFor="import-file-input"
                  className="block text-xs font-bold text-slate-800 uppercase tracking-wider"
                >
                  Select Encrypted Backup File
                </label>
                <input
                  id="import-file-input"
                  ref={fileInputRef}
                  type="file"
                  accept=".enc,.json"
                  onChange={handleFileChange}
                  className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                />
                {importFile && (
                  <div className="text-xs text-slate-600 flex items-center gap-1.5 pt-1">
                    <FileCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Selected: {importFile.name}</span>
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <label
                  htmlFor="import-passphrase"
                  className="block text-xs font-bold text-slate-800 uppercase tracking-wider"
                >
                  Decryption Passphrase
                </label>
                <div className="relative">
                  <input
                    id="import-passphrase"
                    type={showPassword ? "text" : "password"}
                    value={passphrase}
                    onChange={(e) => setPassphrase(e.target.value)}
                    placeholder="Enter decryption passphrase"
                    required
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                    aria-label={showPassword ? "Hide passphrase" : "Show passphrase"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
                <div className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <Key className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Monotonic State Lattice Merge (Rule R-CR-03):</span>
                </div>
                <p>
                  Demonstrated competencies are strictly preserved. Incoming records will upgrade
                  unproven and self-reported skills without degrading proven achievements.
                </p>
              </div>

              <button
                type="submit"
                disabled={isProcessing}
                className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold text-sm flex items-center justify-center gap-2 transition-colors shadow-sm"
              >
                <Upload className="w-4 h-4" />
                <span>
                  {isProcessing ? "Decrypting & Merging..." : "Decrypt & Merge with Ledger"}
                </span>
              </button>
            </form>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
