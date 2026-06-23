# Troubleshooting Guide

Solutions for the supported pipeline and app workflows.

## Quick Fixes

| Issue                       | Quick Fix                                                  |
| --------------------------- | ---------------------------------------------------------- |
| `ModuleNotFoundError`       | Run from the repo root with `uv run`                       |
| Missing manual source files | Run `dotenvx run -- uv run python scripts/00_sync_data.py` |
| Pipeline stage failure      | Re-run the prerequisite stage with `main.py --stage ...`   |
| Docs validator failure      | Update the active docs path or remove stale references     |
| App test/build issue        | Reinstall in `app/` with `bun install`                     |

## Python Import Errors

Symptom:

```text
ModuleNotFoundError: No module named 'egg_n_bacon_housing'
```

Fix:

```bash
cd /path/to/egg-n-bacon-housing
dotenvx run -- uv run python main.py --stage all
```

## Missing Pipeline Outputs

If an expected dataset is not present, re-run the upstream stage:

```bash
dotenvx run -- uv run python main.py --stage ingest
dotenvx run -- uv run python main.py --stage clean
dotenvx run -- uv run python main.py --stage features
dotenvx run -- uv run python main.py --stage export
dotenvx run -- uv run python main.py --stage metrics
```

You can inspect the most common outputs with:

```python
from egg_n_bacon_housing.utils.data_loader import (
    load_market_summary,
    load_planning_area_metrics,
)

print(load_market_summary().shape)
print(load_planning_area_metrics().shape)
```

## OneMap Credential Problems

Check that `.env` contains the current credentials:

```bash
rg '^ONEMAP_' .env
```

If requests still fail, verify the account in the OneMap portal and re-run the failed stage.

## Manual Source Data Missing

The repo does not keep the full manual CSV and GeoJSON bundle in git.

Sync it with:

```bash
dotenvx run -- uv run python scripts/00_sync_data.py
```

## Docs Validator Failures

Run:

```bash
uv run python scripts/tools/validate_docs_layout.py
```

Typical causes:

- links to removed files from older pipeline workflows
- references to retired generated app-content copies
- app docs that still describe an outdated workflow

## App Build or E2E Failures

Run commands from `app/`:

```bash
cd app
bun install
bun run build
bun run test:e2e
```

Use Bun as the only supported package manager for `app/`.

If the preview-based suite fails, run:

```bash
cd app
bun run test:e2e:prod
```

## Large Dataset Memory Pressure

Read only the columns you need:

```python
import pandas as pd

df = pd.read_parquet(
    "data/04_platinum/unified_dataset.parquet",
    columns=["planning_area", "price_psf", "rental_yield_pct"],
)
```

## Jupyter Environment Drift

If notebooks cannot find project modules:

```bash
uv run jupyter notebook
uv run python -m ipykernel install --user --name=egg-n-bacon
```

## Stale or Broken data.gov.sg Resource IDs

data.gov.sg periodically restructures its datasets. If a pipeline stage fails with wrong data or 404 errors on an API fetch:

1. Check the resource ID via the v2 metadata API:

   ```bash
   curl -s "https://api-production.data.gov.sg/v2/public/api/datasets/{datasetId}/metadata" | python3 -m json.tool
   ```

2. If it returns `"No table found"` or the dataset name doesn't match, scan for the replacement:

   ```bash
   curl -s "https://api-production.data.gov.sg/v2/public/api/datasets?page=1" | python3 -m json.tool
   ```

3. Update the resource ID in the active ingestion modules under `src/egg_n_bacon_housing/components/ingestion/` and delete the stale bronze cache.

See the [data.gov.sg Resource ID Migration guide](guides/datagovsg-resource-migration.md) for the full investigation process and the June 2026 migration details.

## Macro Indicator API Returns Zero Records

If `raw_macro_data` logs "Fetched CPI: 0 records" (or unemployment/GDP), the API returned data but the melt/pivot transform produced nothing. Common causes:

### Wrong label column in melt functions

data.gov.sg pivot tables have an `_id` column (integers) followed by `DataSeries` (text labels like "All Items"). The melt helpers in `src/egg_n_bacon_housing/components/ingestion/macro.py` must use `DataSeries` as the id column, not `df.columns[0]`:

```python
# WRONG — _id is integers, never matches string filters
id_col = df.columns[0]

# RIGHT
label_col = "DataSeries" if "DataSeries" in df.columns else df.columns[1]
```

### Quarter period parse off-by-one

data.gov.sg uses `YYYY{Q}Q` format (e.g. `20261Q` = 2026 Q1). The year is the first 4 chars, not `p[:-1]` (which gives 5 chars):

```python
# WRONG — "20261Q"[:-1] = "20261"
year = int(p[:-1])

# RIGHT — "20261Q"[:-2] = "2026"
year = int(p[:-2])
qtr = int(p[-2])
```

### GDP filter mismatch

The GDP dataset (`d_a5ff719648a0e6d4b4c623ee383ab686`) contains **GDP levels** (e.g. "GDP In Chained (2015) Dollars"), not growth rates. The filter `"Growth Rate"` returns nothing. Use `"GDP In Chained (2015) Dollars"` instead.

### Stale empty parquet cache

If a previous failed fetch saved a 0-row parquet, subsequent runs load it from cache without re-fetching. Delete the stale cache:

```bash
rm data/pipeline/01_bronze/external/{cpi,gdp,unemployment}.parquet
```

## School Directory Missing Latitude/Longitude

The new school directory resource (`d_688b934f82c1059ed0a6993d2a829089`) does not include `latitude`/`longitude` columns. The pipeline geocodes schools via OneMap postal code lookup.

### OneMap 429 Rate Limiting

OneMap aggressively rate-limits (429 Too Many Requests). The `_geocode_schools()` function in `utils/school_features.py` uses sequential requests with a 0.3s delay. If you still hit 429s:

- Wait 60+ seconds and retry — the rate window resets.
- Check that `max_workers` hasn't been bumped back to concurrent mode.
- Pre-cache geocoded schools by running the standalone geocode script before the pipeline.

If the parquet already has `latitude`/`longitude` columns with valid values, the geocoding step is skipped entirely.

### `np.radians` TypeError on None Values

If `_geocode_schools` stores Python `None` instead of `NaN`, the `latitude` column becomes `object` dtype and `np.radians()` crashes. The fix is `pd.to_numeric(..., errors="coerce")` after geocoding to convert `None` → `NaN`.

## Kindergartens GeoJSON Is Actually CSV

The file `data/pipeline/01_bronze/external/Kindergartens.geojson` is misnamed — it contains **incidental charges data** (CSV format, no coordinates), not kindergarten locations. The `raw_kindergartens` node uses `PreSchoolsLocation.geojson` instead, which has 2,290 Point features covering preschools and kindergartens with lat/lon.

## Pipeline Stage Runs But `--stage all` Skips Nodes

`STAGE_VARS["all"]` defines which nodes are computed during a full pipeline run. If a node is in `STAGE_VARS["metrics"]` or `STAGE_VARS["export"]` but not in `STAGE_VARS["all"]`, it will only execute when you explicitly run that stage. Check `pipeline.py` and add any missing terminal output nodes to the `all` list.

## Related Docs

- [Quick Start](guides/quick-start.md)
- [Usage Guide](guides/usage-guide.md)
- [R2 Sync Guide](guides/r2-sync-guide.md)
- [data.gov.sg Resource Migration](guides/datagovsg-resource-migration.md)
