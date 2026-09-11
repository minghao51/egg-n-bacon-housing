# WS4 — Ingestion Resilience: MRT Fallback + Wiki-Mall Remedy (Batch 1)

## Context

Two confirmed high-severity silent-degradation paths in bronze ingestion:

1. **MRT legacy fallback collapses interchanges** — `components/ingestion/geojson.py:373`: merge produces one row per (station×line), then `drop_duplicates(subset=["name"], keep="first")` keeps ONE arbitrary line per station. Interchange stations (NSL+EWL etc.) lose lines. Fallback is 2019-vintage and activates on ANY transient live-fetch failure (`geojson.py:316-328`).
2. **Wiki-mall deprecation remedy is a no-op** — `components/ingestion/datagov.py:489-497`: legacy `raw_wiki_shopping_mall*.parquet` wins forever; the runtime warning says `main.py --refresh raw_mp25_malls` switches sources, but `clear_bronze` (`utils/bronze.py:103-128`) fnmatches `raw_mp25_malls*` only — it CANNOT delete the wiki files. Documented recovery doesn't work.

Also: `utils/mrt_line_mapping.py:117-183` fallback station→lines map is NSL/EWL-only (~50 stations); when the JSON config is absent, CCL/DTL/TEL/LRT stations silently get tier 3, no interchange flag.

## Read first

- `.agents/skills/change-data-ingestion/SKILL.md` (mandatory, follow its checklist)

## Decisions locked

- D6a: minimal fix — correct the interchange aggregation + loud warnings. NOT deriving a full fallback from MRTStations.geojson (follow-up).
- D5b: fix the wiki-mall REMEDY (warning text + docs to a working command); keep honoring legacy files for now; branch removal is a later release.

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/components/ingestion/geojson.py`
- `src/egg_n_bacon_housing/components/ingestion/datagov.py`
- `src/egg_n_bacon_housing/utils/mrt_line_mapping.py`
- `src/egg_n_bacon_housing/utils/bronze.py` (only if the remedy fix requires it)
- `docs/guides/data-ingestion-development.md`
- `tests/test_geojson*.py`, `tests/test_ingestion*.py`, `tests/test_mrt*.py` (extend; create if absent)

## Forbidden

Everything else, incl. `adapters/*` (WS6 owns them), `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Interchange-safe legacy MRT fallback — `geojson.py` `_mrt_stations_from_legacy_files` (~:363-429)

Replace `drop_duplicates(subset=["name"], keep="first")` (:373) with per-station line aggregation: group merged (station×line) rows by station key and join lines as `";".join(sorted(lines))` — reuse the semantics/format of the live path's `_attach_station_lines` (:281-286) so downstream parsing is consistent.

### 2. Loud fallback warnings — `geojson.py`

- When the live LTA fetch fails and the 2019 legacy path activates: `logger.warning` including the fetch failure reason, legacy station count, and explicit note that data is 2019-vintage.
- Tripwire (cheap): after live fetch, if any station ends with empty/missing `line` (present in exits, absent from codes+`_STATION_LINE_SUPPLEMENT`), `logger.warning` with the count and a few example station names — that's the signal the supplement needs updating.

### 3. Two-line-fallback warning — `utils/mrt_line_mapping.py`

In `station_lines_mapping` (~:117-183 path): when the JSON is absent and `_build_fallback_station_lines` is used, `logger.warning` ONCE per process (guard with a module flag) stating the fallback covers only NSL/EWL (~N stations) while `mrt_lines()` knows 9 lines — tiers/interchange flags will be degraded.

### 4. Wiki-mall remedy — `datagov.py` + docs

- `datagov.py:493-497`: change the warning text so the recovery command actually works: `--refresh 'raw_wiki_shopping_mall*'` (verify against `utils/bronze.py clear_bronze` fnmatch semantics on relative `.parquet` paths — confirm the glob matches the actual legacy filenames listed at `datagov.py:489-490`). Keep the deprecation framing.
- Update `docs/guides/data-ingestion-development.md` (~line 77) to the working command.
- Only edit `utils/bronze.py` if the fnmatch genuinely cannot match the legacy names (e.g., subdirectory) — report first, prefer zero bronze.py changes.

## Tests required

- Legacy fallback: a station appearing under 2 lines produces ONE row with `";"`-joined sorted lines (e.g. `"NSL;EWL"`), matching the live-path format.
- Fallback activation logs a warning (caplog) mentioning 2019/legacy.
- Empty-`line` station tripwire warns with counts.
- `mrt_line_mapping` fallback warning fires once; JSON-present path silent.
- Wiki-mall: warning text contains a refresh pattern that `clear_bronze` would actually match (test the fnmatch against the legacy filename).

## Verification

```
dotenvx run -- uv run pytest tests/test_geojson.py tests/test_ingestion.py tests/test_mrt_line_mapping.py -x -q
uv run ruff check src/egg_n_bacon_housing/components/ingestion/geojson.py src/egg_n_bacon_housing/components/ingestion/datagov.py src/egg_n_bacon_housing/utils/mrt_line_mapping.py
uv run ruff format --check <same>
uv run mypy src/egg_n_bacon_housing/components/ingestion/geojson.py src/egg_n_bacon_housing/utils/mrt_line_mapping.py
```

(Adjust test filenames to what exists — `ls tests/` first.)

## Constraints

- NO commits. Owned files only. Re-verify line anchors first. No behavior changes beyond the listed items.

## Definition of done

Interchange stations keep all lines on fallback; every fallback path warns loudly; wiki-mall remedy verifiably works; tests/lint/mypy green.

## Report back

Edits (file:line), tests added, verification tail, confirmation the refresh glob matches legacy filenames.
