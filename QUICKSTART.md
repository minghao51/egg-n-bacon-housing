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
# Fetch manual data from Cloudflare R2 (~100MB) - one time after clone
dotenvx run -- uv run python scripts/00_sync_data.py

# Run the pipeline
uv run python main.py --stage all
```

---

## 📚 Documentation

- **[R2 Sync Guide](docs/guides/r2-sync-guide.md)** - Manual data setup
- **[Usage Guide](docs/20250120-usage-guide.md)** - Complete usage reference
- **[Architecture](docs/20250120-architecture.md)** - System design
- **[Pipeline Details](docs/20250120-data-pipeline.md)** - Data flow

## 🎯 Common Commands

```bash
# Sync manual data from R2
dotenvx run -- uv run python scripts/00_sync_data.py

# Run tests
uv run pytest

# Run the pipeline
uv run python main.py --stage all

# Lint
uv run ruff check .
```
