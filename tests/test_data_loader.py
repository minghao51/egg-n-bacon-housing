"""Tests for utils/data_loader.py."""

from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from egg_n_bacon_housing.utils import data_loader


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


def test_transaction_loader_filters_unified_features_by_property_type(tmp_path, monkeypatch):
    """L2 loader should filter unified features to the requested property type."""
    settings = _DummySettings(tmp_path)
    settings.gold_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {"property_type": "hdb", "town": "TOA PAYOH"},
            {"property_type": "condo", "town": "ORCHARD"},
            {"property_type": "ec", "town": "TAMPINES"},
        ]
    ).to_parquet(settings.gold_dir / "unified_features.parquet", index=False)

    monkeypatch.setattr(data_loader, "settings", settings)

    loader = data_loader.TransactionLoader()
    condo_rows = loader.load_transaction("condo", stage="L2")

    assert len(condo_rows) == 1
    assert condo_rows.iloc[0]["property_type"] == "condo"


def test_load_market_summary_prefers_platinum_metrics_path(tmp_path, monkeypatch):
    """Market summary should prefer the new platinum metrics file over legacy path."""
    settings = _DummySettings(tmp_path)
    metrics_dir = settings.platinum_dir / "metrics"
    metrics_dir.mkdir(parents=True)
    legacy_dir = settings.data_dir / "pipeline" / "L3"
    legacy_dir.mkdir(parents=True)

    pd.DataFrame([{"marker": "new"}]).to_parquet(
        metrics_dir / "L5_price_metrics_by_area.parquet",
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


def test_filter_by_property_type_returns_df_unchanged_when_no_column(tmp_path, monkeypatch):
    """Returns df unchanged when property_type column is absent."""
    settings = _DummySettings(tmp_path)
    monkeypatch.setattr(data_loader, "settings", settings)

    loader = data_loader.TransactionLoader()
    df = pd.DataFrame([{"town": "TOA PAYOH"}, {"town": "ORCHARD"}])

    result = loader._filter_by_property_type(df, data_loader.PropertyType.HDB)

    assert len(result) == 2


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


def test_load_planning_area_metrics_merges_price_and_affordability(tmp_path, monkeypatch):
    """Should merge price and affordability datasets when both exist."""
    settings = _DummySettings(tmp_path)
    metrics_dir = settings.platinum_dir / "metrics"
    metrics_dir.mkdir(parents=True)

    pd.DataFrame([{"planning_area": "Toa Payoh", "median_price": 500000}]).to_parquet(
        metrics_dir / "L5_price_metrics_by_area.parquet",
        index=False,
    )
    pd.DataFrame([{"planning_area": "Toa Payoh", "affordability_ratio": 0.6}]).to_parquet(
        metrics_dir / "L5_affordability_by_area.parquet",
        index=False,
    )

    monkeypatch.setattr(data_loader, "settings", settings)
    monkeypatch.setattr(data_loader, "DATA_DIR", settings.data_dir / "pipeline")

    result = data_loader.load_planning_area_metrics()

    assert not result.empty
    assert "median_price" in result.columns
    assert "affordability_ratio" in result.columns


def test_load_planning_area_metrics_returns_single_file_when_one_missing(tmp_path, monkeypatch):
    """Should return whichever file exists when only one platinum file is present."""
    settings = _DummySettings(tmp_path)
    metrics_dir = settings.platinum_dir / "metrics"
    metrics_dir.mkdir(parents=True)

    pd.DataFrame([{"planning_area": "Toa Payoh", "median_price": 500000}]).to_parquet(
        metrics_dir / "L5_price_metrics_by_area.parquet",
        index=False,
    )

    monkeypatch.setattr(data_loader, "settings", settings)
    monkeypatch.setattr(data_loader, "DATA_DIR", settings.data_dir / "pipeline")

    result = data_loader.load_planning_area_metrics()

    assert not result.empty
    assert "median_price" in result.columns
