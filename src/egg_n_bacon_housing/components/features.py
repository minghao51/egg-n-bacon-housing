"""Features: Gold layer feature engineering (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing features
from silver data into the gold layer.
"""

import inspect
import logging

import pandas as pd
from hamilton.function_modifiers import extract_fields, hamilton_exclude

from egg_n_bacon_housing.schemas.feature_models import LocationDimRecord
from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.geocoding import Geocoder
from egg_n_bacon_housing.utils.proximity import compute_proximity_features
from egg_n_bacon_housing.utils.regional_mapping import PLANNING_AREA_TO_REGION
from egg_n_bacon_housing.utils.runtime import MrtReference, SchoolReference, SpatialReference
from egg_n_bacon_housing.utils.school_features import (
    QUALITY_FEATURE_COLUMNS,
    _geocode_schools,
    calculate_school_features,
    calculate_school_quality_features,
)
from egg_n_bacon_housing.utils.validation_gateway import (
    empty_extracted,
    extracted_validation,
    validate_and_quarantine,
)

logger = logging.getLogger(__name__)


@hamilton_exclude
def location_dim(*args, **kwargs) -> pd.DataFrame:
    return validate_location_dim(*args, **kwargs)["location_dim"]


def _add_planning_area(
    df: pd.DataFrame, spatial_reference: SpatialReference | None = None
) -> pd.DataFrame:
    """Derive planning_area from lat/lon via point-in-polygon on unique coords.

    Derives only for rows whose planning_area is null and leaves populated
    values untouched (previously the whole frame was re-derived only when no
    row had a planning_area, so a single non-null value froze derivation for
    every remaining row).
    """
    if "lat" not in df.columns or "lon" not in df.columns:
        return df

    if "planning_area" in df.columns:
        null_mask = df["planning_area"].isna()
    else:
        null_mask = pd.Series(True, index=df.index)
    if not bool(null_mask.any()):
        return df

    to_derive = df.loc[null_mask, ["lat", "lon"]]
    unique_coords = to_derive.drop_duplicates(subset=["lat", "lon"])
    if unique_coords.empty:
        return df

    if spatial_reference is None:
        logger.warning("No spatial reference injected — skipping planning_area derivation")
        return df

    logger.info(
        "Deriving planning_area for %s null row(s) (%s unique coordinates)",
        len(to_derive),
        len(unique_coords),
    )

    # Single batched spatial join over the unique coordinates (vectorized)
    # instead of a per-row iterrows() + apply() loop.
    pa_names = spatial_reference.planning_areas_for_points(
        unique_coords["lat"], unique_coords["lon"]
    )
    lookup = unique_coords.assign(planning_area=pa_names.to_numpy())

    # Anti-join style: resolve the lookup into only the null rows, then write
    # the derived values back — existing planning_area values are preserved.
    derived = to_derive.merge(lookup, on=["lat", "lon"], how="left")
    df = df.copy()
    if "planning_area" not in df.columns:
        df["planning_area"] = pd.NA
    df.loc[null_mask, "planning_area"] = derived["planning_area"].to_numpy()

    filled = int(derived["planning_area"].notna().sum())
    logger.info(
        "planning_area derived: %s/%s null row(s) filled (%.1f%%)",
        filled,
        len(to_derive),
        filled / len(to_derive) * 100 if len(to_derive) else 0,
    )
    return df


@extract_fields({"location_dim": pd.DataFrame, "location_dim_quarantine": pd.DataFrame})
def validate_location_dim(
    geocoded_validated: pd.DataFrame,
    raw_mrt_stations: pd.DataFrame,
    raw_school_directory: pd.DataFrame,
    raw_shopping_malls: pd.DataFrame,
    raw_hawker_centres: pd.DataFrame,
    raw_supermarkets: pd.DataFrame,
    raw_parks: pd.DataFrame,
    raw_childcare: pd.DataFrame,
    raw_kindergartens: pd.DataFrame,
    raw_bus_stops: pd.DataFrame,
    raw_chas_clinics: pd.DataFrame,
    raw_sports_facilities: pd.DataFrame,
    raw_community_clubs: pd.DataFrame,
    geocoded_green_mark_buildings: pd.DataFrame,
    raw_hdb_property_info: pd.DataFrame,
    geocoder: Geocoder,
    mrt_reference: MrtReference | None = None,
    spatial_reference: SpatialReference | None = None,
    school_reference: SchoolReference | None = None,
) -> dict[str, pd.DataFrame]:
    """Build the location dimension table — one row per unique (lat, lon).

    Computes ALL proximity features, school scores, block metadata, and
    planning_area on ~10K unique locations instead of 1M transactions.
    """
    if geocoded_validated.empty:
        return empty_extracted(geocoded_validated, "location_dim", "location_dim_quarantine")

    df = geocoded_validated.copy()
    require_columns(df, {"lat", "lon"}, "geocoded_validated")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    pre_coord_filter = len(df)
    df = df.dropna(subset=["lat", "lon"])
    dropped_no_coords = pre_coord_filter - len(df)
    if dropped_no_coords:
        # Benign hygiene, not a population cut: the (lat, lon)-keyed dimension
        # cannot hold null coordinates, transactions re-join it with a left
        # merge (no rows lost), and coordinate coverage is separately gated
        # at the silver boundary — this count is the drift tripwire.
        logger.info(
            "location_dim: %s/%s row(s) without usable lat/lon excluded from the "
            "(lat, lon) dimension; kept %s",
            dropped_no_coords,
            pre_coord_filter,
            len(df),
        )

    if df.empty:
        return empty_extracted(geocoded_validated, "location_dim", "location_dim_quarantine")

    carry_cols = [c for c in ("block", "street_name", "town") if c in df.columns]
    loc = (
        df.drop_duplicates(subset=["lat", "lon"], keep="first")[["lat", "lon", *carry_cols]]
        .reset_index(drop=True)
        .copy()
    )
    logger.info("location_dim: %s unique (lat, lon) pairs", len(loc))

    # --- School features ---
    if not raw_school_directory.empty:
        schools = raw_school_directory
        if "latitude" not in schools.columns or schools["latitude"].isna().all():
            logger.info("School directory lacks lat/lon — geocoding via OneMap...")
            schools = _geocode_schools(schools, geocoder)
        loc = calculate_school_features(loc, schools)
        school_distance_cols = [
            col
            for col in [
                "nearest_schoolPRIMARY_dist",
                "nearest_schoolSECONDARY_dist",
                "nearest_schoolJUNIOR_dist",
            ]
            if col in loc.columns
        ]
        if school_distance_cols:
            loc["dist_to_nearest_school"] = loc[school_distance_cols].min(axis=1, skipna=True)
        else:
            # calculate_school_features returns without the per-level columns
            # when no geocoded schools exist — keep the column contract stable.
            loc["dist_to_nearest_school"] = pd.NA

        # --- School quality features (tier-weighted; methodology in
        # data/manual/csv/school_scoring_methodology.md) ---
        primary_tiers: pd.DataFrame | None = None
        secondary_tiers: pd.DataFrame | None = None
        if school_reference is not None:
            primary_tiers, secondary_tiers = school_reference.load_school_tiers()
        if (
            primary_tiers is not None
            and secondary_tiers is not None
            and not (primary_tiers.empty and secondary_tiers.empty)
        ):
            loc = calculate_school_quality_features(loc, schools, primary_tiers, secondary_tiers)
        else:
            # Manual tier files are R2-synced and may be absent — degrade to
            # NA columns rather than failing the run (income-source pattern).
            for col in QUALITY_FEATURE_COLUMNS:
                loc[col] = pd.NA
            logger.warning(
                "location_dim: school tier data unavailable (school_reference=%s) "
                "— school quality features degrade to NA",
                "injected" if school_reference is not None else "not injected",
            )

    # --- Proximity features (all 14 POI types) ---
    try:
        loc = compute_proximity_features(
            loc,
            mrt_stations=raw_mrt_stations if not raw_mrt_stations.empty else None,
            malls=raw_shopping_malls if not raw_shopping_malls.empty else None,
            hawkers=raw_hawker_centres if not raw_hawker_centres.empty else None,
            supermarkets=raw_supermarkets if not raw_supermarkets.empty else None,
            parks=raw_parks if not raw_parks.empty else None,
            childcare=raw_childcare if not raw_childcare.empty else None,
            kindergartens=raw_kindergartens if not raw_kindergartens.empty else None,
            bus_stops=raw_bus_stops if not raw_bus_stops.empty else None,
            chas_clinics=raw_chas_clinics if not raw_chas_clinics.empty else None,
            sports_facilities=raw_sports_facilities if not raw_sports_facilities.empty else None,
            community_clubs=raw_community_clubs if not raw_community_clubs.empty else None,
            green_mark_buildings=(
                geocoded_green_mark_buildings if not geocoded_green_mark_buildings.empty else None
            ),
            mrt_reference=mrt_reference,
        )
    except (ValueError, KeyError) as exc:
        # Narrowed to the verified source failures raised inside
        # compute_proximity_features: malformed source coordinates raise
        # ValueError (BallTree rejects NaN/inf; astype(float) rejects
        # unparseable strings), and a bronze MRT frame without lat/lon
        # columns raises KeyError (the legacy raw_mrt_stations path returns
        # name/line-only frames when the GeoJSON is missing). Programming
        # errors (TypeError, IndexError, ...) propagate to the surface.
        logger.warning(
            "Proximity features degraded to NA columns (%s: %s)",
            type(exc).__name__,
            exc,
        )
        loc["dist_to_nearest_mrt"] = pd.NA
        loc["nearest_mrt_station"] = pd.NA
        for label in (
            "mall",
            "hawker",
            "supermarket",
            "park",
            "childcare",
            "kindergarten",
            "bus_stop",
            "chas_clinic",
            "sports_facility",
            "community_club",
            "green_mark_building",
        ):
            loc[f"dist_to_nearest_{label}"] = pd.NA
            loc[f"nearest_{label}"] = pd.NA

    # --- Block metadata from HDB Property Info ---
    if not raw_hdb_property_info.empty and "block" in loc.columns and "street_name" in loc.columns:
        prop = raw_hdb_property_info.copy()
        prop["blk_no"] = prop["blk_no"].astype(str).str.strip().str.upper()
        prop["street"] = prop["street"].astype(str).str.strip().str.upper()

        loc["_join_block"] = loc["block"].astype(str).str.strip().str.upper()
        loc["_join_street"] = loc["street_name"].astype(str).str.strip().str.upper()

        prop_lookup = prop[
            [
                "blk_no",
                "street",
                "max_floor_lvl",
                "year_completed",
                "total_dwelling_units",
                "residential",
                "commercial",
                "market_hawker",
                "multistorey_carpark",
            ]
        ].copy()
        prop_lookup = prop_lookup.rename(
            columns={"blk_no": "_join_block", "street": "_join_street"}
        )
        for col in ("max_floor_lvl", "year_completed", "total_dwelling_units"):
            if col in prop_lookup.columns:
                prop_lookup[col] = pd.to_numeric(prop_lookup[col], errors="coerce")
        prop_lookup = prop_lookup.drop_duplicates(
            subset=["_join_block", "_join_street"], keep="first"
        )

        loc = loc.merge(prop_lookup, on=["_join_block", "_join_street"], how="left")
        loc = loc.drop(columns=["_join_block", "_join_street"], errors="ignore")

        matched = loc["year_completed"].notna().sum() if "year_completed" in loc.columns else 0
        logger.info(
            "location_dim block metadata: %s/%s (%.1f%%) matched",
            matched,
            len(loc),
            matched / len(loc) * 100 if len(loc) else 0,
        )

    for col in (
        "max_floor_lvl",
        "year_completed",
        "total_dwelling_units",
        "residential",
        "commercial",
        "market_hawker",
        "multistorey_carpark",
    ):
        if col not in loc.columns:
            loc[col] = pd.NA

    # --- Planning area + region ---
    loc = _add_planning_area(loc, spatial_reference)
    if "planning_area" in loc.columns:
        # Vectorized region derivation — same semantics as the per-row
        # get_region_for_planning_area apply it replaces: strip + upper +
        # dict lookup, with unknown and null planning areas passing through
        # as None (never a wrong region).
        pa_keys = loc["planning_area"].astype("string").str.strip().str.upper()
        region = pa_keys.map(PLANNING_AREA_TO_REGION)
        loc["region"] = region.astype(object).where(region.notna(), None)

    return extracted_validation(
        validate_and_quarantine(loc, LocationDimRecord, "location_dim"),
        "location_dim",
        "location_dim_quarantine",
    )


# Keep the excluded direct-call facade introspectable for callers that inspect
# the Hamilton boundary's dependency seam.  Hamilton itself discovers the
# explicitly typed ``validate_location_dim`` node above.
location_dim.__signature__ = inspect.signature(validate_location_dim)
