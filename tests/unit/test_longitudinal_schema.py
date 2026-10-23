"""Unit tests for optional longitudinal career schema extension (Task T13.04, ADR-0008).

Verifies:
1. Canonical CompensationObservation model optionality (defaults to None, accepts dates/flags).
2. Date ordering invariant (last_promotion_date >= career_start_date).
3. Pandera Polars canonical_dataframe_schema compatibility with and without longitudinal columns.
4. SQLAlchemy Contribution ORM model column definitions and types.
5. Governance ContributionSubmission service dataclass defaults and overrides.
6. Service submit_contribution persistence and validation.
7. FastAPI ContributionCreateRequest parsing and error handling.
8. Operational erasure cascade purges longitudinal records completely.
9. Machine learning serving and prediction independence (zero interference with model features).
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal

import polars as pl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from compintel.errors import DataContractError
from compintel.governance.db import create_sync_engine, get_db
from compintel.governance.models import Base, Contribution
from compintel.governance.router import router as governance_router
from compintel.governance.service import (
    ContributionSubmission,
    GovernanceError,
    execute_erasure,
    submit_contribution,
)
from compintel.schema import (
    CURRENT_SCHEMA_VERSION,
    CompensationObservation,
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    RoleFamily,
    SeniorityLevel,
    TaxBasis,
    canonical_dataframe_schema,
)


def _sample_canonical_payload() -> dict:
    """Generate a standard valid canonical dictionary."""
    return {
        "observation_id": f"OBS-LONG-{uuid.uuid4().hex[:8]}",
        "source_id": "SRC-INT-VOL-01",
        "source_version": "2026-10-23",
        "schema_version": CURRENT_SCHEMA_VERSION,
        "license_id": "PROPRIETARY-CONSENTED",
        "provenance_tier": ProvenanceTier.TIER_A,
        "as_of_date": date(2026, 10, 23),
        "ingested_at": datetime.now(UTC),
        "is_synthetic": False,
        "role_family": RoleFamily.SWE,
        "canonical_title": "Senior Systems Engineer",
        "raw_title": "Senior Systems Engineer",
        "seniority": SeniorityLevel.SR,
        "location": MetroLocation.BENGALURU,
        "raw_location": "Bengaluru, Karnataka",
        "years_experience": 6.5,
        "guaranteed_cash_annual": 38.5,
        "raw_pay_amount": 3850000.0,
        "raw_currency": "INR",
        "raw_pay_period": PayPeriod.ANNUAL,
        "raw_tax_basis": TaxBasis.GROSS_PRETAX,
        "is_unbundled_aggregate": False,
        "quarantine_status": False,
    }


@pytest.fixture
def isolated_db_session() -> Generator[Session, None, None]:
    """Provide an in-memory SQLite database session with translated governance schemas."""
    engine = create_sync_engine(
        "sqlite:///:memory:",
        schema_translate_map={"identity": None, "app": None},
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.mark.unit
def test_canonical_observation_longitudinal_defaults_none() -> None:
    """Verify longitudinal fields default to None if omitted (zero breaking changes)."""
    payload = _sample_canonical_payload()
    obs = CompensationObservation(**payload)

    assert obs.career_start_date is None
    assert obs.last_promotion_date is None
    assert obs.right_censored_exit_flag is None


@pytest.mark.unit
def test_canonical_observation_longitudinal_valid_fields() -> None:
    """Verify longitudinal fields accept valid dates and boolean exit indicator."""
    payload = _sample_canonical_payload()
    payload["career_start_date"] = date(2018, 7, 1)
    payload["last_promotion_date"] = date(2022, 4, 1)
    payload["right_censored_exit_flag"] = False

    obs = CompensationObservation(**payload)
    assert obs.career_start_date == date(2018, 7, 1)
    assert obs.last_promotion_date == date(2022, 4, 1)
    assert obs.right_censored_exit_flag is False


@pytest.mark.unit
def test_canonical_observation_invalid_date_order_raises() -> None:
    """Verify last_promotion_date < career_start_date raises DataContractError."""
    payload = _sample_canonical_payload()
    payload["career_start_date"] = date(2022, 1, 1)
    payload["last_promotion_date"] = date(2019, 1, 1)  # Invalid: before career start

    with pytest.raises(DataContractError) as exc_info:
        CompensationObservation(**payload)

    assert "INVALID_LONGITUDINAL_DATES" in exc_info.value.code
    assert "last_promotion_date" in str(exc_info.value)


@pytest.mark.unit
def test_pandera_canonical_dataframe_schema_compatibility() -> None:
    """Verify canonical_dataframe_schema validates polars DataFrames with/without new columns."""
    base_dict = {
        "observation_id": ["OBS-01"],
        "source_id": ["SRC-01"],
        "source_version": ["2026-10"],
        "schema_version": ["1.0.0"],
        "license_id": ["CC-BY-4.0"],
        "provenance_tier": ["tier_a"],
        "as_of_date": [date(2026, 1, 1)],
        "ingested_at": [datetime.now(UTC)],
        "is_synthetic": [False],
        "role_family": ["software_engineer"],
        "canonical_title": ["SWE II"],
        "raw_title": ["SWE II"],
        "seniority": ["MID"],
        "location": ["BLR"],
        "raw_location": ["Bengaluru"],
        "years_experience": [3.5],
        "guaranteed_cash_annual": [22.0],
        "raw_pay_amount": [2200000.0],
        "raw_currency": ["INR"],
        "raw_pay_period": ["annual"],
        "is_unbundled_aggregate": [False],
        "quarantine_status": [False],
    }

    # 1. Without longitudinal columns (backward compatibility)
    df_no_long = pl.DataFrame(base_dict)
    validated_df = canonical_dataframe_schema.validate(df_no_long)
    assert len(validated_df) == 1

    # 2. With longitudinal columns populated
    dict_with_long = dict(base_dict)
    dict_with_long["career_start_date"] = [date(2020, 6, 1)]
    dict_with_long["last_promotion_date"] = [date(2023, 1, 15)]
    dict_with_long["right_censored_exit_flag"] = [True]

    df_with_long = pl.DataFrame(dict_with_long)
    validated_with_long = canonical_dataframe_schema.validate(df_with_long)
    assert len(validated_with_long) == 1
    assert validated_with_long["career_start_date"][0] == date(2020, 6, 1)


@pytest.mark.unit
def test_contribution_orm_model_mapping() -> None:
    """Verify Contribution SQLAlchemy model holds longitudinal attributes."""
    key = uuid.uuid4()
    consent_id = uuid.uuid4()
    contrib = Contribution(
        contributor_key=key,
        consent_id=consent_id,
        role_family="software_engineer",
        title_raw="Platform Engineer",
        seniority="IC3_SENIOR",
        location="BLR",
        years_experience=Decimal("5.0"),
        guaranteed_cash_annual=Decimal("3500000.00"),
        career_start_date=date(2019, 6, 1),
        last_promotion_date=date(2023, 1, 1),
        right_censored_exit_flag=False,
    )

    assert contrib.career_start_date == date(2019, 6, 1)
    assert contrib.last_promotion_date == date(2023, 1, 1)
    assert contrib.right_censored_exit_flag is False


@pytest.mark.unit
def test_service_submit_contribution_persists_longitudinal(isolated_db_session: Session) -> None:
    """Verify submit_contribution saves longitudinal attributes to the database."""
    submission = ContributionSubmission(
        role_family="software_engineer",
        title_raw="Staff Engineer",
        seniority="IC4_STAFF",
        location="BLR",
        years_experience=Decimal("10.0"),
        guaranteed_cash_annual=Decimal("6500000.00"),
        consent_benchmarking=True,
        consent_research=True,
        career_start_date=date(2014, 8, 1),
        last_promotion_date=date(2021, 10, 1),
        right_censored_exit_flag=True,
    )

    receipt = submit_contribution(isolated_db_session, submission)
    assert receipt.status == "submitted"

    # Query database directly
    saved = isolated_db_session.query(Contribution).filter_by(id=receipt.contribution_id).first()
    assert saved is not None
    assert saved.career_start_date == date(2014, 8, 1)
    assert saved.last_promotion_date == date(2021, 10, 1)
    assert saved.right_censored_exit_flag is True


@pytest.mark.unit
def test_service_submit_contribution_invalid_dates_raises(isolated_db_session: Session) -> None:
    """Verify submit_contribution raises GovernanceError on invalid date order."""
    submission = ContributionSubmission(
        role_family="software_engineer",
        title_raw="Engineer",
        seniority="IC2_MID",
        location="BLR",
        years_experience=Decimal("4.0"),
        guaranteed_cash_annual=Decimal("2000000.00"),
        consent_benchmarking=True,
        career_start_date=date(2022, 1, 1),
        last_promotion_date=date(2020, 1, 1),  # Invalid order
    )

    with pytest.raises(GovernanceError, match="Invalid longitudinal career timeline"):
        submit_contribution(isolated_db_session, submission)


@pytest.mark.unit
def test_router_contribution_create_request_validation(isolated_db_session: Session) -> None:
    """Verify FastAPI router parses optional longitudinal fields and responds 201."""
    app = FastAPI()
    app.include_router(governance_router)

    def override_get_db() -> Generator[Session, None, None]:
        yield isolated_db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    payload = {
        "role_family": "software_engineer",
        "title_raw": "Senior Frontend Developer",
        "seniority": "IC3_SENIOR",
        "location": "HYD",
        "years_experience": 7.0,
        "guaranteed_cash_annual": 4200000.00,
        "currency": "INR",
        "consent_benchmarking": True,
        "consent_research": True,
        "career_start_date": "2017-06-15",
        "last_promotion_date": "2022-03-01",
        "right_censored_exit_flag": False,
    }

    response = client.post("/v1/contributions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "contribution_id" in data
    assert "deletion_token" in data

    # Verify invalid dates return 422
    payload_invalid = dict(payload)
    payload_invalid["last_promotion_date"] = "2015-01-01"  # before start date
    resp_invalid = client.post("/v1/contributions", json=payload_invalid)
    assert resp_invalid.status_code == 422
    assert "Invalid longitudinal career timeline" in resp_invalid.json()["detail"]


@pytest.mark.unit
def test_erasure_cascade_purges_longitudinal_records(isolated_db_session: Session) -> None:
    """Verify statutory erasure cascade completely scrubs longitudinal records from DB."""
    submission = ContributionSubmission(
        role_family="software_engineer",
        title_raw="ML Engineer",
        seniority="IC3_SENIOR",
        location="BLR",
        years_experience=Decimal("5.0"),
        guaranteed_cash_annual=Decimal("3600000.00"),
        consent_benchmarking=True,
        career_start_date=date(2019, 7, 1),
        last_promotion_date=date(2022, 1, 1),
        right_censored_exit_flag=False,
    )

    receipt = submit_contribution(isolated_db_session, submission)
    contrib_id = receipt.contribution_id

    # Verify record exists
    assert isolated_db_session.query(Contribution).filter_by(id=contrib_id).count() == 1

    # Execute statutory erasure cascade
    deletion_receipt = execute_erasure(
        isolated_db_session,
        deletion_token=receipt.deletion_token,
    )
    assert deletion_receipt.status == "completed"
    assert deletion_receipt.records_purged_count == 1

    # Verify record is purged completely
    assert isolated_db_session.query(Contribution).filter_by(id=contrib_id).count() == 0


@pytest.mark.unit
def test_model_bundle_feature_independence() -> None:
    """Verify that model bundle feature specification has zero dependence on longitudinal fields."""
    from compintel.features.spec import FEATURE_REGISTRY

    # Inspect all registered feature IDs across all levels
    longitudinal_names = {"career_start_date", "last_promotion_date", "right_censored_exit_flag"}
    registered_ids = {feat.feature_id for feat in FEATURE_REGISTRY}
    intersection = registered_ids & longitudinal_names
    assert not intersection, (
        f"Feature specification violates independence by registering "
        f"longitudinal fields: {intersection}"
    )
