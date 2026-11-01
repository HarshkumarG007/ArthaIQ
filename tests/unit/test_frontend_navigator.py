"""Unit tests for Phase 30: Frontend Cross-Family Career Pathway Navigator.

Verifies:
- Structural integrity and TypeScript component export of CrossFamilyPathwayNavigator.
- Corridor definitions and bridge competency metadata.
- Canonical scenario linking to the 21 flaw-finding scenarios.
- CareerRoute and NavigationShell routing integration.
- Compliance with Rule R-CR-01 (CPA 2019 disclaimer) and Rule R-CR-02 (Two Streams Two Places).
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"
NAVIGATOR_PATH = WEB_SRC / "components" / "career" / "CrossFamilyPathwayNavigator.tsx"
NAVIGATOR_TEST_PATH = WEB_SRC / "components" / "career" / "CrossFamilyPathwayNavigator.test.tsx"
CAREER_ROUTE_PATH = WEB_SRC / "routes" / "career.tsx"
NAV_SHELL_PATH = WEB_SRC / "components" / "NavigationShell.tsx"


class TestFrontendNavigatorArchitecture:
    """Verifies the architecture and contents of the CrossFamilyPathwayNavigator."""

    def test_navigator_files_exist(self) -> None:
        """Component and test suite files must exist."""
        assert NAVIGATOR_PATH.exists(), f"Missing {NAVIGATOR_PATH}"
        assert NAVIGATOR_TEST_PATH.exists(), f"Missing {NAVIGATOR_TEST_PATH}"

    def test_canonical_corridors_defined(self) -> None:
        """All three canonical multi-family corridors must be configured."""
        content = NAVIGATOR_PATH.read_text(encoding="utf-8")
        assert "SWE_TO_MLAI" in content
        assert "DATA_TO_MLAI" in content
        assert "SWE_TO_DATA" in content

    def test_bridge_competencies_flagged(self) -> None:
        """Milestones must include bridge flags and rationale."""
        content = NAVIGATOR_PATH.read_text(encoding="utf-8")
        assert "isBridge: true" in content
        assert "bridgeRationale:" in content
        assert "Bridge Competency" in content

    def test_practice_scenario_linking(self) -> None:
        """Milestones link to verified flaw-finding scenarios."""
        content = NAVIGATOR_PATH.read_text(encoding="utf-8")
        scenarios = re.findall(r'scenarioId:\s*"([^"]+)"', content)
        assert len(scenarios) >= 8, f"Expected >= 8 linked scenarios, got {len(scenarios)}"
        for sc in scenarios:
            assert (
                sc.startswith("SCEN-DATA-")
                or sc.startswith("SCEN-SWE-")
                or sc.startswith("SCEN-MLAI-")
            )

    def test_rule_r_cr_01_and_r_cr_02_compliance(self) -> None:
        """Mandatory CPA 2019 statutory disclaimer and Two Streams Two Places decoupling."""
        content = NAVIGATOR_PATH.read_text(encoding="utf-8")
        assert "India Consumer Protection Act 2019" in content
        assert "does not guarantee salary" in content
        assert "Target Market Compensation Distribution (Decoupled Evidence)" in content
        assert "Stream A: Market Pay" in content

    def test_career_route_and_shell_integration(self) -> None:
        """CareerRoute and NavigationShell must wire up the pathways sub-view and hash routing."""
        career_content = CAREER_ROUTE_PATH.read_text(encoding="utf-8")
        assert '"pathways"' in career_content
        assert "CrossFamilyPathwayNavigator" in career_content
        assert 'id="tab-pathways"' in career_content
        assert 'id="panel-pathways"' in career_content

        shell_content = NAV_SHELL_PATH.read_text(encoding="utf-8")
        assert 'hash.includes("/pathways")' in shell_content
