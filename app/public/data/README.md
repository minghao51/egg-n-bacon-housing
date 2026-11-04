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
uv run python scripts/export_app_data.py --last-complete-month 2026-10
cd app && bun run validate-data            # enforce the manifest contract
```

`--last-complete-month` is the published-month boundary and it must be given
for a reproducible release. Transaction dates in platinum are month-truncated,
so a partial trailing month is indistinguishable from a quiet one, and monthly
volume swings too far (0.56x–1.66x of the trailing median in 2025) for a
coverage heuristic to be safe. Declaring the month sets the completed-bucket
rules to evaluate as of the first day of the following month, which keeps the
trailing-month drop, the completed-year pair and the 150-transaction ranking
window consistent. Omit it and the boundary falls back to the UTC clock: the
same parquet then publishes a different trailing month before and after a
rollover, and the manifest records
`trailingMonth.resolvedFrom: "utc-clock"` so a clock-dependent release is
distinguishable from a declared one. A declared month later than the latest
month in the source is rejected rather than published as empty.

Alongside the seven payloads the exporter writes `dashboard-release.json`, a
publication-compatibility manifest: schema version, content-derived
generation id, UTC export time, observation range, literal period definitions,
national-vs-area inclusion rules, both input-parquet identities (repo-relative
path, SHA-256, bytes, rows, columns) and per-asset SHA-256/bytes/shape/metric
scopes. Each entry records both `sha256` (the published `.gz` file bytes, used
at build time) and `contentSha256` (the decompressed JSON text). Hosts that send
`Content-Encoding: gzip` for `.gz` assets hand the browser the decoded body, so
a browser verifies `contentSha256`; `validate-data` and the exporter verify both.
It is staged after the payloads and swapped in **last**, so a failure before
the first swap leaves the previous release intact. It also records
`trailingMonth` (`lastCompleteMonth` plus `resolvedFrom`), which is part of the
generation id: a clock-derived release cannot claim the identity of a declared
one. The seven payload swaps are
individually atomic but not one transaction, so an interruption inside that
short window can still publish new payloads beside an older manifest;
`validate-data` recomputes the hashes and the generation id, and reports that
mixed state instead of trusting the files. `validate-data` also rejects a
missing, extra, resized or re-hashed asset, a wrong schema version, and a
malformed manifest. The manifest describes one exporter generation
only: research (`segments_enhanced`, `interactive_tools/*`, `analytics/*`),
`planning_areas*` and `catalog.jsonl.gz` are not covered and keep their own
vintages. `generatedAt` is the export time, never source freshness.

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
month: monthly buckets after the declared `--last-complete-month` are excluded
until the source publishes them in full, and year-bucketed leaderboard growth
pairs completed years only. Full-history aggregates (e.g. the overview stats
blocks) intentionally still include the partial month. Exported payload bytes
are deterministic (gzip `mtime=0`), so re-exporting unchanged data only changes
`dashboard_overview`'s own `metadata.generated_at`.

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
