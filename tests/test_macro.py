"""Unit tests for macro ingestion transform guards (WS12).

Focus: the GDP preferred-series fallback warning and the unified
first-non-``_id``-column rule for pivot frames lacking a ``DataSeries``
header (CPI / GDP / SORA / wage growth all share ``_label_column``).
"""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.components.ingestion import macro

pytestmark = pytest.mark.unit

_MACRO_LOGGER = "egg_n_bacon_housing.components.ingestion.macro"


class TestGdpFallback:
    def test_preferred_label_present_uses_it_without_warning(self, caplog):
        raw = pd.DataFrame(
            [
                {
                    "DataSeries": "GDP In Chained (2015) Dollars",
                    "20261Q": "100.0",
                    "20262Q": "110.0",
                },
                {"DataSeries": "Percent Change Over Same Period Previous Year", "20261Q": "3.1"},
            ]
        )

        with caplog.at_level(logging.WARNING, logger=_MACRO_LOGGER):
            result = macro._transform_gdp(raw)

        assert result["gdp"].tolist() == [100.0, 110.0]
        assert result["quarter"].dt.strftime("%Y-%m-%d").tolist() == ["2026-03-31", "2026-06-30"]
        assert caplog.records == []

    def test_preferred_label_absent_warns_and_uses_first_series(self, caplog):
        raw = pd.DataFrame(
            [
                {"DataSeries": "Fallback GDP Label", "20261Q": "100.0", "20262Q": "110.0"},
            ]
        )

        with caplog.at_level(logging.WARNING, logger=_MACRO_LOGGER):
            result = macro._transform_gdp(raw)

        assert result["gdp"].tolist() == [100.0, 110.0]
        warnings = [r for r in caplog.records if "not found" in r.getMessage()]
        assert len(warnings) == 1, caplog.text
        message = warnings[0].getMessage()
        assert "GDP In Chained (2015) Dollars" in message  # preferred series named
        assert "Fallback GDP Label" in message  # series actually used named
        assert "available labels" in message  # available labels listed

    def test_preferred_label_absent_and_empty_frame_warns_and_degrades(self, caplog):
        """Fallback path with a preferred-label-less frame that melts to nothing
        (no parseable quarters) still warns, and returns an empty frame."""
        raw = pd.DataFrame([{"DataSeries": "GDP In Chained (2015) Dollars", "junk": "x"}])

        with caplog.at_level(logging.WARNING, logger=_MACRO_LOGGER):
            result = macro._transform_gdp(raw)

        assert result.empty
        warnings = [r for r in caplog.records if "not found" in r.getMessage()]
        assert len(warnings) == 1


class TestLabelColumnFallback:
    def test_monthly_melt_warns_when_dataseries_header_missing(self, caplog):
        raw = pd.DataFrame([{"_id": 0, "Indicator": "All Items", "2026Jan": "101.0"}])

        with caplog.at_level(logging.WARNING, logger=_MACRO_LOGGER):
            result = macro._melt_pivot_monthly(raw, "All Items", "cpi")

        assert result["cpi"].tolist() == [101.0]
        fallbacks = [r for r in caplog.records if "DataSeries" in r.getMessage()]
        assert len(fallbacks) == 1
        message = fallbacks[0].getMessage()
        assert "'Indicator'" in message  # column actually used
        assert "'_id'" in message and "'2026Jan'" in message  # available columns listed

    def test_quarterly_melt_warns_when_dataseries_header_missing(self, caplog):
        raw = pd.DataFrame([{"_id": 0, "Series": "Total Unemployment Rate", "20261Q": "2.0"}])

        with caplog.at_level(logging.WARNING, logger=_MACRO_LOGGER):
            result = macro._melt_pivot_quarterly(
                raw, "Total Unemployment Rate", "unemployment_rate"
            )

        assert result["unemployment_rate"].tolist() == [2.0]
        assert len([r for r in caplog.records if "DataSeries" in r.getMessage()]) == 1

    def test_wage_growth_uses_first_non_id_column_not_last(self, caplog):
        """Unified rule: the label is the first non-``_id`` column (position 1).

        The pre-WS12 wage-growth code used the LAST column, which on a frame
        without ``DataSeries`` would pick the period column '2025' as the
        label and melt garbage.
        """
        raw = pd.DataFrame([{"_id": 0, "Indicator": "Overall Economy", "2025": "4.5"}])

        with caplog.at_level(logging.WARNING, logger=_MACRO_LOGGER):
            result = macro._transform_wage_growth(raw)

        assert result["wage_growth"].tolist() == [4.5, 4.5, 4.5, 4.5]
        assert result["quarter"].dt.strftime("%Y-%m-%d").tolist() == [
            "2025-03-31",
            "2025-06-30",
            "2025-09-30",
            "2025-12-31",
        ]
        fallbacks = [r for r in caplog.records if "DataSeries" in r.getMessage()]
        assert len(fallbacks) == 1
        assert "'Indicator'" in fallbacks[0].getMessage()

    def test_wage_growth_with_dataseries_header_does_not_warn(self, caplog):
        raw = pd.DataFrame([{"metric": "ignored", "DataSeries": "Overall Economy", "2025": "4.5"}])

        with caplog.at_level(logging.WARNING, logger=_MACRO_LOGGER):
            result = macro._transform_wage_growth(raw)

        assert result["wage_growth"].tolist() == [4.5] * 4
        assert caplog.records == []

    def test_gdp_resolves_label_column_once_when_header_missing(self, caplog):
        """GDP's two melts share one resolved label column: exactly one
        column-fallback warning, not one per melt."""
        raw = pd.DataFrame([{"_id": 0, "Indicator": "Fallback GDP Label", "20261Q": "100.0"}])

        with caplog.at_level(logging.WARNING, logger=_MACRO_LOGGER):
            result = macro._transform_gdp(raw)

        assert result["gdp"].tolist() == [100.0]
        fallbacks = [r for r in caplog.records if "DataSeries" in r.getMessage()]
        series_fallbacks = [r for r in caplog.records if "not found" in r.getMessage()]
        assert len(fallbacks) == 1
        assert len(series_fallbacks) == 1
