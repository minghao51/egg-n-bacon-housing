"""Test config module works correctly."""

import logging
import sys
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

sys.path.insert(0, "src")

from egg_n_bacon_housing import config as config_module
from egg_n_bacon_housing.config import (
    AFFORDABILITY_THRESHOLD_DEFAULTS,
    LayerDirs,
    MetricsConfig,
    Settings,
    settings,
)

pytestmark = pytest.mark.unit


def test_config_loads():
    assert settings.app_name == "egg-n-bacon-housing"
    assert settings.data_dir.name == "data"


def test_local_env_file_loads_and_process_environment_takes_precedence(tmp_path, monkeypatch):
    """Plain ignored .env files work without an environment wrapper."""
    (tmp_path / ".env").write_text("DATA_PATH=from-file\nAPP_NAME=file-name\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_PATH", "from-process")

    configured = Settings()

    assert configured.data_path == "from-process"
    assert configured.app_name == "file-name"


def test_medallion_dirs():
    assert settings.bronze_dir.name == "01_bronze"
    assert settings.silver_dir.name == "02_silver"
    assert settings.gold_dir.name == "03_gold"
    assert settings.platinum_dir.name == "04_platinum"


def test_resolve_data_path_and_layer_dir(tmp_path):
    resolved = settings.resolve_data_path(tmp_path)

    assert resolved == tmp_path
    assert settings.layer_dir("bronze", tmp_path) == tmp_path / "pipeline" / "01_bronze"


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
    assert settings.pipeline.large_table_validation_policy == "full"
    assert settings.pipeline.max_transaction_age_days == 120


def test_geocoding_coverage_threshold_setting():
    assert 0 <= settings.geocoding.min_coordinate_coverage <= 1
    assert settings.geocoding.coordinate_coverage_policy == "fail"


def test_geocoding_per_type_coverage_defaults():
    """WS16: HDB strict / condo lenient gates; legacy single threshold retained."""
    from egg_n_bacon_housing.config import GeocodingConfig

    cfg = GeocodingConfig()
    assert cfg.min_coordinate_coverage_hdb == 0.7
    assert cfg.min_coordinate_coverage_condo == 0.3
    assert cfg.min_coordinate_coverage == 0.7  # legacy fallback, not removed


def test_geocoding_per_type_coverage_env_override(monkeypatch):
    monkeypatch.setenv("GEOCODING__MIN_COORDINATE_COVERAGE_HDB", "0.8")
    monkeypatch.setenv("GEOCODING__MIN_COORDINATE_COVERAGE_CONDO", "0.2")
    configured = Settings()

    assert configured.geocoding.min_coordinate_coverage_hdb == 0.8
    assert configured.geocoding.min_coordinate_coverage_condo == 0.2


def test_geocoding_per_type_coverage_bounds():
    from egg_n_bacon_housing.config import GeocodingConfig

    with pytest.raises(ValidationError):
        GeocodingConfig(min_coordinate_coverage_hdb=1.5)
    with pytest.raises(ValidationError):
        GeocodingConfig(min_coordinate_coverage_condo=-0.1)


def test_affordability_thresholds_must_be_ordered():
    with pytest.raises(ValueError):
        MetricsConfig(affordability_thresholds={"affordable": 7, "moderate": 5, "expensive": 9})


def test_min_transactions_for_hotspot_default_and_ge_constraint():
    assert MetricsConfig().min_transactions_for_hotspot == 5
    with pytest.raises(ValidationError):
        MetricsConfig(min_transactions_for_hotspot=0)


def test_min_transactions_for_hotspot_env_override(monkeypatch):
    monkeypatch.setenv("METRICS__MIN_TRANSACTIONS_FOR_HOTSPOT", "7")
    assert Settings().metrics.min_transactions_for_hotspot == 7


def test_affordability_defaults_are_copied_from_authoritative_registry():
    first = MetricsConfig()
    second = MetricsConfig()

    assert first.affordability_thresholds == AFFORDABILITY_THRESHOLD_DEFAULTS
    first.affordability_thresholds["affordable"] = 1
    assert second.affordability_thresholds == AFFORDABILITY_THRESHOLD_DEFAULTS


def test_custom_nested_layer_paths_are_preserved(tmp_path):
    from egg_n_bacon_housing.config import Settings

    configured = Settings(
        data_path=str(tmp_path),
        layer_dirs={"bronze": "custom/raw/bronze", "silver": "custom/clean/silver"},
    )
    assert configured.layer_dir("bronze") == tmp_path / "pipeline" / "custom/raw/bronze"


def test_absolute_layer_path_is_supported_by_writer(tmp_path):
    from egg_n_bacon_housing.config import Settings
    from egg_n_bacon_housing.utils.layer_writer import build_writer

    external = tmp_path / "external-gold"
    configured = Settings(data_path=str(tmp_path), layer_dirs={"gold": str(external)})
    writer = build_writer(configured, tmp_path / "pipeline")

    assert (
        writer.resolve_path("features", "gold", tmp_path / "pipeline")
        == external / "features.parquet"
    )


def test_layer_paths_registry_includes_derived_layers(tmp_path):
    configured = Settings(data_path=str(tmp_path))
    paths = configured.layer_paths()
    assert paths["silver"] == tmp_path / "pipeline" / "02_silver"
    assert paths["platinum_metrics"] == tmp_path / "pipeline" / "04_platinum" / "metrics"


def test_tracking_requires_explicit_identity():
    with pytest.raises(ValueError, match="required when tracking_enabled"):
        Settings(tracking_enabled=True)

    configured = Settings(
        tracking_enabled=True,
        tracking_project_id=42,
        tracking_username="pipeline@example.com",
        tracking_environment="production",
    )
    assert configured.tracking_project_id == 42


# ----------------------------------------------------------------------------
# Layer registry consolidation (WS7): one registry, configured LayerDirs
# ----------------------------------------------------------------------------


def test_published_layer_registry_values_resolve_via_settings():
    """Every PUBLISHED_LAYERS value must be a key Settings.layer_paths() resolves."""
    from egg_n_bacon_housing.utils.layer_writer import PUBLISHED_LAYERS

    paths = Settings().layer_paths()
    unresolved = sorted(
        f"{node}->{layer}" for node, layer in PUBLISHED_LAYERS.items() if layer not in paths
    )
    assert unresolved == []


def test_build_writer_threads_configured_layer_dirs(tmp_path):
    """A TrackedWriter from build_writer honors custom LayerDirs (silver -> custom/silver)."""
    from egg_n_bacon_housing.utils.layer_writer import TrackedWriter, build_writer

    configured = Settings(
        data_path=str(tmp_path),
        layer_dirs={"silver": "custom/silver"},
    )
    writer = build_writer(configured, tmp_path / "pipeline")

    assert isinstance(writer, TrackedWriter)
    path = writer.write(pd.DataFrame([{"v": 1}]), "silver_output", "silver")

    assert path == tmp_path / "pipeline" / "custom" / "silver" / "silver_output.parquet"
    assert path.exists()


def test_simple_writer_default_layer_dirs_resolution(tmp_path):
    """SimpleWriter() with no LayerDirs keeps the default medallion layout."""
    from egg_n_bacon_housing.utils.layer_writer import SimpleWriter

    writer = SimpleWriter(tmp_path / "pipeline")

    assert (
        writer.resolve_path("out", "bronze", tmp_path / "pipeline")
        == tmp_path / "pipeline" / "01_bronze" / "out.parquet"
    )
    assert (
        writer.resolve_path("m", "platinum_metrics", tmp_path / "pipeline")
        == tmp_path / "pipeline" / "04_platinum" / "metrics" / "m.parquet"
    )


def test_simple_writer_honors_explicit_layer_dirs(tmp_path):
    from egg_n_bacon_housing.utils.layer_writer import SimpleWriter

    writer = SimpleWriter(tmp_path / "pipeline", layer_dirs=LayerDirs(silver="custom/silver"))

    path = writer.write(pd.DataFrame([{"v": 1}]), "s", "silver")

    assert path == tmp_path / "pipeline" / "custom" / "silver" / "s.parquet"
    assert path.exists()


def test_layer_dirs_warns_once_for_nonstandard_relative_paths(caplog):
    """Relative paths without the data/pipeline prefix warn exactly once."""
    config_module._NONSTANDARD_LAYER_WARNED.clear()
    dirs = LayerDirs(silver="custom/silver")

    with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.config"):
        dirs.relative_path("silver")
        dirs.relative_path("silver")

    warnings = [record for record in caplog.records if "custom/silver" in record.getMessage()]
    assert len(warnings) == 1
    # The warning must not change resolution — still pipeline-root relative.
    assert dirs.relative_path("silver") == Path("custom/silver")


def test_layer_dirs_silent_for_standard_and_absolute_paths(caplog):
    """Default, data/pipeline-prefixed, and absolute paths do not warn."""
    config_module._NONSTANDARD_LAYER_WARNED.clear()

    with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.config"):
        LayerDirs().relative_path("bronze")
        LayerDirs(gold="data/pipeline/03_gold").relative_path("gold")
        LayerDirs(platinum="/absolute/platinum").relative_path("platinum")
        LayerDirs(platinum="data/pipeline/04_platinum").relative_path("platinum_metrics")

    assert caplog.records == []
