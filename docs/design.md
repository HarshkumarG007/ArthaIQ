# ArthaIQ Design System

| Field | Value |
|---|---|
| Status | Draft v0.2 (direction ratified at T0.05, D-006) |
| Last updated | 2026-10-13 |
| Depends on | `PRD.md` (FR-02, FR-03, FR-04, FR-05, FR-06, FR-08, FR-18, FR-19), `rules.md` (R-UI-01 to R-UI-06) |
| Built in | Phase 9 (T9.07 tokens and components, T9.08 screens, T9.09 accessibility) |

Tags: `[H]` hypothesis · `[U]` unverified external fact · `[TBD: id]` decision owed. Every colour pair below was computed, not assumed. Fonts and glyph coverage are verified at T9.07 before adoption.

This file exists to stop random UI. If a screen needs something this file does not specify, add the specification here first, then build it (R-UI-01).

---

## 1. What this design answers

| | |
|---|---|
| Subject | A pay range for a person's role, level and location, with the evidence behind it |
| Audience `[H]` | Working professionals in India, often on mid-range phones with variable connections, often deciding under some pressure (an offer, a negotiation) |
| Primary job | Read a range, judge how far to trust it, decide what to do next |
| Hard constraints | No lone number (R-UQ-01). Abstention is a designed state (R-UI-03). WCAG 2.2 AA. Indian digit grouping. Dark theme from the start |
| Tone | Calm, exact, unhurried. Closer to a well-edited statistical publication than to a fintech app |

## 2. Principles

| ID | Principle |
|---|---|
| DP-1 | **Range first.** The range is the headline. The typical value is a marker inside it. |
| DP-2 | **Evidence beside every estimate.** Cohort size, source types and recency are never a click away from the number. |
| DP-3 | **Abstention is a result.** It gets a calm, useful screen, not an error state. |
| DP-4 | **No false precision.** Round to a granularity the range can justify. |
| DP-5 | **Reveal progressively, and show effects.** Ask only what is needed now. After each addition, show how the range changed, even when it did not. |
| DP-6 | **Quiet everywhere except the Span.** One memorable element; everything else recedes. |
| DP-7 | **Plain words.** Define terms where they appear, in a popover the user opens, never in hover-only tooltips. |
| DP-8 | **Accessible by construction.** Colour never carries meaning alone. Everything works by keyboard and at 200% zoom. |
| DP-9 | **Light on phones** `[H]`. No heavy assets. Self-hosted fonts. SVG only. |
| DP-10 | **Local numbers.** Indian grouping and lakh shorthand are first-class. |
| DP-11 | **No manipulation.** No urgency, streaks, completeness meters or pressure to share more. |

## 3. Choices made and defaults rejected

| Default considered | Why rejected | What this design does instead |
|---|---|---|
| Teal accent on slate neutrals with a grid of identical rounded cards | A generic SaaS kit that says nothing about measurement | Cobalt on cool paper. Structure comes from hairline rules and spacing. The Span is the single memorable element |
| Inter or the system sans for everything | The choice anyone makes without thinking | IBM Plex pairing: serif for figures, sans for interaction, with a Devanagari companion available for later Hindi `[U]` |
| Giant gradient number plus a "confidence 87%" badge | Implies precision the data cannot support | Range headline. Evidence in words and a three-tick gauge |
| A row of attribute chips joined by dots | Template chrome | One plain sentence that defines the measure, with a definition popover |
| Warm cream background with serif and terracotta | A common generated look | Cool paper and blue-black ink, no warm accent |
| Saffron, white and green for an Indian audience | National symbolism risks an unintended political reading | A neutral palette |
| Count-up animation on the result | Reads as "AI computing" and carries no meaning | Motion only when the user acts, and only to show what changed |

---

## 4. The Span

The Span is the product's signature element: an engineering **dimension line** applied to pay. A measured span between two end caps, a notch for the typical value, extension lines down to a quiet scale. It reads as "measured, with limits", not as a point with error bars.

**Anatomy**

1. **Scale.** A hairline baseline with ticks at round steps (1, 2 or 5 × a power of ten, in lakh or thousands) giving four to eight ticks. On compact screens, label every second tick.
2. **Dimension line.** A 2px line in `--span` between two end caps 12px tall, at P10 and P90.
3. **Wash.** `--span-wash` fills the span between the extension lines and the baseline.
4. **Median notch.** A 10px triangle in `--ink` pointing at the baseline, labelled "Typical".
5. **End labels.** Amounts in the serif figure style, with "Lower end" and "Higher end" in sans above.
6. **Second marker** (compare view). A diamond in `--ink` labelled "Your figure". The scale extends to include it. If it falls more than three span-widths outside, show an off-scale chevron and say so in text.
7. **Ghost span** (refine view). The previous span stays above as a 1px line in `--ink-3`, labelled "Before". The new caps animate from the old positions in 220ms. Under reduced motion they jump, and the ghost remains.

**States**

| State | Treatment |
|---|---|
| Default | As above |
| Limited evidence (grade C) | Dimension line dashed; caution sentence beneath in `--caution`. Never red |
| Loading | Static placeholder line, no shimmer; `aria-busy` |
| Abstained | **No Span.** The abstention notice replaces it. A Span with invented numbers is never drawn |
| Stale data | Caution banner above (section 8) |
| Scenario comparison (deferred) | Two spans on one shared scale |

**Accessibility.** The Span is `role="img"` with a generated label: "Estimated range: from {p10} to {p90} a year. Typical value {p50}. {measure}, before tax, {currency}, as of {date}." A "View as table" button reveals a three-row table (Lower end, Typical, Higher end) with definitions. Line and caps use `--span`, at least 6:1 against the surfaces they sit on (section 5).

**Never**: stretch or truncate the scale to exaggerate width · show only the typical value · use a gradient that implies a density shape · draw percentiles that are not calibrated · animate on page load · encode meaning by colour alone.

---

## 5. Color

Light and dark themes share one hue family: blue-black ink, cool paper, one cobalt accent.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#F5F6F8` | `#0C1424` | Page background |
| `--sheet` | `#FFFFFF` | `#131D33` | Reading surfaces, inputs, popovers |
| `--sunken` | `#EBEEF3` | `#0A101D` | Recessed areas, abstention notice |
| `--rule` | `#D5DAE3` | `#2C3A5C` | Hairline structure (decorative only) |
| `--rule-strong` | `#6B7589` | `#8190AE` | Control borders and anything needed to identify a control |
| `--ink` | `#17213A` | `#E8ECF6` | Primary text, median notch |
| `--ink-2` | `#434E66` | `#B7C0D6` | Secondary text |
| `--ink-3` | `#5B667D` | `#98A3BD` | Tertiary text, placeholders, ghost span |
| `--span` | `#2447C6` | `#8EA6FF` | Span line and caps, links, primary button |
| `--span-strong` | `#1B3799` | `#B4C3FF` | Hover, pressed, focus ring |
| `--span-wash` | `#E4EAFB` | `#1F2F63` | Span fill, selected rows |
| `--on-span` | `#FFFFFF` | `#0C1424` | Text on a `--span` fill |
| `--ok`, `--ok-wash` | `#1E7A4C`, `#E6F4EC` | `#6FD3A0`, `#12301F` | Consent given, record validated |
| `--caution`, `--caution-wash` | `#8A5300`, `#FBF1DC` | `#F0B35A`, `#3A2A0A` | Limited evidence, stale data, definition mismatch |
| `--alert`, `--alert-wash` | `#B3261E`, `#FBE9E7` | `#FF9E96`, `#3D1512` | Errors, destructive actions |
| `--focus` | `#1B3799` | `#B4C3FF` | Focus ring |

**Verified contrast** (WCAG relative luminance, computed 2026-10-11). Text needs 4.5:1; non-text parts needed to identify a control or read the Span need 3:1.

| Pair | Light | Dark |
|---|---|---|
| `--ink` on `--paper` | 14.77 | 15.56 |
| `--ink` on `--sheet` | 15.97 | 14.19 |
| `--ink-2` on `--sheet` | 8.33 | 9.21 |
| `--ink-3` on `--sheet` | 5.77 | 6.64 |
| `--ink-3` on `--sunken` | 4.96 | 7.52 |
| `--span` as text on `--sheet` | 7.52 | 7.23 |
| `--on-span` on `--span` (button) | 7.52 | 7.93 |
| `--ink` on `--span-wash` | 13.28 | 10.80 |
| Control border `--rule-strong` on `--sheet` | 4.63 | 5.22 |
| Control border `--rule-strong` on `--sunken` | 3.99 | 5.91 |
| Span line `--span` on `--span-wash` | 6.25 | 5.50 |
| Focus ring `--focus` on `--sheet` | 10.23 | 9.74 |
| `--ok` on `--ok-wash` | 4.70 | 7.83 |
| `--caution` on `--caution-wash` | 5.64 | 7.46 |
| `--alert` on `--alert-wash` | 5.58 | 8.05 |

`scripts/check_contrast.py` is added at T9.07 and runs in CI, so a token change cannot silently regress these.

**Usage rules**

1. `--span` is the only chromatic accent in the interface chrome.
2. Semantic colours appear only when they mean something: ok for consent and validation, caution for limited evidence, staleness and definition mismatch, alert for errors and destructive actions.
3. Abstention is neutral: `--ink-2` on `--sunken`. Never caution or alert colours.
4. Never use red or green to suggest higher or lower pay.
5. Colour never carries meaning alone. Pair it with words, ticks or icons.
6. Avoid saffron, white and green together, and avoid national symbols `[design judgment]`.

---

## 6. Typography

| Role | Family | Why |
|---|---|---|
| Figures and titles | IBM Plex Serif | Reads as a published statistic; set with tabular lining figures |
| Interface and body | IBM Plex Sans | Clear numerals and forms; same superfamily as the serif |
| Hindi (deferred) | IBM Plex Sans Devanagari `[U: confirm availability and licence]` | Matching design for later localization |
| Code and ids | `ui-monospace` stack | Rare; never for small data labels |

Licence is expected to be SIL OFL `[U: confirm at T9.07]`. **Self-host** subsetted WOFF2 files. No third-party font requests.

**Verify before adopting (T9.07 acceptance):** both families contain the rupee sign (U+20B9); tabular figures are available by default or through OpenType `tnum`; the metric-matched fallback keeps layout shift low with `font-display: swap`. If any check fails, replace the family and update this file.

Fallbacks: serif `"Iowan Old Style", "Palatino Linotype", Georgia, serif`; sans `system-ui, "Segoe UI", Roboto, "Noto Sans", sans-serif`.

| Style | Family and weight | Size and line height | Use |
|---|---|---|---|
| display | Serif 600 | 2.25rem / 1.15 (compact: 1.75rem / 1.2) | The range headline only |
| title | Serif 500 | 1.5rem / 1.25 | Page and section titles |
| heading | Sans 600 | 1.125rem / 1.35 | Subsections |
| body | Sans 400 | 1rem / 1.55 | Default text |
| prose | Serif 400 | 1.0625rem / 1.65 | Long explanatory pages (model card, sources) |
| small | Sans 400 or 500 | 0.875rem / 1.45 | Helper text, the disclaimer, table cells |
| note | Sans 400 | 0.8125rem / 1.4 | Smallest size; never essential information |

Rules: weights 400, 500, 600 only · sentence case everywhere · no all-caps labels, no letter-spacing tricks · prose lines at most 68 characters · `font-variant-numeric: tabular-nums lining-nums` on every figure · numbers right-aligned in tables · left-aligned body text, never centred paragraphs.

---

## 7. Layout, spacing, shape, motion

| Topic | Specification |
|---|---|
| Grid | 4px base. Spacing steps: 4, 8, 12, 16, 24, 32, 48, 64 |
| Breakpoints | Compact below 640px · medium 640 to 899px · wide from 900px. Support 320px width |
| Content width | Maximum 1120px; two columns from 900px (form left at about 320px, result right) |
| Structure | Hairline rules (`--rule`) and spacing, not boxed cards. A section is a heading over a top rule |
| Radius by role | Controls 6px · dialogs and bottom sheets 12px · data blocks 0 |
| Elevation | None in flow. One shadow token for popovers and dialogs: `0 8px 24px rgb(23 33 58 / 0.14)`. In dark theme use a border instead |
| Motion | 120ms for state changes, 220ms for the Span and disclosures, ease-out. Only in response to a user action. `prefers-reduced-motion` removes all non-essential motion |
| Icons | Lucide, 1.5px stroke, 16 or 20px. Never the only carrier of meaning. No emoji |
| Focus | Double ring: 2px `--sheet` gap then 2px `--focus`. Never removed |
| Touch targets | At least 44px on compact; never below 24px (WCAG 2.2 minimum) |

---

## 8. Components

Names are the code names. Build them in `apps/web/src/components/`.

### EstimateHeadline

1. Title: "Estimated range" (serif title).
2. Display line: `₹{p10} to ₹{p90} lakh a year`, or `${p10} to ${p90} a year` in USD.
3. Typical line: "Typical: ₹{p50} lakh" in body, `--ink-2`.
4. Definition sentence: "{Measure}, before tax, in rupees, as of {Month YYYY}." The measure name is a DefinitionPopover trigger.

Money formatting goes through one `formatMoney()` (R-UI-06): INR in lakh to one decimal (crore from 100 lakh), table cells in full Indian grouping (`1,23,456`, not `123,456`), USD with thousands separators. Display rounding defaults: INR to 0.1 lakh, USD to $1,000 `[H: tune at T9.15]`. Never imply precision finer than the range supports. Do not rely on browser compact-number notation for lakh; test the formatter.

### RangeSpan

Section 4. Props: `p10`, `p50`, `p90`, `currency`, `state`, optional `compareValue`, optional `previous`. It owns its text alternative and table view.

### SpanDelta

Wraps RangeSpan with the ghost. Beneath it, one sentence in plain words: "The range got narrower.", "The range got wider.", or "The range did not change much." Followed by: "This reflects patterns in the data, not what you would earn by changing this detail." Never celebrate narrowing.

### EvidenceList and EvidenceGauge

A definition list with hairline rules between rows. Not cards, not chips.

| Row | Content |
|---|---|
| Evidence | Gauge plus word: three ticks "Strong", two "Moderate", one "Limited" |
| Comparable records | "{n} records from {k} sources" |
| Source types | "{type} {share}, {type} {share}" as text |
| Recency | "Median record age {m} months; newest {Mon YYYY}" |
| Model and data | `{model_version}`, `{data_snapshot_id}` in small text |
| Known limits | Two or three plain sentences, with a link to the model card |

The gauge is ticks plus a word, never a percentage (R-UI-02). Grade logic lives in the API (FR-19); the UI only renders it.

### AbstentionNotice

A notice with a 3px left rule in `--ink-3` on `--sunken`, an `Info` icon, a heading, reasons and next options. No Span, no model number.

| Reason code | Text |
|---|---|
| `INSUFFICIENT_SUPPORT` | We have too few comparable records for this combination. |
| `OUT_OF_RANGE` | This profile is unusual compared with the records we have. |
| `STALE_DATA` | The newest records for this combination are too old. |
| `LOW_SOURCE_QUALITY` | The records we have for this combination are not reliable enough. |
| `INTERVAL_TOO_WIDE` | The range would be too wide to be useful. |

Offer only options that exist: broaden the role or location (with the nearest supported option named), an official benchmark for a wider group (labelled "not personalized"), and adding your own record in beta.

### ProfileForm

Section "About the role": Role, Location, Years of relevant experience, with "Not sure" available. Primary button "Show estimated range". After the first result, optional disclosures appear: Skills, Industry and employer type, Work arrangement. Each says why it is asked. Only families that passed the ablation gate appear (FR-05). No step numbers, no progress bar, no percentage complete (DP-11).

Controls:

| Control | Rules |
|---|---|
| OccupationCombobox | Type-ahead over the taxonomy; shows the canonical title and "also known as"; keyboard operable; "I can't find my role" sends a request without personal data |
| LocationSelect | Search over city and region; grouped |
| Experience | Number input with `inputmode="decimal"`; hint: "Count time in similar roles. Round to the nearest half year." Alternative: level select |
| MoneyField | Currency prefix; Indian grouping as the user types; explicit per-year or per-month toggle; "Which figure is this?" helper: fixed pay, CTC, in-hand, total including bonus, with plain explanations and "Not sure" |
| Button | Primary: `--span` fill, `--on-span` text. Secondary: 1px `--rule-strong` border, `--ink` text. Tertiary: underlined link in `--span`. Destructive: `--alert` fill. Min height 44px on compact. No trailing arrows or decorative icons |
| Forms | Labels above fields. Helper text below. Errors below with an icon and text. Error summary at the top on submit. `aria-describedby` wiring. User input kept on error. Never placeholder-as-label |

### PayCompare

Input: MoneyField with the definition helper. Output sentence: "Your figure is inside the estimated range." (or "below", "above"), then "It sits around the {a}th to {b}th percentile of comparable pay. The band is wide because the estimate itself is uncertain." Then the Span with the "Your figure" marker. Always add: "Your pay may reflect things this estimate does not include, such as scope, employer or timing." If the user's measure differs from the estimate's, show a caution notice (section 10). Never say "underpaid" or "overpaid".

### ExplanationList

MVP: plain cohort statements. Beta: model drivers with small bars, headed "How the model reached this range", followed by: "This describes the model. It does not show what would change your pay." (R-MD-08).

### DefinitionPopover

A term with a dotted underline that opens a popover on click, tap or Enter. Short definition plus a glossary link. Focus moves in and returns on Esc. Essential definitions are never hover-only.

### DisclaimerLine

"This range is an estimate from data of varying quality. It is not an offer, appraisal or guarantee." In `small` size, `--ink-2`, directly under the evidence list. Always visible; never collapsed or moved to a footer (FR-18).

### ContributionFlow (beta)

A real sequence, so "Step 1 of 3" is allowed here. Consent comes first, unbundled, unchecked by default, one purpose per checkbox, with what is stored, for how long and how to delete. Then pay details with the definition helper, then confirmation with a summary and a delete link. No document uploads unless ADR-0008 approves.

### State views

| State | Specification |
|---|---|
| Loading | Skeleton lines, no spinner under one second, no fake progress, `aria-busy` |
| Empty | "Enter a role, location and experience to see an estimated range." |
| Error | What happened, what to do, reference id. Retry button "Try again". No apology |
| Offline | "You're offline. Reconnect to see an estimate." |
| Stale | Caution banner: "The newest records for this combination are from {Mon YYYY}. Treat this range with extra caution." |

### Tables and other charts

Tables (sources, model card): right-aligned numerals, units in headers, `aria-sort` on sortable columns, hairline rules, no zebra. Other charts are limited to quantile strips of aggregated cohorts (k_min applies) and internal monitoring bars. Direct labels, zero baseline for bars, no 3D, no pies, no dual axes, a table alternative for every chart.

---

## 9. Screens and wireframes

**Layout concept.** One reading column per task. The question sits on the left, the answer on the right, and the Span runs the full width of the answer. Text is left-aligned. Sections are separated by hairline rules. On compact screens the form comes first and the result follows beneath it.

**Estimate screen, wide**

```text
+------------------------------------------------------------------------------+
| ArthaIQ                                              INR  USD        Sign in |
+------------------------------------------------------------------------------+
|                                                                              |
| About the role                   | Estimated range                           |
| -------------------------------- | ----------------------------------------- |
| Role                             | ₹{p10} to ₹{p90} lakh a year              |
| [ Software engineer          v ] | Typical: ₹{p50} lakh                      |
|                                  | Fixed annual cash pay, before tax,        |
| Location                         | in rupees, as of {Month YYYY}.            |
| [ Bengaluru                  v ] |                                           |
|                                  | Lower end          Typical     Higher end |
| Years of relevant experience     | |<-------[=========v=========]------->|   |
| [ 4    ]   Not sure              | ₹{p10}             ₹{p50}          ₹{p90} |
|                                  |                                           |
| [ Show estimated range ]         | What this is based on                     |
|                                  | ----------------------------------------- |
| Add detail (optional)            | Evidence     [##-]  Moderate              |
| > Skills                         | Comparable   {n} records, {k} sources     |
| > Industry and employer type     | Recency      Median {m} months old        |
| > Work arrangement               | Model        {model_version}              |
|                                  |                                           |
|                                  | This range is an estimate from data of    |
|                                  | varying quality. It is not an offer,      |
|                                  | appraisal or guarantee.                   |
|                                  |                                           |
|                                  | [ Refine estimate ]  [ Compare my pay ]   |
|                                  | How this was calculated   Data sources    |
+------------------------------------------------------------------------------+
```

**Abstention screen, compact**

```text
+--------------------------------+
| ArthaIQ           INR   USD    |
+--------------------------------+
| Role                           |
| [ {less common role}     v ]   |
| Location                       |
| [ {smaller city}         v ]   |
| Years of relevant experience   |
| [ 2 ]   Not sure               |
| [ Show estimated range ]       |
|                                |
| (i) We can't give a reliable   |
|     range for this yet.        |
|                                |
|     We have too few            |
|     comparable records for     |
|     this combination.          |
|                                |
|     What you can try           |
|     - Broaden the location.    |
|       Try {nearest area}.      |
|     - See an official          |
|       benchmark for a wider    |
|       group. It is not         |
|       personalized.            |
|     - Add your own record      |
|       (beta).                  |
|                                |
| Estimates are decision         |
| support, not an offer.         |
+--------------------------------+
```

| Screen | Purpose | Stage |
|---|---|---|
| Estimate | Profile form and result | PB |
| Refine | Optional details with SpanDelta, inline | PB |
| Compare | PayCompare, inline panel | PB |
| How this was calculated | Model card in plain language | PB |
| Data sources | Sources, licences, freshness | PB |
| Contribute | ContributionFlow | PB |
| My data | View, export, delete | PB |
| Monitoring | Internal coverage, drift, freshness | PB |
| Not found and error | Plain-language pages with reference id | PB |

---

## 10. Content and microcopy

**Voice.** Plain, direct, calm. Active voice. Sentence case. No exclamation marks. Errors do not apologize; they say what happened and what to do. Empty states invite the next action. A button's name reappears in its confirmation. One name per action across the product.

| Use | Avoid | Why |
|---|---|---|
| Estimated range | Your salary, predicted salary, AI estimate | Not a prediction of one number |
| Typical | Average | Mean and median differ; "typical" is defined as the middle value |
| Lower end, higher end | Min, max, floor, ceiling | They are not limits |
| Evidence: strong, moderate, limited | Confidence score 87% | False precision |
| Based on {n} comparable records | Based on millions of data points | Say what is true for this estimate |
| Associated with | Will increase, boosts, is worth | Association is not cause |
| Fixed annual cash pay | Salary, CTC, package, used loosely | Each is defined separately |

Coverage statement (in the typical-value and range definitions): "The range is designed so that about 8 in 10 comparable outcomes fall inside it. We check this against new data." Use only after the model card confirms the nominal level.

**Forbidden phrases:** underpaid · overpaid · you should ask for · guaranteed · AI-powered accuracy · negotiate {x}% more · best offer · limited time.

| Context | Text |
|---|---|
| Primary action | Show estimated range |
| Refine | Refine estimate |
| Compare | Compare with my pay |
| Loading | Calculating the range |
| Validation, experience | Enter years of experience as a number, like 4 or 4.5. |
| Role not found | We don't have that role yet. Pick the closest match, or tell us what's missing. |
| Definition mismatch | You chose {their measure}, but this range is for {estimate measure}. The comparison may be off. |
| Generic error | Couldn't load the estimate. The server didn't respond. Try again, or reload the page. Reference {request_id}. |
| Consent | Use my record to improve estimates for everyone. You can delete it at any time. |
| Deletion done | Deleted. Your record is removed. Statistics that included it update at the next data refresh on {date}. |

---

## 11. Accessibility checklist

Target WCAG 2.2 AA `[U: confirm no newer Recommendation at T9.09]`.

- [ ] Text contrast at least 4.5:1; non-text parts at least 3:1 (script in CI)
- [ ] Every function works by keyboard; order follows reading order; focus is never lost or hidden
- [ ] Visible focus on every control; focus not obscured by sticky elements
- [ ] Touch targets meet the sizes in section 7
- [ ] Reflow at 400% zoom with no two-dimensional scrolling for text
- [ ] Meaning never carried by colour alone
- [ ] RangeSpan has a text alternative and a table view
- [ ] Forms: programmatic labels, errors identified in text, error summary, input preserved
- [ ] Popovers and dialogs trap and restore focus; Esc closes
- [ ] Status changes announced (`aria-live="polite"`); loading uses `aria-busy`
- [ ] `prefers-reduced-motion` and `prefers-color-scheme` respected
- [ ] Page language set; heading levels in order; one `h1` per page
- [ ] Axe checks in CI plus a manual screen-reader pass of the estimate, abstention and compare flows

## 12. Responsive behaviour and performance

| Topic | Rule |
|---|---|
| Compact | Single column, form then result. Span full width with stacked labels. Tables become definition lists |
| Wide | Two columns; result column sticky only if it never hides content |
| Images | None required. Icons and the Span are SVG |
| Fonts | Subsetted, self-hosted WOFF2, preloaded for the display and body styles |
| Third parties | No analytics or font scripts that receive personal data |
| Web vitals | Targets: LCP 2.5s or less, INP 200ms or less, CLS 0.1 or less, on a throttled mid-range mobile profile `[U: confirm current thresholds at T9.15]` |
| Bundle | Initial JavaScript budget `[TBD: T9.07]`, enforced in CI |

---

## 13. Tokens in code

Single source: `apps/web/src/styles/tokens.css`, generated from one token file so light and dark cannot drift.

```css
:root {
  --paper: #F5F6F8;  --sheet: #FFFFFF;  --sunken: #EBEEF3;
  --rule: #D5DAE3;   --rule-strong: #6B7589;
  --ink: #17213A;    --ink-2: #434E66;  --ink-3: #5B667D;
  --span: #2447C6;   --span-strong: #1B3799;  --span-wash: #E4EAFB;  --on-span: #FFFFFF;
  --ok: #1E7A4C;     --ok-wash: #E6F4EC;
  --caution: #8A5300; --caution-wash: #FBF1DC;
  --alert: #B3261E;  --alert-wash: #FBE9E7;
  --focus: #1B3799;
  --radius-control: 6px;  --radius-dialog: 12px;
  --font-serif: "IBM Plex Serif", "Iowan Old Style", "Palatino Linotype", Georgia, serif;
  --font-sans: "IBM Plex Sans", system-ui, "Segoe UI", Roboto, "Noto Sans", sans-serif;
}
:root[data-theme="dark"] {
  --paper: #0C1424;  --sheet: #131D33;  --sunken: #0A101D;
  --rule: #2C3A5C;   --rule-strong: #8190AE;
  --ink: #E8ECF6;    --ink-2: #B7C0D6;  --ink-3: #98A3BD;
  --span: #8EA6FF;   --span-strong: #B4C3FF;  --span-wash: #1F2F63;  --on-span: #0C1424;
  --ok: #6FD3A0;     --ok-wash: #12301F;
  --caution: #F0B35A; --caution-wash: #3A2A0A;
  --alert: #FF9E96;  --alert-wash: #3D1512;
  --focus: #B4C3FF;
}
/* Repeat the dark block inside @media (prefers-color-scheme: dark)
   for :root:not([data-theme="light"]). Generate both from one source. */
body { font-family: var(--font-sans); color: var(--ink); background: var(--paper); }
.figure { font-family: var(--font-serif); font-variant-numeric: tabular-nums lining-nums; }
```

**Mapping to shadcn/ui variables** `[U: verify names against the installed version at T9.07]`. Override its defaults so the component library never sets the look.

| shadcn variable | Token |
|---|---|
| `--background` | `--paper` |
| `--foreground` | `--ink` |
| `--card`, `--popover` | `--sheet` |
| `--card-foreground`, `--popover-foreground` | `--ink` |
| `--primary` | `--span` |
| `--primary-foreground` | `--on-span` |
| `--secondary`, `--muted` | `--sunken` |
| `--secondary-foreground` | `--ink` |
| `--muted-foreground` | `--ink-3` |
| `--accent` | `--span-wash` |
| `--accent-foreground` | `--span-strong` |
| `--destructive` | `--alert` |
| `--border` | `--rule` |
| `--input` | `--rule-strong` |
| `--ring` | `--focus` |
| `--radius` | `--radius-control` |

---

## 14. Rules for AI-generated UI

| Do | Do not |
|---|---|
| Use tokens from section 13 only | Introduce a colour, font, radius or shadow that is not a token |
| Build from the component specs in section 8 | Invent a new card, badge or widget |
| Implement all states (R-UI-03) | Ship a happy path only |
| Write copy from section 10 | Improvise marketing copy or reassurance |
| Test at 360px width and 200% zoom, in light and dark | Check only a wide light screen |
| Reuse `formatMoney()` and `RangeSpan` | Format money inline or draw ranges ad hoc |
| Structure with rules and spacing | Wrap everything in identical rounded, shadowed cards |
| Keep one accent | Add gradients, glass effects or decorative blobs |
| Use sentence case | Use all-caps labels, tracked-out eyebrow text or labels joined by middle dots |
| State actions in words | Append arrows to links and buttons, or add sparkle and "AI" icons |
| Animate only to show a change the user caused | Add entrance or count-up animation |
| Show higher and lower pay in words and position | Colour pay red or green |

## 15. Design acceptance checklist

- [ ] No lone number anywhere; range, definition and as-of date accompany every figure
- [ ] Evidence and the disclaimer are visible without scrolling past the Span on wide screens
- [ ] Abstention, limited-evidence, stale, loading, error and offline states exist for every estimate view
- [ ] All colours and type come from tokens; contrast script passes
- [ ] RangeSpan has a text alternative, a table view and a reduced-motion path
- [ ] Copy matches section 10; no forbidden phrases
- [ ] Works at 320px, 200% zoom, light and dark, keyboard only
- [ ] Fonts verified for the rupee sign and tabular figures
- [ ] Money formatting tested against Indian grouping and the rounding rules

## 16. Change log

| Date | Version | Change |
|---|---|---|
| 2026-10-11 | 0.1 | Initial draft |
