"""Benchmark for Enterprise Batch REST Endpoints (Phase 23, Task T23.05).

Evaluates:
- Synchronous batch endpoint (POST /v1/estimates/batch) throughput and latency distribution
  across different batch sizes (N=10, N=50, N=100, N=500).
- Memory-bounded streaming NDJSON endpoint (POST /v1/estimates/batch/stream) throughput.
- Verifies SLA targets:
  * Throughput >= 1,000 predictions/sec
  * 50-item batch p95 latency <= 100 ms
- Rule R-UQ-01: Full percentile distributions (p50, p90, p95, p99), zero lone numbers.
- Serializes results to experiments/results/batch_api_benchmark_v1.json.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from compintel.logging import get_logger
from compintel.serving.app import create_app

logger = get_logger(__name__)

SAMPLE_PROFILES: list[dict[str, Any]] = [
    {
        "id": "prof_swe_01",
        "occupation_id": "SWE",
        "location_id": "BENGALURU",
        "experience": {"total_years": 4.5, "level_id": "MID"},
        "education": {"tier_id": "TIER_1"},
    },
    {
        "id": "prof_data_01",
        "occupation_id": "DATA",
        "location_id": "HYDERABAD",
        "experience": {"total_years": 7.0, "level_id": "SR"},
        "education": {"tier_id": "TIER_2"},
    },
    {
        "id": "prof_mlai_01",
        "occupation_id": "MLAI",
        "location_id": "DELHI_NCR",
        "experience": {"total_years": 3.0, "level_id": "JR"},
        "education": {"tier_id": "TIER_1"},
    },
    {
        "id": "prof_swe_02",
        "occupation_id": "SWE",
        "location_id": "PUNE",
        "experience": {"total_years": 10.0, "level_id": "LEAD"},
        "education": {"tier_id": "TIER_2"},
    },
    {
        "id": "prof_data_02",
        "occupation_id": "DATA",
        "location_id": "MUMBAI",
        "experience": {"total_years": 2.0, "level_id": "ENTRY"},
        "education": {"tier_id": "TIER_3"},
    },
]


def generate_batch_payload(size: int) -> dict[str, Any]:
    """Generate a batch request payload of specified size by cycling sample profiles."""
    items = []
    for i in range(size):
        base = SAMPLE_PROFILES[i % len(SAMPLE_PROFILES)]
        item = {
            "id": f"rec_{i:04d}_{base['id']}",
            "occupation_id": base["occupation_id"],
            "location_id": base["location_id"],
            "experience": dict(base["experience"]),
            "education": dict(base["education"]),
        }
        items.append(item)
    return {"items": items, "as_of": "2026-10-31"}


def compute_distribution_stats(latencies_ms: list[float]) -> dict[str, float]:
    """Compute comprehensive percentile and moment statistics for latencies."""
    if not latencies_ms:
        return {}
    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)

    def pct(p: float) -> float:
        k = (n - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, n - 1)
        d0 = sorted_lats[f] * (c - k)
        d1 = sorted_lats[c] * (k - f)
        return float(round(d0 + d1, 3))

    return {
        "count": float(n),
        "mean_ms": float(round(statistics.mean(latencies_ms), 3)),
        "std_dev_ms": float(round(statistics.stdev(latencies_ms), 3)) if n > 1 else 0.0,
        "min_ms": float(round(min(latencies_ms), 3)),
        "p50_ms": pct(50.0),
        "p90_ms": pct(90.0),
        "p95_ms": pct(95.0),
        "p99_ms": pct(99.0),
        "max_ms": float(round(max(latencies_ms), 3)),
    }


def run_batch_api_benchmark(
    iterations: int = 50,
    warmup: int = 5,
) -> dict[str, Any]:
    """Execute end-to-end HTTP batch API benchmark suite."""
    print("Initializing application and loading champion model bundle...")
    app = create_app()
    client = TestClient(app)

    # Warmup
    print(f"Executing {warmup} warm-up iterations...")
    warmup_payload = generate_batch_payload(10)
    for _ in range(warmup):
        resp = client.post("/v1/estimates/batch", json=warmup_payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Warm-up failed with status {resp.status_code}: {resp.text}")

    benchmarks: dict[str, Any] = {}
    batch_sizes = [10, 50, 100, 500]

    for size in batch_sizes:
        print(
            f"\nBenchmarking POST /v1/estimates/batch with batch size N={size} ({iterations} runs)..."
        )
        payload = generate_batch_payload(size)
        latencies_ms: list[float] = []
        total_items_processed = 0

        start_all = time.perf_counter()
        for _ in range(iterations):
            t0 = time.perf_counter()
            resp = client.post("/v1/estimates/batch", json=payload)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            if resp.status_code != 200:
                raise RuntimeError(f"Batch N={size} failed: {resp.status_code} - {resp.text}")
            latencies_ms.append(elapsed_ms)
            total_items_processed += size
        total_time_sec = time.perf_counter() - start_all

        stats = compute_distribution_stats(latencies_ms)
        throughput_pps = round(total_items_processed / total_time_sec, 1)

        benchmarks[f"batch_{size}"] = {
            "batch_size": size,
            "iterations": iterations,
            "total_items": total_items_processed,
            "total_time_sec": round(total_time_sec, 3),
            "throughput_predictions_per_sec": throughput_pps,
            "latency": stats,
        }
        print(
            f"  -> N={size}: Throughput = {throughput_pps:,.1f} pred/sec | "
            f"p50 = {stats['p50_ms']:.2f} ms | p95 = {stats['p95_ms']:.2f} ms"
        )

    # Streaming NDJSON Benchmark
    print(f"\nBenchmarking POST /v1/estimates/batch/stream with N=500 ({iterations} runs)...")
    stream_payload = generate_batch_payload(500)
    stream_latencies: list[float] = []
    total_stream_items = 0

    t_start_stream = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        resp = client.post("/v1/estimates/batch/stream", json=stream_payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code != 200:
            raise RuntimeError(f"Streaming failed: {resp.status_code}")
        # Parse lines
        lines = [line for line in resp.text.split("\n") if line.strip()]
        total_stream_items += len(lines)
        stream_latencies.append(elapsed_ms)
    t_end_stream = time.perf_counter() - t_start_stream
    stream_throughput = round(total_stream_items / t_end_stream, 1)
    stream_stats = compute_distribution_stats(stream_latencies)

    benchmarks["streaming_500"] = {
        "batch_size": 500,
        "iterations": iterations,
        "total_items": total_stream_items,
        "total_time_sec": round(t_end_stream, 3),
        "throughput_predictions_per_sec": stream_throughput,
        "latency": stream_stats,
    }
    print(
        f"  -> Stream N=500: Throughput = {stream_throughput:,.1f} pred/sec | "
        f"p50 = {stream_stats['p50_ms']:.2f} ms | p95 = {stream_stats['p95_ms']:.2f} ms"
    )

    # SLA Evaluation
    b50_p95 = benchmarks["batch_50"]["latency"]["p95_ms"]
    b500_tp = benchmarks["batch_500"]["throughput_predictions_per_sec"]
    meets_throughput_sla = b500_tp >= 1000.0
    meets_p95_latency_sla = b50_p95 <= 100.0
    all_sla_pass = meets_throughput_sla and meets_p95_latency_sla

    verdict = {
        "benchmark_id": "BENCH-BATCH-REST-01",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "sla_criteria": {
            "min_throughput_predictions_per_sec": 1000.0,
            "max_batch_50_p95_latency_ms": 100.0,
        },
        "observed_metrics": {
            "batch_50_p95_latency_ms": b50_p95,
            "batch_500_throughput_pps": b500_tp,
            "streaming_500_throughput_pps": stream_throughput,
        },
        "verdict": {
            "meets_throughput_sla": meets_throughput_sla,
            "meets_latency_sla": meets_p95_latency_sla,
            "overall_sla_pass": all_sla_pass,
            "status": "PASS" if all_sla_pass else "FAIL",
        },
        "hardware_metadata": {
            "platform": platform.platform(),
            "python_version": sys.version,
            "processor": platform.processor(),
            "machine": platform.machine(),
        },
        "benchmarks": benchmarks,
    }

    return verdict


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Batch REST Endpoint Throughput & Latency Benchmark"
    )
    parser.add_argument("--iterations", type=int, default=30, help="Benchmark iterations per size")
    parser.add_argument("--warmup", type=int, default=5, help="Warmup iterations")
    parser.add_argument(
        "--output",
        type=str,
        default="experiments/results/batch_api_benchmark_v1.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    results = run_batch_api_benchmark(iterations=args.iterations, warmup=args.warmup)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSerialized results to {out_path}")

    v = results["verdict"]
    print("==========================================")
    print(f"VERDICT: {v['status']}")
    print(
        f"Batch 500 Throughput: {results['observed_metrics']['batch_500_throughput_pps']:,.1f} pred/sec (SLA >= 1,000)"
    )
    print(
        f"Batch 50 p95 Latency: {results['observed_metrics']['batch_50_p95_latency_ms']:.2f} ms (SLA <= 100 ms)"
    )
    print("==========================================")

    if not v["overall_sla_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
