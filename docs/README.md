# Documentation

This directory is split into a small active set of operational docs plus a larger archive of historical design and implementation notes.

## Start Here

| Need | Document |
|------|----------|
| Project overview | [README.md](../README.md) |
| System structure | [docs/architecture.md](./architecture.md) |
| Daily commands and workflows | [docs/guides/usage-guide.md](./guides/usage-guide.md) |
| Guide index | [docs/guides/README.md](./guides/README.md) |
| Troubleshooting | [docs/TROUBLESHOOTING.md](./TROUBLESHOOTING.md) |

## Main Sections

| Path | Purpose |
|------|---------|
| `docs/analytics/` | Published analytics writeups that also feed the app |
| `docs/guides/` | How-to guides for setup, testing, and operations |
| `docs/plans/` | Design docs and implementation plans |
| `docs/archive/` | Historical references and superseded material |

## Active Validation Scope

The docs validator is intended to protect the active documentation path, not every historical note in the repository.

Validated operational docs:

- `README.md`
- `docs/README.md`
- `docs/guides/README.md`
- `docs/guides/usage-guide.md`
- `docs/architecture.md`

The validator also checks:

- analytics frontmatter conventions in `docs/analytics/`
- one-to-one slug parity between `docs/analytics/*.md` and `app/src/content/analytics/*.mdx`

Run it with:

```bash
uv run python scripts/tools/validate_docs_layout.py
```

## Maintenance Notes

- Keep operational docs aligned to the current Hamilton pipeline and `main.py` CLI
- Treat `docs/analytics/*.md` as the editable source of truth for app analytics content
- Move superseded implementation notes into `docs/archive/` instead of rewriting history in place
