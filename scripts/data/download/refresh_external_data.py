#!/usr/bin/env python3
"""
Refresh External Data Pipeline

This script checks for missing external data files and runs the appropriate
download scripts to refresh them. It handles:

1. Amenity datasets from data.gov.sg (Phase 1 & 2)
2. URA rental index
3. HDB rental data
4. URA private property transactions (manual download reminder)

Usage:
    # Check and download all missing data
    uv run python scripts/data/download/refresh_external_data.py

    # Check only (dry run)
    uv run python scripts/data/download/refresh_external_data.py --dry-run

    # Force refresh all data
    uv run python scripts/data/download/refresh_external_data.py --force-all

    # Download specific categories
    uv run python scripts/data/download/refresh_external_data.py --amenities --ura --hdb

    # Download specific phase of amenities
    uv run python scripts/data/download/refresh_external_data.py --amenities --phase 2
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config import Config
from network_check import require_network

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataRefreshManager:
    """Manages external data refresh operations."""

    def __init__(self, force_all: bool = False):
        """Initialize the refresh manager.

        Args:
            force_all: Force refresh all data even if files exist
        """
        self.force_all = force_all
        self.missing_files = []
        self.existing_files = []

    def check_file(self, path: Path, category: str) -> bool:
        """Check if a file exists.

        Args:
            path: File path to check
            category: Category name for logging

        Returns:
            True if file exists, False otherwise
        """
        if path.exists():
            self.existing_files.append((path, category))
            return True
        else:
            self.missing_files.append((path, category))
            return False

    def check_amenity_datasets(self, phase: str = 'all') -> dict[str, Path]:
        """Check amenity datasets.

        Args:
            phase: Which phase to check ('1', '2', or 'all')

        Returns:
            Dict of dataset name to path
        """
        target_dir = Config.DATA_DIR / 'raw_data' / 'csv' / 'datagov'

        phase1_datasets = {
            'PreSchoolsLocation.geojson',
            'NParksParksandNatureReserves.geojson',
            'MasterPlan2019SDCPParkConnectorLinelayerGEOJSON.geojson',
            'MasterPlan2019SDCPWaterbodylayerKML.kml',
            'Kindergartens.geojson',
            'GymsSGGEOJSON.geojson',
            'HawkerCentresGEOJSON.geojson',
            'SupermarketsGEOJSON.geojson',
            'WaterActivitiesSG.geojson'
        }

        phase2_datasets = {
            'MRTStations.geojson',
            'ChildCareServices.geojson',
            'MRTStationExits.geojson'
        }

        datasets_to_check = set()
        if phase in ['1', 'all']:
            datasets_to_check.update(phase1_datasets)
        if phase in ['2', 'all']:
            datasets_to_check.update(phase2_datasets)

        results = {}
        for dataset_name in datasets_to_check:
            path = target_dir / dataset_name
            results[dataset_name] = path
            self.check_file(path, f"Amenity ({phase})")

        return results

    def check_ura_rental_index(self) -> Path:
        """Check URA rental index file.

        Returns:
            Path to URA rental index file
        """
        path = Config.PARQUETS_DIR / "L2" / "ura_rental_index.parquet"
        self.check_file(path, "URA Rental Index")
        return path

    def check_hdb_rental_data(self) -> Path:
        """Check HDB rental data file.

        Returns:
            Path to HDB rental data file
        """
        path = Config.PARQUETS_DIR / "L1" / "housing_hdb_rental.parquet"
        self.check_file(path, "HDB Rental Data")
        return path

    def check_ura_transactions(self) -> list[Path]:
        """Check URA private property transaction files.

        Returns:
            List of paths to URA transaction CSV files
        """
        ura_dir = Config.DATA_DIR / 'manual' / 'csv' / 'ura'

        if not ura_dir.exists():
            logger.warning(f"URA directory not found: {ura_dir}")
            return []

        # Check for expected URA files
        expected_patterns = [
            'ECResidentialTransaction*.csv',
            'ResidentialTransaction*.csv'
        ]

        found_files = []
        for pattern in expected_patterns:
            matches = list(ura_dir.glob(pattern))
            if matches:
                found_files.extend(matches)

        # Check if we have any URA files
        if found_files:
            for f in found_files:
                self.check_file(f, "URA Transactions")
        else:
            self.missing_files.append((ura_dir, "URA Transactions (any CSV files)"))

        return found_files

    def print_summary(self):
        """Print summary of missing and existing files."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("DATA REFRESH SUMMARY")
        logger.info("=" * 80)

        if self.existing_files and not self.force_all:
            logger.info(f"\n✅ Existing files ({len(self.existing_files)}):")
            for path, category in self.existing_files:
                logger.info(f"  [{category}] {path.name}")
        elif self.force_all:
            logger.info(f"\n🔄 Force refresh enabled - will re-download {len(self.existing_files)} existing files")

        if self.missing_files:
            logger.warning(f"\n❌ Missing files ({len(self.missing_files)}):")
            for path, category in self.missing_files:
                logger.warning(f"  [{category}] {path}")

        logger.info("")

    def has_missing_files(self) -> bool:
        """Check if there are any missing files.

        Returns:
            True if any files are missing or force_all is enabled
        """
        return len(self.missing_files) > 0 or self.force_all


def run_download_script(script_path: Path, args: list[str] = None) -> bool:
    """Run a download script.

    Args:
        script_path: Path to the script
        args: Additional arguments to pass

    Returns:
        True if successful, False otherwise
    """
    import subprocess

    logger.info(f"\n🚀 Running: {script_path.name}")
    logger.info("-" * 80)

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=False
        )
        logger.info(f"✅ {script_path.name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {script_path.name} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        logger.error(f"❌ Error running {script_path.name}: {e}")
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Refresh external data files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Check for missing files without downloading'
    )
    parser.add_argument(
        '--force-all',
        action='store_true',
        help='Force refresh all data even if files exist'
    )
    parser.add_argument(
        '--amenities',
        action='store_true',
        help='Check/download amenity datasets'
    )
    parser.add_argument(
        '--phase',
        choices=['1', '2', 'all'],
        default='all',
        help='Which amenity phase to check (default: all)'
    )
    parser.add_argument(
        '--ura',
        action='store_true',
        help='Check/download URA rental index'
    )
    parser.add_argument(
        '--hdb',
        action='store_true',
        help='Check/download HDB rental data'
    )

    args = parser.parse_args()

    # If no specific categories selected, check all
    check_all = not (args.amenities or args.ura or args.hdb)

    logger.info("=" * 80)
    logger.info("EXTERNAL DATA REFRESH PIPELINE")
    logger.info("=" * 80)

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No downloads will be performed")

    # Check network
    if not args.dry_run:
        if not require_network():
            logger.error("Network unavailable. Cannot download data.")
            return 1

    # Initialize manager
    manager = DataRefreshManager(force_all=args.force_all)

    # Check amenity datasets
    if check_all or args.amenities:
        logger.info("\n📍 Checking amenity datasets...")
        manager.check_amenity_datasets(phase=args.phase)

    # Check URA rental index
    if check_all or args.ura:
        logger.info("\n📍 Checking URA rental index...")
        manager.check_ura_rental_index()

    # Check HDB rental data
    if check_all or args.hdb:
        logger.info("\n📍 Checking HDB rental data...")
        manager.check_hdb_rental_data()

    # Check URA transactions (manual download reminder)
    if check_all:
        logger.info("\n📍 Checking URA transaction files...")
        manager.check_ura_transactions()

    # Print summary
    manager.print_summary()

    # Early exit if dry run or no missing files
    if args.dry_run:
        logger.info("🔍 Dry run complete - no downloads performed")
        return 0

    if not manager.has_missing_files():
        logger.info("✅ All data files present. No downloads needed.")
        logger.info("Use --force-all to re-download all data.")
        return 0

    # Download missing files
    logger.info("=" * 80)
    logger.info("DOWNLOADING MISSING DATA")
    logger.info("=" * 80)

    success_count = 0
    failure_count = 0

    # Download amenity datasets
    if check_all or args.amenities:
        if manager.force_all or any('Amenity' in cat for _, cat in manager.missing_files):
            script_args = ['--phase', args.phase]
            if manager.force_all:
                script_args.append('--force')

            if run_download_script(
                PROJECT_ROOT / 'scripts' / 'data' / 'download' / 'download_datagov_datasets.py',
                script_args
            ):
                success_count += 1
            else:
                failure_count += 1

    # Download URA rental index
    if check_all or args.ura:
        if manager.force_all or any('URA Rental Index' in cat for _, cat in manager.missing_files):
            # Temporarily move/rename existing file if forcing
            if manager.force_all:
                ura_path = Config.PARQUETS_DIR / "L2" / "ura_rental_index.parquet"
                if ura_path.exists():
                    import shutil
                    backup_path = ura_path.with_suffix('.parquet.bak')
                    shutil.move(str(ura_path), str(backup_path))
                    logger.info(f"Backed up existing file to {backup_path}")

            if run_download_script(
                PROJECT_ROOT / 'scripts' / 'data' / 'download' / 'download_ura_rental_index.py'
            ):
                success_count += 1
            else:
                failure_count += 1

    # Download HDB rental data
    if check_all or args.hdb:
        if manager.force_all or any('HDB Rental Data' in cat for _, cat in manager.missing_files):
            # Temporarily move/rename existing file if forcing
            if manager.force_all:
                hdb_path = Config.PARQUETS_DIR / "L1" / "housing_hdb_rental.parquet"
                if hdb_path.exists():
                    import shutil
                    backup_path = hdb_path.with_suffix('.parquet.bak')
                    shutil.move(str(hdb_path), str(backup_path))
                    logger.info(f"Backed up existing file to {backup_path}")

            if run_download_script(
                PROJECT_ROOT / 'scripts' / 'data' / 'download' / 'download_hdb_rental_data.py'
            ):
                success_count += 1
            else:
                failure_count += 1

    # Check for URA transaction files (manual download)
    ura_missing = any('URA Transactions' in cat for _, cat in manager.missing_files)
    if ura_missing and not manager.force_all:
        logger.info("\n" + "=" * 80)
        logger.info("⚠️  MANUAL DOWNLOAD REQUIRED")
        logger.info("=" * 80)
        logger.info("\nURA private property transaction files must be downloaded manually:")
        logger.info("1. Visit: https://www.ura.gov.sg/property-market-information/transaction-bulk-download")
        logger.info("2. Download the following files:")
        logger.info("   - EC Residential Transaction (latest)")
        logger.info("   - Residential Transaction (multiple files)")
        logger.info("3. Extract and place CSV files in:")
        logger.info(f"   {Config.DATA_DIR / 'manual' / 'csv' / 'ura'}")
        logger.info("\nThese files are needed for condo/EC transaction data.")

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("REFRESH COMPLETE")
    logger.info("=" * 80)
    logger.info(f"✅ Successful downloads: {success_count}")
    if failure_count > 0:
        logger.warning(f"❌ Failed downloads: {failure_count}")

    if ura_missing:
        logger.warning("\n⚠️  Manual downloads still required (see above)")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
