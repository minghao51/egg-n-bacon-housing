"""L3: Unified dataset creation and export pipeline.

This module creates a comprehensive unified housing dataset by combining:
- HDB, Condo, and EC transaction data from L1
- Geocoding and amenity features from L2
- Planning areas from geojson
- Rental yield data
- Precomputed growth metrics
- School distance features (nearest school distances, counts, and attributes)

Creates:
    L3/housing_unified.parquet - Complete dataset with all features
    L3/market_summary.parquet - Precomputed summary by property_type/period/tier
    L3/tier_thresholds_evolution.parquet - Tier thresholds over time
    L3/planning_area_metrics.parquet - Planning area aggregated metrics
    L3/lease_decay_stats.parquet - HDB lease decay statistics
    L3/rental_yield_top_combos.parquet - Top rental yield combinations

Usage:
    from scripts.core.stages.L3_export import run_l3_pipeline
    run_l3_pipeline(upload_s3=False, export_csv=False)
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import geopandas as gpd
import pandas as pd

from scripts.core.config import Config
from scripts.core.school_features import calculate_school_features, load_schools

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# DATA LOADING
# ============================================================================

def load_hdb_transactions() -> pd.DataFrame:
    """Load HDB transaction data from L1.

    Returns:
        DataFrame with HDB transactions
    """
    logger.info("Loading HDB transactions from L1...")

    path = Config.PARQUETS_DIR / "L1" / "housing_hdb_transaction.parquet"

    if not path.exists():
        logger.warning(f"HDB data not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    logger.info(f"Loaded {len(df):,} HDB transactions")

    return df


def load_condo_transactions() -> pd.DataFrame:
    """Load Condo transaction data from L1.

    Returns:
        DataFrame with Condo transactions
    """
    logger.info("Loading Condo transactions from L1...")

    path = Config.PARQUETS_DIR / "L1" / "housing_condo_transaction.parquet"

    if not path.exists():
        logger.warning(f"Condo data not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Clean price column: Remove commas and convert to numeric
    if 'Transacted Price ($)' in df.columns:
        df['Transacted Price ($)'] = (
            df['Transacted Price ($)']
            .astype(str)
            .str.replace(',', '')
            .astype(float)
        )

    # Clean area columns: Remove commas and convert to numeric
    if 'Area (SQFT)' in df.columns:
        df['Area (SQFT)'] = (
            df['Area (SQFT)']
            .astype(str)
            .str.replace(',', '')
            .astype(float)
        )

    if 'Area (SQM)' in df.columns:
        df['Area (SQM)'] = (
            df['Area (SQM)']
            .astype(str)
            .str.replace(',', '')
            .astype(float)
        )

    # Clean PSF column: Remove commas and convert to numeric
    if 'Unit Price ($ PSF)' in df.columns:
        df['Unit Price ($ PSF)'] = (
            df['Unit Price ($ PSF)']
            .astype(str)
            .str.replace(',', '')
            .astype(float)
        )

    logger.info(f"Loaded {len(df):,} Condo transactions")

    return df


def load_ec_transactions() -> pd.DataFrame:
    """Load Executive Condo (EC) transaction data from L1.

    Returns:
        DataFrame with EC transactions
    """
    logger.info("Loading Executive Condo (EC) transactions from L1...")

    path = Config.PARQUETS_DIR / "L1" / "housing_ec_transaction.parquet"

    if not path.exists():
        logger.warning(f"EC data not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Clean price column: Remove commas and convert to numeric
    if 'Transacted Price ($)' in df.columns:
        df['Transacted Price ($)'] = (
            df['Transacted Price ($)']
            .astype(str)
            .str.replace(',', '')
            .str.replace('$', '')
            .str.strip()
            .astype(float)
        )

    # Clean area columns: Remove commas and convert to numeric
    if 'Area (SQFT)' in df.columns:
        df['Area (SQFT)'] = (
            df['Area (SQFT)']
            .astype(str)
            .str.replace(',', '')
            .astype(float)
        )

    if 'Area (SQM)' in df.columns:
        # Area SQM is already int64 in EC data
        df['Area (SQM)'] = pd.to_numeric(df['Area (SQM)'], errors='coerce')

    # Clean PSF column: Remove commas and convert to numeric
    if 'Unit Price ($ PSF)' in df.columns:
        df['Unit Price ($ PSF)'] = (
            df['Unit Price ($ PSF)']
            .astype(str)
            .str.replace(',', '')
            .astype(float)
        )

    # Clean PSM column
    if 'Unit Price ($ PSM)' in df.columns:
        df['Unit Price ($ PSM)'] = (
            df['Unit Price ($ PSM)']
            .astype(str)
            .str.replace(',', '')
            .astype(float)
        )

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

    # Use multi-amenity features (has all distance and count columns)
    path = Config.PARQUETS_DIR / "L2" / "housing_multi_amenity_features.parquet"

    if not path.exists():
        logger.warning(f"Amenity features not found: {path}")
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

    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not path.exists():
        logger.warning(f"Unified data not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Extract only school-related columns
    school_cols = [col for col in df.columns if 'school' in col.lower()]
    if not school_cols:
        logger.warning("No school features found in unified data")
        return pd.DataFrame()

    school_df = df[['address', 'block', 'street_name'] + school_cols].copy()
    logger.info(f"Loaded {len(school_df)} records with {len(school_cols)} school feature columns")

    return school_df


def load_planning_areas() -> gpd.GeoDataFrame:
    """Load planning area geojson.

    Returns:
        GeoDataFrame with planning area polygons
    """
    logger.info("Loading planning areas from geojson...")

    # Try common paths
    possible_paths = [
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
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')

    logger.info(f"Loaded {len(gdf)} planning areas")

    return gdf


# ============================================================================
# DATA STANDARDIZATION
# ============================================================================

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
    df['property_type'] = 'HDB'

    # Standardize price
    df['price'] = df['resale_price']

    # Standardize floor area (keep both sqm and sqft)
    df['floor_area_sqm'] = df['floor_area_sqm']
    df['floor_area_sqft'] = df['floor_area_sqm'] * 10.764

    # Standardize date
    df['transaction_date'] = pd.to_datetime(df['month'], format='%Y-%m')

    # Standardize address
    df['address'] = df['block'] + ' ' + df['street_name']

    # Add town (already exists)
    # No planning area yet (will be added later from coordinates)

    # Add price per square foot (primary) and per square meter (derived)
    df['price_psf'] = df['price'] / df['floor_area_sqft']
    df['price_psm'] = df['price_psf'] * 10.764

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
    df['property_type'] = 'Condominium'

    # Standardize price
    df['price'] = df['Transacted Price ($)']

    # Standardize floor area
    df['floor_area_sqft'] = df['Area (SQFT)']
    df['floor_area_sqm'] = df['Area (SQM)']

    # Standardize date
    df['transaction_date'] = pd.to_datetime(
        df['Sale Date'],
        format='%b-%y',
        errors='coerce'
    )

    # Standardize address
    df['address'] = df['Project Name'] + ', ' + df['Street Name']

    # Add town (use street name as proxy for now)
    df['town'] = 'Condo - ' + df['Street Name']

    # Add price per square foot (primary) and per square meter (derived)
    df['price_psf'] = df['Unit Price ($ PSF)']  # Already provided
    df['price_psm'] = df['price_psf'] * 10.764

    # Ensure month is consistent (add if missing)
    if 'month' not in df.columns:
        df['month'] = pd.to_datetime(df['transaction_date']).dt.to_period('M').astype(str)

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
    df['property_type'] = 'EC'

    # Standardize price
    df['price'] = df['Transacted Price ($)']

    # Standardize floor area
    df['floor_area_sqft'] = df['Area (SQFT)']
    df['floor_area_sqm'] = df['Area (SQM)']

    # Standardize date (EC uses same format as Condo: Dec-22)
    df['transaction_date'] = pd.to_datetime(
        df['Sale Date'],
        format='%b-%y',
        errors='coerce'
    )

    # Standardize address
    df['address'] = df['Project Name'] + ', ' + df['Street Name']

    # Add town (use street name as proxy for now)
    df['town'] = 'EC - ' + df['Street Name']

    # Add price per square foot (primary) and per square meter (derived)
    df['price_psf'] = df['Unit Price ($ PSF)']
    df['price_psm'] = df['price_psf'] * 10.764

    # Ensure month is consistent (add if missing)
    if 'month' not in df.columns:
        df['month'] = pd.to_datetime(df['transaction_date']).dt.to_period('M').astype(str)

    logger.info(f"Standardized {len(df):,} EC transactions")

    return df


# ============================================================================
# FEATURE ENRICHMENT
# ============================================================================

def merge_with_geocoding(
    transactions_df: pd.DataFrame,
    geo_df: pd.DataFrame
) -> pd.DataFrame:
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
    hdb_mask = transactions_df['property_type'] == 'HDB'
    private_mask = transactions_df['property_type'].isin(['Condominium', 'EC'])

    merged_dfs = []

    # Merge HDB transactions
    if hdb_mask.any():
        hdb_df = transactions_df[hdb_mask].copy()

        # Prepare geo data for HDB (filter to HDB properties if property_type exists)
        if 'property_type' in geo_df.columns:
            geo_hdb = geo_df[geo_df['property_type'] == 'hdb'].copy()
        else:
            geo_hdb = geo_df.copy()

        if not geo_hdb.empty:
            hdb_merged = pd.merge(
                hdb_df,
                geo_hdb[['BLK_NO', 'ROAD_NAME', 'POSTAL', 'LATITUDE', 'LONGITUDE']],
                left_on=['block', 'street_name'],
                right_on=['BLK_NO', 'ROAD_NAME'],
                how='left'
            )
            hdb_merged['lat'] = hdb_merged['LATITUDE']
            hdb_merged['lon'] = hdb_merged['LONGITUDE']
            hdb_merged.drop(['BLK_NO', 'ROAD_NAME', 'LATITUDE', 'LONGITUDE'], axis=1, inplace=True)
        else:
            hdb_merged = hdb_df
            hdb_merged['lat'] = None
            hdb_merged['lon'] = None

        merged_dfs.append(hdb_merged)

    # Merge Condo and EC transactions (both use private housing geocoding)
    if private_mask.any():
        private_df = transactions_df[private_mask].copy()

        # Prepare geo data for Condo (filter to private housing if property_type exists)
        if 'property_type' in geo_df.columns:
            geo_condo = geo_df[geo_df['property_type'] == 'private'].copy()
        else:
            geo_condo = geo_df.copy()

        if not geo_condo.empty:
            # Drop duplicates on street name (use first occurrence)
            geo_condo_unique = geo_condo.drop_duplicates(subset=['ROAD_NAME'], keep='first').copy()
            geo_condo_unique['street_name_upper'] = geo_condo_unique['ROAD_NAME'].str.upper()

            private_df = private_df.copy()
            private_df['street_name_upper'] = private_df['Street Name'].str.upper()

            private_merged = pd.merge(
                private_df,
                geo_condo_unique[['street_name_upper', 'LATITUDE', 'LONGITUDE']],
                on='street_name_upper',
                how='left'
            )
            private_merged['lat'] = private_merged['LATITUDE']
            private_merged['lon'] = private_merged['LONGITUDE']
            private_merged.drop(['street_name_upper', 'LATITUDE', 'LONGITUDE'], axis=1, inplace=True)
        else:
            private_merged = private_df
            private_merged['lat'] = None
            private_merged['lon'] = None

        merged_dfs.append(private_merged)

    # Combine back
    result = pd.concat(merged_dfs, ignore_index=True)

    # Report geocoding success
    geo_count = result['lat'].notna().sum()
    total_count = len(result)
    logger.info(f"Geocoded {geo_count:,} of {total_count:,} properties ({geo_count/total_count*100:.1f}%)")

    return result


def add_planning_area(
    transactions_df: pd.DataFrame,
    planning_areas_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """Add planning area by spatial join with coordinates.

    Args:
        transactions_df: Transactions with lat/lon
        planning_areas_gdf: Planning area polygons

    Returns:
        Transactions with planning_area column added
    """
    logger.info("Adding planning areas...")

    if planning_areas_gdf.empty:
        logger.warning("No planning area data available, skipping")
        transactions_df['planning_area'] = None
        return transactions_df

    # Create GeoDataFrame from transactions
    gdf = gpd.GeoDataFrame(
        transactions_df,
        geometry=gpd.points_from_xy(
            transactions_df['lon'].astype(float),
            transactions_df['lat'].astype(float)
        ),
        crs='EPSG:4326'
    )

    # Spatial join with planning areas
    result = gpd.sjoin(
        gdf,
        planning_areas_gdf[['pln_area_n', 'geometry']],
        how='left',
        predicate='within'
    )

    # Extract planning area name
    transactions_df['planning_area'] = result['pln_area_n']

    # Report coverage
    coverage = transactions_df['planning_area'].notna().sum()
    total = len(transactions_df)
    logger.info(f"Added planning area to {coverage:,} of {total:,} properties ({coverage/total*100:.1f}%)")

    return transactions_df


def add_amenity_features(
    transactions_df: pd.DataFrame,
    amenity_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge amenity distance and count features.

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
    if 'POSTAL' in transactions_df.columns and 'POSTAL' in amenity_df.columns:
        # Select ALL amenity columns to merge (distances AND counts)
        amenity_cols = [col for col in amenity_df.columns
                       if col.startswith('dist_') or col.startswith('count_') or col.endswith('_within_500m')
                       or col.endswith('_within_1km') or col.endswith('_within_2km')]

        merge_cols = ['POSTAL'] + amenity_cols

        result = pd.merge(
            transactions_df,
            amenity_df[merge_cols],
            on='POSTAL',
            how='left'
        )

        # Log what was added
        added_cols = [col for col in amenity_cols if col in result.columns]
        logger.info(f"Merged {len(added_cols)} amenity columns on postal code")
    elif 'address' in transactions_df.columns and 'address' in amenity_df.columns:
        result = pd.merge(
            transactions_df,
            amenity_df,
            on='address',
            how='left'
        )
        logger.info("Merged amenity features on address")
    else:
        logger.warning("Cannot merge amenity features - no common key")
        result = transactions_df

    return result


def merge_rental_yield(
    transactions_df: pd.DataFrame,
    rental_yield_df: pd.DataFrame
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

    # Ensure month columns are both datetime
    # Convert transactions_df month if it's a string
    if transactions_df['month'].dtype == 'object':
        transactions_df['month'] = pd.to_datetime(transactions_df['month'], format='%Y-%m', errors='coerce')

    # Convert rental_yield_df month if it's a string
    if rental_yield_df['month'].dtype == 'object':
        rental_yield_df['month'] = pd.to_datetime(rental_yield_df['month'], format='%Y-%m', errors='coerce')
    else:
        rental_yield_df['month'] = pd.to_datetime(rental_yield_df['month'])

    # Merge on town and month
    result = pd.merge(
        transactions_df,
        rental_yield_df[['town', 'month', 'rental_yield_pct']],
        on=['town', 'month'],
        how='left'
    )

    # Report coverage
    coverage = result['rental_yield_pct'].notna().sum()
    total = len(result)
    logger.info(f"Added rental yield to {coverage:,} of {total:,} records ({coverage/total*100:.1f}%)")

    return result


def merge_precomputed_metrics(
    transactions_df: pd.DataFrame,
    metrics_df: pd.DataFrame
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
    if transactions_df['month'].dtype == 'object':
        transactions_df['month'] = pd.to_datetime(transactions_df['month'], format='%Y-%m', errors='coerce')

    # Handle different types for metrics_df month (Period, datetime, or string)
    if str(metrics_df['month'].dtype) == 'period[M]':
        # PeriodDtype - convert to timestamp
        metrics_df['month'] = metrics_df['month'].dt.to_timestamp()
    elif metrics_df['month'].dtype == 'object':
        metrics_df['month'] = pd.to_datetime(metrics_df['month'], format='%Y-%m', errors='coerce')
    else:
        # Already datetime or convertible
        metrics_df['month'] = pd.to_datetime(metrics_df['month'])

    # Determine join key (prefer planning_area, fall back to town)
    if 'planning_area' in transactions_df.columns and 'planning_area' in metrics_df.columns:
        join_key = 'planning_area'
    elif 'town' in transactions_df.columns and 'town' in metrics_df.columns:
        join_key = 'town'
    else:
        logger.warning("No common geographic key for merging metrics")
        return transactions_df

    # Select key metric columns to merge (include month and join_key)
    metric_cols = [
        'month',
        join_key,  # Include the join key column
        'stratified_median_price',
        'mom_change_pct',
        'yoy_change_pct',
        'momentum_signal',
        'transaction_count',
        'volume_3m_avg',
        'volume_12m_avg'
    ]

    # Only select columns that exist
    available_cols = [col for col in metric_cols if col in metrics_df.columns]

    if len(available_cols) <= 2:  # Only 'month' and join_key exist
        logger.warning("No metric columns available for merge")
        return transactions_df

    metrics_to_merge = metrics_df[available_cols].copy()

    # Merge
    result = pd.merge(
        transactions_df,
        metrics_to_merge,
        on=['month', join_key],
        how='left'
    )

    # Log what was added (exclude month and join_key from count)
    added_cols = [col for col in available_cols if col not in ['month', join_key]]
    logger.info(f"Merged {len(added_cols)} metric columns on {join_key}+month")

    return result


# ============================================================================
# FINAL COLUMN SELECTION
# ============================================================================

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
        'property_type',  # CRITICAL: Must always be included
        'transaction_date',
        'town',
        'planning_area',  # NEW
        'address',
        'price',
        'floor_area_sqm',
        'floor_area_sqft',
        'price_psm',
        'price_psf',
        'lat',
        'lon'
    ]

    # Ensure all core columns exist (even if null)
    for col in core_columns:
        if col not in df.columns:
            logger.warning(f"Core column '{col}' not found in dataset, adding as None")
            df[col] = None

    # Optional columns to include if present
    optional_columns = [
        'month',  # Original date column
        'flat_type',  # HDB only
        'flat_model',  # HDB only
        'storey_range',  # HDB only
        'lease_commence_date',  # HDB only
        'remaining_lease_months',  # HDB only
        'Project Name',  # Condo only
        'Street Name',  # Condo only
        'Postal District',  # Condo only
        'Property Type',  # Condo only
        'Market Segment',  # Condo only
        # Amenity distance features
        'dist_to_nearest_supermarket',
        'dist_to_nearest_preschool',
        'dist_to_nearest_park',
        'dist_to_nearest_hawker',
        'dist_to_nearest_mrt',
        'dist_to_nearest_childcare',
        # Amenity count features (within radius)
        'supermarket_within_500m',
        'supermarket_within_1km',
        'supermarket_within_2km',
        'preschool_within_500m',
        'preschool_within_1km',
        'preschool_within_2km',
        'park_within_500m',
        'park_within_1km',
        'park_within_2km',
        'hawker_within_500m',
        'hawker_within_1km',
        'hawker_within_2km',
        'mrt_within_500m',
        'mrt_within_1km',
        'mrt_within_2km',
        'childcare_within_500m',
        'childcare_within_1km',
        'childcare_within_2km',
        # Rental yield
        'rental_yield_pct',  # NEW
        # Precomputed metrics
        'stratified_median_price',  # NEW
        'mom_change_pct',  # NEW
        'yoy_change_pct',  # NEW
        'momentum_signal',  # NEW
        'transaction_count',  # NEW
        'volume_3m_avg',  # NEW
        'volume_12m_avg',  # NEW
        # Period-dependent market segmentation (NEW)
        'year',  # NEW - Transaction year (for period calculation)
        'period_5yr',  # NEW - 5-year period bucket
        'market_tier_period',  # NEW - Period-dependent price tier
        'psf_tier_period',  # NEW - Period-dependent PSF tier
        # School features
        'school_within_500m',
        'school_within_1km',
        'school_within_2km',
        'school_accessibility_score',
        'school_primary_dist_score',
        'school_primary_quality_score',
        'school_secondary_dist_score',
        'school_secondary_quality_score',
        'school_density_score',
    ]

    # Add any other amenity/metric columns that might exist
    amenity_cols = [col for col in df.columns if col.startswith('dist_') or col.startswith('count_')]
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
    df['year'] = pd.to_datetime(df['transaction_date']).dt.year
    df['period_5yr'] = (df['year'] // 5) * 5
    df['period_5yr'] = df['period_5yr'].astype(str) + '-' + (df['period_5yr'] + 4).astype(str)

    # Calculate period-dependent price tiers
    def assign_price_tier(group):
        """Assign price tier based on 30/40/30 percentiles within period."""
        p30 = group['price'].quantile(0.30)
        p70 = group['price'].quantile(0.70)

        tiers = []
        for price in group['price']:
            if price <= p30:
                tiers.append('Mass Market')
            elif price <= p70:
                tiers.append('Mid-Tier')
            else:
                tiers.append('Luxury')

        return pd.Series(tiers, index=group.index)

    # Apply tier assignment within each property type + period
    df['market_tier_period'] = df.groupby(['property_type', 'period_5yr'], group_keys=False).apply(
        lambda g: assign_price_tier(g)
    )

    # Calculate period-dependent PSF tiers (if PSF column exists)
    if 'price_psf' in df.columns:
        def assign_psf_tier(group):
            """Assign PSF tier based on 30/40/30 percentiles within period."""
            p30 = group['price_psf'].quantile(0.30)
            p70 = group['price_psf'].quantile(0.70)

            tiers = []
            for psf in group['price_psf']:
                if psf <= p30:
                    tiers.append('Low PSF')
                elif psf <= p70:
                    tiers.append('Medium PSF')
                else:
                    tiers.append('High PSF')

            return pd.Series(tiers, index=group.index)

        df['psf_tier_period'] = df.groupby(['property_type', 'period_5yr'], group_keys=False).apply(
            lambda g: assign_psf_tier(g)
        )
    else:
        logger.warning("price_psf column not found, skipping PSF tier calculation")
        df['psf_tier_period'] = None

    logger.info(f"Added period segmentation: {len(df):,} transactions classified")
    logger.info(f"Periods: {sorted(df['period_5yr'].unique())}")

    return df


# ============================================================================
# PRECOMPUTED SUMMARY TABLES
# ============================================================================

def create_market_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create market summary table with aggregated statistics.

    Args:
        df: Full transaction DataFrame

    Returns:
        Summary table by property_type, period_5yr, market_tier_period
    """
    logger.info("Creating market summary table...")

    if df.empty:
        return pd.DataFrame()

    group_cols = ['property_type', 'period_5yr', 'market_tier_period']

    # Filter to columns that exist
    available_group_cols = [col for col in group_cols if col in df.columns]

    if len(available_group_cols) < 2:
        logger.warning("Cannot create market summary - missing required columns")
        return pd.DataFrame()

    summary = df.groupby(available_group_cols).agg({
        'price': ['count', 'median', 'mean', 'min', 'max', 'std'],
        'price_psm': ['median', 'mean'] if 'price_psm' in df.columns else 'count',
        'price_psf': ['median', 'mean'] if 'price_psf' in df.columns else 'count',
        'floor_area_sqft': ['median', 'mean'] if 'floor_area_sqft' in df.columns else 'count',
    }).reset_index()

    # Flatten column names
    summary.columns = [
        '_'.join(col).strip('_') if isinstance(col, tuple) else col
        for col in summary.columns
    ]

    # Calculate tier distribution percentages
    if 'market_tier_period' in available_group_cols:
        total_by_group = summary.groupby(available_group_cols[:2])['price_count'].sum().reset_index()
        total_by_group.columns = available_group_cols[:2] + ['total_count']
        summary = summary.merge(total_by_group, on=available_group_cols[:2], how='left')
        summary['tier_pct'] = (summary['price_count'] / summary['total_count'] * 100).round(1)
        summary = summary.drop(columns=['total_count'])

    logger.info(f"Created market summary with {len(summary):,} rows")
    return summary


def create_tier_thresholds_evolution(df: pd.DataFrame) -> pd.DataFrame:
    """Create tier threshold evolution table.

    Args:
        df: Full transaction DataFrame

    Returns:
        Table with max/median price thresholds by period and property_type
    """
    logger.info("Creating tier thresholds evolution table...")

    if df.empty or 'market_tier_period' not in df.columns:
        return pd.DataFrame()

    # Calculate thresholds for each tier
    thresholds = []

    for ptype in df['property_type'].unique():
        ptype_df = df[df['property_type'] == ptype]

        for period in ptype_df['period_5yr'].unique():
            period_df = ptype_df[ptype_df['period_5yr'] == period]

            for tier in ['Mass Market', 'Mid-Tier', 'Luxury']:
                tier_data = period_df[period_df['market_tier_period'] == tier]

                if not tier_data.empty:
                    thresholds.append({
                        'property_type': ptype,
                        'period': period,
                        'tier': tier,
                        'count': len(tier_data),
                        'min_price': tier_data['price'].min(),
                        'max_price': tier_data['price'].max(),
                        'median_price': tier_data['price'].median(),
                        'mean_price': tier_data['price'].mean(),
                    })

    result = pd.DataFrame(thresholds)

    # Pivot to get tier columns for easier comparison
    if not result.empty:
        pivot = result.pivot_table(
            index=['property_type', 'period'],
            columns='tier',
            values='median_price'
        ).reset_index()
        pivot.columns.name = None
        pivot = pivot.rename(columns={
            'Mass Market': 'mass_market_median',
            'Mid-Tier': 'mid_tier_median',
            'Luxury': 'luxury_median'
        })
        result = result.merge(pivot, on=['property_type', 'period'], how='left')

    logger.info(f"Created tier thresholds with {len(result):,} rows")
    return result


def create_planning_area_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Create planning area metrics table.

    Args:
        df: Full transaction DataFrame

    Returns:
        Aggregated metrics by planning_area
    """
    logger.info("Creating planning area metrics table...")

    if df.empty or 'planning_area' not in df.columns:
        return pd.DataFrame()

    metrics = df.groupby('planning_area').agg({
        'price': ['count', 'median', 'mean'],
        'price_psf': ['median', 'mean'] if 'price_psf' in df.columns else 'count',
        'rental_yield_pct': ['median', 'mean'] if 'rental_yield_pct' in df.columns else 'count',
    }).reset_index()

    # Flatten column names
    metrics.columns = [
        '_'.join(col).strip('_') if isinstance(col, tuple) else col
        for col in metrics.columns
    ]

    # Add amenity accessibility scores if available
    amenity_distance_cols = [col for col in df.columns if col.startswith('dist_to_nearest_')]
    if amenity_distance_cols:
        amenity_means = df.groupby('planning_area')[amenity_distance_cols].mean().reset_index()
        # Rename amenity columns to include _avg suffix
        rename_cols = {col: f'{col}_avg' for col in amenity_means.columns if col != 'planning_area'}
        amenity_means = amenity_means.rename(columns=rename_cols)
        metrics = metrics.merge(amenity_means, on='planning_area', how='left')

    # Add period breakdown
    if 'period_5yr' in df.columns:
        pa_period_counts = df.groupby(['planning_area', 'period_5yr']).size().unstack(fill_value=0)
        pa_period_counts.columns = [f'transactions_{col}' for col in pa_period_counts.columns]
        pa_period_counts = pa_period_counts.reset_index()
        metrics = metrics.merge(pa_period_counts, on='planning_area', how='left')

    metrics = metrics.rename(columns={'price_count': 'transaction_count'})
    metrics = metrics.sort_values('transaction_count', ascending=False)

    logger.info(f"Created planning area metrics with {len(metrics):,} rows")
    return metrics


def create_lease_decay_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Create lease decay statistics table for HDB properties.

    Args:
        df: Full transaction DataFrame

    Returns:
        Price statistics by lease band
    """
    logger.info("Creating lease decay statistics...")

    if df.empty:
        return pd.DataFrame()

    # Filter to HDB with remaining lease
    hdb_df = df[df['property_type'] == 'HDB'].copy()

    if 'remaining_lease_months' not in hdb_df.columns and 'remaining_lease_years' not in hdb_df.columns:
        logger.warning("No remaining lease data found, skipping lease decay stats")
        return pd.DataFrame()

    # Convert to years if needed
    if 'remaining_lease_months' in hdb_df.columns and 'remaining_lease_years' not in hdb_df.columns:
        hdb_df['remaining_lease_years'] = hdb_df['remaining_lease_months'] / 12

    if 'remaining_lease_years' not in hdb_df.columns:
        return pd.DataFrame()

    # Create lease bands
    hdb_df['lease_band'] = pd.cut(
        hdb_df['remaining_lease_years'],
        bins=[0, 60, 70, 80, 90, 100],
        labels=['<60 years', '60-70 years', '70-80 years', '80-90 years', '90+ years']
    )

    # Calculate statistics
    stats = hdb_df.groupby('lease_band', observed=True).agg({
        'price': ['count', 'median', 'mean', 'min', 'max'],
        'price_psf': ['median', 'mean'] if 'price_psf' in hdb_df.columns else 'count',
    }).reset_index()

    stats.columns = ['lease_band', 'transaction_count', 'median_price', 'mean_price', 'min_price', 'max_price', 'median_psf', 'mean_psf']

    # Calculate discount to baseline (90+ years)
    baseline_median = stats[stats['lease_band'] == '90+ years']['median_price'].values
    if len(baseline_median) > 0:
        baseline = baseline_median[0]
        stats['discount_to_baseline_pct'] = ((baseline - stats['median_price']) / baseline * 100).round(1)
        stats['annual_decay_pct'] = (stats['discount_to_baseline_pct'] / (99 - stats['lease_band'].astype(str).str.extract(r'(\d+)')[0].astype(float))).round(2)

    logger.info(f"Created lease decay stats with {len(stats):,} rows")
    return stats


def create_rental_yield_top_combos(df: pd.DataFrame) -> pd.DataFrame:
    """Create top rental yield combinations table.

    Args:
        df: Full transaction DataFrame

    Returns:
        Top rental yield combos by town and flat_type
    """
    logger.info("Creating rental yield top combinations...")

    if df.empty or 'rental_yield_pct' not in df.columns:
        return pd.DataFrame()

    rental_df = df[df['rental_yield_pct'].notna()].copy()

    if rental_df.empty:
        return pd.DataFrame()

    # Town + flat type combinations
    if 'flat_type' in rental_df.columns and 'town' in rental_df.columns:
        combos = rental_df.groupby(['town', 'flat_type']).agg({
            'rental_yield_pct': ['median', 'mean', 'count'],
            'price': ['median', 'mean'],
        }).reset_index()

        combos.columns = ['town', 'flat_type', 'yield_median', 'yield_mean', 'yield_count', 'price_median', 'price_mean']

        # Calculate estimated monthly rent
        combos['monthly_rent_est'] = (combos['price_median'] * combos['yield_median'] / 100 / 12).round(0)

        combos = combos.sort_values('yield_median', ascending=False)
        combos['rank'] = range(1, len(combos) + 1)

        logger.info(f"Created {len(combos)} rental yield combinations")
        return combos

    # Town only
    if 'town' in rental_df.columns:
        town_yields = rental_df.groupby('town').agg({
            'rental_yield_pct': ['median', 'mean', 'count'],
            'price': ['median', 'mean'],
        }).reset_index()

        town_yields.columns = ['town', 'yield_median', 'yield_mean', 'yield_count', 'price_median', 'price_mean']
        town_yields = town_yields.sort_values('yield_median', ascending=False)
        town_yields['rank'] = range(1, len(town_yields) + 1)

        logger.info(f"Created {len(town_yields)} town rental yields")
        return town_yields

    return pd.DataFrame()


def save_precomputed_tables(
    market_summary: pd.DataFrame,
    tier_thresholds: pd.DataFrame,
    pa_metrics: pd.DataFrame,
    lease_decay: pd.DataFrame,
    rental_combos: pd.DataFrame,
    l3_dir: Path
) -> None:
    """Save all precomputed tables to parquet.

    Args:
        market_summary: Market summary table
        tier_thresholds: Tier thresholds evolution
        pa_metrics: Planning area metrics
        lease_decay: Lease decay statistics
        rental_combos: Rental yield combinations
        l3_dir: Output directory
    """
    logger.info("Saving precomputed tables...")

    tables = {
        'market_summary': market_summary,
        'tier_thresholds_evolution': tier_thresholds,
        'planning_area_metrics': pa_metrics,
        'lease_decay_stats': lease_decay,
        'rental_yield_top_combos': rental_combos,
    }

    for name, table in tables.items():
        if not table.empty:
            output_path = l3_dir / f"{name}.parquet"
            table.to_parquet(output_path, compression='snappy', index=False)
            logger.info(f"  Saved {name}: {len(table):,} rows -> {output_path}")
        else:
            logger.warning(f"  Skipping {name}: empty DataFrame")


# ============================================================================
# OPTIONAL EXPORT FUNCTIONS
# ============================================================================

def upload_to_s3(df: pd.DataFrame, key: str, bucket: Optional[str] = None) -> bool:
    """Upload DataFrame to S3.

    Args:
        df: DataFrame to upload
        key: S3 key (path)
        bucket: S3 bucket name (defaults to Config.S3_BUCKET)

    Returns:
        True if upload successful
    """
    if bucket is None:
        bucket = Config.S3_BUCKET

    if not bucket:
        logger.warning("S3_BUCKET not configured, skipping upload")
        return False

    try:
        import boto3
        from io import BytesIO

        s3_client = boto3.client("s3")

        buffer = BytesIO()
        df.to_parquet(buffer, compression="snappy", index=False)
        buffer.seek(0)

        s3_client.put_object(
            Bucket=bucket, Key=key, Body=buffer.getvalue(), ContentType="application/parquet"
        )

        logger.info(f"✅ Uploaded to s3://{bucket}/{key}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to upload to S3: {e}")
        return False


def export_to_csv(df: pd.DataFrame, filename: str, output_dir: Optional[Path] = None) -> Path:
    """Export DataFrame to CSV.

    Args:
        df: DataFrame to export
        filename: Output filename
        output_dir: Output directory (defaults to Config.DATA_DIR / 'exports')

    Returns:
        Path to exported file
    """
    if output_dir is None:
        output_dir = Config.DATA_DIR / "exports"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    df.to_csv(output_path, index=False)
    logger.info(f"✅ Exported to {output_path}")

    return output_path


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_l3_pipeline(
    upload_s3: bool = False,
    export_csv: bool = False,
    s3_bucket: Optional[str] = None
) -> Dict:
    """Run complete L3 unified dataset creation and export pipeline.

    Args:
        upload_s3: Whether to upload unified dataset to S3
        export_csv: Whether to export unified dataset to CSV
        s3_bucket: S3 bucket name (defaults to Config.S3_BUCKET)

    Returns:
        Dictionary with pipeline results
    """
    logger.info("=" * 60)
    logger.info("L3 Unified Dataset Creation Pipeline")
    logger.info("=" * 60)

    results = {}

    # Load data
    hdb_df = load_hdb_transactions()
    condo_df = load_condo_transactions()
    ec_df = load_ec_transactions()
    geo_df = load_geocoded_properties()
    amenity_df = load_amenity_features()
    rental_yield_df = load_rental_yield()
    metrics_df = load_precomputed_metrics()
    planning_areas_gdf = load_planning_areas()

    # Check if we have any data
    if hdb_df.empty and condo_df.empty and ec_df.empty:
        logger.error("No transaction data available. Exiting.")
        return results

    # Standardize data
    standardized_dfs = []

    if not hdb_df.empty:
        hdb_standardized = standardize_hdb_data(hdb_df)
        standardized_dfs.append(hdb_standardized)

    if not condo_df.empty:
        condo_standardized = standardize_condo_data(condo_df)
        standardized_dfs.append(condo_standardized)

    if not ec_df.empty:
        ec_standardized = standardize_ec_data(ec_df)
        standardized_dfs.append(ec_standardized)

    # Combine HDB, Condo, and EC
    combined = pd.concat(standardized_dfs, ignore_index=True)
    logger.info(f"Combined {len(combined):,} total transactions")

    # Merge with geocoding
    combined = merge_with_geocoding(combined, geo_df)

    # Add planning areas
    combined = add_planning_area(combined, planning_areas_gdf)

    # Add amenity features
    combined = add_amenity_features(combined, amenity_df)

    # Merge rental yield
    combined = merge_rental_yield(combined, rental_yield_df)

    # Merge precomputed metrics
    combined = merge_precomputed_metrics(combined, metrics_df)

    # Add period-dependent market segmentation
    combined = add_period_segmentation(combined)

    # Add school distance features
    logger.info("=" * 60)
    logger.info("Adding School Distance Features")
    logger.info("=" * 60)
    try:
        schools_df = load_schools()
        logger.info(f"Loaded {len(schools_df)} schools")

        # Only process properties that have coordinates
        combined_with_coords = combined.dropna(subset=['lat', 'lon'])
        if not combined_with_coords.empty:
            combined = calculate_school_features(combined, schools_df)
            logger.info("✅ School features added successfully")
        else:
            logger.warning("No properties with coordinates found, skipping school features")
    except Exception as e:
        logger.warning(f"Failed to add school features: {e}")
        logger.info("Continuing without school features...")

    # Filter to successfully geocoded properties
    if 'lat' in combined.columns and 'lon' in combined.columns:
        before_count = len(combined)
        combined = combined.dropna(subset=['lat', 'lon'])
        after_count = len(combined)
        logger.info(f"Filtered to {after_count:,} geocoded properties (removed {before_count - after_count:,} without coordinates)")

    # Select final columns
    final_df = filter_final_columns(combined)

    # Create L3 directory
    l3_dir = Config.PARQUETS_DIR / "L3"
    l3_dir.mkdir(exist_ok=True)

    # Save main unified dataset
    output_path = l3_dir / "housing_unified.parquet"
    final_df.to_parquet(output_path, compression='snappy', index=False)
    logger.info(f"Saved unified dataset to {output_path}")
    results['unified'] = len(final_df)

    # Optional: Upload to S3
    if upload_s3:
        upload_to_s3(final_df, "unified/l3_housing_unified.parquet", bucket=s3_bucket)

    # Optional: Export to CSV
    if export_csv:
        export_to_csv(final_df, "l3_housing_unified.csv")

    # ============================================================================
    # PRECOMPUTE SUMMARY TABLES
    # ============================================================================
    logger.info("=" * 60)
    logger.info("Creating Precomputed Summary Tables")
    logger.info("=" * 60)

    market_summary = create_market_summary(final_df)
    tier_thresholds = create_tier_thresholds_evolution(final_df)
    pa_metrics = create_planning_area_metrics(final_df)
    lease_decay = create_lease_decay_stats(final_df)
    rental_combos = create_rental_yield_top_combos(final_df)

    save_precomputed_tables(
        market_summary, tier_thresholds, pa_metrics, lease_decay, rental_combos, l3_dir
    )

    results['market_summary'] = len(market_summary)
    results['tier_thresholds'] = len(tier_thresholds)
    results['planning_area_metrics'] = len(pa_metrics)
    results['lease_decay_stats'] = len(lease_decay)
    results['rental_yield_combos'] = len(rental_combos)

    logger.info("=" * 60)
    logger.info("Precomputed tables created successfully!")
    logger.info("=" * 60)

    # Print summary
    logger.info("=" * 60)
    logger.info("Dataset Summary")
    logger.info("=" * 60)
    logger.info(f"Total records: {len(final_df):,}")
    logger.info(f"Total columns: {len(final_df.columns)}")
    logger.info(f"Date range: {final_df['transaction_date'].min()} to {final_df['transaction_date'].max()}")

    if 'property_type' in final_df.columns:
        for ptype, count in final_df['property_type'].value_counts().items():
            logger.info(f"  {ptype}: {count:,} records")

    if 'planning_area' in final_df.columns:
        pa_coverage = final_df['planning_area'].notna().sum()
        logger.info(f"Planning area coverage: {pa_coverage:,} of {len(final_df):,} ({pa_coverage/len(final_df)*100:.1f}%)")

    if 'price' in final_df.columns:
        logger.info(f"Price range: ${final_df['price'].min():,.0f} to ${final_df['price'].max():,.0f}")
        logger.info(f"Median price: ${final_df['price'].median():,.0f}")

    # New feature coverage
    if 'rental_yield_pct' in final_df.columns:
        ry_coverage = final_df['rental_yield_pct'].notna().sum()
        logger.info(f"Rental yield coverage: {ry_coverage:,} of {len(final_df):,} ({ry_coverage/len(final_df)*100:.1f}%)")

    amenity_distance_cols = [col for col in final_df.columns if col.startswith('dist_to_nearest_')]
    if amenity_distance_cols:
        logger.info(f"Amenity distance features: {len(amenity_distance_cols)} columns")

    amenity_count_cols = [col for col in final_df.columns if col.endswith('_within_500m') or col.endswith('_within_1km') or col.endswith('_within_2km')]
    if amenity_count_cols:
        logger.info(f"Amenity count features: {len(amenity_count_cols)} columns")

    metric_cols = [col for col in final_df.columns if col in ['stratified_median_price', 'mom_change_pct', 'momentum_signal']]
    if metric_cols:
        logger.info(f"Precomputed metrics: {len(metric_cols)} columns")

    # Precomputed summary tables summary
    logger.info("-" * 60)
    logger.info("Precomputed Summary Tables:")
    if not market_summary.empty:
        logger.info(f"  - market_summary: {len(market_summary):,} rows (by property_type/period/tier)")
    if not tier_thresholds.empty:
        logger.info(f"  - tier_thresholds_evolution: {len(tier_thresholds):,} rows")
    if not pa_metrics.empty:
        logger.info(f"  - planning_area_metrics: {len(pa_metrics):,} rows")
    if not lease_decay.empty:
        logger.info(f"  - lease_decay_stats: {len(lease_decay):,} rows")
    if not rental_combos.empty:
        logger.info(f"  - rental_yield_top_combos: {len(rental_combos):,} rows")

    logger.info("=" * 60)
    logger.info("Pipeline completed successfully!")
    logger.info("=" * 60)

    return results


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run L3 unified dataset creation pipeline")
    parser.add_argument("--upload-s3", action="store_true", help="Upload unified dataset to S3")
    parser.add_argument("--export-csv", action="store_true", help="Export unified dataset to CSV")
    parser.add_argument("--s3-bucket", type=str, help="S3 bucket name")

    args = parser.parse_args()
    run_l3_pipeline(upload_s3=args.upload_s3, export_csv=args.export_csv, s3_bucket=args.s3_bucket)


if __name__ == "__main__":
    main()
