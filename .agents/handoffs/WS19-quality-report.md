# WS19 — Quality Report Tool (D2, Batch 5)

## Context

`data/quality_metrics.db` accumulates per-write snapshots (`run_snapshots`), Welford baselines (`historical_baselines`), and anomaly checks (`check_anomaly` — 3σ or >50% row change) — but nothing surfaces any of it. Quarantine files land in `_quarantine/` dirs with no summary. This WS adds a read-only reporting tool. No pipeline changes.

## Read first

- `utils/data_quality.py` (schema, `DataQualityCollector`, `check_anomaly`, `record_dataframe_quality`)
- `utils/layer_writer.py` (who writes what: layer dirs, `_quarantine/` naming, `track_quality` flag from WS16)

## Owned files (EXCLUSIVE)

- `scripts/tools/quality_report.py` (NEW)
- `tests/test_quality_report.py` (NEW)
- `docs/guides/ops-scheduling.md` — NO, that's WS18's. Instead: mention the report in a NEW section of `docs/guides/pipeline-development.md`? NOT owned either. → Keep docs to the script's `--help` + module docstring; report-only suggestion for docs.

## Forbidden

Everything else, incl. `utils/data_quality.py`, `utils/layer_writer.py`, all docs files, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. `scripts/tools/quality_report.py`

- Read-only CLI over `data/quality_metrics.db` + the pipeline layer dirs. Output: human-readable report to stdout; `--json` for machine use. Sections:
  1. **Snapshot trends**: per dataset — latest snapshot (rows, null%, dup count, when) vs baseline mean/σ; flag datasets where `check_anomaly` would fire.
  2. **Row-count deltas**: latest vs previous snapshot per dataset (catch collapse-to-zero; empty 0-row writes are visible post-WS5).
  3. **Quarantine summary**: walk `<layer>/_quarantine/` dirs — count files + total rows per entity (parse filenames `<entity>_<timestamp>`), newest first, top N.
  4. **Freshness**: read `01_bronze/bronze_manifest.json` — per entry age vs `utils.bronze.STALE_WARN_DAYS`, flag stale/missing.
- Flags: `--db PATH`, `--data PATH` (defaults from `Settings` resolution), `--dataset FILTER`, `--top N`.
- Exit code: 0 always unless DB unreadable (report tool, not a gate — document that a future CI gate could be added).
- Pure stdlib + pandas reads; no writes anywhere.

### 2. Tests — `tests/test_quality_report.py`

- Build a tmp sqlite DB via `DataQualityCollector`/`record_dataframe_quality` with a few datasets + snapshots; tmp layer dirs with quarantine parquets; tmp manifest.
- Assert: anomaly flag fires for an injected outlier; row-delta section correct; quarantine counts parsed correctly; freshness flags stale entry; `--json` is valid JSON with the same facts; no files written (read-only assertion on tmp tree mtimes optional — keep simple).

## Verification

```
uv run pytest tests/test_quality_report.py -x -q
uv run ruff check scripts/tools/quality_report.py && uv run ruff format --check scripts/tools/quality_report.py
uv run mypy scripts/tools/quality_report.py
```

## Constraints

- NO commits. Owned files only. Read-only with respect to everything except stdout.

## Definition of done

Report covers trends/anomalies/deltas/quarantine/freshness; JSON mode; hermetic tests green.

## Report back

Files, report sections, test delta, verification tail, docs-placement suggestion (report-only).
