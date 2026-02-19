#!/usr/bin/env python3
"""Geocode shopping mall names from Wikipedia data."""

import logging
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.data_helpers import load_parquet, save_parquet  # noqa: E402
from scripts.core.geocoding import fetch_data_cached, setup_onemap_headers  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def geocode_mall_with_fallbacks(mall_name: str, headers: dict) -> dict | None:
    """Try multiple search variations for mall geocoding.

    Args:
        mall_name: Original mall name to geocode
        headers: OneMap API headers with authentication

    Returns:
        Dict with shopping_mall, name, type, lat, lon if found, else None
    """
    search_queries = [
        mall_name,  # Original name
        f"{mall_name} shopping centre",  # Add suffix
        f"{mall_name} mall",  # Alternative suffix
    ]

    for query in search_queries:
        try:
            result_df = fetch_data_cached(query, headers)
            if result_df is not None and len(result_df) > 0:
                first_result = result_df.iloc[0]
                logger.debug(f"  ✅ Found using: '{query}'")
                return {
                    "shopping_mall": mall_name,
                    "name": mall_name.lower(),
                    "type": "mall",
                    "lat": float(first_result["LATITUDE"]),
                    "lon": float(first_result["LONGITUDE"]),
                }
        except Exception as e:
            logger.debug(f"Error geocoding '{query}': {e}")
            continue

    return None


def geocode_malls(delay: float = 1.0):
    """Geocode mall names using OneMap API with resume capability.

    Args:
        delay: Seconds to wait between API calls (default: 1.0)

    Features:
        - Resume: Skips already geocoded malls
        - Fallbacks: Tries multiple search variations
        - Progress bar: Shows real-time progress
        - Summary: Reports success rate and failed malls
    """
    logger.info("🚀 Starting mall geocoding")

    # Check if we have existing results
    try:
        existing_df = load_parquet("L1_amenity_mall")
        existing_names = set(existing_df["name"].tolist())
        logger.info(f"✅ Found {len(existing_names)} already geocoded malls")
    except FileNotFoundError:
        existing_names = set()

    # Load all mall names
    mall_df = load_parquet("raw_wiki_shopping_mall")
    logger.info(f"📋 Loaded {len(mall_df)} total mall names")

    # Filter out already geocoded
    mall_df["name_lower"] = mall_df["shopping_mall"].str.lower()
    pending_df = mall_df[~mall_df["name_lower"].isin(existing_names)]

    if len(pending_df) == 0:
        logger.info("✅ All malls already geocoded!")
        return

    logger.info(f"📍 Pending: {len(pending_df)} malls to geocode")
    logger.info(f"⏭️  Skipping: {len(existing_names)} already done")

    headers = setup_onemap_headers()

    results = []
    failed = []

    # Progress bar for geocoding
    for idx, row in tqdm(pending_df.iterrows(), total=len(pending_df), desc="Geocoding"):
        mall_name: str = str(row["shopping_mall"])

        logger.info(f"Geocoding: {mall_name}")

        result = geocode_mall_with_fallbacks(mall_name, headers)

        if result:
            results.append(result)
            logger.info(f"  ✅ Found: {result['lat']:.4f}, {result['lon']:.4f}")
        else:
            failed.append(mall_name)
            logger.warning(f"  ❌ Not found: {mall_name}")

        time.sleep(delay)

    # Combine with existing results
    if existing_names and results:
        logger.info(f"🔄 Merging {len(results)} new results with {len(existing_names)} existing")
        combined_df = pd.concat([existing_df, pd.DataFrame(results)], ignore_index=True)
    elif existing_names:
        combined_df = existing_df
    elif results:
        combined_df = pd.DataFrame(results)
    else:
        logger.error("❌ No geocoding results to save!")
        return

    # Save combined results
    save_parquet(combined_df, "L1_amenity_mall", source="geocoded malls")
    logger.info(f"✅ Saved {len(combined_df)} total geocoded malls")

    # Print summary statistics
    total_malls = len(mall_df)
    success_count = len(combined_df)
    failed_count = len(failed)
    success_rate = (success_count / total_malls * 100) if total_malls > 0 else 0

    logger.info("\n📊 Geocoding Summary:")
    logger.info(f"   Total malls: {total_malls}")
    logger.info(f"   Successfully geocoded: {success_count} ({success_rate:.1f}%)")
    logger.info(f"   Failed: {failed_count} ({100 - success_rate:.1f}%)")

    if failed:
        logger.info(f"\n❌ Failed malls ({len(failed)}):")
        for name in failed[:20]:
            logger.info(f"   - {name}")
        if len(failed) > 20:
            logger.info(f"   ... and {len(failed) - 20} more")


if __name__ == "__main__":
    geocode_malls()
