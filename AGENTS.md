# Agent Notes

## Behavior

- **Analyze first** — Understand code, imports, patterns before changes.
- **Minimal scope** — Only what's needed. No scope-creep refactors.
- **Check skills** — Before any task, check + follow matching skill.
- **Verify** — Lint + type-check after changes. Ask user for command.
- **No commits** — Never commit unless explicitly asked.

## Stack

- **Package mgr:** `uv`
- **Execution:** `uv run <cmd>` (never `python` directly)
- **Install:** `uv add <pkg>`
- **Sync:** `uv sync`

## Output

- Concise. Bulletpoints > paragraphs.
- File:line references.
- No preamble/postamble. Answer directly.

## File Ops

- Read before edit. Edit > Write for surgical changes. Edit existing > new files.

## Project Structure

Source code lives in `src/egg_n_bacon_housing/`:

- `config.py` — pydantic-settings configuration
- `pipeline.py` — Hamilton DAG driver
- `components/` — DAG nodes (01_ingestion → 06_analytics)
- `schemas/` — Pydantic models (raw, clean, feature)
- `adapters/` — External API clients (onemap, datagovsg, geocoding)
- `utils/` — Utilities (cache, data_helpers, metrics, etc.)
- `analytics/` — Standalone exploratory analysis scripts (not wired to DAG)

**Manual data**: ~100MB of CSV/GeoJSON source files in `data/manual/` are stored in **Cloudflare R2** (gitignored). Fetch with `dotenvx run -- uv run python scripts/00_sync_data.py`. See `docs/guides/r2-sync-guide.md`.

**Env vars**: Encrypted via `dotenvx` — run commands as `dotenvx run -- uv run <cmd>`.

**Pipeline vs Analytics**: The Hamilton DAG (`components/`) runs the core automated pipeline from bronze to platinum. Analytics modules are run on-demand as standalone scripts that consume exported datasets from the platinum layer. They are not part of the automated pipeline.

Data lives in `data/pipeline/` with medallion layers:

- `01_bronze/` — raw immutable data
- `02_silver/` — validated, cleaned data
- `03_gold/` — feature-enriched data
- `04_platinum/` — predictions, exports, metrics

## Analytics Doc Charting

Analytics tables in `docs/analytics/` render into `app/`, but charts are opt-in only.

Use this marker immediately before a markdown table when a chart should appear in the app:

```html
<div
  data-chart-metadata="true"
  data-chart="comparison"
  data-chart-title="Descriptive chart title"
  data-chart-columns="Column A,Column B"
></div>
```

Rules:

- Leave tables unmarked unless a chart clearly improves comprehension.
- `data-chart` may be `comparison`, `time-series`, or both separated by commas.
- Prefer `data-chart-columns` to limit charts to the few numeric series that matter.
- Do not opt in descriptive tables such as data dictionaries, methodology summaries, file inventories, or risk/mitigation matrices.
- Keep the marker directly adjacent to the target table so the renderer can bind it reliably.
