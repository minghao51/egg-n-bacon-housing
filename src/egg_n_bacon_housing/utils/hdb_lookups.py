"""Shared HDB reference lookups and normalization helpers.

Single home for the gold feature lookups (town supply, resident population,
IRAS annual value, median income) and the HDB flat-type normalizer, so
``feature_profiles``, ``feature_transactions``, and ``feature_rental`` no
longer share logic through private cross-module imports.
"""

import numpy as np
import pandas as pd

# 1 sqm = 10.7639 sqft (exact factor; single source for all sqft<->sqm conversion).
SQFT_PER_SQM: float = 10.7639


def dwelling_units_lookup(raw_dwelling_units_by_town: pd.DataFrame) -> pd.DataFrame:
    """Latest-financial-year sold units per town.

    Returns columns ``_town_upper``, ``dwelling_units_in_town``; empty frame
    when the source is empty or its schema drifted.
    """
    raw = raw_dwelling_units_by_town
    if raw.empty or not {
        "town_or_estate",
        "no_of_dwelling_units",
        "financial_year",
        "sold_or_rental",
    }.issubset(raw.columns):
        return pd.DataFrame()
    dwell = raw.copy()
    dwell["financial_year"] = pd.to_numeric(dwell["financial_year"], errors="coerce")
    dwell = dwell[dwell["financial_year"] == dwell["financial_year"].max()]
    dwell = dwell[dwell["sold_or_rental"].astype(str).str.strip() == "Sold Units"]
    dwell["no_of_dwelling_units"] = pd.to_numeric(dwell["no_of_dwelling_units"], errors="coerce")
    dwell["_town_upper"] = dwell["town_or_estate"].astype(str).str.strip().str.upper()
    return (
        dwell.groupby("_town_upper")["no_of_dwelling_units"]
        .sum()
        .reset_index()
        .rename(columns={"no_of_dwelling_units": "dwelling_units_in_town"})
    )


def population_lookup(raw_hdb_resident_population: pd.DataFrame) -> pd.DataFrame:
    """Latest-SHS-year resident population per town.

    Returns columns ``_town_upper``, ``population_in_town``; empty frame when
    the source is empty or its schema drifted.
    """
    raw = raw_hdb_resident_population
    if raw.empty or not {"town_estate", "number", "shs_year"}.issubset(raw.columns):
        return pd.DataFrame()
    pop = raw.copy()
    pop["shs_year"] = pd.to_numeric(pop["shs_year"], errors="coerce")
    pop = pop[pop["shs_year"] == pop["shs_year"].max()]
    pop["number"] = pd.to_numeric(pop["number"], errors="coerce")
    pop["_town_upper"] = pop["town_estate"].astype(str).str.strip().str.upper()
    # Multi-row towns are summed (consistent with dwelling_units_lookup).
    # Previously this kept an arbitrary first row per town, silently dropping
    # the population of any town reported across multiple source rows.
    return (
        pop.groupby("_town_upper", as_index=False)["number"]
        .sum()
        .rename(columns={"number": "population_in_town"})
    )


def annual_value_lookup(raw_median_annual_value: pd.DataFrame) -> pd.DataFrame:
    """Latest-financial-year IRAS annual value/tax per flat-type category.

    Returns columns ``type_of_hdb``, ``annual_value``, ``property_tax``;
    empty frame when the source is empty or its schema drifted.
    """
    raw = raw_median_annual_value
    if raw.empty or not {
        "type_of_hdb",
        "median_annual_value",
        "property_tax_collection",
        "financial_year",
    }.issubset(raw.columns):
        return pd.DataFrame()
    mav = raw.copy()
    mav["financial_year"] = pd.to_numeric(mav["financial_year"], errors="coerce")
    mav = mav[mav["financial_year"] == mav["financial_year"].max()]
    mav["annual_value"] = pd.to_numeric(mav["median_annual_value"], errors="coerce")
    mav["property_tax"] = pd.to_numeric(mav["property_tax_collection"], errors="coerce")
    return mav[["type_of_hdb", "annual_value", "property_tax"]].drop_duplicates(
        subset="type_of_hdb", keep="first"
    )


def population_per_dwelling(df: pd.DataFrame) -> pd.Series:
    """Row-wise population / dwelling-unit ratio.

    Requires the ``dwelling_units_in_town`` and ``population_in_town``
    columns to exist (missing values allowed); returns ``NA`` wherever the
    unit count is not a positive number.
    """
    units = pd.to_numeric(df["dwelling_units_in_town"], errors="coerce")
    pop_vals = pd.to_numeric(df["population_in_town"], errors="coerce")
    return pd.Series(np.where(units > 0, pop_vals / units, pd.NA), index=df.index)


def merge_median_income(
    df: pd.DataFrame, raw_income_by_planning_area: pd.DataFrame
) -> pd.DataFrame:
    """Left-join median monthly income onto ``df`` by normalized planning area.

    Single implementation shared by ``planning_area_360`` and
    ``transactions_enriched``. NaN planning areas are guarded on both sides
    (``astype(str)`` would turn them into the literal ``"NAN"`` key), source
    rows without an income value are dropped, and the first row wins for
    duplicate planning areas. Returns ``df`` unchanged when the income source
    is empty or ``df`` lacks a ``planning_area`` column.
    """
    if raw_income_by_planning_area.empty or "planning_area" not in df.columns:
        return df

    income_lookup = raw_income_by_planning_area[["planning_area", "median_monthly_income"]].copy()
    # Guard against NaN keys: astype(str) would turn them into the literal
    # "NAN", creating a bogus planning area in the lookup.
    income_lookup = income_lookup[income_lookup["planning_area"].notna()]
    income_lookup["planning_area"] = (
        income_lookup["planning_area"].astype(str).str.strip().str.upper()
    )
    income_lookup = income_lookup.dropna(subset=["median_monthly_income"])
    income_lookup = income_lookup.drop_duplicates(subset="planning_area", keep="first")

    result = df.copy()
    # Only normalize non-null values; astype(str) on the whole column would
    # turn NaN into the literal "NAN" and leak it into published metrics.
    known_planning_area = result["planning_area"].notna()
    result.loc[known_planning_area, "planning_area"] = (
        result.loc[known_planning_area, "planning_area"].astype(str).str.strip().str.upper()
    )
    return result.merge(income_lookup, on="planning_area", how="left")


def _build_flat_type_map() -> dict[str, str]:
    canonical = [
        ("1-ROOM", "1-ROOM"),
        ("2-ROOM", "2-ROOM"),
        ("3-ROOM", "3-ROOM"),
        ("4-ROOM", "4-ROOM"),
        ("5-ROOM", "5-ROOM"),
        ("EXECUTIVE", "EXECUTIVE"),
        ("MULTI-GENERATION", "MULTI-GENERATION"),
    ]
    variants: dict[str, str] = {}
    for std, val in canonical:
        for form in [std, std.replace("-", " "), std.replace("-", "")]:
            variants[form] = val
    variants["EXEC"] = "EXECUTIVE"
    variants["EXEC."] = "EXECUTIVE"
    variants["MULTI-GEN"] = "MULTI-GENERATION"
    variants["MULTI GEN"] = "MULTI-GENERATION"
    variants["MG"] = "MULTI-GENERATION"
    variants["STUDIO"] = "2-ROOM"
    variants["STUDIO APARTMENT"] = "2-ROOM"
    m: dict[str, str] = {}
    for k, v in {**variants}.items():
        m[k] = v
        m[k.upper()] = v
        m[k.lower()] = v
    return m


_FLAT_TYPE_NORMALIZE_MAP: dict[str, str] = _build_flat_type_map()


def normalize_hdb_flat_type(series: pd.Series) -> pd.Series:
    """Normalize HDB flat-type variants to canonical dashed-upper form.

    Unmapped values (including the aggregated ``"ALL"`` sentinel) pass
    through unchanged after whitespace strip + upper-case.
    """
    upper = series.astype(str).str.strip().str.upper()
    return upper.map(_FLAT_TYPE_NORMALIZE_MAP).fillna(upper)
