# WS12 — Ingestion Transform Hardening: Income Interpolation, GDP Guard, Coordinate Checks (Batch 3)

## Context
Three confirmed validity gaps in ingestion transforms:
1. **Income-bracket medians biased** — `components/ingestion/datagov.py` `_transform_income_by_planning_area` (~:230-260): hardcoded bracket midpoints; open top bracket `("12_000andOver", 15000)`; weighted median returns the bracket MIDPOINT with no interpolation; unknown bracket columns silently skipped (`if col in df.columns`). Result: `median_monthly_income` biased low exactly in affluent planning areas (top bracket understated) → `affordability_ratio` inflated → "Severely Unaffordable" over-classification downstream.
2. **GDP transform silent heuristic** — `components/ingestion/macro.py:66`: when the preferred series label is absent, melts whatever `raw.iloc[0]` holds, no warning. Related inconsistency: GDP/CPI fallbacks use `raw.columns[1]` but wage growth uses `raw.columns[-1]` (~:64, :209, :224, :108).
3. **Falsy-zero coordinate guards** — `components/ingestion/geojson.py:102` `if lat and lon:` and `:134` `if name and lat and lon:` — `0.0` treated as missing; name-less POIs dropped silently at `:134`.

DECISION LOCKED (validity-first): implement real grouped-median interpolation. `median_monthly_income` values WILL shift (that is the fix). Downstream affordability classifications may change for affluent PAs — intended.

## Read first
- `.agents/skills/change-data-ingestion/SKILL.md` (mandatory)

## Owned files (EXCLUSIVE)
- `src/egg_n_bacon_housing/components/ingestion/datagov.py`
- `src/egg_n_bacon_housing/components/ingestion/macro.py`
- `src/egg_n_bacon_housing/components/ingestion/geojson.py`
- `tests/test_ingestion.py`, `tests/test_datagov.py` (create if absent), `tests/test_macro.py` (create if absent), `tests/test_geojson.py`

## Forbidden
Everything else, incl. `ura_csv.py`, `utils/bronze.py` (manifest wiring is live — preserve call sites), `metrics.py`, `cleaning.py`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Interpolated grouped median — `datagov.py`
- Replace midpoint-per-bracket with linear interpolation WITHIN the median bracket (standard grouped-data median): sort brackets by lower bound; cumulative weights; when cumsum crosses 50%, interpolate `lower + (target - cum_before) / bracket_weight * bracket_width` (width = next lower bound − this lower bound for closed brackets).
- Top open bracket (`12_000andOver`): no upper bound exists — keep a documented assumption (lower + half of the PREVIOUS bracket's width is a defensible convention; state it in a comment + module docstring) and `logger.info` once per transform how many PAs landed in the open bracket (that's the bias tripwire).
- Unknown/missing bracket columns: `logger.warning` listing skipped bracket names instead of silent skip.
- Keep the bracket table where it is (module constant) but add a source-date comment.
- PRESERVE: bronze rawness (transform outputs are still bronze node outputs — this changes the transform, which is the node's job), manifest `record_bronze_fetch` call sites, `@parameterize` structure.

### 2. GDP/fallback guard — `macro.py`
- `_transform_gdp`: when the preferred series label is absent and a fallback series is used, `logger.warning` naming the preferred label, the series actually used, and the available labels.
- Unify the fallback-column rule across GDP/CPI/wage-growth to ONE documented choice (inspect all three; pick "first non-label column" or "last column" — whichever matches the dominant existing behavior — and apply everywhere with the same warning when fallback fires).

### 3. Coordinate guards — `geojson.py`
- `:102` → `if lat is not None and lon is not None and not (isinstance(lat, float) and math.isnan(lat)) ...` (or a small `_valid_coord` helper used both places; keep pd.isna semantics for str-converted values as currently parsed).
- `:134` → same coordinate fix; name-less POIs: keep dropping but `logger.warning` once per file-load with the count of POIs dropped for missing names.
- PRESERVE: manifest wiring, MRT fallback aggregation + warnings (Batch 1 WS4 work), `_STATION_LINE_SUPPLEMENT` tripwire.

## Tests required
- Interpolation: distribution with median mid-bracket → interpolated value (hand-computed expectation, not the old midpoint); median exactly on bracket boundary; single-bracket distribution; open-top-bracket PA → logged info + documented convention value; unknown bracket column → warning.
- GDP: preferred label present → unchanged, no warning; absent → warning naming both series.
- Coordinates: `0.0` coords now kept; NaN/None still dropped; name-less POI drop count warned.

## Verification
```
uv run pytest tests/test_ingestion.py tests/test_geojson.py tests/test_macro.py tests/test_datagov.py -x -q
uv run ruff check <owned src files> && uv run ruff format --check <owned src + tests>
uv run mypy <owned src files>
```

## Constraints
- NO commits. Owned files only. No changes to adapters, cache, or other ingestion modules.
- If downstream gold/metrics tests fail due to the intended income-value shift, REPORT which ones (do not edit) — fixtures using income midpoints may legitimately need updates in Batch 4.

## Definition of done
Interpolated medians with open-bracket tripwire; loud GDP fallback; correct coordinate validity checks; tests/lint/mypy green.

## Report back
Edits (file:line), the open-bracket convention chosen, downstream tests affected by the income shift (report-only), verification tail.
