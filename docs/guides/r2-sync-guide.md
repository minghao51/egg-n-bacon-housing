# R2 Manual Data Sync Guide

The pipeline needs ~100MB of manual source data (URA transactions, HDB resale prices, school directory, planning area geojson, etc.) that lives in `data/manual/`. To keep the git repo lean, these files are stored in **Cloudflare R2** and fetched on demand. The same script also backs up the **OneMap geocode cache** (flat `data/cache/` entries) under a separate `geocache/` prefix, and carries the narrow **`evidence/`** scope that provisions the pipeline artifacts the evidence producers re-measure in CI.

## Quick Start

```bash
# Fetch all manual data from R2 (~100MB)
uv run python scripts/00_sync_data.py

# Compare local vs R2 by size (fast, content NOT verified)
uv run python scripts/00_sync_data.py --verify

# Compare local vs R2 by content (downloads/compares bytes)
uv run python scripts/00_sync_data.py --verify-content
```

The script is **idempotent** — it skips files whose _size_ matches exactly, in both
directions. Safe to re-run. Size matching is a **pre-filter for speed, not a
content check**: see [Verification Modes](#verification-modes).

## Safety: Key Containment

Remote object keys are mapped onto local paths by a single containment resolver
before any transfer is submitted. A key is **rejected** (logged as
`REJECTED KEY:`, nothing written) unless it:

- starts with `<prefix>/` (so `manualx/...` cannot masquerade as `manual/...`);
- leaves a non-empty, relative remainder (`manual/`, `manual//etc/passwd` rejected);
- contains no empty, `.` or `..` path segment (`manual/../escape.txt` rejected);
- for the flat `geocache/` set, has no directory component
  (`geocache/hamilton/injected.json` rejected);
- resolves — following symlinks — to a path still under its sync root
  (an escaping symlink is rejected).

This applies to download _and_ verify. Rejected keys never reach
`download_file`.

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

### `evidence/` ↔ `data/pipeline/` (enumerated artifacts only)

`data/pipeline/**` is gitignored (0 tracked files), so a fresh checkout has no
pipeline layers. The read-only evidence producers (`scripts/tools/*_evidence.py`)
re-measure every ledger from them, which is why `.github/workflows/evidence.yml`
fails closed when they are absent. This scope provisions **exactly** the seven
files those producers open, enumerated in `EVIDENCE_FILES` in the script:

| Artifact                                   | Layer            |
| ------------------------------------------ | ---------------- |
| `04_platinum/unified_dataset.parquet`      | platinum (≈75MB) |
| `02_silver/geocoded_validated.parquet`     | silver (≈19MB)   |
| `01_bronze/raw_hdb_resale.parquet`         | bronze           |
| `01_bronze/raw_condo_transactions.parquet` | bronze           |
| `01_bronze/raw_hdb_rental.parquet`         | bronze           |
| `01_bronze/raw_school_directory.parquet`   | bronze           |
| `01_bronze/raw_mrt_stations.parquet`       | bronze           |

```bash
# Provision the CI evidence inputs (upload once from a machine with the layers)
uv run python scripts/00_sync_data.py --upload --only evidence

# Read-only check of what R2 holds vs local
uv run python scripts/00_sync_data.py --verify-content --only evidence

# In CI: restore them before the producers run
uv run python scripts/00_sync_data.py --only evidence
```

Three properties matter here:

- **Opt-in only.** `--only evidence` is never part of the default run, so a
  routine sync does not start moving ~110MB of parquet, and nothing enumerates
  `data/pipeline/` unless asked.
- **Enumerated, not a tree walk.** Whole-tree `data/pipeline/**` is ~4GB of
  regenerable bronze/silver plus per-run scratch; the producers only ever open
  the seven files above. Anything else found under `evidence/` in R2 is reported
  as `OUT OF SCOPE` and never transferred.
- **Same machinery as every other scope.** Keys go through the one containment
  resolver, uploads record the same `sha256` metadata, and `--verify-content`
  compares the same way.

**Why sync these layers instead of rebuilding them in CI?** Re-deriving them
needs what CI does not have: live URA/data.gov.sg/OneMap credentials, the ~100MB
`data/manual/` corpus (only partly covered by the `manual/` scope), and hours of
rate-limited OneMap geocoding for `geocoded_validated.parquet`. A narrow,
explicitly enumerated sync scope turns a multi-hour credentialed rebuild into one
paced download while keeping the blast radius of what leaves the bucket small.
These artifacts are **regenerable** — they are a CI input, not a backup; delete
the `evidence/` prefix and re-upload from a fresh pipeline run whenever the
layers are regenerated, so the producers never measure a stale copy.

Back up new entries after a pipeline run. Any ingestion that geocodes
addresses not seen before — a new month of transactions, or a change to the
geocode query itself — writes flat cache files that exist only on that machine
until they are pushed. The upload compares **exact sizes** and skips matches
(a 1-byte change is re-uploaded), so it transfers only what differs:

```bash
uv run python scripts/00_sync_data.py --upload --only geocache
```

Check the backup state without transferring anything:

```bash
uv run python scripts/00_sync_data.py --verify          # size-only, fast
uv run python scripts/00_sync_data.py --verify-content  # bytes, slower
```

The steady state in size mode is
`Summary: N SIZE-OK (CONTENT-UNVERIFIED), 0 missing locally, 0 missing in R2, 0 rejected key(s)`.
`SIZE-OK` means byte _sizes_ matched — it does **not** claim the bytes match;
run `--verify-content` for that. A non-zero "missing in R2" count is geocoding
work that a cache wipe would have to redo.

## Verification Modes

`--verify` is a **size-only** comparison. For every object present on both
sides it prints one of:

| Line                           | Meaning                                                                   |
| ------------------------------ | ------------------------------------------------------------------------- |
| `SIZE-OK (CONTENT-UNVERIFIED)` | Local and remote byte sizes are equal. Content was **not** compared.      |
| `SIZE MISMATCH`                | Sizes differ by **1 byte or more** — always reported, never skipped.      |
| `MISSING LOCALLY`              | The object exists in R2 but not on disk.                                  |
| `MISSING IN R2`                | The file exists on disk but not in R2.                                    |
| `REJECTED KEY`                 | The key failed the containment checks above; nothing was read or written. |

Because size equality is not content equality, the summary never prints
`0 size mismatches` as a clean bill of health; it prints
`N SIZE-OK (CONTENT-UNVERIFIED)` plus a reminder that content was not compared.

`--verify-content` (alias `--check-content`) compares **bytes** for the
selected scope:

- If the object has a `sha256` entry in its user metadata (recorded by `--upload`),
  the local file is hashed and compared to it — no download.
- Otherwise the object is downloaded to a temporary file and hashed.

It prints `CONTENT-OK` / `CONTENT MISMATCH` per object. This is slower (it
reads every object in scope), so prefer the size mode for routine checks.

**Provider limitation.** Content equality depends on either object metadata or
downloading the bytes. R2 (S3-compatible) supports user metadata, so `--upload`
records `sha256` there. If a provider drops that metadata, `--verify-content`
still works by downloading and hashing, but `--verify` alone can never assert
content equality — it only ever reports `SIZE-OK (CONTENT-UNVERIFIED)`.

## Sync Skips Are Size Pre-Filters

Both `--upload` and a plain (download) run skip a file only when its size
matches **exactly**. This is a speed pre-filter: equal size is _not_ proof of
equal bytes. Their summary lines say so explicitly —
`N skipped by exact size match (content not compared)`. To guarantee that two
sides hold identical bytes, diff the `--verify-content` scope or re-download.

## Live (real-network) Validation

Some fixes can only be proven against the real services: data.gov.sg pagination
completeness, the OneMap cold/warm geocode cache contract, and R2 content
verification. Those checks live in `tests/test_live_datagovsg.py`,
`tests/test_live_onemap.py` and `tests/test_live_r2_sync.py`, all marked `live`
and **skipped unless `EGG_LIVE=1`** — so `uv run pytest tests/ -q` stays hermetic
and never touches the network.

```bash
# Default live run (~2 min): real data.gov.sg fetches, OneMap cold/warm, read-only R2
EGG_LIVE=1 uv run pytest tests/ -m live -q --no-cov

# Add the full next-chain walk of every ingested dataset (the
# advertised-total vs rows-fetched table; ~6 min, dominated by HDB rental/resale)
EGG_LIVE=1 EGG_LIVE_DEEP=1 uv run pytest tests/test_live_datagovsg.py -m live -q --no-cov -s
```

Each file skips with a stated reason when its prerequisite is missing: OneMap
credentials (`ONEMAP_TOKEN` or `ONEMAP_EMAIL`/`ONEMAP_EMAIL_PASSWORD`) for the
geocode tests, `R2_*` credentials for the bucket tests. Requests are paced and
429-aware (`EGG_LIVE_PAUSE_SECONDS`, default 1.0s); data.gov.sg throttles a few
requests per minute, so a burst probe gets `429` rather than data.

What the live run actually establishes:

- **`fetch_datagovsg_dataset` returns whole datasets, not partial ones.** Small
  ingested datasets are fetched end-to-end through the real adapter and must
  equal the source's advertised `total`; the pagination arithmetic probe checks
  that every ingested dataset's `next` chain ends exactly at `total` (the deep
  mode walks the whole chain).
- **Cold and warm geocodes are equal.** The same real addresses are geocoded via
  the API, then read back from the cache — with deliberately invalid credentials,
  so a cache hit that silently fell through to the network would fail — and the
  two rows must be identical. A coordinate-only (legacy) entry must read as a
  miss and be dropped.
- **Content verification works on real objects.** `--verify-content`'s comparison
  is exercised against a real R2 object, read-only, including a negative case.

The full `evidence/` upload (~110MB) is an explicit owner action: it publishes
regenerable pipeline data to the bucket, so no automated run does it.

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
scripts/00_sync_data.py [-h] [--upload] [--download] [--verify]
                        [--verify-content | --check-content] [--dry-run]
                        [--only {manual,geocache,evidence}]
```

| Flag                                   | Action                                                                                                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| _(none)_                               | Download from R2 (default). Skips local files whose size matches exactly; summary notes content was not compared.                                       |
| `--upload`                             | Upload local files to R2, recording a per-object `sha256` metadata entry. Skips remote objects whose size matches exactly.                              |
| `--verify`                             | Size-only compare across both prefixes. Prints `SIZE-OK (CONTENT-UNVERIFIED)` / `SIZE MISMATCH` / `MISSING LOCALLY` / `MISSING IN R2` / `REJECTED KEY`. |
| `--verify-content` (`--check-content`) | Compare **content**: uses recorded `sha256` metadata when present, else downloads and hashes. Prints `CONTENT-OK` / `CONTENT MISMATCH`. Slower.         |
| `--only`                               | Restrict the operation to one sync set (`manual`, `geocache`, or the enumerated `evidence` set). Default: `manual` + `geocache`.                        |
| `--dry-run`                            | Show what would happen without transferring files. Combine with `--upload` or `--download`.                                                             |

### Unchanged by design

- `_TRANSFER_CONCURRENCY` (16) and the bounded `ThreadPoolExecutor` transfer pool.
- Retry-free transfer semantics: a failed transfer propagates and stops the run.
- Idempotent "skip what matches" behaviour — now an **exact** size match (previously a 100-byte tolerance, which silently stranded small corrections).

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

For jobs that re-measure finished layers instead of rebuilding them — the
evidence producers in `.github/workflows/evidence.yml` — restore the enumerated
pipeline artifacts as well. `--only` takes one scope per invocation:

```yaml
- name: Restore the inputs the producers read
  run: |
    uv run python scripts/00_sync_data.py --only manual
    uv run python scripts/00_sync_data.py --only evidence
```

That is the whole provisioning answer for `data/pipeline/**`: the layers are not
tracked in git and are not rebuilt in CI, they are fetched from the narrow
`evidence/` prefix. Wiring this into `evidence.yml` and turning on
`pull_request:`/`push:` triggers there is an owner decision — the workflow
currently runs on a schedule plus manual dispatch and fails closed when the
layers are missing.

## Troubleshooting

**"R2 credentials not configured"** — R2 env vars are missing from `.env`. See step 3 above.

**"No files found in R2"** — Bucket is empty. Run with `--upload` to push local files, or follow step 4.

**Size mismatch warnings** — Local file was modified, or its size differs from R2 by 1+ bytes. Delete the local file and re-run the script to re-download, or upload if the local copy is authoritative.

**`SIZE-OK (CONTENT-UNVERIFIED)` but the file is wrong** — expected: size mode never compares bytes. Run `--verify-content` (optionally with `--only`) to compare real content, then re-download the mismatched objects.

**`REJECTED KEY`** — the object key cannot be mapped safely inside its sync root (traversal, absolute remainder, a `geocache/` subdirectory, or a symlink escaping the root). Nothing was written. Inspect and remove the offending object from R2; it is never transferred.

**`OUT OF SCOPE` (evidence scope)** — the object exists under `evidence/` in R2 but is not one of the enumerated artifacts the evidence producers read. It is never transferred. Either delete it from R2 or add the path to `EVIDENCE_FILES` if a producer legitimately needs it.

**Small corrections never propagated (fixed)** — older versions skipped uploads/downloads within a 100-byte tolerance, so a 1–99 byte edit was never sent. The skip is now an exact size match, so any size change propagates.
