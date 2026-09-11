# WS18 — Local Scheduled Refresh (D1, Batch 5)

## Context
Bronze stale warnings exist (WS10 manifest + `STALE_WARN_DAYS`) but nothing ACTS on them. Rolling-window sources (`raw_condo_transactions` URA 5y, `raw_hdb_resale` HDB API) freeze unless manually refreshed. DECISION LOCKED (#6): LOCAL scheduling for now — no GitHub Actions, no CI secrets.

## Read first
- `.agents/skills/change-data-ingestion/SKILL.md` (mandatory)
- `utils/bronze.py` (`refresh_bronze`, `refresh_all`, `STALE_WARN_DAYS`, manifest helpers), `main.py` (CLI `--refresh` semantics)

## Owned files (EXCLUSIVE)
- `scripts/40_refresh_rolling.py` (NEW)
- `docs/guides/ops-scheduling.md` (NEW)
- `tests/test_refresh_rolling.py` (NEW)
- `README.md` (one-line link only, if an ops/scripts section exists; else skip)

## Forbidden
Everything else, incl. `utils/bronze.py`, `main.py`, `pipeline.py`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. `scripts/40_refresh_rolling.py`
- Purpose: one-command rolling-source refresh + optional pipeline rerun. Behavior:
  - Default: `refresh_bronze` for the rolling patterns (`raw_condo_transactions*`, `raw_hdb_resale*` — derive from `STALE_WARN_DAYS` keys so the list stays single-sourced), then optionally run the pipeline (`--run` flag → invoke `run_pipeline(stage="all")` via the supported entrypoint functions, mirroring `main.py`'s pattern; do NOT shell out).
  - `--dry-run`: print what would be refreshed (which bronze files exist matching patterns, manifest ages) without deleting.
  - `--stale-only`: consult the manifest and only refresh entries already past `STALE_WARN_DAYS` (idempotent scheduling target).
  - `--all`: full `refresh_all` (documented as nuclear).
- Exit code 0 on success; non-zero on pipeline failure. Logging via `utils.logging_config`.
- Must run under `dotenvx run -- uv run python scripts/40_refresh_rolling.py` (document in module docstring).

### 2. `docs/guides/ops-scheduling.md`
- Local scheduling recipes: cron (Linux/macOS) and launchd (macOS) examples calling the script weekly/monthly with `--stale-only --run`; log redirection; note that `dotenvx` env is required for API-backed refreshes (URA key optional; OneMap creds only if geocode cache misses).
- Include the STALE_WARN_DAYS table + how to add a source to it.

### 3. Tests — `tests/test_refresh_rolling.py`
- Dry-run lists matching files without deleting (tmp bronze tree + manifest).
- `--stale-only` refreshes only entries past threshold (inject old `fetched_at`).
- Default refresh clears matching parquets + Hamilton cache dir (mirror `refresh_bronze` semantics via tmp settings/data paths).
- Pattern derivation from `STALE_WARN_DAYS` (test fails if the constant and script drift).

## Verification
```
uv run pytest tests/test_refresh_rolling.py -x -q
uv run ruff check scripts/40_refresh_rolling.py && uv run ruff format --check scripts/40_refresh_rolling.py docs 2>/dev/null || true
uv run mypy scripts/40_refresh_rolling.py
uv run python scripts/tools/validate_docs_layout.py
```

## Constraints
- NO commits. Owned files only. No changes to refresh semantics in `utils/bronze.py`.

## Definition of done
Script + guide + tests; single-sourced patterns; hermetic tests.

## Report back
Files, CLI surface, test delta, verification tail.
