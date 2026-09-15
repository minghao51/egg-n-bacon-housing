# R2 Manual Data Sync Guide

The pipeline needs ~100MB of manual source data (URA transactions, HDB resale prices, school directory, planning area geojson, etc.) that lives in `data/manual/`. To keep the git repo lean, these files are stored in **Cloudflare R2** and fetched on demand. The same script also backs up the **OneMap geocode cache** (flat `data/cache/` entries) under a separate `geocache/` prefix.

## Quick Start

```bash
# Fetch all manual data from R2 (~100MB)
uv run python scripts/00_sync_data.py

# Verify local matches R2
uv run python scripts/00_sync_data.py --verify
```

The script is **idempotent** — it skips files that already exist with matching size, in both directions. Safe to re-run.

## What Gets Synced

Two sync sets, each mapped to its own R2 prefix.

### `manual/` ↔ `data/manual/`

52 files, ~123MB across these subdirectories:

| Directory                           | Contents                                                 | Approx Size |
| ----------------------------------- | -------------------------------------------------------- | ----------- |
| `data/manual/csv/ura/`              | URA residential transaction CSVs (14 files)              | 22MB        |
| `data/manual/csv/ResaleFlatPrices/` | HDB resale price CSVs (5 files, 1990–present)            | 78MB        |
| `data/manual/csv/datagov/`          | datagov.sg geojson (MRT, schools, hawker centres, parks) | 12MB        |
| `data/manual/geojsons/`             | OneMap planning area polygon, parks                      | 9MB         |
| `data/manual/crosswalks/`           | Town/district → planning area mapping CSVs               | <1MB        |
| `data/manual/csv/`                  | School tiers, scoring methodology                        | <1MB        |

`*.md` files in `data/manual/` are tracked in git directly (documentation, not data).

### `geocache/` ↔ `data/cache/` (flat entries only)

The flat `data/cache/*.parquet` / `*.json` files are OneMap geocode results
(`onemap_search:{address}` entries — ~14k entries, ~92MB). Cold re-geocoding
them costs ~4.7h of rate-limited OneMap API calls, and
`scripts/99_cleanup.py` (or any cache clear) wipes them, so they are backed
up to R2. The Hamilton node cache under `data/cache/hamilton/` (~4.3GB) is
**deliberately excluded** — it is keyed by code/config fingerprints,
invalidated by any code change, and fully regenerable.

Notes:

- Cache TTL is mtime-based (`GEOCODING__CACHE_DURATION_HOURS`, default 24h).
  Set a long TTL (`.env.example` suggests 8760 = 1 year) so restored entries
  survive reads; address→coordinate results are effectively immutable.
- Downloads reset file mtimes to "now", which conveniently refreshes the TTL
  window on restore.

Restore after a cache wipe (e.g. `scripts/99_cleanup.py`) or on a new
machine:

```bash
uv run python scripts/00_sync_data.py --only geocache
```

## Bronze Seeding

Static reference files the pipeline expects under `data/pipeline/01_bronze/external/`
(amenity GeoJSONs, `mrt_stations.json`, `mrt_lines.json`, `school_tiers.json`,
`sora_rates.parquet`) are **seeded automatically at pipeline startup** from
`data/manual/` and git-tracked `data/raw/` (`utils/bronze.seed_bronze_external`).
Files missing from every source directory are logged as errors at startup —
upload them to R2 (`data/manual/...`) and re-sync to distribute them.

## One-Time R2 Bucket Setup

If you're setting up a new R2 bucket or adding a new collaborator:

### 1. Create the bucket

In the Cloudflare dashboard:

- **R2 → Create bucket** → name: `egg-bacon-housing-data`
- (Optional) Enable **public read access** if you want direct downloads without credentials

### 2. Generate an API token

- **R2 → Manage R2 API Tokens → Create API token**
- Permissions: **Object Read & Write** (scoped to the bucket)
- Note: **Access Key ID**, **Secret Access Key**, and the **endpoint URL** (format: `https://<account_id>.r2.cloudflarestorage.com`)

### 3. Add to `.env`

```bash
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_key
R2_SECRET_ACCESS_KEY=your_secret
R2_BUCKET=egg-bacon-housing-data
R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
```

### 4. Upload the data (one-time)

Using the AWS CLI:

```bash
aws s3 sync data/manual/ s3://egg-bacon-housing-data/manual/ \
  --endpoint-url https://<account_id>.r2.cloudflarestorage.com
```

The script's `--dry-run --upload` flag shows what would be uploaded without doing it:

```bash
uv run python scripts/00_sync_data.py --dry-run --upload
```

## Script Reference

```bash
scripts/00_sync_data.py [-h] [--upload] [--download] [--verify] [--dry-run]
                        [--only {manual,geocache}]
```

| Flag        | Action                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------- |
| _(none)_    | Download from R2 (default). Skips files that already exist locally with matching size.      |
| `--upload`  | Upload local files to R2. Skips remote objects that already match by size.                  |
| `--verify`  | Compare local vs R2 across both prefixes. Reports OK / missing locally / missing in R2 / size mismatches. |
| `--only`    | Restrict the operation to one sync set (`manual` or `geocache`). Default: both.             |
| `--dry-run` | Show what would happen without transferring files. Combine with `--upload` or `--download`. |

## CI/CD

Add the sync step to your CI pipeline before running the pipeline:

```yaml
- name: Sync manual data
  run: uv run python scripts/00_sync_data.py --only manual

- name: Run pipeline
  run: uv run python main.py --stage all
```

(`--only manual` keeps CI lean — the geocache only helps warm local runs;
CI refetches anyway since Hamilton node fingerprints differ per code state.)

## Troubleshooting

**"R2 credentials not configured"** — R2 env vars are missing from `.env`. See step 3 above.

**"No files found in R2"** — Bucket is empty. Run with `--upload` to push local files, or follow step 4.

**Size mismatch warnings** — Local file was modified or is corrupted. Delete the local file and re-run the script to re-download.
