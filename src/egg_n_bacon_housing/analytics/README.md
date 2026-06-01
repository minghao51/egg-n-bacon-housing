# Analytics Scripts

Standalone analysis scripts that consume data from the medallion pipeline.
These are **not** wired to the Hamilton DAG — run them on-demand as standalone scripts.

> **See AGENTS.md** for the distinction between pipeline components (`components/`) and analytics modules.

## Structure

```
analytics/
├── analysis/          # Domain-specific analyses
│   ├── amenity/       # Amenity impact on prices
│   ├── appreciation/  # Price appreciation patterns
│   ├── causal/        # Causal inference (DiD, RDD)
│   ├── market/        # Lease decay, policy, segmentation
│   ├── mrt/           # MRT proximity effects
│   ├── policy/        # Policy impact findings
│   ├── school/        # School quality effects
│   └── spatial/       # Hotspots, autocorrelation, H3 clusters
├── models/            # Reusable model classes (ARIMAX, VAR)
├── pipelines/         # Orchestration scripts (forecasting, segmentation)
├── segmentation/      # Market segmentation modules
├── viz/               # Visualization utilities
├── run_backtesting.py
└── run_simple_backtest.py
```

## Running

```bash
# Example: run a pipeline script
uv run python -m egg_n_bacon_housing.analytics.pipelines.forecast_prices_pipeline

# Example: run an analysis script directly
uv run python src/egg_n_bacon_housing/analytics/analysis/spatial/analyze_spatial_hotspots.py
```

## Data Paths

Scripts read from:

- `data/pipeline/02_silver/` — cleaned data
- `data/pipeline/03_gold/` — feature-enriched data
- `data/pipeline/04_platinum/` — predictions, exports
- `data/analytics/` — intermediate analytics outputs
- `data/manual/` — reference data (URA, crosswalks)

Scripts write to `data/analytics/`, `data/forecasts/`, or `data/pipeline/04_platinum/`.

## Dependencies

Core: `pandas`, `numpy`, `scikit-learn`, `statsmodels`, `plotly`
Optional: `prophet`, `xgboost`, `shap`, `lifelines`, `h3`, `libpysal`, `esda`
