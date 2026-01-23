#!/usr/bin/env python3
"""
Download Phase 2 amenity datasets from data.gov.sg.

This script downloads:
- MRT/LRT Stations (Master Plan 2019 Rail Station layer)
- Child Care Services (ECDA)
- MRT Station Exits (optional)

Usage:
    uv run python scripts/download_phase2_amenities.py
"""

import logging
import pathlib
import sys
import time

import requests
from tqdm import tqdm

# Add project root to path
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / 'src'))

from config import Config
from network_check import check_local_file_exists, require_network

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Phase 2 dataset IDs
PHASE2_DATASETS = {
    'MRTStations.geojson': {
        'dataset_id': 'd_8d886e3a83934d7447acdf5bc6959999',
        'description': 'MRT and LRT stations'
    },
    'ChildCareServices.geojson': {
        'dataset_id': 'd_5d668e3f544335f8028f546827b773b4',
        'description': 'Child care services'
    },
    'MRTStationExits.geojson': {
        'dataset_id': 'd_b39d3a0871985372d7e1637193335da5',
        'description': 'MRT station exits'
    }
}


def download_file(dataset_id, destination, description):
    """
    Download a file from data.gov.sg using the API.

    Args:
        dataset_id: data.gov.sg dataset ID
        destination: Destination file path
        description: Description of the file being downloaded

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Downloading {description}...")

    try:
        # Step 1: Get download URL from poll-download API
        poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
        logger.debug(f"Poll URL: {poll_url}")

        poll_response = requests.get(poll_url, timeout=30)
        poll_response.raise_for_status()

        json_data = poll_response.json()
        if json_data.get('code') != 0:
            logger.error(f"API error: {json_data.get('errMsg', 'Unknown error')}")
            return False

        # Extract download URL
        download_url = json_data['data']['url']
        logger.debug(f"Download URL: {download_url}")

        # Step 2: Download from the actual URL
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        # Get file size for progress bar
        total_size = int(response.headers.get('content-length', 0))

        # Create parent directories if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Download with progress bar
        with open(destination, 'wb') as f:
            with tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                desc=destination.name,
                ncols=80
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        file_size_mb = destination.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Downloaded {description} ({file_size_mb:.2f} MB)")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to download {description}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error saving {description}: {e}")
        return False


def main():
    """Download Phase 2 amenity datasets."""
    logger.info("🚀 Starting Phase 2 Amenity Download from data.gov.sg")
    logger.info("=" * 80)

    target_dir = Config.DATA_DIR / 'raw_data' / 'csv' / 'datagov'
    target_dir.mkdir(parents=True, exist_ok=True)

    all_exist = True
    for filename in PHASE2_DATASETS:
        destination = target_dir / filename
        if not check_local_file_exists(destination):
            all_exist = False
            break

    if all_exist:
        logger.info("All Phase 2 amenity files already exist locally.")
        logger.info("Skipping download. To re-download, delete the local files first.")
        return 0

    if not require_network():
        logger.error("Network unavailable. Cannot download data. Exiting.")
        return 1

    # Track results
    successful = []
    failed = []

    # Download each dataset
    for filename, info in PHASE2_DATASETS.items():
        destination = target_dir / filename

        # Skip if already exists
        if check_local_file_exists(destination):
            logger.info(f"⏭️  Skipping {filename} (already exists)")
            successful.append(filename)
            continue

        # Download file
        success = download_file(
            dataset_id=info['dataset_id'],
            destination=destination,
            description=info['description']
        )

        if success:
            successful.append(filename)
        else:
            failed.append(filename)

        # Small delay between downloads
        time.sleep(0.5)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 Download Summary")
    logger.info("=" * 80)
    logger.info(f"✅ Successful: {len(successful)}/{len(PHASE2_DATASETS)}")
    logger.info(f"❌ Failed: {len(failed)}/{len(PHASE2_DATASETS)}")

    if successful:
        logger.info("\n✅ Downloaded files:")
        for filename in successful:
            logger.info(f"  - {filename}")

    if failed:
        logger.warning("\n❌ Failed downloads:")
        for filename in failed:
            logger.warning(f"  - {filename}")

    logger.info(f"\n📁 Files saved to: {target_dir}")

    # Return exit code
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
