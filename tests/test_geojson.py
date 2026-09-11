"""Legacy MRT fallback resilience in GeoJSON ingestion.

Covers WS4: interchange-safe line aggregation in the legacy (2019) fallback,
the loud fallback-activation warning, and the empty-`line` tripwire.
"""

import json
import logging

import pandas as pd
import pytest

pytestmark = pytest.mark.unit

_GEOJSON_LOGGER = "egg_n_bacon_housing.components.ingestion.geojson"


def _geojson_module():
    from egg_n_bacon_housing.components.ingestion import geojson

    return geojson


def _disable_live_mrt_fetch(geojson, monkeypatch):
    """Make the live LTA MRT fetch fail fast so tests exercise legacy paths."""
    from egg_n_bacon_housing.adapters.exceptions import DatasetFetchError

    def _boom(*_a, **_kw):
        raise DatasetFetchError("live fetch disabled in test")

    monkeypatch.setattr(geojson.datagovsg, "fetch_datagovsg_geojson", _boom)


def _write_legacy_external(bronze_dir, stations, station_lines):
    """Write the 2019 legacy seeds: MRTStations.geojson + mrt_stations.json."""
    external = bronze_dir / "external"
    external.mkdir(parents=True, exist_ok=True)
    (external / "mrt_stations.json").write_text(json.dumps(station_lines))
    (external / "MRTStations.geojson").write_text(
        json.dumps(
            {
                "features": [
                    {
                        "properties": {"NAME": name},
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    }
                    for name, lat, lon in stations
                ]
            }
        )
    )


class TestMrtLegacyFallbackAggregation:
    def test_interchange_station_keeps_all_lines_joined_and_sorted(self, tmp_path, monkeypatch):
        """A station under 2 lines must yield ONE row, `";"`-joined sorted lines."""
        geojson = _geojson_module()
        _disable_live_mrt_fetch(geojson, monkeypatch)
        _write_legacy_external(
            tmp_path,
            [("JURONG EAST", 1.3330, 103.7414), ("BISHAN", 1.3509, 103.8483)],
            {
                # deliberately unsorted to prove the fallback sorts before joining
                "JURONG EAST": ["NSL", "EWL"],
                "BISHAN": "CCL",
            },
        )

        result = geojson.raw_mrt_stations(bronze_dir=tmp_path)

        jurong = result[result["name"] == "JURONG EAST"]
        assert len(jurong) == 1
        assert jurong.iloc[0]["line"] == "EWL;NSL"
        assert result.loc[result["name"] == "BISHAN", "line"].iloc[0] == "CCL"

    def test_line_format_matches_live_path(self, tmp_path, monkeypatch):
        """Fallback `line` strings must be indistinguishable from the live path's."""
        geojson = _geojson_module()
        _disable_live_mrt_fetch(geojson, monkeypatch)
        _write_legacy_external(
            tmp_path,
            [("JURONG EAST", 1.3330, 103.7414)],
            {"JURONG EAST": ["NSL", "EWL"]},
        )

        fallback = geojson.raw_mrt_stations(bronze_dir=tmp_path)

        live = geojson._attach_station_lines(
            pd.DataFrame([{"name": "JURONG EAST", "lat": 1.3330, "lon": 103.7414}]),
            pd.DataFrame(
                [
                    {
                        "stn_code": "NS1",
                        "mrt_station_english": "Jurong East",
                        "mrt_line_english": "North-South Line",
                    },
                    {
                        "stn_code": "EW24",
                        "mrt_station_english": "Jurong East",
                        "mrt_line_english": "East-West Line",
                    },
                ]
            ),
        )
        # Same codes, same ";"-joined string format; the live path preserves
        # dataset row order while the fallback sorts — parsing is identical.
        assert fallback.iloc[0]["line"] == "EWL;NSL"
        assert set(fallback.iloc[0]["line"].split(";")) == set(live.iloc[0]["line"].split(";"))
        assert live.iloc[0]["line"] == "NSL;EWL"

    def test_station_absent_from_mapping_gets_empty_line_string(self, tmp_path, monkeypatch):
        """Unknown stations keep the live-path format: '' (not NaN, not dropped)."""
        geojson = _geojson_module()
        _disable_live_mrt_fetch(geojson, monkeypatch)
        _write_legacy_external(
            tmp_path,
            [("BISHAN", 1.3509, 103.8483), ("MYSTERY", 1.4, 103.9)],
            {"BISHAN": ["NSL"]},
        )

        result = geojson.raw_mrt_stations(bronze_dir=tmp_path)

        assert len(result) == 2
        assert result.loc[result["name"] == "MYSTERY", "line"].iloc[0] == ""

    def test_fallback_activation_warns_2019_legacy_with_reason_and_count(
        self, tmp_path, monkeypatch, caplog
    ):
        geojson = _geojson_module()
        _disable_live_mrt_fetch(geojson, monkeypatch)
        _write_legacy_external(
            tmp_path,
            [("BISHAN", 1.3509, 103.8483)],
            {"BISHAN": ["NSL"]},
        )

        with caplog.at_level(logging.WARNING, logger=_GEOJSON_LOGGER):
            result = geojson.raw_mrt_stations(bronze_dir=tmp_path)

        assert len(result) == 1
        fallback_warnings = [r for r in caplog.records if "2019 vintage" in r.getMessage()]
        assert fallback_warnings, caplog.text
        message = fallback_warnings[0].getMessage()
        assert "legacy" in message
        assert "live fetch disabled in test" in message  # fetch failure reason
        assert "1 station" in message  # legacy station count


class TestLiveFetchLineTripwire:
    def _exits_geojson(self):
        return {
            "features": [
                {
                    "properties": {"STATION_NA": "BAYSHORE MRT STATION"},
                    "geometry": {"type": "Point", "coordinates": [103.9412, 1.3118]},
                },
                {
                    "properties": {"STATION_NA": "MYSTERY MRT STATION"},
                    "geometry": {"type": "Point", "coordinates": [103.9, 1.4]},
                },
            ]
        }

    def _wire_live_fetch(self, geojson, monkeypatch, codes):
        monkeypatch.setattr(
            geojson.datagovsg, "fetch_datagovsg_geojson", lambda *a, **kw: self._exits_geojson()
        )
        monkeypatch.setattr(geojson.datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: codes)

    def test_stations_without_lines_warn_with_count_and_examples(
        self, tmp_path, monkeypatch, caplog
    ):
        """Stations absent from codes+supplement trigger the tripwire warning."""
        geojson = _geojson_module()
        self._wire_live_fetch(
            geojson,
            monkeypatch,
            pd.DataFrame(
                [
                    {
                        "stn_code": "TE29",
                        "mrt_station_english": "Bayshore",
                        "mrt_line_english": "Thomson-East Coast Line",
                    }
                ]
            ),
        )

        with caplog.at_level(logging.WARNING, logger=_GEOJSON_LOGGER):
            result = geojson.raw_mrt_stations(bronze_dir=tmp_path)

        assert len(result) == 2
        assert result.loc[result["name"] == "MYSTERY", "line"].iloc[0] == ""
        tripwire = [r for r in caplog.records if "no line assignment" in r.getMessage()]
        assert tripwire, caplog.text
        message = tripwire[0].getMessage()
        assert "1 MRT station" in message
        assert "MYSTERY" in message
        assert "_STATION_LINE_SUPPLEMENT" in message

    def test_fully_mapped_stations_do_not_trigger_tripwire(self, tmp_path, monkeypatch, caplog):
        geojson = _geojson_module()
        self._wire_live_fetch(
            geojson,
            monkeypatch,
            pd.DataFrame(
                [
                    {
                        "stn_code": "TE29",
                        "mrt_station_english": "Bayshore",
                        "mrt_line_english": "Thomson-East Coast Line",
                    },
                    {
                        "stn_code": "TE10",
                        "mrt_station_english": "Mystery",
                        "mrt_line_english": "Thomson-East Coast Line",
                    },
                ]
            ),
        )

        with caplog.at_level(logging.WARNING, logger=_GEOJSON_LOGGER):
            result = geojson.raw_mrt_stations(bronze_dir=tmp_path)

        assert len(result) == 2
        assert not [r for r in caplog.records if "no line assignment" in r.getMessage()]


class TestCoordinateValidity:
    """WS12: 0.0 is a valid coordinate; None/NaN are not (falsy-zero fix)."""

    def test_valid_coord_semantics(self):
        geojson = _geojson_module()

        assert geojson._valid_coord(0.0)
        assert geojson._valid_coord(0)
        assert geojson._valid_coord(1.33)
        assert geojson._valid_coord("1.33")
        assert not geojson._valid_coord(None)
        assert not geojson._valid_coord(float("nan"))
        assert not geojson._valid_coord(float("inf"))
        assert not geojson._valid_coord("not-a-number")
        assert not geojson._valid_coord(pd.NA)

    def test_zero_coordinates_are_kept(self, tmp_path):
        geojson = _geojson_module()
        path = tmp_path / "amenity.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "Null Island Depot"},
                            "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                        }
                    ]
                }
            )
        )

        result = geojson._load_geojson_amenities(path, ["NAME"], "test")

        assert len(result) == 1
        assert result.loc[0, "lat"] == 0.0
        assert result.loc[0, "lon"] == 0.0

    def test_nan_and_missing_coordinates_still_dropped(self, tmp_path):
        geojson = _geojson_module()
        path = tmp_path / "amenity.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "A"},
                            "geometry": {"type": "Point", "coordinates": [float("nan"), 1.0]},
                        },
                        {
                            "properties": {"NAME": "B"},
                            "geometry": {"type": "Point", "coordinates": [103.0, None]},
                        },
                        {"properties": {"NAME": "C"}},
                    ]
                }
            )
        )

        result = geojson._load_geojson_amenities(path, ["NAME"], "test")

        assert result.empty

    def test_invalid_amenity_coordinates_dropped_with_count_warning(self, tmp_path, caplog):
        """WO-7: coordinate drops in _load_geojson_amenities are counted (like
        the MRT loader's name-less pattern)."""
        geojson = _geojson_module()
        path = tmp_path / "amenity.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "Good"},
                            "geometry": {"type": "Point", "coordinates": [103.8, 1.35]},
                        },
                        {
                            "properties": {"NAME": "NanLat"},
                            "geometry": {"type": "Point", "coordinates": [float("nan"), 1.0]},
                        },
                        {"properties": {"NAME": "NoGeom"}},
                    ]
                }
            )
        )

        with caplog.at_level(logging.WARNING, logger=_GEOJSON_LOGGER):
            result = geojson._load_geojson_amenities(path, ["NAME"], "test")

        assert len(result) == 1
        assert result.loc[0, "name"] == "Good"
        warnings = [
            r for r in caplog.records if "invalid/unparseable coordinates" in r.getMessage()
        ]
        assert len(warnings) == 1, caplog.text
        message = warnings[0].getMessage()
        assert "Dropped 2 test feature(s)" in message
        assert path.name in message

    def test_valid_amenity_features_do_not_warn(self, tmp_path, caplog):
        geojson = _geojson_module()
        path = tmp_path / "amenity.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "Good"},
                            "geometry": {"type": "Point", "coordinates": [103.8, 1.35]},
                        }
                    ]
                }
            )
        )

        with caplog.at_level(logging.WARNING, logger=_GEOJSON_LOGGER):
            geojson._load_geojson_amenities(path, ["NAME"], "test")

        assert not [r for r in caplog.records if "coordinates" in r.getMessage()]

    def test_nameless_mrt_features_dropped_with_count_warning(self, tmp_path, caplog):
        geojson = _geojson_module()
        path = tmp_path / "MRTStations.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "BISHAN"},
                            "geometry": {"type": "Point", "coordinates": [103.83, 1.35]},
                        },
                        {
                            "properties": {},
                            "geometry": {"type": "Point", "coordinates": [103.84, 1.36]},
                        },
                        {
                            "properties": {"NAME": ""},
                            "geometry": {"type": "Point", "coordinates": [103.85, 1.37]},
                        },
                        {
                            # named but coordinate-less: dropped for coords, NOT counted
                            "properties": {"NAME": "COORDLESS"},
                            "geometry": {"type": "Point", "coordinates": [float("nan"), 1.0]},
                        },
                    ]
                }
            )
        )

        with caplog.at_level(logging.WARNING, logger=_GEOJSON_LOGGER):
            result = geojson._load_mrt_geojson(path)

        assert len(result) == 1
        assert result.loc[0, "name"] == "BISHAN"
        warnings = [r for r in caplog.records if "name-less" in r.getMessage()]
        assert len(warnings) == 1, caplog.text
        assert "2" in warnings[0].getMessage()

    def test_zero_coordinate_mrt_station_is_kept(self, tmp_path):
        """A station at exactly 0.0 in either axis survives the name+coord guard."""
        geojson = _geojson_module()
        path = tmp_path / "MRTStations.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "NULL ISLAND"},
                            "geometry": {"type": "Point", "coordinates": [0, 0]},
                        }
                    ]
                }
            )
        )

        result = geojson._load_mrt_geojson(path)

        assert len(result) == 1
        assert result.loc[0, "name"] == "NULL ISLAND"
        assert result.loc[0, "lat"] == 0
        assert result.loc[0, "lon"] == 0
