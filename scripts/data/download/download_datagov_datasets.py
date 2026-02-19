#!/usr/bin/env python3
"""
Download amenity GeoJSON/KML files from data.gov.sg.

This script downloads amenity datasets in two phases:
- Phase 1: Preschools, parks, gyms, hawker centres, supermarkets, etc.
- Phase 2: MRT/LRT stations, child care services, MRT exits

Usage:
    # Download phase 1 datasets (default)
    uv run python scripts/data/download/download_datagov_datasets.py

    # Download phase 2 datasets only
    uv run python scripts/data/download/download_datagov_datasets.py --phase 2

    # Download all datasets
    uv run python scripts/data/download/download_datagov_datasets.py --phase all

    # Download specific datasets
    uv run python scripts/data/download/download_datagov_datasets.py \
        --datasets MRTStations.geojson,ChildCareServices.geojson
"""

import argparse
import logging
import pathlib
import sys
import time

import requests
from tqdm import tqdm

# Add project root to path (script is in scripts/data/download/, go up 3 levels)
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.config import Config  # noqa: E402
from scripts.core.network_check import check_local_file_exists, require_network  # noqa: E402

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Dataset definitions
PHASE1_DATASETS = {
    "PreSchoolsLocation.geojson": {
        "dataset_id": "d_61eefab99958fd70e6aab17320a71f1c",
        "description": "Pre-school locations",
    },
    "NParksParksandNatureReserves.geojson": {
        "dataset_id": "d_77d7ec97be83d44f61b85454f844382f",
        "description": "NParks parks and nature reserves",
    },
    "MasterPlan2019SDCPParkConnectorLinelayerGEOJSON.geojson": {
        "dataset_id": "d_3e902a9be74243ad68998e66b7dd4970",
        "description": "Park connector network",
    },
    "MasterPlan2019SDCPWaterbodylayerKML.kml": {
        "dataset_id": "d_40d896d7-18c1-4b7f-843f-347c3ffde4f3",
        "description": "Water bodies",
    },
    "Kindergartens.geojson": {
        "dataset_id": "d_253a7e348279bf0a87666a71f7ea2e67",
        "description": "Kindergarten locations",
    },
    "GymsSGGEOJSON.geojson": {
        "dataset_id": "d_81a33939-f94b-4e52-8915-3253bb38f72e",
        "description": "Gym locations",
    },
    "HawkerCentresGEOJSON.geojson": {
        "dataset_id": "d_4a086da0a5553be1d89383cd90d07ecd",
        "description": "Hawker centre locations",
    },
    "SupermarketsGEOJSON.geojson": {
        "dataset_id": "d_cac2c32f01960a3ad7202a99c27268a0",
        "description": "Supermarket locations",
    },
    "WaterActivitiesSG.geojson": {
        "dataset_id": "d_2c062bf1-040a-406e-bcd0-31304363e4e4",
        "description": "Water activities locations",
    },
}

PHASE2_DATASETS = {
    "MRTStations.geojson": {
        "dataset_id": "d_8d886e3a83934d7447acdf5bc6959999",
        "description": "MRT and LRT stations",
    },
    "ChildCareServices.geojson": {
        "dataset_id": "d_5d668e3f544335f8028f546827b773b4",
        "description": "Child care services",
    },
    "MRTStationExits.geojson": {
        "dataset_id": "d_b39d3a0871985372d7e1637193335da5",
        "description": "MRT station exits",
    },
}

# Combined datasets
ALL_DATASETS = {**PHASE1_DATASETS, **PHASE2_DATASETS}


def download_file(
    dataset_id: str, destination: pathlib.Path, description: str, max_retries: int = 3
) -> bool:
    """
    Download a file from data.gov.sg using the API with exponential backoff retry.

    Args:
        dataset_id: data.gov.sg dataset ID
        destination: Destination file path
        description: Description of the file being downloaded
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Downloading {description}...")

    for attempt in range(max_retries):
        try:
            # Calculate wait time for exponential backoff (2^attempt seconds)
            if attempt > 0:
                wait_time = 2**attempt
                logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {wait_time}s wait...")
                time.sleep(wait_time)

            # Step 1: Get download URL from poll-download API
            poll_url = (
                f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
            )
            logger.debug(f"Poll URL: {poll_url}")

            poll_response = requests.get(poll_url, timeout=30)

            # Handle rate limiting specifically
            if poll_response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)  # Exponential backoff
                    logger.warning(f"Rate limited (429), waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Rate limited after {max_retries} attempts")
                    return False

            poll_response.raise_for_status()

            json_data = poll_response.json()
            if json_data.get("code") != 0:
                logger.error(f"API error: {json_data.get('errMsg', 'Unknown error')}")
                return False

            # Extract download URL
            download_url = json_data["data"]["url"]
            logger.debug(f"Download URL: {download_url}")

            # Step 2: Download from the actual URL
            response = requests.get(download_url, stream=True, timeout=30)

            # Handle rate limiting on download URL
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(
                        f"Download rate limited (429), waiting {wait_time}s before retry..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Download rate limited after {max_retries} attempts")
                    return False

            response.raise_for_status()

            # Get file size for progress bar
            total_size = int(response.headers.get("content-length", 0))

            # Create parent directories if needed
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress bar
            with open(destination, "wb") as f:
                with tqdm(
                    total=total_size, unit="B", unit_scale=True, desc=destination.name, ncols=80
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            file_size_mb = destination.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Downloaded {description} ({file_size_mb:.2f} MB)")
            return True

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                logger.warning(f"Request failed: {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(
                    f"❌ Failed to download {description} after {max_retries} attempts: {e}"
                )
                return False
        except Exception as e:
            logger.error(f"❌ Error saving {description}: {e}")
            return False

    return False


def main():
    """Download datasets based on phase or specific files."""
    parser = argparse.ArgumentParser(
        description="Download amenity datasets from data.gov.sg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--phase",
        choices=["1", "2", "all"],
        default="1",
        help="Which phase to download (default: 1)",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        help="Comma-separated list of specific dataset filenames to download",
    )
    parser.add_argument("--force", action="store_true", help="Re-download files even if they exist")

    args = parser.parse_args()

    # Determine which datasets to download
    if args.datasets:
        # Parse specific datasets
        dataset_names = [d.strip() for d in args.datasets.split(",")]
        datasets_to_download = {k: v for k, v in ALL_DATASETS.items() if k in dataset_names}
        phase_desc = f"specific datasets ({len(datasets_to_download)})"
    elif args.phase == "1":
        datasets_to_download = PHASE1_DATASETS
        phase_desc = "Phase 1 datasets"
    elif args.phase == "2":
        datasets_to_download = PHASE2_DATASETS
        phase_desc = "Phase 2 datasets"
    else:  # all
        datasets_to_download = ALL_DATASETS
        phase_desc = "all datasets"

    logger.info("🚀 Starting Amenity Download from data.gov.sg")
    logger.info(f"Phase: {phase_desc}")
    logger.info(f"Target directory: {Config.DATA_DIR / 'raw_data' / 'csv' / 'datagov'}")
    logger.info("")

    target_dir = Config.DATA_DIR / "raw_data" / "csv" / "datagov"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Check if files already exist
    if not args.force:
        all_exist = True
        for filename in datasets_to_download:
            destination = target_dir / filename
            if not check_local_file_exists(destination):
                all_exist = False
                break

        if all_exist:
            logger.info(f"All {phase_desc} already exist locally.")
            logger.info("Skipping download. Use --force to re-download.")
            return 0

    if not require_network():
        logger.error("Network unavailable. Cannot download data. Exiting.")
        return 1

    # Track results
    successful = []
    failed = []

    # Download each dataset
    for filename, info in datasets_to_download.items():
        destination = target_dir / filename

        # Skip if already exists (unless --force)
        if not args.force and check_local_file_exists(destination):
            logger.info(f"⏭️  Skipping {filename} (already exists)")
            successful.append(filename)
            continue

        # Download file
        success = download_file(
            dataset_id=info["dataset_id"], destination=destination, description=info["description"]
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
    logger.info(f"✅ Successful: {len(successful)}/{len(datasets_to_download)}")
    logger.info(f"❌ Failed: {len(failed)}/{len(datasets_to_download)}")

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
