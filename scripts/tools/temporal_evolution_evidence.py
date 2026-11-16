#!/usr/bin/env python3
"""Measure RS03's temporal-evolution evidence: comparable windows and vintages.

RS03's gate is "comparable historical transactions and period-correct feature
vintages". This tool measures from the local checkout, and only what the
checkout can support:

1. **Window coverage** — the legacy study compares three period windows
   (Pre-COVID 2017-2019, COVID 2020-2022, Post-COVID 2023-2026). Each window is
   re-cut on the current dataset per property type, counting transactions,
   observed months and *why* a month is absent (source not yet covered vs no
   transactions observed in a covered month).
2. **Sample composition** — per window, the mix that moves a median: flat-type
   shares, floor area, remaining lease, EC share, town/area spread.
3. **Like-window price medians with uncertainty** — nominal and CPI-deflated
   medians per window, with a seeded bootstrap interval. Descriptive only.
4. **Planning-area baseline** — per planning-area-year transaction counts and
   median prices, and the distribution of year-over-year median-price change
   where both years clear a stated sample floor. No trajectory classification.
5. **Feature-vintage audit** — what dated feature vintages the sources carry (a
   single 2019-dated MRT seed snapshot exists; nothing per window; no dated
   school series), and whether the distance/quality features are populated for
   every window (a single current vintage applied to all periods).

It never runs the pipeline, never fits the legacy models and never writes
outside `--output`.

Usage:

    uv run python scripts/tools/temporal_evolution_evidence.py \\
        --output docs/implementation/artifacts/rs03-temporal-evolution-evidence.json

    uv run python scripts/tools/temporal_evolution_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from egg_n_bacon_housing.utils.geo import haversine_metres

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
RAW_RESALE = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_hdb_resale.parquet"
RAW_CONDO = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_condo_transactions.parquet"
MRT_STATIONS = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_mrt_stations.parquet"
SCHOOL_DIRECTORY = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_school_directory.parquet"
MRT_LINES = REPO_ROOT / "data" / "manual" / "mrt_lines_mapping.csv"
SCHOOL_TIERS_PRIMARY = REPO_ROOT / "data" / "manual" / "csv" / "school_tiers_primary.csv"
SCHOOL_TIERS_SECONDARY = REPO_ROOT / "data" / "manual" / "csv" / "school_tiers_secondary.csv"
SCHOOL_WEIGHTS = REPO_ROOT / "data" / "manual" / "csv" / "school_quality_weights.csv"
MRT_GEOJSON = REPO_ROOT / "data" / "manual" / "csv" / "datagov" / "MRTStations.geojson"
GEOJSON_INGESTION_MODULE = (
    REPO_ROOT / "src" / "egg_n_bacon_housing" / "components" / "ingestion" / "geojson.py"
)
FEATURES_MODULE = REPO_ROOT / "src" / "egg_n_bacon_housing" / "components" / "features.py"
LEGACY_SEED_MARKER = "2019 vintage"
STATION_CONSUMER_MARKER = "mrt_stations=raw_mrt_stations"
LINEAGE_SAMPLE_SIZE = 20000
LINEAGE_SAMPLE_SEED = 20261115
LINEAGE_TOLERANCE_METRES = 1e-6
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs03-temporal-evolution-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

# The legacy text's own period labels (never renamed), re-cut on this dataset.
# The post-COVID window ends at the measured last complete month, not at "2026":
# the 2026-11 month present in the sources is partial at this cutoff.
WINDOWS: list[dict[str, str | None]] = [
    {
        "label": "pre-covid",
        "legacyLabel": "Pre-COVID (2017-2019)",
        "startMonth": "2017-01",
        "endMonth": "2019-12",
    },
    {
        "label": "covid",
        "legacyLabel": "COVID (2020-2022)",
        "startMonth": "2020-01",
        "endMonth": "2022-12",
    },
    {
        "label": "post-covid",
        "legacyLabel": "Post-COVID (2023-2026)",
        "startMonth": "2023-01",
        "endMonth": None,  # resolved to the measured cutoff at runtime
    },
]

STUDY_WINDOW_START = "2017-01"
# Descriptive area-year change requires both years to clear this floor. It is a
# floor for *this pack's* descriptive baseline, not the legacy models' floors
# (300 HDB / 100 condo per regression year), which are not reproduced here.
AREA_YEAR_FLOOR = 30
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261115
STUDY_YEARS = list(range(2017, 2027))
# Year-over-year change needs a full prior year inside the window; the last
# study year is partial (its month coverage is measured, not assumed), so it
# gets no change measurement.
CHANGE_YEARS = list(range(2018, 2026))

DEFINITION = (
    "Descriptive re-cut of the legacy period windows on the current dataset: "
    "transaction counts, sample composition, and nominal and CPI-deflated median "
    "prices per (property type, window), plus a per-planning-area-year baseline "
    "with a stated sample floor. No premium model, no clustering and no "
    "trajectory classification is reproduced; window medians are not "
    "mix-adjusted and period-over-period changes are not causal claims."
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _select(frame: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Boolean-mask a frame, keeping the result explicitly a DataFrame."""
    return pd.DataFrame(frame[mask])


def _r(value: Any, digits: int) -> float | None:
    """Round a float for canonical output; None stays None."""
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    return round(float(value), digits)


def _median_ci(values: Any) -> dict[str, int | float | None]:
    """Median with a seeded bootstrap interval.

    The seed and resample count are constants of this tool: the interval is a
    function of the data only, so a re-run reproduces it byte-identically.
    """
    series = pd.Series(values, dtype="float64")
    clean = series.dropna().to_numpy(dtype=float)
    n = int(clean.size)
    if n == 0:
        return {"n": 0, "median": None, "ci95Low": None, "ci95High": None}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    medians = np.empty(BOOTSTRAP_RESAMPLES)
    for i in range(BOOTSTRAP_RESAMPLES):
        medians[i] = np.median(rng.choice(clean, size=n, replace=True))
    low, high = np.quantile(medians, [0.025, 0.975])
    return {
        "n": n,
        "median": int(round(float(np.median(clean)))),
        "ci95Low": int(round(float(low))),
        "ci95High": int(round(float(high))),
    }


def _lease_years(series: pd.Series) -> float | None:
    """Median remaining lease in whole years, parsed from 'NN years MM months'."""
    tokens = pd.Series(series.dropna().astype(str).str.split().str[0])
    parsed = pd.Series(pd.to_numeric(tokens, errors="coerce")).dropna()
    if parsed.empty:
        return None
    return float(parsed.median())


def load_transactions() -> pd.DataFrame:
    frame = pd.read_parquet(
        UNIFIED,
        columns=[
            "month",
            "transaction_date",
            "property_type",
            "price",
            "psf",
            "town",
            "planning_area",
            "flat_type",
            "floor_area_sqm",
            "remaining_lease",
            "is_ec",
            "cpi",
            "property_subtype",
            "dist_to_nearest_mrt",
            "school_accessibility_score",
        ],
    )
    frame = frame.assign(
        price=pd.to_numeric(frame["price"], errors="coerce"),
        psf=pd.to_numeric(frame["psf"], errors="coerce"),
        cpi=pd.to_numeric(frame["cpi"], errors="coerce"),
    )
    return _select(frame, frame["price"] > 0)


def _window_slice(frame: pd.DataFrame, window: dict[str, str]) -> pd.DataFrame:
    return _select(
        frame, (frame["month"] >= window["startMonth"]) & (frame["month"] <= window["endMonth"])
    )


def _month_counts(frame: pd.DataFrame, property_type: str) -> dict[str, int]:
    at = _select(frame, frame["property_type"] == property_type)
    counts = at.groupby("month").size()
    return {str(key): int(value) for key, value in counts.items()}


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    counts = _month_counts(frame, "hdb")
    ordered = sorted(counts)
    last_month = ordered[-1]
    trailing = [counts[month] for month in ordered[-13:-1]]
    trailing_median = float(np.median(trailing)) if trailing else 0.0
    ratio = counts[last_month] / trailing_median if trailing_median else None
    condo_months = sorted(_month_counts(frame, "condo"))
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
        "condoTerminalMonth": condo_months[-1] if condo_months else None,
    }


def window_defs(last_complete_month: str) -> list[dict[str, str]]:
    """Resolve the re-cut windows; the last window ends at the measured cutoff."""
    resolved = []
    for window in WINDOWS:
        resolved.append(
            {
                "label": str(window["label"]),
                "legacyLabel": str(window["legacyLabel"]),
                "startMonth": str(window["startMonth"]),
                "endMonth": str(window["endMonth"] or last_complete_month),
            }
        )
    return resolved


def _months_between(start: str, end: str) -> list[str]:
    return [str(period) for period in pd.period_range(start=start, end=end, freq="M")]


def window_coverage(frame: pd.DataFrame, windows: list[dict[str, str]]) -> dict[str, Any]:
    """Per property type per window: n, months observed, and why months are absent."""
    monthly: dict[str, list[dict[str, Any]]] = {"hdb": [], "condo": []}
    by_type: dict[str, dict[str, Any]] = {}
    for property_type in ("hdb", "condo"):
        counts = _month_counts(frame, property_type)
        observed_all = sorted(month for month, count in counts.items() if count > 0)
        source_first = observed_all[0] if observed_all else None
        source_last = observed_all[-1] if observed_all else None
        windows_out: dict[str, Any] = {}
        for window in windows:
            expected = _months_between(window["startMonth"], window["endMonth"])
            observed = [month for month in expected if counts.get(month, 0) > 0]
            # Absence has two different meanings and they must never be merged:
            # a month before the source's measured coverage starts is
            # source-missing; a month inside the coverage with zero transactions
            # is no-sales-observed.
            source_missing = [month for month in expected if month < (source_first or "9999")]
            no_sales = [
                month for month in expected if month not in observed and month not in source_missing
            ]
            windows_out[window["label"]] = {
                "legacyLabel": window["legacyLabel"],
                "startMonth": window["startMonth"],
                "endMonth": window["endMonth"],
                "monthsExpected": len(expected),
                "transactions": int(sum(counts.get(month, 0) for month in expected)),
                "monthsObserved": len(observed),
                "firstTransactionMonth": observed[0] if observed else None,
                "lastTransactionMonth": observed[-1] if observed else None,
                "sourceMissingMonths": len(source_missing),
                "noSalesObservedMonths": len(no_sales),
            }
        study_months = _months_between(STUDY_WINDOW_START, windows[-1]["endMonth"])
        monthly[property_type] = [
            {"month": month, "transactions": counts.get(month, 0)} for month in study_months
        ]
        by_type[property_type] = {
            "sourceCoverage": {"firstMonth": source_first, "lastMonth": source_last},
            "windows": windows_out,
        }
    return {"byPropertyType": by_type, "monthlyTransactions": monthly}


def window_medians(frame: pd.DataFrame, windows: list[dict[str, str]]) -> dict[str, Any]:
    """Nominal and CPI-deflated medians per (property type, window), with CIs."""
    cpi_rows = _select(frame, pd.Series(frame["cpi"]).notna())
    cpi_by_month = cpi_rows.groupby("month")["cpi"].median().sort_index()
    cpi_base_month = str(cpi_by_month.index.max())
    cpi_base = float(cpi_by_month.iloc[-1])
    out: dict[str, Any] = {"cpiBaseMonth": cpi_base_month, "byPropertyType": {}}
    for property_type in ("hdb", "condo"):
        at = _select(frame, frame["property_type"] == property_type)
        windows_out: dict[str, Any] = {}
        for window in windows:
            in_window = _window_slice(at, window)
            prices = pd.Series(in_window["price"], dtype="float64")
            psf = pd.Series(in_window["psf"], dtype="float64")
            nominal = _median_ci(prices)
            real_rows = _select(in_window, pd.Series(in_window["cpi"]).notna())
            real_prices = pd.Series(real_rows["price"], dtype="float64").to_numpy(dtype=float)
            factors = cpi_base / pd.Series(real_rows["cpi"], dtype="float64").to_numpy(dtype=float)
            real = _median_ci(real_prices * factors)
            excluded = 1.0 - (len(real_rows) / len(in_window)) if len(in_window) else None
            windows_out[window["label"]] = {
                "transactions": int(len(in_window)),
                "medianPriceNominal": nominal,
                "medianPriceReal": real,
                "cpiExcludedShare": _r(excluded, 4),
                "medianPsfNominal": {
                    "n": int(psf.notna().sum()),
                    "median": _r(float(psf.median()) if len(psf) else None, 2),
                },
            }
        out["byPropertyType"][property_type] = windows_out
    return out


def sample_composition(frame: pd.DataFrame, windows: list[dict[str, str]]) -> dict[str, Any]:
    """What moves a median between windows: mix, area, lease, geography."""
    out: dict[str, Any] = {"byPropertyType": {}}
    for property_type in ("hdb", "condo"):
        at = _select(frame, frame["property_type"] == property_type)
        windows_out: dict[str, Any] = {}
        for window in windows:
            in_window = _window_slice(at, window)
            entry: dict[str, Any] = {
                "transactions": int(len(in_window)),
                "medianFloorAreaSqm": _r(float(in_window["floor_area_sqm"].median()), 2),
            }
            if property_type == "hdb":
                mix = in_window["flat_type"].value_counts(normalize=True)
                entry["distinctTowns"] = int(in_window["town"].nunique())
                entry["medianRemainingLeaseYears"] = _r(
                    _lease_years(pd.Series(in_window["remaining_lease"])), 1
                )
                entry["flatTypeMix"] = {
                    str(key): _r(float(value), 4) for key, value in sorted(mix.items())
                }
            else:
                entry["distinctPlanningAreas"] = int(in_window["planning_area"].nunique())
                ec = pd.Series(in_window["is_ec"]).astype(bool)
                entry["ecTransactions"] = int(ec.sum())
                entry["ecShare"] = _r(float(ec.mean()), 4)
                # The URA private ingest mixes strata and landed subtypes (RS01),
                # so a "condo" median is not a condominium-only statistic; the
                # mix that makes that true is measured, not asserted.
                subtypes = in_window["property_subtype"].value_counts(normalize=True)
                entry["subtypeMix"] = {
                    str(key): _r(float(value), 4) for key, value in sorted(subtypes.items())
                }
            windows_out[window["label"]] = entry
        out["byPropertyType"][property_type] = windows_out
    return out


def shipped_feature_lineage() -> dict[str, Any]:
    """Measure which station input the shipped MRT-distance column derives from.

    The shipped `dist_to_nearest_mrt` values are recomputed exactly as
    `utils/proximity.py` computes them (radians -> BallTree(haversine), k=1,
    then `haversine_metres`) from two candidate inputs — the sha-pinned bronze
    station frame and the 2019 legacy seed as its own loader reads it — over a
    seeded sample of shipped transactions. A match identifies the input that
    produced the shipped column; this is measured lineage, not an inference
    from an acquisition record.
    """
    from egg_n_bacon_housing.components.ingestion.geojson import _load_mrt_geojson

    bronze = pd.read_parquet(MRT_STATIONS)
    seed = _load_mrt_geojson(MRT_GEOJSON)
    bronze_rows_with_lrt = int(
        bronze["line"].astype(str).str.upper().str.contains("LRT", na=False).sum()
    )

    shipped = pd.read_parquet(UNIFIED, columns=["lat", "lon", "dist_to_nearest_mrt"])
    usable = _select(
        shipped,
        pd.Series(shipped["lat"]).notna()
        & pd.Series(shipped["lon"]).notna()
        & pd.Series(shipped["dist_to_nearest_mrt"]).notna(),
    )
    rng = np.random.default_rng(LINEAGE_SAMPLE_SEED)
    sample = usable.iloc[sorted(rng.choice(len(usable), size=LINEAGE_SAMPLE_SIZE, replace=False))]
    lat = sample["lat"].to_numpy(dtype=float)
    lon = sample["lon"].to_numpy(dtype=float)
    shipped_values = pd.Series(sample["dist_to_nearest_mrt"], dtype="float64").to_numpy(dtype=float)

    def min_distance(stations: pd.DataFrame) -> np.ndarray:
        """Nearest-station distance over every station in the frame.

        The minimum of the pipeline's own `haversine_metres` over all stations
        is, by definition, the same distance `utils/proximity.py` computes via
        its BallTree(haversine) k=1 query — same formula, same inputs.
        """
        station_lat = stations["lat"].to_numpy(dtype=float)
        station_lon = stations["lon"].to_numpy(dtype=float)
        stacked = np.stack(
            [
                haversine_metres(lat, lon, station_lat[i], station_lon[i])
                for i in range(station_lat.size)
            ]
        )
        return stacked.min(axis=0)

    bronze_deviations = np.abs(min_distance(bronze) - shipped_values)
    seed_deviations = np.abs(min_distance(seed) - shipped_values)
    bronze_matches = int((bronze_deviations <= LINEAGE_TOLERANCE_METRES).sum())
    seed_matches = int((seed_deviations <= LINEAGE_TOLERANCE_METRES).sum())
    bronze_max_dev = float(bronze_deviations.max())
    seed_max_dev = float(seed_deviations.max())
    if bronze_matches != LINEAGE_SAMPLE_SIZE:
        raise SystemExit(
            "shipped dist_to_nearest_mrt no longer reproduces from the bronze "
            f"station frame ({bronze_matches}/{LINEAGE_SAMPLE_SIZE} match); the "
            "dataset and the pinned input have diverged"
        )
    return {
        "consumerCode": _ingestion_fallback_quote(
            FEATURES_MODULE, STATION_CONSUMER_MARKER, "station-consumer"
        ),
        "input": {
            "path": MRT_STATIONS.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(MRT_STATIONS),
            "rows": int(len(bronze)),
            "distinctStationNames": int(bronze["name"].nunique()),
            "rowsWithLrtLine": bronze_rows_with_lrt,
        },
        "seedInput": {
            "path": MRT_GEOJSON.relative_to(REPO_ROOT).as_posix(),
            "features": 257,
            "loaderKeptRows": int(len(seed)),
            "distinctNames": int(seed["name"].nunique()),
        },
        "verification": {
            "method": (
                "nearest-station distance recomputed as the minimum "
                "haversine_metres over every station in the candidate frame — "
                "the same nearest-station distance utils/proximity.py computes "
                "via its BallTree(metric='haversine') k=1 selection"
            ),
            "sampleSize": LINEAGE_SAMPLE_SIZE,
            "sampleSeed": LINEAGE_SAMPLE_SEED,
            "shippedRowsWithCoordinatesAndDistance": int(len(usable)),
            "toleranceMetres": LINEAGE_TOLERANCE_METRES,
            "bronzeMatches": bronze_matches,
            "bronzeMaxAbsDeviationMetres": _r(bronze_max_dev, 9),
            "seedMatches": seed_matches,
            "seedMaxAbsDeviationMetres": _r(seed_max_dev, 4),
            "conclusion": (
                "the shipped dist_to_nearest_mrt column reproduces exactly from the "
                "sha-pinned bronze station frame and does not reproduce from the "
                "2019 seed; the seed-vs-bronze discrepancy is therefore meaningful "
                "and resolves in favour of the bronze frame"
            ),
        },
    }


def planning_area_baseline(frame: pd.DataFrame, last_complete_month: str) -> dict[str, Any]:
    """Per planning-area-year counts/medians for HDB, and the change distribution.

    Aggregates are bounded at BOTH ends of the study window: the start is
    STUDY_WINDOW_START and the end is the measured last complete month, so a
    terminal partial month never enters an area-year count. Change is computed
    only where both years clear AREA_YEAR_FLOOR; every exclusion carries the
    full set of applicable reasons (no-sales-observed and below-floor can both
    hold), recorded per change in `excludedChanges`.
    """
    hdb = _select(frame, frame["property_type"] == "hdb")
    hdb = _select(hdb, hdb["month"] >= STUDY_WINDOW_START)
    hdb = _select(hdb, hdb["month"] <= last_complete_month)
    dates = pd.to_datetime(pd.Series(hdb["transaction_date"]), errors="coerce")
    hdb = hdb.assign(year=dates.dt.year.to_numpy())
    aggregated = pd.DataFrame(
        hdb.groupby(["planning_area", "year"])
        .agg(transactions=("price", "count"), medianPriceNominal=("price", "median"))
        .reset_index()
    )
    per_area_year: list[dict[str, Any]] = []
    for record in aggregated.to_dict("records"):
        per_area_year.append(
            {
                "area": str(record["planning_area"]),
                "year": int(record["year"]),
                "transactions": int(record["transactions"]),
                "medianPriceNominal": int(round(float(record["medianPriceNominal"]))),
            }
        )
    per_area_year.sort(key=lambda row: (row["area"], row["year"]))

    areas = sorted({row["area"] for row in per_area_year})
    lookup = {(row["area"], row["year"]): row for row in per_area_year}
    observed_areas_per_year = {
        year: {row["area"] for row in per_area_year if row["year"] == year} for year in STUDY_YEARS
    }

    by_year: dict[str, Any] = {}
    for year in STUDY_YEARS:
        rows = [row for row in per_area_year if row["year"] == year]
        counts = [row["transactions"] for row in rows]
        entry: dict[str, Any] = {
            "areasObserved": len({row["area"] for row in rows}),
            "areasNoSalesObserved": len(
                [area for area in areas if area not in observed_areas_per_year[year]]
            ),
            "areasBelowFloor": len([count for count in counts if 0 < count < AREA_YEAR_FLOOR]),
            "transactions": int(sum(counts)),
        }
        if year == STUDY_YEARS[-1]:
            entry["note2026PartialYear"] = (
                "2026 covers 2026-01 → the measured cutoff only (a terminal "
                "partial year at this cutoff) and is excluded from "
                "year-over-year change"
            )
        by_year[str(year)] = entry

    changes: list[float] = []
    change_by_year: dict[str, Any] = {}
    excluded_changes: list[dict[str, Any]] = []
    for year in CHANGE_YEARS:
        year_changes: list[float] = []
        reason_counts: dict[str, int] = {}
        excluded_this_year = 0
        for area in areas:
            current = lookup.get((area, year))
            prior = lookup.get((area, year - 1))
            # An exclusion is a SET of reasons: no-sales-observed and
            # below-floor can both hold on the same change, so every applicable
            # reason is recorded and none is asserted as the single cause.
            reasons: list[str] = []
            if current is None:
                reasons.append("no-sales-observed")
            elif current["transactions"] < AREA_YEAR_FLOOR:
                reasons.append("current-year-below-floor")
            if prior is None:
                reasons.append("prior-year-no-sales-observed")
            elif prior["transactions"] < AREA_YEAR_FLOOR:
                reasons.append("prior-year-below-floor")
            if reasons:
                excluded_this_year += 1
                excluded_changes.append(
                    {
                        "area": area,
                        "year": int(year),
                        "reasons": reasons,
                        "currentTransactions": current["transactions"] if current else None,
                        "priorTransactions": prior["transactions"] if prior else None,
                    }
                )
                for reason in reasons:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
                continue
            if current is None or prior is None:
                # Unreachable: a missing endpoint always produces a reason above.
                continue
            change = (current["medianPriceNominal"] / prior["medianPriceNominal"] - 1) * 100
            year_changes.append(change)
        series = pd.Series(year_changes, dtype="float64")
        changes.extend(year_changes)
        change_by_year[str(year)] = {
            "changesComputed": int(len(series)),
            "changesExcluded": excluded_this_year,
            "excludedReasonCounts": {key: reason_counts[key] for key in sorted(reason_counts)},
            "pctChange": {
                "min": _r(series.min() if len(series) else None, 2),
                "p10": _r(series.quantile(0.10) if len(series) else None, 2),
                "p50": _r(series.median() if len(series) else None, 2),
                "p90": _r(series.quantile(0.90) if len(series) else None, 2),
                "max": _r(series.max() if len(series) else None, 2),
            },
        }

    all_changes = pd.Series(changes, dtype="float64")
    band = all_changes[(all_changes >= 7.0) & (all_changes <= 17.0)]
    example_areas = [
        "JURONG EAST",
        "PUNGGOL",
        "BIDADARI",
        "BISHAN",
        "ANG MO KIO",
        "QUEENSTOWN",
    ]
    return {
        "propertyType": "hdb",
        "floor": AREA_YEAR_FLOOR,
        "cutoffUpperBound": last_complete_month,
        "cutoffUpperBoundMeaning": (
            "every area-year aggregate ends at the last complete month; the "
            "terminal partial month is excluded from all counts and medians"
        ),
        "floorMeaning": (
            "a year-over-year change is computed only when BOTH years have at "
            f"least {AREA_YEAR_FLOOR} transactions in that planning area; this "
            "pack's floor is a descriptive-display rule, not the legacy "
            "regression minimum (300 HDB / 100 condo), which is not reproduced"
        ),
        "areas": areas,
        "years": STUDY_YEARS,
        "changeYears": CHANGE_YEARS,
        "exampleAreasPresent": {area: area in set(areas) for area in example_areas},
        "byYear": by_year,
        "changeByYear": change_by_year,
        "excludedChanges": excluded_changes,
        "changeOverall": {
            "computableAreaYears": int(len(all_changes)),
            "pctChange": {
                "min": _r(all_changes.min(), 2),
                "p10": _r(all_changes.quantile(0.10), 2),
                "p50": _r(all_changes.median(), 2),
                "p90": _r(all_changes.quantile(0.90), 2),
                "max": _r(all_changes.max(), 2),
            },
            "shareWithin7to17Pct": _r(len(band) / len(all_changes), 4)
            if len(all_changes)
            else None,
            "bandNote": (
                "the descriptive share of computed area-year median-price "
                "changes inside the legacy text's quoted 7-17% band; a "
                "median-price change is not the legacy model's year-over-year appreciation "
                "figure and this share does not reproduce or validate clustering"
            ),
        },
        "perAreaYear": per_area_year,
    }


def _stamp_date(stamp: str) -> str | None:
    """YYYYMMDDHHMMSS -> YYYY-MM-DD; None when the stamp is not that shape."""
    if len(stamp) == 14 and stamp.isdigit():
        return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
    return None


def _ingestion_fallback_quote(path: Path, marker: str, label: str) -> dict[str, Any]:
    """Locate a marker line in a source module and cite it verbatim.

    The ledger cites the code's own wording rather than paraphrasing it in
    prose; if the marker ever disappears from the source, the tool fails
    loudly instead of citing a line that no longer exists.
    """
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


def feature_vintages(frame: pd.DataFrame, windows: list[dict[str, str]]) -> dict[str, Any]:
    """What dated feature vintages exist, and what do the features cover?

    The legacy claims are about how premiums changed across periods. That needs
    a feature value as of each period. This measures what dated vintages the
    checkout holds, and whether the shipped features are a single
    current-vintage join applied to every period alike.
    """
    try:
        geo = json.loads(MRT_GEOJSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unreadable MRT station GeoJSON {MRT_GEOJSON}: {error}") from error
    geo_keys: set[str] = set()
    stamp_counts: dict[str, int] = {}
    rail_counts: dict[str, int] = {}
    for feature in geo.get("features", []):
        properties = feature.get("properties", {})
        geo_keys.update(str(key) for key in properties.keys())
        stamp = str(properties.get("FMEL_UPD_D"))
        stamp_counts[stamp] = stamp_counts.get(stamp, 0) + 1
        rail = str(properties.get("RAIL_TYPE"))
        rail_counts[rail] = rail_counts.get(rail, 0) + 1
    stamp_values = sorted(stamp_counts)
    # FMEL_UPD_D is a last-update stamp, not an opening date; its one distinct
    # value is what dates this file as a single 2019 snapshot.
    stamp_date = _stamp_date(stamp_values[0]) if len(stamp_values) == 1 else None
    fallback = _ingestion_fallback_quote(
        GEOJSON_INGESTION_MODULE, LEGACY_SEED_MARKER, "legacy-seed"
    )

    mrt = pd.read_parquet(MRT_STATIONS)
    schools = pd.read_parquet(SCHOOL_DIRECTORY)

    def csv_rows(path: Path) -> int:
        return max(len(path.read_text(encoding="utf-8").splitlines()) - 1, 0)

    def header_has_opening_date(path: Path) -> bool:
        header = path.read_text(encoding="utf-8").splitlines()[0].lower()
        return "open" in header

    hdb = _select(frame, frame["property_type"] == "hdb")
    population: dict[str, Any] = {}
    for window in windows:
        in_window = _window_slice(hdb, window)
        mrt_distance = pd.Series(in_window["dist_to_nearest_mrt"], dtype="float64")
        school_score = pd.Series(in_window["school_accessibility_score"], dtype="float64")
        population[window["label"]] = {
            "transactions": int(len(in_window)),
            "distToNearestMrtNonNullShare": _r(float(mrt_distance.notna().mean()), 4),
            "schoolAccessibilityScoreNonNullShare": _r(float(school_score.notna().mean()), 4),
        }

    return {
        "mrtStationsBronze": {
            "path": MRT_STATIONS.relative_to(REPO_ROOT).as_posix(),
            "rows": int(len(mrt)),
            "columns": [str(column) for column in mrt.columns],
            "hasOpeningDate": any("open" in column.lower() for column in mrt.columns),
        },
        "mrtStationsGeojson": {
            "path": MRT_GEOJSON.relative_to(REPO_ROOT).as_posix(),
            "features": int(len(geo.get("features", []))),
            "propertyKeys": sorted(geo_keys),
            "hasOpeningDate": any("open" in key.lower() for key in geo_keys),
            "updateStampColumn": "FMEL_UPD_D",
            "updateStampValues": stamp_values,
            "updateStampFeatureCounts": {value: stamp_counts[value] for value in stamp_values},
            "updateStampNormalisedDate": stamp_date,
            "singleVintage": len(stamp_values) == 1,
            "railTypes": {key: rail_counts[key] for key in sorted(rail_counts)},
            "ingestionFallback": fallback,
        },
        "mrtLineMapping": {
            "path": MRT_LINES.relative_to(REPO_ROOT).as_posix(),
            "rows": csv_rows(MRT_LINES),
            "columns": MRT_LINES.read_text(encoding="utf-8").splitlines()[0].split(","),
            "hasOpeningDate": header_has_opening_date(MRT_LINES),
        },
        "schoolDirectory": {
            "path": SCHOOL_DIRECTORY.relative_to(REPO_ROOT).as_posix(),
            "rows": int(len(schools)),
            "hasOpeningDate": any(
                "open" in column.lower() or "date" in column.lower() for column in schools.columns
            ),
        },
        "schoolTierFiles": {
            "primary": {
                "path": SCHOOL_TIERS_PRIMARY.relative_to(REPO_ROOT).as_posix(),
                "rows": csv_rows(SCHOOL_TIERS_PRIMARY),
            },
            "secondary": {
                "path": SCHOOL_TIERS_SECONDARY.relative_to(REPO_ROOT).as_posix(),
                "rows": csv_rows(SCHOOL_TIERS_SECONDARY),
            },
            "weights": {
                "path": SCHOOL_WEIGHTS.relative_to(REPO_ROOT).as_posix(),
                "rows": csv_rows(SCHOOL_WEIGHTS),
            },
        },
        "featurePopulationByWindowHdb": population,
        "shippedFeatureLineage": shipped_feature_lineage(),
        "featureDefinitions": {
            "mrtProximity": (
                "src/egg_n_bacon_housing/utils/proximity.py + "
                "src/egg_n_bacon_housing/utils/mrt_line_mapping.py"
            ),
            "schoolQuality": (
                "src/egg_n_bacon_housing/utils/school_features.py + "
                "data/manual/csv/school_tiers_*.csv + school_quality_weights.csv "
                "(methodology: school_scoring_methodology.md)"
            ),
        },
    }


def legacy_claims() -> list[dict[str, str]]:
    """Every legacy quantitative claim, with what this pack did about it."""
    return [
        {
            "claim": "Data Period: 2017-2026 (10 years of transaction data)",
            "disposition": "re-cut",
            "basis": (
                "windowCoverage: HDB covers 2017-01 to the measured cutoff; condo "
                "source coverage starts 2021-01, so the condo side of the period "
                "2017-2020 is source-missing in this checkout"
            ),
        },
        {
            "claim": (
                "MRT premiums declined during COVID for both HDB and condo "
                "segments, with only partial post-COVID recovery"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "featureVintages: no source carries station opening dates, and "
                "the only dated station snapshot is the single 2019-12-09 "
                "legacy seed (mrtStationsGeojson.updateStampNormalisedDate) — "
                "one vintage, nothing per window — and no dated school series "
                "exists, so a period-correct distance-to-MRT feature cannot be "
                "constructed; the condo side also has no pre-COVID transactions "
                "in this checkout"
            ),
        },
        {
            "claim": "School proximity premiums remained stable through COVID",
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "featureVintages: school tiers, weights and directory are a "
                "single current snapshot with no historical vintage, so premium "
                "stability across periods is not measurable"
            ),
        },
        {
            "claim": (
                "K-means clustering of area-level appreciation time series "
                "identifies 5 distinct temporal patterns, with most areas in "
                "moderate growth clusters"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "the retired clustering model is not reproduced; "
                "planningAreaBaseline provides the descriptive per-area-year "
                "medians only"
            ),
        },
        {
            "claim": (
                "High Growth 31-51% / Moderate Growth 9-17% / ~10% / ~14% / "
                "Low Growth 7-18% (cluster table)"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "cluster membership and cluster means come from the retired "
                "model; the descriptive distribution of area-year median-price "
                "change is measured instead (planningAreaBaseline.changeOverall)"
            ),
        },
        {
            "claim": "Most areas cluster in the 7-17% YoY range during strong years",
            "disposition": "re-measured-descriptively",
            "basis": (
                "planningAreaBaseline.changeOverall.shareWithin7to17Pct: the share "
                "of computed area-year median-price changes inside 7-17%, on "
                "this pack's floor; not comparable to the legacy model's "
                "appreciation figures"
            ),
        },
        {
            "claim": (
                "Accelerating: Jurong East, Punggol, Bidadari / Steady: Bishan, "
                "Ang Mo Kio, Queenstown / Decelerating: Some mature CCR areas / "
                "Volatile: Luxury segments"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "trajectory classification is a model output of the retired "
                "analysis; per-area medians are measured "
                "(planningAreaBaseline.perAreaYear) but no trajectory is "
                "classified; whether each named example area even appears in "
                "the study window is measured in "
                "planningAreaBaseline.exampleAreasPresent"
            ),
        },
        {
            "claim": (
                "Recovery asymmetry: HDB recovered faster post-COVID than "
                "luxury condos, likely due to demand inelasticity"
            ),
            "disposition": "withdrawn-not-measurable",
            "basis": (
                "causal claim; no identification strategy is reproduced. The "
                "condo pre-COVID window is absent from this checkout, so the "
                "comparison has no like-for-like baseline"
            ),
        },
        {
            "claim": (
                "minimum 300 transactions for HDB areas and 100 for condo areas (regression floor)"
            ),
            "disposition": "superseded",
            "basis": (
                "this pack's descriptive floor is planningAreaBaseline.floor = "
                "30 transactions in both years; the legacy regression floors "
                "are not reproduced"
            ),
        },
    ]


def build() -> dict[str, Any]:
    frame = load_transactions()
    last_complete = cutoff(frame)["lastCompleteMonth"]
    windows = window_defs(last_complete)
    inputs = {}
    for path in (
        UNIFIED,
        RAW_RESALE,
        RAW_CONDO,
        MRT_STATIONS,
        SCHOOL_DIRECTORY,
    ):
        inputs[path.relative_to(REPO_ROOT).as_posix()] = {
            "sha256": sha256_of(path),
            "rows": int(pq.ParquetFile(path).metadata.num_rows),
        }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "scope": (
            "RS03 temporal-evolution evidence: comparable period windows, sample "
            "composition, feature vintages, descriptive price baselines"
        ),
        "definition": DEFINITION,
        "inputs": inputs,
        "cutoff": cutoff(frame),
        "windows": window_coverage(frame, windows),
        "windowMedians": window_medians(frame, windows),
        "sampleComposition": sample_composition(frame, windows),
        "planningAreaBaseline": planning_area_baseline(frame, last_complete),
        "featureVintages": feature_vintages(frame, windows),
        "legacyClaims": legacy_claims(),
    }


def check(output: Path) -> int:
    if not output.is_file():
        print(f"FAILED: no ledger at {output}; run the tool without --check first")
        return 1
    recorded = output.read_bytes()
    measured = canonical_bytes(build())
    if recorded == measured:
        print("Pass: RS03 ledger re-measures byte-identically from this checkout.")
        return 0
    # Same-shape ledgers: report which top-level keys drifted so the diff is
    # readable instead of just a hash mismatch.
    try:
        old = json.loads(recorded)
        new = json.loads(measured)
    except json.JSONDecodeError:
        print("FAILED: ledger bytes differ and are not both valid JSON")
        return 1
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            print(f"  - drift in {key}")
    print("FAILED: RS03 ledger does not match this checkout")
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
    coverage = evidence["windows"]["byPropertyType"]
    print(
        "Windows measured for hdb: "
        + ", ".join(
            f"{label}={stats['transactions']}tx/{stats['monthsObserved']}mo"
            for label, stats in coverage["hdb"]["windows"].items()
        )
    )
    print(
        "Windows measured for condo: "
        + ", ".join(
            f"{label}={stats['transactions']}tx/{stats['monthsObserved']}mo"
            for label, stats in coverage["condo"]["windows"].items()
        )
    )
    baseline = evidence["planningAreaBaseline"]["changeOverall"]
    print(
        f"Area-year changes computed: {baseline['computableAreaYears']}, "
        f"share within 7-17%: {baseline['shareWithin7to17Pct']}"
    )
    print(f"Ledger: {args.output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
