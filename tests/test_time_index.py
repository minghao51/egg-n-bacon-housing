"""Tests for utils/time_index.py — the shared month-period derivation."""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.time_index import ensure_month_column

pytestmark = pytest.mark.unit

TIME_INDEX_LOGGER = "egg_n_bacon_housing.utils.time_index"


def _warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno >= logging.WARNING]


class TestDeriveFromDateColumn:
    def test_derives_month_and_keeps_all_parseable_rows(self, caplog):
        df = pd.DataFrame(
            {
                "transaction_date": pd.to_datetime(["2024-01-15", "2024-02-20"]),
                "price": [1.0, 2.0],
            }
        )

        with caplog.at_level(logging.WARNING, logger=TIME_INDEX_LOGGER):
            result = ensure_month_column(df)

        assert result["month"].tolist() == ["2024-01", "2024-02"]
        assert _warnings(caplog) == []

    def test_all_parseable_is_silent(self, caplog):
        df = pd.DataFrame(
            {
                "transaction_date": ["2024-01-15", "2024-02-15", "2024-03-15"],
                "price": [1.0, 2.0, 3.0],
            }
        )

        with caplog.at_level(logging.WARNING, logger=TIME_INDEX_LOGGER):
            result = ensure_month_column(df)

        assert result["month"].tolist() == ["2024-01", "2024-02", "2024-03"]
        assert _warnings(caplog) == []

    def test_unparseable_dates_dropped_loudly_with_exact_counts(self, caplog):
        df = pd.DataFrame(
            {
                "transaction_date": ["2024-01-15", "not-a-date", "2024-03-05", ""],
                "price": [1.0, 2.0, 3.0, 4.0],
            }
        )

        with caplog.at_level(logging.WARNING, logger=TIME_INDEX_LOGGER):
            result = ensure_month_column(df)

        # Correct rows kept, unparseable rows dropped.
        assert result["month"].tolist() == ["2024-01", "2024-03"]
        assert result["price"].tolist() == [1.0, 3.0]

        warnings = _warnings(caplog)
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert "transaction_date" in message  # column name
        assert "2/4" in message  # dropped/total
        assert "kept 2" in message  # kept count

    def test_input_frame_not_mutated(self):
        df = pd.DataFrame({"transaction_date": ["2024-01-15"], "price": [1.0]})

        result = ensure_month_column(df)

        assert "month" not in df.columns
        assert result["month"].tolist() == ["2024-01"]

    def test_custom_column_names(self):
        df = pd.DataFrame({"rent_approval_date": ["2024-05"], "monthly_rent": [3500.0]})

        result = ensure_month_column(df, date_column="rent_approval_date")

        assert result["month"].tolist() == ["2024-05"]


class TestExistingMonthColumn:
    def test_string_month_passthrough(self, caplog):
        df = pd.DataFrame({"month": ["2024-01", "2024-02"], "price": [1.0, 2.0]})

        with caplog.at_level(logging.WARNING, logger=TIME_INDEX_LOGGER):
            result = ensure_month_column(df)

        assert result["month"].tolist() == ["2024-01", "2024-02"]
        assert _warnings(caplog) == []

    def test_period_dtype_month_normalized_to_strings(self):
        df = pd.DataFrame(
            {"month": list(pd.period_range("2024-01", periods=2, freq="M")), "price": [1.0, 2.0]}
        )
        df["month"] = df["month"].astype("period[M]")

        result = ensure_month_column(df)

        assert result["month"].tolist() == ["2024-01", "2024-02"]
        assert pd.api.types.is_string_dtype(result["month"])

    def test_period_nat_dropped_loudly_and_literal_nat_never_survives(self, caplog):
        df = pd.DataFrame(
            {
                "month": list(pd.period_range("2024-01", periods=3, freq="M")),
                "price": [1.0, 2.0, 3.0],
            }
        )
        df["month"] = df["month"].astype("period[M]")
        df.loc[1, "month"] = pd.NaT

        with caplog.at_level(logging.WARNING, logger=TIME_INDEX_LOGGER):
            result = ensure_month_column(df)

        # NaT periods stringify to the literal "NaT" on some pandas paths —
        # the guard must keep it out of the output.
        assert result["month"].tolist() == ["2024-01", "2024-03"]
        assert "NaT" not in set(result["month"].astype(str))

        warnings = _warnings(caplog)
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert "transaction_date" in message
        assert "1/3" in message
        assert "kept 2" in message

    def test_existing_month_column_does_not_require_date_column(self):
        df = pd.DataFrame({"month": ["2024-01"], "price": [1.0]})

        result = ensure_month_column(df)

        assert result["month"].tolist() == ["2024-01"]


class TestMissingColumns:
    # Caller audit (WS14): every call site structurally guarantees the month or
    # date column — feature_rental.py guards its required sale/rent column sets,
    # feature_transactions._enforce_transaction_time_contract raises without
    # transaction_date and always sets month, and metrics.py consumes the
    # upstream transactions_enriched contract (empty frames short-circuit).
    # A missing column is therefore a schema break and must raise, not return
    # a logged empty frame.
    def test_missing_both_columns_raises_value_error(self):
        df = pd.DataFrame({"price": [1.0]})

        with pytest.raises(ValueError, match="transaction_date"):
            ensure_month_column(df)

    def test_missing_custom_date_column_raises_value_error(self):
        df = pd.DataFrame({"price": [1.0]})

        with pytest.raises(ValueError, match="rent_approval_date"):
            ensure_month_column(df, date_column="rent_approval_date")
