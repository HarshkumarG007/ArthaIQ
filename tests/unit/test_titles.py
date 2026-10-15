"""Unit tests for taxonomy and title normalization engine (Rule R-MD-09, R-SC-07)."""

from __future__ import annotations

import polars as pl
import pytest

from compintel.normalization.titles import (
    DEFAULT_TAXONOMY_VERSION,
    TitleMappingResult,
    normalize_title,
    normalize_titles_df,
    sanitize_title,
)
from compintel.schema.enums import RoleFamily


@pytest.mark.unit
def test_sanitize_title_variants() -> None:
    """Verify title sanitization cleans casing, punctuation, acronyms, and prefixes."""
    assert sanitize_title("") == ""
    assert sanitize_title("   ") == ""
    assert sanitize_title("SOFTWARE ENGINEER") == "software engineer"
    assert sanitize_title("Sr. SWE II") == "software engineer"
    assert sanitize_title("Junior ML Dev") == "machine learning developer"
    assert sanitize_title("Staff Data Engineer (ETL)") == "data engineer etl"
    assert sanitize_title("Lead SRE / DevOps!") == "site reliability engineer devops"
    assert sanitize_title("Principal SDET") == "software development engineer in test"


@pytest.mark.unit
def test_sanitize_title_unicode() -> None:
    """Verify sanitize_title handles unicode accents and non-ASCII gracefully."""
    cleaned = sanitize_title("Ingénieur Système")
    assert "ingenieur systeme" in cleaned


@pytest.mark.unit
def test_exact_match_software_engineer() -> None:
    """Verify exact matching for standard SWE titles with confidence = 1.0."""
    res = normalize_title("Software Engineer")
    assert isinstance(res, TitleMappingResult)
    assert res.canonical_title == "Software Engineer"
    assert res.role_family == RoleFamily.SWE
    assert res.confidence == 1.0
    assert res.match_method == "exact"
    assert res.soc_code == "15-1252.00"
    assert res.taxonomy_version == DEFAULT_TAXONOMY_VERSION


@pytest.mark.unit
def test_exact_match_data_scientist() -> None:
    """Verify exact matching for Data Scientist in MLAI family."""
    res = normalize_title("Data Scientist")
    assert res.canonical_title == "Data Scientist"
    assert res.role_family == RoleFamily.MLAI
    assert res.confidence == 1.0
    assert res.match_method == "exact"
    assert res.soc_code == "15-2051.00"


@pytest.mark.unit
def test_exact_match_data_engineer() -> None:
    """Verify exact matching for Data Engineer in DATA family."""
    res = normalize_title("Data Engineer")
    assert res.canonical_title == "Data Engineer"
    assert res.role_family == RoleFamily.DATA
    assert res.confidence == 1.0
    assert res.match_method == "exact"
    assert res.soc_code == "15-1243.00"


@pytest.mark.unit
def test_alias_matching_acronyms() -> None:
    """Verify acronyms map directly to canonical titles with exact match confidence."""
    res_swe = normalize_title("SWE")
    assert res_swe.canonical_title == "Software Engineer"
    assert res_swe.role_family == RoleFamily.SWE
    assert res_swe.confidence == 1.0

    res_ml = normalize_title("ML Engineer")
    assert res_ml.canonical_title == "Machine Learning Engineer"
    assert res_ml.role_family == RoleFamily.MLAI
    assert res_ml.confidence == 1.0


@pytest.mark.unit
def test_regex_matching_complex_titles() -> None:
    """Verify complex titles match prioritized regex rules."""
    res_genai = normalize_title("Senior Generative AI Specialist")
    assert res_genai.canonical_title == "AI Engineer"
    assert res_genai.role_family == RoleFamily.MLAI
    assert res_genai.confidence == 0.95
    assert res_genai.match_method == "regex"

    res_pipe = normalize_title("Staff Big Data Pipeline Architect")
    assert res_pipe.canonical_title == "Data Engineer"
    assert res_pipe.role_family == RoleFamily.DATA
    assert res_pipe.confidence == 0.95
    assert res_pipe.match_method == "regex"

    res_sre = normalize_title("Site Reliability & Cloud Infrastructure Lead")
    assert res_sre.canonical_title == "DevOps Engineer"
    assert res_sre.role_family == RoleFamily.SWE
    assert res_sre.confidence == 0.92
    assert res_sre.match_method == "regex"

    res_qa = normalize_title("Lead Test Automation Specialist")
    assert res_qa.canonical_title == "QA Engineer"
    assert res_qa.role_family == RoleFamily.SWE
    assert res_qa.confidence == 0.92
    assert res_qa.match_method == "regex"


@pytest.mark.unit
def test_management_and_other_roles() -> None:
    """Verify non-tech and management roles map to RoleFamily.OTHER."""
    res_em = normalize_title("VP of Engineering")
    assert res_em.role_family == RoleFamily.OTHER
    assert res_em.canonical_title == "Engineering Manager"

    res_pm = normalize_title("Senior Technical Product Manager")
    assert res_pm.role_family == RoleFamily.OTHER
    assert res_pm.canonical_title == "Product Manager"

    res_hr = normalize_title("Talent Acquisition Partner")
    assert res_hr.role_family == RoleFamily.OTHER
    assert res_hr.canonical_title == "Other / Non-Tech"


@pytest.mark.unit
def test_fuzzy_matching_typos() -> None:
    """Verify rapidfuzz handles minor typos with scaled confidence."""
    res = normalize_title("Softwre Engineeer")
    assert res.canonical_title == "Software Engineer"
    assert res.role_family == RoleFamily.SWE
    assert res.match_method == "fuzzy"
    assert 0.60 <= res.confidence < 1.0


@pytest.mark.unit
def test_empty_or_unknown_fallback() -> None:
    """Verify empty or unrecognized titles fall back safely with zero confidence."""
    res_none = normalize_title(None)
    assert res_none.role_family == RoleFamily.OTHER
    assert res_none.canonical_title == "Other / Unclassified"
    assert res_none.confidence == 0.0
    assert res_none.match_method == "fallback"

    res_empty = normalize_title("   ")
    assert res_empty.role_family == RoleFamily.OTHER
    assert res_empty.confidence == 0.0

    res_gibberish = normalize_title("xyz123 completely unknown title token 999")
    assert res_gibberish.role_family == RoleFamily.OTHER
    assert res_gibberish.canonical_title == "Other / Unclassified"
    assert res_gibberish.confidence == 0.0
    assert res_gibberish.match_method == "fallback"


@pytest.mark.unit
def test_title_mapping_result_to_dict() -> None:
    """Verify TitleMappingResult converts cleanly to dictionary representation."""
    res = normalize_title("Senior Software Engineer", taxonomy_version="v0.2.0")
    d = res.to_dict()
    assert d["raw_title"] == "Senior Software Engineer"
    assert d["canonical_title"] == "Software Engineer"
    assert d["role_family"] == "SWE"
    assert d["confidence"] == 1.0
    assert d["taxonomy_version"] == "v0.2.0"
    assert d["match_method"] == "exact"


@pytest.mark.unit
def test_normalize_titles_df() -> None:
    """Verify batch normalization over Polars DataFrame."""
    df = pl.DataFrame(
        {
            "raw_title": [
                "Software Engineer",
                "Senior ML Engineer",
                "Data Analyst",
                "Project Manager",
                "Unknown Gibberish 404",
            ]
        }
    )
    result_df = normalize_titles_df(df, title_column="raw_title", taxonomy_version="v0.1.0")

    assert result_df.height == 5
    assert "canonical_title" in result_df.columns
    assert "role_family" in result_df.columns
    assert "title_confidence" in result_df.columns
    assert "taxonomy_version" in result_df.columns
    assert "soc_code" in result_df.columns

    # Verify every record records confidence and taxonomy_version
    confidences = result_df["title_confidence"].to_list()
    tax_versions = result_df["taxonomy_version"].to_list()
    role_families = result_df["role_family"].to_list()

    assert all(0.0 <= c <= 1.0 for c in confidences)
    assert all(t == "v0.1.0" for t in tax_versions)
    assert role_families == ["SWE", "MLAI", "DATA", "OTHER", "OTHER"]


@pytest.mark.unit
def test_normalize_titles_df_empty() -> None:
    """Verify normalize_titles_df handles empty DataFrame without error."""
    df = pl.DataFrame({"raw_title": pl.Series([], dtype=pl.String)})
    result_df = normalize_titles_df(df, title_column="raw_title")
    assert result_df.height == 0
    assert "canonical_title" in result_df.columns
    assert "role_family" in result_df.columns
    assert "title_confidence" in result_df.columns
    assert "taxonomy_version" in result_df.columns
