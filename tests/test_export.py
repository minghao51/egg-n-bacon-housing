"""Test 04_export component."""

import logging

import pandas as pd
import pytest
from pydantic import ValidationError

from egg_n_bacon_housing.schemas.platinum_models import HUnifiedRecord
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

        result = export.unified_dataset(transactions_enriched)

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "town" in result.columns
            assert "lat" in result.columns

    def test_unified_dataset_with_empty_input(self, tmp_path):
        """Test that unified_dataset handles empty input."""
        export = _get_export_module()

        transactions_enriched = pd.DataFrame()

        result = export.unified_dataset(transactions_enriched)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_unified_dataset_requires_contract_columns(self, tmp_path):
        export = _get_export_module()
        with pytest.raises(ValueError, match="missing required columns"):
            export.unified_dataset(pd.DataFrame([{"price": 500000.0}]))

    def test_unified_dataset_materializer_writes_output(self, tmp_path):
        export = _get_export_module()
        from egg_n_bacon_housing.components.materialization import materialize_unified_dataset

        df = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-01"),
                }
            ]
        )
        result = export.unified_dataset(df)
        path = materialize_unified_dataset(result, SimpleWriter(tmp_path))

        assert path == tmp_path / "04_platinum" / "unified_dataset.parquet"
        assert path.exists()


def _unified_row(**overrides) -> dict:
    """A row satisfying the HUnifiedRecord platinum contract."""
    row = {
        "town": "TOA PAYOH",
        "lat": 1.35,
        "lon": 103.8,
        "price": 500000.0,
        "property_type": "hdb",
        "transaction_date": pd.Timestamp("2024-01-01"),
    }
    row.update(overrides)
    return row


class TestUnifiedDatasetPlatinumContract:
    """unified_dataset validates every row against HUnifiedRecord."""

    def test_valid_rows_pass_validation_unchanged(self, tmp_path):
        export = _get_export_module()
        df = pd.DataFrame([_unified_row(price=500000.0), _unified_row(price=600000.0)])

        result = export.unified_dataset(df)

        assert len(result) == 2
        assert "town" in result.columns
        # Materializer owns persistence — the node itself writes nothing.
        assert list(tmp_path.rglob("*.parquet")) == []

    def test_poisoned_price_row_quarantined(self, tmp_path, caplog):
        export = _get_export_module()
        df = pd.DataFrame([_unified_row(price=500000.0), _unified_row(price=-1.0)])

        with caplog.at_level(logging.WARNING):
            result = export.unified_dataset(df)

        assert len(result) == 1
        assert result["price"].iloc[0] == 500000.0
        assert "unified_dataset: 1 row(s) quarantined" in caplog.text
        # persist=False — quarantine frames are dropped, not written.
        assert list(tmp_path.rglob("*.parquet")) == []

    def test_row_missing_required_key_quarantined(self, tmp_path, caplog):
        export = _get_export_module()
        df = pd.DataFrame([_unified_row(), _unified_row(lat=float("nan"))])

        with caplog.at_level(logging.WARNING):
            result = export.unified_dataset(df)

        assert len(result) == 1
        assert "unified_dataset: 1 row(s) quarantined" in caplog.text

    def test_sample_policy_path_returns_all_rows(self, tmp_path):
        export = _get_export_module()
        rows = [_unified_row(price=500000.0 + i) for i in range(11)]
        rows.append(_unified_row(price=-1.0))
        df = pd.DataFrame(rows)

        result = export.unified_dataset(
            df,
            large_table_validation_policy="sample",
            sample_validation_size=5,
        )

        # Sample policy saves the full table; invalid rows are only reported.
        assert len(result) == 12

    def test_schema_rejects_negative_price(self):
        with pytest.raises(ValidationError):
            HUnifiedRecord(
                price=-1.0,
                lat=1.35,
                lon=103.8,
                property_type="hdb",
                transaction_date=pd.Timestamp("2024-01-01"),
            )
