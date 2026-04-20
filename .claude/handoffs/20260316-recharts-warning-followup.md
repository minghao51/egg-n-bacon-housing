# Recharts Warning Follow-up

## Goal

Do a focused pass to eliminate the remaining Recharts sizing warnings on analytics article pages without undoing the new opt-in charting system.

## Current State

The broad issue is fixed:
- Markdown tables are no longer auto-charted by loose heuristics.
- Charts now render only when a table is explicitly marked with metadata in `docs/analytics/*.md`.
- The source docs, sync flow, and app renderer all support the new opt-in pattern.

Build status:
- `bash scripts/sync-content.sh` passes
- `cd app && npm run build` passes

## What Changed

Key app files already updated:
- `app/src/components/charts/InlineChartRenderer.tsx`
  - Only renders charts for tables preceded by a metadata marker.
  - Uses `parseChartConfigFromElement()`.
- `app/src/utils/data-parser.ts`
  - Added `ChartConfig`.
  - Added `parseChartConfigFromElement()`.
  - Tightened numeric parsing to avoid junk series.
- `app/src/components/charts/ClientChart.tsx`
  - Waits for mount and non-zero width before rendering children.
- `app/src/components/charts/ComparisonChart.tsx`
  - Uses horizontal bar layout by default and better axis sizing.
- `app/src/components/charts/TimeSeriesChart.tsx`
  - Uses `ResponsiveContainer` with `minWidth`/`minHeight`.
- `app/src/pages/analytics/[slug].astro`
  - Hides the metadata `<div>` from display.

Docs/guidance updated:
- `docs/analytics/*.md` now include explicit chart markers for selected tables.
- `CLAUDE.md` documents the authoring pattern.
- `AGENTS.md` documents the authoring pattern.

## Remaining Problem

In local browser checks, charts render and the nonsense charts are gone, but the dev console still shows repeated warnings like:

`The width(-1) and height(-1) of chart should be greater than 0`

Observed on:
- `http://127.0.0.1:4321/analytics/lease-decay`

Manual checks were done with the local Astro dev server.

## Likely Root Cause

This now looks like a first-render measurement timing issue inside Recharts/ResponsiveContainer rather than bad table selection.

Even after:
- inserting the chart container before mounting,
- waiting for `requestAnimationFrame`,
- and gating render on non-zero container width,

Recharts still logs the warning at least once per chart in dev.

Possible causes to investigate:
- `ResponsiveContainer` measuring before final layout settles
- zero/invalid parent height chain during first paint
- React Strict Mode / dev-mode double render behavior
- chart mount order within dynamically created DOM nodes
- a `ResponsiveContainer` + `ClientChart` interaction pattern that still allows an initial invalid measurement

## Suggested Next Steps

1. Reproduce in dev and verify whether warnings also occur in preview/build mode.
2. Check whether using a fixed-size wrapper around `ResponsiveContainer` removes the warning.
3. Try replacing dynamic `createRoot()` mounts with a more idiomatic React/Astro render path if the issue is mount-order related.
4. Test whether delaying render until both width and height are known removes the warning.
5. Inspect whether the warning is dev-only noise and harmless, or also present in production preview.

## Useful Commands

Run sync:

```bash
bash scripts/sync-content.sh
```

Build app:

```bash
cd app
npm run build
```

Run dev server:

```bash
cd app
npm run dev -- --host 127.0.0.1
```

## Files Most Relevant For Follow-up

- `/Users/minghao/Desktop/personal/egg-n-bacon-housing/app/src/components/charts/InlineChartRenderer.tsx`
- `/Users/minghao/Desktop/personal/egg-n-bacon-housing/app/src/components/charts/ClientChart.tsx`
- `/Users/minghao/Desktop/personal/egg-n-bacon-housing/app/src/components/charts/TimeSeriesChart.tsx`
- `/Users/minghao/Desktop/personal/egg-n-bacon-housing/app/src/components/charts/ComparisonChart.tsx`
- `/Users/minghao/Desktop/personal/egg-n-bacon-housing/app/src/utils/data-parser.ts`

## Important Constraint

Do not revert back to heuristic auto-charting. The explicit metadata-driven chart opt-in is intentional and should stay.
