#!/usr/bin/env python3
"""
Download amenity GeoJSON/KML files from data.gov.sg.

This script downloads the required amenity datasets for L1 utilities processing:
- Preschools
- Parks
- Park connectors
- Water bodies
- Kindergartens
- Gyms
- Hawker centres
- Supermarkets
- Water activities

Usage:
    uv run python scripts/download_amenity_data.py
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

# data.gov.sg dataset IDs (new format)
DATASETS: dict[str, dict[str, str]] = {
    'PreSchoolsLocation.geojson': {
        'dataset_id': 'd_61eefab99958fd70e6aab17320a71f1c',
        'description': 'Pre-school locations'
    },
    'NParksParksandNatureReserves.geojson': {
        'dataset_id': 'd_77d7ec97be83d44f61b85454f844382f',
        'description': 'NParks parks and nature reserves'
    },
    'MasterPlan2019SDCPParkConnectorLinelayerGEOJSON.geojson': {
        'dataset_id': 'd_3e902a9be74243ad68998e66b7dd4970',
        'description': 'Park connector network'
    },
    'MasterPlan2019SDCPWaterbodylayerKML.kml': {
        'dataset_id': 'd_40d896d7-18c1-4b7f-843f-347c3ffde4f3',
        'description': 'Water bodies'
    },
    'Kindergartens.geojson': {
        'dataset_id': 'd_253a7e348279bf0a87666a71f7ea2e67',
        'description': 'Kindergarten locations'
    },
    'GymsSGGEOJSON.geojson': {
        'dataset_id': 'd_81a33939-f94b-4e52-8915-3253bb38f72e',
        'description': 'Gym locations'
    },
    'HawkerCentresGEOJSON.geojson': {
        'dataset_id': 'd_4a086da0a5553be1d89383cd90d07ecd',
        'description': 'Hawker centre locations'
    },
    'SupermarketsGEOJSON.geojson': {
        'dataset_id': 'd_cac2c32f01960a3ad7202a99c27268a0',
        'description': 'Supermarket locations'
    },
    'WaterActivitiesSG.geojson': {
        'dataset_id': 'd_2c062bf1-040a-406e-bcd0-31304363e4e4',
        'description': 'Water activities locations'
    }
}


def download_file(dataset_id: str, destination: pathlib.Path, description: str) -> bool:
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
    """Download all amenity datasets."""
    logger.info("🚀 Starting amenity data download from data.gov.sg")
    logger.info(f"Target directory: {Config.DATA_DIR / 'raw_data' / 'csv' / 'datagov'}")
    logger.info("")

    target_dir = Config.DATA_DIR / 'raw_data' / 'csv' / 'datagov'
    target_dir.mkdir(parents=True, exist_ok=True)

    all_exist = True
    for filename in DATASETS:
        destination = target_dir / filename
        if not check_local_file_exists(destination):
            all_exist = False
            break

    if all_exist:
        logger.info("All amenity files already exist locally.")
        logger.info("Skipping download. To re-download, delete the local files first.")
        return 0

    if not require_network():
        logger.error("Network unavailable. Cannot download data. Exiting.")
        return 1

    # Track results
    successful = []
    failed = []

    # Download each dataset
    for filename, info in DATASETS.items():
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

        # Small delay between downloads to be polite
        time.sleep(0.5)

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 Download Summary")
    logger.info("=" * 80)
    logger.info(f"✅ Successful: {len(successful)}/{len(DATASETS)}")
    logger.info(f"❌ Failed: {len(failed)}/{len(DATASETS)}")

    if successful:
        logger.info("\n✅ Downloaded files:")
        for filename in successful:
            logger.info(f"  - {filename}")

    if failed:
        logger.warning("\n❌ Failed downloads:")
        for filename in failed:
            logger.warning(f"  - {filename}")
        logger.warning("\n💡 You may need to download these manually from data.gov.sg")

    logger.info("")
    logger.info(f"📁 Files saved to: {target_dir}")

    # Return exit code
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
