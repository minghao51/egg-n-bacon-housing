"""Focused tests for components/feature_transactions.py — town-merge equivalence.

Roadmap item 15: the town supply/population orchestration moved into
``utils.hdb_lookups.merge_town_context``. These tests pin the refactor:

- an equivalence test against a verbatim replica of the retired inline block
  (values + row order + columns must match exactly);
- a fixture-driven end-to-end test through the real
  ``validate_transactions_enriched`` node with hand-computed expected values.

Roadmap item 23: month is derived exactly once, in
``_enforce_transaction_time_contract``; the rental/macro joins reuse that
canonical column instead of re-copying and re-parsing the ~1M-row frame.
``TestMonthDerivationEquivalence`` pins month values, row order, dtype, and
join outcomes on a frame that exercises every join path.
"""

import inspect
from datetime import date

import numpy as np
import pandas as pd
import pytest

from egg_n_bacon_housing.components import feature_transactions
from egg_n_bacon_housing.utils.hdb_lookups import (
    dwelling_units_lookup,
    merge_town_context,
    population_lookup,
    population_per_dwelling,
)

pytestmark = pytest.mark.unit


def _reference_town_merge(
    df: pd.DataFrame,
    raw_dwelling_units_by_town: pd.DataFrame,
    raw_hdb_resident_population: pd.DataFrame,
) -> pd.DataFrame:
    """Verbatim replica of the retired inline block in
    ``validate_transactions_enriched`` (pre item-15 refactor).

    Kept here as the equivalence oracle: the shared
    ``merge_town_context`` must reproduce this output exactly.
    """
    town_col = "town" if "town" in df.columns else None
    if town_col:
        df = df.copy()
        df["_town_upper"] = df[town_col].astype(str).str.strip().str.upper()

        dwell_lookup = dwelling_units_lookup(raw_dwelling_units_by_town)
        if not dwell_lookup.empty:
            df = df.merge(dwell_lookup, on="_town_upper", how="left")

        if "dwelling_units_in_town" not in df.columns:
            df["dwelling_units_in_town"] = pd.NA

        pop_lookup = population_lookup(raw_hdb_resident_population)
        if not pop_lookup.empty:
            df = df.merge(pop_lookup, on="_town_upper", how="left")

        if "population_in_town" not in df.columns:
            df["population_in_town"] = pd.NA

        df["population_per_dwelling"] = population_per_dwelling(df)

        df = df.drop(columns=["_town_upper"], errors="ignore")
    return df


def _town_fixture_inputs():
    """Shared source frames: case/space variants, a zero-unit town, an
    unknown town, and an older survey/financial year that must be ignored."""
    tx = pd.DataFrame(
        [
            {"town": "TOA PAYOH", "price": 500_000.0},
            {"town": " bedok ", "price": 400_000.0},
            {"town": "UNKNOWN TOWN", "price": 600_000.0},
            {"town": "Toa Payoh", "price": 550_000.0},
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
            # Older financial year: ignored.
            {
                "town_or_estate": "TOA PAYOH",
                "no_of_dwelling_units": 999,
                "financial_year": 2023,
                "sold_or_rental": "Sold Units",
            },
            # Zero units: ratio must degrade to NA, not divide by zero.
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
            {"town_estate": " Toa Payoh", "number": 50, "shs_year": 2023},
            {"town_estate": "BEDOK", "number": 250, "shs_year": 2023},
            # Older survey year: ignored.
            {"town_estate": "BEDOK", "number": 9_999, "shs_year": 2022},
        ]
    )
    return tx, dwell, population


class TestMergeTownContextEquivalence:
    def test_matches_retired_inline_block_values_and_row_order(self):
        tx, dwell, population = _town_fixture_inputs()

        reference = _reference_town_merge(tx, dwell, population)
        result = merge_town_context(tx, dwell, population)

        pd.testing.assert_frame_equal(result, reference)

    def test_matches_retired_inline_block_when_lookups_are_empty(self):
        tx, _dwell, _population = _town_fixture_inputs()

        reference = _reference_town_merge(tx, pd.DataFrame(), pd.DataFrame())
        result = merge_town_context(tx, pd.DataFrame(), pd.DataFrame())

        pd.testing.assert_frame_equal(result, reference)
        assert result["dwelling_units_in_town"].isna().all()
        assert result["population_per_dwelling"].isna().all()

    def test_no_town_column_returns_frame_unchanged(self):
        tx, dwell, population = _town_fixture_inputs()
        tx = tx.drop(columns=["town"])

        result = merge_town_context(tx, dwell, population)

        assert result is tx
        assert "population_per_dwelling" not in tx.columns

    def test_matches_retired_town360_block_on_uppercase_town_frame(self):
        """The town_360 site merged lookups renamed onto its (already
        uppercase) ``town`` column; merge_town_context must be equivalent."""
        _tx, dwell, population = _town_fixture_inputs()
        grouped = pd.DataFrame(
            {"town": ["TOA PAYOH", "BEDOK", "UNKNOWN TOWN"], "median_price": [1.0, 2.0, 3.0]}
        )

        # Verbatim replica of the retired town_360 block (annual-value
        # broadcast excluded — that stays call-site-specific).
        result_ref = grouped.copy()
        dwell_lookup = dwelling_units_lookup(dwell)
        if not dwell_lookup.empty:
            dwell_lookup = dwell_lookup.rename(columns={"_town_upper": "town"})
            result_ref = result_ref.merge(dwell_lookup, on="town", how="left")
        pop_lookup = population_lookup(population)
        if not pop_lookup.empty:
            pop_lookup = pop_lookup.rename(columns={"_town_upper": "town"})
            result_ref = result_ref.merge(pop_lookup, on="town", how="left")
        if (
            "dwelling_units_in_town" in result_ref.columns
            and "population_in_town" in result_ref.columns
        ):
            result_ref["population_per_dwelling"] = population_per_dwelling(result_ref)

        result = merge_town_context(grouped, dwell, population)

        pd.testing.assert_frame_equal(result, result_ref)
        assert "_town_upper" not in result.columns

    def test_input_frame_is_not_mutated(self):
        tx, dwell, population = _town_fixture_inputs()

        merge_town_context(tx, dwell, population)

        assert "_town_upper" not in tx.columns
        assert "dwelling_units_in_town" not in tx.columns
        assert "population_per_dwelling" not in tx.columns


class TestValidateTransactionsEnrichedTownMerge:
    """End-to-end fixture through the real node: town context + per-row
    annual-value join, with exact values and input row order."""

    def _geocoded_fixture(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.85,
                    "town": "TOA PAYOH",
                    "price": 500_000.0,
                    "flat_type": "4 Room",
                    "property_type": "HDB",
                    "floor_area_sqft": 100.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "lat": 1.36,
                    "lon": 103.86,
                    "town": " bedok ",
                    "price": 400_000.0,
                    "flat_type": "EXEC",
                    "property_type": "HDB",
                    "floor_area_sqft": 120.0,
                    "transaction_date": pd.Timestamp("2024-01-20"),
                },
                {
                    "lat": 1.37,
                    "lon": 103.87,
                    "town": "UNKNOWN TOWN",
                    "price": 600_000.0,
                    "flat_type": "3 ROOM",
                    "property_type": "HDB",
                    "floor_area_sqft": 80.0,
                    "transaction_date": pd.Timestamp("2024-01-25"),
                },
                {
                    "lat": 1.38,
                    "lon": 103.88,
                    "town": "Toa Payoh",
                    "price": 550_000.0,
                    "flat_type": "4-ROOM",
                    "property_type": "HDB",
                    "floor_area_sqft": 90.0,
                    "transaction_date": pd.Timestamp("2024-01-30"),
                },
            ]
        )

    def _dwell_fixture(self) -> pd.DataFrame:
        return pd.DataFrame(
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

    def _population_fixture(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"town_estate": "TOA PAYOH", "number": 300, "shs_year": 2023},
                {"town_estate": "BEDOK", "number": 250, "shs_year": 2023},
            ]
        )

    def _annual_value_fixture(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "type_of_hdb": "4 Room",
                    "median_annual_value": "7000",
                    "property_tax_collection": "1200",
                    "financial_year": 2024,
                },
                {
                    "type_of_hdb": "3 Room",
                    "median_annual_value": "5000",
                    "property_tax_collection": "800",
                    "financial_year": 2024,
                },
                {
                    "type_of_hdb": "Executive & Others",
                    "median_annual_value": "3000",
                    "property_tax_collection": "500",
                    "financial_year": 2024,
                },
                # Older financial year: ignored by the lookup.
                {
                    "type_of_hdb": "4 Room",
                    "median_annual_value": "1",
                    "property_tax_collection": "1",
                    "financial_year": 2023,
                },
            ]
        )

    def test_town_context_and_annual_values_match_expected(self):
        result = feature_transactions.validate_transactions_enriched(
            geocoded_validated=self._geocoded_fixture(),
            location_dim=pd.DataFrame(),
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=self._dwell_fixture(),
            raw_hdb_resident_population=self._population_fixture(),
            raw_median_annual_value=self._annual_value_fixture(),
            raw_income_by_planning_area=pd.DataFrame(),
            pipeline_as_of_date=date(2024, 2, 1),
        )

        enriched = result["transactions_enriched"]
        quarantine = result["transactions_enriched_quarantine"]

        # Input row order preserved; every row survived validation.
        assert enriched["town"].tolist() == ["TOA PAYOH", " bedok ", "UNKNOWN TOWN", "Toa Payoh"]
        assert quarantine.empty

        # Town context: case/whitespace-normalized joins, per-town values.
        np.testing.assert_allclose(enriched["dwelling_units_in_town"], [100.0, 0.0, np.nan, 100.0])
        np.testing.assert_allclose(enriched["population_in_town"], [300.0, 250.0, np.nan, 300.0])
        # Ratio: 300/100 = 3.0; BEDOK has 0 units -> NA; unknown town -> NA.
        np.testing.assert_allclose(
            pd.to_numeric(enriched["population_per_dwelling"], errors="coerce").astype(float),
            [3.0, np.nan, np.nan, 3.0],
        )

        # Per-row IRAS annual-value join via normalized flat_type.
        np.testing.assert_allclose(enriched["annual_value"], [7000.0, 3000.0, 5000.0, 7000.0])
        np.testing.assert_allclose(enriched["property_tax"], [1200.0, 500.0, 800.0, 1200.0])

        # The temporary join key must not leak into the published frame.
        assert "_town_upper" not in enriched.columns
        assert "type_of_hdb" not in enriched.columns

        # Flat types are canonicalized unconditionally by the node.
        assert enriched["flat_type"].tolist() == [
            "4-ROOM",
            "EXECUTIVE",
            "3-ROOM",
            "4-ROOM",
        ]

    def test_missing_town_column_still_publishes_na_context_columns(self):
        geocoded = self._geocoded_fixture().drop(columns=["town"])

        result = feature_transactions.validate_transactions_enriched(
            geocoded_validated=geocoded,
            location_dim=pd.DataFrame(),
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=self._dwell_fixture(),
            raw_hdb_resident_population=self._population_fixture(),
            raw_median_annual_value=self._annual_value_fixture(),
            raw_income_by_planning_area=pd.DataFrame(),
            pipeline_as_of_date=date(2024, 2, 1),
        )

        enriched = result["transactions_enriched"]
        for col in (
            "dwelling_units_in_town",
            "population_in_town",
            "population_per_dwelling",
            "annual_value",
            "property_tax",
        ):
            assert col in enriched.columns
            assert enriched[col].isna().all()


class TestMonthDerivationEquivalence:
    """Item 23: month is derived exactly once, in the time contract.

    Every expectation below is the pre-refactor behavior: the canonical
    "YYYY-MM" month, source row order, the "string" month dtype (no merge
    upcast), and hand-computed rental/macro join outcomes on a frame that
    walks every join path — rental by (town, month), monthly macro, quarterly
    macro.
    """

    def _geocoded_fixture(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.85,
                    "town": "TOA PAYOH",
                    "price": 500_000.0,
                    "flat_type": "4 Room",
                    "property_type": "HDB",
                    "floor_area_sqft": 100.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "lat": 1.36,
                    "lon": 103.86,
                    "town": "BEDOK",
                    "price": 400_000.0,
                    "flat_type": "4 Room",
                    "property_type": "HDB",
                    "floor_area_sqft": 100.0,
                    "transaction_date": pd.Timestamp("2024-01-20"),
                },
                {
                    "lat": 1.37,
                    "lon": 103.87,
                    "town": "TOA PAYOH",
                    "price": 600_000.0,
                    "flat_type": "EXEC",
                    "property_type": "HDB",
                    "floor_area_sqft": 120.0,
                    "transaction_date": pd.Timestamp("2024-02-05"),
                },
                {
                    "lat": 1.38,
                    "lon": 103.88,
                    "town": "BEDOK",
                    "price": 450_000.0,
                    "flat_type": "3 Room",
                    "property_type": "HDB",
                    "floor_area_sqft": 80.0,
                    "transaction_date": pd.Timestamp("2024-02-25"),
                },
                {
                    "lat": 1.39,
                    "lon": 103.89,
                    "town": "TOA PAYOH",
                    "price": 700_000.0,
                    "flat_type": "5 Room",
                    "property_type": "HDB",
                    "floor_area_sqft": 130.0,
                    "transaction_date": pd.Timestamp("2024-03-10"),
                },
            ]
        )

    def _rental_fixture(self) -> pd.DataFrame:
        # month dtype mirrors production (ensure_month_column's "string").
        return pd.DataFrame(
            {
                "town": ["TOA PAYOH", "BEDOK", "TOA PAYOH"],
                "month": pd.array(["2024-01", "2024-01", "2024-02"], dtype="string"),
                "rental_yield_pct": [3.5, 3.0, 3.6],
            }
        )

    def _macro_fixture(self) -> dict[str, pd.DataFrame]:
        return {
            "cpi": pd.DataFrame(
                {"date": pd.to_datetime(["2024-01-01", "2024-02-01"]), "cpi": [100.0, 100.5]}
            ),
            "unemployment": pd.DataFrame(
                {
                    "quarter": pd.to_datetime(["2024-01-01", "2024-04-01"]),
                    "unemployment_rate": [2.0, 2.1],
                }
            ),
        }

    def _run_node(self, geocoded, rental, macro):
        return feature_transactions.validate_transactions_enriched(
            geocoded_validated=geocoded,
            location_dim=pd.DataFrame(),
            rental_yield=rental,
            raw_macro_data=macro,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            pipeline_as_of_date=date(2024, 4, 1),
        )

    def test_month_row_order_and_join_outcomes_unchanged(self):
        geocoded = self._geocoded_fixture()

        result = self._run_node(geocoded, self._rental_fixture(), self._macro_fixture())

        enriched = result["transactions_enriched"]
        quarantine = result["transactions_enriched_quarantine"]
        assert quarantine.empty

        # Source row order preserved.
        assert enriched["town"].tolist() == [
            "TOA PAYOH",
            "BEDOK",
            "TOA PAYOH",
            "BEDOK",
            "TOA PAYOH",
        ]

        # Canonical month, derived once, matching transaction_date.
        assert enriched["month"].tolist() == [
            "2024-01",
            "2024-01",
            "2024-02",
            "2024-02",
            "2024-03",
        ]
        assert isinstance(enriched["month"].dtype, pd.StringDtype)
        pd.testing.assert_series_equal(
            enriched["month"],
            enriched["transaction_date"].dt.to_period("M").astype("string"),
            check_names=False,
        )

        # Rental join by (town, month); missing keys degrade to NA.
        np.testing.assert_allclose(
            enriched["rental_yield_pct"].to_numpy(dtype=float),
            [3.5, 3.0, 3.6, np.nan, np.nan],
        )
        # Monthly macro join by month; March is absent from the lookup.
        np.testing.assert_allclose(
            enriched["cpi"].to_numpy(dtype=float), [100.0, 100.0, 100.5, 100.5, np.nan]
        )
        # Quarterly macro join; every fixture row falls in 2024Q1.
        np.testing.assert_allclose(enriched["unemployment_rate"].to_numpy(dtype=float), [2.0] * 5)

        # Temp join keys must not leak into the published frame.
        for col in ("_month", "_month_ts", "_quarter"):
            assert col not in enriched.columns

    def test_month_derived_even_without_join_paths(self):
        geocoded = self._geocoded_fixture()

        result = self._run_node(geocoded, pd.DataFrame(), {})

        enriched = result["transactions_enriched"]
        assert enriched["month"].tolist() == [
            "2024-01",
            "2024-01",
            "2024-02",
            "2024-02",
            "2024-03",
        ]
        assert enriched["town"].tolist() == [
            "TOA PAYOH",
            "BEDOK",
            "TOA PAYOH",
            "BEDOK",
            "TOA PAYOH",
        ]
        assert isinstance(enriched["month"].dtype, pd.StringDtype)

    def test_supplied_mismatched_month_raises(self):
        geocoded = self._geocoded_fixture()
        geocoded["month"] = "1999-12"

        with pytest.raises(ValueError, match="month must be YYYY-MM and match"):
            self._run_node(geocoded, self._rental_fixture(), self._macro_fixture())

    def test_default_validation_policy_is_sample(self):
        """Item 22c: node default flipped from "full" to "sample"."""
        signature = inspect.signature(feature_transactions.validate_transactions_enriched)
        assert signature.parameters["large_table_validation_policy"].default == "sample"
