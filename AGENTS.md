# Agent Notes

## Project Structure

Source code lives in `src/egg_n_bacon_housing/`:
- `config.py` — pydantic-settings configuration
- `pipeline.py` — Hamilton DAG driver
- `components/` — DAG nodes (01_ingestion → 06_analytics)
- `schemas/` — Pydantic models (raw, clean, feature)
- `adapters/` — External API clients (onemap, datagovsg, geocoding)
- `utils/` — Utilities (cache, data_helpers, metrics, etc.)
- `analytics/` — Standalone exploratory analysis scripts (not wired to DAG)

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
