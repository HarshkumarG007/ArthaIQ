"""Feature specification, taxonomy, and registry for progressive personalization (Phase 6, T6.01).

Implements the formal feature catalog covering Level 0 through Level 3 across 7 feature
families, adhering to:
- PRD Section 5 & FR-05: Progressive disclosure and ablation-gated features.
- Rule R-MD-03: Zero lookahead; all features available at prediction time.
- Rule R-MD-06: Feature pipelines fitted strictly inside training folds.
- Rule R-MD-07: Anti-heuristic unbundling; no hard-coded multipliers.
- Rule R-MD-09: No ungrounded GPUs, GNNs, or Vector DBs without charters.
- Rule R-MD-11: Strict synthetic data isolation from production artifacts.
- Rule R-MD-13: Current pay anchoring analysis (EXP-07) and Compare-Only architecture.
- Rule R-MD-15: Missingness study; indicators only if justified, never personal traits.
- rules.md Section 16 Rule 11: Absolute prohibition of protected demographic inputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class FeatureLevel(StrEnum):
    """Progressive profiling and personalization levels (PRD Section 5, architecture 4.2)."""

    L0_CORE = "L0_CORE"
    L1_ROLE_PROFILE = "L1_ROLE_PROFILE"
    L2_TARGET_OPPORTUNITY = "L2_TARGET_OPPORTUNITY"
    L3_ADDITIONAL_EVIDENCE = "L3_ADDITIONAL_EVIDENCE"


class FeatureFamily(StrEnum):
    """Categorical grouping of compensation features."""

    ROLE_RESPONSIBILITY = "ROLE_RESPONSIBILITY"
    EXPERIENCE_HISTORY = "EXPERIENCE_HISTORY"
    SKILLS_CAPABILITY = "SKILLS_CAPABILITY"
    EMPLOYER_BUSINESS = "EMPLOYER_BUSINESS"
    LOCATION_WORK_ARRANGEMENT = "LOCATION_WORK_ARRANGEMENT"
    MACRO_MARKET = "MACRO_MARKET"
    TRANSACTIONAL_SEARCH = "TRANSACTIONAL_SEARCH"


class FeatureDataType(StrEnum):
    """Representation data types for features."""

    STRING = "STRING"
    CATEGORICAL = "CATEGORICAL"
    NUMERICAL_CONTINUOUS = "NUMERICAL_CONTINUOUS"
    NUMERICAL_DISCRETE = "NUMERICAL_DISCRETE"
    BOOLEAN = "BOOLEAN"
    ARRAY_STRING = "ARRAY_STRING"


class AblationDisposition(StrEnum):
    """Governance lifecycle status for feature families under ablation rules."""

    ACCEPTED_CORE = "ACCEPTED_CORE"
    EVALUATE_IN_PHASE_6 = "EVALUATE_IN_PHASE_6"
    DEFERRED_TO_PHASE_7 = "DEFERRED_TO_PHASE_7"
    COMPARE_ONLY = "COMPARE_ONLY"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class FeatureSpec:
    """Formal, auditable specification of a conditioning feature."""

    feature_id: str
    display_name: str
    level: FeatureLevel
    family: FeatureFamily
    data_type: FeatureDataType
    definition: str
    availability_timing: str
    data_source: str
    leakage_risk: str
    leakage_mitigations: str
    privacy_implications: str
    expected_utility: str
    ablation_plan: str
    ablation_threshold: str
    is_input_feature: bool = True
    disposition: AblationDisposition = AblationDisposition.EVALUATE_IN_PHASE_6

    def to_dict(self) -> dict[str, Any]:
        """Convert specification to JSON-serializable dictionary."""
        d = asdict(self)
        d["level"] = self.level.value
        d["family"] = self.family.value
        d["data_type"] = self.data_type.value
        d["disposition"] = self.disposition.value
        return d


# ==============================================================================
# Feature Registry: 23 Features Across Levels L0 to L3
# ==============================================================================

FEATURE_REGISTRY: tuple[FeatureSpec, ...] = (
    # --------------------------------------------------------------------------
    # Level 0 — Core Baseline Profile (Mandatory Conditioning)
    # --------------------------------------------------------------------------
    FeatureSpec(
        feature_id="feat_l0_role_family",
        display_name="Role Family",
        level=FeatureLevel.L0_CORE,
        family=FeatureFamily.ROLE_RESPONSIBILITY,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Standardized primary technology occupation family mapped via deterministic rules "
            "and O*NET 29.0 taxonomy: SWE (Software Engineering), DATA (Data Engineering & "
            "Analytics), MLAI (Machine Learning & AI), or OTHER."
        ),
        availability_timing="Available at query time from mandatory user input selection.",
        data_source="User input; validated against canonical RoleFamily enum and titles taxonomy.",
        leakage_risk="Zero leakage risk; canonical taxonomy mapping fitted prior to splits.",
        leakage_mitigations=(
            "Deterministic sanitization and O*NET crosswalk without target awareness."
        ),
        privacy_implications="Standard occupational metadata; non-sensitive under DPDPA 2023.",
        expected_utility=(
            "Primary baseline segmenting pay distributions across tech disciplines (e.g. MLAI "
            "vs SWE)."
        ),
        ablation_plan="Core anchor feature (Rung A/B/E/F baseline). Cannot be ablated.",
        ablation_threshold="N/A (Accepted Core baseline invariant).",
        is_input_feature=True,
        disposition=AblationDisposition.ACCEPTED_CORE,
    ),
    FeatureSpec(
        feature_id="feat_l0_seniority",
        display_name="Seniority Level",
        level=FeatureLevel.L0_CORE,
        family=FeatureFamily.ROLE_RESPONSIBILITY,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Canonical standardized career seniority grade: ENTRY (0-2y), MID (2-5y), SR (5-8y), "
            "LEAD (8-12y), STAFF (10-15y), PRINCIPAL (15y+), mapped via rules and soft labels."
        ),
        availability_timing="Available at query time from mandatory user input selection.",
        data_source="User input or title parsing crosswalked via compintel.normalization.levels.",
        leakage_risk=(
            "Post-promotion or future title leakage if historical profiles are dated incorrectly."
        ),
        leakage_mitigations=(
            "Observation effective_on timestamp enforcement (R-DA-03) and zero lookahead (R-MD-03)."
        ),
        privacy_implications="Standard career grade; non-sensitive under DPDPA 2023.",
        expected_utility=(
            "Major determinant of base cash compensation; accounts for >40% of variance."
        ),
        ablation_plan="Core anchor feature (Rung A/B/E/F baseline). Cannot be ablated.",
        ablation_threshold="N/A (Accepted Core baseline invariant).",
        is_input_feature=True,
        disposition=AblationDisposition.ACCEPTED_CORE,
    ),
    FeatureSpec(
        feature_id="feat_l0_location",
        display_name="Metro Location",
        level=FeatureLevel.L0_CORE,
        family=FeatureFamily.LOCATION_WORK_ARRANGEMENT,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Primary Indian employment metro technology hub: BENGALURU, HYDERABAD, NCR "
            "(Delhi/Noida/Gurugram), PUNE, MUMBAI, CHENNAI, or OTHER_IN."
        ),
        availability_timing="Available at query time from mandatory user input selection.",
        data_source="User input; validated against MetroLocation enum and pincode directory.",
        leakage_risk="Geographic regional shift leakage if foreign locations are pooled.",
        leakage_mitigations=(
            "Strict cross-market isolation (R-MD-08) prohibiting foreign datasets from Indian "
            "stream."
        ),
        privacy_implications="Metro-level granularity avoids residential re-identification risk.",
        expected_utility=(
            "Captures geographical cost-of-living premiums (e.g. Bengaluru/NCR +15-25% vs Tier-2)."
        ),
        ablation_plan="Core anchor feature (Rung A/B/E/F baseline). Cannot be ablated.",
        ablation_threshold="N/A (Accepted Core baseline invariant).",
        is_input_feature=True,
        disposition=AblationDisposition.ACCEPTED_CORE,
    ),
    FeatureSpec(
        feature_id="feat_l0_years_experience",
        display_name="Years of Experience",
        level=FeatureLevel.L0_CORE,
        family=FeatureFamily.EXPERIENCE_HISTORY,
        data_type=FeatureDataType.NUMERICAL_CONTINUOUS,
        definition=(
            "Total cumulative verified relevant professional software / tech industry experience "
            "in years, bounded continuously in [0.0, 45.0]."
        ),
        availability_timing="Available at query time from mandatory continuous user input.",
        data_source="User input or verified employment chronology from voluntary intake.",
        leakage_risk=(
            "Experience lookahead if measured as of interview/hire rather than observation date."
        ),
        leakage_mitigations="Computed strictly as of observation effective_on date (R-DA-03).",
        privacy_implications=(
            "Continuous numeric metric; does not disclose exact age or date of birth."
        ),
        expected_utility=(
            "Fundamental wage curve covariate; captures concave Mincerian wage growth."
        ),
        ablation_plan="Core anchor feature (Rung A/B/E/F baseline). Cannot be ablated.",
        ablation_threshold="N/A (Accepted Core baseline invariant).",
        is_input_feature=True,
        disposition=AblationDisposition.ACCEPTED_CORE,
    ),
    # --------------------------------------------------------------------------
    # Level 1 — Role-Relevant Profile (Optional, Gated by EXP-06 Ablation)
    # --------------------------------------------------------------------------
    FeatureSpec(
        feature_id="feat_l1_skills_primary",
        display_name="Primary Technical Skills",
        level=FeatureLevel.L1_ROLE_PROFILE,
        family=FeatureFamily.SKILLS_CAPABILITY,
        data_type=FeatureDataType.ARRAY_STRING,
        definition=(
            "Curated list of verified primary technical capabilities, frameworks, and programming "
            "languages (e.g. Python, Distributed Systems, PyTorch, Golang, Kubernetes, Rust) "
            "mapped to canonical ESCO/O*NET tech skill IDs."
        ),
        availability_timing="Optional user selection at query time via multi-select search.",
        data_source="Curated taxonomy from SRC-SUP-TAX-01 (O*NET) & SRC-SUP-TAX-02 (ESCO).",
        leakage_risk=(
            "Keyword inflation or future buzzwords not present in historical training records."
        ),
        leakage_mitigations=(
            "Frequency clipping (min occurrences >= 50); skills taxonomy frozen per snapshot."
        ),
        privacy_implications="Non-sensitive professional capability indicators.",
        expected_utility=(
            "Captures specialized technology premia (e.g. Distributed Systems/AI +15-30% over "
            "generic CRUD)."
        ),
        ablation_plan="EXP-06 Family A: Multi-hot sparse binary encoding vs Level 0 baseline.",
        ablation_threshold=(
            "Keep if Δ Pinball Loss <= -0.03 LPA and coverage maintained in [75%, 85%]."
        ),
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l1_skills_depth",
        display_name="Skill Specialization Depth Index",
        level=FeatureLevel.L1_ROLE_PROFILE,
        family=FeatureFamily.SKILLS_CAPABILITY,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Categorical index of technical depth: COMMODITY (widely available general stack), "
            "INTERMEDIATE (specialized frameworks with production track record), or HIGH_DEPTH "
            "(niche systems, compilers, distributed consensus, low-level optimization)."
        ),
        availability_timing=(
            "Optional self-selection based on production scale and system ownership."
        ),
        data_source="Taxonomy-derived heuristic mapped to ESCO competence levels.",
        leakage_risk="Subjective self-inflation bias on voluntary intake.",
        leakage_mitigations="Calibrated against experience and role level; bounded categories.",
        privacy_implications="Non-sensitive self-reported skill rating.",
        expected_utility="Separates superficial resume keyword match from architectural expertise.",
        ablation_plan="EXP-06 Family A: Depth interaction term ablation on quantile loss.",
        ablation_threshold="Keep if Δ Pinball Loss <= -0.02 LPA with zero crossing increase.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l1_domain_specialization",
        display_name="Domain Specialization",
        level=FeatureLevel.L1_ROLE_PROFILE,
        family=FeatureFamily.ROLE_RESPONSIBILITY,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Technical specialization sub-domain within role family: BACKEND, FRONTEND, FULLSTACK, "
            "ML_INFRA, DATA_PLATFORM, CLOUD_DEVOPS_SRE, EMBEDDED_IOT, SECURITY, or MOBILE."
        ),
        availability_timing="Optional selection at query time.",
        data_source="User input; cross-referenced with titles taxonomy sub-rules.",
        leakage_risk="Overfitting to rare niche specializations.",
        leakage_mitigations="Rare domains (< 20 records) pooled into general parent family.",
        privacy_implications="Standard occupational sub-classification.",
        expected_utility=(
            "Distinguishes compensation between high-scarcity (ML Infra/Security) and high- "
            "supply tracks."
        ),
        ablation_plan="EXP-06 Family B: Domain categorical dummy ablation.",
        ablation_threshold="Keep if Δ Pinball Loss <= -0.025 LPA across evaluated splits.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l1_employer_tier",
        display_name="Employer Tier / Archetype",
        level=FeatureLevel.L1_ROLE_PROFILE,
        family=FeatureFamily.EMPLOYER_BUSINESS,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Canonical employer organizational archetype: TIER_1_PRODUCT (global tech leaders & "
            "FAANG), GCC (Global Capability Centers of MNCs), HIGH_GROWTH_STARTUP (Series B+ "
            "venture-backed), DOMESTIC_PRODUCT (mature Indian product firms), or IT_SERVICES "
            "(global & domestic system integrators)."
        ),
        availability_timing="Optional input; user selects current or prospective company category.",
        data_source="Canonical employer mapping (T3.10b) and MCA / BSE statutory filings.",
        leakage_risk=(
            "Halo effect and circular attribution of high pay to arbitrary prestige labels."
        ),
        leakage_mitigations=(
            "Tiers defined strictly by objective business model, margin structure, and "
            "capital source "
            "rather than proprietary black-box rankings (R-MD-09)."
        ),
        privacy_implications=(
            "Coarse organizational archetype; zero employer-level re-identification."
        ),
        expected_utility=(
            "Explains the well-documented bimodal/trimodal tech salary distribution in India "
            "(e.g. IT Services P50 ~ 10 LPA vs Tier-1 Product P50 ~ 35 LPA at identical YoE)."
        ),
        ablation_plan="EXP-06 Family C: Tier categorical ablation vs Level 0 baseline.",
        ablation_threshold="Keep if Δ Pinball Loss <= -0.05 LPA and width ratio R_width <= 0.90.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l1_work_arrangement",
        display_name="Work Mode Arrangement",
        level=FeatureLevel.L1_ROLE_PROFILE,
        family=FeatureFamily.LOCATION_WORK_ARRANGEMENT,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Formal attendance requirement: ON_SITE, HYBRID (1-3 days office), or FULL_REMOTE."
        ),
        availability_timing="Optional user selection at query time.",
        data_source="User input; validated against job posting metadata.",
        leakage_risk="Post-pandemic policy drift and unrecorded policy reversals.",
        leakage_mitigations=(
            "Temporal validity check; observations older than 365 days re-weighted."
        ),
        privacy_implications="Standard workplace policy descriptor.",
        expected_utility=(
            "Tests whether remote discounts or hybrid premiums exist in post-2024 India tech."
        ),
        ablation_plan="EXP-06 Family D: Work arrangement ablation on interval sharpness.",
        ablation_threshold="Keep if Δ Pinball Loss <= -0.01 LPA; otherwise defer to Level 0 geo.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l1_career_velocity",
        display_name="Career Velocity Index",
        level=FeatureLevel.L1_ROLE_PROFILE,
        family=FeatureFamily.EXPERIENCE_HISTORY,
        data_type=FeatureDataType.NUMERICAL_CONTINUOUS,
        definition=(
            "Ratio of verified career level attained relative to expected tenure: "
            "Level_Index / (1 + Years_Experience). Captures fast-track promotions."
        ),
        availability_timing="Derived from voluntary intake employment history timestamps.",
        data_source="Chronological dates in SRC-INT-VOL-01 intake.",
        leakage_risk="Lookahead bias if promotion occurred after observation date.",
        leakage_mitigations="Strictly calculated on past tenure epochs prior to observation date.",
        privacy_implications="Derived ratio; no individual dates stored in serving layer.",
        expected_utility="Distinguishes high-trajectory early-career talent from stagnant tenures.",
        ablation_plan="EXP-06 Family E: Continuous spline interaction with YoE.",
        ablation_threshold="Keep if Δ Pinball Loss <= -0.015 LPA.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l1_leadership_scope",
        display_name="Team & Scope Scale",
        level=FeatureLevel.L1_ROLE_PROFILE,
        family=FeatureFamily.ROLE_RESPONSIBILITY,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Scope of leadership and team accountability: IC_INDIVIDUAL (0 reports), TECH_LEAD "
            "(technical oversight of 1-5 engineers), TEAM_LEAD_MGR (direct manager of 5-15), "
            "or ORG_LEAD (oversight of 15+ engineers or multiple teams)."
        ),
        availability_timing="Optional user selection.",
        data_source="User input; cross-referenced with Title mapping (IC vs Management tracks).",
        leakage_risk="Conflating nominal title with true responsibility.",
        leakage_mitigations="Standardized to team size bands rather than company-specific titles.",
        privacy_implications="Standard functional responsibility indicator.",
        expected_utility="Separates Senior IC compensation from Engineering Management pay scales.",
        ablation_plan="EXP-06 Family F: Scope categorical dummy ablation.",
        ablation_threshold="Keep if Δ Pinball Loss <= -0.02 LPA.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l1_macro_market_regime",
        display_name="Macro Tech Market Regime",
        level=FeatureLevel.L1_ROLE_PROFILE,
        family=FeatureFamily.MACRO_MARKET,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Macroeconomic tech labor market hiring regime indexed to observation effective "
            "quarter: "
            "COOLING (post-2022 normalization / hiring freezes), STABLE (steady replacement "
            "demand), "
            "or EXPANSIONARY (peak hiring boom e.g. 2021-2022)."
        ),
        availability_timing=(
            "Available at query time joined strictly via point-in-time release date."
        ),
        data_source="RBI / NASSCOM / MCA quarterly tech labor and GDP indicators.",
        leakage_risk="Lookahead bias if joined on publication date rather than release date.",
        leakage_mitigations=(
            "Point-in-time release date joining; strictly zero lookahead (R-MD-03, T7.05)."
        ),
        privacy_implications="Macro-level economic indicator; zero personal data under DPDPA 2023.",
        expected_utility=(
            "Captures structural compensation shifts across macroeconomic tech hiring cycles."
        ),
        ablation_plan="EXP-06 Family G: Macro-market regime ablation.",
        ablation_threshold=(
            "Keep if Δ Pinball Loss <= -0.01 LPA across temporal splits; otherwise defer to T7.05."
        ),
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    # --------------------------------------------------------------------------
    # Level 2 — Target Opportunity & Job Search Context (Opportunity-Specific)
    # --------------------------------------------------------------------------
    FeatureSpec(
        feature_id="feat_l2_target_employer_id",
        display_name="Target Employer Identifier",
        level=FeatureLevel.L2_TARGET_OPPORTUNITY,
        family=FeatureFamily.EMPLOYER_BUSINESS,
        data_type=FeatureDataType.STRING,
        definition=(
            "Canonical employer cluster identifier (e.g. EMP-0A1B2C3D) for the specific "
            "prospective "
            "or current hiring organization, canonicalized via exact & fuzzy resolution (T3.10b)."
        ),
        availability_timing="Optional user search query during target scenario planning.",
        data_source="Canonical employer registry and MCA company filings.",
        leakage_risk="Extreme small-cell de-anonymization and employer-level overfitting.",
        leakage_mitigations=(
            "Strict k_min >= 5 person cluster floor (R-DA-10). Employers with N < 5 shrink "
            "entirely "
            "to their parent feat_l1_employer_tier via hierarchical partial pooling."
        ),
        privacy_implications="Employer entity; personal identities remain strictly masked.",
        expected_utility=(
            "Enables company-specific pay benchmarking for high-volume tech employers."
        ),
        ablation_plan="Hierarchical partial pooling evaluation (T6.02, Rung C) vs generic tier.",
        ablation_threshold=(
            "Keep if shrinkage variance sigma_emp > 0 and empirical coverage preserved."
        ),
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l2_target_level_code",
        display_name="Employer-Specific Level Code",
        level=FeatureLevel.L2_TARGET_OPPORTUNITY,
        family=FeatureFamily.ROLE_RESPONSIBILITY,
        data_type=FeatureDataType.STRING,
        definition=(
            "Specific internal level code (e.g. L5, SDE3, 64, MTS-3) crosswalked to canonical "
            "seniority via compintel.normalization.levels."
        ),
        availability_timing="Optional query input.",
        data_source="Level taxonomy and verified voluntary intake.",
        leakage_risk="Misalignment between company-specific leveling standards.",
        leakage_mitigations=(
            "Soft-label probability distribution mapped across canonical levels (T3.09)."
        ),
        privacy_implications="Standard corporate career code.",
        expected_utility="Eliminates ambiguity in cross-company seniority transitions.",
        ablation_plan="Ablation of explicit level code vs generic seniority grade.",
        ablation_threshold="Keep if MAE improves by >= 0.50 LPA on mapped enterprise cohort.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l2_advertised_band_midpoint",
        display_name="Advertised Salary Band Midpoint",
        level=FeatureLevel.L2_TARGET_OPPORTUNITY,
        family=FeatureFamily.TRANSACTIONAL_SEARCH,
        data_type=FeatureDataType.NUMERICAL_CONTINUOUS,
        definition=(
            "Midpoint of recruiter-disclosed or job-posting advertised guaranteed cash range: "
            "(min_annual + max_annual) / 2 in nominal INR LPA."
        ),
        availability_timing="Available only when user has received a transparent recruiter band.",
        data_source="Voluntary intake / search context input.",
        leakage_risk="Advertised range may represent aspirations rather than closed transactions.",
        leakage_mitigations=(
            "Separate target PT3 calibration; quarantined from core market benchmark PT1."
        ),
        privacy_implications="Commercial job offer context; non-personal.",
        expected_utility="Narrows offer negotiation range for concrete active opportunities.",
        ablation_plan="Opportunity-conditioning ablation on offer targets (PT3/PT4).",
        ablation_threshold="Reserved strictly for scenario modeling (Phase 8); prohibited in PT1.",
        is_input_feature=False,
        disposition=AblationDisposition.DEFERRED_TO_PHASE_7,
    ),
    FeatureSpec(
        feature_id="feat_l2_competing_offers_count",
        display_name="Competing Offers Count",
        level=FeatureLevel.L2_TARGET_OPPORTUNITY,
        family=FeatureFamily.TRANSACTIONAL_SEARCH,
        data_type=FeatureDataType.NUMERICAL_DISCRETE,
        definition="Number of active, concurrent written job offers held: 0, 1, 2, or 3+.",
        availability_timing="Optional input during active negotiation scenario.",
        data_source="User input in negotiation simulator.",
        leakage_risk="Spurious correlation with candidate unobserved skill; non-causal.",
        leakage_mitigations=(
            "Explicitly barred from baseline PT1 market value (R-MD-09, rules.md Sec 16 rule 12)."
        ),
        privacy_implications="Sensitive negotiation leverage context.",
        expected_utility="Empirical premium associated with competitive bidding dynamics.",
        ablation_plan="Causal caveat analysis: verify association vs causal effect.",
        ablation_threshold="Restricted to PT4 negotiation counterfactuals; excluded from PT1.",
        is_input_feature=False,
        disposition=AblationDisposition.DEFERRED_TO_PHASE_7,
    ),
    FeatureSpec(
        feature_id="feat_l2_notice_period_days",
        display_name="Notice Period Duration",
        level=FeatureLevel.L2_TARGET_OPPORTUNITY,
        family=FeatureFamily.TRANSACTIONAL_SEARCH,
        data_type=FeatureDataType.NUMERICAL_DISCRETE,
        definition=(
            "Statutory contractual notice period: 0 (immediate joiner), 15, 30, 60, or 90 days."
        ),
        availability_timing="Optional user selection.",
        data_source="User input; prevalent in Indian tech employment contracts.",
        leakage_risk="Notice buyout dynamics and employer willingness to wait.",
        leakage_mitigations=(
            "Modeled strictly as hiring friction covariate, not permanent market worth."
        ),
        privacy_implications="Standard contractual term.",
        expected_utility=(
            "Quantifies the Indian 'immediate joiner premium' vs 90-day drop-off risk."
        ),
        ablation_plan="Ablation in offer acceptance probability (PT3).",
        ablation_threshold="Keep in PT3 if offer realization delta > 5%; excluded from base PT1.",
        is_input_feature=False,
        disposition=AblationDisposition.DEFERRED_TO_PHASE_7,
    ),
    FeatureSpec(
        feature_id="feat_l2_search_urgency",
        display_name="Job Search Urgency",
        level=FeatureLevel.L2_TARGET_OPPORTUNITY,
        family=FeatureFamily.TRANSACTIONAL_SEARCH,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Search posture: CASUAL_EXPLORING (employed, browsing), ACTIVE_SEARCH (actively "
            "interviewing), or IMMEDIATE_TRANSITION (serving notice / unemployed)."
        ),
        availability_timing="Optional user input.",
        data_source="User self-disclosure.",
        leakage_risk="Selection bias; distressed candidates accepting lower offers.",
        leakage_mitigations="Prohibited from depressing baseline market rate PT1.",
        privacy_implications="Personal job search status.",
        expected_utility="Helps simulate reservation wage bounds in career decision support.",
        ablation_plan="Reservation wage analysis in scenario modeling.",
        ablation_threshold="Excluded from PT1 market compensation by policy.",
        is_input_feature=False,
        disposition=AblationDisposition.DEFERRED_TO_PHASE_7,
    ),
    # --------------------------------------------------------------------------
    # Level 3 — Additional Evidence & Compensation Components
    # --------------------------------------------------------------------------
    FeatureSpec(
        feature_id="feat_l3_current_guaranteed_cash",
        display_name="Current Guaranteed Cash (Anchor Candidate)",
        level=FeatureLevel.L3_ADDITIONAL_EVIDENCE,
        family=FeatureFamily.EXPERIENCE_HISTORY,
        data_type=FeatureDataType.NUMERICAL_CONTINUOUS,
        definition=(
            "Candidate's current annualized guaranteed base cash in nominal INR LPA, "
            "unbundled strictly "
            "per ADR-0002. Governed by Rule R-MD-13 & EXP-07."
        ),
        availability_timing="Optional voluntary user disclosure.",
        data_source="User self-report or verified payslip via SRC-INT-VOL-01.",
        leakage_risk=(
            "CRITICAL: Historical underpayment persistence, gender/caste wage anchoring, and "
            "tautological model dependence where predicted pay simply equals past pay * 1.2."
        ),
        leakage_mitigations=(
            "Enforce 'COMPARE-ONLY' architecture per Decision D-010 and Rule R-MD-13. "
            "Current pay is used exclusively as a benchmark target (PT6) to evaluate market "
            "positioning, "
            "and NEVER fed as an input feature into the PT1 market estimation model without "
            "passing "
            "pre-registered ablation EXP-07."
        ),
        privacy_implications="High sensitivity personal financial data under DPDPA 2023.",
        expected_utility=(
            "Strong predictive power, but high ethical hazard of compounding historical "
            "underpayment."
        ),
        ablation_plan=(
            "EXP-07 Anchoring & Selection Analysis: Compare PT1 prediction with vs without "
            "current pay. "
            "Measure wage compression across underpaid demographics."
        ),
        ablation_threshold=(
            "REJECT as input feature if current pay explains >60% of model weight or increases "
            "wage disparity by >5% for historical underpayment cohorts. Default: COMPARE_ONLY."
        ),
        is_input_feature=False,
        disposition=AblationDisposition.COMPARE_ONLY,
    ),
    FeatureSpec(
        feature_id="feat_l3_verified_payslip_level",
        display_name="Income Verification Proof Level",
        level=FeatureLevel.L3_ADDITIONAL_EVIDENCE,
        family=FeatureFamily.EXPERIENCE_HISTORY,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Cryptographic proof level of contributor record: SELF_REPORTED (unverified), "
            "DOCUMENT_VERIFIED (client-side WebAssembly redacted payslip verified), or "
            "ENTERPRISE_CONFIRMED (statutory corporate disclosure)."
        ),
        availability_timing="Recorded automatically by voluntary intake ingestion pipeline.",
        data_source="SRC-INT-VOL-01 WebAssembly verification token metadata.",
        leakage_risk="Verification disparity: higher paid workers may verify more frequently.",
        leakage_mitigations=(
            "Modeled as sample weighting / SQSF tier (R-UQ-07), not causal salary input."
        ),
        privacy_implications="Zero cleartext payslip images retained (R-DA-07).",
        expected_utility=(
            "Calibrates observation confidence and error bounds in Rung C partial pooling."
        ),
        ablation_plan="Variance weighting ablation in hierarchical partial pooling (T6.02).",
        ablation_threshold=(
            "Keep if measurement error variance sigma_e is significantly reduced (p < 0.01)."
        ),
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l3_fixed_allowance_ratio",
        display_name="Fixed Allowance to Base Ratio",
        level=FeatureLevel.L3_ADDITIONAL_EVIDENCE,
        family=FeatureFamily.EXPERIENCE_HISTORY,
        data_type=FeatureDataType.NUMERICAL_CONTINUOUS,
        definition=(
            "Ratio of fixed monthly allowances (Special Allowance + HRA) to statutory Basic Pay: "
            "(hra_annual + special_allowance_annual) / basic_annual."
        ),
        availability_timing="Available when contributor provides itemized payslip breakdown.",
        data_source="Itemized fields in SRC-INT-VOL-01 intake.",
        leakage_risk="Tax structuring artifacts masquerading as productivity signals.",
        leakage_mitigations=(
            "Unbundled per ADR-0002; total guaranteed cash remains the primary target."
        ),
        privacy_implications="Detailed financial structure.",
        expected_utility=(
            "Detects aggressive tax structuring vs standard corporate payroll policies."
        ),
        ablation_plan="Ablation in component breakdown analysis (Phase 8).",
        ablation_threshold="Keep if residual variance of guaranteed cash decreases by >= 2%.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l3_project_scale_tier",
        display_name="Technical Project Scale Tier",
        level=FeatureLevel.L3_ADDITIONAL_EVIDENCE,
        family=FeatureFamily.SKILLS_CAPABILITY,
        data_type=FeatureDataType.CATEGORICAL,
        definition=(
            "Engineering throughput scale: SCALE_MODEST (<10k DAU / single node), SCALE_MEDIUM "
            "(10k-1M DAU / distributed cluster), or HYPERSCALE (1M+ DAU / >10k QPS)."
        ),
        availability_timing="Optional self-reported engineering scale questionnaire.",
        data_source="User input in deep profiling.",
        leakage_risk="Self-reporting bias and unverifiable claims.",
        leakage_mitigations="Coarse 3-tier categorization; verified against company tier.",
        privacy_implications="Technical system capability; non-personal.",
        expected_utility=(
            "Refines individual capability assessment within identical seniority tiers."
        ),
        ablation_plan="Ablation on Staff/Principal engineering slices.",
        ablation_threshold="Keep if MAE improves by >= 1.0 LPA on Staff/Principal cohort.",
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
    FeatureSpec(
        feature_id="feat_l3_tenure_stability_index",
        display_name="Employment Tenure Stability Index",
        level=FeatureLevel.L3_ADDITIONAL_EVIDENCE,
        family=FeatureFamily.EXPERIENCE_HISTORY,
        data_type=FeatureDataType.NUMERICAL_CONTINUOUS,
        definition="Median tenure duration across past completed employment epochs in years.",
        availability_timing="Derived from detailed chronological employment history.",
        data_source="Chronological timeline in SRC-INT-VOL-01.",
        leakage_risk="Penalizing involuntary job transitions or pandemic-era layoffs.",
        leakage_mitigations="Symmetric tenure metric; career breaks explicitly audited.",
        privacy_implications="Employment chronology summary.",
        expected_utility="Evaluates job-hopping premium vs long-tenure stagnation in India tech.",
        ablation_plan="Linear regression interaction with years of experience.",
        ablation_threshold=(
            "Keep if coefficient is statistically significant (p < 0.05) and stable."
        ),
        is_input_feature=True,
        disposition=AblationDisposition.EVALUATE_IN_PHASE_6,
    ),
)


# ==============================================================================
# Helper Lookup Functions
# ==============================================================================


def get_feature(feature_id: str) -> FeatureSpec:
    """Retrieve feature specification by unique identifier.

    Raises:
        KeyError: If feature_id is not registered.
    """
    for feat in FEATURE_REGISTRY:
        if feat.feature_id == feature_id:
            return feat
    msg = f"Feature '{feature_id}' is not registered in FEATURE_REGISTRY."
    raise KeyError(msg)


def get_features_by_level(level: FeatureLevel) -> list[FeatureSpec]:
    """Return all features associated with a progressive personalization level."""
    return [feat for feat in FEATURE_REGISTRY if feat.level == level]


def get_features_by_family(family: FeatureFamily) -> list[FeatureSpec]:
    """Return all features associated with a specific feature family."""
    return [feat for feat in FEATURE_REGISTRY if feat.family == family]


def get_input_features() -> list[FeatureSpec]:
    """Return all features authorized as direct regression inputs for PT1."""
    return [feat for feat in FEATURE_REGISTRY if feat.is_input_feature]


def get_compare_only_features() -> list[FeatureSpec]:
    """Return all features reserved strictly for Compare-Only benchmarking (e.g. PT6)."""
    return [
        feat
        for feat in FEATURE_REGISTRY
        if feat.disposition == AblationDisposition.COMPARE_ONLY or not feat.is_input_feature
    ]
