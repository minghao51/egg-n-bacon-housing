# Contributing to Egg-n-Bacon-Housing

This repository has two supported development surfaces:

- the Python pipeline under `src/egg_n_bacon_housing/`
- the Astro app under `app/`

Keep changes scoped to the surface you are working on and prefer the active workflows below over older notebook- or script-era paths.

## Setup

```bash
git clone https://github.com/your-username/egg-n-bacon-housing.git
cd egg-n-bacon-housing
uv sync
cp .env.example .env
```

If you need the manual source bundle:

```bash
dotenvx run -- uv run python scripts/00_sync_data.py
```

## Core Commands

### Python pipeline

```bash
uv run python main.py --stage all
uv run python main.py --stage ingest
uv run python main.py --stage clean
uv run python main.py --stage features
uv run python main.py --stage export
uv run python main.py --stage metrics
uv run python main.py --visualize
```

### Quality checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/egg_n_bacon_housing/components src/egg_n_bacon_housing/adapters src/egg_n_bacon_housing/utils/cache.py src/egg_n_bacon_housing/utils/contracts.py src/egg_n_bacon_housing/pipeline.py src/egg_n_bacon_housing/config.py tests
uv run python scripts/tools/validate_docs_layout.py
```

### Web app

```bash
cd app
bun install
bun run dev
bun run build
bun run test:e2e
```

## Repository Shape

```text
src/egg_n_bacon_housing/
├── components/   # Supported Hamilton DAG stages
├── adapters/     # External API clients
├── utils/        # Reusable helpers and loaders
├── config.py     # Pydantic settings
└── analytics/    # Standalone exploratory scripts, not part of the DAG

app/              # Astro app
docs/analytics/   # Analytics markdown loaded directly by Astro
tests/            # Python test suite
```

## Working Conventions

- Run Python commands with `uv run`.
- Run app commands from `app/` with Bun.
- Treat `docs/analytics/*.md` as the editable analytics content source.
- Do not reintroduce the retired pre-`main.py` pipeline runner, the old content-sync shell step, or the removed generated analytics content copy; those are no longer supported surfaces.
- Keep pipeline changes aligned to the 5-stage `main.py` flow ending at `05_metrics`.

## Tests

- Use `tests/test_*.py` style for Python coverage.
- Mark slower or broader tests explicitly with the existing pytest markers.
- For app changes, prefer the Playwright suite in `app/tests/e2e/`.

## Pull Requests

Before opening a PR:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/tools/validate_docs_layout.py
```

For app-facing changes, also run:

```bash
cd app
bun run build
```
