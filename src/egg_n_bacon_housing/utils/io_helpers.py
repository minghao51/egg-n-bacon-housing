"""I/O helpers for DAG layer persistence.

Centralizes parquet/JSON write logic so component nodes stay
focused on computation.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def save_parquet(df: pd.DataFrame, path: Path, description: str = "") -> Path:
    """Write a DataFrame to parquet, creating parent dirs as needed.

    Args:
        df: DataFrame to persist.
        path: Destination file path.
        description: Human-readable label for log messages.

    Returns:
        The path written to.
    """
    if df.empty:
        logger.debug(f"Skipping parquet write for empty DataFrame: {description or path.name}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    label = description or path.stem
    logger.info(f"Saved {len(df)} {label} records to {path.parent.name}/")
    return path
