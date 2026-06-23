"""Test schema validation in 02_cleaning.py."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder
from egg_n_bacon_housing.utils.layer_writer import SimpleWriter

pytestmark = pytest.mark.unit


def _get_cleaning_module():
    """Get the 02_cleaning module."""
    from egg_n_bacon_housing.components import cleaning

    return cleaning


class TestHDBValidation:
    """Test HDB transaction validation."""

    def test_hdb_validated_with_valid_data(self, tmp_path):
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

        result = cleaning.hdb_validated(valid_data, silver_dir=tmp_path)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["price"] == 500000.0

    def test_hdb_validated_with_invalid_price(self, tmp_path):
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

        result = cleaning.hdb_validated(invalid_data, silver_dir=tmp_path)

        assert result.empty

    def test_hdb_validated_with_empty_dataframe(self, tmp_path):
        """Test that empty DataFrame is handled correctly."""
        cleaning = _get_cleaning_module()

        empty_data = pd.DataFrame()

        result = cleaning.hdb_validated(empty_data, silver_dir=tmp_path)

        assert result.empty

    def test_cleaned_hdb_transactions_fills_remaining_lease_in_months(self, tmp_path):
        """Test missing remaining_lease_months is backfilled in months, not years."""
        cleaning = _get_cleaning_module()

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

        result = cleaning.cleaned_hdb_transactions(raw_data, silver_dir=tmp_path)

        assert not result.empty
        assert result.loc[0, "remaining_lease_months"] == 900

    def test_cleaned_hdb_transactions_requires_month_column(self, tmp_path):
        cleaning = _get_cleaning_module()
        with pytest.raises(ValueError, match="missing required columns"):
            cleaning.cleaned_hdb_transactions(
                pd.DataFrame([{"resale_price": 500000.0}]), silver_dir=tmp_path
            )

    def test_cleaned_hdb_transactions_derives_storey_and_address(self, tmp_path):
        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {
                    "month": "2024-01",
                    "resale_price": 500000.0,
                    "storey_range": "04 TO 06",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                }
            ]
        )

        result = cleaning.cleaned_hdb_transactions(raw_data, silver_dir=tmp_path)

        assert result.loc[0, "storey_min"] == 4
        assert result.loc[0, "storey_max"] == 6
        assert result.loc[0, "address"] == "123 TOA PAYOH LOR 1"


class TestCondoValidation:
    """Test condo transaction validation."""

    def test_condo_validated_with_valid_data(self, tmp_path):
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

        result = cleaning.condo_validated(valid_data, silver_dir=tmp_path)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["price"] == 1500000.0

    def test_cleaned_condo_transactions_requires_price_column(self, tmp_path):
        cleaning = _get_cleaning_module()
        with pytest.raises(ValueError, match="missing required columns"):
            cleaning.cleaned_condo_transactions(
                pd.DataFrame([{"date": "2023-01-01", "project_name": "X"}]), silver_dir=tmp_path
            )

    def test_cleaned_condo_transactions_fills_defaults_and_normalizes_types(self, tmp_path):
        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {
                    "price": "1500000",
                    "date": "2024-01-15",
                    "area_sqft": "1292",
                    "area_sqm": "120",
                    "postal_district": "9",
                    "street_name": "ORCHARD ROAD",
                }
            ]
        )

        result = cleaning.cleaned_condo_transactions(raw_data, silver_dir=tmp_path)

        assert result.loc[0, "price"] == pytest.approx(1500000.0)
        assert result.loc[0, "floor_area_sqft"] == pytest.approx(1292.0)
        assert result.loc[0, "floor_area_sqm"] == pytest.approx(120.0)
        assert result.loc[0, "postal_district"] == 9
        assert result.loc[0, "address"] == "ORCHARD ROAD"
        assert result.loc[0, "area"] == ""
        assert result.loc[0, "project_name"] == ""


class TestGeocodedValidation:
    """Test geocoded property validation."""

    def test_geocoded_validated_with_valid_data(self, tmp_path):
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

        result = cleaning.geocoded_validated(valid_data, silver_dir=tmp_path)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["lat"] == 1.35

    def test_geocoded_validated_with_invalid_coordinates(self, tmp_path):
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

        result = cleaning.geocoded_validated(invalid_data, silver_dir=tmp_path)

        assert result.empty

    def test_geocoded_properties_fills_na_when_coordinate_columns_missing(self, tmp_path):
        """Test geocoded_properties fills lat/lon with NA when columns missing."""
        cleaning = _get_cleaning_module()

        hdb_validated = pd.DataFrame([{"town": "TOA PAYOH", "price": 500000.0}])
        condo_validated = pd.DataFrame()

        result = cleaning.geocoded_properties(
            hdb_validated,
            condo_validated,
            silver_dir=tmp_path,
            writer=SimpleWriter(tmp_path),
            geocoder=InMemoryGeocoder({}),
        )

        assert not result.empty
        assert "lat" in result.columns
        assert "lon" in result.columns
        assert pd.isna(result.loc[0, "lat"])

    def test_geocoded_properties_warns_on_low_coordinate_coverage(self, tmp_path):
        """Test geocoded_properties logs warning when coverage is low."""
        cleaning = _get_cleaning_module()

        hdb_validated = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0, "lat": 1.35, "lon": 103.8},
                {"town": "ANG MO KIO", "price": 600000.0, "lat": pd.NA, "lon": 103.84},
            ]
        )
        condo_validated = pd.DataFrame()

        result = cleaning.geocoded_properties(
            hdb_validated,
            condo_validated,
            silver_dir=tmp_path,
            writer=SimpleWriter(tmp_path),
            geocoder=InMemoryGeocoder({}),
            min_coordinate_coverage=0.8,
        )

        assert not result.empty
        assert len(result) == 2

    def test_geocoded_properties_returns_cached_geocoded_file(self, tmp_path):
        cleaning = _get_cleaning_module()
        cached = pd.DataFrame([{"address": "123 TOA PAYOH", "lat": 1.35, "lon": 103.8}])
        cached.to_parquet(tmp_path / "geocoded_properties.parquet", index=False)

        result = cleaning.geocoded_properties(
            pd.DataFrame([{"address": "123 TOA PAYOH"}]),
            pd.DataFrame(),
            silver_dir=tmp_path,
            writer=SimpleWriter(tmp_path),
            geocoder=InMemoryGeocoder({}),
        )

        pd.testing.assert_frame_equal(result, cached)


class TestQuarantineIntegration:
    """Test that quarantine rows are saved to disk with _rejection_reason."""

    def test_hdb_invalid_rows_saved_to_quarantine(self, tmp_path):
        cleaning = _get_cleaning_module()

        mixed_data = pd.DataFrame(
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
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": -100.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "planning_area": "Toa Payoh",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "456",
                    "street_name": "ANG MO KIO AVE 1",
                    "storey_min": 4,
                    "storey_max": 6,
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                    "remaining_lease_months": 960,
                    "address": "456 ANG MO KIO AVE 1",
                },
            ]
        )

        result = cleaning.hdb_validated(mixed_data, silver_dir=tmp_path)

        assert len(result) == 1
        assert result.iloc[0]["price"] == 500000.0

        quarantine_dir = tmp_path / "_quarantine"
        assert quarantine_dir.exists()
        quarantine_files = list(quarantine_dir.glob("HDB_*.parquet"))
        assert len(quarantine_files) == 1

        quarantine_df = pd.read_parquet(quarantine_files[0])
        assert len(quarantine_df) == 1
        assert "_rejection_reason" in quarantine_df.columns
        assert "price" in quarantine_df.columns
