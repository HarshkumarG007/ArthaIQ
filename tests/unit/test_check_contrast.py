"""Unit tests for WCAG 2.2 contrast checking and token generation (T9.07, design.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.check_contrast import (
    contrast_ratio,
    generate_tokens_css,
    hex_to_relative_luminance,
    verify_token_contrasts,
)


def test_relative_luminance_known_values() -> None:
    """Verify luminance calculations on known standards (pure black, pure white)."""
    assert hex_to_relative_luminance("#000000") == pytest.approx(0.0, abs=1e-5)
    assert hex_to_relative_luminance("#FFFFFF") == pytest.approx(1.0, abs=1e-5)
    # Shorthand hex
    assert hex_to_relative_luminance("#fff") == pytest.approx(1.0, abs=1e-5)
    assert hex_to_relative_luminance("#000") == pytest.approx(0.0, abs=1e-5)


def test_relative_luminance_invalid_hex() -> None:
    """Invalid hex strings raise ValueError."""
    with pytest.raises(ValueError, match="Invalid hex color code"):
        hex_to_relative_luminance("#invalid")
    with pytest.raises(ValueError, match="Invalid hex color code"):
        hex_to_relative_luminance("#12345")


def test_contrast_ratio_pure_black_and_white() -> None:
    """Black on white is exactly 21:1."""
    ratio = contrast_ratio("#000000", "#FFFFFF")
    assert ratio == pytest.approx(21.0, abs=0.01)


def test_contrast_ratio_symmetry() -> None:
    """Contrast ratio is symmetric regardless of argument order."""
    r1 = contrast_ratio("#17213A", "#F5F6F8")
    r2 = contrast_ratio("#F5F6F8", "#17213A")
    assert r1 == pytest.approx(r2, abs=1e-5)


def test_verify_token_contrasts_all_pass() -> None:
    """All 15 token pairs in tokens.json satisfy WCAG 2.2 AA in light and dark modes."""
    tokens_path = Path("apps/web/src/styles/tokens.json")
    assert tokens_path.exists(), "tokens.json not found"

    with open(tokens_path, encoding="utf-8") as f:
        data = json.load(f)

    results = verify_token_contrasts(data)
    assert len(results) == 15

    for r in results:
        assert r.light_pass is True, (
            f"Failed in light mode: {r.name} ratio {r.light_ratio} < {r.min_ratio}"
        )
        assert r.dark_pass is True, (
            f"Failed in dark mode: {r.name} ratio {r.dark_ratio} < {r.min_ratio}"
        )
        assert r.light_ratio >= r.min_ratio
        assert r.dark_ratio >= r.min_ratio


def test_generate_tokens_css_contains_all_tokens() -> None:
    """Generated CSS contains root tokens, dark theme block, and shadcn mappings."""
    tokens_path = Path("apps/web/src/styles/tokens.json")
    with open(tokens_path, encoding="utf-8") as f:
        data = json.load(f)

    css = generate_tokens_css(data)
    assert ":root {" in css
    assert ':root[data-theme="dark"] {' in css
    assert "@media (prefers-color-scheme: dark)" in css
    assert "--paper: #F5F6F8;" in css
    assert "--span: #2447C6;" in css
    assert "--primary: var(--span);" in css
    assert "--radius: var(--radius-control);" in css
    assert ".figure {" in css
