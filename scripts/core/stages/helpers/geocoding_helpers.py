"""Helper functions for L1 geocoding pipeline."""

import logging
from typing import List, Optional, Tuple

import pandas as pd

from scripts.core.config import Config
from scripts.core.geocoding import (
    batch_geocode_addresses,
    fetch_data_cached,
    setup_onemap_headers,
)

logger = logging.getLogger(__name__)


def load_existing_geocoded_data(
    addresses: List[str],
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Load existing geocoded data and filter out already geocoded addresses.

    Args:
        addresses: List of all addresses to check

    Returns:
        Tuple of (existing_geocoded_df, new_addresses_to_geocode)
    """
    existing_path = Config.PIPELINE_DIR / "L2" / "housing_unique_searched.parquet"

    if not existing_path.exists():
        logger.info("No existing geocoded data found")
        return pd.DataFrame(), addresses

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

        return existing_geocoded_df, new_addresses

    except Exception as e:
        logger.warning(f"Could not load existing data: {e}")
        logger.info("Will geocode all addresses from scratch")
        return pd.DataFrame(), addresses


def setup_geocoding_auth() -> dict:
    """
    Setup OneMap authentication with proper error handling.

    Returns:
        Headers dictionary for OneMap API requests

    Raises:
        Exception: If authentication fails and no cached data available
    """
    try:
        headers = setup_onemap_headers()
        return headers
    except Exception as e:
        logger.error(f"❌ Failed to authenticate with OneMap API: {e}")
        raise Exception(
            "Cannot proceed without OneMap authentication. "
            "Please check your credentials in .env"
        )


def geocode_sequential(
    addresses: List[str],
    headers: dict,
    show_progress: bool = True,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Geocode addresses sequentially (slower but more reliable).

    Args:
        addresses: List of addresses to geocode
        headers: OneMap API headers
        show_progress: Show progress messages

    Returns:
        Tuple of (geocoded_df, failed_addresses)
    """
    import requests

    logger.info("Using sequential geocoding (slower)")
    logger.warning("This may take 30+ minutes due to API rate limiting")

    df_list = []
    failed = []
    total = len(addresses)

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

    return new_geocoded_df, failed


def geocode_parallel(
    addresses: List[str],
    headers: dict,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Geocode addresses using parallel batch processing (5x faster).

    Args:
        addresses: List of addresses to geocode
        headers: OneMap API headers

    Returns:
        Tuple of (geocoded_df, failed_addresses)
    """
    logger.info("Using parallel geocoding (5x faster)")

    total = len(addresses)
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

    return new_geocoded_df, failed


def merge_geocoded_results(
    existing_geocoded_df: pd.DataFrame,
    new_geocoded_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge existing and new geocoded results.

    Args:
        existing_geocoded_df: Previously geocoded addresses
        new_geocoded_df: Newly geocoded addresses

    Returns:
        Combined geocoded DataFrame
    """
    logger.info("🔄 Merging geocoded results...")

    if existing_geocoded_df.empty:
        logger.info(f"✅ No existing data, using new geocoded data: {len(new_geocoded_df)} rows")
        return new_geocoded_df

    if new_geocoded_df.empty:
        logger.info("✅ No new geocoded data, using existing data")
        return existing_geocoded_df

    logger.info(
        f"🔄 Concatenating existing ({len(existing_geocoded_df)} rows) + new ({len(new_geocoded_df)} rows)..."
    )

    geocoded_df = pd.concat([existing_geocoded_df, new_geocoded_df], ignore_index=True)
    logger.info(f"✅ Merged with existing data: {len(geocoded_df)} total addresses")

    return geocoded_df
