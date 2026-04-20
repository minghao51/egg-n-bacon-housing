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

import pandas as pd

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.data_quality import monitor_data_quality

logger = logging.getLogger(__name__)

DATA_DIR = settings.data_dir
PARQUETS_DIR = settings.data_dir / "pipeline"
METADATA_FILE = settings.data_dir / "metadata.json"


def load_parquet(
    dataset_name: str, version: str | None = None, columns: list[str] | None = None
) -> pd.DataFrame:
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

    if dataset_name not in metadata["datasets"]:
        available = list(metadata["datasets"].keys())
        raise ValueError(
            f"Dataset '{dataset_name}' not found in metadata. Available datasets: {available}"
        )

    dataset_info = metadata["datasets"][dataset_name]

    if version and dataset_info["version"] != version:
        raise ValueError(
            f"Version mismatch: requested {version}, "
            f"but {dataset_name} has version {dataset_info['version']}"
        )

    parquet_path = PARQUETS_DIR / dataset_info["path"]

    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Parquet file not found: {parquet_path}\n"
            f"Dataset may have been deleted. Run data pipeline to regenerate."
        )

    try:
        df = pd.read_parquet(parquet_path, columns=columns)
        logger.info(f"Loaded {dataset_name}: {len(df)} rows from {parquet_path}")
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to load parquet {parquet_path}: {e}")


@monitor_data_quality
def save_parquet(
    df: pd.DataFrame,
    dataset_name: str,
    source: str | None = None,
    version: str | None = None,
    mode: str = "overwrite",
    partition_cols: list[str] | None = None,
    compression: str | None = None,
    calculate_checksum: bool = False,
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
        compression: Compression codec (defaults to settings.pipeline.parquet_compression)
        calculate_checksum: Whether to calculate MD5 checksum (default False for performance)

    Raises:
        ValueError: If df is empty or invalid mode
        RuntimeError: If save operation fails
    """
    if df.empty:
        raise ValueError(f"Cannot save empty DataFrame for {dataset_name}")

    if mode not in ["overwrite", "append"]:
        raise ValueError(f"mode must be 'overwrite' or 'append', got '{mode}'")

    if version is None:
        version = datetime.now().strftime("%Y-%m-%d")

    if compression is None:
        compression = settings.pipeline.parquet_compression

    path_parts = (
        dataset_name.replace("L1_", "L1/")
        .replace("L2_", "L2/")
        .replace("L3_", "L3/")
        .replace("raw_data", "raw_data")
    )

    if partition_cols:
        parquet_path = PARQUETS_DIR / path_parts
    else:
        parquet_path = PARQUETS_DIR / f"{path_parts}.parquet"

    if partition_cols:
        parquet_path.mkdir(parents=True, exist_ok=True)
    else:
        parquet_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "append" and parquet_path.exists():
        try:
            if partition_cols:
                existing_df = pd.read_parquet(parquet_path)
            else:
                existing_df = pd.read_parquet(parquet_path)
            original_rows = len(existing_df)
            df = pd.concat([existing_df, df], ignore_index=True)
            logger.info(f"Appended {len(df) - original_rows} rows to {dataset_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to append to existing parquet: {e}")

    try:
        save_kwargs = {
            "index": settings.pipeline.parquet_index,
            "compression": compression,
            "engine": "pyarrow",
        }

        if partition_cols:
            df.to_parquet(parquet_path, partition_cols=partition_cols, **save_kwargs)
            logger.info(f"Saved {len(df)} rows to {parquet_path} (partitioned by {partition_cols})")
        else:
            df.to_parquet(parquet_path, **save_kwargs)
            logger.info(f"Saved {len(df)} rows to {parquet_path} (compression: {compression})")
    except Exception as e:
        raise RuntimeError(f"Failed to save parquet {parquet_path}: {e}")

    if not partition_cols and calculate_checksum:
        logger.info("🔐 Calculating checksum...")
        checksum = _calculate_checksum(parquet_path)
        logger.info(f"✅ Checksum: {checksum}")
    else:
        checksum = None

    metadata = _load_metadata()

    if dataset_name in metadata["datasets"] and mode == "overwrite":
        old_version = metadata["datasets"][dataset_name]["version"]
        if old_version != version:
            logger.warning(f"Overwriting {dataset_name}: version {old_version} -> {version}")

    dataset_metadata = {
        "path": str(parquet_path.relative_to(PARQUETS_DIR)),
        "full_path": str(parquet_path),
        "version": version,
        "rows": len(df),
        "created": datetime.now().isoformat(),
        "source": source or "unknown",
        "mode": mode,
        "compression": compression,
    }

    if checksum:
        dataset_metadata["checksum"] = checksum

    if partition_cols:
        dataset_metadata["partition_cols"] = partition_cols

    metadata["datasets"][dataset_name] = dataset_metadata
    metadata["last_updated"] = datetime.now().isoformat()

    _save_metadata(metadata)


def list_datasets(refresh_rows: bool = False) -> dict:
    """
    Return all datasets from metadata.

    Args:
        refresh_rows: If True, recalculate row counts from parquet files on disk
            for more accurate runtime summaries (does not rewrite metadata).

    Returns:
        Dictionary of dataset information
    """
    metadata = _load_metadata()
    datasets = metadata["datasets"]

    if not refresh_rows:
        return datasets

    refreshed: dict = {}
    for name, info in datasets.items():
        updated = dict(info)
        rel_path = info.get("path")
        if rel_path:
            parquet_path = PARQUETS_DIR / rel_path
            if parquet_path.exists():
                try:
                    updated["rows"] = len(pd.read_parquet(parquet_path))
                except Exception as e:
                    logger.debug("Could not refresh row count for %s: %s", name, e)
        refreshed[name] = updated
    return refreshed


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

        if "checksum" in info:
            current_checksum = _calculate_checksum(parquet_path)
            if current_checksum != info["checksum"]:
                logger.error(
                    f"Dataset {name}: checksum mismatch. "
                    f"Expected {info['checksum']}, got {current_checksum}"
                )
                all_valid = False
            else:
                logger.info(
                    f"Dataset {name}: OK ({info['rows']} rows, checksum: {current_checksum})"
                )
        else:
            logger.info(f"Dataset {name}: OK ({info['rows']} rows, no checksum)")

    return all_valid


def _load_metadata(metadata_file: Path | None = None) -> dict:
    """
    Load metadata.json, create if doesn't exist.

    Args:
        metadata_file: Optional path to metadata file (defaults to settings.data_dir / "metadata.json")

    Returns:
        Metadata dictionary
    """
    if metadata_file is None:
        metadata_file = METADATA_FILE

    if not metadata_file.exists():
        logger.info(f"Creating new metadata file at {metadata_file}")
        return {"datasets": {}, "last_updated": None}

    with open(metadata_file) as f:
        return json.load(f)


def _save_metadata(metadata: dict, metadata_file: Path | None = None) -> None:
    """
    Save metadata.json with pretty formatting.

    Args:
        metadata: Metadata dictionary to save
        metadata_file: Optional path to metadata file (defaults to settings.data_dir / "metadata.json")
    """
    if metadata_file is None:
        metadata_file = METADATA_FILE

    with open(metadata_file, "w") as f:
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
