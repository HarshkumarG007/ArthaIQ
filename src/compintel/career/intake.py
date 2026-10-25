"""Job description intake, sanitization, and deterministic competency extraction.

Enforces Rule R-CR-09 (Pasted Text is Untrusted Data), Rule R-SC-01 (OWASP ASVS),
Rule R-DA-07 (PII minimization), Rule R-CR-12 (Local-First ephemeral processing),
and Rule R-CR-15 (ADR-0010 Zero runtime LLMs on serving path).
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import TYPE_CHECKING

from rapidfuzz import fuzz

from compintel.career.schema import (
    CompetencyMatch,
    CompetencyNode,
    JobDescriptionIntakeResult,
)

if TYPE_CHECKING:
    from compintel.career.engine import TaxonomyPort

__all__ = [
    "CANONICAL_DATA_ALIASES",
    "MAX_INPUT_CHARS",
    "extract_competencies_from_text",
    "intake_job_description",
    "sanitize_untrusted_text",
]

# Hard length cap: 32 KB (~32,000 characters) per ADR-0012 and Rule R-CR-09
MAX_INPUT_CHARS: int = 32_000

# Bidirectional Unicode override characters that can obfuscate malicious text
_BIDI_CHARS_RE = re.compile(r"[\u202A-\u202E\u2066-\u2069]")

# Non-printable control characters (excluding standard whitespace \t, \n, \r)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]")

# HTML tags, script blocks, and style blocks
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|iframe|object|embed)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Markdown links and images with suspicious protocols (e.g. javascript:, data:)
_SUSPICIOUS_MD_LINK_RE = re.compile(
    r"\[([^\]]*)\]\((javascript:|data:|vbscript:)[^)]*\)",
    re.IGNORECASE,
)

# Prompt injection & system override signatures (OWASP LLM Top 10)
_PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directions)",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directions)",
    r"you\s+are\s+now\s+(a|an)\s+[a-z0-9_-]+",
    r"new\s+system\s+prompt\s*:",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"reset\s+all\s+(rules|instructions)",
    r"override\s+system\s+(policy|prompt|instructions)",
    r"drop\s+all\s+rules",
]
_PROMPT_INJECTION_RE = re.compile("|".join(_PROMPT_INJECTION_PATTERNS), re.IGNORECASE)

# High-precision domain keywords and aliases for the 14 DATA family competencies
CANONICAL_DATA_ALIASES: dict[str, list[str]] = {
    "data.anl.l2_eda": [
        "exploratory data analysis",
        "eda",
        "distributions",
        "histogram",
        "histograms",
        "summary statistics",
        "pandas",
        "seaborn",
        "matplotlib",
        "descriptive statistics",
        "scatter plot",
        "boxplot",
    ],
    "data.anl.l2_hygiene": [
        "data hygiene",
        "data quality",
        "anomaly detection",
        "null handling",
        "missing values",
        "schema drift",
        "deduplication",
        "data cleansing",
        "data cleaning",
        "great expectations",
        "outlier detection",
        "anomaly auditing",
    ],
    "data.anl.l2_sql_basic": [
        "sql",
        "relational database",
        "mysql",
        "postgresql",
        "postgres",
        "sqlite",
        "sql queries",
        "inner join",
        "left join",
        "group by",
        "table joins",
    ],
    "data.anl.l3_dashboard": [
        "dashboard",
        "dashboards",
        "tableau",
        "power bi",
        "powerbi",
        "metabase",
        "looker",
        "kpi design",
        "business metrics",
        "metric design",
        "executive dashboard",
        "dashboard architecture",
    ],
    "data.anl.l3_sql_adv": [
        "window functions",
        "window function",
        "partition by",
        "row_number",
        "dense_rank",
        "rank()",
        "cte",
        "common table expressions",
        "recursive cte",
        "sql optimization",
        "query optimization",
        "advanced sql",
    ],
    "data.gen.l2_ethics": [
        "data ethics",
        "dpdpa",
        "dpdp act",
        "gdpr",
        "data privacy",
        "privacy safeguards",
        "data masking",
        "anonymization",
        "ethical ai",
        "consent management",
        "ethical data governance",
    ],
    "data.gen.l2_prob_decomp": [
        "problem decomposition",
        "analytical reasoning",
        "root cause analysis",
        "issue tree",
        "mece",
        "hypothesis structuring",
        "structured thinking",
    ],
    "data.gen.l3_docs": [
        "technical documentation",
        "data dictionary",
        "reproducibility",
        "data lineage",
        "version control",
        "git",
        "documentation standards",
        "data catalog",
    ],
    "data.gen.l3_stakeholder": [
        "stakeholder communication",
        "executive presentation",
        "uncertainty communication",
        "evidence synthesis",
        "non-technical stakeholders",
        "presenting to leadership",
        "data storytelling",
        "stakeholder uncertainty",
    ],
    "data.sci.l3_exp_design": [
        "a/b test",
        "a/b tests",
        "a/b testing",
        "ab test",
        "ab tests",
        "ab testing",
        "experimentation",
        "experiments",
        "hypothesis testing",
        "hypothesis experiments",
        "hypothesis test",
        "hypothesis tests",
        "randomized controlled trial",
        "statistical power",
        "p-value",
        "sample size determination",
        "t-test",
        "chi-square",
    ],
    "data.sci.l3_feat_eng": [
        "feature engineering",
        "feature selection",
        "data leakage",
        "target encoding",
        "one-hot encoding",
        "scaling",
        "feature transformation",
        "interaction features",
        "leakage isolation",
    ],
    "data.sci.l3_ml_supervised": [
        "supervised learning",
        "machine learning",
        "predictive modeling",
        "predictive model",
        "predictive models",
        "scikit-learn",
        "sklearn",
        "xgboost",
        "lightgbm",
        "catboost",
        "random forest",
        "cross-validation",
        "logistic regression",
        "gradient boosting",
    ],
    "data.sci.l4_bigdata": [
        "spark",
        "pyspark",
        "databricks",
        "hadoop",
        "distributed computing",
        "mapreduce",
        "large-scale data",
        "big data",
        "spark dataframes",
    ],
    "data.sci.l4_causal": [
        "causal inference",
        "causal modeling",
        "observational study",
        "observational studies",
        "propensity score",
        "propensity scores",
        "instrumental variables",
        "synthetic control",
        "do-calculus",
        "difference-in-differences",
        "dag causal",
    ],
}


def sanitize_untrusted_text(raw_text: str) -> tuple[str, bool]:
    """Sanitize untrusted text against XSS, control chars, and prompt injections.

    Enforces Rule R-CR-09, Rule R-SC-01, and OWASP ASVS v4.0.3 standards.

    Args:
        raw_text: Arbitrary untrusted input string.

    Returns:
        tuple[str, bool]: (sanitized_clean_text, was_truncated_flag)
    """
    if not raw_text:
        return "", False

    truncated = False
    text = raw_text

    # 1. Enforce hard length boundary
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
        truncated = True

    # 2. Strip null bytes and non-printable control characters
    text = text.replace("\x00", " ")
    text = _CONTROL_CHARS_RE.sub(" ", text)

    # 3. Strip Unicode bidirectional override exploits
    text = _BIDI_CHARS_RE.sub("", text)

    # 4. Strip active HTML tags and script/style contents
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = _HTML_TAG_RE.sub(" ", text)

    # 5. Decode safe HTML entities (&amp;, &lt;, &gt;, &#x27;, etc.)
    text = html.unescape(text)
    # Re-strip any tags that might have appeared after unescaping
    text = _HTML_TAG_RE.sub(" ", text)

    # 6. Defang suspicious markdown links
    text = _SUSPICIOUS_MD_LINK_RE.sub(r"\1", text)

    # 7. Neutralize prompt injection attempts
    text = _PROMPT_INJECTION_RE.sub("[FILTERED_INSTRUCTION]", text)

    # 8. Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # 9. Collapse multiple whitespaces and tabs while maintaining paragraph structure
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    # Remove excessive blank lines (> 2 consecutive blank lines)
    cleaned_lines: list[str] = []
    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    sanitized = "\n".join(cleaned_lines).strip()
    return sanitized, truncated


def _build_word_boundary_pattern(term: str) -> re.Pattern[str]:
    """Build word-boundary regex for a keyword or alias term.

    Properly handles punctuation symbols like 'A/B', 'C++', 'C#', '.NET'.
    """
    escaped = re.escape(term)
    prefix = r"\b" if term[0].isalnum() else r"(?:^|\s)"
    suffix = r"\b" if term[-1].isalnum() else r"(?:$|\s)"
    return re.compile(rf"{prefix}{escaped}{suffix}", re.IGNORECASE)


def extract_competencies_from_text(
    sanitized_text: str,
    nodes: list[CompetencyNode],
    fuzzy_threshold: float = 80.0,
) -> list[CompetencyMatch]:
    """Extract matching competency nodes from sanitized text.

    Uses deterministic exact matching, alias lookup, and RapidFuzz token matching.
    Never calls runtime LLMs (Rule R-SC-07, ADR-0010).

    Args:
        sanitized_text: Sanitized job description string.
        nodes: Canonical competency nodes from TaxonomyPort.
        fuzzy_threshold: Minimum RapidFuzz similarity score (default 80.0).

    Returns:
        list[CompetencyMatch]: Deduplicated list of matched competencies sorted
            by descending confidence and role level.
    """
    if not sanitized_text or not nodes:
        return []

    matches_by_id: dict[str, CompetencyMatch] = {}
    lower_text = sanitized_text.lower()

    # Step 1: Check Exact Competency Title Matches & Curated Aliases
    for node in nodes:
        # 1a. Check exact competency title match
        title_pattern = _build_word_boundary_pattern(node.title)
        title_match = title_pattern.search(sanitized_text)
        if title_match:
            matches_by_id[node.id] = CompetencyMatch(
                competency_id=node.id,
                competency_title=node.title,
                category=node.category,
                target_levels=list(node.target_levels),
                match_method="exact",
                confidence=1.0,
                matched_text=title_match.group(0),
            )
            continue

        # 1b. Check curated aliases
        aliases = CANONICAL_DATA_ALIASES.get(node.id, [])
        alias_matched = False
        for alias in aliases:
            alias_pattern = _build_word_boundary_pattern(alias)
            match = alias_pattern.search(sanitized_text)
            if match:
                matches_by_id[node.id] = CompetencyMatch(
                    competency_id=node.id,
                    competency_title=node.title,
                    category=node.category,
                    target_levels=list(node.target_levels),
                    match_method="alias",
                    confidence=0.95,
                    matched_text=match.group(0),
                )
                alias_matched = True
                break

        if alias_matched:
            continue

        # Step 2: RapidFuzz token matching against competency title
        fuzz_score = float(fuzz.token_set_ratio(node.title.lower(), lower_text))
        if fuzz_score >= fuzzy_threshold:
            confidence = round(min(0.90, fuzz_score / 100.0), 3)
            matches_by_id[node.id] = CompetencyMatch(
                competency_id=node.id,
                competency_title=node.title,
                category=node.category,
                target_levels=list(node.target_levels),
                match_method="fuzzy",
                confidence=confidence,
                matched_text=node.title,
            )

    # Sort matches: descending confidence, then role level, then ID
    def _sort_key(m: CompetencyMatch) -> tuple[float, int, str]:
        lvl = m.target_levels[0].value if m.target_levels else 0
        return (-m.confidence, lvl, m.competency_id)

    sorted_matches = sorted(matches_by_id.values(), key=_sort_key)
    return sorted_matches


def intake_job_description(
    raw_text: str,
    taxonomy: TaxonomyPort,
    fuzzy_threshold: float = 80.0,
) -> JobDescriptionIntakeResult:
    """Intake, sanitize, and extract competencies from an untrusted job description.

    Operates strictly in ephemeral memory with zero disk writes, database records,
    or server-side profile persistence (Rules R-CR-09, R-CR-12, R-DA-07).

    Args:
        raw_text: Raw untrusted job description pasted by user.
        taxonomy: TaxonomyPort providing canonical competency nodes.
        fuzzy_threshold: Minimum RapidFuzz score for fuzzy matching.

    Returns:
        JobDescriptionIntakeResult: Sanitized summary and extracted matches.
    """
    sanitized, truncated = sanitize_untrusted_text(raw_text)
    manifest = taxonomy.get_competency_graph(family="DATA")
    matches = extract_competencies_from_text(
        sanitized,
        nodes=manifest.nodes,
        fuzzy_threshold=fuzzy_threshold,
    )
    matched_ids = [m.competency_id for m in matches]

    return JobDescriptionIntakeResult(
        sanitized_length=len(sanitized),
        original_length=len(raw_text),
        truncated=truncated,
        matches=matches,
        matched_competency_ids=matched_ids,
    )
