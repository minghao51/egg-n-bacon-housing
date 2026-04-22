"""Cleaned data schemas (Silver layer - validated with pydantic at boundary)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class HCleanTransactionBase(BaseModel):
    """Base validated transaction fields.

    lat/lon are optional here because geocoding happens in a later pipeline stage
    (geocoded_properties). These fields are added downstream before analytics.
    """

    transaction_date: datetime
    price: Annotated[float, Field(gt=0)]
    lat: Annotated[float, Field(ge=-90, le=90)] | None = None
    lon: Annotated[float, Field(ge=-180, le=180)] | None = None
    property_type: str
    planning_area: str | None = None


class HCleanHDBTransaction(HCleanTransactionBase):
    """Validated HDB transaction.

    storey_min/max and address are optional here because storey_range parsing
    and address construction happen in downstream feature engineering stages.
    remaining_lease_months can be computed from lease_commence_date if missing.
    """

    town: str
    flat_type: str
    block: str
    street_name: str
    storey_min: int | None = None
    storey_max: int | None = None
    floor_area_sqm: Annotated[float, Field(gt=0)]
    floor_area_sqft: Annotated[float, Field(gt=0)]
    remaining_lease_months: Annotated[int, Field(ge=0)] | None = None
    address: str | None = None


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
    """Validated geocoded property record.

    lat/lon are optional here because the geocoding adapter may not have
    coordinates available (e.g., HDB blocks use block+street for geocoding).
    They are added in subsequent feature stages.
    """

    address: str | None = None
    lat: Annotated[float, Field(ge=-90, le=90)] | None = None
    lon: Annotated[float, Field(ge=-180, le=180)] | None = None
    property_type: str
    postal_code: str | None = None
    search_confidence: float | None = Field(default=None, le=1.0, ge=0)
