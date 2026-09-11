"""Tests for immutable per-run runtime paths and reference repositories."""

import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest

from egg_n_bacon_housing.adapters import datagovsg, onemap, ura
from egg_n_bacon_housing.config import LayerDirs, Settings
from egg_n_bacon_housing.utils.cache import CacheManager
from egg_n_bacon_housing.utils.data_loader import SpatialReferenceRepository
from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository
from egg_n_bacon_housing.utils.runtime import RuntimePaths
from egg_n_bacon_housing.utils.school_features import SchoolReferenceRepository

pytestmark = pytest.mark.unit


def _write_mrt(root, code, station):
    root.mkdir(parents=True, exist_ok=True)
    (root / "mrt_lines.json").write_text(json.dumps({code: {"name": f"{code} Line", "tier": 1}}))
    (root / "mrt_stations.json").write_text(json.dumps({station: [code]}))


def _write_planning_area(root, name):
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {"pln_area_n": name},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[103.8, 1.3], [103.9, 1.3], [103.9, 1.4], [103.8, 1.4], [103.8, 1.3]]
                    ],
                },
            }
        ],
    }
    (root / "onemap_planning_area_polygon.geojson").write_text(json.dumps(payload))


def test_runtime_paths_respect_absolute_bronze_override(tmp_path):
    bronze = tmp_path / "custom" / "bronze"
    settings = Settings(layer_dirs=LayerDirs(bronze=str(bronze)))

    paths = RuntimePaths.from_settings(settings, tmp_path / "run")

    assert paths.data_dir == tmp_path / "run"
    assert paths.bronze_dir == bronze
    assert paths.external_dir == bronze / "external"
    assert paths.manual_dir == tmp_path / "run" / "manual"
    assert paths.api_cache_dir == tmp_path / "run" / "cache"


def test_mrt_repositories_are_isolated_and_concurrent(tmp_path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    _write_mrt(root_a, "AAA", "ALPHA")
    _write_mrt(root_b, "BBB", "BETA")
    repositories = [MrtReferenceRepository(root_a), MrtReferenceRepository(root_b)]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda repo: repo.station_lines_mapping(), repositories))

    assert results == [{"ALPHA": ["AAA"]}, {"BETA": ["BBB"]}]


def test_new_mrt_repository_invalidates_instance_cache(tmp_path):
    _write_mrt(tmp_path, "AAA", "ALPHA")
    first = MrtReferenceRepository(tmp_path)
    assert first.station_lines("ALPHA") == ["AAA"]
    (tmp_path / "mrt_stations.json").write_text(json.dumps({"BETA": ["AAA"]}))

    assert first.station_lines("ALPHA") == ["AAA"]
    assert MrtReferenceRepository(tmp_path).station_lines("BETA") == ["AAA"]


def test_school_repository_returns_defensive_copies(tmp_path):
    external = tmp_path / "bronze" / "external"
    external.mkdir(parents=True)
    (external / "school_tiers.json").write_text(
        json.dumps({"primary": [{"school_name": "A", "tier": 1}]})
    )
    repository = SchoolReferenceRepository(tmp_path / "bronze", tmp_path)

    primary, _ = repository.load_school_tiers()
    primary.loc[0, "school_name"] = "MUTATED"
    reloaded, _ = repository.load_school_tiers()

    assert reloaded.loc[0, "school_name"] == "A"


def test_spatial_repositories_do_not_share_polygons(tmp_path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    _write_planning_area(root_a, "AREA_A")
    _write_planning_area(root_b, "AREA_B")

    point_lat = pd.Series([1.35])
    point_lon = pd.Series([103.85])
    assert SpatialReferenceRepository(root_a).planning_areas_for_points(
        point_lat, point_lon
    ).tolist() == ["AREA_A"]
    assert SpatialReferenceRepository(root_b).planning_areas_for_points(
        point_lat, point_lon
    ).tolist() == ["AREA_B"]


@pytest.mark.parametrize(
    ("module", "invoke"),
    [
        (
            datagovsg,
            lambda manager: datagovsg.fetch_datagovsg_dataset(
                "https://example.test?id=", "dataset", cache_manager=manager
            ),
        ),
        (
            onemap,
            lambda manager: onemap.fetch_data_cached("address", {}, cache_manager=manager),
        ),
        (
            ura,
            lambda manager: ura.fetch_ura_token("key", cache_manager=manager),
        ),
    ],
)
def test_cached_adapters_forward_explicit_manager(tmp_path, monkeypatch, module, invoke):
    manager = CacheManager(tmp_path / module.__name__)
    captured = {}

    def fake_cached_call(identifier, func, duration_hours=None, *, cache_manager=None):
        captured["manager"] = cache_manager
        return "cached"

    monkeypatch.setattr(module, "cached_call", fake_cached_call)

    assert invoke(manager) == "cached"
    assert captured["manager"] is manager
