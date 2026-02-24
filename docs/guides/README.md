# Guides Index

Operational and reference guides for working in this repository.

## Start Here

- [Quick Start](./quick-start.md)
- [Usage Guide](./usage-guide.md)
- [External Data Setup](./external-data-setup.md)

## Pipeline Guides

- [L2 Pipeline](./l2-pipeline.md)
- [L4 Analysis Pipeline](./l4-analysis-pipeline.md)
- [CSV Download Guide](./CSV_DOWNLOAD_GUIDE.md)

## Reference Guides

- [Data Reference](./data-reference.md)
- [MRT Features Guide](./mrt-features-guide.md)
- [Architecture](../architecture.md)

## Operations

- [Testing Guide](./testing-guide.md)
- [OneMap Auth Fix](./ONEMAP_AUTH_FIX.md)
- [GitHub Secrets Setup](./github-secrets-setup.md)

## Common Commands

```bash
# Run pipeline stages
uv run python scripts/run_pipeline.py --stage all
uv run python scripts/run_pipeline.py --stage L0
uv run python scripts/run_pipeline.py --stage L5

# Analytics pipelines
uv run python scripts/analytics/pipelines/calculate_l3_metrics_pipeline.py
uv run python scripts/analytics/pipelines/forecast_prices_pipeline.py

# Analysis scripts
uv run python scripts/analytics/analysis/mrt/analyze_mrt_impact.py
uv run python scripts/analytics/analysis/spatial/analyze_spatial_hotspots.py

# Data refresh and geocoding
uv run python scripts/data/download/refresh_external_data.py --dry-run
uv run python scripts/data/process/geocode/geocode_addresses.py --parallel --workers 10

# Utilities
uv run python scripts/utils/refresh_onemap_token.py
uv run python scripts/utils/check_geocoding_progress.py
```

## Notes

- Use `uv run` for project scripts to ensure the managed environment is used.
- `scripts/README.md` is the canonical script layout reference.
- `docs/README.md` is the top-level documentation map.
