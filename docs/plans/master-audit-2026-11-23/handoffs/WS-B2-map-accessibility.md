# WS-B2 — Map accessibility and scope-preserving handoff (UI-2, UI-3)

**Severity:** MEDIUM 9 + MEDIUM 9. **Effort:** M. **Wave:** 2 (after WS-B1 lands).

## Problem

1. **Pointer-only selection.** `/research/map` (and the `/dashboard/map` wrapper) selects a planning area by clicking a Leaflet polygon. Polygons are not focusable, there is no alternative area control, the metric `<select>` has no associated label, and filter buttons expose no pressed state.
2. **Handoff drops scope.** "Open observed comparison" serialises only `area` and `metric`, discarding the selected period and property type, so the explorer silently compares a different scope.

Evidence: `app/src/components/dashboard/PriceMap.tsx:464-489` (only `mouseover`/`mouseout`/`click`), `:593-607` (unlabelled select), `:619-621` and `:657-659` (class-only selected state), `:741` ("click an area"), `:777` (href with only `area` and `metric`). Browser observation: `../evidence/browser-map.log` — 55 polygon paths, **0** focusable, `aria-label=null`, `labels=[]`, no `aria-pressed`; map URL `…?area=TAMPINES&metric=median_price&timeBasis=pre_covid&propertyType=condo` produced href `/explore?area=TAMPINES&metric=median_price`.

## Required change

### Accessibility (UI-2)

1. Add a labelled native control (e.g. `<select>` of planning areas present in the current data) that drives the same `selectedArea` state, placed in the existing filter bar. Keep map clicks working.
2. Associate the metric control with a real label (`<label for>` or `aria-label`). Do not rely on adjacent text.
3. Expose pressed state on the Period and Type buttons (`aria-pressed={active}`) and keep them as `<button type="button">`.
4. Provide a text alternative for inspection: the selected-area inspector values are already in the DOM; ensure they are reachable without the map (they are, once §1 exists) and that each value has a programmatic label/value pairing (`InspectorItem` already renders label+value — verify it is not visual-only).
5. Escape interpolated values in Leaflet tooltip HTML (`:388-459`) with a small `escapeHtml` helper, or build tooltips with DOM text nodes. Current inputs are static published assets, so this is hardening, not a live XSS fix — say so in the commit/PR note.

### Handoff (UI-3)

6. Create one shared serializer (e.g. `app/src/components/**/lib/handoff.ts`) that maps `{area, metric, timeBasis, propertyType}` onto the explorer's supported query parameters (`area`, `metric`, `property`, `period`). Reuse the explorer's existing URL contract — do not invent a second vocabulary.
7. When the map metric has no explorer equivalent, choose explicitly and disclose it in the link text or an adjacent note; never silently substitute.
8. Remove the duplicate ad-hoc URL construction in `PriceMap.tsx:777` and use the serializer. If `/explore` already has a state→URL function, import it instead of duplicating.

## Tests

- Unit: serializer round-trip for every (property, period, metric) combination; unsupported metric yields an explicit fallback marker.
- E2E (`app/tests/e2e/research/map.spec.ts`): keyboard-only — Tab to the area selector, choose an area, inspect a layer, confirm the inspector updates without pointer input.
- E2E: select CONDO + Pre-COVID, follow "Open observed comparison", assert the destination's controls and source section match the map's scope.
- Assert the accessible name of the metric control and `aria-pressed` state after selecting each filter.

## Verification

Frontend gate plus both E2E commands from `handoffs/README.md`. `astro check` must stay at 0 errors / 0 warnings and must not add hints in touched files.

## Owns

`app/src/components/dashboard/PriceMap.tsx`, the new serializer module, `app/tests/e2e/research/map.spec.ts`, `app/tests/unit/` additions. `ExplorerWorkspace.tsx` only if the serializer needs an exported helper — re-read it first (WS-B1 changed it).

## Do not touch

`app/src/utils/release-manifest.ts`, v2 loaders, workflows, Python.

## Done when

Area selection and inspection are completable with a keyboard only, control names/pressed states are exposed, the handoff preserves property and period for every supported combination, and both E2E suites pass.
