"""
Calculate Amenity Distances for Condo/EC Transactions

This script calculates MRT and amenity distances for condo/EC transactions
that have lat/lon coordinates but no amenity features.

Approach:
1. Load condo/EC transactions with coordinates
2. Load amenity locations (MRT, hawker, supermarket, park, etc.)
3. Calculate distances using scipy KDTree for fast nearest-neighbor search
4. Save results with same format as existing amenity features
5. Re-run the L3 unified dataset creation with complete amenity data
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate great circle distance between two points on Earth.

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in meters
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371000  # Earth radius in meters
    return c * r


def load_amenity_locations():
    """Load amenity point locations from L1 data.

    Returns:
        Dictionary mapping amenity type to DataFrame with lat/lon
    """
    logger.info("Loading amenity locations...")

    # Load amenity data
    amenity_path = Config.PARQUETS_DIR / "L1" / "amenity_v2.parquet"
    amenity_df = pd.read_parquet(amenity_path)

    # Ensure lat/lon are numeric
    amenity_df['lat'] = pd.to_numeric(amenity_df['lat'], errors='coerce')
    amenity_df['lon'] = pd.to_numeric(amenity_df['lon'], errors='coerce')
    amenity_df = amenity_df.dropna(subset=['lat', 'lon'])

    # Group by amenity type
    amenities = {}
    for amenity_type in amenity_df['type'].unique():
        subset = amenity_df[amenity_df['type'] == amenity_type]
        amenities[amenity_type] = subset[['lat', 'lon', 'name']].reset_index(drop=True)
        logger.info(f"  {amenity_type}: {len(subset):,} locations")

    return amenities


def calculate_nearest_amenity_distances(properties_df, amenity_type, amenity_locations):
    """Calculate distance to nearest amenity and count within radius.

    Args:
        properties_df: DataFrame with lat/lon columns
        amenity_type: Type of amenity (e.g., 'mrt', 'hawker')
        amenity_locations: DataFrame with lat/lon for this amenity type

    Returns:
        DataFrame with distance and counts
    """
    if len(amenity_locations) == 0:
        return pd.DataFrame()

    logger.info(f"  Calculating distances to {amenity_type}...")

    # Build KDTree for fast nearest-neighbor search
    # Convert lat/lon to radians for KDTree
    amenity_coords = np.radians(amenity_locations[['lat', 'lon']].values)
    property_coords = np.radians(properties_df[['lat', 'lon']].values)

    tree = cKDTree(amenity_coords)

    # Find nearest amenity
    distances, indices = tree.query(property_coords, k=1)

    # Convert angular distance to meters (approximate for small distances)
    # This is faster than haversine but less accurate
    nearest_distances = distances * 6371000  # Earth radius in meters

    # Count amenities within 500m, 1km, 2km
    counts_500m = []
    counts_1km = []
    counts_2km = []

    # For accurate distance calculations, use haversine for amenities within 2km
    for i, (prop_lat, prop_lon) in enumerate(zip(properties_df['lat'].values, properties_df['lon'].values)):
        # Calculate distances to all amenities using haversine
        dists = haversine_distance(
            prop_lat, prop_lon,
            amenity_locations['lat'].values,
            amenity_locations['lon'].values
        )

        counts_500m.append((dists <= 500).sum())
        counts_1km.append((dists <= 1000).sum())
        counts_2km.append((dists <= 2000).sum())

    result = pd.DataFrame({
        f'dist_to_nearest_{amenity_type}': nearest_distances,
        f'{amenity_type}_within_500m': counts_500m,
        f'{amenity_type}_within_1km': counts_1km,
        f'{amenity_type}_within_2km': counts_2km
    })

    return result


def main():
    """Main calculation pipeline."""

    logger.info("="*80)
    logger.info("CALCULATING AMENITY DISTANCES FOR CONDO/EC TRANSACTIONS")
    logger.info("="*80)

    # Load unified dataset
    logger.info("\nLoading unified dataset...")
    unified_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    unified = pd.read_parquet(unified_path)

    # Filter to condos/ECs without amenity features
    condo_ec = unified[
        (unified['property_type'].isin(['Condominium', 'EC'])) &
        (unified['dist_to_nearest_mrt'].isna())
    ].copy()

    logger.info(f"  Condo/EC transactions missing amenity data: {len(condo_ec):,}")

    if len(condo_ec) == 0:
        logger.info("  All condos/ECs already have amenity features!")
        return

    # Check for coordinates and ensure they're numeric
    condo_ec['lat'] = pd.to_numeric(condo_ec['lat'], errors='coerce')
    condo_ec['lon'] = pd.to_numeric(condo_ec['lon'], errors='coerce')

    has_coords = condo_ec['lat'].notna() & condo_ec['lon'].notna()
    condo_ec_with_coords = condo_ec[has_coords].copy()

    logger.info(f"  With valid coordinates: {len(condo_ec_with_coords):,}")

    if len(condo_ec_with_coords) == 0:
        logger.error("No condo/EC transactions with valid coordinates!")
        return

    # Load amenity locations
    amenities = load_amenity_locations()

    # Calculate distances for each amenity type
    amenity_types = ['mrt', 'hawker', 'supermarket', 'park', 'preschool', 'childcare']

    results = []
    for amenity_type in amenity_types:
        if amenity_type not in amenities:
            logger.warning(f"  Amenity type '{amenity_type}' not found, skipping")
            continue

        amenity_locations = amenities[amenity_type]
        result = calculate_nearest_amenity_distances(condo_ec_with_coords, amenity_type, amenity_locations)
        results.append(result)

    # Combine results
    logger.info("\nCombining results...")
    amenity_features = pd.concat(results, axis=1)

    # Reset index
    amenity_features.index = condo_ec_with_coords.index

    # Add to dataframe
    condo_ec_with_amenities = condo_ec_with_coords.copy()

    # Drop existing null amenity columns
    amenity_cols_to_drop = [col for col in condo_ec_with_amenities.columns
                           if col.startswith('dist_to_nearest_') or col.endswith('_within_500m')
                           or col.endswith('_within_1km') or col.endswith('_within_2km')]

    condo_ec_with_amenities = condo_ec_with_amenities.drop(columns=amenity_cols_to_drop, errors='ignore')

    # Add new amenity features
    condo_ec_final = pd.concat([condo_ec_with_amenities, amenity_features], axis=1)

    logger.info(f"  Added {len(amenity_features.columns)} amenity columns")

    # Ensure lat/lon are numeric BEFORE concat (fixes pyarrow save issue)
    condo_ec_final['lat'] = pd.to_numeric(condo_ec_final['lat'], errors='coerce').astype('float64')
    condo_ec_final['lon'] = pd.to_numeric(condo_ec_final['lon'], errors='coerce').astype('float64')

    # Update unified dataset
    logger.info("\nUpdating unified dataset...")

    # Remove old condo/EC records
    unified_without_condo_ec = unified[~unified.index.isin(condo_ec.index)]

    # Combine with updated condo/EC records
    unified_updated = pd.concat([unified_without_condo_ec, condo_ec_final], ignore_index=True)

    # Verify coverage
    hdb_coverage = unified_updated[unified_updated['property_type'] == 'HDB']['dist_to_nearest_mrt'].notna().sum()
    condo_coverage = unified_updated[unified_updated['property_type'] == 'Condominium']['dist_to_nearest_mrt'].notna().sum()
    ec_coverage = unified_updated[unified_updated['property_type'] == 'EC']['dist_to_nearest_mrt'].notna().sum()

    logger.info(f"\nAmenity coverage after update:")
    logger.info(f"  HDB: {hdb_coverage:,}")
    logger.info(f"  Condominium: {condo_coverage:,}")
    logger.info(f"  EC: {ec_coverage:,}")

    # Save updated unified dataset
    output_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    # Backup original
    backup_path = Config.PARQUETS_DIR / "L3" / "housing_unified_backup.parquet"
    logger.info(f"\nBacking up original to {backup_path}")
    unified.to_parquet(backup_path, index=False)

    # Save updated
    logger.info(f"Saving updated unified dataset to {output_path}")
    unified_updated.to_parquet(output_path, index=False)

    logger.info("\n" + "="*80)
    logger.info("✅ AMENITY CALCULATION COMPLETE!")
    logger.info("="*80)
    logger.info(f"\nAdded amenity features for {len(condo_ec_with_amenities):,} condo/EC transactions")


if __name__ == "__main__":
    main()
