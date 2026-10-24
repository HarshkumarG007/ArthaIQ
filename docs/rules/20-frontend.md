# Frontend Architecture, Design System & Accessibility Rules (20-frontend)

| Field | Value |
|---|---|
| Topic | Web Application, Design System 'The Span', and WCAG 2.2 AA Accessibility |
| Governing Rule Families | `R-UI`, `design.md`, Principles DP-1 to DP-11 |
| Audience | AI Assistant, Frontend Engineers, Designers |

---

## 1. UI & Design System Rules (R-UI)

| ID | Rule | Description |
|---|---|---|
| **R-UI-01** | **Design Token Exclusivity** | All styles must use design tokens defined in `design.md` and CSS custom properties (`index.css`). Ad-hoc hex values, arbitrary pixel margins, and unapproved utilities are strictly forbidden. |
| **R-UI-02** | **Zero Lone Numbers** | The UI must never display a solitary point estimate for compensation or competency. Always render full distribution intervals ($P_{10}$ to $P_{90}$) with visible RangeSpan graphics. |
| **R-UI-03** | **Transparent Uncertainty States** | When evidence is insufficient or data fails $k_{\min} \ge 5$, render the explicit `AbstentionNotice` rather than fabricating numbers or collapsing to zero. |
| **R-UI-04** | **Typography Standard** | Use IBM Plex Serif for numbers, figures, and display titles; IBM Plex Sans for body, labels, and forms. Browser defaults are barred. |
| **R-UI-05** | **Cobalt-on-Paper Palette** | Preserve the editorial identity: Cobalt Blue (`#0F52BA` / `#2563EB`) as primary accent against Cool Paper (`#F8FAFC` / `#0F172A`) dark/light themes. |
| **R-UI-06** | **Zero Dark Patterns** | No countdown timers, false urgency, artificial streaks, or gating core utility behind data contribution. |

---

## 2. Accessibility & Performance (WCAG 2.2 AA)

1. **Axe Cleanliness:** All views and components must pass Axe Core automated accessibility scans with **0 violations**.
2. **Keyboard Operability:** 100% of interactive elements, forms, and scenario workspaces must be fully navigable and operable via keyboard (`Tab`, `Enter`, `Space`, `Esc`, `j`/`k`/`f` scenario keys). Focus rings must be visible.
3. **Contrast Compliance:** All text and meaningful graphics must meet or exceed WCAG 2.2 AA minimum contrast ratios (4.5:1 for normal text, 3:1 for large text and UI components). Enforced via `make check-contrast`.
4. **Reduced Motion:** Honor `prefers-reduced-motion` media queries for all transitions and micro-animations.
5. **Screen Reader Equivalents:** Every RangeSpan, Gap Map row, and gauge must provide a clear, structured `aria-label` or accessible text description.
