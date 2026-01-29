"""Centralized configuration for egg-n-bacon-housing project."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class with all project settings."""

    # ============== PATHS ==============
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"

    # Pipeline data (L0-L3 outputs)
    PIPELINE_DIR = DATA_DIR / "pipeline"
    PARQUETS_DIR = PIPELINE_DIR  # Alias for backwards compatibility

    # Manual downloads (CSVs, geojsons, etc.)
    MANUAL_DIR = DATA_DIR / "manual"

    # Analytics outputs (segmentation, feature importance, etc.)
    ANALYSIS_DIR = DATA_DIR / "analysis"

    # Archive for old/unused data
    ARCHIVE_DIR = DATA_DIR / "archive"

    # Other directories
    METADATA_FILE = DATA_DIR / "metadata.json"
    NOTEBOOKS_DIR = BASE_DIR / "notebooks"
    CORE_DIR = BASE_DIR / "core"
    SCRIPTS_DIR = BASE_DIR / "scripts"
    ANALYSIS_SCRIPTS_DIR = SCRIPTS_DIR / "analysis"
    ANALYSIS_OUTPUT_DIR = ANALYSIS_DIR
    L4_REPORT_PATH = ANALYSIS_DIR / "L4_summary_report.md"

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
    GEOCODING_API_DELAY = 1.2  # Delay between API calls in seconds (increased from 1.0 to respect rate limits)
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
        required_keys = {
            "ONEMAP_EMAIL": cls.ONEMAP_EMAIL,
            "GOOGLE_API_KEY": cls.GOOGLE_API_KEY,
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
        (cls.MANUAL_DIR / "csv").mkdir(parents=True, exist_ok=True)
        (cls.MANUAL_DIR / "geojsons").mkdir(parents=True, exist_ok=True)
        (cls.MANUAL_DIR / "crosswalks").mkdir(parents=True, exist_ok=True)

        # Create analytics directory
        cls.ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

        # Create archive directory
        cls.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

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
        print(f"ANALYSIS_DIR: {cls.ANALYSIS_DIR}")
        print(f"USE_CACHING: {cls.USE_CACHING}")
        print(
            f"API Keys configured: {sum([
                bool(cls.ONEMAP_EMAIL),
                bool(cls.GOOGLE_API_KEY),
                bool(cls.SUPABASE_URL)
            ])}/3"
        )


# Convenience: validate on import
# Comment this out if you want lazy validation
# Config.validate()
