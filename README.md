# Egg-n-Bacon-Housing 🏠🥓✨

A Singapore housing data pipeline and ML analysis platform with AI-powered agent assistance.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-0.1.0+-brightgreen.svg)](https://github.com/astral-sh/uv)

## 🚀 Quick Start

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repo-url>
cd egg-n-bacon-housing
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run tests
uv run pytest

# Start Jupyter
uv run jupyter notebook
```

## 📋 Overview

Egg-n-Bacon-Housing collects, processes, and analyzes Singapore housing data from multiple government APIs. It provides:

- **Data Pipeline**: Automated ETL from data.gov.sg, OneMap, and other sources
- **Feature Engineering**: Rich features for ML models and analysis
- **AI Agents**: LangChain-powered agents for querying housing data
- **Interactive Apps**: Streamlit dashboards for data exploration

## 🏗️ Architecture

```
L0: Data Collection (External APIs)
    ↓
L1: Data Processing (Cleaning, Standardization)
    ↓
L2: Feature Engineering (Distance, Aggregation)
    ↓
L3: Export (S3, Supabase, Apps)
```

**Key Technologies**:
- **Package Manager**: uv (10-100x faster than conda/pip)
- **Data Storage**: Local parquet files with metadata tracking
- **Notebooks**: Jupyter + Jupytext (paired .py files for version control)
- **Testing**: pytest + ruff
- **Configuration**: Centralized in `src/config.py`
- **ML/AI**: LangChain + LangGraph + Google Gemini

## 📚 Documentation

- **[Architecture Documentation](docs/20250120-architecture.md)** - System architecture and design
- **[Data Pipeline Documentation](docs/20250120-data-pipeline.md)** - Pipeline details and data flow
- **[Development Workflow](CLAUDE.md)** - Development principles and guidelines
- **[Migration Summary](docs/20250120-migration-summary.md)** - DVC → Parquet migration guide

## 🔧 Setup

### Prerequisites

- Python 3.11+
- uv package manager
- API keys (see below)

### Installation

1. **Install uv** (one-time):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### API Keys Required

Create a `.env` file in the project root:

```bash
# OneMap API (free registration required)
ONEMAP_EMAIL=your_email@example.com
ONEMAP_EMAIL_PASSWORD=your_password

# Google AI (for LangChain agents)
GOOGLE_API_KEY=your_google_api_key

# Supabase (optional, for database export)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Jina AI (optional, for web scraping)
JINA_AI=your_jina_ai_key
```

**Register for APIs**:
- [OneMap API](https://www.onemap.gov.sg/apidocs/register) - Free
- [Google AI Studio](https://makersuite.google.com/app/apikey) - Free tier available
- [Supabase](https://supabase.com/) - Free tier available

## 🎯 Usage

### Running the Pipeline

**Option 1: Run Automated Scripts (Recommended)**

```bash
# Run complete pipeline with checkpointing and resume capability
uv run python scripts/run_pipeline.py

# Run geocoding with parallel batched processing (~5x faster)
uv run python scripts/geocode_addresses_batched.py
```

**Option 2: Run Notebooks Manually**

Run notebooks in order:

```bash
# L0: Data Collection
uv run jupyter notebook notebooks/L0_datagovsg.ipynb
uv run jupyter notebook notebooks/L0_onemap.ipynb
uv run jupyter notebook notebooks/L0_wiki.ipynb

# L1: Data Processing
uv run jupyter notebook notebooks/L1_ura_transactions_processing.ipynb
uv run jupyter notebook notebooks/L1_utilities_processing.ipynb

# L2: Feature Engineering
uv run jupyter notebook notebooks/L2_sales_facilities.ipynb
```

### Using Jupytext (Recommended)

All notebooks are paired with `.py` files for better version control:

```bash
# Edit the .py file in VS Code
code notebooks/L0_datagovsg.py

# Run the .py file
uv run python notebooks/L0_datagovsg.py

# Sync back to .ipynb (automatic, or manual)
cd notebooks
uv run jupytext --sync L0_datagovsg.ipynb
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test
uv run pytest tests/test_data_helpers.py
```

### Monitoring Background Jobs

```bash
# Check running geocoding processes
ps aux | grep geocode_addresses_batched | grep -v grep

# View real-time logs
tail -f data/logs/geocoding_batched_*.log

# Check latest checkpoint
ls -lh data/checkpoints/L2_housing_unique_searched_checkpoint_*.parquet
```

### Running Apps

```bash
# Streamlit apps
uv run streamlit run apps/single_agent.py
uv run streamlit run apps/spiral.py
```

### Code Quality

```bash
# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

## 📁 Project Structure

```
egg-n-bacon-housing/
├── data/               # Data directory
│   ├── parquets/      # All parquet files (gitignored)
│   ├── checkpoints/   # Pipeline checkpoints (gitignored)
│   ├── logs/          # Pipeline logs (gitignored)
│   └── metadata.json  # Dataset registry (git-tracked)
├── notebooks/         # Jupyter notebooks (paired with .py)
├── src/              # Source code
│   ├── config.py     # Centralized configuration
│   ├── data_helpers.py # Parquet management
│   ├── geocoding.py  # OneMap API geocoding utilities
│   ├── cache.py      # API response caching
│   ├── agent/        # LangChain agents
│   └── pipeline/     # Extracted pipeline logic
├── scripts/          # Automated pipeline scripts
│   ├── run_pipeline.py           # Complete pipeline runner
│   ├── geocode_addresses_batched.py # Parallel batched geocoding (recommended)
│   └── geocode_addresses.py      # Sequential geocoding (legacy)
├── apps/             # Streamlit applications
├── tests/            # Test suite
└── docs/             # Documentation
```

## 🎓 Learning Resources

### For New Developers

1. **Start here**: Read [CLAUDE.md](CLAUDE.md) for development principles
2. **Understand architecture**: Read [docs/20250120-architecture.md](docs/20250120-architecture.md)
3. **Learn the pipeline**: Read [docs/20250120-data-pipeline.md](docs/20250120-data-pipeline.md)
4. **Check progress**: See [docs/progress/20250120-dvc-to-parquet-migration-progress.md](docs/progress/20250120-dvc-to-parquet-migration-progress.md)

### Key Concepts

**Data Management**:
- Uses local parquet files (not DVC/S3) for faster access
- Metadata tracked in `data/metadata.json`
- Load/save via `src/data_helpers.py`

**Configuration**:
- All settings in `src/config.py`
- Environment variables in `.env`
- Validation prevents errors

**Testing**:
- 7 tests passing (pytest)
- Linting configured (ruff)
- Run `uv run pytest` to verify

## 🚧 Recent Changes

### v0.3.0 (2026-01-22) - Batched Geocoding

**Performance Improvements**:
- ✅ Added parallel batched geocoding script (~5x faster)
- ✅ 5 parallel workers with checkpointing and resume
- ✅ Fixed import issues in src/ modules
- ✅ Comprehensive progress logging and monitoring

**Benefits**:
- Geocoding time reduced from 4-7 hours to ~48 minutes
- Better error handling and graceful shutdown
- Real-time progress monitoring
- Auto-resume from checkpoints

See [docs/20260122-geocoding-batched-restart.md](docs/20260122-geocoding-batched-restart.md) for details.

### v0.2.0 (2025-01-20) - Major Update

**Migration Complete**:
- ✅ Removed DVC, migrated to local parquet
- ✅ Migrated to uv (from conda)
- ✅ Setup Jupytext for all notebooks
- ✅ Created centralized config
- ✅ Added basic tests (7 passing)
- ✅ Configured ruff linting
- ✅ Added comprehensive documentation

**Benefits**:
- 10-100x faster data access
- Simpler workflow (uv run)
- Better version control (Jupytext)
- Comprehensive testing

See [docs/20250120-parquet-migration-design.md](docs/20250120-parquet-migration-design.md) for details.

## 🤝 Contributing

See [CLAUDE.md](CLAUDE.md) for development principles.

**Quick Start**:
1. Read `CLAUDE.md`
2. Run `uv sync`
3. Run `uv run pytest`
4. Check `docs/` for details

## 🔮 Future Improvements

- [ ] Extract notebook logic to `src/pipeline/*.py` scripts
- [ ] Consolidate Streamlit apps into multi-page app
- [ ] Add integration tests
- [ ] Setup CI/CD pipeline
- [ ] Add more agent tools

## 📞 Support

- **Issues**: Create a GitHub issue
- **Questions**: Check [docs/](docs/) first
- **Notion**: [Internal documentation (invite only)](https://www.notion.so/Housing-Agents-App-0c4bdd40940542b2bcd366207428e517?pvs=4)

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- data.gov.sg for open housing data
- OneMap for excellent geospatial APIs
- LangChain team for the framework
- Supabase for the generous free tier

---

**Made with ❤️ and 🥓 for Singapore housing agents**
