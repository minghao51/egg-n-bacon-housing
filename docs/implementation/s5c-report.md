# S5c implementation report — `/explore` map and table views

The explorer now has three views over one dataset: **list**, **map** (a tile-free SVG choropleth of the 55 published planning areas) and **table**. **No commit**; no published asset modified.

## 1. What shipped

- `app/src/utils/geo-projection.ts` (pure) — projects `planning_areas.geojson` into one SVG path per area with a `cos(mean latitude)` aspect correction, preserves polygon holes as even-odd subpaths, rejects (rather than repairs) a ring with an unreadable vertex, and bins observations into quantiles.
- `app/src/components/explorer/ExplorerMap.tsx` — lazy geometry load, choropleth with per-area `<title>` and fieldnote links, a legend with half-open range notation, and explicit masked groups. Bins are cut by **rank over the observations**, not over distinct values, so the "quantiles of the areas shown" claim is true.
- `app/src/components/explorer/ExplorerView.tsx` — list/map/table tablist with roving focus plus a real table view (caption, column scopes, `N/A` explanation, fieldnote links).
- `app/src/components/explorer/ExplorerWorkspace.tsx` — `view` state in the URL (`?view=`), exact-match validation, included in `replaceState`/`popstate`, never mutating `property`/`period`.

## 2. Verification

| Check                 | Result                                                                                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bun run test:unit`   | **201 pass** (32 geo-projection tests)                                                                                                                                                            |
| `bun run astro check` | **26 errors / 0 warnings / 41 hints / 154 files** — unchanged baseline, none in new files                                                                                                         |
| `bun run build`       | passes                                                                                                                                                                                            |
| Playwright            | **143 pass** (10 map/table tests)                                                                                                                                                                 |
| Browser, default map  | 55 paths, 25 coloured across 5 rank-quantile bins, 31 fieldnote links, 390px no overflow                                                                                                          |
| Browser, legend       | `S$499,000 to under S$568,000` … `S$761,500 to S$849,000`, five areas per bin; `Hidden by the current filters: 6`, `No value for this metric: 0`, `Outside this selection: 24` (55 = 25 + 6 + 24) |
| Browser, table        | 25 rows, `Ang Mo Kio`, `S$499,000`, `971`, links preserved                                                                                                                                        |
| Failure paths         | geometry HTTP 500 falls back to a message while the table stays usable; empty selection shows the empty state                                                                                     |

## 3. Review-driven corrections

- **Bin weighting:** quantile edges were computed over distinct values, producing 4/6/4/5/6 areas per bin while claiming quantiles; edges are now rank-based over the 25 observations (5 per bin), with ties deduplicated.
- **Masked-area language:** thin-sample and search-filtered areas were labelled "no value in this section" even though their values exist; they are now `filtered` with their own legend row and title, distinct from `no value for this metric` and `outside this selection`.
- **Boundary ambiguity:** legend ranges looked inclusive at both ends while values equal to the upper edge belong to the next bin; ranges now read "to under X", with the last bin "to X".
- **Malformed geometry:** rings with an unreadable vertex are rejected instead of being silently repaired into a different polygon.
- **View validation:** `?view=MAP` no longer coerces; unknown values fall back to the documented default like every other enumerated parameter.
- **Test hygiene:** the page-health checks ignore the expected 404 for an unpublished release manifest instead of failing on it.

## 4. Gaps

- The map is an SVG choropleth, not a basemap: there are no tiles, no roads or landmarks, so shape recognition depends on knowing Singapore's outline. This is deliberate — tiles require an API key and the design's fallback is geometry-only.
- 14 of the 55 published geometries appear in no joint section, so they have no fieldnote and are not links; 24 areas fall outside the current selection and are shown masked.
- `areaHref` carries only `from`, `property` and `period`; `metric`, `sort`, `search`, `page` are not round-tripped from a map click.
- The map's quantile bins are descriptive; there is still no statistical-classification claim, and the legend says so.
- 640 kB of path data is fetched and projected on first map open; it is lazy but not pre-split.

## 5. Next

**S7** (segment discovery/investigation/comparison migration) is the largest remaining surface that still runs on the old shell. Alternatively S8 (four-tool workspace with safe output states) if the tools are the bigger user-facing risk.
