"""Tests for utils/data_loader.py — planning areas, CSVLoader, and point-in-polygon."""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from egg_n_bacon_housing.utils import data_loader

pytestmark = pytest.mark.unit


class _DummySettings:
    def __init__(self, root: Path):
        root_path = Path(root)
        self.data_dir = root_path
        self.bronze_dir = root_path / "01_bronze"
        self.silver_dir = root_path / "02_silver"
        self.gold_dir = root_path / "03_gold"
        self.platinum_dir = root_path / "04_platinum"
        self.logging = SimpleNamespace(verbose=True)


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


class TestLoadPlanningAreas:
    def test_loads_from_geojson(self, tmp_path, monkeypatch):
        _clear_planning_cache()
        monkeypatch.setattr(data_loader, "settings", _DummySettings(tmp_path))
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson())
        )
        monkeypatch.setattr(data_loader, "RAW_DATA_DIR", geojson_dir)

        result = data_loader.load_planning_areas()
        assert len(result) == 1
        assert result[0]["name"] == "TEST_AREA"

    def test_missing_geojson_returns_empty(self, tmp_path, monkeypatch):
        _clear_planning_cache()
        monkeypatch.setattr(data_loader, "settings", _DummySettings(tmp_path))
        missing_dir = tmp_path / "nonexistent"
        monkeypatch.setattr(data_loader, "RAW_DATA_DIR", missing_dir)

        result = data_loader.load_planning_areas()
        assert result == []


class TestGetPlanningAreaForPoint:
    def test_point_inside_polygon(self, tmp_path, monkeypatch):
        _clear_planning_cache()
        monkeypatch.setattr(data_loader, "settings", _DummySettings(tmp_path))
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson("INSIDE_AREA"))
        )
        monkeypatch.setattr(data_loader, "RAW_DATA_DIR", geojson_dir)

        result = data_loader.get_planning_area_for_point(1.35, 103.85)
        assert result == "INSIDE_AREA"

    def test_point_outside_all_polygons(self, tmp_path, monkeypatch):
        _clear_planning_cache()
        monkeypatch.setattr(data_loader, "settings", _DummySettings(tmp_path))
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson("SMALL_AREA"))
        )
        monkeypatch.setattr(data_loader, "RAW_DATA_DIR", geojson_dir)

        result = data_loader.get_planning_area_for_point(1.5, 104.0)
        assert result is None

    def test_uses_lon_lat_order_for_point(self, tmp_path, monkeypatch):
        _clear_planning_cache()
        monkeypatch.setattr(data_loader, "settings", _DummySettings(tmp_path))
        geojson_dir = tmp_path / "geojsons"
        geojson_dir.mkdir(parents=True)
        (geojson_dir / "onemap_planning_area_polygon.geojson").write_text(
            json.dumps(_make_geojson("LON_LAT_TEST"))
        )
        monkeypatch.setattr(data_loader, "RAW_DATA_DIR", geojson_dir)

        result = data_loader.get_planning_area_for_point(lat=1.35, lon=103.85)
        assert result == "LON_LAT_TEST"


class TestCSVLoader:
    def test_load_csv_reads_existing_file(self, tmp_path):
        csv_dir = tmp_path / "data"
        csv_dir.mkdir()
        pd.DataFrame([{"col": "val"}]).to_csv(csv_dir / "test.csv", index=False)

        loader = data_loader.CSVLoader(base_path=csv_dir)
        result = loader.load_csv("test.csv")
        assert len(result) == 1
        assert result.iloc[0]["col"] == "val"

    def test_load_csv_returns_empty_for_missing(self, tmp_path, monkeypatch):
        settings = _DummySettings(tmp_path)
        monkeypatch.setattr(data_loader, "settings", settings)

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

    def test_load_hdb_resale_empty_dir(self, tmp_path, monkeypatch):
        settings = _DummySettings(tmp_path)
        monkeypatch.setattr(data_loader, "settings", settings)

        resale_dir = tmp_path / "csv" / "ResaleFlatPrices"
        resale_dir.mkdir(parents=True)

        loader = data_loader.CSVLoader(base_path=tmp_path)
        result = loader.load_hdb_resale()
        assert result.empty

    def test_load_hdb_resale_missing_dir(self, tmp_path, monkeypatch):
        settings = _DummySettings(tmp_path)
        monkeypatch.setattr(data_loader, "settings", settings)

        loader = data_loader.CSVLoader(base_path=tmp_path)
        result = loader.load_hdb_resale()
        assert result.empty
