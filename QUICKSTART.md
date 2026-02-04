# 🚀 Quick Start Guide

**Get up and running in 5 minutes!**

---

## Step 1: Install uv (One-time, 30 seconds)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Step 2: Install Dependencies (1 minute)

```bash
cd egg-n-bacon-housing
uv sync
```

## Step 3: Setup API Keys (2 minutes)

```bash
cp .env.example .env
```

Edit `.env` and add:
- `ONEMAP_EMAIL` - Register free at https://www.onemap.gov.sg/apidocs/register
- `ONEMAP_EMAIL_PASSWORD` - Your OneMap password
- `GOOGLE_API_KEY` - Optional, for agents

## Step 4: Verify Setup (30 seconds)

```bash
uv run pytest
```

All tests should pass! ✅

## Step 5: Run the Pipeline (When ready)

```bash
# Interactive guide - recommended!
uv run python run_real_pipeline.py

# Or run demo first (no API keys needed)
uv run python demo_pipeline.py
```

---

## 📚 Documentation

- **[Usage Guide](docs/20250120-usage-guide.md)** - Complete usage reference
- **[Architecture](docs/20250120-architecture.md)** - System design
- **[Pipeline Details](docs/20250120-data-pipeline.md)** - Data flow
- **[Running Real Pipeline](docs/20250120-running-real-pipeline.md)** - Execution guide

## 🎯 Common Commands

```bash
# Run tests
uv run pytest

# Run demo pipeline
uv run python demo_pipeline.py

# Run real pipeline (needs API keys)
uv run python run_real_pipeline.py

# Start Jupyter
uv run jupyter notebook

# Check linting
uv run ruff check .
```

## 📖 Learning Path

1. **Start Here** - Read [CLAUDE.md](CLAUDE.md) (5 min)
2. **Architecture** - Read [docs/20250120-architecture.md](docs/20250120-architecture.md) (10 min)
3. **Usage** - Read [docs/20250120-usage-guide.md](docs/20250120-usage-guide.md) (15 min)
4. **Build** - Run the pipeline! 🚀

---

**Done!** You're ready to use the project.

Need help? Check the [Usage Guide](docs/20250120-usage-guide.md) or [docs/](docs/) folder.

Happy coding! 🎉
