"""Legacy parquet helpers with filesystem-first path resolution.

The current pipeline writes directly to medallion-layer paths, so this module
keeps `metadata.json` as optional lineage metadata rather than a required
manifest.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.data_quality import monitor_data_quality

logger = logging.getLogger(__name__)

PARQUETS_DIR = settings.data_dir / "pipeline"
METADATA_FILE = settings.data_dir / "metadata.json"


def load_parquet(
    dataset_name: str, version: str | None = None, columns: list[str] | None = None
) -> pd.DataFrame:
    """Load a parquet file by dataset name.

    Metadata is consulted first when available, then the filesystem is searched
    using the current medallion layout. This keeps older notebooks working
    while no longer requiring `metadata.json` to be perfectly up to date.
    """
    metadata = _load_metadata()
    dataset_info = metadata["datasets"].get(dataset_name)
    parquet_path = _resolve_dataset_path(dataset_name, dataset_info)

    if dataset_info is not None and version and dataset_info["version"] != version:
        raise ValueError(
            f"Version mismatch: requested {version}, "
            f"but {dataset_name} has version {dataset_info['version']}"
        )

    if not parquet_path.exists():
        fallback = _find_dataset_path(dataset_name)
        if fallback is None:
            available = list(metadata["datasets"].keys())
            raise FileNotFoundError(
                "Parquet file not found: "
                f"{parquet_path}\nDataset may have been deleted. "
                f"Known datasets: {available if available else 'none'}"
            )
        parquet_path = fallback

    try:
        df = pd.read_parquet(parquet_path, columns=columns)
        logger.info("Loaded %s: %s rows from %s", dataset_name, len(df), parquet_path)
        return df
    except (OSError, ValueError) as e:
        raise RuntimeError(f"Failed to load parquet {parquet_path}: {e}") from e


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
    """Save DataFrame to parquet with lightweight lineage metadata."""
    if df.empty:
        raise ValueError(f"Cannot save empty DataFrame for {dataset_name}")

    if mode not in ["overwrite", "append"]:
        raise ValueError(f"mode must be 'overwrite' or 'append', got '{mode}'")

    if version is None:
        version = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    if compression is None:
        compression = settings.pipeline.parquet_compression

    parquet_path = _resolve_dataset_path(dataset_name)

    if mode == "append" and parquet_path.exists():
        try:
            existing_df = pd.read_parquet(parquet_path)
            original_rows = len(existing_df)
            df = pd.concat([existing_df, df], ignore_index=True)
            logger.info("Appended %s rows to %s", len(df) - original_rows, dataset_name)
        except (OSError, ValueError) as e:
            raise RuntimeError(f"Failed to append to existing parquet: {e}") from e

    try:
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs = {
            "index": settings.pipeline.parquet_index,
            "compression": compression,
            "engine": "pyarrow",
        }

        if partition_cols:
            parquet_path.mkdir(parents=True, exist_ok=True)
            df.to_parquet(parquet_path, partition_cols=partition_cols, **save_kwargs)
            logger.info(
                "Saved %s rows to %s (partitioned by %s)", len(df), parquet_path, partition_cols
            )
        else:
            df.to_parquet(parquet_path, **save_kwargs)
            logger.info("Saved %s rows to %s (compression: %s)", len(df), parquet_path, compression)
    except (OSError, ValueError) as e:
        raise RuntimeError(f"Failed to save parquet {parquet_path}: {e}") from e

    if not partition_cols and calculate_checksum:
        logger.info("Calculating checksum for %s", parquet_path)
        checksum = _calculate_checksum(parquet_path)
        logger.info("Checksum: %s", checksum)
    else:
        checksum = None

    metadata = _load_metadata()

    if dataset_name in metadata["datasets"] and mode == "overwrite":
        old_version = metadata["datasets"][dataset_name]["version"]
        if old_version != version:
            logger.warning("Overwriting %s: version %s -> %s", dataset_name, old_version, version)

    dataset_metadata = {
        "path": str(parquet_path.relative_to(PARQUETS_DIR)),
        "full_path": str(parquet_path),
        "version": version,
        "rows": len(df),
        "created": datetime.now(tz=UTC).isoformat(),
        "source": source or "unknown",
        "mode": mode,
        "compression": compression,
    }

    if checksum:
        dataset_metadata["checksum"] = checksum

    if partition_cols:
        dataset_metadata["partition_cols"] = partition_cols

    metadata["datasets"][dataset_name] = dataset_metadata
    metadata["last_updated"] = datetime.now(tz=UTC).isoformat()

    _save_metadata(metadata)


def _load_metadata(metadata_file: Path | None = None) -> dict:
    if metadata_file is None:
        metadata_file = METADATA_FILE

    if not metadata_file.exists():
        return {"datasets": {}, "last_updated": None}

    with open(metadata_file, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Invalid metadata file at %s; ignoring it", metadata_file)
            return {"datasets": {}, "last_updated": None}


def _save_metadata(metadata: dict, metadata_file: Path | None = None) -> None:
    if metadata_file is None:
        metadata_file = METADATA_FILE

    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def _resolve_dataset_path(dataset_name: str, dataset_info: dict | None = None) -> Path:
    if dataset_info and "path" in dataset_info:
        return PARQUETS_DIR / dataset_info["path"]

    direct_path = Path(dataset_name)
    if direct_path.suffix == ".parquet":
        return direct_path if direct_path.is_absolute() else PARQUETS_DIR / direct_path

    if len(direct_path.parts) > 1:
        return PARQUETS_DIR / direct_path.with_suffix(".parquet")

    if dataset_name.startswith("L1_"):
        return PARQUETS_DIR / "02_silver" / f"{dataset_name[3:]}.parquet"
    if dataset_name.startswith("L2_"):
        return PARQUETS_DIR / "03_gold" / f"{dataset_name[3:]}.parquet"
    if dataset_name.startswith("L3_"):
        return PARQUETS_DIR / "04_platinum" / f"{dataset_name[3:]}.parquet"
    if dataset_name.startswith("L5_"):
        return PARQUETS_DIR / "04_platinum" / "metrics" / f"{dataset_name[3:]}.parquet"

    return PARQUETS_DIR / f"{dataset_name}.parquet"


def _find_dataset_path(dataset_name: str) -> Path | None:
    direct = _resolve_dataset_path(dataset_name)
    if direct.exists():
        return direct

    stem = Path(dataset_name).stem
    if stem.startswith(("L1_", "L2_", "L3_", "L5_")):
        stem = stem[3:]

    matches = [path for path in PARQUETS_DIR.rglob("*.parquet") if path.stem == stem]
    if len(matches) == 1:
        return matches[0]

    return None


def _calculate_checksum(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
