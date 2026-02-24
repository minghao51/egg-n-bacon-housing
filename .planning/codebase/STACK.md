# Tech Stack

## Languages & Runtime

- **Python 3.11+** - Main language for data processing pipeline
- **TypeScript 5.9.3** - Frontend development with strict mode
- **JavaScript** - Frontend React components

## Frontend Stack (app/)

### Framework & Meta-Framework
- **Astro 5.16.16** - Static site generator with islands architecture
- **React 19.2.4** - UI framework for interactive components
- **React-DOM 19.2.4** - React DOM bindings

### UI Libraries
- **Tailwind CSS 3** - Utility-first CSS framework
- **@astrojs/react 4.4.2** - React integration for Astro
- **@astrojs/tailwind 6.0.2** - Tailwind CSS integration
- **@astrojs/mdx 4.3.13** - MDX support for markdown content
- **Lucide React 0.575.0** - Icon library
- **@tanstack/react-table 8.21.3** - Headless UI tables

### Visualization & Maps
- **Recharts 3.7.0** - Data visualization library
- **Leaflet 1.9.4 + React-Leaflet 5.0.0** - Interactive maps
- **KaTeX 0.16.28 + Rehype-Katex 7.0.0** - Math rendering
- **React-Markdown 10.1.0** - Markdown rendering

## Python Data Stack

### Core Data Processing
- **pandas >= 2.0.0** - Data manipulation and analysis
- **numpy >= 1.24.0** - Numerical computing
- **geopandas** - Geospatial data processing
- **pyarrow >= 15.0.0** - Parquet file format support
- **h3 == 4.1.0b2** - Hexagonal hierarchical geospatial indexing

### Machine Learning & Statistics
- **scikit-learn** - Machine learning models
- **xgboost >= 3.1.3** - Gradient boosting
- **statsmodels >= 0.14.0** - Statistical modeling
- **shap >= 0.49.1** - Model explainability
- **prophet >= 1.2.1** - Time series forecasting
- **lifelines >= 0.27.0** - Survival analysis

### Spatial Analysis
- **libpysal >= 4.6.0** - Spatial statistics library
- **esda >= 1.5.0** - Exploratory spatial data analysis
- **scipy >= 1.17.0** - Scientific computing

### Web & APIs
- **requests** - HTTP client
- **supabase** - Database client (configured but not actively used)
- **python-dotenv** - Environment variable management

### AI/LLM Integration
- **langchain >= 0.3.0** - LLM framework
- **langchain-google-genai == 2.0.0** - Google Generative AI integration
- **langchain-experimental == 0.3.0** - Experimental features
- **langchain-community** - Community integrations

### Visualization & Reporting
- **plotly >= 6.5.2** - Interactive charts
- **marimo >= 0.19.6** - Reactive notebooks
- **kaleido >= 1.2.0** - Static image export
- **pygwalker** - Interactive data exploration

## Development Tools

### Python Development
- **uv** - Fast Python package manager
- **pytest 7.0.0+** - Testing framework
- **ruff 0.1.0** - Linter and formatter (line length: 100)
- **jupyter** - Interactive notebooks
- **ipykernel** - Jupyter kernel
- **jupytext** - Notebook pairing (.ipynb ↔ .py)

### Frontend Development
- **Node.js** - JavaScript runtime
- **npm** - Package manager (via package.json)
- **TypeScript 5.9.3** - Static type checking
- **Playwright 1.58.0** - End-to-end testing

## Configuration Files

### Python Configuration
- **pyproject.toml** - Project configuration, dependencies, tool settings
- **jupytext.toml** - Jupytext notebook pairing configuration
- **.env** - Environment variables (not in git)

### Frontend Configuration
- **astro.config.mjs** - Astro framework configuration
- **tsconfig.json** - TypeScript configuration (extends astro strict)
- **package.json** - Node.js dependencies
- **tailwind.config.mjs** - Tailwind CSS configuration

## Code Quality Tools

### Python
- **Ruff** - Linting and formatting
  - Line length: 100 characters
  - Target version: Python 3.11
  - Comprehensive rule set (E, F, W, I, N, UP)

### Testing
- **pytest** - Testing framework with:
  - Unit tests (@pytest.mark.unit)
  - Integration tests (@pytest.mark.integration)
  - Slow tests (@pytest.mark.slow)
  - API tests (@pytest.mark.api)
  - Coverage reporting (term, html, xml)

## Documentation Standards

- **Google-style docstrings** for all public functions
- **Type hints** required for all public APIs
- **Absolute imports** from project root (no relative imports)
- **Structured logging** with emojis for visual cues

## Version Control

- **Git** - Version control
- **GitHub** - Remote repository
- **Conventional Commits** - Commit message format
- **.gitignore** - Excludes: .venv, .env, __pycache__, node_modules, .astro

## Key Technical Decisions

1. **Astro over Next.js** - Better performance for static sites with content-focused pages
2. **Parquet over CSV** - Efficient columnar storage for large datasets
3. **Stage-based pipeline** - Clear separation of concerns (L0-L5)
4. **Metadata-driven** - All datasets tracked in metadata.json
5. **No backend API** - Frontend consumes pre-generated JSON files
6. **Absolute imports** - Prevents import issues when running from different directories
7. **uv over pip/poetry** - Faster dependency management
