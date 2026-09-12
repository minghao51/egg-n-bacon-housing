"""Test 03_features component."""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.components import (
    feature_profiles,
    feature_rental,
    feature_transactions,
    features,
)
from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

pytestmark = pytest.mark.unit


def _make_mrt_stations():
    return pd.DataFrame([{"name": "Toa Payoh", "lat": 1.332, "lon": 103.847}])


class TestGoldLayer:
    """Test gold layer feature engineering functions."""

    def test_rental_yield_uses_rental_transactions_instead_of_placeholder(self, tmp_path):
        """Test that rental yield is derived from observed rent and sale data."""
        features = feature_rental

        hdb_validated = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "town": "TOA PAYOH",
                    "price": 520000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-28"),
                },
            ]
        )

        raw_hdb_rental = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "flat_type": "4-ROOM",
                    "monthly_rent": "3500",
                    "rent_approval_date": "2024-01",
                }
            ]
        )

        raw_rental_index = pd.DataFrame(
            [
                {
                    "quarter": "2024-Q1",
                    "locality": "Whole Island",
                    "index": "108.2",
                }
            ]
        )

        result = features.rental_yield(hdb_validated, raw_hdb_rental, raw_rental_index)

        assert isinstance(result, pd.DataFrame)
        assert list(result["town"]) == ["TOA PAYOH"]
        assert result.loc[0, "month"] == "2024-01"
        assert result.loc[0, "median_rent"] == 3500
        assert result.loc[0, "rental_yield_pct"] == pytest.approx((3500 * 12 / 510000) * 100)
        assert result.loc[0, "rental_yield_pct"] != pytest.approx(0.48)

    def test_rental_yield_with_empty_input(self, tmp_path):
        """Test that rental_yield handles empty input."""
        features = feature_rental

        hdb_validated = pd.DataFrame()
        raw_hdb_rental = pd.DataFrame()
        raw_rental_index = pd.DataFrame()

        result = features.rental_yield(hdb_validated, raw_hdb_rental, raw_rental_index)

        assert isinstance(result, pd.DataFrame)
        assert result.empty


def _empty_poi_args():
    """Return kwargs with empty DataFrames for all POI types."""
    return dict(
        raw_hawker_centres=pd.DataFrame(),
        raw_supermarkets=pd.DataFrame(),
        raw_parks=pd.DataFrame(),
        raw_childcare=pd.DataFrame(),
        raw_kindergartens=pd.DataFrame(),
        raw_bus_stops=pd.DataFrame(),
        raw_chas_clinics=pd.DataFrame(),
        raw_sports_facilities=pd.DataFrame(),
        raw_community_clubs=pd.DataFrame(),
        geocoded_green_mark_buildings=pd.DataFrame(),
    )


class TestLocationDim:
    """Test the location_dim entity dimension table."""

    def test_location_dim_extracts_unique_coords(self, tmp_path, monkeypatch):
        """Test that location_dim deduplicates to unique (lat, lon) pairs."""

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 520000.0,
                    "transaction_date": pd.Timestamp("2024-02-15"),
                },
                {
                    "lat": 1.36,
                    "lon": 103.82,
                    "block": "456",
                    "street_name": "BEDOK NTH RD",
                    "town": "BEDOK",
                    "price": 400000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_location_dim_with_empty_input(self, tmp_path):
        """Test that location_dim handles empty geocoded data."""
        result = features.location_dim(
            pd.DataFrame(),
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_location_dim_computes_proximity(self, tmp_path, monkeypatch):
        """Test that location_dim calls proximity features."""
        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        def fake_proximity(props, **kw):
            props["dist_to_nearest_mrt"] = 456.0
            props["nearest_mrt_station"] = "Toa Payoh"
            return props

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", fake_proximity)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=_make_mrt_stations(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert not result.empty
        assert result.loc[0, "dist_to_nearest_mrt"] == pytest.approx(456.0)
        assert result.loc[0, "nearest_mrt_station"] == "Toa Payoh"

    def test_location_dim_merges_block_metadata(self, tmp_path, monkeypatch):
        """Test that location_dim merges HDB property info."""
        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        raw_hdb_property_info = pd.DataFrame(
            [
                {
                    "blk_no": "123",
                    "street": "TOA PAYOH LOR 1",
                    "max_floor_lvl": 25,
                    "year_completed": 1990,
                    "total_dwelling_units": 100,
                    "residential": "Y",
                    "commercial": "N",
                    "market_hawker": "N",
                    "multistorey_carpark": "N",
                }
            ]
        )

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=raw_hdb_property_info,
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert not result.empty
        assert result.loc[0, "year_completed"] == 1990
        assert result.loc[0, "max_floor_lvl"] == 25

    def test_location_dim_writes_nothing(self, tmp_path, monkeypatch):
        """Materializer owns persistence — the computing node writes nothing (persist=False)."""
        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert not result.empty
        assert list(tmp_path.rglob("*.parquet")) == []

    def test_proximity_source_failure_degrades_to_na_with_warning(
        self, tmp_path, monkeypatch, caplog
    ):
        """WO-8: verified source failures degrade all proximity columns to NA
        with a WARNING carrying the exception detail."""
        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                }
            ]
        )

        def broken_proximity(props, **kw):
            raise ValueError("Input contains NaN")

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", broken_proximity)

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.components.features"):
            result = features.location_dim(
                geocoded_validated,
                raw_mrt_stations=_make_mrt_stations(),
                raw_school_directory=pd.DataFrame(),
                raw_shopping_malls=pd.DataFrame(),
                raw_hdb_property_info=pd.DataFrame(),
                geocoder=InMemoryGeocoder({}),
                **_empty_poi_args(),
            )

        assert not result.empty
        expected_columns = ["dist_to_nearest_mrt", "nearest_mrt_station"]
        for label in (
            "mall",
            "hawker",
            "supermarket",
            "park",
            "childcare",
            "kindergarten",
            "bus_stop",
            "chas_clinic",
            "sports_facility",
            "community_club",
            "green_mark_building",
        ):
            expected_columns.extend([f"dist_to_nearest_{label}", f"nearest_{label}"])
        for col in expected_columns:
            assert col in result.columns, col
            assert result[col].isna().all(), col

        warnings = [r for r in caplog.records if "Proximity features degraded" in r.getMessage()]
        assert len(warnings) == 1, caplog.text
        assert warnings[0].levelno == logging.WARNING
        message = warnings[0].getMessage()
        assert "ValueError" in message
        assert "Input contains NaN" in message

    def test_proximity_programming_error_propagates(self, tmp_path, monkeypatch):
        """WO-8: the narrowed except clause lets programming errors surface."""
        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                }
            ]
        )

        def buggy_proximity(props, **kw):
            raise TypeError("programmer bug")

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", buggy_proximity)

        with pytest.raises(TypeError, match="programmer bug"):
            features.location_dim(
                geocoded_validated,
                raw_mrt_stations=_make_mrt_stations(),
                raw_school_directory=pd.DataFrame(),
                raw_shopping_malls=pd.DataFrame(),
                raw_hdb_property_info=pd.DataFrame(),
                geocoder=InMemoryGeocoder({}),
                **_empty_poi_args(),
            )

    def test_no_geocoded_schools_yields_na_school_distance_column(self, tmp_path, monkeypatch):
        """WO-8: calculate_school_features returning without the per-level
        distance columns still leaves dist_to_nearest_school present as NA."""
        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                }
            ]
        )
        # No postal_code -> geocode_schools adds all-NA latitude/longitude
        # without calling the geocoder, and calculate_school_features then
        # takes its no-geocoded-schools early return (utils/school_features.py).
        raw_school_directory = pd.DataFrame(
            [{"name": "School Without Location", "mainlevel_code": "PRIMARY"}]
        )
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=raw_school_directory,
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert not result.empty
        assert "dist_to_nearest_school" in result.columns
        assert result["dist_to_nearest_school"].isna().all()


class TestPlanningAreaDerivation:
    """WS17: the data_loader module-global fallback is gone — the spatial
    repository must be injected directly."""

    def test_injected_spatial_reference_derives_planning_area(self):
        from egg_n_bacon_housing.components.features import _add_planning_area

        df = pd.DataFrame(
            [
                {"lat": 1.35, "lon": 103.8},
                {"lat": 1.36, "lon": 103.82},
                {"lat": 1.35, "lon": 103.8},
            ]
        )

        class _StubSpatialReference:
            def planning_areas_for_points(self, lat, lon):
                return pd.Series(["TOA PAYOH", "BEDOK"], index=lat.index)

        result = _add_planning_area(df, _StubSpatialReference())

        assert list(result["planning_area"]) == ["TOA PAYOH", "BEDOK", "TOA PAYOH"]
        assert len(result) == 3

    def test_missing_spatial_reference_skips_derivation(self):
        from egg_n_bacon_housing.components.features import _add_planning_area

        df = pd.DataFrame([{"lat": 1.35, "lon": 103.8}])

        result = _add_planning_area(df, None)

        assert "planning_area" not in result.columns

    def test_partial_planning_area_frame_derives_only_null_rows(self):
        """WO-8: one populated value must not freeze derivation for the rest."""
        from egg_n_bacon_housing.components.features import _add_planning_area

        df = pd.DataFrame(
            [
                {"lat": 1.35, "lon": 103.8, "planning_area": "EXISTING"},
                {"lat": 1.36, "lon": 103.82, "planning_area": None},
                {"lat": 1.37, "lon": 103.84, "planning_area": None},
                {"lat": 1.36, "lon": 103.82, "planning_area": None},  # duplicate coords
            ]
        )
        seen_lats: list[float] = []

        class _RecordingSpatialReference:
            def planning_areas_for_points(self, lat, lon):
                seen_lats.extend(lat.tolist())
                return pd.Series(["BEDOK", "CLEMENTI"], index=lat.index)

        result = _add_planning_area(df, _RecordingSpatialReference())

        assert list(result["planning_area"]) == ["EXISTING", "BEDOK", "CLEMENTI", "BEDOK"]
        # Only the null rows' unique coordinates go through the spatial join.
        assert sorted(seen_lats) == [1.36, 1.37]

    def test_fully_populated_planning_area_frame_is_untouched(self):
        from egg_n_bacon_housing.components.features import _add_planning_area

        df = pd.DataFrame(
            [
                {"lat": 1.35, "lon": 103.8, "planning_area": "TOA PAYOH"},
                {"lat": 1.36, "lon": 103.82, "planning_area": "BEDOK"},
            ]
        )

        class _ForbiddenSpatialReference:
            def planning_areas_for_points(self, lat, lon):
                raise AssertionError("no derivation expected for a populated frame")

        result = _add_planning_area(df, _ForbiddenSpatialReference())

        assert list(result["planning_area"]) == ["TOA PAYOH", "BEDOK"]


class TestLocationDimContract:
    """WO-11: school tiers are read through the school_reference DI seam
    (owner decision — rewired instead of deleted). The parameter type is the
    runtime.SchoolReference protocol so tests can stub it."""

    def test_location_dim_declares_school_reference_seam(self):
        import inspect

        params = inspect.signature(features.location_dim).parameters
        assert "school_reference" in params
        assert params["school_reference"].default is None


class TestTransactionsEnriched:
    """Test the transactions_enriched fact table."""

    def test_transactions_enriched_joins_location_dim(self, tmp_path):
        """Test that transactions_enriched joins location_dim by (lat, lon)."""
        features = feature_transactions

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "floor_area_sqft": 1000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                    "remaining_lease_months": 960,
                },
            ]
        )

        location_dim = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "planning_area": "Toa Payoh",
                    "dist_to_nearest_mrt": 300.0,
                    "region": "RCR",
                },
            ]
        )

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim,
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
        )

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "planning_area" in result.columns
        assert result.loc[0, "planning_area"] == "Toa Payoh"
        assert result.loc[0, "dist_to_nearest_mrt"] == pytest.approx(300.0)
        assert result.loc[0, "psf"] == pytest.approx(500.0)
        assert result.loc[0, "remaining_lease_years"] == pytest.approx(80.0)

    def test_transactions_enriched_with_empty_input(self, tmp_path):
        """Test that transactions_enriched handles empty input."""
        features = feature_transactions

        result = features.transactions_enriched(
            pd.DataFrame(),
            pd.DataFrame(),
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.parametrize(
        "month",
        ["2024-02", "2024/01", None],
    )
    def test_transactions_enriched_rejects_invalid_or_mismatched_month(self, tmp_path, month):
        features = feature_transactions
        source = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                    "month": month,
                }
            ]
        )

        with pytest.raises(ValueError, match="month must be YYYY-MM"):
            features.transactions_enriched(
                source,
                pd.DataFrame(),
                rental_yield=pd.DataFrame(),
                raw_macro_data={},
                raw_dwelling_units_by_town=pd.DataFrame(),
                raw_hdb_resident_population=pd.DataFrame(),
                raw_median_annual_value=pd.DataFrame(),
                raw_income_by_planning_area=pd.DataFrame(),
            )

    def test_transactions_enriched_enforces_freshness(self, tmp_path):
        features = feature_transactions
        source = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2020-01-15"),
                }
            ]
        )

        with pytest.raises(ValueError, match="latest transaction"):
            features.transactions_enriched(
                source,
                pd.DataFrame(),
                rental_yield=pd.DataFrame(),
                raw_macro_data={},
                raw_dwelling_units_by_town=pd.DataFrame(),
                raw_hdb_resident_population=pd.DataFrame(),
                raw_median_annual_value=pd.DataFrame(),
                raw_income_by_planning_area=pd.DataFrame(),
                max_transaction_age_days=30,
            )

    def test_transactions_enriched_preserves_nan_planning_area(self, tmp_path):
        """NaN planning areas must stay NaN, not become the literal string 'NAN'."""
        features = feature_transactions

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "floor_area_sqft": 1000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                    "remaining_lease_months": 960,
                },
            ]
        )
        location_dim = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "planning_area": None,
                    "dist_to_nearest_mrt": 300.0,
                    "region": "RCR",
                },
            ]
        )
        raw_income_by_planning_area = pd.DataFrame(
            [
                {"planning_area": "TOA PAYOH", "median_monthly_income": 9000.0},
            ]
        )

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim,
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=raw_income_by_planning_area,
        )

        assert not result.empty
        assert pd.isna(result.loc[0, "planning_area"])
        assert pd.isna(result.loc[0, "median_monthly_income"])

    def test_transactions_enriched_merges_rental_yield(self, tmp_path):
        """Production shape: rental_yield carries a constant flat_type="ALL"
        sentinel, so the join must fall through to (town, month).
        Regression: the 3-key candidate previously won and matched nothing."""
        features = feature_transactions

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "lat": 1.36,
                    "lon": 103.81,
                    "town": "TOA PAYOH",
                    "flat_type": "5 ROOM",
                    "price": 650000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-20"),
                },
            ]
        )

        rental_yield = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "month": "2024-01",
                    "flat_type": "ALL",
                    "rental_yield_pct": 4.5,
                },
            ]
        )

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim=pd.DataFrame(),
            rental_yield=rental_yield,
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
        )

        assert not result.empty
        assert result["rental_yield_pct"].notna().all()
        assert result["rental_yield_pct"].tolist() == pytest.approx([4.5, 4.5])

    def test_transactions_enriched_rental_yield_per_flat_type_wins(self, tmp_path):
        """Future shape: per-flat-type rental data keeps the 3-key merge.
        Distinct per-type yields prove (town, month, flat_type) matched, since a
        (town, month) fallback would collapse both rows onto one value."""
        features = feature_transactions

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "lat": 1.36,
                    "lon": 103.81,
                    "town": "TOA PAYOH",
                    "flat_type": "5 ROOM",
                    "price": 650000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-20"),
                },
            ]
        )

        rental_yield = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "month": "2024-01",
                    "flat_type": "4-ROOM",
                    "rental_yield_pct": 4.0,
                },
                {
                    "town": "TOA PAYOH",
                    "month": "2024-01",
                    "flat_type": "5 ROOM",
                    "rental_yield_pct": 5.5,
                },
            ]
        )

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim=pd.DataFrame(),
            rental_yield=rental_yield,
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
        )

        assert not result.empty
        by_type = result.set_index("flat_type")["rental_yield_pct"]
        assert by_type["4-ROOM"] == pytest.approx(4.0)
        assert by_type["5-ROOM"] == pytest.approx(5.5)

    def test_transactions_enriched_rental_yield_without_town_skips_merge(self, tmp_path):
        """Rental frame without town shares no merge candidate keys, so the
        merge is skipped without crashing and no yield column is added."""
        features = feature_transactions

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        rental_yield = pd.DataFrame(
            [
                {
                    "month": "2024-01",
                    "flat_type": "ALL",
                    "rental_yield_pct": 4.5,
                },
            ]
        )

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim=pd.DataFrame(),
            rental_yield=rental_yield,
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
        )

        assert not result.empty
        assert "rental_yield_pct" not in result.columns

    def test_transactions_enriched_merges_annual_value_with_raw_flat_types(self, tmp_path):
        """Annual-value merge must not depend on rental data being present.

        Regression: flat_type normalization previously ran only inside the
        rental-yield branch, so with an empty rental frame the raw spaced form
        ("4 ROOM") never matched the IRAS "4 Room" category and
        annual_value/property_tax were silently all-NaN."""
        features = feature_transactions

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        raw_median_annual_value = pd.DataFrame(
            [
                {
                    "type_of_hdb": "4 Room",
                    "median_annual_value": 7000,
                    "property_tax_collection": 1200,
                    "financial_year": 2024,
                },
            ]
        )

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim=pd.DataFrame(),
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=raw_median_annual_value,
            raw_income_by_planning_area=pd.DataFrame(),
        )

        assert not result.empty
        # flat_type is canonicalized regardless of rental data presence.
        assert result.loc[0, "flat_type"] == "4-ROOM"
        assert result["annual_value"].notna().all()
        assert result.loc[0, "annual_value"] == pytest.approx(7000)
        assert result["property_tax"].notna().all()
        assert result.loc[0, "property_tax"] == pytest.approx(1200)

    def test_transactions_enriched_merges_macro_indicators(self, tmp_path):
        """Batched macro merge: monthly + quarterly indicators resolve per row,
        partial-quarter coverage yields NA, and indicators with no data degrade
        to all-NA columns. Regression for the 8-merge -> 2-merge batching."""
        features = feature_transactions

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "lat": 1.36,
                    "lon": 103.81,
                    "price": 600000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-04-15"),
                },
            ]
        )

        macro = {
            "cpi": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "cpi": 100.0},
                    {"date": pd.Timestamp("2024-04-01"), "cpi": 101.0},
                ]
            ),
            "bank_rates": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "sora_3m": 3.0},
                    {"date": pd.Timestamp("2024-04-01"), "sora_3m": 3.5},
                ]
            ),
            # 'sora' intentionally absent -> sora_rate must be an all-NA column.
            "gdp": pd.DataFrame(
                [
                    {"quarter": pd.Timestamp("2024-03-31"), "gdp": 1000.0},
                    {"quarter": pd.Timestamp("2024-06-30"), "gdp": 1010.0},
                ]
            ),
            "unemployment": pd.DataFrame(
                [{"quarter": pd.Timestamp("2024-03-31"), "unemployment_rate": 2.0}]
            ),
            # 'hdb_rpi', 'ura_ppi', 'wage_growth' absent -> all-NA columns.
        }

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim=pd.DataFrame(),
            rental_yield=pd.DataFrame(),
            raw_macro_data=macro,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
        )

        assert len(result) == 2
        # Monthly indicators resolve per month.
        assert result.loc[0, "cpi"] == pytest.approx(100.0)
        assert result.loc[1, "cpi"] == pytest.approx(101.0)
        assert result.loc[0, "sora_3m"] == pytest.approx(3.0)
        assert result.loc[1, "sora_3m"] == pytest.approx(3.5)
        # Quarterly indicators resolve per quarter.
        assert result.loc[0, "gdp"] == pytest.approx(1000.0)
        assert result.loc[1, "gdp"] == pytest.approx(1010.0)
        # unemployment only has Q1 data -> the Q2 row is NA.
        assert result.loc[0, "unemployment_rate"] == pytest.approx(2.0)
        assert pd.isna(result.loc[1, "unemployment_rate"])
        # Indicators with no data degrade to NA columns (not missing columns).
        for na_col in ("sora_rate", "hdb_rpi", "ura_ppi", "wage_growth"):
            assert na_col in result.columns, f"{na_col} should exist as an NA column"
            assert result[na_col].isna().all(), f"{na_col} should be all-NA"

    def test_transactions_enriched_writes_nothing(self, tmp_path):
        """Materializer owns persistence — the computing node writes nothing (persist=False)."""
        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        result = feature_transactions.transactions_enriched(
            geocoded_validated,
            location_dim=pd.DataFrame(),
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
        )

        assert not result.empty
        assert list(tmp_path.rglob("*.parquet")) == []


class TestPlanningArea360:
    """Test the planning_area_360 entity table."""

    def test_basic_produces_expected_columns(self, tmp_path):
        """Test spatial medians and market stats are aggregated correctly."""
        features = feature_profiles

        location_dim = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "planning_area": "Toa Payoh",
                    "region": "RCR",
                    "dist_to_nearest_mrt": 300.0,
                    "dist_to_nearest_mall": 500.0,
                    "year_completed": 1990,
                    "max_floor_lvl": 25,
                    "total_dwelling_units": 100,
                },
            ]
        )
        transactions_enriched = pd.DataFrame(
            [
                {"planning_area": "Toa Payoh", "price": 500000.0, "psf": 500.0},
            ]
        )

        result = features.planning_area_360(
            location_dim,
            transactions_enriched,
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data={},
        )

        assert not result.empty
        assert result.loc[0, "planning_area"] == "Toa Payoh"
        assert "median_dist_to_mrt" in result.columns
        assert result.loc[0, "median_dist_to_mrt"] == pytest.approx(300.0)
        assert "median_price" in result.columns
        assert result.loc[0, "median_price"] == pytest.approx(500000.0)
        assert "avg_year_completed" in result.columns

    def test_empty_input_returns_empty(self, tmp_path):
        features = feature_profiles
        result = features.planning_area_360(
            pd.DataFrame(),
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data={},
        )
        assert result.empty

    def test_missing_planning_area_returns_empty(self, tmp_path):
        features = feature_profiles
        location_dim = pd.DataFrame([{"lat": 1.35, "lon": 103.8}])
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data={},
        )
        assert result.empty

    def test_income_merge(self, tmp_path):
        features = feature_profiles
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        income = pd.DataFrame([{"planning_area": "Toa Payoh", "median_monthly_income": 8000}])
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=income,
            raw_macro_data={},
        )
        assert not result.empty
        assert "median_monthly_income" in result.columns
        assert result.loc[0, "median_monthly_income"] == pytest.approx(8000)

    def test_macro_indicators_broadcast_latest(self, tmp_path):
        features = feature_profiles
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        macro = {
            "cpi": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "cpi": 104.5},
                    {"date": pd.Timestamp("2024-06-01"), "cpi": 105.0},
                ]
            ),
            "gdp": pd.DataFrame(
                [
                    {"quarter": pd.Timestamp("2024-03-31"), "gdp": 100.0},
                    {"quarter": pd.Timestamp("2024-06-30"), "gdp": 102.0},
                ]
            ),
        }
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data=macro,
        )
        assert not result.empty
        assert "cpi" in result.columns
        assert result.loc[0, "cpi"] == pytest.approx(105.0)
        assert "gdp" in result.columns
        assert result.loc[0, "gdp"] == pytest.approx(102.0)

    def test_macro_indicators_broadcast_all_keys(self, tmp_path):
        """All 4 macro keys broadcast their latest values."""
        features = feature_profiles
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        macro = {
            "cpi": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "cpi": 104.5},
                    {"date": pd.Timestamp("2024-06-01"), "cpi": 105.0},
                ]
            ),
            "bank_rates": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "sora_3m": 3.5},
                    {"date": pd.Timestamp("2024-06-01"), "sora_3m": 3.8},
                ]
            ),
            "unemployment": pd.DataFrame(
                [
                    {"quarter": pd.Timestamp("2024-03-31"), "unemployment_rate": 2.1},
                    {"quarter": pd.Timestamp("2024-06-30"), "unemployment_rate": 2.3},
                ]
            ),
            "gdp": pd.DataFrame(
                [
                    {"quarter": pd.Timestamp("2024-03-31"), "gdp": 100.0},
                    {"quarter": pd.Timestamp("2024-06-30"), "gdp": 102.0},
                ]
            ),
        }
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data=macro,
        )
        assert not result.empty
        assert result.loc[0, "cpi"] == pytest.approx(105.0)
        assert result.loc[0, "sora_3m"] == pytest.approx(3.8)
        assert result.loc[0, "unemployment_rate"] == pytest.approx(2.3)
        assert result.loc[0, "gdp"] == pytest.approx(102.0)

    def test_region_present(self, tmp_path):
        features = feature_profiles
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data={},
        )
        assert not result.empty
        assert "region" in result.columns
        assert result.loc[0, "region"] == "RCR"


class TestTown360:
    """Test the town_360 entity table."""

    def test_basic_produces_expected_columns(self, tmp_path):
        features = feature_profiles
        tx = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0, "psf": 500.0},
                {"town": "TOA PAYOH", "price": 520000.0, "psf": 520.0},
                {"town": "BEDOK", "price": 400000.0, "psf": 400.0},
            ]
        )
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
        )
        assert not result.empty
        assert len(result) == 2
        assert "median_price" in result.columns
        assert "transaction_volume" in result.columns

    def test_annual_value_broadcasts_to_all_rows(self, tmp_path):
        """Phase 1 fix: ALL rows must get the value, not just index[0]."""
        features = feature_profiles
        tx = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0},
                {"town": "BEDOK", "price": 400000.0},
                {"town": "ANG MO KIO", "price": 450000.0},
            ]
        )
        mav = pd.DataFrame(
            [
                {
                    "type_of_hdb": "3 Room",
                    "median_annual_value": 5000,
                    "property_tax_collection": 800,
                    "financial_year": 2024,
                },
                {
                    "type_of_hdb": "4 Room",
                    "median_annual_value": 7000,
                    "property_tax_collection": 1200,
                    "financial_year": 2024,
                },
                {
                    "type_of_hdb": "5 Room",
                    "median_annual_value": 9000,
                    "property_tax_collection": 1600,
                    "financial_year": 2024,
                },
            ]
        )
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=mav,
        )
        assert not result.empty
        assert "annual_value_3_room" in result.columns
        assert "annual_value_4_room" in result.columns
        assert "annual_value_5_room" in result.columns
        assert result["annual_value_3_room"].notna().all()
        assert result["annual_value_4_room"].notna().all()
        assert result["annual_value_5_room"].notna().all()
        assert (result["annual_value_3_room"] == 5000).all()
        assert (result["annual_value_4_room"] == 7000).all()
        assert (result["annual_value_5_room"] == 9000).all()
        assert (result["property_tax_3_room"] == 800).all()

    def test_title_case_output(self, tmp_path):
        features = feature_profiles
        tx = pd.DataFrame([{"town": "TOA PAYOH", "price": 500000.0}])
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
        )
        assert result.loc[0, "town"] == "Toa Payoh"

    def test_empty_input_returns_empty(self, tmp_path):
        features = feature_profiles
        result = features.town_360(
            pd.DataFrame(),
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
        )
        assert result.empty

    def test_missing_town_column_returns_empty(self, tmp_path):
        features = feature_profiles
        tx = pd.DataFrame([{"price": 500000.0}])
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
        )
        assert result.empty

    def test_no_annual_value_source_creates_na_columns(self, tmp_path):
        """When raw_median_annual_value is empty, per-flat-type columns default to NA."""
        features = feature_profiles
        tx = pd.DataFrame([{"town": "TOA PAYOH", "price": 500000.0}])
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
        )
        assert not result.empty
        for col in (
            "annual_value_3_room",
            "annual_value_4_room",
            "annual_value_5_room",
            "property_tax_3_room",
            "property_tax_4_room",
            "property_tax_5_room",
        ):
            assert col in result.columns
            assert result[col].isna().all()


class TestBlockProfile:
    """Test the block_profile entity table."""

    def test_basic_aggregates_by_block_street(self, tmp_path):
        features = feature_profiles
        tx = pd.DataFrame(
            [
                {
                    "block": "123",
                    "street_name": "LOR 1",
                    "price": 500000.0,
                    "psf": 500.0,
                    "remaining_lease_years": 80.0,
                    "town": "TOA PAYOH",
                },
                {
                    "block": "123",
                    "street_name": "LOR 1",
                    "price": 520000.0,
                    "psf": 520.0,
                    "remaining_lease_years": 80.0,
                    "town": "TOA PAYOH",
                },
                {
                    "block": "456",
                    "street_name": "NTH RD",
                    "price": 400000.0,
                    "psf": 400.0,
                    "remaining_lease_years": 70.0,
                    "town": "BEDOK",
                },
            ]
        )
        result = features.block_profile(tx)
        assert not result.empty
        assert len(result) == 2
        assert "median_price" in result.columns
        assert "transaction_count" in result.columns
        assert "median_psf" in result.columns
        assert "avg_remaining_lease_years" in result.columns

    def test_missing_block_column_returns_empty(self, tmp_path):
        features = feature_profiles
        tx = pd.DataFrame([{"price": 500000.0}])
        result = features.block_profile(tx)
        assert result.empty

    def test_empty_input_returns_empty(self, tmp_path):
        features = feature_profiles
        result = features.block_profile(pd.DataFrame())
        assert result.empty


class TestLegacyShimRemoved:
    """The features module no longer re-exports other modules' nodes."""

    @pytest.mark.parametrize(
        "name",
        [
            "rental_yield",
            "transactions_enriched",
            "_enforce_transaction_time_contract",
            "planning_area_360",
            "town_360",
            "block_profile",
        ],
    )
    def test_shim_names_not_resolvable(self, name):
        assert not hasattr(features, name)

    def test_real_modules_expose_the_nodes(self):
        assert callable(feature_rental.rental_yield)
        assert callable(feature_transactions.transactions_enriched)
        assert callable(feature_profiles.planning_area_360)
        assert callable(feature_profiles.town_360)
        assert callable(feature_profiles.block_profile)

    def test_location_dim_still_lives_in_features(self):
        assert callable(features.location_dim)


class TestGoldSchemaContract:
    """WS9: gold schemas match reality — dead fields out, produced fields in."""

    def test_dead_fields_removed_from_feature_transaction(self):
        from egg_n_bacon_housing.schemas.feature_models import HFeatureTransaction

        fields = HFeatureTransaction.model_fields
        assert "school_tier" not in fields
        assert "mrt_line" not in fields
        # WS17: no producer ever emitted the nearest-school name.
        assert "nearest_school" not in fields

    def test_feature_transaction_round_trip_without_dead_fields(self):
        from egg_n_bacon_housing.schemas.feature_models import HFeatureTransaction

        original = HFeatureTransaction(
            transaction_date=pd.Timestamp("2024-01-15"),
            price=500000.0,
            lat=1.35,
            lon=103.82,
            property_type="hdb",
        )

        reconstructed = HFeatureTransaction(**original.model_dump())

        assert reconstructed == original

    def test_location_dim_validates_produced_mrt_fields(self):
        from egg_n_bacon_housing.schemas.feature_models import LocationDimRecord

        record = LocationDimRecord(
            lat=1.35,
            lon=103.82,
            nearest_mrt_tier=2,
            nearest_mrt_is_interchange=True,
            nearest_mrt_score=7.5,
        )
        assert record.nearest_mrt_tier == 2
        assert record.nearest_mrt_is_interchange is True

        # Degraded MRT paths may omit them entirely.
        missing = LocationDimRecord(lat=1.35, lon=103.82)
        assert missing.nearest_mrt_tier is None
        assert missing.nearest_mrt_is_interchange is None
        assert missing.nearest_mrt_score is None

    @pytest.mark.parametrize(
        ("model_name", "factory"),
        [
            (
                "PlanningArea360",
                lambda median_price, median_psf: {
                    "planning_area": "Toa Payoh",
                    "median_price": median_price,
                    "median_psf": median_psf,
                },
            ),
            (
                "Town360",
                lambda median_price, median_psf: {
                    "town": "Toa Payoh",
                    "median_price": median_price,
                    "median_psf": median_psf,
                },
            ),
            (
                "BlockProfile",
                lambda median_price, median_psf: {
                    "block": "123",
                    "street_name": "LOR 1",
                    "median_price": median_price,
                    "median_psf": median_psf,
                },
            ),
        ],
    )
    def test_profile_medians_must_be_positive_or_null(self, model_name, factory):
        import pydantic

        from egg_n_bacon_housing.schemas import feature_models

        model = getattr(feature_models, model_name)

        with pytest.raises(pydantic.ValidationError):
            model(**factory(-1.0, None))
        with pytest.raises(pydantic.ValidationError):
            model(**factory(None, 0.0))

        valid = model(**factory(500000.0, 500.0))
        assert valid.median_price == pytest.approx(500000.0)

        nullable = model(**factory(None, None))
        assert nullable.median_price is None
        assert nullable.median_psf is None

    def test_profile_medians_nan_maps_to_null_through_validate_schema(self):
        """NaN medians (left-join misses) must survive validation as nulls."""
        from egg_n_bacon_housing.schemas.feature_models import BlockProfile
        from egg_n_bacon_housing.utils.validation import validate_schema

        df = pd.DataFrame([{"block": "123", "street_name": "LOR 1", "median_price": float("nan")}])

        valid_df, quarantine_df = validate_schema(df, BlockProfile, "block_profile")

        assert quarantine_df.empty
        assert len(valid_df) == 1

    def test_rental_yield_sample_size_must_be_at_least_one(self):
        import pydantic

        from egg_n_bacon_housing.schemas.feature_models import HRentalYieldRecord

        base = dict(
            planning_area=None,
            town="TOA PAYOH",
            property_type="HDB",
            flat_type="ALL",
            median_price=500000.0,
            median_rent=3500.0,
            rental_yield_pct=0.84,
            month="2024-01",
        )

        with pytest.raises(pydantic.ValidationError):
            HRentalYieldRecord(**base, sample_size=0)

        assert HRentalYieldRecord(**base, sample_size=1).sample_size == 1

    def test_location_dim_rejects_wrong_type_mrt_tier(self):
        from egg_n_bacon_housing.schemas.feature_models import LocationDimRecord
        from egg_n_bacon_housing.utils.validation import validate_schema

        df = pd.DataFrame(
            [
                {"lat": 1.35, "lon": 103.82, "nearest_mrt_tier": 2},
                {"lat": 1.36, "lon": 103.83, "nearest_mrt_tier": "not-a-number"},
            ]
        )

        valid_df, quarantine_df = validate_schema(df, LocationDimRecord, "location_dim")

        assert len(valid_df) == 1
        assert len(quarantine_df) == 1


class TestAnnualValueTypeMapping:
    """WO-9: vectorized IRAS type_of_hdb lookup (dict .map + compact fallback)
    must match the retired per-row ``_map_flat_type_for_annual_value``."""

    def test_canonical_forms_map_directly(self):
        # Canonical dashed-upper forms (normalize_hdb_flat_type output) are
        # the production fast path — one dict .map, no per-row apply.
        s = pd.Series(
            ["1-ROOM", "2-ROOM", "3-ROOM", "4-ROOM", "5-ROOM", "EXECUTIVE", "MULTI-GENERATION"]
        )
        result = feature_transactions._annual_value_type_series(s)
        assert list(result) == [
            "1 or 2 Room",
            "1 or 2 Room",
            "3 Room",
            "4 Room",
            "5 Room",
            "Executive & Others",
            "Executive & Others",
        ]

    def test_raw_spaced_and_lowercase_forms_still_map(self):
        # Defense in depth: raw forms that skipped normalization go through
        # the dash/space-insensitive compact fallback, same as before.
        s = pd.Series(["4 ROOM", "4 room", "4Room", "MULTI GENERATION", "2 room"])
        result = feature_transactions._annual_value_type_series(s)
        assert list(result) == [
            "4 Room",
            "4 Room",
            "4 Room",
            "Executive & Others",
            "1 or 2 Room",
        ]

    def test_unknown_values_fall_back_to_strip_upper_form(self):
        s = pd.Series(["apartment", " APARTMENT "])
        result = feature_transactions._annual_value_type_series(s)
        assert list(result) == ["APARTMENT", "APARTMENT"]

    def test_null_flat_type_yields_null_category(self):
        # Null in -> null out (the retired scalar returned "NAN", which also
        # never matched an IRAS category — identical merge outcome).
        s = pd.Series(["4-ROOM", None, float("nan")], dtype=object)
        result = feature_transactions._annual_value_type_series(s)
        assert result.iloc[0] == "4 Room"
        assert list(result.isna()) == [False, True, True]


class TestRegionDerivation:
    """WO-9: vectorized region derivation must match the per-row
    get_region_for_planning_area semantics (strip/upper lookup, unknown and
    null planning areas pass through as None)."""

    def test_location_dim_derives_region_vectorized(self, tmp_path, monkeypatch):
        class _RegionSpatialReference:
            # Derived planning areas in mixed case/whitespace, an unknown
            # area, and a null (point outside all polygons).
            def planning_areas_for_points(self, lat, lon):
                return pd.Series(["Toa Payoh", "  bedok ", "ATLANTIS", None])

        geocoded_validated = pd.DataFrame(
            [
                {"lat": 1.35, "lon": 103.80},
                {"lat": 1.36, "lon": 103.82},
                {"lat": 1.37, "lon": 103.84},
                {"lat": 1.38, "lon": 103.86},
            ]
        )

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            geocoder=InMemoryGeocoder({}),
            spatial_reference=_RegionSpatialReference(),
            **_empty_poi_args(),
        )

        assert len(result) == 4
        assert list(result["region"]) == ["RCR", "OCR", None, None]


class _StubSchoolReference:
    """Minimal SchoolReference protocol implementation for DI tests."""

    def __init__(self, primary, secondary):
        self._tiers = (primary, secondary)

    def load_school_tiers(self):
        return self._tiers


_TIER_PRIMARY = pd.DataFrame(
    [{"school_name": "TOP PRIMARY", "gep": "Yes", "sap": "No", "tier": 1, "popularity_p2b": 1.2}]
)
_TIER_SECONDARY = pd.DataFrame(
    [
        {
            "school_name": "TOP SECONDARY",
            "track": "IP",
            "tier": 1,
            "ip_cutoff_2026": "7-8",
            "sap": "No",
            "autonomous": "No",
            "ip": "Yes",
            "awards": "",
        }
    ]
)
_SCHOOLS_WITH_COORDS = pd.DataFrame(
    [
        {
            "school_name": "TOP PRIMARY",
            "latitude": 1.300 + 0.001,
            "longitude": 103.850,
            "mainlevel_code": "PRIMARY",
        },
        {
            "school_name": "TOP SECONDARY",
            "latitude": 1.300 + 0.002,
            "longitude": 103.850,
            "mainlevel_code": "SECONDARY (S1-S5)",
        },
    ]
)


class TestLocationDimSchoolQuality:
    """WO-11: tier-weighted school quality features flow through location_dim."""

    def _geocoded(self):
        return pd.DataFrame(
            [{"lat": 1.300, "lon": 103.850, "town": "TOA PAYOH", "price": 500000.0}]
        )

    def test_school_reference_populates_quality_columns(self, tmp_path, monkeypatch):
        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        result = features.location_dim(
            self._geocoded(),
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=_SCHOOLS_WITH_COORDS,
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            geocoder=InMemoryGeocoder({}),
            school_reference=_StubSchoolReference(_TIER_PRIMARY, _TIER_SECONDARY),
            **_empty_poi_args(),
        )

        from egg_n_bacon_housing.utils.school_features import QUALITY_FEATURE_COLUMNS

        for col in QUALITY_FEATURE_COLUMNS:
            assert col in result.columns, col
            assert result[col].notna().all(), col
        # Schema-validated end to end: the record round-trips.
        assert result["school_accessibility_score"].iloc[0] > 0

    def test_empty_tiers_degrade_to_na_with_warning(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        with caplog.at_level("WARNING"):
            result = features.location_dim(
                self._geocoded(),
                raw_mrt_stations=pd.DataFrame(),
                raw_school_directory=_SCHOOLS_WITH_COORDS,
                raw_shopping_malls=pd.DataFrame(),
                raw_hdb_property_info=pd.DataFrame(),
                geocoder=InMemoryGeocoder({}),
                school_reference=_StubSchoolReference(pd.DataFrame(), pd.DataFrame()),
                **_empty_poi_args(),
            )

        from egg_n_bacon_housing.utils.school_features import QUALITY_FEATURE_COLUMNS

        for col in QUALITY_FEATURE_COLUMNS:
            assert col in result.columns, col
            assert result[col].isna().all(), col
        assert any("school tier data unavailable" in r.message for r in caplog.records)

    def test_no_school_reference_degrades_to_na(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        with caplog.at_level("WARNING"):
            result = features.location_dim(
                self._geocoded(),
                raw_mrt_stations=pd.DataFrame(),
                raw_school_directory=_SCHOOLS_WITH_COORDS,
                raw_shopping_malls=pd.DataFrame(),
                raw_hdb_property_info=pd.DataFrame(),
                geocoder=InMemoryGeocoder({}),
                **_empty_poi_args(),
            )

        assert result["school_accessibility_score"].isna().all()
        assert any("school tier data unavailable" in r.message for r in caplog.records)


class TestPriceStratum:
    """WO-11: price_stratum is populated as a deterministic population quintile."""

    def _run(self, prices, tmp_path):
        features = feature_transactions
        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.30 + i * 0.001,
                    "lon": 103.85,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "price": price,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                }
                for i, price in enumerate(prices)
            ]
        )
        location_dim = pd.DataFrame(
            [
                {"lat": 1.30 + i * 0.001, "lon": 103.85, "planning_area": "TOA PAYOH"}
                for i in range(len(prices))
            ]
        )
        return features.transactions_enriched(
            geocoded_validated,
            location_dim,
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
        )

    def test_quintile_strata_deterministic(self, tmp_path):
        prices = [200_000.0 * (i + 1) for i in range(10)]  # 200k..2M
        result = self._run(prices, tmp_path)

        assert result["price_stratum"].notna().all()
        assert result.loc[0, "price_stratum"] == "Q1"  # cheapest
        assert result.loc[len(prices) - 1, "price_stratum"] == "Q5"  # priciest
        assert set(result["price_stratum"]) == {"Q1", "Q2", "Q3", "Q4", "Q5"}
        # Deterministic: same input → same strata.
        again = self._run(prices, tmp_path)
        assert list(again["price_stratum"]) == list(result["price_stratum"])

    def test_single_price_degrades_to_na(self, tmp_path):
        result = self._run([500_000.0, 500_000.0, 500_000.0], tmp_path)
        assert result["price_stratum"].isna().all()
