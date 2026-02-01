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

from scripts.core.config import Config
from scripts.core.data_helpers import save_parquet
from scripts.core.geocoding import (
    load_ura_files,
    extract_unique_addresses,
    setup_onemap_headers,
    fetch_data_parallel,
    batch_geocode_addresses,
)

logger = logging.getLogger(__name__)


def load_and_save_transaction_data(
    csv_base_path: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load URA and HDB transaction files and save individual datasets.

    Args:
        csv_base_path: Base path to CSV files (defaults to Config.MANUAL_DIR / 'csv')

    Returns:
        Tuple of (ec_df, condo_df, hdb_df)

    Example:
        >>> ec_df, condo_df, hdb_df = load_and_save_transaction_data()
        >>> print(f"Loaded {len(ec_df)} EC transactions")
    """
    if csv_base_path is None:
        csv_base_path = Config.MANUAL_DIR / "csv"

    logger.info("Loading URA and HDB transaction files...")

    # Load all transaction files
    ec_df, condo_df, hdb_df = load_ura_files(csv_base_path)

    # Save individual transaction datasets
    save_parquet(ec_df, "L1_housing_ec_transaction", source="URA CSV data")
    logger.info(f"✅ Saved {len(ec_df)} EC transactions")

    save_parquet(condo_df, "L1_housing_condo_transaction", source="URA CSV data")
    logger.info(f"✅ Saved {len(condo_df)} condo transactions")

    save_parquet(hdb_df, "L1_housing_hdb_transaction", source="data.gov.sg CSV data")
    logger.info(f"✅ Saved {len(hdb_df)} HDB transactions")

    return ec_df, condo_df, hdb_df


def prepare_unique_addresses(
    ec_df: pd.DataFrame, condo_df: pd.DataFrame, hdb_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Extract and prepare unique property addresses from all transaction data.

    Args:
        ec_df: Executive condominium transactions
        condo_df: Condo transactions
        hdb_df: HDB transactions

    Returns:
        DataFrame with unique addresses and property types

    Example:
        >>> addresses_df = prepare_unique_addresses(ec_df, condo_df, hdb_df)
        >>> print(f"Found {len(addresses_df)} unique addresses")
    """
    logger.info("Extracting unique addresses...")

    housing_df = extract_unique_addresses(ec_df, condo_df, hdb_df)

    logger.info(f"✅ Extracted {len(housing_df)} unique addresses")

    # Display sample addresses
    sample_addresses = housing_df["NameAddress"].head(10).tolist()
    logger.info(f"Sample addresses: {sample_addresses[:3]}...")

    return housing_df


def geocode_addresses(
    addresses: List[str],
    use_parallel: bool = True,
    show_progress: bool = True,
    check_existing: bool = True,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Geocode property addresses using OneMap API.

    Args:
        addresses: List of address strings to geocode
        use_parallel: Use parallel geocoding (5x faster)
        show_progress: Show progress messages
        check_existing: Check for already geocoded addresses in L2 data

    Returns:
        Tuple of (geocoded_df, failed_addresses)

    Example:
        >>> addresses_df = prepare_unique_addresses(...)
        >>> geocoded_df, failed = geocode_addresses(
        ...     addresses_df['NameAddress'].tolist(),
        ...     use_parallel=True,
        ...     check_existing=True
        ... )
        >>> print(f"Geocoded {len(geocoded_df)} addresses")
    """
    # Check for existing geocoded data
    existing_geocoded_df = pd.DataFrame()
    if check_existing:
        existing_path = Config.PIPELINE_DIR / "L2" / "housing_unique_searched.parquet"
        if existing_path.exists():
            logger.info(f"Found existing geocoded data: {existing_path}")
            try:
                existing_geocoded_df = pd.read_parquet(existing_path)
                existing_addresses = set(existing_geocoded_df["NameAddress"].tolist())
                logger.info(f"✅ Loaded {len(existing_geocoded_df)} existing geocoded addresses")

                # Filter out already geocoded addresses
                new_addresses = [addr for addr in addresses if addr not in existing_addresses]

                logger.info(
                    f"Addresses to geocode: {len(new_addresses)} new / {len(addresses)} total"
                )

                if len(new_addresses) == 0:
                    logger.info("✅ All addresses already geocoded! Using existing data.")
                    return existing_geocoded_df, []

                addresses = new_addresses
            except Exception as e:
                logger.warning(f"Could not load existing data: {e}")
                logger.info("Will geocode all addresses from scratch")
    else:
        logger.info("Skipping existing data check (check_existing=False)")

    # Only setup OneMap authentication if we have addresses to geocode
    if len(addresses) == 0:
        logger.info("No addresses to geocode, returning existing data")
        return existing_geocoded_df, []

    # Setup OneMap authentication (with error handling for invalid credentials)
    try:
        headers = setup_onemap_headers()
    except Exception as e:
        logger.error(f"❌ Failed to authenticate with OneMap API: {e}")
        if len(existing_geocoded_df) > 0:
            logger.warning(f"⚠️  Using existing cached data ({len(existing_geocoded_df)} addresses)")
            logger.warning(f"⚠️  {len(addresses)} new addresses will not be geocoded")
            logger.warning(f"⚠️  To geocode these addresses, please update your OneMap credentials in .env")
            return existing_geocoded_df, addresses  # Return new addresses as failed
        else:
            logger.error("❌ No cached geocoded data available and cannot authenticate with OneMap")
            raise Exception("Cannot proceed without OneMap authentication. Please check your credentials in .env")

    total = len(addresses)
    logger.info(f"Starting geocoding for {total} unique addresses...")

    if use_parallel:
        logger.info("Using parallel geocoding (5x faster)")
        logger.info(
            f"Estimated time: ~{total / Config.GEOCODING_MAX_WORKERS * Config.GEOCODING_API_DELAY / 60:.1f} minutes"
        )

        # Use batch geocoding for better performance
        new_geocoded_df = batch_geocode_addresses(
            addresses, headers, batch_size=1000, checkpoint_interval=500
        )

        # Determine failed addresses
        if new_geocoded_df.empty:
            failed = addresses
        else:
            geocoded_set = set(new_geocoded_df["NameAddress"].tolist())
            failed = [addr for addr in addresses if addr not in geocoded_set]

    else:
        logger.info("Using sequential geocoding (slower)")
        logger.warning("This may take 30+ minutes due to API rate limiting")

        import requests
        from core.geocoding import fetch_data_cached

        df_list = []
        failed = []

        for i, search_string in enumerate(addresses, 1):
            try:
                _df = fetch_data_cached(search_string, headers, timeout=Config.GEOCODING_TIMEOUT)
                _df["NameAddress"] = search_string
                df_list.append(_df)

                if show_progress and i % 50 == 0:
                    logger.info(f"Progress: {i}/{total} addresses ({i / total * 100:.1f}%)")

            except requests.RequestException:
                failed.append(search_string)
                logger.warning(f"❌ Request failed for {search_string}. Skipping.")

        # Combine results
        if df_list:
            new_geocoded_df = pd.concat(df_list, ignore_index=True)
        else:
            new_geocoded_df = pd.DataFrame()

    logger.info(f"✅ Completed geocoding: {len(new_geocoded_df)}/{total} successful")

    if failed:
        logger.warning(f"⚠️  Failed to retrieve data for {len(failed)} addresses")

    # Merge with existing data if available
    logger.info("🔄 Merging geocoded results...")
    if not existing_geocoded_df.empty:
        if not new_geocoded_df.empty:
            logger.info(
                f"🔄 Concatenating existing ({len(existing_geocoded_df)} rows) + new ({len(new_geocoded_df)} rows)..."
            )
            geocoded_df = pd.concat([existing_geocoded_df, new_geocoded_df], ignore_index=True)
            logger.info(f"✅ Merged with existing data: {len(geocoded_df)} total addresses")
        else:
            logger.info("✅ No new geocoded data, using existing data")
            geocoded_df = existing_geocoded_df
    else:
        logger.info(f"✅ No existing data, using new geocoded data: {len(new_geocoded_df)} rows")
        geocoded_df = new_geocoded_df

    return geocoded_df, failed


def process_geocoded_results(
    geocoded_df: pd.DataFrame,
    housing_df: pd.DataFrame,
    save_full: bool = True,
    save_filtered: bool = True,
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
        logger.info(f"💾 Saving full dataset ({len(geocoded_df)} rows)...")
        save_parquet(geocoded_df, "L2_housing_unique_full_searched", source="L1 transaction data")
        logger.info(f"✅ Saved full dataset: {len(geocoded_df)} rows")

    # Filter for best match (search_result == 0)
    logger.info("🔍 Filtering for best match (search_result == 0)...")
    filtered_df = geocoded_df[geocoded_df["search_result"] == 0].reset_index(drop=True)
    logger.info(f"✅ Filtered to {len(filtered_df)} best-match addresses")

    # Add property_type column from original housing_df
    # Match by NameAddress
    logger.info("🏷️  Adding property_type column...")
    property_type_map = housing_df.set_index("NameAddress")["property_type"].to_dict()
    filtered_df["property_type"] = filtered_df["NameAddress"].map(property_type_map)
    logger.info(f"✅ Added property_type to {len(filtered_df)} addresses")

    # Save filtered dataset
    if save_filtered:
        logger.info(f"💾 Saving filtered dataset ({len(filtered_df)} rows)...")
        save_parquet(filtered_df, "L2_housing_unique_searched", source="L2 housing data")
        logger.info(f"✅ Saved filtered dataset: {len(filtered_df)} rows")

    return filtered_df


def run_processing_pipeline(
    csv_base_path: Optional[Path] = None, use_parallel_geocoding: bool = True
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
        >>> results = run_processing_pipeline(use_parallel_geocoding=True)
        >>> print(f"Geocoded {results['geocoded_count']} addresses")
    """
    logger.info("=" * 80)
    logger.info("🚀 Starting L1 Processing Pipeline")
    logger.info(f"Parallel geocoding: {use_parallel_geocoding}")
    logger.info("=" * 80)

    results = {}

    # Step 1: Load transaction data
    logger.info("Step 1: Loading transaction data...")
    ec_df, condo_df, hdb_df = load_and_save_transaction_data(csv_base_path)

    results["transaction_counts"] = {"ec": len(ec_df), "condo": len(condo_df), "hdb": len(hdb_df)}

    # Step 2: Extract unique addresses
    logger.info("Step 2: Extracting unique addresses...")
    housing_df = prepare_unique_addresses(ec_df, condo_df, hdb_df)
    results["total_addresses"] = len(housing_df)

    # Step 3: Geocode addresses
    logger.info("Step 3: Geocoding addresses...")
    addresses_list = housing_df["NameAddress"].tolist()

    geocoded_df, failed_addresses = geocode_addresses(
        addresses_list, use_parallel=use_parallel_geocoding, show_progress=True
    )

    results["geocoded_count"] = len(geocoded_df)
    results["failed_count"] = len(failed_addresses)
    results["failed_addresses"] = failed_addresses[:10]  # Store first 10

    logger.info(f"Step 3 Complete: Collected {len(geocoded_df)} results. Moving to Step 4...")

    # Step 4: Process results
    logger.info("Step 4: Processing geocoded results...")
    filtered_df = process_geocoded_results(
        geocoded_df, housing_df, save_full=True, save_filtered=True
    )
    logger.info(f"Step 4 Complete: Filtered to {len(filtered_df)} addresses.")

    results["filtered_count"] = len(filtered_df)

    # Summary
    logger.info("=" * 80)
    logger.info("✅ L1 Pipeline Complete!")
    logger.info(f"   Transactions loaded: {sum(results['transaction_counts'].values())}")
    logger.info(f"   Unique addresses: {results['total_addresses']}")
    logger.info(
        f"   Successfully geocoded: {results['geocoded_count']} ({results['geocoded_count'] / results['total_addresses'] * 100:.1f}%)"
    )
    logger.info(f"   Failed: {results['failed_count']}")
    logger.info(f"   Final filtered results: {results['filtered_count']}")
    logger.info("=" * 80)

    return results


def save_failed_addresses(
    failed_addresses: List[str], filename: str = "failed_geocoding.txt"
) -> None:
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

    log_dir = Config.DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    output_file = log_dir / filename

    with open(output_file, "w") as f:
        f.write(f"# Failed Geocoding Addresses\n")
        f.write(f"# Total: {len(failed_addresses)}\n")
        f.write(f"# Generated: {pd.Timestamp.now()}\n\n")
        for addr in failed_addresses:
            f.write(f"{addr}\n")

    logger.info(f"💾 Saved {len(failed_addresses)} failed addresses to {output_file}")
