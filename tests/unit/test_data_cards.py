"""Unit tests verifying that all required data cards exist and follow the standard structure."""

from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
def test_all_approved_sources_have_data_cards() -> None:
    """Verify that every approved source in config/sources/ has a data card in docs/data-cards/."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    sources_dir = repo_root / "config" / "sources"
    cards_dir = repo_root / "docs" / "data-cards"

    assert cards_dir.exists(), f"Data cards directory missing: {cards_dir}"

    approved_sources = []
    for sf in sources_dir.glob("*.yaml"):
        with open(sf, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data.get("ingestion_status") in {"approved", "approved_for_design"}:
                approved_sources.append(data["source_id"])

    msg = f"Expected >= 13 approved sources, got {len(approved_sources)}"
    assert len(approved_sources) >= 13, msg

    missing_cards = []
    for sid in approved_sources:
        card_path = cards_dir / f"{sid}.md"
        if not card_path.exists():
            missing_cards.append(sid)

    assert not missing_cards, f"Missing data cards for approved sources: {missing_cards}"


@pytest.mark.unit
def test_data_cards_contain_mandatory_sections() -> None:
    """Verify that every data card contains mandatory metadata and profiling sections."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    cards_dir = repo_root / "docs" / "data-cards"

    card_files = [cf for cf in cards_dir.glob("*.md") if cf.name != "README.md"]
    assert len(card_files) >= 13, f"Expected >= 13 data cards, found {len(card_files)}"

    mandatory_snippets = [
        "**Source ID**",
        "**Licence**",
        "**SQS",
        "**Ingestion Status**",
        "**Assigned Role**",
    ]

    for cf in card_files:
        text = cf.read_text(encoding="utf-8")
        for snippet in mandatory_snippets:
            assert snippet in text, f"Missing mandatory snippet '{snippet}' in {cf.name}"
