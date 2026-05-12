# Testing Guide

**Last Updated**: 2026-05-12 | **Status**: Active

## Overview

This repository uses `pytest` for core pipeline coverage under `tests/`.

Current test files:

- `tests/test_ingestion.py`
- `tests/test_cleaning_validation.py`
- `tests/test_features.py`
- `tests/test_export.py`
- `tests/test_metrics.py`
- `tests/test_datagovsg.py`
- `tests/test_onemap.py`
- `tests/test_cache.py`
- `tests/test_data_loader.py`
- `tests/test_config.py`
- `tests/test_pipeline.py`

## Run Tests

```bash
# Full suite with configured coverage reports
uv run pytest

# Run one file
uv run pytest tests/test_ingestion.py -v

# Run targeted tests
uv run pytest tests/test_datagovsg.py tests/test_onemap.py -v
```

## Coverage and CI Gates

- Pytest coverage is configured in `pyproject.toml`.
- CI enforces a minimum coverage floor for core component modules using:
  - `scripts/tools/check_core_coverage.py`

Run locally:

```bash
uv run pytest tests/ --cov=egg_n_bacon_housing --cov-report=xml
uv run python scripts/tools/check_core_coverage.py --coverage-xml coverage.xml --min-coverage 60
```

## Quality Checks

```bash
# Lint + format check
uv run ruff format --check src scripts tests
uv run ruff check src scripts tests

# Type checking
uv run mypy src tests
```

## Notes

- Core pipeline is validated via Hamilton component tests (`01_ingestion` through `05_metrics`).
- Analytics standalone scripts under `src/egg_n_bacon_housing/analytics/` are currently out of strict test gating.
