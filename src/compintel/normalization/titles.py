"""Taxonomy and occupational job title normalization engine (Rule R-MD-09, R-SC-07).

Provides rule-based, deterministic title mapping with confidence scoring and
taxonomy version tracking across core Indian tech role families (SWE, DATA, MLAI, OTHER).
Strictly free of LLM dependencies in accordance with Rules R-MD-09 and R-SC-07.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
import unicodedata

import polars as pl
from rapidfuzz import fuzz

from compintel.schema.enums import RoleFamily

DEFAULT_TAXONOMY_VERSION: str = "v0.1.0"


@dataclass(frozen=True)
class TitleMappingResult:
    """Standardized result of occupational title normalization."""

    raw_title: str
    clean_title: str
    canonical_title: str
    role_family: RoleFamily
    confidence: float
    match_method: str
    taxonomy_version: str
    soc_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "raw_title": self.raw_title,
            "clean_title": self.clean_title,
            "canonical_title": self.canonical_title,
            "role_family": self.role_family.value,
            "confidence": self.confidence,
            "match_method": self.match_method,
            "taxonomy_version": self.taxonomy_version,
            "soc_code": self.soc_code,
        }


# Canonical Reference Catalog (O*NET 29.0 & Tech Occupational Ontology)
# Key: normalized title, Value: (Canonical Title, RoleFamily, SOC Code)
EXACT_MAPPINGS: dict[str, tuple[str, RoleFamily, str | None]] = {
    # Software Engineering (SWE)
    "software engineer": ("Software Engineer", RoleFamily.SWE, "15-1252.00"),
    "software developer": ("Software Engineer", RoleFamily.SWE, "15-1252.00"),
    "software development engineer": ("Software Engineer", RoleFamily.SWE, "15-1252.00"),
    "programmer": ("Software Engineer", RoleFamily.SWE, "15-1251.00"),
    "computer programmer": ("Software Engineer", RoleFamily.SWE, "15-1251.00"),
    "backend engineer": ("Backend Engineer", RoleFamily.SWE, "15-1252.00"),
    "backend developer": ("Backend Engineer", RoleFamily.SWE, "15-1252.00"),
    "frontend engineer": ("Frontend Engineer", RoleFamily.SWE, "15-1252.00"),
    "frontend developer": ("Frontend Engineer", RoleFamily.SWE, "15-1252.00"),
    "full stack engineer": ("Full Stack Engineer", RoleFamily.SWE, "15-1252.00"),
    "full stack developer": ("Full Stack Engineer", RoleFamily.SWE, "15-1252.00"),
    "fullstack engineer": ("Full Stack Engineer", RoleFamily.SWE, "15-1252.00"),
    "fullstack developer": ("Full Stack Engineer", RoleFamily.SWE, "15-1252.00"),
    "mobile engineer": ("Mobile Engineer", RoleFamily.SWE, "15-1252.00"),
    "mobile developer": ("Mobile Engineer", RoleFamily.SWE, "15-1252.00"),
    "ios engineer": ("Mobile Engineer", RoleFamily.SWE, "15-1252.00"),
    "ios developer": ("Mobile Engineer", RoleFamily.SWE, "15-1252.00"),
    "android engineer": ("Mobile Engineer", RoleFamily.SWE, "15-1252.00"),
    "android developer": ("Mobile Engineer", RoleFamily.SWE, "15-1252.00"),
    "devops engineer": ("DevOps Engineer", RoleFamily.SWE, "15-1244.00"),
    "site reliability engineer": ("DevOps Engineer", RoleFamily.SWE, "15-1244.00"),
    "cloud engineer": ("DevOps Engineer", RoleFamily.SWE, "15-1244.00"),
    "platform engineer": ("DevOps Engineer", RoleFamily.SWE, "15-1244.00"),
    "infrastructure engineer": ("DevOps Engineer", RoleFamily.SWE, "15-1244.00"),
    "systems engineer": ("Systems Engineer", RoleFamily.SWE, "15-1251.00"),
    "embedded engineer": ("Systems Engineer", RoleFamily.SWE, "15-1251.00"),
    "firmware engineer": ("Systems Engineer", RoleFamily.SWE, "15-1251.00"),
    "qa engineer": ("QA Engineer", RoleFamily.SWE, "15-1253.00"),
    "quality assurance engineer": ("QA Engineer", RoleFamily.SWE, "15-1253.00"),
    "software development engineer in test": ("QA Engineer", RoleFamily.SWE, "15-1253.00"),
    "test automation engineer": ("QA Engineer", RoleFamily.SWE, "15-1253.00"),
    "security engineer": ("Security Engineer", RoleFamily.SWE, "15-1252.00"),
    "application security engineer": ("Security Engineer", RoleFamily.SWE, "15-1252.00"),
    "cyber security engineer": ("Security Engineer", RoleFamily.SWE, "15-1252.00"),
    # Data Science, Engineering & Analytics (DATA)
    "data engineer": ("Data Engineer", RoleFamily.DATA, "15-1243.00"),
    "data analytics engineer": ("Analytics Engineer", RoleFamily.DATA, "15-1243.00"),
    "analytics engineer": ("Analytics Engineer", RoleFamily.DATA, "15-1243.00"),
    "data analyst": ("Data Analyst", RoleFamily.DATA, "15-2051.00"),
    "business intelligence analyst": ("Business Intelligence Analyst", RoleFamily.DATA, "15-2051.00"),
    "business intelligence engineer": ("Business Intelligence Analyst", RoleFamily.DATA, "15-2051.00"),
    "bi analyst": ("Business Intelligence Analyst", RoleFamily.DATA, "15-2051.00"),
    "bi developer": ("Business Intelligence Analyst", RoleFamily.DATA, "15-2051.00"),
    "database administrator": ("Database Administrator", RoleFamily.DATA, "15-1244.00"),
    "database architect": ("Data Engineer", RoleFamily.DATA, "15-1243.00"),
    "data architect": ("Data Engineer", RoleFamily.DATA, "15-1243.00"),
    # Machine Learning & AI (MLAI)
    "machine learning engineer": ("Machine Learning Engineer", RoleFamily.MLAI, "15-1252.00"),
    "ml engineer": ("Machine Learning Engineer", RoleFamily.MLAI, "15-1252.00"),
    "deep learning engineer": ("Machine Learning Engineer", RoleFamily.MLAI, "15-1252.00"),
    "data scientist": ("Data Scientist", RoleFamily.MLAI, "15-2051.00"),
    "ai engineer": ("AI Engineer", RoleFamily.MLAI, "15-1252.00"),
    "artificial intelligence engineer": ("AI Engineer", RoleFamily.MLAI, "15-1252.00"),
    "research scientist": ("Research Scientist", RoleFamily.MLAI, "15-2051.00"),
    "applied scientist": ("Data Scientist", RoleFamily.MLAI, "15-2051.00"),
    "nlp engineer": ("NLP Engineer", RoleFamily.MLAI, "15-1252.00"),
    "computer vision engineer": ("Computer Vision Engineer", RoleFamily.MLAI, "15-1252.00"),
    "mlops engineer": ("MLOps Engineer", RoleFamily.MLAI, "15-1244.00"),
    # Out of Scope / Adjacent / Management (OTHER)
    "engineering manager": ("Engineering Manager", RoleFamily.OTHER, None),
    "product manager": ("Product Manager", RoleFamily.OTHER, None),
    "technical program manager": ("Technical Program Manager", RoleFamily.OTHER, None),
    "project manager": ("Project Manager", RoleFamily.OTHER, None),
    "scrum master": ("Scrum Master", RoleFamily.OTHER, None),
    "business analyst": ("Business Analyst", RoleFamily.OTHER, None),
}

# Regex Rules for prioritized pattern extraction:
# (pattern, canonical_title, role_family, soc_code, confidence)
REGEX_RULES: list[tuple[re.Pattern[str], str, RoleFamily, str | None, float]] = [
    # 1. Machine Learning & AI (Priority over generic SWE/DATA)
    (
        re.compile(r"\b(machine\s+learning|ml|deep\s+learning)\s+(engineer|developer|specialist)\b"),
        "Machine Learning Engineer",
        RoleFamily.MLAI,
        "15-1252.00",
        0.95,
    ),
    (
        re.compile(r"\b(data\s+scientist|data\s+science|applied\s+scientist)\b"),
        "Data Scientist",
        RoleFamily.MLAI,
        "15-2051.00",
        0.95,
    ),
    (
        re.compile(
            r"\b(ai|artificial\s+intelligence|generative\s+ai|llm)\s+"
            r"(engineer|developer|scientist|specialist|architect|researcher)\b"
        ),
        "AI Engineer",
        RoleFamily.MLAI,
        "15-1252.00",
        0.95,
    ),
    (
        re.compile(r"\b(nlp|natural\s+language\s+processing)\s+(engineer|scientist|specialist)\b"),
        "NLP Engineer",
        RoleFamily.MLAI,
        "15-1252.00",
        0.95,
    ),
    (
        re.compile(r"\b(computer\s+vision|cv)\s+(engineer|scientist|specialist)\b"),
        "Computer Vision Engineer",
        RoleFamily.MLAI,
        "15-1252.00",
        0.95,
    ),
    (
        re.compile(r"\b(mlops|ml\s+platform)\s+(engineer|architect)\b"),
        "MLOps Engineer",
        RoleFamily.MLAI,
        "15-1244.00",
        0.95,
    ),
    # 2. Data Engineering & Analytics
    (
        re.compile(r"\b(data|etl|big\s+data|pipeline|warehouse)\s+(engineer|developer|architect)\b"),
        "Data Engineer",
        RoleFamily.DATA,
        "15-1243.00",
        0.95,
    ),
    (
        re.compile(r"\banalytics\s+engineer\b"),
        "Analytics Engineer",
        RoleFamily.DATA,
        "15-1243.00",
        0.95,
    ),
    (
        re.compile(r"\b(data|analytics|bi|business\s+intelligence)\s+(analyst|specialist)\b"),
        "Data Analyst",
        RoleFamily.DATA,
        "15-2051.00",
        0.90,
    ),
    (
        re.compile(r"\b(database\s+administrator|dba)\b"),
        "Database Administrator",
        RoleFamily.DATA,
        "15-1244.00",
        0.95,
    ),
    # 3. Specialized SWE Sub-disciplines
    (
        re.compile(r"\b(qa|quality\s+assurance|sdet|test\s+automation|software\s+test)\b"),
        "QA Engineer",
        RoleFamily.SWE,
        "15-1253.00",
        0.92,
    ),
    (
        re.compile(
            r"\b(devops|sre|site\s+reliability)\b|"
            r"\b(cloud|platform|infrastructure)\s+(engineer|architect|specialist|lead|developer)\b|"
            r"\b(cloud\s+infrastructure|infrastructure\s+cloud)\b"
        ),
        "DevOps Engineer",
        RoleFamily.SWE,
        "15-1244.00",
        0.92,
    ),
    (
        re.compile(r"\b(security|infosec|appsec|cybersecurity)\s+(engineer|analyst|specialist)\b"),
        "Security Engineer",
        RoleFamily.SWE,
        "15-1252.00",
        0.92,
    ),
    (
        re.compile(r"\b(ios|android|mobile|flutter|react\s+native)\s+(engineer|developer)\b"),
        "Mobile Engineer",
        RoleFamily.SWE,
        "15-1252.00",
        0.92,
    ),
    (
        re.compile(r"\b(frontend|front-end|front\s+end|ui|web)\s+(engineer|developer)\b"),
        "Frontend Engineer",
        RoleFamily.SWE,
        "15-1252.00",
        0.92,
    ),
    (
        re.compile(r"\b(backend|back-end|back\s+end|api|server|microservices)\s+(engineer|developer)\b"),
        "Backend Engineer",
        RoleFamily.SWE,
        "15-1252.00",
        0.92,
    ),
    (
        re.compile(r"\b(fullstack|full-stack|full\s+stack)\s+(engineer|developer)\b"),
        "Full Stack Engineer",
        RoleFamily.SWE,
        "15-1252.00",
        0.92,
    ),
    (
        re.compile(r"\b(embedded|firmware|kernel|systems|hardware)\s+(engineer|developer)\b"),
        "Systems Engineer",
        RoleFamily.SWE,
        "15-1251.00",
        0.90,
    ),
    # 4. General Software Engineering
    (
        re.compile(r"\b(software|sde|swe|application|applications|system)\s+(engineer|developer|programmer)\b"),
        "Software Engineer",
        RoleFamily.SWE,
        "15-1252.00",
        0.90,
    ),
    (
        re.compile(r"\b(programmer|coder|software\s+architect|technical\s+architect|solutions\s+architect)\b"),
        "Software Engineer",
        RoleFamily.SWE,
        "15-1252.00",
        0.85,
    ),
    # 5. Management & Out-of-Scope Roles (OTHER)
    (
        re.compile(r"\b(engineering\s+manager|engineering\s+lead|tech\s+lead|cto|vp\s+of\s+engineering|director\s+of\s+engineering)\b"),
        "Engineering Manager",
        RoleFamily.OTHER,
        None,
        0.90,
    ),
    (
        re.compile(r"\b(product\s+manager|technical\s+product\s+manager|product\s+owner)\b"),
        "Product Manager",
        RoleFamily.OTHER,
        None,
        0.90,
    ),
    (
        re.compile(r"\b(program\s+manager|project\s+manager|scrum\s+master|delivery\s+manager)\b"),
        "Project Manager",
        RoleFamily.OTHER,
        None,
        0.88,
    ),
    (
        re.compile(r"\b(hr|human\s+resources|recruiter|talent|sales|marketing|finance|accountant|operations|legal)\b"),
        "Other / Non-Tech",
        RoleFamily.OTHER,
        None,
        0.85,
    ),
]

# Prefixes and suffixes to strip during title sanitization
LEVEL_PREFIXES_REGEX = re.compile(
    r"\b(senior|sr\.?|junior|jr\.?|associate|lead|principal|staff|distinguished|intern|trainee|"
    r"graduate|fellow|consultant|chief|head\s+of|vice\s+president|vp|director|manager|"
    r"level\s+[1-5]|l[1-5]|e[1-5]|ic[1-6]|mts|smts|pmts|i|ii|iii|iv|v|vi|[1-9])\b",
    re.IGNORECASE,
)

COMMON_ACRONYMS: dict[str, str] = {
    r"\bswe\b": "software engineer",
    r"\bsde\b": "software development engineer",
    r"\bdev\b": "developer",
    r"\beng\b": "engineer",
    r"\bengr\b": "engineer",
    r"\bml\b": "machine learning",
    r"\bds\b": "data scientist",
    r"\bde\b": "data engineer",
    r"\bsdet\b": "software development engineer in test",
    r"\bqa\b": "quality assurance",
    r"\bsre\b": "site reliability engineer",
    r"\bbi\b": "business intelligence",
    r"\bai\b": "artificial intelligence",
    r"\bdl\b": "deep learning",
}


def sanitize_title(title: str) -> str:
    """Normalize raw title string for consistent deterministic rule matching.

    Performs unicode normalization, lowercase conversion, punctuation removal,
    acronym expansion, and level prefix stripping (while preserving role nouns).
    """
    if not title or not title.strip():
        return ""

    # Normalize unicode accents and lower
    clean_chars = [
        c for c in unicodedata.normalize("NFKD", title) if unicodedata.category(c) != "Mn"
    ]
    normalized = "".join(clean_chars).lower()

    # Expand common acronyms
    for pattern, replacement in COMMON_ACRONYMS.items():
        normalized = re.sub(pattern, replacement, normalized)

    # Replace punctuation characters with whitespace, keeping alphanumeric and hyphens
    normalized = re.sub(r"[^\w\s-]", " ", normalized)
    normalized = re.sub(r"[-_]+", " ", normalized)

    # Strip level prefixes if resulting string still contains occupational nouns
    stripped = LEVEL_PREFIXES_REGEX.sub(" ", normalized)
    stripped = re.sub(r"\s+", " ", stripped).strip()

    # If stripping removed everything (e.g. title was just "Senior" or "Lead"), keep original
    if stripped and len(stripped) >= 3:
        return stripped

    return re.sub(r"\s+", " ", normalized).strip()


def normalize_title(
    raw_title: str | None,
    taxonomy_version: str = DEFAULT_TAXONOMY_VERSION,
    min_fuzzy_score: float = 75.0,
) -> TitleMappingResult:
    """Normalize a raw job title into a canonical title and role family with confidence.

    Follows a multi-tier rule-based hierarchy:
    1. Direct dictionary match on sanitized string (confidence = 1.0).
    2. Ordered regex pattern rules (confidence = 0.85 to 0.95).
    3. Token-set fuzzy matching with rapidfuzz (confidence = scaled similarity).
    4. Safe fallback to RoleFamily.OTHER (confidence = 0.0).

    Args:
        raw_title: The original raw title string from the source record.
        taxonomy_version: Semantic version of the reference taxonomy.
        min_fuzzy_score: Minimum token-set similarity threshold (0-100) for fuzzy match.

    Returns:
        TitleMappingResult with canonical title, role family, confidence, and taxonomy version.
    """
    original = "" if raw_title is None else str(raw_title).strip()
    if not original:
        return TitleMappingResult(
            raw_title="",
            clean_title="",
            canonical_title="Other / Unclassified",
            role_family=RoleFamily.OTHER,
            confidence=0.0,
            match_method="fallback",
            taxonomy_version=taxonomy_version,
            soc_code=None,
        )

    clean = sanitize_title(original)

    # 1. Exact / Alias Match
    if clean in EXACT_MAPPINGS:
        canonical, family, soc = EXACT_MAPPINGS[clean]
        return TitleMappingResult(
            raw_title=original,
            clean_title=clean,
            canonical_title=canonical,
            role_family=family,
            confidence=1.0,
            match_method="exact",
            taxonomy_version=taxonomy_version,
            soc_code=soc,
        )

    # Also check un-stripped clean title (in case level prefix was integral)
    unstripped_clean = re.sub(r"[^\w\s]", " ", original.lower()).strip()
    unstripped_clean = re.sub(r"\s+", " ", unstripped_clean)
    if unstripped_clean in EXACT_MAPPINGS:
        canonical, family, soc = EXACT_MAPPINGS[unstripped_clean]
        return TitleMappingResult(
            raw_title=original,
            clean_title=clean,
            canonical_title=canonical,
            role_family=family,
            confidence=1.0,
            match_method="exact",
            taxonomy_version=taxonomy_version,
            soc_code=soc,
        )

    # 2. Prioritized Regex Rules
    search_target = f"{clean} {unstripped_clean}"
    for pattern, canonical, family, soc, conf in REGEX_RULES:
        if pattern.search(clean) or pattern.search(unstripped_clean):
            return TitleMappingResult(
                raw_title=original,
                clean_title=clean,
                canonical_title=canonical,
                role_family=family,
                confidence=conf,
                match_method="regex",
                taxonomy_version=taxonomy_version,
                soc_code=soc,
            )

    # 3. Fuzzy Match with RapidFuzz against Known Exact Keys
    best_match_key = None
    best_score = 0.0

    for candidate_key in EXACT_MAPPINGS:
        score = float(fuzz.token_set_ratio(clean, candidate_key))
        if score > best_score:
            best_score = score
            best_match_key = candidate_key

    if best_match_key is not None and best_score >= min_fuzzy_score:
        canonical, family, soc = EXACT_MAPPINGS[best_match_key]
        scaled_conf = round(float((best_score / 100.0) * 0.85), 3)
        return TitleMappingResult(
            raw_title=original,
            clean_title=clean,
            canonical_title=canonical,
            role_family=family,
            confidence=scaled_conf,
            match_method="fuzzy",
            taxonomy_version=taxonomy_version,
            soc_code=soc,
        )

    # 4. Safe Fallback
    return TitleMappingResult(
        raw_title=original,
        clean_title=clean,
        canonical_title="Other / Unclassified",
        role_family=RoleFamily.OTHER,
        confidence=0.0,
        match_method="fallback",
        taxonomy_version=taxonomy_version,
        soc_code=None,
    )


def normalize_titles_df(
    df: pl.DataFrame,
    title_column: str = "raw_title",
    taxonomy_version: str = DEFAULT_TAXONOMY_VERSION,
) -> pl.DataFrame:
    """Batch normalize job titles in a Polars DataFrame, appending standardized columns.

    Appends:
    - clean_title: Sanitized title string
    - canonical_title: Mapped standard title
    - role_family: Standard RoleFamily string (SWE, DATA, MLAI, OTHER)
    - title_confidence: Mapping confidence in [0.0, 1.0]
    - title_match_method: Method used ('exact', 'regex', 'fuzzy', 'fallback')
    - taxonomy_version: Version identifier recorded for every record (Rule T3.08)
    - soc_code: Standardized O*NET SOC code or null

    Args:
        df: Polars DataFrame containing the title column.
        title_column: Name of the column with raw job titles.
        taxonomy_version: Version string to attach to output.

    Returns:
        New Polars DataFrame with appended normalized title metadata columns.
    """
    if df.height == 0:
        return df.with_columns(
            pl.lit(None, dtype=pl.String).alias("clean_title"),
            pl.lit(None, dtype=pl.String).alias("canonical_title"),
            pl.lit(None, dtype=pl.String).alias("role_family"),
            pl.lit(None, dtype=pl.Float64).alias("title_confidence"),
            pl.lit(None, dtype=pl.String).alias("title_match_method"),
            pl.lit(None, dtype=pl.String).alias("taxonomy_version"),
            pl.lit(None, dtype=pl.String).alias("soc_code"),
        )

    raw_titles = df[title_column].to_list()
    results = [
        normalize_title(t, taxonomy_version=taxonomy_version) for t in raw_titles
    ]

    clean_titles = [r.clean_title for r in results]
    canonical_titles = [r.canonical_title for r in results]
    role_families = [r.role_family.value for r in results]
    confidences = [r.confidence for r in results]
    methods = [r.match_method for r in results]
    tax_versions = [r.taxonomy_version for r in results]
    soc_codes = [r.soc_code for r in results]

    return df.with_columns(
        pl.Series("clean_title", clean_titles, dtype=pl.String),
        pl.Series("canonical_title", canonical_titles, dtype=pl.String),
        pl.Series("role_family", role_families, dtype=pl.String),
        pl.Series("title_confidence", confidences, dtype=pl.Float64),
        pl.Series("title_match_method", methods, dtype=pl.String),
        pl.Series("taxonomy_version", tax_versions, dtype=pl.String),
        pl.Series("soc_code", soc_codes, dtype=pl.String),
    )
