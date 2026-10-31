"""Unit test suite for Distributed Batch Inference Pipeline (ENG-17, Phase 21, Task T21.01).

Adheres strictly to:
- Rule R-UQ-01: Zero lone numbers; always full calibrated intervals [P10, P50, P90].
- Rule R-CR-01: Zero causal pay claims in metadata or outputs.
- Rule R-CR-02: Two Streams Two Places decoupled compensation architecture.
- Performance SLA: >= 1,000 predictions/second batch throughput.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from compintel.schema.enums import (
    CompensationMeasure,
    Currency,
)
from compintel.serving.batch_pipeline import (
    STATUTORY_DISCLAIMER,
    BatchInferencePipeline,
    BatchInferenceResponse,
    BatchInferenceResultItem,
)


@pytest.fixture(scope="module")
def pipeline() -> BatchInferencePipeline:
    """Fixture providing ready BatchInferencePipeline."""
    pipe = BatchInferencePipeline()
    assert pipe.is_ready, "BatchInferencePipeline must be ready with active bundle."
    return pipe


def test_batch_pipeline_initialization(pipeline: BatchInferencePipeline) -> None:
    """Verify pipeline initializes with champion model and valid metadata."""
    assert pipeline.is_ready is True
    assert pipeline.model_version == "0.1.0"


def test_batch_pipeline_predict_batch_supported(pipeline: BatchInferencePipeline) -> None:
    """Verify batch prediction on supported profiles produces calibrated intervals."""
    profiles: list[dict[str, Any]] = [
        {
            "profile_id": "swe-sr-blr",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 6.0, "level_id": "SR"},
        },
        {
            "profile_id": "data-mid-hyd",
            "occupation_id": "DATA",
            "location_id": "HYDERABAD",
            "experience": {"total_years": 3.5, "level_id": "MID"},
        },
        {
            "profile_id": "mlai-jr-pun",
            "occupation_id": "MLAI",
            "location_id": "PUNE",
            "experience": {"total_years": 1.5, "level_id": "JR"},
        },
        {
            "profile_id": "swe-mid-del",
            "occupation_id": "SWE",
            "location_id": "NCR",
            "experience": {"total_years": 4.0, "level_id": "MID"},
        },
    ]

    results = pipeline.predict_batch(profiles)
    assert len(results) == len(profiles)

    for item in results:
        assert isinstance(item, BatchInferenceResultItem)
        assert item.status == "ok"
        assert item.is_abstained is False
        assert item.p10 is not None
        assert item.p50 is not None
        assert item.p90 is not None
        assert item.interval_width is not None

        # Monotonicity invariant: P10 <= P50 <= P90
        assert item.p10 <= item.p50 <= item.p90
        # Non-negativity statutory floor
        assert item.p10 >= 0.5
        # Interval width consistency
        assert item.interval_width == round(item.p90 - item.p10, 2)
        # 80% nominal coverage
        assert item.nominal_coverage == 0.80
        assert item.currency == Currency.INR.value
        assert item.target_measure == CompensationMeasure.GUARANTEED_CASH_ANNUAL.value
        assert item.model_version == "0.1.0"
        assert item.latency_ms >= 0.0


def test_batch_pipeline_zero_lone_numbers_invariant(pipeline: BatchInferencePipeline) -> None:
    """Verify Rule R-UQ-01: Zero lone numbers.

    Every output dictionary must have full [p10, p50, p90] interval if ok, or all null if abstained.
    A single solitary scalar estimate is never emitted.
    """
    profiles: list[dict[str, Any]] = [
        {
            "profile_id": "valid-1",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 5.0, "level_id": "SR"},
        },
        {
            "profile_id": "abstained-1",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": -5.0, "level_id": "SR"},
        },
    ]

    results = pipeline.predict_batch(profiles)
    assert len(results) == 2

    # Item 1: Valid
    d_valid = results[0].to_dict()
    assert d_valid["status"] == "ok"
    assert d_valid["p10"] is not None and isinstance(d_valid["p10"], float)
    assert d_valid["p50"] is not None and isinstance(d_valid["p50"], float)
    assert d_valid["p90"] is not None and isinstance(d_valid["p90"], float)
    assert d_valid["interval_width"] is not None and isinstance(d_valid["interval_width"], float)
    assert "point_estimate" not in d_valid
    assert "salary" not in d_valid

    # Item 2: Abstained
    d_abs = results[1].to_dict()
    assert d_abs["status"] == "abstained"
    assert d_abs["p10"] is None
    assert d_abs["p50"] is None
    assert d_abs["p90"] is None
    assert d_abs["interval_width"] is None
    assert len(d_abs["abstention_reasons"]) > 0


def test_batch_pipeline_abstention_domain_and_evidence(pipeline: BatchInferencePipeline) -> None:
    """Verify honest abstention on negative YoE, out-of-range YoE, or unknown role."""
    out_of_domain: list[dict[str, Any]] = [
        {
            "profile_id": "neg-exp",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": -2.0},
        },
        {
            "profile_id": "excess-exp",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 52.0},
        },
        {
            "profile_id": "unknown-role",
            "occupation_id": "UNKNOWN_ALIEN_ROLE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 5.0},
        },
    ]

    results = pipeline.predict_batch(out_of_domain)
    assert len(results) == 3

    assert results[0].is_abstained is True
    assert "OUT_OF_RANGE_EXPERIENCE" in results[0].abstention_reasons

    assert results[1].is_abstained is True
    assert "OUT_OF_RANGE_EXPERIENCE" in results[1].abstention_reasons

    assert results[2].is_abstained is True
    assert "UNSEEN_CATEGORICAL_PROFILE" in results[2].abstention_reasons


def test_batch_pipeline_streaming_chunks(pipeline: BatchInferencePipeline) -> None:
    """Verify streaming generator yields expected chunk sizes and processes all items."""
    n_items = 65
    profiles = [
        {
            "profile_id": f"p-{i}",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 4.0, "level_id": "MID"},
        }
        for i in range(n_items)
    ]

    chunk_sizes: list[int] = []
    total_yielded = 0

    for chunk in pipeline.predict_streaming(profiles, chunk_size=20):
        chunk_sizes.append(len(chunk))
        total_yielded += len(chunk)
        for item in chunk:
            assert item.status == "ok"
            assert item.p50 is not None

    assert total_yielded == n_items
    assert chunk_sizes == [20, 20, 20, 5]


def test_batch_pipeline_polars_df_input(pipeline: BatchInferencePipeline) -> None:
    """Verify pipeline accepts Polars DataFrame input directly."""
    df = pl.DataFrame(
        {
            "profile_id": ["df-1", "df-2"],
            "role": ["SWE", "DATA"],
            "seniority": ["MID", "SR"],
            "location": ["BENGALURU", "HYDERABAD"],
            "years_experience": [3.0, 7.0],
        }
    )

    results = pipeline.predict_batch(df)
    assert len(results) == 2
    assert results[0].profile_id == "df-1"
    assert results[0].role_family == "SWE"
    assert results[1].profile_id == "df-2"
    assert results[1].role_family == "DATA"


def test_batch_pipeline_process_records_and_summary(pipeline: BatchInferencePipeline) -> None:
    """Verify process_records returns BatchInferenceResponse with valid summary and disclaimer."""
    profiles = [
        {
            "profile_id": f"rec-{i}",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 3.0},
        }
        for i in range(30)
    ]
    # Add 2 invalid to check summary counts
    profiles.append(
        {
            "profile_id": "bad-1",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": -1.0},
        }
    )
    profiles.append(
        {
            "profile_id": "bad-2",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 45.0},
        }
    )

    resp: BatchInferenceResponse = pipeline.process_records(profiles, chunk_size=10)
    summary = resp.summary

    assert summary["total_records"] == 32
    assert summary["successful_estimates"] == 30
    assert summary["abstained_count"] == 2
    assert summary["throughput_predictions_per_sec"] > 0
    assert summary["disclaimer"] == STATUTORY_DISCLAIMER
    # CPA 2019 / Rule R-CR-01 zero causal claims check
    assert "causal" in summary["disclaimer"].lower() or "guarantee" in summary["disclaimer"].lower()

    # Verify to_polars_df
    res_df = resp.to_polars_df()
    assert isinstance(res_df, pl.DataFrame)
    assert len(res_df) == 32
    assert "p10" in res_df.columns
    assert "p50" in res_df.columns
    assert "p90" in res_df.columns


def test_batch_pipeline_file_csv_and_ndjson(pipeline: BatchInferencePipeline) -> None:
    """Verify batch file processing on CSV and NDJSON formats."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Test CSV roundtrip
        in_csv = tmp_path / "input.csv"
        out_csv = tmp_path / "output.csv"

        df_in = pl.DataFrame(
            {
                "profile_id": [f"csv-{i}" for i in range(15)],
                "occupation_id": ["SWE"] * 15,
                "location_id": ["BENGALURU"] * 15,
                "years_experience": [4.5] * 15,
                "seniority": ["MID"] * 15,
            }
        )
        df_in.write_csv(in_csv)

        summary_csv = pipeline.process_file(in_csv, out_csv, chunk_size=5)
        assert summary_csv.total_records == 15
        assert summary_csv.successful_estimates == 15
        assert out_csv.exists()

        df_out_csv = pl.read_csv(out_csv)
        assert len(df_out_csv) == 15
        assert "p50" in df_out_csv.columns

        # 2. Test NDJSON roundtrip
        in_ndjson = tmp_path / "input.ndjson"
        out_ndjson = tmp_path / "output.ndjson"

        df_in.write_ndjson(in_ndjson)
        summary_ndjson = pipeline.process_file(in_ndjson, out_ndjson, chunk_size=5)
        assert summary_ndjson.total_records == 15
        assert summary_ndjson.successful_estimates == 15
        assert out_ndjson.exists()

        df_out_ndjson = pl.read_ndjson(out_ndjson)
        assert len(df_out_ndjson) == 15


def test_batch_pipeline_throughput_sla(pipeline: BatchInferencePipeline) -> None:
    """Verify Performance SLA: Batch throughput >= 1,000 predictions/second (ENG-17)."""
    n_benchmark = 1000
    benchmark_records = [
        {
            "profile_id": f"bench-{i}",
            "occupation_id": "SWE" if i % 2 == 0 else "DATA",
            "location_id": "BENGALURU" if i % 3 == 0 else "HYDERABAD",
            "experience": {"total_years": 2.0 + (i % 8), "level_id": "MID"},
        }
        for i in range(n_benchmark)
    ]

    t0 = time.perf_counter()
    results = pipeline.predict_batch(benchmark_records)
    elapsed = time.perf_counter() - t0

    throughput = len(results) / elapsed
    ms = elapsed * 1000.0
    print(f"\n[ENG-17 Benchmark] {n_benchmark} records in {ms:.2f} ms ({throughput:,.1f} pred/s)")

    assert len(results) == n_benchmark
    assert all(r.status == "ok" for r in results)
    # Strict SLA check: >= 1,000 predictions/sec
    assert throughput >= 1000.0, (
        f"Throughput {throughput:.1f} pred/sec fell below 1,000 pred/sec SLA."
    )


def test_batch_pipeline_empty_records(pipeline: BatchInferencePipeline) -> None:
    """Verify empty input returns empty list gracefully."""
    assert pipeline.predict_batch([]) == []
    resp = pipeline.process_records([])
    assert resp.summary["total_records"] == 0
    assert len(resp.results) == 0
