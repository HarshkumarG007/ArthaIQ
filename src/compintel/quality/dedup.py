"""Deduplication and entity resolution engine (Tasks T3.10a and T3.10b).

Adheres strictly to:
- Rule R-DA-03: Companion field and lineage preservation.
- Rule R-DA-04: Mandatory provenance and deterministic cluster IDs.
- Rule R-DA-06: Deduplicate before any split; group by person, employer, posting, source.
- Rule R-DA-07: Zero cleartext PII stored or leaked.
- Rule R-CD-03: Quality layer only imports schema; zero dependencies on higher layers.
- Rule R-MD-09: Deterministic algorithms, strictly free of LLMs.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import polars as pl
from rapidfuzz import fuzz, process

DEFAULT_DEDUP_VERSION: str = "v0.1.0"

# Canonical major tech employers operating in India tech market
CANONICAL_EMPLOYER_REGISTRY: dict[str, str] = {
    "google": "Google",
    "alphabet": "Google",
    "microsoft": "Microsoft",
    "amazon": "Amazon",
    "aws": "Amazon",
    "meta": "Meta",
    "facebook": "Meta",
    "apple": "Apple",
    "netflix": "Netflix",
    "uber": "Uber",
    "adobe": "Adobe",
    "salesforce": "Salesforce",
    "oracle": "Oracle",
    "cisco": "Cisco",
    "intel": "Intel",
    "qualcomm": "Qualcomm",
    "nvidia": "NVIDIA",
    "ibm": "IBM",
    "sap": "SAP",
    "vmware": "VMware",
    "atlassian": "Atlassian",
    "intuit": "Intuit",
    "stripe": "Stripe",
    "paypal": "PayPal",
    "twitter": "X (Twitter)",
    "linkedin": "LinkedIn",
    "spotify": "Spotify",
    "tcs": "Tata Consultancy Services",
    "tata consultancy": "Tata Consultancy Services",
    "tata consultancy services": "Tata Consultancy Services",
    "infosys": "Infosys",
    "infosis": "Infosys",
    "infy": "Infosys",
    "wipro": "Wipro",
    "hcl": "HCLTech",
    "hcltech": "HCLTech",
    "hcl technologies": "HCLTech",
    "tech mahindra": "Tech Mahindra",
    "cognizant": "Cognizant",
    "accenture": "Accenture",
    "capgemini": "Capgemini",
    "larsen & toubro": "Larsen & Toubro",
    "l&t": "Larsen & Toubro",
    "mindtree": "LTIMindtree",
    "ltimindtree": "LTIMindtree",
    "persistent": "Persistent Systems",
    "persistent systems": "Persistent Systems",
    "mphasis": "Mphasis",
    "hexaware": "Hexaware Technologies",
    "zscaler": "Zscaler",
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "flipkart": "Flipkart",
    "paytm": "Paytm",
    "phonepe": "PhonePe",
    "razorpay": "Razorpay",
    "cred": "CRED",
    "ola": "Ola",
    "zerodha": "Zerodha",
    "meesho": "Meesho",
    "groww": "Groww",
    "delhivery": "Delhivery",
    "urban company": "Urban Company",
    "zepto": "Zepto",
    "blinkit": "Blinkit",
    "inmobi": "InMobi",
    "freshworks": "Freshworks",
    "postman": "Postman",
    "browserstack": "BrowserStack",
    "chargebee": "Chargebee",
    "hasura": "Hasura",
    "clevertap": "CleverTap",
    "druva": "Druva",
    "innovaccer": "Innovaccer",
    "darwinbox": "Darwinbox",
}

# Corporate legal and organization suffixes to strip during employer canonicalization
_LEGAL_SUFFIXES_RE = re.compile(
    r"\b("
    r"private\s+limited|pvt\.?\s*ltd\.?|pvt\b|limited|ltd\.?|"
    r"incorporated|inc\.?|corporation|corp\.?|llc|llp|"
    r"technologies|technology|solutions|services|systems|software|"
    r"consulting|consultancy|enterprises|holdings|international|global|"
    r"india|ind\b|co\.?|company"
    r")\b",
    re.IGNORECASE,
)


def compute_exact_record_signature(payload: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 fingerprint for exact record duplicate detection.

    Canonicalizes fields to ensure invariance under dict key order or numerical precision jitter.
    Includes core compensation, profile, location, date, and employer cluster.
    """
    signature_keys = [
        "role_family",
        "canonical_title",
        "seniority",
        "location",
        "years_experience",
        "guaranteed_cash_annual",
        "basic_annual",
        "hra_annual",
        "special_allowance_annual",
        "as_of_date",
    ]

    canonical_payload: dict[str, Any] = {}
    for k in sorted(signature_keys):
        val = payload.get(k)
        if isinstance(val, float):
            # Round floats to 2 decimal places to avoid IEEE 754 precision artifacts
            canonical_payload[k] = round(val, 2)
        elif val is None:
            canonical_payload[k] = None
        else:
            canonical_payload[k] = str(val).strip()

    # Employer cluster component
    emp_token = payload.get("employer_cluster_id")
    if not emp_token:
        raw_emp = (
            payload.get("employer")
            or payload.get("company")
            or payload.get("company_name")
            or payload.get("employer_name")
        )
        if raw_emp is not None and str(raw_emp).strip():
            _, emp_token = canonicalize_employer_name(raw_emp)
        else:
            emp_token = None
    canonical_payload["employer_cluster_id"] = str(emp_token).strip() if emp_token else None

    serialized = json.dumps(canonical_payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_person_signature(payload: dict[str, Any]) -> str:
    """Compute a person-level biometric/profile fingerprint to cluster repeat submissions.

    Matches identical demographic profiles with matching base pay or compensation line items.
    """
    # If the payload explicitly carries an anonymized contributor ID, use it directly
    anon_id = payload.get("anonymized_employee_id") or payload.get("contributor_id")
    if anon_id and str(anon_id).strip():
        token = f"anon:{str(anon_id).strip()}"
        return f"PER-{hashlib.sha256(token.encode('utf-8')).hexdigest()[:12].upper()}"

    person_keys = [
        "location",
        "role_family",
        "education_level",
        "years_experience",
        "basic_annual",
        "guaranteed_cash_annual",
    ]

    canonical_person: dict[str, Any] = {}
    for k in sorted(person_keys):
        val = payload.get(k)
        if isinstance(val, float):
            canonical_person[k] = round(val, 2)
        elif val is None:
            canonical_person[k] = None
        else:
            canonical_person[k] = str(val).strip()

    serialized = json.dumps(canonical_person, sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12].upper()
    return f"PER-{digest}"


def canonicalize_employer_name(raw_employer: str | None) -> tuple[str, str]:
    """Canonicalize employer name into a standardized company name and cluster ID.

    Applies:
    1. Unicode normalization and punctuation sanitization.
    2. Corporate legal suffix stripping (e.g. Pvt Ltd, Inc, Technologies).
    3. Exact and alias dictionary mapping.
    4. RapidFuzz token-based similarity matching (threshold >= 84.0).
    5. Fallback cluster ID generation.

    Returns:
        tuple of (canonical_employer_name, employer_cluster_id).
    """
    if raw_employer is None:
        return ("Anonymous / Unspecified", "EMP-ANONYMOUS")

    clean = unicodedata.normalize("NFKD", str(raw_employer)).strip()
    if not clean or clean.lower() in {"unknown", "n/a", "na", "null", "none", "anonymous"}:
        return ("Anonymous / Unspecified", "EMP-ANONYMOUS")

    # Lowercase and strip legal suffixes
    lowered = clean.lower()
    stripped = _LEGAL_SUFFIXES_RE.sub(" ", lowered)
    # Remove non-alphanumeric characters except ampersands and spaces
    sanitized = re.sub(r"[^\w\s&]", " ", stripped)
    tokens = [t for t in sanitized.split() if t]
    normalized = " ".join(tokens)

    if not normalized:
        # If suffix stripping consumed everything, fall back to original alphanumeric tokens
        orig_tokens = [t for t in re.sub(r"[^\w\s&]", " ", lowered).split() if t]
        normalized = " ".join(orig_tokens) if orig_tokens else clean.lower()

    # 1. Exact alias lookup
    if normalized in CANONICAL_EMPLOYER_REGISTRY:
        canonical_name = CANONICAL_EMPLOYER_REGISTRY[normalized]
        cluster_id = (
            f"EMP-{hashlib.sha256(canonical_name.lower().encode('utf-8')).hexdigest()[:12].upper()}"
        )
        return (canonical_name, cluster_id)

    # 2. Fuzzy match against canonical registry
    choices = list(CANONICAL_EMPLOYER_REGISTRY.keys())
    match = process.extractOne(normalized, choices, scorer=fuzz.token_set_ratio, score_cutoff=84.0)
    if match:
        matched_key = match[0]
        canonical_name = CANONICAL_EMPLOYER_REGISTRY[matched_key]
        cluster_id = (
            f"EMP-{hashlib.sha256(canonical_name.lower().encode('utf-8')).hexdigest()[:12].upper()}"
        )
        return (canonical_name, cluster_id)

    # 3. Standard title-case fallback for uncataloged employers
    canonical_name = " ".join(w.capitalize() for w in normalized.split())
    cluster_id = (
        f"EMP-{hashlib.sha256(canonical_name.lower().encode('utf-8')).hexdigest()[:12].upper()}"
    )
    return (canonical_name, cluster_id)


def compute_employer_signature(payload: dict[str, Any]) -> tuple[str, str]:
    """Extract employer and compute canonical employer and cluster ID from a record payload."""
    raw_employer = (
        payload.get("employer")
        or payload.get("company")
        or payload.get("company_name")
        or payload.get("employer_name")
    )
    return canonicalize_employer_name(raw_employer)


def compute_posting_signature(payload: dict[str, Any], employer_cluster_id: str) -> str:
    """Compute a deterministic posting cluster signature for job posting deduplication.

    Uses explicit posting IDs if available; otherwise hashes employer, role, location, and period.
    """
    raw_posting_id = (
        payload.get("posting_id")
        or payload.get("job_posting_id")
        or payload.get("requisition_id")
        or payload.get("job_id")
    )
    if raw_posting_id and str(raw_posting_id).strip():
        digest = (
            hashlib.sha256(str(raw_posting_id).strip().encode("utf-8")).hexdigest()[:12].upper()
        )
        return f"PST-{digest}"

    role_token = str(payload.get("canonical_title") or payload.get("role_family") or "ROLE").strip()
    loc_token = str(payload.get("location") or "LOC").strip()
    date_token = str(payload.get("as_of_date") or payload.get("posting_date") or "DATE").strip()[:7]

    composite = f"{employer_cluster_id}:{role_token}:{loc_token}:{date_token}"
    digest = hashlib.sha256(composite.encode("utf-8")).hexdigest()[:12].upper()
    return f"PST-{digest}"


@dataclass(frozen=True)
class DeduplicationResult:
    """Standardized deduplication and entity-clustering outcome for an observation."""

    observation_id: str
    record_signature: str
    is_exact_duplicate: bool
    exact_duplicate_of: str | None
    exact_duplicate_cluster_id: str
    person_cluster_id: str
    person_cluster_size: int
    employer_cluster_id: str
    canonical_employer: str
    posting_cluster_id: str
    dedup_version: str = DEFAULT_DEDUP_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "observation_id": self.observation_id,
            "record_signature": self.record_signature,
            "is_exact_duplicate": self.is_exact_duplicate,
            "exact_duplicate_of": self.exact_duplicate_of,
            "exact_duplicate_cluster_id": self.exact_duplicate_cluster_id,
            "person_cluster_id": self.person_cluster_id,
            "person_cluster_size": self.person_cluster_size,
            "employer_cluster_id": self.employer_cluster_id,
            "canonical_employer": self.canonical_employer,
            "posting_cluster_id": self.posting_cluster_id,
            "dedup_version": self.dedup_version,
        }


@dataclass(frozen=True)
class SourceDuplicateMetrics:
    """Duplicate and cluster metrics for a specific ingestion source."""

    source_id: str
    total_records: int
    distinct_records: int
    exact_duplicates: int
    duplicate_rate: float
    distinct_person_clusters: int
    distinct_employer_clusters: int
    cross_source_duplicates: int

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "source_id": self.source_id,
            "total_records": self.total_records,
            "distinct_records": self.distinct_records,
            "exact_duplicates": self.exact_duplicates,
            "duplicate_rate": self.duplicate_rate,
            "distinct_person_clusters": self.distinct_person_clusters,
            "distinct_employer_clusters": self.distinct_employer_clusters,
            "cross_source_duplicates": self.cross_source_duplicates,
        }


@dataclass(frozen=True)
class DeduplicationReport:
    """Overall dataset deduplication audit report across all sources."""

    total_records: int
    distinct_records: int
    total_exact_duplicates: int
    overall_duplicate_rate: float
    total_person_clusters: int
    total_employer_clusters: int
    total_posting_clusters: int
    sources: list[SourceDuplicateMetrics]
    dedup_version: str = DEFAULT_DEDUP_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "total_records": self.total_records,
            "distinct_records": self.distinct_records,
            "total_exact_duplicates": self.total_exact_duplicates,
            "overall_duplicate_rate": self.overall_duplicate_rate,
            "total_person_clusters": self.total_person_clusters,
            "total_employer_clusters": self.total_employer_clusters,
            "total_posting_clusters": self.total_posting_clusters,
            "sources": [s.to_dict() for s in self.sources],
            "dedup_version": self.dedup_version,
        }

    def to_dataframe(self) -> pl.DataFrame:
        """Convert per-source breakdown to Polars DataFrame."""
        if not self.sources:
            return pl.DataFrame(
                schema={
                    "source_id": pl.String,
                    "total_records": pl.Int64,
                    "distinct_records": pl.Int64,
                    "exact_duplicates": pl.Int64,
                    "duplicate_rate": pl.Float64,
                    "distinct_person_clusters": pl.Int64,
                    "distinct_employer_clusters": pl.Int64,
                    "cross_source_duplicates": pl.Int64,
                }
            )
        return pl.DataFrame([s.to_dict() for s in self.sources])


class ExactDeduplicator:
    """Stateful streaming and batch deduplicator tracking seen signatures and clusters."""

    def __init__(self, dedup_version: str = DEFAULT_DEDUP_VERSION) -> None:
        self.dedup_version = dedup_version
        self._seen_signatures: dict[
            str, tuple[str, str]
        ] = {}  # sig -> (primary_obs_id, primary_source_id)
        self._person_clusters: dict[str, list[str]] = {}  # person_cluster_id -> [observation_id]
        self._employer_clusters: dict[
            str, list[str]
        ] = {}  # employer_cluster_id -> [observation_id]
        self._posting_clusters: dict[str, list[str]] = {}  # posting_cluster_id -> [observation_id]

        # Per-source accounting
        self._source_records: dict[str, list[str]] = {}
        self._source_duplicates: dict[str, int] = {}
        self._source_cross_duplicates: dict[str, int] = {}
        self._source_person_clusters: dict[str, set[str]] = {}
        self._source_employer_clusters: dict[str, set[str]] = {}

    @property
    def total_seen(self) -> int:
        """Total distinct signatures recorded."""
        return len(self._seen_signatures)

    @property
    def total_clusters(self) -> int:
        """Total person clusters formed."""
        return len(self._person_clusters)

    def process_record(
        self,
        observation_id: str,
        payload: dict[str, Any],
    ) -> DeduplicationResult:
        """Process a single record, resolving duplicates, person, employer, and posting clusters."""
        obs_id = str(observation_id).strip()
        source_id = str(payload.get("source_id") or "UNKNOWN").strip()
        sig = compute_exact_record_signature(payload)
        person_id = compute_person_signature(payload)
        canonical_emp, emp_id = compute_employer_signature(payload)
        post_id = compute_posting_signature(payload, emp_id)
        exact_cluster_id = f"DUP-{sig[:12].upper()}"

        # Initialize source tracking
        if source_id not in self._source_records:
            self._source_records[source_id] = []
            self._source_duplicates[source_id] = 0
            self._source_cross_duplicates[source_id] = 0
            self._source_person_clusters[source_id] = set()
            self._source_employer_clusters[source_id] = set()

        self._source_records[source_id].append(obs_id)
        self._source_person_clusters[source_id].add(person_id)
        self._source_employer_clusters[source_id].add(emp_id)

        # Exact duplicate detection
        if sig in self._seen_signatures:
            is_dup = True
            primary_obs_id, primary_source_id = self._seen_signatures[sig]
            dup_of = primary_obs_id
            self._source_duplicates[source_id] += 1
            if primary_source_id != source_id:
                self._source_cross_duplicates[source_id] += 1
        else:
            is_dup = False
            dup_of = None
            self._seen_signatures[sig] = (obs_id, source_id)

        # Update person cluster
        if person_id not in self._person_clusters:
            self._person_clusters[person_id] = []
        self._person_clusters[person_id].append(obs_id)
        cluster_size = len(self._person_clusters[person_id])

        # Update employer & posting clusters
        if emp_id not in self._employer_clusters:
            self._employer_clusters[emp_id] = []
        self._employer_clusters[emp_id].append(obs_id)

        if post_id not in self._posting_clusters:
            self._posting_clusters[post_id] = []
        self._posting_clusters[post_id].append(obs_id)

        return DeduplicationResult(
            observation_id=obs_id,
            record_signature=sig,
            is_exact_duplicate=is_dup,
            exact_duplicate_of=dup_of,
            exact_duplicate_cluster_id=exact_cluster_id,
            person_cluster_id=person_id,
            person_cluster_size=cluster_size,
            employer_cluster_id=emp_id,
            canonical_employer=canonical_emp,
            posting_cluster_id=post_id,
            dedup_version=self.dedup_version,
        )

    def build_report(self) -> DeduplicationReport:
        """Compile comprehensive deduplication report across all processed observations."""
        source_metrics: list[SourceDuplicateMetrics] = []
        total_records = sum(len(obs) for obs in self._source_records.values())
        total_duplicates = sum(self._source_duplicates.values())
        distinct_records = len(self._seen_signatures)
        overall_dup_rate = round(total_duplicates / total_records, 4) if total_records > 0 else 0.0

        for sid in sorted(self._source_records.keys()):
            s_total = len(self._source_records[sid])
            s_dup = self._source_duplicates[sid]
            s_rate = round(s_dup / s_total, 4) if s_total > 0 else 0.0
            s_distinct = s_total - s_dup
            s_person = len(self._source_person_clusters[sid])
            s_emp = len(self._source_employer_clusters[sid])
            s_cross = self._source_cross_duplicates[sid]

            source_metrics.append(
                SourceDuplicateMetrics(
                    source_id=sid,
                    total_records=s_total,
                    distinct_records=s_distinct,
                    exact_duplicates=s_dup,
                    duplicate_rate=s_rate,
                    distinct_person_clusters=s_person,
                    distinct_employer_clusters=s_emp,
                    cross_source_duplicates=s_cross,
                )
            )

        return DeduplicationReport(
            total_records=total_records,
            distinct_records=distinct_records,
            total_exact_duplicates=total_duplicates,
            overall_duplicate_rate=overall_dup_rate,
            total_person_clusters=len(self._person_clusters),
            total_employer_clusters=len(self._employer_clusters),
            total_posting_clusters=len(self._posting_clusters),
            sources=source_metrics,
            dedup_version=self.dedup_version,
        )


def deduplicate_records_df(
    df: pl.DataFrame,
    id_column: str = "observation_id",
    dedup_version: str = DEFAULT_DEDUP_VERSION,
) -> pl.DataFrame:
    """Batch process a Polars DataFrame, appending deduplication and entity cluster columns.

    Appends:
    - record_signature: Deterministic SHA-256 fingerprint string
    - is_exact_duplicate: Boolean indicating an identical prior record exists
    - exact_duplicate_of: Observation ID of the original record (or null)
    - exact_duplicate_cluster_id: Clustered signature identity string (DUP-...)
    - person_cluster_id: Clustered worker identity string (PER-...)
    - person_cluster_size: Total records belonging to this person cluster
    - employer_cluster_id: Clustered canonical employer string (EMP-...)
    - canonical_employer: Standardized employer title string
    - posting_cluster_id: Clustered job posting / vacancy string (PST-...)
    - dedup_version: Version identifier attached to output

    Args:
        df: Polars DataFrame of canonical or raw observations.
        id_column: Column name containing the unique observation identifier.
        dedup_version: Version identifier attached to output.

    Returns:
        New Polars DataFrame with appended deduplication and entity cluster columns.
    """
    if df.height == 0:
        return df.with_columns(
            pl.lit(None, dtype=pl.String).alias("record_signature"),
            pl.lit(None, dtype=pl.Boolean).alias("is_exact_duplicate"),
            pl.lit(None, dtype=pl.String).alias("exact_duplicate_of"),
            pl.lit(None, dtype=pl.String).alias("exact_duplicate_cluster_id"),
            pl.lit(None, dtype=pl.String).alias("person_cluster_id"),
            pl.lit(None, dtype=pl.Int64).alias("person_cluster_size"),
            pl.lit(None, dtype=pl.String).alias("employer_cluster_id"),
            pl.lit(None, dtype=pl.String).alias("canonical_employer"),
            pl.lit(None, dtype=pl.String).alias("posting_cluster_id"),
            pl.lit(None, dtype=pl.String).alias("dedup_version"),
        )

    deduplicator = ExactDeduplicator(dedup_version=dedup_version)
    records = df.iter_rows(named=True)

    results: list[DeduplicationResult] = []
    for r in records:
        obs_id = str(r.get(id_column, f"ROW-{len(results)}"))
        res = deduplicator.process_record(observation_id=obs_id, payload=r)
        results.append(res)

    # Post-process to update all records in a cluster with the final cluster_size
    final_cluster_sizes = {
        cid: len(members) for cid, members in deduplicator._person_clusters.items()
    }

    signatures = [r.record_signature for r in results]
    is_dups = [r.is_exact_duplicate for r in results]
    dup_ofs = [r.exact_duplicate_of for r in results]
    exact_cluster_ids = [r.exact_duplicate_cluster_id for r in results]
    person_ids = [r.person_cluster_id for r in results]
    sizes = [final_cluster_sizes[r.person_cluster_id] for r in results]
    emp_ids = [r.employer_cluster_id for r in results]
    canonical_emps = [r.canonical_employer for r in results]
    posting_ids = [r.posting_cluster_id for r in results]
    versions = [r.dedup_version for r in results]

    return df.with_columns(
        pl.Series("record_signature", signatures, dtype=pl.String),
        pl.Series("is_exact_duplicate", is_dups, dtype=pl.Boolean),
        pl.Series("exact_duplicate_of", dup_ofs, dtype=pl.String),
        pl.Series("exact_duplicate_cluster_id", exact_cluster_ids, dtype=pl.String),
        pl.Series("person_cluster_id", person_ids, dtype=pl.String),
        pl.Series("person_cluster_size", sizes, dtype=pl.Int64),
        pl.Series("employer_cluster_id", emp_ids, dtype=pl.String),
        pl.Series("canonical_employer", canonical_emps, dtype=pl.String),
        pl.Series("posting_cluster_id", posting_ids, dtype=pl.String),
        pl.Series("dedup_version", versions, dtype=pl.String),
    )


def compute_source_duplicate_report(
    df: pl.DataFrame,
    id_column: str = "observation_id",
    dedup_version: str = DEFAULT_DEDUP_VERSION,
) -> DeduplicationReport:
    """Compute duplicate and cluster report by source from a Polars DataFrame."""
    deduplicator = ExactDeduplicator(dedup_version=dedup_version)
    for r in df.iter_rows(named=True):
        obs_id = str(r.get(id_column, "UNKNOWN"))
        deduplicator.process_record(observation_id=obs_id, payload=r)
    return deduplicator.build_report()


def generate_deduplication_report_markdown(report: DeduplicationReport) -> str:
    """Generate GFM markdown summary of deduplication and source duplication rates."""
    lines: list[str] = [
        "# CompIntel Data Quality: Deduplication and Entity Resolution Report",
        "",
        f"- **Deduplication Version:** `{report.dedup_version}`",
        f"- **Total Records Analyzed:** {report.total_records:,}",
        f"- **Distinct Records:** {report.distinct_records:,}",
        f"- **Exact Duplicates Detected:** {report.total_exact_duplicates:,}",
        f"- **Overall Duplicate Rate:** {report.overall_duplicate_rate:.2%}",
        f"- **Unique Person Clusters:** {report.total_person_clusters:,}",
        f"- **Unique Employer Clusters:** {report.total_employer_clusters:,}",
        f"- **Unique Posting Clusters:** {report.total_posting_clusters:,}",
        "",
        "## Source Duplicate Breakdown",
        "",
        (
            "| Source ID | Total Records | Distinct Records | Duplicates | "
            "Dup Rate | Person Clusters | Employer Clusters | Cross-Source Dups |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]

    for s in report.sources:
        lines.append(
            f"| `{s.source_id}` | {s.total_records:,} | {s.distinct_records:,} | "
            f"{s.exact_duplicates:,} | {s.duplicate_rate:.2%} | {s.distinct_person_clusters:,} | "
            f"{s.distinct_employer_clusters:,} | {s.cross_source_duplicates:,} |"
        )

    lines.append("")
    return "\n".join(lines)
