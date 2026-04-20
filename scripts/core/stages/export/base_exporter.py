"""Data loading and standardization functions for the L3 export pipeline."""

import logging

import geopandas as gpd
import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet
from scripts.core.data_loader import PropertyType, TransactionLoader
from scripts.core.stages.helpers import export_helpers

logger = logging.getLogger(__name__)

DISTRICT_TO_URA_LOCALITY = {
    **{str(i): "Core Central Region" for i in range(1, 12)},
    **{str(i): "Rest of Central Region" for i in [12, 13, 14, 15, 19, 20]},
    **{str(i): "Outside Central Region" for i in [16, 17, 18, 21, 22, 23, 24, 25, 26, 27, 28]},
}


def load_hdb_transactions() -> pd.DataFrame:
    """Load HDB transaction data from L1.

    Returns:
        DataFrame with HDB transactions
    """
    logger.info("Loading HDB transactions from L1...")

    loader = TransactionLoader()
    df = loader.load_transaction(PropertyType.HDB, stage="L1")

    if df.empty:
        logger.warning("HDB data not found or empty")
        return pd.DataFrame()

    logger.info(f"Loaded {len(df):,} HDB transactions")

    return df


def load_condo_transactions() -> pd.DataFrame:
    """Load Condo transaction data from L1.

    Returns:
        DataFrame with Condo transactions
    """
    logger.info("Loading Condo transactions from L1...")

    loader = TransactionLoader()
    df = loader.load_transaction(PropertyType.CONDO, stage="L1")

    if df.empty:
        logger.warning("Condo data not found or empty")
        return pd.DataFrame()

    # Clean numeric columns using helper
    price_cols = ["Transacted Price ($)"]
    area_cols = ["Area (SQFT)", "Area (SQM)"]
    psf_cols = ["Unit Price ($ PSF)"]

    df = export_helpers.clean_price_columns(df, price_cols, area_cols, psf_cols)

    logger.info(f"Loaded {len(df):,} Condo transactions")

    return df


def load_ec_transactions() -> pd.DataFrame:
    """Load Executive Condo (EC) transaction data from L1.

    Returns:
        DataFrame with EC transactions
    """
    logger.info("Loading Executive Condo (EC) transactions from L1...")

    loader = TransactionLoader()
    df = loader.load_transaction(PropertyType.EC, stage="L1")

    if df.empty:
        logger.warning("EC data not found or empty")
        return pd.DataFrame()

    # Clean numeric columns using helper (EC has $ sign in price column)
    price_cols = ["Transacted Price ($)"]
    area_cols = ["Area (SQFT)", "Area (SQM)"]
    psf_cols = ["Unit Price ($ PSF)", "Unit Price ($ PSM)"]

    df = export_helpers.clean_price_columns(df, price_cols, area_cols, psf_cols)

    logger.info(f"Loaded {len(df):,} EC transactions")

    return df


def load_geocoded_properties() -> pd.DataFrame:
    """Load geocoded property locations from L2.

    Returns:
        DataFrame with property coordinates
    """
    logger.info("Loading geocoded properties from L2...")

    # Try enhanced version first (fuzzy matched), fall back to original
    path_enhanced = Config.PARQUETS_DIR / "L2" / "housing_unique_searched_enhanced.parquet"
    path_original = Config.PARQUETS_DIR / "L2" / "housing_unique_searched.parquet"

    path = path_enhanced if path_enhanced.exists() else path_original

    if not path.exists():
        logger.warning(f"Geocoded properties not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    version = "Enhanced (fuzzy matched)" if path == path_enhanced else "Original"
    logger.info(f"Loaded {len(df):,} geocoded properties [{version}]")

    return df


def load_amenity_features() -> pd.DataFrame:
    """Load amenity distance features from L2.

    Returns:
        DataFrame with amenity features
    """
    logger.info("Loading amenity features from L2...")

    # Try new per-type amenity features first (Phase 2 enhancement)
    path_new = Config.PARQUETS_DIR / "L2" / "housing_per_type_amenity_features.parquet"
    # Fall back to old multi-amenity features
    path_old = Config.PARQUETS_DIR / "L2" / "housing_multi_amenity_features.parquet"

    # Determine which file to use
    if path_new.exists():
        path = path_new
        logger.info(f"  Using new per-type amenity features: {path.name}")
    elif path_old.exists():
        path = path_old
        logger.info(f"  Using legacy amenity features: {path.name}")
    else:
        logger.warning(f"Amenity features not found: tried {path_new.name} and {path_old.name}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    logger.info(f"Loaded amenity features with {len(df.columns)} columns")

    return df


def load_rental_yield() -> pd.DataFrame:
    """Load rental yield data from L2.

    Returns:
        DataFrame with rental yield by town and month
    """
    logger.info("Loading rental yield data from L2...")

    path = Config.PARQUETS_DIR / "L2" / "rental_yield.parquet"

    if not path.exists():
        logger.warning(f"Rental yield data not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    logger.info(f"Loaded rental yield data: {len(df):,} records")

    return df


def load_precomputed_metrics() -> pd.DataFrame:
    """Load precomputed monthly metrics from L3.

    Returns:
        DataFrame with metrics by month and area
    """
    logger.info("Loading precomputed metrics from L3...")

    path = Config.PARQUETS_DIR / "L3" / "metrics_monthly.parquet"

    if not path.exists():
        logger.warning(f"Precomputed metrics not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    logger.info(f"Loaded precomputed metrics: {len(df):,} records")

    return df


def load_school_features() -> pd.DataFrame:
    """Load school distance features from unified dataset.

    Returns:
        DataFrame with school features (distances, counts, scores)
    """
    logger.info("Loading school features from L3 unified data...")

    try:
        df = load_parquet("L3_housing_unified")
    except Exception:
        logger.warning("Could not load L3_housing_unified from metadata, trying direct path...")
        path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
        if not path.exists():
            logger.warning(f"Unified data not found: {path}")
            return pd.DataFrame()
        df = pd.read_parquet(path)

    school_cols = [col for col in df.columns if "school" in col.lower()]
    if not school_cols:
        logger.warning("No school features found in unified data")
        return pd.DataFrame()

    school_df = df[["address", "block", "street_name"] + school_cols].copy()
    logger.info(f"Loaded {len(school_df)} records with {len(school_cols)} school feature columns")

    return school_df


def load_planning_areas() -> gpd.GeoDataFrame:
    """Load planning area geojson with region information.

    Prioritizes URA boundary file which includes region data.

    Returns:
        GeoDataFrame with planning area polygons and region info
    """
    logger.info("Loading planning areas from geojson...")

    # Priority: URA boundary file (has region) > onemap file
    possible_paths = [
        Config.MANUAL_DIR / "geojsons" / "ura_planning_area_boundary.geojson",
        Config.DATA_DIR / "raw_data" / "onemap_planning_area_polygon.geojson",
        Config.DATA_DIR / "raw_data" / "onemap" / "planning-area.geojson",
        Config.MANUAL_DIR / "geojsons" / "onemap_planning_area_polygon.geojson",
    ]

    gdf = None
    for path in possible_paths:
        if path.exists():
            gdf = gpd.read_file(path)
            logger.info(f"Loaded planning areas from {path}")
            break

    if gdf is None:
        logger.warning("Planning area geojson not found")
        return gpd.GeoDataFrame()

    # Ensure CRS is 4326
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    # Standardize column names (URA uses PLN_AREA_N, onemap uses pln_area_n)
    column_mapping = {
        "PLN_AREA_N": "pln_area_n",
        "PLN_AREA_C": "pln_area_c",
        "REGION_N": "region",
        "REGION_C": "region_c",
        "CA_IND": "ca_ind",
    }
    gdf = gdf.rename(columns=column_mapping)

    logger.info(f"Loaded {len(gdf)} planning areas (columns: {list(gdf.columns)})")

    return gdf


def standardize_hdb_data(hdb_df: pd.DataFrame) -> pd.DataFrame:
    """Standardize HDB transaction data to unified schema.

    Args:
        hdb_df: Raw HDB transaction DataFrame

    Returns:
        Standardized DataFrame with unified column names
    """
    logger.info("Standardizing HDB data...")

    df = hdb_df.copy()

    # Add property type
    df["property_type"] = "HDB"

    # Standardize price
    df["price"] = df["resale_price"]

    # Standardize floor area (keep both sqm and sqft)
    df["floor_area_sqm"] = df["floor_area_sqm"]
    df["floor_area_sqft"] = df["floor_area_sqm"] * 10.764

    # Standardize date
    df["transaction_date"] = pd.to_datetime(df["month"], format="%Y-%m")

    # Standardize address
    df["address"] = df["block"] + " " + df["street_name"]

    # Add price per square foot (primary) and per square meter (derived)
    df["price_psf"] = df["price"] / df["floor_area_sqft"]
    df["price_psm"] = df["price_psf"] * 10.764

    logger.info(f"Standardized {len(df):,} HDB transactions")

    return df


def standardize_condo_data(condo_df: pd.DataFrame) -> pd.DataFrame:
    """Standardize Condo transaction data to unified schema.

    Args:
        condo_df: Raw Condo transaction DataFrame

    Returns:
        Standardized DataFrame with unified column names
    """
    logger.info("Standardizing Condo data...")

    df = condo_df.copy()

    # Add property type
    df["property_type"] = "Condominium"

    # Standardize price
    df["price"] = df["Transacted Price ($)"]

    # Standardize floor area
    df["floor_area_sqft"] = df["Area (SQFT)"]
    df["floor_area_sqm"] = df["Area (SQM)"]

    # Standardize date
    df["transaction_date"] = pd.to_datetime(df["Sale Date"], format="%b-%y", errors="coerce")

    # Standardize address
    df["address"] = df["Project Name"] + ", " + df["Street Name"]

    # Add town (use street name as proxy for now)
    df["town"] = "Condo - " + df["Street Name"]

    # Add price per square foot (primary) and per square meter (derived)
    df["price_psf"] = df["Unit Price ($ PSF)"]  # Already provided
    df["price_psm"] = df["price_psf"] * 10.764

    # Ensure month is consistent (add if missing)
    if "month" not in df.columns:
        df["month"] = pd.to_datetime(df["transaction_date"]).dt.to_period("M").astype(str)

    logger.info(f"Standardized {len(df):,} Condo transactions")

    return df


def standardize_ec_data(ec_df: pd.DataFrame) -> pd.DataFrame:
    """Standardize Executive Condo (EC) transaction data to unified schema.

    Args:
        ec_df: Raw EC transaction DataFrame

    Returns:
        Standardized DataFrame with unified column names
    """
    logger.info("Standardizing EC data...")

    df = ec_df.copy()

    # Add property type
    df["property_type"] = "EC"

    # Standardize price
    df["price"] = df["Transacted Price ($)"]

    # Standardize floor area
    df["floor_area_sqft"] = df["Area (SQFT)"]
    df["floor_area_sqm"] = df["Area (SQM)"]

    # Standardize date (EC uses same format as Condo: Dec-22)
    df["transaction_date"] = pd.to_datetime(df["Sale Date"], format="%b-%y", errors="coerce")

    # Standardize address
    df["address"] = df["Project Name"] + ", " + df["Street Name"]

    # Add town (use street name as proxy for now)
    df["town"] = "EC - " + df["Street Name"]

    # Add price per square foot (primary) and per square meter (derived)
    df["price_psf"] = df["Unit Price ($ PSF)"]
    df["price_psm"] = df["price_psf"] * 10.764

    # Ensure month is consistent (add if missing)
    if "month" not in df.columns:
        df["month"] = pd.to_datetime(df["transaction_date"]).dt.to_period("M").astype(str)

    logger.info(f"Standardized {len(df):,} EC transactions")

    return df
