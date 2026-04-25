# Guides Index

Operational guides for the current repository layout.

## Core Guides

| Guide | Purpose |
|-------|---------|
| [usage-guide.md](./usage-guide.md) | Primary setup, pipeline, and analytics workflow |
| [testing-guide.md](./testing-guide.md) | Test commands and testing practices |
| [configuration.md](./configuration.md) | Environment and settings details |
| [e2e-testing.md](./e2e-testing.md) | Astro app end-to-end testing |
| [data-reference.md](./data-reference.md) | Dataset descriptions and schemas |

## Common Commands

```bash
uv sync
uv run python main.py
uv run python main.py --stage export
./scripts/sync-content.sh
uv run python scripts/tools/validate_docs_layout.py
uv run pytest
uv run ruff check .
```

## Notes

- Some older guides still document pre-refactor workflows and should be treated as historical until they are refreshed.
- The active documentation path for onboarding is `README.md` -> `docs/README.md` -> `docs/guides/usage-guide.md`.
