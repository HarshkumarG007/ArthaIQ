---
trigger: glob
description: Frontend design system 'The Span', design tokens, accessibility, and UI honesty rules
globs: apps/web/**
---

# Frontend Design & Accessibility Rules (R-UI)

Consult canonical specification in `docs/rules/20-frontend.md` and `design.md`.

## Key Invariants
1. **R-UI-01:** Design tokens only (`index.css`). Ad-hoc hex values and unapproved utility classes are forbidden.
2. **R-UI-02:** Zero lone numbers. Always render full distribution spans ($P_{10}$ to $P_{90}$) with visible RangeSpan.
3. **R-UI-03:** Explicit `AbstentionNotice` when data is thin; never fabricate numbers or display false precision.
4. **R-UI-04:** Editorial typography: IBM Plex Serif for numbers/titles, IBM Plex Sans for interface text.
5. **R-UI-05:** Cobalt Blue (`#0F52BA` / `#2563EB`) on Cool Paper (`#F8FAFC` / `#0F172A`) palette.
6. **R-UI-06:** Zero dark patterns (no streaks, false urgency, countdown timers, or contribution gates).
7. **Accessibility:** 0 Axe core violations, full keyboard operability, WCAG 2.2 AA contrast, screen reader equivalents.
