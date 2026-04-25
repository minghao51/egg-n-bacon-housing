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
