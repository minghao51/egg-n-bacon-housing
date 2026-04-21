"""Raw data schemas (Bronze layer - no validation, just structure hints)."""

from pydantic import BaseModel


class RawTransactionBase(BaseModel):
    """Base fields for raw transaction data."""

    transaction_date: str | None = None
    price: float | None = None
    property_type: str | None = None
    address: str | None = None


class RawHDBTransaction(RawTransactionBase):
    """Raw HDB transaction from data.gov.sg."""

    town: str | None = None
    flat_type: str | None = None
    block: str | None = None
    street_name: str | None = None
    storey_range: str | None = None
    floor_area_sqm: float | None = None
    floor_area_sqft: float | None = None
    remaining_lease_months: int | None = None
    resale_price: float | None = None


class RawCondoTransaction(RawTransactionBase):
    """Raw condo transaction from URA."""

    project_name: str | None = None
    area: str | None = None
    market_segment: str | None = None
    postal_district: int | None = None
    tenure: str | None = None
    area_sqm: float | None = None
    area_sqft: float | None = None


class RawECTransaction(RawTransactionBase):
    """Raw EC transaction from URA."""

    project_name: str | None = None
    area: str | None = None
    market_segment: str | None = None
    postal_district: int | None = None
    tenure: str | None = None
    area_sqm: float | None = None
    area_sqft: float | None = None


class RawRentalRecord(BaseModel):
    """Raw rental record."""

    date: str | None = None
    property_type: str | None = None
    area: str | None = None
    rental_price: float | None = None
    tenure: str | None = None


class RawSchoolRecord(BaseModel):
    """Raw school directory entry."""

    school_name: str | None = None
    school_code: str | None = None
    address: str | None = None
    postal_code: str | None = None
    lat: float | None = None
    lon: float | None = None
    type: str | None = None
    nature: str | None = None
    priority: str | None = None


class RawMallRecord(BaseModel):
    """Raw shopping mall entry."""

    name: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    mall_type: str | None = None


class RawMacroData(BaseModel):
    """Raw macro economic indicator."""

    indicator: str | None = None
    date: str | None = None
    value: float | None = None
    source: str | None = None
