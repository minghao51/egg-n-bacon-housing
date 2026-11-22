#!/usr/bin/env python3
"""Measure RS07's mrt-impact evidence: units, a standardized-effect comparison,
the calculator asset, and what of the legacy method exists in this checkout.

RS07's gate is "Confirm metres/km and total-price/log/PSF response. Compare
standardized effects or state non-comparability; no raw coefficient "15x" or
"4x" marketing. Separate predictive association from causation. Do not
automatically unlock the MRT calculator." This tool measures from the local
checkout, and only what the checkout can support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04/RS05/RS09/
   RS10 shipped (terminal month's transaction count as a fraction of the
   trailing twelve-month median). Every aggregation below stops there.
2. **Response units** — the shipped distance feature is metres (producer
   cited), the calculator asset's rates are stored per 100 m / per km labels,
   and the refit response is log(total price in SGD) with log(PSF) as a
   secondary recorded response. Nothing is converted into the legacy's
   unstated-unit dollars.
3. **Standardized effects** — one recorded OLS per property segment on the
   common 2021-01 -> cutoff window, each segment with the controls its rows
   actually carry (HDB rows carry lease/storey/town; condo rows carry all-null
   lease, storey and town, so its specification is strictly poorer). The two
   specifications are NOT the same model; the standardized betas and their
   ratio are recorded as descriptive fields and the non-comparability is
   stated alongside them. No raw-coefficient multiple is reported.
4. **Calculator asset** — full read of `mrt_cbd_impact.json.gz`: coefficient
   blocks, the asset's own internal arithmetic (town premium rows equal the
   per-type base times the town multiplier, exactly), and the recorded fact
   that no producer of this asset exists on the scanned surface — it is an
   unlinked artefact and adjudicates nothing in either direction. The app
   consumer is recorded in its inspection-only state; this pack does not
   unlock it.
5. **Absence scans** — per-station opening dates / operating status (frame
   schema plus every MRT-named file), the legacy XGBoost/SHAP importance
   table, the legacy OLS/hierarchical outputs, the H3 grid artefact, and the
   CBD definition asset. Each scan states its roots, its exclusions, lists
   every matched file with a count, and claims no more than the scan does.
6. **Legacy claims** — every quantitative claim of the frozen text, verified
   verbatim, dispositioned re-measured / withdrawn / not-reproducible, with
   each claim's ledgerKey resolved against this ledger at build time (an
   unresolved key fails the build).

It never runs the pipeline, never refits the retired models, never unlocks
the calculator, never writes outside `--output`, and never touches
`data/pipeline/**` (reads only) or `app/public/data/**` (reads only).

Usage:

    uv run python scripts/tools/mrt_impact_evidence.py \\
        --output docs/implementation/artifacts/rs07-mrt-impact-evidence.json

    uv run python scripts/tools/mrt_impact_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import statsmodels.formula.api as smf

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
BRONZE = REPO_ROOT / "data" / "pipeline" / "01_bronze"
RAW_MRT = BRONZE / "raw_mrt_stations.parquet"
BRONZE_MANIFEST = BRONZE / "bronze_manifest.json"
SEED_STATIONS_JSON = BRONZE / "external" / "mrt_stations.json"
SEED_MRT_GEOJSON_BRONZE = BRONZE / "external" / "MRTStations.geojson"
RAW_MRT_GEOJSON = REPO_ROOT / "data" / "raw" / "external" / "datagov" / "MRTStations.geojson"
RAW_EXITS_GEOJSON = REPO_ROOT / "data" / "raw" / "external" / "datagov" / "MRTStationExits.geojson"
MANUAL_LINES_MAPPING = REPO_ROOT / "data" / "manual" / "mrt_lines_mapping.csv"
MANUAL_STATIONS_LIST = REPO_ROOT / "data" / "manual" / "mrt_stations_list.txt"
CALCULATOR_ASSET = (
    REPO_ROOT / "app" / "public" / "data" / "interactive_tools" / "mrt_cbd_impact.json.gz"
)
LEGACY_EDITION = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "mrt-impact.md"
)
REGISTER = REPO_ROOT / "docs" / "plans" / "2026-11-12-reporting-refresh-research-register.md"
MRT_INSPECTION_TSX = REPO_ROOT / "app" / "src" / "components" / "tools" / "MrtCbdInspection.tsx"
TOOL_EVIDENCE_TS = REPO_ROOT / "app" / "src" / "components" / "tools" / "lib" / "tool-evidence.ts"
PROXIMITY_MODULE = REPO_ROOT / "src" / "egg_n_bacon_housing" / "utils" / "proximity.py"
GEO_MODULE = REPO_ROOT / "src" / "egg_n_bacon_housing" / "utils" / "geo.py"
LINE_MAPPING_MODULE = REPO_ROOT / "src" / "egg_n_bacon_housing" / "utils" / "mrt_line_mapping.py"
GEOJSON_MODULE = (
    REPO_ROOT / "src" / "egg_n_bacon_housing" / "components" / "ingestion" / "geojson.py"
)
IMPORTANCE_CSVS = REPO_ROOT / "data" / "analysis" / "feature_importance"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs07-mrt-impact-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

WINDOW_START = "2021-01"
LEGACY_TOWNS_SECTION = "### 2. The average hides large town-level differences"

# The scan universe is a sorted filesystem walk over these roots. The
# exclusions are the programme's own output surfaces, not evidence of RS07's
# retired method: `docs/implementation/` holds the per-study records (this
# ledger and this tool's own prose pack are under it), `scripts/tools/` holds
# the evidence producers themselves, and `prompts/` holds the handoffs and
# runbooks. Published edition texts under `docs/analytics/editions/` are
# programme outputs too and are excluded, EXCEPT the frozen legacy originals,
# because the legacy article's own figures are what the content patterns are
# matched against. The D12 decisions doc is excluded for the same reason the
# RS10 ledger excludes it: it records what reviewers found, in their own
# vocabulary. `app/public/data/analytics/` holds the study producers'
# generated UI payloads (spatial analysis, feature impact, predictive
# analytics, rental hotspots); they are programme outputs, not RS07 evidence,
# and sibling studies publishing there must not drift this pinned scan — the
# RS07 calculator asset lives under `app/public/data/interactive_tools/` and
# stays IN the scan, as do all bronze/raw/external data roots. Every exclusion
# is disclosed in the ledger at `absenceScans.universe.excluded*`.
#
# The pinned inventory at `absenceScans.universe.scannedFiles` follows the
# scanned tree rather than a fixed list: the shared pipeline source under
# `src/`, the app source, `tests/` and the data roots are read and pinned, so a
# semantics-preserving edit to any scanned file (a typing fix, a reflow) re-pins
# that file and drifts the ledger without moving a single match. That is
# declaration-only drift: refresh it by re-running the producer, never by
# widening the exclusions, because excluding a scanned surface would suppress
# the match lists the absence claims rest on. Only the programme's own output
# surfaces above are excluded, and that exclusion set is unchanged.
SCAN_ROOTS = ("app/public", "app/src", "assets", "data", "docs", "scripts", "src", "tests")
EXCLUDED_SCAN_PREFIXES = (
    "docs/implementation/",
    "docs/analytics/editions/",
    "prompts/",
    "scripts/tools/",
    "app/public/data/analytics/",
    "app/src/components/studies/",
    "app/tests/",
)
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
EXCLUDED_SCAN_PATHS = (
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
    ".secrets.baseline",
)
SKIP_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "dist",
    "build",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    "coverage",
}
CONTENT_SUFFIXES = (".md", ".py", ".ts", ".tsx", ".json", ".csv", ".txt", ".astro", ".yml", ".yaml")
GZ_CONTENT_SUFFIX = ".json.gz"  # decompressed before the content patterns run

# Short, factual descriptions for the known MRT-named files the station-date
# scan matches. If a file disappears the scan's match list changes and the
# ledger drifts loudly; a stale note cannot survive a `--check`.
MRT_FILE_NOTES = {
    "data/pipeline/01_bronze/raw_mrt_stations.parquet": (
        "bronze station frame; schema read at mrtStationsFrame"
    ),
    "data/pipeline/01_bronze/external/mrt_stations.json": (
        "station -> line-code list mapping; no date field; no status field"
    ),
    "data/pipeline/01_bronze/external/MRTStations.geojson": (
        "2019 legacy seed layer; per-feature stamps at mrtStationsFrame.seedGeojson"
    ),
    "data/raw/external/datagov/MRTStations.geojson": (
        "same-bytes copy of the 2019 seed layer (sha256 equals the bronze copy)"
    ),
    "data/raw/external/datagov/MRTStationExits.geojson": (
        "station-exit layer; per-feature stamps at mrtStationsFrame.exitsLayer"
    ),
    "data/manual/mrt_lines_mapping.csv": (
        "manual station/line/tier table; no date column; strict CSV parse fails at line 81"
    ),
    "data/manual/mrt_stations_list.txt": ("four-line pasted Python traceback, not a station list"),
    "data/analysis/amenity_impact/mrt_distance_stratification.csv": (
        "derived distance-band summary of an earlier run; unlinked to any run in this checkout"
    ),
    "data/manual/csv/datagov/MRTStations.geojson": (
        "byte-identical copy of the 2019 seed layer (sha256 equals data/raw's copy)"
    ),
    "data/manual/csv/datagov/MRTStationExits.geojson": (
        "byte-identical copy of the station-exit layer (sha256 equals data/raw's copy)"
    ),
    "app/public/data/interactive_tools/mrt_cbd_impact.json.gz": (
        "calculator coefficient asset; no station metadata at all (calculatorAsset)"
    ),
    "app/src/components/tools/MrtCbdInspection.tsx": (
        "app consumer; inspection-only state (calculatorLock)"
    ),
    "app/src/components/tools/lib/tool-evidence.ts": (
        "app consumer notes; inspection-only state (calculatorLock)"
    ),
    "src/egg_n_bacon_housing/utils/mrt_line_mapping.py": (
        "tier/interchange/score producer code; no station dates"
    ),
    "tests/test_mrt_line_mapping.py": "tests for the tier/score code",
    "assets/svg/18-lease-and-mrt-model-tools.svg": "UI artwork",
    "docs/analytics/mrt-impact.md": "living copy of the legacy article (unfrozen)",
    "docs/analytics/editions/legacy/2026-11-12/mrt-impact.md": (
        "frozen legacy text this pack checks against"
    ),
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _r(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    value = float(value)
    if not np.isfinite(value):
        return None
    return round(value, digits)


def _code_quote(path: Path, marker: str, label: str) -> dict[str, Any]:
    """Locate a marker line in a source file and cite it verbatim."""
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


def _resolve_ledger_path(payload: dict[str, Any], dotted: str) -> bool:
    node: Any = payload
    for part in dotted.split("."):
        if isinstance(node, dict):
            if part not in node:
                return False
            node = node[part]
        elif isinstance(node, list):
            match = [item for item in node if isinstance(item, dict) and item.get("id") == part]
            if not match:
                return False
            node = match[0]
        else:
            return False
    return True


# ---------------------------------------------------------------------------
# Cutoff and study window
# ---------------------------------------------------------------------------


def measure_cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    hdb = frame.loc[frame["property_type"] == "hdb"]
    counts = {str(k): int(v) for k, v in hdb.groupby("month").size().items()}
    ordered = sorted(counts)
    terminal = ordered[-1]
    trailing = [counts[month] for month in ordered[-13:-1]]
    trailing_median = float(np.median(trailing)) if trailing else 0.0
    share = counts[terminal] / trailing_median if trailing_median else None
    last_complete = ordered[-2]
    all_counts = {str(k): int(v) for k, v in frame.groupby("month").size().items()}
    all_ordered = sorted(all_counts)
    all_trailing = [all_counts[m] for m in all_ordered[-13:-1]]
    all_median = float(np.median(all_trailing)) if all_trailing else 0.0
    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact"
        ),
        "grain": "HDB transactions (the legacy article's primary focus)",
        "lastCompleteMonth": last_complete,
        "terminalMonth": terminal,
        "terminalMonthTransactions": counts[terminal],
        "trailing12MedianTransactions": _r(trailing_median, 1),
        "terminalMonthShareOfTrailingMedian": _r(share, 4),
        "allPropertyTypesCrossCheck": {
            "terminalMonth": all_ordered[-1],
            "terminalMonthShareOfTrailingMedian": _r(
                all_counts[all_ordered[-1]] / all_median if all_median else None, 4
            ),
        },
        "boundAppliedTo": [
            "studyWindow",
            "shippedMrtFeatures.windowStats",
            "responses",
            "townDescriptives.windowCounts",
        ],
    }


def study_window(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """Measured coverage per segment and the legacy sample-count contrast."""
    out: dict[str, Any] = {}
    for segment in ("hdb", "condo"):
        seg = frame.loc[frame["property_type"] == segment]
        months = sorted(seg["month"].unique())
        win = seg.loc[(seg["month"] >= WINDOW_START) & (seg["month"] <= last_complete)]
        out[segment] = {
            "fileMonths": len(months),
            "firstMonthInFile": months[0],
            "lastMonthInFile": months[-1],
            "windowMonths": sum(1 for m in months if WINDOW_START <= m <= last_complete),
            "windowRows": int(len(win)),
            "windowStart": WINDOW_START,
            "windowEnd": last_complete,
            "rowsInTerminalMonth": int((seg["month"] > last_complete).sum()),
        }
    # The legacy sample bullet, re-measured on this checkout's data.
    hdb = frame.loc[frame["property_type"] == "hdb"]
    with_coords = hdb["lat"].notna() & hdb["lon"].notna()
    from_2021 = hdb["month"] >= "2021-01"
    legacy_filter_rows_incl_terminal = int((from_2021 & with_coords).sum())
    legacy_filter_rows_to_cutoff = int(
        ((hdb["month"] >= WINDOW_START) & (hdb["month"] <= last_complete) & with_coords).sum()
    )
    out["legacySampleContrast"] = {
        "statedFilter": (
            "97,133 HDB transactions, filtered to 2021 onward, with valid coordinates"
        ),
        "measuredFilterRowsIncludingTerminalMonth": legacy_filter_rows_incl_terminal,
        "measuredFilterRowsThroughCutoff": legacy_filter_rows_to_cutoff,
        "reproducesStatedCount": False,
        "note": (
            "the legacy's stated filter does not reproduce 97,133 on this checkout's "
            "data under either bound; the legacy's L3 input file and its H3-grid "
            "minimum-10 filter are absent, so the difference cannot be resolved here "
            "(not-reproducible, not contradicted: a different input frame can hold "
            "a different row count)"
        ),
    }
    return out


# ---------------------------------------------------------------------------
# The bronze station frame and the shipped MRT features
# ---------------------------------------------------------------------------


def mrt_stations_frame() -> dict[str, Any]:
    """Schema-first read of the 188-row frame; the four missingness states."""
    parquet = pq.ParquetFile(RAW_MRT)
    schema = parquet.schema_arrow
    column_names = [schema.field(i).name for i in range(len(schema))]
    frame = pd.read_parquet(RAW_MRT)
    date_like = [
        name
        for name in column_names
        if re.search(r"date|open|status|year|time|stamp", name, flags=re.IGNORECASE)
    ]
    duplicates = frame.loc[frame["name"].duplicated(keep=False)].sort_values("name")
    dup_names = sorted(duplicates["name"].unique().tolist())
    empty_line = frame.loc[frame["line"].astype(str).str.strip() == "", "name"].tolist()
    line_counts = {str(k): int(v) for k, v in frame["line"].value_counts().items()}
    manifest = json.loads(BRONZE_MANIFEST.read_text(encoding="utf-8"))
    mrt_entry = manifest.get("raw_mrt_stations")
    seed_props = [
        dict(feature.get("properties", {}))
        for feature in json.loads(RAW_MRT_GEOJSON.read_text(encoding="utf-8"))["features"]
    ]
    seed_stamps = Counter(str(p.get("FMEL_UPD_D") or "") for p in seed_props)
    seed_rail = Counter(str(p.get("RAIL_TYPE") or "") for p in seed_props)
    exits_payload = json.loads(RAW_EXITS_GEOJSON.read_text(encoding="utf-8"))
    exits_props = [dict(f.get("properties", {})) for f in exits_payload["features"]]
    exits_stamps = Counter(str(p.get("FMEL_UPD_D") or "") for p in exits_props)
    station_lines = json.loads(SEED_STATIONS_JSON.read_text(encoding="utf-8"))
    return {
        "path": RAW_MRT.relative_to(REPO_ROOT).as_posix(),
        "rowGroups": int(parquet.metadata.num_row_groups),
        "rows": int(parquet.metadata.num_rows),
        "columnCount": int(parquet.metadata.num_columns),
        "columns": [
            {"name": schema.field(i).name, "type": str(schema.field(i).type)}
            for i in range(len(schema))
        ],
        "openingDateColumnPresent": False,
        "statusColumnPresent": False,
        "namePatternScanForDateOrStatusColumns": {
            "pattern": "date|open|status|year|time|stamp (case-insensitive, column names)",
            "matchedColumns": date_like,
        },
        "missingnessStates": {
            "nullValues": {
                "name": int(frame["name"].isna().sum()),
                "lat": int(frame["lat"].isna().sum()),
                "lon": int(frame["lon"].isna().sum()),
                "line": int(frame["line"].isna().sum()),
            },
            "recordedZeros": {
                "latExactlyZero": int((frame["lat"] == 0).sum()),
                "lonExactlyZero": int((frame["lon"] == 0).sum()),
            },
            "recordedEmptyStrings": {
                "lineEmptyString": len(empty_line),
                "names": sorted(empty_line),
            },
            "absentColumns": ["no opening-date column", "no operating-status column"],
            "absentRows": "not applicable: all 188 rows carry all four columns",
            "note": (
                "a null value, a recorded zero, an empty string and an absent column "
                "are different states and are counted separately; the row count "
                "describes this file, not the series of stations over time"
            ),
        },
        "distinctStationNames": int(frame["name"].nunique()),
        "duplicateNameRows": {
            "names": dup_names,
            "rows": int(len(duplicates)),
            "note": (
                "each duplicated name appears once per physical centroid with "
                "near-identical coordinates; nearest-station selection picks whichever "
                "centroid is closer"
            ),
        },
        "lineValueCounts": line_counts,
        "lineValuesIncludeEmptyString": True,
        "manifestRecord": {
            "path": BRONZE_MANIFEST.relative_to(REPO_ROOT).as_posix(),
            "entry": mrt_entry,
            "note": (
                "the manifest records the stored frame as fetched from the live LTA "
                "path; the fetch run itself is outside this checkout, so the record is "
                "a screened-as fact about provenance, origin unverified"
            ),
        },
        "seedGeojson": {
            "path": RAW_MRT_GEOJSON.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(RAW_MRT_GEOJSON),
            "bytes": RAW_MRT_GEOJSON.stat().st_size,
            "features": len(seed_props),
            "propertyKeys": sorted(seed_props[0].keys()),
            "fmelUpdDHistogram": {k: seed_stamps[k] for k in sorted(seed_stamps)},
            "railTypeCounts": {k: seed_rail[k] for k in sorted(seed_rail)},
            "identicalBytesInBronze": {
                "path": SEED_MRT_GEOJSON_BRONZE.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(SEED_MRT_GEOJSON_BRONZE),
                "equal": sha256_of(RAW_MRT_GEOJSON) == sha256_of(SEED_MRT_GEOJSON_BRONZE),
            },
            "note": (
                "FMEL_UPD_D is a dataset update stamp; it dates the layer's refresh, "
                "not any station's opening. The layer carries no status property."
            ),
        },
        "exitsLayer": {
            "path": RAW_EXITS_GEOJSON.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(RAW_EXITS_GEOJSON),
            "bytes": RAW_EXITS_GEOJSON.stat().st_size,
            "features": len(exits_props),
            "propertyKeys": sorted(exits_props[0].keys()),
            "fmelUpdDHistogram": {k: exits_stamps[k] for k in sorted(exits_stamps)},
        },
        "stationLinesJson": {
            "path": SEED_STATIONS_JSON.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(SEED_STATIONS_JSON),
            "bytes": SEED_STATIONS_JSON.stat().st_size,
            "stationCount": len(station_lines),
            "shape": "station name -> list of line codes; no dates, no status",
        },
        "verdict": (
            "screened as carrying no per-station opening date and no operating "
            "status anywhere: the frame's schema has four columns (name/lat/lon/line), "
            "the column-name pattern scan matches none, and the only date-like field "
            "on any MRT-named file is a dataset update stamp; origin unverified"
        ),
    }


def _unified_schema_checks(parquet: pq.ParquetFile) -> dict[str, Any]:
    """Read the platinum schema from file metadata; derive the absence checks.

    The legacy's named control (`remaining_lease_months`) and any CBD-distance
    column are absence claims, so the full column-name list and the derived
    checks are recorded fields rather than assumed facts.
    """
    names = list(parquet.schema_arrow.names)
    return {
        "columnNames": names,
        "remainingLeaseMonthsPresent": "remaining_lease_months" in names,
        "remainingLeasePresent": "remaining_lease" in names,
        "leaseCommenceDatePresent": "lease_commence_date" in names,
        "cbdLikeColumnNames": [n for n in names if "cbd" in n.lower()],
    }


def shipped_mrt_features(
    frame: pd.DataFrame, last_complete: str, schema: dict[str, Any]
) -> dict[str, Any]:
    """The four shipped MRT feature columns: states, units, and the join."""
    columns = [
        "dist_to_nearest_mrt",
        "nearest_mrt_tier",
        "nearest_mrt_is_interchange",
        "nearest_mrt_score",
        "nearest_mrt_station",
    ]
    per_column: dict[str, Any] = {}
    for column in columns:
        series = frame[column]
        entry: dict[str, Any] = {
            "present": True,
            "nullsFullFile": int(series.isna().sum()),
            "nonNullFullFile": int(series.notna().sum()),
        }
        if series.dtype != object:
            entry["recordedZerosFullFile"] = int((series == 0).sum())
        per_column[column] = entry
    coord_null = frame["lat"].isna() | frame["lon"].isna()
    mrt_null = frame["dist_to_nearest_mrt"].isna()
    win = frame.loc[(frame["month"] >= WINDOW_START) & (frame["month"] <= last_complete)]
    win_null = win.loc[win["dist_to_nearest_mrt"].isna()]
    station_names = set(frame["nearest_mrt_station"].dropna().astype(str))
    bronze = pd.read_parquet(RAW_MRT)
    bronze_names = set(bronze["name"].astype(str))
    station_lines = json.loads(SEED_STATIONS_JSON.read_text(encoding="utf-8"))
    hdb = win.loc[win["property_type"] == "hdb"]
    condo = win.loc[win["property_type"] == "condo"]

    def dist_stats(seg: pd.DataFrame) -> dict[str, Any]:
        d = seg["dist_to_nearest_mrt"].dropna()
        return {
            "min": _r(d.min(), 1),
            "p25": _r(d.quantile(0.25), 1),
            "median": _r(d.median(), 1),
            "mean": _r(d.mean(), 1),
            "p75": _r(d.quantile(0.75), 1),
            "max": _r(d.max(), 1),
            "sd": _r(d.std(ddof=1), 1),
        }

    return {
        "units": {
            "distToNearestMrt": {
                "unit": "metres",
                "evidence": [
                    _code_quote(GEO_MODULE, "Vectorized great-circle distance in metres", "geo"),
                    _code_quote(PROXIMITY_MODULE, "distances = haversine_metres(", "proximity"),
                ],
            },
            "nearestMrtTier": {
                "unit": "integer tier 1-3 from the station's line set",
                "evidence": [
                    _code_quote(LINE_MAPPING_MODULE, "def station_tier", "tier"),
                ],
            },
            "nearestMrtIsInterchange": {
                "unit": "boolean, true when the station maps to 2+ lines",
                "evidence": [
                    _code_quote(LINE_MAPPING_MODULE, "len(lines) >= 2", "interchange"),
                ],
            },
            "nearestMrtScore": {
                "unit": "(4 - tier + interchange bonuses) * 1000 / max(distance in m, 1)",
                "evidence": [
                    _code_quote(LINE_MAPPING_MODULE, "basis = 4 - tier", "basis"),
                    _code_quote(
                        LINE_MAPPING_MODULE, "(basis * 1000) / max(distance_m, 1)", "score"
                    ),
                ],
            },
        },
        "producerNote": (
            "the four feature columns are produced by utils/proximity.py from the "
            "bronze frame plus the station->line mapping; the citations above are "
            "marker-checked at build time; screened as the producer, origin unverified"
        ),
        "perColumn": per_column,
        "missingnessStates": {
            "rowsWithNullMrtColumnsFullFile": int(mrt_null.sum()),
            "rowsWithNullCoordinatesFullFile": int(coord_null.sum()),
            "nullMrtEqualsNullCoordinates": bool((mrt_null == coord_null).all()),
            "inWindowRowsWithNullMrtColumns": int(len(win_null)),
            "inWindowNullMrtRows": [
                {
                    "month": row["month"],
                    "propertyType": row["property_type"],
                    "price": _r(row["price"], 2),
                }
                for _, row in win_null.iterrows()
            ],
            "recordedZerosFullFile": {
                "distExactlyZero": int((frame["dist_to_nearest_mrt"] == 0).sum()),
                "tierExactlyZero": int((frame["nearest_mrt_tier"] == 0).sum()),
                "scoreExactlyZero": int((frame["nearest_mrt_score"] == 0).sum()),
            },
            "absentColumns": [
                note
                for note, absent in (
                    (
                        "remaining_lease_months (the legacy's named control; absent "
                        "from the recorded schema at inputs.unifiedDataset.columnNames; "
                        "the file carries remaining_lease as a string and "
                        "lease_commence_date as a year)",
                        not schema["remainingLeaseMonthsPresent"],
                    ),
                    (
                        "no CBD-distance column of any name (the recorded schema check "
                        "inputs.unifiedDataset.cbdLikeColumnNames is empty; an absent "
                        "column, not a null value)",
                        not schema["cbdLikeColumnNames"],
                    ),
                )
                if absent
            ],
            "absentRows": (
                "no condo row exists before 2021-01 in this file (source window), "
                "measured at studyWindow.condo; the HDB series begins 1990-01"
            ),
        },
        "windowStats": {
            "cutoffUpperBound": last_complete,
            "hdb": {
                "rows": int(len(hdb)),
                "distance": dist_stats(hdb),
                "tierCounts": {
                    str(int(k)): int(v) for k, v in hdb["nearest_mrt_tier"].value_counts().items()
                },
                "interchangeTrue": int(
                    hdb["nearest_mrt_is_interchange"].fillna(False).astype(bool).sum()
                ),
                "scoreMax": _r(hdb["nearest_mrt_score"].max(), 2),
            },
            "condo": {
                "rows": int(len(condo)),
                "distance": dist_stats(condo),
                "tierCounts": {
                    **{
                        str(int(k)): int(v)
                        for k, v in condo["nearest_mrt_tier"].dropna().value_counts().items()
                    },
                    "null": int(condo["nearest_mrt_tier"].isna().sum()),
                },
                "interchangeTrue": int(
                    condo["nearest_mrt_is_interchange"].fillna(False).astype(bool).sum()
                ),
                "scoreMax": _r(condo["nearest_mrt_score"].max(), 2),
            },
        },
        "stationJoin": {
            "shippedDistinctStations": len(station_names),
            "shippedStationsFoundInBronzeFrame": len(station_names & bronze_names),
            "shippedStationsAbsentFromBronzeFrame": sorted(station_names - bronze_names),
            "shippedStationsFoundInStationLinesJson": len(station_names & set(station_lines)),
            "shippedStationsAbsentFromStationLinesJson": sorted(station_names - set(station_lines)),
            "note": (
                "every shipped nearest-station name is found in the 188-row bronze "
                "frame; the names the station-lines json lacks are exactly the frame's "
                "empty-line rows — screened as consistent with the shipped distances "
                "having been computed against this frame; origin unverified"
            ),
        },
        "lineMappingCsv": {
            "path": MANUAL_LINES_MAPPING.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(MANUAL_LINES_MAPPING),
            "bytes": MANUAL_LINES_MAPPING.stat().st_size,
            "linesOnDisk": len(MANUAL_LINES_MAPPING.read_text(encoding="utf-8").splitlines()),
            "strictParse": "fails at line 81: expected 7 fields, saw 8",
            "wellFormedRowsBeforeFailure": 80,
            "referencedByCode": False,
            "note": (
                "carries station_name/line/is_interchange/tier but no date column; no "
                "code in src/ or app/src references it — a manual lead, not the "
                "pipeline's tier source"
            ),
        },
        "stationsListTxt": {
            "path": MANUAL_STATIONS_LIST.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(MANUAL_STATIONS_LIST),
            "bytes": MANUAL_STATIONS_LIST.stat().st_size,
            "content": MANUAL_STATIONS_LIST.read_text(encoding="utf-8"),
            "note": "a pasted Python traceback, not a station list",
        },
    }


# ---------------------------------------------------------------------------
# Calculator asset and the lock
# ---------------------------------------------------------------------------


def calculator_asset() -> dict[str, Any]:
    """Full read of the coefficient asset; its arithmetic; its unlinkage."""
    gz_bytes = CALCULATOR_ASSET.read_bytes()
    json_bytes = gzip.decompress(gz_bytes)
    payload = json.loads(json_bytes)
    types = payload["property_type_multipliers"]
    towns = payload["town_multipliers"]
    premiums = payload["town_premiums"]
    cbd = payload["cbd_coefficients"]
    hdb_base = float(types["HDB"]["premium_per_100m"])
    condo_base = float(types["Condominium"]["premium_per_100m"])
    hdb_dev = max(
        abs(float(row["hdb_premium_per_100m"]) - hdb_base * float(row["multiplier"]))
        for row in premiums
    )
    condo_dev = max(
        abs(float(row["condo_premium_per_100m"]) - condo_base * float(row["multiplier"]))
        for row in premiums
    )
    return {
        "path": CALCULATOR_ASSET.relative_to(REPO_ROOT).as_posix(),
        "sha256Gz": hashlib.sha256(gz_bytes).hexdigest(),
        "bytesGz": len(gz_bytes),
        "sha256JsonDecompressed": hashlib.sha256(json_bytes).hexdigest(),
        "bytesJsonDecompressed": len(json_bytes),
        "topLevelKeys": sorted(payload.keys()),
        "propertyTypeMultipliers": types,
        "townMultiplierCount": len(towns),
        "townPremiumCount": len(premiums),
        "townImpactCount": len(payload["town_impacts"]),
        "townImpactLabels": sorted({row["label"] for row in payload["town_impacts"].values()}),
        "cbdCoefficients": cbd,
        "internalArithmetic": {
            "hdbPremiumEqualsBaseTimesMultiplier": bool(hdb_dev < 1e-9),
            "condoPremiumEqualsBaseTimesMultiplier": bool(condo_dev < 1e-9),
            "maxDeviationHdb": _r(hdb_dev, 6),
            "maxDeviationCondo": _r(condo_dev, 6),
            "condoOverHdbBasePremiumRatio": _r(condo_base / hdb_base, 4),
            "note": (
                "the stored per-type bases reproduce the asset's own town rows exactly; "
                "the recorded 7.0 condo-over-HDB ratio of stored bases is inventory of "
                "this unlinked asset, not a measured sensitivity, and must not be "
                "marketed as one"
            ),
        },
        "linkStatus": {
            "producerFoundOnScannedSurface": False,
            "statement": (
                "no file in the scanned surface produces or updates this asset; it is "
                "an unlinked artefact and adjudicates nothing in either direction — "
                "evidence neither for nor against any legacy coefficient"
            ),
            "appConsumer": "app/src/components/tools/MrtCbdInspection.tsx (inspection-only; calculatorLock)",
        },
    }


def calculator_lock(register_gate_line: int) -> dict[str, Any]:
    """The calculator stays locked; this pack records the state it found."""
    asset = json.loads(gzip.decompress(CALCULATOR_ASSET.read_bytes()))
    hdb_cbd = asset["cbd_coefficients"]["HDB"]["discount_per_km"]
    return {
        "appSurface": {
            "component": _code_quote(MRT_INSPECTION_TSX, "never a premium total", "component"),
            "evidenceBadge": _code_quote(MRT_INSPECTION_TSX, "Model review required", "badge"),
            "withheldNote": _code_quote(TOOL_EVIDENCE_TS, "MRT_WITHHELD_NOTE =", "note"),
            "unitNote": _code_quote(TOOL_EVIDENCE_TS, "MRT_UNIT_NOTE =", "unit-note"),
            "noFallbackNote": _code_quote(TOOL_EVIDENCE_TS, "MRT_NO_FALLBACK_NOTE =", "fallback"),
        },
        "registerRow": {
            "path": REGISTER.relative_to(REPO_ROOT).as_posix(),
            "gateLine": register_gate_line,
            "assetRowQuote": _code_quote(REGISTER, "mrt_cbd_impact.json.gz", "RA07")["quote"],
            "assetRowDisposition": (
                "RF06 preserves tool contract; RS07 proposes changes. Continue "
                "coefficient inspection/withheld total until model units/combination "
                "semantics are independently approved."
            ),
        },
        "unlockedByThisPack": False,
        "totalDollarEstimateReleased": False,
        "statement": (
            "the gate leaves the calculator locked: the app consumer stays in its "
            "inspection-only state, the stored units and distance direction remain "
            "undeclared, and no output of this pack changes the tool's behaviour or "
            "releases a total-dollar estimate"
        ),
        "storedUnitsAsFound": {
            "propertyTypeBases": {
                key: {
                    "premium_per_100m": value["premium_per_100m"],
                    "cbd_per_km": value["cbd_per_km"],
                }
                for key, value in asset["property_type_multipliers"].items()
            },
            "hdbCbdDiscountPerKm": hdb_cbd,
            "note": (
                "coefficients are recorded exactly as stored, with the app's own "
                "caveat: neither the premium-per-100m nor the CBD-per-km figure "
                "declares a floor-area denominator, and the distance direction is "
                "undeclared"
            ),
        },
    }


# ---------------------------------------------------------------------------
# The refit: one recorded specification per segment, standardized effects
# ---------------------------------------------------------------------------

CONTROLS_COMMON = "floor_area_sqm"
FIXED_EFFECTS_COMMON = "planning_area + transaction year"


def _prep_segment(
    frame: pd.DataFrame, segment: str, last_complete: str, rich: bool
) -> tuple[pd.DataFrame, dict[str, Any]]:
    win = frame.loc[
        (frame["property_type"] == segment)
        & (frame["month"] >= WINDOW_START)
        & (frame["month"] <= last_complete)
    ].copy()
    base_ok = (
        win["dist_to_nearest_mrt"].notna()
        & (win["price"] > 0)
        & (win["psf"] > 0)
        & win["floor_area_sqm"].notna()
        & win["planning_area"].notna()
    )
    rich_ok = (
        win["lease_commence_date"].notna()
        & win["storey_min"].notna()
        & win["storey_max"].notna()
        & win["town"].notna()
    )
    ok = (base_ok & rich_ok) if rich else base_ok
    excluded = win.loc[~ok]
    work = win.loc[ok].copy()
    work["storey_mid"] = (work["storey_min"] + work["storey_max"]) / 2.0
    work["yr"] = work["month"].str[:4]
    reasons = {
        "dist_to_nearest_mrt": "missing-mrt-distance-or-coordinates",
        "planning_area": "missing-planning-area",
        "lease_commence_date": "missing-lease-commencement (all condo rows)",
        "storey_min": "missing-storey (all condo rows)",
        "town": "missing-town (all condo rows)",
    }
    excluded_rows = [
        {
            "month": row["month"],
            "propertyType": row["property_type"],
            "price": _r(row["price"], 2),
            "reasons": [label for column, label in reasons.items() if pd.isna(row[column])],
        }
        for _, row in excluded.iterrows()
    ]
    return work, {
        "windowRows": int(len(win)),
        "estimationRows": int(len(work)),
        "excludedRows": int(len(excluded)),
        "excludedRowDetails": excluded_rows,
    }


def _fit_spec(work: pd.DataFrame, response: str, rich: bool) -> tuple[Any, dict[str, Any]]:
    if rich:
        formula = (
            f"{response} ~ dist_to_nearest_mrt + floor_area_sqm"
            " + lease_commence_date + storey_mid + C(town) + C(yr)"
        )
    else:
        formula = f"{response} ~ dist_to_nearest_mrt + floor_area_sqm + C(planning_area) + C(yr)"
    model = smf.ols(formula, data=work).fit(cov_type="HC1", use_t=False)
    return model, {
        "formula": formula,
        "n": int(model.nobs),
        "k": int(len(model.params)),
        "rSquared": _r(model.rsquared, 4),
    }


def _spec_fields(work: pd.DataFrame, model: Any, response: str) -> tuple[dict[str, Any], float]:
    """Recorded fields for one fit; also returns the raw standardized beta."""
    beta = float(model.params["dist_to_nearest_mrt"])
    se = float(model.bse["dist_to_nearest_mrt"])
    sd_x = float(work["dist_to_nearest_mrt"].std(ddof=1))
    sd_y = float(work[response].std(ddof=1))
    std_beta = beta * sd_x / sd_y
    fields = {
        "sample": {
            "windowStart": WINDOW_START,
            "cutoffUpperBound": None,  # filled by the caller
            "meanPrice": _r(work["price"].mean(), 2),
            "meanPsf": _r(work["psf"].mean(), 2),
            "sdLogResponse": _r(sd_y, 4),
            "sdDistanceMetres": _r(sd_x, 1),
            "ecShareOfSample": _r(float(work["is_ec"].astype(bool).mean()), 4),
            "ecRows": int(work["is_ec"].astype(bool).sum()),
        },
        "fit": {},
        "mrtCoefficient": {
            "betaLogPointsPerMetre": _r(beta, 6),
            "hc1Se": _r(se, 6),
            "tStat": _r(beta / se, 1),
            "logPointsPer100mNearer": _r(-100.0 * beta, 4),
            "pctPer100mNearerExpMinus1": _r(100.0 * (float(np.exp(-100.0 * beta)) - 1.0), 4),
            "standardizedBeta": _r(std_beta, 4),
        },
    }
    return fields, std_beta


def responses(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """One recorded specification per segment; standardized effects only."""
    specs: list[dict[str, Any]] = []
    std: dict[tuple[str, str, bool], float] = {}
    plan = [
        ("hdb-log-price-rich-controls", "hdb", "lprice", True),
        ("hdb-log-psf-rich-controls", "hdb", "lpsf", True),
        ("hdb-log-price-common-controls", "hdb", "lprice", False),
        ("hdb-log-psf-common-controls", "hdb", "lpsf", False),
        ("condo-log-price-available-controls", "condo", "lprice", False),
        ("condo-log-psf-available-controls", "condo", "lpsf", False),
    ]
    prepared: dict[tuple[str, bool], pd.DataFrame] = {}
    sample_infos: dict[tuple[str, bool], dict[str, Any]] = {}
    for spec_id, segment, response, rich in plan:
        key = (segment, rich)
        if key not in prepared:
            work, sample_info = _prep_segment(frame, segment, last_complete, rich)
            prepared[key] = work
            sample_infos[key] = sample_info
        work = prepared[key].copy()
        work["lprice"] = np.log(work["price"])
        work["lpsf"] = np.log(work["psf"])
        model, fit = _fit_spec(work, response, rich)
        fields, std_beta = _spec_fields(work, model, response)
        fields["sample"]["cutoffUpperBound"] = last_complete
        fields["fit"] = fit
        entry = {
            "id": spec_id,
            "segment": segment,
            "response": "log(total price in SGD)"
            if response == "lprice"
            else "log(price per square foot in SGD)",
            "controls": (
                "floor_area_sqm (sqm), lease_commence_date (year), storey midpoint "
                "(floors), town fixed effects, transaction-year fixed effects"
                if rich
                else "floor_area_sqm (sqm), planning_area fixed effects, transaction-year fixed effects"
            ),
            "estimator": (
                "OLS (statsmodels), HC1 heteroskedasticity-robust covariance, use_t=False; "
                "descriptive conditional association only"
            ),
            "sampleSelection": sample_infos[key],
            **fields,
        }
        std[(segment, response, rich)] = std_beta
        specs.append(entry)
    ratio = std[("condo", "lprice", False)] / std[("hdb", "lprice", False)]
    ratio_psf = std[("condo", "lpsf", False)] / std[("hdb", "lpsf", False)]
    condo_window = frame.loc[
        (frame["property_type"] == "condo")
        & (frame["month"] >= WINDOW_START)
        & (frame["month"] <= last_complete)
    ]
    condo_null_controls = {
        "leaseCommenceNonNullRows": int(condo_window["lease_commence_date"].notna().sum()),
        "storeyNonNullRows": int(condo_window["storey_min"].notna().sum()),
        "townNonNullRows": int(condo_window["town"].notna().sum()),
        "condoWindowRows": int(len(condo_window)),
    }
    return {
        "responseDefinition": {
            "primary": "log(total transaction price in SGD)",
            "secondary": "log(price per square foot in SGD, shipped psf column)",
            "gateClause": (
                "the gate asks to confirm the metres/km and total-price/log/PSF "
                "response: distance is metres (shippedMrtFeatures.units), the "
                "calculator asset's rates are stored per 100 m and per km "
                "(calculatorAsset.storedLabels), and the refit responses above are "
                "log total price (primary) and log PSF (secondary). The legacy's "
                "$-per-100m figures state no response unit and are not converted "
                "into any chosen unit here."
            ),
        },
        "specifications": specs,
        "standardizedComparison": {
            "basis": (
                "the two segments never share one specification: the condo rows carry "
                "all-null lease, storey and town (measured below), so the comparison "
                "uses the common-controls specification (floor area + planning-area FE "
                "+ year FE) that both segments can fit on the same window"
            ),
            "hdbCommonControlsStandardizedBeta": std[("hdb", "lprice", False)],
            "condoCommonControlsStandardizedBeta": std[("condo", "lprice", False)],
            "ratioCondoOverHdb": _r(ratio, 4),
            "psfResponseHdbStandardizedBeta": std[("hdb", "lpsf", False)],
            "psfResponseCondoStandardizedBeta": std[("condo", "lpsf", False)],
            "psfResponseRatioCondoOverHdb": _r(ratio_psf, 4),
            "statement": (
                "on the common-controls specification the condo standardized "
                "association is smaller than HDB's, not larger; this is a descriptive "
                "comparison of conditional associations in differently composed "
                "samples, it is not the legacy's interaction coefficient, and it "
                "neither confirms nor refutes the withdrawn 15x claim, whose model "
                "outputs are absent from this checkout"
            ),
        },
        "nonComparability": {
            "condoWindowRowsWithNonNullLeaseControl": condo_null_controls[
                "leaseCommenceNonNullRows"
            ],
            "condoWindowRowsWithNonNullStoreyControl": condo_null_controls["storeyNonNullRows"],
            "condoWindowRowsWithNonNullTown": condo_null_controls["townNonNullRows"],
            "condoWindowRowsMeasured": condo_null_controls["condoWindowRows"],
            "reasons": [
                "control sets cannot be equalised: every condo row carries null "
                "lease commencement, null storey and null town, so the condo "
                "specification is strictly poorer than the HDB rich specification",
                "response variances differ (recorded per specification as "
                "sdLogResponse) and standardized betas are scale facts of their own "
                "samples, not effect sizes comparable across samples",
                "the condo sample mixes ECs with condominiums (ecShareOfSample is "
                "recorded per specification)",
                "the area grain differs (HDB rich uses town FE; the common "
                "specification uses planning_area FE because condo rows carry no town)",
                "both coefficients are conditional associations in one cross-section; "
                "neither is an effect, so a ratio of them is not a ratio of effects",
            ],
            "statement": (
                "the standardized effects are reported as recorded fields and their "
                "ratio is computed, not asserted; the non-comparability reasons above "
                "are stated alongside, and no raw dollar-per-100m multiple between "
                "segments appears anywhere in this ledger"
            ),
        },
    }


def predictive_vs_causal() -> dict[str, Any]:
    return {
        "statement": (
            "every coefficient in responses.specifications is a predictive "
            "association: transactions nearer a station differ in price, conditional "
            "on controls, in one cross-section. Nothing here identifies why — no "
            "instrument, no quasi-experiment, no pretrend design, no treatment "
            "assignment — so no coefficient supports a causal 'premium' claim."
        ),
        "legacyDeltaR2": (
            "the legacy's CBD-only/CBD+MRT hierarchical regression is a predictive "
            "increment claim; its outputs (R² 0.2263 / 0.2341, delta +0.0078) are "
            "absent from this checkout and are not re-derived, so even the "
            "predictive-increment narrative cannot be re-measured here"
        ),
        "calculatorAsset": (
            "the calculator asset's stored formulas are arithmetic on stored "
            "coefficients; the app consumer discloses them without computing a "
            "total, and the asset's own CBD explanation literal ('22.6% of price "
            "variation') is a stored string of unlinked provenance"
        ),
        "languageRule": (
            "this pack writes 'association' for every measured coefficient; 'premium', "
            "'effect' and 'sensitivity' appear only as quoted legacy language or as "
            "withdrawn claims"
        ),
    }


# ---------------------------------------------------------------------------
# Town descriptives beside the legacy table
# ---------------------------------------------------------------------------


def _parse_legacy_town_table(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    inside = False
    seen_table_row = False
    for line in text.splitlines():
        if LEGACY_TOWNS_SECTION in line:
            inside = True
            continue
        if inside:
            if not line.startswith("|"):
                if seen_table_row:
                    break
                continue  # chart-metadata div and blank lines precede the table
            seen_table_row = True
            match = re.match(
                r"^\| (.+?) \| ([+-]\$[\d.]+)\s*\| \$([\d,]+)\s*\| ([\d,]+)\s*\|$",
                line.strip(),
            )
            if match:
                rows.append(
                    {
                        "id": match.group(1).strip(),
                        "legacyPremiumPer100mDollars": float(match.group(2).replace("$", "")),
                        "legacyMeanPsfDollars": float(match.group(3).replace(",", "")),
                        "legacyTransactions": int(match.group(4).replace(",", "")),
                    }
                )
    if len(rows) != 6:
        raise SystemExit(
            f"expected the six legacy town rows, parsed {len(rows)}; the frozen text "
            "may have changed"
        )
    return rows


def town_descriptives(
    frame: pd.DataFrame, last_complete: str, legacy_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    hdb = frame.loc[
        (frame["property_type"] == "hdb")
        & (frame["month"] >= WINDOW_START)
        & (frame["month"] <= last_complete)
    ]
    counts = hdb.groupby("town").size()
    window_counts = {
        "cutoffUpperBound": last_complete,
        "towns": int(len(counts)),
        "townsAtLeast500Transactions": int((counts >= 500).sum()),
        "townsWithFewerThan500Transactions": {
            str(town): int(count) for town, count in counts[counts < 500].sort_index().items()
        },
        "note": (
            "descriptive window counts only; the legacy's minimum-500 town OLS is "
            "not reproduced and no per-town coefficient is estimated here"
        ),
    }
    measured_rows = []
    for row in legacy_rows:
        town = row["id"]
        seg = hdb.loc[hdb["town"] == town]
        measured_rows.append(
            {
                **row,
                "measuredWindowTransactions": int(len(seg)),
                "measuredMedianDistanceMetres": _r(seg["dist_to_nearest_mrt"].median(), 1)
                if len(seg)
                else None,
                "measuredMedianPsf": _r(seg["psf"].median(), 2) if len(seg) else None,
            }
        )
    premiums = [row["legacyPremiumPer100mDollars"] for row in legacy_rows]
    max_premium = max(premiums)
    min_premium = min(premiums)
    return {
        "legacyTable": {
            "source": LEGACY_EDITION.relative_to(REPO_ROOT).as_posix(),
            "section": LEGACY_TOWNS_SECTION,
            "rows": measured_rows,
            "signSpread": {
                "maxLegacyPremiumPer100mDollars": _r(max_premium, 2),
                "minLegacyPremiumPer100mDollars": _r(min_premium, 2),
                "signSpreadDollars": _r(max_premium - min_premium, 2),
                "positiveRows": sum(1 for p in premiums if p > 0),
                "negativeRows": sum(1 for p in premiums if p < 0),
                "label": (
                    "the legacy table mixes three positive and three negative "
                    "per-town coefficients without labelling the spread as "
                    "heterogeneity; this ledger records the spread as a field and "
                    "reads it as unexplained heterogeneity, not as a national premium"
                ),
            },
            "verdict": (
                "the per-town figures are outputs of the retired town-level OLS; no "
                "artefact reproduces them, their window and population are unstated, "
                "and the measured columns beside them (window counts, medians) are "
                "descriptives of this checkout's data, not re-estimates"
            ),
        },
        "windowCounts": window_counts,
    }


# ---------------------------------------------------------------------------
# Absence scans
# ---------------------------------------------------------------------------


def _scan_universe() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                path = (Path(dirpath) / name).resolve()
                rel = path.relative_to(REPO_ROOT).as_posix()
                if any(rel.startswith(prefix) for prefix in EXCLUDED_SCAN_PREFIXES):
                    if rel.startswith(RETAINED_EDITION_PREFIX):
                        files.append(path)
                    continue
                if rel in EXCLUDED_SCAN_PATHS:
                    continue
                files.append(path)
    return sorted(files)


def _read_text_for_scan(path: Path) -> str | None:
    name = path.name
    if name.endswith(GZ_CONTENT_SUFFIX):
        try:
            return gzip.decompress(path.read_bytes()).decode("utf-8", errors="ignore")
        except OSError:
            return None
    if name.endswith(CONTENT_SUFFIXES):
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
    return None


def _filename_matches(rel: str, pattern: str) -> bool:
    return re.search(pattern, rel, flags=re.IGNORECASE) is not None


def _content_matches(files: list[Path], pattern: str) -> list[dict[str, Any]]:
    matches = []
    for path in files:
        text = _read_text_for_scan(path)
        if text is None:
            continue
        count = len(re.findall(pattern, text, flags=re.IGNORECASE))
        if count:
            matches.append(
                {
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "matchCount": count,
                }
            )
    return matches


def absence_scans() -> dict[str, Any]:
    files = _scan_universe()
    # The content patterns read the bytes of every text-suffix file (and every
    # *.json.gz, decompressed). Those reads are inputs of this ledger, so each
    # one is sha-pinned here: the declared input inventory covers everything
    # the producer reads. Files matched only at filename level are never read
    # and are therefore not inputs.
    readable = [
        p for p in files if p.name.endswith(CONTENT_SUFFIXES) or p.name.endswith(GZ_CONTENT_SUFFIX)
    ]
    scanned_files = [
        {
            "bytes": p.stat().st_size,
            "path": p.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(p),
        }
        for p in sorted(readable, key=lambda p: p.relative_to(REPO_ROOT).as_posix())
    ]
    universe = {
        "roots": list(SCAN_ROOTS),
        "skipDirectories": sorted(SKIP_DIRS),
        "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
        "retainedUnderExcludedPrefix": RETAINED_EDITION_PREFIX,
        "excludedPaths": list(EXCLUDED_SCAN_PATHS),
        "scannedFilesReadCount": len(scanned_files),
        "scannedFiles": scanned_files,
        "exclusionDisclosure": (
            "the excluded prefixes are the programme's own surfaces (per-study "
            "records, evidence producers, handoffs/runbooks, published editions "
            "except the frozen legacy originals, and the generated UI analytics "
            "payloads under app/public/data/analytics/ published by the study "
            "producers), app/src/components/studies/ (edition registry/pages), and "
            "app/tests/ (fixtures); .secrets.baseline and the D12 decisions "
            "register docs/plans/2026-11-12-reporting-refresh-decisions.md are "
            "explicitly excluded; the frozen legacy originals are retained because the article's own figures are what "
            "the content patterns match against; the RS07 calculator asset "
            "(app/public/data/interactive_tools/) is NOT excluded and all "
            "bronze/raw/external data roots stay in the scan; content patterns "
            "run only on the listed text suffixes plus *.json.gz (decompressed)"
        ),
        "scannedFileCount": len(files),
    }

    # (a) per-station opening dates / operating status
    mrt_files = [p for p in files if _filename_matches(p.relative_to(REPO_ROOT).as_posix(), r"mrt")]
    station_matches = [
        {
            "path": p.relative_to(REPO_ROOT).as_posix(),
            "note": MRT_FILE_NOTES.get(
                p.relative_to(REPO_ROOT).as_posix(),
                "matched at filename level; not structurally inspected",
            ),
        }
        for p in mrt_files
    ]

    # (b) XGBoost/SHAP importance artefact
    importance_files = [
        p
        for p in files
        if _filename_matches(p.relative_to(REPO_ROOT).as_posix(), r"xgboost|shap|importance")
    ]
    importance_facts = []
    for path in sorted(IMPORTANCE_CSVS.glob("*.csv")):
        frame = pd.read_csv(path)
        fact: dict[str, Any] = {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
            "rows": int(len(frame)),
        }
        if "feature" in frame.columns:
            hawker = frame.loc[frame["feature"] == "hawker_within_1km", "importance"]
            fact["hawkerWithin1kmImportance"] = (
                _r(float(hawker.iloc[0]), 8) if len(hawker) else None
            )
            fact["maxImportance"] = _r(frame["importance"].max(), 8)
            fact["carriesLegacyShares"] = False
        if "target" in frame.columns:
            fact["targets"] = sorted(frame["target"].astype(str).unique().tolist())
        importance_facts.append(fact)
    shap_matches_274 = _content_matches(files, r"27\.4")

    # (c) legacy OLS / hierarchical-regression output; includes the H3 grid artefact
    ols_files = [
        p
        for p in files
        if _filename_matches(
            p.relative_to(REPO_ROOT).as_posix(), r"\bols\b|regression|model_comparison|hierarchical"
        )
    ]
    r2_matches = _content_matches(files, r"0\.2263|0\.2341|0\.4977")
    h3_files = [
        p for p in files if _filename_matches(p.relative_to(REPO_ROOT).as_posix(), r"\bh3\b")
    ]
    h3_matches = _content_matches(files, r"H3 hexagonal|resolution 8")

    # (d) CBD definition asset
    cbd_files = [p for p in files if _filename_matches(p.relative_to(REPO_ROOT).as_posix(), r"cbd")]
    cbd_point_matches = _content_matches(files, r"1\.2839|103\.8513")

    return {
        "universe": universe,
        "stationDates": {
            "claimChecked": "MRT station opening dates / operating status",
            "filenamePattern": "path contains 'mrt' (case-insensitive)",
            "matchedFileCount": len(station_matches),
            "matchedFiles": station_matches,
            "structuredInspection": "see mrtStationsFrame (schema, stamps, seeds)",
            "verdict": (
                "screened as absent on the inspected surfaces only: the bronze frame's "
                "parquet schema carries four columns (name/lat/lon/line) and the "
                "column-name pattern scan for date|open|status|year|time|stamp matches "
                "none (mrtStationsFrame); the 2019 seed layer carries no status "
                "property and one dataset update stamp on all 257 features; the exits "
                "layer carries no status property and one stamp on all 597 features; "
                "the station-lines json carries no date field and no status field; the "
                "manual lines mapping carries no date column. The remaining filename "
                "matches are recorded at filename level and are not structurally "
                "inspected, so this screen makes no claim about their contents; a "
                "stamp dates a layer refresh, not a station opening; origin unverified"
            ),
        },
        "shapImportance": {
            "claimChecked": "legacy XGBoost/SHAP importance table (hawker 27.4% ...)",
            "filenamePattern": "xgboost|shap|importance (case-insensitive, path)",
            "matchedFileCount": len(importance_files),
            "matchedFiles": [p.relative_to(REPO_ROOT).as_posix() for p in importance_files],
            "numericCsvInspection": importance_facts,
            "contentPattern": r"27\.4",
            "contentMatches": shap_matches_274,
            "verdict": (
                "screened as absent: no machine-readable XGBoost/SHAP output on the "
                "scanned surface carries the legacy shares — the only importance CSVs "
                "carry a different mixed-segment model whose hawker_within_1km share "
                "is 0.02% (numericCsvInspection); the content pattern runs at substring "
                "level, so its matches split into narrative-prose files (the frozen "
                "text, its living copy, archive and planning records) and "
                "pattern-level substrings in data/code files (longer numbers, "
                "unrelated statistics) whose reading this screen cannot adjudicate; "
                "origin unverified, and the match lists adjudicate nothing either "
                "way about the legacy table's provenance"
            ),
        },
        "olsOutput": {
            "claimChecked": "legacy OLS / hierarchical-regression outputs (R² 0.2263 / 0.2341 / 0.4977)",
            "filenamePattern": r"\bols\b|regression|model_comparison|hierarchical (case-insensitive, path)",
            "matchedFileCount": len(ols_files),
            "matchedFiles": [p.relative_to(REPO_ROOT).as_posix() for p in ols_files],
            "contentPattern": r"0\.2263|0\.2341|0\.4977",
            "contentMatches": r2_matches,
            "verdict": (
                "screened as absent: no machine-readable OLS coefficient table from "
                "the legacy run exists on the scanned surface; the content matches "
                "are the frozen article text and its living copy (3 matches each) "
                "and the frozen and living findings summaries quoting the same three "
                "legacy values (4 matches each); two further matches in an unrelated "
                "anomalies table are the sequence 0.2341 occurring only inside longer "
                "floats, not the legacy values; the matched model_comparison.csv "
                "carries a different mixed-segment run whose linear-model R² is "
                "0.9120, not any legacy figure — an unlinked artefact, adjudicating nothing"
            ),
        },
        "h3Grid": {
            "claimChecked": "H3 resolution-8 grid with the 10-record minimum",
            "filenamePattern": r"\bh3\b (case-insensitive, path)",
            "matchedFileCount": len(h3_files),
            "matchedFiles": [p.relative_to(REPO_ROOT).as_posix() for p in h3_files],
            "contentPattern": "H3 hexagonal|resolution 8",
            "contentMatches": h3_matches,
            "verdict": (
                "screened as absent: no H3 grid artefact exists on the scanned "
                "surface — the three filename matches are archive notes and a plan "
                "document, not grid assets; the cell-area figure (~0.5 km²) and the "
                "10-record minimum are not re-derivable here and are recorded as "
                "underspecified"
            ),
        },
        "cbdDefinition": {
            "claimChecked": "CBD definition asset / reference point (1.2839, 103.8513)",
            "filenamePattern": "cbd (case-insensitive, path)",
            "matchedFileCount": len(cbd_files),
            "matchedFiles": [p.relative_to(REPO_ROOT).as_posix() for p in cbd_files],
            "contentPattern": r"1\.2839|103\.8513",
            "contentMatches": cbd_point_matches,
            "verdict": (
                "screened as absent: the coordinate pair's content matches are the "
                "frozen article text and its living copy (2 matches each) and a "
                "worked haversine example in a planning document "
                "(docs/plans/2026-01-24-spatial-analytics-overview.md, 2 matches); "
                "no scanned asset carries a CBD reference point or definition — the "
                "calculator asset stores per-km discount rates and explanation "
                "strings, which is a coefficient block, not a definition; the "
                "shipped dataset has no CBD-distance column at all"
            ),
        },
    }


# ---------------------------------------------------------------------------
# Legacy claims
# ---------------------------------------------------------------------------


def legacy_claims() -> list[dict[str, str]]:
    """Every quantitative claim of the frozen text, with phrase, status and key.

    Each `phrase` is checked verbatim (bold/backtick-stripped, whitespace
    normalised) against the frozen file at build time; a phrase that no longer
    matches fails the tool loudly. Status vocabulary: re-measured |
    withdrawn | not-reproducible.
    """
    return [
        {
            "id": "hdb-premium-128-core-table",
            "phrase": "$1.28 per 100m closer",
            "status": "not-reproducible",
            "ledgerKey": "responses.specifications.hdb-log-price-rich-controls",
            "note": (
                "the frozen text states no response unit for the $ figure (total "
                "price? PSF?) and no OLS output exists to re-derive it; the measured "
                "analogue is the recorded log-point slope per 100 m nearer on log "
                "total price (mrtCoefficient.logPointsPer100mNearer), direction "
                "consistent in sign, magnitude not comparable to an unstated-unit "
                "dollar figure"
            ),
        },
        {
            "id": "hdb-premium-128-technical",
            "phrase": "$1.28/100m (mean PSF $552)",
            "status": "not-reproducible",
            "ledgerKey": "responses.specifications.hdb-log-price-rich-controls",
            "note": (
                "same retired coefficient as the core-table figure; no artefact; a "
                "narrative archive record states a PSF basis for the condo variant, "
                "but no model output backs either number on the scanned surface"
            ),
        },
        {
            "id": "mean-hdb-psf-552",
            "phrase": "Mean HDB price PSF | $552",
            "status": "not-reproducible",
            "ledgerKey": "responses.specifications.hdb-log-price-rich-controls.sample.meanPsf",
            "note": (
                "the legacy's population and window for the mean are unstated; the "
                "measured window mean PSF on 2021-01 -> the cutoff is recorded at the "
                "key and is a different population, not a reproduction"
            ),
        },
        {
            "id": "ols-r2-052",
            "phrase": "OLS R² | 0.52",
            "status": "not-reproducible",
            "ledgerKey": "absenceScans.olsOutput",
            "note": (
                "no OLS artefact on the scanned surface; the same text also states "
                "'Full model R² = 0.4977', and the two figures cannot be reconciled "
                "from this checkout because neither has an artefact"
            ),
        },
        {
            "id": "town-row-central-area",
            "phrase": "Central Area | +$59.19 | $903 | 599",
            "status": "not-reproducible",
            "ledgerKey": "townDescriptives.legacyTable.rows.Central Area",
            "note": "retired town-level OLS output; window and population unstated; no artefact",
        },
        {
            "id": "town-row-serangoon",
            "phrase": "Serangoon | +$12.91 | $566 | 1,853",
            "status": "not-reproducible",
            "ledgerKey": "townDescriptives.legacyTable.rows.Serangoon",
            "note": "retired town-level OLS output; window and population unstated; no artefact",
        },
        {
            "id": "town-row-bishan",
            "phrase": "Bishan | +$5.88 | $644 | 1,951",
            "status": "not-reproducible",
            "ledgerKey": "townDescriptives.legacyTable.rows.Bishan",
            "note": "retired town-level OLS output; window and population unstated; no artefact",
        },
        {
            "id": "town-row-marine-parade",
            "phrase": "Marine Parade | -$38.54 | $629 | 515",
            "status": "not-reproducible",
            "ledgerKey": "townDescriptives.legacyTable.rows.Marine Parade",
            "note": (
                "retired town-level OLS output; the negative sign is one end of the "
                "unlabelled heterogeneity spread recorded at "
                "townDescriptives.legacyTable.signSpread"
            ),
        },
        {
            "id": "town-row-geylang",
            "phrase": "Geylang | -$20.54 | $584 | 2,054",
            "status": "not-reproducible",
            "ledgerKey": "townDescriptives.legacyTable.rows.Geylang",
            "note": "retired town-level OLS output; window and population unstated; no artefact",
        },
        {
            "id": "town-row-sengkang",
            "phrase": "Sengkang | -$16.88 | $558 | 7,585",
            "status": "not-reproducible",
            "ledgerKey": "townDescriptives.legacyTable.rows.Sengkang",
            "note": "retired town-level OLS output; window and population unstated; no artefact",
        },
        {
            "id": "condo-15x-table",
            "phrase": "roughly 15x higher than HDB",
            "status": "withdrawn",
            "ledgerKey": "responses.standardizedComparison",
            "note": (
                "withdrawn per the gate: a raw-coefficient multiple is banned "
                "marketing; the permitted replacement is the standardized-effect "
                "comparison recorded at the key, stated with non-comparability"
            ),
        },
        {
            "id": "condo-15x-technical",
            "phrase": "Condo MRT sensitivity ~15× HDB",
            "status": "withdrawn",
            "ledgerKey": "responses.standardizedComparison",
            "note": "same banned multiple in the technical findings; withdrawn",
        },
        {
            "id": "condo-15x-robustness",
            "phrase": "The ~15× condo-vs-HDB sensitivity gap is robust across OLS and XGBoost specifications",
            "status": "withdrawn",
            "ledgerKey": "responses.standardizedComparison",
            "note": (
                "'robust across specifications' cannot be assessed: neither model's "
                "outputs exist on the scanned surface, so there is nothing to be "
                "robust across; the claim is withdrawn, not contradicted"
            ),
        },
        {
            "id": "importance-table-core",
            "phrase": "Hawker within 1km | 27.4%",
            "status": "withdrawn",
            "ledgerKey": "absenceScans.shapImportance",
            "note": (
                "an importance ranking is an output of the retired XGBoost/SHAP "
                "model; no machine-readable artefact carries it (the scanned CSVs "
                "carry a different model at 0.02% for hawker), narrative prose "
                "matches are unlinked records, and no importance table is "
                "re-estimated here"
            ),
        },
        {
            "id": "importance-table-technical",
            "phrase": "hawker_within_1km = 27.4%, remaining_lease_months = 14.1%, park_within_1km = 7.2%, mrt_within_1km = 5.5%",
            "status": "withdrawn",
            "ledgerKey": "absenceScans.shapImportance",
            "note": "same retired-importance table in the technical findings; withdrawn",
        },
        {
            "id": "xgboost-spec",
            "phrase": "XGBoost (100 trees, max_depth=6, learning_rate=0.1) for non-linear patterns, with SHAP for explainability",
            "status": "withdrawn",
            "ledgerKey": "absenceScans.shapImportance",
            "note": (
                "the retired analysis scripts are not in the supported surface (the "
                "legacy text says so itself) and the model is not reproduced"
            ),
        },
        {
            "id": "sample-97133",
            "phrase": "97,133 HDB transactions, filtered to 2021 onward, with valid coordinates",
            "status": "not-reproducible",
            "ledgerKey": "studyWindow.legacySampleContrast",
            "note": (
                "the stated filter is re-measured on this checkout (both bounds "
                "recorded) and does not reproduce the stated count; the legacy's L3 "
                "input file and grid filter are absent, so the difference is "
                "unresolved — underspecified population, not-reproducible"
            ),
        },
        {
            "id": "h3-grid",
            "phrase": "Spatial grid: H3 hexagonal grid at resolution 8 (~0.5 km² cells), minimum 10 records per cell",
            "status": "not-reproducible",
            "ledgerKey": "absenceScans.h3Grid",
            "note": (
                "no H3 artefact on the scanned surface; the cell area and minimum "
                "are recorded as stated, not chosen, and cannot be re-derived here"
            ),
        },
        {
            "id": "cbd-reference-point",
            "phrase": "CBD reference point: (1.2839, 103.8513), haversine distance calculation",
            "status": "not-reproducible",
            "ledgerKey": "absenceScans.cbdDefinition.contentMatches",
            "note": (
                "the coordinate pair's content matches are the frozen text, its living "
                "copy, and a worked haversine example in a planning document "
                "(docs/plans/2026-01-24-spatial-analytics-overview.md, 2 matches); "
                "none of the three is a CBD definition asset; the CBD-distance term "
                "the legacy models rely on cannot be formed from the shipped schema "
                "(no CBD column; recorded check at inputs.unifiedDataset.cbdLikeColumnNames)"
            ),
        },
        {
            "id": "ols-controls",
            "phrase": "OLS LinearRegression controlling for dist_to_nearest_mrt, floor_area_sqm, remaining_lease_months",
            "status": "not-reproducible",
            "ledgerKey": "shippedMrtFeatures.missingnessStates.absentColumns",
            "note": (
                "the named control remaining_lease_months does not exist in the "
                "shipped schema (absent column; the file carries remaining_lease as "
                "a string and lease_commence_date as a year), so the legacy "
                "specification cannot be fitted as named; no OLS artefact exists either"
            ),
        },
        {
            "id": "hierarchical-r2",
            "phrase": "CBD-only model R² = 0.2263, CBD+MRT R² = 0.2341, ΔR² = +0.0078",
            "status": "not-reproducible",
            "ledgerKey": "absenceScans.olsOutput.contentMatches",
            "note": (
                "no hierarchical-regression output on the scanned surface; the three "
                "literals match only narrative texts quoting the legacy figures (the "
                "article copies and the findings summaries) plus two substring hits "
                "inside longer floats in an unrelated anomalies table; the delta is a "
                "predictive-increment narrative and is not re-derived"
            ),
        },
        {
            "id": "full-model-r2",
            "phrase": "Full model R² = 0.4977",
            "status": "not-reproducible",
            "ledgerKey": "absenceScans.olsOutput.contentMatches",
            "note": "no artefact; irreconcilable with the same text's 'OLS R² 0.52'",
        },
        {
            "id": "vif-correlation",
            "phrase": "moderate collinearity (~0.5-0.7 correlation), confirming they capture overlapping but distinct location effects",
            "status": "not-reproducible",
            "ledgerKey": "shippedMrtFeatures.missingnessStates.absentColumns",
            "note": (
                "the MRT-CBD correlation cannot be measured: the shipped dataset has "
                "no CBD-distance column (absent column; the recorded schema check at "
                "inputs.unifiedDataset.cbdLikeColumnNames is empty); 'confirming' is "
                "also causal-flavoured language the pack does not adopt"
            ),
        },
        {
            "id": "town-minimum-500",
            "phrase": "Town-level OLS used a minimum of 500 transactions per town",
            "status": "not-reproducible",
            "ledgerKey": "townDescriptives.windowCounts.townsAtLeast500Transactions",
            "note": (
                "method statement with no artefact; the descriptive analogue (window "
                "town counts against 500) is recorded at the key and is not the "
                "legacy's filter"
            ),
        },
        {
            "id": "interaction-terms",
            "phrase": "Cross-property comparison used interaction terms for property type × MRT distance",
            "status": "withdrawn",
            "ledgerKey": "responses.standardizedComparison",
            "note": (
                "the interaction model is the source of the banned multiple; it is "
                "not reproduced; the permitted replacement is the standardized "
                "comparison with its non-comparability statement"
            ),
        },
        {
            "id": "data-period-2021-2026",
            "phrase": "Data Period: 2021-2026",
            "status": "re-measured",
            "ledgerKey": "studyWindow",
            "note": (
                "coverage measured per segment: the condo source begins 2021-01; HDB "
                "rows exist from 1990-01 and every aggregation here stops at the "
                "measured cutoff, so '2026' holds only through lastCompleteMonth"
            ),
        },
        {
            "id": "town-variation-sign-spread",
            "phrase": "Town-level variation: Central Area +$59.19/100m, Marine Parade -$38.54/100m",
            "status": "not-reproducible",
            "ledgerKey": "townDescriptives.legacyTable.signSpread",
            "note": (
                "the two figures are retired OLS outputs; the spread between them is "
                "recorded as a field and labelled unexplained heterogeneity, per the "
                "gate's demand that the town table's sign spread not pass unlabelled"
            ),
        },
        {
            "id": "upgrader-300-500m",
            "phrase": "The same 300-500m difference carries different market value across segments",
            "status": "withdrawn",
            "ledgerKey": "responses.nonComparability",
            "note": (
                "'market value' across segments needs the retired cross-property "
                "model; the measured fragments (per-segment distance distributions "
                "and standardized associations, with non-comparability) do not "
                "support a cross-segment value claim and none is made"
            ),
        },
    ]


def _verify_legacy_quotes(claims: list[dict[str, str]]) -> dict[str, Any]:
    text = LEGACY_EDITION.read_text(encoding="utf-8")
    stripped = re.sub(r"\*\*|`", "", text)
    normalised = re.sub(r"\s+", " ", stripped)
    checked: list[dict[str, Any]] = []
    for claim in claims:
        phrase = re.sub(r"\s+", " ", re.sub(r"\*\*|`", "", claim["phrase"])).strip()
        checked.append(
            {
                "claim": claim["id"],
                "phrase": phrase,
                "foundInLegacyText": phrase in normalised,
                "occurrences": normalised.count(phrase),
            }
        )
    missing = [item for item in checked if not item["foundInLegacyText"]]
    if missing:
        raise SystemExit(
            "legacy phrase(s) not found verbatim in the frozen text: "
            + ", ".join(item["claim"] for item in missing)
        )
    return {
        "legacyFile": LEGACY_EDITION.relative_to(REPO_ROOT).as_posix(),
        "legacyFileSha256": sha256_of(LEGACY_EDITION),
        "legacyFileBytes": LEGACY_EDITION.stat().st_size,
        "legacyFileLines": len(text.splitlines()),
        "normalisation": "bold/backtick-stripped, whitespace-collapsed, substring match",
        "claimsChecked": len(claims),
        "phrasesVerifiedVerbatim": len(checked),
        "quotes": checked,
    }


def check_claim_keys(payload: dict[str, Any], claims: list[dict[str, str]]) -> dict[str, Any]:
    """Every claim's key must resolve, or the build fails.

    Resolution is syntactic: each `ledgerKey` is walked against this ledger
    (dict keys, list items by their `id`) at build time. It verifies the key
    points at a recorded field; it does not verify the field supports the
    claim. An unresolved key fails the build rather than shipping.
    """
    unresolved = [
        {"id": claim["id"], "ledgerKey": claim["ledgerKey"]}
        for claim in claims
        if not _resolve_ledger_path(payload, claim["ledgerKey"])
    ]
    if unresolved:
        raise SystemExit(
            "unresolved legacyClaims ledgerKey(s): "
            + ", ".join(f"{item['id']} -> {item['ledgerKey']}" for item in unresolved)
        )
    return {
        "claimsChecked": len(claims),
        "unresolved": [],
        "resolutionIsSyntactic": True,
        "method": (
            "each claim's ledgerKey is resolved against this ledger at build time by "
            "walking dict keys and list items by their `id`; an unresolved key fails "
            "the build. Resolution is syntactic: it confirms the key points at a "
            "recorded field, not that the field supports the claim's disposition."
        ),
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build() -> dict[str, Any]:
    register_text = REGISTER.read_text(encoding="utf-8")
    gate_line = next(
        (
            number
            for number, line in enumerate(register_text.splitlines(), start=1)
            if "RS07" in line
        ),
        None,
    )
    if gate_line is None or "Do not automatically unlock the MRT calculator" not in register_text:
        raise SystemExit("RS07 gate row not found in the research register; the citation is stale")
    gate_text_match = re.search(
        r"Confirm metres/km and total-price/log/PSF response\..*?Do not automatically "
        r"unlock the MRT calculator\.",
        register_text,
    )
    if not gate_text_match:
        raise SystemExit("the RS07 gate sentence no longer matches the register verbatim")

    frame_cols = [
        "month",
        "property_type",
        "is_ec",
        "town",
        "planning_area",
        "price",
        "psf",
        "floor_area_sqm",
        "lease_commence_date",
        "storey_min",
        "storey_max",
        "lat",
        "lon",
        "dist_to_nearest_mrt",
        "nearest_mrt_station",
        "nearest_mrt_tier",
        "nearest_mrt_is_interchange",
        "nearest_mrt_score",
    ]
    frame = pd.read_parquet(UNIFIED, columns=frame_cols)
    parquet = pq.ParquetFile(UNIFIED)
    schema = _unified_schema_checks(parquet)

    cutoff = measure_cutoff(frame)
    last_complete = cutoff["lastCompleteMonth"]
    legacy_rows = _parse_legacy_town_table(LEGACY_EDITION.read_text(encoding="utf-8"))
    responses_block = responses(frame, last_complete)
    scans = absence_scans()

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": "RS07 mrt-impact",
        "gate": {
            "registerPath": REGISTER.relative_to(REPO_ROOT).as_posix(),
            "registerLine": gate_line,
            "text": gate_text_match.group(0),
            "clauseDispositions": [
                {
                    "clause": "Confirm metres/km and total-price/log/PSF response.",
                    "addressedAt": [
                        "shippedMrtFeatures.units",
                        "calculatorLock.storedUnitsAsFound",
                        "responses.responseDefinition",
                    ],
                },
                {
                    "clause": (
                        "Compare standardized effects or state non-comparability; no raw "
                        "coefficient \u201c15\u00d7\u201d or \u201c4\u00d7\u201d marketing."
                    ),
                    "addressedAt": [
                        "responses.standardizedComparison",
                        "responses.nonComparability",
                        "legacyClaims (the three 15x claims are withdrawn)",
                    ],
                },
                {
                    "clause": "Separate predictive association from causation.",
                    "addressedAt": ["predictiveVsCausal"],
                },
                {
                    "clause": "Do not automatically unlock the MRT calculator.",
                    "addressedAt": ["calculatorLock"],
                },
            ],
            "note": (
                "no '4×' multiple appears in the frozen text; the ban is applied "
                "prospectively and no raw multiple between segments is stated anywhere "
                "in this ledger except as inventory of the unlinked calculator asset "
                "(calculatorAsset.internalArithmetic)"
            ),
        },
        "cutoff": cutoff,
        "inputs": {
            "unifiedDataset": {
                "path": UNIFIED.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(UNIFIED),
                "rows": int(parquet.metadata.num_rows),
                "columns": int(parquet.metadata.num_columns),
                **schema,
            },
            "rawMrtStations": {
                "path": RAW_MRT.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(RAW_MRT),
                "rows": int(pq.ParquetFile(RAW_MRT).metadata.num_rows),
                "columns": int(pq.ParquetFile(RAW_MRT).metadata.num_columns),
            },
            "calculatorAsset": {
                "path": CALCULATOR_ASSET.relative_to(REPO_ROOT).as_posix(),
                "sha256Gz": sha256_of(CALCULATOR_ASSET),
                "bytesGz": CALCULATOR_ASSET.stat().st_size,
            },
            "legacyEdition": {
                "path": LEGACY_EDITION.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(LEGACY_EDITION),
                "bytes": LEGACY_EDITION.stat().st_size,
            },
            "bronzeManifest": {
                "path": BRONZE_MANIFEST.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(BRONZE_MANIFEST),
                "bytes": BRONZE_MANIFEST.stat().st_size,
            },
            "seedStationsJson": {
                "path": SEED_STATIONS_JSON.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(SEED_STATIONS_JSON),
                "bytes": SEED_STATIONS_JSON.stat().st_size,
            },
            "seedMrtGeojson": {
                "path": RAW_MRT_GEOJSON.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(RAW_MRT_GEOJSON),
                "bytes": RAW_MRT_GEOJSON.stat().st_size,
            },
            "exitsGeojson": {
                "path": RAW_EXITS_GEOJSON.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(RAW_EXITS_GEOJSON),
                "bytes": RAW_EXITS_GEOJSON.stat().st_size,
            },
            "manualLinesMapping": {
                "path": MANUAL_LINES_MAPPING.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(MANUAL_LINES_MAPPING),
                "bytes": MANUAL_LINES_MAPPING.stat().st_size,
            },
            "manualStationsList": {
                "path": MANUAL_STATIONS_LIST.relative_to(REPO_ROOT).as_posix(),
                "sha256": sha256_of(MANUAL_STATIONS_LIST),
                "bytes": MANUAL_STATIONS_LIST.stat().st_size,
            },
            "importanceCsvs": [
                {
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "sha256": sha256_of(path),
                    "bytes": path.stat().st_size,
                }
                for path in sorted(IMPORTANCE_CSVS.glob("*.csv"))
            ],
            "note": (
                "every file read as data is sha-pinned here with its row/column "
                "measures where recorded, and every file whose bytes the absence "
                "scans read is sha-pinned at absenceScans.universe.scannedFiles "
                "(path, bytes, sha256; count at scannedFilesReadCount); files "
                "matched only at filename level are never read and are not inputs"
            ),
        },
        "studyWindow": study_window(frame, last_complete),
        "mrtStationsFrame": mrt_stations_frame(),
        "shippedMrtFeatures": shipped_mrt_features(frame, last_complete, schema),
        "calculatorAsset": calculator_asset(),
        "calculatorLock": calculator_lock(gate_line),
        "responses": responses_block,
        "predictiveVsCausal": predictive_vs_causal(),
        "townDescriptives": town_descriptives(frame, last_complete, legacy_rows),
        "absenceScans": scans,
    }
    claims = legacy_claims()
    payload["legacyClaims"] = claims
    payload["legacyQuoteCheck"] = _verify_legacy_quotes(claims)
    payload["claimKeyCheck"] = check_claim_keys(payload, claims)
    return payload


def check(output: Path) -> int:
    if not output.is_file():
        print(f"FAILED: no ledger at {output}; run the tool without --check first")
        return 1
    recorded = output.read_bytes()
    measured = canonical_bytes(build())
    if recorded == measured:
        print("Pass: RS07 ledger re-measures byte-identically from this checkout.")
        print(f"Ledger sha256: {hashlib.sha256(measured).hexdigest()}")
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
    print("FAILED: RS07 ledger does not match this checkout")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.check:
        return check(args.output)

    evidence = build()
    payload = canonical_bytes(evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)

    cutoff = evidence["cutoff"]
    print(
        f"Cutoff: last complete month {cutoff['lastCompleteMonth']} "
        f"(terminal {cutoff['terminalMonth']} at "
        f"{cutoff['terminalMonthShareOfTrailingMedian']} of the trailing median)"
    )
    for spec in evidence["responses"]["specifications"]:
        coefficient = spec["mrtCoefficient"]
        print(
            f"{spec['id']}: n={spec['fit']['n']} R2={spec['fit']['rSquared']} "
            f"beta/100m-nearer={coefficient['logPointsPer100mNearer']} log pts, "
            f"stdBeta={coefficient['standardizedBeta']}"
        )
    comparison = evidence["responses"]["standardizedComparison"]
    print(f"Standardized ratio condo/hdb (common controls): {comparison['ratioCondoOverHdb']}")
    statuses = Counter(claim["status"] for claim in evidence["legacyClaims"])
    print(
        "Legacy claims: "
        + str(evidence["claimKeyCheck"]["claimsChecked"])
        + " ("
        + ", ".join(f"{status}={count}" for status, count in sorted(statuses.items()))
        + ")"
    )
    quotes = evidence["legacyQuoteCheck"]
    print(f"Quote check: {quotes['phrasesVerifiedVerbatim']}/{quotes['claimsChecked']} verbatim")
    scans = evidence["absenceScans"]
    for name in ("stationDates", "shapImportance", "olsOutput", "h3Grid", "cbdDefinition"):
        print(f"Scan {name}: {scans[name]['matchedFileCount']} filename match(es)")
    print(f"Ledger bytes: {len(payload)}")
    print(f"Ledger sha256: {hashlib.sha256(payload).hexdigest()}")
    try:
        ledger_label = args.output.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        ledger_label = str(args.output)
    print(f"Ledger: {ledger_label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
