"""Tests for spatial reference loading (utils/data_loader.py).

Focus: the vectorized point-in-polygon lookup in
``_planning_areas_for_points`` — a single ``gpd.sjoin`` with
``drop_duplicates(subset="_idx", keep="first")`` — whose contract is:

- first-candidate-wins for points inside overlapping polygons
  (candidate order = polygon order in the reference list);
- miss-returns-None for points outside every polygon, on polygon
  boundaries (``within`` is strict), or with non-numeric coordinates.

The public ``SpatialReferenceRepository`` path is exercised against a real
(small) GeoJSON written to ``tmp_path``.
"""

import json
import logging

import pandas as pd
import pytest
from shapely.geometry import Polygon, box, mapping

from egg_n_bacon_housing.utils.data_loader import (
    SpatialReferenceRepository,
    _planning_areas_for_points,
)

pytestmark = pytest.mark.unit

# Two squares overlapping in [103.81, 103.82] x [1.31, 1.32] (lon, lat).
ALPHA = box(103.80, 1.30, 103.82, 1.32)
BETA = box(103.81, 1.31, 103.83, 1.33)
INSIDE_BOTH = (1.315, 103.815)  # lat, lon: inside Alpha AND Beta
OUTSIDE_ALL = (1.50, 103.99)
ON_ALPHA_EDGE = (1.30, 103.81)  # on Alpha's bottom edge, outside Beta


def _polys(*name_geom_pairs):
    return [{"name": name, "geometry": geom} for name, geom in name_geom_pairs]


def _query(polys, points):
    """points: sequence of (lat, lon) tuples queried against ``polys``."""
    index = list(range(len(points)))
    lat = pd.Series([p[0] for p in points], index=index)
    lon = pd.Series([p[1] for p in points], index=index)
    return _planning_areas_for_points(polys, lat, lon)


class TestPolygonOverlapFirstCandidateWins:
    """Sliver-overlap semantics: drop_duplicates(keep="first") on the sjoin."""

    def test_point_inside_two_overlapping_polygons_takes_first_candidate(self):
        result = _query(_polys(("Alpha", ALPHA), ("Beta", BETA)), [INSIDE_BOTH])

        assert result.tolist() == ["Alpha"]

    def test_first_candidate_wins_is_candidate_order_not_geometry_order(self):
        """Reversing the candidate list flips the winner — order drives it."""
        result = _query(_polys(("Beta", BETA), ("Alpha", ALPHA)), [INSIDE_BOTH])

        assert result.tolist() == ["Beta"]

    def test_overlap_resolution_is_deterministic_across_repeated_calls(self):
        polys = _polys(("Alpha", ALPHA), ("Beta", BETA))

        results = [_query(polys, [INSIDE_BOTH]).tolist() for _ in range(3)]

        assert results == [["Alpha"]] * 3

    def test_non_overlapping_points_keep_their_own_matches(self):
        inside_alpha_only = (1.305, 103.805)
        inside_beta_only = (1.325, 103.825)

        result = _query(
            _polys(("Alpha", ALPHA), ("Beta", BETA)), [inside_alpha_only, inside_beta_only]
        )

        assert result.tolist() == ["Alpha", "Beta"]


class TestMissesAndBoundary:
    """miss-returns-None semantics."""

    def test_point_outside_all_polygons_is_none(self):
        result = _query(_polys(("Alpha", ALPHA)), [OUTSIDE_ALL])

        assert result.tolist() == [None]

    def test_point_on_polygon_boundary_is_none(self):
        """sjoin uses the strict 'within' predicate: edges are misses."""
        result = _query(_polys(("Alpha", ALPHA), ("Beta", BETA)), [ON_ALPHA_EDGE])

        assert result.tolist() == [None]

    def test_nan_coordinates_are_misses(self):
        polys = _polys(("Alpha", ALPHA))

        result = _query(polys, [(1.315, 103.815), (float("nan"), 103.8), (1.315, float("nan"))])

        assert result.tolist() == ["Alpha", None, None]

    def test_non_numeric_coordinates_coerce_then_miss(self):
        result = _query(_polys(("Alpha", ALPHA)), [(1.315, 103.815), ("abc", "def")])

        assert result.tolist() == ["Alpha", None]

    def test_all_nan_input_short_circuits_without_matches(self):
        result = _query(_polys(("Alpha", ALPHA)), [(float("nan"), float("nan"))])

        assert result.tolist() == [None]

    def test_empty_input_returns_empty_series_preserving_index(self):
        lat = pd.Series([], dtype="float64", index=pd.Index([], dtype="int64"))
        lon = pd.Series([], dtype="float64", index=pd.Index([], dtype="int64"))

        result = _planning_areas_for_points(_polys(("Alpha", ALPHA)), lat, lon)

        assert len(result) == 0
        assert result.index.equals(lat.index)

    def test_result_index_aligns_to_input_index(self):
        lat = pd.Series([INSIDE_BOTH[0], OUTSIDE_ALL[0]], index=[10, 20])
        lon = pd.Series([INSIDE_BOTH[1], OUTSIDE_ALL[1]], index=[10, 20])

        result = _planning_areas_for_points(_polys(("Alpha", ALPHA)), lat, lon)

        assert result.index.tolist() == [10, 20]
        assert result.loc[10] == "Alpha"
        assert result.loc[20] is None


class TestDegenerateCandidateSets:
    """Unusable polygon lists degrade to all-miss, never raise."""

    def test_no_polygons_returns_all_miss(self):
        result = _query([], [INSIDE_BOTH])

        assert result.tolist() == [None]

    def test_none_and_empty_geometries_are_skipped(self):
        polys = [
            {"name": "Null", "geometry": None},
            {"name": "Empty", "geometry": Polygon()},
            {"name": "Alpha", "geometry": ALPHA},
        ]

        result = _query(polys, [INSIDE_BOTH])

        assert result.tolist() == ["Alpha"]

    def test_all_geometries_invalid_returns_all_miss(self):
        polys = [
            {"name": "Null", "geometry": None},
            {"name": "Empty", "geometry": Polygon()},
        ]

        result = _query(polys, [INSIDE_BOTH])

        assert result.tolist() == [None]


def _feature(name, geom):
    return {"type": "Feature", "properties": {"pln_area_n": name}, "geometry": mapping(geom)}


def _write_geojson(path, features):
    collection = {"type": "FeatureCollection", "features": features}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection), encoding="utf-8")


class TestSpatialReferenceRepository:
    """The public load-once repository over a real GeoJSON file."""

    def test_resolves_points_from_geojson_on_disk(self, tmp_path):
        _write_geojson(
            tmp_path / "onemap_planning_area_polygon.geojson",
            [_feature("DOWNTOWN CORE", ALPHA), _feature("ORCHARD", BETA)],
        )
        repo = SpatialReferenceRepository(raw_data_dir=tmp_path)

        result = repo.planning_areas_for_points(
            lat=pd.Series([INSIDE_BOTH[0]], index=[0]),
            lon=pd.Series([INSIDE_BOTH[1]], index=[0]),
        )

        assert result.tolist() == ["DOWNTOWN CORE"]

    def test_repository_overlap_semantics_match_the_helper(self, tmp_path):
        """The repo wrapper is a thin pass-through: first candidate wins here too."""
        _write_geojson(
            tmp_path / "onemap_planning_area_polygon.geojson",
            [_feature("FIRST", ALPHA), _feature("SECOND", BETA)],
        )
        repo = SpatialReferenceRepository(raw_data_dir=tmp_path)

        first = repo.planning_areas_for_points(
            lat=pd.Series([INSIDE_BOTH[0]], index=[0]),
            lon=pd.Series([INSIDE_BOTH[1]], index=[0]),
        )
        second = repo.planning_areas_for_points(
            lat=pd.Series([INSIDE_BOTH[0]], index=[0]),
            lon=pd.Series([INSIDE_BOTH[1]], index=[0]),
        )

        assert first.tolist() == ["FIRST"]
        assert first.tolist() == second.tolist()  # load-once cache stays consistent

    def test_load_planning_areas_returns_a_fresh_list(self, tmp_path):
        _write_geojson(
            tmp_path / "onemap_planning_area_polygon.geojson", [_feature("ALPHA", ALPHA)]
        )
        repo = SpatialReferenceRepository(raw_data_dir=tmp_path)

        first = repo.load_planning_areas()
        first.append({"name": "extra", "geometry": None})

        # The list structure is copied per call, so callers cannot grow or
        # shrink the repository's cached list.
        assert len(repo.load_planning_areas()) == 1

    def test_missing_geojson_warns_and_returns_all_miss(self, tmp_path, caplog):
        repo = SpatialReferenceRepository(raw_data_dir=tmp_path)

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.data_loader"):
            result = repo.planning_areas_for_points(
                lat=pd.Series([INSIDE_BOTH[0]], index=[0]),
                lon=pd.Series([INSIDE_BOTH[1]], index=[0]),
            )

        assert result.tolist() == [None]
        assert any("not found" in r.getMessage() for r in caplog.records)

    def test_corrupt_geojson_warns_and_returns_all_miss(self, tmp_path, caplog):
        geojson = tmp_path / "onemap_planning_area_polygon.geojson"
        geojson.parent.mkdir(parents=True, exist_ok=True)
        geojson.write_text("{not json", encoding="utf-8")
        repo = SpatialReferenceRepository(raw_data_dir=tmp_path)

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.data_loader"):
            result = repo.planning_areas_for_points(
                lat=pd.Series([INSIDE_BOTH[0]], index=[0]),
                lon=pd.Series([INSIDE_BOTH[1]], index=[0]),
            )

        assert result.tolist() == [None]
        assert any("Error loading planning areas" in r.getMessage() for r in caplog.records)
