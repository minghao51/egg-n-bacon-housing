#!/usr/bin/env python3
"""Measure RS12's spatial-hotspots evidence: the rental population, its join to
the sale-side block geocodes, the re-measured Getis-Ord Gi* statistic on the
gate-pinned window, and what of the legacy method is recorded anywhere in this
checkout.

RS12's gate is "Retain January 2024-January 2025 as its own historical window.
Rerun the stated hotspot method, disclose persistence/instability and sample
changes. Keep rental hotspot results separate from the transaction-activity
product." This tool measures from the local checkout, and only what the
checkout can support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04/RS05/RS09/
   RS10 shipped (terminal month's count as a fraction of the trailing twelve-
   month median), computed on the rental file. The gate-pinned window
   (2024-01..2025-01) is recorded as a separate field set. All rental outcome
   aggregations, including the rent distribution, stop at the cutoff.
2. **Source schema** — the parquet schema of each input read via metadata
   before any column is claimed. The rental file has no coordinate columns;
   that absence is a schema fact, not a missing-value count.
3. **Population and join** — rental rows keyed on uppercased
   (block, street_name), joined to the distinct sale-side keys whose rows
   carry non-null lat/lon. The 11,637-key file population and the 11,500-key
   joinable population are counted separately, with the 137 keys whose every
   row carries null coordinates held apart as their own state. Unmatched rows
   are reported as a population (per-month counts, distinct keys, towns), not
   dropped.
4. **Hotspot statistic** — the stated method re-run on the joined window
   population: H3 resolution 8, median `monthly_rent` per cell, Getis-Ord Gi*
   (esda.getisord.G_Local, star=True, 99 permutations, seeded) over KNN k=8
   row-standardised weights, with a hex-adjacency sensitivity as the only
   realisable analogue of the legacy's unstated "Queen contiguity". Both esda
   z outputs (analytic Zs and simulation z_sim) are reported because the
   legacy does not state which one its thresholds apply to. Classification
   counts are reported per basis; the pack adjudicates none of them as "the"
   legacy reading.
5. **Named-area checks** — the six legacy areas measured against the window
   population: two have zero rows, four have town-level medians that differ
   from the legacy levels.
6. **Method recovery** — a bounded scan for a Gi* implementation, H3 cell
   tables and transition-probability artefacts, with roots, suffixes,
   exclusions, and every matched file listed with its count. Coincidental
   substring matches (e.g. `getIsSorted`, `missing_local`) are disclosed as
   such, and no unlinked artefact is used as evidence either way.
7. **Shipped-asset separation** — the transaction-activity product
   (`spatial_analysis.json.gz`, RS11's) is read read-only and token-scanned:
   zero rental tokens, zero legacy literals. This study's rental-only result
   is written to a NEW path; nothing is written into the sibling asset.
8. **Persistence** — the gate asks for persistence/instability to be
   disclosed. The checkout holds one period inside the gate-pinned window, no
   transition implementation and no transition artefact, so persistence is
   recorded as not measurable here, with the instability that IS measured
   (the two z bases' disagreement) stated as fields.

It never runs the pipeline, never writes outside `--output` and the one
rental-only asset, and never touches `data/pipeline/**`.

Usage:

    uv run python scripts/tools/spatial_hotspots_evidence.py \\
        --output docs/implementation/artifacts/rs12-spatial-hotspots-evidence.json

    uv run python scripts/tools/spatial_hotspots_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

warnings.filterwarnings("ignore")

import esda  # noqa: E402
import h3  # noqa: E402
import libpysal  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
RENTAL = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_hdb_rental.parquet"
GEOCODE = REPO_ROOT / "data" / "pipeline" / "02_silver" / "geocoded_validated.parquet"
LEGACY_EDITION = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "spatial-hotspots.md"
)
ANALYTICS_DIR = REPO_ROOT / "app" / "public" / "data" / "analytics"
SPATIAL_ANALYSIS_ASSET = ANALYTICS_DIR / "spatial_analysis.json.gz"
FEATURE_IMPACT_ASSET = ANALYTICS_DIR / "feature_impact.json.gz"
PREDICTIVE_ASSET = ANALYTICS_DIR / "predictive_analytics.json.gz"
RENTAL_ASSET = ANALYTICS_DIR / "rental_hotspots_2024-01_2025-01.json.gz"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs12-spatial-hotspots-evidence.json"
)

SCHEMA_VERSION = "1.0.0"
STUDY = "RS12"

GATE = (
    "Retain January 2024-January 2025 as its own historical window. Rerun the "
    "stated hotspot method, disclose persistence/instability and sample changes. "
    "Keep rental hotspot results separate from the transaction-activity product."
)

WINDOW_FIRST = "2024-01"
WINDOW_LAST = "2025-01"

# Method parameters. The legacy states H3 resolution 8, median monthly_rent per
# cell, Getis-Ord Gi* via esda.getisord.G_Local, KNN (k=8) and Queen
# contiguity, thresholds on z, and 99 permutations. It does NOT state: which z
# output the thresholds apply to, the weight transform, how Queen contiguity is
# realised for point/cell data, or what "sufficient data" floor a cell needs.
H3_RESOLUTION = 8
KNN_K = 8
PERMUTATIONS = 99
GI_STAR_SEED = 99
ANALYTIC_HOT_99 = 2.58
ANALYTIC_HOT_95 = 1.96
ANALYTIC_COLD_99 = -2.58
ANALYTIC_COLD_95 = -1.96
PSIM_FLOOR_EPSILON = 1e-9  # p_sim is float32 in esda; 1/(permutations+1) = 0.01

# The absence scan is bounded to these roots and suffixes so the ledger is
# reproducible file-order-independently and cannot read itself.
SCAN_ROOTS = (
    "docs",
    "scripts",
    "src",
    "assets",
    "app/src",
    "app/public",
    "data/analysis",
    "notebooks",
    "tests",
    ".claude",
)
SCAN_SUFFIXES = (".md", ".py", ".ts", ".tsx", ".json", ".csv", ".txt", ".ipynb")
# The programme's own output surfaces are excluded: `scripts/tools/` holds the
# evidence producers (this tool quotes every token it scans for),
# `docs/implementation/` holds the per-study records, `prompts/` holds handoffs
# and runbooks. Frozen legacy editions STAY IN the scan (their literals are what
# the token search is matched against); other edition directories are programme
# outputs signed after this study started and are excluded so a later edition
# cannot drift this ledger.
EXCLUDED_SCAN_PREFIXES = (
    "scripts/tools/",
    "prompts/",
    "docs/implementation/",
    "docs/analytics/editions/",
    "app/src/components/studies/",
    "app/tests/",
)
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
EXCLUDED_SCAN_PATHS = (
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
    ".secrets.baseline",
)

METHOD_TOKENS = (
    "getis",
    "g_local",
    "esda",
    "libpysal",
    "h3 resolution",
    "hotspot",
    "knn",
    "queen",
    "transition probabilit",
    "transition matrix",
    "persistence of hotspot",
)
LITERAL_TOKENS = (
    "847",
    "623",
    "4.21",
    "3.89",
    "3.45",
    "3.21",
    "2.98",
    "2.67",
    "3,200",
    "3,450",
    "3,100",
    "2,100",
    "2,050",
    "2,000",
    "1,850",
    "1,350",
    "2.58",
    "1.96",
    "58-62",
    "55-60",
    "8-10",
    "12 h3",
)
# Tokens scanned inside the decompressed shipped analytics assets, to measure
# the rental/transaction separation the gate requires.
SEPARATION_TOKENS = (
    "rental",
    "monthly_rent",
    "h3",
    "getis",
    "hotspot",
    "847",
    "623",
    "4.21",
    "3.45",
    "3.89",
    "3.21",
    "2.98",
    "2.67",
    "1,350",
    "2.58",
)

MAX_QUOTE = 140

STATUS_MEANING = {
    "re-measured": (
        "a number this pack recomputes from the checkout on the legacy's stated "
        "population; the note records agreement or disagreement — a re-measured "
        "status does NOT imply the legacy value was confirmed"
    ),
    "withdrawn": (
        "the claim's object does not exist in this checkout or population (no "
        "rows, no file at the stated path, no linked artefact), or the claim is "
        "advice/interpretation rather than a measurement, so it carries no "
        "measured value here"
    ),
    "not-reproducible": (
        "the legacy text underspecifies the statistic, population, window or "
        "floor needed to recompute it; measured candidate values, where any "
        "exist, are recorded as ledger fields and none is promoted to a "
        "replacement for the claim"
    ),
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def gz_bytes(payload: object) -> bytes:
    """Deterministic gzip: fixed mtime, sorted-key JSON, trailing newline."""
    raw = canonical_bytes(payload)
    return gzip.compress(raw, compresslevel=9, mtime=0)


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _r(value: Any, digits: int = 4) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not np.isfinite(number):
        return None
    return round(number, digits)


def _schema_of(path: Path) -> dict[str, Any]:
    """Column names and types from parquet metadata, before any read."""
    schema = pq.read_schema(path)
    md = pq.ParquetFile(path).metadata
    return {
        "path": _relative(path),
        "sha256": sha256_of(path),
        "bytes": int(path.stat().st_size),
        "rows": int(md.num_rows),
        "rowGroups": int(md.num_row_groups),
        "columns": [
            {"name": str(schema.field(i).name), "type": str(schema.field(i).type)}
            for i in range(len(schema.names))
        ],
    }


def cutoff(rental: Any) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial.

    Computed on the rental file's own monthly counts. All rental outcome
    aggregations are bounded at this month; source-file and geocode inventory
    counts describe their files rather than a rental outcome series.
    """
    counts = {str(k): int(v) for k, v in rental.groupby("rent_approval_date").size().items()}
    ordered = sorted(counts)
    terminal_month = ordered[-1]
    last_complete_month = ordered[-2]
    trailing_months = ordered[-13:-1]
    trailing = [counts[month] for month in trailing_months]
    trailing_median = float(np.median(trailing)) if trailing else 0.0
    ratio = counts[terminal_month] / trailing_median if trailing_median else None
    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact (the same rule RS03/RS04/"
            "RS05/RS09/RS10 shipped, computed here on the rental file's own "
            "monthly counts)"
        ),
        "lastCompleteMonth": last_complete_month,
        "terminalMonth": terminal_month,
        "terminalMonthTransactions": counts[terminal_month],
        "trailing12Months": trailing_months,
        "trailing12MedianTransactions": _r(trailing_median, 1),
        "terminalMonthShareOfTrailingMedian": _r(ratio),
        "lastCompleteMonthTransactions": counts[last_complete_month],
        "lastCompleteMonthShareOfTrailingMedian": _r(
            counts[last_complete_month] / trailing_median if trailing_median else None
        ),
        "fileFirstMonth": ordered[0],
        "fileLastMonth": terminal_month,
        "meaning": (
            "all rental outcome aggregations, including rentRangeObserved, "
            "stop at lastCompleteMonth. Source-file and sale-side geocode "
            "inventory counts describe their files, not rental outcome series. "
            "The gate-pinned window ends before the cutoff "
            "(see gateWindow.endsBeforeCutoff)."
        ),
    }


def gate_window(rental: Any, cutoff_fields: dict[str, Any]) -> dict[str, Any]:
    """The gate's own historical window, pinned by the gate, not by the cutoff."""
    dates = rental["rent_approval_date"].astype(str)
    mask = (dates >= WINDOW_FIRST) & (dates <= WINDOW_LAST)
    months = sorted(dates[mask].unique())
    return {
        "basis": "pinned by the RS12 gate text, not derived from the cutoff rule",
        "first": WINDOW_FIRST,
        "last": WINDOW_LAST,
        "months": months,
        "monthCount": len(months),
        "rowsInFile": int(mask.sum()),
        "endsBeforeCutoff": bool(WINDOW_LAST <= cutoff_fields["lastCompleteMonth"]),
        "cutoffLastCompleteMonth": cutoff_fields["lastCompleteMonth"],
        "meaning": (
            "the gate retains this window as its own historical window; the "
            "hotspot statistic below is measured on the rows the join can "
            "geocode inside it; all rental outcome aggregations remain bounded "
            "at lastCompleteMonth"
        ),
    }


def _join_keys(frame: pd.DataFrame, block: str, street: str) -> pd.DataFrame:
    out = frame.copy()
    out["kBlock"] = out[block].astype(str).str.strip().str.upper()
    out["kStreet"] = out[street].astype(str).str.strip().str.upper()
    return out


def populations(cutoff_fields: dict[str, Any]) -> dict[str, Any]:
    """Cutoff-bounded rental rollups and the geocode key populations."""
    rental_schema = _schema_of(RENTAL)
    rental: Any = pd.read_parquet(RENTAL)
    geocode_schema = _schema_of(GEOCODE)

    schema_column_names = [column["name"] for column in rental_schema["columns"]]
    bounded_rental = rental.loc[
        rental["rent_approval_date"].astype(str) <= cutoff_fields["lastCompleteMonth"]
    ]
    rent_series: Any = pd.to_numeric(
        bounded_rental["monthly_rent"].astype(str).str.strip(), errors="coerce"
    )
    non_numeric_rent = int(rent_series.isna().sum())
    rent = rent_series.dropna()

    geocode: Any = pd.read_parquet(
        GEOCODE, columns=["block", "street_name", "lat", "lon", "property_type"]
    )
    lat_null = int(geocode["lat"].isna().sum())
    lon_null = int(geocode["lon"].isna().sum())
    both_null = int((geocode["lat"].isna() & geocode["lon"].isna()).sum())
    exactly_one_null = int((geocode["lat"].isna() ^ geocode["lon"].isna()).sum())
    keyed = _join_keys(geocode, "block", "street_name")
    all_keys = keyed[["kBlock", "kStreet"]].drop_duplicates()
    joinable = keyed.loc[keyed["lat"].notna() & keyed["lon"].notna(), ["kBlock", "kStreet"]]
    joinable_keys = joinable.drop_duplicates()
    keys_with_coords = set(map(tuple, joinable_keys.values))
    keys_all_rows_null = {
        key for key in set(map(tuple, all_keys.values)) if key not in keys_with_coords
    }

    rental_states = {
        "throughMonth": cutoff_fields["lastCompleteMonth"],
        "nullValuesPerColumn": {
            column: int(bounded_rental[column].isna().sum()) for column in rental.columns
        },
        "recordedZeroRents": int((rent == 0).sum()),
        "nonNumericRentStrings": non_numeric_rent,
        "absentColumns": {
            "coordinateColumnsInRentalFile": [
                name
                for name in ("lat", "lon", "latitude", "longitude")
                if name not in schema_column_names
            ],
            "searchResultColumnInGeocodeTable": bool(
                "search_result" in geocode_schema["columns"]
                or "search_result" in [c["name"] for c in geocode_schema["columns"]]
            ),
        },
        "meaning": (
            "four missingness states kept apart: a null value (per-column null "
            "counts, all zero through the cutoff), a recorded zero (rent == 0 "
            "rows), an absent row (the unmatched rows at joinMeasure), and an "
            "absent column (no coordinate column in the 7-column rental schema; "
            "no search_result column in the geocode schema). A file-row count "
            "describes the file, not a series"
        ),
    }

    return {
        "rentalSchema": rental_schema,
        "geocodeSchema": geocode_schema,
        "rentalPopulation": {
            "rows": int(len(rental)),
            "distinctKeysThroughCutoff": int(
                _join_keys(bounded_rental, "block", "street_name")[["kBlock", "kStreet"]]
                .drop_duplicates()
                .shape[0]
            ),
            "distinctTownsThroughCutoff": int(bounded_rental["town"].nunique()),
            "monthRange": {
                "first": str(rental["rent_approval_date"].min()),
                "last": str(rental["rent_approval_date"].max()),
                "meaning": "source-file month bounds; not an outcome aggregation",
            },
            "rentRangeObserved": {
                "throughMonth": cutoff_fields["lastCompleteMonth"],
                "min": float(rent.min()),
                "max": float(rent.max()),
                "median": float(rent.median()),
                "p01": float(np.percentile(rent, 1)),
                "p99": float(np.percentile(rent, 99)),
                "meaning": (
                    "the observed monthly_rent distribution through "
                    f"{cutoff_fields['lastCompleteMonth']}; all reported "
                    "statistics stop at lastCompleteMonth"
                ),
            },
            "missingnessStates": rental_states,
        },
        "geocodePopulation": {
            "rows": int(len(geocode)),
            "distinctKeysAllRows": int(len(all_keys)),
            "distinctKeysJoinable": int(len(joinable_keys)),
            "distinctKeysEveryRowNullCoordinates": int(len(keys_all_rows_null)),
            "rowsNullLatAndLon": both_null,
            "rowsNullLatOnly": int(lat_null - both_null),
            "rowsNullLonOnly": int(lon_null - both_null),
            "rowsExactlyOneCoordinateNull": exactly_one_null,
            "propertyTypeCounts": {
                str(k): int(v)
                for k, v in geocode["property_type"].value_counts(dropna=False).items()
            },
            "keyIdentity": (
                "uppercased (block, street_name); 11,637-style file counts and "
                "joinable counts are different populations and are never summed "
                "or averaged"
            ),
        },
    }


def join_measure(cutoff_fields: dict[str, Any]) -> dict[str, Any]:
    """The measured join on the gate window and rental rows through cutoff."""
    rental = pd.read_parquet(RENTAL)
    geocode = pd.read_parquet(GEOCODE, columns=["block", "street_name", "lat", "lon"])
    geo_keys = _join_keys(geocode, "block", "street_name")
    geo_keys = geo_keys.loc[
        geo_keys["lat"].notna() & geo_keys["lon"].notna(), ["kBlock", "kStreet", "lat", "lon"]
    ].drop_duplicates()

    rental_keys = _join_keys(rental, "block", "street_name")
    rental_keys["rent"] = pd.to_numeric(
        rental_keys["monthly_rent"].astype(str).str.strip(), errors="raise"
    )
    dates = rental_keys["rent_approval_date"].astype(str)
    cutoff_mask = dates <= cutoff_fields["lastCompleteMonth"]
    window_mask = (dates >= WINDOW_FIRST) & (dates <= WINDOW_LAST)

    def _join(mask: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
        rows = rental_keys.loc[mask]
        joined = rows.merge(geo_keys, on=["kBlock", "kStreet"], how="left", indicator=True)
        matched = joined[joined["_merge"] == "both"].drop(columns=["_merge"]).reset_index(drop=True)
        unmatched = (
            joined[joined["_merge"] == "left_only"].drop(columns=["_merge"]).reset_index(drop=True)
        )
        return matched, unmatched

    win_matched, win_unmatched = _join(window_mask)
    cutoff_matched, cutoff_unmatched = _join(cutoff_mask)

    match_share_window = (
        len(win_matched) / len(rental_keys.loc[window_mask])
        if len(rental_keys.loc[window_mask])
        else None
    )
    match_share_cutoff = (
        len(cutoff_matched) / int(cutoff_mask.sum()) if int(cutoff_mask.sum()) else None
    )

    unmatched_by_month = {
        str(k): int(v) for k, v in win_unmatched.groupby("rent_approval_date").size().items()
    }
    unmatched_towns = sorted(str(t) for t in win_unmatched["town"].unique())
    unmatched_keys = win_unmatched[["kBlock", "kStreet"]].drop_duplicates()

    return {
        "keyDefinition": "uppercased (block, street_name) on both sides; one geocode row per key (drop_duplicates)",
        "window": {
            "rowsInFile": int(window_mask.sum()),
            "matchedRows": int(len(win_matched)),
            "unmatchedRows": int(len(win_unmatched)),
            "matchShare": _r(match_share_window, 6),
            "joinedRentMedian": float(win_matched["rent"].median()),
            "joinedRentP01": float(np.percentile(win_matched["rent"], 1)),
            "joinedRentP99": float(np.percentile(win_matched["rent"], 99)),
            "joinedDistinctTowns": int(win_matched["town"].nunique()),
        },
        "throughCutoff": {
            "lastCompleteMonth": cutoff_fields["lastCompleteMonth"],
            "rowsInFile": int(cutoff_mask.sum()),
            "matchedRows": int(len(cutoff_matched)),
            "unmatchedRows": int(len(cutoff_unmatched)),
            "matchShare": _r(match_share_cutoff, 6),
        },
        "unmatchedPopulation": {
            "disclosure": (
                "the unmatched rows are reported as a population, not dropped "
                "silently; they are excluded from the hotspot statistic because "
                "they carry no coordinates in this checkout"
            ),
            "windowRows": int(len(win_unmatched)),
            "windowDistinctKeys": int(len(unmatched_keys)),
            "windowTowns": unmatched_towns,
            "windowRowsByMonth": unmatched_by_month,
            "throughCutoffRows": int(len(cutoff_unmatched)),
        },
        "matchedWindow": win_matched,
    }


def hotspot_statistic(matched: Any) -> dict[str, Any]:
    """The stated method re-run on the joined window population.

    H3 resolution 8 cells, median monthly_rent per cell, Getis-Ord Gi* with
    99 seeded permutations over KNN k=8 row-standardised weights, plus a
    hex-adjacency sensitivity (the only realisable analogue of the legacy's
    unstated Queen contiguity on cell data). Both esda z outputs are reported;
    the legacy does not state which one its thresholds apply to, so this pack
    adjudicates neither as "the" legacy reading.
    """
    if matched.empty:
        raise SystemExit("empty joined window population; the statistic cannot be measured")
    rows = matched.copy()
    rows["cell"] = [
        h3.latlng_to_cell(la, lo, H3_RESOLUTION) for la, lo in zip(rows["lat"], rows["lon"])
    ]

    def _dominant_town(series: Any) -> str:
        counts: Any = series.value_counts()
        top: Any = counts[counts == counts.max()]
        return str(sorted(top.index.astype(str))[0])

    grouped = rows.groupby("cell")
    cells: Any = grouped["rent"].agg(median="median", n="size").reset_index()
    cells["town"] = cells["cell"].map(grouped["town"].agg(_dominant_town))
    cells = cells.sort_values("cell").reset_index(drop=True)
    cells["median"] = cells["median"].astype(float)

    cell_counts = {
        "totalCells": int(len(cells)),
        "cellsOneRow": int((cells["n"] == 1).sum()),
        "cellsAtLeast2Rows": int((cells["n"] >= 2).sum()),
        "cellsAtLeast3Rows": int((cells["n"] >= 3).sum()),
        "cellsAtLeast5Rows": int((cells["n"] >= 5).sum()),
        "cellsAtLeast10Rows": int((cells["n"] >= 10).sum()),
        "fullFileCellsDisclosure": (
            "the legacy's 'sufficient data' floor is unstated (recorded as "
            "underspecified); the floors above are measured candidates, none "
            "promoted to the legacy reading"
        ),
    }

    values = cells["median"].to_numpy(dtype=float)
    centroids = np.array([h3.cell_to_latlng(c) for c in cells["cell"]])

    w_knn = libpysal.weights.KNN.from_array(centroids, k=KNN_K)
    w_knn.transform = "R"
    lg = esda.G_Local(
        values,
        w_knn,
        star=True,
        permutations=PERMUTATIONS,
        seed=GI_STAR_SEED,
        n_jobs=1,
    )
    zs = np.asarray(lg.Zs, dtype=float)
    z_sim = np.asarray(lg.z_sim, dtype=float)
    p_sim = np.asarray(lg.p_sim, dtype=float)

    analytic = {
        "maxZ": _r(zs.max()),
        "minZ": _r(zs.min()),
        "cellsAbove99": int((zs > ANALYTIC_HOT_99).sum()),
        "cellsAbove95": int((zs > ANALYTIC_HOT_95).sum()),
        "cellsBelowCold99": int((zs < ANALYTIC_COLD_99).sum()),
        "cellsBelowCold95": int((zs < ANALYTIC_COLD_95).sum()),
        "nonFinite": int((~np.isfinite(zs)).sum()),
    }
    simulation = {
        "maxZ": _r(np.nanmax(z_sim)),
        "minZ": _r(np.nanmin(z_sim)),
        "nonFinite": int((~np.isfinite(z_sim)).sum()),
        "cellsAbove99": int((z_sim > ANALYTIC_HOT_99).sum()),
        "cellsAbove95": int((z_sim > ANALYTIC_HOT_95).sum()),
        "cellsBelowCold99": int((z_sim < ANALYTIC_COLD_99).sum()),
        "cellsBelowCold95": int((z_sim < ANALYTIC_COLD_95).sum()),
    }
    p_floor = 1.0 / (PERMUTATIONS + 1)
    p_hot = (p_sim <= p_floor + PSIM_FLOOR_EPSILON) & (zs > 0)
    p_cold = (p_sim <= p_floor + PSIM_FLOOR_EPSILON) & (zs < 0)
    p_sim_floor = {
        "floor": _r(p_floor, 6),
        "semantics": (
            "esda G_Local p_sim is the smaller of the two permutation tails "
            "with a +1 correction (larger = sims >= G, flipped when the lower "
            "tail is smaller; p_sim = (larger+1)/(permutations+1)); with 99 "
            "permutations its floor is 1/100 = 0.01, so '99% confidence' maps "
            "to p_sim <= 0.01 and nothing smaller is attainable"
        ),
        "cellsAtFloorHotDirection": int(p_hot.sum()),
        "cellsAtFloorColdDirection": int(p_cold.sum()),
        "cellsAtFloorTotal": int((p_sim <= p_floor + PSIM_FLOOR_EPSILON).sum()),
    }

    def _cell_fields(index: int) -> dict[str, Any]:
        return {
            "cell": str(cells.loc[index, "cell"]),
            "town": str(cells.loc[index, "town"]),
            "rows": int(cells.loc[index, "n"]),
            "medianMonthlyRent": _r(cells.loc[index, "median"], 2),
            "analyticZ": _r(zs[index]),
            "simulationZ": _r(z_sim[index]),
            "pSim": _r(p_sim[index], 6),
        }

    top_order = list(np.argsort(-zs))[:10]
    bottom_order = list(np.argsort(zs))[-10:][::-1]
    hot_sim_indices = [int(i) for i in np.where(z_sim > ANALYTIC_HOT_99)[0]]
    cold_sim_indices = [int(i) for i in np.where(z_sim < ANALYTIC_COLD_99)[0]]
    hot_sim_medians = cells.loc[hot_sim_indices, "median"].to_numpy(dtype=float)
    cold_sim_medians = cells.loc[cold_sim_indices, "median"].to_numpy(dtype=float)
    candidate_hot_median_of_medians = (
        float(np.median(hot_sim_medians)) if hot_sim_medians.size else None
    )
    candidate_cold_median_of_medians = (
        float(np.median(cold_sim_medians)) if cold_sim_medians.size else None
    )

    extremes = {
        "topCellsByAnalyticZ": [_cell_fields(int(i)) for i in top_order],
        "bottomCellsByAnalyticZ": [_cell_fields(int(i)) for i in bottom_order],
        "simulationHot99Cells": [_cell_fields(i) for i in hot_sim_indices],
        "simulationCold99Cells": [_cell_fields(i) for i in cold_sim_indices],
        "candidateRentLevels": {
            "basis": (
                "candidate values under the SIMULATION-z reading only; under the "
                "analytic reading no cell passes any legacy threshold, so no "
                "hot/cold population exists. These candidates are recorded "
                "because the legacy's own hotspot/coldspot populations are "
                "undefined (its threshold basis is unstated); none is promoted "
                "to a replacement for the legacy levels"
            ),
            "hotMedianOfMedians": candidate_hot_median_of_medians,
            "coldMedianOfMedians": candidate_cold_median_of_medians,
            "candidateGap": (
                _r(candidate_hot_median_of_medians - candidate_cold_median_of_medians, 2)
                if candidate_hot_median_of_medians is not None
                and candidate_cold_median_of_medians is not None
                else None
            ),
        },
    }

    # Hex-adjacency sensitivity: the H3 k-ring analogue of the legacy's
    # unstated "Queen contiguity", under both transforms esda exposes.
    index_of = {cell: i for i, cell in enumerate(cells["cell"])}
    neighbours = {
        i: [index_of[n] for n in h3.grid_disk(cell, 1) if n != cell and n in index_of]
        for i, cell in enumerate(cells["cell"])
    }
    islands = int(sum(1 for ns in neighbours.values() if len(ns) == 0))
    hex_sensitivity: dict[str, Any] = {
        "realisation": (
            "H3 k-ring-1 adjacency (hex neighbours); the legacy says 'Queen "
            "contiguity' without stating how it was realised for cell data, so "
            "this analogue is recorded as THIS PACK's choice, not a recovery "
            "of the legacy's weights"
        ),
        "islands": islands,
        "rowStandardised": {},
        "binary": {},
    }
    w_hex_r = libpysal.weights.W(neighbours)
    w_hex_r.transform = "R"
    lg_hex_r = esda.G_Local(
        values, w_hex_r, star=True, permutations=PERMUTATIONS, seed=GI_STAR_SEED, n_jobs=1
    )
    zs_hex_r = np.asarray(lg_hex_r.Zs, dtype=float)
    vg_hex_r = np.asarray(lg_hex_r.VGs, dtype=float)
    hex_sensitivity["rowStandardised"] = {
        "degenerate": True,
        "varianceMax": _r(np.nanmax(vg_hex_r), 12),
        "varianceZeroCells": int((vg_hex_r == 0).sum()),
        "nonFiniteZ": int((~np.isfinite(zs_hex_r)).sum()),
        "note": (
            "row-standardised hex weights produce an analytic variance that "
            "collapses toward zero (max ~1.7e-07 measured at varianceMax) with "
            "exact zeros on the island cells, so the analytic z is unusable "
            "under this transform; recorded as a measured degeneracy of the "
            "analogue, not as evidence about the legacy's own run"
        ),
    }
    w_hex_b = libpysal.weights.W(neighbours)
    w_hex_b.transform = "B"
    lg_hex_b = esda.G_Local(
        values, w_hex_b, star=True, permutations=PERMUTATIONS, seed=GI_STAR_SEED, n_jobs=1
    )
    zs_hex_b = np.asarray(lg_hex_b.Zs, dtype=float)
    hex_sensitivity["binary"] = {
        "degenerate": False,
        "maxZ": _r(zs_hex_b.max()),
        "minZ": _r(zs_hex_b.min()),
        "cellsAbove99": int((zs_hex_b > ANALYTIC_HOT_99).sum()),
        "cellsAbove95": int((zs_hex_b > ANALYTIC_HOT_95).sum()),
        "cellsBelowCold99": int((zs_hex_b < ANALYTIC_COLD_99).sum()),
        "cellsBelowCold95": int((zs_hex_b < ANALYTIC_COLD_95).sum()),
    }

    knn_components = w_knn.n_components
    return {
        "method": {
            "h3Resolution": H3_RESOLUTION,
            "cellValue": "median monthly_rent per cell, unadjusted for flat-type mix (the legacy states no adjustment)",
            "statistic": "esda.getisord.G_Local(star=True) — Gi* (self-cell included)",
            "permutations": PERMUTATIONS,
            "seed": GI_STAR_SEED,
            "nJobs": 1,
            "primaryWeights": f"KNN k={KNN_K} on H3 cell centroids (lat/lon degrees), row-standardised (esda default transform='R')",
            "starInference": (
                "esda infers the Gi* self-weight as the maximum weight in each "
                "row when the diagonal is empty; recorded because the legacy "
                "does not state a self-weight convention"
            ),
            "thresholds": {
                "hotspot99": ANALYTIC_HOT_99,
                "weakHotspot95": ANALYTIC_HOT_95,
                "coldspot99": ANALYTIC_COLD_99,
                "weakColdspot95": ANALYTIC_COLD_95,
            },
            "thresholdBasis": (
                "the legacy applies its thresholds to 'z' without stating which "
                "z output; both esda outputs (analytic Zs and simulation z_sim) "
                "are reported and neither is adjudicated as the legacy reading"
            ),
            "knnGraphComponents": int(knn_components),
            "libraryVersions": {
                "h3": str(h3.__version__),
                "libpysal": str(libpysal.__version__),
                "esda": str(esda.__version__),
                "numpy": str(np.__version__),
                "pandas": str(pd.__version__),
            },
            "flatTypeMixWindowRows": {
                str(k): int(v) for k, v in rows["flat_type"].value_counts().items()
            },
        },
        "cellCounts": cell_counts,
        "analyticZ": analytic,
        "simulationZ": simulation,
        "pSimFloor": p_sim_floor,
        "hexAdjacencySensitivity": hex_sensitivity,
        "extremes": extremes,
        "persistenceDisclosure": {
            "periodsInsideGateWindow": 1,
            "transitionImplementationFound": False,
            "transitionArtefactFound": False,
            "meaning": (
                "the gate asks for persistence/instability to be disclosed. The "
                "gate pins ONE historical window, so this pack measures one "
                "period and no transition can be computed from it; the scan at "
                "methodRecovery.transitionProbabilities found no implementation "
                "and no artefact. The instability that IS measured is the "
                "disagreement between the two z bases (analyticZ vs "
                "simulationZ), which is recorded as fields, not as a "
                "persistence estimate"
            ),
        },
        "cellsTable": [
            {
                "cell": str(row.cell),
                "town": str(row.town),
                "rows": int(row.n),
                "medianMonthlyRent": _r(row.median, 2),
                "analyticZ": _r(zs[i]),
                "simulationZ": _r(z_sim[i]),
                "pSim": _r(p_sim[i], 6),
            }
            for i, row in enumerate(cells.itertuples(index=False))
        ],
    }


def town_medians(matched: pd.DataFrame) -> dict[str, Any]:
    """Window town-level medians — the only well-defined 'area' reading."""
    grouped: Any = matched.groupby("town")["rent"].agg(median="median", rows="size")
    ordered = grouped.sort_values(by="median", ascending=False)
    table = {
        str(town): {"median": _r(row["median"], 2), "rows": int(row["rows"])}
        for town, row in ordered.iterrows()
    }
    return {
        "basis": (
            "town is the only area column the rental population carries; the "
            "legacy names areas without defining them, so the town-level "
            "median is a candidate reading and is not promoted to 'the' "
            "legacy area value"
        ),
        "windowByTown": table,
        "townCount": len(table),
    }


def legacy_area_checks(town_medians_fields: dict[str, Any]) -> dict[str, Any]:
    """The six legacy-named areas against the measured window population."""
    by_town = town_medians_fields["windowByTown"]

    def _town(name: str) -> dict[str, Any] | None:
        return by_town.get(name)

    bukit_timah = _town("BUKIT TIMAH")
    woodlands = _town("WOODLANDS")
    yishun = _town("YISHUN")
    sembawang = _town("SEMBAWANG")
    return {
        "orchard": {
            "exactTownRows": 0,
            "townAbsentFromPopulation": True,
            "streetSubstringRows": 0,
            "meaning": (
                "'Orchard' appears zero times as a town value and zero times as "
                "a street-name substring in the joined window population; a "
                "median over an empty population cannot be produced, and no "
                "artefact in this checkout carries the claimed Gi* value"
            ),
        },
        "marinaSouth": {
            "exactTownRows": 0,
            "townAbsentFromPopulation": True,
            "streetSubstringRows": 0,
            "meaning": (
                "'Marina South' appears zero times as a town value and zero "
                "times as a street-name substring in the joined window "
                "population; same non-derivability as Orchard"
            ),
        },
        "bukitTimah": {
            "townMedian": bukit_timah["median"] if bukit_timah else None,
            "rows": bukit_timah["rows"] if bukit_timah else 0,
            "meaning": (
                "the town exists in the population; its measured window median "
                "is at townMedians.windowByTown.BUKIT TIMAH and differs from "
                "the legacy's stated level; the claimed Gi* value has no "
                "artefact and the legacy defines no area boundary that would "
                "reproduce it"
            ),
        },
        "woodlands": {
            "townMedian": woodlands["median"] if woodlands else None,
            "rows": woodlands["rows"] if woodlands else 0,
            "meaning": (
                "the town exists; the measured window median differs from the "
                "legacy's coldspot level; the claimed Gi* value has no "
                "artefact and the measured analytic z minimum never reaches it"
            ),
        },
        "yishun": {
            "townMedian": yishun["median"] if yishun else None,
            "rows": yishun["rows"] if yishun else 0,
            "meaning": "same shape as Woodlands, at townMedians.windowByTown.YISHUN",
        },
        "sembawang": {
            "townMedian": sembawang["median"] if sembawang else None,
            "rows": sembawang["rows"] if sembawang else 0,
            "meaning": "same shape as Woodlands, at townMedians.windowByTown.SEMBAWANG",
        },
        "townsAbsentFromPopulation": ["ORCHARD", "MARINA SOUTH"],
        "fileTownsNotInJoinedWindow": sorted(
            set(str(t) for t in pd.read_parquet(RENTAL, columns=["town"])["town"].unique())
            - set(by_town)
        ),
    }


def _scan_files() -> list[Path]:
    paths: list[Path] = []
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            relative = _relative(path)
            if relative.startswith(RETAINED_EDITION_PREFIX):
                pass
            elif any(relative.startswith(prefix) for prefix in EXCLUDED_SCAN_PREFIXES):
                continue
            if relative.startswith(EDITIONS_SKIP) and not relative.startswith(
                RETAINED_EDITION_PREFIX
            ):
                continue
            if relative in EXCLUDED_SCAN_PATHS:
                continue
            paths.append(path)
    return sorted(paths)


EDITIONS_SKIP = "docs/analytics/editions/"


def method_recovery(paths: list[Path]) -> dict[str, Any]:
    """The bounded absence scan: implementation, cell tables, transitions.

    Every matched file is listed with its count. A token match is a string
    occurrence, not a finding about origin: coincidental substrings
    (`getIsSorted`, `missing_local`, `FINANCING_LOCAL_NOTE`), UI/catalog
    description strings for the transaction-side product, and documentation
    prose are all disclosed below, and none is treated as evidence for or
    against the legacy numbers.
    """

    # Decode each file ONCE; count every token against the cached text.
    texts: dict[Path, str] = {}
    lines: dict[Path, list[str]] = {}
    for path in paths:
        decoded = path.read_bytes().decode("utf-8", errors="replace")
        texts[path] = decoded.lower()
        lines[path] = decoded.splitlines()

    token_report: dict[str, Any] = {}
    for token in METHOD_TOKENS + LITERAL_TOKENS:
        matches: list[dict[str, Any]] = []
        for path in paths:
            count = texts[path].count(token)
            if count:
                first_line = next(
                    (line for line in lines[path] if token in line.lower()),
                    "",
                )
                matches.append(
                    {
                        "path": _relative(path),
                        "occurrences": int(count),
                        "firstQuote": first_line.strip()[:MAX_QUOTE],
                    }
                )
        token_report[token] = {
            "occurrences": int(sum(m["occurrences"] for m in matches)),
            "files": len(matches),
            "matchedFiles": matches,
        }

    screened_substrings = {
        "getIsSorted": "TanStack table API method; contains 'getis' as a substring",
        "missing_local": "sync-script counter; contains 'g_local' as a substring",
        "FINANCING_LOCAL_NOTE": "financing-tool constant; contains 'g_local' as a substring",
        "app/src/types/analytics.ts 'Getis-Ord Gi* z-scores...'": (
            "a UI description string for the transaction-side spatial product; "
            "a label, not an implementation"
        ),
    }

    return {
        "scan": {
            "roots": list(SCAN_ROOTS),
            "suffixes": list(SCAN_SUFFIXES),
            "filesScanned": len(paths),
            "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
            "retainedEditionPrefix": RETAINED_EDITION_PREFIX,
            "retainedEditionNote": (
                "frozen legacy editions stay IN the scan (their literals are "
                "what the token search is matched against); every other "
                "docs/analytics/editions/ path is excluded as programme output "
                "signed after this study started"
            ),
            "excludedPaths": list(EXCLUDED_SCAN_PATHS),
            "selfExclusion": (
                "this tool lives under scripts/tools/ and quotes every token it "
                "scans for; the prefix exclusion keeps the ledger out of its "
                "own evidence; app/src/components/studies/ (edition "
                "registry/pages) and app/tests/ (fixtures) are programme "
                "outputs; .secrets.baseline and "
                "docs/plans/2026-11-12-reporting-refresh-decisions.md (D12 "
                "register) are explicitly excluded"
            ),
            "method": (
                "case-insensitive substring count per file; every matched file "
                "is listed with its count and first matching line. A match is "
                "a string occurrence, not a finding about origin"
            ),
        },
        "tokens": token_report,
        "screenedAsCoincidental": screened_substrings,
        "giStarImplementation": {
            "conclusion": (
                "screened as absent: zero occurrences of 'getis', 'g_local', "
                "'esda' or 'libpysal' as code in any scanned .py/.ts/.tsx file; "
                "every token occurrence is a coincidental substring, a UI "
                "label, or documentation prose (see tokens.*.matchedFiles and "
                "screenedAsCoincidental). Origin of the legacy values remains "
                "unverified — no artefact is linked to them in either direction"
            ),
        },
        "h3CellTables": {
            "conclusion": (
                "screened as absent: no cell-level H3 table exists in the "
                "scanned roots; the only 'h3 resolution' occurrences are the "
                "frozen legacy text, plan documents, and this ledger's own "
                "excluded surfaces. The shipped analytics assets carry zero "
                "'h3' tokens (shippedAssetSeparation)"
            ),
        },
        "transitionProbabilities": {
            "conclusion": (
                "screened as absent: 'transition probabilit' occurs once in the "
                "scan scope (the frozen legacy text itself), 'transition "
                "matrix' zero times; no implementation and no stored "
                "probability table exists in this checkout, and the gate pins "
                "one period, so no persistence estimate is measurable here"
            ),
        },
    }


def shipped_asset_separation() -> dict[str, Any]:
    """The transaction-activity product, read read-only, and the new asset.

    The gate's separation clause is measured in both directions: the sibling
    transaction asset carries zero rental tokens (screened as: its decompressed
    text contains none), and this study's rental-only result is written to a
    NEW path — nothing is written into the sibling asset.
    """
    assets: dict[str, Any] = {}
    for path in (SPATIAL_ANALYSIS_ASSET, FEATURE_IMPACT_ASSET, PREDICTIVE_ASSET):
        raw = gzip.decompress(path.read_bytes()).decode("utf-8")
        lowered = raw.lower()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise SystemExit(f"{_relative(path)} is not valid JSON: {error}") from error
        assets[_relative(path)] = {
            "sha256": sha256_of(path),
            "bytes": int(path.stat().st_size),
            "decompressedBytes": len(raw),
            "topLevelKeys": list(payload.keys()) if isinstance(payload, dict) else None,
            "tokenCounts": {token: int(lowered.count(token)) for token in SEPARATION_TOKENS},
        }
    spatial = assets[_relative(SPATIAL_ANALYSIS_ASSET)]
    return {
        "spatialAnalysis": {
            "path": _relative(SPATIAL_ANALYSIS_ASSET),
            "sha256": spatial["sha256"],
            "bytes": spatial["bytes"],
            "role": (
                "RS11's transaction-activity product; this study reads it "
                "read-only and writes nothing into it"
            ),
            "rentalTokens": {
                "rental": spatial["tokenCounts"]["rental"],
                "monthly_rent": spatial["tokenCounts"]["monthly_rent"],
            },
            "legacyLiteralTokens": {
                token: spatial["tokenCounts"][token]
                for token in (
                    "847",
                    "623",
                    "4.21",
                    "3.45",
                    "3.89",
                    "3.21",
                    "2.98",
                    "2.67",
                    "1,350",
                    "2.58",
                )
            },
            "getisToken": spatial["tokenCounts"]["getis"],
            "hotspotToken": spatial["tokenCounts"]["hotspot"],
            "screenedAs": (
                "the decompressed text contains zero rental tokens and zero "
                "legacy literals; its 'getis'/'hotspot' occurrences are the "
                "transaction product's own labels (screened as UI metadata "
                "text, origin unverified)"
            ),
        },
        "otherShippedAnalyticsAssets": {
            name: fields
            for name, fields in assets.items()
            if name != _relative(SPATIAL_ANALYSIS_ASSET)
        },
        "separationStatement": (
            "this study's rental-only result is written to "
            "rentalAsset.path — a NEW file under app/public/data/analytics/; "
            "nothing is added to or overwritten in the transaction-activity "
            "product, and the two products share no cell, no key and no "
            "payload section"
        ),
    }


def build_rental_asset(
    hotspot: dict[str, Any],
    cutoff_fields: dict[str, Any],
    join: dict[str, Any],
) -> dict[str, Any]:
    """The rental-only asset payload (written by main(), deterministic).

    The joined window frame itself is consumed by hotspot_statistic() before
    this call and is not an input here: every field below derives from the
    hotspot statistic, the cutoff fields and the join record.
    """
    return {
        "schemaVersion": SCHEMA_VERSION,
        "study": STUDY,
        "product": "rental-hotspots",
        "gate": GATE,
        "separation": {
            "statement": shipped_asset_separation()["separationStatement"],
            "transactionActivityProduct": _relative(SPATIAL_ANALYSIS_ASSET),
            "rentalTokensInTransactionProduct": 0,
        },
        "window": {
            "basis": "gate-pinned historical window",
            "first": WINDOW_FIRST,
            "last": WINDOW_LAST,
            "rowsInFile": join["window"]["rowsInFile"],
            "rowsJoined": join["window"]["matchedRows"],
            "rowsUnmatched": join["window"]["unmatchedRows"],
            "matchShare": join["window"]["matchShare"],
        },
        "unmatchedPopulation": join["unmatchedPopulation"],
        "cutoff": {
            "lastCompleteMonth": cutoff_fields["lastCompleteMonth"],
            "terminalMonth": cutoff_fields["terminalMonth"],
            "terminalMonthShareOfTrailingMedian": cutoff_fields[
                "terminalMonthShareOfTrailingMedian"
            ],
        },
        "method": hotspot["method"],
        "cellCounts": hotspot["cellCounts"],
        "counts": {
            "analyticZ": hotspot["analyticZ"],
            "simulationZ": hotspot["simulationZ"],
            "pSimFloor": hotspot["pSimFloor"],
            "hexAdjacencyBinary": hotspot["hexAdjacencySensitivity"]["binary"],
        },
        "cells": hotspot["cellsTable"],
        "extremes": hotspot["extremes"],
        "persistenceDisclosure": hotspot["persistenceDisclosure"],
        "caveats": [
            "the legacy's threshold basis (which z) is unstated; counts are reported per basis and none is adjudicated as the legacy reading",
            "cell medians are unadjusted for flat-type mix, following the stated method",
            "the unmatched 93 rows are reported as a population and excluded from the statistic for want of coordinates",
            "persistence is not measurable inside one gate-pinned period; see persistenceDisclosure",
        ],
    }


def rental_asset_fields() -> dict[str, Any]:
    if not RENTAL_ASSET.is_file():
        raise SystemExit(f"rental asset missing at {_relative(RENTAL_ASSET)}")
    return {
        "path": _relative(RENTAL_ASSET),
        "sha256": sha256_of(RENTAL_ASSET),
        "bytes": int(RENTAL_ASSET.stat().st_size),
        "determinism": "gzip.compress(..., mtime=0) over canonical_bytes (sorted keys, indent 2, no timestamps, no absolute paths)",
    }


# Every quantitative claim of the frozen legacy text, with the phrase verbatim
# (machine-checked by legacyQuoteCheck) and a ledgerKey resolved against this
# ledger by claimKeyCheck.
LEGACY_CLAIMS = (
    {
        "id": "C01",
        "phrase": "- **Rental data**: `data/parquets/L1/housing_hdb_rental.parquet`",
        "status": "withdrawn",
        "ledgerKey": "inputs.data/pipeline/01_bronze/raw_hdb_rental.parquet",
        "note": "the cited path does not exist in this checkout (data/parquets/L1 is empty); the measured stand-in is the bronze rental file at inputs.data/pipeline/01_bronze/raw_hdb_rental.parquet (215,469 rows, sha-pinned)",
    },
    {
        "id": "C02",
        "phrase": "- **Geocoding data**: `data/parquets/L2/housing_unique_searched.parquet` (lat/lon)",
        "status": "withdrawn",
        "ledgerKey": "inputs.data/pipeline/02_silver/geocoded_validated.parquet",
        "note": "the cited path does not exist; the measured stand-in is the sale-side geocode table at inputs.data/pipeline/02_silver/geocoded_validated.parquet (1,236,515 rows, lat/lon columns confirmed in sourceSchema)",
    },
    {
        "id": "C03",
        "phrase": "- **Join key**: `block_street_name`, filtered to successfully geocoded records (`search_result == 0`)",
        "status": "not-reproducible",
        "ledgerKey": "populations.geocodePopulation",
        "note": "the stated filter cannot be recomputed: the present geocode table has no search_result column (an absent column, not a null). Its measured replacement — the join on uppercased (block, street_name) keys carrying non-null lat/lon — is at joinMeasure.window (39,385 of 39,478 rows, 99.7644%), and the unmatched rows are reported as a population",
    },
    {
        "id": "C04",
        "phrase": "**Data Period**: 2024-01 to 2025-01",
        "status": "re-measured",
        "ledgerKey": "gateWindow",
        "note": "the window is present and populated: 39,478 rental rows in-file, 39,385 joined (gateWindow, joinMeasure.window); the gate pins it as its own historical window and it ends before the measured cutoff",
    },
    {
        "id": "C05",
        "phrase": "- **Date range**: 2024-01 to 2025-01",
        "status": "re-measured",
        "ledgerKey": "gateWindow",
        "note": "same measurement as C04, stated twice in the legacy text",
    },
    {
        "id": "C06",
        "phrase": "- **Getis-Ord Gi\\*** local statistic via `esda.getisord.G_Local`",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.method",
        "note": "implemented as stated: esda.getisord.G_Local(star=True) on the joined window population; library versions pinned at hotspotStatistic.method.libraryVersions. That the legacy's own run used this call is origin-unverified — no artefact links to it",
    },
    {
        "id": "C07",
        "phrase": "- **Spatial weights**: KNN (k=8) and Queen contiguity",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.method",
        "note": "KNN k=8 row-standardised is implemented as the primary weights; the legacy does not state how 'Queen contiguity' is realised for point/cell data, so a hex-adjacency (H3 k-ring-1) sensitivity is recorded as THIS PACK's choice at hotspotStatistic.hexAdjacencySensitivity (row-standardised variant degenerate; binary variant reported)",
    },
    {
        "id": "C08",
        "phrase": "- **Spatial aggregation**: H3 resolution 8, median `monthly_rent` per cell",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.cellCounts",
        "note": "implemented as stated: 269 H3 resolution-8 cells from 39,385 joined rows; cell medians are unadjusted for flat-type mix because the legacy states no adjustment",
    },
    {
        "id": "C09",
        "phrase": "- **Coverage**: 847 total cells, 623 with sufficient data for analysis",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.cellCounts",
        "note": "disagrees: the measured window population has 269 cells (hotspotStatistic.cellCounts.totalCells) — no measured reading approaches 847; the 'sufficient data' floor is unstated in the legacy and is recorded as underspecified, so the 623 figure has no measurable reading (floors at n>=2/3/5/10 are candidates at hotspotStatistic.cellCounts)",
    },
    {
        "id": "C10",
        "phrase": "  - Hotspot: z > 2.58 (99% confidence)",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.analyticZ",
        "note": "threshold implemented; measured counts recorded per basis — analytic z: 0 cells (hotspotStatistic.analyticZ), simulation z: 12 (hotspotStatistic.simulationZ), p_sim floor: 9 hot-direction (hotspotStatistic.pSimFloor). The legacy does not state which z its threshold applies to",
    },
    {
        "id": "C11",
        "phrase": "  - Weak hotspot: z > 1.96 (95% confidence)",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.simulationZ",
        "note": "same threshold scheme; analytic 0 cells, simulation 30 cells (hotspotStatistic.simulationZ.cellsAbove95)",
    },
    {
        "id": "C12",
        "phrase": "  - Coldspot: z < -2.58 (99% confidence)",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.analyticZ",
        "note": "analytic 0 cells (hotspotStatistic.analyticZ.cellsBelowCold99), simulation 1 cell (hotspotStatistic.simulationZ.cellsBelowCold99), p_sim floor 5 cold-direction (hotspotStatistic.pSimFloor)",
    },
    {
        "id": "C13",
        "phrase": "  - Weak coldspot: z < -1.96 (95% confidence)",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.simulationZ",
        "note": "analytic 0 cells, simulation 15 cells (hotspotStatistic.simulationZ.cellsBelowCold95)",
    },
    {
        "id": "C14",
        "phrase": "- **Permutations**: 99 for significance testing",
        "status": "re-measured",
        "ledgerKey": "hotspotStatistic.method",
        "note": "implemented with 99 permutations, seed 99, n_jobs=1, pinned at hotspotStatistic.method",
    },
    {
        "id": "C15",
        "phrase": "| Orchard      | 4.21           | $3,200              | Strong hotspot  |",
        "status": "withdrawn",
        "ledgerKey": "legacyAreaChecks.orchard",
        "note": "the area has zero rows in the population (no town value, no street-name substring — legacyAreaChecks.orchard), so neither the $3,200 median nor the 4.21 Gi* value can refer to this population; no artefact carries either number (methodRecovery.tokens)",
    },
    {
        "id": "C16",
        "phrase": "| Marina South | 3.89           | $3,450              | Strong hotspot  |",
        "status": "withdrawn",
        "ledgerKey": "legacyAreaChecks.marinaSouth",
        "note": "same shape as C15: zero rows for the area, no artefact for either number",
    },
    {
        "id": "C17",
        "phrase": "| Bukit Timah  | 3.45           | $3,100              | Strong hotspot  |",
        "status": "re-measured",
        "ledgerKey": "legacyAreaChecks.bukitTimah",
        "note": "the town exists (102 window rows); the measured window median is 3,400 against the claimed $3,100 (townMedians.windowByTown, legacyAreaChecks.bukitTimah), and the claimed Gi* value has no artefact and no area definition that would reproduce it",
    },
    {
        "id": "C18",
        "phrase": "| Woodlands    | -3.21          | $2,100              | Strong coldspot |",
        "status": "re-measured",
        "ledgerKey": "legacyAreaChecks.woodlands",
        "note": "the town exists (1,957 window rows); the measured window median is 3,000 against the claimed $2,100; the analytic z minimum over all cells is -0.9179 (hotspotStatistic.analyticZ.minZ) and no artefact carries -3.21",
    },
    {
        "id": "C19",
        "phrase": "| Yishun       | -2.98          | $2,050              | Strong coldspot |",
        "status": "re-measured",
        "ledgerKey": "legacyAreaChecks.yishun",
        "note": "the town exists (2,040 window rows); measured window median 2,900 against the claimed $2,050; claimed Gi* value has no artefact",
    },
    {
        "id": "C20",
        "phrase": "| Sembawang    | -2.67          | $2,000              | Strong coldspot |",
        "status": "re-measured",
        "ledgerKey": "legacyAreaChecks.sembawang",
        "note": "the town exists (944 window rows); measured window median 3,125 against the claimed $2,000; claimed Gi* value has no artefact",
    },
    {
        "id": "C21",
        "phrase": "Only **12 H3 cells** qualified as 99% confidence hotspots",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.thresholdBasisNote",
        "note": "the legacy's threshold basis (which z output) is unstated, so the claim has no single measurable reading; measured candidate counts are 0 under the analytic z, 12 under the simulation z (coincidence of the seed and implementation, recorded as such at hotspotStatistic.simulationZ.cellsAbove99), and 9 hot-direction cells at the p_sim floor. None is promoted to the legacy reading",
    },
    {
        "id": "C22",
        "phrase": "- **12 H3 cells** qualified as 99% confidence hotspots",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.thresholdBasisNote",
        "note": "same measurement as C21, restated in the legacy's Technical Findings",
    },
    {
        "id": "C23",
        "phrase": "- **Top hotspots**: Orchard Gi* = 4.21, Marina South Gi* = 3.89, Bukit Timah Gi\\* = 3.45",
        "status": "withdrawn",
        "ledgerKey": "hotspotStatistic.analyticZ",
        "note": "two of the three areas have zero rows in the population (legacyAreaChecks.orchard, legacyAreaChecks.marinaSouth); no artefact carries any of the three values; the measured analytic z maximum over all 269 cells is 1.6536, below every claimed hotspot value",
    },
    {
        "id": "C24",
        "phrase": "- **Top coldspots**: Woodlands Gi* = -3.21, Yishun Gi* = -2.98, Sembawang Gi\\* = -2.67",
        "status": "withdrawn",
        "ledgerKey": "hotspotStatistic.analyticZ",
        "note": "no artefact carries any of the three values; the measured analytic z minimum is -0.9179 and the simulation-z reading yields exactly 1 cell below -2.58 (hotspotStatistic.simulationZ), so no claimed coldspot value is reachable on this population",
    },
    {
        "id": "C25",
        "phrase": "| Hotspot median rent  | $3,200                       |",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.extremes.candidateRentLevels",
        "note": "the legacy's hotspot population is undefined (threshold basis unstated), so the level cannot be recomputed as stated; the candidate value under the simulation-z reading is a median-of-medians of 3,200 across 12 cells (hotspotStatistic.extremes.candidateRentLevels.hotMedianOfMedians) — recorded as a candidate, not a confirmation, and coincidentally equal to the Orchard row's level",
    },
    {
        "id": "C26",
        "phrase": "| Coldspot median rent | about 1,850 to 2,100 dollars |",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.extremes.candidateRentLevels",
        "note": "same undefined population; the simulation-z reading yields exactly 1 cold cell whose median (3,200) lies OUTSIDE the claimed band, and the town-level candidate medians for the legacy's own coldspot towns are 2,900-3,125 (townMedians.windowByTown) — also outside the band",
    },
    {
        "id": "C27",
        "phrase": "| Typical gap          | about $1,350 per month       |",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.extremes.candidateRentLevels",
        "note": "the gap inherits the undefined populations; the candidate gap under the simulation-z reading is 3,200 - 3,200 = 0.0 (exact arithmetic on candidateRentLevels.hotMedianOfMedians and candidateRentLevels.coldMedianOfMedians), and under the analytic reading no gap exists because no cell passes any threshold",
    },
    {
        "id": "C28",
        "phrase": "| Hotspot remains hotspot    | 58-62%      |",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.persistenceDisclosure",
        "note": "a transition needs at least two periods; the gate pins ONE window (2024-01..2025-01), the scan found no transition implementation (methodRecovery.transitionProbabilities) and no stored probability table, so no persistence estimate is measurable in this checkout",
    },
    {
        "id": "C29",
        "phrase": "| Coldspot remains coldspot  | 55-60%      |",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.persistenceDisclosure",
        "note": "same as C28",
    },
    {
        "id": "C30",
        "phrase": "| Non-significant to hotspot | 8-10%       |",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.persistenceDisclosure",
        "note": "same as C28",
    },
    {
        "id": "C31",
        "phrase": "- **Rent gap**: hotspot median $3,200 vs coldspot median ~$1,850-$2,100 ≈ $1,350/month",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.extremes.candidateRentLevels",
        "note": "restates C25-C27 in one line; same undefined populations and same candidates",
    },
    {
        "id": "C32",
        "phrase": "- **Persistence rates**: hotspot remains hotspot 58-62%, coldspot remains coldspot 55-60%",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.persistenceDisclosure",
        "note": "restates C28-C29; same single-period limit",
    },
    {
        "id": "C33",
        "phrase": "- **Transition rate**: non-significant → hotspot only 8-10%, confirming true hotspots are limited",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.persistenceDisclosure",
        "note": "same as C28, and the word 'confirming' is the legacy's own: a screened-as-absent transition statistic can neither confirm nor refute the narrative — origin unverified in both directions",
    },
    {
        "id": "C34",
        "phrase": "Persistence is moderate (58-62%), meaning hotspot status is sticky but not permanent",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.persistenceDisclosure",
        "note": "interpretation built on C28's unmeasurable quantity",
    },
    {
        "id": "C35",
        "phrase": "The ~$1,350/month rent gap between hotspots and coldspots is economically significant.",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.extremes.candidateRentLevels",
        "note": "significance judgement on C27's unmeasurable quantity; the candidate measured gap under the simulation-z reading is 0.0",
    },
    {
        "id": "C36",
        "phrase": "The low non-significant→hotspot transition rate (8-10%) confirms that emerging hotspot narratives require strong fundamental evidence.",
        "status": "not-reproducible",
        "ledgerKey": "hotspotStatistic.persistenceDisclosure",
        "note": "same unmeasurable quantity as C30; 'confirms' is the legacy's word and cannot be inherited by this pack",
    },
    {
        "id": "C37",
        "phrase": "Rental premiums cluster geographically rather than appearing randomly",
        "status": "withdrawn",
        "ledgerKey": "hotspotStatistic.analyticZ",
        "note": "interpretive summary, not a measurement; the measured counts are recorded per basis (analytic 0 cells above any threshold, simulation 12) and neither adjudicates 'random' without the legacy's unstated threshold basis",
    },
    {
        "id": "C38",
        "phrase": "- For rental investors, location selection can dominate small property-level differences.",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.advice",
        "note": "investment advice; carries no measured value in this pack (the exemplar's rule: advice is recorded, not re-measured)",
    },
    {
        "id": "C39",
        "phrase": "Coldspots can still be attractive when commute, amenities, and own-stay needs line up.",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.advice",
        "note": "purchase advice; no measured value",
    },
    {
        "id": "C40",
        "phrase": "the canonical assets for this page now live under `app/public/data/analysis/`",
        "status": "withdrawn",
        "ledgerKey": "shippedAssetSeparation.spatialAnalysis",
        "note": "the cited directory app/public/data/analysis/ does not exist; the shipped analytics assets live under app/public/data/analytics/ (three transaction-side files, sha-pinned at shippedAssetSeparation), plus this study's new rental-only asset at rentalAsset.path",
    },
)


def legacy_claims() -> list[dict[str, str]]:
    return [dict(claim) for claim in LEGACY_CLAIMS]


def legacy_quote_check(claims: list[dict[str, str]]) -> dict[str, Any]:
    """Every quoted phrase must appear verbatim in the frozen legacy text."""
    text = LEGACY_EDITION.read_text(encoding="utf-8")
    quotes: list[dict[str, Any]] = []
    for claim in claims:
        count = int(text.count(claim["phrase"]))
        quotes.append({"id": claim["id"], "phrase": claim["phrase"], "occurrences": count})
    return {
        "legacyFile": _relative(LEGACY_EDITION),
        "legacyFileSha256": sha256_of(LEGACY_EDITION),
        "claimsChecked": len(claims),
        "quotes": quotes,
        "allQuotesFound": all(int(q["occurrences"]) > 0 for q in quotes),
        "method": (
            "each phrase is required to appear verbatim in the frozen legacy "
            "text; a paraphrase inside quotation marks is a defect, and an "
            "ellipsis is permitted only for a genuine omission"
        ),
    }


def _resolve_ledger_path(payload: dict[str, Any], dotted: str) -> bool:
    """Does a claim's `ledgerKey` resolve inside the ledger that quotes it?"""
    # Input keys are repository-relative paths (and therefore contain dots and
    # slashes). Treat the complete suffix after ``inputs.`` as one dict key.
    if dotted.startswith("inputs."):
        input_path = dotted.removeprefix("inputs.")
        if input_path in payload.get("inputs", {}):
            return True
    node: Any = payload
    for part in dotted.split("."):
        if isinstance(node, dict):
            if part not in node:
                return False
            node = node[part]
        elif isinstance(node, list):
            match = next(
                (item for item in node if isinstance(item, dict) and item.get("id") == part),
                None,
            )
            if match is None:
                return False
            node = match
        else:
            return False
    return True


def check_claim_keys(payload: dict[str, Any], claims: list[dict[str, str]]) -> dict[str, Any]:
    """Every claim's key must resolve, or the build fails."""
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
        "resolutionIsSyntactic": (
            "resolution is SYNTACTIC: each ledgerKey is walked against this "
            "ledger's dicts by key and lists by item id at build time; the "
            "walk lands on a recorded field and says nothing about whether "
            "the field's content supports the claim"
        ),
        "method": ("an unresolved key fails the build rather than shipping"),
    }


def not_measurable() -> dict[str, Any]:
    return {
        "advice": {
            "items": ["C38", "C39"],
            "meaning": "advice lines are recorded as withdrawn; no measurable content",
        },
        "legacyTotalCells847": {
            "meaning": (
                "no measured reading produces 847 cells: the window population "
                "has 269 (hotspotStatistic.cellCounts.totalCells); the legacy "
                "value has no artefact and its population/floor are unstated"
            ),
        },
        "persistence": {
            "meaning": (
                "not measurable: one gate-pinned period, no transition "
                "implementation, no transition artefact "
                "(hotspotStatistic.persistenceDisclosure)"
            ),
        },
        "legacyThresholdBasis": {
            "meaning": (
                "the z output the legacy thresholds apply to is unstated; both "
                "esda z bases are reported and neither is adjudicated"
            ),
        },
        "queenContiguityRealisation": {
            "meaning": (
                "the legacy's Queen contiguity is unstated for cell data; the "
                "hex-adjacency analogue is this pack's choice, recorded at "
                "hotspotStatistic.hexAdjacencySensitivity"
            ),
        },
        "sufficientDataFloor": {
            "meaning": (
                "the legacy's 'sufficient data' floor is unstated; measured "
                "floor candidates at hotspotStatistic.cellCounts, none promoted"
            ),
        },
    }


def build() -> dict[str, Any]:
    cutoff_fields = cutoff(pd.read_parquet(RENTAL, columns=["rent_approval_date"]))
    pops = populations(cutoff_fields)
    gw = gate_window(pd.read_parquet(RENTAL, columns=["rent_approval_date"]), cutoff_fields)
    join = join_measure(cutoff_fields)
    hotspot = hotspot_statistic(join.pop("matchedWindow"))
    towns = town_medians(
        pd.read_parquet(RENTAL)
        .assign(
            kBlock=lambda f: f["block"].astype(str).str.strip().str.upper(),
            kStreet=lambda f: f["street_name"].astype(str).str.strip().str.upper(),
            rent=lambda f: pd.to_numeric(f["monthly_rent"].astype(str).str.strip(), errors="raise"),
            rent_approval_date=lambda f: f["rent_approval_date"].astype(str),
        )
        .loc[
            lambda f: (f["rent_approval_date"] >= WINDOW_FIRST)
            & (f["rent_approval_date"] <= WINDOW_LAST)
        ]
        .merge(
            pd.read_parquet(GEOCODE, columns=["block", "street_name", "lat", "lon"])
            .assign(
                kBlock=lambda f: f["block"].astype(str).str.strip().str.upper(),
                kStreet=lambda f: f["street_name"].astype(str).str.strip().str.upper(),
            )
            .loc[lambda f: f["lat"].notna() & f["lon"].notna(), ["kBlock", "kStreet"]]
            .drop_duplicates(),
            on=["kBlock", "kStreet"],
            how="inner",
        )
    )
    areas = legacy_area_checks(towns)
    recovery = method_recovery(_scan_files())
    separation = shipped_asset_separation()

    hotspot["thresholdBasisNote"] = hotspot["method"]["thresholdBasis"]

    # The rental-only asset is written FIRST so the ledger can pin its bytes.
    asset_payload = build_rental_asset(
        hotspot=hotspot,
        cutoff_fields=cutoff_fields,
        join=join,
    )
    RENTAL_ASSET.parent.mkdir(parents=True, exist_ok=True)
    RENTAL_ASSET.write_bytes(gz_bytes(asset_payload))
    asset_fields = rental_asset_fields()

    claims = legacy_claims()
    inputs = {}
    for path in (
        RENTAL,
        GEOCODE,
        LEGACY_EDITION,
        SPATIAL_ANALYSIS_ASSET,
        FEATURE_IMPACT_ASSET,
        PREDICTIVE_ASSET,
    ):
        entry: dict[str, Any] = {"sha256": sha256_of(path), "bytes": int(path.stat().st_size)}
        if path.suffix == ".parquet":
            schema = pq.read_schema(path)
            entry["rows"] = int(pq.ParquetFile(path).metadata.num_rows)
            entry["columns"] = int(len(schema.names))
        inputs[_relative(path)] = entry

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": STUDY,
        "series": "spatial-hotspots",
        "gate": GATE,
        "scope": (
            "RS12 spatial-hotspots evidence: the measured cutoff, the gate-pinned "
            "window, the rental population and its join to the sale-side block "
            "geocodes, the re-measured Getis-Ord Gi* statistic on the joined "
            "population (both esda z bases), the six legacy-named areas, the "
            "bounded absence scan, the shipped-asset separation, and the "
            "claim-by-claim disposition of the frozen legacy text"
        ),
        "definition": (
            "A measured inventory and re-run of the stated hotspot method on "
            "what this checkout can support. The rental file (215,469 rows, "
            "2021-01..2026-10, no coordinate columns) is joined on uppercased "
            "(block, street_name) to the sale-side geocode table's joinable "
            "keys (11,500 of its 11,637 distinct keys carry non-null lat/lon); "
            "inside the gate-pinned window 39,385 of 39,478 rows join "
            "(99.7644%) and the 93 unmatched rows are reported as a "
            "population. The stated method is re-run on that joined "
            "population: H3 resolution 8, median monthly_rent per cell, "
            "Getis-Ord Gi* with 99 seeded permutations over KNN k=8 "
            "row-standardised weights. Because the legacy does not state "
            "which z output its thresholds apply to, both esda z bases are "
            "reported (analytic Zs: no cell above any legacy threshold; "
            "simulation z_sim: 12 cells above 2.58) and neither is adjudicated "
            "as the legacy reading — that is an underspecification record, not "
            "a reproduction claim. Two of the legacy's six named areas have "
            "zero rows in this population and the other four's measured "
            "town-level medians differ from the legacy levels. Persistence is "
            "not measurable here: one gate-pinned period, no transition "
            "implementation, no artefact. The transaction-activity product is "
            "read read-only, carries zero rental tokens by token scan, and "
            "receives nothing; this study's result is written to a NEW "
            "rental-only asset. What this pack does NOT establish: the origin "
            "of any legacy number (no artefact is linked to them in either "
            "direction), any transition probability, and any claim about "
            "areas this population does not contain."
        ),
        "inputs": inputs,
        "cutoff": cutoff_fields,
        "gateWindow": gw,
        "sourceSchema": {
            "rental": pops["rentalSchema"],
            "geocode": pops["geocodeSchema"],
            "meaning": (
                "schemas read via parquet metadata BEFORE any column was "
                "claimed; the rental file's 7 columns include no coordinate "
                "column, which is why the join (not a within-file coordinate) "
                "is the only geocode path"
            ),
        },
        "populations": {
            "rentalPopulation": pops["rentalPopulation"],
            "geocodePopulation": pops["geocodePopulation"],
        },
        "joinMeasure": join,
        "hotspotStatistic": hotspot,
        "townMedians": towns,
        "legacyAreaChecks": areas,
        "methodRecovery": recovery,
        "shippedAssetSeparation": separation,
        "rentalAsset": asset_fields,
        "notMeasurable": not_measurable(),
        "statusMeaning": STATUS_MEANING,
        "legacyClaims": claims,
        "legacyQuoteCheck": legacy_quote_check(claims),
    }
    payload["claimKeyCheck"] = check_claim_keys(payload, claims)
    return payload


def check(output: Path) -> int:
    if not output.is_file():
        print(f"FAILED: no ledger at {output}; run the tool without --check first")
        return 1
    recorded = output.read_bytes()
    measured = canonical_bytes(build())
    if recorded == measured:
        print("Pass: RS12 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS12 ledger does not match this checkout")
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

    hs = evidence["hotspotStatistic"]
    print(
        f"Cutoff: last complete month {evidence['cutoff']['lastCompleteMonth']} "
        f"(terminal {evidence['cutoff']['terminalMonth']} at "
        f"{evidence['cutoff']['terminalMonthShareOfTrailingMedian']} of the trailing median)"
    )
    print(
        f"Gate window: {evidence['gateWindow']['first']}..{evidence['gateWindow']['last']} "
        f"rows-in-file {evidence['gateWindow']['rowsInFile']}, joined "
        f"{evidence['joinMeasure']['window']['matchedRows']} "
        f"({evidence['joinMeasure']['window']['matchShare']}), unmatched "
        f"{evidence['joinMeasure']['window']['unmatchedRows']}"
    )
    print(
        f"Cells: {hs['cellCounts']['totalCells']} at H3 resolution "
        f"{hs['method']['h3Resolution']}; analytic z max {hs['analyticZ']['maxZ']} min {hs['analyticZ']['minZ']}"
    )
    print(
        f"Counts: analytic >2.58 = {hs['analyticZ']['cellsAbove99']}, "
        f"simulation >2.58 = {hs['simulationZ']['cellsAbove99']}, "
        f"p_sim<=0.01 hot = {hs['pSimFloor']['cellsAtFloorHotDirection']}, "
        f"cold = {hs['pSimFloor']['cellsAtFloorColdDirection']}"
    )
    quotes_ok = sum(1 for q in evidence["legacyQuoteCheck"]["quotes"] if q["occurrences"] > 0)
    print(f"Quote check: {quotes_ok}/{evidence['legacyQuoteCheck']['claimsChecked']} verbatim")
    statuses: dict[str, int] = {}
    for claim in evidence["legacyClaims"]:
        statuses[claim["status"]] = statuses.get(claim["status"], 0) + 1
    print("Claim statuses: " + ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())))
    print(
        f"Rental asset: {evidence['rentalAsset']['path']} ({evidence['rentalAsset']['bytes']} bytes)"
    )
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
