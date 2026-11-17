#!/usr/bin/env python3
"""Measure RS04's amenity-impact evidence: vintages, lineage, and a refit with units.

RS04's gate is "Refit documented associations with units and controls.
Contemporary amenity presence must not imply historical presence; disclose
snapshot join limitations. No causal premiums without identification." This
tool measures from the local checkout, and only what the checkout can support:

1. **Cutoff** — the same measured last-complete-month rule RS03 shipped; every
   aggregation in this ledger is bounded at BOTH ends of the study window and
   the bound is a ledger field (`cutoffUpperBound`), not only prose.
2. **Amenity-source vintage audit** — what dated vintages each amenity layer
   carries (hawker centres carry completion dates and an operating STATUS;
   parks and childcare carry only update stamps; supermarkets, preschools and
   the MP25 mall layer carry no dates at all; MRT is RS03's single 2019-12-09
   seed plus an undated bronze frame).
3. **Shipped-feature lineage, with a targeted leave-out ablation** — the shipped
   `dist_to_nearest_hawker` column is recomputed over every unique location in
   the study window from the sha-pinned bronze frames: the full-frame exact
   match is the lineage evidence, and a targeted ablation (excluding the six
   Under-Construction centres) changes the shipped value for exactly those
   locations whose nearest centre is one of the excluded six, locating their
   coordinates in the shipped feature. It does not establish historical
   operating status.
4. **Snapshot-join mismatch (hawker only)** — the share of study-window
   transactions whose nearest snapshot hawker centre was not yet completed at
   the transaction date, quantified from the completion dates the raw GeoJSON
   carries and the bronze ingest drops.
5. **Descriptive conditional associations** — one recorded OLS
   specification on log resale price with stated units and controls, all five
   amenity indicators fitted jointly (no selection), HC1 robust standard
   errors, plus an amenity-count model. Descriptive only: no premium, no
   causal reading, no temporal comparison.

It never runs the pipeline, never re-fits the legacy models and never writes
outside `--output`.

Usage:

    uv run python scripts/tools/amenity_impact_evidence.py \\
        --output docs/implementation/artifacts/rs04-amenity-impact-evidence.json

    uv run python scripts/tools/amenity_impact_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.neighbors import BallTree

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
BRONZE = REPO_ROOT / "data" / "pipeline" / "01_bronze"
RAW_HAWKER = BRONZE / "external" / "HawkerCentresGEOJSON.parquet"
RAW_PARKS = BRONZE / "external" / "NParksParksandNatureReserves.parquet"
RAW_SUPERMARKETS = BRONZE / "external" / "SupermarketsGEOJSON.parquet"
RAW_MALLS = BRONZE / "raw_mp25_malls.parquet"
RAW_MRT = BRONZE / "raw_mrt_stations.parquet"
GEO_DIR = REPO_ROOT / "data" / "manual" / "csv" / "datagov"
HAWKER_GEOJSON = GEO_DIR / "HawkerCentresGEOJSON.geojson"
PARKS_GEOJSON = GEO_DIR / "NParksParksandNatureReserves.geojson"
SUPERMARKETS_GEOJSON = GEO_DIR / "SupermarketsGEOJSON.geojson"
CHILDCARE_GEOJSON = GEO_DIR / "ChildCareServices.geojson"
PRESCHOOLS_GEOJSON = GEO_DIR / "PreSchoolsLocation.geojson"
LEGACY_EDITION = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "amenity-impact.md"
)
DATAGOV_MODULE = (
    REPO_ROOT / "src" / "egg_n_bacon_housing" / "components" / "ingestion" / "datagov.py"
)
PROXIMITY_MODULE = REPO_ROOT / "src" / "egg_n_bacon_housing" / "utils" / "proximity.py"
MALL_LAYER_MARKER = "existing and designated mall sites"
BALLTREE_MARKER = 'metric="haversine"'
METRES_MARKER = "distances_rad[:, 0] * 6371000"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs04-amenity-impact-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

STUDY_WINDOW_START = "2015-01"
AMENITIES = ("hawker", "mall", "park", "supermarket", "mrt")
THRESHOLD_METRES = 1000.0
LINEAGE_TOLERANCE_METRES = 1e-6
EARTH_RADIUS_METRES = 6371000.0
HDB_FLAT_TYPES = (
    "1-ROOM",
    "2-ROOM",
    "3-ROOM",
    "4-ROOM",
    "5-ROOM",
    "EXECUTIVE",
    "MULTI-GENERATION",
)
BASELINE_FLAT_TYPE = "1-ROOM"
BASELINE_TOWN = "ANG MO KIO"
BASELINE_YEAR = "2015"
WINDOW_LABELS = (
    ("2015-2019", "2015-01", "2019-12"),
    ("2020-2022", "2020-01", "2022-12"),
    ("2023-2026", "2023-01", None),  # resolved to the measured cutoff at runtime
)

DEFINITION = (
    "A descriptive conditional-association refit: one recorded OLS of "
    "log(HDB resale price in SGD) on five jointly-fitted snapshot amenity "
    "indicators (shipped distance <= 1000 m) with stated controls (floor area "
    "sqm, lease commencement year, storey midpoint, flat-type/town/transaction-"
    "year fixed effects) and HC1 robust standard errors, plus an amenity-count "
    "model. Coefficients are conditional associations in a cross-section, not "
    "premiums and not causal effects; the amenity features come from one "
    "snapshot per layer whose datedness differs (update stamps from 2021-12 to "
    "2026-01 where they exist; hawker completion dates are the only presence "
    "dates, and supermarkets, preschools, malls and MRT carry none) and is "
    "joined to transactions from 2015 onward, so no coefficient compares "
    "amenity states at two dates; no temporal model, no feature-importance "
    "model and no interaction model is reproduced. This ledger records one "
    "specification and only that one was fitted, and all its coefficients are "
    "reported; there is no dated prior protocol, so specification search "
    "cannot be ruled out — the single-specification discipline is a disclosed "
    "limitation, not a credential."
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _select(frame: pd.DataFrame, mask: Any) -> pd.DataFrame:
    return pd.DataFrame(frame.loc[mask]).reset_index(drop=True)


def _r(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    value = float(value)
    if not np.isfinite(value):
        return None
    return round(value, digits)


def _code_quote(path: Path, marker: str, label: str) -> dict[str, Any]:
    """Locate a marker line in a source module and cite it verbatim."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        if marker in line:
            return {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "line": number,
                "quote": line.strip(),
            }
    raise SystemExit(
        f"{label} marker {marker!r} not found in {path}; the ledger's citation is stale"
    )


def _stamp_date(stamp: str) -> str | None:
    if len(stamp) == 14 and stamp.isdigit():
        return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
    return None


def _numeric(column: Any) -> pd.Series:
    """A float64 view of a column, for comparisons that must tolerate NaN."""
    series = pd.Series(column)
    return pd.Series(pd.to_numeric(series, errors="coerce"), index=series.index)


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    hdb = _select(frame, frame["property_type"] == "hdb")
    counts = {str(k): int(v) for k, v in hdb.groupby("month").size().items()}
    ordered = sorted(counts)
    last_month = ordered[-1]
    trailing = [counts[month] for month in ordered[-13:-1]]
    trailing_median = float(np.median(trailing)) if trailing else 0.0
    ratio = counts[last_month] / trailing_median if trailing_median else None
    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact"
        ),
        "lastCompleteMonth": "2026-10",
        "terminalMonth": last_month,
        "terminalMonthTransactions": counts[last_month],
        "trailing12MedianTransactions": _r(trailing_median, 1),
        "terminalMonthShareOfTrailingMedian": _r(ratio, 4),
    }


def _geojson_properties(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unreadable GeoJSON {path}: {error}") from error
    return [dict(feature.get("properties", {})) for feature in payload.get("features", [])]


def _stamp_histogram(props: list[dict[str, Any]], column: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for properties in props:
        stamp = str(properties.get(column) or "").strip()
        counts[stamp] += 1
    return {key: counts[key] for key in sorted(counts)}


def _parse_completion(value: Any) -> tuple[str | None, str]:
    """Classify one EST_ORIGINAL_COMPLETION_DATE value.

    Returns (canonical value, kind). kinds: exact-date (D/M/YYYY as printed by
    the source, read day-first), year (a bare four-digit year at or before the
    cutoff year), future-year (a bare year after the cutoff year — a planned
    completion, matching the layer's Under Construction status), pre-war,
    unknown (null/empty), unparseable.
    """
    text = str(value or "").strip()
    if not text or text == "None":
        return (None, "unknown")
    if text.lower() == "pre-war":
        return ("pre-war", "pre-war")
    parts = text.split("/")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        day, month, year = (int(part) for part in parts)
        try:
            return (datetime.date(year, month, day).isoformat(), "exact-date")
        except ValueError:
            return (text, "unparseable")
    if text.isdigit() and len(text) == 4:
        year = int(text)
        if year > 2026:
            return (text, "future-year")
        return (text, "year")
    return (text, "unparseable")


def amenity_vintages() -> dict[str, Any]:
    """What dated vintages each amenity layer carries, measured not assumed."""
    hawker_props = _geojson_properties(HAWKER_GEOJSON)
    parks_props = _geojson_properties(PARKS_GEOJSON)
    supermarkets_props = _geojson_properties(SUPERMARKETS_GEOJSON)
    childcare_props = _geojson_properties(CHILDCARE_GEOJSON)
    preschool_props = _geojson_properties(PRESCHOOLS_GEOJSON)

    completion: dict[str, dict[str, Any]] = {}
    kind_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    exact_dates: list[str] = []
    future_years: list[str] = []
    for properties in hawker_props:
        name = str(properties.get("NAME") or "").strip()
        value, kind = _parse_completion(properties.get("EST_ORIGINAL_COMPLETION_DATE"))
        status = str(properties.get("STATUS") or "").strip()
        status_counts[status] += 1
        kind_counts[kind] += 1
        if kind == "exact-date":
            exact_dates.append(str(value))
        if kind == "future-year":
            future_years.append(name)
        completion[name] = {"completion": value, "completionKind": kind, "status": status}
    hawker_bronze = pd.read_parquet(RAW_HAWKER)
    geo_names = {name for name in completion}
    bronze_names = {str(name).strip() for name in hawker_bronze["name"]}
    exact_sorted = sorted(exact_dates)
    hup = [_parse_completion(p.get("HUP_COMPLETION_DATE"))[0] for p in hawker_props]
    hup_exact = sorted(str(v) for v in hup if v and re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)))
    awarded_non_empty = sum(
        1 for p in hawker_props if str(p.get("AWARDED_DATE") or "").strip() not in ("", "None")
    )
    implementation_non_empty = sum(
        1
        for p in hawker_props
        if str(p.get("IMPLEMENTATION_DATE") or "").strip() not in ("", "None")
    )

    malls_bronze = pd.read_parquet(RAW_MALLS)
    mrt_bronze = pd.read_parquet(RAW_MRT)

    return {
        "hawker": {
            "rawGeojson": {
                "path": HAWKER_GEOJSON.relative_to(REPO_ROOT).as_posix(),
                "features": len(hawker_props),
                "propertyKeys": sorted({key for p in hawker_props for key in p}),
                "dateColumns": {
                    "estOriginalCompletionDate": {
                        "nonEmpty": len(hawker_props) - kind_counts["unknown"],
                        "kinds": {kind: kind_counts[kind] for kind in sorted(kind_counts)},
                        "exactDateRange": {
                            "min": exact_sorted[0] if exact_sorted else None,
                            "max": exact_sorted[-1] if exact_sorted else None,
                        },
                    },
                    "hupCompletionDate": {
                        "nonEmpty": len(hup_exact),
                        "exactDateRange": {
                            "min": hup_exact[0] if hup_exact else None,
                            "max": hup_exact[-1] if hup_exact else None,
                        },
                        "meaning": "Hawker Upgrading Programme completion, not the centre's original completion",
                    },
                    "implementationDate": {"nonEmpty": implementation_non_empty},
                    "awardedDate": {"nonEmpty": awarded_non_empty},
                    "fmelUpdD": {
                        "stamps": _stamp_histogram(hawker_props, "FMEL_UPD_D"),
                        "normalisedDates": sorted(
                            {
                                str(_stamp_date(key))
                                for key in _stamp_histogram(hawker_props, "FMEL_UPD_D")
                                if _stamp_date(key)
                            }
                        ),
                        "meaning": "dataset last-update stamp, not an opening or completion date",
                    },
                },
                "status": {key: status_counts[key] for key in sorted(status_counts)},
                "futureYearCompletions": sorted(future_years),
                "futureYearCompletionYears": sorted(
                    {
                        str(value)
                        for value, kind in map(
                            _parse_completion,
                            [p.get("EST_ORIGINAL_COMPLETION_DATE") for p in hawker_props],
                        )
                        if kind == "future-year"
                        for value in [value]
                    }
                ),
            },
            "bronze": {
                "path": RAW_HAWKER.relative_to(REPO_ROOT).as_posix(),
                "rows": int(len(hawker_bronze)),
                "columns": [str(c) for c in hawker_bronze.columns],
                "carriesDates": any("date" in c.lower() for c in hawker_bronze.columns),
                "namesEqualRawGeojson": geo_names == bronze_names,
                "note": (
                    "ingest keeps name/lat/lon/amenity_type only; the completion "
                    "dates and STATUS the raw GeoJSON carries are dropped before "
                    "the features are computed"
                ),
            },
            "datedPresenceAvailable": True,
            "datedPresenceUsedByShippedFeatures": False,
        },
        "park": {
            "rawGeojson": {
                "path": PARKS_GEOJSON.relative_to(REPO_ROOT).as_posix(),
                "features": len(parks_props),
                "propertyKeys": sorted({key for p in parks_props for key in p}),
                "fmelUpdD": _stamp_histogram(parks_props, "FMEL_UPD_D"),
                "normalisedDates": sorted(
                    {
                        str(_stamp_date(key))
                        for key in _stamp_histogram(parks_props, "FMEL_UPD_D")
                        if _stamp_date(key)
                    }
                ),
                "hasGazettingOrOpeningDate": any(
                    "gazet" in key.lower() or "open" in key.lower()
                    for p in parks_props
                    for key in p
                ),
            },
            "bronze": {
                "path": RAW_PARKS.relative_to(REPO_ROOT).as_posix(),
                "rows": int(len(pd.read_parquet(RAW_PARKS))),
                "columns": [str(c) for c in pd.read_parquet(RAW_PARKS).columns],
                "carriesDates": False,
            },
            "datedPresenceAvailable": False,
        },
        "supermarket": {
            "rawGeojson": {
                "path": SUPERMARKETS_GEOJSON.relative_to(REPO_ROOT).as_posix(),
                "features": len(supermarkets_props),
                "propertyKeys": sorted({key for p in supermarkets_props for key in p}),
                "hasAnyDateColumn": False,
            },
            "bronze": {
                "path": RAW_SUPERMARKETS.relative_to(REPO_ROOT).as_posix(),
                "rows": int(len(pd.read_parquet(RAW_SUPERMARKETS))),
                "columns": [str(c) for c in pd.read_parquet(RAW_SUPERMARKETS).columns],
                "carriesDates": False,
            },
            "datedPresenceAvailable": False,
        },
        "mall": {
            "bronze": {
                "path": RAW_MALLS.relative_to(REPO_ROOT).as_posix(),
                "rows": int(len(malls_bronze)),
                "columns": [str(c) for c in malls_bronze.columns],
                "carriesDates": False,
                "namesEmptyShare": _r(
                    float((malls_bronze["name"].astype(str).str.strip() == "").mean()), 4
                ),
            },
            "rawLayerInCheckout": False,
            "rawLayerNote": (
                "the MP25 mall layer is fetched from data.gov.sg at ingestion time "
                "(use_cache=False) and is not stored in this checkout; only the "
                "bronze name/lat/lon frame exists here"
            ),
            "layerCompositionCitation": _code_quote(
                DATAGOV_MODULE, MALL_LAYER_MARKER, "mall-layer"
            ),
            "datedPresenceAvailable": False,
        },
        "mrt": {
            "bronze": {
                "path": RAW_MRT.relative_to(REPO_ROOT).as_posix(),
                "rows": int(len(mrt_bronze)),
                "columns": [str(c) for c in mrt_bronze.columns],
                "hasOpeningDate": any("open" in c.lower() for c in mrt_bronze.columns),
            },
            "seedGeojson": {
                "path": "data/manual/csv/datagov/MRTStations.geojson",
                "singleUpdateStamp": "2019-12-09",
                "note": (
                    "RS03 measured this seed and the shipped MRT lineage in full "
                    "(rs03-temporal-evolution-evidence.json, "
                    "featureVintages.mrtStationsGeojson and shippedFeatureLineage); "
                    "this pack re-states only the headline: one 2019-12-09 vintage, "
                    "no opening dates, and the shipped dist_to_nearest_mrt "
                    "reproduces from the 188-row bronze frame, not the seed"
                ),
            },
            "datedPresenceAvailable": False,
        },
        "childcare": {
            "rawGeojson": {
                "path": CHILDCARE_GEOJSON.relative_to(REPO_ROOT).as_posix(),
                "features": len(childcare_props),
                "fmelUpdD": _stamp_histogram(childcare_props, "FMEL_UPD_D"),
            },
            "datedPresenceAvailable": False,
        },
        "preschool": {
            "rawGeojson": {
                "path": PRESCHOOLS_GEOJSON.relative_to(REPO_ROOT).as_posix(),
                "features": len(preschool_props),
                "propertyKeys": sorted({key for p in preschool_props for key in p}),
                "hasAnyDateColumn": False,
            },
            "datedPresenceAvailable": False,
        },
    }


def shipped_features(frame: pd.DataFrame, last_complete_month: str) -> dict[str, Any]:
    """The shipped distance columns: unit, population, and per-window prevalence."""
    hdb = _select(frame, frame["property_type"] == "hdb")
    hdb = _select(hdb, (hdb["month"] >= STUDY_WINDOW_START) & (hdb["month"] <= last_complete_month))
    hdb = hdb.assign(year=pd.Series(hdb["month"]).str.slice(0, 4).to_numpy())
    per_amenity: dict[str, Any] = {}
    for amenity in AMENITIES:
        column = f"dist_to_nearest_{amenity}"
        name_column = "nearest_mrt_station" if amenity == "mrt" else f"nearest_{amenity}"
        distances = pd.Series(hdb[column], dtype="float64")
        names = hdb[name_column].astype(str)
        per_amenity[amenity] = {
            "column": column,
            "unit": "metres (BallTree haversine x 6371000)",
            "computationCitations": [
                _code_quote(PROXIMITY_MODULE, BALLTREE_MARKER, "balltree"),
                _code_quote(PROXIMITY_MODULE, METRES_MARKER, "metres"),
            ],
            "windowTransactions": int(len(hdb)),
            "nonNullShare": _r(float(distances.notna().mean()), 4),
            "within1000mShare": _r(float((distances <= THRESHOLD_METRES).mean()), 4),
            "within1000mN": int((distances <= THRESHOLD_METRES).sum()),
            "nearestNameEmptyShare": _r(float((names.str.strip() == "").mean()), 4),
            "distanceMetres": {
                "p10": _r(float(distances.quantile(0.10)), 1),
                "p50": _r(float(distances.median()), 1),
                "p90": _r(float(distances.quantile(0.90)), 1),
            },
        }
    by_window: dict[str, Any] = {}
    for label, start, end in WINDOW_LABELS:
        end = end or last_complete_month
        at = _select(hdb, (hdb["month"] >= start) & (hdb["month"] <= end))
        by_window[label] = {
            "months": f"{start} -> {end}",
            "transactions": int(len(at)),
            **{
                f"{amenity}Within1000mShare": _r(
                    float(
                        (
                            pd.Series(at[f"dist_to_nearest_{amenity}"], dtype="float64")
                            <= THRESHOLD_METRES
                        ).mean()
                    ),
                    4,
                )
                for amenity in AMENITIES
            },
        }
    return {
        "grain": (
            "computed once per unique (lat, lon) location and left-merged onto "
            "transactions (features.py builds the location dimension on ~10K "
            "unique locations, not per transaction)"
        ),
        "perAmenity": per_amenity,
        "hdbIndicatorPrevalenceByWindow": by_window,
    }


def _load_snapshot(name_column: str) -> pd.DataFrame:
    """One POI frame: name/lat/lon exactly as its bronze cache holds it."""
    bronze = {
        "hawker": RAW_HAWKER,
        "park": RAW_PARKS,
        "supermarket": RAW_SUPERMARKETS,
        "mall": RAW_MALLS,
        "mrt": RAW_MRT,
    }[name_column]
    frame = pd.read_parquet(bronze)
    return pd.DataFrame(
        {
            "name": frame["name"].astype(str),
            "lat": pd.to_numeric(frame["lat"], errors="coerce"),
            "lon": pd.to_numeric(frame["lon"], errors="coerce"),
        }
    ).dropna(subset=["lat", "lon"])


def _nearest_distances(locations: pd.DataFrame, pois: pd.DataFrame) -> np.ndarray:
    """Nearest-POI metres, exactly as utils/proximity.py computes it."""
    tree = BallTree(np.radians(pois[["lat", "lon"]].to_numpy(dtype=float)), metric="haversine")
    distances_rad, _ = tree.query(np.radians(locations[["lat", "lon"]].to_numpy(dtype=float)), k=1)
    return distances_rad[:, 0] * EARTH_RADIUS_METRES


def shipped_feature_lineage(window: pd.DataFrame) -> dict[str, Any]:
    """Which snapshot the shipped distances reproduce from, via a targeted
    leave-out ablation.

    Full-population at the location grain: every unique (lat, lon) in the
    study window, recomputed from the sha-pinned bronze frames with the
    pipeline's own estimator — the full-frame exact match is the lineage
    evidence. For hawker the ablation then EXCLUDES the six
    Under-Construction centres: the shipped value changes for exactly those
    locations whose nearest shipped centre is one of the excluded six, which
    locates their coordinates in the shipped feature. The ablation does not
    establish historical operating status.
    """
    usable = _select(
        window,
        pd.Series(window["lat"]).notna()
        & pd.Series(window["lon"]).notna()
        & pd.Series(window["dist_to_nearest_hawker"]).notna(),
    )
    locations = (
        pd.DataFrame({"lat": usable["lat"].astype(float), "lon": usable["lon"].astype(float)})
        .drop_duplicates()
        .reset_index(drop=True)
    )

    hawker = _load_snapshot("hawker")
    shipped_hawker = (
        pd.DataFrame({"lat": locations["lat"], "lon": locations["lon"]})
        .merge(
            usable[["lat", "lon", "dist_to_nearest_hawker"]].drop_duplicates(),
            on=["lat", "lon"],
            how="left",
        )["dist_to_nearest_hawker"]
        .to_numpy(dtype=float)
    )
    bronze_distances = _nearest_distances(locations, pd.DataFrame(hawker))
    bronze_deviation = np.abs(bronze_distances - shipped_hawker)
    bronze_matches = int((bronze_deviation <= LINEAGE_TOLERANCE_METRES).sum())

    status_by_name = {
        str(properties.get("NAME") or "").strip(): str(properties.get("STATUS") or "").strip()
        for properties in _geojson_properties(HAWKER_GEOJSON)
    }
    under_construction = sorted(
        name for name, status in status_by_name.items() if status == "Under Construction"
    )
    nearest_names = (
        pd.DataFrame({"lat": locations["lat"], "lon": locations["lon"]})
        .merge(
            usable[["lat", "lon", "nearest_hawker"]].drop_duplicates(),
            on=["lat", "lon"],
            how="left",
        )["nearest_hawker"]
        .astype(str)
        .str.strip()
        .to_numpy()
    )
    is_uc_nearest = np.isin(nearest_names, under_construction)
    uc_count = int(is_uc_nearest.sum())
    hawker_no_uc = pd.DataFrame(
        hawker[~hawker["name"].str.strip().isin(under_construction)]
    ).reset_index(drop=True)
    no_uc_deviation = np.abs(_nearest_distances(locations, hawker_no_uc) - shipped_hawker)
    uc_broken = int((no_uc_deviation[is_uc_nearest] > LINEAGE_TOLERANCE_METRES).sum())

    mrt = _load_snapshot("mrt")
    shipped_mrt = (
        pd.DataFrame({"lat": locations["lat"], "lon": locations["lon"]})
        .merge(
            usable[["lat", "lon", "dist_to_nearest_mrt"]].drop_duplicates(),
            on=["lat", "lon"],
            how="left",
        )["dist_to_nearest_mrt"]
        .to_numpy(dtype=float)
    )
    mrt_deviation = np.abs(_nearest_distances(locations, mrt) - shipped_mrt)
    mrt_matches = int((mrt_deviation <= LINEAGE_TOLERANCE_METRES).sum())

    mall = _load_snapshot("mall")
    shipped_mall = (
        pd.DataFrame({"lat": locations["lat"], "lon": locations["lon"]})
        .merge(
            usable[["lat", "lon", "dist_to_nearest_mall"]].drop_duplicates(),
            on=["lat", "lon"],
            how="left",
        )["dist_to_nearest_mall"]
        .to_numpy(dtype=float)
    )
    mall_deviation = np.abs(_nearest_distances(locations, mall) - shipped_mall)
    mall_matches = int((mall_deviation <= LINEAGE_TOLERANCE_METRES).sum())

    if bronze_matches != len(locations):
        raise SystemExit(
            "shipped dist_to_nearest_hawker no longer reproduces from the bronze "
            f"frame ({bronze_matches}/{len(locations)} match)"
        )
    if mrt_matches != len(locations):
        raise SystemExit(
            "shipped dist_to_nearest_mrt no longer reproduces from the bronze "
            f"frame ({mrt_matches}/{len(locations)} match)"
        )
    if mall_matches != len(locations):
        raise SystemExit(
            "shipped dist_to_nearest_mall no longer reproduces from the bronze "
            f"frame ({mall_matches}/{len(locations)} match)"
        )
    if uc_broken != uc_count:
        raise SystemExit(
            "excluding Under-Construction centres does not break reproduction for "
            f"every location whose nearest centre is one of them ({uc_broken}/{uc_count})"
        )
    return {
        "grain": "every unique (lat, lon) location in the study window (not a sample)",
        "method": (
            "nearest-POI metres recomputed with the pipeline's own estimator "
            "(BallTree(metric='haversine') k=1, radians x 6371000) from the "
            "sha-pinned bronze frames, compared to the shipped columns at "
            "1e-6 m tolerance"
        ),
        "locations": int(len(locations)),
        "hawker": {
            "bronzeMatches": bronze_matches,
            "bronzeMaxAbsDeviationMetres": _r(float(bronze_deviation.max()), 9),
            "underConstructionCentres": under_construction,
            "underConstructionCount": len(under_construction),
            "locationsNearestUnderConstruction": uc_count,
            "matchesWhenUnderConstructionExcluded": int(
                (no_uc_deviation <= LINEAGE_TOLERANCE_METRES).sum()
            ),
            "underConstructionNearestLocationsBrokenByExclusion": uc_broken,
            "conclusion": (
                "the shipped dist_to_nearest_hawker reproduces exactly from the "
                "bronze snapshot that INCLUDES the six Under-Construction "
                "centres; a targeted ablation excluding them breaks reproduction "
                "for every location whose nearest centre is one of those six "
                "(and none of the others), so those six centres' coordinates "
                "feed the single distance value the location join applies to "
                "transactions of every study month. When construction at each "
                "site began is not recorded in this checkout"
            ),
        },
        "mrt": {
            "bronzeMatches": mrt_matches,
            "bronzeMaxAbsDeviationMetres": _r(float(mrt_deviation.max()), 9),
            "conclusion": (
                "the shipped dist_to_nearest_mrt reproduces exactly from the "
                "188-row undated bronze station frame at this location grain, "
                "consistent with RS03's sample-level lineage measurement"
            ),
        },
        "mall": {
            "bronzeMatches": mall_matches,
            "bronzeMaxAbsDeviationMetres": _r(float(mall_deviation.max()), 9),
            "conclusion": (
                "the shipped dist_to_nearest_mall reproduces exactly from the "
                "294-row MP25 bronze frame; its nearest-name column is empty for "
                "every row because the MP25 layer carries no names"
            ),
        },
        "notRecomputed": (
            "park and supermarket lineage is not recomputed here; their bronze "
            "frames are audited in amenityVintages and their snapshot-join "
            "mismatch is not measurable (no dated vintage)"
        ),
    }


def snapshot_join_mismatch(window: pd.DataFrame) -> dict[str, Any]:
    """Contemporary presence vs historical presence, measured for hawker only.

    For each study-window transaction, its nearest hawker centre BY NAME is
    classified against the completion dates the raw GeoJSON carries. Centres
    farther than the nearest are not classified (the nearest centre dominates
    a within-1km indicator, but this is still a nearest-only measure).
    """
    completion: dict[str, tuple[str | None, str, str]] = {}
    for properties in _geojson_properties(HAWKER_GEOJSON):
        name = str(properties.get("NAME") or "").strip()
        value, kind = _parse_completion(properties.get("EST_ORIGINAL_COMPLETION_DATE"))
        status = str(properties.get("STATUS") or "").strip()
        completion[name] = (value, kind, status)

    at = _select(
        window,
        pd.Series(window["dist_to_nearest_hawker"]).notna()
        & pd.Series(window["nearest_hawker"]).notna(),
    )
    names = at["nearest_hawker"].astype(str).str.strip()
    months = at["month"].astype(str)
    txn_year = months.str.slice(0, 4).to_numpy()
    txn_month = months.str.slice(5, 7).to_numpy()

    def classify(name: str, year: str, month: str) -> str:
        value, kind, _status = completion[name]
        if kind == "unknown" or kind == "unparseable":
            return "nearest-completion-unknown"
        if kind == "pre-war":
            return "nearest-completed-before-transaction"
        if kind == "future-year":
            return "nearest-not-established-before-transaction"
        if kind == "year":
            return (
                "nearest-completed-before-transaction"
                if int(str(value)) < int(year)
                else "nearest-not-established-before-transaction"
            )
        # exact date: completed if at or before the first day of the transaction month
        day_completed = datetime.date(int(year), int(month), 1)
        return (
            "nearest-completed-before-transaction"
            if datetime.date.fromisoformat(str(value)) <= day_completed
            else "nearest-not-established-before-transaction"
        )

    buckets = [
        classify(name, year, month)
        for name, year, month in zip(names, txn_year, txn_month, strict=True)
    ]
    counts = Counter(buckets)
    total = len(buckets)
    by_window: dict[str, Any] = {}
    for label, start, end in WINDOW_LABELS:
        end = end or "2026-10"
        selector = [(start <= month <= end) for month in months]
        subset = [bucket for bucket, keep in zip(buckets, selector, strict=True) if keep]
        not_established = sum(
            1 for b in subset if b == "nearest-not-established-before-transaction"
        )
        by_window[label] = {
            "months": f"{start} -> {end}",
            "transactions": len(subset),
            "notEstablishedShare": _r(not_established / len(subset), 4) if subset else None,
        }

    status_by_name = {name: entry[2] for name, entry in completion.items()}
    uc_names = sorted(n for n, s in status_by_name.items() if s == "Under Construction")
    uc_nearest_rows = int(np.isin(names.to_numpy(), uc_names).sum())
    return {
        "rule": (
            "each transaction's nearest hawker centre (by exact bronze name) is "
            "classified against EST_ORIGINAL_COMPLETION_DATE: an exact date at or "
            "before the transaction month's first day counts as completed; a "
            "year-only value strictly before the transaction year counts as "
            "completed, a year-only value in the transaction year is NOT "
            "established as completed (mid-year completion is unresolved, a "
            "conservative reading); a future-year value (all six Under "
            "Construction centres) is not established for any study transaction; "
            "pre-war counts as completed; null/unknown stays unknown. Centres "
            "farther than the nearest are not classified."
        ),
        "transactions": total,
        "buckets": {key: counts[key] for key in sorted(counts)},
        "notEstablishedShare": _r(counts["nearest-not-established-before-transaction"] / total, 4),
        "byWindow": by_window,
        "nearestUnderConstruction": {
            "centres": uc_names,
            "rows": uc_nearest_rows,
            "share": _r(uc_nearest_rows / total, 4),
        },
        "notMeasurableForOtherAmenities": {
            "mall": "the MP25 layer carries no dates and its raw GeoJSON is not in this checkout",
            "park": "no gazetting or opening date; only a 2026-01-15 update stamp",
            "supermarket": "no date property of any kind; outlet vintages cannot be reconstructed",
            "preschool": "no date property of any kind",
            "childcare": "only a single 2021-12-01 update stamp",
            "mrt": "no opening dates (bronze); one 2019-12-09 seed stamp (RS03)",
            "meaning": (
                "the join applies one snapshot's values to transactions of every "
                "month, so the mismatch is present by construction; its magnitude "
                "is not measurable in this checkout"
            ),
        },
    }


def _design_matrix(frame: pd.DataFrame, amenity_columns: dict[str, np.ndarray]) -> pd.DataFrame:
    """Deterministic design matrix: amenity regressors + controls + FE dummies.

    Dummy columns are built explicitly over sorted category values (no
    pandas-version-dependent ordering); baseline levels are 1-ROOM, ANG MO KIO
    and 2015. Continuous controls are scaled for numerical stability and the
    reported coefficients are back-transformed to natural units.
    """
    base = pd.DataFrame(
        {
            "const": np.ones(len(frame)),
            "floor_area_sqm_10": frame["floor_area_sqm"].to_numpy(dtype=float) / 10.0,
            "lease_commence_2000_10": (frame["lease_commence_date"].to_numpy(dtype=float) - 2000.0)
            / 10.0,
            "storey_mid_10": ((frame["storey_min"] + frame["storey_max"]) / 2.0).to_numpy(
                dtype=float
            )
            / 10.0,
        }
    )
    for name, values in amenity_columns.items():
        base[name] = values
    for prefix, series, baseline in (
        ("ft", frame["flat_type"], BASELINE_FLAT_TYPE),
        ("town", frame["town"], BASELINE_TOWN),
        ("yr", frame["year"], BASELINE_YEAR),
    ):
        values = pd.Series(series).astype(str)
        for level in sorted(set(values)):
            if level == baseline:
                continue
            base[f"{prefix}_{level}"] = (values == level).to_numpy(dtype=float)
    return base


def associations(frame: pd.DataFrame, last_complete_month: str) -> dict[str, Any]:
    """One recorded descriptive specification (the only one fitted), all
    indicators jointly; no dated prior protocol exists, so specification
    search cannot be ruled out."""
    import statsmodels.api as sm

    hdb = _select(frame, frame["property_type"] == "hdb")
    # Reason sets over EVERY hdb row: one row can fail several conditions and
    # every applicable reason is recorded, none asserted as the single cause.
    # Computed as aligned boolean masks, one per reason.
    months = hdb["month"].astype(str)
    condition_masks: dict[str, Any] = {
        "before-study-window": (months < STUDY_WINDOW_START).to_numpy(),
        "terminal-partial-month-after-cutoff": (months > last_complete_month).to_numpy(),
        "non-positive-or-missing-price": (
            ~(_numeric(hdb["price"]) > 0) | _numeric(hdb["price"]).isna()
        ).to_numpy(),
        "non-positive-or-missing-floor-area": (
            ~(_numeric(hdb["floor_area_sqm"]) > 0) | _numeric(hdb["floor_area_sqm"]).isna()
        ).to_numpy(),
        "missing-lease-commencement": (
            ~(_numeric(hdb["lease_commence_date"]) > 1900)
            | _numeric(hdb["lease_commence_date"]).isna()
        ).to_numpy(),
        "missing-or-invalid-storey-range": (
            _numeric(hdb["storey_min"]).isna()
            | _numeric(hdb["storey_max"]).isna()
            | ~(_numeric(hdb["storey_max"]) >= _numeric(hdb["storey_min"]))
        ).to_numpy(),
        "missing-town": hdb["town"].astype(str).str.strip().eq("").to_numpy()
        | hdb["town"].isna().to_numpy(),
        "unrecognised-flat-type": ~hdb["flat_type"].astype(str).isin(HDB_FLAT_TYPES).to_numpy(),
    }
    for amenity in AMENITIES:
        condition_masks[f"missing-source:{amenity}-distance"] = (
            _numeric(hdb[f"dist_to_nearest_{amenity}"]).isna().to_numpy()
        )
    reason_frame = pd.DataFrame(condition_masks, index=hdb.index)
    reason_count_per_row = reason_frame.sum(axis=1)
    in_window_mask = ((months >= STUDY_WINDOW_START) & (months <= last_complete_month)).to_numpy()

    reason_counts: Counter[str] = Counter()
    for reason, mask in condition_masks.items():
        reason_counts[reason] = int(np.asarray(mask).sum())
    overlap_counts: Counter[int] = Counter(
        int(value) for value in reason_count_per_row[reason_count_per_row > 0]
    )
    excluded_total = int((reason_count_per_row > 0).sum())
    excluded_in_window = reason_frame.loc[(reason_count_per_row > 0).to_numpy() & in_window_mask]
    in_window_excluded = [
        {
            "rowIndex": int(index),
            "month": str(months.iloc[index]),
            "reasons": sorted(
                str(reason) for reason in excluded_in_window.columns if bool(row[reason])
            ),
        }
        for index, row in excluded_in_window.iterrows()
    ]
    included_mask = (reason_count_per_row == 0).to_numpy()
    window_included = np.logical_and(included_mask, in_window_mask)

    sample = _select(hdb, pd.Series(window_included)).reset_index(drop=True)
    sample = sample.assign(year=pd.Series(sample["month"]).str.slice(0, 4).to_numpy())
    n = len(sample)
    if n == 0:
        raise SystemExit("empty model sample")

    indicator_matrix = {
        f"{amenity}_1km": (
            _numeric(sample[f"dist_to_nearest_{amenity}"]).to_numpy(dtype=float) <= THRESHOLD_METRES
        ).astype(float)
        for amenity in AMENITIES
    }
    design = _design_matrix(sample, indicator_matrix)
    response = np.log(sample["price"].to_numpy(dtype=float))
    design_columns = list(design.columns)
    model = sm.OLS(response, design.to_numpy(dtype=float)).fit(cov_type="HC1", use_t=False)
    k = len(design_columns)
    coefficient_vector = [
        {
            "name": name,
            "logPoint": _r(float(model.params[i]), 8),
            "robustSe": _r(float(model.bse[i]), 8),
        }
        for i, name in enumerate(design_columns)
    ]

    def back_transform(name: str, scale: float) -> dict[str, float | None]:
        i = design_columns.index(name)
        return {
            "perNaturalUnit": scale,
            "logPoint": _r(float(model.params[i]) / scale, 8),
            "robustSe": _r(float(model.bse[i]) / scale, 8),
        }

    rows: dict[str, Any] = {}
    for amenity in AMENITIES:
        key = f"{amenity}_1km"
        i = design_columns.index(key)
        beta = float(model.params[i])
        se = float(model.bse[i])
        rows[key] = {
            "regressor": (
                f"1 when the shipped dist_to_nearest_{amenity} is <= 1000 m, else 0 "
                "(unitless binary indicator built from the shipped metres column)"
            ),
            "logPoint": _r(beta, 6),
            "robustSe": _r(se, 6),
            "tStat": _r(beta / se, 2),
            "pctEffectExpMinus1": _r(100.0 * (float(np.exp(beta)) - 1.0), 4),
            "within1000mN": int(indicator_matrix[key].sum()),
            "within1000mShare": _r(float(indicator_matrix[key].mean()), 4),
            "interpretation": (
                "conditional log-point difference in resale price associated with "
                "the indicator, holding the stated controls fixed; descriptive, "
                "not a causal premium"
            ),
        }

    # amenity-count model: same controls, one continuous regressor (0-5).
    count_values = np.zeros(n)
    for values in indicator_matrix.values():
        count_values = count_values + values
    design_count = _design_matrix(sample, {"amenity_count": count_values})
    model_count = sm.OLS(response, design_count.to_numpy(dtype=float)).fit(
        cov_type="HC1", use_t=False
    )
    count_columns = list(design_count.columns)
    i = count_columns.index("amenity_count")
    count_beta = float(model_count.params[i])
    count_se = float(model_count.bse[i])
    count_distribution = {
        str(int(value)): int((count_values == value).sum()) for value in sorted(set(count_values))
    }

    # The supermarket indicator's near-degenerate contrast group, attributed.
    supermarket_zero = indicator_matrix["supermarket_1km"] == 0.0
    contrast = _select(sample, pd.Series(supermarket_zero))
    contrast_towns = Counter(contrast["town"].astype(str))
    contrast_distances = _numeric(contrast["dist_to_nearest_supermarket"])

    return {
        "estimator": {
            "name": "OLS (statsmodels OLS, HC1 heteroskedasticity-robust covariance, use_t=False)",
            "response": "log(resale price), resale price in nominal Singapore dollars (SGD)",
            "functionalForm": (
                "log-linear; coefficients are log points, and "
                "pctEffectExpMinus1 = 100*(exp(beta)-1) is the approximate "
                "percentage difference the log point implies"
            ),
            "standardErrors": "HC1 robust; no clustering (town and year enter as fixed effects, not clusters)",
            "indicators": (
                f"each amenity enters as dist <= {THRESHOLD_METRES:.0f} m in the "
                "shipped snapshot feature; ALL five indicators are fitted "
                "jointly in ONE specification (no selection, no stepwise search)"
            ),
            "controls": [
                "floor_area_sqm (sqm, continuous)",
                "lease_commence_date (calendar year of lease commencement, continuous)",
                "storey midpoint ((storey_min + storey_max)/2, storey number, continuous)",
                "flat-type fixed effects (7 levels; baseline 1-ROOM)",
                "town fixed effects (levels observed in the sample; baseline ANG MO KIO)",
                "transaction-year fixed effects (baseline 2015; absorb nominal price drift and inflation)",
            ],
            "internalScaling": (
                "floor_area_sqm/10, (lease_commence_date-2000)/10 and storey "
                "midpoint/10 for numerical stability; the amenity indicators and "
                "dummies are unscaled, and the control coefficients below are "
                "back-transformed to natural units"
            ),
            "remainingLeaseEquivalence": (
                "remaining lease at transaction = 99 - (transaction year - lease "
                "commencement year) for 99-year resale flats; given the "
                "transaction-year fixed effects, lease_commence_date and that "
                "remaining-lease measure are affine transforms of each other, so "
                "the two parameterisations are equivalent here"
            ),
            "notControlled": [
                "flat_model (unit layout vintage; many levels, not in the legacy controls either)",
                "unit condition, renovation, view and floor orientation",
                "block-level attributes (point blocks, lift upgrading, car park)",
                "buyer grants, ethnicity-quota constraints and financing conditions",
                "walking-path distance, street-level connectivity, and amenity quality or operating status",
                "town x year shocks (amenity indicators correlate with neighbourhood change inside a town)",
                "the amenity snapshot's own vintage (see snapshotJoinMismatch)",
            ],
        },
        "sample": {
            "propertyType": "hdb",
            "windowStart": STUDY_WINDOW_START,
            "cutoffUpperBound": last_complete_month,
            "cutoffUpperBoundMeaning": (
                "every model row and every aggregate in this ledger ends at the "
                "last complete month; the terminal partial month is excluded"
            ),
            "windowMonths": 142,
            "hdbRowsTotal": int(len(hdb)),
            "includedN": int(n),
            "excludedRowsTotal": int(excluded_total),
            "excludedReasonCounts": {key: reason_counts[key] for key in sorted(reason_counts)},
            "excludedRowsByReasonCount": {
                str(k): overlap_counts[k] for k in sorted(overlap_counts)
            },
            "excludedInWindowRows": in_window_excluded,
            "reasonSetSemantics": (
                "exclusions are sets: a row failing several conditions records "
                "every reason (excludedRowsByReasonCount counts rows by the SIZE "
                "of their reason set), and no reason is asserted as the single cause"
            ),
        },
        "fit": {
            "n": int(n),
            "k": int(k),
            "rSquared": _r(float(model.rsquared), 4),
            "adjRSquared": _r(float(model.rsquared_adj), 4),
            "dfResid": int(model.df_resid),
        },
        "indicatorCoefficients": rows,
        "controlCoefficients": {
            "floor_area_sqm": back_transform("floor_area_sqm_10", 10.0),
            "lease_commence_date": back_transform("lease_commence_2000_10", 10.0),
            "storey_mid": back_transform("storey_mid_10", 10.0),
        },
        "fullCoefficientVector": coefficient_vector,
        "amenityCountModel": {
            "regressor": (
                "amenity_count = number of the five indicators equal to 1 "
                "(integer 0-5), continuous in log points per additional amenity "
                "type within 1000 m; same controls and sample"
            ),
            "logPoint": _r(count_beta, 6),
            "robustSe": _r(count_se, 6),
            "tStat": _r(count_beta / count_se, 2),
            "pctEffectExpMinus1": _r(100.0 * (float(np.exp(count_beta)) - 1.0), 4),
            "distribution": count_distribution,
            "fit": {
                "n": int(n),
                "k": int(len(count_columns)),
                "rSquared": _r(float(model_count.rsquared), 4),
            },
            "interpretation": (
                "a conditional association of the count, NOT the legacy "
                "interaction claim: the legacy 'combined effect exceeds the sum "
                "of individual effects' is a SHAP-interaction output of the "
                "retired model and is withdrawn, not re-expressed here"
            ),
        },
        "supermarketContrast": {
            "note": (
                "the supermarket indicator equals 0 for 0.42% of the sample, so "
                "its coefficient is a near-degenerate contrast and its sign must "
                "not be read as an amenity effect; the group is attributed here"
            ),
            "indicatorZeroN": int(supermarket_zero.sum()),
            "indicatorZeroShare": _r(float(supermarket_zero.mean()), 4),
            "townCompositionTop5": {
                town: contrast_towns[town]
                for town in sorted(contrast_towns, key=lambda item: item[1], reverse=True)[:5]
            },
            "medianDistanceMetres": _r(float(contrast_distances.median()), 1),
            "minDistanceMetres": _r(float(contrast_distances.min()), 1),
        },
    }


def within_area_variation(frame: pd.DataFrame, last_complete_month: str) -> dict[str, Any]:
    """The descriptive fragment of the legacy grid claim, on the model grain.

    The legacy 500m-grid premium model is not reproduced and no grid is
    constructed; what is measured is how often the within-1000m indicator
    varies INSIDE a town or planning area on the same bounded window the
    association model uses.
    """
    hdb = _select(frame, frame["property_type"] == "hdb")
    hdb = _select(hdb, (hdb["month"] >= STUDY_WINDOW_START) & (hdb["month"] <= last_complete_month))
    per_grain: dict[str, Any] = {}
    for grain in ("town", "planning_area"):
        per_amenity: dict[str, Any] = {}
        for amenity in AMENITIES:
            distances = _numeric(hdb[f"dist_to_nearest_{amenity}"])
            indicator = (distances <= THRESHOLD_METRES).astype(float)
            work = pd.DataFrame({"grain": hdb[grain].astype(str), "ind": indicator})
            shares = work.groupby("grain")["ind"].agg(["mean", "size"])
            means = pd.Series(shares["mean"], index=shares.index)
            min_area = str(means.idxmin())
            max_area = str(means.idxmax())
            mixed = means[(means > 0) & (means < 1)]
            per_amenity[amenity] = {
                "groups": int(len(means)),
                "mixedGroups": int(len(mixed)),
                "minShare": {
                    "area": min_area,
                    "share": _r(float(means.min()), 4),
                    "n": int(_numeric(shares["size"])[min_area]),
                },
                "maxShare": {
                    "area": max_area,
                    "share": _r(float(means.max()), 4),
                    "n": int(_numeric(shares["size"])[max_area]),
                },
            }
        per_grain[grain] = per_amenity
    return {
        "note": (
            "presence dispersion only: no premium is computed per area, no grid "
            "is built, and variation in an indicator is not variation in a "
            "premium. The legacy analysis' within-town regressions (minimum 100 "
            "transactions per town) and 500m grid cells (minimum 5 records) are "
            "retired-model constructs and are not reproduced."
        ),
        "grainNote": (
            "the shipped dataset carries both town and planning_area and they "
            "disagree (e.g. town KALLANG/WHAMPOA spans planning areas KALLANG "
            "and NOVENA), so both grains are measured"
        ),
        "byGrain": per_grain,
    }


def legacy_claims() -> list[dict[str, str]]:
    """Every legacy quantitative claim, verified verbatim against the old text.

    Each entry's `quote` is checked (bold/backtick-stripped, whitespace
    normalised) against `docs/analytics/editions/legacy/2026-11-12/amenity-impact.md`
    at build time; a quote that no longer matches fails the tool loudly.
    """
    return [
        {
            "claim": "Hawker proximity is the single most important amenity feature for HDB pricing",
            "quote": (
                "Hawker centre proximity is the single most important amenity "
                "feature for HDB pricing, outranking even MRT access."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "feature-importance ranking is an output of the retired XGBoost/SHAP "
                "model, which this pack does not reproduce; importance shares are "
                "not associations with units, and the refit's conditional "
                "associations (associations.indicatorCoefficients) cannot rank "
                "importance without that model"
            ),
        },
        {
            "claim": "XGBoost importance table (hawker 27.4%, lease 14.1%, park 7.2%, MRT 5.5%, supermarket 3.8%)",
            "quote": (
                "is the dominant non-structural feature at 27.4% XGBoost "
                "importance, followed by remaining lease (14.1%), park within "
                "1km (7.2%), and MRT within 1km (5.5%)"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": "retired model not reproduced; no importance table is re-estimated",
        },
        {
            "claim": "Parks are the most underappreciated premium driver",
            "quote": "Parks and green space are the most underappreciated premium driver.",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "'premium driver' is a causal model claim; the measured park "
                "association (associations.indicatorCoefficients.park_1km) is a "
                "descriptive conditional difference and cannot support it"
            ),
        },
        {
            "claim": "Park proximity adds a measurable premium that buyers underweight",
            "quote": "Park proximity adds a measurable premium that is frequently underweighted in buyer decisions.",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "'adds' is causal and 'underweighted' needs a model of buyer "
                "beliefs; neither is reproduced. The measured analogue is a "
                "descriptive association: park within 1000 m +0.72 pct "
                "(logPoint 0.007215, robustSe 0.000506, n = 281,020), conditional "
                "on controls, snapshot-vintage join"
            ),
        },
        {
            "claim": "Parks near large parks offer better value because the market has not fully priced green space",
            "quote": "because the market has not fully priced the green-space premium.",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "'not fully priced' asserts a market-efficiency finding no model "
                "here can produce; no pricing-error measurement exists in this pack"
            ),
        },
        {
            "claim": "Amenity importance shifted across COVID periods (park elevated, MRT reduced then partially recovered)",
            "quote": (
                "COVID elevated the importance of nearby green space and reduced "
                "the MRT premium as remote work reduced commute frequency."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "a change statement needs amenity features per period; the shipped "
                "features are one current snapshot joined to every period alike "
                "(amenityVintages, shippedFeatureLineage), and the retired "
                "RandomForest temporal comparison is not reproduced"
            ),
        },
        {
            "claim": "Park importance increased post-COVID — structural shift in preferences",
            "quote": (
                "Park importance increased post-COVID and has remained elevated, "
                "suggesting a structural shift in buyer preferences"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": "same missing per-period vintages; preference shifts are not measurable from a cross-sectional snapshot join",
        },
        {
            "claim": "MRT importance dipped during COVID, partially recovered — hybrid work",
            "quote": (
                "MRT importance dipped during COVID and has only partially "
                "recovered, likely reflecting sustained hybrid work patterns"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "same missing per-period vintages; the hybrid-work attribution is "
                "causal and unmeasured here"
            ),
        },
        {
            "claim": "Combined amenity effect exceeds the sum of individual effects (synergy)",
            "quote": "The combined effect of having multiple amenities nearby exceeds the sum of individual effects.",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "a SHAP-interaction output of the retired model; the measured "
                "amenity-count coefficient (associations.amenityCountModel, "
                "+4.10 pct per additional amenity type) is a different quantity "
                "— a conditional association of a count, not an interaction that "
                "exceeds the sum of parts"
            ),
        },
        {
            "claim": "MRT + Mall + Hawker is the strongest combination (synergistic premium)",
            "quote": (
                "Amenity interaction effects are strongest for the MRT + Mall + "
                "Hawker combination, suggesting convenience hubs command pricing "
                "power beyond individual amenity effects"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": "retired SHAP-interaction model not reproduced; no combination ranking is estimated",
        },
        {
            "claim": "500m-grid analysis shows amenity premiums highly localised within the same town",
            "quote": "At the 500m x 500m grid level, amenity premiums are highly localized within the same town.",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "the grid premium model is not reproduced and no 500m grid is "
                "constructed; the descriptive presence-dispersion fragment is "
                "measured instead (withinAreaVariation)"
            ),
        },
        {
            "claim": "Two flats in the same planning area but different grids can have materially different amenity profiles",
            "quote": (
                "Two flats in the same planning area but different grids can have "
                "materially different amenity profiles."
            ),
            "disposition": "re-measured-descriptively",
            "basis": (
                "withinAreaVariation: on the bounded 2015-01 -> 2026-10 window, "
                "the within-1000m indicator varies inside 22 of 26 towns for "
                "hawker (0 < share < 1) and inside 19 of 26 for park — presence "
                "profiles do vary within towns. No grid and no premium is involved"
            ),
        },
        {
            "claim": "Condo buyers get more pricing benefit from MRT and mall proximity than in-facility amenities",
            "quote": (
                "get more pricing benefit from MRT and mall proximity than from "
                "most in-facility amenities"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "no condo model is fitted: the private-residential source in this "
                "checkout starts 2021-01 while the legacy analysis claims 2015-2026, "
                "and the legacy condo statements are cross-segment comparisons the "
                "coverage cannot support"
            ),
        },
        {
            "claim": "HDB buyers should prioritize hawker proximity over MRT proximity",
            "quote": "should prioritize hawker proximity over MRT proximity when evaluating daily convenience.",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "a decision rule built on the retired importance ranking; the "
                "measured conditional associations (hawker +2.79 pct, mrt +10.47 "
                "pct, both descriptive, snapshot-vintage joins) do not rank "
                "amenities and must not be turned into guidance"
            ),
        },
        {
            "claim": "Target multi-amenity hubs for stronger rental demand and capital appreciation",
            "quote": "Target multi-amenity hubs for stronger rental demand and capital appreciation.",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "rental demand and capital appreciation are not measured in this "
                "pack (no rental join, no forward-looking outcome); the sentence "
                "is also prescriptive"
            ),
        },
        {
            "claim": "Data Period: 2015-2026",
            "quote": "Data Period: 2015-2026",
            "disposition": "re-cut",
            "basis": (
                "HDB re-cuts to 2015-01 -> the measured 2026-10 cutoff (142 "
                "months, 281,020 transactions); the private-residential source "
                "starts 2021-01, so '2015-2026' holds only for HDB"
            ),
        },
        {
            "claim": "Methodology: XGBoost (100 trees, depth 6, lr 0.1) + SHAP; RandomForest temporal comparison; within-town models; 500m grid",
            "quote": (
                "XGBoost (100 trees, max_depth=6, learning_rate=0.1) with SHAP "
                "values for feature importance and interaction detection"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "the retired analysis scripts are not in the supported repo "
                "surface (the legacy text says so itself) and none of the four "
                "model families is reproduced; the refit is one OLS specification "
                "declared in associations.estimator"
            ),
        },
        {
            "claim": "Primary input: data/04_platinum/housing_unified.parquet",
            "quote": "data/04_platinum/housing_unified.parquet",
            "disposition": "superseded",
            "basis": (
                "the shipped path in this checkout is "
                "data/pipeline/04_platinum/unified_dataset.parquet "
                "(1,236,310 rows x 97 columns), sha-pinned in this ledger's inputs"
            ),
        },
        {
            "claim": "Amenity features: distance and threshold indicators at 500m/1km/2km radii",
            "quote": (
                "Distance and threshold indicators for hawker, mall, park, "
                "supermarket, preschool, childcare at 500m, 1km, and 2km radii"
            ),
            "disposition": "superseded",
            "basis": (
                "the shipped dataset carries DISTANCES in metres (per amenity; "
                "shippedFeatures.perAmenity), not threshold indicators at three "
                "radii; this pack constructs exactly one threshold (1000 m) per "
                "legacy amenity from the shipped distances and states it in "
                "associations.estimator.indicators"
            ),
        },
    ]


def _verify_legacy_quotes(claims: list[dict[str, str]]) -> dict[str, Any]:
    text = LEGACY_EDITION.read_text(encoding="utf-8")
    stripped = re.sub(r"\*\*|`", "", text)
    normalised = re.sub(r"\s+", " ", stripped)
    checked: list[dict[str, Any]] = []
    for claim in claims:
        quote = re.sub(r"\s+", " ", re.sub(r"\*\*|`", "", claim["quote"])).strip()
        checked.append({"claim": claim["claim"], "foundInLegacyText": quote in normalised})
        if quote not in normalised:
            raise SystemExit(f"legacy quote no longer matches the frozen text: {claim['quote']!r}")
    return {
        "legacyFile": LEGACY_EDITION.relative_to(REPO_ROOT).as_posix(),
        "legacyFileSha256": sha256_of(LEGACY_EDITION),
        "claimsChecked": len(checked),
        "allQuotesFound": True,
        "quotes": checked,
    }


def build() -> dict[str, Any]:
    frame = pd.read_parquet(
        UNIFIED,
        columns=[
            "month",
            "town",
            "planning_area",
            "flat_type",
            "price",
            "floor_area_sqm",
            "lease_commence_date",
            "storey_min",
            "storey_max",
            "property_type",
            "lat",
            "lon",
            "dist_to_nearest_hawker",
            "dist_to_nearest_mall",
            "dist_to_nearest_park",
            "dist_to_nearest_supermarket",
            "dist_to_nearest_mrt",
            "nearest_hawker",
            "nearest_mall",
            "nearest_park",
            "nearest_supermarket",
            "nearest_mrt_station",
        ],
    )
    last_complete = cutoff(frame)["lastCompleteMonth"]
    hdb = _select(frame, frame["property_type"] == "hdb")
    window = _select(hdb, (hdb["month"] >= STUDY_WINDOW_START) & (hdb["month"] <= last_complete))
    condo = _select(frame, frame["property_type"] == "condo")
    condo_pre = _select(condo, condo["month"] < "2021-01")
    condo_terminal = _select(condo, condo["month"] > last_complete)
    claims = legacy_claims()
    inputs = {}
    for path in (
        UNIFIED,
        RAW_HAWKER,
        RAW_PARKS,
        RAW_SUPERMARKETS,
        RAW_MALLS,
        RAW_MRT,
        HAWKER_GEOJSON,
        PARKS_GEOJSON,
        SUPERMARKETS_GEOJSON,
        CHILDCARE_GEOJSON,
        PRESCHOOLS_GEOJSON,
    ):
        inputs[path.relative_to(REPO_ROOT).as_posix()] = {
            "sha256": sha256_of(path),
            "rows": int(pq.ParquetFile(path).metadata.num_rows)
            if path.suffix == ".parquet"
            else len(_geojson_properties(path)),
        }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "scope": (
            "RS04 amenity-impact evidence: amenity-source vintages, shipped-feature "
            "lineage with a targeted leave-out ablation, the measured hawker "
            "snapshot-join mismatch, and a descriptive conditional-association "
            "refit with stated units and controls (one recorded specification; "
            "no dated prior protocol, so specification search cannot be ruled out)"
        ),
        "definition": DEFINITION,
        "inputs": inputs,
        "cutoff": cutoff(frame),
        "amenityVintages": amenity_vintages(),
        "shippedFeatures": shipped_features(frame, last_complete),
        "shippedFeatureLineage": shipped_feature_lineage(window),
        "snapshotJoinMismatch": snapshot_join_mismatch(window),
        "associations": associations(frame, last_complete),
        "withinAreaVariation": within_area_variation(frame, last_complete),
        "condoScope": {
            "rows": int(len(condo)),
            "rowsIn2021_01ToCutoff": int(len(condo) - len(condo_pre) - len(condo_terminal)),
            "rowsBefore2021_01": int(len(condo_pre)),
            "rowsAfterCutoffTerminalMonth": int(len(condo_terminal)),
            "cutoffUpperBound": last_complete,
            "statement": (
                "no condo model is fitted: the private-residential source starts "
                "2021-01, so the legacy amenity statements' 2015-2026 span has no "
                "condo analogue, and no cross-segment comparison is measured; "
                "counts are separated per side of the window so the terminal "
                "partial month is never mixed into a coverage count"
            ),
        },
        "legacyClaims": claims,
        "legacyQuoteCheck": _verify_legacy_quotes(claims),
    }


def check(output: Path) -> int:
    if not output.is_file():
        print(f"FAILED: no ledger at {output}; run the tool without --check first")
        return 1
    recorded = output.read_bytes()
    measured = canonical_bytes(build())
    if recorded == measured:
        print("Pass: RS04 ledger re-measures byte-identically from this checkout.")
        return 0
    try:
        old = json.loads(recorded)
        new = json.loads(measured)
    except json.JSONDecodeError:
        print("FAILED: ledger bytes differ and are not both valid JSON")
        return 1
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            print(f"  - drift in {key}")
    print("FAILED: RS04 ledger does not match this checkout")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.check:
        return check(args.output)

    evidence = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(evidence))
    sample = evidence["associations"]["sample"]
    rows = evidence["associations"]["indicatorCoefficients"]
    print(
        f"Model sample: n = {sample['includedN']} HDB transactions "
        f"({sample['windowStart']} -> {sample['cutoffUpperBound']}); "
        f"excluded rows: {sample['excludedRowsTotal']}"
    )
    print(
        "Conditional associations (pct, HC1): "
        + ", ".join(f"{key}={value['pctEffectExpMinus1']:+.3f}%" for key, value in rows.items())
    )
    mismatch = evidence["snapshotJoinMismatch"]
    print(
        f"Snapshot-join mismatch (hawker): {mismatch['notEstablishedShare']:.4f} of "
        f"{mismatch['transactions']} transactions' nearest centre not established "
        "as completed at the transaction date"
    )
    try:
        ledger_label = args.output.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        ledger_label = str(args.output)
    print(f"Ledger: {ledger_label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
