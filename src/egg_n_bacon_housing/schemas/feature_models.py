"""Feature data schemas (Gold layer - business-level enriched features)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class HFeatureTransaction(BaseModel):
    """Transaction enriched with features (Gold layer)."""

    transaction_date: datetime
    price: Annotated[float, Field(gt=0)]
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]
    property_type: str
    planning_area: str
    town: str | None = None

    floor_area_sqft: Annotated[float, Field(gt=0)]
    psf: Annotated[float, Field(gt=0)]
    remaining_lease_years: Annotated[float, Field(ge=0)]

    dist_to_nearest_mrt: float | None = Field(ge=0, default=None)
    nearest_mrt_station: str | None = None
    mrt_line: str | None = None

    dist_to_nearest_school: float | None = Field(ge=0, default=None)
    nearest_school: str | None = None
    school_tier: str | None = None

    dist_to_nearest_mall: float | None = Field(ge=0, default=None)
    nearest_mall: str | None = None

    rental_yield_pct: float | None = None

    h3_cell: str | None = None

    price_stratum: str | None = None


class HAmenityFeatures(BaseModel):
    """Precomputed amenity density features."""

    planning_area: str
    lat: float
    lon: float

    malls_within_1km: int
    malls_within_2km: int
    malls_within_5km: int

    schools_within_1km: int
    schools_within_2km: int
    schools_within_5km: int

    mrt_stations_within_1km: int
    mrt_stations_within_2km: int

    avg_mall_size_within_2km: float | None = None
    school_quality_score: float | None = None


class HRentalYieldRecord(BaseModel):
    """Precomputed rental yield record."""

    planning_area: str | None = None
    town: str | None = None
    property_type: str
    flat_type: str | None = None

    median_price: Annotated[float, Field(gt=0)]
    median_rent: Annotated[float, Field(gt=0)]
    rental_yield_pct: Annotated[float, Field(ge=0, le=20)]
    sample_size: int
    month: str


class HPlanningAreaMetrics(BaseModel):
    """Aggregated planning area metrics."""

    planning_area: str
    month: str

    median_price: float
    mean_price: float
    transaction_count: int

    avg_psf: float
    median_psf: float

    avg_remaining_lease_years: float

    rental_yield_pct: float | None = None

    appreciation_1m_pct: float | None = None
    appreciation_3m_pct: float | None = None
    appreciation_12m_pct: float | None = None
