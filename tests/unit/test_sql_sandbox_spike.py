"""Unit tests for SQL sandbox evaluation spike report (Task T15.26).

Verifies:
- ADR-0012 & Rule R-CR-12: Local-first privacy and client-side execution.
- Rule R-CR-14: Independent offline utility without server roundtrips.
- Comparative benchmark between sql.js and DuckDB-WASM.
- Clear architectural GO / NO-GO recommendations for Phase 15/16.
"""

from __future__ import annotations

from pathlib import Path

SPIKE_REPORT_PATH = Path("docs/research/sql-sandbox-spike.md")


class TestSqlSandboxSpikeReport:
    """Verify presence, structural integrity, and architectural decisions of spike report."""

    def test_report_exists_on_disk(self) -> None:
        """The spike report file exists in docs/research/."""
        assert SPIKE_REPORT_PATH.exists(), f"Spike report {SPIKE_REPORT_PATH} not found"

    def test_metadata_and_document_id(self) -> None:
        """Report contains required document ID and metadata."""
        content = SPIKE_REPORT_PATH.read_text(encoding="utf-8")
        assert "SPIKE-SQL-SANDBOX-01" in content
        assert "2026-10-29" in content
        assert "sql.js" in content
        assert "DuckDB-WASM" in content

    def test_comparative_benchmark_criteria(self) -> None:
        """Report evaluates payload size, RAM consumption, cold boot, and window functions."""
        content = SPIKE_REPORT_PATH.read_text(encoding="utf-8")
        # Check payload size comparison
        assert "350" in content or "KB" in content
        assert "7.5" in content or "MB" in content

        # Check memory footprint comparison
        assert "RAM" in content or "Memory" in content
        assert "Web Worker" in content

        # Check analytical window function fidelity for SCEN-DATA-01-SQL
        assert "OVER" in content
        assert "PARTITION" in content
        assert "3.25" in content or "SQLite" in content

    def test_architectural_recommendations(self) -> None:
        """Report provides clear GO for sql.js and DEFER for DuckDB-WASM."""
        content = SPIKE_REPORT_PATH.read_text(encoding="utf-8")
        assert "GO FOR `sql.js`" in content or "GO for `sql.js`" in content
        assert "DuckDB-WASM" in content
        assert "DEFER" in content or "Defer" in content

    def test_privacy_and_offline_invariants(self) -> None:
        """Report enforces ADR-0012, Rule R-CR-12, and Rule R-CR-14."""
        content = SPIKE_REPORT_PATH.read_text(encoding="utf-8")
        assert "ADR-0012" in content
        assert "R-CR-12" in content
        assert "R-CR-14" in content
        assert "sandbox" in content.lower()

