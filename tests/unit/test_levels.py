"""Unit tests for seniority level mapping engine and ambiguity tracking (Task T3.09).

Governed by:
- Rule R-UQ-01: Uncertainty quantified with confidence and soft labels.
- Rule R-MD-07: Unmapped and ambiguous cases are counted, not forced.
"""

from __future__ import annotations

import polars as pl
import pytest

from compintel.normalization.levels import (
    LevelAmbiguityAudit,
    map_level,
    normalize_levels_df,
)
from compintel.schema.enums import SeniorityLevel


@pytest.mark.unit
def test_map_level_explicit_codes() -> None:
    """Verify explicit company level codes map directly with high confidence."""
    res_l4 = map_level(explicit_level="L4")
    assert res_l4.seniority == SeniorityLevel.SR
    assert res_l4.confidence >= 0.95
    assert res_l4.mapping_method == "explicit_code"
    assert not res_l4.is_ambiguous
    assert not res_l4.is_unmapped

    res_e5 = map_level(explicit_level="E5")
    assert res_e5.seniority == SeniorityLevel.STAFF
    assert res_e5.confidence >= 0.95

    res_mts2 = map_level(explicit_level="MTS II")
    assert res_mts2.seniority == SeniorityLevel.MID
    assert res_mts2.confidence >= 0.95

    res_l2 = map_level(explicit_level="L2")
    assert res_l2.seniority == SeniorityLevel.JR
    assert res_l2.confidence >= 0.95

    res_l6 = map_level(explicit_level="L6")
    assert res_l6.seniority == SeniorityLevel.PRINCIPAL
    assert res_l6.confidence >= 0.95


@pytest.mark.unit
def test_map_level_title_tokens() -> None:
    """Verify title seniority keywords map accurately when explicit level is absent."""
    res_sr = map_level(raw_title="Senior Backend Engineer")
    assert res_sr.seniority == SeniorityLevel.SR
    assert res_sr.confidence == 0.90
    assert res_sr.mapping_method == "title_token"
    assert not res_sr.is_ambiguous

    res_staff = map_level(raw_title="Staff Data Scientist")
    assert res_staff.seniority == SeniorityLevel.STAFF
    assert res_staff.confidence == 0.90

    res_jr = map_level(raw_title="Junior QA Engineer")
    assert res_jr.seniority == SeniorityLevel.JR
    assert res_jr.confidence == 0.90

    res_sde2 = map_level(raw_title="SDE II")
    assert res_sde2.seniority == SeniorityLevel.MID
    assert res_sde2.confidence == 0.90

    res_princ = map_level(raw_title="Distinguished Engineer")
    assert res_princ.seniority == SeniorityLevel.PRINCIPAL
    assert res_princ.confidence == 0.95


@pytest.mark.unit
def test_map_level_ambiguous_lead_title() -> None:
    """Verify ambiguous title tokens (e.g. Lead) are flagged as ambiguous with soft labels."""
    res = map_level(raw_title="Tech Lead")
    assert res.seniority == SeniorityLevel.SR
    assert res.is_ambiguous
    assert res.confidence == 0.75
    # Soft labels reflect spread between Senior and Staff
    assert res.soft_labels["SR"] == 0.60
    assert res.soft_labels["STAFF"] == 0.35
    assert pytest.approx(sum(res.soft_labels.values()), 0.01) == 1.0


@pytest.mark.unit
def test_map_level_title_yoe_concordance_and_discordance() -> None:
    """Verify concordance preserves confidence, while discordance increases ambiguity."""
    # Concordant: Senior with 8 years experience
    res_conc = map_level(raw_title="Senior Software Engineer", years_experience=8.0)
    assert res_conc.seniority == SeniorityLevel.SR
    assert res_conc.confidence == 0.90
    assert not res_conc.is_ambiguous

    # Discordant: Senior title with 0.5 years experience
    res_disc = map_level(raw_title="Senior Software Engineer", years_experience=0.5)
    assert res_disc.seniority == SeniorityLevel.SR
    assert res_disc.is_ambiguous
    assert res_disc.confidence < 0.90


@pytest.mark.unit
def test_map_level_yoe_when_title_lacks_level() -> None:
    """Verify smooth YoE bands are used when title lacks seniority tokens."""
    res_jr = map_level(raw_title="Software Engineer", years_experience=1.0)
    assert res_jr.seniority == SeniorityLevel.JR
    assert res_jr.mapping_method == "experience_heuristic"
    assert not res_jr.is_ambiguous

    res_mid = map_level(raw_title="Data Scientist", years_experience=4.0)
    assert res_mid.seniority == SeniorityLevel.MID
    assert not res_mid.is_ambiguous

    # Borderline YoE (6.0 yrs): flagged as ambiguous
    res_border = map_level(raw_title="Data Engineer", years_experience=6.0)
    assert res_border.seniority == SeniorityLevel.MID
    assert res_border.is_ambiguous
    assert res_border.soft_labels["MID"] == 0.55
    assert res_border.soft_labels["SR"] == 0.40

    res_sr = map_level(raw_title="Frontend Engineer", years_experience=9.0)
    assert res_sr.seniority == SeniorityLevel.SR
    assert not res_sr.is_ambiguous

    res_staff = map_level(raw_title="DevOps Engineer", years_experience=14.0)
    assert res_staff.seniority == SeniorityLevel.STAFF

    res_princ = map_level(raw_title="Systems Engineer", years_experience=18.0)
    assert res_princ.seniority == SeniorityLevel.PRINCIPAL


@pytest.mark.unit
def test_map_level_unmapped_counted_not_forced() -> None:
    """Rule R-MD-07 & T3.09: Unmapped cases must NOT be forced into arbitrary seniorities."""
    res = map_level(raw_title="Software Engineer", years_experience=None, explicit_level=None)

    assert res.seniority == SeniorityLevel.OTHER
    assert res.confidence == 0.0
    assert res.is_unmapped
    assert res.is_ambiguous
    assert res.mapping_method == "unmapped"
    assert pytest.approx(sum(res.soft_labels.values()), 0.01) == 1.0

    res_none = map_level(raw_title=None, years_experience=None)
    assert res_none.is_unmapped
    assert res_none.confidence == 0.0


@pytest.mark.unit
def test_level_ambiguity_audit_counter() -> None:
    """Verify LevelAmbiguityAudit accurately computes rates and tracks counts."""
    audit = LevelAmbiguityAudit()

    r1 = map_level(raw_title="Senior Software Engineer", years_experience=7.0)  # Clean
    r2 = map_level(raw_title="Tech Lead")  # Ambiguous
    r3 = map_level(raw_title="Software Engineer", years_experience=None)  # Unmapped

    audit.record_result(r1)
    audit.record_result(r2)
    audit.record_result(r3)

    assert audit.total_records == 3
    assert audit.clean_mapped_count == 1
    assert audit.ambiguous_count == 1
    assert audit.unmapped_count == 1
    assert pytest.approx(audit.ambiguity_rate, 0.01) == 1 / 3
    assert pytest.approx(audit.unmapped_rate, 0.01) == 1 / 3

    d = audit.to_dict()
    assert d["total_records"] == 3
    assert "seniority_counts" in d


@pytest.mark.unit
def test_normalize_levels_df() -> None:
    """Verify batch Polars DataFrame level normalization and audit generation."""
    df = pl.DataFrame(
        {
            "raw_title": [
                "Senior Software Engineer",
                "Tech Lead",
                "Software Engineer",
                "Data Scientist",
            ],
            "explicit_level": [None, None, "L3", None],
            "years_experience": [7.0, 8.0, None, None],
        }
    )

    out_df, audit = normalize_levels_df(
        df, title_column="raw_title", explicit_level_column="explicit_level"
    )

    assert out_df.height == 4
    assert "seniority" in out_df.columns
    assert "level_confidence" in out_df.columns
    assert "is_level_ambiguous" in out_df.columns
    assert "is_level_unmapped" in out_df.columns
    assert "level_mapping_version" in out_df.columns

    seniorities = out_df["seniority"].to_list()
    assert seniorities == ["SR", "SR", "MID", "OTHER"]

    # Audit counts: 2 clean (Senior with YoE, L3), 1 ambiguous (Tech Lead), 1 unmapped
    assert audit.total_records == 4
    assert audit.clean_mapped_count == 2
    assert audit.ambiguous_count == 1
    assert audit.unmapped_count == 1


@pytest.mark.unit
def test_normalize_levels_df_empty() -> None:
    """Verify empty DataFrame returns cleanly with zero audit counts."""
    df = pl.DataFrame({"raw_title": pl.Series([], dtype=pl.String)})
    out_df, audit = normalize_levels_df(df)
    assert out_df.height == 0
    assert audit.total_records == 0
    assert "seniority" in out_df.columns
