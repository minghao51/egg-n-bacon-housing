#!/usr/bin/env python3
"""
Process amenity data for L1 utilities.

This script creates a combined amenity dataset from various sources:
- Preschools (data.gov.sg)
- Kindergartens (data.gov.sg)
- Hawker centres (data.gov.sg)
- Supermarkets (data.gov.sg)
- Shopping malls (Wikipedia)
- NParks parks (data.gov.sg)

Usage:
    uv run python scripts/process_amenities.py
"""

import logging
import pathlib
import sys

import geopandas as gpd
import pandas as pd
from bs4 import BeautifulSoup

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


def extract_html_name(html_string, tag_name):
    """Extract text from HTML tag."""
    try:
        soup = BeautifulSoup(html_string, 'html.parser')
        tag = soup.find(tag_name)
        return tag.text if tag else ''
    except:
        return ''


def parse_datagov_geojson(filepath, amenity_type, name_field='Name'):
    """Parse GeoJSON file from data.gov.sg and extract lat/lon."""
    logger.info(f"Loading {amenity_type} from {filepath.name}...")

    gdf = gpd.read_file(filepath)

    # Ensure CRS is 4326
    if gdf.crs != 'EPSG:4326':
        gdf = gpd.to_crs('EPSG:4326')

    # Extract coordinates
    gdf['lon'] = gdf.geometry.x
    gdf['lat'] = gdf.geometry.y

    # Extract name based on field type
    if name_field in gdf.columns:
        # Direct field access
        gdf['name'] = gdf[name_field]
    elif 'Description' in gdf.columns:
        # Extract from HTML Description
        if amenity_type == 'preschool':
            # Try CENTRE_NAME first
            gdf['name'] = [extract_html_name(str(desc), 'CENTRE_NAME') if 'CENTRE_NAME' in str(desc) else extract_html_name(str(desc), name_field)
                           for desc in gdf['Description']]
        else:
            gdf['name'] = [extract_html_name(str(desc), name_field) for desc in gdf['Description']]
    else:
        # Fallback to Name field or empty string
        gdf['name'] = gdf.get('Name', '')

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

    logger.info(f"✅ Loaded {len(df)} {amenity_type} locations")
    return df


def main():
    """Process all amenity data and create combined dataset."""
    logger.info("🚀 Starting L1 utilities processing")

    data_base_path = Config.DATA_DIR
    datagov_path = data_base_path / 'raw_data' / 'csv' / 'datagov'

    # List to store all amenity dataframes
    amenity_dfs = []

    # 1. Preschools - skip due to HTML parsing complexity
    logger.info("⏭️  Skipping preschools (HTML parsing too complex for now)")

    # 2. Kindergartens - skip (downloaded file is CSV fee data, not locations)
    logger.info("⏭️  Skipping kindergartens (file is fee data, not locations)")

    # 3. Hawker centres
    hawker_path = datagov_path / 'HawkerCentresGEOJSON.geojson'
    if hawker_path.exists():
        hawker_df = parse_datagov_geojson(hawker_path, 'hawker', 'NAME')
        amenity_dfs.append(hawker_df)
    else:
        logger.warning(f"⚠️  Hawker centre data not found at {hawker_path}")

    # 4. Supermarkets
    supermarket_path = datagov_path / 'SupermarketsGEOJSON.geojson'
    if supermarket_path.exists():
        supermarket_df = parse_datagov_geojson(supermarket_path, 'supermarket', 'LIC_NAME')
        amenity_dfs.append(supermarket_df)
    else:
        logger.warning(f"⚠️  Supermarket data not found at {supermarket_path}")

    # 5. Shopping malls (from Wikipedia)
    try:
        mall_df = load_parquet("raw_wiki_shopping_mall")
        # The column is 'shopping_mall', rename it to 'name'
        if 'shopping_mall' in mall_df.columns:
            mall_df = mall_df.rename(columns={'shopping_mall': 'name'})
        elif 'Name' in mall_df.columns:
            mall_df = mall_df.rename(columns={'Name': 'name'})
        elif 'name' not in mall_df.columns:
            logger.warning(f"⚠️  Mall data has unexpected columns: {list(mall_df.columns)}")
            raise ValueError("Unexpected column structure")

        mall_df['type'] = 'mall'
        mall_df['name'] = mall_df['name'].str.lower()
        mall_df = mall_df[['name', 'type', 'lat', 'lon']]
        mall_df['lat'] = mall_df['lat'].astype(float)
        mall_df['lon'] = mall_df['lon'].astype(float)
        logger.info(f"✅ Loaded {len(mall_df)} mall locations from Wikipedia")
        amenity_dfs.append(mall_df)
    except Exception as e:
        logger.warning(f"⚠️  Mall data error: {e}")

    # Check if we have any data
    if not amenity_dfs:
        logger.error("❌ No amenity data found! Cannot proceed.")
        return 1

    # Combine all amenity data
    logger.info("Combining all amenity data...")
    df_combined = pd.concat(amenity_dfs, ignore_index=True)

    # Ensure data types
    df_combined['lat'] = df_combined['lat'].astype(float)
    df_combined['lon'] = df_combined['lon'].astype(float)

    # Display summary
    logger.info(f"✅ Combined {len(df_combined)} total amenities")
    logger.info("\nAmenity breakdown:")
    for amenity_type, count in df_combined['type'].value_counts().items():
        logger.info(f"  - {amenity_type}: {count:,}")

    # Save combined amenity dataset
    save_parquet(df_combined, "L1_amenity", source="L1 utilities processing")
    logger.info(f"✅ Saved L1_amenity.parquet ({len(df_combined)} rows)")

    # Save individual geojson files for L2 processing
    data_L1_path = data_base_path / 'L1'
    data_L1_path.mkdir(parents=True, exist_ok=True)

    # Save park geojson
    park_path = datagov_path / 'NParksParksandNatureReserves.geojson'
    if park_path.exists():
        park_gdf = gpd.read_file(park_path)
        park_gdf = park_gdf.to_crs('EPSG:4326')
        park_gdf['lon'] = park_gdf.geometry.x
        park_gdf['lat'] = park_gdf.geometry.y
        park_gdf['type'] = 'park'
        park_gdf['name'] = [extract_html_name(str(desc), 'NAME') for desc in park_gdf.get('Description', '')]
        park_gdf = park_gdf[['name', 'type', 'lon', 'lat', 'geometry']]
        park_gdf.to_file(data_L1_path / 'park.geojson', driver='GeoJSON')
        logger.info(f"✅ Saved park.geojson")

    # Save park connector geojson
    pc_path = datagov_path / 'MasterPlan2019SDCPParkConnectorLinelayerGEOJSON.geojson'
    if pc_path.exists():
        pc_gdf = gpd.read_file(pc_path)
        pc_gdf.to_file(data_L1_path / 'park_connector.geojson', driver='GeoJSON')
        logger.info(f"✅ Saved park_connector.geojson")

    logger.info("\n✅ L1 utilities processing completed successfully!")
    logger.info(f"📁 Combined amenity data saved to: {Config.PARQUETS_DIR / 'L1_amenity.parquet'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
