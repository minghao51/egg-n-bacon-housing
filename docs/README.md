# Documentation Map

Top-level documentation index for the project.

## Active Documentation

- `docs/architecture.md` - System architecture and design overview
- `docs/guides/` - How-to guides, setup, operations, and references
- `docs/analytics/` - Published analytics content used by the app
- `docs/plans/` - Planning/design/implementation notes (active + recent)

## Historical Documentation

- `docs/archive/` - Completed summaries, historical reports, and superseded notes

## Conventions

- Prefer `kebab-case` file names for guides and analytics docs.
- Use `YYYY-MM-DD-short-title.md` for dated plans/reports.
- Keep only foundational docs at `docs/` root.
- Move completed implementation summaries to `docs/archive/` after they are no longer actively referenced.

## Maintenance

Run the docs/layout validation script after moving files or changing references:

```bash
uv run python scripts/tools/validate_docs_layout.py
```
