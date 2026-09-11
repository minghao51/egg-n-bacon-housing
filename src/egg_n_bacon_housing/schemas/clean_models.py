"""Cleaned data schemas (Silver layer - validated with pydantic at boundary)."""

from datetime import datetime
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field

# Dataset floor: HDB resale records begin 1990-01. Earlier transaction dates
# are implausible for this dataset and are quarantined at validation time.
_DATASET_EARLIEST_TRANSACTION = datetime(1990, 1, 1)


class HCleanTransactionBase(BaseModel):
    """Base validated transaction fields.

    lat/lon are optional here because geocoding happens in a later pipeline stage
    (geocoded_properties). These fields are added downstream before analytics.
    """

    transaction_date: Annotated[datetime, Field(ge=_DATASET_EARLIEST_TRANSACTION)]
    price: Annotated[float, Field(gt=0)]
    lat: Annotated[float, Field(ge=-90, le=90)] | None = None
    lon: Annotated[float, Field(ge=-180, le=180)] | None = None
    property_type: Annotated[str, Field(min_length=1)]
    property_subtype: str | None = None
    property_segment: str | None = None
    is_ec: bool = False
    planning_area: str | None = None


class HCleanHDBTransaction(HCleanTransactionBase):
    """Validated HDB transaction.

    storey_min/max and address are optional here because storey_range parsing
    and address construction happen in downstream feature engineering stages.
    remaining_lease_months can be computed from lease_commence_date if missing.
    """

    catalog_dataset_id: ClassVar[str] = "hdb_validated"

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

    catalog_dataset_id: ClassVar[str] = "condo_validated"

    project_name: str
    area: str
    postal_district: int
    tenure: str
    floor_area_sqm: Annotated[float, Field(gt=0)]
    floor_area_sqft: Annotated[float, Field(gt=0)]
    address: str


class GeocodedProperty(BaseModel):
    """Validated geocoded property record.

    The address/coordinate fields are geocoding outputs; the optional
    transaction fields below are the pass-through columns downstream gold
    nodes consume (location_dim carry columns, transactions_enriched
    area/psf/month joins). They are Optional because the frame is the union
    of HDB rows (which carry them) and condo rows (which do not).
    """

    catalog_dataset_id: ClassVar[str] = "geocoded_validated"

    address: str | None = None
    lat: Annotated[float, Field(ge=-90, le=90)] | None = None
    lon: Annotated[float, Field(ge=-180, le=180)] | None = None
    property_type: Annotated[str, Field(min_length=1)]
    property_subtype: str | None = None
    property_segment: str | None = None
    is_ec: bool = False
    postal_code: str | None = None
    block: str | None = None
    street_name: str | None = None
    town: str | None = None
    flat_type: str | None = None
    floor_area_sqm: float | None = Field(default=None, gt=0)
    floor_area_sqft: float | None = Field(default=None, gt=0)
    month: str | None = None
