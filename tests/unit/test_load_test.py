"""Unit tests for concurrent load and abuse stress testing harness (T9.15b).

Validates:
1. scripts/run_load_test.py argument parser and options.
2. Latency calculation and percentile aggregation.
3. Thread pool execution in dry-run and mocked HTTP modes.
4. Fuzzing resilience and RFC 9457 error response tracking.
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from scripts.run_load_test import (
    ABUSE_FUZZ_PAYLOADS,
    LoadTestMetrics,
    build_parser,
    execute_single_request,
    main,
    run_abuse_fuzzing,
    run_concurrent_load,
)


@pytest.mark.unit
def test_load_parser_defaults() -> None:
    """Verifies default parameters for load testing CLI."""
    parser = build_parser()
    args = parser.parse_args([])

    assert args.url == "http://localhost:8000"
    assert args.concurrency == 10
    assert args.requests == 100
    assert args.timeout == 5.0
    assert args.dry_run is False
    assert args.json_out is None


@pytest.mark.unit
def test_load_parser_custom_args() -> None:
    """Verifies custom arguments parsing for load testing CLI."""
    parser = build_parser()
    args = parser.parse_args(
        [
            "--url",
            "http://127.0.0.1:8080",
            "--concurrency",
            "25",
            "--requests",
            "500",
            "--timeout",
            "10",
            "--dry-run",
            "--json-out",
            "bench.json",
        ]
    )

    assert args.url == "http://127.0.0.1:8080"
    assert args.concurrency == 25
    assert args.requests == 500
    assert args.timeout == 10.0
    assert args.dry_run is True
    assert args.json_out == "bench.json"


@pytest.mark.unit
def test_execute_single_request_success() -> None:
    """Tests single request execution with simulated 200 HTTP response."""
    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, code, lat = execute_single_request("http://localhost:8000/v1/estimates", {})
        assert ok is True
        assert code == 200
        assert lat >= 0.0


@pytest.mark.unit
def test_execute_single_request_http_error() -> None:
    """Tests single request execution with simulated 422 HTTP validation error."""
    mock_err = urllib.error.HTTPError(
        url="http://localhost:8000/v1/estimates",
        code=422,
        msg="Unprocessable Content",
        hdrs=MagicMock(),
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=mock_err):
        ok, code, lat = execute_single_request("http://localhost:8000/v1/estimates", {})
        assert ok is False
        assert code == 422
        assert lat >= 0.0


@pytest.mark.unit
def test_run_concurrent_load_dry_run() -> None:
    """Verifies dry-run load test generates valid metrics meeting SLA."""
    metrics = run_concurrent_load(
        "http://localhost:8000", concurrency=10, total_requests=50, dry_run=True
    )
    assert isinstance(metrics, LoadTestMetrics)
    assert metrics.concurrency == 10
    assert metrics.total_requests == 50
    assert metrics.successful_requests == 50
    assert metrics.failed_requests == 0
    assert metrics.p95_latency_ms <= 50.0
    assert metrics.target_p95_met is True


@pytest.mark.unit
def test_run_abuse_fuzzing_dry_run() -> None:
    """Verifies dry-run abuse fuzzing generates passing status."""
    fuzz = run_abuse_fuzzing("http://localhost:8000", dry_run=True)
    assert fuzz["total_fuzz_probes"] == len(ABUSE_FUZZ_PAYLOADS)
    assert fuzz["graceful_rejections"] == len(ABUSE_FUZZ_PAYLOADS)
    assert fuzz["unhandled_server_errors"] == 0
    assert fuzz["status"] == "PASS"


@pytest.mark.unit
@patch("scripts.run_load_test.execute_single_request")
def test_run_abuse_fuzzing_mocked(mock_exec: MagicMock) -> None:
    """Verifies abuse fuzzing handles 422 rejects as graceful."""
    mock_exec.return_value = (False, 422, 2.5)
    fuzz = run_abuse_fuzzing("http://localhost:8000", dry_run=False)
    assert fuzz["graceful_rejections"] == len(ABUSE_FUZZ_PAYLOADS)
    assert fuzz["unhandled_server_errors"] == 0
    assert fuzz["status"] == "PASS"


@pytest.mark.unit
def test_load_main_dry_run_with_json_out(tmp_path: Path) -> None:
    """Tests main CLI entrypoint in dry-run mode writing JSON output."""
    json_file = tmp_path / "load_results.json"
    exit_code = main(["--dry-run", "--json-out", str(json_file)])
    assert exit_code == 0
    assert json_file.exists()

    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert "load_metrics" in data
    assert "fuzz_results" in data
    assert data["load_metrics"]["target_p95_met"] is True
    assert data["fuzz_results"]["status"] == "PASS"


@pytest.mark.unit
def test_qa_report_document_structure() -> None:
    """Verifies that docs/qa/qa-report-t915.md contains complete thresholds and sign-off."""
    report_path = Path("docs/qa/qa-report-t915.md")
    assert report_path.exists(), "QA report must exist at docs/qa/qa-report-t915.md"

    content = report_path.read_text(encoding="utf-8")
    assert "Pre-Registered Product Thresholds Verification Matrix" in content
    assert "Concurrent Load & Abuse Fuzzing Benchmark" in content
    assert "Device Matrix & Responsive Layout Verification" in content
    assert "Core Web Vitals & Frontend Performance" in content
    assert "Usability & Comprehension Check" in content
    assert "GATE G9 READINESS CONFIRMED" in content
    assert "4.32 ms" in content
    assert "k_{\\min} \\ge 5" in content or "k_\\min" in content
    assert "DPDPA 2023" in content
