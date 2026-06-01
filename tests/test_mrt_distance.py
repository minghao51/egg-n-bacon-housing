"""Tests for utils/mrt_distance.py."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils import mrt_distance

pytestmark = pytest.mark.unit


def _make_mrt_df():
    return pd.DataFrame(
        [
            {
                "name": "TOA PAYOH",
                "lat": 1.3329,
                "lon": 103.8478,
                "rail_type": "MRT",
                "ground_level": "Underground",
                "lines": ["NSL"],
                "tier": 1,
                "is_interchange": False,
                "line_names": ["North-South Line"],
                "colors": ["#DC241F"],
            },
            {
                "name": "BISHAN INTERCHANGE",
                "lat": 1.3506,
                "lon": 103.8497,
                "rail_type": "MRT",
                "ground_level": "Underground",
                "lines": ["NSL", "CCL"],
                "tier": 1,
                "is_interchange": True,
                "line_names": ["North-South Line", "Circle Line"],
                "colors": ["#DC241F", "#C46500"],
            },
        ]
    )


class TestCalculateNearestMRT:
    def test_adds_expected_columns(self):
        props = pd.DataFrame([{"lat": 1.335, "lon": 103.85, "id": 1}])
        mrt_df = _make_mrt_df()
        result = mrt_distance.calculate_nearest_mrt(props, mrt_df, show_progress=False)
        assert "nearest_mrt_station" in result.columns
        assert "nearest_mrt_distance" in result.columns
        assert "nearest_mrt_tier" in result.columns
        assert "nearest_mrt_is_interchange" in result.columns
        assert "nearest_mrt_score" in result.columns

    def test_finds_closest_station(self):
        props = pd.DataFrame([{"lat": 1.333, "lon": 103.848, "id": 1}])
        mrt_df = _make_mrt_df()
        result = mrt_distance.calculate_nearest_mrt(props, mrt_df, show_progress=False)
        assert result.iloc[0]["nearest_mrt_station"] == "TOA PAYOH"

    def test_distance_is_positive(self):
        props = pd.DataFrame([{"lat": 1.335, "lon": 103.85, "id": 1}])
        mrt_df = _make_mrt_df()
        result = mrt_distance.calculate_nearest_mrt(props, mrt_df, show_progress=False)
        assert result.iloc[0]["nearest_mrt_distance"] > 0

    def test_multiple_properties(self):
        props = pd.DataFrame(
            [
                {"lat": 1.333, "lon": 103.848},
                {"lat": 1.351, "lon": 103.850},
            ]
        )
        mrt_df = _make_mrt_df()
        result = mrt_distance.calculate_nearest_mrt(props, mrt_df, show_progress=False)
        assert len(result) == 2
        assert result.iloc[0]["nearest_mrt_station"] == "TOA PAYOH"
        assert result.iloc[1]["nearest_mrt_station"] == "BISHAN INTERCHANGE"

    def test_empty_mrt_data_with_explicit_empty_df(self, monkeypatch):
        props = pd.DataFrame([{"lat": 1.35, "lon": 103.82, "id": 1}])
        monkeypatch.setattr(mrt_distance, "load_mrt_stations", lambda path=None: pd.DataFrame())
        result = mrt_distance.calculate_nearest_mrt(props, None, show_progress=False)
        assert result.iloc[0]["nearest_mrt_station"] is None
        assert result.iloc[0]["nearest_mrt_distance"] is None
        assert result.iloc[0]["nearest_mrt_score"] == 0.0

    def test_missing_lat_lon_returns_unmodified(self):
        props = pd.DataFrame([{"id": 1}])
        result = mrt_distance.calculate_nearest_mrt(props, _make_mrt_df(), show_progress=False)
        assert "nearest_mrt_station" not in result.columns

    def test_invalid_coordinates_handled(self):
        props = pd.DataFrame(
            [
                {"lat": None, "lon": 103.82, "id": 1},
                {"lat": 1.35, "lon": None, "id": 2},
                {"lat": 1.35, "lon": 103.82, "id": 3},
            ]
        )
        mrt_df = _make_mrt_df()
        result = mrt_distance.calculate_nearest_mrt(props, mrt_df, show_progress=False)
        assert result.loc[result["id"] == 3, "nearest_mrt_station"].iloc[0] is not None
        assert result.loc[result["id"] == 1, "nearest_mrt_station"].iloc[0] is None

    def test_interchange_detected(self):
        props = pd.DataFrame([{"lat": 1.3506, "lon": 103.8497}])
        mrt_df = _make_mrt_df()
        result = mrt_distance.calculate_nearest_mrt(props, mrt_df, show_progress=False)
        assert result.iloc[0]["nearest_mrt_is_interchange"] is True

    def test_does_not_modify_original(self):
        props = pd.DataFrame([{"lat": 1.335, "lon": 103.85, "id": 1}])
        original_cols = list(props.columns)
        mrt_distance.calculate_nearest_mrt(props, _make_mrt_df(), show_progress=False)
        assert list(props.columns) == original_cols
