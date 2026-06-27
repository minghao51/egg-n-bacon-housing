"""Tests for utils/data_loader.py — planning areas and point-in-polygon."""

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


def _make_multi_polygon_geojson():
    def square(name, lon0, lon1, lat0, lat1):
        return {
            "type": "Feature",
            "properties": {"pln_area_n": name},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [lon0, lat0],
                        [lon1, lat0],
                        [lon1, lat1],
                        [lon0, lat1],
                        [lon0, lat0],
                    ]
                ],
            },
        }

    return {
        "type": "FeatureCollection",
        "features": [
            square("AREA_A", 103.80, 103.90, 1.30, 1.40),
            square("AREA_B", 104.00, 104.10, 1.50, 1.60),
        ],
    }


class TestGetPlanningAreasForPoints:
    """Differential tests: the batch spatial join must match the row-wise oracle."""

    def _setup_polygons(self, tmp_path):
        _clear_planning_cache()
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_multi_polygon_geojson())
        )
        data_loader._paths["raw_data_dir"] = geojson_dir

    def test_matches_row_wise_oracle(self, tmp_path):
        self._setup_polygons(tmp_path)
        lats = pd.Series([1.35, 1.55, 1.50, 1.20, 1.38, None])
        lons = pd.Series([103.85, 104.05, 103.85, 103.80, 103.88, 103.80])

        batch = data_loader.get_planning_areas_for_points(lats, lons)
        oracle = pd.Series(
            [
                None
                if (pd.isna(lat) or pd.isna(lon))
                else data_loader.get_planning_area_for_point(lat, lon)
                for lat, lon in zip(lats, lons)
            ]
        )

        assert list(batch.index) == list(lats.index)
        assert batch.tolist() == oracle.tolist()
        assert batch.tolist()[0] == "AREA_A"
        assert batch.tolist()[1] == "AREA_B"
        assert batch.tolist()[2] is None
        assert batch.tolist()[5] is None

    def test_returns_none_when_no_polygons(self, tmp_path):
        _clear_planning_cache()
        data_loader._paths["raw_data_dir"] = tmp_path / "nonexistent"
        result = data_loader.get_planning_areas_for_points(
            pd.Series([1.35, 1.55]), pd.Series([103.85, 104.05])
        )
        assert result.tolist() == [None, None]

    def test_empty_series(self, tmp_path):
        self._setup_polygons(tmp_path)
        result = data_loader.get_planning_areas_for_points(
            pd.Series([], dtype=float), pd.Series([], dtype=float)
        )
        assert len(result) == 0

    def test_all_nan_coords(self, tmp_path):
        self._setup_polygons(tmp_path)
        result = data_loader.get_planning_areas_for_points(
            pd.Series([None, None]), pd.Series([None, None])
        )
        assert result.tolist() == [None, None]
