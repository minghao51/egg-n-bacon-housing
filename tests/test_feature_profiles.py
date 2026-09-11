"""Focused tests for components/feature_profiles.py — shared-lookup integration.

Covers the behaviors that changed when the private lookups moved to
``utils.hdb_lookups``: the unified NaN-guarded income merge in
``planning_area_360`` and summed population aggregation in ``town_360``,
plus the WO-7 silent-loss count logging at the null-planning_area filters.
"""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.components import feature_profiles

pytestmark = pytest.mark.unit

_PROFILES_LOGGER = "egg_n_bacon_housing.components.feature_profiles"


class TestPlanningArea360IncomeMerge:
    def test_income_merge_guards_nan_source_keys(self, tmp_path):
        """NaN source planning areas never surface as a literal 'NAN' key."""
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        income = pd.DataFrame(
            [
                {"planning_area": None, "median_monthly_income": 1234.0},
                {"planning_area": "toa payoh ", "median_monthly_income": 8000.0},
                {"planning_area": "TOA PAYOH", "median_monthly_income": 9999.0},
            ]
        )

        result = feature_profiles.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=income,
            raw_macro_data={},
        )

        assert len(result) == 1
        assert result.loc[0, "planning_area"] == "TOA PAYOH"
        # Case/space normalized match; duplicate keys keep the first row.
        assert result.loc[0, "median_monthly_income"] == pytest.approx(8000.0)

    def test_income_merge_drops_rows_without_income_value(self, tmp_path):
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Bishan", "region": "RCR"}]
        )
        income = pd.DataFrame([{"planning_area": "BISHAN", "median_monthly_income": None}])

        result = feature_profiles.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=income,
            raw_macro_data={},
        )

        assert len(result) == 1
        assert "median_monthly_income" in result.columns
        assert pd.isna(result.loc[0, "median_monthly_income"])


class TestPlanningArea360SilentLossCounts:
    """WO-7: both null-planning_area filters announce dropped/kept counts."""

    def test_null_pa_location_dim_rows_dropped_with_count_warning(self, tmp_path, caplog):
        location_dim = pd.DataFrame(
            [
                {"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"},
                {"lat": 1.36, "lon": 103.81, "planning_area": None, "region": "RCR"},
                {"lat": 1.37, "lon": 103.82, "planning_area": "Bishan", "region": "RCR"},
            ]
        )

        with caplog.at_level(logging.WARNING, logger=_PROFILES_LOGGER):
            result = feature_profiles.planning_area_360(
                location_dim,
                pd.DataFrame(),
                raw_income_by_planning_area=pd.DataFrame(),
                raw_macro_data={},
            )

        assert set(result["planning_area"]) == {"Toa Payoh", "Bishan"}
        warnings = [r for r in caplog.records if "location_dim row(s)" in r.getMessage()]
        assert len(warnings) == 1, caplog.text
        assert warnings[0].levelno == logging.WARNING
        message = warnings[0].getMessage()
        assert "dropped 1 location_dim row(s) with null planning_area" in message
        assert "kept 2" in message

    def test_null_pa_transaction_rows_dropped_with_count_warning(self, tmp_path, caplog):
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        transactions_enriched = pd.DataFrame(
            [
                {"planning_area": "Toa Payoh", "price": 500000.0, "psf": 500.0},
                {"planning_area": None, "price": 600000.0, "psf": 600.0},
                {"planning_area": None, "price": 650000.0, "psf": 650.0},
            ]
        )

        with caplog.at_level(logging.WARNING, logger=_PROFILES_LOGGER):
            result = feature_profiles.planning_area_360(
                location_dim,
                transactions_enriched,
                raw_income_by_planning_area=pd.DataFrame(),
                raw_macro_data={},
            )

        assert len(result) == 1
        assert result.loc[0, "transaction_volume"] == 1  # null-PA rows excluded
        warnings = [r for r in caplog.records if "transactions_enriched row(s)" in r.getMessage()]
        assert len(warnings) == 1, caplog.text
        assert warnings[0].levelno == logging.WARNING
        message = warnings[0].getMessage()
        assert "dropped 2 transactions_enriched row(s) with null planning_area" in message
        assert "kept 1" in message


class TestPlanningArea360MacroLatestValue:
    """WO-8: a trailing null macro row must not NaN the broadcast column."""

    def test_trailing_null_macro_row_is_skipped_for_latest_value(self, tmp_path):
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        macro = {
            "cpi": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "cpi": 104.5},
                    {"date": pd.Timestamp("2024-06-01"), "cpi": 105.0},
                    {"date": pd.Timestamp("2024-12-01"), "cpi": None},
                ]
            )
        }

        result = feature_profiles.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data=macro,
        )

        assert len(result) == 1
        assert result.loc[0, "cpi"] == pytest.approx(105.0)

    def test_all_null_macro_series_is_skipped_entirely(self, tmp_path):
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        macro = {
            "unemployment": pd.DataFrame(
                [
                    {"quarter": pd.Timestamp("2024-03-31"), "unemployment_rate": None},
                    {"quarter": pd.Timestamp("2024-06-30"), "unemployment_rate": None},
                ]
            )
        }

        result = feature_profiles.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data=macro,
        )

        assert len(result) == 1
        assert "unemployment_rate" not in result.columns


class TestTown360SharedLookups:
    def test_population_multi_row_towns_are_summed(self, tmp_path):
        """Multi-row towns aggregate by sum, not an arbitrary first row."""
        tx = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0, "psf": 500.0},
                {"town": "BEDOK", "price": 400000.0, "psf": 400.0},
            ]
        )
        population = pd.DataFrame(
            [
                {"town_estate": "TOA PAYOH", "number": 100, "shs_year": 2023},
                {"town_estate": " Toa Payoh", "number": 50, "shs_year": 2023},
                # Older survey year: ignored entirely.
                {"town_estate": "BEDOK", "number": 999, "shs_year": 2022},
            ]
        )

        result = feature_profiles.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=population,
            raw_median_annual_value=pd.DataFrame(),
        ).set_index("town")

        assert result.loc["Toa Payoh", "population_in_town"] == pytest.approx(150.0)
        assert pd.isna(result.loc["Bedok", "population_in_town"])

    def test_population_per_dwelling_uses_shared_helper(self, tmp_path):
        tx = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0},
                {"town": "BEDOK", "price": 400000.0},
            ]
        )
        dwell = pd.DataFrame(
            [
                {
                    "town_or_estate": "TOA PAYOH",
                    "no_of_dwelling_units": 100,
                    "financial_year": 2024,
                    "sold_or_rental": "Sold Units",
                },
                {
                    "town_or_estate": "BEDOK",
                    "no_of_dwelling_units": 0,
                    "financial_year": 2024,
                    "sold_or_rental": "Sold Units",
                },
            ]
        )
        population = pd.DataFrame(
            [
                {"town_estate": "TOA PAYOH", "number": 300, "shs_year": 2023},
                {"town_estate": "BEDOK", "number": 250, "shs_year": 2023},
            ]
        )

        result = feature_profiles.town_360(
            tx,
            raw_dwelling_units_by_town=dwell,
            raw_hdb_resident_population=population,
            raw_median_annual_value=pd.DataFrame(),
        ).set_index("town")

        assert result.loc["Toa Payoh", "dwelling_units_in_town"] == pytest.approx(100.0)
        assert result.loc["Toa Payoh", "population_per_dwelling"] == pytest.approx(3.0)
        # Zero dwelling units -> NA ratio, not division-by-zero.
        assert pd.isna(result.loc["Bedok", "population_per_dwelling"])
