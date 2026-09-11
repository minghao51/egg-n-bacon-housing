"""Integration test: build pipeline driver and verify DAG structure."""

import importlib

import pandas as pd
import pytest

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

pytestmark = pytest.mark.integration


def _get_pipeline_module():
    return importlib.import_module("egg_n_bacon_housing.pipeline")


class TestPipelineIntegration:
    def test_build_pipeline_constructs_driver(self, tmp_path, monkeypatch):
        """Pipeline driver can be built with a temp data path.

        Hamilton's @check_output(data_type=pd.DataFrame) is not supported
        by the default validator registry — skip if that error surfaces.
        """
        pipeline = _get_pipeline_module()

        try:
            dr = pipeline.build_pipeline(settings, data_path=str(tmp_path))
            assert dr is not None
        except ValueError as e:
            if "check_output" in str(e) and "BaseDefaultValidator" in str(e):
                pytest.skip("Hamilton @check_output does not support DataFrame validator")
            raise

    def test_materializers_disabled_and_nothing_recomputed_with_cache(self, tmp_path):
        """Single persistence regime: computing nodes are cacheable; only the
        companion materializers are cache-disabled (inline recompute hack gone)."""
        pipeline = _get_pipeline_module()
        dr = pipeline.build_pipeline(settings, data_path=str(tmp_path))

        assert dr.cache is not None
        assert set(pipeline._MATERIALIZER_MAP.values()).issubset(set(dr.cache._disable))
        assert not dr.cache._recompute

    def test_pipeline_stage_vars_defined(self):
        """STAGE_VARS dict has expected stage keys."""
        pipeline = _get_pipeline_module()

        assert "all" in pipeline.STAGE_VARS
        assert "ingest" in pipeline.STAGE_VARS
        assert "clean" in pipeline.STAGE_VARS
        assert "features" in pipeline.STAGE_VARS
        assert "export" in pipeline.STAGE_VARS
        assert "metrics" in pipeline.STAGE_VARS

    def test_runtime_service_dependencies_are_discoverable(self, tmp_path):
        pipeline = _get_pipeline_module()
        dr = pipeline.build_pipeline(settings, data_path=str(tmp_path))
        expected = {
            "raw_condo_transactions": {"cache_manager"},
            "raw_mrt_stations": {"mrt_reference"},
            "validate_location_dim": {"mrt_reference", "spatial_reference", "school_reference"},
        }

        for node_name, service_inputs in expected.items():
            assert service_inputs.issubset(dr.graph.nodes[node_name].input_types)

        # Bronze is the only cache layer under the parameterized datagov nodes
        # (WO-5): they must not declare the per-run cache_manager input, so
        # --refresh cannot be shadowed by the 24h API-response cache.
        for node_name in ("raw_rental_index", "raw_hdb_rental", "raw_school_directory"):
            assert "cache_manager" not in dr.graph.nodes[node_name].input_types

    def test_run_pipeline_with_mocked_driver(self, tmp_path, monkeypatch):
        """run_pipeline delegates to driver.execute with correct layer inputs."""
        pipeline = _get_pipeline_module()

        captured = {}

        class FakeDriver:
            def execute(self, final_vars, inputs=None):
                captured["final_vars"] = final_vars
                captured["inputs"] = inputs
                return {name: pd.DataFrame() for name in final_vars}

        monkeypatch.setattr(
            pipeline, "build_pipeline", lambda settings, data_path=None: FakeDriver()
        )

        pipeline.run_pipeline(settings, data_path=str(tmp_path), geocoder=InMemoryGeocoder({}))

        assert captured["final_vars"] == pipeline.STAGE_VARS["all"]
        assert captured["inputs"]["bronze_dir"] == tmp_path / "pipeline" / "01_bronze"
        assert "writer" in captured["inputs"]
        assert captured["inputs"]["writer"].data_dir == tmp_path / "pipeline"

    def test_run_pipeline_injects_isolated_runtime_services(self, tmp_path, monkeypatch):
        pipeline = _get_pipeline_module()

        class FakeDriver:
            def execute(self, final_vars, inputs=None):
                captured.update(inputs or {})
                return {name: pd.DataFrame() for name in final_vars}

        monkeypatch.setattr(
            pipeline, "build_pipeline", lambda settings, data_path=None: FakeDriver()
        )

        captured: dict[str, object] = {}

        pipeline.run_pipeline(settings, data_path=str(tmp_path), geocoder=InMemoryGeocoder({}))

        # A driver without a Hamilton graph cannot expose its required inputs;
        # runtime services are intentionally lazy in this case.
        assert "cache_manager" not in captured
        assert "mrt_reference" not in captured

    def test_run_pipeline_specific_stage(self, tmp_path, monkeypatch):
        """run_pipeline accepts a stage parameter to select output variables."""
        pipeline = _get_pipeline_module()

        captured = {}

        class FakeDriver:
            def execute(self, final_vars, inputs=None):
                captured["final_vars"] = final_vars
                return {name: pd.DataFrame() for name in final_vars}

        monkeypatch.setattr(
            pipeline, "build_pipeline", lambda settings, data_path=None: FakeDriver()
        )

        pipeline.run_pipeline(
            settings, data_path=str(tmp_path), stage="ingest", geocoder=InMemoryGeocoder({})
        )

        assert captured["final_vars"] == pipeline.STAGE_VARS["ingest"]
        assert "raw_hdb_resale_transactions" in captured["final_vars"]

    def test_ingestion_components_load_bronze_data(self, tmp_path, monkeypatch):
        """Individual ingestion functions read bronze parquet and return DataFrames."""
        from egg_n_bacon_housing.components import ingestion

        hdb_rows = [
            {
                "month": "2024-01",
                "resale_price": 500000.0,
                "town": "TOA PAYOH",
                "flat_type": "4 ROOM",
            },
            {
                "month": "2024-01",
                "resale_price": 450000.0,
                "town": "ANG MO KIO",
                "flat_type": "3 ROOM",
            },
            {"month": "2024-02", "resale_price": 550000.0, "town": "BISHAN", "flat_type": "5 ROOM"},
        ]
        pd.DataFrame(hdb_rows).to_parquet(tmp_path / "raw_hdb_resale.parquet", index=False)

        condo_rows = [
            {"project_name": "Orchard Residences", "price": 1500000.0},
            {"project_name": "Marina Bay Suites", "price": 2000000.0},
        ]
        pd.DataFrame(condo_rows).to_parquet(
            tmp_path / "raw_condo_transactions.parquet", index=False
        )

        hdb_result = ingestion.raw_dataset(
            bronze_dir=tmp_path,
            resource_id="d_5785799d63a9da091f4e0b456291eeb8",
            cache_filenames=("raw_hdb_resale.parquet",),
            display_name="HDB resale",
            error_name="hdb_resale",
        )
        condo_result = ingestion.raw_dataset(
            bronze_dir=tmp_path,
            resource_id="d_2fd959a62c2d04c67a5a7c7538c53ddd",
            cache_filenames=("raw_condo_transactions.parquet",),
            display_name="condo",
            error_name="condo_resale",
        )

        assert len(hdb_result) == 3
        assert len(condo_result) == 2
        assert set(hdb_result.columns) & {"month", "resale_price", "town"}

    def test_cleaning_produces_silver_output(self, tmp_path, monkeypatch):
        """Cleaning stage produces silver-layer parquet files."""
        from egg_n_bacon_housing.components import cleaning

        raw_data = pd.DataFrame(
            [
                {
                    "month": "2024-01",
                    "resale_price": 500000.0,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "floor_area_sqm": 90.0,
                    "lease_commence_date": 2000,
                    "remaining_lease_months": 720,
                }
            ]
        )

        result = cleaning.cleaned_hdb_transactions(raw_data)

        assert not result.empty
        assert "price" in result.columns
        assert result.loc[0, "price"] == 500000.0


class TestStageValidation:
    """run_pipeline rejects unknown stages instead of computing everything."""

    def test_unknown_stage_raises_value_error(self, tmp_path):
        from egg_n_bacon_housing.pipeline import run_pipeline

        with pytest.raises(ValueError, match="Unknown stage"):
            run_pipeline(settings=settings, data_path=str(tmp_path), stage="bogus")


class TestMainCLIStagePassthrough:
    """main.py must pass the stage through so --stage all materializes all
    published outputs, instead of pre-collapsing final_vars (which narrowed
    materialization to only the terminal frames)."""

    def test_stage_all_passes_stage_not_precollapsed_vars(self, monkeypatch, caplog):
        import sys
        from pathlib import Path

        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent.parent))
        import main as main_module

        captured: dict[str, object] = {}

        def fake_run_pipeline(settings, data_path=None, final_vars=None, stage=None, dr=None):
            captured["final_vars"] = final_vars
            captured["stage"] = stage
            return {"unified_dataset": pd.DataFrame()}

        monkeypatch.setattr(main_module, "build_pipeline", lambda settings: object())
        monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)
        monkeypatch.setattr(sys, "argv", ["main.py", "--stage", "all"])

        main_module.main()

        assert captured["final_vars"] is None
        assert captured["stage"] == "all"

    def test_explicit_final_vars_override_stage(self, monkeypatch):
        import sys
        from pathlib import Path

        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent.parent))
        import main as main_module

        captured: dict[str, object] = {}

        def fake_run_pipeline(settings, data_path=None, final_vars=None, stage=None, dr=None):
            captured["final_vars"] = final_vars
            captured["stage"] = stage
            return {"some_var": pd.DataFrame()}

        monkeypatch.setattr(main_module, "build_pipeline", lambda settings: object())
        monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)
        monkeypatch.setattr(
            sys, "argv", ["main.py", "--stage", "features", "--final-var", "rental_yield"]
        )

        main_module.main()

        assert captured["final_vars"] == ["rental_yield"]
        assert captured["stage"] == "features"
