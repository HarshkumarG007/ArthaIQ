import React, { useState, useMemo } from "react";
import type { ClientEvidenceRecord } from "../../lib/careerLedger";
import {
  Compass,
  GitBranch,
  Clock,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Shield,
  Layers,
  Sparkles,
} from "lucide-react";

export type CorridorId = "SWE_TO_MLAI" | "DATA_TO_MLAI" | "SWE_TO_DATA";

export interface CrossFamilyMilestone {
  id: string;
  title: string;
  cluster: string;
  categoryLabel: string;
  sourceFamily: string;
  targetFamily: string;
  minHours: number;
  maxHours: number;
  isBridge: boolean;
  bridgeRationale?: string;
  scenarioId?: string;
  scenarioTitle?: string;
  prerequisites: string[];
}

export interface CorridorConfig {
  id: CorridorId;
  label: string;
  sourceFamily: string;
  targetFamily: string;
  targetRoleTitle: string;
  description: string;
  benchmarks: {
    metro: string;
    level: string;
    p10: number;
    p50: number;
    p90: number;
  };
  milestones: CrossFamilyMilestone[];
}

export const CANONICAL_CORRIDORS: Record<CorridorId, CorridorConfig> = {
  SWE_TO_MLAI: {
    id: "SWE_TO_MLAI",
    label: "Software Engineering → ML/AI Systems",
    sourceFamily: "SWE",
    targetFamily: "MLAI",
    targetRoleTitle: "Senior Machine Learning & AI Systems Engineer (L4)",
    description:
      "Transition from backend software engineering into high-throughput machine learning infrastructure, model serving, and LLM guardrails.",
    benchmarks: {
      metro: "Bengaluru",
      level: "L4 Senior",
      p10: 34.5,
      p50: 48.0,
      p90: 68.5,
    },
    milestones: [
      {
        id: "data.anl.l2_eda",
        title: "Exploratory Data Analysis & Statistics",
        cluster: "data_foundations",
        categoryLabel: "Data Foundations (Bridge)",
        sourceFamily: "DATA",
        targetFamily: "MLAI",
        minHours: 20,
        maxHours: 35,
        isBridge: true,
        bridgeRationale:
          "Connects software data structures to empirical distributions, outlier detection, and sampling variance.",
        scenarioId: "SCEN-DATA-02-EDA",
        scenarioTitle: "Cohort Churn Pre-filtering & Imputation",
        prerequisites: [],
      },
      {
        id: "data.sci.l3_exp_design",
        title: "Experiment Design & Causal Inference",
        cluster: "data_foundations",
        categoryLabel: "Data Foundations (Bridge)",
        sourceFamily: "DATA",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 45,
        isBridge: true,
        bridgeRationale:
          "Bridges backend telemetry to hypothesis testing, A/B evaluation, and statistical significance.",
        scenarioId: "SCEN-DATA-03-EXP",
        scenarioTitle: "A/B Experiment Ratio Mismatch & Sequential Peeking",
        prerequisites: ["data.anl.l2_eda"],
      },
      {
        id: "mlai.core.l2_neural_backprop",
        title: "Tensor Graph Execution & Autograd",
        cluster: "ml_core",
        categoryLabel: "Machine Learning Core",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 40,
        isBridge: false,
        scenarioId: "SCEN-MLAI-01-TENS",
        scenarioTitle: "Computational Graph Detachment & Backprop Zero-Grad",
        prerequisites: [],
      },
      {
        id: "mlai.core.l3_repr_learning",
        title: "High-Dimensional Embeddings & Vector Indexing",
        cluster: "ml_core",
        categoryLabel: "Machine Learning Core",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 45,
        isBridge: false,
        scenarioId: "SCEN-MLAI-04-VEC",
        scenarioTitle: "HNSW Vector Indexing & Cosine Distance Normalization",
        prerequisites: ["mlai.core.l2_neural_backprop"],
      },
      {
        id: "mlai.core.l3_transformer_attn",
        title: "Transformer Attention & Context Windows",
        cluster: "ml_core",
        categoryLabel: "Machine Learning Core",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 30,
        maxHours: 50,
        isBridge: false,
        scenarioId: "SCEN-MLAI-02-LEAK",
        scenarioTitle: "Causal Mask Inversion & Token Context Horizon",
        prerequisites: ["mlai.core.l2_neural_backprop"],
      },
      {
        id: "mlai.ops.l4_dist_training",
        title: "Distributed Training & OpenMP/NCCL Scaling",
        cluster: "ml_infrastructure",
        categoryLabel: "ML Systems & Operations",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 35,
        maxHours: 60,
        isBridge: false,
        scenarioId: "SCEN-MLAI-05-DIST",
        scenarioTitle: "AllReduce Deadlock & Mixed Precision Gradient Overflow",
        prerequisites: ["mlai.core.l3_transformer_attn"],
      },
      {
        id: "mlai.eval.l3_conformal_calib",
        title: "Conformal Calibration & Covariate Shift Audit",
        cluster: "ml_evaluation",
        categoryLabel: "Evaluation & Quality",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 45,
        isBridge: false,
        scenarioId: "SCEN-MLAI-06-DRIFT",
        scenarioTitle: "Population Shift & Conformal Non-Conformity Coverage",
        prerequisites: ["data.sci.l3_exp_design"],
      },
      {
        id: "mlai.gen.l3_guardrails",
        title: "Adversarial Prompt Defenses & Output Guardrails",
        cluster: "generative_ai",
        categoryLabel: "Generative AI Engineering",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 30,
        maxHours: 50,
        isBridge: false,
        scenarioId: "SCEN-MLAI-07-GUARD",
        scenarioTitle: "Indirect Prompt Injection & System Delimiter Escapes",
        prerequisites: ["mlai.core.l3_transformer_attn"],
      },
      {
        id: "mlai.ops.l4_quant_serving",
        title: "Low-Latency Serving & Model Quantization",
        cluster: "ml_infrastructure",
        categoryLabel: "ML Systems & Operations",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 35,
        maxHours: 60,
        isBridge: false,
        scenarioId: "SCEN-MLAI-03-DEPLOY",
        scenarioTitle: "INT8 TensorRT Inference & KV-Cache Fragmentation",
        prerequisites: ["mlai.ops.l4_dist_training"],
      },
    ],
  },
  DATA_TO_MLAI: {
    id: "DATA_TO_MLAI",
    label: "Data Science → Machine Learning / AI",
    sourceFamily: "DATA",
    targetFamily: "MLAI",
    targetRoleTitle: "Machine Learning Research Engineer (L4)",
    description:
      "Bridge from exploratory statistics and classical modeling into deep neural network architectures, vector representations, and scalable inference systems.",
    benchmarks: {
      metro: "Bengaluru",
      level: "L4 Senior",
      p10: 32.0,
      p50: 46.5,
      p90: 64.0,
    },
    milestones: [
      {
        id: "swe.core.l2_data_structures",
        title: "Algorithms & In-Memory Data Structures",
        cluster: "systems_foundation",
        categoryLabel: "Systems Foundations (Bridge)",
        sourceFamily: "SWE",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 40,
        isBridge: true,
        bridgeRationale:
          "Connects data science dataframe manipulation to memory-efficient tree and hash data structures.",
        prerequisites: [],
      },
      {
        id: "swe.core.l2_concurrency",
        title: "Concurrency & Asynchronous Execution",
        cluster: "systems_foundation",
        categoryLabel: "Systems Foundations (Bridge)",
        sourceFamily: "SWE",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 45,
        isBridge: true,
        bridgeRationale:
          "Essential prerequisite for multi-threaded dataloaders and asynchronous model serving.",
        scenarioId: "SCEN-SWE-01-CONCUR",
        scenarioTitle: "Thread Pool Deadlock & Unsafe Race In Global State",
        prerequisites: ["swe.core.l2_data_structures"],
      },
      {
        id: "mlai.core.l2_neural_backprop",
        title: "Tensor Graph Execution & Autograd",
        cluster: "ml_core",
        categoryLabel: "Machine Learning Core",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 40,
        isBridge: false,
        scenarioId: "SCEN-MLAI-01-TENS",
        scenarioTitle: "Computational Graph Detachment & Backprop Zero-Grad",
        prerequisites: [],
      },
      {
        id: "mlai.core.l3_repr_learning",
        title: "High-Dimensional Embeddings & Vector Indexing",
        cluster: "ml_core",
        categoryLabel: "Machine Learning Core",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 45,
        isBridge: false,
        scenarioId: "SCEN-MLAI-04-VEC",
        scenarioTitle: "HNSW Vector Indexing & Cosine Distance Normalization",
        prerequisites: ["mlai.core.l2_neural_backprop"],
      },
      {
        id: "mlai.core.l3_transformer_attn",
        title: "Transformer Attention & Context Windows",
        cluster: "ml_core",
        categoryLabel: "Machine Learning Core",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 30,
        maxHours: 50,
        isBridge: false,
        scenarioId: "SCEN-MLAI-02-LEAK",
        scenarioTitle: "Causal Mask Inversion & Token Context Horizon",
        prerequisites: ["mlai.core.l2_neural_backprop"],
      },
      {
        id: "mlai.eval.l3_conformal_calib",
        title: "Conformal Calibration & Covariate Shift Audit",
        cluster: "ml_evaluation",
        categoryLabel: "Evaluation & Quality",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 25,
        maxHours: 45,
        isBridge: false,
        scenarioId: "SCEN-MLAI-06-DRIFT",
        scenarioTitle: "Population Shift & Conformal Non-Conformity Coverage",
        prerequisites: [],
      },
      {
        id: "mlai.gen.l3_guardrails",
        title: "Adversarial Prompt Defenses & Output Guardrails",
        cluster: "generative_ai",
        categoryLabel: "Generative AI Engineering",
        sourceFamily: "MLAI",
        targetFamily: "MLAI",
        minHours: 30,
        maxHours: 50,
        isBridge: false,
        scenarioId: "SCEN-MLAI-07-GUARD",
        scenarioTitle: "Indirect Prompt Injection & System Delimiter Escapes",
        prerequisites: ["mlai.core.l3_transformer_attn"],
      },
    ],
  },
  SWE_TO_DATA: {
    id: "SWE_TO_DATA",
    label: "Software Engineering → Data Engineering",
    sourceFamily: "SWE",
    targetFamily: "DATA",
    targetRoleTitle: "Senior Data & Analytics Systems Engineer (L4)",
    description:
      "Transition from application backend services into enterprise data pipelines, partitioned columnar stores, and large-scale analytical architectures.",
    benchmarks: {
      metro: "Bengaluru",
      level: "L4 Senior",
      p10: 28.0,
      p50: 42.0,
      p90: 58.0,
    },
    milestones: [
      {
        id: "data.anl.l2_sql_basic",
        title: "Relational SQL Querying & Joins",
        cluster: "core_analytics",
        categoryLabel: "Core Relational Analytics",
        sourceFamily: "DATA",
        targetFamily: "DATA",
        minHours: 25,
        maxHours: 40,
        isBridge: false,
        scenarioId: "SCEN-DATA-01-SQL",
        scenarioTitle: "Customer Revenue Aggregation & Leakage",
        prerequisites: [],
      },
      {
        id: "swe.db.l3_query_perf",
        title: "Database Indexing & Query Plan Optimization",
        cluster: "systems_foundation",
        categoryLabel: "Systems Foundations (Bridge)",
        sourceFamily: "SWE",
        targetFamily: "DATA",
        minHours: 25,
        maxHours: 45,
        isBridge: true,
        bridgeRationale:
          "Applies database execution plans and B-tree indexing to large-scale analytical warehousing queries.",
        scenarioId: "SCEN-SWE-03-DB",
        scenarioTitle: "Unindexed Foreign Key Lock Escalation & N+1",
        prerequisites: ["data.anl.l2_sql_basic"],
      },
      {
        id: "data.gen.l2_prob_decomp",
        title: "Analytical Reasoning & Problem Decomposition",
        cluster: "core_analytics",
        categoryLabel: "Core Relational Analytics",
        sourceFamily: "DATA",
        targetFamily: "DATA",
        minHours: 15,
        maxHours: 25,
        isBridge: false,
        scenarioId: "SCEN-DATA-04-DECOMP",
        scenarioTitle: "Product Metric Decomposition & Conversion",
        prerequisites: [],
      },
      {
        id: "data.gen.l2_ethics",
        title: "Data Ingestion & Privacy Guardrails",
        cluster: "data_engineering",
        categoryLabel: "Data Engineering & Governance",
        sourceFamily: "DATA",
        targetFamily: "DATA",
        minHours: 20,
        maxHours: 35,
        isBridge: false,
        scenarioId: "SCEN-DATA-05-ETHICS",
        scenarioTitle: "Data Ingestion Pipeline & Privacy Guardrails",
        prerequisites: [],
      },
      {
        id: "data.sci.l3_feat_eng",
        title: "Feature Pipeline Engineering & Preprocessing",
        cluster: "data_engineering",
        categoryLabel: "Data Engineering & Governance",
        sourceFamily: "DATA",
        targetFamily: "DATA",
        minHours: 25,
        maxHours: 45,
        isBridge: false,
        scenarioId: "SCEN-DATA-06-FEATENG",
        scenarioTitle: "Feature Leakage & Out-of-Fold Preprocessing",
        prerequisites: ["data.anl.l2_sql_basic"],
      },
      {
        id: "data.sci.l4_bigdata",
        title: "Distributed Big Data Architectures & Partitioning",
        cluster: "data_engineering",
        categoryLabel: "Data Engineering & Governance",
        sourceFamily: "DATA",
        targetFamily: "DATA",
        minHours: 35,
        maxHours: 60,
        isBridge: false,
        scenarioId: "SCEN-DATA-07-BIGDATA",
        scenarioTitle: "Distributed Join Skew & Shuffle Partition Overflow",
        prerequisites: ["data.sci.l3_feat_eng"],
      },
    ],
  },
};

interface CrossFamilyPathwayNavigatorProps {
  evidenceRecords?: ClientEvidenceRecord[];
  onSelectScenario?: (scenarioId: string) => void;
}

export function CrossFamilyPathwayNavigator({
  evidenceRecords = [],
  onSelectScenario,
}: CrossFamilyPathwayNavigatorProps): React.JSX.Element {
  const [selectedCorridorId, setSelectedCorridorId] = useState<CorridorId>("SWE_TO_MLAI");
  const [weeklyHours, setWeeklyHours] = useState<number>(10);
  const [hideDemonstrated, setHideDemonstrated] = useState<boolean>(false);

  const activeCorridor = CANONICAL_CORRIDORS[selectedCorridorId];

  // Map of demonstrated competency IDs from on-device evidence ledger
  const demonstratedMap = useMemo(() => {
    const map = new Map<string, boolean>();
    evidenceRecords.forEach((r) => {
      if (r.verification_state === "demonstrated") {
        map.set(r.competency_id, true);
      }
    });
    return map;
  }, [evidenceRecords]);

  // Filtered milestones based on toggle
  const visibleMilestones = useMemo(() => {
    if (!hideDemonstrated) return activeCorridor.milestones;
    return activeCorridor.milestones.filter((m) => !demonstratedMap.get(m.id));
  }, [activeCorridor, hideDemonstrated, demonstratedMap]);

  // Cumulative heuristic effort calculations
  const totalEffort = useMemo(() => {
    const minH = visibleMilestones.reduce((acc, m) => acc + m.minHours, 0);
    const maxH = visibleMilestones.reduce((acc, m) => acc + m.maxHours, 0);
    const minW = Math.max(1, Math.ceil(minH / weeklyHours));
    const maxW = Math.max(1, Math.ceil(maxH / weeklyHours));
    const bridgeCount = visibleMilestones.filter((m) => m.isBridge).length;

    return {
      minHours: minH,
      maxHours: maxH,
      minWeeks: minW,
      maxWeeks: maxW,
      bridgeCount,
      totalCount: visibleMilestones.length,
    };
  }, [visibleMilestones, weeklyHours]);

  return (
    <div className="space-y-8" data-testid="cross-family-navigator">
      {/* Header Banner */}
      <div className="bg-slate-900 text-white rounded-xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-semibold tracking-wide uppercase border border-indigo-500/30">
              <Compass className="w-3.5 h-3.5" />
              <span>Multi-Family Career Pathways</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Cross-Family Transition Navigator
            </h2>
            <p className="text-slate-300 max-w-2xl text-sm sm:text-base">
              Synthesize topologically ordered, acyclic learning corridors across Software
              Engineering, Data Science, and Machine Learning systems with calibrated effort bounds.
            </p>
          </div>

          <div className="bg-slate-800/80 p-4 rounded-lg border border-slate-700 space-y-2 text-xs sm:text-sm">
            <div className="flex items-center gap-2 text-slate-300">
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>Deterministic Topological DAG</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Bridge Competency Acceleration</span>
            </div>
          </div>
        </div>
      </div>

      {/* Corridor Selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <label className="block text-sm font-semibold text-slate-900" id="corridor-selector-label">
          Select Transition Corridor
        </label>
        <div
          className="grid grid-cols-1 md:grid-cols-3 gap-3"
          role="radiogroup"
          aria-labelledby="corridor-selector-label"
        >
          {(Object.keys(CANONICAL_CORRIDORS) as CorridorId[]).map((cid) => {
            const corridor = CANONICAL_CORRIDORS[cid];
            const isSelected = selectedCorridorId === cid;
            return (
              <button
                key={cid}
                type="button"
                role="radio"
                aria-checked={isSelected}
                onClick={() => setSelectedCorridorId(cid)}
                className={`p-4 rounded-xl border text-left transition-all ${
                  isSelected
                    ? "border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-600/20 shadow-sm"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                    <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200">
                      {corridor.sourceFamily}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                    <span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 border border-indigo-200">
                      {corridor.targetFamily}
                    </span>
                  </div>
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-indigo-600 animate-pulse" />
                  )}
                </div>
                <div className="font-semibold text-slate-900 text-sm">{corridor.label}</div>
                <div className="text-xs text-slate-500 mt-1 line-clamp-2">
                  {corridor.description}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Pacing & Filter Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weekly Budget Slider */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label
                htmlFor="pacing-slider"
                className="text-sm font-semibold text-slate-900 flex items-center gap-2"
              >
                <Clock className="w-4 h-4 text-indigo-600" />
                Weekly Study Commitment
              </label>
              <p className="text-xs text-slate-500 mt-0.5">
                Adjust dedicated learning hours to recalibrate estimated completion timeline.
              </p>
            </div>
            <div className="text-right">
              <span className="text-xl font-bold text-indigo-600">{weeklyHours}</span>
              <span className="text-xs text-slate-500 ml-1">hrs / week</span>
            </div>
          </div>

          <div className="space-y-2">
            <input
              id="pacing-slider"
              type="range"
              min={5}
              max={20}
              step={5}
              value={weeklyHours}
              onChange={(e) => setWeeklyHours(Number(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
              aria-label="Weekly study hours"
            />
            <div className="flex justify-between text-xs font-medium text-slate-400 px-1">
              <span>5 h/wk (Casual)</span>
              <span>10 h/wk (Standard)</span>
              <span>15 h/wk (Focused)</span>
              <span>20 h/wk (Accelerated)</span>
            </div>
          </div>
        </div>

        {/* Filter & Progress Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between space-y-4">
          <div>
            <div className="text-sm font-semibold text-slate-900 mb-1">Evidence Ledger Sync</div>
            <p className="text-xs text-slate-500">
              Filter demonstrated competencies tracked on your local browser ledger.
            </p>
          </div>

          <label className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 cursor-pointer transition-colors">
            <input
              type="checkbox"
              checked={hideDemonstrated}
              onChange={(e) => setHideDemonstrated(e.target.checked)}
              className="w-4 h-4 rounded text-indigo-600 accent-indigo-600"
            />
            <span className="text-xs font-medium text-slate-700">
              Hide proven competencies ({demonstratedMap.size} demonstrated)
            </span>
          </label>
        </div>
      </div>

      {/* Pathway Summary Metrics Bar */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5 shadow-sm">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center sm:text-left">
          <div className="border-r border-indigo-200/60 last:border-0 pr-2">
            <div className="text-xs font-medium text-indigo-700 uppercase tracking-wider">
              Corridor Milestones
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-0.5">
              {totalEffort.totalCount}{" "}
              <span className="text-xs font-normal text-slate-500">steps</span>
            </div>
          </div>

          <div className="border-r border-indigo-200/60 last:border-0 pr-2">
            <div className="text-xs font-medium text-amber-700 uppercase tracking-wider flex items-center gap-1 justify-center sm:justify-start">
              <span>Bridge Skills</span>
              <Sparkles className="w-3 h-3 text-amber-500" />
            </div>
            <div className="text-2xl font-bold text-amber-700 mt-0.5">
              {totalEffort.bridgeCount}{" "}
              <span className="text-xs font-normal text-slate-500">nodes</span>
            </div>
          </div>

          <div className="border-r border-indigo-200/60 last:border-0 pr-2">
            <div className="text-xs font-medium text-indigo-700 uppercase tracking-wider">
              Heuristic Effort
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-0.5">
              {totalEffort.minHours}–{totalEffort.maxHours}{" "}
              <span className="text-xs font-normal text-slate-500">hrs</span>
            </div>
          </div>

          <div>
            <div className="text-xs font-medium text-indigo-700 uppercase tracking-wider">
              Projected Timeline
            </div>
            <div className="text-2xl font-bold text-indigo-700 mt-0.5">
              {totalEffort.minWeeks}–{totalEffort.maxWeeks}{" "}
              <span className="text-xs font-normal text-slate-500">weeks</span>
            </div>
          </div>
        </div>
      </div>

      {/* Milestone Step Flow */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-600" />
            <span>Topological Milestone Sequence</span>
          </h3>
          <span className="text-xs text-slate-500">
            Ordered strictly by prerequisite dependencies
          </span>
        </div>

        <div className="space-y-3">
          {visibleMilestones.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-xl border border-dashed border-slate-300 text-slate-500 space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
              <div className="font-semibold text-slate-800">All corridor milestones demonstrated!</div>
              <p className="text-xs">
                You have demonstrated all competencies in this corridor in your local evidence ledger.
              </p>
            </div>
          ) : (
            visibleMilestones.map((m, idx) => {
              const isDemonstrated = demonstratedMap.get(m.id);
              return (
                <div
                  key={m.id}
                  className={`bg-white rounded-xl border p-5 transition-all shadow-sm ${
                    m.isBridge
                      ? "border-amber-200 hover:border-amber-300 bg-amber-50/20"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                  data-testid={`milestone-${m.id}`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="px-2 py-0.5 text-xs font-bold rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                          Step {idx + 1}
                        </span>

                        {m.isBridge && (
                          <span
                            className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded-md bg-amber-100 text-amber-800 border border-amber-200"
                            data-testid="bridge-badge"
                          >
                            <Sparkles className="w-3 h-3 text-amber-600" />
                            Bridge Competency ({m.sourceFamily} → {m.targetFamily})
                          </span>
                        )}

                        <span className="text-xs font-medium text-slate-500 px-2 py-0.5 bg-slate-50 rounded border border-slate-200">
                          {m.categoryLabel}
                        </span>

                        {isDemonstrated && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-md bg-emerald-100 text-emerald-800 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            Demonstrated
                          </span>
                        )}
                      </div>

                      <h4 className="text-base font-bold text-slate-900">{m.title}</h4>

                      {m.bridgeRationale && (
                        <p className="text-xs text-amber-900/80 bg-amber-50 p-2 rounded border border-amber-200/50 mt-1">
                          <strong>Bridge rationale:</strong> {m.bridgeRationale}
                        </p>
                      )}

                      {m.prerequisites.length > 0 && (
                        <div className="text-xs text-slate-500 pt-1 flex items-center gap-1">
                          <GitBranch className="w-3 h-3" />
                          <span>Requires: {m.prerequisites.join(", ")}</span>
                        </div>
                      )}
                    </div>

                    {/* Effort & Scenario Actions */}
                    <div className="flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-3 pt-3 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                      <div className="text-right">
                        <div className="text-xs font-semibold text-slate-700">
                          {m.minHours}–{m.maxHours} hrs
                        </div>
                        <div className="text-[10px] text-slate-400 uppercase tracking-wider">
                          Heuristic
                        </div>
                      </div>

                      {m.scenarioId && (
                        <button
                          type="button"
                          onClick={() => onSelectScenario && onSelectScenario(m.scenarioId!)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold border border-indigo-200 transition-colors"
                          aria-label={`Launch practice scenario for ${m.title}`}
                        >
                          <span>Practice Flaw-Finding</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Decoupled Compensation Context (Two Streams Two Places) */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">
              Target Market Compensation Distribution (Decoupled Evidence)
            </h3>
          </div>
          <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
            Stream A: Market Pay
          </span>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed">
          The compensation figures below reflect empirical macroeconomic distributions for{" "}
          <strong>{activeCorridor.targetRoleTitle}</strong> in {activeCorridor.benchmarks.metro}{" "}
          ({activeCorridor.benchmarks.level}) derived from verified corporate remuneration
          disclosures and voluntary reports.
        </p>

        {/* Quantile Interval Card */}
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
          <div className="text-xs text-slate-500 mb-2">
            Empirical Market Benchmark (Guaranteed Cash Annual, LPA):
          </div>
          <div className="flex items-center justify-between text-center sm:text-left gap-4">
            <div>
              <div className="text-[11px] text-slate-400 uppercase font-semibold">P10 (Entry)</div>
              <div className="text-lg font-bold text-slate-800">
                ₹{activeCorridor.benchmarks.p10.toFixed(1)} LPA
              </div>
            </div>
            <div className="h-8 w-px bg-slate-300" />
            <div>
              <div className="text-[11px] text-indigo-600 uppercase font-semibold">P50 (Median)</div>
              <div className="text-xl font-extrabold text-indigo-700">
                ₹{activeCorridor.benchmarks.p50.toFixed(1)} LPA
              </div>
            </div>
            <div className="h-8 w-px bg-slate-300" />
            <div>
              <div className="text-[11px] text-slate-400 uppercase font-semibold">P90 (Senior)</div>
              <div className="text-lg font-bold text-slate-800">
                ₹{activeCorridor.benchmarks.p90.toFixed(1)} LPA
              </div>
            </div>
          </div>
        </div>

        {/* Mandatory Statutory Disclaimer (Rule R-CR-01) */}
        <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>Statutory Disclosure (India Consumer Protection Act 2019):</strong> Completing
            practice scenarios or acquiring cross-family competencies does not guarantee salary
            increases, job offers, or promotions. Compensation is governed by macroeconomic market
            dynamics, organizational structures, and verified individual performance.
          </p>
        </div>
      </div>
    </div>
  );
}
