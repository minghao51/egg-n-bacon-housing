"""Tests for the stage-boundary column contract helper (utils/contracts.py)."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.contracts import require_columns

pytestmark = pytest.mark.unit


class TestRequireColumns:
    def test_all_present_passes(self):
        df = pd.DataFrame({"lat": [1.3], "lon": [103.8], "price": [500_000]})

        assert require_columns(df, {"lat", "lon", "price"}, "geocoded_validated") is None

    def test_missing_single_column_raises_with_dataset_name_and_column(self):
        df = pd.DataFrame({"lat": [1.3], "lon": [103.8]})

        with pytest.raises(ValueError, match="geocoded_validated") as excinfo:
            require_columns(df, {"lat", "lon", "price"}, "geocoded_validated")

        assert "['price']" in str(excinfo.value)

    def test_missing_columns_are_reported_sorted(self):
        df = pd.DataFrame(columns=["transaction_date"])

        with pytest.raises(ValueError) as excinfo:
            require_columns(df, {"price", "lat", "lon"}, "transactions_enriched")

        # The message carries the sorted missing list regardless of set order.
        assert str(excinfo.value) == (
            "transactions_enriched is missing required columns: ['lat', 'lon', 'price']"
        )

    def test_empty_required_set_passes_on_empty_frame(self):
        assert require_columns(pd.DataFrame(), set(), "anything") is None

    def test_required_columns_on_empty_frame_raises(self):
        with pytest.raises(ValueError, match=r"\['a', 'b'\]"):
            require_columns(pd.DataFrame(), {"b", "a"}, "empty_frame")

    def test_column_present_but_zero_rows_passes(self):
        """require_columns is a column-level contract: row count is irrelevant."""
        df = pd.DataFrame({"a": pd.Series([], dtype="float64")})

        assert require_columns(df, {"a"}, "no_rows") is None

    def test_extra_columns_are_allowed(self):
        df = pd.DataFrame({"a": [1], "b": [2], "extra": ["ignored"]})

        assert require_columns(df, {"a"}, "with_extra") is None

    def test_error_message_contains_dataset_name_and_full_missing_list(self):
        df = pd.DataFrame({"keep": [1]})

        with pytest.raises(ValueError) as excinfo:
            require_columns(df, {"keep", "x", "y", "z"}, "my_dataset")

        message = str(excinfo.value)
        assert message.startswith("my_dataset is missing required columns: ")
        assert "['x', 'y', 'z']" in message
        assert "keep" not in message  # present columns are never listed
