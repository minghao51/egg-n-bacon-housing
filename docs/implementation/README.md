# Implementation progress

Status of the redesign defined in [`assets/svg/implementation-plan.md`](../../assets/svg/implementation-plan.md). Read this first; the plan is the contract, this file is the ledger.

Branch: `main` — slices S0–S6 are merged (PR #2, merge commit `8ab248a`); S7–S10 are not started. Published data assets were regenerated through **2026-10** in that merge (`app/public/data/*.json.gz` plus `dashboard-release.json`, generation `0e1013ee485f`).

## Slice status

| Slice | Scope                                                                                                    | Status          | Report                           |
| ----- | -------------------------------------------------------------------------------------------------------- | --------------- | -------------------------------- |
| S0    | Baseline, reproductions, route/query inventory                                                           | done            | [s0-baseline.md](s0-baseline.md) |
| S1    | Evidence boundary: joint-section adapter, fetch lifecycle, map URL state, overlay keys, tool containment | done            | [s1-report.md](s1-report.md)     |
| S2    | Publication compatibility manifest (`dashboard-release.json`) + build verification                       | done            | [s2-report.md](s2-report.md)     |
| S3    | Fieldnotes tokens, skip link, `aria-current`, mobile drawer accessibility                                | done            | [s3-report.md](s3-report.md)     |
| S4    | Honest dashboard overview + `/research/trends` monthly destination                                       | done            | [s4-report.md](s4-report.md)     |
| S5    | `/explore`: joint selection, list, threshold, pagination, URL state                                      | done            | [s5-report.md](s5-report.md)     |
| S5c   | `/explore`: SVG choropleth map + table view                                                              | done            | [s5c-report.md](s5c-report.md)   |
| S6    | `/areas/[slug]` fieldnote with build-time generation gate                                                | done            | [s6-report.md](s6-report.md)     |
| S7    | Segment discovery/investigation/comparison migration                                                     | **not started** | —                                |
| S8    | Four-tool workspace with safe output states                                                              | **not started** | —                                |
| S9    | Research-map archive, studies, catalog detail                                                            | **not started** | —                                |
| S10   | Integration, regression, release readiness                                                               | **not started** | —                                |

## Shipped surfaces

- `/explore` — joint property × period comparison, 150-sale caution threshold, list/map/table, fieldnote links, release-gated national baseline.
- `/research/trends` — monthly medians and volumes with gap-preserving charts and a full table.
- `/areas/[slug]` — 41 static fieldnotes; national comparison rendered only when the build-time manifest verification passes.
- `/dashboard` — scoped 2025 medians from one asset, capability strip.
- Shell — Fieldnotes tokens, skip link, one `aria-current` per route, mobile drawer with focus trap and `inert`.

Legacy routes preserved: `/dashboard/{leaderboard,map,segments,trends}`, `/analytics/*`, `/catalog/*`. `/dashboard/trends` is still **Decision Tools**, not trends.

## Invariants future work must keep

1. **One generation or no comparison.** Cross-asset numbers require a verified `dashboard-release.json` (build-time for `/areas`, runtime for `/explore`). Never average area medians into a "national" figure.
2. **Joint sections only.** `map_metrics[era_property]`; never fall back to property-only (`hdb`) or period-only (`whole`) blocks.
3. **Missing ≠ zero.** `formatNumber`/`formatPercent` return `N/A`; exporter zeros are `empty`; charts break lines instead of filling.
4. **Absolute data claims.** Fixed 2025 where verified; literal era labels; export time is not source freshness.
5. **Base path.** All links/fetches use `import.meta.env.BASE_URL`; `Astro.url.pathname` includes it and must be normalised before matching nav state.
6. **No fabricated behaviour.** Gate unknown models (lease/MRT/spatial/forecast) behind explicit unavailable states rather than presenting them as current.

## Verification commands

```bash
# frontend
cd app && bun run test:unit                     # bun:test, hermetic
cd app && bun run astro check                   # baseline debt: 26 errors, 0 warnings, 41 hints
cd app && bun run validate-data                 # manifest contract + release warning
cd app && bun run build                         # regenerates catalog.jsonl.gz — restore it afterwards
cd app && LD_LIBRARY_PATH=/tmp/qna-browser-libs/root/usr/lib/x86_64-linux-gnu \
  PLAYWRIGHT_BASE_URL=http://127.0.0.1:4321 bunx playwright test

# exporter / data boundary
uv run pytest tests/test_export_app_data.py --no-cov -q
uv run ruff check scripts/export_app_data.py tests/test_export_app_data.py
uv run ruff format --check scripts/export_app_data.py tests/test_export_app_data.py
uv run python scripts/export_app_data.py --last-complete-month 2026-10 --output-dir /tmp/exp-check
```

## Published-month boundary

`--last-complete-month` is mandatory for a reproducible release: without it the
exporter's completed-bucket rules read the UTC clock, so the same parquet
publishes a different trailing month after a rollover. `2026-10` is the current
published boundary — `app/public/data/dashboard-release.json` records it under
`trailingMonth`. Raising it needs a pipeline refresh that actually contains the
complete month (`uv run python main.py --stage all`), not just a later export;
see [app/public/data/README.md](../../app/public/data/README.md).

## Known environment notes:

- `bun run build` rewrites `app/public/data/catalog.jsonl.gz` through `sync-catalog`; restore it (`git checkout -- app/public/data/catalog.jsonl.gz`) unless a data refresh is explicitly authorised.
- A cold Vite dev server can fail "no console errors" tests with `Failed to fetch dynamically imported module`; run against `bun run preview` after a fresh build, or restart the dev server.
- Playwright Chromium needs `LD_LIBRARY_PATH=/tmp/qna-browser-libs/root/usr/lib/x86_64-linux-gnu` in this environment.
- `bun run astro check` fails on pre-existing debt. Treat 26 errors / 0 warnings / 41 hints as the baseline; touched files must add none.

## Remaining slices — entry points

### S7 — segment migration

Files: `app/src/components/dashboard/segments/*`, `hooks/useFilterState.ts`, `hooks/useSegmentMatching.ts`, `segments/lib/buildSegmentAreaRows.ts`, new `/research/segments` route, `dashboard/segments` wrapper (coordinator-owned).

Must preserve: `persona`, `tab`, `segment`, `segments` (2–4 shortlist), `area` query IDs; stored research averages are archive values, not annual medians; add a weighted-fit explanation and a source/status note; do not silently change scoring.

### S8 — four-tool workspace

Files: `InteractiveToolsPanel.tsx`, `tools/{Affordance,LeaseDecay,MrtCbd,SpatialHotspot}*.tsx`, new `/research/tools` route, `dashboard/trends` wrapper (coordinator-owned).

Must deliver: explicit hypothetical inputs; standard amortization including the zero-interest branch; the reference price import named and source-bound; signed lease results with the endpoint policy surfaced; MRT unit/direction/cap caveats exposed rather than hidden behind a total-dollar estimate; spatial unavailable state (already contained by S1's boundary). Model regeneration is **not** authorised by UI work.

### S9 — research map, studies, catalog

Files: research-map workspace, analytics library/article shell, catalog routes. Keep nine layer IDs and query state; never relabel historical forecasts as current; keep chart-marker opt-in behaviour; preserve catalog IDs/slugs/schema links.

### S10 — integration

Full build, preview, E2E at root and Pages base, keyboard/dialog checks, mixed-generation simulation, payload/hydration measurements, final debt report.

## Decision register (still open)

See [`assets/svg/implementation-plan.md` §6](../../assets/svg/implementation-plan.md). The ones that block S7/S8:

- Segment scoring changes require an owner decision; the UI may explain, not redefine.
- Lease/MRT model repairs and any "recommendation" promotion require separate approval.
- Financial scenarios stay illustrative arithmetic; no CPF/MSR/TDSR or eligibility claims.

## How to continue in a fresh session

1. Read `AGENTS.md`, the two `.agents/skills/*` checklists (if touching ingestion/pipeline), this file, then the specific slice in `assets/svg/implementation-plan.md` plus its SVG.
2. Inspect `git log` and the working tree first: `git status`, `git diff --stat`, and the relevant files. Do not assume the slice status above matches the branch tip.
3. Keep slice ownership exclusive; the coordinator owns shared files (`Layout.astro`, nav, `package.json`, route wrappers, `types/*`, `constants/data-urls.ts`).
4. Verify with the commands above and record the exact counts; never report a fail-closed gate as "passed".
