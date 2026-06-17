"""Tests for utils/data_loader.py."""

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from egg_n_bacon_housing.utils import data_loader

pytestmark = pytest.mark.unit


class _DummySettings:
    """Minimal settings object for data_loader tests."""

    def __init__(self, root: Path):
        root_path = Path(root)
        self.data_dir = root_path
        self.bronze_dir = root_path / "01_bronze"
        self.silver_dir = root_path / "02_silver"
        self.gold_dir = root_path / "03_gold"
        self.platinum_dir = root_path / "04_platinum"
        self.logging = SimpleNamespace(verbose=True)


def test_load_market_summary_prefers_platinum_metrics_path(tmp_path, monkeypatch):
    """Market summary should prefer the new platinum metrics file over legacy path."""
    settings = _DummySettings(tmp_path)
    metrics_dir = settings.platinum_dir / "metrics"
    metrics_dir.mkdir(parents=True)
    legacy_dir = settings.data_dir / "pipeline" / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"marker": "new"}]).to_parquet(
        metrics_dir / "pa_monthly_metrics.parquet",
        index=False,
    )
    pd.DataFrame([{"marker": "legacy"}]).to_parquet(
        legacy_dir / "market_summary.parquet",
        index=False,
    )

    monkeypatch.setattr(data_loader, "settings", settings)
    monkeypatch.setattr(data_loader, "DATA_DIR", settings.data_dir / "pipeline")

    result = data_loader.load_market_summary()

    assert result.loc[0, "marker"] == "new"


def test_load_market_summary_falls_back_to_legacy_path(tmp_path, monkeypatch):
    """Market summary should fall back to the legacy path when new output is missing."""
    settings = _DummySettings(tmp_path)
    legacy_dir = settings.data_dir / "pipeline" / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"marker": "legacy"}]).to_parquet(
        legacy_dir / "market_summary.parquet",
        index=False,
    )

    monkeypatch.setattr(data_loader, "settings", settings)
    monkeypatch.setattr(data_loader, "DATA_DIR", settings.data_dir / "pipeline")

    result = data_loader.load_market_summary()

    assert result.loc[0, "marker"] == "legacy"


def test_read_first_existing_returns_empty_when_no_paths_exist(tmp_path, monkeypatch):
    """Returns empty DataFrame when none of the paths exist."""
    settings = _DummySettings(tmp_path)
    monkeypatch.setattr(data_loader, "settings", settings)

    result = data_loader._read_first_existing(
        tmp_path / "nonexistent1.parquet",
        tmp_path / "nonexistent2.parquet",
    )

    assert result.empty


def test_load_unified_data_falls_back_to_legacy_path(tmp_path, monkeypatch):
    """Should fall back to the legacy unified path when new path is missing."""
    settings = _DummySettings(tmp_path)
    legacy_dir = settings.data_dir / "pipeline" / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"transaction_date": "2023-01-01", "price": 500000}]).to_parquet(
        legacy_dir / "housing_unified.parquet",
        index=False,
    )

    monkeypatch.setattr(data_loader, "settings", settings)
    monkeypatch.setattr(data_loader, "DATA_DIR", settings.data_dir / "pipeline")

    result = data_loader.load_unified_data()

    assert not result.empty
    assert "transaction_date" in result.columns


def test_load_planning_area_metrics_prefers_pa_monthly(tmp_path, monkeypatch):
    """Should prefer pa_monthly_metrics when available."""
    settings = _DummySettings(tmp_path)
    metrics_dir = settings.platinum_dir / "metrics"
    metrics_dir.mkdir(parents=True)

    pd.DataFrame([{"planning_area": "Toa Payoh", "median_price": 500000}]).to_parquet(
        metrics_dir / "pa_monthly_metrics.parquet",
        index=False,
    )

    monkeypatch.setattr(data_loader, "settings", settings)
    monkeypatch.setattr(data_loader, "DATA_DIR", settings.data_dir / "pipeline")

    result = data_loader.load_planning_area_metrics()

    assert not result.empty
    assert "median_price" in result.columns


def test_load_planning_area_metrics_falls_back_to_legacy(tmp_path, monkeypatch):
    """Should fall back to legacy L3 path when platinum file is missing."""
    settings = _DummySettings(tmp_path)
    legacy_dir = settings.data_dir / "pipeline" / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"planning_area": "Toa Payoh", "median_price": 500000}]).to_parquet(
        legacy_dir / "planning_area_metrics.parquet",
        index=False,
    )

    monkeypatch.setattr(data_loader, "settings", settings)
    monkeypatch.setattr(data_loader, "DATA_DIR", settings.data_dir / "pipeline")

    result = data_loader.load_planning_area_metrics()

    assert not result.empty
    assert "median_price" in result.columns
