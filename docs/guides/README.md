# Guides Index

Operational guides for the current repository layout.

## Core Guides

| Guide                                  | Purpose                                               |
| -------------------------------------- | ----------------------------------------------------- |
| [usage-guide.md](./usage-guide.md)     | Primary setup, pipeline, app, and publishing workflow |
| [r2-sync-guide.md](./r2-sync-guide.md) | Manual data fetch from Cloudflare R2                  |
| [testing-guide.md](./testing-guide.md) | Test commands and testing practices                   |
| [e2e-testing.md](./e2e-testing.md)     | Astro app end-to-end testing                          |

## Common Commands

```bash
uv sync
uv run python main.py
uv run python main.py --stage export
uv run python scripts/tools/validate_docs_layout.py
uv run pytest --no-cov
uv run ruff check .
uv run mypy
```

## Notes

- The active guide path is intentionally small; older script-era analytics guides were removed with the retired Python analytics surface.
- The active documentation path for onboarding is `README.md` -> `docs/README.md` -> `docs/guides/usage-guide.md`.
