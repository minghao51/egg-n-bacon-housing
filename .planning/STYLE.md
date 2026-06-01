# egg-n-bacon-housing — Code Style & Conventions

## File Organization

### Where Things Go

```
src/egg_n_bacon_housing/
  __init__.py
  config.py               # pydantic-settings singleton (settings)
  pipeline.py              # Hamilton DAG driver (build_pipeline, run_pipeline, STAGE_VARS)
  components/              # Hamilton DAG nodes — medallion pipeline stages
    __init__.py
    01_ingestion.py        # Bronze: fetch raw data from APIs → parquet
    02_cleaning.py         # Silver: validate, rename, coerce columns
    03_features.py         # Gold: distance features, amenity counts, PSF, yields
    04_export.py           # Platinum: unified dataset, webapp JSON, segments
    05_metrics.py          # Platinum: aggregated metrics by planning area
    06_analytics.py        # Platinum: LLM-driven analytics summaries
  schemas/                 # Pydantic models — one file per medallion layer
    raw_models.py          # Bronze: all Optional, no validators
    clean_models.py        # Silver: required fields, Annotated constraints
    feature_models.py      # Gold: enriched features with amenities/yields
  adapters/                # External API clients
    __init__.py
    datagovsg.py           # data.gov.sg dataset fetcher (paginated)
    onemap.py              # OneMap geocoding + auth (tenacity retries)
    geocoding.py           # High-level geocoding orchestrator
    exceptions.py          # AdapterError hierarchy
  utils/                   # Shared utilities
    __init__.py
    cache.py               # CacheManager, cached_call(), cached_api_call()
    contracts.py           # require_columns() boundary validation
    data_helpers.py        # save_parquet(), data I/O helpers
    data_loader.py         # Pipeline data loading
    data_quality.py        # Data quality checks
    logging_config.py      # Logging setup
    metrics.py             # Metrics computation
    mrt_distance.py        # MRT distance calculations
    mrt_line_mapping.py    # MRT line code → name mapping
    school_features.py     # School feature engineering
    regional_mapping.py    # Regional/area mapping
    network_check.py       # Network connectivity check
    utils.py               # Misc helpers (add_project_to_path)
  analytics/               # Standalone exploratory scripts (NOT wired to DAG)
    analysis/              # Analysis by domain
      market/              #   HDB rental, lease decay, policy impact
      spatial/             #   H3 clusters, autocorrelation, hotspots
      mrt/                 #   MRT impact, heterogeneity
      amenity/             #   Feature importance
      causal/              #   RD, DiD causal analysis
      appreciation/        #   Appreciation patterns
      policy/              #   Policy findings
    models/                #   ARIMAX, VAR models
    pipelines/             #   End-to-end analytics pipelines
    price_appreciation_modeling/  #   Price model training & evaluation
    segmentation/          #   Market/period segmentation
    viz/                   #   Visualization generation
    school/                #   School-specific analytics
    run_backtesting.py     # Backtesting runner
    run_simple_backtest.py # Simplified backtesting
app/                       # Astro + React frontend
  src/
    components/
      charts/              # Chart components (ClientChart, TimeSeriesChart, etc.)
      dashboard/           # Dashboard pages & tools
        map/               #   Map with overlays
        leaderboard/       #   Leaderboard table & map
        segments/          #   Segments dashboard (discover, compare, investigate, details)
        tools/             #   Interactive tools (AffordabilityCalculator, LeaseDecayAnalyzer)
      MarkdownContent.tsx  # Markdown renderer
      DarkModeToggle.tsx
    hooks/                 # React hooks (useAnalyticsData, useGzipJson, useSegmentsData, etc.)
    types/                 # TypeScript interfaces (analytics.ts, segments.ts, leaderboard.ts)
    utils/                 # Utilities (cn, data-parser, gzip, colorScales)
    constants/             # Data URLs, nav config
    pages/                 # Astro pages (index, dashboard/*, analytics/*)
    layouts/               # Layout.astro
    data/                  # Static JSON data (persona-content, analytics-glossary)
  public/data/             # Static data served to frontend
data/
  pipeline/
    01_bronze/             # Raw immutable data (parquet)
    02_silver/             # Validated, cleaned
    03_gold/               # Feature-enriched
    04_platinum/           # Predictions, exports, metrics
tests/                     # pytest (flat structure, mirrors source module names)
docs/
  analytics/               # Analytics documentation with chart metadata markers
```

## Naming Conventions

### Python

| Element                   | Convention                             | Example                                             |
| ------------------------- | -------------------------------------- | --------------------------------------------------- |
| Package                   | `snake_case`                           | `egg_n_bacon_housing`                               |
| Module files              | `snake_case.py`                        | `data_helpers.py`, `mrt_distance.py`                |
| DAG node files            | `{NN}_{stage}.py`                      | `01_ingestion.py`, `04_export.py`                   |
| Schema files              | `{layer}_models.py`                    | `raw_models.py`, `feature_models.py`                |
| Analytics scripts         | `{verb}_{domain}.py`                   | `analyze_hdb_rental_market.py`, `train_models.py`   |
| Test files                | `test_{module}.py`                     | `test_ingestion.py`, `test_cache.py`                |
| Classes                   | `PascalCase`                           | `HCleanHDBTransaction`, `CacheManager`              |
| Pydantic models (raw)     | `Raw{Entity}`                          | `RawHDBTransaction`, `RawSchoolRecord`              |
| Pydantic models (clean)   | `HClean{Entity}`                       | `HCleanHDBTransaction`, `HCleanCondoTransaction`    |
| Pydantic models (feature) | `H{Domain}{Entity}`                    | `HFeatureTransaction`, `HAmenityFeatures`           |
| Exceptions                | `{Domain}Error`                        | `AdapterError`, `DatasetFetchError`                 |
| Config sub-models         | `{Domain}Config`                       | `PipelineConfig`, `GeocodingConfig`                 |
| Functions                 | `snake_case`                           | `raw_hdb_resale_transactions()`, `build_pipeline()` |
| Private helpers           | `_leading_underscore`                  | `_normalize_hdb_flat_type()`, `_fetch_from_api()`   |
| Constants                 | `UPPER_SNAKE_CASE`                     | `DATASET_IDS`, `STAGE_VARS`                         |
| Module-level logger       | `logger = logging.getLogger(__name__)` | Every module                                        |

### TypeScript / React

| Element         | Convention         | Example                                   |
| --------------- | ------------------ | ----------------------------------------- |
| Component files | `PascalCase.tsx`   | `ClientChart.tsx`, `LeaderboardTable.tsx` |
| Hook files      | `camelCase.ts`     | `useAnalyticsData.ts`, `useGzipJson.ts`   |
| Type files      | `camelCase.ts`     | `analytics.ts`, `segments.ts`             |
| Utility files   | `camelCase.ts`     | `cn.ts`, `data-parser.ts`                 |
| Constant files  | `kebab-case.ts`    | `data-urls.ts`, `dashboard-nav.ts`        |
| Astro pages     | `kebab-case.astro` | `segments.astro`, `leaderboard.astro`     |
| Interfaces      | `PascalCase`       | `SpatialAnalyticsData`, `MapMetrics`      |
| Type aliases    | `PascalCase`       | `LayerId`, `TradingSignal`, `MetricType`  |
| Hooks           | `use{Feature}`     | `useAnalyticsData()`, `useFilterState()`  |
| Functions       | `camelCase`        | `cn()`, `getAnalyticsUrl()`               |

## Python Patterns

### Hamilton DAG Nodes (`components/`)

Each stage file is a Hamilton module — top-level functions declare dependencies via parameter names:

```python
# components/02_cleaning.py — function param name = upstream DAG output
def cleaned_hdb_transactions(raw_hdb_resale_transactions: pd.DataFrame) -> pd.DataFrame:
```

Rules:

- Every function is a pure Hamilton node — output depends only on inputs + config
- Layer directory accessor: `def silver_dir() -> Path` returns `settings.silver_dir`
- Use `require_columns(df, {"col1", "col2"}, "dataset_name")` at entry to validate inputs
- Load from parquet cache in bronze/silver/gold before re-computing
- Save intermediate parquet to the layer directory after computation
- Raise `RuntimeError("Core dataset fetch failed: {name}")` if a core dataset is empty
- Private helpers prefixed with `_` for internal logic not exposed to DAG

### Pydantic Models (`schemas/`)

Three layers with escalating strictness:

- **Raw** (`raw_models.py`): All fields `Optional`, no validators — structure hints only
- **Clean** (`clean_models.py`): Required fields, `Annotated[float, Field(gt=0)]` constraints, `datetime` types
- **Feature** (`feature_models.py`): Enriched with computed fields, nested `BaseModel` groups

Naming prefix convention:

- `Raw` prefix for bronze models (`RawHDBTransaction`)
- `HClean` prefix for silver models (`HCleanHDBTransaction`) — `H` denotes "Housing" domain
- `H` prefix for gold models (`HFeatureTransaction`, `HAmenityFeatures`)

### Adapters (`adapters/`)

- One module per external API (`onemap.py`, `datagovsg.py`)
- Authentication setup returns typed dict (`dict[str, str]` for headers)
- Use `tenacity` `@retry` decorator with exponential backoff for API calls
- Raise typed exceptions from `adapters/exceptions.py` (`AdapterError` hierarchy)
- Credentials via `settings.onemap_email.get_secret_value()` — never hardcoded
- Cache via `cached_call(cache_id, fetch_fn)` from `utils/cache.py`

### Config (`config.py`)

- Singleton `settings = Settings()` at module level
- Nested `BaseSettings` sub-models: `PipelineConfig`, `GeocodingConfig`, `MetricsConfig`, etc.
- Secrets as `SecretStr` fields with `alias="ENV_VAR_NAME"` mapping
- Layer dirs as computed `@property` methods returning `Path`

### Analytics Scripts (`analytics/`)

- Standalone scripts, not part of the Hamilton DAG
- Use `add_project_to_path()` for path setup
- Self-contained: load data, compute, save outputs
- Run via `uv run python scripts/...` or as marimo notebooks
- Relaxed linting (ruff exclusions for `analytics/`): `E402`, `N806`, `N803`, `F401` ignored

### Utilities (`utils/`)

- `cache.py`: `CacheManager` class + `cached_call()` function. JSON for dicts, parquet for DataFrames, no pickle by default
- `contracts.py`: `require_columns()` for stage boundary validation
- Logging: always `logger = logging.getLogger(__name__)` at module top

## TypeScript / React Patterns

### Frontend Stack

- **Astro 5** pages with **React 19** islands
- **Tailwind CSS v3** with `tailwind-merge` (`cn()` utility) for class composition
- **Recharts** for charts, **Leaflet** for maps
- Path aliases: `@/*` → `src/*`, `@components/*`, `@hooks/*`, `@types/*`, `@utils/*`

### Component Patterns

- Default exports for React components: `export default function ComponentName()`
- `ClientChart` wrapper handles SSR hydration (renders children only after mount)
- Data hooks use `useGzipJson<T>()` for lazy gzip-compressed JSON loading
- Types defined as `interface` for objects, `type` for unions/literals

## Testing

### Python (pytest)

- **Runner**: `uv run pytest` from project root
- **File naming**: `test_{module}.py` in flat `tests/` directory
- **Class naming**: `Test{Feature}` (e.g., `TestBronzeLayer`)
- **Function naming**: `test_{behavior}` (e.g., `test_raw_hdb_resale_transactions_prefers_bronze_cache`)
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.api`
- **Fixtures**: Defined in `tests/conftest.py` — `mock_config`, `temp_data_dir`, `sample_dataframe`, `mock_onemap_response`, `mock_env_vars`
- **Mocking**: `monkeypatch` for env vars and module attributes; `MagicMock` for API responses
- **Coverage**: `--cov=egg_n_bacon_housing` with HTML + XML + terminal reports
- **Strict markers**: `--strict-markers` enabled

### Frontend (Playwright)

- **Runner**: `npm run test:e2e` from `app/`
- **E2E only**: No unit test framework configured
- **Variants**: `test:e2e:headed`, `test:e2e:ui`, `test:e2e:debug`, `test:e2e:prod`

## Linting & Formatting

### Python (ruff)

Config in `pyproject.toml [tool.ruff]`:

- **Line length**: 100
- **Target**: Python 3.12
- **Rules**: `E`, `F`, `W`, `I` (isort), `N` (pep8-naming), `UP` (pyupgrade)
- **E501 ignored** (line length handled by formatter)
- **Excluded**: `notebooks/`, `analytics/` directory
- **Per-file ignores**:
  - `components/*.py`: `N999` (numbered stage files)
  - `analytics/**/*.py`: `E402`, `N806`, `N803`, `F401`, `F821`, `F841`, `I001`
  - `notebooks/*.py`: `E402`, `E722`, `F821`, `F841`

### Python (mypy)

- **Version**: Python 3.12
- **Strict mode**: Not yet enabled (gradual adoption)
- **Plugins**: `pydantic.mypy`
- **`ignore_missing_imports`**: `true`
- **`config.py`**: `ignore_errors = true` (known SecretStr issue)

### Python (pre-commit)

Hooks in `.pre-commit-config.yaml`:

- `trailing-whitespace`, `end-of-file-fixer`, `check-yaml/toml/json`
- `ruff` (lint + fix), `ruff-format`
- `uv-lock` (lockfile consistency)
- `prettier` (frontend JS/TS/CSS/MD)
- `detect-secrets` (with `.secrets.baseline`)
- `mypy` (local hook via `uv run mypy`)
- `pip-audit` (manual stage)
- `dotenvx ext precommit` (manual stage)

### Frontend (Prettier)

- Via pre-commit hook, not standalone config
- Handles JS, JSX, TS, TSX, CSS, JSON, Markdown

## Build/Dev Commands

```
# Python pipeline
uv sync                            → Install all dependencies
uv run python -m egg_n_bacon_housing.pipeline  → Run the full Hamilton DAG pipeline
uv run pytest                      → Run all Python tests with coverage
uv run pytest -m unit              → Run only unit tests
uv run pytest -m "not slow"        → Skip slow tests
uv run ruff check .                → Lint Python code
uv run ruff format .               → Format Python code
uv run mypy                        → Type-check Python
pre-commit run --all-files         → Run all pre-commit hooks

# Frontend (from app/)
npm install                        → Install frontend dependencies
npm run dev                        → Astro dev server
npm run build                      → Production build
npm run preview                    → Preview production build
npm run test:e2e                   → Run Playwright E2E tests

# Analytics
uv run python scripts/{script}.py  → Run standalone analytics script
marimo edit notebooks/{name}.py    → Run interactive marimo notebook
```
