"""Unit tests for canonical schema models and entities (Rules R-DA-03, R-DA-04, R-MD-07)."""

from datetime import UTC, date, datetime

import pytest

from compintel.errors import DataContractError
from compintel.schema import (
    CURRENT_SCHEMA_VERSION,
    CompensationObservation,
    CoverageCell,
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    QuarantineReason,
    QuarantineRecord,
    RawRecord,
    RoleFamily,
    SeniorityLevel,
    SourceManifest,
    TaxBasis,
)


def _sample_valid_dict() -> dict:
    return {
        "observation_id": "OBS-2026-TEST-001",
        "source_id": "SRC-INT-VOL-01",
        "source_version": "2026-10-14",
        "schema_version": CURRENT_SCHEMA_VERSION,
        "license_id": "PROPRIETARY-CONSENTED",
        "provenance_tier": ProvenanceTier.TIER_A,
        "as_of_date": date(2026, 10, 1),
        "ingested_at": datetime.now(UTC),
        "is_synthetic": False,
        "role_family": RoleFamily.SWE,
        "canonical_title": "Backend Software Engineer",
        "raw_title": "Software Engineer II - Platform",
        "seniority": SeniorityLevel.MID,
        "location": MetroLocation.BENGALURU,
        "raw_location": "Bengaluru, Karnataka",
        "years_experience": 4.5,
        "education_level": "B.Tech Computer Science",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "guaranteed_cash_annual": 24.5,
        "basic_annual": 12.0,
        "hra_annual": 6.0,
        "special_allowance_annual": 6.5,
        "variable_cash_annual": 3.0,
        "signon_bonus_cash": 2.0,
        "equity_annual_val": 5.0,
        "total_comp_annual": 32.5,
        "raw_pay_amount": 2450000.0,
        "raw_currency": "INR",
        "raw_pay_period": PayPeriod.ANNUAL,
        "raw_tax_basis": TaxBasis.GROSS_PRETAX,
        "is_unbundled_aggregate": False,
        "quarantine_status": False,
    }


@pytest.mark.unit
def test_valid_observation_creation() -> None:
    """Verify standard valid observation instantiates with all properties."""
    data = _sample_valid_dict()
    obs = CompensationObservation(**data)

    assert obs.observation_id == "OBS-2026-TEST-001"
    assert obs.role_family == RoleFamily.SWE.value
    assert obs.seniority == SeniorityLevel.MID.value
    assert obs.location == MetroLocation.BENGALURU.value
    assert obs.guaranteed_cash_annual == 24.5
    assert obs.raw_pay_amount == 2450000.0
    assert obs.raw_currency == "INR"
    assert obs.schema_version == CURRENT_SCHEMA_VERSION


@pytest.mark.unit
def test_anti_heuristic_unbundling_rmd07_violation() -> None:
    """Rule R-MD-07: Bundled CTC cannot populate guaranteed_cash_annual."""
    data = _sample_valid_dict()
    data["is_unbundled_aggregate"] = True
    data["guaranteed_cash_annual"] = 28.0  # Must fail!

    with pytest.raises(DataContractError) as exc_info:
        CompensationObservation(**data)

    assert "R_MD_07_CTC_UNBUNDLING_VIOLATION" in exc_info.value.code
    assert "Rule R-MD-07" in str(exc_info.value)


@pytest.mark.unit
def test_anti_heuristic_unbundling_rmd07_compliant() -> None:
    """Rule R-MD-07: Bundled CTC with null guaranteed_cash_annual is valid."""
    data = _sample_valid_dict()
    data["is_unbundled_aggregate"] = True
    data["guaranteed_cash_annual"] = None
    data["ctc_annual"] = 28.0

    obs = CompensationObservation(**data)
    assert obs.is_unbundled_aggregate is True
    assert obs.guaranteed_cash_annual is None
    assert obs.ctc_annual == 28.0


@pytest.mark.unit
def test_quarantine_reason_consistency() -> None:
    """Quarantine status requires a deterministic reason code."""
    data = _sample_valid_dict()
    data["quarantine_status"] = True
    data["quarantine_reason"] = None

    with pytest.raises(DataContractError) as exc_info:
        CompensationObservation(**data)
    assert "MISSING_QUARANTINE_REASON" in exc_info.value.code

    # Passing case with reason code
    data["quarantine_reason"] = QuarantineReason.UNBUNDLED_AGGREGATE
    obs = CompensationObservation(**data)
    assert obs.quarantine_status is True
    assert obs.quarantine_reason == QuarantineReason.UNBUNDLED_AGGREGATE.value


@pytest.mark.unit
def test_invalid_records_raise_data_contract_error_via_from_record() -> None:
    """Invalid input dictionaries must raise DataContractError when parsed."""
    invalid_data = _sample_valid_dict()
    invalid_data["observation_id"] = "   "  # Blank string

    with pytest.raises(DataContractError):
        CompensationObservation.from_record(invalid_data)

    # Negative experience
    invalid_exp = _sample_valid_dict()
    invalid_exp["years_experience"] = -2.0
    with pytest.raises(DataContractError):
        CompensationObservation.from_record(invalid_exp)


@pytest.mark.unit
def test_advertised_range_bounds() -> None:
    """Advertised min cannot exceed max."""
    data = _sample_valid_dict()
    data["advertised_min_annual"] = 30.0
    data["advertised_max_annual"] = 20.0

    with pytest.raises(DataContractError) as exc_info:
        CompensationObservation(**data)
    assert "INVALID_ADVERTISED_RANGE" in exc_info.value.code


@pytest.mark.unit
def test_supporting_entities() -> None:
    """Verify RawRecord, QuarantineRecord, SourceManifest, and CoverageCell."""
    now = datetime.now(UTC)

    raw = RawRecord(
        source_id="SRC-INT-VOL-01",
        source_version="v1",
        license_id="PROPRIETARY",
        retrieved_at=now,
        raw_payload={"salary": 2000000},
        record_hash="abc123sha",
    )
    assert raw.source_id == "SRC-INT-VOL-01"

    quarantine = QuarantineRecord(
        quarantine_id="QR-001",
        source_id="SRC-INT-VOL-01",
        quarantine_reason=QuarantineReason.MISSING_PAY,
        exclusion_details="No pay reported",
        raw_payload={"title": "Dev"},
        quarantined_at=now,
    )
    assert quarantine.quarantine_reason == QuarantineReason.MISSING_PAY

    manifest = SourceManifest(
        source_id="SRC-IND-MOSPI-01",
        source_name="MOSPI PLFS",
        version="2023-24",
        license_spdx="OGD-India",
        provenance_tier=ProvenanceTier.TIER_A,
        retrieved_at=now,
        sha256_checksum="123456",
        row_count=5000,
        file_format="csv",
    )
    assert manifest.row_count == 5000

    # Core cell vs non-core cell check
    core_cell = CoverageCell(
        role_family=RoleFamily.SWE,
        location=MetroLocation.BENGALURU,
        seniority=SeniorityLevel.SR,
    )
    assert core_cell.cell_id == "SWE.BENGALURU.SR"
    assert core_cell.is_core_cell is True

    extended_cell = CoverageCell(
        role_family=RoleFamily.DATA,
        location=MetroLocation.PUNE,
        seniority=SeniorityLevel.MID,
    )
    assert extended_cell.is_core_cell is False
