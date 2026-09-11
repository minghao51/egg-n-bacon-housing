# WS10 — Bronze Freshness Metadata + External-File Registry (Batch 2a)

## Context
Bronze parquets never expire (by design for static refs; wrong for rolling sources). Freshness relies entirely on manual `--refresh`. No fetch metadata exists anywhere.
Also `EXPECTED_EXTERNAL_FILES` (`utils/bronze.py:41-55`) is a hand-maintained tuple whose own comment admits it must be manually synced with `components/ingestion/geojson.py` and `macro.py` — nothing checks the sync.

Confirmed rolling-window sources that silently freeze at first run: `raw_condo_transactions` (URA 5y), `raw_hdb_resale_transactions` (API 2017+). All bronze nodes short-circuit on file existence (e.g. `geojson.py:391-393`, `datagov.py:170-175`, `ura_csv.py:201-203` post-Batch-1).

NOTE: Batch 1 (WS4) modified `geojson.py`, `datagov.py`, `utils/mrt_line_mapping.py`, and possibly `utils/bronze.py` — re-verify current state first.

## Read first
- `.agents/skills/change-data-ingestion/SKILL.md` (mandatory — bronze immutability + cache-not-replaced-by-partial rules)

## Decisions locked
- Freshness is OBSERVABILITY ONLY: warn-on-stale; never auto-invalidate (bronze stays cache-first; `--refresh` remains the only invalidation).
- Manifest is a single JSON per bronze dir, maintained by a helper in `utils/bronze.py` — not per-file sidecars, not in-frame columns (bronze stays raw).

## Owned files (EXCLUSIVE)
- `src/egg_n_bacon_housing/utils/bronze.py`
- `src/egg_n_bacon_housing/components/ingestion/geojson.py`
- `src/egg_n_bacon_housing/components/ingestion/datagov.py`
- `src/egg_n_bacon_housing/components/ingestion/macro.py`
- `src/egg_n_bacon_housing/components/ingestion/ura_csv.py`
- `tests/test_bronze.py`, `tests/test_ingestion.py` (extend)

## Forbidden
Everything else, incl. `pipeline.py`, `config.py`, `utils/cache.py`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Manifest helper — `utils/bronze.py`
- `record_bronze_fetch(bronze_dir: Path, name: str, source: str, rows: int) -> None` — upserts into `bronze_dir / "bronze_manifest.json"`: `{"<name>": {"fetched_at": "<iso8601-utc>", "source": "<id>", "rows": N}}`. Atomic write (tmp + `os.replace`). Tolerate missing/corrupt manifest (log warning, recreate).
- `warn_if_stale(bronze_dir: Path, name: str, max_age_days: int) -> None` — reads manifest; if `fetched_at` older than threshold (or entry missing while the parquet exists), `logger.warning` with name, age, source, and the refresh command (`main.py --refresh <name>`). Missing manifest entry for an existing parquet → single warning noting metadata predates the manifest.
- `STALE_WARN_DAYS: dict[str, int]` module constant — opt-in per dataset. Seed with `{"raw_condo_transactions": 35, "raw_hdb_resale_transactions": 35}`. Everything else: no warning (static refs).

### 2. Wire into ingestion nodes
- At every bronze FETCH-AND-WRITE point (not the cache-hit path) in `geojson.py`, `datagov.py`, `macro.py`, `ura_csv.py`: call `record_bronze_fetch(...)` with a short source id (e.g. `"lta_api"`, `"datagov_api"`, `"ura_api+manual_csv"`, `"r2_external"`). Cover: parameterized datagov nodes, geojson amenities (source `"r2_external"`), live MRT, macro sources, URA merge path.
- At the CACHE-HIT read path for the two rolling sources only: call `warn_if_stale(bronze_dir, name, STALE_WARN_DAYS[name])`.
- Keep bronze semantics 100% unchanged otherwise (cache-first, raw, immutable; empty frames still never cached).

### 3. External-file registry consistency check
- Make the sync verifiable: whichever is least invasive — (a) export the external filenames from `geojson.py`/`macro.py` module constants and derive/compare against `EXPECTED_EXTERNAL_FILES` in a test, or (b) a test asserting `EXPECTED_EXTERNAL_FILES` equals the set of `.geojson`/`.json`/`.csv` filenames those modules reference. Pick (a) if the loader loops over a list constant; else (b) with an explicit literal list in the test and a failure message explaining both sides to update.
- Place in `tests/test_bronze.py`.

## Tests required
- Manifest: record → file exists with entry; second record upserts (same name overwritten, others preserved); corrupt manifest tolerated.
- Stale: entry older than threshold warns (inject old `fetched_at`); fresh entry silent; missing entry + existing parquet warns once; non-mapped dataset never warns.
- Ingestion wiring: one representative node test asserting `record_bronze_fetch` called on fetch path and NOT on cache-hit; rolling-source cache-hit warns via manifest.
- Registry consistency test passes and fails loudly when a filename is added to one side only.

## Verification
```
uv run pytest tests/test_bronze.py tests/test_ingestion.py -x -q
uv run ruff check <owned src files>
uv run ruff format --check <owned src + test files>
uv run mypy <owned src files>
```

## Constraints
- NO commits. Owned files only. No changes to refresh/clear semantics, cache manager, or validation.

## Definition of done
Manifest recorded on every fetch; stale warnings for the two rolling sources; registry drift caught by CI-able test; tests/lint/mypy green.

## Report back
Edits (file:line), wiring points list (node → source id), verification tail.
