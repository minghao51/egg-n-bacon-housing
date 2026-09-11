"""Integration-oriented tests for pipeline.py orchestration."""

import importlib
import sys
import types

import pandas as pd
import pytest

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder
from egg_n_bacon_housing.utils.layer_writer import SimpleWriter, TrackedWriter

pytestmark = pytest.mark.integration


def _get_pipeline_module():
    return importlib.import_module("egg_n_bacon_housing.pipeline")


def test_build_pipeline_and_execute_minimal_graph(monkeypatch, tmp_path):
    pipeline = _get_pipeline_module()

    module = types.ModuleType("test_component")
    exec(
        "import pandas as pd\n"
        "from pathlib import Path\n"
        "def test_output(platinum_dir: Path) -> pd.DataFrame:\n"
        "    return pd.DataFrame([{'price': 1}])\n",
        module.__dict__,
    )
    sys.modules[module.__name__] = module

    monkeypatch.setattr(pipeline, "_STAGE_MODULES", [module])
    monkeypatch.setattr(settings.pipeline, "use_caching", False)

    try:
        dr = pipeline.build_pipeline(settings, data_path=str(tmp_path))
        result = dr.execute(
            final_vars=["test_output"],
            inputs={"platinum_dir": tmp_path / "platinum"},
        )

        assert "test_output" in result
        assert isinstance(result["test_output"], pd.DataFrame)
        assert len(result["test_output"]) == 1
    finally:
        sys.modules.pop(module.__name__, None)


def test_run_pipeline_defaults_to_all_stage(monkeypatch):
    pipeline = _get_pipeline_module()

    captured = {}

    class DummyDriver:
        def execute(self, final_vars, inputs=None):
            captured["final_vars"] = final_vars
            captured["inputs"] = inputs
            return {name: "ok" for name in final_vars}

    monkeypatch.setattr(pipeline, "build_pipeline", lambda settings, data_path=None: DummyDriver())

    result = pipeline.run_pipeline(settings, geocoder=InMemoryGeocoder({}))

    assert captured["final_vars"] == pipeline.STAGE_VARS["all"]
    assert set(result.keys()) == set(captured["final_vars"])


def test_run_pipeline_injects_hotspot_volume_floor(monkeypatch):
    """settings.metrics.min_transactions_for_hotspot reaches the driver inputs."""
    pipeline = _get_pipeline_module()
    captured = {}

    class DummyDriver:
        def execute(self, final_vars, inputs=None):
            captured["inputs"] = inputs or {}
            return {name: "ok" for name in final_vars}

    monkeypatch.setattr(pipeline, "build_pipeline", lambda settings, data_path=None: DummyDriver())
    monkeypatch.setattr(settings.metrics, "min_transactions_for_hotspot", 7)

    pipeline.run_pipeline(settings, geocoder=InMemoryGeocoder({}))

    assert captured["inputs"]["min_transactions_for_hotspot"] == 7


def test_run_pipeline_injects_per_type_coordinate_coverage(monkeypatch):
    """WS16 rider: per-property-type coverage gates reach the driver inputs."""
    pipeline = _get_pipeline_module()
    captured = {}

    class DummyDriver:
        def execute(self, final_vars, inputs=None):
            captured["inputs"] = inputs or {}
            return {name: "ok" for name in final_vars}

    monkeypatch.setattr(pipeline, "build_pipeline", lambda settings, data_path=None: DummyDriver())
    monkeypatch.setattr(settings.geocoding, "min_coordinate_coverage_hdb", 0.9)
    monkeypatch.setattr(settings.geocoding, "min_coordinate_coverage_condo", 0.2)

    pipeline.run_pipeline(settings, geocoder=InMemoryGeocoder({}))

    assert captured["inputs"]["min_coordinate_coverage_hdb"] == 0.9
    assert captured["inputs"]["min_coordinate_coverage_condo"] == 0.2


def test_run_pipeline_injects_school_reference(monkeypatch, tmp_path):
    """WO-11: location_dim reads school tiers through the school_reference DI
    seam (owner decision — rewired instead of deleted)."""
    pipeline = _get_pipeline_module()
    captured = {}

    class DummyDriver:
        def execute(self, final_vars, inputs=None):
            captured["inputs"] = inputs or {}
            return {name: "ok" for name in final_vars}

    monkeypatch.setattr(pipeline, "build_pipeline", lambda settings, data_path=None: DummyDriver())

    pipeline.run_pipeline(settings, data_path=str(tmp_path), geocoder=InMemoryGeocoder({}))

    assert "school_reference" not in captured["inputs"]


def test_run_pipeline_injects_manual_dir(monkeypatch, tmp_path):
    """RuntimePaths.manual_dir is injected so ingestion nodes never traverse
    the filesystem (bronze_dir.parent.parent / "manual" is banned)."""
    pipeline = _get_pipeline_module()
    captured = {}

    class DummyDriver:
        def execute(self, final_vars, inputs=None):
            captured["inputs"] = inputs or {}
            return {name: "ok" for name in final_vars}

    monkeypatch.setattr(pipeline, "build_pipeline", lambda settings, data_path=None: DummyDriver())

    pipeline.run_pipeline(settings, data_path=str(tmp_path), geocoder=InMemoryGeocoder({}))

    assert captured["inputs"]["manual_dir"] == tmp_path / "manual"


# ----------------------------------------------------------------------------
# Materializer wiring invariant (single persistence regime)
# ----------------------------------------------------------------------------


def test_every_published_output_has_exactly_one_materializer():
    """_MATERIALIZED_NAMES == set(_PUBLISHED_LAYERS): one materializer each."""
    pipeline = _get_pipeline_module()

    assert set(pipeline._MATERIALIZER_MAP) == set(pipeline._PUBLISHED_LAYERS)
    assert len(pipeline._MATERIALIZER_MAP) == len(pipeline._PUBLISHED_LAYERS)


def test_persisted_vars_recompute_hack_is_gone():
    """The transitional recompute override must not come back."""
    pipeline = _get_pipeline_module()

    assert not hasattr(pipeline, "_PERSISTED_VARS")


def test_cache_disables_materializers_and_recomputes_nothing(monkeypatch, tmp_path):
    """Computing nodes are cacheable; only their materializer companions are not."""
    pipeline = _get_pipeline_module()
    monkeypatch.setattr(settings.pipeline, "use_caching", True)

    dr = pipeline.build_pipeline(settings, data_path=str(tmp_path))

    assert dr.cache is not None
    assert set(pipeline._MATERIALIZER_MAP.values()).issubset(set(dr.cache._disable))
    assert not dr.cache._recompute


# ---------------------------------------------------------------------------
# Empty-frame persistence (decision D2a: 0-row schema-only parquet, no skip)
# ---------------------------------------------------------------------------


def test_simple_writer_persists_empty_dataframe_with_columns(tmp_path):
    """An empty (0-row) frame must persist as a schema-only parquet file."""
    writer = SimpleWriter(tmp_path)
    df = pd.DataFrame({"a": pd.Series([], dtype="int64"), "b": pd.Series([], dtype="object")})

    path = writer.write(df, "empty_output", "platinum")

    assert path.exists()
    back = pd.read_parquet(path)
    assert len(back) == 0
    assert list(back.columns) == ["a", "b"]


def test_simple_writer_columnless_dataframe_does_not_crash(tmp_path):
    writer = SimpleWriter(tmp_path)

    path = writer.write(pd.DataFrame(), "columnless_output", "silver")

    assert path.exists()
    assert len(pd.read_parquet(path)) == 0


def test_tracked_writer_persists_empty_dataframe_and_records_quality(monkeypatch, tmp_path):
    """Empty writes persist AND still record a 0-row quality snapshot."""
    import egg_n_bacon_housing.utils.data_quality as data_quality

    recorded = []

    def spy_record(df, **kwargs):
        recorded.append((kwargs["dataset_name"], len(df)))

    monkeypatch.setattr(data_quality, "record_dataframe_quality", spy_record)

    writer = TrackedWriter(
        data_dir=tmp_path / "pipeline",
        settings=settings,
        quality_db_path=tmp_path / "quality.db",
    )
    df = pd.DataFrame({"a": pd.Series([], dtype="int64")})

    path = writer.write(df, "empty_tracked", "gold")

    assert path.exists()
    back = pd.read_parquet(path)
    assert len(back) == 0
    assert list(back.columns) == ["a"]
    assert recorded == [("empty_tracked", 0)]


def test_tracked_writer_columnless_dataframe_does_not_crash(monkeypatch, tmp_path):
    import egg_n_bacon_housing.utils.data_quality as data_quality

    monkeypatch.setattr(data_quality, "record_dataframe_quality", lambda df, **kwargs: None)

    writer = TrackedWriter(
        data_dir=tmp_path / "pipeline",
        settings=settings,
        quality_db_path=tmp_path / "quality.db",
    )

    path = writer.write(pd.DataFrame(), "columnless_tracked", "gold")

    assert path.exists()
    assert len(pd.read_parquet(path)) == 0


# ----------------------------------------------------------------------------
# final_vars contract
# ----------------------------------------------------------------------------


def test_run_pipeline_raises_on_missing_final_var(monkeypatch):
    pipeline = _get_pipeline_module()

    class DummyDriver:
        def execute(self, final_vars, inputs=None):
            return {name: "ok" for name in final_vars if name != "missing_var"}

    monkeypatch.setattr(pipeline, "build_pipeline", lambda settings, data_path=None: DummyDriver())

    with pytest.raises(RuntimeError, match="missing_var"):
        pipeline.run_pipeline(
            settings,
            final_vars=["present_var", "missing_var"],
            geocoder=InMemoryGeocoder({}),
        )


def test_run_pipeline_rejects_unknown_stage(monkeypatch):
    pipeline = _get_pipeline_module()

    monkeypatch.setattr(pipeline, "build_pipeline", lambda settings, data_path=None: None)

    with pytest.raises(ValueError, match="Unknown stage"):
        pipeline.run_pipeline(settings, stage="bogus_stage", geocoder=InMemoryGeocoder({}))
