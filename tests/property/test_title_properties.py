"""Property-based tests for title and taxonomy normalization (Rule R-MD-09, R-SC-07).

Verifies invariants across title normalization:
1. Determinism: Same input always yields identical mapping result.
2. Confidence bounds: Confidence is strictly in [0.0, 1.0].
3. Taxonomy tracking: taxonomy_version is recorded on every result.
4. Robustness: Never raises unhandled exceptions on arbitrary unicode strings.
5. Case invariance: Lower/Upper/Title case yields identical role family.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
import pytest

from compintel.normalization.titles import (
    DEFAULT_TAXONOMY_VERSION,
    TitleMappingResult,
    normalize_title,
    sanitize_title,
)
from compintel.schema.enums import RoleFamily

KNOWN_TECH_TITLES = [
    "Software Engineer",
    "Backend Developer",
    "Frontend Engineer",
    "Full Stack Engineer",
    "Data Scientist",
    "Data Engineer",
    "Machine Learning Engineer",
    "DevOps Engineer",
    "QA Engineer",
    "Security Engineer",
]


@pytest.mark.property
@given(raw_text=st.text(max_size=200))
def test_title_normalization_robustness_and_invariants(raw_text: str) -> None:
    """Invariant: normalize_title never crashes, records taxonomy_version, and bounds confidence."""
    res = normalize_title(raw_text, taxonomy_version="v0.1.0")

    assert isinstance(res, TitleMappingResult)
    assert 0.0 <= res.confidence <= 1.0
    assert res.taxonomy_version == "v0.1.0"
    assert isinstance(res.role_family, RoleFamily)
    assert isinstance(res.canonical_title, str)
    assert len(res.canonical_title) > 0


@pytest.mark.property
@given(raw_text=st.text(max_size=100))
def test_title_normalization_determinism(raw_text: str) -> None:
    """Invariant: normalize_title is strictly deterministic for identical inputs."""
    res1 = normalize_title(raw_text)
    res2 = normalize_title(raw_text)

    assert res1.canonical_title == res2.canonical_title
    assert res1.role_family == res2.role_family
    assert res1.confidence == res2.confidence
    assert res1.match_method == res2.match_method
    assert res1.soc_code == res2.soc_code


@pytest.mark.property
@given(title=st.sampled_from(KNOWN_TECH_TITLES), casing=st.sampled_from(["lower", "upper", "title"]))
def test_title_case_invariance(title: str, casing: str) -> None:
    """Invariant: title casing does not alter canonical role family or title."""
    if casing == "lower":
        cased_title = title.lower()
    elif casing == "upper":
        cased_title = title.upper()
    else:
        cased_title = title.title()

    base_res = normalize_title(title)
    cased_res = normalize_title(cased_title)

    assert cased_res.role_family == base_res.role_family
    assert cased_res.canonical_title == base_res.canonical_title
    assert cased_res.confidence == base_res.confidence


@pytest.mark.property
@given(
    title=st.sampled_from(KNOWN_TECH_TITLES),
    prefix=st.sampled_from(["Senior", "Junior", "Lead", "Staff", "Principal", "Associate"]),
)
def test_title_level_prefix_invariance(title: str, prefix: str) -> None:
    """Invariant: Level prefix prepended to standard tech title preserves role family."""
    prefixed_title = f"{prefix} {title}"
    base_res = normalize_title(title)
    prefixed_res = normalize_title(prefixed_title)

    assert prefixed_res.role_family == base_res.role_family
    assert prefixed_res.canonical_title == base_res.canonical_title
