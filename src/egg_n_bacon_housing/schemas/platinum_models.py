"""Published platinum schemas (validated with pydantic at the boundary)."""

from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field

from egg_n_bacon_housing.schemas.feature_models import HFeatureTransaction

# Month keys are Period("M").astype(str) — e.g. "2024-01" (utils.time_index).
_MONTH_PATTERN = r"^\d{4}-\d{2}$"


class HUnifiedRecord(HFeatureTransaction):
    """Published unified transaction record (platinum layer).

    Same grain as the gold fact table (one row per source transaction) and
    the same field contract; kept as a separate model so the platinum
    contract can diverge from gold later.
    """

    catalog_dataset_id: ClassVar[str] = "unified_dataset"


class PaMonthlyMetric(BaseModel):
    """Planning-area x month metrics (~5K rows, platinum_metrics layer)."""

    catalog_dataset_id: ClassVar[str] = "pa_monthly_metrics"

    planning_area: str
    month: Annotated[str, Field(pattern=_MONTH_PATTERN)]

    median_price: Annotated[float, Field(gt=0)]
    mean_price: Annotated[float, Field(gt=0)]
    transaction_count: Annotated[int, Field(ge=0)]

    # Conditionally present columns in the node output — nulls legitimately occur.
    avg_psf: Annotated[float, Field(gt=0)] | None = None
    median_rental_yield: float | None = None
    avg_rental_yield: float | None = None
    median_monthly_income: Annotated[float, Field(ge=0)] | None = None

    affordability_ratio: Annotated[float, Field(gt=0)]
    affordability_class: Literal["Affordable", "Moderate", "Expensive", "Severely Unaffordable"]


class AppreciationHotspot(BaseModel):
    """Appreciation hotspot ranking rows (top 20, platinum_metrics layer)."""

    catalog_dataset_id: ClassVar[str] = "appreciation_hotspots"

    planning_area: str
    month: Annotated[str, Field(pattern=_MONTH_PATTERN)]

    median_price: Annotated[float, Field(gt=0)]
    appreciation_3m_pct: float
    # Null until 12 months of history exist for the planning area.
    appreciation_12m_pct: float | None = None
    is_declining: bool
