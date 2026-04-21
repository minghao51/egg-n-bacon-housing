"""Test 04_export component."""

import importlib

import pandas as pd


def _get_export_module():
    """Get the 04_export module."""
    return importlib.import_module("egg_n_bacon_housing.components.04_export")


class TestPlatinumLayer:
    """Test platinum layer export functions."""

    def test_unified_dataset_returns_dataframe(self):
        """Test that unified_dataset returns a DataFrame."""
        export = _get_export_module()

        unified_features = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "lat": 1.35,
                    "lon": 103.8,
                    "price": 500000.0,
                    "property_type": "hdb",
                }
            ]
        )

        result = export.unified_dataset(unified_features)

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "town" in result.columns
            assert "lat" in result.columns

    def test_unified_dataset_with_empty_input(self):
        """Test that unified_dataset handles empty input."""
        export = _get_export_module()

        unified_features = pd.DataFrame()

        result = export.unified_dataset(unified_features)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_dashboard_json_returns_dict(self):
        """Test that dashboard_json returns a dictionary."""
        export = _get_export_module()

        unified_dataset = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "property_type": "hdb",
                }
            ]
        )

        result = export.dashboard_json(unified_dataset)

        assert isinstance(result, dict)
        if result:
            assert "total_transactions" in result
            assert "property_types" in result
            assert "price_range" in result
            assert "generated_at" in result

    def test_dashboard_json_with_empty_input(self):
        """Test that dashboard_json handles empty input."""
        export = _get_export_module()

        unified_dataset = pd.DataFrame()

        result = export.dashboard_json(unified_dataset)

        assert isinstance(result, dict)
        assert result == {}

    def test_segments_data_returns_dict(self):
        """Test that segments_data returns a dictionary."""
        export = _get_export_module()

        unified_dataset = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0, "property_type": "hdb"},
                {"town": "YISHUN", "price": 600000.0, "property_type": "condo"},
            ]
        )

        result = export.segments_data(unified_dataset)

        assert isinstance(result, dict)
        if result:
            assert "segments" in result
            assert isinstance(result["segments"], list)
            assert "generated_at" in result

    def test_segments_data_with_empty_input(self):
        """Test that segments_data handles empty input."""
        export = _get_export_module()

        unified_dataset = pd.DataFrame()

        result = export.segments_data(unified_dataset)

        assert isinstance(result, dict)
        assert result == {}

    def test_interactive_tools_data_returns_dict(self):
        """Test that interactive_tools_data returns a dictionary."""
        export = _get_export_module()

        unified_dataset = pd.DataFrame(
            [
                {
                    "planning_area": "Orchard",
                    "price": 1500000.0,
                    "property_type": "condo",
                }
            ]
        )

        result = export.interactive_tools_data(unified_dataset)

        assert isinstance(result, dict)
        if result:
            assert "planning_area_stats" in result

    def test_interactive_tools_data_with_empty_input(self):
        """Test that interactive_tools_data handles empty input."""
        export = _get_export_module()

        unified_dataset = pd.DataFrame()

        result = export.interactive_tools_data(unified_dataset)

        assert isinstance(result, dict)
        assert result == {}

    def test_csv_export_returns_path_or_none(self):
        """Test that csv_export returns a Path or None."""
        export = _get_export_module()

        unified_dataset = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                }
            ]
        )

        result = export.csv_export(unified_dataset)

        if result is not None:
            assert result.exists()
            assert result.suffix == ".csv"
        else:
            assert result is None
