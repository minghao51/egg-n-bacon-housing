"""L2: Feature engineering pipeline.

This module provides functions for:
- Loading and processing transaction data (HDB, Condo, EC)
- Generating H3 grid polygons for properties
- Computing amenity distances via spatial join
- Creating property, facilities, and listings tables
- Running complete L2 features pipeline
"""

import logging
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

from src.config import Config
from src.data_helpers import load_parquet, save_parquet

from .spatial_h3 import generate_polygons

logger = logging.getLogger(__name__)

SQM_TO_SQFT = 10.764


def load_transaction_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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


def load_property_and_amenity_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
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


def load_planning_area(data_base_path: Optional[Path] = None) -> Optional[gpd.GeoDataFrame]:
    """Load planning area shapefile.

    Args:
        data_base_path: Base path to data directory

    Returns:
        GeoDataFrame with planning areas, or None if not found
    """
    if data_base_path is None:
        data_base_path = Config.DATA_DIR

    planning_area_path = data_base_path / "raw_data" / "onemap_planning_area_polygon.shp"

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


def compute_planning_area(
    unique_gdf: gpd.GeoDataFrame, planning_area_gpd: Optional[gpd.GeoDataFrame]
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


def extract_lease_info(lease_info: str) -> Tuple[Optional[int], str]:
    """Extract lease information from tenure string.

    Args:
        lease_info: Tenure string like "99 yrs lease commencing from 2007" or "Freehold"

    Returns:
        Tuple of (commencing_year or None, hold_type)
    """
    if lease_info == "Freehold":
        return None, "freehold"
    else:
        parts = lease_info.split(" ")
        if parts[-1].isdigit() and 1900 <= int(parts[-1]) <= 2100:
            return int(parts[-1]), "leasehold"
        return None, "leasehold"


def extract_two_digits(string: str) -> Tuple[str, str]:
    """Extract first two digits from floor range string.

    Args:
        string: String like "01 to 05"

    Returns:
        Tuple of (low, high)
    """
    digits_parts = string.split(" to ")
    return (digits_parts[0], digits_parts[1])


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

    private_df.columns = (
        private_df.columns.str.replace(r"\((.*?)\)", r"_\1", regex=True)
        .str.replace(r"\)$", "", regex=True)
        .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
        .str.replace(r"_$", "", regex=True)
        .str.lower()
    )

    private_df = private_df.drop(
        ["nettprice", "numberofunits", "typeofarea", "typeofsale"], axis=1, errors="ignore"
    )

    private_df[["lease_start_yr", "hold_type"]] = private_df["tenure"].apply(
        lambda x: pd.Series(extract_lease_info(x))
    )

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
        private_df["property_index"] = private_df["project_name"].fillna("") + " " + private_df["street_name"].fillna("")
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

    listing_sales["room_no"] = [
        i[0] if "room" in i else 0 for i in listing_sales["property_sub_type"]
    ]
    listing_sales["room_no"] = [
        x if x != 0 else np.clip(int(y / np.random.randint(15, 25) / SQM_TO_SQFT), a_min=1, a_max=6)
        for x, y in zip(listing_sales["room_no"], listing_sales["area_sqft"])
    ]
    listing_sales["room_no"] = listing_sales["room_no"].astype("int")

    listing_sales["bathroom_no"] = [
        np.clip(int(x / np.random.randint(35, 45) / SQM_TO_SQFT), a_min=1, a_max=4)
        for x in listing_sales["area_sqft"]
    ]
    listing_sales["bathroom_no"] = listing_sales["bathroom_no"].astype("int")

    listing_sales["floor"] = [
        int(np.random.randint(int(x.replace("B", "-").lstrip("-").zfill(2)), int(y.replace("B", "-").lstrip("-").zfill(2))))
        for x, y in zip(listing_sales["floor_low"], listing_sales["floor_high"])
    ]
    listing_sales["floor"] = listing_sales["floor"].astype("int")

    drop_cols = ["floor_low", "floor_high", "floor_level"]
    listing_sales = listing_sales.drop(columns=drop_cols, errors="ignore")

    logger.info(f"  Created listing sales with {len(listing_sales):,} records")
    return listing_sales


def run_features_pipeline(
    data_base_path: Optional[Path] = None, include_planning_area: bool = True
) -> Dict:
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

    unique_joined = compute_amenity_distances(unique_gdf, amenity_gdf)

    planning_area_gpd = None
    if include_planning_area:
        planning_area_gpd = load_planning_area(data_base_path)

    unique_gdf = compute_planning_area(unique_gdf, planning_area_gpd)

    private_df = process_private_transactions(condo_df, ec_df)
    hdb_df = process_hdb_transactions(hdb_df)

    property_df = create_property_table(unique_gdf)
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
