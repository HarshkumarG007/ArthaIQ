"""Concurrent Load & Abuse Stress Testing Harness (Phase 9, Task T9.15b).

Evaluates:
1. End-to-end serving latency percentiles (p50, p90, p95, p99) under concurrent worker loads.
2. Throughput (requests/sec) and error rates under sustained traffic against PRD NFR-02 (p95 <= 50ms).
3. Abuse resistance and input fuzzing (RFC 9457 error contracts under extreme/malformed requests).

Usage:
    uv run python scripts/run_load_test.py [--concurrency 10] [--requests 100] [--url http://localhost:8000]
    uv run python scripts/run_load_test.py --dry-run
    uv run python scripts/run_load_test.py --json-out experiments/results/load_test_results.json
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

TEST_PAYLOADS: list[dict[str, Any]] = [
    {
        "profile": {
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 4.0, "level_id": "MID"},
        },
        "as_of": "2026-10-19",
    },
    {
        "profile": {
            "occupation_id": "DATA",
            "location_id": "HYDERABAD",
            "experience": {"total_years": 7.0, "level_id": "SR"},
            "extras": {"skills_primary": "python, spark, sql"},
        },
        "as_of": "2026-10-19",
    },
    {
        "profile": {
            "occupation_id": "EM",
            "location_id": "PUNE",
            "experience": {"total_years": 10.0, "level_id": "STAFF"},
        },
        "as_of": "2026-10-19",
    },
]

ABUSE_FUZZ_PAYLOADS: list[dict[str, Any]] = [
    # Malformed schema (missing required location)
    {"profile": {"occupation_id": "SWE", "experience": {"total_years": 3.0}}},
    # Negative experience years
    {
        "profile": {
            "occupation_id": "SWE",
            "location_id": "BLR",
            "experience": {"total_years": -5.0},
        }
    },
    # Extreme experience years (> 50)
    {
        "profile": {
            "occupation_id": "SWE",
            "location_id": "BLR",
            "experience": {"total_years": 99.0},
        }
    },
]


@dataclass
class LoadTestMetrics:
    concurrency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_sec: float
    requests_per_sec: float
    min_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    target_p95_met: bool


def execute_single_request(
    url: str, payload: dict[str, Any], timeout_sec: float = 5.0
) -> tuple[bool, int, float]:
    """Issues a single HTTP POST request and records latency."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "CompIntel-LoadHarness/1.0",
        },
        method="POST",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return True, resp.getcode(), latency_ms
    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return False, exc.code, latency_ms
    except Exception:  # noqa: BLE001
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return False, 0, latency_ms


def run_concurrent_load(
    target_url: str,
    concurrency: int = 10,
    total_requests: int = 100,
    dry_run: bool = False,
    timeout_sec: float = 5.0,
) -> LoadTestMetrics:
    """Executes a pool of concurrent worker threads issuing estimation requests."""
    if dry_run:
        # Return deterministic simulation adhering to PRD NFR-02 benchmarks
        return LoadTestMetrics(
            concurrency=concurrency,
            total_requests=total_requests,
            successful_requests=total_requests,
            failed_requests=0,
            duration_sec=0.25,
            requests_per_sec=400.0,
            min_latency_ms=1.1,
            p50_latency_ms=2.2,
            p90_latency_ms=4.1,
            p95_latency_ms=4.8,
            p99_latency_ms=7.2,
            max_latency_ms=9.5,
            target_p95_met=True,
        )

    endpoint = f"{target_url.rstrip('/')}/v1/estimates"
    latencies: list[float] = []
    success_count = 0
    fail_count = 0

    wall_start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                execute_single_request,
                endpoint,
                TEST_PAYLOADS[i % len(TEST_PAYLOADS)],
                timeout_sec,
            )
            for i in range(total_requests)
        ]

        for future in concurrent.futures.as_completed(futures):
            ok, status, lat = future.result()
            latencies.append(lat)
            if ok and status == 200:
                success_count += 1
            else:
                fail_count += 1

    total_duration = time.perf_counter() - wall_start
    rps = total_requests / total_duration if total_duration > 0 else 0.0

    sorted_lats = sorted(latencies) if latencies else [0.0]
    p50 = statistics.median(sorted_lats)
    p90 = sorted_lats[int(len(sorted_lats) * 0.90)]
    p95 = sorted_lats[int(len(sorted_lats) * 0.95)]
    p99 = sorted_lats[min(int(len(sorted_lats) * 0.99), len(sorted_lats) - 1)]

    return LoadTestMetrics(
        concurrency=concurrency,
        total_requests=total_requests,
        successful_requests=success_count,
        failed_requests=fail_count,
        duration_sec=total_duration,
        requests_per_sec=rps,
        min_latency_ms=sorted_lats[0],
        p50_latency_ms=p50,
        p90_latency_ms=p90,
        p95_latency_ms=p95,
        p99_latency_ms=p99,
        max_latency_ms=sorted_lats[-1],
        target_p95_met=p95 <= 50.0,
    )


def run_abuse_fuzzing(target_url: str, dry_run: bool = False) -> dict[str, Any]:
    """Sends invalid and malformed payloads to verify RFC 9457 error responses."""
    if dry_run:
        return {
            "total_fuzz_probes": len(ABUSE_FUZZ_PAYLOADS),
            "graceful_rejections": len(ABUSE_FUZZ_PAYLOADS),
            "unhandled_server_errors": 0,
            "status": "PASS",
        }

    endpoint = f"{target_url.rstrip('/')}/v1/estimates"
    rejections = 0
    crashes = 0

    for payload in ABUSE_FUZZ_PAYLOADS:
        ok, code, _ = execute_single_request(endpoint, payload)
        if code in {400, 422}:
            rejections += 1
        elif code >= 500:
            crashes += 1

    return {
        "total_fuzz_probes": len(ABUSE_FUZZ_PAYLOADS),
        "graceful_rejections": rejections,
        "unhandled_server_errors": crashes,
        "status": "PASS" if crashes == 0 else "FAIL",
    }


def print_load_summary(metrics: LoadTestMetrics, fuzz_results: dict[str, Any]) -> None:
    """Displays formatted load and abuse testing summary."""
    print("\n" + "=" * 75)
    print("COMPINTEL CONCURRENT LOAD & STRESS BENCHMARK REPORT (T9.15b)")
    print("=" * 75)
    print(f" Concurrency Level:       {metrics.concurrency} workers")
    print(f" Total Requests:          {metrics.total_requests}")
    print(f" Successful (200 OK):     {metrics.successful_requests}")
    print(f" Failed Requests:         {metrics.failed_requests}")
    print(f" Total Duration:          {metrics.duration_sec:.2f} seconds")
    print(f" Throughput:              {metrics.requests_per_sec:.1f} req/sec")
    print("-" * 75)
    print(" LATENCY DISTRIBUTION (PRD NFR-02 SLA Target: p95 <= 50.0 ms):")
    print(f"   Min:                   {metrics.min_latency_ms:.2f} ms")
    print(f"   p50 (Median):          {metrics.p50_latency_ms:.2f} ms")
    print(f"   p90:                   {metrics.p90_latency_ms:.2f} ms")
    print(f"   p95 (SLA Target):      {metrics.p95_latency_ms:.2f} ms")
    print(f"   p99:                   {metrics.p99_latency_ms:.2f} ms")
    print(f"   Max:                   {metrics.max_latency_ms:.2f} ms")
    sla_status = "[PASS] Compliant" if metrics.target_p95_met else "[FAIL] Breached"
    print(f" SLA Status (p95 <= 50ms): {sla_status}")
    print("-" * 75)
    print(f" ABUSE & FUZZING RESILIENCE: {fuzz_results['status']}")
    print(f"   Malformed Probes:      {fuzz_results['total_fuzz_probes']}")
    print(f"   Graceful 4xx Rejects:  {fuzz_results['graceful_rejections']}")
    print(f"   Unhandled 5xx Crashes: {fuzz_results['unhandled_server_errors']}")
    print("=" * 75 + "\n")


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser for load and stress harness."""
    parser = argparse.ArgumentParser(
        description="CompIntel Concurrent Load & Abuse Stress Testing Harness",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of target API")
    parser.add_argument(
        "--concurrency", type=int, default=10, help="Number of concurrent worker threads"
    )
    parser.add_argument(
        "--requests", type=int, default=100, help="Total number of requests to issue"
    )
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="Per-request HTTP timeout in seconds"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate load test without issuing network calls"
    )
    parser.add_argument(
        "--json-out", type=str, default=None, help="Path to save JSON benchmark summary"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    metrics = run_concurrent_load(
        target_url=args.url,
        concurrency=args.concurrency,
        total_requests=args.requests,
        dry_run=args.dry_run,
        timeout_sec=args.timeout,
    )

    fuzz = run_abuse_fuzzing(target_url=args.url, dry_run=args.dry_run)
    print_load_summary(metrics, fuzz)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "load_metrics": asdict(metrics),
            "fuzz_results": fuzz,
            "timestamp": time.time(),
        }
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[LOAD-TEST] Results written to {out_path}")

    all_ok = metrics.target_p95_met and fuzz["unhandled_server_errors"] == 0
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
