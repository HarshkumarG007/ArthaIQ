import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { EncryptedSyncModal } from "./EncryptedSyncModal";
import * as cryptoSync from "../../lib/cryptoSync";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false },
  },
};

describe("EncryptedSyncModal (Phase 31, ADR-0014 Zero-Knowledge Sync UI)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders modal when open with zero-knowledge notice and export tab by default", () => {
    render(<EncryptedSyncModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: /encrypted multi-device sync/i })).toBeInTheDocument();
    expect(screen.getByText(/Zero-Knowledge WebCrypto \(ADR-0014\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Zero Server Retention:/i)).toBeInTheDocument();

    expect(screen.getByRole("tab", { name: /export encrypted backup/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByLabelText(/encryption passphrase/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm passphrase/i)).toBeInTheDocument();
  });

  it("returns null when isOpen is false", () => {
    const { container } = render(<EncryptedSyncModal isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("switches to import mode and displays file selector", () => {
    render(<EncryptedSyncModal isOpen={true} onClose={vi.fn()} />);

    const importTab = screen.getByRole("tab", { name: /import & merge backup/i });
    fireEvent.click(importTab);

    expect(importTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText(/select encrypted backup file/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/decryption passphrase/i)).toBeInTheDocument();
    expect(screen.getByText(/Monotonic State Lattice Merge/i)).toBeInTheDocument();
  });

  it("validates passphrase match and length in export mode", async () => {
    render(<EncryptedSyncModal isOpen={true} onClose={vi.fn()} />);

    const passInput = screen.getByLabelText(/^encryption passphrase$/i);
    const confirmInput = screen.getByLabelText(/^confirm passphrase$/i);
    const exportBtn = screen.getByRole("button", { name: /encrypt & download backup/i });

    // Short passphrase
    fireEvent.change(passInput, { target: { value: "short" } });
    fireEvent.change(confirmInput, { target: { value: "short" } });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /passphrase must be at least 8 characters long/i
      );
    });

    // Mismatched passphrase
    fireEvent.change(passInput, { target: { value: "password123" } });
    fireEvent.change(confirmInput, { target: { value: "mismatch456" } });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/passphrases do not match/i);
    });
  });

  it("triggers exportEncryptedBackup and download on valid passphrases", async () => {
    const mockEnvelope: cryptoSync.EncryptedSyncEnvelope = {
      sync_version: "1.0",
      sync_id: "usr_sync_test_123",
      algorithm: "AES-256-GCM",
      kdf: "PBKDF2-SHA256",
      iterations: 100000,
      salt_b64: "c2FsdA==",
      iv_b64: "aXY=",
      ciphertext_b64: "Y2lwaGVydGV4dA==",
      updated_at_utc: "2026-11-01T08:00:00Z",
      schema_version: 2,
    };

    const spyExport = vi
      .spyOn(cryptoSync, "exportEncryptedBackup")
      .mockResolvedValue(mockEnvelope);

    const originalCreate = URL.createObjectURL;
    const originalRevoke = URL.revokeObjectURL;
    const originalClick = HTMLAnchorElement.prototype.click;
    URL.createObjectURL = vi.fn().mockReturnValue("blob:mock-enc");
    URL.revokeObjectURL = vi.fn();
    HTMLAnchorElement.prototype.click = vi.fn();

    render(<EncryptedSyncModal isOpen={true} onClose={vi.fn()} />);

    const passInput = screen.getByLabelText(/^encryption passphrase$/i);
    const confirmInput = screen.getByLabelText(/^confirm passphrase$/i);
    const exportBtn = screen.getByRole("button", { name: /encrypt & download backup/i });

    fireEvent.change(passInput, { target: { value: "ValidPassword123!" } });
    fireEvent.change(confirmInput, { target: { value: "ValidPassword123!" } });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(spyExport).toHaveBeenCalledWith("ValidPassword123!");
      expect(
        screen.getByText(/encrypted backup file generated and downloaded successfully/i)
      ).toBeInTheDocument();
    });

    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
    HTMLAnchorElement.prototype.click = originalClick;
  });

  it("handles import flow and calls importAndMergeEncryptedBackup", async () => {
    const onSyncSuccess = vi.fn();
    const spyImport = vi
      .spyOn(cryptoSync, "importAndMergeEncryptedBackup")
      .mockResolvedValue({
        mergedCompetenciesCount: 15,
        demonstratedCount: 4,
      });

    render(
      <EncryptedSyncModal isOpen={true} onClose={vi.fn()} onSyncSuccess={onSyncSuccess} />
    );

    // Switch to import tab
    const importTab = screen.getByRole("tab", { name: /import & merge backup/i });
    fireEvent.click(importTab);

    const mockFileContent = JSON.stringify({
      sync_version: "1.0",
      algorithm: "AES-256-GCM",
      kdf: "PBKDF2-SHA256",
      iterations: 100000,
      salt_b64: "test",
      iv_b64: "test",
      ciphertext_b64: "test",
    });

    const file = new File([mockFileContent], "backup.enc", { type: "application/json" });
    file.text = vi.fn().mockResolvedValue(mockFileContent);

    const fileInput = screen.getByLabelText(/select encrypted backup file/i);
    fireEvent.change(fileInput, { target: { files: [file] } });

    const passInput = screen.getByLabelText(/decryption passphrase/i);
    fireEvent.change(passInput, { target: { value: "SecretKey123!" } });

    const submitBtn = screen.getByRole("button", { name: /decrypt & merge with ledger/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(spyImport).toHaveBeenCalled();
      expect(onSyncSuccess).toHaveBeenCalled();
      expect(screen.getByText(/merged 15 competencies \(4 demonstrated\)/i)).toBeInTheDocument();
    });
  });

  it("passes axe-core accessibility audit with 0 violations", async () => {
    const { container } = render(<EncryptedSyncModal isOpen={true} onClose={vi.fn()} />);
    const results = await axe.run(container, AXE_OPTIONS);
    expect(results.violations).toEqual([]);
  });
});
