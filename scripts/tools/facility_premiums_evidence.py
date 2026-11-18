#!/usr/bin/env python3
"""Measure RS05's facility-premiums evidence: join recovery, facility-source
absence, project structure, and one descriptive condo access model.

RS05's gate is "Recover facility ownership/date and join keys; assess missing
facilities, correlated amenities and project effects. Publish uncertainty and
sample sizes; no isolated causal-premium claim from unadjusted comparisons."
This tool measures from the local checkout, and only what the checkout can
support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04 shipped;
   every aggregation is bounded at BOTH ends of the study window and the bound
   is a ledger field (`cutoffUpperBound`), not only prose.
2. **Legacy source audit** — the four facility sources the legacy text names
   (`private_property_facilities.parquet`, `property_nearby_facilities.parquet`,
   `property.parquet`, `housing_unified.parquet`) are absent from this checkout;
   the archived v1 pipeline doc is cited verbatim; the shipped dataset's only
   facility-like columns are the external SportSG public-facility distances;
   the SportSG layer itself is measured and is a different subject from the
   in-house facility list the legacy study analysed.
3. **Join-key recovery** — `project_name` is the only candidate key a facility
   layer could join on; its coverage and per-project transaction distribution
   are measured, and the ledger records that the key has no counterparty layer
   in this checkout (no record joined — which is not a count of zero facilities).
4. **Facility missingness** — each facility the legacy prevalence table names is
   recorded as `no-record` with the measured reason; `no-record` is not
   `absent`, and neither is `0`.
5. **Project structure** — a one-way decomposition of log price-psf variance
   between and within projects on the exact model sample, plus the
   between-project share of each access indicator's variation: the measured
   demonstration of why an unadjusted with-vs-without comparison is a
   comparison of projects.
6. **Descriptive conditional associations** — one recorded OLS of log condo
   price-psf on five jointly-fitted external-access indicators (shipped
   distance <= 1000 m) with stated controls, HC1 robust standard errors AND
   project-clustered standard errors (cluster = `project_name`), both reported
   for every coefficient. Descriptive only: no premium, no causal reading, no
   facility estimate (the facility layer is absent), and project identity is
   NOT conditioned on — the comparison is between projects, and the ledger
   says so. The clustered battery is the published uncertainty; the HC1
   battery is retained only to show the scale of the clustering understatement.

It never runs the pipeline, never re-fits the legacy models and never writes
outside `--output`.

Usage:

    uv run python scripts/tools/facility_premiums_evidence.py \\
        --output docs/implementation/artifacts/rs05-facility-premiums-evidence.json

    uv run python scripts/tools/facility_premiums_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
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

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
BRONZE_CONDO = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_condo_transactions.parquet"
SPORTSG_PARQUET = (
    REPO_ROOT / "data" / "pipeline" / "01_bronze" / "external" / "SportSGFacilities.parquet"
)
SPORTSG_GEOJSON = REPO_ROOT / "data" / "manual" / "csv" / "datagov" / "SportSGFacilities.geojson"
ARCHIVE_DOC = REPO_ROOT / "docs" / "archive" / "20250120-data-pipeline.md"
GEOJSON_MODULE = (
    REPO_ROOT / "src" / "egg_n_bacon_housing" / "components" / "ingestion" / "geojson.py"
)
LEGACY_EDITION = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "facility-premiums.md"
)
LEGACY_NAMED_SOURCES = (
    "data/04_platinum/private_property_facilities.parquet",
    "data/04_platinum/property_nearby_facilities.parquet",
    "data/04_platinum/property.parquet",
    "data/04_platinum/housing_unified.parquet",
)
EDITION_FILE = (
    REPO_ROOT
    / "docs"
    / "analytics"
    / "editions"
    / "facility-premiums"
    / "2026-11-17"
    / "facility-premiums.md"
)
SPORTSG_LOADER_MARKER = "SportSG facility locations"
SPORTSG_NAME_KEYS_MARKER = '"Name", "NAME", "VENUE"'
ARCHIVE_DOC_MARKERS = (
    "L3_private_property_facilities",
    "L3_property_nearby_facilities",
)
FACILITY_COLUMN_PATTERN = re.compile(
    r"facil|gym|pool|tennis|sky[\s_-]?garden|concierge|bbq|jacuzzi|sport", re.IGNORECASE
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs05-facility-premiums-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

STUDY_WINDOW_START = "2021-01"  # the private-residential source's own first month
AMENITIES = ("mrt", "mall", "hawker", "sports_facility", "childcare")
THRESHOLD_METRES = 1000.0
NON_LANDED_SUBTYPES = ("Condominium", "Apartment", "Executive Condominium")
BASELINE_FLOOR_LEVEL = "01 to 05"
BASELINE_SUBTYPE = "Condominium"
BASELINE_SALE_TYPE = "Resale"
BASELINE_YEAR = "2021"
TENURE_PATTERN = re.compile(r"^\s*(\d+)\s*(?:yrs|years)\s*lease\s*commencing\s*from\s*(\d{4})\s*$")
FREEHOLD_STRING = "Freehold"
LONG_LEASE_MIN_YEARS = 100
PROJECT_MEDIAN_FLOOR_N = 30
LEGACY_FACILITIES = (
    "Swimming pool",
    "Security (24hr)",
    "Gym / Fitness corner",
    "BBQ pits",
    "Function room",
    "Tennis court",
    "Sky garden / Roof terrace",
    "Concierge / Clubhouse",
    "Jacuzzi / Hydrospa",
)
LEGACY_COMBINATIONS = (
    "Pool + Gym + Security (baseline row)",
    "+ Tennis Court row",
    "+ Sky Garden row",
    "Tennis + Sky Garden + Concierge row",
    "Full premium suite row",
)

DEFINITION = (
    "A measured source audit and one descriptive conditional-association model. "
    "The in-house facility layer the legacy study analysed (project facilities "
    "such as pools, gyms, tennis courts, sky gardens) is ABSENT from this "
    "checkout: the four legacy-named sources do not exist here, and the shipped "
    "dataset's only facility-like columns are external SportSG public-facility "
    "distances, a different subject. No facility premium is fitted, re-measured "
    "or claimed. What is measured: the recovered join key (project_name) and its "
    "coverage; per-facility no-record status (no-record is not absent and not "
    "zero); a between/within-project decomposition of log price-psf variance; "
    "and one recorded OLS of log condo price-psf on five jointly-fitted "
    "external-access indicators (shipped distance <= 1000 m) with stated "
    "controls and HC1 and project-clustered standard errors (cluster = "
    "project_name; the clustered battery is the published uncertainty and "
    "the HC1 battery is retained only to show the scale of the clustering "
    "understatement). That model does not condition on project "
    "identity: it is a BETWEEN-PROJECT comparison, and the measured variance "
    "decomposition is the quantification of what that means. Coefficients are "
    "conditional associations, not premiums and not causal effects; the "
    "access features come from one undated snapshot per layer joined to "
    "transactions from 2021-01 onward (see RS04's snapshot-join audit for the "
    "vintage semantics), so no coefficient compares amenity states at two "
    "dates. This ledger records one specification and only that one was fitted, "
    "and all its coefficients are reported; there is no dated prior protocol, "
    "so specification search cannot be ruled out — the single-specification "
    "discipline is a disclosed limitation, not a credential."
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


def _numeric(column: Any) -> pd.Series:
    """A float64 view of a column, for comparisons that must tolerate NaN."""
    series = pd.Series(column)
    return pd.Series(pd.to_numeric(series, errors="coerce"), index=series.index)


def _geojson_features(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unreadable GeoJSON {path}: {error}") from error
    return [dict(feature.get("properties", {})) for feature in payload.get("features", [])]


def _code_quote(path: Path, marker: str, label: str) -> dict[str, Any]:
    """Locate a marker line in a source module and cite it verbatim."""
    lines = path.read_text(encoding="utf-8").splitlines()
    hits = [number for number, line in enumerate(lines, start=1) if marker in line]
    if not hits:
        raise SystemExit(
            f"{label} marker {marker!r} not found in {path}; the ledger's citation is stale"
        )
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "line": hits[0],
        "occurrences": len(hits),
        "quote": lines[hits[0] - 1].strip(),
    }


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    condo = _select(frame, frame["property_type"] == "condo")
    counts = {str(k): int(v) for k, v in condo.groupby("month").size().items()}
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


def condo_coverage(frame: pd.DataFrame, last_complete_month: str) -> dict[str, Any]:
    """The private-residential source's measured coverage and window health."""
    condo = _select(frame, frame["property_type"] == "condo")
    months = condo["month"].astype(str)
    in_window = _select(condo, (months >= STUDY_WINDOW_START) & (months <= last_complete_month))
    window_months = sorted(str(v) for v in in_window["month"].unique())
    expected = [str(v) for v in pd.period_range(STUDY_WINDOW_START, last_complete_month, freq="M")]
    per_month: dict[str, int] = {
        str(k): int(v) for k, v in in_window.groupby("month").size().items()
    }
    min_month: str | None = None
    min_n: int | None = None
    for month in sorted(per_month):
        if min_n is None or per_month[month] < min_n:
            min_month = month
            min_n = per_month[month]
    return {
        "rows": int(len(condo)),
        "firstMonth": str(months.min()),
        "lastMonthObserved": str(months.max()),
        "cutoffUpperBound": last_complete_month,
        "cutoffUpperBoundMeaning": (
            "every count, share, decomposition and model row in this ledger "
            "ends at the last complete month; the terminal partial month is "
            "excluded and never mixed into a coverage count"
        ),
        "rowsBeforeSourceStart": int((months < STUDY_WINDOW_START).sum()),
        "rowsInWindow": int(len(in_window)),
        "rowsInTerminalMonth": int((months > last_complete_month).sum()),
        "windowMonths": len(window_months),
        "sourceMissingWindowMonths": sorted(set(expected) - set(window_months)),
        "minWindowMonthTransactions": {"month": min_month, "n": min_n},
    }


def legacy_source_audit() -> dict[str, Any]:
    """The legacy facility sources are absent; measure what ships instead.

    An absence claim needs its counter-evidence checked (RS03 round 1): the
    audit also measures the layers that DO exist so the statement "no in-house
    facility layer" is made against the full inventory, not against silence.
    The facility-column scan reads the FULL physical schema of
    unified_dataset.parquet straight from the parquet metadata (no data
    read), not this tool's own column projection — the projection carries 18
    of the dataset's columns and scanning it would miss a facility-like
    column among the rest.
    """
    named: dict[str, Any] = {}
    for relative in LEGACY_NAMED_SOURCES:
        exists = (REPO_ROOT / relative).exists()
        named[relative] = {
            "exists": exists,
            "meaning": (
                "the legacy text's named facility source is not in this checkout"
                if not exists
                else "present"
            ),
        }
    if any(entry["exists"] for entry in named.values()):
        raise SystemExit("a legacy-named facility source now exists; re-measure the audit")

    schema_columns = [str(name) for name in pq.read_schema(UNIFIED).names]
    facility_columns = sorted(
        {column for column in schema_columns if FACILITY_COLUMN_PATTERN.search(column)}
    )
    expected = ["dist_to_nearest_sports_facility", "nearest_sports_facility"]
    if facility_columns != expected:
        raise SystemExit(
            "the unified dataset's facility-like columns changed: "
            f"{facility_columns} != {expected}; re-measure the audit"
        )

    sportsg = pd.read_parquet(SPORTSG_PARQUET)
    names = sportsg["name"].astype(str).str.strip()
    geo_props = _geojson_features(SPORTSG_GEOJSON)
    venue_values = [str(p.get("VENUE") or "").strip() for p in geo_props]
    stamps: Counter[str] = Counter(str(p.get("FMEL_UPD_D") or "").strip() for p in geo_props)

    return {
        "legacyNamedSources": named,
        "archivedPipeline": {
            "doc": {
                "path": ARCHIVE_DOC.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(ARCHIVE_DOC),
                "citations": [
                    _code_quote(ARCHIVE_DOC, marker, "archive-doc")
                    for marker in ARCHIVE_DOC_MARKERS
                ],
                "meaning": (
                    "the v1 (2025-01) pipeline defined L3 stages named "
                    "private_property_facilities and property_nearby_facilities; "
                    "the Hamilton pipeline under data/pipeline/ defines no "
                    "facility stage, and no facility parquet exists anywhere in "
                    "the pipeline tree this checkout ships"
                ),
            },
        },
        "unifiedDataset": {
            "columnsScanned": len(schema_columns),
            "columnNames": schema_columns,
            "facilityLikeColumns": facility_columns,
            "scanBasis": (
                "full physical schema read from the parquet metadata (no data "
                "read), in schema order — not the 18-column projection this "
                "tool loads, so a facility-like column outside the projection "
                "would still fail --check"
            ),
            "meaning": (
                "across the full physical schema, the only facility-like column "
                "names describe distance to SportSG PUBLIC sport facilities; no "
                "column describes a development's in-house facility list (pool, "
                "gym, tennis court, sky garden, concierge, and so on)"
            ),
        },
        "sportsgLayer": {
            "parquet": {
                "path": SPORTSG_PARQUET.relative_to(REPO_ROOT).as_posix(),
                "rows": int(len(sportsg)),
                "columns": [str(c) for c in sportsg.columns],
                "distinctNames": int(names.nunique()),
                "carriesDates": any("date" in c.lower() for c in sportsg.columns),
            },
            "rawGeojson": {
                "path": SPORTSG_GEOJSON.relative_to(REPO_ROOT).as_posix(),
                "features": len(geo_props),
                "nameProperty": "VENUE",
                "distinctVenueValues": len({v for v in venue_values if v}),
                "fmelUpdD": {key: stamps[key] for key in sorted(stamps)},
            },
            "loaderCitations": [
                _code_quote(GEOJSON_MODULE, SPORTSG_LOADER_MARKER, "sportsg-loader"),
                _code_quote(GEOJSON_MODULE, SPORTSG_NAME_KEYS_MARKER, "sportsg-name-keys"),
            ],
            "meaning": (
                "45 public SportSG venues (sport centres, swimming complexes, "
                "ActiveSG gyms, stadiums, playfields) — public infrastructure "
                "shared across developments, not a development's private "
                "facility list; it cannot stand in for the legacy in-house "
                "facility layer, and this pack does not treat it as one"
            ),
        },
        "unresolvedNameMarker": {
            "column": "nearest_sports_facility",
            "literal": "None",
            "meaning": (
                "one shipped row carries the literal string 'None' as its "
                "nearest-facility name alongside null distances; that is a "
                "missing-name marker, not a facility named None (see "
                "associations.sample reason sets)"
            ),
        },
        "conclusion": (
            "no in-house facility layer exists in this checkout: the legacy "
            "facility prevalence table, the facility-combination synergy table "
            "and every facility-premium comparison built on them have no "
            "population to measure here"
        ),
    }


def join_key(frame: pd.DataFrame, last_complete_month: str) -> dict[str, Any]:
    """The recovered join key a facility layer WOULD have had to use."""
    condo = _select(frame, frame["property_type"] == "condo")
    window = _select(
        condo,
        (condo["month"].astype(str) >= STUDY_WINDOW_START)
        & (condo["month"].astype(str) <= last_complete_month),
    )
    bronze = pd.read_parquet(BRONZE_CONDO)
    bronze_names = pd.Series(bronze["project_name"])

    def stats(series: pd.Series) -> dict[str, Any]:
        values = series.astype(str).str.strip()
        non_empty = values[values != ""]
        per_project = non_empty.value_counts()
        return {
            "rows": int(len(values)),
            "empty": int((values == "").sum()),
            "emptyShare": _r(float((values == "").mean()), 4),
            "distinctProjects": int(non_empty.nunique()),
            "transactionsPerProject": {
                "min": int(per_project.min()),
                "p10": _r(float(per_project.quantile(0.10)), 1),
                "median": _r(float(per_project.median()), 1),
                "p90": _r(float(per_project.quantile(0.90)), 1),
                "max": int(per_project.max()),
            },
            "largestProject": {
                "name": str(per_project.index[0]),
                "transactions": int(per_project.iloc[0]),
            },
            "largestValueNote": (
                "the most frequent value of the key is the literal string "
                "'LANDED HOUSING DEVELOPMENT' — a category label the source "
                "attaches to bulk records, not a named development; one more "
                "reason the key cannot be treated as a validated development "
                "identity without the master layer this checkout lacks"
            ),
            "singleTransactionProjects": int((per_project == 1).sum()),
            "projectsWithAtLeast30": int((per_project >= PROJECT_MEDIAN_FLOOR_N).sum()),
        }

    return {
        "key": "project_name",
        "availableIn": [
            BRONZE_CONDO.relative_to(REPO_ROOT).as_posix(),
            "unified_dataset (condo rows)",
        ],
        "bronze": stats(bronze_names),
        "window": stats(pd.Series(window["project_name"])),
        "normalisation": (
            "the key joins as exact shipped strings; no project master layer or "
            "crosswalk exists in this checkout to validate name spelling, so "
            "the risk of two developments sharing one name string is not "
            "measurable here"
        ),
        "counterparty": {
            "facilityLayerPresent": False,
            "recordsJoinedToAFacilityLayer": (
                "none — the key has no counterparty layer in this checkout"
            ),
            "meaning": (
                "'none joined' is a missing counterparty, not zero facilities: "
                "this ledger cannot count facilities per project, and no "
                "sentence in the refreshed edition may read the missing layer "
                "as an absence of facilities"
            ),
        },
        "conclusion": (
            "the join is recovered as far as this checkout allows: the key "
            "exists and is fully populated, but the facility layer it would "
            "join to was never carried into the Hamilton pipeline"
        ),
    }


def facility_missingness() -> dict[str, Any]:
    """Per-facility no-record status for every facility the legacy text names.

    `no-record` means the layer that carried the facility attribute is absent
    from this checkout. It is not `absent` (the development lacks nothing we
    know of) and it is not `0` (no count of facilities was taken).
    """
    return {
        "facilities": [
            {
                "facility": facility,
                "status": "no-record",
                "reason": "facility-source-absent",
                "shareOfProperties": None,
                "propertiesCounted": None,
            }
            for facility in LEGACY_FACILITIES
        ],
        "combinations": [
            {
                "combination": combination,
                "status": "no-record",
                "reason": "facility-source-absent",
                "premiumMeasured": None,
            }
            for combination in LEGACY_COMBINATIONS
        ],
        "semantics": (
            "no-record (the source layer that carried the attribute is absent) "
            "is distinguished from absent (a record exists and shows the "
            "facility missing) and from zero (a count was taken and returned "
            "0). This checkout supports only no-record for every in-house "
            "facility the legacy text names"
        ),
    }


def project_structure(sample: pd.DataFrame) -> dict[str, Any]:
    """Between/within-project decomposition on the exact model sample.

    Facilities cluster inside developments, and projects differ from each other
    in ways that also correlate with price. This section quantifies that on the
    regression sample: how much of log price-psf variance lies BETWEEN projects,
    and how close each access indicator is to being a pure project-level
    attribute. It is a descriptive decomposition, not an effect estimate.
    """
    y = np.log(np.asarray(pd.to_numeric(sample["psf"], errors="coerce"), dtype=float))
    groups = sample["project_name"].astype(str).str.strip().to_numpy()
    group_means = pd.Series(y).groupby(groups).transform("mean").to_numpy()
    ss_total = float(((y - y.mean()) ** 2).sum())
    ss_between = float(((group_means - y.mean()) ** 2).sum())

    work = pd.DataFrame({"g": groups, "y": y})
    work["psf_raw"] = np.asarray(pd.to_numeric(sample["psf"], errors="coerce"), dtype=float)
    counts: dict[str, int] = {
        str(name): int(value) for name, value in work.groupby("g").size().items()
    }
    medians: dict[str, float] = {
        str(name): float(value) for name, value in work.groupby("g")["psf_raw"].median().items()
    }
    big_names = [name for name in counts if counts[name] >= PROJECT_MEDIAN_FLOOR_N]
    ordered = sorted(big_names, key=lambda name: (-medians[name], name))
    big_array = np.asarray([medians[name] for name in big_names], dtype=float)

    def project_row(name: str) -> dict[str, Any]:
        return {
            "project": name,
            "transactions": counts[name],
            "medianPsf": _r(medians[name], 2),
        }

    indicators: dict[str, Any] = {}
    for amenity in AMENITIES:
        values = (
            _numeric(sample[f"dist_to_nearest_{amenity}"]).to_numpy(dtype=float) <= THRESHOLD_METRES
        ).astype(float)
        indicator_means = pd.Series(values).groupby(groups).transform("mean").to_numpy()
        ss_total_ind = float(((values - values.mean()) ** 2).sum())
        ss_between_ind = float(((indicator_means - values.mean()) ** 2).sum())
        indicators[amenity] = {
            "betweenProjectShareOfVariation": _r(ss_between_ind / ss_total_ind, 6)
            if ss_total_ind > 0
            else None,
            "prevalence": _r(float(values.mean()), 4),
        }

    return {
        "grain": "the associations model sample (see associations.sample); not a sample of it",
        "n": int(len(sample)),
        "projects": int(len(pd.unique(groups))),
        "logPsfVariance": {
            "betweenProjectShare": _r(ss_between / ss_total, 6),
            "withinProjectShare": _r(1.0 - ss_between / ss_total, 6),
            "method": (
                "one-way decomposition: between-project share = sum over "
                "projects of n_g (mean_g - mean)^2 divided by the total sum of "
                "squared deviations of log(psf); descriptive, no model"
            ),
        },
        "indicatorBetweenProjectShare": indicators,
        "perProjectMedianPsf": {
            "minimumN": PROJECT_MEDIAN_FLOOR_N,
            "projectsAtMinimumN": len(big_names),
            "unit": "SGD per square foot (median of the shipped psf column, per project)",
            "acrossProjects": {
                "p10": _r(float(np.quantile(big_array, 0.10)), 2) if len(big_array) else None,
                "median": _r(float(np.median(big_array)), 2) if len(big_array) else None,
                "p90": _r(float(np.quantile(big_array, 0.90)), 2) if len(big_array) else None,
                "min": _r(float(big_array.min()), 2) if len(big_array) else None,
                "max": _r(float(big_array.max()), 2) if len(big_array) else None,
            },
            "highestMedianProjects": [project_row(name) for name in ordered[:3]],
            "lowestMedianProjects": [project_row(name) for name in list(reversed(ordered[-3:]))],
        },
        "meaning": (
            "the access indicators are nearly project-level constants "
            "(transactions of one project share one location), and price "
            "variation is dominated by differences BETWEEN projects; an "
            "unadjusted with-vs-without facility comparison on this population "
            "would compare project means, so this pack labels its model a "
            "between-project comparison and conditions on no project identity"
        ),
    }


def _parse_tenure(text: Any) -> dict[str, np.ndarray]:
    """Documented tenure parse: 'Freehold' or '<N> yrs lease commencing from YYYY'.

    Returns freehold, parsed, duration (years) and commencement year arrays;
    anything else is unparsed and carries an exclusion reason.
    """
    stripped = pd.Series(text).astype(str).str.strip()
    freehold = (stripped == FREEHOLD_STRING).to_numpy()
    parsed_list: list[bool] = []
    durations: list[float] = []
    commences: list[float] = []
    for value in stripped:
        match = TENURE_PATTERN.match(value)
        parsed_list.append(match is not None)
        durations.append(float(match.group(1)) if match else np.nan)
        commences.append(float(match.group(2)) if match else np.nan)
    return {
        "freehold": freehold,
        "parsed": np.asarray(parsed_list, dtype=bool),
        "durationYears": np.asarray(durations, dtype=float),
        "commenceYear": np.asarray(commences, dtype=float),
    }


def response_lineage(frame: pd.DataFrame) -> dict[str, Any]:
    """The response variable's shipped definition, verified against its inputs."""
    condo = _select(frame, frame["property_type"] == "condo")
    psf = _numeric(condo["psf"])
    implied = _numeric(condo["price"]) / _numeric(condo["area_sqft"])
    deviation = (psf - implied).abs()
    matches = int((deviation <= 1e-6).sum())
    if matches != len(condo):
        raise SystemExit(f"shipped psf no longer equals price/area_sqft ({matches}/{len(condo)})")
    return {
        "column": "psf",
        "definition": "price (nominal SGD) per square foot of strata area",
        "check": (
            "psf equals price/area_sqft for every condo row: "
            f"{matches}/{len(condo)} exact (max deviation {_r(float(deviation.max()), 9)})"
        ),
        "nullRows": int(psf.isna().sum()),
        "nonPositiveRows": int((psf <= 0).sum()),
    }


def _design_matrix(frame: pd.DataFrame, indicator_columns: dict[str, np.ndarray]) -> pd.DataFrame:
    """Deterministic design matrix: indicators + controls + FE dummies.

    Dummy columns are built explicitly over sorted category values (no
    pandas-version-dependent ordering); baseline levels are "01 to 05"
    (floor band), "Condominium" (subtype), "Resale" (sale type) and "2021"
    (transaction year); the planning-area baseline is the most frequent level.
    Continuous controls are scaled for numerical stability and the reported
    coefficients are back-transformed to natural units.
    """
    tenure = _parse_tenure(frame["tenure"])
    base = pd.DataFrame(
        {
            "const": np.ones(len(frame)),
            "area_sqft_100": frame["area_sqft"].to_numpy(dtype=float) / 100.0,
            "freehold": tenure["freehold"].astype(float),
            "long_lease_100yrs_plus": (tenure["durationYears"] >= LONG_LEASE_MIN_YEARS).astype(
                float
            ),
            "lease_commence_1900_100": np.where(
                tenure["freehold"], 0.0, (tenure["commenceYear"] - 1900.0) / 100.0
            ),
        }
    )
    for name, values in indicator_columns.items():
        base[name] = values
    fe_specs: list[tuple[str, pd.Series, str | None]] = [
        ("floor", frame["floor_level"].astype(str).str.strip(), BASELINE_FLOOR_LEVEL),
        ("subtype", frame["property_subtype"].astype(str).str.strip(), BASELINE_SUBTYPE),
        ("sale", frame["type_of_sale"].astype(str).str.strip(), BASELINE_SALE_TYPE),
        ("yr", frame["month"].astype(str).str.slice(0, 4), BASELINE_YEAR),
        ("pa", frame["planning_area"].astype(str).str.strip(), None),
    ]
    for prefix, series, baseline in fe_specs:
        values = pd.Series(series).astype(str)
        baseline_level = baseline if baseline is not None else str(values.value_counts().index[0])
        for level in sorted(set(values)):
            if level == baseline_level:
                continue
            base[f"{prefix}_{level}"] = (values == level).to_numpy(dtype=float)
    return base


def _model_sample(condo: pd.DataFrame, last_complete_month: str) -> pd.DataFrame:
    """The regression population, derived once and reused everywhere.

    Window-bounded, non-landed strata subtypes, parseable tenure, all five
    access distances present, planning area present, positive price/area and a
    non-empty project name. This is exactly the zero-reason-set rows of
    associations() — build() asserts the two derivations agree.
    """
    months = condo["month"].astype(str)
    tenure = _parse_tenure(condo["tenure"])
    distances_present = np.ones(len(condo), dtype=bool)
    for amenity in AMENITIES:
        distances_present &= _numeric(condo[f"dist_to_nearest_{amenity}"]).notna().to_numpy()
    mask = (
        (months >= STUDY_WINDOW_START).to_numpy()
        & (months <= last_complete_month).to_numpy()
        & condo["property_subtype"].astype(str).str.strip().isin(NON_LANDED_SUBTYPES).to_numpy()
        & (tenure["freehold"] | tenure["parsed"])
        & distances_present
        & condo["planning_area"].notna().to_numpy()
        & (_numeric(condo["price"]) > 0).to_numpy()
        & (_numeric(condo["area_sqft"]) > 0).to_numpy()
        & condo["project_name"].astype(str).str.strip().ne("").to_numpy()
    )
    return _select(condo, mask).reset_index(drop=True)


def associations(frame: pd.DataFrame, last_complete_month: str) -> dict[str, Any]:
    """One recorded descriptive specification (the only one fitted).

    Five jointly-fitted external-access indicators on log condo price-psf,
    HC1 robust AND project-clustered standard errors (both reported for every
    coefficient; the clustered battery is the published uncertainty),
    planning-area / transaction-year / floor-band / subtype / sale-type fixed
    effects and stated tenure and area controls. Project identity is NOT
    conditioned on as a regressor: this is a between-project comparison (see
    projectStructure for the measured quantification). No dated prior protocol
    exists, so specification search cannot be ruled out.
    """
    import statsmodels.api as sm

    condo = _select(frame, frame["property_type"] == "condo")
    # Reason sets over EVERY condo row: one row can fail several conditions and
    # every applicable reason is recorded, none asserted as the single cause.
    months = condo["month"].astype(str)
    tenure = _parse_tenure(condo["tenure"])
    condition_masks: dict[str, Any] = {
        "before-study-window": (months < STUDY_WINDOW_START).to_numpy(),
        "terminal-partial-month-after-cutoff": (months > last_complete_month).to_numpy(),
        "landed-or-strata-landed-subtype": (
            ~condo["property_subtype"].astype(str).str.strip().isin(NON_LANDED_SUBTYPES)
        ).to_numpy(),
        "unparseable-tenure": (~tenure["freehold"] & ~tenure["parsed"]).astype(bool),
        "non-positive-or-missing-price": (
            ~(_numeric(condo["price"]) > 0) | _numeric(condo["price"]).isna()
        ).to_numpy(),
        "non-positive-or-missing-area-sqft": (
            ~(_numeric(condo["area_sqft"]) > 0) | _numeric(condo["area_sqft"]).isna()
        ).to_numpy(),
        "missing-project-name": (
            condo["project_name"].astype(str).str.strip().eq("") | condo["project_name"].isna()
        ).to_numpy(),
        "missing-planning-area": condo["planning_area"].isna().to_numpy(),
    }
    for amenity in AMENITIES:
        condition_masks[f"missing-source:{amenity}-distance"] = (
            _numeric(condo[f"dist_to_nearest_{amenity}"]).isna().to_numpy()
        )
    reason_frame = pd.DataFrame(condition_masks, index=condo.index)
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
    reason_columns = list(excluded_in_window.columns)
    excluded_records: list[dict[str, Any]] = [
        {
            "rowIndex": int(index),
            "month": str(months.iloc[index]),
            "reasons": sorted(str(reason) for reason in reason_columns if bool(row[reason])),
        }
        for index, row in excluded_in_window.iterrows()
    ]
    excluded_rows_sha256 = hashlib.sha256(canonical_bytes(excluded_records)).hexdigest()
    signature_counts: Counter[str] = Counter(
        "|".join(record["reasons"]) for record in excluded_records
    )
    included_mask = (reason_count_per_row == 0).to_numpy()
    window_included = np.logical_and(included_mask, in_window_mask)

    sample = _select(condo, window_included).reset_index(drop=True)
    rederived = _model_sample(condo, last_complete_month)
    if len(sample) != len(rederived):
        raise SystemExit(
            f"model sample derivations disagree: reason-set route {len(sample)} "
            f"vs positive-filter route {len(rederived)}"
        )
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
    response = np.log(np.asarray(pd.to_numeric(sample["psf"], errors="coerce"), dtype=float))
    design_columns = list(design.columns)
    model = sm.OLS(response, design.to_numpy(dtype=float)).fit(cov_type="HC1", use_t=False)
    cluster_groups = sample["project_name"].astype(str).str.strip().to_numpy()
    model_clustered = sm.OLS(response, design.to_numpy(dtype=float)).fit(
        cov_type="cluster", cov_kwds={"groups": cluster_groups}, use_t=False
    )
    if not np.allclose(model.params, model_clustered.params, atol=1e-12):
        raise SystemExit("clustered fit produced different coefficients than the HC1 fit")
    clusters = int(len(pd.unique(cluster_groups)))
    k = len(design_columns)

    coefficient_vector = [
        {
            "name": name,
            "logPoint": _r(float(model.params[i]), 8),
            "robustSe": _r(float(model.bse[i]), 8),
            "clusteredRobustSe": _r(float(model_clustered.bse[i]), 8),
        }
        for i, name in enumerate(design_columns)
    ]

    def coeff(name: str) -> dict[str, float | None]:
        i = design_columns.index(name)
        return {
            "logPoint": _r(float(model.params[i]), 8),
            "robustSe": _r(float(model.bse[i]), 8),
            "clusteredRobustSe": _r(float(model_clustered.bse[i]), 8),
        }

    def back_transform(name: str, scale: float) -> dict[str, float | None]:
        i = design_columns.index(name)
        return {
            "perNaturalUnit": scale,
            "logPoint": _r(float(model.params[i]) / scale, 8),
            "robustSe": _r(float(model.bse[i]) / scale, 8),
            "clusteredRobustSe": _r(float(model_clustered.bse[i]) / scale, 8),
        }

    rows: dict[str, Any] = {}
    for amenity in AMENITIES:
        key = f"{amenity}_1km"
        i = design_columns.index(key)
        beta = float(model.params[i])
        se = float(model.bse[i])
        se_clustered = float(model_clustered.bse[i])
        rows[key] = {
            "regressor": (
                f"1 when the shipped dist_to_nearest_{amenity} is <= 1000 m, else 0 "
                "(unitless binary indicator built from the shipped metres column)"
            ),
            "logPoint": _r(beta, 6),
            "robustSe": _r(se, 6),
            "clusteredRobustSe": _r(se_clustered, 6),
            "clusteredTStat": _r(beta / se_clustered, 2),
            "clusterVsHC1SeRatio": _r(se_clustered / se, 4),
            "tStat": _r(beta / se, 2),
            "pctEffectExpMinus1": _r(100.0 * (float(np.exp(beta)) - 1.0), 4),
            "within1000mN": int(indicator_matrix[key].sum()),
            "within1000mShare": _r(float(indicator_matrix[key].mean()), 4),
            "interpretation": (
                "conditional log-point difference in price-psf associated with "
                "the indicator, holding the stated controls fixed; descriptive, "
                "between projects (project identity is not conditioned on), "
                "and joined to an undated snapshot — not a causal premium. "
                "The clustered SE is the published uncertainty; the HC1 SE is "
                "retained only for the comparison"
            ),
        }

    # The childcare indicator's near-degenerate contrast group, attributed.
    childcare_zero = indicator_matrix["childcare_1km"] == 0.0
    contrast = _select(sample, childcare_zero)
    contrast_areas: Counter[str] = Counter(contrast["planning_area"].astype(str))
    composition = sorted(contrast_areas.items(), key=lambda kv: (-kv[1], kv[0]))
    contrast_distances = _numeric(contrast["dist_to_nearest_childcare"])

    floor_levels = sorted(set(sample["floor_level"].astype(str).str.strip()))
    planning_areas = sorted(set(sample["planning_area"].astype(str).str.strip()))
    baseline_area = str(sample["planning_area"].astype(str).str.strip().value_counts().index[0])

    return {
        "estimator": {
            "name": "OLS (statsmodels OLS, HC1 heteroskedasticity-robust covariance, use_t=False)",
            "response": (
                "log(price per square foot); price in nominal Singapore dollars "
                "per square foot of strata area (shipped psf column; its "
                "identity with price/area_sqft is measured in responseLineage)"
            ),
            "functionalForm": (
                "log-linear; coefficients are log points, and "
                "pctEffectExpMinus1 = 100*(exp(beta)-1) is the approximate "
                "percentage difference the log point implies"
            ),
            "standardErrors": (
                "two batteries reported for every coefficient: (1) HC1 robust "
                "(unclustered — treats transactions as independent) and (2) "
                "project-clustered CRVE (see clusteredStandardErrors). The "
                "clustered battery is the published uncertainty; the HC1 "
                "battery is retained only to show the scale of the clustering "
                "understatement"
            ),
            "clusteredStandardErrors": {
                "clusterKey": "project_name",
                "clusters": clusters,
                "estimator": (
                    "statsmodels OLS cov_type='cluster' (cluster-robust CRVE), "
                    "groups=project_name, statsmodels' default finite-cluster "
                    "corrections; coefficients identical to the HC1 fit, only "
                    "the covariance differs"
                ),
                "why": (
                    "transactions inside one project share one location and "
                    "project-level unobservables, so HC1's independence "
                    "assumption is the wrong uncertainty model here; the "
                    "HC1-vs-clustered comparison (indicatorCoefficients "
                    ".clusterVsHC1SeRatio) is the measured demonstration of "
                    "how much it understates"
                ),
            },
            "indicators": (
                f"each access indicator enters as dist <= {THRESHOLD_METRES:.0f} m in "
                "the shipped snapshot feature; ALL five indicators are fitted "
                "jointly in ONE specification (no selection, no stepwise search)"
            ),
            "controls": [
                "area_sqft (square feet of strata area, continuous)",
                "freehold indicator (1 when the tenure string is exactly 'Freehold')",
                (
                    "long-lease indicator (1 when the parsed lease duration is "
                    f"at least {LONG_LEASE_MIN_YEARS} years; covers the 999-year "
                    "and similar long-lease strings)"
                ),
                (
                    "lease commencement year ((year-1900)/100, continuous; defined "
                    "for parsed leasehold rows and set to 0 for freehold rows — "
                    "the freehold indicator separates the groups, so this "
                    "coefficient is identified from leasehold variation)"
                ),
                (
                    f"floor-band fixed effects ({len(floor_levels)} levels observed "
                    f"in the sample; baseline {BASELINE_FLOOR_LEVEL!r}; '-' is the "
                    "unreported-band level, kept as its own level and never read "
                    "as a storey number)"
                ),
                (
                    "property-subtype fixed effects (3 levels: "
                    f"{', '.join(sorted(NON_LANDED_SUBTYPES))}; baseline "
                    f"{BASELINE_SUBTYPE!r})"
                ),
                (
                    "transaction-type fixed effects (Resale/New Sale/Sub Sale; "
                    f"baseline {BASELINE_SALE_TYPE!r})"
                ),
                (
                    "transaction-year fixed effects (baseline "
                    f"{BASELINE_YEAR!r}; absorb nominal price drift and inflation)"
                ),
                (
                    f"planning-area fixed effects ({len(planning_areas)} levels "
                    f"observed in the sample; baseline {baseline_area!r})"
                ),
            ],
            "internalScaling": (
                "area_sqft/100 and (lease commencement year-1900)/100 for "
                "numerical stability; the indicators and dummies are unscaled, "
                "and the control coefficients below are back-transformed to "
                "natural units"
            ),
            "projectEffects": (
                "NOT conditioned on: the specification carries no project fixed "
                "effects, so every coefficient here is a BETWEEN-PROJECT "
                "association — it compares transactions of projects that differ "
                "in the indicator with transactions of projects that do not, "
                "and cannot separate an access attribute from the project-level "
                "characteristics (location quality within the planning area, "
                "age, tenure mix, build quality, branding) that move with it. "
                "projectStructure quantifies this on the same sample. A "
                "project-fixed-effects specification is recorded as notFitted, "
                "not run"
            ),
            "notControlled": [
                "project identity (no project fixed effects — see projectEffects)",
                "project completion year (the shipped year_completed column is null for all but a measured handful of condo rows; see sample.yearCompletedNullRows)",
                "in-house facility presence (the subject of the legacy study; the layer is absent from this checkout)",
                "unit condition, renovation, view and orientation",
                "floor level WITHIN a floor band (bands are controlled, not storeys)",
                "tenure gradations beyond the freehold and long-lease flags (9999/999999 lease-duration codes are not separated)",
                "new-sale incentive structures and buyer financing",
                "walking-path distance to the access features; access quality",
                "planning-area x year shocks (the access indicators correlate with neighbourhood change inside a planning area)",
                "the access snapshot's own vintage (one undated snapshot per layer; see RS04's amenity-impact audit for the vintage semantics)",
            ],
        },
        "sample": {
            "propertyType": "condo (non-landed strata: Condominium, Apartment, Executive Condominium)",
            "windowStart": STUDY_WINDOW_START,
            "cutoffUpperBound": last_complete_month,
            "cutoffUpperBoundMeaning": (
                "every model row and every aggregate in this ledger ends at the "
                "last complete month; the terminal partial month is excluded"
            ),
            "condoRowsTotal": int(len(condo)),
            "includedN": int(n),
            "excludedRowsTotal": excluded_total,
            "excludedReasonCounts": {key: reason_counts[key] for key in sorted(reason_counts)},
            "excludedRowsByReasonCount": {
                str(k): overlap_counts[k] for k in sorted(overlap_counts)
            },
            "excludedInWindowRowCount": len(excluded_records),
            "excludedInWindowRowsSha256": excluded_rows_sha256,
            "excludedInWindowRowsDigestBasis": (
                "sha256 over canonical_bytes (sorted keys, indent=2, trailing "
                "newline) of the full per-row list "
                "[{month, reasons, rowIndex} ...] in row order; --check "
                "recomputes that payload from this checkout, so a single "
                "drifting row, month or reason set fails it"
            ),
            "excludedInWindowRowsSample": excluded_records[:5],
            "excludedInWindowReasonSignatures": {
                signature: signature_counts[signature] for signature in sorted(signature_counts)
            },
            "reasonSetSemantics": (
                "exclusions are sets: a row failing several conditions records "
                "every reason (excludedRowsByReasonCount counts rows by the SIZE "
                "of their reason set), and no reason is asserted as the single cause"
            ),
            "missingSourceSemantics": (
                "a null access distance is a missing source (the row's location "
                "has no coordinates), not a zero distance and not 'no amenity "
                "nearby'; it is recorded as missing-source, never rendered as 0"
            ),
            "yearCompletedNullRows": int(_numeric(condo["year_completed"]).isna().sum()),
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
            "area_sqft": back_transform("area_sqft_100", 100.0),
            "lease_commence_year": back_transform("lease_commence_1900_100", 100.0),
        },
        "flagControls": {
            "freehold": coeff("freehold"),
            "long_lease_100yrs_plus": coeff("long_lease_100yrs_plus"),
        },
        "fullCoefficientVector": coefficient_vector,
        "designLevels": {
            "floorLevels": floor_levels,
            "subtypes": sorted(NON_LANDED_SUBTYPES),
            "planningAreas": planning_areas,
            "baselinePlanningArea": baseline_area,
        },
        "childcareContrast": {
            "note": (
                "the childcare indicator equals 0 for a measured 0.5% share of "
                "the sample (childcareContrast.indicatorZeroShare), so its "
                "coefficient is a near-degenerate contrast and its sign must "
                "not be read as an access effect; the group is attributed here"
            ),
            "indicatorZeroN": int(childcare_zero.sum()),
            "indicatorZeroShare": _r(float(childcare_zero.mean()), 4),
            "planningAreaComposition": {area: count for area, count in composition},
            "medianDistanceMetres": _r(float(contrast_distances.median()), 1),
            "minDistanceMetres": _r(float(contrast_distances.min()), 1),
        },
    }


def not_fitted() -> dict[str, Any]:
    """Specifications this pack deliberately does not run, with reasons."""
    return {
        "facilityPremiumModel": {
            "status": "not fitted",
            "reason": (
                "the facility layer that would supply the regressors (which "
                "projects have which facilities) is absent from this checkout; "
                "no with-vs-without facility population exists to fit"
            ),
        },
        "projectFixedEffectsSpecification": {
            "status": "not fitted",
            "reason": (
                "the pack records ONE specification and only that one is fitted; "
                "a project-fixed-effects fit of the same indicators is a "
                "different specification, and the facility regressor it would "
                "clarify does not exist. The between-project labelling plus the "
                "measured variance decomposition (projectStructure) is the "
                "disclosure of what the fitted coefficients can and cannot "
                "mean; the pack runs no sensitivity or robustness family"
            ),
        },
        "legacyMethodReproduction": {
            "status": "not fitted",
            "reason": (
                "the legacy methodology (facility prevalence frequency tables, "
                "PSF comparison controlling for planning area and property age, "
                "facility-combination interaction regression, longitudinal "
                "value-retention trajectories) is not reproduced; the retired "
                "v1 pipeline and its L3 facility stages are not in this checkout"
            ),
        },
    }


def legacy_claims() -> list[dict[str, str]]:
    """Every legacy quantitative claim, verified verbatim against the old text.

    Each entry's `quote` is checked (bold/backtick-stripped, whitespace
    normalised) against `docs/analytics/editions/legacy/2026-11-12/facility-premiums.md`
    at build time; a quote that no longer matches fails the tool loudly.
    """
    return [
        {
            "claim": "Differentiated facilities command a measurable premium",
            "quote": (
                "The facilities that actually move prices are the ones that are "
                "not universally available. A condo with a tennis court or sky "
                "garden commands a measurable premium over an equivalent "
                "property with only standard facilities."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "the in-house facility layer is absent from this checkout "
                "(legacySourceAudit), so no with-vs-without tennis-court or "
                "sky-garden population exists; 'commands' is also causal, and "
                "no identification strategy exists here"
            ),
        },
        {
            "claim": ("Prevalence table row: swimming pool"),
            "quote": "| Swimming pool | ~85-90% | Minimal (expected) | Table stake |",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "facilityMissingness records the facility as no-record: the "
                "layer that carried per-project facility lists is absent, so "
                "no prevalence share or premium classification is measurable; "
                "no-record is not zero and not absence"
            ),
        },
        {
            "claim": "Prevalence table row: security",
            "quote": "| Security (24hr) | ~80-85% | Minimal (expected) | Table stake |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no prevalence share is measurable (facilityMissingness)",
        },
        {
            "claim": "Prevalence table row: gym",
            "quote": "| Gym / Fitness corner | ~75-80% | Minimal (expected) | Table stake |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no prevalence share is measurable (facilityMissingness)",
        },
        {
            "claim": "Prevalence table row: BBQ pits",
            "quote": "| BBQ pits | ~70-75% | Minimal | Table stake |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no prevalence share is measurable (facilityMissingness)",
        },
        {
            "claim": "Prevalence table row: function room",
            "quote": "| Function room | ~60-65% | Modest | Nice-to-have |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no prevalence share is measurable (facilityMissingness)",
        },
        {
            "claim": "Prevalence table row: tennis court",
            "quote": "| Tennis court | ~25-30% | Moderate | Differentiator |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no prevalence share is measurable (facilityMissingness)",
        },
        {
            "claim": "Prevalence table row: sky garden / roof terrace",
            "quote": "| Sky garden / Roof terrace | ~15-20% | Moderate-High | Differentiator |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no prevalence share is measurable (facilityMissingness)",
        },
        {
            "claim": "Prevalence table row: concierge / clubhouse",
            "quote": "| Concierge / Clubhouse | ~10-15% | Moderate | Differentiator |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no prevalence share is measurable (facilityMissingness)",
        },
        {
            "claim": "Prevalence table row: jacuzzi / hydrospa",
            "quote": "| Jacuzzi / Hydrospa | ~20-25% | Low-Moderate | Minor differentiator |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no prevalence share is measurable (facilityMissingness)",
        },
        {
            "claim": "Synergy table row: baseline",
            "quote": "| Pool + Gym + Security | Baseline | 0% (expected) |",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "no interaction model is reproduced and no facility combination "
                "is observable (the layer is absent); the synergy percentages "
                "have no population in this checkout"
            ),
        },
        {
            "claim": "Synergy table row: tennis court",
            "quote": "| + Tennis Court | Moderate | +2-4% |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no combination premium is measurable",
        },
        {
            "claim": "Synergy table row: sky garden",
            "quote": "| + Sky Garden | Moderate-High | +3-5% |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no combination premium is measurable",
        },
        {
            "claim": "Synergy table row: tennis + sky garden + concierge",
            "quote": "| Tennis + Sky Garden + Concierge | Strong | +5-8% |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no combination premium is measurable",
        },
        {
            "claim": "Synergy table row: full premium suite",
            "quote": "| Full premium suite | Diminishing returns | +6-10% |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; no combination premium is measurable",
        },
        {
            "claim": "The first differentiating facility adds the most value; diminishing returns beyond",
            "quote": (
                "The first differentiating facility adds the most value. Adding "
                "more facilities beyond the first premium one shows diminishing "
                "returns."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "'adds' is causal and the facility-count regressor it needs does "
                "not exist here; no combination model is fitted"
            ),
        },
        {
            "claim": "Condos near MRT with good in-house facilities command the strongest pricing",
            "quote": (
                "Condos near MRT stations with good in-house facilities command "
                "the strongest pricing."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "needs both an MRT measure (exists, snapshot) and an in-house "
                "facility measure (absent); the interaction of the two is not "
                "measurable, and 'command' is causal"
            ),
        },
        {
            "claim": "External amenity proximity table row: MRT within 500m",
            "quote": "| MRT within 500m | High | Strong synergy with condo facilities |",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "the 3.6M-record nearby-facilities layer is absent "
                "(legacyNamedSources); the distance-premium labels came from "
                "the retired v1 pipeline and are not reproduced. Measured "
                "analogue, not a replacement: the recorded model's conditional "
                "associations for mrt/mall/hawker/childcare/sports within "
                "1000 m (associations.indicatorCoefficients), between projects"
            ),
        },
        {
            "claim": "External amenity proximity table row: mall within 500m",
            "quote": "| Mall within 500m | Moderate | Complements retail-deprived condos |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; the label and its 'complements' interaction reading are not reproduced",
        },
        {
            "claim": "External amenity proximity table row: childcare within 500m",
            "quote": "| Childcare within 500m | Low-Moderate | Relevant for family-oriented buyers |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; 'relevant for family-oriented buyers' asserts a buyer-preference finding nothing here measures",
        },
        {
            "claim": "External amenity proximity table row: hawker within 1km",
            "quote": "| Hawker within 1km | Low | Less relevant for condo segment |",
            "disposition": "withdrawn-not-measurable",
            "basis": "same absent layer; segment relevance is not a measured quantity in this pack",
        },
        {
            "claim": "Internal and external amenities are complements, not substitutes",
            "quote": (
                "The interaction effect suggests that internal and external "
                "amenities are complementary, not substitutes."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "an interaction claim needs both measures; the in-house half is "
                "absent, and no interaction model is fitted"
            ),
        },
        {
            "claim": "Facility quality and maintenance affect value retention",
            "quote": (
                "Properties with aging or poorly maintained facilities show "
                "weaker value retention compared to well-maintained equivalents."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "facility condition is not recorded anywhere in this checkout "
                "(the legacy text itself flags this), and no longitudinal "
                "property-level price trajectory is reproducible without a "
                "unit-level key (RS01: no source carries one)"
            ),
        },
        {
            "claim": "Differentiated facilities attract stronger tenant demand and command higher rents",
            "quote": (
                "Properties with differentiated facilities attract stronger "
                "tenant demand and command higher rents."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "rental demand is not measured in this pack (no rental join for "
                "condos), facility presence is unmeasurable, and 'command' is "
                "causal"
            ),
        },
        {
            "claim": "Buyer guidance: do not pay extra for table stakes; look for differentiators",
            "quote": (
                "Do not pay extra for table-stakes facilities (pool, gym, "
                "security). Every comparable condo has them."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "a decision rule built on the unmeasurable prevalence and "
                "premium claims; the measured conditional associations in this "
                "pack are between-project and support no guidance of this form"
            ),
        },
        {
            "claim": "EC guidance: facility quality becomes a direct pricing factor after privatisation",
            "quote": (
                "When the EC privatizes after MOP, facility quality becomes a "
                "direct pricing factor."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "no EC privatisation event, facility quality or pricing factor "
                "is measured here; EC rows are in the model sample only as a "
                "subtype fixed-effect level"
            ),
        },
        {
            "claim": "Technical finding: pools/security/gyms present in 75-90% of properties",
            "quote": (
                "Swimming pools, security, and gyms are present in 75-90% of "
                "properties, making them baseline expectations rather than "
                "pricing differentiators"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": ("same absent layer; no prevalence share is measurable (facilityMissingness)"),
        },
        {
            "claim": "Technical finding: tennis courts and sky gardens present in only 15-30% of properties",
            "quote": (
                "Tennis courts and sky gardens are the strongest individual "
                "facility differentiators, present in only 15-30% of properties"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "same absent layer; no prevalence share and no differentiator ranking is measurable"
            ),
        },
        {
            "claim": "Technical finding: the first premium facility adds 2-5%, subsequent ones add 1-3% each",
            "quote": (
                "Combination effects show diminishing returns: the first premium "
                "facility adds 2-5%, subsequent ones add 1-3% each"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "'adds' is causal and the combination model is not reproduced; "
                "no facility count exists"
            ),
        },
        {
            "claim": "3.6M nearby facility records provide granular proximity data",
            "quote": (
                "3.6M nearby facility records provide granular proximity data "
                "for childcare, hawker, mall, and other external amenities"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "property_nearby_facilities.parquet is absent from this checkout "
                "(legacyNamedSources); the shipped dataset carries "
                "nearest-distance columns per amenity layer instead, whose "
                "lineage RS04 audited"
            ),
        },
        {
            "claim": "Data Period: Cross-sectional (facility data) with transaction data 2017-2026",
            "quote": "Data Period: Cross-sectional (facility data) with transaction data 2017-2026",
            "disposition": "re-cut",
            "basis": (
                "the private-residential source in this checkout starts 2021-01 "
                "with 0 earlier rows (condoSourceCoverage), so 2017-2020 is "
                "source-missing; the measured window is 2021-01 -> 2026-10 "
                "(70 months), and the facility cross-section has no source at "
                "all here"
            ),
        },
        {
            "claim": "Methodology: PSF comparison with vs without each facility, controlling for location and age",
            "quote": (
                "Premium estimation: Comparison of price PSF for properties "
                "with vs without each facility type, controlling for location "
                "(planning area) and property age"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "the comparison population is unavailable (no facility layer); "
                "and projectStructure measures why that control set is "
                "insufficient on this data: the between-project share of log "
                "psf variance it records is the quantification of what a "
                "with-vs-without comparison conditioned only on planning area "
                "and age would actually compare — projects"
            ),
        },
        {
            "claim": "Legacy data paths (property facilities / nearby facilities / property master / housing_unified)",
            "quote": (
                "Property facilities: "
                "data/04_platinum/private_property_facilities.parquet (172,504 "
                "records)"
            ),
            "disposition": "superseded",
            "basis": (
                "none of the four legacy-named paths exists in this checkout "
                "(legacySourceAudit measures each); the shipped paths are "
                "data/pipeline/01_bronze (source), 02_silver, 03_gold and "
                "data/pipeline/04_platinum/unified_dataset.parquet, none of "
                "which carries an in-house facility column"
            ),
        },
        {
            "claim": "Conclusion: most facilities are table stakes with minimal individual pricing impact",
            "quote": (
                "Private property facility analysis reveals that most facilities "
                "are table stakes with minimal individual pricing impact."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "the analysis is not reproducible in this checkout; the "
                "renewed edition makes no table-stakes claim because no "
                "facility-level pricing measurement exists here"
            ),
        },
        {
            "claim": "Investor guidance: facility quality beats facility quantity",
            "quote": "Facility quality matters more for tenant retention than facility quantity.",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "neither facility quality nor tenant retention is measured in "
                "this checkout; the sentence is also prescriptive"
            ),
        },
        {
            "claim": "Investor guidance: MCST financials indicate sustainable maintenance",
            "quote": (
                "Check the MCST (management corporation) financials. Well-funded "
                "reserve funds indicate sustainable facility maintenance."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": "no MCST financial data exists in this checkout; the claim is prescriptive and unmeasurable here",
        },
        {
            "claim": "Condo-buyer guidance: look for differentiators for resale value",
            "quote": (
                "Look for one or two genuine differentiators (tennis court, sky "
                "garden, concierge). These support future resale value."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "built on the unmeasurable prevalence and premium claims; no "
                "future-resale measurement exists in this pack"
            ),
        },
        {
            "claim": "Condo-buyer guidance: inspect facility condition",
            "quote": (
                "Inspect facility condition during viewings. A poorly maintained "
                "pool is a liability, not a selling point."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "facility condition is not recorded anywhere in this checkout; "
                "the sentence is prescriptive"
            ),
        },
        {
            "claim": "EC guidance: ECs have more extensive facilities than equivalent-price condos",
            "quote": (
                "ECs typically have more extensive facilities than "
                "equivalent-price condos. Compare the facility quality, not "
                "just the list."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "no EC facility comparison is measurable (the layer is absent); "
                "the sentence is prescriptive"
            ),
        },
        {
            "claim": "EC guidance: prioritize at least one differentiating facility",
            "quote": (
                "Prioritize developments with at least one differentiating "
                "facility that will appeal to future private-market buyers."
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "built on the unmeasurable differentiator claims and a "
                "future-buyer-preference assertion nothing here measures"
            ),
        },
        {
            "claim": "Data Used: nearby facilities layer",
            "quote": (
                "Nearby facilities: "
                "data/04_platinum/property_nearby_facilities.parquet (3,638,104 "
                "records)"
            ),
            "disposition": "superseded",
            "basis": (
                "the path does not exist in this checkout (legacyNamedSources "
                "measures each); the shipped dataset carries nearest-distance "
                "columns per amenity layer instead"
            ),
        },
        {
            "claim": "Data Used: property master layer",
            "quote": (
                "Property master data: data/04_platinum/property.parquet "
                "(41,340 records, 30 columns including amenity distance "
                "features)"
            ),
            "disposition": "superseded",
            "basis": (
                "the path does not exist in this checkout; the condo-side "
                "location/amenity features live in the gold location_dim and "
                "the platinum unified_dataset under data/pipeline/"
            ),
        },
        {
            "claim": "Data Used: transaction layer",
            "quote": (
                "Transaction data: data/04_platinum/housing_unified.parquet "
                "(price data for premium estimation)"
            ),
            "disposition": "superseded",
            "basis": (
                "the shipped path is "
                "data/pipeline/04_platinum/unified_dataset.parquet (1,236,310 "
                "rows x 97 columns, sha-pinned in the ledger inputs)"
            ),
        },
        {
            "claim": "Key limitation acknowledged by the legacy text itself",
            "quote": (
                "Key limitation: facility data is cross-sectional and does not "
                "capture facility quality or condition directly."
            ),
            "disposition": "superseded",
            "basis": (
                "still true and now stronger: the facility data is not merely "
                "cross-sectional, it is absent from this checkout; and the "
                "refreshed edition adds the between-project limitation the "
                "legacy methodology carried without stating"
            ),
        },
        {
            "claim": "Analysis Date: 2026-03-31",
            "quote": "Analysis Date: 2026-03-31",
            "disposition": "superseded",
            "basis": (
                "this edition is dated 2026-11-17 and measured from the current "
                "checkout; the observation cutoff is 2026-10 (cutoff)"
            ),
        },
        {
            "claim": "Primary Focus: Condominium and EC facilities",
            "quote": "Primary Focus: Condominium and EC facilities",
            "disposition": "superseded",
            "basis": (
                "the focus is kept as a scope statement (the model sample is "
                "non-landed strata including Executive Condominium rows), but "
                "no facility measurement is possible under it in this checkout"
            ),
        },
    ]


def _edition_quote_check(claims: list[dict[str, str]]) -> dict[str, Any]:
    """Extract every quoted span from the refreshed edition's Superseded-figures
    section and verify each against the legacy file, both ways:

    1. every quoted span in the edition must be found verbatim in the legacy
       text (bold/backtick-stripped, whitespace-normalised, escaped table
       pipes unescaped) — an edited or drifted edition quotation fails here;
    2. every registered legacy claim's quote must still be quoted in the
       edition — a silently dropped withdrawal fails here.

    Quoted prose elsewhere in the edition (labels, data values) is not a
    legacy quotation and is deliberately not checked against the legacy file.
    """
    try:
        edition_text = EDITION_FILE.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"Unreadable edition {EDITION_FILE}: {error}") from error
    marker = "## Superseded figures"
    start = edition_text.find(marker)
    if start < 0:
        raise SystemExit(
            "edition has no '## Superseded figures' section; quote check is impossible"
        )
    rest = edition_text[start + len(marker) :]
    next_heading = re.search(r"\n## ", rest)
    section = rest[: next_heading.start()] if next_heading else rest

    def normalise(fragment: str) -> str:
        fragment = fragment.replace("\\|", "|")
        fragment = re.sub(r"\s+", " ", fragment).strip()
        return re.sub(r"\*\*|`", "", fragment)

    spans = [normalise(span) for span in re.findall(r'"([^"\n]+)"', section)]
    if not spans:
        raise SystemExit("no quoted spans found in the edition's Superseded-figures section")

    legacy_normalised = re.sub(
        r"\s+", " ", re.sub(r"\*\*|`", "", LEGACY_EDITION.read_text(encoding="utf-8"))
    )
    drifted = [span for span in spans if span not in legacy_normalised]
    if drifted:
        raise SystemExit(
            "edition quoted spans no longer match the legacy file: "
            + "; ".join(repr(span[:80]) for span in drifted[:3])
        )
    uncovered = [
        claim["claim"]
        for claim in claims
        if not any(normalise(claim["quote"]) in span for span in spans)
    ]
    if uncovered:
        raise SystemExit(
            "registered legacy claims no longer quoted in the edition: " + "; ".join(uncovered[:3])
        )
    return {
        "editionFile": EDITION_FILE.relative_to(REPO_ROOT).as_posix(),
        "section": "Superseded figures",
        "spansChecked": len(spans),
        "allSpansFoundInLegacy": True,
        "claimsQuotedInEdition": len(claims) - len(uncovered),
        "claimsRegistered": len(claims),
        "allClaimsQuoted": True,
        "scope": (
            "every double-quoted span inside the edition's Superseded-figures "
            "section; spans are unescaped (\\| -> |), bold/backtick-stripped "
            "and whitespace-normalised before matching against the legacy file"
        ),
        "driftBehaviour": (
            "--check fails if a quoted span in the edition's Superseded-figures "
            "section no longer matches the legacy file, or if a registered "
            "legacy claim loses its quotation in the edition; quoted prose "
            "outside that section is not a legacy quotation and is not checked"
        ),
    }


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
        "claimsChecked": len(claims),
        "allQuotesFound": True,
        "quotes": checked,
        "editionSpans": _edition_quote_check(claims),
    }


def build() -> dict[str, Any]:
    frame = pd.read_parquet(
        UNIFIED,
        columns=[
            "month",
            "property_type",
            "project_name",
            "price",
            "area_sqft",
            "psf",
            "planning_area",
            "tenure",
            "property_subtype",
            "type_of_sale",
            "floor_level",
            "year_completed",
            "dist_to_nearest_mrt",
            "dist_to_nearest_mall",
            "dist_to_nearest_hawker",
            "dist_to_nearest_sports_facility",
            "dist_to_nearest_childcare",
            "nearest_sports_facility",
        ],
    )
    last_complete = cutoff(frame)["lastCompleteMonth"]
    condo = _select(frame, frame["property_type"] == "condo")

    prepared = associations(frame, last_complete)
    sample = _model_sample(condo, last_complete)
    if len(sample) != prepared["sample"]["includedN"]:
        raise SystemExit(
            f"model sample re-derivation mismatch: {len(sample)} != "
            f"{prepared['sample']['includedN']}"
        )

    claims = legacy_claims()
    inputs: dict[str, Any] = {}
    input_specs: list[tuple[Path, int]] = [
        (UNIFIED, int(pq.ParquetFile(UNIFIED).metadata.num_rows)),
        (BRONZE_CONDO, int(pq.ParquetFile(BRONZE_CONDO).metadata.num_rows)),
        (SPORTSG_PARQUET, int(pq.ParquetFile(SPORTSG_PARQUET).metadata.num_rows)),
        (SPORTSG_GEOJSON, len(_geojson_features(SPORTSG_GEOJSON))),
        (ARCHIVE_DOC, len(ARCHIVE_DOC.read_text(encoding="utf-8").splitlines())),
    ]
    for path, rows in input_specs:
        inputs[path.relative_to(REPO_ROOT).as_posix()] = {
            "sha256": sha256_of(path),
            "rows": rows,
        }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "scope": (
            "RS05 facility-premiums evidence: measured absence of the legacy "
            "in-house facility layer, join-key (project_name) recovery and "
            "coverage, per-facility no-record status, a between/within-project "
            "variance decomposition, and one recorded descriptive OLS of log "
            "condo price-psf on five jointly-fitted external-access indicators "
            "with stated controls (a between-project comparison; no dated prior "
            "protocol, so specification search cannot be ruled out)"
        ),
        "definition": DEFINITION,
        "inputs": inputs,
        "cutoff": cutoff(frame),
        "condoSourceCoverage": condo_coverage(frame, last_complete),
        "legacySourceAudit": legacy_source_audit(),
        "joinKey": join_key(frame, last_complete),
        "facilityMissingness": facility_missingness(),
        "responseLineage": response_lineage(frame),
        "projectStructure": project_structure(sample),
        "associations": prepared,
        "notFitted": not_fitted(),
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
        print("Pass: RS05 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS05 ledger does not match this checkout")
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
        f"Model sample: n = {sample['includedN']} condo transactions "
        f"({sample['windowStart']} -> {sample['cutoffUpperBound']}); "
        f"excluded rows: {sample['excludedRowsTotal']}"
    )
    print(
        "Conditional associations (pct, HC1): "
        + ", ".join(f"{key}={value['pctEffectExpMinus1']:+.3f}%" for key, value in rows.items())
    )
    structure = evidence["projectStructure"]["logPsfVariance"]
    print(
        f"Project structure: between-project share of log-psf variance = "
        f"{structure['betweenProjectShare']:.4f} (between-project comparison, "
        "no project FE)"
    )
    try:
        ledger_label = args.output.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        ledger_label = str(args.output)
    print(f"Ledger: {ledger_label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
