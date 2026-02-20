"""L2: Feature engineering pipeline.

This module provides functions for:
- Loading and processing transaction data (HDB, Condo, EC)
- Generating H3 grid polygons for properties
- Computing amenity distances via spatial join
- Creating property, facilities, and listings tables
- Running complete L2 features pipeline
"""  # noqa: N999

import logging
import random
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet, save_parquet
from scripts.core.stages.helpers import feature_helpers
from scripts.core.stages.helpers.feature_helpers import SQM_TO_SQFT

from .spatial_h3 import generate_polygons

logger = logging.getLogger(__name__)


def load_transaction_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load transaction data from parquet files.

    Returns:
        Tuple of (condo_df, ec_df, hdb_df)
    """
    logger.info("Loading transaction data...")
    condo_df = load_parquet("L1_housing_condo_transaction")
    ec_df = load_parquet("L1_housing_ec_transaction")
    hdb_df = load_parquet("L1_housing_hdb_transaction")

    logger.info(f"  Loaded {len(condo_df):,} condo transactions")
    logger.info(f"  Loaded {len(ec_df):,} EC transactions")
    logger.info(f"  Loaded {len(hdb_df):,} HDB transactions")

    return condo_df, ec_df, hdb_df


def load_property_and_amenity_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load property and amenity data.

    Returns:
        Tuple of (unique_df, amenity_df)
    """
    logger.info("Loading property and amenity data...")
    unique_df = load_parquet("L2_housing_unique_searched")
    amenity_df = load_parquet("L1_amenity")

    logger.info(f"  Loaded {len(unique_df):,} unique properties")
    logger.info(f"  Loaded {len(amenity_df):,} amenities")

    return unique_df, amenity_df


def load_planning_area(data_base_path: Path | None = None) -> gpd.GeoDataFrame | None:
    """Load planning area shapefile.

    Args:
        data_base_path: Base path to data directory (defaults to Config.MANUAL_DIR / 'geojsons')

    Returns:
        GeoDataFrame with planning areas, or None if not found
    """
    if data_base_path is None:
        data_base_path = Config.MANUAL_DIR / "geojsons"

    planning_area_path = data_base_path / "onemap_planning_area_polygon.shp"

    if planning_area_path.exists():
        planning_area_gpd = gpd.read_file(planning_area_path)
        logger.info(f"  Loaded {len(planning_area_gpd)} planning areas")
        return planning_area_gpd
    else:
        logger.warning(f"Planning area data not found at {planning_area_path}")
        return None


def prepare_unique_properties(unique_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare unique property dataframe for processing.

    Args:
        unique_df: Raw unique property DataFrame

    Returns:
        Processed DataFrame with standardized columns
    """
    unique_df = unique_df.loc[unique_df["search_result"] == 0].copy()
    unique_df = unique_df.rename(columns={"LATITUDE": "lat", "LONGITUDE": "lon"})
    unique_df["lat"] = unique_df["lat"].astype(float)
    unique_df["lon"] = unique_df["lon"].astype(float)
    return unique_df


def create_property_geodataframe(
    unique_df: pd.DataFrame, resolution: int = 8, k: int = 3
) -> gpd.GeoDataFrame:
    """Create GeoDataFrame from unique properties with H3 polygons.

    Args:
        unique_df: DataFrame with lat/lon columns
        resolution: H3 resolution level
        k: Grid disk radius

    Returns:
        GeoDataFrame with polygon geometries
    """
    logger.info("Creating property polygons...")
    polygon_list = generate_polygons(unique_df, resolution=resolution, k=k)

    unique_gdf = gpd.GeoDataFrame(unique_df, geometry=polygon_list)
    unique_gdf = unique_gdf.drop("search_result", axis=1, errors="ignore")
    unique_gdf = unique_gdf.set_crs("EPSG:4326")

    logger.info(f"  Created {len(unique_gdf)} property polygons")
    return unique_gdf


def create_amenity_geodataframe(amenity_df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Create GeoDataFrame from amenities with point geometries.

    Args:
        amenity_df: DataFrame with lat/lon columns

    Returns:
        GeoDataFrame with point geometries
    """
    amenity_gdf = gpd.GeoDataFrame(
        amenity_df, geometry=gpd.points_from_xy(amenity_df.lon, amenity_df.lat), crs="EPSG:4326"
    )
    return amenity_gdf


def compute_amenity_distances(
    unique_gdf: gpd.GeoDataFrame, amenity_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """Compute distances from properties to nearby amenities via spatial join.

    Args:
        unique_gdf: GeoDataFrame with property polygons
        amenity_gdf: GeoDataFrame with amenity points

    Returns:
        DataFrame with property-amenity pairs and distances
    """
    logger.info("Computing amenity distances via spatial join...")

    unique_gdf_proj = unique_gdf.to_crs(crs=3857)
    amenity_gdf_proj = amenity_gdf.to_crs(crs=3857).copy()
    amenity_gdf_proj["amenity_centroid"] = amenity_gdf_proj.geometry

    unique_joined = (
        unique_gdf_proj[["SEARCHVAL", "POSTAL", "geometry"]]
        .drop_duplicates()
        .sjoin(amenity_gdf_proj[["type", "name", "geometry", "amenity_centroid"]].drop_duplicates())
        .drop("index_right", axis=1)
    )

    unique_joined = unique_joined.to_crs(crs="EPSG:4326")
    amenity_gdf_proj = amenity_gdf_proj.to_crs(crs="EPSG:4326")

    unique_joined["polygon_centroid"] = unique_joined["geometry"].centroid
    unique_joined["distance"] = unique_joined["polygon_centroid"].distance(
        unique_joined["amenity_centroid"]
    )

    unique_joined["SEARCHVAL"] = unique_joined["SEARCHVAL"].str.lower()
    unique_joined.columns = unique_joined.columns.str.lower()

    logger.info(f"  Computed distances for {len(unique_joined):,} property-amenity pairs")
    return unique_joined


def compute_amenity_distances_by_type(
    unique_gdf: gpd.GeoDataFrame,
    amenity_gdf: gpd.GeoDataFrame,
    distance_thresholds: list[int] | None = None,
) -> pd.DataFrame:
    """Compute per-type amenity distances and counts for each property.

    Calculates distance to nearest amenity and count of amenities within
    specified radius for each amenity type (hawker, supermarket, mrt_station,
    mrt_exit, childcare, park, mall).

    Args:
        unique_gdf: GeoDataFrame with property polygons
        amenity_gdf: GeoDataFrame with amenity points (has 'type' column)
        distance_thresholds: List of radius sizes in meters for counting amenities
            (default: [500, 1000])

    Returns:
        DataFrame with property indices and per-type amenity metrics.
        Columns: property_id, POSTAL, dist_nearest_{type}, count_{type}_{radius}m
    """
    if distance_thresholds is None:
        distance_thresholds = [500, 1000]

    logger.info(
        f"Computing per-type amenity distances for {len(distance_thresholds)} "
        f"radius thresholds: {distance_thresholds}m"
    )

    # Get unique amenity types
    amenity_types = sorted(amenity_gdf["type"].unique())
    logger.info(f"  Found {len(amenity_types)} amenity types: {amenity_types}")

    # Project to metric CRS for accurate distance calculations
    unique_gdf_proj = unique_gdf.to_crs(crs=3857)
    amenity_gdf_proj = amenity_gdf.to_crs(crs=3857).copy()

    results = []

    for idx, property_row in unique_gdf_proj.iterrows():
        # Get property identifier
        property_id = (
            property_row.get("project_id")
            or property_row.get("property_index")
            or property_row.get("SEARCHVAL")
            or idx
        )

        # Get postal code for merging (from original CRS projection)
        postal_code = property_row.get("POSTAL") or property_row.get("postal") or None

        row_result = {"property_id": property_id, "POSTAL": postal_code}
        property_geom = property_row.geometry

        # Process each amenity type
        for amenity_type in amenity_types:
            # Filter amenities by type
            type_amenities = amenity_gdf_proj[amenity_gdf_proj["type"] == amenity_type]

            if len(type_amenities) == 0:
                # Add default values if no amenities of this type
                row_result[f"dist_nearest_{amenity_type}"] = None
                for dist_threshold in distance_thresholds:
                    row_result[f"count_{amenity_type}_{dist_threshold}m"] = 0
                continue

            # Calculate distances to all amenities of this type (in meters)
            distances = property_geom.distance(type_amenities.geometry)

            # Nearest distance
            nearest_dist = distances.min()
            row_result[f"dist_nearest_{amenity_type}"] = round(nearest_dist, 2)

            # Count within each radius
            for dist_threshold in distance_thresholds:
                count = (distances <= dist_threshold).sum()
                row_result[f"count_{amenity_type}_{dist_threshold}m"] = count

        results.append(row_result)

    df = pd.DataFrame(results)

    # Log summary statistics
    logger.info(f"✅ Computed amenity metrics for {len(df)} properties")
    logger.info(f"  Columns: {len(df.columns)}")

    # Log non-null ratios for distance columns
    dist_cols = [c for c in df.columns if c.startswith("dist_nearest_")]
    if dist_cols:
        logger.info("  Distance column coverage:")
        for col in dist_cols:
            non_null_ratio = df[col].notna().sum() / len(df) * 100
            logger.info(f"    {col}: {non_null_ratio:.1f}%")

    return df


def compute_planning_area(
    unique_gdf: gpd.GeoDataFrame, planning_area_gpd: gpd.GeoDataFrame | None
) -> gpd.GeoDataFrame:
    """Assign planning area to each property via spatial join.

    Args:
        unique_gdf: GeoDataFrame with property centroids
        planning_area_gpd: GeoDataFrame with planning area polygons

    Returns:
        GeoDataFrame with planning_area column added
    """
    if planning_area_gpd is None:
        logger.warning("Planning area data not available, skipping")
        return unique_gdf

    logger.info("Computing planning area assignments...")

    planning_area_gpd = planning_area_gpd.set_crs(crs="EPSG:4326")
    planning_area_gpd = planning_area_gpd.rename({"pln_area_n": "planning_area"}, axis=1)

    unique_gdf_proj = unique_gdf.to_crs(crs=3857)
    unique_gdf_proj["geometry"] = unique_gdf_proj["geometry"].centroid
    unique_gdf_proj = unique_gdf_proj.to_crs(crs="EPSG:4326")

    unique_gdf_with_area = unique_gdf_proj.sjoin(
        planning_area_gpd, how="left", predicate="within"
    ).drop("index_right", axis=1)

    logger.info(f"  Assigned planning areas to {len(unique_gdf_with_area):,} properties")
    return unique_gdf_with_area


def extract_lease_info(lease_info: str) -> tuple[int | None, str]:
    """Extract lease information from tenure string.

    Delegates to feature_helpers.extract_lease_info for consistency.

    Args:
        lease_info: Tenure string like "99 yrs lease commencing from 2007" or "Freehold"

    Returns:
        Tuple of (commencing_year or None, hold_type)
    """
    return feature_helpers.extract_lease_info(lease_info)


def extract_two_digits(string: str) -> tuple[str, str]:
    """Extract first two digits from floor range string.

    Delegates to feature_helpers.extract_floor_range for consistency.

    Args:
        string: String like "01 to 05"

    Returns:
        Tuple of (low, high)
    """
    return feature_helpers.extract_floor_range(string)


def process_private_transactions(condo_df: pd.DataFrame, ec_df: pd.DataFrame) -> pd.DataFrame:
    """Process private property (Condo + EC) transactions.

    Args:
        condo_df: Condo transaction DataFrame
        ec_df: EC transaction DataFrame

    Returns:
        Processed private transaction DataFrame
    """
    logger.info("Processing private property transactions...")

    private_df = pd.concat([condo_df, ec_df])

    # Standardize column names using helper
    private_df = feature_helpers.standardize_column_names(private_df)

    private_df = private_df.drop(
        ["nettprice", "numberofunits", "typeofarea", "typeofsale"], axis=1, errors="ignore"
    )

    # Process tenure using vectorized operations
    private_df = feature_helpers.process_private_property_tenure(private_df)

    private_df["saledate"] = pd.to_datetime(private_df["saledate"], format="%b-%y").dt.date

    numerical_cast_dict = {
        "transactedprice": int,
        "unitprice_psf": int,
        "unitprice_psm": int,
        "area_sqft": float,
    }

    for key, val in numerical_cast_dict.items():
        if key in private_df.columns:
            private_df[key] = private_df[key].astype(str).str.replace(",", "").astype(val)

    private_df["propertytype"] = private_df["propertytype"].replace("Apartment", "Condominium")
    private_df["property_type"] = "Private"

    for col in ["marketsegment", "propertytype", "hold_type"]:
        if col in private_df.columns:
            private_df[col] = private_df[col].astype("category")

    if "floorlevel" in private_df.columns:
        private_df["floorlevel"] = private_df["floorlevel"].replace("-", "Unknown")
        private_df = private_df.loc[private_df["floorlevel"] != "Unknown"]
        private_df["floorlevel"] = private_df["floorlevel"].astype("category")

    rename_map = {
        "projectname": "project_name",
        "saledate": "transaction_date",
        "lease_start_yr": "lease_commence_date",
        "floorlevel": "floor_level",
        "streetname": "street_name",
        "propertytype": "property_sub_type",
        "transactedprice": "resale_price",
    }
    private_df = private_df.rename(columns=rename_map)

    if "project_name" in private_df.columns and "street_name" in private_df.columns:
        private_df["property_index"] = (
            private_df["project_name"].fillna("") + " " + private_df["street_name"].fillna("")
        )
        private_df["property_index"] = private_df["property_index"].str.strip().str.upper()

    for col in ["project_name", "street_name", "property_index"]:
        if col in private_df.columns:
            private_df[col] = private_df[col].astype("string")

    if "area_sqft" in private_df.columns:
        private_df["area_sqft"] = pd.to_numeric(private_df["area_sqft"], errors="coerce")
        if "area_sqm" in private_df.columns:
            private_df["area_sqm"] = private_df.apply(
                lambda row: row["area_sqft"] / 10.7639
                if pd.isna(row["area_sqm"])
                else row["area_sqm"],
                axis=1,
            )

    if "lease_commence_date" in private_df.columns:
        private_df["lease_commence_date"] = private_df["lease_commence_date"].astype("Int64")

    if "floor_level" in private_df.columns:
        private_df[["floor_low", "floor_high"]] = [
            extract_two_digits(i) for i in private_df["floor_level"]
        ]

    if "property_sub_type" in private_df.columns:
        private_df["property_sub_type"] = private_df["property_sub_type"].str.lower()

    drop_cols = ["tenure", "marketsegment", "postaldistrict", "unitprice_psm"]
    private_df = private_df.drop(columns=drop_cols, errors="ignore")

    logger.info(f"  Processed {len(private_df):,} private property transactions")
    return private_df


def process_hdb_transactions(hdb_df: pd.DataFrame) -> pd.DataFrame:
    """Process HDB transaction data.

    Args:
        hdb_df: HDB transaction DataFrame

    Returns:
        Processed HDB transaction DataFrame
    """
    logger.info("Processing HDB transactions...")

    hdb_df["property_index"] = hdb_df["block"].fillna("") + " " + hdb_df["street_name"].fillna("")
    hdb_df["property_index"] = hdb_df["property_index"].str.strip().str.upper()

    hdb_df = hdb_df.rename(
        columns={
            "month": "transaction_date",
            "floor_area_sqm": "area_sqm",
            "storey_range": "floor_level",
            "flat_type": "property_sub_type",
            "block": "project_name",
        }
    )

    for col in ["floor_level", "property_sub_type"]:
        if col in hdb_df.columns:
            hdb_df[col] = hdb_df[col].str.lower()

    numerical_cols = ["resale_price", "area_sqm", "remaining_lease_months", "lease_commence_date"]
    for col in numerical_cols:
        if col in hdb_df.columns:
            hdb_df[col] = pd.to_numeric(hdb_df[col], errors="coerce")
            hdb_df[col] = pd.Series(hdb_df[col], dtype="Int64")

    if "area_sqm" in hdb_df.columns:
        hdb_df["area_sqft"] = hdb_df["area_sqm"] * SQM_TO_SQFT

    if "transaction_date" in hdb_df.columns:
        hdb_df["transaction_date"] = pd.to_datetime(
            hdb_df["transaction_date"], format="%Y-%m"
        ).dt.date

    categorical_cols = ["property_sub_type", "flat_model", "floor_level", "town"]
    for col in categorical_cols:
        if col in hdb_df.columns:
            hdb_df[col] = hdb_df[col].astype("category")

    string_cols = ["street_name", "property_index", "project_name"]
    for col in string_cols:
        if col in hdb_df.columns:
            hdb_df[col] = hdb_df[col].astype("string")

    hdb_df["property_type"] = "HDB"
    hdb_df["hold_type"] = "leasehold"

    if "floor_level" in hdb_df.columns:
        hdb_df[["floor_low", "floor_high"]] = [extract_two_digits(i) for i in hdb_df["floor_level"]]

    drop_cols = ["remaining_lease_months", "town", "flat_model"]
    hdb_df = hdb_df.drop(columns=drop_cols, errors="ignore")

    if "resale_price" in hdb_df.columns and "area_sqft" in hdb_df.columns:
        hdb_df["unitprice_psf"] = hdb_df["resale_price"] / hdb_df["area_sqft"]

    logger.info(f"  Processed {len(hdb_df):,} HDB transactions")
    return hdb_df


def create_property_table(unique_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Create standardized property table.

    Args:
        unique_gdf: GeoDataFrame with property data

    Returns:
        Property DataFrame with standardized columns
    """
    logger.info("Creating property table...")

    property_df = unique_gdf.copy()
    property_df.columns = property_df.columns.str.lower()
    property_df = property_df.rename({"nameaddress": "property_id"}, axis=1)

    # Store postal code for later merge with amenity metrics
    if "postal" in property_df.columns:
        property_df["_postal_code"] = property_df["postal"]

    str_cast_list = ["property_id", "blk_no", "road_name", "building", "address"]
    for col in str_cast_list:
        if col in property_df.columns:
            property_df[col] = property_df[col].astype("string")

    if "postal" in property_df.columns:
        property_df["postal"] = pd.to_numeric(property_df["postal"], errors="coerce")
        property_df["postal"] = property_df["postal"].astype("Int64")

    cols_to_keep = [
        "property_id",
        "blk_no",
        "road_name",
        "building",
        "address",
        "postal",
        "_postal_code",  # Keep postal code for amenity merge
        "planning_area",
        "property_type",
    ]
    cols_exist = [c for c in cols_to_keep if c in property_df.columns]
    property_df = property_df[cols_exist]

    logger.info(f"  Created property table with {len(property_df):,} records")
    return property_df


def create_private_facilities(property_df: pd.DataFrame) -> pd.DataFrame:
    """Create private property facilities table with random assignments.

    Args:
        property_df: Property DataFrame

    Returns:
        Facilities DataFrame with exploded facilities
    """
    logger.info("Creating private property facilities...")

    facilities_list = [
        "bbq",
        "gym",
        "tennis court",
        "sky terrace",
        "jacuzzi",
        "swimming pool",
        "yoga corner",
        "pavilion",
        "fitness corner",
    ]

    private_properties = property_df[property_df["property_type"].str.lower() == "private"][
        ["property_id"]
    ].copy()

    private_properties["facilities"] = [
        random.sample(facilities_list, np.random.randint(5, 7))
        for _ in range(len(private_properties))
    ]

    private_facilities = private_properties.explode("facilities").reset_index(drop=True)

    logger.info(f"  Created {len(private_facilities):,} facility records")
    return private_facilities


def create_nearby_facilities(unique_joined: pd.DataFrame) -> pd.DataFrame:
    """Create nearby facilities table from spatial join results.

    Args:
        unique_joined: DataFrame from compute_amenity_distances

    Returns:
        Nearby facilities DataFrame
    """
    logger.info("Creating nearby facilities table...")

    nearby_df = unique_joined.copy()
    nearby_df = nearby_df.rename({"searchval": "property_index", "distance": "distance_m"}, axis=1)
    nearby_df = nearby_df[["property_index", "type", "name", "distance_m"]]
    nearby_df["distance_m"] = nearby_df["distance_m"].astype("int32")

    logger.info(f"  Created nearby facilities table with {len(nearby_df):,} records")
    return nearby_df


def create_transaction_sales(hdb_df: pd.DataFrame, private_df: pd.DataFrame) -> pd.DataFrame:
    """Combine HDB and private transactions into sales table.

    Args:
        hdb_df: Processed HDB transactions
        private_df: Processed private transactions

    Returns:
        Combined transaction sales DataFrame
    """
    logger.info("Creating transaction sales table...")

    transaction_sales = pd.concat([hdb_df, private_df], ignore_index=True)
    logger.info(f"  Created transaction sales with {len(transaction_sales):,} records")
    return transaction_sales


def create_listing_sales(transaction_sales: pd.DataFrame) -> pd.DataFrame:
    """Create listing sales from transaction data with derived columns.

    Args:
        transaction_sales: Transaction sales DataFrame

    Returns:
        Listing sales DataFrame
    """
    logger.info("Creating listing sales table...")

    frac = 0.8
    replace = True

    hdb_sales = (
        transaction_sales[transaction_sales["property_type"] == "HDB"]
        .sort_values("transaction_date", ascending=False)
        .groupby("property_index")
        .first()
        .sample(frac=frac, replace=replace)
    )

    private_sales = (
        transaction_sales[transaction_sales["property_type"] != "HDB"]
        .sort_values("transaction_date", ascending=False)
        .groupby("property_index")
        .first()
        .sample(frac=frac, replace=replace)
    )

    listing_sales = pd.concat([hdb_sales, private_sales]).reset_index()

    # Infer room count using helper (cleaner than nested list comprehensions)
    listing_sales["room_no"] = listing_sales.apply(
        lambda row: feature_helpers.infer_room_count(row["property_sub_type"], row["area_sqft"]),
        axis=1,
    )

    # Estimate bathroom count using helper
    listing_sales["bathroom_no"] = listing_sales["area_sqft"].apply(
        feature_helpers.estimate_bathroom_count
    )

    # Calculate floor number using helper
    listing_sales["floor"] = listing_sales.apply(
        lambda row: feature_helpers.calculate_floor_number(row["floor_low"], row["floor_high"]),
        axis=1,
    )

    drop_cols = ["floor_low", "floor_high", "floor_level"]
    listing_sales = listing_sales.drop(columns=drop_cols, errors="ignore")

    logger.info(f"  Created listing sales with {len(listing_sales):,} records")
    return listing_sales


def run_l2_features_pipeline(
    data_base_path: Path | None = None, include_planning_area: bool = True
) -> dict:
    """Run complete L2 features pipeline.

    Args:
        data_base_path: Base path to data directory
        include_planning_area: Whether to include planning area data

    Returns:
        Dictionary with pipeline results and output DataFrames
    """
    logger.info("=" * 60)
    logger.info("L2 Features Pipeline")
    logger.info("=" * 60)

    results = {}

    condo_df, ec_df, hdb_df = load_transaction_data()
    results["transaction_count"] = len(condo_df) + len(ec_df) + len(hdb_df)

    unique_df, amenity_df = load_property_and_amenity_data()
    unique_df = prepare_unique_properties(unique_df)

    unique_gdf = create_property_geodataframe(unique_df)
    amenity_gdf = create_amenity_geodataframe(amenity_df)

    # Compute amenity distances for nearby facilities table (spatial join)
    unique_joined = compute_amenity_distances(unique_gdf, amenity_gdf)

    # Compute per-type amenity metrics for property features
    amenity_metrics = compute_amenity_distances_by_type(unique_gdf, amenity_gdf)

    planning_area_gpd = None
    if include_planning_area:
        planning_area_gpd = load_planning_area(data_base_path)

    unique_gdf = compute_planning_area(unique_gdf, planning_area_gpd)

    private_df = process_private_transactions(condo_df, ec_df)
    hdb_df = process_hdb_transactions(hdb_df)

    property_df = create_property_table(unique_gdf)

    # Merge amenity metrics into property table
    logger.info("Merging amenity metrics into property table...")

    # Use postal code as merge key since amenity_metrics is keyed by POSTAL
    if "_postal_code" in property_df.columns:
        # Merge on postal code
        # Add merge_key column BEFORE adding prefix to avoid it getting prefixed
        amenity_metrics = amenity_metrics.copy()
        amenity_metrics["merge_key"] = amenity_metrics["POSTAL"]
        amenity_metrics_renamed = amenity_metrics.add_prefix("amty_")
        # The merge_key column is now amty_merge_key

        property_df = property_df.merge(
            amenity_metrics_renamed,
            left_on="_postal_code",
            right_on="amty_merge_key",
            how="left",
        ).drop(columns=["_postal_code", "amty_merge_key", "amty_POSTAL"], errors="ignore")

        # Count merged columns
        amenity_cols = [col for col in property_df.columns if col.startswith("amty_")]
        logger.info(f"  Merged {len(amenity_cols)} amenity metric columns")
    else:
        logger.warning("No postal code column found, skipping amenity merge")

    # Also export amenity metrics separately for L3 pipeline
    logger.info("Exporting amenity metrics for L3 pipeline...")
    amenity_for_l3 = amenity_metrics.copy()
    save_parquet(
        amenity_for_l3,
        "L2_housing_per_type_amenity_features",
        source="L2 per-type amenity metrics",
    )
    logger.info(f"  Saved amenity features for L3: {len(amenity_for_l3)} properties")

    private_facilities = create_private_facilities(property_df)
    nearby_df = create_nearby_facilities(unique_joined)

    transaction_sales = create_transaction_sales(hdb_df, private_df)
    listing_sales = create_listing_sales(transaction_sales)

    logger.info("\nSaving outputs...")
    save_parquet(property_df, "L3_property", source="L2 features pipeline")
    save_parquet(
        private_facilities, "L3_private_property_facilities", source="L2 features pipeline"
    )
    save_parquet(nearby_df, "L3_property_nearby_facilities", source="L2 features pipeline")
    save_parquet(transaction_sales, "L3_property_transactions_sales", source="L2 features pipeline")
    save_parquet(listing_sales, "L3_property_listing_sales", source="L2 features pipeline")

    results["property_df"] = property_df
    results["private_facilities"] = private_facilities
    results["nearby_df"] = nearby_df
    results["transaction_sales"] = transaction_sales
    results["listing_sales"] = listing_sales

    logger.info("\n" + "=" * 60)
    logger.info("✅ L2 Features Pipeline Complete!")
    logger.info(f"  Property records: {len(property_df):,}")
    logger.info(f"  Facility records: {len(private_facilities):,}")
    logger.info(f"  Nearby records: {len(nearby_df):,}")
    logger.info(f"  Transaction sales: {len(transaction_sales):,}")
    logger.info(f"  Listing sales: {len(listing_sales):,}")
    logger.info("=" * 60)

    return results


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run L2 features pipeline")
    parser.add_argument(
        "--skip-planning-area", action="store_true", help="Skip planning area assignment"
    )

    args = parser.parse_args()
    run_l2_features_pipeline(include_planning_area=not args.skip_planning_area)


if __name__ == "__main__":
    main()
