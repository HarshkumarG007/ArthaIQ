import React, { useState, useMemo } from "react";
import {
  saveLedgerRecord,
  deleteLedgerRecord,
  type ClientEvidenceRecord,
} from "../../lib/careerLedger";
import { CheckCircle2, AlertCircle, Clock, Shield, Search, Filter } from "lucide-react";

export interface CompetencyDataNode {
  id: string;
  title: string;
  category:
    | "core_analytics"
    | "statistical_modeling"
    | "data_engineering"
    | "business_communication"
    | "experimentation"
    | "systems_architecture"
    | "application_development"
    | "testing_quality"
    | "security_reliability"
    | "dev_workflow"
    | string;
  category_label: string;
  description: string;
  target_levels: number[];
  prerequisite_ids: string[];
  learning_difficulty: number;
  application_difficulty: number;
  provenance: {
    source_id: string;
    license: string;
    attribution_text: string;
  };
}

export const CANONICAL_DATA_COMPETENCIES: CompetencyDataNode[] = [
  {
    id: "data.anl.l2_eda",
    title: "Exploratory Data Analysis and Distributions",
    category: "statistical_modeling",
    category_label: "Statistical Modeling",
    description: "Conduct exploratory analysis, assess central tendencies, empirical distributions, and identify anomalies or skewness.",
    target_levels: [2],
    prerequisite_ids: [],
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.anl.l2_sql_basic",
    title: "Relational SQL Querying and Table Joins",
    category: "core_analytics",
    category_label: "Core Relational Analytics",
    description: "Formulate efficient relational queries, table joins, group-by aggregations, and filtered views for analytical reporting.",
    target_levels: [2],
    prerequisite_ids: [],
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.anl.l2_hygiene",
    title: "Data Hygiene and Anomaly Auditing",
    category: "core_analytics",
    category_label: "Core Relational Analytics",
    description: "Inspect raw datasets for schema drift, null rates, duplicated keys, and distributional outliers prior to aggregation.",
    target_levels: [2, 3],
    prerequisite_ids: ["data.anl.l2_sql_basic"],
    learning_difficulty: 2.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.anl.l3_dashboard",
    title: "Dashboard Architecture and Business Metric Design",
    category: "business_communication",
    category_label: "Problem Structuring & Communication",
    description: "Design responsive dashboards and self-serve reporting views translating business questions into operational KPIs.",
    target_levels: [3],
    prerequisite_ids: ["data.anl.l2_eda", "data.anl.l2_sql_basic"],
    learning_difficulty: 2.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.anl.l3_sql_adv",
    title: "Advanced SQL Window Functions and Partitions",
    category: "core_analytics",
    category_label: "Core Relational Analytics",
    description: "Apply analytical window functions (ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD), cumulative sums, and complex partition frames.",
    target_levels: [3],
    prerequisite_ids: ["data.anl.l2_sql_basic"],
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.gen.l2_ethics",
    title: "Ethical Data Governance and Privacy Safeguards",
    category: "data_engineering",
    category_label: "Data Engineering & Governance",
    description: "Apply privacy-by-design safeguards, statutory DPDP Act 2023 compliance, PII anonymization, and data retention quarantine.",
    target_levels: [2, 3, 4],
    prerequisite_ids: [],
    learning_difficulty: 1.0,
    application_difficulty: 2.0,
    provenance: {
      source_id: "ESCO-v1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences and Occupations (ESCO v1.1.1). Commission Decision 2011/833/EU.",
    },
  },
  {
    id: "data.gen.l2_prob_decomp",
    title: "Analytical Reasoning and Problem Decomposition",
    category: "core_analytics",
    category_label: "Core Relational Analytics",
    description: "Structure ambiguous business dilemmas into solvable analytical sub-problems with testable hypotheses and measurable deliverables.",
    target_levels: [2, 3],
    prerequisite_ids: [],
    learning_difficulty: 2.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ESCO-v1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences and Occupations (ESCO v1.1.1). Commission Decision 2011/833/EU.",
    },
  },
  {
    id: "data.gen.l3_docs",
    title: "Technical Documentation and Reproducibility Standards",
    category: "business_communication",
    category_label: "Problem Structuring & Communication",
    description: "Author repeatable analytical runbooks, reproducible notebooks, versioned data contracts, and technical specifications.",
    target_levels: [3, 4],
    prerequisite_ids: ["data.gen.l2_prob_decomp"],
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    provenance: {
      source_id: "ESCO-v1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences and Occupations (ESCO v1.1.1). Commission Decision 2011/833/EU.",
    },
  },
  {
    id: "data.gen.l3_stakeholder",
    title: "Stakeholder Uncertainty and Evidence Communication",
    category: "business_communication",
    category_label: "Problem Structuring & Communication",
    description: "Communicate statistical quantile intervals, confidence limits, model boundaries, and honest abstentions to executive leaders.",
    target_levels: [3, 4],
    prerequisite_ids: ["data.gen.l2_prob_decomp"],
    learning_difficulty: 3.0,
    application_difficulty: 4.0,
    provenance: {
      source_id: "ESCO-v1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences and Occupations (ESCO v1.1.1). Commission Decision 2011/833/EU.",
    },
  },
  {
    id: "data.sci.l3_exp_design",
    title: "Statistical Hypothesis Testing and A/B Experimentation",
    category: "experimentation",
    category_label: "Experimentation & Causal Inference",
    description: "Formulate randomized control trials, detect sample ratio mismatches (SRM), compute sample size power, and control false discovery.",
    target_levels: [3],
    prerequisite_ids: ["data.anl.l2_eda"],
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.sci.l3_ml_supervised",
    title: "Supervised Predictive Modeling and Cross-Validation",
    category: "statistical_modeling",
    category_label: "Statistical Modeling",
    description: "Train tabular predictive models (GBDT/CatBoost/LightGBM), configure nested grouped-temporal cross-validation, and evaluate loss curves.",
    target_levels: [3],
    prerequisite_ids: ["data.anl.l2_eda"],
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.sci.l3_feat_eng",
    title: "Feature Engineering and Leakage Isolation",
    category: "data_engineering",
    category_label: "Data Engineering & Governance",
    description: "Engineer temporal lag features, frequency encoding, out-of-fold statistics, and rigorously eliminate lookahead target leakage.",
    target_levels: [3, 4],
    prerequisite_ids: ["data.anl.l2_hygiene", "data.sci.l3_ml_supervised"],
    learning_difficulty: 3.0,
    application_difficulty: 4.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.sci.l4_bigdata",
    title: "Distributed Big Data Processing with Spark",
    category: "data_engineering",
    category_label: "Data Engineering & Governance",
    description: "Engineer resilient PySpark distributed pipelines, optimize shuffle partitions, mitigate data skew, and manage parquet lakehouses.",
    target_levels: [4],
    prerequisite_ids: ["data.anl.l3_sql_adv", "data.sci.l3_feat_eng"],
    learning_difficulty: 4.0,
    application_difficulty: 4.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "data.sci.l4_causal",
    title: "Causal Inference and Observational Study Design",
    category: "experimentation",
    category_label: "Experimentation & Causal Inference",
    description: "Estimate causal treatment effects under unconfoundedness using propensity score weighting, difference-in-differences, and synthetic controls.",
    target_levels: [4],
    prerequisite_ids: ["data.sci.l3_exp_design"],
    learning_difficulty: 4.0,
    application_difficulty: 5.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
];

export const CANONICAL_SWE_COMPETENCIES: CompetencyDataNode[] = [
  {
    id: "swe.gen.l2_git_hygiene",
    title: "Git Workflow and Trunk-Based Hygiene",
    category: "dev_workflow",
    category_label: "Developer Workflow & DevOps",
    description: "Maintain clean trunk-based commit histories, atomic diffs, interactive rebase conflict resolution, and pull request hygiene.",
    target_levels: [2, 3],
    prerequisite_ids: [],
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    provenance: {
      source_id: "ESCO-1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences, Qualifications and Occupations (ESCO v1.1.1), European Commission. Reused and adapted under European Commission open reuse policy (Decision 2011/833/EU).",
    },
  },
  {
    id: "swe.core.l2_data_structures",
    title: "Algorithmic Complexity and Core Data Structures",
    category: "systems_architecture",
    category_label: "Systems Architecture",
    description: "Analyze asymptotic time and space complexity, hash collision strategies, and tree/graph representations for low-latency execution.",
    target_levels: [2, 3],
    prerequisite_ids: [],
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.core.l2_concurrency",
    title: "Concurrency Primitives and Thread Safety",
    category: "systems_architecture",
    category_label: "Systems Architecture",
    description: "Design multithreaded and asynchronous routines using mutexes, read-write locks, atomic variables, and deadlock detection.",
    target_levels: [2, 3],
    prerequisite_ids: ["swe.core.l2_data_structures"],
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.arch.l2_api_design",
    title: "Contract-First API Architecture and Idempotency",
    category: "application_development",
    category_label: "Application Development",
    description: "Design REST and gRPC API contracts with RFC 9457 problem details, semantic versioning, and strict idempotency keys for mutative endpoints.",
    target_levels: [2, 3],
    prerequisite_ids: [],
    learning_difficulty: 2.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.test.l2_unit_tdd",
    title: "Automated Unit Testing and Test Isolation",
    category: "testing_quality",
    category_label: "Testing & Quality",
    description: "Author deterministic unit test suites with test doubles, hermetic fixture isolation, property testing, and high statement coverage.",
    target_levels: [2, 3],
    prerequisite_ids: [],
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    provenance: {
      source_id: "ESCO-1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences, Qualifications and Occupations (ESCO v1.1.1), European Commission. Reused and adapted under European Commission open reuse policy (Decision 2011/833/EU).",
    },
  },
  {
    id: "swe.ops.l2_container_docker",
    title: "Container Packaging and Minimal Base Images",
    category: "dev_workflow",
    category_label: "Developer Workflow & DevOps",
    description: "Author multi-stage container builds, non-root user execution, minimal attack surfaces, and reproducible image digest pinning.",
    target_levels: [2, 3],
    prerequisite_ids: [],
    learning_difficulty: 2.0,
    application_difficulty: 2.0,
    provenance: {
      source_id: "ESCO-1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences, Qualifications and Occupations (ESCO v1.1.1), European Commission. Reused and adapted under European Commission open reuse policy (Decision 2011/833/EU).",
    },
  },
  {
    id: "swe.core.l3_memory_perf",
    title: "Memory Profiling and Resource Management",
    category: "systems_architecture",
    category_label: "Systems Architecture",
    description: "Profile process heap allocation, identify memory leaks, manage connection lifecycles, and optimize allocator throughput.",
    target_levels: [3, 4],
    prerequisite_ids: ["swe.core.l2_concurrency"],
    learning_difficulty: 3.0,
    application_difficulty: 4.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.arch.l3_microservices",
    title: "Microservice Resiliency and Fault Isolation",
    category: "application_development",
    category_label: "Application Development",
    description: "Implement circuit breakers, exponential backoff, bulkhead isolation, and graceful degradation in distributed microservices.",
    target_levels: [3, 4],
    prerequisite_ids: ["swe.arch.l2_api_design"],
    learning_difficulty: 3.0,
    application_difficulty: 4.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.db.l3_query_perf",
    title: "Relational Indexing and Query Performance",
    category: "application_development",
    category_label: "Application Development",
    description: "Optimize database query execution plans, design composite B-tree indexes, resolve table lock contention, and prevent N+1 query patterns.",
    target_levels: [3, 4],
    prerequisite_ids: ["swe.arch.l2_api_design"],
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.sec.l3_owasp_top10",
    title: "Web Application Security and Input Sanitization",
    category: "security_reliability",
    category_label: "Security & Reliability",
    description: "Enforce OWASP Top 10 defenses including parametrized SQL statements, CSP headers, CSRF tokens, SSRF protection, and cryptographically secure tokens.",
    target_levels: [3, 4],
    prerequisite_ids: ["swe.arch.l2_api_design", "swe.test.l2_unit_tdd"],
    learning_difficulty: 3.0,
    application_difficulty: 4.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.rel.l3_observability",
    title: "Telemetry, Structured Logging and Distributed Tracing",
    category: "security_reliability",
    category_label: "Security & Reliability",
    description: "Instrument services with OpenTelemetry traces, RED metric collection, and correlation IDs across asynchronous log streams.",
    target_levels: [3, 4],
    prerequisite_ids: ["swe.arch.l2_api_design"],
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ESCO-1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences, Qualifications and Occupations (ESCO v1.1.1), European Commission. Reused and adapted under European Commission open reuse policy (Decision 2011/833/EU).",
    },
  },
  {
    id: "swe.ops.l3_cicd_pipeline",
    title: "Hermetic CI/CD Pipelines and Automated Rollback",
    category: "dev_workflow",
    category_label: "Developer Workflow & DevOps",
    description: "Configure reproducible deployment pipelines with canary gates, automated health checks, zero-downtime rollouts, and rollback triggers.",
    target_levels: [3, 4],
    prerequisite_ids: ["swe.gen.l2_git_hygiene", "swe.ops.l2_container_docker", "swe.test.l2_unit_tdd"],
    learning_difficulty: 3.0,
    application_difficulty: 3.0,
    provenance: {
      source_id: "ESCO-1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences, Qualifications and Occupations (ESCO v1.1.1), European Commission. Reused and adapted under European Commission open reuse policy (Decision 2011/833/EU).",
    },
  },
  {
    id: "swe.sys.l4_dist_consensus",
    title: "Distributed Consensus and Replicated State",
    category: "systems_architecture",
    category_label: "Systems Architecture",
    description: "Evaluate distributed consensus protocols (Raft, Paxos), split-brain scenarios, leader election timeouts, and linearizable consistency.",
    target_levels: [4],
    prerequisite_ids: ["swe.core.l3_memory_perf", "swe.arch.l3_microservices"],
    learning_difficulty: 4.0,
    application_difficulty: 5.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.arch.l4_event_driven",
    title: "Event-Driven Architecture and Asynchronous Messaging",
    category: "application_development",
    category_label: "Application Development",
    description: "Architect transactional outbox patterns, message deduplication, at-least-once delivery guarantees, and dead-letter queue handling.",
    target_levels: [4],
    prerequisite_ids: ["swe.arch.l3_microservices", "swe.db.l3_query_perf"],
    learning_difficulty: 4.0,
    application_difficulty: 4.0,
    provenance: {
      source_id: "ONET-28.0",
      license: "CC-BY-4.0",
      attribution_text: "Source: O*NET 28.0 Database by USDOL/ETA. Used under CC BY 4.0 license. Restructured by ArthaIQ for career intelligence.",
    },
  },
  {
    id: "swe.sec.l4_crypto_dpdp",
    title: "Cryptographic Privacy and Verifiable Purge Operations",
    category: "security_reliability",
    category_label: "Security & Reliability",
    description: "Implement envelope encryption, keyed hash message authentication, and verifiable zero-byte hard deletion under DPDP Act 2023 Sec 12.",
    target_levels: [4],
    prerequisite_ids: ["swe.sec.l3_owasp_top10"],
    learning_difficulty: 4.0,
    application_difficulty: 5.0,
    provenance: {
      source_id: "ESCO-1.1.1",
      license: "EU-OPEN-REUSE",
      attribution_text: "Source: European Skills, Competences, Qualifications and Occupations (ESCO v1.1.1), European Commission. Reused and adapted under European Commission open reuse policy (Decision 2011/833/EU).",
    },
  },
];

interface GapMapViewProps {
  records: ClientEvidenceRecord[];
  onRecordUpdated?: () => void;
  onNavigatePractice?: (scenarioId?: string) => void;
  roleFamily?: string;
}

export function GapMapView({
  records,
  onRecordUpdated,
  onNavigatePractice,
  roleFamily = "DATA",
}: GapMapViewProps): React.JSX.Element {
  const [activeFamily, setActiveFamily] = useState<string>(roleFamily || "DATA");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "gaps" | "actionable">("all");
  const [provenanceModalNode, setProvenanceModalNode] = useState<CompetencyDataNode | null>(null);

  const activeCompetencies = useMemo(() => {
    return activeFamily.toUpperCase() === "SWE"
      ? CANONICAL_SWE_COMPETENCIES
      : CANONICAL_DATA_COMPETENCIES;
  }, [activeFamily]);

  const allCompetenciesMap = useMemo(() => {
    const map = new Map<string, CompetencyDataNode>();
    for (const c of CANONICAL_DATA_COMPETENCIES) map.set(c.id, c);
    for (const c of CANONICAL_SWE_COMPETENCIES) map.set(c.id, c);
    return map;
  }, []);

  const availableCategories = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of activeCompetencies) {
      map.set(c.category, c.category_label);
    }
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }));
  }, [activeCompetencies]);

  // Map of competency ID to client evidence record
  const recordsMap = useMemo(() => {
    const map = new Map<string, ClientEvidenceRecord>();
    for (const r of records) {
      map.set(r.competency_id, r);
    }
    return map;
  }, [records]);

  // Check if prerequisites for a node are satisfied
  const checkPrerequisites = (node: CompetencyDataNode): { satisfied: boolean; missing: string[] } => {
    const missing: string[] = [];
    for (const prereqId of node.prerequisite_ids) {
      const rec = recordsMap.get(prereqId);
      if (!rec || (rec.verification_state !== "demonstrated" && rec.verification_state !== "self_reported")) {
        const prereqNode = allCompetenciesMap.get(prereqId);
        missing.push(prereqNode ? prereqNode.title : prereqId);
      }
    }
    return { satisfied: missing.length === 0, missing };
  };

  // Toggle self-attestation
  const handleToggleAttestation = async (node: CompetencyDataNode): Promise<void> => {
    const current = recordsMap.get(node.id);
    const now = new Date().toISOString();

    if (current && current.verification_state === "self_reported") {
      // Clear back to unproven
      await deleteLedgerRecord(node.id);
    } else {
      // Set to self_reported
      await saveLedgerRecord({
        competency_id: node.id,
        verification_state: "self_reported",
        evidence_type: "self_attestation",
        created_at: current?.created_at || now,
        updated_at: now,
        metadata: { source: "client_gap_map_toggle" },
        recheck_suggested: false,
      });
    }

    if (onRecordUpdated) {
      onRecordUpdated();
    }
  };

  // Filtered competencies
  const filteredNodes = useMemo(() => {
    return activeCompetencies.filter((node) => {
      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesQuery =
          node.title.toLowerCase().includes(q) ||
          node.id.toLowerCase().includes(q) ||
          node.description.toLowerCase().includes(q);
        if (!matchesQuery) return false;
      }

      // Category filter
      if (selectedCategory !== "all" && node.category !== selectedCategory) {
        return false;
      }

      // Status filter
      const record = recordsMap.get(node.id);
      const isDemonstrated = record?.verification_state === "demonstrated";
      const isSelfReported = record?.verification_state === "self_reported";
      const isUnproven = !isDemonstrated && !isSelfReported;
      const { satisfied } = checkPrerequisites(node);

      if (statusFilter === "gaps") {
        return isUnproven;
      }
      if (statusFilter === "actionable") {
        return isUnproven && satisfied;
      }

      return true;
    });
  }, [activeCompetencies, searchQuery, selectedCategory, statusFilter, recordsMap]);

  // Statistics
  const totalCount = activeCompetencies.length;
  const demonstratedCount = activeCompetencies.filter(
    (n) => recordsMap.get(n.id)?.verification_state === "demonstrated"
  ).length;
  const selfReportedCount = activeCompetencies.filter(
    (n) => recordsMap.get(n.id)?.verification_state === "self_reported"
  ).length;
  const unprovenCount = Math.max(0, totalCount - (demonstratedCount + selfReportedCount));
  const actionableCount = activeCompetencies.filter((n) => {
    const isUnproven = !recordsMap.get(n.id) || recordsMap.get(n.id)?.verification_state === "unproven";
    return isUnproven && checkPrerequisites(n).satisfied;
  }).length;

  return (
    <div className="space-y-6" data-testid="gap-map-view">
      {/* Family Switcher */}
      <div className="flex items-center gap-2" role="group" aria-label="Role family selector">
        <span className="text-2xs font-semibold uppercase text-ink-3">Family:</span>
        <button
          type="button"
          onClick={() => {
            setActiveFamily("DATA");
            setSelectedCategory("all");
          }}
          className={`px-3 py-1 rounded-control text-xs font-semibold transition-colors ${
            activeFamily.toUpperCase() === "DATA"
              ? "bg-span text-on-span shadow-xs"
              : "border border-rule text-ink-2 hover:bg-sunken"
          }`}
          aria-label="View Data & AI competencies"
        >
          Data & AI ({CANONICAL_DATA_COMPETENCIES.length})
        </button>
        <button
          type="button"
          onClick={() => {
            setActiveFamily("SWE");
            setSelectedCategory("all");
          }}
          className={`px-3 py-1 rounded-control text-xs font-semibold transition-colors ${
            activeFamily.toUpperCase() === "SWE"
              ? "bg-span text-on-span shadow-xs"
              : "border border-rule text-ink-2 hover:bg-sunken"
          }`}
          aria-label="View Software Engineering competencies"
        >
          Software Engineering ({CANONICAL_SWE_COMPETENCIES.length})
        </button>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-control border border-rule bg-sheet">
          <span className="text-2xs font-semibold uppercase tracking-wider text-ink-3">
            Demonstrated
          </span>
          <p className="text-2xl font-serif font-bold text-ok mt-1">
            {demonstratedCount}
            <span className="text-xs font-sans font-normal text-ink-2 ml-1">/ {totalCount}</span>
          </p>
          <p className="text-2xs text-ink-3 mt-1">Practice scenarios</p>
        </div>

        <div className="p-4 rounded-control border border-rule bg-sheet">
          <span className="text-2xs font-semibold uppercase tracking-wider text-ink-3">
            Self-Reported
          </span>
          <p className="text-2xl font-serif font-bold text-caution mt-1">
            {selfReportedCount}
            <span className="text-xs font-sans font-normal text-ink-2 ml-1">/ {totalCount}</span>
          </p>
          <p className="text-2xs text-ink-3 mt-1">Production experience</p>
        </div>

        <div className="p-4 rounded-control border border-rule bg-sheet">
          <span className="text-2xs font-semibold uppercase tracking-wider text-ink-3">
            Unproven Gaps
          </span>
          <p className="text-2xl font-serif font-bold text-ink mt-1">
            {unprovenCount}
            <span className="text-xs font-sans font-normal text-ink-2 ml-1">/ {totalCount}</span>
          </p>
          <p className="text-2xs text-ink-3 mt-1">Need evidence</p>
        </div>

        <div className="p-4 rounded-control border border-rule bg-sheet">
          <span className="text-2xs font-semibold uppercase tracking-wider text-span">
            Actionable Next
          </span>
          <p className="text-2xl font-serif font-bold text-span mt-1">
            {actionableCount}
            <span className="text-xs font-sans font-normal text-ink-2 ml-1">unlocked</span>
          </p>
          <p className="text-2xs text-ink-3 mt-1">Prerequisites clear</p>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="p-4 rounded-control border border-rule bg-sheet space-y-3">
        <div className="flex flex-col sm:flex-row gap-3 justify-between items-stretch sm:items-center">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-ink-3" aria-hidden="true" />
            <input
              type="text"
              id="gap-map-search"
              aria-label="Filter competencies by keyword or code"
              placeholder="Search competencies (e.g. SQL, EDA, Spark)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-control border border-rule text-ink bg-paper text-xs placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-focus"
            />
          </div>

          {/* Status Segment Filter */}
          <div className="flex items-center gap-1 p-1 rounded-control bg-sunken border border-rule shrink-0 text-xs">
            <button
              type="button"
              onClick={() => setStatusFilter("all")}
              aria-pressed={statusFilter === "all"}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                statusFilter === "all"
                  ? "bg-sheet text-ink font-semibold shadow-sm"
                  : "text-ink-2 hover:text-ink"
              }`}
            >
              All ({totalCount})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("actionable")}
              aria-pressed={statusFilter === "actionable"}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                statusFilter === "actionable"
                  ? "bg-sheet text-span font-semibold shadow-sm"
                  : "text-ink-2 hover:text-ink"
              }`}
            >
              Actionable ({actionableCount})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("gaps")}
              aria-pressed={statusFilter === "gaps"}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${
                statusFilter === "gaps"
                  ? "bg-sheet text-ink font-semibold shadow-sm"
                  : "text-ink-2 hover:text-ink"
              }`}
            >
              Gaps Only ({unprovenCount})
            </button>
          </div>
        </div>

        {/* Cluster Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pt-1 text-2xs">
          <Filter className="w-3.5 h-3.5 text-ink-3 shrink-0" aria-hidden="true" />
          <button
            type="button"
            onClick={() => setSelectedCategory("all")}
            className={`px-2.5 py-1 rounded-full border transition-colors shrink-0 ${
              selectedCategory === "all"
                ? "border-span bg-span text-on-span font-semibold"
                : "border-rule text-ink-2 bg-sheet hover:bg-sunken"
            }`}
          >
            All Clusters
          </button>
          {availableCategories.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-2.5 py-1 rounded-full border transition-colors shrink-0 ${
                selectedCategory === cat.value
                  ? "border-span bg-span text-on-span font-semibold"
                  : "border-rule text-ink-2 bg-sheet hover:bg-sunken"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Skill Span Rows List */}
      <div className="space-y-3" role="list" aria-label="Competency Skill Span Rows">
        {filteredNodes.length === 0 ? (
          <div className="p-8 text-center border border-dashed border-rule rounded-control bg-sheet text-ink-3 text-xs">
            No competencies match your filter. Reset search or category filters to view full graph.
          </div>
        ) : (
          filteredNodes.map((node) => {
            const record = recordsMap.get(node.id);
            const isDemonstrated = record?.verification_state === "demonstrated";
            const isSelfReported = record?.verification_state === "self_reported";
            const isUnproven = !isDemonstrated && !isSelfReported;
            const { satisfied, missing } = checkPrerequisites(node);
            const isStale = record?.recheck_suggested === true;

            const stateText = isDemonstrated
              ? "Demonstrated"
              : isSelfReported
              ? "Self-reported"
              : "Unproven";

            const levelText = node.target_levels.map((lvl) => `L${lvl}`).join(", ");

            return (
              <div
                key={node.id}
                role="listitem"
                data-testid={`skill-row-${node.id}`}
                className="p-4 rounded-control border border-rule bg-sheet transition-colors hover:border-rule-strong space-y-3"
              >
                {/* Header row: ID, Title, Level, Cluster */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-semibold text-span">
                      {node.id}
                    </span>
                    <span className="text-2xs px-2 py-0.5 rounded font-medium bg-sunken text-ink-2">
                      {levelText}
                    </span>
                    <span className="text-2xs px-2 py-0.5 rounded font-medium bg-paper border border-rule text-ink-3">
                      {node.category_label}
                    </span>
                    {isStale && (
                      <span className="flex items-center gap-1 text-2xs px-2 py-0.5 rounded font-medium bg-caution-wash text-caution border border-caution">
                        <Clock className="w-3 h-3" aria-hidden="true" />
                        <span>Recheck suggested</span>
                      </span>
                    )}
                  </div>

                  {/* Verification State Badge */}
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                        isDemonstrated
                          ? "bg-ok-wash text-ok border-ok"
                          : isSelfReported
                          ? "bg-caution-wash text-caution border-caution"
                          : "bg-sunken text-ink-2 border-rule"
                      }`}
                    >
                      {isDemonstrated ? (
                        <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                      ) : isSelfReported ? (
                        <Shield className="w-3.5 h-3.5" aria-hidden="true" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
                      )}
                      <span>{stateText}</span>
                    </span>
                  </div>
                </div>

                {/* Title and Description */}
                <div>
                  <h3 className="text-sm font-semibold text-ink">{node.title}</h3>
                  <p className="text-xs text-ink-2 mt-1 leading-relaxed">
                    {node.description}
                  </p>
                </div>

                {/* Prerequisite status bar */}
                <div className="text-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-rule text-ink-3">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-ink">Prerequisites:</span>
                    {node.prerequisite_ids.length === 0 ? (
                      <span className="text-ok font-medium">None (Root entry node)</span>
                    ) : satisfied ? (
                      <span className="text-ok font-medium">All satisfied</span>
                    ) : (
                      <span className="text-alert font-medium">
                        Blocked by: {missing.join(", ")}
                      </span>
                    )}
                  </div>

                  {/* Accessible Plain-Text Equivalent (Rule R-UI-01) */}
                  <span className="sr-only">
                    Required {levelText}, state: {stateText}, prerequisites:{" "}
                    {satisfied ? "satisfied" : `blocked by ${missing.join(", ")}`}.
                  </span>

                  {/* Interactive Action Controls */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setProvenanceModalNode(node)}
                      className="px-2 py-0.5 rounded border border-rule text-ink-2 hover:bg-sunken text-2xs font-medium focus:outline-none focus:ring-2 focus:ring-focus"
                      aria-label={`View provenance for ${node.title}`}
                    >
                      Provenance
                    </button>

                    {isUnproven && (
                      <button
                        type="button"
                        onClick={() => handleToggleAttestation(node)}
                        className="px-2 py-0.5 rounded border border-rule-strong bg-sheet text-ink hover:bg-sunken text-2xs font-medium focus:outline-none focus:ring-2 focus:ring-focus"
                      >
                        Self-Attest
                      </button>
                    )}

                    {isSelfReported && (
                      <button
                        type="button"
                        onClick={() => handleToggleAttestation(node)}
                        className="px-2 py-0.5 rounded border border-rule text-ink-3 hover:bg-sunken text-2xs font-medium focus:outline-none focus:ring-2 focus:ring-focus"
                      >
                        Clear Attestation
                      </button>
                    )}

                    {onNavigatePractice && isUnproven && satisfied && (
                      <button
                        type="button"
                        onClick={() => onNavigatePractice(node.id)}
                        className="px-2 py-0.5 rounded bg-span text-on-span text-2xs font-semibold hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus"
                      >
                        Practice
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Statutory Provenance Modal Dialog (Rule R-CR-04) */}
      {provenanceModalNode && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="provenance-title"
        >
          <div
            className="modal-backdrop"
            onClick={() => setProvenanceModalNode(null)}
            aria-hidden="true"
          />
          <div className="modal-panel p-6 max-w-lg w-full bg-sheet border border-rule rounded-dialog shadow-xl relative z-50 space-y-4">
            <div className="flex justify-between items-start border-b border-rule pb-2">
              <div>
                <span className="font-mono text-2xs text-span font-semibold">
                  {provenanceModalNode.id}
                </span>
                <h3 id="provenance-title" className="text-base font-serif font-bold text-ink">
                  {provenanceModalNode.title}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setProvenanceModalNode(null)}
                className="text-ink-3 hover:text-ink text-sm font-bold focus:outline-none focus:ring-2 focus:ring-focus p-1"
                aria-label="Close provenance modal"
              >
                X
              </button>
            </div>

            <div className="space-y-3 text-xs text-ink-2">
              <div>
                <strong className="block text-ink font-semibold">Taxonomy Source & License:</strong>
                <p>
                  {provenanceModalNode.provenance.source_id} ({provenanceModalNode.provenance.license})
                </p>
              </div>

              <div>
                <strong className="block text-ink font-semibold">Statutory Attribution Notice:</strong>
                <p className="p-3 rounded-control bg-sunken border border-rule font-sans text-2xs text-ink leading-relaxed">
                  {provenanceModalNode.provenance.attribution_text}
                </p>
              </div>

              <div className="p-3 rounded-control bg-sunken border border-rule text-2xs text-ink-3">
                <p>
                  <strong>Rule R-CR-01 Invariant:</strong> Competencies and taxonomy structures
                  describe technical capability hierarchies. Acquisition of skills does not guarantee
                  or calculate specific compensation increases.
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setProvenanceModalNode(null)}
                className="px-4 py-1.5 rounded-control bg-span text-on-span text-xs font-semibold hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default GapMapView;
