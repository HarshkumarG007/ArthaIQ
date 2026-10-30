import React, { useState, useMemo } from "react";
import type { ClientEvidenceRecord } from "../../lib/careerLedger";
import {
  Clock,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Shield,
  ChevronRight,
} from "lucide-react";

export interface RoadmapMilestoneData {
  id: string;
  title: string;
  cluster: string;
  category_label: string;
  min_hours: number;
  max_hours: number;
  learning_difficulty: number;
  application_difficulty: number;
  prerequisite_ids: string[];
  associated_scenario_id?: string;
  associated_scenario_title?: string;
}

export const CANONICAL_ROADMAP_MILESTONES: RoadmapMilestoneData[] = [
  {
    id: "data.gen.l2_prob_decomp",
    title: "Analytical Reasoning and Problem Decomposition",
    cluster: "core_analytics",
    category_label: "Core Relational Analytics",
    min_hours: 15,
    max_hours: 25,
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    prerequisite_ids: [],
  },
  {
    id: "data.gen.l2_ethics",
    title: "Ethical Data Governance and Privacy Safeguards",
    cluster: "data_engineering",
    category_label: "Data Engineering & Governance",
    min_hours: 20,
    max_hours: 35,
    learning_difficulty: 2.0,
    application_difficulty: 3.0,
    prerequisite_ids: [],
  },
  {
    id: "data.anl.l2_sql_basic",
    title: "Relational SQL Querying and Table Joins",
    cluster: "core_analytics",
    category_label: "Core Relational Analytics",
    min_hours: 25,
    max_hours: 40,
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    prerequisite_ids: [],
    associated_scenario_id: "SCEN-DATA-01-SQL",
    associated_scenario_title: "Customer Revenue Aggregation & Leakage",
  },
  {
    id: "data.anl.l2_eda",
    title: "Exploratory Data Analysis and Distributions",
    cluster: "statistical_modeling",
    category_label: "Statistical Modeling",
    min_hours: 20,
    max_hours: 35,
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    prerequisite_ids: [],
    associated_scenario_id: "SCEN-DATA-02-EDA",
    associated_scenario_title: "Cohort Churn Pre-filtering & Imputation",
  },
  {
    id: "data.anl.l2_hygiene",
    title: "Data Hygiene and Anomaly Auditing",
    cluster: "core_analytics",
    category_label: "Core Relational Analytics",
    min_hours: 20,
    max_hours: 35,
    learning_difficulty: 2.0,
    application_difficulty: 3.0,
    prerequisite_ids: ["data.anl.l2_sql_basic"],
  },
  {
    id: "data.anl.l3_dashboard",
    title: "Dashboard Architecture and Business Metric Design",
    cluster: "business_communication",
    category_label: "Problem Structuring & Communication",
    min_hours: 25,
    max_hours: 40,
    learning_difficulty: 2.0,
    application_difficulty: 3.0,
    prerequisite_ids: ["data.anl.l2_eda", "data.anl.l2_sql_basic"],
  },
  {
    id: "data.anl.l3_sql_adv",
    title: "Advanced SQL Window Functions and Partitions",
    cluster: "core_analytics",
    category_label: "Core Relational Analytics",
    min_hours: 30,
    max_hours: 50,
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    prerequisite_ids: ["data.anl.l2_sql_basic"],
    associated_scenario_id: "SCEN-DATA-01-SQL",
    associated_scenario_title: "Customer Revenue Aggregation & Leakage",
  },
  {
    id: "data.gen.l3_docs",
    title: "Technical Documentation and Reproducibility Standards",
    cluster: "business_communication",
    category_label: "Problem Structuring & Communication",
    min_hours: 15,
    max_hours: 25,
    learning_difficulty: 2.0,
    application_difficulty: 3.0,
    prerequisite_ids: ["data.gen.l2_prob_decomp"],
  },
  {
    id: "data.gen.l3_stakeholder",
    title: "Stakeholder Uncertainty and Evidence Communication",
    cluster: "business_communication",
    category_label: "Problem Structuring & Communication",
    min_hours: 30,
    max_hours: 45,
    learning_difficulty: 3.0,
    application_difficulty: 4.0,
    prerequisite_ids: ["data.gen.l2_prob_decomp"],
  },
  {
    id: "data.sci.l3_exp_design",
    title: "Statistical Hypothesis Testing and A/B Experimentation",
    cluster: "experimentation",
    category_label: "Experimentation & Causal Inference",
    min_hours: 35,
    max_hours: 55,
    learning_difficulty: 3.0,
    application_difficulty: 4.0,
    prerequisite_ids: ["data.anl.l2_eda"],
    associated_scenario_id: "SCEN-DATA-03-EXP",
    associated_scenario_title: "A/B Test Ratio Mismatch & Sequential Peeking",
  },
  {
    id: "data.sci.l3_ml_supervised",
    title: "Supervised Predictive Modeling and Cross-Validation",
    cluster: "statistical_modeling",
    category_label: "Statistical Modeling",
    min_hours: 40,
    max_hours: 65,
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    prerequisite_ids: ["data.anl.l2_eda"],
    associated_scenario_id: "SCEN-DATA-02-EDA",
    associated_scenario_title: "Cohort Churn Pre-filtering & Imputation",
  },
  {
    id: "data.sci.l3_feat_eng",
    title: "Feature Engineering and Leakage Isolation",
    cluster: "data_engineering",
    category_label: "Data Engineering & Governance",
    min_hours: 35,
    max_hours: 55,
    learning_difficulty: 3.0,
    application_difficulty: 4.0,
    prerequisite_ids: ["data.anl.l2_hygiene", "data.sci.l3_ml_supervised"],
  },
  {
    id: "data.sci.l4_bigdata",
    title: "Distributed Big Data Processing with Spark",
    cluster: "data_engineering",
    category_label: "Data Engineering & Governance",
    min_hours: 50,
    max_hours: 90,
    learning_difficulty: 4.0,
    application_difficulty: 5.0,
    prerequisite_ids: ["data.anl.l3_sql_adv", "data.sci.l3_feat_eng"],
  },
  {
    id: "data.sci.l4_causal",
    title: "Causal Inference and Observational Study Design",
    cluster: "experimentation",
    category_label: "Experimentation & Causal Inference",
    min_hours: 60,
    max_hours: 100,
    learning_difficulty: 4.0,
    application_difficulty: 5.0,
    prerequisite_ids: ["data.sci.l3_exp_design"],
    associated_scenario_id: "SCEN-DATA-03-EXP",
    associated_scenario_title: "A/B Test Ratio Mismatch & Sequential Peeking",
  },
];

export const PACING_OPTIONS = [
  { hours: 5, label: "Casual", description: "5 hours / week (Balanced pace)" },
  { hours: 10, label: "Recommended", description: "10 hours / week (Optimal progress)" },
  { hours: 15, label: "Accelerated", description: "15 hours / week (Fast-track study)" },
  { hours: 20, label: "Intensive", description: "20 hours / week (Full-immersion pace)" },
];

interface RoadmapViewProps {
  initialWeeklyHours?: number;
  records?: ClientEvidenceRecord[];
  onNavigatePractice?: (scenarioId?: string) => void;
  onNavigateSkills?: () => void;
}

export function RoadmapView({
  initialWeeklyHours = 10,
  records = [],
  onNavigatePractice,
  onNavigateSkills,
}: RoadmapViewProps): React.JSX.Element {
  const [weeklyHours, setWeeklyHours] = useState<number>(initialWeeklyHours);
  const [filterState, setFilterState] = useState<"all" | "unproven" | "actionable">("all");

  // Map of verified competency states
  const recordMap = useMemo(() => {
    const map = new Map<string, "demonstrated" | "self_reported">();
    for (const r of records) {
      if (r.verification_state === "demonstrated") {
        map.set(r.competency_id, "demonstrated");
      } else if (r.verification_state === "self_reported" && !map.has(r.competency_id)) {
        map.set(r.competency_id, "self_reported");
      }
    }
    return map;
  }, [records]);

  // Index map of canonical milestones to find step numbers for prerequisites
  const milestoneIndexMap = useMemo(() => {
    const map = new Map<string, { stepNumber: number; title: string }>();
    CANONICAL_ROADMAP_MILESTONES.forEach((m, idx) => {
      map.set(m.id, { stepNumber: idx + 1, title: m.title });
    });
    return map;
  }, []);

  // Compute enriched milestone data
  const enrichedMilestones = useMemo(() => {
    return CANONICAL_ROADMAP_MILESTONES.map((m, idx) => {
      const stepNumber = idx + 1;
      const state = recordMap.get(m.id) ?? "unproven";
      const isDemonstrated = state === "demonstrated";
      const isSelfReported = state === "self_reported";
      const isUnproven = state === "unproven";

      // Prerequisite satisfaction check
      const prereqsSatisfied = m.prerequisite_ids.every((pid) => recordMap.has(pid));
      const isActionable = isUnproven && prereqsSatisfied;

      // Build prerequisite display labels
      const prerequisiteLabels = m.prerequisite_ids.map((pid) => {
        const info = milestoneIndexMap.get(pid);
        return info ? `Step ${info.stepNumber} (${info.title})` : pid;
      });

      return {
        ...m,
        stepNumber,
        state,
        isDemonstrated,
        isSelfReported,
        isUnproven,
        prereqsSatisfied,
        isActionable,
        prerequisiteLabels,
      };
    });
  }, [recordMap, milestoneIndexMap]);

  // Filtered milestones based on tab selection
  const displayedMilestones = useMemo(() => {
    if (filterState === "unproven") {
      return enrichedMilestones.filter((m) => m.isUnproven);
    }
    if (filterState === "actionable") {
      return enrichedMilestones.filter((m) => m.isActionable);
    }
    return enrichedMilestones;
  }, [enrichedMilestones, filterState]);

  // Calculate cumulative effort and weeks projection
  const unprovenMilestones = useMemo(() => {
    return enrichedMilestones.filter((m) => m.isUnproven);
  }, [enrichedMilestones]);

  const totalMinHours = useMemo(() => {
    return unprovenMilestones.reduce((acc, m) => acc + m.min_hours, 0);
  }, [unprovenMilestones]);

  const totalMaxHours = useMemo(() => {
    return unprovenMilestones.reduce((acc, m) => acc + m.max_hours, 0);
  }, [unprovenMilestones]);

  const estimatedMinWeeks = useMemo(() => {
    if (totalMinHours === 0) return 0;
    return Math.ceil(totalMinHours / weeklyHours);
  }, [totalMinHours, weeklyHours]);

  const estimatedMaxWeeks = useMemo(() => {
    if (totalMaxHours === 0) return 0;
    return Math.ceil(totalMaxHours / weeklyHours);
  }, [totalMaxHours, weeklyHours]);

  // Counts
  const demonstratedCount = enrichedMilestones.filter((m) => m.isDemonstrated).length;
  const selfReportedCount = enrichedMilestones.filter((m) => m.isSelfReported).length;
  const unprovenCount = unprovenMilestones.length;

  return (
    <div className="space-y-6" data-testid="roadmap-view">
      {/* Header & Section Title */}
      <div className="p-6 rounded-control border border-rule bg-sheet space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <span className="text-2xs uppercase tracking-wider font-semibold text-span">
              Topological Roadmap Plan (Rule R-CR-05)
            </span>
            <h2 className="text-xl font-serif font-bold text-ink mt-0.5">
              Topological Roadmap & Calibrated Effort Estimator
            </h2>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="px-2.5 py-1 rounded bg-sunken text-ink-2 border border-rule">
              {demonstratedCount} Demonstrated
            </span>
            <span className="px-2.5 py-1 rounded bg-caution-wash text-caution border border-rule">
              {selfReportedCount} Self-Reported
            </span>
            <span className="px-2.5 py-1 rounded bg-span-wash text-span-strong border border-rule font-medium">
              {unprovenCount} Unproven Gaps
            </span>
          </div>
        </div>

        <p className="text-xs text-ink-2 leading-relaxed">
          Milestones are strictly scheduled in dependency-respecting topological order. Prerequisites appear
          prior to dependent competencies. Pacing adjustments dynamically scale transition timelines.
        </p>

        {/* Weekly Study Budget Pacing Selector */}
        <div className="pt-2 border-t border-rule space-y-3">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
            <label
              htmlFor="pacing-slider"
              className="text-xs font-semibold text-ink flex items-center gap-1.5"
            >
              <Clock className="w-3.5 h-3.5 text-span" aria-hidden="true" />
              <span>Available Study Hours / Week:</span>
              <span className="font-mono text-span font-bold ml-1">{weeklyHours} hours/week</span>
            </label>

            <span className="text-2xs text-ink-3">
              {PACING_OPTIONS.find((p) => p.hours === weeklyHours)?.label ?? "Custom"} Pace
            </span>
          </div>

          {/* Quick Option Segment Pills */}
          <div
            className="grid grid-cols-2 sm:grid-cols-4 gap-2"
            role="radiogroup"
            aria-label="Weekly study hours options"
          >
            {PACING_OPTIONS.map((opt) => (
              <button
                key={opt.hours}
                type="button"
                role="radio"
                aria-checked={weeklyHours === opt.hours}
                onClick={() => setWeeklyHours(opt.hours)}
                className={`p-2.5 rounded-control text-left border transition-colors ${
                  weeklyHours === opt.hours
                    ? "bg-span-wash border-span text-span-strong font-semibold shadow-sm"
                    : "bg-paper border-rule text-ink-2 hover:bg-sunken"
                }`}
              >
                <div className="text-xs font-bold">{opt.hours} h / week</div>
                <div className="text-2xs text-ink-3">{opt.label}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Cumulative Projection Banner */}
        <div
          className="p-4 rounded-control bg-paper border border-rule flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
          role="region"
          aria-label="Cumulative effort and timeline projection"
        >
          <div className="space-y-1">
            <span className="text-2xs uppercase tracking-wider font-semibold text-ink-3">
              Projected Timeline & Effort (Heuristic Bounds)
            </span>
            <div className="flex items-baseline gap-3">
              <h3 className="text-2xl font-serif font-bold text-ink" data-testid="projected-timeline">
                {unprovenCount === 0 ? (
                  <span className="text-ok">0 weeks (All competencies verified)</span>
                ) : (
                  <span>
                    {estimatedMinWeeks} – {estimatedMaxWeeks} weeks
                  </span>
                )}
              </h3>
              {unprovenCount > 0 && (
                <span className="text-xs text-ink-2 font-mono">
                  ({totalMinHours} – {totalMaxHours} total hours)
                </span>
              )}
            </div>
          </div>

          <div className="text-right text-2xs text-ink-3">
            <span className="block font-medium text-ink-2">
              Based on {unprovenCount} unproven forward milestones
            </span>
            <span>Allocating {weeklyHours} hours each calendar week</span>
          </div>
        </div>

        {/* Heuristic & Anti-Causal Notice (Rules R-CR-01, R-CR-05) */}
        <div className="p-3 rounded-control bg-sunken border border-rule text-2xs text-ink-3 flex items-start gap-2">
          <Shield className="w-4 h-4 text-span shrink-0 mt-0.5" aria-hidden="true" />
          <p>
            <strong className="font-semibold text-ink">Statutory Heuristic Disclaimer (Rule R-CR-05):</strong>{" "}
            Estimated effort ranges are calibrated heuristic models based on domain syllabus depth. Learning
            competencies or completing scenarios does NOT promise, calculate, or guarantee salary increases
            or job offers (Consumer Protection Act, 2019).
          </p>
        </div>
      </div>

      {/* Filter Tabs for Milestones */}
      <div className="flex items-center justify-between gap-3 border-b border-rule pb-2 text-xs">
        <div className="flex items-center gap-2" role="tablist" aria-label="Milestone filter tabs">
          <button
            type="button"
            role="tab"
            aria-selected={filterState === "all"}
            onClick={() => setFilterState("all")}
            className={`px-3 py-1.5 rounded-control font-medium transition-colors ${
              filterState === "all"
                ? "bg-span text-on-span font-semibold"
                : "border border-rule text-ink-2 hover:bg-sunken"
            }`}
          >
            All Milestones ({enrichedMilestones.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={filterState === "unproven"}
            onClick={() => setFilterState("unproven")}
            className={`px-3 py-1.5 rounded-control font-medium transition-colors ${
              filterState === "unproven"
                ? "bg-span text-on-span font-semibold"
                : "border border-rule text-ink-2 hover:bg-sunken"
            }`}
          >
            Unproven Forward Gaps ({unprovenCount})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={filterState === "actionable"}
            onClick={() => setFilterState("actionable")}
            className={`px-3 py-1.5 rounded-control font-medium transition-colors ${
              filterState === "actionable"
                ? "bg-span text-on-span font-semibold"
                : "border border-rule text-ink-2 hover:bg-sunken"
            }`}
          >
            Ready to Start ({enrichedMilestones.filter((m) => m.isActionable).length})
          </button>
        </div>

        {onNavigateSkills && (
          <button
            type="button"
            onClick={onNavigateSkills}
            className="flex items-center gap-1 text-span hover:underline font-semibold text-xs"
          >
            <span>View Full Gap Map</span>
            <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        )}
      </div>

      {/* Sequential Milestone Cards */}
      <div className="space-y-3" data-testid="milestones-list">
        {displayedMilestones.map((m) => (
          <div
            key={m.id}
            data-testid={`milestone-step-${m.stepNumber}`}
            className={`p-4 rounded-control border transition-all ${
              m.isDemonstrated
                ? "bg-ok-wash/40 border-ok text-ink"
                : m.isActionable
                ? "bg-sheet border-span shadow-sm"
                : "bg-sheet border-rule text-ink"
            }`}
          >
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-2xs font-bold px-2 py-0.5 rounded bg-sunken text-ink border border-rule">
                    Step {m.stepNumber}
                  </span>
                  <span className="text-2xs font-semibold uppercase tracking-wider text-ink-3">
                    {m.category_label}
                  </span>

                  {/* Status Badge */}
                  {m.isDemonstrated ? (
                    <span className="flex items-center gap-1 text-2xs font-semibold px-2 py-0.5 rounded-full bg-ok text-sheet">
                      <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                      <span>Demonstrated</span>
                    </span>
                  ) : m.isSelfReported ? (
                    <span className="flex items-center gap-1 text-2xs font-semibold px-2 py-0.5 rounded-full bg-caution-wash text-caution border border-rule">
                      <AlertCircle className="w-3 h-3" aria-hidden="true" />
                      <span>Self-Reported</span>
                    </span>
                  ) : m.isActionable ? (
                    <span className="text-2xs font-bold px-2 py-0.5 rounded-full bg-span text-on-span">
                      Ready to Learn
                    </span>
                  ) : (
                    <span className="text-2xs font-medium px-2 py-0.5 rounded-full bg-sunken text-ink-3">
                      Prerequisites Pending
                    </span>
                  )}
                </div>

                <h3 className="text-base font-serif font-bold text-ink">
                  {m.title}
                </h3>
              </div>

              {/* Effort Range Pill */}
              <div className="flex items-center gap-2 shrink-0">
                <div className="text-right">
                  <span className="text-xs font-mono font-bold text-ink block">
                    {m.min_hours}–{m.max_hours} hours
                  </span>
                  <span className="text-2xs text-ink-3 italic">
                    Heuristic Range
                  </span>
                </div>
              </div>
            </div>

            {/* Prerequisites & Practice Actions */}
            <div className="mt-3 pt-3 border-t border-rule flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-xs">
              <div className="text-ink-2">
                <span className="text-2xs font-semibold uppercase tracking-wider text-ink-3 mr-1">
                  Prerequisites:
                </span>
                {m.prerequisiteLabels.length === 0 ? (
                  <span className="text-2xs text-ink-3 font-medium">None (Foundational entry point)</span>
                ) : (
                  <span className="text-2xs font-mono text-ink-2">
                    {m.prerequisiteLabels.join(", ")}
                  </span>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 shrink-0">
                {m.associated_scenario_id && onNavigatePractice && (
                  <button
                    type="button"
                    onClick={() => onNavigatePractice(m.associated_scenario_id)}
                    className="flex items-center gap-1 px-3 py-1 rounded-control bg-paper hover:bg-sunken border border-rule text-ink text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-focus"
                  >
                    <span>Practice Flaw-Finding</span>
                    <ArrowRight className="w-3 h-3 text-span" aria-hidden="true" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RoadmapView;
