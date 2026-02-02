"""Helper functions for L0 data collection."""

import logging
from typing import Callable, Optional

import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import save_parquet

logger = logging.getLogger(__name__)


def fetch_and_save_datagovsg_dataset(
    dataset_name: str,
    dataset_id: str,
    fetch_fn: Callable,
    use_cache: bool = True,
) -> Optional[pd.DataFrame]:
    """
    Fetch dataset from data.gov.sg and save to parquet.

    This is a template function that reduces code duplication across
    multiple fetch_* functions.

    Args:
        dataset_name: Name for the parquet file (without extension)
        dataset_id: data.gov.sg dataset ID
        fetch_fn: Function that fetches the data (no arguments)
        use_cache: Whether to use caching

    Returns:
        DataFrame with data, or None if unavailable
    """
    df = load_existing_or_fetch(dataset_name, fetch_fn, use_cache)

    if df is not None and not df.empty:
        save_parquet(df, dataset_name, source="data.gov.sg API")
        logger.info(f"✅ Saved {dataset_name}: {len(df)} records")
        return df

    return None


def load_existing_or_fetch(
    dataset_name: str, fetch_fn: Callable, use_cache: bool = True
) -> Optional[pd.DataFrame]:
    """
    Load existing parquet file or fetch from API.

    Args:
        dataset_name: Name of the parquet file (without extension)
        fetch_fn: Function to fetch data from API
        use_cache: Whether to use API caching

    Returns:
        DataFrame with data, or None if not available
    """
    # Check for existing local data
    parquet_path = Config.DATA_DIR / "pipeline" / f"{dataset_name}.parquet"

    if parquet_path.exists():
        logger.info(f"📂 Found existing {dataset_name}.parquet, loading local copy")
        df = pd.read_parquet(parquet_path)
        logger.info(f"   Loaded {len(df)} records from local cache")
        return df

    # No local data, fetch from API
    logger.info(f"🌐 No local data found for {dataset_name}, fetching from API...")
    return fetch_fn()
