"""Tests for utils/proximity.py -- the unified proximity seam.

Re-homes behavioral assertions from the deleted mrt_distance.py.
"""

import logging
import sys

import numpy as np
import pandas as pd
import pytest

from egg_n_bacon_housing.utils.geo import haversine_distance
from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository
from egg_n_bacon_housing.utils.proximity import compute_proximity_features

pytestmark = pytest.mark.unit

_PROXIMITY_LOGGER = "egg_n_bacon_housing.utils.proximity"


@pytest.fixture(autouse=True)
def _inject_mrt_reference(monkeypatch):
    """Inject the explicit reference required by the production seam."""
    original = compute_proximity_features

    def with_reference(*args, **kwargs):
        kwargs.setdefault("mrt_reference", MrtReferenceRepository(None))
        return original(*args, **kwargs)

    monkeypatch.setattr(sys.modules[__name__], "compute_proximity_features", with_reference)


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
        assert result.iloc[0]["dist_to_nearest_mrt"] > 0

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

    def test_bronze_station_frame_gets_derived_tier_and_interchange(self, monkeypatch):
        """Bronze MRT frames lack tier/is_interchange — they must be derived."""

        class _Reference:
            @staticmethod
            def station_tier(_name):
                return 2

            @staticmethod
            def station_lines(name):
                return ["NSL", "EWL"] if "JURONG" in name else ["NSL"]

        bronze_frame = pd.DataFrame(
            [
                {"name": "TOA PAYOH", "lat": 1.3329, "lon": 103.8478},
                {"name": "JURONG EAST", "lat": 1.3497, "lon": 103.8489},
            ]
        )
        props = pd.DataFrame([{"lat": 1.333, "lon": 103.848}])

        result = compute_proximity_features(
            props, mrt_stations=bronze_frame, mrt_reference=_Reference()
        )

        assert result.iloc[0]["nearest_mrt_tier"] == 2
        # nearest station here is TOA PAYOH (1 line) vs JURONG EAST (2 lines)
        station = result.iloc[0]["nearest_mrt_station"]
        expected_interchange = station == "JURONG EAST"
        assert bool(result.iloc[0]["nearest_mrt_is_interchange"]) is expected_interchange


class TestMrtColumnContract:
    """WS17: dist_to_nearest_mrt is the one canonical distance column."""

    def test_duplicate_alias_column_removed(self):
        props = pd.DataFrame([{"lat": 1.333, "lon": 103.848, "id": 1}])
        result = compute_proximity_features(props, mrt_stations=_make_mrt_df())

        assert "nearest_mrt_distance" not in result.columns
        assert "dist_to_nearest_mrt" in result.columns
        # Interchange/tier columns unchanged by the alias removal.
        for col in (
            "nearest_mrt_station",
            "nearest_mrt_tier",
            "nearest_mrt_is_interchange",
            "nearest_mrt_score",
        ):
            assert col in result.columns

    def test_alias_absent_when_no_valid_coordinates(self):
        props = pd.DataFrame([{"lat": None, "lon": None, "id": 1}])
        result = compute_proximity_features(props, mrt_stations=_make_mrt_df())

        assert "nearest_mrt_distance" not in result.columns
        assert "dist_to_nearest_mrt" in result.columns
        assert result["dist_to_nearest_mrt"].isna().all()
        # WO-8: the empty branch must emit the full MRT column contract,
        # matching the invalid-row convention (0.0 score, not a missing column).
        assert "nearest_mrt_score" in result.columns
        assert result["nearest_mrt_score"].eq(0.0).all()
        assert result["nearest_mrt_is_interchange"].eq(False).all()
        assert result["nearest_mrt_station"].isna().all()
        assert result["nearest_mrt_tier"].isna().all()


class TestMrtSelectionMetric:
    """WO-8: nearest-station selection must be haversine-consistent.

    The retired cKDTree ranked stations by Euclidean distance on raw
    (lon, lat) degrees, which misranks whenever longitude degrees shrink
    relative to latitude degrees. Selection now uses the same
    BallTree/haversine metric as the generic amenity path.
    """

    def test_near_tie_picks_min_haversine_station(self):
        # At latitude 60, one degree of longitude is half a degree of latitude
        # in metres. Euclidean-on-degrees ranks NORTH STATION (0.35 deg) over
        # EAST STATION (0.40 deg); true haversine ranks EAST STATION first.
        mrt = pd.DataFrame(
            [
                {
                    "name": "NORTH STATION",
                    "lat": 60.35,
                    "lon": 100.0,
                    "tier": 1,
                    "is_interchange": False,
                },
                {
                    "name": "EAST STATION",
                    "lat": 60.0,
                    "lon": 100.4,
                    "tier": 1,
                    "is_interchange": False,
                },
            ]
        )
        props = pd.DataFrame([{"lat": 60.0, "lon": 100.0, "id": 1}])

        result = compute_proximity_features(props, mrt_stations=mrt)

        # Brute-force haversine minimum over every station in the fixture.
        brute_force = {
            row["name"]: haversine_distance(60.0, 100.0, row["lat"], row["lon"])
            for _, row in mrt.iterrows()
        }
        expected_station = min(brute_force, key=brute_force.get)
        assert expected_station == "EAST STATION"  # the deliberate near-tie
        row = result.iloc[0]
        assert row["nearest_mrt_station"] == expected_station
        assert row["dist_to_nearest_mrt"] == pytest.approx(brute_force[expected_station], abs=1e-6)

    def test_selection_matches_brute_force_on_multiple_properties(self):
        mrt = pd.DataFrame(
            [
                {"name": "A", "lat": 1.30, "lon": 103.85, "tier": 1, "is_interchange": False},
                {"name": "B", "lat": 1.35, "lon": 103.90, "tier": 1, "is_interchange": False},
                {"name": "C", "lat": 1.40, "lon": 103.80, "tier": 1, "is_interchange": False},
            ]
        )
        props = pd.DataFrame(
            [
                {"lat": 1.32, "lon": 103.87, "id": 1},
                {"lat": 1.38, "lon": 103.81, "id": 2},
                {"lat": 1.31, "lon": 103.88, "id": 3},
            ]
        )

        result = compute_proximity_features(props, mrt_stations=mrt)

        for _, row in result.iterrows():
            distances = {
                station["name"]: haversine_distance(
                    row["lat"], row["lon"], station["lat"], station["lon"]
                )
                for _, station in mrt.iterrows()
            }
            expected_station = min(distances, key=distances.get)
            assert row["nearest_mrt_station"] == expected_station
            assert row["dist_to_nearest_mrt"] == pytest.approx(
                distances[expected_station], abs=1e-6
            )


class TestMrtVectorizationEquivalence:
    """Vectorized haversine must reproduce the retired per-row scalar loop.

    The pinned distances/scores below were captured from the pre-refactor
    scalar implementation (utils.geo.haversine_distance per row +
    station_score per row) on this exact fixture, per the WS17 handoff.
    """

    @pytest.fixture
    def mrt_frame(self):
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
                {
                    "name": "JURONG EAST INTERCHANGE",
                    "lat": 1.3386,
                    "lon": 103.8429,
                    "tier": 1,
                    "is_interchange": True,
                },
            ]
        )

    @pytest.fixture
    def result(self, mrt_frame):
        props = pd.DataFrame(
            [
                {"lat": 1.333, "lon": 103.848, "id": 1},
                {"lat": 1.335, "lon": 103.85, "id": 2},
                {"lat": 1.351, "lon": 103.85, "id": 3},
                {"lat": None, "lon": 103.82, "id": 4},
                {"lat": 1.33, "lon": 103.844, "id": 5},
            ]
        )
        return compute_proximity_features(props, mrt_stations=mrt_frame)

    # (id, nearest_mrt_station, dist_to_nearest_mrt, nearest_mrt_score)
    # as emitted by the pre-refactor scalar loop.
    PINNED_SCALAR_OUTPUTS = [
        (1, "TOA PAYOH", 24.858559008666866, 120.6827796797899),
        (2, "TOA PAYOH", 338.1382136818535, 8.872111694606135),
        (3, "BISHAN INTERCHANGE", 55.591901646959386, 53.96469469693138),
        (5, "TOA PAYOH", 531.4396725801007, 5.64504336952343),
    ]

    def test_distances_match_pinned_scalar_outputs(self, result):
        for pid, station, dist, score in self.PINNED_SCALAR_OUTPUTS:
            row = result[result["id"] == pid].iloc[0]
            assert row["nearest_mrt_station"] == station
            assert row["dist_to_nearest_mrt"] == pytest.approx(dist, abs=1e-9)
            assert row["nearest_mrt_score"] == pytest.approx(score, abs=1e-9)

        # Invalid-coordinate rows still get NA distance and 0.0 score.
        invalid = result[result["id"] == 4].iloc[0]
        assert pd.isna(invalid["dist_to_nearest_mrt"])
        assert invalid["nearest_mrt_score"] == 0.0

    def test_distances_match_scalar_haversine_reference(self, result, mrt_frame):
        """Every vectorized distance equals the scalar utils.geo formula on
        the matched station, within the handoff's 1e-9 tolerance."""
        for _, row in result[result["dist_to_nearest_mrt"].notna()].iterrows():
            station = mrt_frame[mrt_frame["name"] == row["nearest_mrt_station"]].iloc[0]
            scalar = haversine_distance(row["lat"], row["lon"], station["lat"], station["lon"])
            assert row["dist_to_nearest_mrt"] == pytest.approx(scalar, abs=1e-9)

    def test_scores_match_scalar_station_score_reference(self, result, mrt_frame, monkeypatch):
        """Cached per-station score basis reproduces station_score per row."""
        from egg_n_bacon_housing.utils.mrt_line_mapping import get_station_score

        for _, row in result[result["dist_to_nearest_mrt"].notna()].iterrows():
            scalar = get_station_score(
                row["nearest_mrt_station"],
                row["dist_to_nearest_mrt"],
                MrtReferenceRepository(None),
            )
            assert row["nearest_mrt_score"] == pytest.approx(scalar, abs=1e-9)

        # Interchange flags/tiers are untouched by the vectorization.
        bishan = result[result["nearest_mrt_station"] == "BISHAN INTERCHANGE"].iloc[0]
        assert bool(bishan["nearest_mrt_is_interchange"]) is True
        assert bishan["nearest_mrt_tier"] == 1

    def test_results_are_finite_and_mrt_reference_path_matches(self, mrt_frame):
        """The injected-mrt_reference path yields the same numbers as the
        module-fallback path (same station->line mapping)."""
        from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository

        props = pd.DataFrame([{"lat": 1.333, "lon": 103.848, "id": 1}])
        without = compute_proximity_features(props, mrt_stations=mrt_frame)
        with_ref = compute_proximity_features(
            props, mrt_stations=mrt_frame, mrt_reference=MrtReferenceRepository(None)
        )

        assert np.isfinite(without["dist_to_nearest_mrt"].astype(float)).all()
        pd.testing.assert_frame_equal(without, with_ref)


class TestMallProximity:
    def test_mall_proximity_accepts_latitude_longitude_columns(self):
        props = pd.DataFrame([{"lat": 1.3049, "lon": 103.8319}])
        malls = pd.DataFrame(
            [{"shopping_mall": "ION Orchard", "latitude": 1.3048, "longitude": 103.8318}]
        )

        result = compute_proximity_features(props, malls=malls)

        assert result.iloc[0]["nearest_mall"] == "ION Orchard"
        assert result.iloc[0]["dist_to_nearest_mall"] >= 0

    def test_mall_proximity_handles_missing_coordinate_columns(self):
        props = pd.DataFrame([{"lat": 1.3049, "lon": 103.8319}])
        malls = pd.DataFrame([{"shopping_mall": "ION Orchard"}])

        result = compute_proximity_features(props, malls=malls)

        assert pd.isna(result.iloc[0]["nearest_mall"])
        assert pd.isna(result.iloc[0]["dist_to_nearest_mall"])


class TestGenericAmenityProximity:
    def test_generic_proximity_uses_first_column_as_name_fallback(self):
        props = pd.DataFrame([{"lat": 1.33, "lon": 103.85}])
        hawkers = pd.DataFrame([{"centre": "Toa Payoh Hawker", "lat": 1.331, "lon": 103.851}])

        result = compute_proximity_features(props, hawkers=hawkers)

        assert result.iloc[0]["nearest_hawker"] == "Toa Payoh Hawker"
        assert result.iloc[0]["dist_to_nearest_hawker"] > 0

    def test_generic_proximity_returns_na_when_all_pois_are_invalid(self):
        props = pd.DataFrame([{"lat": 1.33, "lon": 103.85}])
        parks = pd.DataFrame([{"name": "Invalid Park", "lat": "oops", "lon": None}])

        result = compute_proximity_features(props, parks=parks)

        assert pd.isna(result.iloc[0]["nearest_park"])
        assert pd.isna(result.iloc[0]["dist_to_nearest_park"])


class TestPoiDropCountLogging:
    """WO-7: POIs lost to unparseable coordinates are counted per amenity."""

    def test_partial_poi_loss_logs_info_with_dropped_and_kept_counts(self, caplog):
        props = pd.DataFrame([{"lat": 1.33, "lon": 103.85}])
        parks = pd.DataFrame(
            [
                {"name": "Good Park", "lat": 1.331, "lon": 103.851},
                {"name": "Bad Park", "lat": "oops", "lon": 103.851},
                {"name": "Worse Park", "lat": 1.331, "lon": None},
            ]
        )

        with caplog.at_level(logging.INFO, logger=_PROXIMITY_LOGGER):
            result = compute_proximity_features(props, parks=parks)

        assert result.iloc[0]["nearest_park"] == "Good Park"
        infos = [r for r in caplog.records if "unparseable coordinates" in r.getMessage()]
        assert len(infos) == 1, caplog.text
        assert infos[0].levelno == logging.INFO
        message = infos[0].getMessage()
        assert "park proximity: dropped 2/3 POI row(s)" in message
        assert "kept 1" in message

    def test_total_poi_loss_warns_about_all_na_degradation(self, caplog):
        props = pd.DataFrame([{"lat": 1.33, "lon": 103.85}])
        parks = pd.DataFrame(
            [
                {"name": "Bad Park", "lat": "oops", "lon": 103.851},
                {"name": "Worse Park", "lat": 1.331, "lon": None},
            ]
        )

        with caplog.at_level(logging.WARNING, logger=_PROXIMITY_LOGGER):
            result = compute_proximity_features(props, parks=parks)

        assert pd.isna(result.iloc[0]["dist_to_nearest_park"])
        assert pd.isna(result.iloc[0]["nearest_park"])
        warnings = [r for r in caplog.records if "ALL" in r.getMessage()]
        assert len(warnings) == 1, caplog.text
        message = warnings[0].getMessage()
        assert "ALL 2 POI row(s)" in message
        assert "dist_to_nearest_park" in message
        assert "nearest_park" in message

    def test_unparseable_property_coordinates_log_count(self, caplog):
        props = pd.DataFrame(
            [
                {"lat": 1.33, "lon": 103.85, "id": 1},
                {"lat": "oops", "lon": 103.85, "id": 2},
            ]
        )
        hawkers = pd.DataFrame([{"name": "Hawker", "lat": 1.331, "lon": 103.851}])

        with caplog.at_level(logging.INFO, logger=_PROXIMITY_LOGGER):
            result = compute_proximity_features(props, hawkers=hawkers)

        assert pd.isna(result.loc[result["id"] == 2, "dist_to_nearest_hawker"].iloc[0])
        infos = [r for r in caplog.records if "amenity features degrade to NA" in r.getMessage()]
        assert len(infos) == 1, caplog.text
        assert "1/2 property row(s)" in infos[0].getMessage()
