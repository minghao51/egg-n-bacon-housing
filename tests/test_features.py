"""Test 03_features component."""

import importlib
import pandas as pd
import pytest


def _get_features_module():
    """Get the 03_features module."""
    return importlib.import_module("egg_n_bacon_housing.components.03_features")


class TestGoldLayer:
    """Test gold layer feature engineering functions."""

    def test_rental_yield_returns_dataframe(self):
        """Test that rental_yield returns a DataFrame."""
        features = _get_features_module()

        hdb_validated = pd.DataFrame([{
            "town": "TOA PAYOH",
            "price": 500000.0,
        }])

        raw_rental_index = pd.DataFrame([{
            "month": "2023-01",
            "rental_index": 100.0,
        }])

        result = features.rental_yield(hdb_validated, raw_rental_index)

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "town" in result.columns
            assert "rental_yield_pct" in result.columns

    def test_rental_yield_with_empty_input(self):
        """Test that rental_yield handles empty input."""
        features = _get_features_module()

        hdb_validated = pd.DataFrame()
        raw_rental_index = pd.DataFrame()

        result = features.rental_yield(hdb_validated, raw_rental_index)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_features_with_amenities_returns_dataframe(self):
        """Test that features_with_amenities returns a DataFrame."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame([{
            "lat": 1.35,
            "lon": 103.8,
            "property_type": "hdb",
            "address": "123 TOA PAYOH LOR 1",
        }])

        raw_school_directory = pd.DataFrame([{
            "lat": 1.36,
            "lon": 103.82,
            "school_name": "Test School",
        }])

        result = features.features_with_amenities(geocoded_validated, raw_school_directory)

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "lat" in result.columns
            assert "lon" in result.columns

    def test_features_with_amenities_with_empty_geocoded(self):
        """Test that features_with_amenities handles empty geocoded data."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame()
        raw_school_directory = pd.DataFrame([{
            "lat": 1.36,
            "lon": 103.82,
            "school_name": "Test School",
        }])

        result = features.features_with_amenities(geocoded_validated, raw_school_directory)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_unified_features_returns_dataframe(self):
        """Test that unified_features returns a DataFrame."""
        features = _get_features_module()

        features_with_amenities = pd.DataFrame([{
            "town": "TOA PAYOH",
            "lat": 1.35,
            "lon": 103.8,
        }])

        rental_yield = pd.DataFrame([{
            "town": "TOA PAYOH",
            "rental_yield_pct": 0.48,
        }])

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
