# Tech Stack

## Languages

- **Python** 3.11+ (primary data/ML pipeline)
- **TypeScript** (frontend/app)
- **JavaScript** (minimal, Astro config)

## Runtime & Package Managers

- **uv** (Python package manager, per pyproject.toml)
- **npm** (Node.js for Astro app)

## Frontend Framework (app/)

- **Astro** 5.x - Static site generator with islands architecture
- **React** 19 - UI components (Astro integration)
- **TailwindCSS** 3 - Utility-first styling
- **MDX** - Markdown with JSX for content

### Frontend Dependencies

| Package | Purpose |
|---------|---------|
| `recharts` | Data visualization charts |
| `react-leaflet` / `leaflet` | Interactive maps |
| `react-markdown` | Markdown rendering |
| `katex` / `rehype-katex` | Math rendering |
| `shiki` | Syntax highlighting |
| `clsx` / `tailwind-merge` | Class utilities |
| `dompurify` | HTML sanitization |
| `@tanstack/react-table` | Data tables |

## Data Processing (scripts/, notebooks/)

| Package | Purpose |
|---------|---------|
| `pandas` 2.0+ | Data manipulation |
| `numpy` 1.24+ | Numerical computing |
| `pyarrow` 15+ | Parquet file support |
| `scipy` 1.17+ | Scientific computing |

## ML & Statistics

| Package | Purpose |
|---------|---------|
| `scikit-learn` | ML algorithms |
| `xgboost` 3.1+ | Gradient boosting |
| `prophet` 1.2+ | Time series forecasting |
| `statsmodels` 0.14+ | Statistical models |
| `lifelines` 0.27+ | Survival analysis |
| `shap` 0.49+ | SHAP explanations |

## Spatial/GIS

| Package | Purpose |
|---------|---------|
| `geopandas` | Geospatial data |
| `pygwalker` | Visual Geoprocessing |
| `h3` 4.1b2 | Hexagonal spatial indexing |
| `libpysal` 4.6+ | Spatial analysis |
| `esda` 1.5+ | Spatial autocorrelation |
| `shapely` | Geometric operations |

## AI/LLM (notebooks/exploration/)

| Package | Purpose |
|---------|---------|
| `langchain` 0.3+ | LLM framework |
| `langgraph` 0.2+ | Agent orchestration |
| `langchain-google-genai` 2.0 | Google Gemini integration |
| `langchain-community` | Databricks, SQL agents |
| `langchain-experimental` | Pandas/Spark DataFrame agents |

## Visualization

| Package | Purpose |
|---------|---------|
| `plotly` 6.5+ | Interactive plots |
| `seaborn` | Statistical plots |
| `kaleido` | Static plot export |

## Infrastructure & External Services

| Package | Purpose |
|---------|---------|
| `boto3` | AWS S3 interactions |
| `supabase` | Backend-as-a-service |
| `requests` | HTTP client |

## Config Files

### Frontend (app/)

| File | Purpose |
|------|---------|
| `tsconfig.json` | Extends Astro strict, path aliases (@/*, @components/*, etc.) |
| `astro.config.mjs` | Astro integrations: React, MDX, Tailwind, remark/rehype plugins |
| `tailwind.config.mjs` | Dark mode class, custom color tokens |
| `playwright.config.ts` | E2E test config, Chromium only |
| `content.config.ts` | Astro content collections schema |

### Python (root/)

| File | Purpose |
|------|---------|
| `pyproject.toml` | Ruff linting (E,F,W,I,N,UP), pytest config, coverage settings |

## Testing

| Framework | Scope |
|-----------|-------|
| `pytest` | Python unit/integration tests |
| `pytest-cov` | Coverage reporting |
| `pytest-mock` | Mocking |
| `pytest-asyncio` | Async tests |
| `@playwright/test` | E2E tests |

## Linting & Formatting

| Tool | Config |
|------|--------|
| `ruff` | pyproject.toml [tool.ruff], line-length 100, py311 target |
