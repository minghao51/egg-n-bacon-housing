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

# Add project root to path (script is in scripts/data/process/amenities/, go up 5 levels)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet, save_parquet

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_html_name(html_string, tag_name):
    """Extract text from HTML table row where tag_name is in <th> and value is in <td>.

    Args:
        html_string: HTML string containing a table structure
        tag_name: The label to find in the <th> tag (e.g., 'LIC_NAME', 'CENTRE_NAME')

    Returns:
        The text content from the <td> tag following the matching <th>, or empty string if not found
    """
    try:
        soup = BeautifulSoup(html_string, 'html.parser')
        # Find all table rows
        rows = soup.find_all('tr')
        for row in rows:
            # Find the <th> tag with matching tag_name
            th = row.find('th')
            if th and tag_name in str(th):
                # Get the next sibling which should be <td>
                td = th.find_next_sibling('td')
                if td:
                    return td.text.strip()
        return ''
    except Exception as e:
        logger.debug(f"Failed to extract {tag_name} from HTML: {e}")
        return ''


def parse_datagov_geojson(filepath, amenity_type, name_field='Name'):
    """Parse GeoJSON file from data.gov.sg and extract lat/lon."""
    logger.info(f"Loading {amenity_type} from {filepath.name}...")

    gdf = gpd.read_file(filepath)

    # Ensure CRS is 4326
    if gdf.crs != 'EPSG:4326':
        gdf = gpd.to_crs('EPSG:4326')

    # Extract coordinates - use centroid for non-point geometries
    if gdf.geometry.geom_type.iloc[0] == 'Point':
        gdf['lon'] = gdf.geometry.x
        gdf['lat'] = gdf.geometry.y
    else:
        # For Polygon/MultiPolygon, use centroid
        gdf['lon'] = gdf.geometry.centroid.x
        gdf['lat'] = gdf.geometry.centroid.y

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

    # Track extraction success for HTML-based fields
    if 'Description' in gdf.columns and name_field not in gdf.columns:
        before_count = len(df)
        df = df[df['name'] != '']
        after_count = len(df)
        extraction_rate = (after_count / before_count * 100) if before_count > 0 else 0
        logger.info(f"  HTML parsing: {after_count}/{before_count} names extracted ({extraction_rate:.1f}%)")
    else:
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

    # 5. MRT Stations
    mrt_path = datagov_path / 'MRTStations.geojson'
    if mrt_path.exists():
        mrt_df = parse_datagov_geojson(mrt_path, 'mrt_station', 'NAME')
        amenity_dfs.append(mrt_df)
    else:
        logger.warning(f"⚠️  MRT station data not found at {mrt_path}")

    # 6. MRT Exits
    mrt_exit_path = datagov_path / 'MRTStationExits.geojson'
    if mrt_exit_path.exists():
        mrt_exit_df = parse_datagov_geojson(mrt_exit_path, 'mrt_exit', 'STATION_NA')
        amenity_dfs.append(mrt_exit_df)
    else:
        logger.warning(f"⚠️  MRT exit data not found at {mrt_exit_path}")

    # 7. Childcare Services
    childcare_path = datagov_path / 'ChildCareServices.geojson'
    if childcare_path.exists():
        childcare_df = parse_datagov_geojson(childcare_path, 'childcare', 'NAME')
        amenity_dfs.append(childcare_df)
    else:
        logger.warning(f"⚠️  Childcare data not found at {childcare_path}")

    # 8. Shopping malls (from Wikipedia)
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
        # Extract centroid coordinates for parks (non-point geometries)
        park_gdf['lon'] = park_gdf.geometry.centroid.x
        park_gdf['lat'] = park_gdf.geometry.centroid.y
        park_gdf['type'] = 'park'
        # Extract name from Description if it exists, otherwise use Name column
        if 'Description' in park_gdf.columns:
            park_gdf['name'] = [extract_html_name(str(desc), 'NAME') for desc in park_gdf['Description']]
        elif 'Name' in park_gdf.columns:
            park_gdf['name'] = park_gdf['Name'].str.lower()
        else:
            park_gdf['name'] = ''
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
