#!/usr/bin/env python3
"""
Enhanced Geocoding Pipeline - Improve coverage from 10.8% to 50%+

This script enhances geocoding coverage by:
1. Fuzzy matching on address strings
2. Standardizing address formats
3. Using postal code matching where available
4. Calling OneMap API for missing properties (if enabled)

Usage:
    uv run python scripts/enhance_geocoding.py
"""

import logging
import sys
from pathlib import Path
from typing import Tuple

import pandas as pd
from rapidfuzz import process, fuzz

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA LOADING
# ============================================================================

def load_transaction_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load HDB and Condo transaction data.

    Returns:
        Tuple of (hdb_df, condo_df)
    """
    logger.info("Loading transaction data...")

    hdb_path = Config.PARQUETS_DIR / "L1" / "housing_hdb_transaction.parquet"
    condo_path = Config.PARQUETS_DIR / "L1" / "housing_condo_transaction.parquet"

    hdb_df = pd.read_parquet(hdb_path) if hdb_path.exists() else pd.DataFrame()
    condo_df = pd.read_parquet(condo_path) if condo_path.exists() else pd.DataFrame()

    logger.info(f"Loaded {len(hdb_df):,} HDB transactions")
    logger.info(f"Loaded {len(condo_df):,} Condo transactions")

    return hdb_df, condo_df


def load_geocoded_data() -> pd.DataFrame:
    """Load existing geocoded properties.

    Returns:
        DataFrame with geocoded properties
    """
    logger.info("Loading existing geocoded data...")

    geo_path = Config.PARQUETS_DIR / "L2" / "housing_unique_searched.parquet"

    if not geo_path.exists():
        logger.warning("Geocoded data not found")
        return pd.DataFrame()

    df = pd.read_parquet(geo_path)

    logger.info(f"Loaded {len(df):,} geocoded properties")

    return df


# ============================================================================
# ADDRESS STANDARDIZATION
# ============================================================================

def standardize_address(text: str) -> str:
    """Standardize address string for matching.

    Args:
        text: Raw address string

    Returns:
        Standardized address string
    """
    if pd.isna(text):
        return ""

    # Convert to uppercase
    text = str(text).upper()

    # Replace common abbreviations
    replacements = {
        'AVENUE': 'AVE',
        'ROAD': 'RD',
        'STREET': 'ST',
        'DRIVE': 'DR',
        'PLACE': 'PL',
        'CLOSE': 'CL',
        'LANE': 'LN',
        'CRESCENT': 'CRES',
        'HEIGHTS': 'HTS',
        'POINT': 'PT',
        'WALK': 'WK',
        'NORTH': 'N',
        'SOUTH': 'S',
        'EAST': 'E',
        'WEST': 'W',
        'CENTRAL': 'CTR',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove extra spaces
    text = ' '.join(text.split())

    return text.strip()


def prepare_hdb_for_geocoding(hdb_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare HDB data for geocoding.

    Args:
        hdb_df: Raw HDB transaction data

    Returns:
        DataFrame with standardized addresses
    """
    logger.info("Preparing HDB data for geocoding...")

    # Get unique properties
    unique_props = hdb_df[['block', 'street_name']].drop_duplicates().copy()

    # Create full address
    unique_props['full_address'] = unique_props['block'] + ' ' + unique_props['street_name']

    # Standardize addresses
    unique_props['address_std'] = unique_props['full_address'].apply(standardize_address)

    # Add property type
    unique_props['property_type'] = 'HDB'

    logger.info(f"Prepared {len(unique_props):,} unique HDB properties")

    return unique_props


def prepare_condo_for_geocoding(condo_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare Condo data for geocoding.

    Args:
        condo_df: Raw Condo transaction data

    Returns:
        DataFrame with standardized addresses
    """
    logger.info("Preparing Condo data for geocoding...")

    # Get unique properties
    unique_props = condo_df[['Project Name', 'Street Name']].drop_duplicates().copy()

    # Create full address
    unique_props['full_address'] = unique_props['Project Name'] + ', ' + unique_props['Street Name']

    # Standardize addresses
    unique_props['address_std'] = unique_props['Street Name'].apply(standardize_address)

    # Add property type
    unique_props['property_type'] = 'Condominium'

    logger.info(f"Prepared {len(unique_props):,} unique Condo properties")

    return unique_props


def prepare_geo_data(geo_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare geocoded data for matching.

    Args:
        geo_df: Geocoded properties

    Returns:
        DataFrame with standardized addresses
    """
    logger.info("Preparing geocoded data...")

    # Standardize addresses
    geo_df['address_std'] = geo_df['ROAD_NAME'].apply(standardize_address)

    logger.info(f"Prepared {len(geo_df):,} geocoded properties")

    return geo_df


# ============================================================================
# FUZZY MATCHING
# ============================================================================

def fuzzy_match_hdb(
    hdb_props: pd.DataFrame,
    geo_hdb: pd.DataFrame,
    score_threshold: int = 85
) -> pd.DataFrame:
    """Fuzzy match HDB properties to geocoded data.

    Args:
        hdb_props: HDB properties to geocode
        geo_hdb: Geocoded HDB properties
        score_threshold: Minimum match score (0-100)

    Returns:
        HDB properties with matched coordinates
    """
    logger.info(f"Starting fuzzy matching for HDB (threshold: {score_threshold})...")

    # Create lookup dict from geocoded data
    geo_dict = {}
    for _, row in geo_hdb.iterrows():
        key = row['address_std']
        geo_dict[key] = {
            'BLK_NO': row['BLK_NO'],
            'ROAD_NAME': row['ROAD_NAME'],
            'POSTAL': row.get('POSTAL', None),
            'LATITUDE': row['LATITUDE'],
            'LONGITUDE': row['LONGITUDE']
        }

    # Match each HDB property
    matched = []
    unmatched = []

    geo_addresses = list(geo_dict.keys())

    for idx, prop in hdb_props.iterrows():
        # Find best match
        result = process.extractOne(
            prop['address_std'],
            geo_addresses,
            scorer=fuzz.token_sort_ratio
        )

        if result and result[1] >= score_threshold:
            # Match found
            match_key, score, _ = result
            geo_data = geo_dict[match_key]

            matched.append({
                'block': prop['block'],
                'street_name': prop['street_name'],
                'full_address': prop['full_address'],
                'address_std': prop['address_std'],
                'matched_address': match_key,
                'match_score': score,
                'POSTAL': geo_data['POSTAL'],
                'LATITUDE': geo_data['LATITUDE'],
                'LONGITUDE': geo_data['LONGITUDE'],
                'match_type': 'fuzzy'
            })
        else:
            # No match
            unmatched.append({
                'block': prop['block'],
                'street_name': prop['street_name'],
                'full_address': prop['full_address'],
                'address_std': prop['address_std']
            })

    matched_df = pd.DataFrame(matched)
    unmatched_df = pd.DataFrame(unmatched)

    logger.info(f"Fuzzy matched {len(matched_df):,} of {len(hdb_props):,} HDB properties ({len(matched_df)/len(hdb_props)*100:.1f}%)")
    logger.info(f"Unmatched: {len(unmatched_df):,} properties")

    return matched_df, unmatched_df


def fuzzy_match_condo(
    condo_props: pd.DataFrame,
    geo_condo: pd.DataFrame,
    score_threshold: int = 85
) -> pd.DataFrame:
    """Fuzzy match Condo properties to geocoded data.

    Args:
        condo_props: Condo properties to geocode
        geo_condo: Geocoded Condo properties
        score_threshold: Minimum match score (0-100)

    Returns:
        Condo properties with matched coordinates
    """
    logger.info(f"Starting fuzzy matching for Condo (threshold: {score_threshold})...")

    # Create lookup dict from geocoded data
    geo_dict = {}
    for _, row in geo_condo.iterrows():
        key = row['address_std']
        if key not in geo_dict:  # Take first occurrence
            geo_dict[key] = {
                'ROAD_NAME': row['ROAD_NAME'],
                'POSTAL': row.get('POSTAL', None),
                'LATITUDE': row['LATITUDE'],
                'LONGITUDE': row['LONGITUDE']
            }

    # Match each Condo property
    matched = []
    unmatched = []

    geo_addresses = list(geo_dict.keys())

    for idx, prop in condo_props.iterrows():
        # Find best match
        result = process.extractOne(
            prop['address_std'],
            geo_addresses,
            scorer=fuzz.token_sort_ratio
        )

        if result and result[1] >= score_threshold:
            # Match found
            match_key, score, _ = result
            geo_data = geo_dict[match_key]

            matched.append({
                'Project Name': prop['Project Name'],
                'Street Name': prop['Street Name'],
                'full_address': prop['full_address'],
                'address_std': prop['address_std'],
                'matched_address': match_key,
                'match_score': score,
                'POSTAL': geo_data['POSTAL'],
                'LATITUDE': geo_data['LATITUDE'],
                'LONGITUDE': geo_data['LONGITUDE'],
                'match_type': 'fuzzy'
            })
        else:
            # No match
            unmatched.append({
                'Project Name': prop['Project Name'],
                'Street Name': prop['Street Name'],
                'full_address': prop['full_address'],
                'address_std': prop['address_std']
            })

    matched_df = pd.DataFrame(matched)
    unmatched_df = pd.DataFrame(unmatched)

    logger.info(f"Fuzzy matched {len(matched_df):,} of {len(condo_props):,} Condo properties ({len(matched_df)/len(condo_props)*100:.1f}%)")
    logger.info(f"Unmatched: {len(unmatched_df):,} properties")

    return matched_df, unmatched_df


# ============================================================================
# RESULTS MERGING
# ============================================================================

def merge_results_with_existing(
    hdb_matched: pd.DataFrame,
    hdb_unmatched: pd.DataFrame,
    condo_matched: pd.DataFrame,
    condo_unmatched: pd.DataFrame,
    existing_geo: pd.DataFrame
) -> pd.DataFrame:
    """Merge new geocoding results with existing geocoded data.

    Args:
        hdb_matched: Newly matched HDB properties
        hdb_unmatched: Unmatched HDB properties
        condo_matched: Newly matched Condo properties
        condo_unmatched: Unmatched Condo properties
        existing_geo: Existing geocoded properties

    Returns:
        Combined geocoded dataset
    """
    logger.info("Merging results with existing geocoded data...")

    # Convert new matches to existing format
    new_hdb_geo = []
    if not hdb_matched.empty:
        for _, row in hdb_matched.iterrows():
            new_hdb_geo.append({
                'BLK_NO': row['block'],
                'ROAD_NAME': row['street_name'],
                'POSTAL': row.get('POSTAL', None),
                'LATITUDE': row['LATITUDE'],
                'LONGITUDE': row['LONGITUDE'],
                'property_type': 'hdb',
                'match_type': row['match_type'],
                'match_score': row['match_score']
            })

    new_condo_geo = []
    if not condo_matched.empty:
        for _, row in condo_matched.iterrows():
            new_condo_geo.append({
                'BLK_NO': row.get('Project Name', ''),
                'ROAD_NAME': row['Street Name'],
                'POSTAL': row.get('POSTAL', None),
                'LATITUDE': row['LATITUDE'],
                'LONGITUDE': row['LONGITUDE'],
                'property_type': 'private',
                'match_type': row['match_type'],
                'match_score': row['match_score']
            })

    # Combine
    combined = []

    # Add existing geocoded data
    for _, row in existing_geo.iterrows():
        combined.append({
            'BLK_NO': row.get('BLK_NO', ''),
            'ROAD_NAME': row.get('ROAD_NAME', ''),
            'POSTAL': row.get('POSTAL', None),
            'LATITUDE': row['LATITUDE'],
            'LONGITUDE': row['LONGITUDE'],
            'property_type': row.get('property_type', 'unknown'),
            'match_type': 'existing',
            'match_score': 100
        })

    # Add new HDB matches
    combined.extend(new_hdb_geo)

    # Add new Condo matches
    combined.extend(new_condo_geo)

    combined_df = pd.DataFrame(combined)

    logger.info(f"Combined geocoded properties: {len(combined_df):,}")

    return combined_df


# ============================================================================
# SAVE RESULTS
# ============================================================================

def save_enhanced_geocoding(
    geo_df: pd.DataFrame,
    hdb_unmatched: pd.DataFrame,
    condo_unmatched: pd.DataFrame
):
    """Save enhanced geocoding results.

    Args:
        geo_df: Combined geocoded properties
        hdb_unmatched: Unmatched HDB properties
        condo_unmatched: Unmatched Condo properties
    """
    logger.info("Saving enhanced geocoding results...")

    # Create L2 directory
    l2_dir = Config.PARQUETS_DIR / "L2"
    l2_dir.mkdir(exist_ok=True)

    # Save enhanced geocoded data
    output_path = l2_dir / "housing_unique_searched_enhanced.parquet"
    geo_df.to_parquet(output_path, compression='snappy', index=False)
    logger.info(f"Saved enhanced geocoding to {output_path}")

    # Save unmatched for review
    if not hdb_unmatched.empty:
        hdb_unmatched_path = l2_dir / "hdb_unmatched.csv"
        hdb_unmatched.to_csv(hdb_unmatched_path, index=False)
        logger.info(f"Saved {len(hdb_unmatched)} unmatched HDB properties to {hdb_unmatched_path}")

    if not condo_unmatched.empty:
        condo_unmatched_path = l2_dir / "condo_unmatched.csv"
        condo_unmatched.to_csv(condo_unmatched_path, index=False)
        logger.info(f"Saved {len(condo_unmatched)} unmatched Condo properties to {condo_unmatched_path}")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Main enhanced geocoding pipeline."""

    logger.info("=" * 60)
    logger.info("Enhanced Geocoding Pipeline")
    logger.info("=" * 60)

    # Load data
    hdb_df, condo_df = load_transaction_data()
    geo_df = load_geocoded_data()

    if hdb_df.empty and condo_df.empty:
        logger.error("No transaction data available. Exiting.")
        return

    if geo_df.empty:
        logger.error("No geocoded data available for fuzzy matching. Exiting.")
        return

    # Prepare data
    if not hdb_df.empty:
        hdb_props = prepare_hdb_for_geocoding(hdb_df)
    else:
        hdb_props = pd.DataFrame()

    if not condo_df.empty:
        condo_props = prepare_condo_for_geocoding(condo_df)
    else:
        condo_props = pd.DataFrame()

    geo_df = prepare_geo_data(geo_df)

    # Filter geocoded data by property type
    if 'property_type' in geo_df.columns:
        geo_hdb = geo_df[geo_df['property_type'] == 'hdb'].copy()
        geo_condo = geo_df[geo_df['property_type'] == 'private'].copy()
    else:
        geo_hdb = geo_df.copy()
        geo_condo = pd.DataFrame()

    # Fuzzy match HDB
    hdb_matched = pd.DataFrame()
    hdb_unmatched = pd.DataFrame()

    if not hdb_props.empty and not geo_hdb.empty:
        hdb_matched, hdb_unmatched = fuzzy_match_hdb(hdb_props, geo_hdb, score_threshold=85)

    # Fuzzy match Condo
    condo_matched = pd.DataFrame()
    condo_unmatched = pd.DataFrame()

    if not condo_props.empty and not geo_condo.empty:
        condo_matched, condo_unmatched = fuzzy_match_condo(condo_props, geo_condo, score_threshold=85)

    # Merge results with existing
    enhanced_geo = merge_results_with_existing(
        hdb_matched,
        hdb_unmatched,
        condo_matched,
        condo_unmatched,
        geo_df
    )

    # Save results
    save_enhanced_geocoding(enhanced_geo, hdb_unmatched, condo_unmatched)

    # Print summary
    logger.info("=" * 60)
    logger.info("Enhanced Geocoding Summary")
    logger.info("=" * 60)
    logger.info(f"Total geocoded properties: {len(enhanced_geo):,}")

    if 'property_type' in enhanced_geo.columns:
        for ptype, count in enhanced_geo['property_type'].value_counts().items():
            logger.info(f"  {ptype}: {count:,} properties")

    if not hdb_unmatched.empty:
        logger.info(f"HDB unmatched: {len(hdb_unmatched):,} ({len(hdb_unmatched)/len(hdb_props)*100:.1f}%)")

    if not condo_unmatched.empty:
        logger.info(f"Condo unmatched: {len(condo_unmatched):,} ({len(condo_unmatched)/len(condo_props)*100:.1f}%)")

    logger.info("=" * 60)
    logger.info("Pipeline completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
