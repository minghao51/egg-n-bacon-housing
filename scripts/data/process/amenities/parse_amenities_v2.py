#!/usr/bin/env python3
"""
Improved amenity data processor with robust HTML parsing.

This script handles:
- Supermarkets (SFA) - HTML table parsing
- Preschools (ECDA) - HTML table parsing
- Parks (NParks) - Polygon centroid extraction
- Shopping Malls (Wikipedia) - Column mapping fixes

Usage:
    uv run python scripts/parse_amenities_v2.py
"""

import logging
import pathlib
import re
import sys

import geopandas as gpd
import pandas as pd

# Add project root to path
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / 'src'))

from config import Config
from data_helpers import load_parquet, save_parquet

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_html_table_value(html_string, field_name):
    """
    Extract a specific field value from HTML table description.

    Args:
        html_string: HTML string containing table
        field_name: Name of the field to extract (e.g., 'LIC_NAME', 'CENTRE_NAME')

    Returns:
        Extracted value or empty string if not found
    """
    try:
        # Find the field in the HTML table
        pattern = rf'<th>{field_name}</th>\s*<td>(.*?)</td>'
        match = re.search(pattern, html_string, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            # Remove any HTML tags within the value
            value = re.sub(r'<[^>]+>', '', value)
            return value
        return ''
    except Exception as e:
        logger.debug(f"Error extracting {field_name}: {e}")
        return ''


def parse_datagov_geojson_v2(filepath, amenity_type, name_field):
    """
    Parse GeoJSON file from data.gov.sg with improved HTML parsing.

    Args:
        filepath: Path to GeoJSON file
        amenity_type: Type of amenity (for logging)
        name_field: Field name to extract (e.g., 'LIC_NAME', 'CENTRE_NAME')

    Returns:
        DataFrame with standardized columns: name, type, lat, lon
    """
    logger.info(f"Loading {amenity_type} from {filepath.name}...")

    try:
        gdf = gpd.read_file(filepath)
    except Exception as e:
        logger.error(f"Failed to read {filepath.name}: {e}")
        return pd.DataFrame()

    # Ensure CRS is 4326
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')

    # Extract coordinates based on geometry type
    if gdf.geometry.geom_type.iloc[0] == 'Point':
        gdf['lon'] = gdf.geometry.x
        gdf['lat'] = gdf.geometry.y
    elif gdf.geometry.geom_type.iloc[0] == 'Polygon':
        # For polygons, project to SVY21 (Singapore grid) first, then get centroid
        logger.info("  Projecting polygons to SVY21 for accurate centroids...")
        gdf_projected = gdf.to_crs('EPSG:3414')  # SVY21 Singapore grid
        gdf['lon'] = gdf_projected.centroid.to_crs('EPSG:4326').x
        gdf['lat'] = gdf_projected.centroid.to_crs('EPSG:4326').y
    else:
        logger.warning(f"Unknown geometry type: {gdf.geometry.geom_type.iloc[0]}")
        return pd.DataFrame()

    # Extract names
    if 'Description' in gdf.columns and name_field:
        logger.info(f"  Extracting {name_field} from HTML tables...")
        gdf['name'] = gdf['Description'].apply(
            lambda x: extract_html_table_value(str(x), name_field)
        )
    elif 'Name' in gdf.columns:
        gdf['name'] = gdf['Name']
    elif 'NAME' in gdf.columns:
        gdf['name'] = gdf['NAME']
    else:
        logger.warning(f"No name field found for {amenity_type}")
        return pd.DataFrame()

    # Create standardized dataframe
    df = pd.DataFrame({
        'name': gdf['name'].str.lower(),
        'type': amenity_type,
        'lat': gdf['lat'].astype(float),
        'lon': gdf['lon'].astype(float)
    })

    # Drop rows with missing coordinates or empty names
    df = df.dropna(subset=['lat', 'lon'])
    df = df[df['name'] != '']
    df = df[df['name'].str.len() > 0]

    logger.info(f"✅ Loaded {len(df)} {amenity_type} locations")
    return df


def process_shopping_malls():
    """Process shopping mall data from Wikipedia."""
    logger.info("Processing shopping malls from Wikipedia...")

    try:
        mall_df = load_parquet("raw_wiki_shopping_mall")

        # Standardize column names
        if 'shopping_mall' in mall_df.columns:
            mall_df = mall_df.rename(columns={'shopping_mall': 'name'})
        elif 'Name' in mall_df.columns:
            mall_df = mall_df.rename(columns={'Name': 'name'})
        elif 'name' not in mall_df.columns:
            logger.warning(f"⚠️  Mall data has unexpected columns: {list(mall_df.columns)}")
            return pd.DataFrame()

        # Check if lat/lon columns exist
        if 'lat' not in mall_df.columns or 'lon' not in mall_df.columns:
            logger.warning("⚠️  Mall data missing lat/lon columns - needs geocoding via OneMap")
            logger.warning("⏭️  Skipping malls for now (will geocode in Phase 3)")
            return pd.DataFrame()

        # Create standardized dataframe
        df = pd.DataFrame({
            'name': mall_df['name'].str.lower(),
            'type': 'mall',
            'lat': mall_df['lat'].astype(float),
            'lon': mall_df['lon'].astype(float)
        })

        df = df.dropna(subset=['lat', 'lon'])
        df = df[df['name'] != '']

        logger.info(f"✅ Loaded {len(df)} mall locations")
        return df

    except Exception as e:
        logger.warning(f"⚠️  Mall data error: {e}")
        return pd.DataFrame()


def main():
    """Process all amenity data with improved parsing."""
    logger.info("🚀 Starting Amenity Processing v2")
    logger.info("=" * 80)

    data_base_path = Config.DATA_DIR
    datagov_path = data_base_path / 'raw_data' / 'csv' / 'datagov'

    # List to store all amenity dataframes
    amenity_dfs = []

    # 1. Supermarkets
    supermarket_path = datagov_path / 'SupermarketsGEOJSON.geojson'
    if supermarket_path.exists():
        supermarket_df = parse_datagov_geojson_v2(supermarket_path, 'supermarket', 'LIC_NAME')
        if not supermarket_df.empty:
            amenity_dfs.append(supermarket_df)
    else:
        logger.warning("⚠️  Supermarket data not found")

    # 2. Preschools
    preschool_path = datagov_path / 'PreSchoolsLocation.geojson'
    if preschool_path.exists():
        preschool_df = parse_datagov_geojson_v2(preschool_path, 'preschool', 'CENTRE_NAME')
        if not preschool_df.empty:
            amenity_dfs.append(preschool_df)
    else:
        logger.warning("⚠️  Preschool data not found")

    # 3. Parks (with centroid extraction)
    park_path = datagov_path / 'NParksParksandNatureReserves.geojson'
    if park_path.exists():
        park_df = parse_datagov_geojson_v2(park_path, 'park', 'NAME')
        if not park_df.empty:
            amenity_dfs.append(park_df)
    else:
        logger.warning("⚠️  Park data not found")

    # 4. Shopping Malls
    mall_df = process_shopping_malls()
    if not mall_df.empty:
        amenity_dfs.append(mall_df)

    # 5. Hawker Centres (already working, but include for completeness)
    hawker_path = datagov_path / 'HawkerCentresGEOJSON.geojson'
    if hawker_path.exists():
        hawker_df = parse_datagov_geojson_v2(hawker_path, 'hawker', 'NAME')
        if not hawker_df.empty:
            amenity_dfs.append(hawker_df)
    else:
        logger.warning("⚠️  Hawker centre data not found")

    # 6. MRT/LRT Stations (Phase 2)
    mrt_path = datagov_path / 'MRTStations.geojson'
    if mrt_path.exists():
        mrt_df = parse_datagov_geojson_v2(mrt_path, 'mrt', 'NAME')
        if not mrt_df.empty:
            amenity_dfs.append(mrt_df)
    else:
        logger.warning("⚠️  MRT station data not found")

    # 7. Child Care Services (Phase 2)
    childcare_path = datagov_path / 'ChildCareServices.geojson'
    if childcare_path.exists():
        childcare_df = parse_datagov_geojson_v2(childcare_path, 'childcare', 'CENTRE_NAME')
        if not childcare_df.empty:
            amenity_dfs.append(childcare_df)
    else:
        logger.warning("⚠️  Child care data not found")

    # 8. MRT Station Exits (Phase 2 - optional, more granular)
    mrt_exits_path = datagov_path / 'MRTStationExits.geojson'
    if mrt_exits_path.exists():
        mrt_exits_df = parse_datagov_geojson_v2(mrt_exits_path, 'mrt_exit', 'STATION_NAME')
        if not mrt_exits_df.empty:
            amenity_dfs.append(mrt_exits_df)
    else:
        logger.warning("⚠️  MRT exit data not found")

    # Check if we have any data
    if not amenity_dfs:
        logger.error("❌ No amenity data found! Cannot proceed.")
        return 1

    # Combine all amenity data
    logger.info("\n" + "=" * 80)
    logger.info("Combining all amenity data...")
    df_combined = pd.concat(amenity_dfs, ignore_index=True)

    # Ensure data types
    df_combined['lat'] = df_combined['lat'].astype(float)
    df_combined['lon'] = df_combined['lon'].astype(float)

    # Display summary
    logger.info(f"✅ Combined {len(df_combined):,} total amenities")
    logger.info("\nAmenity breakdown:")
    for amenity_type, count in df_combined['type'].value_counts().items():
        logger.info(f"  - {amenity_type}: {count:,}")

    # Save combined amenity dataset
    save_parquet(df_combined, "L1_amenity_v2", source="L1 utilities processing v2")
    logger.info(f"\n✅ Saved L1_amenity_v2.parquet ({len(df_combined):,} rows)")

    # Save individual geojson files for L2 processing
    data_L1_path = data_base_path / 'L1'
    data_L1_path.mkdir(parents=True, exist_ok=True)

    # Save park geojson (for spatial joins in L2)
    if park_path.exists():
        try:
            park_gdf = gpd.read_file(park_path)
            park_gdf = park_gdf.to_crs('EPSG:4326')
            park_gdf.to_file(data_L1_path / 'park.geojson', driver='GeoJSON')
            logger.info("✅ Saved park.geojson for spatial analysis")
        except Exception as e:
            logger.warning(f"⚠️  Could not save park.geojson: {e}")

    # Save park connector geojson
    pc_path = datagov_path / 'MasterPlan2019SDCPParkConnectorLinelayerGEOJSON.geojson'
    if pc_path.exists():
        try:
            pc_gdf = gpd.read_file(pc_path)
            pc_gdf.to_file(data_L1_path / 'park_connector.geojson', driver='GeoJSON')
            logger.info("✅ Saved park_connector.geojson for spatial analysis")
        except Exception as e:
            logger.warning(f"⚠️  Could not save park_connector.geojson: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ L1 Utilities Processing v2 Complete!")
    logger.info("=" * 80)
    logger.info(f"📁 Combined amenity data: {Config.PARQUETS_DIR / 'L1_amenity_v2.parquet'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
