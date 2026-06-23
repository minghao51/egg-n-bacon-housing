"""Tests for utils/data_loader.py — planning areas, CSVLoader, and point-in-polygon."""

import json

import pandas as pd
import pytest

from egg_n_bacon_housing.utils import data_loader

pytestmark = pytest.mark.unit


def _clear_planning_cache():
    data_loader._load_planning_areas_raw.cache_clear()


def _make_geojson(area_name="TEST_AREA"):
    polygon = {
        "type": "Polygon",
        "coordinates": [[[103.8, 1.3], [103.9, 1.3], [103.9, 1.4], [103.8, 1.4], [103.8, 1.3]]],
    }
    return {
        "type": "FeatureCollection",
        "features": [{"properties": {"pln_area_n": area_name}, "geometry": polygon}],
    }


@pytest.fixture(autouse=True)
def _configure_paths(tmp_path):
    """Configure data_loader paths for each test."""
    data_loader.configure(tmp_path)
    yield
    data_loader._paths.clear()


class TestLoadPlanningAreas:
    def test_loads_from_geojson(self, tmp_path):
        _clear_planning_cache()
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson())
        )
        data_loader._paths["raw_data_dir"] = geojson_dir

        result = data_loader.load_planning_areas()
        assert len(result) == 1
        assert result[0]["name"] == "TEST_AREA"

    def test_missing_geojson_returns_empty(self, tmp_path):
        _clear_planning_cache()
        data_loader._paths["raw_data_dir"] = tmp_path / "nonexistent"

        result = data_loader.load_planning_areas()
        assert result == []


class TestGetPlanningAreaForPoint:
    def test_point_inside_polygon(self, tmp_path):
        _clear_planning_cache()
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson("INSIDE_AREA"))
        )
        data_loader._paths["raw_data_dir"] = geojson_dir

        result = data_loader.get_planning_area_for_point(1.35, 103.85)
        assert result == "INSIDE_AREA"

    def test_point_outside_all_polygons(self, tmp_path):
        _clear_planning_cache()
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson("SMALL_AREA"))
        )
        data_loader._paths["raw_data_dir"] = geojson_dir

        result = data_loader.get_planning_area_for_point(1.5, 104.0)
        assert result is None

    def test_uses_lon_lat_order_for_point(self, tmp_path):
        _clear_planning_cache()
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson("LON_LAT_TEST"))
        )
        data_loader._paths["raw_data_dir"] = geojson_dir

        result = data_loader.get_planning_area_for_point(lat=1.35, lon=103.85)
        assert result == "LON_LAT_TEST"

    def test_reconfigure_invalidates_cached_planning_areas(self, tmp_path_factory):
        _clear_planning_cache()
        first_root = tmp_path_factory.mktemp("planning-a")
        second_root = tmp_path_factory.mktemp("planning-b")

        first_geojson_dir = first_root / "manual" / "geojsons"
        second_geojson_dir = second_root / "manual" / "geojsons"
        first_geojson_dir.mkdir(parents=True)
        second_geojson_dir.mkdir(parents=True)

        (first_geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson("AREA_ONE"))
        )
        (second_geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson("AREA_TWO"))
        )

        data_loader.configure(first_root)
        assert data_loader.load_planning_areas()[0]["name"] == "AREA_ONE"

        data_loader.configure(second_root)
        assert data_loader.load_planning_areas()[0]["name"] == "AREA_TWO"


class TestCSVLoader:
    def test_load_csv_reads_existing_file(self, tmp_path):
        csv_dir = tmp_path / "data"
        csv_dir.mkdir()
        pd.DataFrame([{"col": "val"}]).to_csv(csv_dir / "test.csv", index=False)

        loader = data_loader.CSVLoader(base_path=csv_dir)
        result = loader.load_csv("test.csv")
        assert len(result) == 1
        assert result.iloc[0]["col"] == "val"

    def test_load_csv_returns_empty_for_missing(self, tmp_path):
        loader = data_loader.CSVLoader(base_path=tmp_path)
        result = loader.load_csv("nonexistent.csv")
        assert result.empty

    def test_load_ura_data_reads_all_files(self, tmp_path):
        ura_dir = tmp_path / "csv" / "ura"
        ura_dir.mkdir(parents=True)

        for name in ["ec", "condo", "condo_rental", "ec_rental"]:
            pd.DataFrame([{"type": name}]).to_csv(ura_dir / f"{name}.csv", index=False)

        loader = data_loader.CSVLoader(base_path=tmp_path)
        result = loader.load_ura_data()

        assert set(result.keys()) == {"ec", "condo", "condo_rental", "ec_rental"}
        assert result["ec"].iloc[0]["type"] == "ec"

    def test_load_ura_data_returns_partial(self, tmp_path):
        ura_dir = tmp_path / "csv" / "ura"
        ura_dir.mkdir(parents=True)
        pd.DataFrame([{"type": "ec"}]).to_csv(ura_dir / "ec.csv", index=False)

        loader = data_loader.CSVLoader(base_path=tmp_path)
        result = loader.load_ura_data()

        assert "ec" in result
        assert "condo" not in result

    def test_load_hdb_resale_combines_csvs(self, tmp_path):
        resale_dir = tmp_path / "csv" / "ResaleFlatPrices"
        resale_dir.mkdir(parents=True)

        pd.DataFrame([{"town": "A"}]).to_csv(resale_dir / "f1.csv", index=False)
        pd.DataFrame([{"town": "B"}]).to_csv(resale_dir / "f2.csv", index=False)

        loader = data_loader.CSVLoader(base_path=tmp_path)
        result = loader.load_hdb_resale()

        assert len(result) == 2

    def test_load_hdb_resale_empty_dir(self, tmp_path):
        resale_dir = tmp_path / "csv" / "ResaleFlatPrices"
        resale_dir.mkdir(parents=True)

        loader = data_loader.CSVLoader(base_path=tmp_path)
        result = loader.load_hdb_resale()
        assert result.empty

    def test_load_hdb_resale_missing_dir(self, tmp_path):
        loader = data_loader.CSVLoader(base_path=tmp_path)
        result = loader.load_hdb_resale()
        assert result.empty
