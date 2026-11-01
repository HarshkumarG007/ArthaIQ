"""Enterprise Batch Estimation Client SDK (Phase 26, Task T26.01).

Provides high-throughput synchronous batching, streaming NDJSON consumption,
auto-chunking for payloads exceeding 500 items, and CSV/JSON ingestion/export.

Adheres to:
- Rule R-UQ-01: Zero lone numbers. Full calibrated intervals [P10, P50, P90].
- Rule R-UQ-02: Structured abstention preserved honestly without exceptions.
- Rule R-CR-01: Mandatory CPA 2019 statutory disclaimers attached to all outputs.
- Rule R-CD-03: Architectural boundary; client depends only on schema/types.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx

from compintel.serving.types import (
    BatchEstimateItem,
    BatchEstimateResponse,
    BatchEstimateSummary,
    BatchProfileItem,
    ExperienceInput,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from fastapi.testclient import TestClient


class BatchClientError(Exception):
    """Base exception for BatchClient operations."""


class BatchClient:
    """Client for ArthaIQ high-throughput batch and streaming compensation estimation."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 60.0,
        app: Any = None,
    ) -> None:
        """Initialize BatchClient.

        Args:
            base_url: Base HTTP URL of the ArthaIQ serving API.
            api_key: Optional API key passed via X-API-Key header.
            timeout: Timeout in seconds for HTTP operations.
            app: Optional FastAPI/ASGI application for in-memory testing.
        """
        clean_base = base_url.strip().rstrip("/")
        if clean_base.endswith("/v1"):
            clean_base = clean_base[:-3]
        self.base_url = clean_base
        self.api_key = api_key
        self.timeout = timeout
        self.app = app

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            headers["X-API-Key"] = api_key

        self._client: httpx.Client | TestClient
        if app is not None:
            from fastapi.testclient import TestClient

            self._client = TestClient(
                app=app,
                base_url=self.base_url,
                headers=headers,
            )
        else:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=timeout,
            )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> BatchClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _prepare_items(
        self, items: Sequence[BatchProfileItem | dict[str, Any]]
    ) -> list[BatchProfileItem]:
        """Normalize input sequence into validated BatchProfileItem instances."""
        normalized: list[BatchProfileItem] = []
        for item in items:
            if isinstance(item, BatchProfileItem):
                normalized.append(item)
            elif isinstance(item, dict):
                exp = item.get("experience")
                if isinstance(exp, dict) and exp:
                    exp_obj = ExperienceInput(
                        total_years=float(exp.get("total_years", 0.0)),
                        level_id=exp.get("level_id"),
                    )
                else:
                    years = float(item.get("total_years") or item.get("experience_years") or 0.0)
                    level = item.get("level_id") or item.get("level")
                    exp_obj = ExperienceInput(total_years=years, level_id=level)

                profile_id = str(item.get("profile_id") or uuid4())
                occ_id = str(item.get("occupation_id") or item.get("role") or "SWE").strip().upper()
                raw_loc = item.get("location_id") or item.get("city") or "BENGALURU"
                loc_id = str(raw_loc).strip().upper()

                extras: dict[str, Any] = {}
                if "current_ctc_inr" in item:
                    extras["current_ctc_inr"] = item["current_ctc_inr"]

                normalized.append(
                    BatchProfileItem(
                        profile_id=profile_id,
                        occupation_id=occ_id,
                        location_id=loc_id,
                        experience=exp_obj,
                        extras=extras,
                    )
                )
            else:
                raise ValueError(f"Unsupported profile item format: {type(item)}")
        return normalized

    def estimate_batch(
        self,
        profiles: Sequence[BatchProfileItem | dict[str, Any]],
        nominal_coverage: float = 0.80,
        chunk_size: int = 500,
    ) -> BatchEstimateResponse:
        """Execute batch estimation, auto-chunking payloads larger than chunk_size.

        Args:
            profiles: Sequence of profiles as BatchProfileItem or dicts.
            nominal_coverage: Conformal nominal coverage probability (default: 0.80).
            chunk_size: Maximum items per HTTP request (default: 500).

        Returns:
            BatchEstimateResponse combining all processed chunks with aggregated telemetry.
        """
        all_items = self._prepare_items(profiles)
        if not all_items:
            raise ValueError("Input profiles sequence cannot be empty.")

        chunk_size = max(1, min(chunk_size, 500))

        # Chunk items if length > chunk_size
        chunks = [all_items[i : i + chunk_size] for i in range(0, len(all_items), chunk_size)]

        aggregated_items: list[BatchEstimateItem] = []
        total_successful = 0
        total_abstained = 0
        total_duration = 0.0
        disclaimer = ""
        model_version = "0.1.0"
        as_of_date = ""

        t_start = time.perf_counter()

        for chunk in chunks:
            payload = {
                "items": [it.model_dump() for it in chunk],
                "nominal_coverage": nominal_coverage,
            }

            resp = self._client.post("/v1/estimates/batch", json=payload)
            if resp.status_code != 200:
                raise BatchClientError(
                    f"Batch request failed with status {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            response_obj = BatchEstimateResponse.model_validate(data)

            aggregated_items.extend(response_obj.items)
            total_successful += response_obj.summary.successful_estimates
            total_abstained += response_obj.summary.abstained_count
            total_duration += response_obj.summary.duration_seconds
            disclaimer = response_obj.summary.disclaimer
            model_version = response_obj.summary.model_version
            as_of_date = response_obj.summary.as_of_date

        wall_duration = max(time.perf_counter() - t_start, 0.0001)
        throughput = len(aggregated_items) / wall_duration

        combined_summary = BatchEstimateSummary(
            total_records=len(aggregated_items),
            successful_estimates=total_successful,
            abstained_count=total_abstained,
            duration_seconds=round(wall_duration, 4),
            throughput_predictions_per_sec=round(throughput, 2),
            model_version=model_version,
            nominal_coverage=nominal_coverage,
            as_of_date=as_of_date or time.strftime("%Y-%m-%d"),
            disclaimer=disclaimer,
        )

        return BatchEstimateResponse(
            summary=combined_summary,
            items=aggregated_items,
        )

    def stream_batch(
        self,
        profiles: Sequence[BatchProfileItem | dict[str, Any]],
        nominal_coverage: float = 0.80,
        chunk_size: int = 500,
    ) -> Iterator[BatchEstimateItem]:
        """Stream predictions row-by-row via the NDJSON streaming endpoint in chunks.

        Yields:
            BatchEstimateItem instances as they arrive over the wire.
        """
        all_items = self._prepare_items(profiles)
        if not all_items:
            return

        chunk_size = max(1, min(chunk_size, 500))
        chunks = [all_items[i : i + chunk_size] for i in range(0, len(all_items), chunk_size)]

        for chunk in chunks:
            payload = {
                "items": [it.model_dump() for it in chunk],
                "nominal_coverage": nominal_coverage,
            }

            headers = {"Accept": "application/x-ndjson", "Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            with self._client.stream(
                "POST", "/v1/estimates/batch/stream", json=payload, headers=headers
            ) as response:
                if response.status_code != 200:
                    err_msg = response.text
                    raise BatchClientError(
                        f"Streaming request failed with status {response.status_code}: {err_msg}"
                    )

                for line in response.iter_lines():
                    clean_line = line.strip()
                    if clean_line:
                        item_data = json.loads(clean_line)
                        yield BatchEstimateItem.model_validate(item_data)


def load_profiles_from_csv(path: Path | str) -> list[BatchProfileItem]:
    """Parse a CSV file containing candidate profiles into BatchProfileItem objects."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    profiles: list[BatchProfileItem] = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            role = row.get("occupation_id") or row.get("role") or "SWE"
            city = row.get("location_id") or row.get("city") or "BENGALURU"
            try:
                years = float(row.get("total_years") or row.get("experience_years") or 3.0)
            except ValueError:
                years = 3.0

            level = row.get("level_id") or row.get("level") or "MID"
            profile_id = row.get("profile_id") or f"profile-{idx + 1}"

            profiles.append(
                BatchProfileItem(
                    profile_id=profile_id,
                    occupation_id=role.strip().upper(),
                    location_id=city.strip().upper(),
                    experience=ExperienceInput(total_years=years, level_id=level.strip().upper()),
                )
            )

    return profiles


def load_profiles_from_json(path: Path | str) -> list[BatchProfileItem]:
    """Parse JSON or NDJSON file containing candidate profiles."""
    json_path = Path(path)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    text = json_path.read_text(encoding="utf-8").strip()
    if text.startswith("["):
        # JSON Array
        data = json.loads(text)
        items = data
    elif text.startswith("{") and "items" in text:
        # Standard BatchEstimateRequest JSON
        data = json.loads(text)
        items = data.get("items", [])
    else:
        # NDJSON
        items = [json.loads(line) for line in text.splitlines() if line.strip()]

    client = BatchClient()
    return client._prepare_items(items)


def export_results_to_csv(items: Sequence[BatchEstimateItem], path: Path | str) -> None:
    """Export estimation results to an enriched CSV file with full intervals."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "profile_id",
        "role_family",
        "seniority",
        "location",
        "status",
        "support_status",
        "p10_lpa",
        "p50_lpa",
        "p90_lpa",
        "interval_width_lpa",
        "nominal_coverage",
        "evidence_grade",
        "abstention_reasons",
        "explanation",
        "latency_ms",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for it in items:
            writer.writerow(
                {
                    "profile_id": it.profile_id,
                    "role_family": it.role_family,
                    "seniority": it.seniority,
                    "location": it.location,
                    "status": it.status,
                    "support_status": it.support_status,
                    "p10_lpa": f"{it.p10:.2f}" if it.p10 is not None else "",
                    "p50_lpa": f"{it.p50:.2f}" if it.p50 is not None else "",
                    "p90_lpa": f"{it.p90:.2f}" if it.p90 is not None else "",
                    "interval_width_lpa": (
                        f"{it.interval_width:.2f}" if it.interval_width is not None else ""
                    ),
                    "nominal_coverage": f"{it.nominal_coverage:.2f}",
                    "evidence_grade": it.evidence_grade,
                    "abstention_reasons": ";".join(it.abstention_reasons),
                    "explanation": it.explanation,
                    "latency_ms": f"{it.latency_ms:.2f}",
                }
            )


def export_results_to_json(response: BatchEstimateResponse, path: Path | str) -> None:
    """Export complete BatchEstimateResponse to formatted JSON."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(response.model_dump(), indent=2), encoding="utf-8")
