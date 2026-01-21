"""L1: Data processing and geocoding of URA and HDB transactions.

This module provides functions for:
- Loading and processing URA transaction data
- Extracting unique property addresses
- Geocoding addresses using OneMap API
- Combining and filtering geocoded results
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.config import Config
from src.data_helpers import save_parquet
from src.geocoding import (
    load_ura_files,
    extract_unique_addresses,
    setup_onemap_headers,
    fetch_data_parallel,
    batch_geocode_addresses
)

logger = logging.getLogger(__name__)


def load_and_save_transaction_data(
    csv_base_path: Optional[Path] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load URA and HDB transaction files and save individual datasets.

    Args:
        csv_base_path: Base path to CSV files (defaults to Config.DATA_DIR / 'raw_data' / 'csv')

    Returns:
        Tuple of (ec_df, condo_df, residential_df, hdb_df)

    Example:
        >>> ec_df, condo_df, res_df, hdb_df = load_and_save_transaction_data()
        >>> print(f"Loaded {len(ec_df)} EC transactions")
    """
    if csv_base_path is None:
        csv_base_path = Config.DATA_DIR / 'raw_data' / 'csv'

    logger.info("Loading URA and HDB transaction files...")

    # Load all transaction files
    ec_df, condo_df, residential_df, hdb_df = load_ura_files(csv_base_path)

    # Save individual transaction datasets
    save_parquet(ec_df, "L1_housing_ec_transaction", source="URA CSV data")
    logger.info(f"✅ Saved {len(ec_df)} EC transactions")

    save_parquet(condo_df, "L1_housing_condo_transaction", source="URA CSV data")
    logger.info(f"✅ Saved {len(condo_df)} condo transactions")

    save_parquet(residential_df, "L1_housing_residential_transaction", source="URA CSV data")
    logger.info(f"✅ Saved {len(residential_df)} residential transactions")

    save_parquet(hdb_df, "L1_housing_hdb_transaction", source="data.gov.sg CSV data")
    logger.info(f"✅ Saved {len(hdb_df)} HDB transactions")

    return ec_df, condo_df, residential_df, hdb_df


def prepare_unique_addresses(
    ec_df: pd.DataFrame,
    condo_df: pd.DataFrame,
    residential_df: pd.DataFrame,
    hdb_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Extract and prepare unique property addresses from all transaction data.

    Args:
        ec_df: Executive condominium transactions
        condo_df: Condo transactions
        residential_df: Residential transactions
        hdb_df: HDB transactions

    Returns:
        DataFrame with unique addresses and property types

    Example:
        >>> addresses_df = prepare_unique_addresses(ec_df, condo_df, res_df, hdb_df)
        >>> print(f"Found {len(addresses_df)} unique addresses")
    """
    logger.info("Extracting unique addresses...")

    housing_df = extract_unique_addresses(ec_df, condo_df, residential_df, hdb_df)

    logger.info(f"✅ Extracted {len(housing_df)} unique addresses")

    # Display sample addresses
    sample_addresses = housing_df['NameAddress'].head(10).tolist()
    logger.info(f"Sample addresses: {sample_addresses[:3]}...")

    return housing_df


def geocode_addresses(
    addresses: List[str],
    use_parallel: bool = True,
    show_progress: bool = True
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Geocode property addresses using OneMap API.

    Args:
        addresses: List of address strings to geocode
        use_parallel: Use parallel geocoding (5x faster)
        show_progress: Show progress messages

    Returns:
        Tuple of (geocoded_df, failed_addresses)

    Example:
        >>> addresses_df = prepare_unique_addresses(...)
        >>> geocoded_df, failed = geocode_addresses(
        ...     addresses_df['NameAddress'].tolist(),
        ...     use_parallel=True
        ... )
        >>> print(f"Geocoded {len(geocoded_df)} addresses")
    """
    # Setup OneMap authentication
    headers = setup_onemap_headers()

    total = len(addresses)
    logger.info(f"Starting geocoding for {total} unique addresses...")

    if use_parallel:
        logger.info("Using parallel geocoding (5x faster)")
        logger.info(f"Estimated time: ~{total / Config.GEOCODING_MAX_WORKERS * Config.GEOCODING_API_DELAY / 60:.1f} minutes")

        # Use batch geocoding for better performance
        geocoded_df = batch_geocode_addresses(
            addresses,
            headers,
            batch_size=1000,
            checkpoint_interval=500
        )

        # Determine failed addresses
        if geocoded_df.empty:
            failed = addresses
        else:
            geocoded_set = set(geocoded_df['NameAddress'].tolist())
            failed = [addr for addr in addresses if addr not in geocoded_set]

    else:
        logger.info("Using sequential geocoding (slower)")
        logger.warning("This may take 30+ minutes due to API rate limiting")

        import requests
        from src.geocoding import fetch_data_cached

        df_list = []
        failed = []

        for i, search_string in enumerate(addresses, 1):
            try:
                _df = fetch_data_cached(search_string, headers, timeout=Config.GEOCODING_TIMEOUT)
                _df['NameAddress'] = search_string
                df_list.append(_df)

                if show_progress and i % 50 == 0:
                    logger.info(f"Progress: {i}/{total} addresses ({i/total*100:.1f}%)")

            except requests.RequestException:
                failed.append(search_string)
                logger.warning(f"❌ Request failed for {search_string}. Skipping.")

        # Combine results
        if df_list:
            geocoded_df = pd.concat(df_list, ignore_index=True)
        else:
            geocoded_df = pd.DataFrame()

    logger.info(f"✅ Completed geocoding: {len(geocoded_df)}/{total} successful")

    if failed:
        logger.warning(f"⚠️  Failed to retrieve data for {len(failed)} addresses")

    return geocoded_df, failed


def process_geocoded_results(
    geocoded_df: pd.DataFrame,
    housing_df: pd.DataFrame,
    save_full: bool = True,
    save_filtered: bool = True
) -> pd.DataFrame:
    """
    Process and filter geocoded results.

    Args:
        geocoded_df: Geocoded addresses DataFrame
        housing_df: Original housing DataFrame with property types
        save_full: Whether to save full dataset
        save_filtered: Whether to save filtered dataset

    Returns:
        Filtered DataFrame with best match per address (search_result == 0)

    Example:
        >>> filtered_df = process_geocoded_results(
        ...     geocoded_df,
        ...     housing_df,
        ...     save_full=True,
        ...     save_filtered=True
        ... )
    """
    if geocoded_df.empty:
        logger.error("❌ No geocoded results to process")
        return pd.DataFrame()

    logger.info("Processing geocoded results...")

    # Save full dataset
    if save_full:
        save_parquet(
            geocoded_df,
            "L2_housing_unique_full_searched",
            source="L1 transaction data"
        )
        logger.info(f"✅ Saved full dataset: {len(geocoded_df)} rows")

    # Filter for best match (search_result == 0)
    filtered_df = geocoded_df[
        geocoded_df['search_result'] == 0
    ].reset_index(drop=True)

    # Add property_type column from original housing_df
    # Match by NameAddress
    property_type_map = housing_df.set_index('NameAddress')['property_type'].to_dict()
    filtered_df['property_type'] = filtered_df['NameAddress'].map(property_type_map)

    logger.info(f"Filtered to {len(filtered_df)} best-match addresses")

    # Save filtered dataset
    if save_filtered:
        save_parquet(
            filtered_df,
            "L2_housing_unique_searched",
            source="L2 housing data"
        )
        logger.info(f"✅ Saved filtered dataset: {len(filtered_df)} rows")

    return filtered_df


def run_full_l1_pipeline(
    csv_base_path: Optional[Path] = None,
    use_parallel_geocoding: bool = True
) -> Dict:
    """
    Run complete L1 processing pipeline.

    This includes:
    1. Loading transaction data
    2. Extracting unique addresses
    3. Geocoding addresses
    4. Processing and saving results

    Args:
        csv_base_path: Base path to CSV files
        use_parallel_geocoding: Use parallel geocoding (5x faster)

    Returns:
        Dictionary with pipeline results

    Example:
        >>> results = run_full_l1_pipeline(use_parallel_geocoding=True)
        >>> print(f"Geocoded {results['geocoded_count']} addresses")
    """
    logger.info("=" * 80)
    logger.info("🚀 Starting L1 Processing Pipeline")
    logger.info(f"Parallel geocoding: {use_parallel_geocoding}")
    logger.info("=" * 80)

    results = {}

    # Step 1: Load transaction data
    logger.info("Step 1: Loading transaction data...")
    ec_df, condo_df, residential_df, hdb_df = load_and_save_transaction_data(csv_base_path)

    results['transaction_counts'] = {
        'ec': len(ec_df),
        'condo': len(condo_df),
        'residential': len(residential_df),
        'hdb': len(hdb_df)
    }

    # Step 2: Extract unique addresses
    logger.info("Step 2: Extracting unique addresses...")
    housing_df = prepare_unique_addresses(ec_df, condo_df, residential_df, hdb_df)
    results['total_addresses'] = len(housing_df)

    # Step 3: Geocode addresses
    logger.info("Step 3: Geocoding addresses...")
    addresses_list = housing_df['NameAddress'].tolist()

    geocoded_df, failed_addresses = geocode_addresses(
        addresses_list,
        use_parallel=use_parallel_geocoding,
        show_progress=True
    )

    results['geocoded_count'] = len(geocoded_df)
    results['failed_count'] = len(failed_addresses)
    results['failed_addresses'] = failed_addresses[:10]  # Store first 10

    # Step 4: Process results
    logger.info("Step 4: Processing geocoded results...")
    filtered_df = process_geocoded_results(
        geocoded_df,
        housing_df,
        save_full=True,
        save_filtered=True
    )

    results['filtered_count'] = len(filtered_df)

    # Summary
    logger.info("=" * 80)
    logger.info("✅ L1 Pipeline Complete!")
    logger.info(f"   Transactions loaded: {sum(results['transaction_counts'].values())}")
    logger.info(f"   Unique addresses: {results['total_addresses']}")
    logger.info(f"   Successfully geocoded: {results['geocoded_count']} ({results['geocoded_count']/results['total_addresses']*100:.1f}%)")
    logger.info(f"   Failed: {results['failed_count']}")
    logger.info(f"   Final filtered results: {results['filtered_count']}")
    logger.info("=" * 80)

    return results


def save_failed_addresses(failed_addresses: List[str], filename: str = "failed_geocoding.txt") -> None:
    """
    Save list of failed addresses to file for later retry.

    Args:
        failed_addresses: List of addresses that failed to geocode
        filename: Output filename (saved to data/logs/)

    Example:
        >>> save_failed_addresses(failed_addresses)
        >>> # Check: data/logs/failed_geocoding.txt
    """
    if not failed_addresses:
        logger.info("No failed addresses to save")
        return

    log_dir = Config.DATA_DIR / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    output_file = log_dir / filename

    with open(output_file, 'w') as f:
        f.write(f"# Failed Geocoding Addresses\n")
        f.write(f"# Total: {len(failed_addresses)}\n")
        f.write(f"# Generated: {pd.Timestamp.now()}\n\n")
        for addr in failed_addresses:
            f.write(f"{addr}\n")

    logger.info(f"💾 Saved {len(failed_addresses)} failed addresses to {output_file}")
