"""Test 04_export component."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.layer_writer import SimpleWriter

pytestmark = pytest.mark.unit


def _get_export_module():
    """Get the 04_export module."""
    from egg_n_bacon_housing.components import export

    return export


class TestPlatinumLayer:
    """Test platinum layer export functions."""

    def test_unified_dataset_returns_dataframe(self, tmp_path):
        """Test that unified_dataset returns a DataFrame."""
        export = _get_export_module()

        transactions_enriched = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "lat": 1.35,
                    "lon": 103.8,
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-01"),
                }
            ]
        )

        result = export.unified_dataset(transactions_enriched, writer=SimpleWriter(tmp_path))

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "town" in result.columns
            assert "lat" in result.columns

    def test_unified_dataset_with_empty_input(self, tmp_path):
        """Test that unified_dataset handles empty input."""
        export = _get_export_module()

        transactions_enriched = pd.DataFrame()

        result = export.unified_dataset(transactions_enriched, writer=SimpleWriter(tmp_path))

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_unified_dataset_requires_contract_columns(self, tmp_path):
        export = _get_export_module()
        with pytest.raises(ValueError, match="missing required columns"):
            export.unified_dataset(
                pd.DataFrame([{"price": 500000.0}]), writer=SimpleWriter(tmp_path)
            )
