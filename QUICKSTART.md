# Quick Start

Get the supported pipeline and app surfaces running with the smallest setup path.

## 1. Install dependencies

```bash
cd egg-n-bacon-housing
uv sync
```

## 2. Configure secrets

```bash
cp .env.example .env
```

Populate the values used by the core workflow:

- `ONEMAP_EMAIL`
- `ONEMAP_EMAIL_PASSWORD`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `R2_ENDPOINT`

## 3. Sync manual source data

```bash
dotenvx run -- uv run python scripts/00_sync_data.py
```

## 4. Verify the local setup

```bash
uv run pytest --no-cov
uv run python main.py --help
```

## 5. Run the pipeline

```bash
uv run python main.py --stage all
```

Common stage-only runs:

```bash
uv run python main.py --stage ingest
uv run python main.py --stage clean
uv run python main.py --stage features
uv run python main.py --stage export
uv run python main.py --stage metrics
```

## 6. Run the app

```bash
cd app
bun install
bun run dev
```

## Docs

- [README.md](README.md)
- [Architecture](docs/architecture.md)
- [Usage Guide](docs/guides/usage-guide.md)
- [R2 Sync Guide](docs/guides/r2-sync-guide.md)
