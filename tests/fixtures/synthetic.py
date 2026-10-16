"""Synthetic compensation data generator for plumbing and test suites (Rule R-MD-11).

Generates realistic, schema-conforming synthetic observations and raw records for testing
pipeline stages without leaking synthetic metrics into production reporting or benchmarks.

Governed by:
- Rule R-MD-11: Synthetic data is for plumbing and tests only. Metrics computed on it
  MUST NOT be reported as model performance or canonical data quality.
- Rule R-DA-03: Raw values preserved beside normalized values.
- Rule R-DA-04: Mandatory provenance metadata attached to every record.
- Rule R-DA-06: Deduplication cluster IDs populated.
- Rule R-MD-07: Guaranteed cash strictly unbundled; aggregate CTC quarantined.
"""

import random
from datetime import UTC, date, datetime
from typing import Any

import polars as pl

from compintel.schema.canonical import (
    CURRENT_SCHEMA_VERSION,
    validate_observations_df,
)
from compintel.schema.enums import (
    Currency,
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    RoleFamily,
    SeniorityLevel,
    TaxBasis,
)

SYNTHETIC_EPOCH_TIMESTAMP: datetime = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)

# Reference career ladder salary distributions (nominal INR LPA)
SENIORITY_PAY_PARAMS: dict[SeniorityLevel, tuple[float, float, float, float]] = {
    # Seniority: (yoe_min, yoe_max, cash_min, cash_max)
    SeniorityLevel.JR: (0.0, 2.5, 6.0, 16.0),
    SeniorityLevel.MID: (2.0, 6.0, 14.0, 32.0),
    SeniorityLevel.SR: (5.0, 11.0, 26.0, 58.0),
    SeniorityLevel.STAFF: (9.0, 16.0, 48.0, 92.0),
    SeniorityLevel.PRINCIPAL: (14.0, 25.0, 78.0, 170.0),
    SeniorityLevel.OTHER: (0.0, 10.0, 5.0, 30.0),
}

ROLE_TITLES: dict[RoleFamily, list[str]] = {
    RoleFamily.SWE: [
        "Backend Software Engineer",
        "Frontend Software Engineer",
        "Full Stack Engineer",
        "Platform Engineer",
        "Systems Software Engineer",
        "Site Reliability Engineer",
    ],
    RoleFamily.DATA: [
        "Data Scientist",
        "Data Engineer",
        "Analytics Engineer",
        "Data Analyst",
        "Business Intelligence Developer",
    ],
    RoleFamily.MLAI: [
        "Machine Learning Engineer",
        "AI Research Engineer",
        "Applied Scientist - ML",
        "Computer Vision Engineer",
        "MLOps Engineer",
        "NLP Specialist",
    ],
    RoleFamily.OTHER: [
        "Technical Program Manager",
        "Product Manager - Tech",
        "Engineering Manager",
    ],
}

DEFAULT_METROS: list[MetroLocation] = [
    MetroLocation.BENGALURU,
    MetroLocation.HYDERABAD,
    MetroLocation.PUNE,
    MetroLocation.MUMBAI,
    MetroLocation.NCR,
    MetroLocation.CHENNAI,
]

TECH_EMPLOYERS: list[str] = [
    "Acme Corp India Pvt Ltd",
    "Apex Tech Solutions",
    "Bharat Systems Ltd",
    "CloudScale Networks",
    "DataPulse Analytics",
    "Echo Software Labs",
    "FinOptima Technologies",
    "GigaBytes Infotech",
]


class SyntheticDataGenerator:
    """Configurable synthetic data generator for plumbing and pipeline tests."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_observation_dict(
        self,
        obs_idx: int = 1,
        role_family: RoleFamily | None = None,
        seniority: SeniorityLevel | None = None,
        location: MetroLocation | None = None,
        is_unbundled_aggregate: bool = False,
    ) -> dict[str, Any]:
        """Generate a single canonical observation dictionary with is_synthetic=True."""
        rf = role_family or self.rng.choice([RoleFamily.SWE, RoleFamily.DATA, RoleFamily.MLAI])
        sen = seniority or self.rng.choice(
            [
                SeniorityLevel.JR,
                SeniorityLevel.MID,
                SeniorityLevel.SR,
                SeniorityLevel.STAFF,
            ]
        )
        loc = location or self.rng.choice(DEFAULT_METROS)

        yoe_min, yoe_max, cash_min, cash_max = SENIORITY_PAY_PARAMS[sen]
        yoe = round(self.rng.uniform(yoe_min, yoe_max), 1)

        # Base salary generation within band
        base_cash = round(self.rng.uniform(cash_min, cash_max), 2)
        basic_part = round(base_cash * self.rng.uniform(0.40, 0.50), 2)
        hra_part = round(base_cash * self.rng.uniform(0.20, 0.25), 2)
        special_part = round(base_cash - (basic_part + hra_part), 2)

        titles = ROLE_TITLES.get(rf, ["Software Engineer"])
        title = self.rng.choice(titles)
        employer = self.rng.choice(TECH_EMPLOYERS)

        var_cash = round(base_cash * self.rng.uniform(0.05, 0.20), 2)
        equity_val = (
            round(base_cash * self.rng.uniform(0.10, 0.35), 2)
            if sen in (SeniorityLevel.SR, SeniorityLevel.STAFF, SeniorityLevel.PRINCIPAL)
            else 0.0
        )
        total_comp = round(base_cash + var_cash + equity_val, 2)

        raw_inr = round(base_cash * 100_000.0, 2)
        now = SYNTHETIC_EPOCH_TIMESTAMP

        obs_id = f"OBS-SYN-{self.seed:04d}-{obs_idx:05d}"
        person_id = f"PER-SYN-{obs_idx % 80:04d}"
        emp_id = f"EMP-SYN-{abs(hash(employer)) % 1000:04d}"
        pst_id = f"PST-SYN-{obs_idx % 60:04d}"

        # Unbundled aggregates have None guaranteed cash to avoid Rule R-MD-07 violation
        guaranteed_cash = None if is_unbundled_aggregate else base_cash

        return {
            "observation_id": obs_id,
            "source_id": "SRC-SYN-FIXTURE-01",
            "source_version": "v1.0-synthetic",
            "schema_version": CURRENT_SCHEMA_VERSION,
            "license_id": "SYNTHETIC-PERMISSIVE-TEST",
            "provenance_tier": ProvenanceTier.TIER_D.value,
            "as_of_date": date(2026, 10, 1),
            "ingested_at": now,
            "is_synthetic": True,  # Mandatory Rule R-MD-11 flag
            "role_family": rf.value,
            "canonical_title": title,
            "raw_title": f"{sen.value} {title}",
            "seniority": sen.value,
            "location": loc.value,
            "raw_location": f"{loc.value.title()}, India",
            "years_experience": yoe,
            "guaranteed_cash_annual": guaranteed_cash,
            "basic_annual": basic_part if not is_unbundled_aggregate else None,
            "hra_annual": hra_part if not is_unbundled_aggregate else None,
            "special_allowance_annual": special_part if not is_unbundled_aggregate else None,
            "variable_cash_annual": var_cash,
            "equity_annual_val": equity_val,
            "total_comp_annual": total_comp,
            "raw_pay_amount": raw_inr,
            "raw_currency": Currency.INR.value,
            "raw_pay_period": PayPeriod.ANNUAL.value,
            "raw_tax_basis": TaxBasis.GROSS_PRETAX.value,
            "is_unbundled_aggregate": is_unbundled_aggregate,
            "quarantine_status": False,
            "quarantine_reason": None,
            "exact_duplicate_cluster_id": f"EX-SYN-{obs_idx:05d}",
            "person_cluster_id": person_id,
            "employer_cluster_id": emp_id,
            "posting_cluster_id": pst_id,
            "is_exact_duplicate": False,
            "source_quality_score": 50.0,
            "hard_gates_passed": False,
            "is_pt1_eligible": False,  # Strict Rule R-MD-11 invariant
        }

    def generate_observations_df(
        self,
        n_records: int = 100,
        inject_duplicates: int = 0,
        inject_unbundled: int = 0,
    ) -> pl.DataFrame:
        """Generate a valid Polars DataFrame of synthetic observations."""
        records: list[dict[str, Any]] = []

        for i in range(1, n_records + 1):
            is_unbundled = i <= inject_unbundled
            record = self.generate_observation_dict(
                obs_idx=i,
                is_unbundled_aggregate=is_unbundled,
            )
            records.append(record)

        # Inject exact duplicates if requested
        if inject_duplicates > 0 and len(records) > 0:
            for j in range(inject_duplicates):
                dup_source = records[j % len(records)]
                dup = dict(dup_source)
                dup["observation_id"] = f"OBS-SYN-DUP-{j + 1:04d}"
                dup["is_exact_duplicate"] = True
                records.append(dup)

        df = pl.DataFrame(records)
        return validate_observations_df(df)

    def generate_raw_records_df(self, n_records: int = 50) -> pl.DataFrame:
        """Generate synthetic raw intake records for connector and ingestion testing."""
        raw_list: list[dict[str, Any]] = []
        now = SYNTHETIC_EPOCH_TIMESTAMP

        for i in range(1, n_records + 1):
            sen = self.rng.choice(list(SeniorityLevel))
            yoe_min, yoe_max, cash_min, cash_max = SENIORITY_PAY_PARAMS[sen]
            cash = round(self.rng.uniform(cash_min, cash_max), 2)
            rf = self.rng.choice([RoleFamily.SWE, RoleFamily.DATA, RoleFamily.MLAI])
            title = self.rng.choice(ROLE_TITLES[rf])
            loc = self.rng.choice(DEFAULT_METROS)

            raw_list.append(
                {
                    "submission_id": f"SUB-SYN-{i:05d}",
                    "job_title": title,
                    "seniority": sen.value,
                    "location": loc.value,
                    "experience_years": round(self.rng.uniform(yoe_min, yoe_max), 1),
                    "base_pay_inr": cash * 100_000.0,
                    "variable_pay_inr": cash * 0.10 * 100_000.0,
                    "currency": "INR",
                    "pay_period": "ANNUAL",
                    "submitted_at": now.isoformat(),
                    "is_synthetic": True,
                }
            )

        return pl.DataFrame(raw_list)


def generate_synthetic_observations_df(
    n_records: int = 100,
    seed: int = 42,
    inject_duplicates: int = 0,
    inject_unbundled: int = 0,
) -> pl.DataFrame:
    """Functional convenience wrapper generating valid synthetic observations."""
    generator = SyntheticDataGenerator(seed=seed)
    return generator.generate_observations_df(
        n_records=n_records,
        inject_duplicates=inject_duplicates,
        inject_unbundled=inject_unbundled,
    )


def generate_synthetic_raw_records_df(
    n_records: int = 50,
    seed: int = 42,
) -> pl.DataFrame:
    """Functional convenience wrapper generating synthetic raw ingestion records."""
    generator = SyntheticDataGenerator(seed=seed)
    return generator.generate_raw_records_df(n_records=n_records)
