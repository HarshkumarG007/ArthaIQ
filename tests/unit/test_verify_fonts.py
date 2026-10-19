"""Unit tests for font verification script (T9.07, ADR-0007)."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.verify_fonts import check_font_file, verify_fonts

FONTS_DIR = Path("apps/web/node_modules/@fontsource")


@pytest.mark.skipif(
    not FONTS_DIR.exists(),
    reason="apps/web/node_modules/@fontsource not installed; verified in frontend CI job",
)
def test_verify_fonts_all_variants_pass() -> None:
    """Verify that all IBM Plex Sans and Serif variants meet the acceptance criteria."""
    results = verify_fonts()
    assert len(results) == 6

    for r in results:
        assert r.has_rupee is True, f"{r.family} weight {r.weight} missing Rupee glyph"
        assert r.has_tabular_figures is True, f"{r.family} weight {r.weight} lacks tabular figures"
        assert r.digit_width == 600, (
            f"{r.family} weight {r.weight} expected digit width 600, got {r.digit_width}"
        )
        assert r.is_ofl is True, f"{r.family} weight {r.weight} missing OFL licence metadata"


def test_verify_fonts_missing_dir_raises() -> None:
    """Non-existent font directory raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Font directories not found"):
        verify_fonts(Path("/nonexistent/path/to/fonts"))


@pytest.mark.skipif(
    not FONTS_DIR.exists(),
    reason="apps/web/node_modules/@fontsource not installed; verified in frontend CI job",
)
def test_check_font_file_individual() -> None:
    """Directly test single font file check."""
    base_dir = Path("apps/web/node_modules/@fontsource/ibm-plex-sans/files")
    font_path = base_dir / "ibm-plex-sans-latin-400-normal.woff2"
    if font_path.exists():
        res = check_font_file(font_path, "IBM Plex Sans", 400)
        assert res.family == "IBM Plex Sans"
        assert res.weight == 400
        assert res.has_rupee is True
        assert res.has_tabular_figures is True
        assert res.is_ofl is True
