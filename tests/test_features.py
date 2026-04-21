"""Test 03_features component."""

import importlib

import numpy as np
import pandas as pd
import pytest


def _get_features_module():
    """Get the 03_features module."""
    return importlib.import_module("egg_n_bacon_housing.components.03_features")


class TestGoldLayer:
    """Test gold layer feature engineering functions."""

    def test_rental_yield_uses_rental_transactions_instead_of_placeholder(self):
        """Test that rental yield is derived from observed rent and sale data."""
        features = _get_features_module()

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
        assert result.loc[0, "rental_index"] == pytest.approx(108.2)
        assert result.loc[0, "rental_yield_pct"] == pytest.approx((3500 * 12 / 510000) * 100)
        assert result.loc[0, "rental_yield_pct"] != pytest.approx(0.48)

    def test_rental_yield_with_empty_input(self):
        """Test that rental_yield handles empty input."""
        features = _get_features_module()

        hdb_validated = pd.DataFrame()
        raw_hdb_rental = pd.DataFrame()
        raw_rental_index = pd.DataFrame()

        result = features.rental_yield(hdb_validated, raw_hdb_rental, raw_rental_index)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_features_with_amenities_derives_real_feature_columns(self, monkeypatch):
        """Test that amenity features come from helper outputs, not placeholders."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "address": "123 TOA PAYOH LOR 1",
                    "price": 500000.0,
                    "floor_area_sqft": 1000.0,
                    "remaining_lease_months": 960,
                }
            ]
        )

        raw_school_directory = pd.DataFrame(
            [
                {
                    "latitude": 1.36,
                    "longitude": 103.82,
                    "school_name": "Test School",
                    "mainlevel_code": "PRIMARY",
                }
            ]
        )
        raw_shopping_malls = pd.DataFrame(
            [
                {
                    "shopping_mall": "Toa Payoh Mall",
                    "lat": 1.351,
                    "lon": 103.801,
                }
            ]
        )

        def fake_school_features(properties_df, schools_df):
            enriched = properties_df.copy()
            enriched["nearest_schoolPRIMARY_dist"] = 123.0
            enriched["nearest_schoolPRIMARY_name"] = "Test School"
            return enriched

        def fake_load_mrt_stations():
            return pd.DataFrame([{"name": "Toa Payoh", "lat": 1.332, "lon": 103.847}])

        def fake_calculate_nearest_mrt(properties_df, mrt_stations_df, show_progress):
            enriched = properties_df.copy()
            enriched["nearest_mrt_distance"] = 456.0
            enriched["nearest_mrt_name"] = "Toa Payoh"
            return enriched

        monkeypatch.setattr(features, "calculate_school_features", fake_school_features)
        monkeypatch.setattr(features, "load_mrt_stations", fake_load_mrt_stations)
        monkeypatch.setattr(features, "calculate_nearest_mrt", fake_calculate_nearest_mrt)

        result = features.features_with_amenities(
            geocoded_validated,
            raw_school_directory,
            raw_shopping_malls,
        )

        assert isinstance(result, pd.DataFrame)
        assert result.loc[0, "dist_to_nearest_school"] == pytest.approx(123.0)
        assert result.loc[0, "dist_to_nearest_mrt"] == pytest.approx(456.0)
        assert result.loc[0, "nearest_mrt_station"] == "Toa Payoh"
        assert result.loc[0, "nearest_mall"] == "Toa Payoh Mall"
        assert result.loc[0, "dist_to_nearest_mall"] > 0
        assert result.loc[0, "psf"] == pytest.approx(500.0)
        assert result.loc[0, "remaining_lease_years"] == pytest.approx(80.0)

    def test_features_with_amenities_with_empty_geocoded(self):
        """Test that features_with_amenities handles empty geocoded data."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame()
        raw_school_directory = pd.DataFrame(
            [
                {
                    "latitude": 1.36,
                    "longitude": 103.82,
                    "school_name": "Test School",
                }
            ]
        )
        raw_shopping_malls = pd.DataFrame()

        result = features.features_with_amenities(
            geocoded_validated,
            raw_school_directory,
            raw_shopping_malls,
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_features_with_amenities_leaves_mall_distance_empty_without_coordinates(
        self, monkeypatch
    ):
        """Test that mall distance is not fabricated when source coordinates are missing."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "price": 500000.0, "floor_area_sqft": 1000.0}]
        )
        raw_school_directory = pd.DataFrame()
        raw_shopping_malls = pd.DataFrame([{"shopping_mall": "Name Only Mall"}])

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "load_mrt_stations", lambda: pd.DataFrame())
        monkeypatch.setattr(
            features,
            "calculate_nearest_mrt",
            lambda properties_df, mrt_stations_df, show_progress: properties_df.assign(
                nearest_mrt_distance=np.nan,
                nearest_mrt_name=pd.NA,
            ),
        )

        result = features.features_with_amenities(
            geocoded_validated,
            raw_school_directory,
            raw_shopping_malls,
        )

        assert pd.isna(result.loc[0, "dist_to_nearest_mall"])
        assert pd.isna(result.loc[0, "nearest_mall"])

    def test_unified_features_returns_dataframe(self):
        """Test that unified_features returns a DataFrame."""
        features = _get_features_module()

        features_with_amenities = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "lat": 1.35,
                    "lon": 103.8,
                }
            ]
        )

        rental_yield = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "rental_yield_pct": 0.48,
                }
            ]
        )

        result = features.unified_features(features_with_amenities, rental_yield)

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "town" in result.columns

    def test_unified_features_with_empty_input(self):
        """Test that unified_features handles empty input."""
        features = _get_features_module()

        features_with_amenities = pd.DataFrame()
        rental_yield = pd.DataFrame()

        result = features.unified_features(features_with_amenities, rental_yield)

        assert isinstance(result, pd.DataFrame)
        assert result.empty
