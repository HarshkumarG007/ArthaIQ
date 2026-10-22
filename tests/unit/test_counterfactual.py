"""Unit tests for Counterfactual Negotiation Scenario Modeling (EXP-15 / T12.02).

Validates:
1. CounterfactualConfig parameter constraints and validation.
2. IndiaNewTaxRegimeEngine (Section 115BAC) slab math, rebate, and net take-home bounds.
3. CounterfactualScenarioEngine:
   - Experience progression monotonicity and isotonic repair.
   - Seniority promotion step-ups and non-crossing quantiles.
   - Metro relocation frontiers and calibrated spans.
   - Dual offer trade-off analysis and risk-adjusted certainty.
4. FastAPI endpoints: POST /v1/scenarios and POST /v1/scenarios/dual-offer.
5. Invariant enforcement: Zero lone numbers (Rule R-UQ-01 / R-MD-08) and latency SLA <= 150 ms.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from compintel.errors import ValidationError
from compintel.schema.enums import MetroLocation, RoleFamily, SeniorityLevel
from compintel.serving.app import app
from compintel.serving.counterfactual import (
    CounterfactualConfig,
    CounterfactualQuery,
    CounterfactualScenarioEngine,
    CounterfactualScenarioResponse,
    DualOfferComparisonResponse,
    IndiaNewTaxRegimeEngine,
    OfferStructure,
    ScenarioType,
)
from compintel.serving.types import ExperienceInput, ProfileRequest, QuantileSpan


@pytest.mark.unit
class TestCounterfactualConfig:
    """Test suite for configuration validation."""

    def test_default_config_valid(self) -> None:
        cfg = CounterfactualConfig()
        assert cfg.min_monotonicity_threshold_pct == 98.0
        assert cfg.min_coverage_bound == 0.75
        assert cfg.max_coverage_bound == 0.85
        assert cfg.max_latency_ms == 150.0
        assert cfg.standard_deduction_lpa == 0.75
        assert cfg.conformal_coverage_nominal == 0.80

    def test_invalid_coverage_bounds_raises(self) -> None:
        with pytest.raises(ValidationError, match="must exceed min_coverage_bound"):
            CounterfactualConfig(min_coverage_bound=0.80, max_coverage_bound=0.80)


@pytest.mark.unit
class TestIndiaNewTaxRegimeEngine:
    """Test suite for statutory Section 115BAC tax calculations."""

    @pytest.fixture
    def tax_engine(self) -> IndiaNewTaxRegimeEngine:
        return IndiaNewTaxRegimeEngine(standard_deduction_lpa=0.75)

    def test_zero_or_negative_pay_yields_zero_tax(
        self, tax_engine: IndiaNewTaxRegimeEngine
    ) -> None:
        assert tax_engine.compute_annual_tax(0.0) == 0.0
        assert tax_engine.compute_annual_tax(-5.0) == 0.0

    def test_income_within_section_87a_rebate_yields_zero_tax(
        self, tax_engine: IndiaNewTaxRegimeEngine
    ) -> None:
        # Gross 7.5 LPA - 0.75 standard deduction = 6.75 LPA taxable (<= 7.0 LPA rebate threshold)
        assert tax_engine.compute_annual_tax(7.50) == 0.0
        assert tax_engine.compute_annual_tax(7.75) == 0.0

    def test_higher_income_computes_slabs_and_cess(
        self, tax_engine: IndiaNewTaxRegimeEngine
    ) -> None:
        # Gross 20.75 LPA -> taxable 20.0 LPA:
        # 3 to 7: 4.0 * 5% = 0.20 LPA
        # 7 to 10: 3.0 * 10% = 0.30 LPA
        # 10 to 12: 2.0 * 15% = 0.30 LPA
        # 12 to 15: 3.0 * 20% = 0.60 LPA
        # Above 15: 5.0 * 30% = 1.50 LPA
        # Total tax = 2.90 LPA * 1.04 cess = 3.016 LPA
        tax = tax_engine.compute_annual_tax(20.75)
        assert round(tax, 3) == 3.016

    def test_take_home_span_returns_monotonic_net_bounds(
        self, tax_engine: IndiaNewTaxRegimeEngine
    ) -> None:
        span = QuantileSpan(p10=18.0, p50=25.0, p90=35.0)
        net_span = tax_engine.compute_take_home_span(span)

        assert net_span.p10_net_lpa <= net_span.p50_net_lpa <= net_span.p90_net_lpa
        assert net_span.p10_net_lpa < 18.0
        assert net_span.effective_tax_rate_p50_pct > 0.0


@pytest.mark.unit
class TestCounterfactualScenarioEngine:
    """Test suite for scenario simulation and monotonicity."""

    @pytest.fixture
    def engine(self) -> CounterfactualScenarioEngine:
        return CounterfactualScenarioEngine()

    def test_simulate_experience_progression_maintains_monotonicity(
        self, engine: CounterfactualScenarioEngine
    ) -> None:
        query = CounterfactualQuery(
            role_family=RoleFamily.SWE.value,
            seniority=SeniorityLevel.MID.value,
            location=MetroLocation.BENGALURU.value,
            years_experience=4.0,
            scenario_type=ScenarioType.EXPERIENCE_PROGRESSION,
        )

        resp = engine.simulate_experience_progression(query, max_horizon_years=5)
        assert isinstance(resp, CounterfactualScenarioResponse)
        assert resp.scenario_type == ScenarioType.EXPERIENCE_PROGRESSION
        assert len(resp.frontier_points) == 5
        assert resp.monotonicity_satisfaction_pct >= 98.0
        assert resp.zero_lone_numbers_verified is True
        assert resp.generation_latency_ms <= 150.0

        # Verify each point has non-crossing quantiles
        for pt in resp.frontier_points:
            span = pt.guaranteed_cash_span
            assert span.p10 <= span.p50 <= span.p90
            assert pt.interval_width_lpa > 0.0
            assert pt.tax_adjusted_take_home.p50_net_lpa > 0.0

    def test_simulate_seniority_promotion_yields_step_ups(
        self, engine: CounterfactualScenarioEngine
    ) -> None:
        query = CounterfactualQuery(
            role_family=RoleFamily.SWE.value,
            seniority=SeniorityLevel.MID.value,
            location=MetroLocation.BENGALURU.value,
            years_experience=5.0,
            scenario_type=ScenarioType.SENIORITY_PROMOTION,
        )

        resp = engine.simulate_seniority_promotion(query)
        assert isinstance(resp, CounterfactualScenarioResponse)
        assert resp.scenario_type == ScenarioType.SENIORITY_PROMOTION
        assert len(resp.frontier_points) >= 2  # SR, STAFF, PRINCIPAL
        assert resp.monotonicity_satisfaction_pct == 100.0

        # Step ups should be strictly positive
        for pt in resp.frontier_points:
            assert pt.delta_p50_lpa >= 0.0

    def test_simulate_metro_relocation_returns_all_major_tech_hubs(
        self, engine: CounterfactualScenarioEngine
    ) -> None:
        query = CounterfactualQuery(
            role_family=RoleFamily.DATA.value,
            seniority=SeniorityLevel.SR.value,
            location=MetroLocation.BENGALURU.value,
            years_experience=7.0,
            scenario_type=ScenarioType.METRO_RELOCATION,
        )

        resp = engine.simulate_metro_relocation(query)
        assert len(resp.frontier_points) == 5  # NCR, HYD, PUNE, MUMBAI, CHENNAI
        assert resp.zero_lone_numbers_verified is True

    def test_evaluate_dual_offer_tradeoff(self, engine: CounterfactualScenarioEngine) -> None:
        profile = ProfileRequest(
            occupation_id=RoleFamily.SWE.value,
            location_id=MetroLocation.BENGALURU.value,
            experience=ExperienceInput(total_years=6.0, level_id=SeniorityLevel.SR.value),
        )
        offer_a = OfferStructure(
            offer_label="Offer A (Cash-heavy)",
            guaranteed_cash_annual=32.0,
            equity_annualized=3.0,
            variable_performance_annual=2.0,
        )
        offer_b = OfferStructure(
            offer_label="Offer B (Equity-heavy)",
            guaranteed_cash_annual=26.0,
            equity_annualized=10.0,
            variable_performance_annual=4.0,
        )

        res = engine.evaluate_dual_offer_tradeoff(profile, offer_a, offer_b)
        assert isinstance(res, DualOfferComparisonResponse)
        assert res.guaranteed_cash_delta_lpa == -6.0
        assert res.total_on_target_earnings_delta_lpa > 0.0
        assert res.offer_a_percentile_position["estimated_percentile"] > 0.0
        assert res.offer_b_percentile_position["estimated_percentile"] > 0.0
        assert res.offer_a_tax_adjusted_cash.p50_net_lpa > 0.0
        assert res.offer_b_tax_adjusted_cash.p50_net_lpa > 0.0
        assert "New Tax Regime" in res.comparison_summary


@pytest.mark.unit
class TestScenariosAPIRouter:
    """Test suite for FastAPI endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(app)

    def test_scenarios_endpoint_experience_success(self, client: TestClient) -> None:
        payload = {
            "role_family": "SWE",
            "seniority": "MID",
            "location": "BENGALURU",
            "years_experience": 4.0,
            "scenario_type": "EXPERIENCE_PROGRESSION",
        }
        res = client.post("/v1/scenarios", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["charter_id"] == "CHARTER-EXP-15"
        assert len(data["frontier_points"]) > 0
        assert data["zero_lone_numbers_verified"] is True
        assert "statutory_disclaimer" in data

    def test_scenarios_endpoint_dual_offer_success(self, client: TestClient) -> None:
        payload = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 5.0, "level_id": "SR"},
            },
            "offer_a": {
                "offer_label": "Offer A",
                "guaranteed_cash_annual": 30.0,
                "equity_annualized": 2.0,
                "variable_performance_annual": 2.0,
            },
            "offer_b": {
                "offer_label": "Offer B",
                "guaranteed_cash_annual": 27.0,
                "equity_annualized": 8.0,
                "variable_performance_annual": 3.0,
            },
        }
        res = client.post("/v1/scenarios/dual-offer", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["charter_id"] == "CHARTER-EXP-15"
        assert "offer_a_tax_adjusted_cash" in data
        assert "offer_b_tax_adjusted_cash" in data
        assert "comparison_summary" in data
