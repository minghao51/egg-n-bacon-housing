# Documentation

This directory keeps a small active operational path plus a larger archive of historical notes.

## Start Here

| Need             | Document                                         |
| ---------------- | ------------------------------------------------ |
| Project overview | [README.md](../README.md)                        |
| System structure | [architecture.md](./architecture.md)             |
| Daily workflow   | [guides/usage-guide.md](./guides/usage-guide.md) |
| Guide index      | [guides/README.md](./guides/README.md)           |
| Troubleshooting  | [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)       |

## Main Sections

| Path              | Purpose                                             |
| ----------------- | --------------------------------------------------- |
| `docs/analytics/` | Analytics markdown loaded directly by the Astro app |
| `docs/guides/`    | Setup, testing, and operations guides               |
| `docs/plans/`     | Design and implementation plans                     |
| `docs/archive/`   | Historical references and superseded material       |

## Active Validation Scope

The docs validator protects the active operational surface, not every historical note in the repo.

Validated docs:

- `README.md`
- `QUICKSTART.md`
- `CONTRIBUTING.md`
- `docs/README.md`
- `docs/TROUBLESHOOTING.md`
- `docs/architecture.md`
- `docs/guides/README.md`
- `docs/guides/quick-start.md`
- `docs/guides/usage-guide.md`
- `docs/guides/ci-cd-pipeline.md`
- `docs/guides/e2e-testing.md`
- `app/README.md`

The validator also checks:

- analytics frontmatter conventions in `docs/analytics/`
- that the app content loader still points at `docs/analytics/`
- that the analytics pages used by the app still exist

Run it with:

```bash
uv run python scripts/tools/validate_docs_layout.py
```

## Maintenance Notes

- Keep operational docs aligned to `main.py` and the current GitHub workflows.
- Treat `docs/analytics/*.md` as the editable analytics content source.
- Move superseded operational notes into `docs/archive/` instead of keeping stale guidance in the active docs path.
