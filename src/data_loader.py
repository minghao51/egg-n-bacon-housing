"""
Data loading utilities for Singapore Housing Price Visualization.

This module provides optimized data loading functions with caching
for HDB, Condo, and amenity data.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from shapely.geometry import Point, shape

# Constants
DATA_DIR = Path("data/parquets")
RAW_DATA_DIR = Path("data/raw_data")
SINGAPORE_CENTER = {"lat": 1.3521, "lon": 103.8198}


# Global cache for planning areas
_planning_areas = None


def load_planning_areas() -> list[dict]:
    """
    Load Singapore planning area polygons from GeoJSON.

    Returns:
        List of planning areas with properties and geometry
    """
    global _planning_areas

    if _planning_areas is not None:
        return _planning_areas

    geojson_path = RAW_DATA_DIR / "onemap_planning_area_polygon.geojson"

    if not geojson_path.exists():
        st.warning(f"Planning area GeoJSON not found at {geojson_path}")
        _planning_areas = []
        return _planning_areas

    try:
        with open(geojson_path) as f:
            geojson_data = json.load(f)

        # Extract features and convert geometries to shapely objects
        planning_areas = []
        for feature in geojson_data.get('features', []):
            props = feature.get('properties', {})
            geom = feature.get('geometry')

            planning_areas.append({
                'name': props.get('pln_area_n', 'Unknown'),
                'geometry': shape(geom) if geom else None
            })

        _planning_areas = planning_areas
        return _planning_areas

    except Exception as e:
        st.warning(f"Error loading planning areas: {e}")
        _planning_areas = []
        return _planning_areas


def get_planning_area_for_point(lat: float, lon: float) -> str | None:
    """
    Get the planning area name for a given lat/lon coordinate.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Planning area name or None if not found
    """
    planning_areas = load_planning_areas()

    if not planning_areas:
        return None

    point = Point(lon, lat)

    for area in planning_areas:
        if area['geometry'] and area['geometry'].contains(point):
            return area['name']

    return None


@st.cache_data(ttl=3600)
def load_hdb_resale() -> pd.DataFrame:
    """
    Load HDB resale transaction data.

    Returns:
        DataFrame with HDB transactions including:
        - month, town, flat_type, street_name
        - floor_area_sqm, lease_commence_date
        - resale_price, remaining_lease_months
    """
    # Try both possible file names
    path1 = DATA_DIR / "L1" / "housing_hdb_transaction.parquet"
    path2 = DATA_DIR / "L1" / "hdb_resale.parquet"

    path = path1 if path1.exists() else path2

    if not path.exists():
        st.warning(f"HDB data not found at {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Convert month to datetime
    if 'month' in df.columns:
        df['month'] = pd.to_datetime(df['month'])

    # Calculate price per sqm if not present
    if 'price_psm' not in df.columns and 'resale_price' in df.columns and 'floor_area_sqm' in df.columns:
        df['price_psm'] = df['resale_price'] / df['floor_area_sqm']
        df['price_psf'] = df['price_psm'] * 0.092903  # Convert to sqft

    return df


@st.cache_data(ttl=3600)
def load_condo_data() -> pd.DataFrame:
    """
    Load Condo transaction data from URA.

    Returns:
        DataFrame with condo transactions including:
        - Project Name, Transacted Price ($)
        - Area (SQFT), Unit Price ($ PSF)
        - Sale Date, Street Name, Property Type
        - Postal District, Market Segment
    """
    # Try both possible file names
    path1 = DATA_DIR / "L1" / "housing_condo_transaction.parquet"
    path2 = DATA_DIR / "L1" / "condo_ura.parquet"

    path = path1 if path1.exists() else path2

    if not path.exists():
        st.warning(f"Condo data not found at {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Clean numeric columns stored as strings (remove commas and convert to float)
    string_numeric_cols = [
        'Transacted Price ($)',
        'Area (SQFT)',
        'Unit Price ($ PSF)',
        'Unit Price ($ PSM)'
    ]

    for col in string_numeric_cols:
        if col in df.columns:
            # Remove commas and convert to numeric
            df[col] = df[col].astype(str).str.replace(',', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Handle Nett Price($) column which may have '-' values
    if 'Nett Price($)' in df.columns:
        df['Nett Price($)'] = pd.to_numeric(df['Nett Price($)'], errors='coerce')

    # Convert sale date to datetime
    # Format: 'Jan-23' -> January 2023 (not year 23 AD)
    if 'Sale Date' in df.columns:
        df['sale_date'] = pd.to_datetime(df['Sale Date'], format='%b-%y', errors='coerce')

    return df


@st.cache_data(ttl=3600)
def load_geocoded_properties() -> pd.DataFrame:
    """
    Load geocoded unique properties with coordinates.

    Returns:
        DataFrame with property locations:
        - NameAddress, BLK_NO, ROAD_NAME, ADDRESS
        - POSTAL, LATITUDE, LONGITUDE
        - property_type
    """
    path = DATA_DIR / "L2" / "housing_unique_searched.parquet"

    if not path.exists():
        st.warning(f"Geocoded properties not found at {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Standardize coordinate column names
    if 'LATITUDE' in df.columns and 'LONGITUDE' in df.columns:
        df['lat'] = df['LATITUDE']
        df['lon'] = df['LONGITUDE']

    # Convert coordinates to numeric if they're strings
    if 'lat' in df.columns:
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    if 'lon' in df.columns:
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    # Filter out invalid coordinates
    if 'lat' in df.columns and 'lon' in df.columns:
        df = df[
            (df['lat'].between(1.2, 1.5)) &
            (df['lon'].between(103.6, 104.0))
        ]

    return df


@st.cache_data(ttl=3600)
def load_amenity_features() -> pd.DataFrame:
    """
    Load amenity distance features for properties.

    Returns:
        DataFrame with amenity distances:
        - dist_to_nearest_mrt, hawker, supermarket, etc.
        - amenity counts within radius (500m, 1km, 2km)
    """
    path = DATA_DIR / "L2" / "amenity_features.parquet"

    if not path.exists():
        st.warning(f"Amenity features not found at {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    return df


@st.cache_data(ttl=3600)
def load_amenity_locations() -> pd.DataFrame:
    """
    Load raw amenity locations for map overlay.

    Returns:
        DataFrame with amenity coordinates:
        - name, amenity_type, lat, lon
    """
    path = DATA_DIR / "L1" / "amenity_v2.parquet"

    if not path.exists():
        st.warning(f"Amenity locations not found at {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Standardize column names
    if 'LATITUDE' in df.columns and 'LONGITUDE' in df.columns:
        df['lat'] = df['LATITUDE']
        df['lon'] = df['LONGITUDE']
    elif 'latitude' in df.columns and 'longitude' in df.columns:
        df['lat'] = df['latitude']
        df['lon'] = df['longitude']

    # Standardize amenity type
    if 'type' in df.columns:
        df['amenity_type'] = df['type']

    return df


@st.cache_data(ttl=3600)
def geocode_condo_properties(
    condo_df: pd.DataFrame,
    geo_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Geocode condo properties by fuzzy matching with geo data.

    Args:
        condo_df: Condo transactions with 'Project Name' and 'Street Name'
        geo_df: Geocoded properties with coordinates

    Returns:
        condo_df with added 'lat' and 'lon' columns
    """
    if condo_df.empty or geo_df.empty:
        return condo_df

    # Prepare geo data for matching - filter to private properties only
    geo_private = geo_df[geo_df['property_type'] == 'private'].copy()
    if geo_private.empty:
        return condo_df

    # Take one coordinate per unique road name (use first occurrence)
    geo_private = geo_private.drop_duplicates(subset=['ROAD_NAME'], keep='first')
    geo_private['road_name_upper'] = geo_private['ROAD_NAME'].str.upper()

    # Try exact street name match first
    condo_df = condo_df.copy()
    condo_df['street_name_upper'] = condo_df['Street Name'].str.upper()

    # Merge on street name to get coordinates
    merged = pd.merge(
        condo_df[['street_name_upper']],
        geo_private[['road_name_upper', 'LATITUDE', 'LONGITUDE']],
        left_on='street_name_upper',
        right_on='road_name_upper',
        how='left'
    )

    # Assign coordinates back to original dataframe using index alignment
    condo_df['lat'] = merged['LATITUDE'].values
    condo_df['lon'] = merged['LONGITUDE'].values

    # Filter to successfully geocoded properties
    geo_count = condo_df['lat'].notna().sum()
    total_count = len(condo_df)

    if geo_count > 0:
        st.info(f"📍 Geocoded {geo_count:,} of {total_count:,} condo properties ({geo_count/total_count*100:.1f}%)")
    else:
        st.warning("⚠️ Could not geocode any condo properties. They won't appear on the map.")

    return condo_df


@st.cache_data(ttl=3600)
def load_unified_data() -> pd.DataFrame:
    """
    Load pre-computed unified dataset from L3.

    This dataset combines HDB and Condo transactions with standardized columns,
    geocoding, and amenity features. It's the recommended way to load data for
    the Streamlit app.

    Returns:
        DataFrame with unified schema:
        - property_type: 'HDB' or 'Condominium'
        - transaction_date: Transaction date (datetime)
        - price: Unified price column (float)
        - floor_area_sqft / floor_area_sqm: Floor area in both units
        - price_psf / price_psm: Price per square foot/meter
        - lat / lon: Coordinates
        - town: Town or area name
        - address: Property address
        - Plus other original columns and amenity features
    """
    path = DATA_DIR / "L3" / "housing_unified.parquet"

    if not path.exists():
        st.error(f"Unified dataset not found at {path}")
        st.info(
            "Please run the following command to create the L3 unified dataset:\n"
            "`uv run python scripts/create_l3_unified_dataset.py`"
        )
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Convert lat/lon to numeric if stored as strings
    if 'lat' in df.columns and df['lat'].dtype == 'object':
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    if 'lon' in df.columns and df['lon'].dtype == 'object':
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    # Convert transaction_date to datetime if needed
    if 'transaction_date' in df.columns and df['transaction_date'].dtype != 'datetime64[ns]':
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])

    st.info(f"📊 Loaded {len(df):,} properties from unified dataset")

    return df


@st.cache_data(ttl=3600)
def load_combined_data() -> pd.DataFrame:
    """
    Load and combine HDB + Condo data with geocoding.

    Returns:
        Combined DataFrame with all transactions and coordinates
    """
    hdb_df = load_hdb_resale()
    condo_df = load_condo_data()
    geo_df = load_geocoded_properties()

    if hdb_df.empty and condo_df.empty:
        return pd.DataFrame()

    # Add property type
    if not hdb_df.empty:
        hdb_df['property_type'] = 'HDB'
        hdb_df['address'] = hdb_df['block'] + ' ' + hdb_df['street_name']

    if not condo_df.empty:
        condo_df['property_type'] = 'Condominium'
        if 'Street Name' in condo_df.columns:
            condo_df['address'] = condo_df['Project Name'] + ', ' + condo_df['Street Name']

            # Assign town based on street name (use "Condo - [Street Name]" format)
            # If coordinates are available after geocoding, this will be used
            condo_df['town'] = 'Condo - ' + condo_df['Street Name']

    # Merge transactions with geocoded data
    if not geo_df.empty:
        # Try to merge on postal code or address
        if not hdb_df.empty:
            hdb_df = pd.merge(
                hdb_df,
                geo_df[['BLK_NO', 'ROAD_NAME', 'lat', 'lon', 'POSTAL']],
                left_on=['block', 'street_name'],
                right_on=['BLK_NO', 'ROAD_NAME'],
                how='left'
            )

        if not condo_df.empty:
            # Geocode condos using fuzzy address matching
            condo_df = geocode_condo_properties(condo_df, geo_df)

    # Combine
    combined_df = pd.concat([hdb_df, condo_df], ignore_index=True)

    # Standardize floor area column (convert to sqft)
    if 'floor_area_sqm' in combined_df.columns:
        combined_df['floor_area_sqft'] = combined_df['floor_area_sqm'] * 10.764
    elif 'Area (SQFT)' in combined_df.columns:
        combined_df['floor_area_sqft'] = combined_df['Area (SQFT)']

    # Filter out rows without coordinates
    if 'lat' in combined_df.columns:
        combined_df = combined_df.dropna(subset=['lat', 'lon'])

    # Assign planning areas based on coordinates
    if 'lat' in combined_df.columns and 'lon' in combined_df.columns:
        with st.spinner("Assigning planning areas..."):
            planning_areas_list = []
            for _, row in combined_df.iterrows():
                pa = get_planning_area_for_point(row['lat'], row['lon'])
                planning_areas_list.append(pa)

            combined_df['planning_area'] = planning_areas_list

            # Replace NaN planning areas with "Unknown"
            combined_df['planning_area'] = combined_df['planning_area'].fillna('Unknown')

            pa_count = (combined_df['planning_area'] != 'Unknown').sum()
            st.info(f"📍 Assigned planning areas to {pa_count:,} of {len(combined_df):,} properties")

    # Fill any remaining NaN towns with "NA" (shouldn't happen with above logic)
    if 'town' in combined_df.columns:
        combined_df['town'] = combined_df['town'].fillna('NA')

    return combined_df


def get_unified_filter_options(df: pd.DataFrame) -> dict:
    """
    Extract filter options from unified dataset.

    Args:
        df: Unified property data from L3

    Returns:
        Dictionary with filter options for:
        - towns, property_types, date_range
    """
    if df.empty:
        return {}

    options = {
        'property_types': sorted(df['property_type'].unique()) if 'property_type' in df.columns else [],
        'towns': sorted(df['town'].unique()) if 'town' in df.columns else [],
    }

    # Date range from transaction_date column
    if 'transaction_date' in df.columns:
        options['date_range'] = (
            df['transaction_date'].min().to_pydatetime(),
            df['transaction_date'].max().to_pydatetime()
        )

    return options


def apply_unified_filters(
    df: pd.DataFrame,
    property_types: list[str] | None = None,
    towns: list[str] | None = None,
    price_range: tuple[int, int] | None = None,
    date_range: tuple[datetime, datetime] | None = None,
    floor_area_range: tuple[int, int] | None = None
) -> pd.DataFrame:
    """
    Apply filters to unified property data.

    Uses standardized column names from L3 unified dataset.

    Args:
        df: Unified property data from L3
        property_types: List of property types to include
        towns: List of towns to include
        price_range: Tuple of (min_price, max_price)
        date_range: Tuple of (start_date, end_date)
        floor_area_range: Tuple of (min_area, max_area) in sqft

    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()

    # Property type filter
    if property_types and 'property_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['property_type'].isin(property_types)]

    # Town filter
    if towns and 'town' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['town'].isin(towns)]

    # Price filter (unified 'price' column)
    if price_range and 'price' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['price'].between(price_range[0], price_range[1]))
        ]

    # Date filter (transaction_date column)
    if date_range and 'transaction_date' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['transaction_date'].between(date_range[0], date_range[1]))
        ]

    # Floor area filter (floor_area_sqft column)
    if floor_area_range and 'floor_area_sqft' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['floor_area_sqft'].between(floor_area_range[0], floor_area_range[1]))
        ]

    return filtered_df


def get_unified_data_summary(df: pd.DataFrame) -> dict:
    """
    Get summary statistics for unified data.

    Args:
        df: Unified property data from L3

    Returns:
        Dictionary with summary stats using standardized column names
    """
    if df.empty:
        return {}

    summary = {
        'total_records': len(df),
        'property_types': df['property_type'].value_counts().to_dict() if 'property_type' in df.columns else {},
    }

    # Date range from transaction_date
    if 'transaction_date' in df.columns:
        summary['date_range'] = (
            df['transaction_date'].min().strftime('%Y-%m'),
            df['transaction_date'].max().strftime('%Y-%m')
        )

    # Price statistics (unified 'price' column)
    if 'price' in df.columns:
        summary['price_stats'] = {
            'median': df['price'].median(),
            'mean': df['price'].mean(),
            'min': df['price'].min(),
            'max': df['price'].max()
        }

    return summary


def get_filter_options(df: pd.DataFrame) -> dict:
    """
    Extract filter options from dataset.

    Args:
        df: Combined property data

    Returns:
        Dictionary with filter options for:
        - towns, planning_areas, property_types, date_range
    """
    if df.empty:
        return {}

    options = {
        'property_types': sorted(df['property_type'].unique()) if 'property_type' in df.columns else [],
        'towns': sorted(df['town'].unique()) if 'town' in df.columns else [],
        'date_range': (
            df['month'].min().to_pydatetime() if 'month' in df.columns else datetime(2015, 1, 1),
            df['month'].max().to_pydatetime() if 'month' in df.columns else datetime.now()
        )
    }

    return options


def apply_filters(
    df: pd.DataFrame,
    property_types: list[str] | None = None,
    towns: list[str] | None = None,
    planning_areas: list[str] | None = None,
    price_range: tuple[int, int] | None = None,
    date_range: tuple[datetime, datetime] | None = None,
    floor_area_range: tuple[int, int] | None = None
) -> pd.DataFrame:
    """
    Apply filters to property data.

    Args:
        df: Combined property data
        property_types: List of property types to include
        towns: List of towns to include (deprecated, use planning_areas)
        planning_areas: List of planning areas to include
        price_range: Tuple of (min_price, max_price)
        date_range: Tuple of (start_date, end_date)
        floor_area_range: Tuple of (min_area, max_area) in sqft

    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()

    # Property type filter
    if property_types and 'property_type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['property_type'].isin(property_types)]

    # Town filter
    if towns and 'town' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['town'].isin(towns)]

    # Planning area filter
    if planning_areas and 'planning_area' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['planning_area'].isin(planning_areas)]

    # Price filter
    if price_range:
        price_col = 'resale_price' if 'resale_price' in filtered_df.columns else 'Transacted Price ($)'
        if price_col in filtered_df.columns and filtered_df[price_col].notna().any():
            filtered_df = filtered_df[
                (filtered_df[price_col].between(price_range[0], price_range[1]))
            ]

    # Date filter - handle both HDB 'month' and Condo 'sale_date' columns
    if date_range:
        date_mask = pd.Series(False, index=filtered_df.index)
        if 'month' in filtered_df.columns:
            date_mask |= filtered_df['month'].between(date_range[0], date_range[1])
        if 'sale_date' in filtered_df.columns:
            date_mask |= filtered_df['sale_date'].between(date_range[0], date_range[1])
        filtered_df = filtered_df[date_mask]

    # Floor area filter - now uses standardized floor_area_sqft column
    if floor_area_range and 'floor_area_sqft' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['floor_area_sqft'].between(floor_area_range[0], floor_area_range[1]))
        ]

    return filtered_df


def get_data_summary(df: pd.DataFrame) -> dict:
    """
    Get summary statistics for the data.

    Args:
        df: Property data

    Returns:
        Dictionary with summary stats
    """
    if df.empty:
        return {}

    summary = {
        'total_records': len(df),
        'property_types': df['property_type'].value_counts().to_dict() if 'property_type' in df.columns else {},
        'date_range': (
            df['month'].min().strftime('%Y-%m') if 'month' in df.columns else 'N/A',
            df['month'].max().strftime('%Y-%m') if 'month' in df.columns else 'N/A'
        )
    }

    # Price statistics
    price_col = 'resale_price' if 'resale_price' in df.columns else 'Transacted Price ($)'
    if price_col in df.columns:
        summary['price_stats'] = {
            'median': df[price_col].median(),
            'mean': df[price_col].mean(),
            'min': df[price_col].min(),
            'max': df[price_col].max()
        }

    return summary


# ============================================================================
# PRECOMPUTED SUMMARY TABLE LOADERS
# ============================================================================

@st.cache_data(ttl=3600)
def load_market_summary() -> pd.DataFrame:
    """
    Load precomputed market summary table.

    Returns:
        DataFrame with aggregated stats by property_type, period_5yr, market_tier_period
    """
    path = DATA_DIR / "L3" / "market_summary.parquet"

    if not path.exists():
        st.warning(f"Market summary not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


@st.cache_data(ttl=3600)
def load_tier_thresholds() -> pd.DataFrame:
    """
    Load precomputed tier thresholds evolution table.

    Returns:
        DataFrame with tier price thresholds by period and property_type
    """
    path = DATA_DIR / "L3" / "tier_thresholds_evolution.parquet"

    if not path.exists():
        st.warning(f"Tier thresholds not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


@st.cache_data(ttl=3600)
def load_planning_area_metrics() -> pd.DataFrame:
    """
    Load precomputed planning area metrics table.

    Returns:
        DataFrame with aggregated metrics by planning_area
    """
    path = DATA_DIR / "L3" / "planning_area_metrics.parquet"

    if not path.exists():
        st.warning(f"Planning area metrics not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


@st.cache_data(ttl=3600)
def load_lease_decay_stats() -> pd.DataFrame:
    """
    Load precomputed lease decay statistics.

    Returns:
        DataFrame with price statistics by lease band
    """
    path = DATA_DIR / "L3" / "lease_decay_stats.parquet"

    if not path.exists():
        st.warning(f"Lease decay stats not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


@st.cache_data(ttl=3600)
def load_rental_yield_top_combos() -> pd.DataFrame:
    """
    Load precomputed top rental yield combinations.

    Returns:
        DataFrame with town/flat_type combinations ranked by yield
    """
    path = DATA_DIR / "L3" / "rental_yield_top_combos.parquet"

    if not path.exists():
        st.warning(f"Rental yield combos not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)
