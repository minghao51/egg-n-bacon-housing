# OVERVIEW

> Last updated: 2026-05-31

## Project Identity

Singapore housing data pipeline that ingests HDB/condo transaction data from government APIs, enriches it with geospatial amenity features, and serves analytics through an Astro web app. Built on a Medallion architecture orchestrated by a Hamilton DAG.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        External APIs                                │
│  data.gov.sg (CKAN)  │  OneMap (geocoding/auth)  │  Google Gemini  │
└────────┬─────────────┴────────────┬───────────────┴────────┬───────┘
         │                          │                         │
┌────────▼──────────────────────────▼─────────────────────────▼───────┐
│                     Adapters (src/.../adapters/)                     │
│         datagovsg.py  │  onemap.py  │  geocoding.py                  │
└────────┬──────────────┴─────────────┴──────────────────────────────┘
         │
┌────────▼─────────────────────────────────────────────────────────────┐
│                  Hamilton DAG Pipeline (6 stages)                    │
│  src/egg_n_bacon_housing/components/                                 │
│                                                                      │
│  01_ingestion ──▶ 02_cleaning ──▶ 03_features ──▶ 04_export         │
│   (bronze)         (silver)        (gold)          (platinum)        │
│                                          │                           │
│                               05_metrics ─┘                          │
│                               06_analytics                           │
└────────┬─────────────────────────────────────────────────────────────┘
         │  parquet (layers)  +  JSON (app/public/data/)
┌────────▼─────────────────────────────────────────────────────────────┐
│                    Astro Frontend (app/)                             │
│   React islands  │  Recharts  │  Leaflet maps  │  Markdown analytics│
│   (dashboard, segments, trends, map, leaderboard, analytics docs)   │
└──────────────────────────────────────────────────────────────────────┘
```

## Key Components

### Pipeline (Hamilton DAG)

Entry point: `src/egg_n_bacon_housing/pipeline.py:65` (`build_pipeline`) and `pipeline.py:87` (`run_pipeline`)

| Stage        | File                         | Layer            | Pattern                                                      |
| ------------ | ---------------------------- | ---------------- | ------------------------------------------------------------ |
| 01 Ingestion | `components/01_ingestion.py` | Bronze           | Fetch from APIs → parquet cache                              |
| 02 Cleaning  | `components/02_cleaning.py`  | Silver           | Clean + Pydantic schema validation                           |
| 03 Features  | `components/03_features.py`  | Gold             | Amenity distances (MRT, schools, malls), rental yield, PSF   |
| 04 Export    | `components/04_export.py`    | Platinum         | Unified dataset + JSON for webapp                            |
| 05 Metrics   | `components/05_metrics.py`   | Platinum/metrics | Price metrics, rental yield, affordability, hotspots by area |
| 06 Analytics | `components/06_analytics.py` | Analytics        | Lightweight market/spatial/appreciation analysis             |

### Analytics (standalone scripts)

Location: `src/egg_n_bacon_housing/analytics/`

Not wired to the Hamilton DAG. On-demand scripts that consume platinum layer exports. Sub-modules include: `spatial/`, `market/`, `segmentation/`, `mrt/`, `school/`, `amenity/`, `price_modeling/`, `price_appreciation_modeling/`, `causal/`, `policy/`, `viz/`, `models/`, `pipelines/`, `special/`.

### Frontend (Astro app)

Location: `app/`

| Page           | File                                        | Description                         |
| -------------- | ------------------------------------------- | ----------------------------------- |
| Home           | `app/src/pages/index.astro`                 | Landing page                        |
| Dashboard      | `app/src/pages/dashboard/index.astro`       | Summary dashboard                   |
| Segments       | `app/src/pages/dashboard/segments.astro`    | Market segments                     |
| Trends         | `app/src/pages/dashboard/trends.astro`      | Price trends                        |
| Map            | `app/src/pages/dashboard/map.astro`         | Leaflet map view                    |
| Leaderboard    | `app/src/pages/dashboard/leaderboard.astro` | Area rankings                       |
| Analytics docs | `app/src/pages/analytics/[slug].astro`      | Markdown-rendered analytics reports |

## Key Data Flows

1. `data.gov.sg API → 01_ingestion → bronze/*.parquet` — Raw transaction fetch with pagination and rate-limit retry
2. `bronze → 02_cleaning (Pydantic validate) → silver/*.parquet` — Schema-validated clean data
3. `silver + OneMap geocoding → 03_features → gold/*.parquet` — BallTree haversine distances to MRT/schools/malls + rental yield computation
4. `gold → 04_export → platinum/ + app/public/data/*.json` — Unified dataset + webapp JSON exports consumed by Astro frontend

## Tech Stack

| Category              | Technology                                   | Version/Notes                                                |
| --------------------- | -------------------------------------------- | ------------------------------------------------------------ |
| Language              | Python                                       | 3.12+                                                        |
| Package manager       | uv                                           | `uv run`, `uv add`                                           |
| Pipeline orchestrator | sf-hamilton                                  | >=1.0, DAG driver                                            |
| Data processing       | pandas, numpy, pyarrow, geopandas            | DataFrames + parquet I/O                                     |
| ML                    | scikit-learn, xgboost, prophet, shap         | Models in analytics/                                         |
| Validation            | pydantic v2, pydantic-settings               | Schema boundary validation + config                          |
| Geospatial            | geopandas, h3, libpysal, esda                | H3 cells, spatial autocorrelation                            |
| Statistics            | statsmodels, scipy, lifelines                | Regression, survival analysis                                |
| Frontend              | Astro 5, React 19, Tailwind CSS 3            | SSG with React islands                                       |
| Charts                | Recharts 3, Plotly, Kaleido                  | Interactive + static charts                                  |
| Maps                  | Leaflet, react-leaflet                       | Interactive map                                              |
| LLM                   | langchain, langchain-google-genai, langgraph | Gemini integration                                           |
| E2E testing           | Playwright                                   | Browser tests                                                |
| Linting               | ruff, mypy                                   | Python lint + type check                                     |
| CI                    | GitHub Actions                               | 6 workflows (lint, test, security, e2e, deploy, docs-layout) |
| Dev container         | micromamba (Dockerfile)                      | `.devcontainer/`                                             |

## Infrastructure

**Pipeline:**

```bash
uv sync                          # Install dependencies
uv run python -m egg_n_bacon_housing.pipeline   # Run pipeline (via Hamilton driver)
```

**Frontend:**

```bash
cd app && npm install && npm run dev    # Dev server at localhost:4321
cd app && npm run build                 # Static build to app/dist/
```

**CI/CD:** GitHub Actions deploys Astro static site to GitHub Pages (`minghao51.github.io/egg-n-bacon-housing`).

**Devcontainer:** `.devcontainer/Dockerfile` uses micromamba with `environment.yml`.

## Integrations

| Service                | Adapter                          | Purpose                          | Auth                 | Status     |
| ---------------------- | -------------------------------- | -------------------------------- | -------------------- | ---------- |
| data.gov.sg (CKAN API) | `adapters/datagovsg.py`          | HDB/condo/rental/school datasets | None (public)        | Active     |
| OneMap API             | `adapters/onemap.py`             | Geocoding (address → lat/lon)    | JWT (email/password) | Active     |
| URA CSV files          | `adapters/geocoding.py`          | EC + condo transaction CSVs      | N/A (local files)    | Active     |
| Google Gemini          | via langchain-google-genai       | LLM-powered analysis             | API key              | Active     |
| Supabase               | config only (`SUPABASE_URL/KEY`) | Data storage                     | API key              | Configured |
| Jina AI                | config only (`JINA_AI`)          | Web scraping/embeddings          | API key              | Configured |

## Environment Variables

| Variable                        | Required                   | Purpose                        | Used in                  |
| ------------------------------- | -------------------------- | ------------------------------ | ------------------------ |
| `ONEMAP_EMAIL`                  | Yes (geocoding)            | OneMap API auth email          | `adapters/onemap.py:103` |
| `ONEMAP_EMAIL_PASSWORD`         | Yes (geocoding)            | OneMap API auth password       | `adapters/onemap.py:104` |
| `ONEMAP_TOKEN`                  | Optional                   | Cached OneMap JWT token        | `adapters/onemap.py:47`  |
| `GOOGLE_API_KEY`                | Optional                   | Google Gemini LLM access       | `config.py:66`           |
| `SUPABASE_URL`                  | Optional                   | Supabase project URL           | `config.py:67`           |
| `SUPABASE_KEY`                  | Optional                   | Supabase API key               | `config.py:68`           |
| `JINA_AI`                       | Optional                   | Jina AI API key                | `config.py:69`           |
| `PIPELINE__PARQUET_COMPRESSION` | Optional (default: snappy) | Parquet compression algo       | `config.py:10`           |
| `PIPELINE__USE_CACHING`         | Optional (default: true)   | Enable Hamilton DAG cache      | `config.py:12`           |
| `GEOCODING__MAX_WORKERS`        | Optional (default: 5)      | Parallel geocoding workers     | `config.py:18`           |
| `GEOCODING__API_DELAY_SECONDS`  | Optional (default: 1.2)    | Rate limit delay between calls | `config.py:19`           |
