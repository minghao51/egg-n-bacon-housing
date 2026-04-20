"""Cleaned data schemas (Silver layer - validated with pydantic at boundary)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class HCleanTransactionBase(BaseModel):
    """Base validated transaction fields."""

    transaction_date: datetime
    price: Annotated[float, Field(gt=0)]
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]
    property_type: str
    planning_area: str | None = None


class HCleanHDBTransaction(HCleanTransactionBase):
    """Validated HDB transaction."""

    town: str
    flat_type: str
    block: str
    street_name: str
    storey_min: int
    storey_max: int
    floor_area_sqm: Annotated[float, Field(gt=0)]
    floor_area_sqft: Annotated[float, Field(gt=0)]
    remaining_lease_months: Annotated[int, Field(ge=0)]
    address: str


class HCleanCondoTransaction(HCleanTransactionBase):
    """Validated condo transaction."""

    project_name: str
    area: str
    postal_district: int
    tenure: str
    floor_area_sqm: Annotated[float, Field(gt=0)]
    floor_area_sqft: Annotated[float, Field(gt=0)]
    address: str


class HCleanECTransaction(HCleanTransactionBase):
    """Validated EC transaction."""

    project_name: str
    area: str
    postal_district: int
    tenure: str
    floor_area_sqm: Annotated[float, Field(gt=0)]
    floor_area_sqft: Annotated[float, Field(gt=0)]
    address: str


class HCleanRentalRecord(BaseModel):
    """Validated rental record."""

    date: datetime
    property_type: str
    area: str
    rental_price: Annotated[float, Field(gt=0)]
    tenure: str


class GeocodedProperty(BaseModel):
    """Validated geocoded property record."""

    address: str
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]
    property_type: str
    postal_code: str | None = None
    search_confidence: float | None = Field(default=1.0, le=1.0, ge=0)
