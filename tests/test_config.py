"""Test config module works correctly."""

import sys
import pytest
sys.path.insert(0, "src")

from egg_n_bacon_housing.config import settings


def test_config_loads():
    assert settings.app_name == "egg-n-bacon-housing"
    assert settings.data_dir.name == "data"


def test_medallion_dirs():
    assert settings.bronze_dir.name == "01_bronze"
    assert settings.silver_dir.name == "02_silver"
    assert settings.gold_dir.name == "03_gold"
    assert settings.platinum_dir.name == "04_platinum"


def test_legacy_dirs_removed():
    """Legacy paths removed in favor of layer_dirs."""
    with pytest.raises(AttributeError):
        _ = settings.parquets_dir
    with pytest.raises(AttributeError):
        _ = settings.l0_dir
    with pytest.raises(AttributeError):
        _ = settings.l1_dir
    with pytest.raises(AttributeError):
        _ = settings.l2_dir
    with pytest.raises(AttributeError):
        _ = settings.l3_dir
    with pytest.raises(AttributeError):
        _ = settings.l5_dir


def test_pipeline_cache_settings():
    assert settings.pipeline.use_caching is True
    assert settings.pipeline.parquet_compression == "snappy"