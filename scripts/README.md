# Scripts Directory

Operational scripts for the data pipeline, analytics pipelines, webapp exports, and maintenance tooling.

## Layout

```text
scripts/
├── run_pipeline.py                 # Main pipeline entrypoint (stable)
├── prepare_webapp_data.py          # Dashboard export entrypoint (stable)
├── create_l3_unified_dataset.py    # Convenience wrapper (stable)
├── sync-content.sh                 # Sync analytics markdown into app content
├── webapp/                         # Webapp JSON generation/transforms
├── tools/                          # Dev/validation helpers
├── analytics/                      # Analytics pipelines, models, analysis, viz
├── data/                           # Data download and processing scripts
├── core/                           # Shared pipeline/core modules
└── utils/                          # Operational utilities (tokens, validation, checks)
```

## Root-Level Policy

Keep only frequently used entrypoints and top-level script docs at `scripts/`.

- `scripts/webapp/` contains dashboard JSON generators and transforms
- `scripts/tools/` contains developer tooling and validations

Compatibility wrappers remain at some legacy root paths for tests and old docs.

## Common Commands

```bash
# Pipeline
uv run python scripts/run_pipeline.py --stage all
uv run python scripts/run_pipeline.py --stage L0

# L3 unified dataset
uv run python scripts/create_l3_unified_dataset.py

# Webapp export
uv run python scripts/prepare_webapp_data.py
uv run python scripts/webapp/prepare_interactive_tools_data.py

# Analytics pipelines
uv run python scripts/analytics/pipelines/calculate_l3_metrics_pipeline.py
uv run python scripts/analytics/pipelines/forecast_prices_pipeline.py

# Analysis scripts
uv run python scripts/analytics/analysis/mrt/analyze_mrt_impact.py
uv run python scripts/analytics/analysis/spatial/analyze_spatial_hotspots.py

# Utilities and tooling
uv run python scripts/utils/check_geocoding_progress.py
uv run python scripts/tools/verify_imports.py
uv run python scripts/tools/validate_docs_layout.py
```

## Conventions

- Names: `verb_noun.py` (general) or `*_pipeline.py` (analytics pipelines)
- Put reusable logic in `scripts/core/` or package modules, not in root scripts
- Update the nearest README when adding or moving scripts
- Prefer compatibility wrappers when relocating scripts that are referenced by tests/docs

## Related Docs

- `scripts/PIPELINE_GUIDE.md`
- `scripts/analytics/README.md`
- `scripts/data/README.md`
- `scripts/utils/README.md`
- `scripts/webapp/README.md`
- `scripts/tools/README.md`
- `docs/README.md`
