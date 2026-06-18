"""Integration-oriented tests for pipeline.py orchestration."""

import importlib
import sys
import types

import pandas as pd
import pytest

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

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
