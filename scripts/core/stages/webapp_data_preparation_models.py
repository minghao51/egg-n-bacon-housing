"""
Pydantic models for dashboard JSON exports.

These models act as a formal contract between the Python pipeline
and the TypeScript frontend, ensuring data consistency.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Metadata(BaseModel):
    generated_at: datetime
    total_records: int
    date_range: dict[str, str]


class StatsRecord(BaseModel):
    count: int
    median_price: int
    median_psf: int
    volume: int


class OverviewData(BaseModel):
    metadata: Metadata
    stats: dict[str, StatsRecord]
    distributions: dict[str, dict[str, int]]


class TrendRecord(BaseModel):
    date: str
    Overall_Price: int | None = None
    Overall_PSF: int | None = None
    Overall_Volume: int | None = None
    HDB_Price: int | None = None
    HDB_Volume: int | None = None
    Condominium_Price: int | None = None
    Condominium_Volume: int | None = None
    EC_Price: int | None = None
    EC_Volume: int | None = None


class MapMetrics(BaseModel):
    median_price: int
    median_psf: int
    volume: int
    mom_change_pct: float | None = None
    yoy_change_pct: float | None = None
    momentum: float | None = None
    momentum_signal: str | None = None
    rental_yield_mean: float | None = None
    rental_yield_median: float | None = None
    rental_yield_std: float | None = None
    affordability_ratio: float | None = None
    affordability_class: str | None = None
    mortgage_to_income_pct: float | None = None


class LeaderboardEntry(BaseModel):
    planning_area: str
    region: str
    coordinates: list[float] | None = None
    spatial_hotspot: str
    rank_overall: int
    median_price: int
    median_psf: int
    rental_yield_mean: float
    rental_yield_median: float | None = None
    yoy_growth_pct: float
    mom_change_pct: float
    momentum: float
    volume: int
    affordability_ratio: float
    by_property_type: dict[str, dict[str, int | None]] | None = None
    by_time_period: dict[str, dict[str, int | float | None]] | None = None


class HotspotData(BaseModel):
    category: str
    mean_yoy_growth: float
    median_yoy_growth: float
    std_yoy_growth: float
    consistency: float
    years: int


class AmenitySummaryRecord(BaseModel):
    planning_area: str
    avg_dist_to_hawker: float | None = None
    avg_dist_to_supermarket: float | None = None
    avg_dist_to_mrt_station: float | None = None
    avg_dist_to_mrt_exit: float | None = None
    avg_dist_to_childcare: float | None = None
    avg_dist_to_park: float | None = None
    avg_dist_to_mall: float | None = None
    avg_count_hawker_500m: float | None = None
    avg_count_supermarket_500m: float | None = None
    avg_count_mrt_station_500m: float | None = None
    avg_count_mrt_exit_500m: float | None = None
    avg_count_childcare_500m: float | None = None
    avg_count_park_500m: float | None = None
    avg_count_mall_500m: float | None = None


class SegmentPoint(BaseModel):
    name: str
    x: float
    y: float
    z: int
    category: Literal["HDB", "EC", "Condominium"]
