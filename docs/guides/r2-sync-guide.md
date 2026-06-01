# R2 Manual Data Sync Guide

The pipeline needs ~100MB of manual source data (URA transactions, HDB resale prices, school directory, planning area geojson, etc.) that lives in `data/manual/`. To keep the git repo lean, these files are stored in **Cloudflare R2** and fetched on demand.

## Quick Start

```bash
# Fetch all manual data from R2 (~100MB)
dotenvx run -- uv run python scripts/00_sync_data.py

# Verify local matches R2
dotenvx run -- uv run python scripts/00_sync_data.py --verify
```

The script is **idempotent** — it skips files that already exist with matching size. Safe to re-run.

## What Gets Synced

48 files, ~141MB across these subdirectories:

| Directory                           | Contents                                                 | Approx Size |
| ----------------------------------- | -------------------------------------------------------- | ----------- |
| `data/manual/csv/ura/`              | URA residential transaction CSVs (14 files)              | 22MB        |
| `data/manual/csv/ResaleFlatPrices/` | HDB resale price CSVs (5 files, 1990–present)            | 78MB        |
| `data/manual/csv/datagov/`          | datagov.sg geojson (MRT, schools, hawker centres, parks) | 12MB        |
| `data/manual/geojsons/`             | OneMap planning area polygon, parks                      | 9MB         |
| `data/manual/crosswalks/`           | Town/district → planning area mapping CSVs               | <1MB        |
| `data/manual/csv/`                  | School tiers, scoring methodology                        | <1MB        |

`*.md` files in `data/manual/` are tracked in git directly (documentation, not data).

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
dotenvx run -- uv run python scripts/00_sync_data.py --dry-run --upload
```

## Script Reference

```bash
scripts/00_sync_data.py [-h] [--upload] [--download] [--verify] [--dry-run]
```

| Flag        | Action                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------- |
| _(none)_    | Download from R2 (default). Skips files that already exist locally with matching size.      |
| `--upload`  | Upload local `data/manual/` to R2. Use after adding new data files.                         |
| `--verify`  | Compare local vs R2. Reports OK / missing locally / missing in R2 / size mismatches.        |
| `--dry-run` | Show what would happen without transferring files. Combine with `--upload` or `--download`. |

## CI/CD

Add the sync step to your CI pipeline before running the pipeline:

```yaml
- name: Sync manual data
  run: dotenvx run -- uv run python scripts/00_sync_data.py

- name: Run pipeline
  run: dotenvx run -- uv run python main.py --stage all
```

## Troubleshooting

**"R2 credentials not configured"** — R2 env vars are missing from `.env`. See step 3 above.

**"No files found in R2"** — Bucket is empty. Run with `--upload` to push local files, or follow step 4.

**Size mismatch warnings** — Local file was modified or is corrupted. Delete the local file and re-run the script to re-download.
