# Guides Index

Operational and reference guides for working with this repository.

## Start Here

- **[Quick Start](./quick-start.md)** - 5-minute setup walkthrough
- **[Usage Guide](./usage-guide.md)** - Common tasks and workflows
- **[External Data Setup](./external-data-setup.md)** - API key configuration

## User Guides

For running the pipeline and exploring data:

| Guide | Description |
|-------|-------------|
| **[Data Reference](./data-reference.md)** | Available datasets and schemas |
| **[L2 Pipeline](./l2-pipeline.md)** | Feature engineering pipeline |
| **[L4 Analysis Pipeline](./l4-analysis-pipeline.md)** | Running market analyses |
| **[CSV Download Guide](./csv-download-guide.md)** | Exporting data to CSV |
| **[MRT Features Guide](./mrt-features-guide.md)** | MRT distance feature engineering |

## Developer Guides

For contributing and development:

| Guide | Description |
|-------|-------------|
| **[Testing Guide](./testing-guide.md)** | Writing and running tests |
| **[E2E Testing](./e2e-testing.md)** | Frontend end-to-end tests |
| **[Configuration](./configuration.md)** | Environment variables and settings |
| **[CI/CD Pipeline](./ci-cd-pipeline.md)** | GitHub Actions workflows |
| **[Data Quality Monitoring](./data-quality-monitoring.md)** | Quality metrics and alerts |
| **[GitHub Secrets Setup](./github-secrets-setup.md)** | CI/CD secrets configuration |

**See also:** [CONTRIBUTING.md](../../CONTRIBUTING.md) for complete contributor guide.

## Common Commands

### Pipeline Operations

```bash
# Run all stages
uv run python scripts/run_pipeline.py --stage all

# Run specific stage
uv run python scripts/run_pipeline.py --stage L0    # Data collection
uv run python scripts/run_pipeline.py --stage L1    # Processing
uv run python scripts/run_pipeline.py --stage L2    # Features
uv run python scripts/run_pipeline.py --stage L3    # Metrics
uv run python scripts/run_pipeline.py --stage L5    # Dashboard data
```

### Analytics Pipelines

```bash
# Calculate metrics
uv run python scripts/analytics/pipelines/calculate_l3_metrics_pipeline.py

# Price forecasting
uv run python scripts/analytics/pipelines/forecast_prices_pipeline.py

# Market segmentation
uv run python scripts/analytics/pipelines/segment_market_pipeline.py
```

### Analysis Scripts

```bash
# MRT impact analysis
uv run python scripts/analytics/analysis/mrt/analyze_mrt_impact.py

# Spatial hotspots
uv run python scripts/analytics/analysis/spatial/analyze_spatial_hotspots.py

# Amenity impact
uv run python scripts/analytics/analysis/amenity/analyze_amenity_impact.py
```

### Data Operations

```bash
# Refresh external data (dry run first)
uv run python scripts/data/download/refresh_external_data.py --dry-run

# Geocode addresses (parallel)
uv run python scripts/data/process/geocode/geocode_addresses.py --parallel --workers 10

# Prepare webapp data
uv run python scripts/prepare_webapp_data.py
```

### Utilities

```bash
# Refresh OneMap token
uv run python scripts/utils/refresh_onemap_token.py

# Data quality report
uv run python scripts/utils/data_quality_report.py --summary

# Validate docs layout
uv run python scripts/tools/validate_docs_layout.py
```

### Development

```bash
# Run tests
uv run pytest

# Run specific test
uv run pytest tests/core/test_config.py

# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix
```

---

**See:** [Documentation Hub](../README.md) for complete documentation index
