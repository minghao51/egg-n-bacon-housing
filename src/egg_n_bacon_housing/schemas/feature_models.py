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
    planning_area: str | None = None
    town: str | None = None

    floor_area_sqft: Annotated[float, Field(gt=0)] | None = None
    psf: Annotated[float, Field(gt=0)] | None = None
    remaining_lease_years: Annotated[float, Field(ge=0)] | None = None

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
