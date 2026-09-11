"""Immutable per-run paths and reference-data service contracts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import pandas as pd

from egg_n_bacon_housing.config import Settings


@dataclass(frozen=True)
class RuntimePaths:
    """Authoritative filesystem roots for one pipeline execution."""

    data_dir: Path
    bronze_dir: Path
    external_dir: Path
    manual_dir: Path
    api_cache_dir: Path

    @classmethod
    def from_settings(
        cls, settings: Settings, data_path: str | Path | None = None
    ) -> "RuntimePaths":
        data_dir = settings.resolve_data_path(data_path)
        bronze_dir = settings.layer_dir("bronze", data_dir)
        return cls(
            data_dir=data_dir,
            bronze_dir=bronze_dir,
            external_dir=bronze_dir / "external",
            manual_dir=data_dir / "manual",
            api_cache_dir=data_dir / "cache",
        )


@runtime_checkable
class MrtReference(Protocol):
    """Read-only MRT line and station metadata used by ingestion/features."""

    def mrt_lines(self) -> dict[str, dict]: ...

    def station_lines_mapping(self) -> dict[str, list[str]]: ...

    def station_lines(self, station_name: str) -> list[str]: ...

    def station_tier(self, station_name: str) -> int: ...

    def station_score(self, station_name: str, distance_m: float) -> float: ...


@runtime_checkable
class SchoolReference(Protocol):
    """Read-only school reference-data source."""

    def load_school_tiers(self) -> tuple[pd.DataFrame, pd.DataFrame]: ...


@runtime_checkable
class SpatialReference(Protocol):
    """Read-only spatial reference-data source."""

    def planning_areas_for_points(self, lat: pd.Series, lon: pd.Series) -> pd.Series: ...
