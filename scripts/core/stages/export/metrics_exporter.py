"""Feature enrichment functions for the L3 export pipeline."""

import logging

import geopandas as gpd
import pandas as pd

from scripts.core.stages.export.base_exporter import DISTRICT_TO_URA_LOCALITY

logger = logging.getLogger(__name__)


def merge_with_geocoding(transactions_df: pd.DataFrame, geo_df: pd.DataFrame) -> pd.DataFrame:
    """Merge transaction data with geocoded properties.

    Args:
        transactions_df: Combined HDB + Condo transactions
        geo_df: Geocoded properties with coordinates

    Returns:
        Transactions with lat/lon columns added
    """
    logger.info("Merging transactions with geocoding data...")

    if geo_df.empty:
        logger.warning("No geocoding data available, skipping merge")
        return transactions_df

    # Separate HDB, Condo, and EC for different merge strategies
    hdb_mask = transactions_df["property_type"] == "HDB"
    private_mask = transactions_df["property_type"].isin(["Condominium", "EC"])

    merged_dfs = []

    def _dedupe_geocoding(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
        """Keep the best geocoding row per key (prefer existing, then higher score)."""
        if df.empty:
            return df
        ranked = df.copy()
        if "match_type" in ranked.columns:
            ranked["_geo_match_rank"] = (ranked["match_type"].astype(str) == "existing").astype(int)
        else:
            ranked["_geo_match_rank"] = 0
        if "match_score" in ranked.columns:
            ranked["_geo_score_rank"] = pd.to_numeric(
                ranked["match_score"], errors="coerce"
            ).fillna(-1)
        else:
            ranked["_geo_score_rank"] = -1
        ranked = ranked.sort_values(
            key_cols + ["_geo_match_rank", "_geo_score_rank"],
            ascending=[True] * len(key_cols) + [False, False],
        )
        ranked = ranked.drop_duplicates(subset=key_cols, keep="first")
        return ranked.drop(columns=["_geo_match_rank", "_geo_score_rank"])

    # Merge HDB transactions
    if hdb_mask.any():
        hdb_df = transactions_df[hdb_mask].copy()

        # Prepare geo data for HDB (filter to HDB properties if property_type exists)
        if "property_type" in geo_df.columns:
            geo_hdb = geo_df[geo_df["property_type"] == "hdb"].copy()
        else:
            geo_hdb = geo_df.copy()

        if not geo_hdb.empty:
            geo_hdb = _dedupe_geocoding(geo_hdb, ["BLK_NO", "ROAD_NAME"])
            hdb_merged = pd.merge(
                hdb_df,
                geo_hdb[["BLK_NO", "ROAD_NAME", "POSTAL", "LATITUDE", "LONGITUDE"]],
                left_on=["block", "street_name"],
                right_on=["BLK_NO", "ROAD_NAME"],
                how="left",
            )
            hdb_merged["lat"] = hdb_merged["LATITUDE"]
            hdb_merged["lon"] = hdb_merged["LONGITUDE"]
            hdb_merged.drop(["BLK_NO", "ROAD_NAME", "LATITUDE", "LONGITUDE"], axis=1, inplace=True)
        else:
            hdb_merged = hdb_df
            hdb_merged["lat"] = None
            hdb_merged["lon"] = None

        merged_dfs.append(hdb_merged)

    # Merge Condo and EC transactions (both use private housing geocoding)
    if private_mask.any():
        private_df = transactions_df[private_mask].copy()

        # Prepare geo data for Condo (filter to private housing if property_type exists)
        if "property_type" in geo_df.columns:
            geo_condo = geo_df[geo_df["property_type"] == "private"].copy()
        else:
            geo_condo = geo_df.copy()

        if not geo_condo.empty:
            # Keep best candidate per street before street-level merge.
            geo_condo_unique = _dedupe_geocoding(geo_condo, ["ROAD_NAME"]).copy()
            geo_condo_unique["street_name_upper"] = geo_condo_unique["ROAD_NAME"].str.upper()

            private_df = private_df.copy()
            private_df["street_name_upper"] = private_df["Street Name"].str.upper()

            private_merged = pd.merge(
                private_df,
                geo_condo_unique[["street_name_upper", "LATITUDE", "LONGITUDE"]],
                on="street_name_upper",
                how="left",
            )
            private_merged["lat"] = private_merged["LATITUDE"]
            private_merged["lon"] = private_merged["LONGITUDE"]
            private_merged.drop(
                ["street_name_upper", "LATITUDE", "LONGITUDE"], axis=1, inplace=True
            )
        else:
            private_merged = private_df
            private_merged["lat"] = None
            private_merged["lon"] = None

        merged_dfs.append(private_merged)

    # Combine back
    result = pd.concat(merged_dfs, ignore_index=True)

    # Report geocoding success
    geo_count = result["lat"].notna().sum()
    total_count = len(result)
    logger.info(
        f"Geocoded {geo_count:,} of {total_count:,} properties ({geo_count / total_count * 100:.1f}%)"
    )

    return result


def add_planning_area(
    transactions_df: pd.DataFrame, planning_areas_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """Add planning area and region by spatial join with coordinates.

    Args:
        transactions_df: Transactions with lat/lon
        planning_areas_gdf: Planning area polygons (may include region)

    Returns:
        Transactions with planning_area and region columns added
    """
    logger.info("Adding planning areas and regions...")

    if planning_areas_gdf.empty:
        logger.warning("No planning area data available, skipping")
        transactions_df["planning_area"] = None
        transactions_df["region"] = None
        return transactions_df

    # Determine which columns to join
    join_cols = ["pln_area_n", "geometry"]
    if "region" in planning_areas_gdf.columns:
        join_cols.append("region")
        logger.info("Region data available in planning area file")

    # Create GeoDataFrame from transactions
    gdf = gpd.GeoDataFrame(
        transactions_df,
        geometry=gpd.points_from_xy(
            transactions_df["lon"].astype(float), transactions_df["lat"].astype(float)
        ),
        crs="EPSG:4326",
    )

    # Spatial join with planning areas
    result = gpd.sjoin(gdf, planning_areas_gdf[join_cols], how="left", predicate="within")

    # Extract planning area name
    transactions_df["planning_area"] = result["pln_area_n"]

    # Extract region if available
    if "region" in result.columns:
        transactions_df["region"] = result["region"]
    else:
        transactions_df["region"] = None

    # Report coverage
    pa_coverage = transactions_df["planning_area"].notna().sum()
    total = len(transactions_df)
    logger.info(
        f"Added planning area to {pa_coverage:,} of {total:,} properties ({pa_coverage / total * 100:.1f}%)"
    )

    if "region" in transactions_df.columns:
        reg_coverage = transactions_df["region"].notna().sum()
        logger.info(
            f"Added region to {reg_coverage:,} of {total:,} properties ({reg_coverage / total * 100:.1f}%)"
        )

    return transactions_df


def add_amenity_features(transactions_df: pd.DataFrame, amenity_df: pd.DataFrame) -> pd.DataFrame:
    """Merge amenity distance and count features.

    Supports both new schema (dist_nearest_*, count_*_m) and
    legacy schema (*_within_500m, *_within_1km, *_within_2km).

    Args:
        transactions_df: Transactions with geocoding
        amenity_df: Amenity features from L2

    Returns:
        Transactions with amenity columns added
    """
    logger.info("Adding amenity features...")

    if amenity_df.empty:
        logger.warning("No amenity features available, skipping")
        return transactions_df

    # Try to merge on postal code if available
    if "POSTAL" in transactions_df.columns and "POSTAL" in amenity_df.columns:
        # Select ALL amenity columns to merge (distances AND counts)
        # Supports new schema: dist_nearest_*, count_*_*m
        # Supports legacy schema: *_within_500m, *_within_1km, *_within_2km
        amenity_cols = [
            col
            for col in amenity_df.columns
            if col.startswith("dist_")
            or col.startswith("count_")
            or col.endswith("_within_500m")
            or col.endswith("_within_1km")
            or col.endswith("_within_2km")
        ]

        merge_cols = ["POSTAL"] + amenity_cols
        amenity_merge_df = amenity_df[merge_cols].copy()

        # L2 per-type amenity exports can contain repeated postal rows; collapse to one row per postal
        # before joining to transactions to avoid one-to-many row inflation in L3.
        dup_mask = amenity_merge_df.duplicated(subset=["POSTAL"], keep=False)
        if dup_mask.any():
            dup_rows = int(dup_mask.sum())
            dup_postals = int(amenity_merge_df.loc[dup_mask, ["POSTAL"]].drop_duplicates().shape[0])
            logger.warning(
                "Amenity features contain duplicate POSTAL rows; collapsing %s rows across %s postals",
                dup_rows,
                dup_postals,
            )
            agg_spec = {col: "median" for col in amenity_cols}
            amenity_merge_df = (
                amenity_merge_df.groupby("POSTAL", as_index=False)
                .agg(agg_spec)
                .sort_values("POSTAL", kind="stable")
            )

        result = pd.merge(transactions_df, amenity_merge_df, on="POSTAL", how="left")

        if len(result) != len(transactions_df):
            logger.error(
                "Amenity merge changed row count unexpectedly: %s -> %s",
                len(transactions_df),
                len(result),
            )

        # Log what was added
        added_cols = [col for col in amenity_cols if col in result.columns]
        logger.info(f"  Merged {len(added_cols)} amenity columns on postal code")

        # Log amenity column types
        dist_cols = [c for c in added_cols if c.startswith("dist_")]
        count_cols = [c for c in added_cols if c.startswith("count_")]
        within_cols = [c for c in added_cols if "_within_" in c]

        if dist_cols:
            logger.info(f"    Distance columns: {len(dist_cols)} (e.g., {dist_cols[0]})")
        if count_cols:
            logger.info(f"    Count columns: {len(count_cols)} (e.g., {count_cols[0]})")
        if within_cols:
            logger.info(f"    Within-radius columns: {len(within_cols)} (legacy schema)")
    elif "address" in transactions_df.columns and "address" in amenity_df.columns:
        result = pd.merge(transactions_df, amenity_df, on="address", how="left")
        logger.info("Merged amenity features on address")
    else:
        logger.warning("Cannot merge amenity features - no common key")
        result = transactions_df

    return result


def merge_rental_yield(
    transactions_df: pd.DataFrame, rental_yield_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge rental yield data by town and month.

    Args:
        transactions_df: Transactions with town and month
        rental_yield_df: Rental yield by town and month

    Returns:
        Transactions with rental_yield_pct column added
    """
    logger.info("Merging rental yield data...")

    if rental_yield_df.empty:
        logger.warning("No rental yield data available, skipping")
        return transactions_df

    # Make copies to avoid modifying originals
    transactions_df = transactions_df.copy()
    rental_yield_df = rental_yield_df.copy()
    transactions_df["_merge_row_id"] = range(len(transactions_df))

    def _collapse_duplicate_yield_keys(
        df: pd.DataFrame, key_cols: list[str], label: str
    ) -> pd.DataFrame:
        if df.empty:
            return df
        dup_mask = df.duplicated(subset=key_cols, keep=False)
        dup_rows = int(dup_mask.sum())
        dup_keys = int(df.loc[dup_mask, key_cols].drop_duplicates().shape[0]) if dup_rows else 0
        if not dup_rows:
            return df
        logger.warning(
            "Duplicate rental yield rows detected for %s keys; collapsing %s rows across %s keys",
            label,
            dup_rows,
            dup_keys,
        )
        collapsed = (
            df.groupby(key_cols, as_index=False)["rental_yield_pct"]
            .median()
            .sort_values(key_cols, kind="stable")
        )
        return collapsed

    # Ensure month columns are both datetime
    if transactions_df["month"].dtype == "object":
        transactions_df["month"] = pd.to_datetime(
            transactions_df["month"], format="%Y-%m", errors="coerce"
        )

    # Backward compatibility for older rental_yield outputs (HDB-only / no property_type).
    if "property_type" not in rental_yield_df.columns:
        logger.warning("rental_yield.parquet missing property_type; using legacy town+month merge")
        if rental_yield_df["month"].dtype == "object":
            rental_yield_df["month"] = pd.to_datetime(
                rental_yield_df["month"], format="%Y-%m", errors="coerce"
            )
        else:
            rental_yield_df["month"] = pd.to_datetime(rental_yield_df["month"], errors="coerce")
        rental_yield_df["month"] = rental_yield_df["month"].dt.normalize()
        rental_yield_df = _collapse_duplicate_yield_keys(
            rental_yield_df, ["town", "month"], "legacy town+month"
        )

        result = pd.merge(
            transactions_df,
            rental_yield_df[["town", "month", "rental_yield_pct"]],
            on=["town", "month"],
            how="left",
        )
        result = result.drop(columns=["_merge_row_id"])
        coverage = result["rental_yield_pct"].notna().sum()
        total = len(result)
        logger.info(
            f"Added rental yield to {coverage:,} of {total:,} records ({coverage / total * 100:.1f}%)"
        )
        return result

    if rental_yield_df["month"].dtype == "object":
        month_str = rental_yield_df["month"].astype(str).str.strip()
        rental_yield_df["month"] = pd.to_datetime(month_str, format="%Y-%m", errors="coerce")
        quarter_mask = rental_yield_df["month"].isna() & month_str.str.match(r"^\d{4}Q[1-4]$")
        if quarter_mask.any():
            rental_yield_df.loc[quarter_mask, "month"] = pd.PeriodIndex(
                month_str[quarter_mask], freq="Q"
            ).to_timestamp(how="start")
    else:
        rental_yield_df["month"] = pd.to_datetime(rental_yield_df["month"], errors="coerce")

    rental_yield_df["month"] = rental_yield_df["month"].dt.normalize()

    if "property_type" in transactions_df.columns:
        tx_type = transactions_df["property_type"].astype(str)
        transactions_df["_ry_property_type"] = tx_type.replace({"Condominium": "Condo"})
    else:
        transactions_df["_ry_property_type"] = None

    rental_yield_df["_ry_property_type"] = rental_yield_df["property_type"].astype(str)

    # HDB: exact month + town join, keyed by property_type for safety.
    hdb_tx = transactions_df[transactions_df["_ry_property_type"] == "HDB"].copy()
    private_tx = transactions_df[transactions_df["_ry_property_type"].isin(["Condo", "EC"])].copy()
    other_tx = transactions_df[
        ~transactions_df["_ry_property_type"].isin(["HDB", "Condo", "EC"])
    ].copy()

    hdb_ry = rental_yield_df[rental_yield_df["_ry_property_type"] == "HDB"].copy()
    private_ry = rental_yield_df[rental_yield_df["_ry_property_type"].isin(["Condo", "EC"])].copy()

    hdb_ry = _collapse_duplicate_yield_keys(hdb_ry, ["_ry_property_type", "town", "month"], "HDB")
    private_ry = _collapse_duplicate_yield_keys(
        private_ry, ["_ry_property_type", "town", "month"], "private"
    )

    hdb_result = pd.merge(
        hdb_tx,
        hdb_ry[["town", "month", "_ry_property_type", "rental_yield_pct"]],
        on=["town", "month", "_ry_property_type"],
        how="left",
    )

    if not private_tx.empty:
        postal = (
            private_tx["Postal District"]
            if "Postal District" in private_tx.columns
            else pd.Series(index=private_tx.index)
        )
        private_tx["_postal_district_key"] = (
            pd.to_numeric(postal, errors="coerce").astype("Int64").astype(str)
        )
        private_tx["_ura_locality"] = private_tx["_postal_district_key"].map(
            DISTRICT_TO_URA_LOCALITY
        )
        private_tx["_quarter_start_month"] = (
            private_tx["month"].dt.to_period("Q").dt.to_timestamp(how="start").dt.normalize()
        )

        private_result = pd.merge(
            private_tx,
            private_ry.rename(columns={"town": "_ura_locality"})[
                ["_ura_locality", "month", "_ry_property_type", "rental_yield_pct"]
            ].rename(columns={"month": "_quarter_start_month"}),
            on=["_ura_locality", "_quarter_start_month", "_ry_property_type"],
            how="left",
        )
    else:
        private_result = private_tx
        private_result["rental_yield_pct"] = pd.Series(dtype="float64")

    if not other_tx.empty and "rental_yield_pct" not in other_tx.columns:
        other_tx["rental_yield_pct"] = pd.NA

    result = pd.concat([hdb_result, private_result, other_tx], ignore_index=True, sort=False)
    result = result.sort_values("_merge_row_id").reset_index(drop=True)

    if len(result) != len(transactions_df):
        logger.error(
            "Rental yield merge changed row count unexpectedly: %s -> %s",
            len(transactions_df),
            len(result),
        )

    drop_cols = [
        "_merge_row_id",
        "_ry_property_type",
        "_postal_district_key",
        "_ura_locality",
        "_quarter_start_month",
    ]
    result = result.drop(columns=[c for c in drop_cols if c in result.columns])

    # Report coverage
    coverage = result["rental_yield_pct"].notna().sum()
    total = len(result)
    logger.info(
        f"Added rental yield to {coverage:,} of {total:,} records ({coverage / total * 100:.1f}%)"
    )

    return result


def merge_precomputed_metrics(
    transactions_df: pd.DataFrame, metrics_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge precomputed monthly metrics.

    Args:
        transactions_df: Transactions with month and geographic info
        metrics_df: Precomputed metrics by month and area

    Returns:
        Transactions with metric columns added
    """
    logger.info("Merging precomputed metrics...")

    if metrics_df.empty:
        logger.warning("No precomputed metrics available, skipping")
        return transactions_df

    # Make copies to avoid modifying originals
    transactions_df = transactions_df.copy()
    metrics_df = metrics_df.copy()

    # Ensure month columns are both datetime
    if transactions_df["month"].dtype == "object":
        transactions_df["month"] = pd.to_datetime(
            transactions_df["month"], format="%Y-%m", errors="coerce"
        )

    # Handle different types for metrics_df month (Period, datetime, or string)
    if str(metrics_df["month"].dtype) == "period[M]":
        # PeriodDtype - convert to timestamp
        metrics_df["month"] = metrics_df["month"].dt.to_timestamp()
    elif metrics_df["month"].dtype == "object":
        metrics_df["month"] = pd.to_datetime(metrics_df["month"], format="%Y-%m", errors="coerce")
    else:
        # Already datetime or convertible
        metrics_df["month"] = pd.to_datetime(metrics_df["month"])

    # Determine join key (prefer planning_area, fall back to town)
    if "planning_area" in transactions_df.columns and "planning_area" in metrics_df.columns:
        join_key = "planning_area"
    elif "town" in transactions_df.columns and "town" in metrics_df.columns:
        join_key = "town"
    else:
        logger.warning("No common geographic key for merging metrics")
        return transactions_df

    # Select key metric columns to merge (include month and join_key)
    metric_cols = [
        "month",
        join_key,  # Include the join key column
        "stratified_median_price",
        "mom_change_pct",
        "yoy_change_pct",
        "momentum_signal",
        "transaction_count",
        "volume_3m_avg",
        "volume_12m_avg",
    ]

    # Only select columns that exist
    available_cols = [col for col in metric_cols if col in metrics_df.columns]

    if len(available_cols) <= 2:  # Only 'month' and join_key exist
        logger.warning("No metric columns available for merge")
        return transactions_df

    metrics_to_merge = metrics_df[available_cols].copy()

    # Merge
    result = pd.merge(transactions_df, metrics_to_merge, on=["month", join_key], how="left")

    # Log what was added (exclude month and join_key from count)
    added_cols = [col for col in available_cols if col not in ["month", join_key]]
    logger.info(f"Merged {len(added_cols)} metric columns on {join_key}+month")

    return result


def filter_final_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order final columns for L3 dataset.

    Args:
        df: Full merged DataFrame

    Returns:
        DataFrame with selected columns
    """
    logger.info("Selecting final columns...")

    # Core columns that must be present (order matters)
    core_columns = [
        "property_type",  # CRITICAL: Must always be included
        "transaction_date",
        "town",
        "planning_area",  # NEW
        "region",  # NEW - Central/West/North/North-East/East
        "address",
        "price",
        "floor_area_sqm",
        "floor_area_sqft",
        "price_psm",
        "price_psf",
        "lat",
        "lon",
    ]

    # Ensure all core columns exist (even if null)
    for col in core_columns:
        if col not in df.columns:
            logger.warning(f"Core column '{col}' not found in dataset, adding as None")
            df[col] = None

    # Optional columns to include if present
    optional_columns = [
        "month",  # Original date column
        "flat_type",  # HDB only
        "flat_model",  # HDB only
        "storey_range",  # HDB only
        "lease_commence_date",  # HDB only
        "remaining_lease_months",  # HDB only
        "Project Name",  # Condo only
        "Street Name",  # Condo only
        "Postal District",  # Condo only
        "Property Type",  # Condo only
        "Market Segment",  # Condo only
        # Amenity distance features
        "dist_to_nearest_supermarket",
        "dist_to_nearest_preschool",
        "dist_to_nearest_park",
        "dist_to_nearest_hawker",
        "dist_to_nearest_mrt",
        "dist_to_nearest_childcare",
        # Amenity count features (within radius)
        "supermarket_within_500m",
        "supermarket_within_1km",
        "supermarket_within_2km",
        "preschool_within_500m",
        "preschool_within_1km",
        "preschool_within_2km",
        "park_within_500m",
        "park_within_1km",
        "park_within_2km",
        "hawker_within_500m",
        "hawker_within_1km",
        "hawker_within_2km",
        "mrt_station_within_500m",
        "mrt_station_within_1km",
        "mrt_station_within_2km",
        "mrt_exit_within_500m",
        "mrt_exit_within_1km",
        "mrt_exit_within_2km",
        "childcare_within_500m",
        "childcare_within_1km",
        "childcare_within_2km",
        # Mall amenity features
        "mall_within_500m",
        "mall_within_1km",
        "mall_within_2km",
        # Rental yield
        "rental_yield_pct",  # NEW
        # Precomputed metrics
        "stratified_median_price",  # NEW
        "mom_change_pct",  # NEW
        "yoy_change_pct",  # NEW
        "momentum_signal",  # NEW
        "transaction_count",  # NEW
        "volume_3m_avg",  # NEW
        "volume_12m_avg",  # NEW
        # Period-dependent market segmentation (NEW)
        "year",  # NEW - Transaction year (for period calculation)
        "period_5yr",  # NEW - 5-year period bucket
        "market_tier_period",  # NEW - Period-dependent price tier
        "psf_tier_period",  # NEW - Period-dependent PSF tier
        # School features
        "school_within_500m",
        "school_within_1km",
        "school_within_2km",
        "school_accessibility_score",
        "school_primary_dist_score",
        "school_primary_quality_score",
        "school_secondary_dist_score",
        "school_secondary_quality_score",
        "school_density_score",
    ]

    # Add any other amenity/metric columns that might exist
    amenity_cols = [
        col for col in df.columns if col.startswith("dist_") or col.startswith("count_")
    ]
    optional_columns.extend(amenity_cols)

    # Build final column list - ALWAYS start with core_columns
    final_columns = core_columns.copy()

    # Add optional columns that exist
    for col in optional_columns:
        if col in df.columns and col not in final_columns:
            final_columns.append(col)

    # Verify core_columns are present
    for col in core_columns:
        if col not in final_columns:
            logger.error(f"Core column '{col}' is missing from final columns!")
            final_columns.insert(0, col)

    result = df[final_columns].copy()

    logger.info(f"Selected {len(final_columns)} columns for final dataset")

    return result


def add_period_segmentation(df: pd.DataFrame) -> pd.DataFrame:
    """Add period-dependent market segmentation to transaction data.

    Creates 5-year period buckets and calculates price tiers within each period.
    This accounts for inflation and market changes over time.

    Args:
        df: Transaction data with price, property_type, and transaction_date

    Returns:
        DataFrame with period_5yr, market_tier_period, and psf_tier_period columns
    """
    logger.info("Adding period-dependent market segmentation...")

    df = df.copy()

    # Create 5-year period buckets
    df["year"] = pd.to_datetime(df["transaction_date"]).dt.year
    df["period_5yr"] = (df["year"] // 5) * 5
    df["period_5yr"] = df["period_5yr"].astype(str) + "-" + (df["period_5yr"] + 4).astype(str)

    # Calculate period-dependent price tiers
    def assign_price_tier(group):
        """Assign price tier based on 30/40/30 percentiles within period."""
        p30 = group["price"].quantile(0.30)
        p70 = group["price"].quantile(0.70)

        tiers = []
        for price in group["price"]:
            if price <= p30:
                tiers.append("Mass Market")
            elif price <= p70:
                tiers.append("Mid-Tier")
            else:
                tiers.append("Luxury")

        return pd.Series(tiers, index=group.index)

    # Apply tier assignment within each property type + period
    df["market_tier_period"] = df.groupby(["property_type", "period_5yr"], group_keys=False).apply(
        lambda g: assign_price_tier(g)
    )

    # Calculate period-dependent PSF tiers (if PSF column exists)
    if "price_psf" in df.columns:

        def assign_psf_tier(group):
            """Assign PSF tier based on 30/40/30 percentiles within period."""
            p30 = group["price_psf"].quantile(0.30)
            p70 = group["price_psf"].quantile(0.70)

            tiers = []
            for psf in group["price_psf"]:
                if psf <= p30:
                    tiers.append("Low PSF")
                elif psf <= p70:
                    tiers.append("Medium PSF")
                else:
                    tiers.append("High PSF")

            return pd.Series(tiers, index=group.index)

        df["psf_tier_period"] = df.groupby(["property_type", "period_5yr"], group_keys=False).apply(
            lambda g: assign_psf_tier(g)
        )
    else:
        logger.warning("price_psf column not found, skipping PSF tier calculation")
        df["psf_tier_period"] = None

    logger.info(f"Added period segmentation: {len(df):,} transactions classified")
    logger.info(f"Periods: {sorted(df['period_5yr'].unique())}")

    return df
