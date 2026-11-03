# Interaction specification

All behavior below describes the **proposed redesign**, unless explicitly called existing. Static SVGs illustrate hierarchy and states, not functioning controls.

## Navigation and route state

Primary navigation: Overview, Explore, Research, Data & methods. Logo returns to Overview; active destination uses aria-current, visual underline and weight. Skip link goes to main. Mobile Menu opens an accessible navigation dialog, not an unmanaged sidebar.

Proposed URLs (base-path aware):
- `/`: overview.
- `/explore?type=hdb&period=2025&minSales=150&metric=median_price&dir=asc&view=list`.
- `/areas/tampines?type=hdb&period=2025`: area fieldnote, with a validated return-to explorer context.
- `/research/trends`, `/research/segments`, `/research/tools`, `/research/map`: explicit capability destinations / aliases.
- `/analytics/*`: retain published article URLs.
- `/data`: methods guide, linking to retained `/catalog/*`.

Normalize unknown query values to documented defaults and announce the correction. Do not accept arbitrary return-to URLs; preserve only internal known query state. Back restores committed settings, search, selected area and scroll anchor. Shareability of this state is proposed; current hooks are mostly local component state.

Legacy /dashboard, map, leaderboard, trends and segments links must still reach equivalent capabilities. Static-hosting compatibility pages/redirects must honor BASE_URL and query strings. Do not drop working tools/persona/catalog entry points during the new-shell rollout.

## Overview

- Show fixed supported 2025 complete-year medians by type, counts and source.
- Bars are comparisons, not clickable secrets; the named “Explore HDB areas” button starts the primary journey.
- Full accessible table includes property type, period, median transaction price, count.
- Research teaser opens the existing lease-decay article. Its question is editorial copy, not a claim that new analysis was performed.
- Source links open definitions within the app; filenames are explanatory provenance, not broken local-download links.
- Do not animate counters from zero, imply live streaming, or use a current-date freshness badge.

## Explorer

### Committed settings
Default: HDB, 2025, ≥150 sales, median_price ascending, chart/list.
- Property is a single selection: HDB / EC / Condo.
- Period menu: 2025 complete year; 2022 onward (through observed coverage); through 2021; all history. Display actual start/end alongside any open-ended period.
- Call “through 2021” literally; do not use “pre-COVID”.
- Use joint section price/PSF/count only. A missing combination is unavailable; never borrow the closest period/type.
- Sample checkbox excludes selected-subset counts below 150 by default. Show hidden count. Unchecking includes thin areas, badges them and keeps their small denominators visible.
- Threshold is a caution policy, not significance testing or the existing exporter's trailing-window rank gate.
- Search applies case-insensitive trimmed substring matching on area names only. Debounce announcement, not basic input responsiveness. Search is not address search.
- Sort menu: median price low/high, median PSF low/high, sales high/low. Metric change updates plot/axis/column label and matching national reference where one exists. Volume has no national-median reference.
- Equal values sort alphabetically by canonical area key. Missing values sort last with “—”, not 0.
- Reset returns to defaults, clears search, starts first page and announces change.

### Pagination and responsive identity
- Desktop: 12 rows/page. 25 eligible areas → 3 pages.
- Mobile: 4 rows/page. Same 25 → 7 pages. SVG 05 shows the same first four records as SVG 02.
- Show Previous/Next and page position; hide or disable at ends with proper semantics. Desktop first-page SVG only illustrates Next.
- Keep canonical first visible area as the anchor when viewport/page size changes; do not silently select another area. Search or settings change resets pagination.
- Every row has a named area link. A row-sized pointer target is allowed, but only one clear keyboard link is required; no click-only tr.
- Area selection synchronizes map and list and displays a textual selected status. Opening a fieldnote is a separate named link/activation.
- Do not introduce accounts or persistent shortlist state.

### Chart/list, Map and Table
- These are one dataset and selection state with three representations; no separate filter defaults.
- Chart/list desktop: shared 0–S$1m dotplot in the illustrated HDB state, exact values and samples beside it. National median = S$628,000, dashed vertical line and textual label.
- Mobile: exact price plus sales first; aligned mini-bars share 0–S$1m, national marker labeled in text. Do not autoscale each row.
- For other property types/metrics, use a shared zero-based domain that includes all selected-set values and reference; round outward to readable ticks. Never clamp higher prices into the HDB demo scale.
- Map uses the same section, domain, units and selected area. No-data polygons get distinct patterned/neutral treatment and label, not zero color. Optional spatial context is not a scoring system.
- Lazy-load Leaflet/tile resources only when Map is selected. Preserve provider attribution and support a geometry-only or textual fallback when tiles fail. Do not put private API credentials into the client.
- Provide zoom buttons with names and a “Skip map to area list” link. Chart/list remains usable with no external tiles.
- Table: caption names period, property, metric and source; numeric cells align, sort buttons expose aria-sort, area names are links.
- No tooltip-only definitions. Hover/focus details supplement always-visible units and values.

## Area detail

- Proposed static /areas/[slug], generated only for supported canonical planning areas. Preserve query type/period.
- Same-year/type national baseline is required to calculate a difference. Missing or incompatible baseline → omit comparison, retain area values and explain why.
- Tampines example: S$710,000 vs S$628,000, difference S$82,000 and 13.1%. Label as a median-level difference, never growth, premium, uplift or causation.
- PSF median S$620 vs national S$603 is separate from transaction median. Do not infer a representative area by division.
- Show exact sample 1,921, period, evidence kind, underlying source rows, limitations and source timestamps/unknowns.
- Missing flat-size, lease and floor controls are not disabled “coming soon” sliders; say these dimensions are unavailable in this view.
- On mobile: title wraps at 34px, comparison bars stack vertically full-width, limitations follows chart, underlying rows become an accessible compact table or labeled definition groups; never horizontal-page scroll.
- Back to Explore restores originating state. A direct deep link provides a sensible default explorer return; no history.back dependency.

## Data & methods and research

Three distinct clocks: observation period, asset export time, source publication time. Label unknowns. Do not call an old export “source-stale” based solely on its generation date.

Evidence labels:
- Observed aggregate.
- Derived estimate / formula + assumptions.
- Research model + training/publication vintage.
- Unavailable / freshness unknown.

Research secondary navigation explicitly exposes Studies, Trends, Segments, Tools and Research map. Preserve `/dashboard/map` legacy layer state, `/dashboard/segments` research selection and `/dashboard/trends` tools while adding aliases; that last route is not a trend-series page.

Research index retains reports, segment investigation, trends and calculators. Keep report headings and table-chart opt-in semantics; descriptive dictionaries/inventories are not auto-charted. A future research refactor must audit modeled yields and forecasts first. Do not remove tools merely because they are absent from the new primary overview.

## Mobile filter sheet

Illustrated in SVG 06; apply to a full-height mobile dialog, not a fixed 530px content container.
1. Filters opens a draft copy of committed settings; focus dialog title/first meaningful control; background becomes inert.
2. Controls change draft only. Prospective result count updates from loaded data, politely, without moving focus.
3. Sticky Apply footer remains reachable above browser/keyboard safe area. If preview data is unavailable, label Apply without a numeric count.
4. Apply commits settings, updates URL and results, closes sheet and restores focus to Filters; announces “25 areas, HDB, 2025”.
5. Cancel, close and Escape discard draft. Backdrop dismissal may cancel, but never apply.
6. Tab/Shift-Tab remain within the dialog; focus returns to opener. Browser Back closes the open sheet before navigating if modal state is in history.

## States and recovery

| State | What remains / action | Accessibility |
|---|---|---|
| Loading | Question + settings stay; neutral non-numeric skeleton; no zero-price placeholder | aria-busy region; one polite loading announcement; reduced-motion static alternative |
| No search results | Preserve query/settings; Clear search | Announce 0 matches, keep input focus |
| Empty subset | “No records for this combination”; explicit change type/period | Distinguish from network failure, no silent widening |
| First-load failure | Clear error, Retry; no fabricated empty market | role=alert once; keyboard retry |
| Failed refresh with cache | Retain last successful data, timestamp/unknowns and Retry update | Status associated with displayed result; avoid repeated alerts |
| Mixed asset generations | Omit national difference/reference until compatible; explain | Do not render stale baseline as current |
| Thin sample included | Visible sales count and caution; allow exclude | Badge text, not just orange color |
| Selected area | Name, marker/icon, selected text, detail link | Announce selection; focus is not lost to rerender |
| Invalid deep link | Unknown area or unsupported combination; link back to Explorer | Proper not-found/unavailable page and unique H1 |

Retry scope is the affected static asset, not “rerun the pipeline” for public users. Prevent duplicate in-flight retries and preserve existing data on background failure.

## Accessibility acceptance requirements

- Semantic header/nav/main/footer, one page H1, ordered heading levels, visible skip link.
- Inputs have persistent labels, fieldsets/legends for grouped radios, selected states via checked/aria-pressed as appropriate, 44×44 CSS-pixel target policy.
- All normal text ≥4.5:1; large text ≥3:1; meaningful non-text boundaries/marks ≥3:1. Teal/rust/plum never solely communicate meaning.
- Keyboard focus 2px minimum high-contrast outline with offset; visible in dialogs, chart/table controls and nav.
- Native anchors/buttons/selects before custom widgets; no clickable divs or rows as the only activation.
- No forced horizontal body scrolling at 320px or 200% text resize. Tables may have a labeled local overflow region only if a reflow alternative is insufficient.
- Charts expose concise accessible names, textual findings, source and data table; use SVG marks/library output without making every decorative mark a tab stop.
- Modal focus trapping, Escape, background inertness and focus restoration tested, not just specified.
- Announce result counts after committed changes and announce error once; no noisy announcements for every slider/key event.
- Respect reduced motion and OS zoom. Dark mode, if retained, needs independent chart/contrast tokens; these light-mode SVGs do not validate it.

## Revision 2 feature contracts

[feature-specifications.md](feature-specifications.md) is normative for observed map bins, nine research layers, trends, segment discover/investigate/compare, all four calculators, article reading and catalog lineage. It also specifies exactly which model outputs remain gated.

Retry Update requires a forced network revalidation path that preserves displayed data on failure. The existing useGzipJson reload defaults to foreground mode and may return the five-minute cache; it does not satisfy this contract unchanged. Refactor deliberately, test failure/cache paths, and do not call cached reuse a successful freshness check.
