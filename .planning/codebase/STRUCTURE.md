# Structure

## Top-Level

```
egg-n-bacon-housing/
├── main.py                  # CLI entry: --stage {stage}, --visualize
├── config.yaml              # Pipeline config overrides
├── pyproject.toml           # Python deps, ruff, pytest, coverage, mypy
├── .env.example             # Env var template
├── .pre-commit-config.yaml  # Ruff + mypy + detect-secrets
├── src/egg_n_bacon_housing/ # Main Python package
├── app/                     # Astro webapp
├── tests/                   # Pytest suite
├── scripts/                 # Tools (CI coverage check, docs validator)
├── notebooks/               # Jupyter/marimo notebooks
├── data/                    # Pipeline data (gitignored)
│   ├── 01_bronze/           # Raw immutable data
│   ├── 02_silver/           # Validated cleaned data
│   ├── 03_gold/             # Feature-enriched data
│   ├── 04_platinum/         # Exports, dashboard JSON, metrics
│   └── cache/               # Hamilton cache
└── docs/                    # Documentation
```

## Python Package (`src/egg_n_bacon_housing/`)

```
src/egg_n_bacon_housing/
├── __init__.py
├── config.py                # pydantic-settings (PipelineConfig, LayerDirs, etc.)
├── pipeline.py              # Hamilton DAG driver, STAGE_VARS
│
├── components/              # Hamilton DAG nodes
│   ├── 01_ingestion.py      # Bronze: raw data fetch from APIs
│   ├── 02_cleaning.py       # Silver: validation and cleaning
│   ├── 03_features.py       # Gold: feature engineering
│   ├── 04_export.py         # Platinum: exports + webapp data
│   ├── 05_metrics.py        # Planning area metrics, hotspots
│   └── 06_analytics.py      # Analytics integration
│
├── schemas/                 # Pydantic models for medallion layers
│   ├── raw_models.py        # Bronze schema
│   ├── clean_models.py      # Silver schema
│   └── feature_models.py    # Gold schema
│
├── adapters/                # External API clients
│   ├── onemap.py            # OneMap geospatial API
│   ├── datagovsg.py         # data.gov.sg API
│   └── geocoding.py         # Geocoding adapter
│
├── utils/                   # Shared utilities
│   ├── cache.py             # LRU/file caching
│   ├── data_helpers.py      # Data helpers
│   ├── data_loader.py       # Parquet I/O
│   ├── data_quality.py      # Quality checks, SQLite tracking
│   ├── logging_config.py    # Structured logging
│   ├── metrics.py           # Metric calculations
│   ├── mrt_distance.py      # MRT distance calculations
│   ├── mrt_line_mapping.py  # MRT line mappings
│   ├── network_check.py     # Network connectivity
│   ├── regional_mapping.py  # SG regional/planning area maps
│   └── school_features.py   # School proximity features
│
└── analytics/               # Standalone analysis (NOT wired to DAG)
    ├── analysis/            # Analysis scripts by domain
    │   ├── amenity/
    │   ├── appreciation/
    │   ├── causal/
    │   ├── market/
    │   ├── mrt/
    │   ├── policy/
    │   ├── school/
    │   └── spatial/
    ├── models/              # ML models (ARIMAX, VAR)
    ├── pipelines/           # Analytics Hamilton pipelines
    ├── price_appreciation_modeling/
    ├── segmentation/
    ├── viz/
    └── school/
```

## Test Structure

```
tests/
├── conftest.py             # Shared fixtures
├── test_cache.py
├── test_cleaning_validation.py
├── test_config.py
├── test_data_loader.py
├── test_datagovsg.py
├── test_export.py
├── test_features.py
├── test_ingestion.py
├── test_metrics.py
├── test_onemap.py
└── test_pipeline.py
```

## Key Locations

| Purpose            | Location                              |
| ------------------ | ------------------------------------- |
| CLI entry          | `main.py`                             |
| Config             | `src/egg_n_bacon_housing/config.py`   |
| Pipeline driver    | `src/egg_n_bacon_housing/pipeline.py` |
| Stage definitions  | `pipeline.py:STAGE_VARS`              |
| Pipeline stages    | `src/egg_n_bacon_housing/components/` |
| API adapters       | `src/egg_n_bacon_housing/adapters/`   |
| Pydantic models    | `src/egg_n_bacon_housing/schemas/`    |
| Tests              | `tests/`                              |
| App entry          | `app/src/pages/index.astro`           |
| Dashboard routes   | `app/src/pages/dashboard/`            |
| Analytics routes   | `app/src/pages/analytics/`            |
| Content collection | `app/src/content/analytics/`          |

## Naming Conventions

| Type                   | Convention            | Example              |
| ---------------------- | --------------------- | -------------------- |
| Python modules         | snake_case            | `data_helpers.py`    |
| Pipeline stage modules | NN_name.py            | `01_ingestion.py`    |
| Python classes         | PascalCase            | `PipelineConfig`     |
| Python functions/vars  | snake_case            | `load_data()`        |
| Astro pages            | kebab-case            | `price-trends.astro` |
| React components       | PascalCase            | `PriceMap.tsx`       |
| Hooks                  | camelCase, use prefix | `useSegmentsData.ts` |
| CSS classes            | kebab-case            | `bg-background`      |
