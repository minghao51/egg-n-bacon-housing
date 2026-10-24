# App data provenance

These compressed JSON files are precomputed dashboard assets. They are not
written by the Hamilton runtime; they are exported from platinum pipeline
outputs by a maintenance script. The manifest is the required-file and
schema-shape contract.

## Dashboard export workflow

Regenerate the seven dashboard files (`dashboard_overview`, `dashboard_trends`,
`dashboard_segments`, `dashboard_leaderboard`, `map_metrics`, `hotspots`,
`amenity_summary` — all `.json.gz`) after a successful pipeline run:

```bash
uv run python main.py --stage all          # materialize platinum parquets
uv run python scripts/export_app_data.py   # export dashboard JSON assets
cd app && bun run validate-data            # enforce the manifest contract
```

`scripts/export_app_data.py` reads `data/pipeline/04_platinum/unified_dataset.parquet`
and `data/pipeline/04_platinum/metrics/pa_monthly_metrics.parquet` (plus the
planning-area GeoJSON under `data/manual/geojsons/` for leaderboard
region/centroid metadata) and atomically rewrites exactly those seven files.
It never touches `segments_enhanced`, `interactive_tools/*`, `analytics/*`,
`planning_areas*`, or `catalog.jsonl.gz`. Growth (MoM/YoY/momentum), hotspot
classification, and rental-yield stats are derived with the same formulas the
retired web exporter used, so frontend semantics are unchanged; affordability
is the one deliberate exception — see [Affordability semantics](#affordability-semantics).
Published growth and the trends series run through the last **completed**
month: monthly buckets in the current calendar month are excluded until the
source publishes it in full, and year-bucketed leaderboard growth pairs
completed years only. Full-history aggregates (e.g. the overview stats
blocks) intentionally still include the partial month.

Area-level surfaces (leaderboard, map, segments, hotspots, amenity summary)
cover residential planning areas only: `NON_RESIDENTIAL_AREAS` (nature
reserves and industrial land) is excluded because the few transactions that
geocode into those polygons are artifacts, not a housing market. The
comparison list then ranks areas with at least `MIN_RANKING_VOLUME` (150)
trailing-12-month transactions first; thinner areas keep their row but sort
after every qualified area, so a 3-transaction area cannot top the board on
noisy growth or yield. Global aggregates keep every row (see
`scripts/export_app_data.py`). Regeneration is
atomic per file: all seven payloads are staged to `.tmp`
siblings and fully validated before the final `os.replace` swaps, which narrows
(but does not eliminate) the window in which a reader could see a mixed
generation.

## Affordability semantics

Published affordability values changed contract with this exporter. The retired
exporter hardcoded a median annual household income of 90,000 and banded
`affordability_class` with 3/5/7 ratio thresholds; the new exporter uses the
pipeline-configured `metrics.median_household_income` (85,000) and
`affordability_thresholds` (5/7/9) — the same settings that feed the DAG — as
the single source of truth. Published `affordability_ratio` and
`affordability_class` values therefore differ from the 2026-08 exports
independent of data freshness.

Remaining assets and their refresh methods:

- `interactive_tools/*` and `segments_enhanced.json.gz` are maintained
  research/analytics extracts. Refresh them with the corresponding research
  notebook or generator documented in `docs/analytics/`.
- `analytics/*` is maintained analytics content; its provenance and refresh
  method are documented alongside each report in `docs/analytics/`.
- `planning_areas*` and `catalog.jsonl.gz` are generated reference/catalog
  assets. Regenerate the catalog with `uv run python scripts/generate_catalog.py`.
