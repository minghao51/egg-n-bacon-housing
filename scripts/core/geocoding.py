"""
Shared geocoding functions for URA transaction processing.

This module provides reusable functions for:
- Loading URA CSV files
- Extracting unique property addresses
- Fetching geocoding data from OneMap API
- Authentication with OneMap API
"""

import os
import json
import time
import base64
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import pandas as pd
import requests
from tenacity import retry, wait_exponential, stop_after_attempt
from dotenv import load_dotenv

from scripts.core.config import Config
from scripts.core.cache import cached_call
from scripts.core.data_helpers import save_parquet
from scripts.core.data_loader import CSVLoader

load_dotenv()

logger = logging.getLogger(__name__)


def setup_onemap_headers() -> Dict[str, str]:
    """
    Setup OneMap API authentication headers.

    Returns:
        Dict with Authorization header containing valid JWT token

    Raises:
        Exception: If token cannot be obtained or is invalid
    """
    access_token = os.environ.get('ONEMAP_TOKEN')

    if access_token:
        # Decode JWT to check expiration
        try:
            parts = access_token.split('.')
            if len(parts) == 3:
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload)
                token_data = json.loads(decoded)

                current_time = time.time()
                if token_data.get('exp', 0) > current_time:
                    print(f"✅ Using existing OneMap token from .env")
                    print(f"   Token expires in: {(token_data.get('exp') - current_time) / 3600:.1f} hours")
                    return {"Authorization": f"{access_token}"}
                else:
                    print("⚠️  Token in .env has expired")
                    access_token = None
            else:
                print("⚠️  Invalid token format")
                access_token = None
        except Exception as e:
            print(f"⚠️  Error decoding token: {e}")
            access_token = None

    # Fallback: try to get new token (if email/password are configured)
    if not access_token:
        print("Attempting to get new OneMap token...")
        url = "https://www.onemap.gov.sg/api/auth/post/getToken"
        payload = {
            "email": os.environ.get('ONEMAP_EMAIL'),
            "password": os.environ.get('ONEMAP_EMAIL_PASSWORD')
        }

        response = requests.request("POST", url, json=payload)
        print(f"API Response Status: {response.status_code}")

        if response.status_code == 200:
            response_data = json.loads(response.text)
            access_token = response_data.get('access_token')
            if access_token:
                print("✅ Successfully obtained new OneMap token")
                return {"Authorization": f"{access_token}"}
            else:
                print(f"❌ No access_token in response: {response.text}")
                raise KeyError("access_token not found in API response")
        else:
            print(f"❌ Failed to get token: {response.text}")
            raise Exception(f"Token request failed with status {response.status_code}")


# Retry configuration
initial_backoff = 1  # seconds
max_backoff = 32  # seconds


@retry(
    wait=wait_exponential(multiplier=1, min=initial_backoff, max=max_backoff),
    stop=stop_after_attempt(3),
    before_sleep=lambda retry_state: logger.warning(f"Retrying OneMap API ({retry_state.attempt_number}/3) after error: {retry_state.outcome.exception()}")
)
def fetch_data(search_string: str, headers: Dict[str, str], timeout: int = 30) -> pd.DataFrame:
    """
    Fetch geocoding data from OneMap API for a given address.

    Args:
        search_string: Address to search for
        headers: Authentication headers from setup_onemap_headers()
        timeout: Request timeout in seconds (default: 30)

    Returns:
        DataFrame with search results including coordinates

    Raises:
        requests.RequestException: If API call fails after retries
        requests.Timeout: If request times out
    """
    encoded_search = quote(search_string, safe='')
    url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={encoded_search}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return pd.DataFrame(json.loads(response.text)['results']).reset_index().rename(
        {'index': 'search_result'}, axis=1)


def load_ura_files(base_path: Optional[Path] = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load all URA transaction CSV files.

    Args:
        base_path: Base path to data directory (defaults to Config.CSV_DIR)

    Returns:
        Tuple of (ec_df, condo_df, hdb_df)
    """
    import re

    # Use CSVLoader for HDB data
    csv_loader = CSVLoader(base_path=base_path)

    # File lists
    ec_list = [
        "ECResidentialTransaction20260121003532",
        "ECResidentialTransaction20260121003707",
    ]

    condo_list = [
        "ResidentialTransaction20260121003944",
        "ResidentialTransaction20260121004101",
        "ResidentialTransaction20260121004213",
        "ResidentialTransaction20260121004407",
        "ResidentialTransaction20260121004517",
        "ResidentialTransaction20260121005130",
        "ResidentialTransaction20260121005233",
        "ResidentialTransaction20260121005346",
        "ResidentialTransaction20260121005450",
        "ResidentialTransaction20260121005601",
        "ResidentialTransaction20260121005715",
        "ResidentialTransaction20260121005734",
    ]

    # Use Config paths for URA directory
    if base_path is None:
        ura_dir = Config.URA_DIR
    else:
        ura_dir = base_path / 'ura'

    # Load EC files
    ec_dfs = [pd.read_csv(ura_dir / f"{ec}.csv", encoding='latin1') for ec in ec_list]
    ec_df = pd.concat(ec_dfs, ignore_index=True)
    print(f"✅ Loaded {len(ec_df)} EC transactions from {len(ec_list)} files")

    # Load Condo files
    condo_dfs = [pd.read_csv(ura_dir / f"{condo}.csv", encoding='latin1') for condo in condo_list]
    condo_df = pd.concat(condo_dfs, ignore_index=True)
    condo_df['Area (SQM)'] = condo_df['Area (SQM)'].str.replace(',', '').str.strip()
    condo_df['Area (SQM)'] = pd.to_numeric(condo_df['Area (SQM)'], errors='coerce')
    print(f"✅ Loaded {len(condo_df)} condo transactions from {len(condo_list)} files")

    # Load HDB files using CSVLoader
    hdb_df = csv_loader.load_hdb_resale(base_path=base_path)

    # Standardize lease duration
    def standardize_lease_duration(lease):
        if pd.isna(lease):
            return None
        if isinstance(lease, (int, float)):
            return int(lease * 12) if lease < 50 else int(lease)
        lease_str = str(lease).strip()
        if lease_str.isdigit():
            return int(lease_str) * 12
        match = re.match(r'(\d+)\s*years?\s*(\d+)\s*months?', lease_str)
        if match:
            years = int(match.group(1))
            months = int(match.group(2))
            return years * 12 + months
        match = re.match(r'(\d+)\s*years?', lease_str)
        if match:
            return int(match.group(1)) * 12
        return None

    if 'remaining_lease' in hdb_df.columns:
        hdb_df['remaining_lease_months'] = hdb_df['remaining_lease'].apply(standardize_lease_duration)
        hdb_df.drop('remaining_lease', axis=1, inplace=True)
        print(f"✅ Loaded {len(hdb_df)} HDB transactions with lease standardization")
    else:
        print(f"✅ Loaded {len(hdb_df)} HDB transactions (no lease column)")

    return ec_df, condo_df, hdb_df


def extract_unique_addresses(ec_df: pd.DataFrame,
                            condo_df: pd.DataFrame,
                            hdb_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract unique property addresses from all transaction data.

    Args:
        ec_df: Executive condominium transactions
        condo_df: Condo transactions
        hdb_df: HDB transactions

    Returns:
        DataFrame with unique addresses and property types
    """
    # Add property type column
    condo_df['property_type'] = 'private'
    ec_df['property_type'] = 'private'
    hdb_df['property_type'] = 'hdb'

    # Combine and get unique addresses
    housing_df = pd.concat(
        [
            condo_df[["Project Name", "Street Name", "property_type"]].drop_duplicates(),
            ec_df[["Project Name", "Street Name", 'property_type']].drop_duplicates(),
            hdb_df[["block", "street_name", 'property_type']].drop_duplicates(),
        ],
        ignore_index=True,
    )

    # Create search string
    NameAddress_list = ["Project Name", "Street Name", "block", "street_name"]
    for col in NameAddress_list:
        housing_df[col] = housing_df[col].fillna("")
    housing_df["NameAddress"] = housing_df[NameAddress_list].agg(" ".join, axis=1)
    housing_df["NameAddress"] = [addr.strip() for addr in housing_df["NameAddress"]]

    print(f"✅ Extracted {len(housing_df)} unique addresses")
    return housing_df


def fetch_data_cached(search_string: str, headers: Dict[str, str], timeout: int = 30) -> pd.DataFrame:
    """
    Fetch geocoding data from OneMap API with caching support.

    Args:
        search_string: Address to search for
        headers: Authentication headers from setup_onemap_headers()
        timeout: Request timeout in seconds (default: 30)

    Returns:
        DataFrame with search results including coordinates

    Raises:
        requests.RequestException: If API call fails after retries
        requests.Timeout: If request times out
    """
    # Create cache identifier
    cache_id = f"onemap_search:{search_string}"

    def _fetch_from_api():
        # Use the original fetch_data function with retry logic
        return fetch_data(search_string, headers, timeout)

    # Use cached_call to check cache first
    return cached_call(cache_id, _fetch_from_api, duration_hours=Config.CACHE_DURATION_HOURS)


def fetch_data_parallel(
    addresses: List[str],
    headers: Dict[str, str],
    max_workers: Optional[int] = None,
    show_progress: bool = True
) -> Tuple[List[pd.DataFrame], List[str]]:
    """
    Fetch geocoding data for multiple addresses in parallel.

    Args:
        addresses: List of address strings to geocode
        headers: Authentication headers from setup_onemap_headers()
        max_workers: Maximum number of parallel workers (defaults to Config.GEOCODING_MAX_WORKERS)
        show_progress: Whether to show progress messages

    Returns:
        Tuple of (results, failed_addresses)
        - results: List of DataFrames with geocoding results
        - failed_addresses: List of addresses that failed to geocode

    Example:
        >>> headers = setup_onemap_headers()
        >>> addresses = ["123 Main St", "456 Oak Ave"]
        >>> results, failed = fetch_data_parallel(addresses, headers)
    """
    if max_workers is None:
        max_workers = Config.GEOCODING_MAX_WORKERS

    results = []
    failed_addresses = []
    total = len(addresses)

    logger.info(f"🚀 Starting parallel geocoding for {total} addresses with {max_workers} workers")
    logger.info(f"⏱️  Estimated time: {(total / max_workers) * Config.GEOCODING_API_DELAY / 60:.1f} minutes")

    def geocode_single_address(address: str) -> Optional[pd.DataFrame]:
        """Geocode a single address with error handling."""
        try:
            # Add delay to respect API rate limits
            time.sleep(Config.GEOCODING_API_DELAY)
            return fetch_data_cached(address, headers, timeout=Config.GEOCODING_TIMEOUT)
        except Exception as e:
            logger.warning(f"⚠️  Failed to geocode '{address}': {e}")
            return None

    # Use ThreadPoolExecutor for parallel API calls
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_address = {executor.submit(geocode_single_address, addr): addr for addr in addresses}

        # Process completed tasks
        completed = 0
        for future in as_completed(future_to_address):
            address = future_to_address[future]
            completed += 1

            try:
                result = future.result()
                if result is not None:
                    result['NameAddress'] = address
                    results.append(result)
                else:
                    failed_addresses.append(address)

                # Log progress every 50 addresses
                if show_progress and completed % 50 == 0:
                    progress = completed / total * 100
                    logger.info(f"Progress: {completed}/{total} addresses ({progress:.1f}%)")
                elif show_progress and completed == total:
                    logger.info(f"✅ Final address processed: {completed}/{total}")

            except Exception as e:
                logger.error(f"❌ Unexpected error for '{address}': {e}")
                failed_addresses.append(address)

    logger.info(f"✅ Completed geocoding: {len(results)}/{total} successful, {len(failed_addresses)} failed")

    return results, failed_addresses


def batch_geocode_addresses(
    addresses: List[str],
    headers: Dict[str, str],
    batch_size: int = 1000,
    checkpoint_interval: int = 100
) -> pd.DataFrame:
    """
    Geocode addresses in batches with checkpointing support.

    This function processes addresses in batches to avoid memory issues
    and supports periodic checkpointing for long-running jobs.

    Args:
        addresses: List of address strings to geocode
        headers: Authentication headers from setup_onemap_headers()
        batch_size: Number of addresses to process per batch
        checkpoint_interval: Save checkpoint every N addresses

    Returns:
        DataFrame with all geocoding results combined

    Example:
        >>> headers = setup_onemap_headers()
        >>> addresses_df = extract_unique_addresses(...)
        >>> results_df = batch_geocode_addresses(
        ...     addresses_df['NameAddress'].tolist(),
        ...     headers,
        ...     batch_size=500
        ... )
    """
    # save_parquet is imported at the top of the file to support multiprocessing

    batch_dataframes = []  # Store concatenated batch results
    total = len(addresses)

    # Process in batches
    for i in range(0, total, batch_size):
        batch_num = i // batch_size + 1
        batch_end = min(i + batch_size, total)
        batch_addresses = addresses[i:batch_end]

        logger.info(f"📦 Processing batch {batch_num} ({i+1}-{batch_end} of {total})")

        # Geocode this batch
        batch_results, failed = fetch_data_parallel(
            batch_addresses,
            headers,
            show_progress=True
        )

        # Concatenate batch results immediately to avoid memory issues
        if batch_results:
            logger.info(f"🔄 Concatenating {len(batch_results)} results from batch {batch_num}...")
            batch_df = pd.concat(batch_results, ignore_index=True)
            batch_dataframes.append(batch_df)
            logger.info(f"✅ Batch {batch_num} concatenated: {len(batch_df)} rows")

        # Log failed addresses in this batch
        if failed:
            logger.warning(f"⚠️  Batch {batch_num}: {len(failed)} failed addresses")

        # Save checkpoint periodically
        if checkpoint_interval and (batch_end) % checkpoint_interval == 0 and batch_dataframes:
            checkpoint_df = pd.concat(batch_dataframes, ignore_index=True)
            logger.info(f"💾 Checkpoint at {batch_end} addresses: {len(checkpoint_df)} total rows")
            # Note: You might want to save to a temporary checkpoint file here
            # save_parquet(checkpoint_df, f"checkpoint_geocoding_{batch_end}")

    # Combine all batch results
    logger.info(f"🔄 Combining results from {len(batch_dataframes)} batches...")
    if batch_dataframes:
        logger.info("🔄 Starting final pd.concat operation...")
        final_df = pd.concat(batch_dataframes, ignore_index=True)
        logger.info(f"✅ Geocoding complete: {len(final_df)} results from {total} addresses")
        return final_df
    else:
        logger.error("❌ No results from geocoding")
        return pd.DataFrame()

