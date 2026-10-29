"""Script to author and validate canonical DATA family practice scenarios (Task T15.24).

Adheres to:
- ADR-0010 & Rule R-CR-15: Zero runtime LLMs.
- ADR-0013 & Rule R-CR-08: 100% deterministic rubric scoring with partial credit.
- Rule R-CR-11: Practice, not certification (no exam or credential terminology).
- Rule R-CR-01: Prohibits causal compensation promises.
- Rule R-CR-04: Ground-truth provenance and source attribution tracking.
"""

from __future__ import annotations

import json
from pathlib import Path

from compintel.career.scenario_schema import (
    ArtifactLanguage,
    DefectCategory,
    DefectSeverity,
    FalseFlagPenalty,
    PracticeScenario,
    ScenarioArtifact,
    ScenarioRubric,
    ScenarioVariant,
    SeededDefect,
)
from compintel.career.schema import (
    RoleLevel,
    TaxonomyLicense,
    TaxonomyProvenance,
    TaxonomySource,
)
from compintel.schema.enums import RoleFamily


def generate_scenarios() -> dict[str, PracticeScenario]:
    """Build and validate all three canonical DATA family scenarios."""
    out_dir = Path("config/scenarios")
    out_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 1. SCEN-DATA-01-SQL: SQL Pitfall Review
    # =========================================================================
    sql_content = (
        "SELECT\n"
        "    user_id,\n"
        "    payment_method,\n"
        "    COUNT(order_id) AS total_orders,\n"
        "    SUM(order_amount_inr) AS total_spend,\n"
        "    SUM(order_amount_inr) / COUNT(order_id) AS avg_order_value,\n"
        "    MAX(order_timestamp) OVER (\n"
        "        PARTITION BY user_id\n"
        "        ORDER BY order_timestamp\n"
        "        ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING\n"
        "    ) AS next_activity_timestamp,\n"
        "    AVG(delivery_fee_inr) AS avg_delivery_fee\n"
        "FROM customer_orders\n"
        "WHERE order_status = 'DELIVERED'\n"
        "  AND order_timestamp >= '2026-01-01'\n"
        "GROUP BY user_id, payment_method\n"
        "ORDER BY total_spend DESC;"
    )
    sql_lines = len(sql_content.splitlines())

    provenance_sql = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-DATA-01",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (DATA Family)",
        modified_flag=False,
        curator="Data Engineering Review Board",
        curated_date="2026-10-29",
    )

    defects_sql = [
        SeededDefect(
            id="DEF-SQL-01",
            line_number=6,
            category=DefectCategory.DIVISION_BY_ZERO,
            severity=DefectSeverity.CRITICAL,
            title="Unguarded Division in Average Order Value Calculation",
            consequence=(
                "When a customer has zero matching orders, unguarded division yields runtime "
                "SQL zero division exceptions or silent NULL propagation."
            ),
            diagnostic_explanation=(
                "Wrap the denominator with NULLIF(COUNT(order_id), 0) or use the native AVG "
                "aggregate function."
            ),
            competency_id="data.anl.l2_sql_basic",
            points=1.0,
        ),
        SeededDefect(
            id="DEF-SQL-02",
            line_number=10,
            category=DefectCategory.LOOKAHEAD_BIAS,
            severity=DefectSeverity.CRITICAL,
            title="Future Activity Window Lookahead Leakage",
            consequence=(
                "Partitioning with UNBOUNDED FOLLOWING injects future event timestamps into "
                "historical feature records, causing fatal target leakage in downstream models."
            ),
            diagnostic_explanation=(
                "Restrict window frames to historical data using ROWS BETWEEN UNBOUNDED "
                "PRECEDING AND CURRENT ROW."
            ),
            competency_id="data.anl.l2_sql_basic",
            points=1.0,
        ),
        SeededDefect(
            id="DEF-SQL-03",
            line_number=16,
            category=DefectCategory.AGGREGATION_BIAS,
            severity=DefectSeverity.MAJOR,
            title="Extraneous Grouping Key in Customer Level Aggregation",
            consequence=(
                "Including payment_method in the GROUP BY clause fragments customer metrics across "
                "payment instruments, producing multiple records per user instead of a single "
                "customer rollup."
            ),
            diagnostic_explanation=(
                "Group strictly by user_id to compute true user-level metrics, or aggregate "
                "payment methods into an array."
            ),
            competency_id="data.anl.l2_eda",
            points=1.0,
        ),
    ]

    rubric_sql = ScenarioRubric(
        scenario_id="SCEN-DATA-01-SQL",
        defects=defects_sql,
        pass_threshold_score=2.0,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.5),
    )

    scen_sql = PracticeScenario(
        id="SCEN-DATA-01-SQL",
        title="Diagnostic Review: Customer Revenue Aggregation and Window Leakage",
        description=(
            "Review a high-volume relational aggregation query for mathematical errors, "
            "aggregation bias, and lookahead feature leakage."
        ),
        role_family=RoleFamily.DATA,
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="data.anl.l2_sql_basic",
        secondary_competency_ids=["data.anl.l2_eda"],
        artifact=ScenarioArtifact(
            content=sql_content,
            language=ArtifactLanguage.SQL,
            line_count=sql_lines,
        ),
        rubric=rubric_sql,
        variants=[
            ScenarioVariant(
                variant_id="VAR-ECOMMERCE",
                description="E-commerce marketplace transaction table variant",
                parameters={"table_name": "order_items", "customer_id_col": "buyer_id"},
            ),
            ScenarioVariant(
                variant_id="VAR-FINTECH-PAYMENTS",
                description="Fintech merchant settlement ledger variant",
                parameters={
                    "table_name": "merchant_settlements",
                    "customer_id_col": "merchant_id",
                },
            ),
        ],
        instructions=(
            "Inspect the SQL query for relational pitfalls, unguarded mathematical operations, "
            "and predictive feature leakage. Flag flawed line numbers and select correct "
            "defect classifications."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_sql,
    )

    # =========================================================================
    # 2. SCEN-DATA-02-EDA: Metric Definition & Hygiene Investigation
    # =========================================================================
    eda_content = (
        "import numpy as np\n"
        "import pandas as pd\n"
        "\n"
        "\n"
        "def compute_monthly_churn(df: pd.DataFrame) -> dict[str, float]:\n"
        "    # Filter active verified accounts\n"
        '    filtered_df = df[df["email_verified"] == True].copy()\n'
        "\n"
        "    # Impute missing customer lifetime spend\n"
        '    imputed_spend = df["total_spend_inr"].fillna(df["total_spend_inr"].mean())\n'
        '    filtered_df["imputed_spend"] = imputed_spend\n'
        "\n"
        "    # Compute monthly churn rates\n"
        "    monthly_rates = []\n"
        '    for month in filtered_df["signup_month"].unique():\n'
        '        cohort = filtered_df[filtered_df["signup_month"] == month]\n'
        '        churned = cohort[cohort["status"] == "CHURNED"]\n'
        "        rate = len(churned) / len(cohort) if len(cohort) > 0 else 0.0\n"
        "        monthly_rates.append(rate)\n"
        "\n"
        "    # Calculate overall platform churn metric\n"
        "    platform_churn = float(np.mean(monthly_rates))\n"
        "\n"
        "    return {\n"
        '        "platform_churn": round(platform_churn, 4),\n'
        '        "total_cohorts": len(monthly_rates),\n'
        "    }\n"
    )
    eda_lines = len(eda_content.splitlines())

    provenance_eda = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-DATA-02",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (DATA Family)",
        modified_flag=False,
        curator="Data Engineering Review Board",
        curated_date="2026-10-29",
    )

    defects_eda = [
        SeededDefect(
            id="DEF-EDA-01",
            line_number=7,
            category=DefectCategory.SAMPLE_RATIO_MISMATCH,
            severity=DefectSeverity.CRITICAL,
            title="Selection Bias from Pre-Filtering Unverified Accounts",
            consequence=(
                "Filtering out unverified signups prior to cohort formation artificially "
                "inflates measured retention and introduces severe survivor bias."
            ),
            diagnostic_explanation=(
                "Retain all registered accounts in the cohort denominator, or evaluate "
                "verified and unverified cohorts as stratified segments."
            ),
            competency_id="data.anl.l2_eda",
            points=1.0,
        ),
        SeededDefect(
            id="DEF-EDA-02",
            line_number=10,
            category=DefectCategory.DATA_LEAKAGE,
            severity=DefectSeverity.MAJOR,
            title="Global Mean Imputation Across Stratified Segments",
            consequence=(
                "Imputing missing values using the global unstratified mean distorts segment "
                "variance and leaks cohort-level properties into individual records."
            ),
            diagnostic_explanation=(
                "Impute missing spend within specific signup cohorts or use median imputation "
                "with an explicit missingness indicator flag."
            ),
            competency_id="data.anl.l2_eda",
            points=1.0,
        ),
        SeededDefect(
            id="DEF-EDA-03",
            line_number=22,
            category=DefectCategory.METRIC_MISALIGNMENT,
            severity=DefectSeverity.MAJOR,
            title="Unweighted Arithmetic Mean of Cohort Churn Rates",
            consequence=(
                "Taking a simple unweighted arithmetic mean over monthly churn rates treats "
                "large and small cohorts identically, violating volume weighting."
            ),
            diagnostic_explanation=(
                "Calculate platform churn by dividing total churned users across all cohorts by "
                "total cohort users, or use volume-weighted averages."
            ),
            competency_id="data.anl.l2_eda",
            points=1.0,
        ),
    ]

    rubric_eda = ScenarioRubric(
        scenario_id="SCEN-DATA-02-EDA",
        defects=defects_eda,
        pass_threshold_score=2.0,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.5),
    )

    scen_eda = PracticeScenario(
        id="SCEN-DATA-02-EDA",
        title="Diagnostic Review: Churn Metric Formulation and Imputation Leakage",
        description=(
            "Inspect a cohort retention analytics pipeline for selection bias, improper global "
            "imputation, and unweighted summary metric formulation."
        ),
        role_family=RoleFamily.DATA,
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="data.anl.l2_eda",
        secondary_competency_ids=["data.anl.l2_hygiene"],
        artifact=ScenarioArtifact(
            content=eda_content,
            language=ArtifactLanguage.PYTHON,
            line_count=eda_lines,
        ),
        rubric=rubric_eda,
        variants=[
            ScenarioVariant(
                variant_id="VAR-SAAS-RECURRING",
                description="B2B SaaS subscription recurring revenue cohort variant",
                parameters={"metric_focus": "arr_churn", "entity": "organization_id"},
            ),
            ScenarioVariant(
                variant_id="VAR-EDTECH-SUBSCRIPTIONS",
                description="Consumer EdTech learner monthly renewal cohort variant",
                parameters={"metric_focus": "subscriber_churn", "entity": "learner_id"},
            ),
        ],
        instructions=(
            "Review the data cleaning and cohort aggregation script. Identify methodological "
            "flaws in filtering, imputation, and metric aggregation."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_eda,
    )

    # =========================================================================
    # 3. SCEN-DATA-03-EXP: A/B Experiment Design Review
    # =========================================================================
    exp_content = (
        "import numpy as np\n"
        "from scipy import stats\n"
        "\n"
        "\n"
        "def evaluate_ab_experiment(\n"
        "    control_conversions: np.ndarray,\n"
        "    treatment_conversions: np.ndarray,\n"
        "    daily_peeking_p_values: list[float],\n"
        ") -> dict[str, object]:\n"
        "    n_ctrl = len(control_conversions)\n"
        "    n_trt = len(treatment_conversions)\n"
        "\n"
        "    # Check sample ratio mismatch (50/50 allocation expected)\n"
        "    chi2_stat, srm_p_value = stats.chisquare([n_ctrl, n_trt])\n"
        "    if srm_p_value < 0.001:\n"
        '        print("Discrepancy detected; continuing evaluation.")\n'
        "\n"
        "    # Continuous monitoring check without alpha spending correction\n"
        "    early_winner_declared = any(p < 0.05 for p in daily_peeking_p_values)\n"
        "\n"
        "    # Compute aggregate conversion rate\n"
        "    ctrl_mean = float(np.mean(control_conversions))\n"
        "    trt_mean = float(np.mean(treatment_conversions))\n"
        "    relative_lift = (trt_mean - ctrl_mean) / ctrl_mean if ctrl_mean > 0 else 0.0\n"
        "\n"
        "    # Two-sample t-test on combined mobile and desktop traffic\n"
        "    t_stat, final_p_val = stats.ttest_ind(treatment_conversions, control_conversions)\n"
        "\n"
        "    return {\n"
        '        "srm_p_value": round(float(srm_p_value), 6),\n'
        '        "early_stop": early_winner_declared,\n'
        '        "relative_lift": round(relative_lift, 4),\n'
        '        "final_p_val": round(float(final_p_val), 5),\n'
        "    }\n"
    )
    exp_lines = len(exp_content.splitlines())

    provenance_exp = TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-DATA-03",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark (DATA Family)",
        modified_flag=False,
        curator="Data Engineering Review Board",
        curated_date="2026-10-29",
    )

    defects_exp = [
        SeededDefect(
            id="DEF-EXP-01",
            line_number=14,
            category=DefectCategory.SAMPLE_RATIO_MISMATCH,
            severity=DefectSeverity.CRITICAL,
            title="Continuing Experiment Analysis Despite Extreme Sample Ratio Mismatch",
            consequence=(
                "Evaluating lift when sample ratio mismatch is present invalidates causal "
                "inference because randomization has been compromised by delivery bias."
            ),
            diagnostic_explanation=(
                "When SRM is confirmed (p < 0.001), halt the analysis and debug traffic allocation "
                "infrastructure before evaluating treatment lift."
            ),
            competency_id="data.sci.l3_exp_design",
            points=1.0,
        ),
        SeededDefect(
            id="DEF-EXP-02",
            line_number=18,
            category=DefectCategory.LOOKAHEAD_BIAS,
            severity=DefectSeverity.CRITICAL,
            title="Sequential Peeking Without Alpha Spending Correction",
            consequence=(
                "Stopping early on uncorrected daily p-values inflates the False Positive Rate "
                "well beyond the nominal 5% threshold."
            ),
            diagnostic_explanation=(
                "Use formal group sequential boundaries (e.g. O'Brien-Fleming) or evaluate "
                "strictly at predetermined sample horizons."
            ),
            competency_id="data.sci.l3_exp_design",
            points=1.0,
        ),
        SeededDefect(
            id="DEF-EXP-03",
            line_number=26,
            category=DefectCategory.AGGREGATION_BIAS,
            severity=DefectSeverity.MAJOR,
            title="Aggregated Lift Estimation Ignoring Device Mix Confounders",
            consequence=(
                "Combining disparate device segments directly risks Simpson's Paradox where "
                "treatment appears positive in aggregate but is negative within device cohorts."
            ),
            diagnostic_explanation=(
                "Estimate treatment lift using stratified variance-weighted estimates or "
                "regression adjustment with device interaction terms."
            ),
            competency_id="data.sci.l4_causal",
            points=1.0,
        ),
    ]

    rubric_exp = ScenarioRubric(
        scenario_id="SCEN-DATA-03-EXP",
        defects=defects_exp,
        pass_threshold_score=2.0,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.5),
    )

    scen_exp = PracticeScenario(
        id="SCEN-DATA-03-EXP",
        title="Diagnostic Review: Controlled Experiment Evaluation and Peeking Bias",
        description=(
            "Audit an online A/B testing analysis script for sample ratio mismatches, "
            "unadjusted sequential peeking, and unstratified aggregation."
        ),
        role_family=RoleFamily.DATA,
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="data.sci.l3_exp_design",
        secondary_competency_ids=["data.sci.l4_causal"],
        artifact=ScenarioArtifact(
            content=exp_content,
            language=ArtifactLanguage.PYTHON,
            line_count=exp_lines,
        ),
        rubric=rubric_exp,
        variants=[
            ScenarioVariant(
                variant_id="VAR-CHECKOUT-FUNNEL",
                description="E-commerce checkout funnel 1-click buy experiment variant",
                parameters={"metric_name": "checkout_completed", "treatment_split": "50/50"},
            ),
            ScenarioVariant(
                variant_id="VAR-SEARCH-ALGO",
                description="Search ranking relevance algorithm test variant",
                parameters={"metric_name": "click_through_rate", "treatment_split": "50/50"},
            ),
        ],
        instructions=(
            "Audit the A/B test analysis pipeline. Identify flaws in randomization diagnostics, "
            "significance testing methodology, and segment aggregation."
        ),
        disclaimer=(
            "Technical practice scenario for capability self-reflection and professional "
            "development (Rules R-CR-08, R-CR-11)."
        ),
        provenance=provenance_exp,
    )

    scenarios = {
        "scen_data_01_sql.json": scen_sql,
        "scen_data_02_eda.json": scen_eda,
        "scen_data_03_exp.json": scen_exp,
    }

    for filename, scenario in scenarios.items():
        filepath = out_dir / filename
        data = scenario.model_dump(mode="json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(
            f"Serialized {filename} ({len(scenario.artifact.content.splitlines())} lines, "
            f"{len(scenario.rubric.defects)} defects, {len(scenario.variants)} variants)"
        )

    return scenarios


if __name__ == "__main__":
    generate_scenarios()
