# S5 implementation report — observed explorer

The first slice where the published numbers are shown under one verified generation. New route `/explore`; no existing route, label or asset changed (one nav item was added). **No commit**, no data regenerated.

## 1. What shipped

**Data layer (pure, tested):**

- `app/src/utils/release-manifest.ts` — parses the S2 manifest, recomputes the content-derived generation with a canonical JSON encoder that matches the Python exporter (proven against a real generated manifest: same `b2afd46d…` digest), verifies `sha256`/`contentSha256`/bytes per asset, and returns `verified | mismatch | unverified | absent` without ever throwing.
- `app/src/utils/explorer-selection.ts` — validated property/period/metric/sort/threshold/search/page state with default-omitting serialization and page reset on filter change.
- `app/src/utils/observed-rows.ts` — builds rows from the joint `map_metrics[period_property]` section only, no fallback to property-only or period-only blocks; nulls sort last; thin-sample counting is independent of search; the national baseline is attached only when the caller passes `baselineCompatible`.

**UI:**

- `/explore` (`app/src/pages/explore.astro` + `components/explorer/*`) — settings rail (property, period, 150-sale caution threshold with an explicit "show thin samples"), sort/search, 12-row paged list (4-row scroll viewport on mobile), N/A cells with a screen-reader explanation, thin-sample notice, error/retry, empty state, and an evidence footer naming `map_metrics.<section>` and `dashboard_overview.stats.<section>`.
- The release check runs **before** any data fetch, and the data cache keys include the verified generation, so a cached copy cannot outlive its manifest.
- Baseline copy is status-specific: `mismatch` says the assets do not share one generation; `absent`/`unverified` says the generation could not be verified; neither claims incompatibility without evidence.

## 2. Compatibility fix found while building this

Browsers cannot hash a `.gz` file when the host serves it with `Content-Encoding: gzip` (GitHub Pages does), because the body arrives already decoded. The first end-to-end run therefore withheld the baseline even with a valid manifest. `dashboard-release.json` now also records `contentSha256` (hash of the decompressed JSON text); the browser verifies that value, while `validate-data` and the exporter verify both hashes. Python and browser canonical forms still agree.

## 3. Verification

| Check                                         | Result                                                                                                                                                                              |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bun run test:unit`                           | **125 pass** (51 new: manifest, selection, rows)                                                                                                                                    |
| `uv run pytest tests/test_export_app_data.py` | **29 pass**                                                                                                                                                                         |
| `bun run astro check`                         | **36 errors / 0 warnings / 43 hints / 136 files** — unchanged baseline, none in new files                                                                                           |
| `bun run build`                               | passes                                                                                                                                                                              |
| Playwright full suite                         | **112 pass** (7 explorer + 2 baseline-gate tests added)                                                                                                                             |
| Browser, default view                         | 25 of 31 areas, Ang Mo Kio S$499,000 / 971 sales, page 1 of 3, section `map_metrics.year_2025_hdb`                                                                                  |
| Browser, baseline gate                        | with a synthesised matching manifest: `National HDB median transaction price: S$628,000` from `dashboard_overview.stats.year_2025_hdb`; with one tampered hash: withheld, no number |
| Browser, deep link                            | non-default `?property=condo&period=whole&metric=median_psf&sort=median_psf&direction=desc&minSales=all` preserved, 40 of 40 areas, section `whole_condo`                           |
| Browser, accessibility                        | one `aria-current`, labelled controls, no horizontal overflow at 390px                                                                                                              |
| Repository state                              | no published asset modified; `catalog.jsonl.gz` regenerated by the build was restored                                                                                               |

## 4. Gaps deliberately left open

- **Chart + list view** (design 02 bars/national marker), **table view** and the **map** are not implemented; the list is the only representation. No copy claims they exist.
- **Mobile paging** shows 4 rows in a scrollable region rather than true 4-row pages, and the page says so. Real paging needs a viewport-aware page size and anchor preservation.
- **Area detail navigation** (per-row links to `/areas/[slug]`) is absent; `?area=` round-trips but has no consumer until S6.
- The 150-sale threshold is a caution rule for this view, not a significance test; this is stated in the UI.
- Verified status covers only the two assets this screen compares (manifest + the two hashes); the footer says so.

## 5. Next

**S6** should add `/areas/[slug]` using the same adapter plus the difference-to-national calculation (withheld when the generation is unverified), and turn explorer rows into links. **S4** should rebuild the overview around one verified asset. The map (S5 remainder) can follow once S6 establishes the area route.
