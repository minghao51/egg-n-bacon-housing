# Analytics Scripts

Standalone analysis scripts that consume pipeline outputs. These are not wired into the Hamilton DAG.

## Scope

- `analysis/` contains domain-specific analyses
- `pipelines/` contains standalone orchestration scripts
- `models/`, `segmentation/`, and `viz/` hold supporting logic

The flattened file names under `analysis/` are intentional. Do not assume the older nested `analysis/<domain>/...` layout is still present.

## Running

Examples:

```bash
uv run python src/egg_n_bacon_housing/analytics/analysis/market_analyze_lease_decay.py
uv run python src/egg_n_bacon_housing/analytics/analysis/spatial_analyze_spatial_hotspots.py
uv run python -m egg_n_bacon_housing.analytics.pipelines.forecast_prices_pipeline
```

## Boundaries

- Treat this tree as exploratory or report-generation code.
- The supported automated pipeline surface lives in `src/egg_n_bacon_housing/components/`.
- If you change paths here, update any active docs that mention concrete script paths.
