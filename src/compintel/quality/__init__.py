"""CompIntel Data Quality Package (Rules R-DA-04, R-DA-05, R-ER-06).

Includes dataset profiling, coverage mapping, sufficiency evaluation,
target prototype construction, and deduplication with entity resolution.
"""

from compintel.quality.coverage import (
    BANDS,
    CORE_CELL_KEYS,
    FAMILIES,
    LOCATIONS,
    CellDefinition,
    audit_candidate_survey_density,
    compute_coverage_map,
    compute_kish_effective_sample,
    export_coverage_artifacts,
    generate_coverage_chart_svg,
    generate_coverage_table_markdown,
    get_canonical_cells,
    map_location_to_canonical,
    map_role_to_family,
    map_yoe_to_band,
)
from compintel.quality.dedup import (
    DEFAULT_DEDUP_VERSION,
    DeduplicationResult,
    ExactDeduplicator,
    compute_exact_record_signature,
    compute_person_signature,
    deduplicate_records_df,
)
from compintel.quality.profiler import (
    ColumnProfile,
    DatasetProfile,
    profile_csv,
    profile_source_directory,
)
from compintel.quality.sufficiency import (
    compute_bootstrap_precision,
    compute_naive_cohort_widths,
    evaluate_gate_g2_decision,
    evaluate_precision_for_all_cells,
    export_sufficiency_artifacts,
    generate_sufficiency_report_markdown,
    update_coverage_map_with_c5,
)
from compintel.quality.target_prototype import (
    PrototypeTargetResult,
    build_pt1_prototype,
    export_prototype_artifacts,
    generate_exclusion_report_markdown,
)

__all__ = [
    "BANDS",
    "CORE_CELL_KEYS",
    "DEFAULT_DEDUP_VERSION",
    "FAMILIES",
    "LOCATIONS",
    "CellDefinition",
    "ColumnProfile",
    "DatasetProfile",
    "DeduplicationResult",
    "ExactDeduplicator",
    "PrototypeTargetResult",
    "audit_candidate_survey_density",
    "build_pt1_prototype",
    "compute_bootstrap_precision",
    "compute_coverage_map",
    "compute_exact_record_signature",
    "compute_kish_effective_sample",
    "compute_naive_cohort_widths",
    "compute_person_signature",
    "deduplicate_records_df",
    "evaluate_gate_g2_decision",
    "evaluate_precision_for_all_cells",
    "export_coverage_artifacts",
    "export_prototype_artifacts",
    "export_sufficiency_artifacts",
    "generate_coverage_chart_svg",
    "generate_coverage_table_markdown",
    "generate_exclusion_report_markdown",
    "generate_sufficiency_report_markdown",
    "get_canonical_cells",
    "map_location_to_canonical",
    "map_role_to_family",
    "map_yoe_to_band",
    "profile_csv",
    "profile_source_directory",
    "update_coverage_map_with_c5",
]
