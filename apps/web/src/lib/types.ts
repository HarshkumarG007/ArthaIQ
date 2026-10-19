/**
 * Client-side domain and API types conforming to architecture.md Section 11,
 * PRD Section 5 & FR-19, and design.md.
 */

export interface QuantileSpanData {
  p10: floatNumber;
  p50: floatNumber;
  p90: floatNumber;
  currency: string;
  period: string;
  measure: string;
  pre_tax: boolean;
  nominal: boolean;
}

type floatNumber = number;

export interface ReliabilityData {
  grade: "GRADE_A" | "GRADE_B" | "GRADE_C" | string;
  reasons: string[];
}

export interface SourceMixData {
  source_type: string;
  share: number;
}

export interface EvidenceData {
  cohort_n: number;
  source_mix: SourceMixData[];
  median_observation_age_days: number;
  data_snapshot_id: string;
  model_version: string;
}

export interface ComparisonData {
  current_compensation: number;
  delta_to_median_lpa: number;
  position_category: "below_floor" | "below_median" | "median" | "above_median" | "top" | string;
  percentile_band: "<P10" | "P10-P50" | "P50-P90" | ">P90" | string;
}

export interface EstimateResponseData {
  request_id: string;
  status: "ok";
  estimate: QuantileSpanData;
  reliability: ReliabilityData;
  evidence: EvidenceData;
  profile_level_used: number;
  warnings: string[];
  disclaimer_id: string;
  as_of: string;
  model_version: string;
  data_snapshot_id: string;
  comparison?: ComparisonData | null;
}

export interface AbstentionReasonData {
  code: string;
  detail: string;
}

export interface FallbackData {
  type: string;
  description: string;
}

export interface AbstainedResponseData {
  request_id: string;
  status: "abstained";
  reasons: AbstentionReasonData[];
  fallbacks: FallbackData[];
  disclaimer_id: string;
  as_of: string;
  model_version: string;
  data_snapshot_id: string;
}

export type EstimateApiResponse = EstimateResponseData | AbstainedResponseData;

export interface ProfileRefinementData {
  skills?: string[];
  industry?: string;
  work_arrangement?: string;
}

export interface ProfileFormData {
  occupation_id: string;
  location_id: string;
  years_experience: number | null;
  not_sure_experience: boolean;
  seniority_level?: string;
  refinements?: ProfileRefinementData;
}

export interface TaxonomyOccupation {
  id: string;
  name: string;
  description: string;
  examples: string[];
}

export interface TaxonomyLocation {
  id: string;
  name: string;
  state: string;
  tier: number;
  aliases: string[];
}
