#!/usr/bin/env python3
"""Verify font files for ArthaIQ design system compliance (T9.07, ADR-0007).

Checks:
1. Self-hosted IBM Plex Sans and IBM Plex Serif font files exist for required weights (400, 500, 600).
2. The Indian Rupee glyph (U+20B9, ₹) is present in character maps for both Sans and Serif.
3. Tabular lining figures are available (digits '0'-'9' have uniform advance widths).
4. Licence metadata in the font files conforms to SIL Open Font License (OFL).

Usage:
    uv run python scripts/verify_fonts.py [--font-dir <path>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

from fontTools.ttLib import TTFont


class FontCheckResult(NamedTuple):
    family: str
    weight: int
    has_rupee: bool
    has_tabular_figures: bool
    digit_width: int
    is_ofl: bool
    file_path: Path


def check_font_file(file_path: Path, family: str, weight: int) -> FontCheckResult:
    """Inspect font file using fontTools and verify glyphs, metrics, and licence."""
    font = TTFont(str(file_path))
    cmap = font.getBestCmap() or {}

    # 1. Rupee sign check (U+20B9)
    # Check current file or companion latin-ext file
    has_rupee = 0x20B9 in cmap
    if not has_rupee:
        # Check if the latin-ext companion has it
        ext_candidate = file_path.parent / file_path.name.replace("latin-", "latin-ext-")
        if ext_candidate.exists():
            ext_font = TTFont(str(ext_candidate))
            ext_cmap = ext_font.getBestCmap() or {}
            has_rupee = 0x20B9 in ext_cmap

    # 2. Tabular figures check (digits 0-9 uniform advance width)
    hmtx = font.get("hmtx")
    digit_widths: dict[str, int] = {}
    if hmtx:
        for digit in "0123456789":
            cp = ord(digit)
            glyph_name = cmap.get(cp)
            if glyph_name and glyph_name in hmtx.metrics:
                width, _ = hmtx[glyph_name]
                digit_widths[digit] = width

    is_uniform = len(digit_widths) == 10 and len(set(digit_widths.values())) == 1
    digit_width = next(iter(digit_widths.values())) if digit_widths else 0

    # 3. Licence check
    is_ofl = False
    name_table = font.get("name")
    if name_table:
        for record in name_table.names:
            try:
                text = record.toUnicode().lower()
                if "ofl" in text or "open font license" in text or "sil.org" in text:
                    is_ofl = True
                    break
            except Exception:
                continue

    return FontCheckResult(
        family=family,
        weight=weight,
        has_rupee=has_rupee,
        has_tabular_figures=is_uniform,
        digit_width=digit_width,
        is_ofl=is_ofl,
        file_path=file_path,
    )


def verify_fonts(base_dir: Path | None = None) -> list[FontCheckResult]:
    """Verify all required font variants."""
    root = base_dir or Path("apps/web/node_modules/@fontsource")
    sans_dir = root / "ibm-plex-sans" / "files"
    serif_dir = root / "ibm-plex-serif" / "files"

    if not sans_dir.exists() or not serif_dir.exists():
        raise FileNotFoundError(
            f"Font directories not found at {sans_dir} or {serif_dir}. "
            "Ensure npm install has been run in apps/web."
        )

    targets = [
        ("IBM Plex Sans", sans_dir, 400, "ibm-plex-sans-latin-400-normal.woff2"),
        ("IBM Plex Sans", sans_dir, 500, "ibm-plex-sans-latin-500-normal.woff2"),
        ("IBM Plex Sans", sans_dir, 600, "ibm-plex-sans-latin-600-normal.woff2"),
        ("IBM Plex Serif", serif_dir, 400, "ibm-plex-serif-latin-400-normal.woff2"),
        ("IBM Plex Serif", serif_dir, 500, "ibm-plex-serif-latin-500-normal.woff2"),
        ("IBM Plex Serif", serif_dir, 600, "ibm-plex-serif-latin-600-normal.woff2"),
    ]

    results: list[FontCheckResult] = []
    for family, font_dir, weight, filename in targets:
        file_path = font_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Missing required font file: {file_path}")
        results.append(check_font_file(file_path, family, weight))

    return results


def main(args: list[str] | None = None) -> int:
    """CLI entry point for font verification."""
    parser = argparse.ArgumentParser(description="Verify fonts for ArthaIQ design system.")
    parser.add_argument(
        "--font-dir",
        type=Path,
        default=Path("apps/web/node_modules/@fontsource"),
        help="Path to fontsource directory.",
    )
    parsed = parser.parse_args(args)

    print("=" * 80)
    print("ArthaIQ Font Verification (T9.07, ADR-0007)")
    print("=" * 80)

    try:
        results = verify_fonts(parsed.font_dir)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    all_passed = True
    print(
        f"{'Family':<16} {'Weight':<8} {'Rupee (U+20B9)':<16} {'Tabular Figures':<18} {'Width':<8} {'OFL Licence':<12}"
    )
    print("-" * 80)

    for r in results:
        rupee_str = "PASS (Present)" if r.has_rupee else "FAIL (Missing)"
        tab_str = f"PASS ({r.digit_width}u)" if r.has_tabular_figures else "FAIL (Variable)"
        ofl_str = "PASS (OFL)" if r.is_ofl else "FAIL"

        passed = r.has_rupee and r.has_tabular_figures and r.is_ofl
        if not passed:
            all_passed = False

        print(
            f"{r.family:<16} {r.weight:<8} {rupee_str:<16} {tab_str:<18} {r.digit_width:<8} {ofl_str:<12}"
        )

    print("=" * 80)
    if all_passed:
        print(
            "SUCCESS: All fonts verified for Rupee sign (U+20B9), tabular figures, and SIL OFL licence."
        )
        return 0
    else:
        print("FAILURE: One or more font verification checks failed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
