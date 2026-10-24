"""Cleaning: Silver layer cleaning and validation (Hamilton DAG node).

This module provides Hamilton-compatible functions for cleaning and
validating bronze data into the silver layer.
"""

import logging
from typing import Literal, NamedTuple

import pandas as pd
from hamilton.function_modifiers import extract_fields, hamilton_exclude

from egg_n_bacon_housing.schemas.clean_models import (
    GeocodedProperty,
    HCleanCondoTransaction,
    HCleanHDBTransaction,
)
from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.geocoding import Geocoder, plausible_project_match
from egg_n_bacon_housing.utils.hdb_lookups import SQFT_PER_SQM
from egg_n_bacon_housing.utils.validation_gateway import (
    extracted_validation,
    validate_and_quarantine,
)

logger = logging.getLogger(__name__)


@hamilton_exclude
def hdb_validated(cleaned_hdb_transactions: pd.DataFrame) -> pd.DataFrame:
    """Direct-call view of the validated Hamilton output."""
    return validate_hdb(cleaned_hdb_transactions)["hdb_validated"]


@hamilton_exclude
def condo_validated(cleaned_condo_transactions: pd.DataFrame) -> pd.DataFrame:
    return validate_condo(cleaned_condo_transactions)["condo_validated"]


@hamilton_exclude
def geocoded_validated(geocoded_properties: pd.DataFrame) -> pd.DataFrame:
    return validate_geocoded(geocoded_properties)["geocoded_validated"]


class SegmentCoverage(NamedTuple):
    """Geocode coverage for one property-type segment."""

    segment: str
    coverage: float
    threshold: float
    rows: int


def _filter_invalid_rows(df: pd.DataFrame, node: str) -> pd.DataFrame:
    """Drop rows with null price/transaction_date or non-positive price.

    Every filter on the silver boundary announces its dropped-row count so
    source drift shows up in logs instead of quietly shrinking the data.
    """
    pre_filter = len(df)
    df = df.dropna(subset=["price", "transaction_date"])
    dropped_nulls = pre_filter - len(df)
    if dropped_nulls:
        logger.warning(
            "%s: dropped %s row(s) with null price/transaction_date", node, dropped_nulls
        )

    df = df[df["price"] > 0]
    dropped_nonpositive = pre_filter - dropped_nulls - len(df)
    if dropped_nonpositive:
        logger.warning("%s: dropped %s row(s) with non-positive price", node, dropped_nonpositive)
    return df


def _per_type_coverage(
    combined: pd.DataFrame,
    min_coordinate_coverage: float,
    min_coordinate_coverage_hdb: float,
    min_coordinate_coverage_condo: float,
) -> list[SegmentCoverage]:
    """Per-property-type geocode coverage with its applicable threshold.

    HDB and condo get dedicated thresholds; any other property type falls
    back to the legacy ``min_coordinate_coverage`` gate.
    """
    thresholds = {
        "hdb": min_coordinate_coverage_hdb,
        "condo": min_coordinate_coverage_condo,
    }
    segments: list[SegmentCoverage] = []
    for segment, rows in combined.groupby("property_type", observed=True):
        coverage = rows[["lat", "lon"]].notna().all(axis=1).mean()
        segments.append(
            SegmentCoverage(
                segment=str(segment),
                coverage=float(coverage),
                threshold=thresholds.get(str(segment), min_coordinate_coverage),
                rows=len(rows),
            )
        )
    return segments


_PRIVATE_PROPERTY_SEGMENTS = {
    "condominium": "condominium",
    "apartment": "apartment",
    "executive condominium": "ec",
    "detached house": "detached_house",
    "semi-detached house": "semi_detached_house",
    "terrace house": "terrace_house",
}


def cleaned_hdb_transactions(raw_hdb_resale_transactions: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate HDB resale transactions.

    Args:
        raw_hdb_resale_transactions: Raw bronze data.

    Returns:
        Cleaned DataFrame with validated fields.
    """
    if raw_hdb_resale_transactions.empty:
        return pd.DataFrame()

    df = raw_hdb_resale_transactions.copy()

    if "resale_price" in df.columns:
        df = df.rename(columns={"resale_price": "price"})

    # Derivation-critical contract: each column feeds a derived silver field
    # or a downstream join key. A missing source column must fail loudly
    # rather than silently degrade features (e.g. all-NaN psf).
    require_columns(
        df,
        {"month", "price", "floor_area_sqm", "town", "flat_type"},
        "raw_hdb_resale_transactions",
    )

    if "floor_area_sqm" in df.columns and "floor_area_sqft" not in df.columns:
        df["floor_area_sqft"] = df["floor_area_sqm"] * SQFT_PER_SQM

    if "month" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")

    if "property_type" not in df.columns:
        df["property_type"] = "hdb"

    if (
        "remaining_lease_months" in df.columns
        and "lease_commence_date" in df.columns
        and "transaction_date" in df.columns
    ):
        mask = df["remaining_lease_months"].isna()
        if mask.any():
            lease_commence_year = pd.to_numeric(
                df.loc[mask, "lease_commence_date"], errors="coerce"
            )
            transaction_year = pd.to_numeric(
                df.loc[mask, "transaction_date"].dt.year,
                errors="coerce",
            )
            remaining_lease_years = 99 - (transaction_year - lease_commence_year)
            df.loc[mask, "remaining_lease_months"] = (remaining_lease_years * 12).clip(lower=0)

    if "storey_range" in df.columns and "storey_min" not in df.columns:
        storey_parts = df["storey_range"].str.split(" TO ", n=1, expand=True)
        df["storey_min"] = pd.to_numeric(storey_parts[0], errors="coerce").astype("Int64")
        df["storey_max"] = pd.to_numeric(storey_parts[1], errors="coerce").astype("Int64")

    if "address" not in df.columns and "block" in df.columns and "street_name" in df.columns:
        df["address"] = df["block"] + " " + df["street_name"]

    return _filter_invalid_rows(df, "cleaned_hdb_transactions")


@extract_fields({"hdb_validated": pd.DataFrame, "hdb_quarantine": pd.DataFrame})
def validate_hdb(cleaned_hdb_transactions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Validate HDB transactions against schema.

    Validation only — persistence is owned by ``materialize_hdb_validated``.
    """
    result = validate_and_quarantine(cleaned_hdb_transactions, HCleanHDBTransaction, "HDB")
    if not result["rejected"].empty:
        logger.warning(
            "hdb_validated: %s row(s) quarantined at the silver boundary",
            len(result["rejected"]),
        )
    return extracted_validation(
        result,
        "hdb_validated",
        "hdb_quarantine",
    )


def cleaned_condo_transactions(raw_condo_transactions: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate condo transactions.

    Args:
        raw_condo_transactions: Raw bronze data.

    Returns:
        Cleaned DataFrame.
    """
    if raw_condo_transactions.empty:
        return pd.DataFrame()

    df = raw_condo_transactions.copy()

    # Derivation-critical contract, mirroring the HDB side. The bronze URA
    # contract (docs/guides/data-ingestion-development.md) guarantees
    # transaction_date (API + CSV paths normalize to it), price, and
    # street_name (the address substrate condo geocoding runs on).
    require_columns(
        df,
        {"price", "transaction_date", "street_name"},
        "raw_condo_transactions",
    )

    # Schema parity with the HDB side: monthly aggregations key on "month".
    if "month" not in df.columns and "transaction_date" in df.columns:
        df["month"] = pd.to_datetime(df["transaction_date"], errors="coerce").dt.strftime("%Y-%m")

    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    if "area_sqft" in df.columns and "floor_area_sqft" not in df.columns:
        df["floor_area_sqft"] = pd.to_numeric(df["area_sqft"], errors="coerce")

    if "area_sqm" in df.columns and "floor_area_sqm" not in df.columns:
        df["floor_area_sqm"] = pd.to_numeric(df["area_sqm"], errors="coerce")

    if "postal_district" in df.columns:
        df["postal_district"] = pd.to_numeric(df["postal_district"], errors="coerce").astype(
            "Int64"
        )

    if "address" not in df.columns:
        if "street_name" in df.columns:
            df["address"] = df["street_name"].fillna("")
        else:
            df["address"] = ""

    if "area" not in df.columns:
        df["area"] = ""

    if "project_name" not in df.columns:
        df["project_name"] = ""

    if "tenure" not in df.columns:
        df["tenure"] = ""

    subtype = (
        df["property_subtype"].astype("string").str.strip()
        if "property_subtype" in df.columns
        else pd.Series(pd.NA, index=df.index, dtype="string")
    )
    subtype_key = subtype.str.casefold()
    segment = subtype_key.map(_PRIVATE_PROPERTY_SEGMENTS)
    missing_subtype = subtype.isna() | subtype.eq("")
    df["property_subtype"] = subtype.mask(missing_subtype, pd.NA)
    df["property_segment"] = segment.mask(
        missing_subtype, "private_residential_unspecified"
    ).fillna("other_private_residential")
    df["is_ec"] = df["property_segment"].eq("ec")

    return _filter_invalid_rows(df, "cleaned_condo_transactions")


@extract_fields({"condo_validated": pd.DataFrame, "condo_quarantine": pd.DataFrame})
def validate_condo(cleaned_condo_transactions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Validate condo transactions against schema.

    Validation only — persistence is owned by ``materialize_condo_validated``.
    """
    return extracted_validation(
        validate_and_quarantine(cleaned_condo_transactions, HCleanCondoTransaction, "condo"),
        "condo_validated",
        "condo_quarantine",
    )


def geocoded_properties(
    hdb_validated: pd.DataFrame,
    condo_validated: pd.DataFrame,
    geocoder: Geocoder,
    min_coordinate_coverage: float = 0.7,
    coordinate_coverage_policy: Literal["fail", "warn"] = "fail",
    min_coordinate_coverage_hdb: float = 0.7,
    min_coordinate_coverage_condo: float = 0.3,
) -> pd.DataFrame:
    """Merge validated transactions and geocode addresses via OneMap.

    HDB rows geocode exactly as before: the persisted ``block + street``
    address column is both the geocode query and the cache key, in a single
    pass. Condo rows (no postal codes, street-only addresses) use a two-pass
    strategy:

    1. Pass 1 geocodes project-aware queries ``"{project_name} {address}
       Singapore"`` and accepts only plausibility-checked results (variant-
       tolerant project-token containment of the matched name/address plus
       street-name corroboration of the matched address; see
       ``plausible_project_match``) — road-name queries otherwise collapse
       whole projects onto a point ON the road.
    2. Pass 2 re-geocodes everything still missing (project misses,
       implausible matches, rows without a project name) with the legacy
       street-only address string and fills from that.

    The project-aware string is a geocode QUERY only: the persisted
    ``address`` column values are never modified (schema stability).

    Always geocodes the full unique-query set; the geocoder itself is
    cache-first (OneMap address cache, ``utils/geocoding.py``), so repeat
    runs only hit the API for queries not seen before. This node returns
    an in-memory frame only; persistence happens once, in
    ``materialize_geocoded_validated``.

    Args:
        hdb_validated: Validated HDB transactions.
        condo_validated: Validated condo transactions.
        geocoder: Cache-first geocoder (OneMap address cache).
        min_coordinate_coverage: Legacy coverage threshold, applied to
            property-type segments without a dedicated gate.
        coordinate_coverage_policy: "fail" raises listing each failing
            segment with its coverage; "warn" warns per failing segment.
        min_coordinate_coverage_hdb: Coverage gate for the hdb segment
            (strict — block + street substrate geocodes reliably).
        min_coordinate_coverage_condo: Coverage gate for the condo segment
            (lenient — street-only addresses geocode worse).

    Returns:
        DataFrame with lat/lon coordinates.
    """

    dfs = []
    for df, ptype in [(hdb_validated, "hdb"), (condo_validated, "condo")]:
        if df.empty:
            continue
        df = df.copy()
        df["property_type"] = ptype
        if ptype == "hdb":
            df["property_segment"] = "hdb"
            df["is_ec"] = False
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    address_col = "address" if "address" in combined.columns else None
    if address_col is None:
        combined["lat"] = pd.NA
        combined["lon"] = pd.NA
        logger.warning("No address column found — skipping geocoding")
        return combined

    combined["lat"] = float("nan")
    combined["lon"] = float("nan")

    is_hdb = combined["property_type"].eq("hdb")
    hdb_rows = combined.index[is_hdb]
    if len(hdb_rows):
        unique_addresses = (
            combined.loc[hdb_rows, address_col].dropna().astype(str).unique().tolist()
        )
        logger.info("Geocoding %s unique HDB addresses...", len(unique_addresses))
        lookup = geocoder.geocode(pd.Series(unique_addresses, name=address_col))
        coord_map = lookup.set_index("input")[["lat", "lon"]]
        combined.loc[hdb_rows, "lat"] = combined.loc[hdb_rows, address_col].map(coord_map["lat"])
        combined.loc[hdb_rows, "lon"] = combined.loc[hdb_rows, address_col].map(coord_map["lon"])

    condo_rows = combined.index[combined["property_type"].eq("condo")]
    if len(condo_rows):
        _geocode_condo_two_pass(combined, condo_rows, address_col, geocoder)

    coverage = combined[["lat", "lon"]].notna().all(axis=1).mean()
    logger.info("Geocoding coverage: %.1f%%", coverage * 100)

    segment_coverages = _per_type_coverage(
        combined,
        min_coordinate_coverage,
        min_coordinate_coverage_hdb,
        min_coordinate_coverage_condo,
    )
    failing = [s for s in segment_coverages if s.coverage < s.threshold]
    if failing:
        detail = "; ".join(
            f"{s.segment} {s.coverage:.1%} < threshold {s.threshold:.1%} (n={s.rows})"
            for s in failing
        )
        message = (
            f"Geocoding coverage {coverage:.1%} below per-type thresholds — "
            f"failing segment(s): {detail}"
        )
        if coordinate_coverage_policy == "fail":
            raise ValueError(message)
        for s in failing:
            logger.warning(
                "Geocoding coverage for %s: %.1f%% below threshold %.1f%% "
                "(aggregate %.1f%%) — proceeding under warn policy",
                s.segment,
                s.coverage * 100,
                s.threshold * 100,
                coverage * 100,
            )

    return combined


def _accept_plausible_project_coords(
    lookup: pd.DataFrame, query_project: dict[str, tuple[str, str]]
) -> dict[str, tuple[float, float]]:
    """Keep pass-1 condo project-query results that plausibly match the project.

    OneMap's first hit for a bare road-name query is a point ON the road, so a
    project query answered with e.g. "BUKIT TIMAH ROAD" must not be trusted. A
    result is accepted only when its ``matched_name`` or ``address`` contains
    the queried project's name tokens variant-tolerantly AND its address
    corroborates the transaction's street name (see
    ``plausible_project_match``); null-coordinate and implausible results are
    treated as misses for pass 2.
    """
    coord_map = lookup.set_index("input")
    accepted: dict[str, tuple[float, float]] = {}
    for query, (project, street) in query_project.items():
        if query not in coord_map.index:
            continue
        row = coord_map.loc[query]
        if pd.isna(row.get("lat")) or pd.isna(row.get("lon")):
            continue
        if plausible_project_match(
            project, row.get("matched_name"), row.get("address"), street_name=street
        ):
            accepted[query] = (float(row["lat"]), float(row["lon"]))
    return accepted


def _geocode_condo_two_pass(
    combined: pd.DataFrame,
    condo_rows: pd.Index,
    address_col: str,
    geocoder: Geocoder,
) -> None:
    """Fill lat/lon for condo rows in place via a two-pass strategy.

    Condo transactions have no postal codes, so the persisted ``address`` is
    street-only and OneMap's first hit for a street-only query is a point on
    the road. Pass 1 therefore geocodes a project-aware query,
    ``"{project_name} {address} Singapore"``, and keeps only plausibility-
    checked results (``_accept_plausible_project_coords``). Pass 2 re-geocodes
    everything still missing — project misses, implausible matches, and rows
    without a project name — with the legacy street-only string and fills
    from that.

    The project-aware string is a geocode QUERY only: the persisted
    ``address`` column keeps its schema-stable street-only value.
    """
    condo = combined.loc[condo_rows]
    street = condo[address_col].fillna("").astype(str)
    projects = (
        condo["project_name"].fillna("").astype(str)
        if "project_name" in condo.columns
        else pd.Series("", index=condo.index)
    )
    has_project = projects.str.strip().ne("")

    if has_project.any():
        query_rows = condo.index[has_project]
        project_query = (projects + " " + street + " Singapore").str.strip()
        query_project: dict[str, tuple[str, str]] = {}
        for label in query_rows:
            query_project.setdefault(
                project_query.at[label], (projects.at[label], street.at[label])
            )
        logger.info("Geocoding %s unique condo project queries...", len(query_project))
        lookup = geocoder.geocode(pd.Series(list(query_project), name="project_query"))
        accepted = _accept_plausible_project_coords(lookup, query_project)
        lat_map = {query: coords[0] for query, coords in accepted.items()}
        lon_map = {query: coords[1] for query, coords in accepted.items()}
        combined.loc[query_rows, "lat"] = project_query.loc[query_rows].map(lat_map)
        combined.loc[query_rows, "lon"] = project_query.loc[query_rows].map(lon_map)

    still_missing = combined.loc[condo_rows, "lat"].isna()
    missing_rows = still_missing.index[still_missing]
    if len(missing_rows):
        unique_fallback = (
            combined.loc[missing_rows, address_col].dropna().astype(str).unique().tolist()
        )
        logger.info("Geocoding %s unique condo street fallbacks...", len(unique_fallback))
        lookup = geocoder.geocode(pd.Series(unique_fallback, name=address_col))
        # to_numeric coerces geocoder None misses to NaN so the assignments
        # below never write None into the float coordinate columns.
        coord_map = lookup.set_index("input")[["lat", "lon"]].apply(pd.to_numeric, errors="coerce")
        combined.loc[missing_rows, "lat"] = combined.loc[missing_rows, address_col].map(
            coord_map["lat"]
        )
        combined.loc[missing_rows, "lon"] = combined.loc[missing_rows, address_col].map(
            coord_map["lon"]
        )


@extract_fields({"geocoded_validated": pd.DataFrame, "geocoded_quarantine": pd.DataFrame})
def validate_geocoded(geocoded_properties: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Validate geocoded properties against schema.

    Validation only — persistence is owned by ``materialize_geocoded_validated``.
    """
    result = validate_and_quarantine(geocoded_properties, GeocodedProperty, "geocoded")
    if not result["rejected"].empty:
        logger.warning(
            "geocoded_validated: %s row(s) quarantined at the silver boundary",
            len(result["rejected"]),
        )
    return extracted_validation(
        result,
        "geocoded_validated",
        "geocoded_quarantine",
    )
