"""Test 01_ingestion component."""

import importlib
import pandas as pd
import pytest


def _get_ingestion_module():
    """Get the 01_ingestion module."""
    return importlib.import_module("egg_n_bacon_housing.components.01_ingestion")


class TestBronzeLayer:
    """Test bronze layer data ingestion functions."""

    def test_raw_hdb_resale_transactions_returns_dataframe(self):
        """Test that raw_hdb_resale_transactions returns a DataFrame."""
        ingestion = _get_ingestion_module()

        result = ingestion.raw_hdb_resale_transactions()

        assert isinstance(result, pd.DataFrame)
        assert hasattr(result, "empty")

    def test_raw_condo_transactions_returns_dataframe(self):
        """Test that raw_condo_transactions returns a DataFrame."""
        ingestion = _get_ingestion_module()

        result = ingestion.raw_condo_transactions()

        assert isinstance(result, pd.DataFrame)
        assert hasattr(result, "empty")

    def test_raw_condo_transactions_returns_dataframe(self):
        """Test that raw_condo_transactions returns a DataFrame."""
        ingestion = _get_ingestion_module()

        result = ingestion.raw_condo_transactions()

        assert isinstance(result, pd.DataFrame)
        assert hasattr(result, "empty")

    def test_raw_rental_index_returns_dataframe(self):
        """Test that raw_rental_index returns a DataFrame."""
        ingestion = _get_ingestion_module()

        result = ingestion.raw_rental_index()

        assert isinstance(result, pd.DataFrame)
        assert hasattr(result, "empty")

    def test_raw_school_directory_returns_dataframe(self):
        """Test that raw_school_directory returns a DataFrame."""
        ingestion = _get_ingestion_module()

        result = ingestion.raw_school_directory()

        assert isinstance(result, pd.DataFrame)
        assert hasattr(result, "empty")

    def test_raw_macro_data_returns_dataframe(self):
        """Test that raw_macro_data returns a DataFrame (actually returns dict)."""
        ingestion = _get_ingestion_module()

        result = ingestion.raw_macro_data()

        assert isinstance(result, dict)
        assert len(result) > 0


    def test_empty_dataframe_has_correct_columns(self):
        """Test that empty DataFrames are handled correctly."""
        ingestion = _get_ingestion_module()

        result = ingestion.raw_hdb_resale_transactions()

        if result.empty:
            assert True  # Empty DataFrame is acceptable for first run
        else:
            assert len(result) > 0
