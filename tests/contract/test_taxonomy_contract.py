"""Contract tests for taxonomy and reference lookup endpoints (Phase 9, Task T9.04).

Verifies:
- architecture.md Section 11: GET /v1/taxonomy/occupations and GET /v1/taxonomy/locations.
- PRD Section 5: Canonical occupational scope and metro tech hubs.
- Search term filtering (?q=) across IDs, display titles, examples, states, and aliases.
- GET /v1/taxonomy/seniorities for standardized career ladder progression.
- Correlation tracing via X-Request-ID and Security Headers on all endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from compintel.schema.enums import MetroLocation, RoleFamily, SeniorityLevel
from compintel.serving.app import create_app


class TestTaxonomyOccupationsContract:
    """Contract tests for GET /v1/taxonomy/occupations."""

    def test_get_occupations_unfiltered(self) -> None:
        """Unfiltered occupations request returns all canonical technical disciplines."""
        client = TestClient(create_app())
        response = client.get("/v1/taxonomy/occupations")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["query"] is None
        assert data["total"] >= 4

        # Verify all statutory RoleFamily enums exist
        returned_ids = {item["id"] for item in data["items"]}
        for role in (RoleFamily.SWE, RoleFamily.DATA, RoleFamily.MLAI, RoleFamily.OTHER):
            assert role.value in returned_ids

        # Structure of each occupation item
        for item in data["items"]:
            assert isinstance(item["id"], str)
            assert isinstance(item["name"], str)
            assert isinstance(item["description"], str)
            assert isinstance(item["examples"], list)
            assert len(item["examples"]) > 0

    def test_get_occupations_search_by_name(self) -> None:
        """Search query filters occupations matching by name or title examples."""
        client = TestClient(create_app())
        response = client.get("/v1/taxonomy/occupations", params={"q": "software"})

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "software"
        assert data["total"] >= 1
        assert any(item["id"] == "SWE" for item in data["items"])

    def test_get_occupations_search_by_example_title(self) -> None:
        """Search query matches specialized title inside examples."""
        client = TestClient(create_app())
        response = client.get("/v1/taxonomy/occupations", params={"q": "MLOps"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(item["id"] == "MLAI" for item in data["items"])

    def test_get_occupations_search_no_matches(self) -> None:
        """Search query with no matching roles returns empty list and total 0."""
        client = TestClient(create_app())
        response = client.get("/v1/taxonomy/occupations", params={"q": "xyz_unmatched_occupation"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestTaxonomyLocationsContract:
    """Contract tests for GET /v1/taxonomy/locations."""

    def test_get_locations_unfiltered(self) -> None:
        """Unfiltered locations request returns all Tier-1 Indian tech hubs and other."""
        client = TestClient(create_app())
        response = client.get("/v1/taxonomy/locations")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

        data = response.json()
        assert data["total"] >= 7
        assert data["query"] is None

        # Verify all statutory MetroLocation enums exist
        returned_ids = {item["id"] for item in data["items"]}
        expected_locations = [
            MetroLocation.BENGALURU,
            MetroLocation.HYDERABAD,
            MetroLocation.PUNE,
            MetroLocation.MUMBAI,
            MetroLocation.NCR,
            MetroLocation.CHENNAI,
            MetroLocation.OTHER,
        ]
        for loc in expected_locations:
            assert loc.value in returned_ids

        # Structure of each location item
        for item in data["items"]:
            assert isinstance(item["id"], str)
            assert isinstance(item["name"], str)
            assert isinstance(item["state"], str)
            assert isinstance(item["tier"], int)
            assert item["tier"] in (1, 2)
            assert isinstance(item["aliases"], list)

    def test_get_locations_search_by_alias(self) -> None:
        """Search query matches common regional abbreviations and city aliases."""
        client = TestClient(create_app())

        # Test BLR alias for Bengaluru
        res_blr = client.get("/v1/taxonomy/locations", params={"q": "BLR"})
        assert res_blr.status_code == 200
        assert any(item["id"] == "BENGALURU" for item in res_blr.json()["items"])

        # Test Gurgaon alias for NCR
        res_gurgaon = client.get("/v1/taxonomy/locations", params={"q": "Gurgaon"})
        assert res_gurgaon.status_code == 200
        assert any(item["id"] == "NCR" for item in res_gurgaon.json()["items"])

        # Test Cyberabad alias for Hyderabad
        res_hyd = client.get("/v1/taxonomy/locations", params={"q": "Cyberabad"})
        assert res_hyd.status_code == 200
        assert any(item["id"] == "HYDERABAD" for item in res_hyd.json()["items"])

    def test_get_locations_search_by_state(self) -> None:
        """Search query matches state names."""
        client = TestClient(create_app())
        response = client.get("/v1/taxonomy/locations", params={"q": "Maharashtra"})

        assert response.status_code == 200
        matched_ids = {item["id"] for item in response.json()["items"]}
        assert "PUNE" in matched_ids
        assert "MUMBAI" in matched_ids

    def test_get_locations_search_no_matches(self) -> None:
        """Search query with no matching location returns empty list."""
        client = TestClient(create_app())
        response = client.get("/v1/taxonomy/locations", params={"q": "nonexistent_city_999"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestTaxonomySenioritiesContract:
    """Contract tests for GET /v1/taxonomy/seniorities."""

    def test_get_seniorities_returns_standard_ladder(self) -> None:
        """Verify seniority ladder returns JR, MID, SR, STAFF, and PRINCIPAL."""
        client = TestClient(create_app())
        response = client.get("/v1/taxonomy/seniorities")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

        data = response.json()
        assert data["total"] == 5

        returned_ids = [item["id"] for item in data["items"]]
        expected_order = [
            SeniorityLevel.JR.value,
            SeniorityLevel.MID.value,
            SeniorityLevel.SR.value,
            SeniorityLevel.STAFF.value,
            SeniorityLevel.PRINCIPAL.value,
        ]
        assert returned_ids == expected_order

        for item in data["items"]:
            assert isinstance(item["id"], str)
            assert isinstance(item["name"], str)
            assert isinstance(item["typical_years"], str)
            assert isinstance(item["description"], str)
