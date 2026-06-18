"""LayerWriter: unified persistence for DAG layer data.

One interface, two adapters:
- TrackedWriter (prod): path routing, quality monitoring, compression from settings.
- SimpleWriter (tests): mkdir + to_parquet, no side effects.

Replaces io_helpers.save_parquet with a single deep interface.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import Settings

logger = logging.getLogger(__name__)

LAYER_PATH_MAP = {
    "bronze": "01_bronze",
    "silver": "02_silver",
    "gold": "03_gold",
    "platinum": "04_platinum",
    "platinum_metrics": "04_platinum/metrics",
    "webapp": "app/public/data",
}


class LayerWriter(ABC):
    """Abstract interface for layer persistence."""

    @abstractmethod
    def write(self, df: pd.DataFrame, name: str, layer: str) -> Path:
        """Persist a DataFrame to the appropriate layer directory.

        Args:
            df: DataFrame to persist.
            name: Filename without extension (e.g. "cleaned_hdb_transactions").
            layer: Layer key — one of "bronze", "silver", "gold",
                   "platinum", "platinum_metrics", "webapp".

        Returns:
            Path to the written file.
        """
        ...

    def resolve_path(self, name: str, layer: str, data_dir: Path) -> Path:
        """Resolve a (name, layer) pair to a concrete file path."""
        layer_dir = LAYER_PATH_MAP.get(layer, layer)
        return data_dir / layer_dir / f"{name}.parquet"


def build_writer(settings: Settings, data_dir: Path) -> LayerWriter:
    """Construct the production LayerWriter from settings."""
    return TrackedWriter(data_dir=data_dir, settings=settings)


class SimpleWriter(LayerWriter):
    """Thin writer for tests — mkdir + to_parquet, no tracking."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def write(self, df: pd.DataFrame, name: str, layer: str) -> Path:
        path = self.resolve_path(name, layer, self.data_dir)
        if df.empty:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        logger.info("Saved %s %s records to %s", len(df), name, path)
        return path


class TrackedWriter(LayerWriter):
    """Production writer with quality monitoring and compression from settings."""

    def __init__(self, data_dir: Path, settings: Settings):
        self.data_dir = data_dir
        self.settings = settings

    def write(self, df: pd.DataFrame, name: str, layer: str) -> Path:
        path = self.resolve_path(name, layer, self.data_dir)
        if df.empty:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        compression = self.settings.pipeline.parquet_compression
        df.to_parquet(path, index=False, compression=compression)
        logger.info(
            "Saved %s %s records to %s (compression: %s)",
            len(df),
            name,
            path,
            compression,
        )

        from egg_n_bacon_housing.utils.data_quality import record_dataframe_quality

        record_dataframe_quality(
            df,
            dataset_name=name,
            db_path=self.settings.data_dir / "quality_metrics.db",
            source="layer_writer",
            stage=f"L_{layer}",
        )

        return path
