"""Unit tests for Active Learning & Targeted Data Sourcing (EXP-14 / T12.01).

Validates:
1. ActiveLearningConfig validation and constraints.
2. ActiveLearningAcquisitionScorer ranking, utility formulation, and cohort scoring.
3. TargetedRecruitmentRouter campaign directives, channel selection, and quota assignment.
4. ActiveLearningSimulator convergence, trajectory tracking, and Keep Criteria validation.
5. Report serialization and schema compliance.
"""

from __future__ import annotations

import polars as pl
import pytest
from pydantic import ValidationError as PydanticValidationError

from compintel.acquisition.active_learning import (
    ActiveLearningAcquisitionScorer,
    ActiveLearningConfig,
    ActiveLearningExperimentReport,
    ActiveLearningSimulator,
    ActiveLearningVerdict,
    CampaignChannel,
    TargetedRecruitmentRouter,
)
from compintel.errors import ConfigError, ValidationError
from compintel.schema.enums import MetroLocation, RoleFamily, SeniorityLevel


@pytest.mark.unit
class TestActiveLearningConfig:
    """Test suite for configuration validation."""

    def test_default_config_valid(self) -> None:
        cfg = ActiveLearningConfig()
        assert cfg.target_acquisition_budget == 150
        assert cfg.abstention_floor == 10
        assert cfg.sparse_threshold == 15
        assert cfg.top_k_target_cells == 20
        assert cfg.min_coverage_bound == 0.75
        assert cfg.max_coverage_bound == 0.85
        assert cfg.min_width_reduction_pct == 20.0
        assert cfg.min_abstention_drop_pct == 15.0
        assert cfg.max_relative_cost == 2.0
        assert cfg.random_seed == 42

    def test_invalid_abstention_floor_raises(self) -> None:
        with pytest.raises(PydanticValidationError):
            ActiveLearningConfig(abstention_floor=2)

    def test_invalid_sparse_threshold_raises(self) -> None:
        with pytest.raises(PydanticValidationError):
            ActiveLearningConfig(sparse_threshold=5)

    def test_invalid_budget_raises(self) -> None:
        with pytest.raises(PydanticValidationError):
            ActiveLearningConfig(target_acquisition_budget=20)

    def test_invalid_coverage_bounds_raises(self) -> None:
        with pytest.raises(ConfigError, match="must exceed min_coverage_bound"):
            ActiveLearningConfig(min_coverage_bound=0.80, max_coverage_bound=0.80)


@pytest.mark.unit
class TestActiveLearningAcquisitionScorer:
    """Test suite for cell acquisition utility scoring."""

    @pytest.fixture
    def sample_cohort_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "role_family": [
                    RoleFamily.SWE.value,
                    RoleFamily.SWE.value,
                    RoleFamily.DATA.value,
                ],
                "seniority": [
                    SeniorityLevel.PRINCIPAL.value,
                    SeniorityLevel.MID.value,
                    SeniorityLevel.SR.value,
                ],
                "location": [
                    MetroLocation.BENGALURU.value,
                    MetroLocation.BENGALURU.value,
                    MetroLocation.MUMBAI.value,
                ],
                "cohort_size": [3, 150, 8],
                "interval_width_lpa": [35.0, 8.5, 22.0],
            }
        )

    def test_missing_columns_raises_validation_error(self) -> None:
        scorer = ActiveLearningAcquisitionScorer()
        invalid_df = pl.DataFrame({"role_family": ["SWE"], "location": ["BENGALURU"]})
        with pytest.raises(ValidationError, match="Missing required columns"):
            scorer.score_cells(invalid_df)

    def test_scoring_prefers_higher_uncertainty_and_sparsity(
        self, sample_cohort_df: pl.DataFrame
    ) -> None:
        scorer = ActiveLearningAcquisitionScorer()
        scored = scorer.score_cells(sample_cohort_df)

        assert len(scored) == 3
        # First element should have the highest acquisition utility (sparse principal cell)
        top_cell = scored[0]
        assert top_cell.role_family == RoleFamily.SWE.value
        assert top_cell.seniority == SeniorityLevel.PRINCIPAL.value
        assert top_cell.is_sparse is True
        assert top_cell.is_abstained is True
        assert top_cell.acquisition_utility > scored[-1].acquisition_utility

        # The dense cell (n_observations=150) should be ranked last
        assert scored[-1].n_observations == 150
        assert scored[-1].is_sparse is False
        assert scored[-1].is_abstained is False

    def test_search_demand_weighting(self, sample_cohort_df: pl.DataFrame) -> None:
        scorer = ActiveLearningAcquisitionScorer()
        # Boost Mumbai DATA cell demand artificially
        custom_demand = {"DATA:SR:MUMBAI": 5.0}
        scored = scorer.score_cells(sample_cohort_df, search_demand_map=custom_demand)

        mumbai_cell = next(c for c in scored if c.location == MetroLocation.MUMBAI.value)
        assert mumbai_cell.search_demand_weight == 5.0
        assert mumbai_cell.acquisition_utility > 0.0


@pytest.mark.unit
class TestTargetedRecruitmentRouter:
    """Test suite for campaign generation and channel routing."""

    def test_routing_generates_channel_directives(self) -> None:
        scorer = ActiveLearningAcquisitionScorer()
        df = pl.DataFrame(
            {
                "role_family": [
                    RoleFamily.SWE.value,
                    RoleFamily.MLAI.value,
                    RoleFamily.DATA.value,
                ],
                "seniority": [
                    SeniorityLevel.PRINCIPAL.value,
                    SeniorityLevel.JR.value,
                    SeniorityLevel.MID.value,
                ],
                "location": [
                    MetroLocation.BENGALURU.value,
                    MetroLocation.PUNE.value,
                    MetroLocation.HYDERABAD.value,
                ],
                "cohort_size": [2, 3, 100],  # 2 sparse, 1 dense
                "interval_width_lpa": [38.0, 18.0, 8.0],
            }
        )
        scored = scorer.score_cells(df)
        router = TargetedRecruitmentRouter()
        campaigns = router.generate_campaign_directives(scored)

        # Only the 2 sparse cells should have campaign directives
        assert len(campaigns) == 2
        # Principal SWE gets referral bounty
        assert campaigns[0].recommended_channel == CampaignChannel.COMMUNITY_REFERRAL_BOUNTY
        assert campaigns[0].target_sample_quota >= 5
        assert campaigns[0].incentive_multiplier >= 1.5

        # Check serialization
        campaign_dict = campaigns[0].to_dict()
        assert "cell_key" in campaign_dict
        assert "recommended_channel" in campaign_dict
        assert "target_sample_quota" in campaign_dict


@pytest.mark.unit
class TestActiveLearningSimulator:
    """Test suite for simulation dynamics and Keep Criteria evaluation."""

    @pytest.fixture
    def simulation_cohort_df(self) -> pl.DataFrame:
        roles = [
            RoleFamily.SWE.value,
            RoleFamily.DATA.value,
            RoleFamily.MLAI.value,
            RoleFamily.OTHER.value,
        ]
        seniors = [
            SeniorityLevel.JR.value,
            SeniorityLevel.MID.value,
            SeniorityLevel.SR.value,
            SeniorityLevel.STAFF.value,
            SeniorityLevel.PRINCIPAL.value,
            SeniorityLevel.OTHER.value,
        ]
        locations = [
            MetroLocation.BENGALURU.value,
            MetroLocation.HYDERABAD.value,
            MetroLocation.PUNE.value,
            MetroLocation.NCR.value,
        ]

        rows = []
        for r in roles:
            for s in seniors:
                for loc in locations:
                    # make some sparse, some dense
                    if s in {SeniorityLevel.STAFF.value, SeniorityLevel.PRINCIPAL.value}:
                        cohort_size = 4
                        width = 30.0
                    else:
                        cohort_size = 65
                        width = 12.0
                    rows.append(
                        {
                            "role_family": r,
                            "seniority": s,
                            "location": loc,
                            "cohort_size": cohort_size,
                            "interval_width_lpa": width,
                        }
                    )
        return pl.DataFrame(rows)

    def test_simulation_generates_valid_report_and_meets_criteria(
        self, simulation_cohort_df: pl.DataFrame
    ) -> None:
        cfg = ActiveLearningConfig(target_acquisition_budget=150, random_seed=42)
        simulator = ActiveLearningSimulator(config=cfg)

        report = simulator.run_simulation(simulation_cohort_df)
        assert isinstance(report, ActiveLearningExperimentReport)
        assert report.charter_id == "CHARTER-EXP-14"
        expected_name = "Active Learning & Targeted Data Sourcing for Sparse Realization Cells"
        assert report.experiment_name == expected_name
        assert len(report.trajectory) > 0

        # Trajectory ends at budget
        assert report.trajectory[-1]["samples_acquired"] == 150

        # Keep criteria validated
        assert report.verdict == ActiveLearningVerdict.PROMOTE
        criteria = report.keep_criteria
        assert criteria["criterion_1_width_reduction"]["passed"] is True
        assert criteria["criterion_1_width_reduction"]["reduction_pct"] >= 20.0

        assert criteria["criterion_2_abstention_drop"]["passed"] is True
        assert criteria["criterion_2_abstention_drop"]["drop_pp"] >= 15.0
        assert criteria["criterion_2_abstention_drop"]["quantile_crossing_rate"] == 0.0

        assert criteria["criterion_3_empirical_coverage"]["passed"] is True
        cov = criteria["criterion_3_empirical_coverage"]["measured_coverage"]
        assert 0.75 <= cov <= 0.85

        cost_crit = criteria["criterion_4_cost_efficiency"]
        assert cost_crit["passed"] is True
        assert cost_crit["relative_cost_per_informative_sample"] <= 2.0

    def test_report_serialization(self, simulation_cohort_df: pl.DataFrame) -> None:
        cfg = ActiveLearningConfig(target_acquisition_budget=150, random_seed=42)
        simulator = ActiveLearningSimulator(config=cfg)
        report = simulator.run_simulation(simulation_cohort_df)

        report_dict = report.to_dict()
        assert report_dict["charter_id"] == "CHARTER-EXP-14"
        assert report_dict["verdict"] == "PROMOTE"
        assert "keep_criteria" in report_dict
        assert "baseline_policy" in report_dict
        assert "treatment_policy" in report_dict
        assert "trajectory" in report_dict
        assert len(report_dict["trajectory"]) == 6  # 0 + 5 batches
