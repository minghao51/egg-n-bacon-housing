"""Bronze layer ingestion package.

Re-exports all Hamilton DAG nodes from submodules so that
``from egg_n_bacon_housing.components import ingestion`` discovers every node
exactly as the old monolithic ``ingestion.py`` did.
"""

from egg_n_bacon_housing.components.ingestion.datagov import (
    geocoded_green_mark_buildings,
    raw_dataset,
    raw_dwelling_units_by_town,
    raw_green_mark_buildings,
    raw_hdb_property_info,
    raw_hdb_resale_transactions,
    raw_hdb_resident_population,
    raw_income_by_planning_area,
    raw_median_annual_value,
    raw_shopping_malls,
)
from egg_n_bacon_housing.components.ingestion.geojson import (
    raw_bus_stops,
    raw_chas_clinics,
    raw_childcare,
    raw_community_clubs,
    raw_hawker_centres,
    raw_kindergartens,
    raw_mrt_stations,
    raw_parks,
    raw_sports_facilities,
    raw_supermarkets,
)
from egg_n_bacon_housing.components.ingestion.macro import raw_macro_data
from egg_n_bacon_housing.components.ingestion.ura_csv import raw_condo_transactions

__all__ = [
    "geocoded_green_mark_buildings",
    "raw_bus_stops",
    "raw_chas_clinics",
    "raw_childcare",
    "raw_community_clubs",
    "raw_condo_transactions",
    "raw_dataset",
    "raw_dwelling_units_by_town",
    "raw_green_mark_buildings",
    "raw_hawker_centres",
    "raw_hdb_property_info",
    "raw_hdb_resale_transactions",
    "raw_hdb_resident_population",
    "raw_income_by_planning_area",
    "raw_kindergartens",
    "raw_macro_data",
    "raw_median_annual_value",
    "raw_mrt_stations",
    "raw_parks",
    "raw_shopping_malls",
    "raw_sports_facilities",
    "raw_supermarkets",
]
