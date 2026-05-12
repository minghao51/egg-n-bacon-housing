# Tech Stack

## Languages

- **Python** 3.12+ (primary data/ML pipeline)
- **TypeScript** (frontend)
- **JavaScript** (Astro config)

## Runtime & Package Managers

- **uv** (Python package manager)
- **npm/bun** (Node.js for Astro app)

## Data Processing

| Package        | Purpose              |
| -------------- | -------------------- |
| `pandas` 2.0+  | Data manipulation    |
| `numpy` 1.24+  | Numerical computing  |
| `pyarrow` 15+  | Parquet file support |
| `polars` 1.40+ | Fast DataFrame ops   |
| `scipy` 1.17+  | Scientific computing |

## Pipeline Orchestration

| Package                  | Purpose                  |
| ------------------------ | ------------------------ |
| `sf-hamilton` 1.0+       | DAG pipeline driver      |
| `pydantic` 2.0+          | Data validation          |
| `pydantic-settings` 2.0+ | Configuration management |
| `pyyaml` 6.0+            | YAML config parsing      |

## ML & Statistics

| Package             | Purpose                 |
| ------------------- | ----------------------- |
| `scikit-learn`      | ML algorithms           |
| `xgboost` 3.1+      | Gradient boosting       |
| `prophet` 1.2+      | Time series forecasting |
| `statsmodels` 0.14+ | Statistical models      |
| `lifelines` 0.27+   | Survival analysis       |
| `shap` 0.49+        | SHAP explanations       |

## Spatial/GIS

| Package         | Purpose                    |
| --------------- | -------------------------- |
| `geopandas`     | Geospatial data            |
| `h3` 4.1b2      | Hexagonal spatial indexing |
| `libpysal` 4.6+ | Spatial analysis           |
| `esda` 1.5+     | Spatial autocorrelation    |
| `shapely`       | Geometric operations       |

## LLM/AI

| Package                      | Purpose                |
| ---------------------------- | ---------------------- |
| `langchain` 0.3+             | LLM framework          |
| `langgraph` 0.2+             | Agent orchestration    |
| `langchain-google-genai` 2.0 | Google Gemini          |
| `langchain-community`        | Community integrations |
| `langchain-experimental` 0.3 | Pandas/Spark agents    |

## Visualization

| Package       | Purpose            |
| ------------- | ------------------ |
| `plotly` 6.5+ | Interactive plots  |
| `seaborn`     | Statistical plots  |
| `kaleido`     | Static plot export |
| `pygwalker`   | Visual exploration |

## Frontend (app/)

- **Astro** 5.x — Static site generator
- **React** 19 — UI islands
- **TailwindCSS** 3 — Utility-first styling
- **MDX** — Markdown + JSX

### Frontend Key Dependencies

| Package                     | Purpose             |
| --------------------------- | ------------------- |
| `recharts`                  | Charts              |
| `react-leaflet` / `leaflet` | Maps                |
| `react-markdown`            | Markdown rendering  |
| `katex`                     | Math rendering      |
| `shiki`                     | Syntax highlighting |
| `@tanstack/react-table`     | Data tables         |

## Infrastructure

| Package    | Purpose              |
| ---------- | -------------------- |
| `boto3`    | AWS S3               |
| `supabase` | Backend-as-a-service |
| `requests` | HTTP client          |
| `tenacity` | Retry logic          |

## Testing

| Framework          | Scope                   |
| ------------------ | ----------------------- |
| `pytest`           | Python unit/integration |
| `pytest-cov`       | Coverage                |
| `pytest-mock`      | Mocking                 |
| `pytest-asyncio`   | Async                   |
| `@playwright/test` | E2E                     |
| `mypy`             | Type checking           |
