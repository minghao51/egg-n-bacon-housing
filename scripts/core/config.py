"""Centralized configuration for egg-n-bacon-housing project."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class with all project settings."""

    # ============== PATHS ==============
    # core/ is now in scripts/core/, so go up 3 levels to reach project root
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"

    # Pipeline data (L0-L3 outputs)
    PIPELINE_DIR = DATA_DIR / "pipeline"
    PARQUETS_DIR = PIPELINE_DIR  # Alias for backwards compatibility

    # Manual downloads (CSVs, geojsons, etc.)
    MANUAL_DIR = DATA_DIR / "manual"

    # Analytics outputs (segmentation, feature importance, etc.)
    ANALYTICS_DIR = DATA_DIR / "analytics"

    # Other directories
    METADATA_FILE = DATA_DIR / "metadata.json"
    NOTEBOOKS_DIR = BASE_DIR / "notebooks"
    CORE_DIR = BASE_DIR / "scripts" / "core"  # Updated: core is now inside scripts
    SCRIPTS_DIR = BASE_DIR / "scripts"
    ANALYSIS_SCRIPTS_DIR = SCRIPTS_DIR / "analytics"  # Updated: analytics not analysis
    ANALYTICS_OUTPUT_DIR = ANALYTICS_DIR
    L4_REPORT_PATH = ANALYTICS_DIR / "L4_summary_report.md"

    # ============== PIPELINE STAGE SUBDIRECTORIES ==============
    L0_DIR = PARQUETS_DIR / "L0"
    L1_DIR = PARQUETS_DIR / "L1"
    L2_DIR = PARQUETS_DIR / "L2"
    L3_DIR = PARQUETS_DIR / "L3"

    # ============== MANUAL DATA SUBDIRECTORIES ==============
    CSV_DIR = MANUAL_DIR / "csv"
    GEOJSON_DIR = MANUAL_DIR / "geojsons"
    CROSSWALK_DIR = MANUAL_DIR / "crosswalks"
    URA_DIR = CSV_DIR / "ura"
    HDB_RESALE_DIR = CSV_DIR / "ResaleFlatPrices"

    # ============== DATASET FILE NAMES ==============
    # Dataset names without .parquet extension
    DATASET_HDB_TRANSACTION = "housing_hdb_transaction"
    DATASET_CONDO_TRANSACTION = "housing_condo_transaction"
    DATASET_EC_TRANSACTION = "housing_ec_transaction"

    # ============== API KEYS ==============
    ONEMAP_EMAIL = os.getenv("ONEMAP_EMAIL")
    ONEMAP_PASSWORD = os.getenv("ONEMAP_EMAIL_PASSWORD")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    JINA_AI = os.getenv("JINA_AI")

    # ============== DATA PIPELINE SETTINGS ==============
    # Parquet settings
    PARQUET_COMPRESSION = "snappy"  # Options: snappy, gzip, brotli, zstd
    PARQUET_INDEX = False  # Whether to include index in parquet files
    PARQUET_PARTITION_BY_DATE = True  # Partition parquet files by date columns
    PARQUET_ENGINE = "pyarrow"  # Options: pyarrow, fastparquet

    # Feature flags
    USE_CACHING = True
    CACHE_DIR = DATA_DIR / "cache"
    CACHE_DURATION_HOURS = 24  # Default cache duration for API calls
    VERBOSE_LOGGING = True

    # Geocoding settings
    GEOCODING_MAX_WORKERS = 5  # Parallel workers for geocoding (respect API limits)
    GEOCODING_API_DELAY = (
        1.2  # Delay between API calls in seconds (increased from 1.0 to respect rate limits)
    )
    GEOCODING_TIMEOUT = 30  # Request timeout in seconds

    # ============== NOTEBOOK SETTINGS ==============
    # Automatically add src to path in notebooks
    AUTO_ADD_SRC_PATH = True

    # ============== VALIDATION ==============
    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration is present.

        Raises:
            ValueError: If required configuration is missing
        """
        # Check current environment values (not just cached class attributes)
        required_keys = {
            "ONEMAP_EMAIL": os.getenv("ONEMAP_EMAIL"),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        }

        missing = [k for k, v in required_keys.items() if not v]

        if missing:
            raise ValueError(
                f"Missing required configuration: {missing}\n"
                f"Please set these in your .env file or environment variables."
            )

        # Verify directories exist
        if not cls.DATA_DIR.exists():
            raise ValueError(f"DATA_DIR does not exist: {cls.DATA_DIR}")

        # Create pipeline directories
        for stage_dir in ["L0", "L1", "L2", "L3"]:
            (cls.PIPELINE_DIR / stage_dir).mkdir(parents=True, exist_ok=True)

        # Create manual data subdirectories
        cls.CSV_DIR.mkdir(parents=True, exist_ok=True)
        cls.GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
        cls.CROSSWALK_DIR.mkdir(parents=True, exist_ok=True)

        # Create URA and HDB resale subdirectories
        cls.URA_DIR.mkdir(parents=True, exist_ok=True)
        cls.HDB_RESALE_DIR.mkdir(parents=True, exist_ok=True)

        # Create analytics directory
        cls.ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

        # Create cache directory
        if not cls.CACHE_DIR.exists():
            cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (safe for logging)."""
        print(f"BASE_DIR: {cls.BASE_DIR}")
        print(f"DATA_DIR: {cls.DATA_DIR}")
        print(f"PIPELINE_DIR: {cls.PIPELINE_DIR}")
        print(f"MANUAL_DIR: {cls.MANUAL_DIR}")
        print(f"ANALYTICS_DIR: {cls.ANALYTICS_DIR}")
        print(f"USE_CACHING: {cls.USE_CACHING}")
        print(
            f"API Keys configured: {sum([bool(cls.ONEMAP_EMAIL), bool(cls.GOOGLE_API_KEY), bool(cls.SUPABASE_URL)])}/3"
        )


# Convenience: validate on import
# Comment this out if you want lazy validation
# Config.validate()
