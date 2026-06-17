"""Tests for utils/proximity.py -- the unified proximity seam.

Re-homes behavioral assertions from the deleted mrt_distance.py.
"""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.proximity import compute_proximity_features

pytestmark = pytest.mark.unit


def _make_mrt_df():
    return pd.DataFrame(
        [
            {
                "name": "TOA PAYOH",
                "lat": 1.3329,
                "lon": 103.8478,
                "tier": 1,
                "is_interchange": False,
            },
            {
                "name": "BISHAN INTERCHANGE",
                "lat": 1.3506,
                "lon": 103.8497,
                "tier": 1,
                "is_interchange": True,
            },
        ]
    )


class TestMrtProximity:
    def test_finds_closest_station(self):
        props = pd.DataFrame([{"lat": 1.333, "lon": 103.848, "id": 1}])
        result = compute_proximity_features(props, mrt_stations=_make_mrt_df())
        assert result.iloc[0]["nearest_mrt_station"] == "TOA PAYOH"

    def test_distance_is_positive(self):
        props = pd.DataFrame([{"lat": 1.335, "lon": 103.85, "id": 1}])
        result = compute_proximity_features(props, mrt_stations=_make_mrt_df())
        assert result.iloc[0]["nearest_mrt_distance"] > 0

    def test_multiple_properties_get_different_stations(self):
        props = pd.DataFrame(
            [
                {"lat": 1.333, "lon": 103.848},
                {"lat": 1.351, "lon": 103.850},
            ]
        )
        result = compute_proximity_features(props, mrt_stations=_make_mrt_df())
        assert len(result) == 2
        assert result.iloc[0]["nearest_mrt_station"] == "TOA PAYOH"
        assert result.iloc[1]["nearest_mrt_station"] == "BISHAN INTERCHANGE"

    def test_interchange_detected(self):
        props = pd.DataFrame([{"lat": 1.3506, "lon": 103.8497}])
        result = compute_proximity_features(props, mrt_stations=_make_mrt_df())
        assert bool(result.iloc[0]["nearest_mrt_is_interchange"]) is True

    def test_invalid_coordinates_get_no_station(self):
        props = pd.DataFrame(
            [
                {"lat": None, "lon": 103.82, "id": 1},
                {"lat": 1.35, "lon": 103.82, "id": 2},
            ]
        )
        result = compute_proximity_features(props, mrt_stations=_make_mrt_df())
        assert result.loc[result["id"] == 1, "nearest_mrt_station"].iloc[0] is None
        assert result.loc[result["id"] == 2, "nearest_mrt_station"].iloc[0] is not None

    def test_no_mrt_data_skips_mrt_features(self):
        props = pd.DataFrame([{"lat": 1.35, "lon": 103.82, "id": 1}])
        result = compute_proximity_features(props, mrt_stations=None)
        assert "nearest_mrt_station" not in result.columns
