"""Tests for utils/hdb_lookups.py — the shared gold feature lookup module."""

import numpy as np
import pandas as pd
import pytest

from egg_n_bacon_housing.utils.hdb_lookups import (
    SQFT_PER_SQM,
    annual_value_lookup,
    dwelling_units_lookup,
    merge_median_income,
    merge_town_context,
    normalize_hdb_flat_type,
    population_lookup,
    population_per_dwelling,
)

pytestmark = pytest.mark.unit


class TestDwellingUnitsLookup:
    def test_latest_year_sold_units_summed_per_town(self):
        raw = pd.DataFrame(
            [
                {
                    "town_or_estate": "TOA PAYOH",
                    "no_of_dwelling_units": 100,
                    "financial_year": 2023,
                    "sold_or_rental": "Sold Units",
                },
                {
                    "town_or_estate": "toa payoh ",
                    "no_of_dwelling_units": 50,
                    "financial_year": 2023,
                    "sold_or_rental": "Sold Units",
                },
                # Older year: ignored.
                {
                    "town_or_estate": "TOA PAYOH",
                    "no_of_dwelling_units": 999,
                    "financial_year": 2022,
                    "sold_or_rental": "Sold Units",
                },
                # Rental row: ignored.
                {
                    "town_or_estate": "BEDOK",
                    "no_of_dwelling_units": 777,
                    "financial_year": 2023,
                    "sold_or_rental": "Rental Units",
                },
            ]
        )

        result = dwelling_units_lookup(raw)

        assert len(result) == 1
        assert result.loc[0, "_town_upper"] == "TOA PAYOH"
        assert result.loc[0, "dwelling_units_in_town"] == pytest.approx(150)

    def test_empty_source_returns_empty(self):
        assert dwelling_units_lookup(pd.DataFrame()).empty

    def test_schema_drift_returns_empty(self):
        raw = pd.DataFrame([{"town_or_estate": "BEDOK", "no_of_dwelling_units": 10}])
        assert dwelling_units_lookup(raw).empty


class TestPopulationLookup:
    def test_latest_shs_year_population_summed_per_town(self):
        raw = pd.DataFrame(
            [
                {"town_estate": "TOA PAYOH", "number": 100, "shs_year": 2023},
                {"town_estate": " Toa Payoh", "number": 50, "shs_year": 2023},
                # Older survey year: ignored.
                {"town_estate": "BEDOK", "number": 999, "shs_year": 2022},
            ]
        )

        result = population_lookup(raw)

        # Multi-row towns are SUMMED (previously an arbitrary first row won).
        assert len(result) == 1
        assert result.loc[0, "_town_upper"] == "TOA PAYOH"
        assert result.loc[0, "population_in_town"] == pytest.approx(150)

    def test_empty_source_returns_empty(self):
        assert population_lookup(pd.DataFrame()).empty

    def test_schema_drift_returns_empty(self):
        raw = pd.DataFrame([{"town_estate": "BEDOK", "number": 10}])
        assert population_lookup(raw).empty


class TestAnnualValueLookup:
    def test_latest_financial_year_values_kept(self):
        raw = pd.DataFrame(
            [
                {
                    "type_of_hdb": "3 Room",
                    "median_annual_value": "5000",
                    "property_tax_collection": "800",
                    "financial_year": 2024,
                },
                {
                    "type_of_hdb": "4 Room",
                    "median_annual_value": "7000",
                    "property_tax_collection": "1200",
                    "financial_year": 2024,
                },
                # Older year: ignored.
                {
                    "type_of_hdb": "3 Room",
                    "median_annual_value": "4000",
                    "property_tax_collection": "600",
                    "financial_year": 2023,
                },
                # Duplicate within latest year: first row wins.
                {
                    "type_of_hdb": "4 Room",
                    "median_annual_value": "9",
                    "property_tax_collection": "9",
                    "financial_year": 2024,
                },
            ]
        )

        result = annual_value_lookup(raw).set_index("type_of_hdb")

        assert result.loc["3 Room", "annual_value"] == pytest.approx(5000.0)
        assert result.loc["3 Room", "property_tax"] == pytest.approx(800.0)
        assert result.loc["4 Room", "annual_value"] == pytest.approx(7000.0)

    def test_empty_source_returns_empty(self):
        assert annual_value_lookup(pd.DataFrame()).empty

    def test_schema_drift_returns_empty(self):
        raw = pd.DataFrame([{"type_of_hdb": "3 Room", "median_annual_value": 1}])
        assert annual_value_lookup(raw).empty


class TestPopulationPerDwelling:
    def test_ratio_computed_and_zero_units_gives_na(self):
        df = pd.DataFrame(
            {
                "dwelling_units_in_town": [100.0, 0.0, None],
                "population_in_town": [300.0, 500.0, 400.0],
            }
        )

        result = population_per_dwelling(df)

        assert result.iloc[0] == pytest.approx(3.0)
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])


class TestMergeTownContext:
    def test_joins_lookups_by_normalized_town_and_drops_key(self):
        df = pd.DataFrame(
            [{"town": " Toa Payoh ", "price": 1.0}, {"town": "UNKNOWN", "price": 2.0}]
        )
        dwell = pd.DataFrame(
            [
                {
                    "town_or_estate": "TOA PAYOH",
                    "no_of_dwelling_units": 100,
                    "financial_year": 2024,
                    "sold_or_rental": "Sold Units",
                }
            ]
        )
        population = pd.DataFrame([{"town_estate": "TOA PAYOH", "number": 300, "shs_year": 2023}])

        result = merge_town_context(df, dwell, population)

        np.testing.assert_allclose(result["dwelling_units_in_town"].astype(float), [100.0, np.nan])
        np.testing.assert_allclose(result["population_in_town"].astype(float), [300.0, np.nan])
        assert result["population_per_dwelling"].iloc[0] == pytest.approx(3.0)
        assert pd.isna(result["population_per_dwelling"].iloc[1])
        assert "_town_upper" not in result.columns
        assert result["town"].tolist() == [" Toa Payoh ", "UNKNOWN"]

    def test_empty_lookups_fill_na_columns_and_ratio(self):
        df = pd.DataFrame([{"town": "BEDOK", "price": 1.0}])

        result = merge_town_context(df, pd.DataFrame(), pd.DataFrame())

        assert result["dwelling_units_in_town"].isna().all()
        assert result["population_in_town"].isna().all()
        assert result["population_per_dwelling"].isna().all()

    def test_no_town_column_returns_frame_unchanged(self):
        df = pd.DataFrame([{"price": 1.0}])

        assert merge_town_context(df, pd.DataFrame(), pd.DataFrame()) is df


class TestMergeMedianIncome:
    def test_nan_source_planning_areas_are_guarded(self):
        df = pd.DataFrame(
            [{"planning_area": "Toa Payoh", "price": 1.0}, {"planning_area": None, "price": 2.0}]
        )
        income = pd.DataFrame(
            [
                {"planning_area": None, "median_monthly_income": 1234.0},
                {"planning_area": "toa payoh ", "median_monthly_income": 8000.0},
                # Duplicate after normalization: first row wins.
                {"planning_area": "TOA PAYOH", "median_monthly_income": 9999.0},
                # Missing income value: dropped.
                {"planning_area": "BISHAN", "median_monthly_income": None},
            ]
        )

        result = merge_median_income(df, income)

        assert result.loc[0, "planning_area"] == "TOA PAYOH"
        assert result.loc[0, "median_monthly_income"] == pytest.approx(8000.0)
        # NaN df-side planning areas stay NaN — never the literal "NAN".
        assert pd.isna(result.loc[1, "planning_area"])
        assert pd.isna(result.loc[1, "median_monthly_income"])
        assert "NAN" not in set(result["planning_area"].dropna())

    def test_input_frame_is_not_mutated(self):
        df = pd.DataFrame([{"planning_area": "Toa Payoh", "price": 1.0}])
        income = pd.DataFrame([{"planning_area": "TOA PAYOH", "median_monthly_income": 8000.0}])

        result = merge_median_income(df, income)

        assert df.loc[0, "planning_area"] == "Toa Payoh"  # original untouched
        assert "median_monthly_income" not in df.columns
        assert result.loc[0, "planning_area"] == "TOA PAYOH"

    def test_empty_income_source_returns_frame_unchanged(self):
        df = pd.DataFrame([{"planning_area": "Toa Payoh", "price": 1.0}])
        result = merge_median_income(df, pd.DataFrame())
        assert result is df
        assert "median_monthly_income" not in result.columns

    def test_missing_planning_area_column_returns_frame_unchanged(self):
        df = pd.DataFrame([{"price": 1.0}])
        income = pd.DataFrame([{"planning_area": "TOA PAYOH", "median_monthly_income": 8000.0}])
        result = merge_median_income(df, income)
        assert result is df


class TestSqftPerSqmConstant:
    def test_constant_is_the_exact_sqft_per_sqm_factor(self):
        assert SQFT_PER_SQM == 10.7639


class TestNormalizeHdbFlatType:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("3 Room", "3-ROOM"),
            ("5-room", "5-ROOM"),
            ("4ROOM", "4-ROOM"),
            ("exec", "EXECUTIVE"),
            ("EXEC.", "EXECUTIVE"),
            ("Multi Generation", "MULTI-GENERATION"),
            ("mg", "MULTI-GENERATION"),
            ("Studio Apartment", "2-ROOM"),
            ("1 ROOM", "1-ROOM"),
            # Aggregated sentinel and unknown values pass through unchanged.
            ("ALL", "ALL"),
            ("all", "ALL"),
            ("Penthouse", "PENTHOUSE"),
        ],
    )
    def test_variants_map_to_canonical(self, raw, expected):
        assert normalize_hdb_flat_type(pd.Series([raw])).iloc[0] == expected

    def test_series_order_preserved(self):
        result = normalize_hdb_flat_type(pd.Series(["3 Room", "ALL", "EXEC"]))
        assert result.tolist() == ["3-ROOM", "ALL", "EXECUTIVE"]
