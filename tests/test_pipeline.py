"""Integration-oriented tests for pipeline.py orchestration."""

import importlib
import sys
import types

import pandas as pd


def _get_pipeline_module():
    return importlib.import_module("egg_n_bacon_housing.pipeline")


def test_build_pipeline_and_execute_minimal_graph(monkeypatch, tmp_path):
    pipeline = _get_pipeline_module()
    config_module = importlib.import_module("egg_n_bacon_housing.config")

    module = types.ModuleType("test_component")
    exec(
        "import pandas as pd\n"
        "def unified_dataset() -> pd.DataFrame:\n"
        "    return pd.DataFrame([{'price': 1}])\n",
        module.__dict__,
    )
    sys.modules[module.__name__] = module

    monkeypatch.setattr(pipeline, "COMPONENTS", [module])
    monkeypatch.setattr(config_module.settings.pipeline, "use_caching", False)

    try:
        dr = pipeline.build_pipeline(data_path=str(tmp_path))
        result = dr.execute(final_vars=["unified_dataset"])

        assert "unified_dataset" in result
        assert isinstance(result["unified_dataset"], pd.DataFrame)
        assert len(result["unified_dataset"]) == 1
    finally:
        sys.modules.pop(module.__name__, None)


def test_run_full_pipeline_uses_default_final_vars(monkeypatch):
    pipeline = _get_pipeline_module()

    captured = {}

    class DummyDriver:
        def execute(self, final_vars):
            captured["final_vars"] = final_vars
            return {name: "ok" for name in final_vars}

    monkeypatch.setattr(pipeline, "build_pipeline", lambda data_path=None: DummyDriver())

    result = pipeline.run_full_pipeline()

    assert captured["final_vars"] == [
        "unified_dataset",
        "dashboard_json",
        "segments_data",
        "price_metrics_by_area",
    ]
    assert set(result.keys()) == set(captured["final_vars"])
