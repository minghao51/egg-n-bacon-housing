"""Tests for utils/data_loader.py."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils import data_loader

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _configure_paths(tmp_path):
    """Configure data_loader paths for each test."""
    data_loader.configure(tmp_path)
    yield
    data_loader._paths.clear()


def test_load_market_summary_prefers_platinum_metrics_path(tmp_path):
    """Market summary should prefer the new platinum metrics file over legacy path."""
    metrics_dir = data_loader._get("platinum_dir") / "metrics"
    metrics_dir.mkdir(parents=True)
    legacy_dir = data_loader._get("pipeline_dir") / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"marker": "new"}]).to_parquet(
        metrics_dir / "pa_monthly_metrics.parquet", index=False
    )
    pd.DataFrame([{"marker": "legacy"}]).to_parquet(
        legacy_dir / "market_summary.parquet", index=False
    )

    result = data_loader.load_market_summary()
    assert result.loc[0, "marker"] == "new"


def test_load_market_summary_falls_back_to_legacy_path(tmp_path):
    """Market summary should fall back to the legacy path when new output is missing."""
    legacy_dir = data_loader._get("pipeline_dir") / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"marker": "legacy"}]).to_parquet(
        legacy_dir / "market_summary.parquet", index=False
    )

    result = data_loader.load_market_summary()
    assert result.loc[0, "marker"] == "legacy"


def test_read_first_existing_returns_empty_when_no_paths_exist(tmp_path):
    """Returns empty DataFrame when none of the paths exist."""
    result = data_loader._read_first_existing(
        tmp_path / "nonexistent1.parquet",
        tmp_path / "nonexistent2.parquet",
    )
    assert result.empty


def test_load_unified_data_falls_back_to_legacy_path(tmp_path):
    """Should fall back to the legacy unified path when new path is missing."""
    legacy_dir = data_loader._get("pipeline_dir") / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"transaction_date": "2023-01-01", "price": 500000}]).to_parquet(
        legacy_dir / "housing_unified.parquet", index=False
    )

    result = data_loader.load_unified_data()
    assert not result.empty
    assert "transaction_date" in result.columns


def test_load_planning_area_metrics_prefers_pa_monthly(tmp_path):
    """Should prefer pa_monthly_metrics when available."""
    metrics_dir = data_loader._get("platinum_dir") / "metrics"
    metrics_dir.mkdir(parents=True)

    pd.DataFrame([{"planning_area": "Toa Payoh", "median_price": 500000}]).to_parquet(
        metrics_dir / "pa_monthly_metrics.parquet", index=False
    )

    result = data_loader.load_planning_area_metrics()
    assert not result.empty
    assert "median_price" in result.columns


def test_load_planning_area_metrics_falls_back_to_legacy(tmp_path):
    """Should fall back to legacy L3 path when platinum file is missing."""
    legacy_dir = data_loader._get("pipeline_dir") / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"planning_area": "Toa Payoh", "median_price": 500000}]).to_parquet(
        legacy_dir / "planning_area_metrics.parquet", index=False
    )

    result = data_loader.load_planning_area_metrics()
    assert not result.empty
    assert "median_price" in result.columns
