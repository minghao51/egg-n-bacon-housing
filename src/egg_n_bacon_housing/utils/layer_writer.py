"""LayerWriter: unified persistence for DAG layer data.

One interface, two adapters:
- TrackedWriter (prod): path routing, quality monitoring, compression from settings.
- SimpleWriter (tests): mkdir + to_parquet, no side effects.

Re-exports the registry-derived ``PUBLISHED_LAYERS`` mapping so persistence
callers can resolve layer ownership without importing the pipeline driver.
"""

import logging
import os
import uuid
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import LayerDirs, Settings
from egg_n_bacon_housing.utils.output_registry import PUBLISHED_LAYERS as _PUBLISHED_LAYERS

logger = logging.getLogger(__name__)
PUBLISHED_LAYERS = _PUBLISHED_LAYERS

_LAYER_KEYS: tuple[str, ...] = (
    "bronze",
    "silver",
    "gold",
    "platinum",
    "platinum_metrics",
)


def _atomic_parquet_write(df: pd.DataFrame, path: Path, compression: str | None = None) -> None:
    """Write parquet beside the destination and atomically publish it."""
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        kwargs: dict[str, object] = {"index": False}
        if compression is not None:
            kwargs["compression"] = compression
        df.to_parquet(tmp, **kwargs)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def resolve_layer_paths(layer_dirs: LayerDirs, data_dir: Path) -> dict[str, Path]:
    """Resolve every layer key to its concrete directory under ``data_dir``.

    Mirrors ``Settings.layer_paths`` anchored at the pipeline directory
    ``data_dir``. Absolute configured paths are returned unchanged.
    """
    resolved: dict[str, Path] = {}
    for layer in _LAYER_KEYS:
        relative = layer_dirs.relative_path(layer)
        resolved[layer] = relative if relative.is_absolute() else data_dir / relative
    return resolved


class LayerWriter(ABC):
    """Abstract interface for layer persistence."""

    def __init__(self, layer_dirs: LayerDirs | None = None) -> None:
        self.layer_dirs = layer_dirs if layer_dirs is not None else LayerDirs()

    @abstractmethod
    def write(self, df: pd.DataFrame, name: str, layer: str, *, track_quality: bool = True) -> Path:
        """Persist a DataFrame to the appropriate layer directory.

        Args:
            df: DataFrame to persist.
            name: Filename without extension (e.g. "cleaned_hdb_transactions").
            layer: Layer key — one of "bronze", "silver", "gold",
                   "platinum", or "platinum_metrics".
            track_quality: When False, skip the quality-DB snapshot. Used for
                quarantine files whose timestamped names would otherwise
                create one-shot baselines and deaden anomaly detection.
                Writers without quality tracking ignore it.

        Returns:
            Path to the written file.
        """
        ...

    def resolve_path(self, name: str, layer: str, data_dir: Path) -> Path:
        """Resolve a (name, layer) pair to a concrete file path."""
        layer_dir = self.layer_dirs.relative_path(layer)
        return data_dir / layer_dir / f"{name}.parquet"


def build_writer(settings: Settings, data_dir: Path) -> LayerWriter:
    """Construct the production LayerWriter from settings.

    Threads ``settings.layer_dirs`` through so production paths honor
    ``LAYER_DIRS__*`` env overrides.
    """
    return TrackedWriter(
        data_dir=data_dir,
        settings=settings,
        layer_dirs=settings.layer_dirs,
        quality_db_path=data_dir.parent / "quality_metrics.db",
    )


class SimpleWriter(LayerWriter):
    """Thin writer for tests — mkdir + to_parquet, no tracking."""

    def __init__(self, data_dir: Path, layer_dirs: LayerDirs | None = None) -> None:
        super().__init__(layer_dirs=layer_dirs)
        self.data_dir = data_dir

    def write(self, df: pd.DataFrame, name: str, layer: str, *, track_quality: bool = True) -> Path:
        """Persist without tracking; ``track_quality`` is accepted and ignored."""
        path = self.resolve_path(name, layer, self.data_dir)
        # Empty frames persist as 0-row schema-only parquet so legitimately
        # empty outputs still exist on disk (a missing file means "recompute").
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_parquet_write(df, path)
        logger.info("Saved %s %s records to %s", len(df), name, path)
        return path


class TrackedWriter(LayerWriter):
    """Production writer with quality monitoring and compression from settings."""

    def __init__(
        self,
        data_dir: Path,
        settings: Settings,
        layer_paths: Mapping[str, Path] | None = None,
        quality_db_path: Path | None = None,
        layer_dirs: LayerDirs | None = None,
    ) -> None:
        super().__init__(layer_dirs if layer_dirs is not None else settings.layer_dirs)
        self.data_dir = data_dir
        self.settings = settings
        self.layer_paths: dict[str, Path] = (
            dict(layer_paths)
            if layer_paths is not None
            else resolve_layer_paths(self.layer_dirs, data_dir)
        )
        self.quality_db_path = quality_db_path or data_dir / "quality_metrics.db"

    def resolve_path(self, name: str, layer: str, data_dir: Path) -> Path:
        layer_dir = Path(self.layer_paths.get(layer, layer))
        return (
            layer_dir / f"{name}.parquet"
            if layer_dir.is_absolute()
            else data_dir / layer_dir / f"{name}.parquet"
        )

    def write(self, df: pd.DataFrame, name: str, layer: str, *, track_quality: bool = True) -> Path:
        path = self.resolve_path(name, layer, self.data_dir)
        # Empty frames persist as 0-row schema-only parquet so legitimately
        # empty outputs still exist on disk; the quality snapshot is still
        # recorded (0 rows) so anomaly detection sees the collapse to zero.
        path.parent.mkdir(parents=True, exist_ok=True)
        compression = self.settings.pipeline.parquet_compression
        _atomic_parquet_write(df, path, compression=compression)
        logger.info(
            "Saved %s %s records to %s (compression: %s)",
            len(df),
            name,
            path,
            compression,
        )

        if track_quality:
            from egg_n_bacon_housing.utils.data_quality import record_dataframe_quality

            record_dataframe_quality(
                df,
                dataset_name=name,
                db_path=self.quality_db_path,
                source="layer_writer",
                stage=f"L_{layer}",
            )

        return path
