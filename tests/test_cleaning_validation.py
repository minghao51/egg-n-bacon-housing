"""Test schema validation in 02_cleaning.py."""

import importlib

import pandas as pd
import pytest


def _get_cleaning_module():
    """Get the 02_cleaning module."""
    return importlib.import_module("egg_n_bacon_housing.components.02_cleaning")


class TestHDBValidation:
    """Test HDB transaction validation."""

    def test_hdb_validated_with_valid_data(self):
        """Test that valid HDB transactions pass validation."""
        cleaning = _get_cleaning_module()

        valid_data = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": 500000.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "planning_area": "Toa Payoh",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "storey_min": 4,
                    "storey_max": 6,
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                    "remaining_lease_months": 960,
                    "address": "123 TOA PAYOH LOR 1",
                },
            ]
        )

        result = cleaning.hdb_validated(valid_data)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["price"] == 500000.0

    def test_hdb_validated_with_invalid_price(self):
        """Test that transactions with invalid price fail validation."""
        cleaning = _get_cleaning_module()

        invalid_data = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": -100.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "planning_area": "Toa Payoh",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "storey_min": 4,
                    "storey_max": 6,
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                    "remaining_lease_months": 960,
                    "address": "123 TOA PAYOH LOR 1",
                },
            ]
        )

        result = cleaning.hdb_validated(invalid_data)

        assert result.empty

    def test_hdb_validated_with_empty_dataframe(self):
        """Test that empty DataFrame is handled correctly."""
        cleaning = _get_cleaning_module()

        empty_data = pd.DataFrame()

        result = cleaning.hdb_validated(empty_data)

        assert result.empty

    def test_cleaned_hdb_transactions_fills_remaining_lease_in_months(self, tmp_path, monkeypatch):
        """Test missing remaining_lease_months is backfilled in months, not years."""
        cleaning = _get_cleaning_module()

        monkeypatch.setattr(cleaning, "silver_dir", lambda: tmp_path)

        raw_data = pd.DataFrame(
            [
                {
                    "month": "2024-01",
                    "resale_price": 500000.0,
                    "lease_commence_date": 2000,
                    "remaining_lease_months": pd.NA,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "floor_area_sqm": 90.0,
                }
            ]
        )

        result = cleaning.cleaned_hdb_transactions(raw_data)

        assert not result.empty
        assert result.loc[0, "remaining_lease_months"] == 900


class TestCondoValidation:
    """Test condo transaction validation."""

    def test_condo_validated_with_valid_data(self):
        """Test that valid condo transactions pass validation."""
        cleaning = _get_cleaning_module()

        valid_data = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": 1500000.0,
                    "lat": 1.30,
                    "lon": 103.8,
                    "property_type": "condo",
                    "planning_area": "Orchard",
                    "project_name": "Orchard Residences",
                    "area": "Central",
                    "postal_district": 9,
                    "tenure": "Freehold",
                    "floor_area_sqm": 120.0,
                    "floor_area_sqft": 1292.0,
                    "address": "1 ORCHARD ROAD",
                },
            ]
        )

        result = cleaning.condo_validated(valid_data)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["price"] == 1500000.0


class TestGeocodedValidation:
    """Test geocoded property validation."""

    def test_geocoded_validated_with_valid_data(self):
        """Test that valid geocoded properties pass validation."""
        cleaning = _get_cleaning_module()

        valid_data = pd.DataFrame(
            [
                {
                    "address": "123 TOA PAYOH LOR 1",
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "postal_code": "312345",
                    "search_confidence": 0.95,
                },
            ]
        )

        result = cleaning.geocoded_validated(valid_data)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["lat"] == 1.35

    def test_geocoded_validated_with_invalid_coordinates(self):
        """Test that invalid coordinates fail validation."""
        cleaning = _get_cleaning_module()

        invalid_data = pd.DataFrame(
            [
                {
                    "address": "123 TOA PAYOH LOR 1",
                    "lat": 91.0,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "postal_code": "312345",
                    "search_confidence": 0.95,
                },
            ]
        )

        result = cleaning.geocoded_validated(invalid_data)

        assert result.empty

    def test_geocoded_properties_raises_when_coordinate_columns_missing(self):
        """Test geocoded_properties fails fast when lat/lon columns are missing."""
        cleaning = _get_cleaning_module()

        hdb_validated = pd.DataFrame([{"town": "TOA PAYOH", "price": 500000.0}])
        condo_validated = pd.DataFrame()

        with pytest.raises(ValueError, match="lat/lon columns are missing"):
            cleaning.geocoded_properties(hdb_validated, condo_validated)

    def test_geocoded_properties_raises_on_low_coordinate_coverage(self, monkeypatch):
        """Test geocoded_properties enforces minimum coordinate coverage."""
        cleaning = _get_cleaning_module()

        monkeypatch.setattr(cleaning.settings.geocoding, "min_coordinate_coverage", 0.8)

        hdb_validated = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0, "lat": 1.35, "lon": 103.8},
                {"town": "ANG MO KIO", "price": 600000.0, "lat": pd.NA, "lon": 103.84},
            ]
        )
        condo_validated = pd.DataFrame()

        with pytest.raises(ValueError, match="Geocoding coverage too low"):
            cleaning.geocoded_properties(hdb_validated, condo_validated)
