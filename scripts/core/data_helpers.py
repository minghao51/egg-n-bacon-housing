"""
Data helper functions for parquet file management with metadata tracking.

This module provides a simple interface for loading and saving parquet files
with automatic metadata tracking for reproducibility and lineage.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

try:
    from scripts.core.config import Config
except ImportError:
    from ..config import Config

# Get logger (don't call basicConfig - let the main script configure logging)
logger = logging.getLogger(__name__)

# Path configuration
DATA_DIR = Config.DATA_DIR
PARQUETS_DIR = Config.PARQUETS_DIR
METADATA_FILE = Config.METADATA_FILE


def load_parquet(dataset_name: str, version: str | None = None) -> pd.DataFrame:
    """
    Load a parquet file by dataset name with error handling.

    Args:
        dataset_name: Key from metadata.json (e.g., 'raw_data', 'L1_ura_transactions')
        version: Optional version string (defaults to latest)

    Returns:
        pandas DataFrame

    Raises:
        ValueError: If dataset not found or version mismatch
        FileNotFoundError: If parquet file missing
        RuntimeError: If file read fails
    """
    metadata = _load_metadata()

    # Check if dataset exists
    if dataset_name not in metadata["datasets"]:
        available = list(metadata["datasets"].keys())
        raise ValueError(
            f"Dataset '{dataset_name}' not found in metadata. "
            f"Available datasets: {available}"
        )

    dataset_info = metadata["datasets"][dataset_name]

    # Version checking
    if version and dataset_info["version"] != version:
        raise ValueError(
            f"Version mismatch: requested {version}, "
            f"but {dataset_name} has version {dataset_info['version']}"
        )

    parquet_path = PARQUETS_DIR / dataset_info["path"]

    # Check if file exists
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Parquet file not found: {parquet_path}\n"
            f"Dataset may have been deleted. Run data pipeline to regenerate."
        )

    try:
        df = pd.read_parquet(parquet_path)
        logger.info(f"Loaded {dataset_name}: {len(df)} rows from {parquet_path}")
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to load parquet {parquet_path}: {e}")


def save_parquet(
    df: pd.DataFrame,
    dataset_name: str,
    source: str | None = None,
    version: str | None = None,
    mode: str = "overwrite",
    partition_cols: Optional[list[str]] = None,
    compression: Optional[str] = None,
    calculate_checksum: bool = False
) -> None:
    """
    Save DataFrame to parquet with validation and error handling.

    Args:
        df: DataFrame to save
        dataset_name: Unique identifier for this dataset
        source: Source dataset or description (for lineage tracking)
        version: Version string (defaults to current date)
        mode: 'overwrite' to replace existing data, 'append' to add to it
        partition_cols: Columns to partition by (e.g., ['year', 'month'])
        compression: Compression codec (defaults to Config.PARQUET_COMPRESSION)
        calculate_checksum: Whether to calculate MD5 checksum (default False for performance)

    Raises:
        ValueError: If df is empty or invalid mode
        RuntimeError: If save operation fails
    """
    # Input validation
    if df.empty:
        raise ValueError(f"Cannot save empty DataFrame for {dataset_name}")

    if mode not in ["overwrite", "append"]:
        raise ValueError(f"mode must be 'overwrite' or 'append', got '{mode}'")

    # Create version string
    if version is None:
        version = datetime.now().strftime("%Y-%m-%d")

    # Use config compression if not specified
    if compression is None:
        compression = Config.PARQUET_COMPRESSION

    # Determine path from dataset name
    path_parts = dataset_name.replace("L1_", "L1/").replace("L2_", "L2/").replace("L3_", "L3/").replace("raw_data", "raw_data")

    # If partitioning, save to directory instead of file
    if partition_cols:
        parquet_path = PARQUETS_DIR / path_parts  # Directory
    else:
        parquet_path = PARQUETS_DIR / f"{path_parts}.parquet"  # File

    # Create parent directories
    if partition_cols:
        parquet_path.mkdir(parents=True, exist_ok=True)
    else:
        parquet_path.parent.mkdir(parents=True, exist_ok=True)

    # Handle append vs overwrite
    if mode == "append" and parquet_path.exists():
        try:
            if partition_cols:
                # For partitioned data, read and concat
                existing_df = pd.read_parquet(parquet_path)
            else:
                existing_df = pd.read_parquet(parquet_path)
            original_rows = len(existing_df)
            df = pd.concat([existing_df, df], ignore_index=True)
            logger.info(f"Appended {len(df) - original_rows} rows to {dataset_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to append to existing parquet: {e}")

    # Save parquet
    try:
        save_kwargs = {
            "index": Config.PARQUET_INDEX,
            "compression": compression,
            "engine": Config.PARQUET_ENGINE,
        }

        if partition_cols:
            # Save as partitioned dataset
            df.to_parquet(parquet_path, partition_cols=partition_cols, **save_kwargs)
            logger.info(f"Saved {len(df)} rows to {parquet_path} (partitioned by {partition_cols})")
        else:
            # Save as single file
            df.to_parquet(parquet_path, **save_kwargs)
            logger.info(f"Saved {len(df)} rows to {parquet_path} (compression: {compression})")
    except Exception as e:
        raise RuntimeError(f"Failed to save parquet {parquet_path}: {e}")

    # Calculate checksum (for single files only, not partitioned datasets)
    if not partition_cols and calculate_checksum:
        logger.info("🔐 Calculating checksum...")
        checksum = _calculate_checksum(parquet_path)
        logger.info(f"✅ Checksum: {checksum}")
    else:
        checksum = None  # Skip checksum by default for performance

    # Update metadata
    metadata = _load_metadata()

    # Warn if overwriting different version
    if dataset_name in metadata["datasets"] and mode == "overwrite":
        old_version = metadata["datasets"][dataset_name]["version"]
        if old_version != version:
            logger.warning(
                f"Overwriting {dataset_name}: version {old_version} -> {version}"
            )

    # Prepare metadata entry
    dataset_metadata = {
        "path": str(parquet_path.relative_to(PARQUETS_DIR)),
        "version": version,
        "rows": len(df),
        "created": datetime.now().isoformat(),
        "source": source or "unknown",
        "mode": mode,
        "compression": compression,
    }

    # Add checksum only for non-partitioned datasets
    if checksum:
        dataset_metadata["checksum"] = checksum

    # Add partition info if applicable
    if partition_cols:
        dataset_metadata["partition_cols"] = partition_cols

    metadata["datasets"][dataset_name] = dataset_metadata
    metadata["last_updated"] = datetime.now().isoformat()

    _save_metadata(metadata)


def list_datasets() -> dict:
    """
    Return all datasets from metadata.

    Returns:
        Dictionary of dataset information
    """
    metadata = _load_metadata()
    return metadata["datasets"]


def verify_metadata() -> bool:
    """
    Verify all datasets in metadata actually exist and checksums match.

    Returns:
        True if all datasets valid, False otherwise

    Logs errors for any invalid datasets found.
    """
    metadata = _load_metadata()
    all_valid = True

    if not metadata["datasets"]:
        logger.warning("No datasets found in metadata")
        return True

    for name, info in metadata["datasets"].items():
        parquet_path = PARQUETS_DIR / info["path"]

        if not parquet_path.exists():
            logger.error(f"Dataset {name}: file not found at {parquet_path}")
            all_valid = False
            continue

        # Only verify checksum if it exists
        if "checksum" in info:
            current_checksum = _calculate_checksum(parquet_path)
            if current_checksum != info["checksum"]:
                logger.error(
                    f"Dataset {name}: checksum mismatch. "
                    f"Expected {info['checksum']}, got {current_checksum}"
                )
                all_valid = False
            else:
                logger.info(f"Dataset {name}: OK ({info['rows']} rows, checksum: {current_checksum})")
        else:
            logger.info(f"Dataset {name}: OK ({info['rows']} rows, no checksum)")

    return all_valid


def _load_metadata() -> dict:
    """
    Load metadata.json, create if doesn't exist.

    Returns:
        Metadata dictionary
    """
    if not METADATA_FILE.exists():
        logger.info(f"Creating new metadata file at {METADATA_FILE}")
        return {"datasets": {}, "last_updated": None}

    with open(METADATA_FILE) as f:
        return json.load(f)


def _save_metadata(metadata: dict) -> None:
    """
    Save metadata.json with pretty formatting.

    Args:
        metadata: Metadata dictionary to save
    """
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


def _calculate_checksum(file_path: Path) -> str:
    """
    Calculate MD5 checksum of file.

    Args:
        file_path: Path to file

    Returns:
        First 8 characters of MD5 hash
    """
    return hashlib.md5(file_path.read_bytes()).hexdigest()[:8]
