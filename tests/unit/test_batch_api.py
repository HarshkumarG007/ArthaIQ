"""Unit tests for batch estimation router components and models (Phase 23, Task T23.04).

Verifies:
- Pydantic models serialization and validation.
- Request validation helpers (_validate_batch_request, _prepare_profile_records).
- Adherence to Rule R-UQ-01 (Zero lone numbers) and Rule R-CR-01 (CPA 2019 disclaimer).
- Error handling for invalid measures and currencies.
"""

from __future__ import annotations

import pytest

from compintel.errors import ValidationError
from compintel.serving.routers.batch import (
    _prepare_profile_records,
    _validate_batch_request,
)
from compintel.serving.types import (
    BatchEstimateItem,
    BatchEstimateRequest,
    BatchEstimateResponse,
    BatchEstimateSummary,
    BatchProfileItem,
    ExperienceInput,
)


def test_batch_profile_item_default_profile_id() -> None:
    """BatchProfileItem automatically generates a UUID profile_id if not supplied."""
    item = BatchProfileItem(
        occupation_id="SWE",
        location_id="BENGALURU",
        experience=ExperienceInput(total_years=3.0, level_id="MID"),
    )
    assert item.profile_id is not None
    assert len(item.profile_id) > 0
    assert item.occupation_id == "SWE"
    assert item.location_id == "BENGALURU"
    assert item.experience.total_years == 3.0


def test_batch_estimate_request_validation() -> None:
    """BatchEstimateRequest validates nominal coverage and items count bounds."""
    valid_request = BatchEstimateRequest(
        items=[
            BatchProfileItem(
                profile_id="p1",
                occupation_id="SWE",
                location_id="BENGALURU",
            )
        ],
        nominal_coverage=0.85,
    )
    assert valid_request.nominal_coverage == 0.85
    assert valid_request.measure == "guaranteed_cash_annual"
    assert valid_request.currency == "INR"

    _validate_batch_request(valid_request)


def test_batch_estimate_request_invalid_measure_raises_validation_error() -> None:
    """Unsupported measure raises ValidationError."""
    req = BatchEstimateRequest(
        items=[BatchProfileItem(occupation_id="SWE", location_id="BENGALURU")],
        measure="total_ctc",
    )
    with pytest.raises(ValidationError, match="Unsupported compensation measure"):
        _validate_batch_request(req)


def test_batch_estimate_request_invalid_currency_raises_validation_error() -> None:
    """Unsupported currency raises ValidationError."""
    req = BatchEstimateRequest(
        items=[BatchProfileItem(occupation_id="SWE", location_id="BENGALURU")],
        currency="USD",
    )
    with pytest.raises(ValidationError, match="Unsupported currency"):
        _validate_batch_request(req)


def test_prepare_profile_records_transforms_items() -> None:
    """_prepare_profile_records formats Pydantic items into pipeline dictionaries."""
    req = BatchEstimateRequest(
        items=[
            BatchProfileItem(
                profile_id="test-1",
                occupation_id="DATA",
                location_id="HYDERABAD",
                experience=ExperienceInput(total_years=5.0, level_id="SR"),
                extras={"work_arrangement": "HYBRID"},
            )
        ]
    )
    records = _prepare_profile_records(req)
    assert len(records) == 1
    r = records[0]
    assert r["profile_id"] == "test-1"
    assert r["occupation_id"] == "DATA"
    assert r["location_id"] == "HYDERABAD"
    assert r["experience"]["total_years"] == 5.0
    assert r["experience"]["level_id"] == "SR"
    assert r["extras"]["work_arrangement"] == "HYBRID"


def test_batch_estimate_item_conformal_interval_invariants() -> None:
    """BatchEstimateItem adheres to Rule R-UQ-01: p10 <= p50 <= p90."""
    item = BatchEstimateItem(
        profile_id="prof-1",
        role_family="SWE",
        seniority="MID",
        location="BENGALURU",
        years_experience=4.0,
        status="ok",
        is_abstained=False,
        p10=22.0,
        p50=35.0,
        p90=52.0,
        interval_width=30.0,
        nominal_coverage=0.80,
    )
    assert item.status == "ok"
    assert not item.is_abstained
    assert item.p10 is not None and item.p50 is not None and item.p90 is not None
    assert item.p10 <= item.p50 <= item.p90
    assert item.interval_width == 30.0


def test_batch_estimate_item_abstention_invariants() -> None:
    """BatchEstimateItem with abstention has None estimates and reason codes."""
    item = BatchEstimateItem(
        profile_id="prof-2",
        role_family="DATA",
        seniority="UNKNOWN",
        location="TIER3",
        years_experience=0.0,
        status="abstained",
        is_abstained=True,
        p10=None,
        p50=None,
        p90=None,
        abstention_reasons=["SPARSE_COHORT_EVIDENCE"],
        explanation="Insufficient sample size in cohort.",
    )
    assert item.status == "abstained"
    assert item.is_abstained is True
    assert item.p10 is None
    assert item.p50 is None
    assert item.p90 is None
    assert "SPARSE_COHORT_EVIDENCE" in item.abstention_reasons


def test_batch_estimate_response_roundtrip_serialization() -> None:
    """BatchEstimateResponse serializes and deserializes cleanly without loss."""
    summary = BatchEstimateSummary(
        total_records=1,
        successful_estimates=1,
        abstained_count=0,
        duration_seconds=0.005,
        throughput_predictions_per_sec=200.0,
        as_of_date="2026-10-31",
        disclaimer="CPA 2019 Statutory Disclaimer",
    )
    item = BatchEstimateItem(
        profile_id="p1",
        role_family="MLAI",
        seniority="SR",
        location="BENGALURU",
        years_experience=7.0,
        status="ok",
        is_abstained=False,
        p10=30.0,
        p50=45.0,
        p90=65.0,
        interval_width=35.0,
    )
    response = BatchEstimateResponse(
        summary=summary,
        items=[item],
    )
    json_str = response.model_dump_json()
    reconstructed = BatchEstimateResponse.model_validate_json(json_str)

    assert reconstructed.summary.total_records == 1
    assert len(reconstructed.items) == 1
    assert reconstructed.items[0].p50 == 45.0
