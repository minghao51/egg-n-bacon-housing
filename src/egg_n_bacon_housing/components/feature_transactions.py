"""Transaction-enrichment Hamilton nodes and helpers."""

import logging
from datetime import date
from typing import Literal

import numpy as np
import pandas as pd
from hamilton.function_modifiers import extract_fields, hamilton_exclude

from egg_n_bacon_housing.schemas.feature_models import HFeatureTransaction
from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.hdb_lookups import (
    annual_value_lookup,
    merge_median_income,
    merge_town_context,
    normalize_hdb_flat_type,
)
from egg_n_bacon_housing.utils.validation_gateway import (
    empty_extracted,
    extracted_validation,
    validate_and_quarantine,
)

logger = logging.getLogger(__name__)


@hamilton_exclude
def transactions_enriched(*args, **kwargs) -> pd.DataFrame:
    # The Hamilton node requires this input.  The excluded direct-call facade
    # keeps a deterministic convenience default for small unit-level callers;
    # production execution always injects it through ``run_pipeline``.
    kwargs.setdefault("pipeline_as_of_date", date.today())
    return validate_transactions_enriched(*args, **kwargs)["transactions_enriched"]


# IRAS type_of_hdb category lookup for the annual-value merge. Two key
# families, same values: the canonical dashed-upper forms produced by
# ``normalize_hdb_flat_type`` (fast path — the node normalizes flat_type
# unconditionally upstream), and the dash/space-insensitive compact forms
# ("4 ROOM", "4-room", "4Room" -> "4ROOM") for callers that skipped
# normalization.
_ANNUAL_VALUE_TYPE_MAP: dict[str, str] = {
    "1-ROOM": "1 or 2 Room",
    "2-ROOM": "1 or 2 Room",
    "3-ROOM": "3 Room",
    "4-ROOM": "4 Room",
    "5-ROOM": "5 Room",
    "EXECUTIVE": "Executive & Others",
    "MULTI-GENERATION": "Executive & Others",
    "1ROOM": "1 or 2 Room",
    "2ROOM": "1 or 2 Room",
    "3ROOM": "3 Room",
    "4ROOM": "4 Room",
    "5ROOM": "5 Room",
    "MULTIGENERATION": "Executive & Others",
}


def _annual_value_type_series(flat_type: pd.Series) -> pd.Series:
    """Vectorized IRAS type_of_hdb category lookup for a flat_type Series.

    Replaces a row-wise ``.apply`` over ~1M transactions with one dict
    ``.map``. Fast path: the node's flat_type is already canonical
    (``normalize_hdb_flat_type`` output), so a single ``.map`` resolves every
    row. Slow path: only unmapped non-null residuals — empty in production —
    pay the dash/space-insensitive compact-form matching, so raw spaced or
    lowercase variants ("4 room", "4Room") still map. This is the same
    contract as the retired per-row ``_map_flat_type_for_annual_value``:
    unmapped values fall back to their strip+upper form, and a null
    flat_type yields a null category (previously the string "NAN", which
    likewise never matched an IRAS category — merge outcome unchanged).
    """
    mapped = flat_type.map(_ANNUAL_VALUE_TYPE_MAP)
    residual = mapped.isna() & flat_type.notna()
    if bool(residual.any()):
        upper = flat_type[residual].astype(str).str.strip().str.upper()
        compact = upper.str.replace(" ", "", regex=False).str.replace("-", "", regex=False)
        mapped.loc[residual] = compact.map(_ANNUAL_VALUE_TYPE_MAP).fillna(upper)
    return mapped


def _enforce_transaction_time_contract(
    df: pd.DataFrame, max_transaction_age_days: int | None, pipeline_as_of_date: date
) -> pd.DataFrame:
    """Require valid dates/months and optionally enforce source freshness.

    This is the single month-derivation site for the node (roadmap item 23):
    ``month`` is derived once from the parsed dates as the canonical
    ``Period("M")`` string (``YYYY-MM``) and every later consumer — the
    rental and macro monthly merge keys, the quarterly key — reuses it
    instead of re-parsing or re-copying the ~1M-row frame.
    """
    require_columns(df, {"transaction_date"}, "geocoded_validated")
    result = df.copy()
    dates = pd.to_datetime(result["transaction_date"], errors="coerce")
    invalid_dates = int(dates.isna().sum())
    if invalid_dates:
        raise ValueError(f"transactions_enriched has {invalid_dates} invalid transaction_date rows")

    expected_month = dates.dt.to_period("M").astype("string")
    if "month" in result.columns:
        supplied_month = result["month"].astype("string").str.strip()
        invalid_month = supplied_month.isna() | ~supplied_month.str.fullmatch(r"\d{4}-\d{2}")
        mismatched_month = ~invalid_month & supplied_month.ne(expected_month)
        if invalid_month.any() or mismatched_month.any():
            raise ValueError(
                "transactions_enriched month must be YYYY-MM and match transaction_date"
            )
    result["transaction_date"] = dates
    result["month"] = expected_month

    if max_transaction_age_days is not None:
        latest = dates.max()
        now = pd.Timestamp(pipeline_as_of_date)
        if latest.tz is not None:
            now = now.tz_localize(latest.tz)
        age_days = (now.normalize() - latest.normalize()).days
        if age_days > max_transaction_age_days:
            raise ValueError(
                f"transactions_enriched latest transaction is {age_days} days old; "
                f"maximum is {max_transaction_age_days}"
            )
    return result


@extract_fields(
    {"transactions_enriched": pd.DataFrame, "transactions_enriched_quarantine": pd.DataFrame}
)
def validate_transactions_enriched(
    geocoded_validated: pd.DataFrame,
    location_dim: pd.DataFrame,
    rental_yield: pd.DataFrame,
    raw_macro_data: dict[str, pd.DataFrame],
    raw_dwelling_units_by_town: pd.DataFrame,
    raw_hdb_resident_population: pd.DataFrame,
    raw_median_annual_value: pd.DataFrame,
    raw_income_by_planning_area: pd.DataFrame,
    pipeline_as_of_date: date,
    large_table_validation_policy: Literal["sample", "full", "fail"] = "sample",
    max_transaction_age_days: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Join location_dim onto transactions + merge macro + yield + supply.

    Fast merge: location_dim (10K) → transactions (1M) by (lat, lon),
    then macro indicators, rental yield, town supply, income, and annual value.
    """
    if geocoded_validated.empty:
        return empty_extracted(
            geocoded_validated, "transactions_enriched", "transactions_enriched_quarantine"
        )

    df = _enforce_transaction_time_contract(
        geocoded_validated,
        max_transaction_age_days=max_transaction_age_days,
        pipeline_as_of_date=pipeline_as_of_date,
    )
    require_columns(df, {"lat", "lon", "price"}, "geocoded_validated")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    # --- Derived columns ---
    if "price" in df.columns and "floor_area_sqft" in df.columns:
        price = pd.to_numeric(df["price"], errors="coerce")
        floor_area_sqft = pd.to_numeric(df["floor_area_sqft"], errors="coerce")
        df["psf"] = np.where(floor_area_sqft > 0, price / floor_area_sqft, np.nan)
    else:
        df["psf"] = np.nan

    if "remaining_lease_months" in df.columns:
        df["remaining_lease_years"] = df["remaining_lease_months"] / 12

    # --- LEFT JOIN location_dim by (lat, lon) ---
    if not location_dim.empty:
        loc_join = location_dim.copy()
        overlap = set(df.columns) & set(loc_join.columns) - {"lat", "lon"}
        loc_join = loc_join.drop(columns=list(overlap))
        df = df.merge(loc_join, on=["lat", "lon"], how="left")
        logger.info("transactions_enriched: joined location_dim (%s cols)", len(loc_join.columns))

    # --- Flat-type canonicalization ---
    # Canonical dashed-upper form ("4-ROOM") is the join key for both the
    # rental merge below and the annual-value category mapping further down.
    # Normalize unconditionally (when the column exists) so enrichment output
    # does not depend on rental data being present for flat_type to match.
    if "flat_type" in df.columns:
        df["flat_type"] = normalize_hdb_flat_type(df["flat_type"])

    # --- Rental yield ---
    # ``month`` is guaranteed canonical (YYYY-MM string) by the time contract
    # above, so it is reused directly as the merge key — no ensure_month_column
    # round trip (which would deep-copy and re-parse the ~1M-row frame).
    if not rental_yield.empty and "rental_yield_pct" in rental_yield.columns:
        rental_df = rental_yield.copy()
        if "flat_type" in rental_df.columns:
            rental_df["flat_type"] = normalize_hdb_flat_type(rental_df["flat_type"])

        # rental_yield is aggregated across flat types (flat_type == "ALL" sentinel).
        # A constant sentinel can never match transaction-level flat_type values, so
        # drop it and let merge_priority fall through to (town, month). If rental
        # data ever becomes per-flat-type, the 3-key merge re-engages automatically.
        if "flat_type" in rental_df.columns and rental_df["flat_type"].nunique(dropna=True) <= 1:
            rental_df = rental_df.drop(columns=["flat_type"])

        merge_priority = [["town", "month", "flat_type"], ["town", "month"]]
        merge_keys: list[str] = []
        for keys in merge_priority:
            if all(k in df.columns for k in keys) and all(k in rental_df.columns for k in keys):
                merge_keys = keys
                break

        if merge_keys:
            rental_cols = [*merge_keys, "rental_yield_pct"]
            rental_lookup = rental_df[rental_cols].dropna(subset=["rental_yield_pct"])
            sort_col = next((c for c in merge_keys if "month" in c or "date" in c), merge_keys[0])
            rental_lookup = rental_lookup.sort_values(sort_col).drop_duplicates(
                subset=merge_keys, keep="last"
            )
            df = df.merge(rental_lookup, on=merge_keys, how="left")

    # --- Macro indicators ---
    # Combine per-indicator lookups into ONE monthly frame and ONE quarterly
    # frame, then left-merge each onto the ~1M-row transactions frame a single
    # time (previously 8 sequential merges, each a full pass). The indicator
    # value columns are mutually distinct and do not pre-exist on df, so a
    # plain left-merge is exactly equivalent to the old per-indicator
    # suffix/coalesce approach -- verified by an equivalence test.
    #
    # Month is derived exactly once, in ``_enforce_transaction_time_contract``:
    # the canonical ``month`` string column is reused directly as the monthly
    # merge key (lookup keys are cast to the same "string" dtype so the merge
    # cannot upcast month), and the quarterly key derives from the
    # already-parsed datetime ``transaction_date``. The previous
    # ``ensure_month_column`` calls deep-copied and re-parsed the ~1M-row
    # frame twice for identical values, and the ``_month_ts``/``_month``
    # columns round-tripped month → datetime → period → string → datetime.
    monthly_indicators = {
        "cpi": ("date", "cpi"),
        "sora": ("date", "sora_rate"),
        "bank_rates": ("date", "sora_3m"),
    }
    monthly_lookups: list[pd.DataFrame] = []
    monthly_present: set[str] = set()
    for key, (date_col, value_col) in monthly_indicators.items():
        macro_df = raw_macro_data.get(key, pd.DataFrame())
        if macro_df.empty or date_col not in macro_df.columns:
            continue
        lookup = macro_df[[date_col, value_col]].copy()
        lookup[date_col] = pd.to_datetime(lookup[date_col], errors="coerce")
        lookup["month"] = lookup[date_col].dt.to_period("M").astype("string")
        lookup = lookup.dropna(subset=["month", value_col])
        lookup = lookup.sort_values("month").drop_duplicates(subset="month", keep="last")
        monthly_lookups.append(lookup[["month", value_col]])
        monthly_present.add(value_col)

    if monthly_lookups:
        monthly_combined = monthly_lookups[0]
        for nxt in monthly_lookups[1:]:
            monthly_combined = monthly_combined.merge(nxt, on="month", how="outer")
        df = df.merge(monthly_combined, on="month", how="left")
    for value_col in (v for _, v in monthly_indicators.values() if v not in monthly_present):
        df[value_col] = pd.NA

    quarterly_indicators = {
        "unemployment": ("quarter", "unemployment_rate"),
        "gdp": ("quarter", "gdp"),
        "hdb_rpi": ("quarter", "hdb_rpi"),
        "ura_ppi": ("quarter", "ura_ppi"),
        "wage_growth": ("quarter", "wage_growth"),
    }
    df["_quarter"] = df["transaction_date"].dt.to_period("Q")
    quarterly_lookups: list[pd.DataFrame] = []
    quarterly_present: set[str] = set()
    for key, (qtr_col, value_col) in quarterly_indicators.items():
        macro_df = raw_macro_data.get(key, pd.DataFrame())
        if macro_df.empty or qtr_col not in macro_df.columns:
            continue
        lookup = macro_df[[qtr_col, value_col]].copy()
        lookup[qtr_col] = pd.to_datetime(lookup[qtr_col], errors="coerce")
        lookup["_quarter"] = lookup[qtr_col].dt.to_period("Q")
        lookup = lookup.dropna(subset=["_quarter", value_col])
        lookup = lookup.sort_values("_quarter").drop_duplicates(subset="_quarter", keep="last")
        quarterly_lookups.append(lookup[["_quarter", value_col]])
        quarterly_present.add(value_col)

    if quarterly_lookups:
        quarterly_combined = quarterly_lookups[0]
        for nxt in quarterly_lookups[1:]:
            quarterly_combined = quarterly_combined.merge(nxt, on="_quarter", how="outer")
        df = df.merge(quarterly_combined, on="_quarter", how="left")
    for value_col in (v for _, v in quarterly_indicators.values() if v not in quarterly_present):
        df[value_col] = pd.NA

    df = df.drop(columns=["_quarter"], errors="ignore")

    # --- Town supply, population, annual value ---
    # merge_town_context is the shared town-merge orchestration (normalized
    # town key + dwelling/population lookups + population_per_dwelling);
    # the per-row IRAS annual-value join below stays transaction-specific.
    if "town" in df.columns:
        df = merge_town_context(
            df,
            raw_dwelling_units_by_town=raw_dwelling_units_by_town,
            raw_hdb_resident_population=raw_hdb_resident_population,
        )

        mav_lookup = annual_value_lookup(raw_median_annual_value)
        if not mav_lookup.empty and "flat_type" in df.columns:
            df["_av_type"] = _annual_value_type_series(df["flat_type"])
            df = df.merge(mav_lookup, left_on="_av_type", right_on="type_of_hdb", how="left")
            df = df.drop(columns=["_av_type", "type_of_hdb"], errors="ignore")

    # --- Income by planning area ---
    df = merge_median_income(df, raw_income_by_planning_area)

    for col in (
        "dwelling_units_in_town",
        "population_in_town",
        "population_per_dwelling",
        "annual_value",
        "property_tax",
        "wage_growth",
        "median_monthly_income",
    ):
        if col not in df.columns:
            df[col] = pd.NA

    # Price stratum: population quintile of transaction price (Q1 cheapest
    # through Q5 most expensive). Deterministic given the frame (rank-based
    # qcut); NA where price is null — those rows are quarantined at the gold
    # boundary below. Fewer than five distinct prices degrade to NA (the
    # duplicates-dropped bin count cannot cover five labels).
    try:
        strata = pd.qcut(df["price"], q=5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"], duplicates="drop")
        df["price_stratum"] = strata.astype("string")
    except ValueError:
        df["price_stratum"] = pd.NA

    return extracted_validation(
        validate_and_quarantine(
            df,
            HFeatureTransaction,
            "transactions_enriched",
            sample_validation_size=10_000,
            large_table_policy=large_table_validation_policy,
        ),
        "transactions_enriched",
        "transactions_enriched_quarantine",
    )
