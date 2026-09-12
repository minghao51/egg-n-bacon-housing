"""Profile-entity Hamilton nodes and shared source lookups."""

import logging

import pandas as pd
from hamilton.function_modifiers import extract_fields, hamilton_exclude

from egg_n_bacon_housing.schemas.feature_models import BlockProfile, PlanningArea360, Town360
from egg_n_bacon_housing.utils.hdb_lookups import (
    annual_value_lookup,
    merge_median_income,
    merge_town_context,
)
from egg_n_bacon_housing.utils.validation_gateway import (
    empty_extracted,
    extracted_validation,
    validate_and_quarantine,
)

logger = logging.getLogger(__name__)


@hamilton_exclude
def planning_area_360(*args, **kwargs) -> pd.DataFrame:
    return validate_planning_area_360(*args, **kwargs)["planning_area_360"]


@hamilton_exclude
def town_360(*args, **kwargs) -> pd.DataFrame:
    return validate_town_360(*args, **kwargs)["town_360"]


@hamilton_exclude
def block_profile(*args, **kwargs) -> pd.DataFrame:
    return validate_block_profile(*args, **kwargs)["block_profile"]


@extract_fields({"planning_area_360": pd.DataFrame, "planning_area_360_quarantine": pd.DataFrame})
def validate_planning_area_360(
    location_dim: pd.DataFrame,
    transactions_enriched: pd.DataFrame,
    raw_income_by_planning_area: pd.DataFrame,
    raw_macro_data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Build the planning-area 360-degree profile table (~43 rows).

    Aggregates spatial medians from location_dim, market stats from
    transactions_enriched, and merges income + latest macro indicators.
    """
    if location_dim.empty or "planning_area" not in location_dim.columns:
        return empty_extracted(location_dim, "planning_area_360", "planning_area_360_quarantine")

    pre_loc_filter = len(location_dim)
    loc = location_dim[location_dim["planning_area"].notna()].copy()
    dropped_null_pa = pre_loc_filter - len(loc)
    if dropped_null_pa:
        logger.warning(
            "planning_area_360: dropped %s location_dim row(s) with null planning_area; kept %s",
            dropped_null_pa,
            len(loc),
        )

    dist_cols = [c for c in loc.columns if c.startswith("dist_to_nearest_")]
    loc_spatial = loc.groupby("planning_area")[dist_cols].median().reset_index()
    rename_map = {c: c.replace("dist_to_nearest_", "median_dist_to_") for c in dist_cols}
    loc_spatial = loc_spatial.rename(columns=rename_map)

    agg_map: dict[str, str] = {}
    if "year_completed" in loc.columns:
        agg_map["year_completed"] = "mean"
    if "max_floor_lvl" in loc.columns:
        agg_map["max_floor_lvl"] = "mean"
    if "total_dwelling_units" in loc.columns:
        agg_map["total_dwelling_units"] = "sum"
    if agg_map:
        block_profile = loc.groupby("planning_area").agg(agg_map).reset_index()
        block_profile = block_profile.rename(
            columns={
                "year_completed": "avg_year_completed",
                "max_floor_lvl": "avg_max_floor",
            }
        )
        loc_spatial = loc_spatial.merge(block_profile, on="planning_area", how="left")

    if "region" in loc.columns:
        pa_region = loc.groupby("planning_area")["region"].first().reset_index()
        loc_spatial = loc_spatial.merge(pa_region, on="planning_area", how="left")

    result = loc_spatial

    if not transactions_enriched.empty and "planning_area" in transactions_enriched.columns:
        pre_tx_filter = len(transactions_enriched)
        tx = transactions_enriched[transactions_enriched["planning_area"].notna()].copy()
        dropped_null_tx = pre_tx_filter - len(tx)
        if dropped_null_tx:
            logger.warning(
                "planning_area_360: dropped %s transactions_enriched row(s) with null "
                "planning_area; kept %s",
                dropped_null_tx,
                len(tx),
            )
        agg_dict: dict[str, tuple] = {
            "median_price": ("price", "median"),
            "transaction_volume": ("price", "count"),
        }
        if "psf" in tx.columns:
            agg_dict["median_psf"] = ("psf", "median")
        if "rental_yield_pct" in tx.columns:
            agg_dict["median_rental_yield_pct"] = ("rental_yield_pct", "median")

        market = tx.groupby("planning_area").agg(**agg_dict).reset_index()
        result = result.merge(market, on="planning_area", how="left")

    result = merge_median_income(result, raw_income_by_planning_area)

    for key in ("cpi", "bank_rates", "unemployment", "gdp"):
        macro_df = raw_macro_data.get(key, pd.DataFrame())
        if macro_df.empty:
            continue
        value_col = {
            "cpi": "cpi",
            "bank_rates": "sora_3m",
            "unemployment": "unemployment_rate",
            "gdp": "gdp",
        }.get(key)
        date_col = "date" if "date" in macro_df.columns else "quarter"
        if value_col not in macro_df.columns or date_col not in macro_df.columns:
            continue
        # A trailing null value must not broadcast NaN for the whole column.
        macro_values = macro_df.dropna(subset=[value_col])
        if macro_values.empty:
            continue
        latest_value = macro_values.sort_values(date_col)[value_col].iloc[-1]
        result[value_col] = latest_value

    validated = validate_and_quarantine(result, PlanningArea360, "planning_area_360")
    logger.info("planning_area_360: %s planning areas", len(validated["valid"]))
    return extracted_validation(validated, "planning_area_360", "planning_area_360_quarantine")


@extract_fields({"town_360": pd.DataFrame, "town_360_quarantine": pd.DataFrame})
def validate_town_360(
    transactions_enriched: pd.DataFrame,
    raw_dwelling_units_by_town: pd.DataFrame,
    raw_hdb_resident_population: pd.DataFrame,
    raw_median_annual_value: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build the town 360-degree profile table (~27 rows).

    Aggregates market stats from transactions_enriched, merges supply,
    population, and tax from external sources.
    """
    if transactions_enriched.empty or "town" not in transactions_enriched.columns:
        return empty_extracted(transactions_enriched, "town_360", "town_360_quarantine")

    tx = transactions_enriched.copy()
    tx["_town_upper"] = tx["town"].astype(str).str.strip().str.upper()

    agg_dict: dict[str, tuple] = {
        "median_price": ("price", "median"),
        "transaction_volume": ("price", "count"),
    }
    if "psf" in tx.columns:
        agg_dict["median_psf"] = ("psf", "median")

    result = (
        tx.groupby("_town_upper")
        .agg(**agg_dict)
        .reset_index()
        .rename(columns={"_town_upper": "town"})
    )

    result = merge_town_context(
        result,
        raw_dwelling_units_by_town=raw_dwelling_units_by_town,
        raw_hdb_resident_population=raw_hdb_resident_population,
    )

    # Per-flat-type annual-value broadcast is town_360-specific; the shared
    # merge_town_context covers only the dwelling/population core.
    mav_lookup = annual_value_lookup(raw_median_annual_value)
    if not mav_lookup.empty:
        for ft in ("3 Room", "4 Room", "5 Room"):
            row = mav_lookup[mav_lookup["type_of_hdb"] == ft]
            if not row.empty:
                suffix = ft.lower().replace(" ", "_")
                result[f"annual_value_{suffix}"] = row.iloc[0]["annual_value"]
                result[f"property_tax_{suffix}"] = row.iloc[0]["property_tax"]

    for col in (
        "dwelling_units_in_town",
        "population_in_town",
        "population_per_dwelling",
        "annual_value_3_room",
        "annual_value_4_room",
        "annual_value_5_room",
        "property_tax_3_room",
        "property_tax_4_room",
        "property_tax_5_room",
    ):
        if col not in result.columns:
            result[col] = pd.NA

    result["town"] = result["town"].str.title()

    validated = validate_and_quarantine(result, Town360, "town_360")
    logger.info("town_360: %s towns", len(validated["valid"]))
    return extracted_validation(validated, "town_360", "town_360_quarantine")


@extract_fields({"block_profile": pd.DataFrame, "block_profile_quarantine": pd.DataFrame})
def validate_block_profile(
    transactions_enriched: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build per-block transaction profile table (~10K rows).

    Aggregates median price/PSF, transaction count, and average remaining
    lease years by (block, street_name).
    """
    if transactions_enriched.empty:
        return empty_extracted(transactions_enriched, "block_profile", "block_profile_quarantine")

    df = transactions_enriched.copy()

    if "block" not in df.columns or "street_name" not in df.columns:
        logger.warning("block_profile: missing block/street_name columns")
        return empty_extracted(transactions_enriched, "block_profile", "block_profile_quarantine")

    agg_dict: dict[str, tuple] = {
        "median_price": ("price", "median"),
        "transaction_count": ("price", "count"),
    }
    if "psf" in df.columns:
        agg_dict["median_psf"] = ("psf", "median")
    if "remaining_lease_years" in df.columns:
        agg_dict["avg_remaining_lease_years"] = ("remaining_lease_years", "mean")
    if "town" in df.columns:
        agg_dict["town"] = ("town", "first")

    profile = df.groupby(["block", "street_name"]).agg(**agg_dict).reset_index()

    validated = validate_and_quarantine(profile, BlockProfile, "block_profile")
    logger.info("block_profile: %s blocks", len(validated["valid"]))
    return extracted_validation(validated, "block_profile", "block_profile_quarantine")
