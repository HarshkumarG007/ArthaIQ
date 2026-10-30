import React, { useMemo } from "react";
import type { ClientEvidenceRecord, ClientCareerProfile } from "../../lib/careerLedger";
import {
  CANONICAL_ROADMAP_MILESTONES,
  type RoadmapMilestoneData,
} from "./RoadmapView";
import {
  Sparkles,
  Code2,
  CheckCircle2,
  Clock,
  Unlock,
  Layers,
  ChevronRight,
  Award,
} from "lucide-react";

export interface NextStepCardProps {
  profile: ClientCareerProfile | null;
  records: ClientEvidenceRecord[];
  onLaunchPractice?: (scenarioId: string) => void;
  onNavigateTab?: (tab: "skills" | "plan" | "practice" | "ledger") => void;
  className?: string;
}

// Level requirement map for canonical DATA milestones (Level 2 = Junior, 3 = Mid, 4 = Senior)
export const COMPETENCY_TARGET_LEVELS: Record<string, number> = {
  "data.gen.l2_prob_decomp": 2,
  "data.gen.l2_ethics": 2,
  "data.anl.l2_sql_basic": 2,
  "data.anl.l2_eda": 2,
  "data.anl.l2_hygiene": 2,
  "data.anl.l3_dashboard": 3,
  "data.anl.l3_sql_adv": 3,
  "data.gen.l3_docs": 3,
  "data.gen.l3_stakeholder": 3,
  "data.sci.l3_exp_design": 3,
  "data.sci.l3_ml_supervised": 3,
  "data.sci.l3_feat_eng": 3,
  "data.sci.l4_bigdata": 4,
  "data.sci.l4_causal": 4,
};

export const NextStepCard: React.FC<NextStepCardProps> = ({
  profile,
  records,
  onLaunchPractice,
  onNavigateTab,
  className = "",
}) => {
  // Map records by competency_id for fast lookup
  const recordsMap = useMemo(() => {
    const map = new Map<string, ClientEvidenceRecord>();
    for (const rec of records) {
      map.set(rec.competency_id, rec);
    }
    return map;
  }, [records]);

  // Determine user's target level ceiling: 2 for Junior, 3 for Mid, 4 for Senior (default 3)
  const maxTargetLevel = useMemo(() => {
    if (!profile) return 3;
    if (profile.target_level === "L2_junior") return 2;
    if (profile.target_level === "L4_senior") return 4;
    return 3;
  }, [profile]);

  // Filter milestones to those required for the targeted level
  const targetMilestones = useMemo(() => {
    return CANONICAL_ROADMAP_MILESTONES.filter((m) => {
      const minLevel = COMPETENCY_TARGET_LEVELS[m.id] ?? 2;
      return minLevel <= maxTargetLevel;
    });
  }, [maxTargetLevel]);

  // Check which target milestones are demonstrated vs unproven/self-reported
  const { demonstratedCount, totalTargetCount, nextActionableMilestone, unlockedByNext } =
    useMemo(() => {
      let demonstrated = 0;
      let nextStep: RoadmapMilestoneData | null = null;
      let unlocked: RoadmapMilestoneData[] = [];

      for (const milestone of targetMilestones) {
        const record = recordsMap.get(milestone.id);
        const isDemonstrated = record?.verification_state === "demonstrated";

        if (isDemonstrated) {
          demonstrated++;
        } else if (!nextStep) {
          // Check if all prerequisites are satisfied
          const prereqsSatisfied = milestone.prerequisite_ids.every((prereqId) => {
            const prereqRec = recordsMap.get(prereqId);
            return (
              prereqRec?.verification_state === "demonstrated" ||
              prereqRec?.verification_state === "self_reported"
            );
          });

          if (prereqsSatisfied) {
            nextStep = milestone;
            // Find downstream milestones in the full graph that this milestone unlocks
            unlocked = CANONICAL_ROADMAP_MILESTONES.filter((m) =>
              m.prerequisite_ids.includes(milestone.id)
            );
          }
        }
      }

      return {
        demonstratedCount: demonstrated,
        totalTargetCount: targetMilestones.length,
        nextActionableMilestone: nextStep,
        unlockedByNext: unlocked,
      };
    }, [targetMilestones, recordsMap]);

  const allTargetMilestonesDemonstrated =
    totalTargetCount > 0 && demonstratedCount === totalTargetCount;

  // Format step number in topological sequence
  const stepIndex = useMemo(() => {
    if (!nextActionableMilestone) return null;
    const idx = CANONICAL_ROADMAP_MILESTONES.findIndex((m) => m.id === nextActionableMilestone.id);
    return idx >= 0 ? idx + 1 : 1;
  }, [nextActionableMilestone]);

  const currentRecord = nextActionableMilestone
    ? recordsMap.get(nextActionableMilestone.id)
    : null;
  const isSelfReported = currentRecord?.verification_state === "self_reported";

  // CASE 1: All target level milestones are demonstrated
  if (allTargetMilestonesDemonstrated) {
    const levelLabel =
      maxTargetLevel === 2 ? "Junior L2" : maxTargetLevel === 3 ? "Mid-Level L3" : "Senior L4";

    return (
      <section
        role="region"
        aria-label="Recommended next step action card"
        className={`p-6 rounded-control border border-ok/40 bg-ok-wash/20 text-ink shadow-sm ${className}`}
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-ok text-on-span flex items-center justify-center">
                <CheckCircle2 className="w-4 h-4 text-white" aria-hidden="true" />
              </span>
              <span className="text-xs uppercase tracking-wider font-semibold text-ok">
                Target Level Complete
              </span>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-sheet border border-ok/40 text-ink">
                {demonstratedCount}/{totalTargetCount} Demonstrated
              </span>
            </div>
            <h2 className="text-xl font-serif font-semibold text-ink">
              All {levelLabel} Competencies Demonstrated
            </h2>
            <p className="text-sm text-ink-2 max-w-2xl">
              You have established verified evidence for every competency required under your{" "}
              <strong>{profile?.target_role || "Data Specialist"}</strong> target level. You can explore
              advanced competencies in the Roadmap or export your DPDP Act 2023 evidence ledger.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => onNavigateTab?.("plan")}
              className="px-4 py-2 min-h-[44px] rounded-control bg-span text-on-span font-medium text-xs hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus transition-colors flex items-center gap-2"
              aria-label="View full roadmap plan"
            >
              <Layers className="w-4 h-4" aria-hidden="true" />
              <span>View Full Roadmap</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigateTab?.("ledger")}
              className="px-4 py-2 min-h-[44px] rounded-control border border-rule text-ink-2 hover:bg-sunken font-medium text-xs focus:outline-none focus:ring-2 focus:ring-focus transition-colors flex items-center gap-2"
              aria-label="Review evidence ledger records"
            >
              <Award className="w-4 h-4" aria-hidden="true" />
              <span>Review Evidence Ledger</span>
            </button>
          </div>
        </div>
      </section>
    );
  }

  // CASE 2: No actionable milestone found (e.g. graph has no matching unmet node)
  if (!nextActionableMilestone) {
    return (
      <section
        role="region"
        aria-label="Recommended next step action card"
        className={`p-6 rounded-control border border-rule bg-sheet text-ink shadow-sm ${className}`}
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-span uppercase font-semibold">
              <Sparkles className="w-4 h-4" aria-hidden="true" />
              <span>Career Architect Guidance</span>
            </div>
            <h2 className="text-lg font-serif font-semibold text-ink">
              Explore Your Competency Gap Map
            </h2>
            <p className="text-sm text-ink-2 max-w-2xl">
              Select or attest competencies in the Skills &amp; Gap Map to initialize your next-step
              learning priorities.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigateTab?.("skills")}
            className="px-4 py-2 min-h-[44px] rounded-control bg-span text-on-span font-medium text-xs hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus transition-colors flex items-center gap-2"
            aria-label="Open Skills and Gap Map"
          >
            <span>Open Skills Map</span>
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </section>
    );
  }

  // CASE 3: Active Actionable Next Step
  const step = nextActionableMilestone;

  return (
    <section
      role="region"
      aria-label="Recommended next step action card"
      className={`p-6 rounded-control border-2 border-span/40 bg-span-wash/10 text-ink shadow-sm relative overflow-hidden ${className}`}
    >
      {/* Top Banner & Priority Badge */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-span text-on-span">
            <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Priority Next Step</span>
          </span>
          <span className="text-xs px-2.5 py-1 rounded bg-sheet border border-rule text-ink-2 font-medium">
            Step {stepIndex} of 14 in DATA Sequence
          </span>
          <span className="text-xs px-2.5 py-1 rounded bg-sheet border border-rule text-ink-2 font-medium">
            {step.category_label}
          </span>
          {isSelfReported && (
            <span className="text-xs px-2 py-0.5 rounded bg-caution-wash text-caution border border-caution/40 font-semibold">
              Self-Reported (Ready to Demonstrate)
            </span>
          )}
        </div>

        {/* Calibrated Heuristic Range */}
        <div className="flex items-center gap-1.5 text-xs text-ink-2 bg-sheet px-3 py-1 rounded border border-rule">
          <Clock className="w-3.5 h-3.5 text-ink-3" aria-hidden="true" />
          <span>
            Typical Effort:{" "}
            <strong className="text-ink font-semibold">
              {step.min_hours}–{step.max_hours} hours
            </strong>
          </span>
          <span
            className="text-[10px] px-1 rounded bg-sunken text-ink-3 font-mono uppercase"
            title="Calibrated heuristic effort range (Rule R-CR-05)"
          >
            Heuristic
          </span>
        </div>
      </div>

      {/* Main Milestone Information */}
      <div className="space-y-3">
        <div>
          <h2 className="text-xl font-serif font-bold text-ink tracking-tight flex items-center gap-2">
            <span>{step.title}</span>
          </h2>
          <p className="text-xs text-ink-3 mt-1">
            Node ID: <code className="font-mono text-ink-2">{step.id}</code> · Prerequisites
            Satisfied
          </p>
        </div>

        {/* Why this next & downstream unlock impact */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          <div className="p-3 rounded bg-sheet border border-rule text-xs space-y-1">
            <div className="flex items-center gap-1.5 text-ink font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 text-ok" aria-hidden="true" />
              <span>Prerequisites Ready</span>
            </div>
            <p className="text-ink-2">
              {step.prerequisite_ids.length === 0
                ? "Foundational milestone with zero prior dependencies."
                : `All ${step.prerequisite_ids.length} direct prerequisite competencies are verified in your local ledger.`}
            </p>
          </div>

          <div className="p-3 rounded bg-sheet border border-rule text-xs space-y-1">
            <div className="flex items-center gap-1.5 text-ink font-semibold">
              <Unlock className="w-3.5 h-3.5 text-span" aria-hidden="true" />
              <span>Unlocks Downstream Capabilities</span>
            </div>
            <p className="text-ink-2">
              {unlockedByNext.length === 0
                ? "Terminal specialization milestone in this cluster."
                : `Unlocks prerequisites for ${unlockedByNext.length} milestone${unlockedByNext.length > 1 ? "s" : ""}: ${unlockedByNext.map((u) => u.title).slice(0, 2).join(", ")}${unlockedByNext.length > 2 ? ` (+${unlockedByNext.length - 2} more)` : ""}.`}
            </p>
          </div>
        </div>

        {/* Practice Scenario Integration & Action CTAs */}
        <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-t border-rule/60">
          <div className="text-xs text-ink-3 max-w-xl">
            {step.associated_scenario_id ? (
              <p>
                <strong className="text-ink font-medium">Practice Available:</strong> Flaw-finding
                scenario{" "}
                <span className="font-mono text-ink-2">{step.associated_scenario_id}</span> ({step.associated_scenario_title})
                runs offline in your browser.
              </p>
            ) : (
              <p>
                Demonstrate this milestone through code reviews, peer attestations, or project artifacts
                tracked in your evidence ledger.
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            {step.associated_scenario_id ? (
              <button
                type="button"
                onClick={() => onLaunchPractice?.(step.associated_scenario_id!)}
                className="px-4 py-2 min-h-[44px] rounded-control bg-span text-on-span font-semibold text-xs hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus transition-colors flex items-center gap-2 shadow-sm"
                aria-label={`Launch flaw-finding practice scenario for ${step.title}`}
              >
                <Code2 className="w-4 h-4" aria-hidden="true" />
                <span>Launch Flaw-Finding Practice</span>
              </button>
            ) : null}

            <button
              type="button"
              onClick={() => onNavigateTab?.("skills")}
              className="px-3.5 py-2 min-h-[44px] rounded-control border border-rule text-ink-2 hover:bg-sunken font-medium text-xs focus:outline-none focus:ring-2 focus:ring-focus transition-colors flex items-center gap-1.5"
              aria-label={`View ${step.title} in Skills and Gap Map`}
            >
              <span>View in Skills Map</span>
              <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Statutory Disclaimers (Rules R-CR-01, R-CR-05) */}
        <div className="pt-2">
          <p className="text-[11px] text-ink-3 leading-relaxed">
            * <strong>Statutory Disclaimer:</strong> Effort estimates are calibrated heuristic ranges ($H_\min$–$H_\max$),
            not guarantees. Acquiring or demonstrating competencies does not guarantee employment offers, compensation
            increases, or appraisals (India Consumer Protection Act 2019, Rules R-CR-01, R-CR-05).
          </p>
        </div>
      </div>
    </section>
  );
};
