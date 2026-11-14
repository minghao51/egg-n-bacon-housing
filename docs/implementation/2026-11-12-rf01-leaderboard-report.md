# RF01 report — scoped area rankings

- **Date:** 2026-11-12
- **Status:** Complete for code + verification; **not deployed**. Decisions D04/D05/D06 accepted in the [decision ledger](../plans/2026-11-12-reporting-refresh-decisions.md).
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §6
- **Baseline:** [RF00](2026-11-12-rf00-baseline.md) · **Audit:** [reporting refresh audit](2026-reporting-refresh-audit.md)

## 1. Defect fixed

`/dashboard/leaderboard` resolved prices, PSF and volume per property type **or** per period, never both, with a top-level all-population fallback. For Punggol HDB 2025 it rendered **S$500,000 / 24,854 sales** (property-only margin) or **S$742,444** (period-only 2025 median) instead of the joint section value **S$672,000 / 686 psf / 1,538 sales**.

Region controls mapped three published planning regions onto CCR/RCR/OCR (`useLeaderboardData.ts:10-23`), so "Core Central Region" filtered on a label the data does not contain.

## 2. What changed

| File                                                | Change                                                                                                                                                                                               |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/src/utils/leaderboard-observed.ts` (new)       | Pure adapter: joint `map_metrics` reads via `readAreaObservation`, planning-region resolution, 150-sale caution rule, metric availability, ranking order                                             |
| `app/src/hooks/useLeaderboardData.ts`               | Loads leaderboard + `map_metrics` from the same release pack; no margin fallbacks; reports unpublished/unranked counts and unsupported-metric reason                                                 |
| `app/src/types/leaderboard.ts`                      | `region: PlanningRegion \| null`, `rank: number \| null`, nullable metrics, `isThinSample`; margin-derived display fields removed                                                                    |
| `LeaderboardControls.tsx`                           | Five planning-region checkboxes; time labels `2022 onward` / `All history` / `2025 complete year`                                                                                                    |
| `LeaderboardDashboard.tsx`                          | Default metric `median_price`, default regions = all five; unavailable-metric panel keeps legacy metric URLs link-compatible without substitution; summary separates ranked / unranked / unpublished |
| `LeaderboardTable.tsx`                              | `—` rank for thin rows, "Thin sample" badge, nullable cells, scoped property mix, explanatory footnote                                                                                               |
| `LeaderboardMap.tsx`                                | Null-safe colour scale, tooltip and rank label                                                                                                                                                       |
| `MetricHelpModal.tsx`                               | Only the three jointly published metrics documented; explicit "not published for this selection" section; scope note                                                                                 |
| `app/tests/unit/leaderboard-observed.test.ts` (new) | 17 tests over the RF00 fixture                                                                                                                                                                       |
| `app/tests/e2e/dashboard/leaderboard.spec.ts`       | Punggol regression plus region/metric-availability tests                                                                                                                                             |

Behaviour now: price/PSF/volume come only from `map_metrics[era_property][area]`; unrecognised region labels resolve to `null` and render `Unmapped`; rows under 150 sales stay visible, sort after ranked rows and carry `data-ranked="false"`; `yoy_growth_pct`, `mom_change_pct`, `momentum`, both yield metrics and `affordability_ratio` report a reason instead of a number.

## 3. Why five metrics stay unavailable

`map_metrics` does publish `rental_yield_*` and `affordability_ratio` inside joint sections, but inspection shows the **same values repeated across property types**: Punggol 2025 reports yield 5.71 for HDB, EC and condo, and affordability 6.24 for all three. They are area-level margins carried into each section, so ranking on them per property type would repeat the audited defect. `yoy_growth`/`mom_change_pct`/`momentum` exist only in `by_time_period` or top level. All five are deferred to RF05/RS02 rather than presented as property-specific.

## 4. Verification

```bash
cd app && bun run test:unit                 # 351 pass (334 baseline + 17 new)
cd app && bun run astro check               # 0 errors, 0 warnings, 22 hints (baseline unchanged)
cd app && bunx playwright test tests/e2e/dashboard/leaderboard.spec.ts   # 10 passed
uv run python scripts/tools/verify_reporting_baseline.py --sources --assets  # pass
uv run python scripts/tools/validate_docs_layout.py && uv run ruff check && git diff --check
```

The regression test reads the rendered row for `?propertyType=hdb&timeBasis=year_2025&area=PUNGGOL` and asserts **$672,000**, **1,538**, `data-ranked="true"`, and the absence of `$500,000` / `24,854`.

`bun run build` was run for preview and its incidental `app/public/data/catalog.jsonl.gz` rewrite was restored with `git checkout --` (no catalog work was authorised).

## 5. Payload and behaviour notes

- Adds one existing-asset fetch for the island: `map_metrics.json.gz`, 11.3 KB gzip (same release pack, cached by `useGzipJson`). No new props, islands or dependencies.
- The map is still Leaflet/carto; only its value lookup changed.
- A row's property mix now uses the selected period's volumes per type, so the bar matches the rest of the row.

## 6. Left open (not RF01)

- Region filtering is not written to the URL; it resets with a bare link. RF05 owns URL lifecycle.
- Defaults are still `2022 onward`; the ratified trailing-12 default needs the RF04 v2 periods.
- `by_property_type`, `by_time_period` and the top-level entry fields remain in the published asset and the `LeaderboardEntry` type (marked unused by observed surfaces); removing them is an exporter change for RF04.
- Yield/affordability correct property-type scoping awaits RS02 and RF05.
