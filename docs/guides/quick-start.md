# Quick Start Guide

**Last Updated**: 2026-06-12 | **Status**: Active

## Setup

```bash
git clone <repo-url>
cd egg-n-bacon-housing
uv sync
cp .env.example .env
dotenvx run -- uv run python scripts/00_sync_data.py
```

## Verify

```bash
uv run pytest --no-cov
uv run python main.py --help
```

## Run the Pipeline

```bash
uv run python main.py --stage all
```

Common stage runs:

```bash
uv run python main.py --stage ingest
uv run python main.py --stage clean
uv run python main.py --stage features
uv run python main.py --stage export
uv run python main.py --stage metrics
```

## Run the App

```bash
cd app
bun install
bun run dev
```

## Quality Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/tools/validate_docs_layout.py
```
