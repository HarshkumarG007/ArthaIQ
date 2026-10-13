# ADR-0007: Frontend Stack

| Field | Value |
|---|---|
| Status | **Proposed** |
| Decided at | T9.07 |
| Relates to | `architecture.md` section 6, `design.md`, `rules.md` R-CD-09, R-UI-01 |

---

## Context

The web application is built in Phase 9 (T9.07 onwards). The design is specified in `design.md`. The frontend must implement the Span, all component states, accessibility (WCAG 2.2 AA), the design token system and the money formatter. The stack must be mainstream, AI-assistant friendly, typed, and testable.

## Proposed stack

| Layer | Choice | Why |
|---|---|---|
| Language | TypeScript strict, no `any` | Type safety; R-CD-09 |
| Framework | React | Mainstream; ecosystem for forms and data fetching |
| Build | Vite | Fast HMR; simple config |
| Styling | Tailwind CSS + design tokens from `design.md` section 13 | Token-driven; shadcn/ui overrides |
| Component primitives | shadcn/ui, restyled per `design.md` | Accessible primitives; tokens override defaults |
| Data fetching / caching | TanStack Query | Typed cache; retry and stale logic |
| Forms | React Hook Form + Zod | Typed validation; aligns with Pydantic on the backend |
| Charts / Span | Custom SVG for the RangeSpan; a small chart library only if needed | The key visual is bespoke |
| Testing | Vitest + Testing Library + Playwright + axe-core | Unit, e2e, accessibility |
| Linting | ESLint with jsx-a11y + Prettier | Accessibility enforced in CI |

## Design system integration

- All colours, fonts, radii and spacing come from `apps/web/src/styles/tokens.css` (generated from one source).
- The shadcn/ui variable mapping is in `design.md` section 13.
- No arbitrary values; no inline styles; no component-library defaults that override `design.md`.

## Acceptance criteria at T9.07

- [ ] `RangeSpan` renders with correct text alternative and table view
- [ ] `formatMoney()` passes Indian grouping and lakh rounding tests
- [ ] Rupee sign (U+20B9) present in IBM Plex Serif and Sans
- [ ] Tabular figures available
- [ ] Contrast script passes in CI
- [ ] Token file generates both light and dark themes from one source

## Decision

**Pending.** Finalized at T9.07 after font verification and token setup.

## Consequences

- The frontend is built only in Phase 9; the research prototype (G6) is API or CLI only (D-008).
- Any change to the design token system after T9.07 runs through the contrast script and a PR.
- Large UI kits and heavy chart libraries are not permitted without updating this ADR.

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
