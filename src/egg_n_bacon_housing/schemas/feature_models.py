"""Feature data schemas (Gold layer - business-level enriched features)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class LocationDimRecord(BaseModel):
    """Location dimension record — one row per unique (lat, lon) pair.

    Contains all spatial features (proximity, school scores, block metadata,
    planning area) computed on ~10K unique locations.
    """

    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]

    block: str | None = None
    street_name: str | None = None
    town: str | None = None

    dist_to_nearest_mrt: float | None = Field(ge=0, default=None)
    nearest_mrt_station: str | None = None
    nearest_mrt_score: float | None = None

    dist_to_nearest_school: float | None = Field(ge=0, default=None)
    dist_to_nearest_mall: float | None = Field(ge=0, default=None)
    nearest_mall: str | None = None
    dist_to_nearest_hawker: float | None = Field(ge=0, default=None)
    nearest_hawker: str | None = None
    dist_to_nearest_supermarket: float | None = Field(ge=0, default=None)
    nearest_supermarket: str | None = None
    dist_to_nearest_park: float | None = Field(ge=0, default=None)
    nearest_park: str | None = None
    dist_to_nearest_childcare: float | None = Field(ge=0, default=None)
    nearest_childcare: str | None = None
    dist_to_nearest_kindergarten: float | None = Field(ge=0, default=None)
    nearest_kindergarten: str | None = None
    dist_to_nearest_bus_stop: float | None = Field(ge=0, default=None)
    nearest_bus_stop: str | None = None
    dist_to_nearest_chas_clinic: float | None = Field(ge=0, default=None)
    nearest_chas_clinic: str | None = None
    dist_to_nearest_sports_facility: float | None = Field(ge=0, default=None)
    nearest_sports_facility: str | None = None
    dist_to_nearest_community_club: float | None = Field(ge=0, default=None)
    nearest_community_club: str | None = None
    dist_to_nearest_green_mark_building: float | None = Field(ge=0, default=None)
    nearest_green_mark_building: str | None = None

    max_floor_lvl: float | None = Field(ge=0, default=None)
    year_completed: float | None = Field(ge=1900, default=None)
    total_dwelling_units: float | None = Field(ge=0, default=None)

    planning_area: str | None = None
    region: str | None = None


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

    dist_to_nearest_hawker: float | None = Field(ge=0, default=None)
    nearest_hawker: str | None = None

    dist_to_nearest_supermarket: float | None = Field(ge=0, default=None)
    nearest_supermarket: str | None = None

    dist_to_nearest_park: float | None = Field(ge=0, default=None)
    nearest_park: str | None = None

    dist_to_nearest_childcare: float | None = Field(ge=0, default=None)
    nearest_childcare: str | None = None

    dist_to_nearest_kindergarten: float | None = Field(ge=0, default=None)
    nearest_kindergarten: str | None = None

    dist_to_nearest_bus_stop: float | None = Field(ge=0, default=None)
    nearest_bus_stop: str | None = None

    dist_to_nearest_chas_clinic: float | None = Field(ge=0, default=None)
    nearest_chas_clinic: str | None = None

    dist_to_nearest_sports_facility: float | None = Field(ge=0, default=None)
    nearest_sports_facility: str | None = None

    dist_to_nearest_community_club: float | None = Field(ge=0, default=None)
    nearest_community_club: str | None = None

    dist_to_nearest_green_mark_building: float | None = Field(ge=0, default=None)
    nearest_green_mark_building: str | None = None

    rental_yield_pct: float | None = None

    cpi: float | None = None
    sora_rate: float | None = None
    sora_3m: float | None = None
    unemployment_rate: float | None = None
    gdp: float | None = None
    hdb_rpi: float | None = None
    ura_ppi: float | None = None

    max_floor_lvl: float | None = Field(ge=0, default=None)
    year_completed: float | None = Field(ge=1900, default=None)
    total_dwelling_units: float | None = Field(ge=0, default=None)

    median_monthly_income: float | None = Field(ge=0, default=None)

    dwelling_units_in_town: float | None = Field(ge=0, default=None)
    population_in_town: float | None = Field(ge=0, default=None)
    population_per_dwelling: float | None = Field(ge=0, default=None)
    annual_value: float | None = Field(ge=0, default=None)
    property_tax: float | None = Field(ge=0, default=None)
    wage_growth: float | None = None

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


class PlanningArea360(BaseModel):
    """Planning area 360-degree profile (~43 rows)."""

    planning_area: str
    region: str | None = None

    median_dist_to_mrt: float | None = None
    median_dist_to_school: float | None = None
    median_dist_to_mall: float | None = None
    median_dist_to_hawker: float | None = None
    median_dist_to_supermarket: float | None = None
    median_dist_to_park: float | None = None
    median_dist_to_childcare: float | None = None
    median_dist_to_kindergarten: float | None = None
    median_dist_to_bus_stop: float | None = None
    median_dist_to_chas_clinic: float | None = None
    median_dist_to_sports_facility: float | None = None
    median_dist_to_community_club: float | None = None
    median_dist_to_green_mark_building: float | None = None

    median_price: float | None = None
    median_psf: float | None = None
    transaction_volume: int | None = None
    median_rental_yield_pct: float | None = None

    avg_year_completed: float | None = None
    avg_max_floor: float | None = None
    total_dwelling_units: float | None = None

    median_monthly_income: float | None = None

    cpi: float | None = None
    sora_3m: float | None = None
    unemployment_rate: float | None = None
    gdp: float | None = None


class Town360(BaseModel):
    """Town 360-degree profile (~27 rows)."""

    town: str

    median_price: float | None = None
    median_psf: float | None = None
    transaction_volume: int | None = None

    dwelling_units_in_town: float | None = None
    population_in_town: float | None = None
    population_per_dwelling: float | None = None

    annual_value_3_room: float | None = Field(ge=0, default=None)
    annual_value_4_room: float | None = Field(ge=0, default=None)
    annual_value_5_room: float | None = Field(ge=0, default=None)
    property_tax_3_room: float | None = Field(ge=0, default=None)
    property_tax_4_room: float | None = Field(ge=0, default=None)
    property_tax_5_room: float | None = Field(ge=0, default=None)


class BlockProfile(BaseModel):
    """Per-block transaction profile (~10K rows)."""

    block: str
    street_name: str
    town: str | None = None

    median_price: float | None = None
    median_psf: float | None = None
    transaction_count: int | None = None
    avg_remaining_lease_years: float | None = None
