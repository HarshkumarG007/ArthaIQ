import React, { useState, useMemo } from "react";
import {
  saveScenarioAttempt,
  type ClientScenarioAttemptRecord,
} from "../../lib/careerLedger";
import {
  Play,
  RotateCcw,
  Shield,
  Trash2,
  Plus,
} from "lucide-react";

export interface SeededDefectDefinition {
  id: string;
  line_number: number;
  category: string;
  severity: "critical" | "major" | "minor";
  title: string;
  consequence: string;
  diagnostic_explanation: string;
  competency_id: string;
  points: number;
}

export interface ScenarioDefinition {
  id: string;
  title: string;
  description: string;
  role_family: string;
  target_level: number;
  primary_competency_id: string;
  language: "sql" | "python";
  content: string;
  instructions: string;
  pass_threshold_score: number;
  false_flag_penalty_per_flag: number;
  max_penalty: number;
  defects: SeededDefectDefinition[];
  mock_output_headers?: string[];
  mock_output_rows?: (string | number)[][];
}

export const CANONICAL_SCENARIOS: ScenarioDefinition[] = [
  {
    id: "SCEN-DATA-01-SQL",
    title: "Diagnostic Review: Customer Revenue Aggregation and Window Leakage",
    description: "Review a high-volume relational aggregation query for mathematical errors, aggregation bias, and lookahead feature leakage.",
    role_family: "DATA",
    target_level: 3,
    primary_competency_id: "data.anl.l2_sql_basic",
    language: "sql",
    instructions: "Inspect the SQL query for relational pitfalls, unguarded mathematical operations, and predictive feature leakage. Click any line number to flag a defect.",
    pass_threshold_score: 2.0,
    false_flag_penalty_per_flag: 0.5,
    max_penalty: 1.5,
    content: `SELECT
    user_id,
    payment_method,
    COUNT(order_id) AS total_orders,
    SUM(order_amount_inr) AS total_spend,
    SUM(order_amount_inr) / COUNT(order_id) AS avg_order_value,
    MAX(order_timestamp) OVER (
        PARTITION BY user_id
        ORDER BY order_timestamp
        ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
    ) AS next_activity_timestamp,
    AVG(delivery_fee_inr) AS avg_delivery_fee
FROM customer_orders
WHERE order_status = 'DELIVERED'
  AND order_timestamp >= '2026-01-01'
GROUP BY user_id, payment_method
ORDER BY total_spend DESC;`,
    mock_output_headers: ["user_id", "payment_method", "total_orders", "total_spend", "avg_order_value", "next_activity_timestamp"],
    mock_output_rows: [
      ["USR-9921", "UPI", 14, "₹42,500", "₹3,035.71", "2026-10-28 19:42:00 (Future Leak)"],
      ["USR-9921", "CREDIT_CARD", 3, "₹18,200", "₹6,066.67", "2026-10-29 11:15:00 (Future Leak)"],
      ["USR-4810", "NET_BANKING", 1, "₹1,250", "₹1,250.00", "2026-10-14 08:30:00 (Future Leak)"],
    ],
    defects: [
      {
        id: "DEF-SQL-01",
        line_number: 6,
        category: "division_by_zero",
        severity: "critical",
        title: "Unguarded Division in Average Order Value Calculation",
        consequence: "When a customer has zero matching orders, unguarded division yields runtime SQL zero division exceptions or silent NULL propagation.",
        diagnostic_explanation: "Wrap the denominator with NULLIF(COUNT(order_id), 0) or use the native AVG aggregate function.",
        competency_id: "data.anl.l2_sql_basic",
        points: 1.0,
      },
      {
        id: "DEF-SQL-02",
        line_number: 10,
        category: "lookahead_bias",
        severity: "critical",
        title: "Future Activity Window Lookahead Leakage",
        consequence: "Partitioning with UNBOUNDED FOLLOWING injects future event timestamps into historical feature records, causing fatal target leakage in downstream models.",
        diagnostic_explanation: "Restrict window frames to historical data using ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.",
        competency_id: "data.anl.l2_sql_basic",
        points: 1.0,
      },
      {
        id: "DEF-SQL-03",
        line_number: 16,
        category: "aggregation_bias",
        severity: "major",
        title: "Extraneous Grouping Key in Customer Level Aggregation",
        consequence: "Including payment_method in the GROUP BY clause fragments customer metrics across payment instruments, producing multiple records per user instead of a single customer rollup.",
        diagnostic_explanation: "Group strictly by user_id to compute true user-level metrics, or aggregate payment methods into an array.",
        competency_id: "data.anl.l2_eda",
        points: 1.0,
      },
    ],
  },
  {
    id: "SCEN-DATA-02-EDA",
    title: "Diagnostic Review: Cohort Churn Pre-filtering and Imputation",
    description: "Review exploratory cohort analytics code for selection bias from row filtering, global mean imputation skew, and unweighted churn rates.",
    role_family: "DATA",
    target_level: 3,
    primary_competency_id: "data.anl.l2_eda",
    language: "python",
    instructions: "Inspect the Python data cleaning and cohort aggregation code for methodological bias, statistical skew, and leakage. Click any line number to flag a defect.",
    pass_threshold_score: 2.0,
    false_flag_penalty_per_flag: 0.5,
    max_penalty: 1.5,
    content: `import pandas as pd
import numpy as np

def compute_monthly_churn(df: pd.DataFrame) -> pd.DataFrame:
    # Filter active subscribers
    clean_df = df[df['days_active'] > 30].copy()
    
    # Impute missing engagement score
    mean_engagement = clean_df['engagement_score'].mean()
    clean_df['engagement_score'] = clean_df['engagement_score'].fillna(mean_engagement)
    
    # Compute cohort summary
    cohort = clean_df.groupby('signup_month').agg(
        total_users=('user_id', 'count'),
        churned_users=('is_churned', 'sum')
    ).reset_index()
    
    # Calculate simple average churn across cohorts
    mean_churn_rate = (cohort['churned_users'] / cohort['total_users']).mean()
    cohort['unweighted_mean'] = mean_churn_rate
    
    return cohort`,
    mock_output_headers: ["signup_month", "total_users", "churned_users", "unweighted_mean"],
    mock_output_rows: [
      ["2026-01", 12400, 1860, "15.00%"],
      ["2026-02", 450, 112, "15.00% (Distorted by small cohort)"],
      ["2026-03", 8900, 1157, "15.00%"],
    ],
    defects: [
      {
        id: "DEF-EDA-01",
        line_number: 6,
        category: "sample_ratio_mismatch",
        severity: "critical",
        title: "Selection Survivorship Bias from Pre-filtering Active Days",
        consequence: "Dropping users active <= 30 days censors the exact cohort experiencing highest early churn, artificially suppressing churn rates.",
        diagnostic_explanation: "Retain early dropouts or compute retention curves survival models across all signed-up users.",
        competency_id: "data.anl.l2_eda",
        points: 1.0,
      },
      {
        id: "DEF-EDA-02",
        line_number: 10,
        category: "data_leakage",
        severity: "major",
        title: "Global Mean Imputation Distorting Variance",
        consequence: "Imputing engagement scores with a single global cohort mean collapses variance and hides bimodality between active and disengaged users.",
        diagnostic_explanation: "Impute conditionally by plan tier or utilize explicit missingness indicators.",
        competency_id: "data.sci.l3_ml_supervised",
        points: 1.0,
      },
      {
        id: "DEF-EDA-03",
        line_number: 20,
        category: "metric_misalignment",
        severity: "major",
        title: "Unweighted Mean Across Unequal Cohort Sizes (Simpson's Paradox)",
        consequence: "Taking the simple unweighted mean of cohort churn rates gives a 450-user cohort identical weight to a 12,400-user cohort.",
        diagnostic_explanation: "Compute pooled weighted churn: total churned users divided by total users across cohorts.",
        competency_id: "data.anl.l2_eda",
        points: 1.0,
      },
    ],
  },
  {
    id: "SCEN-DATA-03-EXP",
    title: "Diagnostic Review: A/B Test Ratio Mismatch and Sequential Peeking",
    description: "Review experiment evaluation script for sample ratio mismatch (SRM), continuous peeking without alpha spending, and unstratified metric aggregation.",
    role_family: "DATA",
    target_level: 4,
    primary_competency_id: "data.sci.l3_exp_design",
    language: "python",
    instructions: "Inspect the A/B experiment evaluation script for statistical hypothesis violations and methodological flaws. Click any line number to flag a defect.",
    pass_threshold_score: 2.0,
    false_flag_penalty_per_flag: 0.5,
    max_penalty: 1.5,
    content: `import scipy.stats as stats
import pandas as pd

def evaluate_ab_experiment(df: pd.DataFrame) -> dict:
    ctrl = df[df['variant'] == 'control']
    treat = df[df['variant'] == 'treatment']
    
    # Check sample counts (configured 50/50 split)
    n_ctrl = len(ctrl)
    n_treat = len(treat)
    
    # Run two-sample t-test every day during rollout
    t_stat, p_val = stats.ttest_ind(ctrl['conversion'], treat['conversion'])
    
    # Declare victory if p < 0.05 on any daily check
    is_significant = bool(p_val < 0.05)
    
    # Aggregate conversion without device stratification
    pooled_conv_ctrl = ctrl['conversion'].mean()
    pooled_conv_treat = treat['conversion'].mean()
    lift = (pooled_conv_treat - pooled_conv_ctrl) / pooled_conv_ctrl
    
    return {
        'n_control': n_ctrl,
        'n_treatment': n_treat,
        'p_value': p_val,
        'significant': is_significant,
        'relative_lift': lift
    }`,
    mock_output_headers: ["metric", "value", "status"],
    mock_output_rows: [
      ["n_control", "48,200", "Observed ratio 48.2% vs expected 50.0%"],
      ["n_treatment", "51,800", "Severe SRM (Chi-square p < 1e-12)"],
      ["p_value", "0.038", "Inflated Type I error from continuous peeking"],
    ],
    defects: [
      {
        id: "DEF-EXP-01",
        line_number: 10,
        category: "sample_ratio_mismatch",
        severity: "critical",
        title: "Ignored Sample Ratio Mismatch (SRM) Check",
        consequence: "Analyzing conversion rates without a chi-square goodness-of-fit check for sample allocation ratio renders the entire test invalid due to latent assignment bias.",
        diagnostic_explanation: "Execute chi-square test on observed vs expected assignment counts; halt inference if p < 0.001.",
        competency_id: "data.sci.l3_exp_design",
        points: 1.0,
      },
      {
        id: "DEF-EXP-02",
        line_number: 17,
        category: "lookahead_bias",
        severity: "critical",
        title: "Continuous Peeking without Alpha Spending Function",
        consequence: "Evaluating p-values daily without O'Brien-Fleming or Pocock correction inflates cumulative Type I error from nominal 5% to over 30%.",
        diagnostic_explanation: "Pre-commit to fixed sample size, or implement sequential testing with an alpha spending schedule.",
        competency_id: "data.sci.l3_exp_design",
        points: 1.0,
      },
      {
        id: "DEF-EXP-03",
        line_number: 22,
        category: "aggregation_bias",
        severity: "major",
        title: "Unstratified Aggregation across Heterogeneous Segments",
        consequence: "Aggregating conversion across mobile and web without covariate adjustment induces Simpson's paradox when device distribution shifts between variants.",
        diagnostic_explanation: "Fit a logistic regression model with variant and device covariates, or compute stratified Cochran-Mantel-Haenszel odds ratios.",
        competency_id: "data.sci.l4_causal",
        points: 1.0,
      },
    ],
  },
];

export interface CandidateFlagSubmission {
  line_number: number;
  category: string;
  rationale?: string;
}

export interface DefectEvaluationResult {
  defect_id: string;
  title: string;
  line_number: number;
  category: string;
  match_type: "perfect" | "partial_category" | "partial_adjacent" | "unmatched";
  points_awarded: number;
  max_points: number;
  consequence: string;
  diagnostic_explanation: string;
  competency_id: string;
}

export interface AttemptReport {
  score: number;
  max_possible_score: number;
  raw_score: number;
  false_flags_count: number;
  penalty_deducted: number;
  passed: boolean;
  defects: DefectEvaluationResult[];
  unlocked_competencies: string[];
}

interface PracticeWorkspaceProps {
  initialScenarioId?: string;
  attempts?: ClientScenarioAttemptRecord[];
  onAttemptCompleted?: (record: ClientScenarioAttemptRecord) => void;
}

export function PracticeWorkspace({
  initialScenarioId = "SCEN-DATA-01-SQL",
  attempts = [],
  onAttemptCompleted,
}: PracticeWorkspaceProps): React.JSX.Element {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(initialScenarioId);
  const [selectedLine, setSelectedLine] = useState<number>(1);
  const [categoryInput, setCategoryInput] = useState<string>("division_by_zero");
  const [rationaleInput, setRationaleInput] = useState<string>("");
  const [flags, setFlags] = useState<CandidateFlagSubmission[]>([]);
  const [showSandbox, setShowSandbox] = useState<boolean>(false);
  const [evaluationReport, setEvaluationReport] = useState<AttemptReport | null>(null);

  const scenario = useMemo(() => {
    return CANONICAL_SCENARIOS.find((s) => s.id === selectedScenarioId) || CANONICAL_SCENARIOS[0]!;
  }, [selectedScenarioId]);

  const priorAttempt = useMemo(() => {
    if (!attempts || attempts.length === 0) return null;
    const norm = (id: string) => id.toLowerCase().replace(/[-_]/g, "");
    return attempts.find((a) => norm(a.scenario_id) === norm(scenario.id));
  }, [attempts, scenario.id]);

  const lines = useMemo(() => {
    return scenario.content.split("\n");
  }, [scenario.content]);

  // Switch scenario
  const handleSelectScenario = (id: string): void => {
    setSelectedScenarioId(id);
    setSelectedLine(1);
    setFlags([]);
    setEvaluationReport(null);
    setShowSandbox(false);
  };

  // Add or update candidate flag
  const handleAddFlag = (e: React.FormEvent): void => {
    e.preventDefault();
    if (selectedLine < 1 || selectedLine > lines.length) return;

    // Check if line is already flagged
    const existingIndex = flags.findIndex((f) => f.line_number === selectedLine);
    const newFlag: CandidateFlagSubmission = {
      line_number: selectedLine,
      category: categoryInput,
      rationale: rationaleInput.trim() || undefined,
    };

    if (existingIndex >= 0) {
      const updated = [...flags];
      updated[existingIndex] = newFlag;
      setFlags(updated);
    } else {
      setFlags([...flags, newFlag]);
    }

    setRationaleInput("");
  };

  const handleRemoveFlag = (lineNum: number): void => {
    setFlags(flags.filter((f) => f.line_number !== lineNum));
  };

  // Deterministic scoring evaluation (ADR-0013, Rule R-CR-08)
  const handleSubmitAttempt = async (): Promise<void> => {
    const matchedFlags = new Set<number>(); // indices in flags
    const defectResults: DefectEvaluationResult[] = [];
    let rawScore = 0;
    const totalMaxPoints = scenario.defects.reduce((acc, d) => acc + d.points, 0);

    for (const defect of scenario.defects) {
      let matched = false;
      let matchType: "perfect" | "partial_category" | "partial_adjacent" | "unmatched" = "unmatched";
      let pointsAwarded = 0;

      // 1. Exact line + exact category (100% points)
      for (let i = 0; i < flags.length; i++) {
        const flag = flags[i]!;
        if (!matchedFlags.has(i) && flag.line_number === defect.line_number && flag.category === defect.category) {
          matched = true;
          matchType = "perfect";
          pointsAwarded = defect.points;
          matchedFlags.add(i);
          break;
        }
      }

      // 2. Exact line + category mismatch (50% points)
      if (!matched) {
        for (let i = 0; i < flags.length; i++) {
          const flag = flags[i]!;
          if (!matchedFlags.has(i) && flag.line_number === defect.line_number) {
            matched = true;
            matchType = "partial_category";
            pointsAwarded = defect.points * 0.5;
            matchedFlags.add(i);
            break;
          }
        }
      }

      // 3. Adjacent line (+/- 1) + exact category (50% points)
      if (!matched) {
        for (let i = 0; i < flags.length; i++) {
          const flag = flags[i]!;
          if (
            !matchedFlags.has(i) &&
            Math.abs(flag.line_number - defect.line_number) === 1 &&
            flag.category === defect.category
          ) {
            matched = true;
            matchType = "partial_adjacent";
            pointsAwarded = defect.points * 0.5;
            matchedFlags.add(i);
            break;
          }
        }
      }

      rawScore += pointsAwarded;
      defectResults.push({
        defect_id: defect.id,
        title: defect.title,
        line_number: defect.line_number,
        category: defect.category,
        match_type: matchType,
        points_awarded: pointsAwarded,
        max_points: defect.points,
        consequence: defect.consequence,
        diagnostic_explanation: defect.diagnostic_explanation,
        competency_id: defect.competency_id,
      });
    }

    // False flag penalty
    const falseFlagsCount = flags.length - matchedFlags.size;
    const penaltyDeducted = Math.min(
      falseFlagsCount * scenario.false_flag_penalty_per_flag,
      scenario.max_penalty
    );

    const netScore = Math.max(0.0, rawScore - penaltyDeducted);
    const passed = netScore >= scenario.pass_threshold_score;

    // Unlocked competencies on pass
    const unlocked: string[] = [];
    if (passed) {
      unlocked.push(scenario.primary_competency_id);
      for (const res of defectResults) {
        if (res.match_type !== "unmatched" && !unlocked.includes(res.competency_id)) {
          unlocked.push(res.competency_id);
        }
      }
    }

    const report: AttemptReport = {
      score: netScore,
      max_possible_score: totalMaxPoints,
      raw_score: rawScore,
      false_flags_count: falseFlagsCount,
      penalty_deducted: penaltyDeducted,
      passed,
      defects: defectResults,
      unlocked_competencies: unlocked,
    };

    setEvaluationReport(report);

    // Save attempt to IndexedDB and sync to evidence ledger
    const attemptRecord: ClientScenarioAttemptRecord = {
      attempt_id: `att_${Date.now()}`,
      scenario_id: scenario.id,
      score: netScore,
      max_possible_score: totalMaxPoints,
      passed,
      completed_at: new Date().toISOString(),
      demonstrated_competencies: unlocked,
    };

    try {
      await saveScenarioAttempt(attemptRecord, true);
      if (onAttemptCompleted) {
        onAttemptCompleted(attemptRecord);
      }
    } catch (err) {
      console.error("Failed to persist scenario attempt:", err);
    }
  };

  const flaggedLineSet = useMemo(() => {
    return new Set(flags.map((f) => f.line_number));
  }, [flags]);

  return (
    <div className="space-y-6" data-testid="practice-workspace">
      {/* Scenario Selector Header */}
      <div className="p-4 rounded-control border border-rule bg-sheet space-y-3">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <span className="text-2xs uppercase tracking-wider font-semibold text-span">
              Technical Practice Scenarios (Rule R-CR-11)
            </span>
            <h2 className="text-lg font-serif font-bold text-ink mt-0.5">
              {scenario.title}
            </h2>
            {priorAttempt && (
              <div className="mt-1 text-xs font-medium">
                <span className="text-ok font-semibold">
                  Completed (Score: {priorAttempt.score}/{priorAttempt.max_possible_score})
                </span>
              </div>
            )}
          </div>

          {/* Scenario Tab Pills */}
          <div className="flex items-center gap-2 overflow-x-auto text-xs">
            {CANONICAL_SCENARIOS.map((scen) => (
              <button
                key={scen.id}
                type="button"
                onClick={() => handleSelectScenario(scen.id)}
                className={`px-3 py-1.5 rounded-control font-medium transition-colors shrink-0 ${
                  scen.id === scenario.id
                    ? "bg-span text-on-span font-semibold shadow-sm"
                    : "border border-rule text-ink-2 hover:bg-sunken"
                }`}
              >
                {scen.id}
              </button>
            ))}
          </div>
        </div>

        <p className="text-xs text-ink-2 leading-relaxed">
          {scenario.instructions}
        </p>

        {/* Anti-Credentialism & Anti-Causal Notice (Rules R-CR-11, R-CR-01) */}
        <div className="p-2.5 rounded-control bg-sunken border border-rule text-2xs text-ink-3 flex items-center justify-between">
          <p>
            <strong>Practice Notice:</strong> Capability self-reflection only. Not an exam, certification,
            or appraisal guarantee. Does not promise salary increases.
          </p>
          <span className="text-ok font-medium shrink-0 ml-2">Offline Sandbox Active</span>
        </div>
      </div>

      {/* Evaluation Results Banner (Visible after submission) */}
      {evaluationReport && (
        <div
          role="region"
          aria-label="Scenario scoring report"
          data-testid="scoring-report"
          className={`p-6 rounded-control border ${
            evaluationReport.passed
              ? "bg-ok-wash border-ok text-ink"
              : "bg-paper border-rule text-ink"
          } space-y-4 shadow-sm`}
        >
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-rule pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    evaluationReport.passed
                      ? "bg-ok text-sheet"
                      : "bg-rule-strong text-sheet"
                  }`}
                >
                  {evaluationReport.passed ? "PASSED THRESHOLD" : "PRACTICE COMPLETED"}
                </span>
                <span className="text-xs text-ink-2">
                  Pass Threshold: {scenario.pass_threshold_score.toFixed(1)} / {evaluationReport.max_possible_score.toFixed(1)} pts
                </span>
              </div>
              <h3 className="text-2xl font-serif font-bold text-ink mt-1">
                Net Score: {evaluationReport.score.toFixed(1)} / {evaluationReport.max_possible_score.toFixed(1)} pts
              </h3>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="px-2 py-1 rounded bg-sheet border border-rule text-ink-2">
                Raw: {evaluationReport.raw_score.toFixed(1)}
              </span>
              <span className="px-2 py-1 rounded bg-sheet border border-rule text-alert">
                Penalties: -{evaluationReport.penalty_deducted.toFixed(1)}
              </span>
              <button
                type="button"
                onClick={() => setEvaluationReport(null)}
                className="flex items-center gap-1 px-3 py-1 rounded-control bg-sheet border border-rule-strong text-ink hover:bg-sunken font-medium focus:outline-none focus:ring-2 focus:ring-focus"
              >
                <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Retry</span>
              </button>
            </div>
          </div>

          {/* Unlocked Competencies Banner */}
          {evaluationReport.passed && evaluationReport.unlocked_competencies.length > 0 && (
            <div className="p-3 rounded-control bg-sheet border border-ok text-xs text-ink">
              <strong className="block text-ok font-semibold mb-1">
                Demonstrated Evidence Unlocked in Local Ledger:
              </strong>
              <div className="flex flex-wrap gap-2 pt-1">
                {evaluationReport.unlocked_competencies.map((c) => (
                  <span
                    key={c}
                    className="font-mono text-2xs px-2 py-0.5 rounded bg-ok-wash text-ok font-semibold border border-ok"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Itemized Defect Breakdown */}
          <div className="space-y-2 pt-1">
            <h4 className="text-xs uppercase font-semibold text-ink-2 tracking-wider">
              Itemized Defect Diagnostic Breakdown
            </h4>
            <div className="divide-y divide-rule border border-rule rounded-control bg-sheet overflow-hidden text-xs">
              {evaluationReport.defects.map((d) => (
                <div key={d.defect_id} className="p-3 space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-ink">
                      Line {d.line_number}: {d.title}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full font-semibold text-2xs ${
                        d.match_type === "perfect"
                          ? "bg-ok-wash text-ok"
                          : d.match_type === "partial_category" || d.match_type === "partial_adjacent"
                          ? "bg-caution-wash text-caution"
                          : "bg-sunken text-ink-3"
                      }`}
                    >
                      {d.match_type === "perfect"
                        ? "Full Credit (+1.0)"
                        : d.match_type === "partial_category"
                        ? "Partial: Category Mismatch (+0.5)"
                        : d.match_type === "partial_adjacent"
                        ? "Partial: Adjacent Line (+0.5)"
                        : "Missed (0.0)"}
                    </span>
                  </div>
                  <p className="text-ink-2 text-2xs leading-relaxed">{d.consequence}</p>
                  <p className="text-ink-3 text-2xs italic">
                    Resolution: {d.diagnostic_explanation}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Workspace Split Layout: Code on Left/Top, Console on Right/Bottom */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Code Inspection Viewer (7 cols on lg) */}
        <div className="lg:col-span-7 space-y-3">
          <div className="flex justify-between items-center text-xs">
            <span className="font-semibold text-ink">
              Source Artifact ({scenario.language.toUpperCase()} · {lines.length} lines)
            </span>
            <span className="text-ink-3 text-2xs">Click any line number to flag</span>
          </div>

          <div
            className="p-4 rounded-control border border-rule bg-sunken overflow-x-auto font-mono text-xs leading-relaxed select-none"
            role="region"
            aria-label="Scenario source code artifact"
          >
            {lines.map((codeLine, idx) => {
              const lineNum = idx + 1;
              const isSelected = selectedLine === lineNum;
              const isFlagged = flaggedLineSet.has(lineNum);

              return (
                <div
                  key={lineNum}
                  onClick={() => setSelectedLine(lineNum)}
                  className={`flex items-start cursor-pointer rounded px-1.5 py-0.5 transition-colors ${
                    isSelected
                      ? "bg-span-wash text-span-strong font-semibold"
                      : isFlagged
                      ? "bg-caution-wash text-ink"
                      : "hover:bg-sheet text-ink"
                  }`}
                  data-testid={`code-line-${lineNum}`}
                >
                  <span
                    className={`w-8 text-right pr-3 select-none text-2xs shrink-0 ${
                      isSelected
                        ? "text-span font-bold"
                        : isFlagged
                        ? "text-caution font-bold"
                        : "text-ink-3"
                    }`}
                  >
                    {lineNum}
                  </span>
                  <pre className="font-mono whitespace-pre overflow-visible flex-1">
                    {codeLine || " "}
                  </pre>
                  {isFlagged && (
                    <span className="text-2xs px-1.5 py-0 rounded bg-caution text-sheet font-sans font-bold shrink-0 ml-2">
                      FLAGGED
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Sandbox Toggle & Preview */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setShowSandbox(!showSandbox)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-control border border-rule-strong bg-sheet text-ink hover:bg-sunken text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
            >
              <Play className="w-3.5 h-3.5 text-ok" aria-hidden="true" />
              <span>{showSandbox ? "Hide Sandbox Runner" : "Run in Sandbox (Offline)"}</span>
            </button>

            {showSandbox && scenario.mock_output_headers && (
              <div
                className="mt-3 p-4 rounded-control border border-rule bg-sheet text-xs space-y-2 animate-fadeIn"
                role="region"
                aria-label="Sandbox runtime output"
              >
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-ink">
                    Sandbox Execution Output (Offline SQLite / WASM)
                  </span>
                  <span className="text-2xs px-2 py-0.5 rounded bg-ok-wash text-ok font-medium">
                    Exit Code 0 · 3 records returned
                  </span>
                </div>
                <div className="overflow-x-auto border border-rule rounded-control">
                  <table className="min-w-full text-2xs font-mono">
                    <thead className="bg-sunken border-b border-rule text-ink">
                      <tr>
                        {scenario.mock_output_headers.map((h) => (
                          <th key={h} className="p-2 text-left font-semibold">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-rule bg-sheet text-ink-2">
                      {scenario.mock_output_rows?.map((row, rIdx) => (
                        <tr key={rIdx}>
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="p-2 whitespace-nowrap">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Flagging Console (5 cols on lg) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-5 rounded-control border border-rule bg-sheet space-y-4">
            <h3 className="text-sm font-semibold text-ink flex items-center justify-between">
              <span>Flag Defect on Line {selectedLine}</span>
              <span className="text-2xs text-ink-3 font-normal">Active Selection</span>
            </h3>

            <form onSubmit={handleAddFlag} className="space-y-3">
              <div>
                <label htmlFor="defect-line" className="block text-2xs font-semibold text-ink mb-1">
                  Line Number
                </label>
                <input
                  type="number"
                  id="defect-line"
                  min={1}
                  max={lines.length}
                  value={selectedLine}
                  onChange={(e) => setSelectedLine(Number(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-control border border-rule text-xs bg-paper text-ink focus:outline-none focus:ring-2 focus:ring-focus font-mono"
                />
              </div>

              <div>
                <label htmlFor="defect-category" className="block text-2xs font-semibold text-ink mb-1">
                  Suspected Defect Category
                </label>
                <select
                  id="defect-category"
                  value={categoryInput}
                  onChange={(e) => setCategoryInput(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-control border border-rule text-xs bg-sheet text-ink focus:outline-none focus:ring-2 focus:ring-focus"
                >
                  <option value="division_by_zero">Division by Zero / Unguarded Denominator</option>
                  <option value="lookahead_bias">Lookahead Bias / Future Activity Leakage</option>
                  <option value="aggregation_bias">Aggregation Bias / Extraneous Group Key</option>
                  <option value="sample_ratio_mismatch">Sample Ratio Mismatch / Assignment Bias</option>
                  <option value="data_leakage">Feature Leakage / Premature Pre-filtering</option>
                  <option value="metric_misalignment">Metric Misalignment / Unweighted Mean</option>
                  <option value="syntax_runtime">Syntax or Runtime Exception</option>
                </select>
              </div>

              <div>
                <label htmlFor="defect-rationale" className="block text-2xs font-semibold text-ink mb-1">
                  Diagnostic Reasoning (Optional)
                </label>
                <textarea
                  id="defect-rationale"
                  rows={2}
                  value={rationaleInput}
                  onChange={(e) => setRationaleInput(e.target.value)}
                  placeholder="Explain why this code line is flawed..."
                  className="w-full px-3 py-1.5 rounded-control border border-rule text-xs bg-paper text-ink focus:outline-none focus:ring-2 focus:ring-focus placeholder:text-ink-3"
                />
              </div>

              <button
                type="submit"
                className="w-full flex items-center justify-center gap-1.5 px-4 py-2 rounded-control bg-span text-on-span text-xs font-semibold hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
              >
                <Plus className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Flag Line {selectedLine} as Defect</span>
              </button>
            </form>
          </div>

          {/* Current Candidate Flags List */}
          <div className="p-5 rounded-control border border-rule bg-sheet space-y-3">
            <div className="flex justify-between items-center border-b border-rule pb-2">
              <h4 className="text-xs font-semibold text-ink">
                Candidate Flags ({flags.length})
              </h4>
              <span className="text-2xs text-ink-3">False flags penalize score</span>
            </div>

            {flags.length === 0 ? (
              <p className="text-2xs text-ink-3 py-4 text-center">
                No defects flagged yet. Inspect the source code and flag suspicious lines.
              </p>
            ) : (
              <div className="space-y-2">
                {flags.map((f) => (
                  <div
                    key={f.line_number}
                    className="p-2.5 rounded-control bg-sunken border border-rule flex justify-between items-center text-xs"
                    data-testid={`flag-item-${f.line_number}`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-span">Line {f.line_number}</span>
                        <span className="font-semibold text-ink">{f.category}</span>
                      </div>
                      {f.rationale && (
                        <p className="text-2xs text-ink-3 mt-0.5 italic">{f.rationale}</p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveFlag(f.line_number)}
                      className="p-1 rounded text-alert hover:bg-alert-wash focus:outline-none focus:ring-2 focus:ring-focus"
                      aria-label={`Remove flag on line ${f.line_number}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* False Flag Warning Note (ADR-0013) */}
            <div className="p-2.5 rounded-control bg-paper border border-rule text-2xs text-ink-3 space-y-1">
              <p className="font-semibold text-ink flex items-center gap-1">
                <Shield className="w-3 h-3 text-span" aria-hidden="true" />
                <span>ADR-0013 Deterministic Scoring Safeguards:</span>
              </p>
              <p>
                - Exact Line + Category = 100% points.
                <br />
                - Category mismatch or adjacent line ($\pm 1$) = 50% partial credit.
                <br />
                - False flag penalty: -0.5 pts each (capped at 1.5 pts max).
              </p>
            </div>

            <button
              type="button"
              onClick={handleSubmitAttempt}
              disabled={flags.length === 0}
              className={`w-full py-2.5 rounded-control text-xs font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-focus ${
                flags.length === 0
                  ? "bg-sunken text-ink-3 cursor-not-allowed border border-rule"
                  : "bg-ok text-sheet hover:opacity-90 shadow-sm"
              }`}
            >
              Submit Attempt for Scoring
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PracticeWorkspace;
