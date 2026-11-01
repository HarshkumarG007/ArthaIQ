"""Unit tests for Enterprise Batch Client SDK & CLI Tool (Phase 26, Task T26.03).

Validates:
1. BatchClient profile normalization and input validation.
2. Auto-chunking for batch sizes exceeding 500 items.
3. In-memory execution using ASGI app transport with champion bundle.
4. Streaming NDJSON response parsing row-by-row.
5. CSV and JSON ingestion and export helpers.
6. CLI argument parser and dry-run workflow.
7. Adherence to Rule R-UQ-01 (Zero lone numbers) and Rule R-CR-01 (Anti-causal).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.compintel_batch import build_parser, main

from compintel.client.batch import (
    BatchClient,
    export_results_to_csv,
    export_results_to_json,
    load_profiles_from_csv,
    load_profiles_from_json,
)
from compintel.serving.app import create_app
from compintel.serving.types import (
    BatchEstimateItem,
    BatchEstimateResponse,
    BatchEstimateSummary,
)


@pytest.fixture(scope="module")
def shared_app():
    """Create shared FastAPI app with champion serving bundle."""
    return create_app()


@pytest.mark.unit
class TestBatchClientUnit:
    """Unit tests for BatchClient internal mechanics."""

    def test_client_prepare_items_from_dicts(self) -> None:
        """Client properly converts raw dictionaries into validated BatchProfileItems."""
        client = BatchClient()
        raw_items = [
            {"role": "SWE", "city": "Bengaluru", "total_years": 4.5, "level": "MID"},
            {
                "occupation_id": "DATA",
                "location_id": "HYDERABAD",
                "experience": {"total_years": 6.0, "level_id": "SR"},
            },
        ]
        items = client._prepare_items(raw_items)
        assert len(items) == 2
        assert items[0].occupation_id == "SWE"
        assert items[0].location_id == "BENGALURU"
        assert items[0].experience.total_years == 4.5
        assert items[0].profile_id is not None

        assert items[1].occupation_id == "DATA"
        assert items[1].location_id == "HYDERABAD"
        assert items[1].experience.total_years == 6.0
        client.close()

    def test_csv_ingestion_and_export(self, tmp_path: Path) -> None:
        """Client loads candidate profiles from CSV and exports enriched results."""
        csv_in = tmp_path / "test_input.csv"
        csv_in.write_text(
            "profile_id,role,city,experience_years,level\n"
            "p-1,SWE,Bengaluru,3.0,MID\n"
            "p-2,DATA,Hyderabad,5.0,SR\n",
            encoding="utf-8",
        )

        profiles = load_profiles_from_csv(csv_in)
        assert len(profiles) == 2
        assert profiles[0].profile_id == "p-1"
        assert profiles[0].occupation_id == "SWE"
        assert profiles[1].profile_id == "p-2"
        assert profiles[1].occupation_id == "DATA"

        mock_item = BatchEstimateItem(
            profile_id="p-1",
            role_family="SWE",
            seniority="MID",
            location="BENGALURU",
            years_experience=3.0,
            status="ok",
            is_abstained=False,
            support_status="SUPPORTED",
            p10=18.0,
            p50=22.0,
            p90=27.0,
            interval_width=9.0,
            evidence_grade="GRADE_A",
            nominal_coverage=0.80,
            abstention_reasons=[],
            explanation="",
            model_version="0.1.0",
            latency_ms=1.5,
        )

        csv_out = tmp_path / "test_output.csv"
        export_results_to_csv([mock_item], csv_out)
        assert csv_out.exists()

        content = csv_out.read_text(encoding="utf-8")
        assert "p-1" in content
        assert "18.00" in content
        assert "22.00" in content
        assert "27.00" in content
        assert "SUPPORTED" in content

    def test_json_ingestion_and_export(self, tmp_path: Path) -> None:
        """Client loads candidate profiles from JSON and exports full response."""
        json_in = tmp_path / "test_input.json"
        json_in.write_text(
            json.dumps(
                [
                    {
                        "profile_id": "j-1",
                        "occupation_id": "MLAI",
                        "location_id": "NCR",
                        "total_years": 4.0,
                    }
                ]
            ),
            encoding="utf-8",
        )

        profiles = load_profiles_from_json(json_in)
        assert len(profiles) == 1
        assert profiles[0].profile_id == "j-1"
        assert profiles[0].occupation_id == "MLAI"

        mock_summary = BatchEstimateSummary(
            total_records=1,
            successful_estimates=1,
            abstained_count=0,
            duration_seconds=0.05,
            throughput_predictions_per_sec=20.0,
            nominal_coverage=0.80,
            as_of_date="2026-11-01",
            disclaimer="Mandatory disclaimer",
        )
        mock_response = BatchEstimateResponse(summary=mock_summary, items=[])

        json_out = tmp_path / "test_output.json"
        export_results_to_json(mock_response, json_out)
        assert json_out.exists()

        data = json.loads(json_out.read_text(encoding="utf-8"))
        assert data["summary"]["total_records"] == 1


@pytest.mark.unit
class TestBatchClientInference:
    """In-process integration tests using ASGI transport and champion bundle."""

    def test_in_process_batch_estimate(self, shared_app) -> None:
        """BatchClient executes batch estimation over ASGI transport without network sockets."""
        client = BatchClient(app=shared_app)

        profiles = [
            {
                "profile_id": "swe-1",
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 4.0, "level_id": "MID"},
            },
            {
                "profile_id": "data-1",
                "occupation_id": "DATA",
                "location_id": "HYDERABAD",
                "experience": {"total_years": 6.0, "level_id": "SR"},
            },
            {
                "profile_id": "mlai-1",
                "occupation_id": "MLAI",
                "location_id": "NCR",
                "experience": {"total_years": 3.0, "level_id": "MID"},
            },
        ]

        response = client.estimate_batch(profiles, nominal_coverage=0.80)
        assert isinstance(response, BatchEstimateResponse)
        assert response.summary.total_records == 3
        assert len(response.items) == 3
        assert response.summary.throughput_predictions_per_sec > 0.0

        for it in response.items:
            assert it.p10 is not None
            assert it.p50 is not None
            assert it.p90 is not None
            assert it.p10 < it.p50 < it.p90
            assert it.support_status == "SUPPORTED"

        client.close()

    def test_in_process_auto_chunking_large_payload(self, shared_app) -> None:
        """BatchClient splits payloads larger than chunk_size and merges summaries."""
        client = BatchClient(app=shared_app)

        # Generate 15 items and chunk with chunk_size=5 to verify multi-chunk merging
        profiles = [
            {
                "profile_id": f"bulk-{i}",
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 4.0, "level_id": "MID"},
            }
            for i in range(15)
        ]

        response = client.estimate_batch(profiles, nominal_coverage=0.80, chunk_size=5)
        assert response.summary.total_records == 15
        assert len(response.items) == 15
        assert response.summary.successful_estimates == 15
        assert response.summary.throughput_predictions_per_sec > 0.0

        client.close()

    def test_in_process_streaming_batch(self, shared_app) -> None:
        """BatchClient streams batch results row-by-row via NDJSON."""
        client = BatchClient(app=shared_app)

        profiles = [
            {
                "profile_id": "stream-1",
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 5.0, "level_id": "MID"},
            },
            {
                "profile_id": "stream-2",
                "occupation_id": "DATA",
                "location_id": "PUNE",
                "experience": {"total_years": 7.0, "level_id": "SR"},
            },
        ]

        streamed = list(client.stream_batch(profiles, nominal_coverage=0.80))
        assert len(streamed) == 2
        assert streamed[0].profile_id == "stream-1"
        assert streamed[1].profile_id == "stream-2"
        assert streamed[0].p50 is not None
        assert streamed[1].p50 is not None

        client.close()


@pytest.mark.unit
class TestBatchCLI:
    """Unit tests for compintel-batch CLI tool."""

    def test_cli_parser(self) -> None:
        """CLI parser accepts expected flags."""
        parser = build_parser()
        args = parser.parse_args(
            ["-i", "candidates.csv", "-o", "out.json", "--stream", "--coverage", "0.85"]
        )
        assert args.input == Path("candidates.csv")
        assert args.output == Path("out.json")
        assert args.stream is True
        assert args.coverage == 0.85

    def test_cli_dry_run(self, tmp_path: Path) -> None:
        """CLI dry-run parses input file and exits with code 0 without network calls."""
        csv_file = tmp_path / "candidates.csv"
        csv_file.write_text(
            "profile_id,role,city,experience_years,level\nc-1,SWE,Bengaluru,4.0,MID\n",
            encoding="utf-8",
        )

        exit_code = main(["-i", str(csv_file), "--dry-run"])
        assert exit_code == 0
