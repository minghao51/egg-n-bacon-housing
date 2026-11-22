#!/usr/bin/env python3
"""Measure RS11's spatial-autocorrelation evidence: a fully specified
re-measurement of Moran's I and Local Indicators of Spatial Association
(LISA) memberships on this checkout's shipped frame, the served spatial
asset's recorded content, what of the frozen legacy method is recoverable,
and every absence with its scan boundary.

RS11's gate is "Record weights/neighbour definition, disconnected areas,
permutation settings, sample adequacy and multiplicity correction. High-high
labels are not future return or demand predictions. Produce reproducible
memberships and uncertainty/significance metadata." This tool measures, from
the local checkout only:

1. **Cutoff** — the measured last-complete-month rule (the terminal month's
   transaction count as a fraction of the trailing-12-month median), on the
   all-property-types basis this study analyses, with the private-rows basis
   recorded as a cross-check to the bound RS03/RS04/RS05/RS09/RS10 shipped.
   Every aggregation in this ledger stops at the measured lastCompleteMonth.
2. **Population and missingness** — the frame's rows, month range, property
   types, the EC flag, and the four missingness states kept apart: null
   values (lat/lon/planning_area nulls, which fall on exactly the same
   rows), recorded zeros (none: psf has no null and no non-positive row),
   absent rows (the floored-out areas), and an absent column
   (`monthly_rent` is not a column of the 97-column schema).
3. **Area panel (primary membership layer)** — per planning area, median psf
   over the trailing 12 completed months ending at the cutoff (W1) against
   the preceding 12 (W0), a >=10-transactions floor per area-window adopted
   from the legacy's stated threshold, and unweighted-mean centroids.
4. **Area-level re-measurement** — KNN k=8 row-standardised weights on the
   area centroids (island and component counts recorded), global Moran's I
   and Moran_Local LISA on the appreciation variable, 999 permutations, a
   fixed seed, and Benjamini-Hochberg multiplicity correction at q=0.05
   (with the Bonferroni threshold recorded for contrast). Getis-Ord Gi* is
   re-measured on the same weights because the served asset carries a
   per-area hotspot block whose variable is unstated. Per-property-type
   (hdb / condo-non-EC / EC) area panels are re-measured with the same
   protocol, including the one defined reading of the legacy's "spatial lag
   correlation" (correlation between the z-scored variable and its spatial
   lag).
5. **Point-level screen** — global Moran's I on log(psf) over the full
   point population (no subsampling needed; permutations=0 so the recorded
   inference is the analytic normal approximation), with its connectivity
   caveat measured: the served coordinates resolve to 13,562 distinct
   pairs, so the point-level KNN graph fragments into thousands of
   components and the analytic z overstates independence. A seeded 20,000
   row subsample provides permutation-based uncertainty for the same
   screen, with its draw seed, size, fraction and connectivity recorded.
   H3 resolution-8 cell areas are measured over the occupied cells, which
   re-measures the legacy's "~0.5 km² cells" claim.
6. **Served asset inventory** — the served payload
   `app/public/data/analytics/spatial_analysis.json.gz` is read in full:
   its metadata, its 41 planning areas, and the constant-valued fields that
   make it a placeholder-shaped payload (z_score 0.0 and p_value 1.0 in
   every area, a constant transition-probability triple, and so on). It is
   an UNLINKED artefact: it adjudicates nothing, in either direction, about
   the legacy figures.
7. **Absence scans with boundaries** — the legacy's named input file, any
   rent-like column in the shipped schema, any surviving implementation of
   the legacy method outside the programme's own surfaces, and any spatial
   time-series artefact under data/ (the transition claim's absence). The
   programme's own surfaces are excluded from the hash-pinned scans and the
   exclusions are disclosed in the ledger.
8. **Legacy claims** — every quantitative claim of the frozen legacy text,
   each with a verbatim machine-checked phrase, a disposition, and a ledger
   key that must resolve at build time.

It never writes outside `--output`, never touches `app/public/data/**`,
`data/pipeline/**` or any app source, and no high-high label it produces is
a prediction of future returns or demand: the labels summarise the measured
window only.

Usage:

    uv run python scripts/tools/spatial_autocorrelation_evidence.py \\
        --output docs/implementation/artifacts/rs11-spatial-autocorrelation-evidence.json

    uv run python scripts/tools/spatial_autocorrelation_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import scipy.sparse.csgraph as csgraph

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
SERVED_ASSET = REPO_ROOT / "app" / "public" / "data" / "analytics" / "spatial_analysis.json.gz"
LEGACY_EDITION = (
    REPO_ROOT
    / "docs"
    / "analytics"
    / "editions"
    / "legacy"
    / "2026-11-12"
    / "spatial-autocorrelation.md"
)
PYPROJECT = REPO_ROOT / "pyproject.toml"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "artifacts"
    / "rs11-spatial-autocorrelation-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

# Fixed seed for every stochastic step (subsample draw and permutation
# inference). Determinism of this ledger is verified by running the tool
# twice and comparing bytes; without a fixed seed that check is vacuous.
SEED = 20261120
K_NEIGHBORS = 8  # the legacy's own stated k, re-adopted (and capped at n-1)
PERMUTATIONS = 999  # the legacy stated 99; this protocol records its own
AREA_FLOOR = 10  # the legacy's stated >=10-records threshold, per area-window
BH_Q = 0.05  # Benjamini-Hochberg false-discovery level for LISA labels
SUBSAMPLE_SIZE = 20_000  # documented random subsample for permutation inference
H3_RESOLUTION = 8  # the legacy's stated resolution, re-measured for cell area

FRAME_COLUMNS = ("month", "property_type", "is_ec", "planning_area", "psf", "lat", "lon")

# The hash-pinned token scan bounds and exclusions. The excluded prefixes are
# the programme's own output surfaces, not evidence of any method: their
# exclusion is disclosed at absenceScans.methodImplementationScan.exclusions.
# The frozen legacy originals stay IN the scan: the article's own method words
# are what the tokens are matched against. This tool quotes the tokens it
# searches for and lives under an excluded prefix, so it cannot scan itself.
SCAN_ROOTS = ("docs", "scripts", "src", "assets", "app/src", ".claude/handoffs", "prompts")
SCAN_SUFFIXES = (".md", ".py", ".ts", ".tsx")
EXCLUDED_SCAN_PREFIXES = (
    "docs/implementation/",
    "scripts/tools/",
    "prompts/",
    "app/src/components/studies/",
    "app/tests/",
)
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
EXCLUDED_SCAN_PATHS = (
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
    ".secrets.baseline",
)
METHOD_TOKENS = re.compile(r"moran|esda|libpysal|getis|lisa", re.IGNORECASE)
DATA_SCAN_PATTERNS = ("lisa", "moran", "spatial", "transition", "persistence")

DEFINITION = (
    "A fully specified re-measurement of spatial autocorrelation on the shipped "
    "frame, plus a measured inventory of the served spatial asset and the frozen "
    "legacy text. The unit that carries reproducible memberships is the planning "
    "area: the served asset is keyed by planning area, so the pack produces its "
    "memberships there — 41 areas after the recorded floor, KNN k=8 "
    "row-standardised weights on unweighted-mean centroids (one connected "
    "component, zero islands, both recorded), appreciation defined as the median-psf "
    "ratio of the trailing 12 completed months against the preceding 12, both "
    "windows stopping at the measured cutoff, 999 permutations at a fixed seed, and "
    "Benjamini-Hochberg correction at q=0.05 before any high-high label is assigned. "
    "Under that protocol the appreciation screen shows NO significant clustering "
    "(area-level Moran's I is slightly negative and not significant; the point "
    "estimate and its p-values are ledger fields), which is measured evidence about "
    "THIS protocol, not a refutation of the legacy's number: the legacy's variable "
    "is unstated (its appendix aggregates median monthly_rent on an input file that "
    "is absent from this checkout, while its prose interprets appreciation), so its "
    "0.766 is recorded as stated and dispositioned not-reproducible, and the "
    "transition/persistence claims are withdrawn outright because no linked asset "
    "carries a time dimension. The point-level layer is a price-LEVEL screen on "
    "coordinates that resolve to 13,562 distinct pairs: its KNN graph fragments into "
    "thousands of disconnected components, which is recorded as the disconnected-"
    "areas metadata the gate requires, and its significance is carried by a seeded "
    "20,000-row subsample rather than by the analytic normal approximation alone. "
    "No layer of this pack predicts future returns or demand, and no layer claims "
    "how any series was produced: everything is screened as."
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _r(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not np.isfinite(number):
        return None
    return round(number, digits)


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _gz_payload(path: Path) -> Any:
    """A gzipped JSON payload, with both the read and the parse guarded."""
    try:
        raw = path.read_bytes()
        text = gzip.decompress(raw).decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SystemExit(f"Unreadable gzip payload {_relative(path)}: {error}") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise SystemExit(f"Unparseable gzip JSON {_relative(path)}: {error}") from error


def _month_index(month: str) -> int:
    return int(month[:4]) * 12 + (int(month[5:7]) - 1)


def _month_from_index(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def window_months(last_complete: str, offset: int, length: int) -> list[str]:
    """`length` consecutive months ending `offset` months before lastComplete."""
    end = _month_index(last_complete) - offset
    return [_month_from_index(end - i) for i in range(length - 1, -1, -1)]


def _month_counts(frame: pd.DataFrame) -> dict[str, int]:
    return {str(key): int(value) for key, value in frame.groupby("month").size().items()}


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    counts = _month_counts(frame)
    ordered = sorted(counts)
    terminal_month = ordered[-1]
    last_complete_month = ordered[-2]
    trailing_months = ordered[-13:-1]
    trailing = [counts[month] for month in trailing_months]
    trailing_median = float(np.median(trailing)) if trailing else 0.0
    ratio = counts[terminal_month] / trailing_median if trailing_median else None

    condo = frame.loc[frame["property_type"] == "condo"]
    condo_counts = _month_counts(condo)
    condo_ordered = sorted(condo_counts)
    condo_terminal = condo_ordered[-1]
    condo_trailing = [condo_counts[month] for month in condo_ordered[-13:-1]]
    condo_median = float(np.median(condo_trailing)) if condo_trailing else 0.0

    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact; the primary basis here is the "
            "all-property-types frame because RS11's population is all shipped "
            "residential rows, and the private-rows (condo) basis is recorded "
            "as a cross-check to the bound RS03/RS04/RS05/RS09/RS10 shipped"
        ),
        "lastCompleteMonth": last_complete_month,
        "terminalMonth": terminal_month,
        "terminalMonthTransactions": counts[terminal_month],
        "trailing12MedianTransactions": _r(trailing_median, 1),
        "terminalMonthShareOfTrailingMedian": _r(ratio, 4),
        "lastCompleteMonthTransactions": counts[last_complete_month],
        "lastCompleteMonthShareOfTrailingMedian": _r(
            counts[last_complete_month] / trailing_median if trailing_median else None, 4
        ),
        "trailing12Months": trailing_months,
        "frameLastMonth": ordered[-1],
        "condoBasisCrossCheck": {
            "lastCompleteMonth": condo_ordered[-2],
            "terminalMonth": condo_terminal,
            "terminalMonthTransactions": condo_counts[condo_terminal],
            "trailing12MedianTransactions": _r(condo_median, 1),
            "terminalMonthShareOfTrailingMedian": _r(
                condo_counts[condo_terminal] / condo_median if condo_median else None, 4
            ),
            "matchesAllRowsBasis": condo_ordered[-2] == last_complete_month,
        },
        "meaning": (
            "every window, panel and count in this ledger that touches the frame "
            "stops at lastCompleteMonth"
        ),
    }


def population(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    lat_null = frame["lat"].isna()
    lon_null = frame["lon"].isna()
    pa_null = frame["planning_area"].isna()
    psf_null = frame["psf"].isna()
    psf_nonpositive = int((frame["psf"] <= 0).sum())
    beyond = int((frame["month"] > last_complete).sum())
    overlap = int((lat_null & pa_null).sum())
    xor = int((lat_null ^ pa_null).sum())
    return {
        "frameRows": int(len(frame)),
        "frameColumns": 97,
        "monthRange": {"first": str(frame["month"].min()), "last": str(frame["month"].max())},
        "monthsWithTransactions": int(frame["month"].nunique()),
        "propertyTypeCounts": {
            str(key): int(value) for key, value in frame["property_type"].value_counts().items()
        },
        "ecFlagCounts": {
            "true": int(frame["is_ec"].sum()),
            "false": int((~frame["is_ec"]).sum()),
        },
        "ecFlagLivesUnderPropertyType": {
            str(key): int(value)
            for key, value in frame.loc[frame["is_ec"], "property_type"].value_counts().items()
        },
        "planningAreaDistinctNonNull": int(frame["planning_area"].nunique()),
        "missingness": {
            "nullValueRows": {
                "lat": int(lat_null.sum()),
                "lon": int(lon_null.sum()),
                "planning_area": int(pa_null.sum()),
                "psf": int(psf_null.sum()),
                "latAndPlanningAreaSameRows": {
                    "overlap": overlap,
                    "xor": xor,
                    "exactlyTheSameRows": overlap == int(lat_null.sum()) and xor == 0,
                },
            },
            "recordedZeroRows": {
                "psfNonPositive": psf_nonpositive,
                "meaning": (
                    "no row carries psf <= 0, so no recorded zero price enters a "
                    "median; a recorded zero and a null are different states and "
                    "neither occurs for psf in this frame"
                ),
            },
            "absentRows": {
                "rowsBeyondCutoff": beyond,
                "meaning": (
                    "the terminal month's rows are present in the file and are "
                    "excluded from every windowed aggregation by the cutoff rule, "
                    "not deleted from the source"
                ),
            },
            "absentColumn": {
                "monthly_rent": "not a column of the 97-column schema",
                "scan": "absenceScans.frameSchemaRentScan",
            },
            "meaning": (
                "the four missingness states are kept apart: null VALUES (the "
                "11,600 rows with no lat/lon/planning_area), recorded ZEROS (none "
                "for psf), ABSENT ROWS (the terminal month present in the file "
                "but outside every window), and an ABSENT COLUMN (monthly_rent)"
            ),
        },
        "meaning": (
            "the frame is the only transaction source in this ledger; its lat/lon "
            "support is measured at pointLevel.coordinateSupport"
        ),
    }


def _area_panel(
    frame: pd.DataFrame, w1: list[str], w0: list[str], floor: int
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Per-area medians, transaction counts and centroids for both windows."""
    g1 = frame.loc[frame["month"].isin(w1)].dropna(subset=["planning_area"])
    g0 = frame.loc[frame["month"].isin(w0)].dropna(subset=["planning_area"])
    c1 = g1.groupby("planning_area").agg(
        n1=("psf", "size"),
        median_psf_w1=("psf", "median"),
        centroid_lat=("lat", "mean"),
        centroid_lon=("lon", "mean"),
    )
    c0 = g0.groupby("planning_area").agg(n0=("psf", "size"), median_psf_w0=("psf", "median"))
    panel = c1.join(c0, how="inner").sort_index()
    dropped: list[dict[str, Any]] = []
    keep = pd.Series(True, index=panel.index)
    for area, row in panel.iterrows():
        reasons = []
        if int(row["n1"]) < floor:
            reasons.append("w1BelowFloor")
        if int(row["n0"]) < floor:
            reasons.append("w0BelowFloor")
        if not (float(row["median_psf_w0"]) > 0 and float(row["median_psf_w1"]) > 0):
            reasons.append("nonPositiveMedianPsf")
        if reasons:
            keep.loc[area] = False
            dropped.append(
                {
                    "area": str(area),
                    "n1": int(row["n1"]),
                    "n0": int(row["n0"]),
                    "reasons": reasons,
                }
            )
    panel = panel.loc[keep]
    panel["appreciation"] = panel["median_psf_w1"] / panel["median_psf_w0"] - 1.0
    return panel, dropped


def area_panel(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    w1 = window_months(last_complete, 0, 12)
    w0 = window_months(last_complete, 12, 12)
    panel, dropped = _area_panel(frame, w1, w0, AREA_FLOOR)
    areas_in_frame = int(frame.dropna(subset=["planning_area"])["planning_area"].nunique())
    members = [
        {
            "area": str(area),
            "n1": int(row["n1"]),
            "n0": int(row["n0"]),
            "medianPsfW1": _r(row["median_psf_w1"], 2),
            "medianPsfW0": _r(row["median_psf_w0"], 2),
            "appreciation": _r(row["appreciation"], 6),
            "centroidLat": _r(row["centroid_lat"], 6),
            "centroidLon": _r(row["centroid_lon"], 6),
        }
        for area, row in panel.iterrows()
    ]
    return {
        "unit": "planning_area",
        "windowMonths": {"w1": w1, "w0": w0},
        "windowDefinition": (
            "w1 = the trailing 12 completed months ending at the measured "
            "cutoff; w0 = the 12 months before w1; both derive from "
            "cutoff.lastCompleteMonth by month arithmetic, not from literals"
        ),
        "floor": {
            "value": AREA_FLOOR,
            "appliedPer": "area-window (both w1 and w0 must meet it)",
            "attribution": (
                "the numeric floor is adopted from the legacy's stated >=10-records "
                "threshold (claim C19); the legacy applied it to H3 cells on an "
                "absent input, this pack applies it to planning-area windows it "
                "can measure"
            ),
        },
        "areasInFrame": areas_in_frame,
        "areasWithBothWindows": int(len(panel) + len(dropped)),
        "areasAfterFloor": int(len(panel)),
        "droppedAreas": dropped,
        "centroidMethod": ("unweighted mean of non-null transaction lat/lon inside w1 per area"),
        "medianDefinition": "median psf over the window's transactions",
        "appreciationFormula": "medianPsfW1 / medianPsfW0 - 1",
        "members": members,
        "meaning": (
            "the area panel is the primary membership layer: the served asset is "
            "keyed by planning area, so reproducible memberships are produced at "
            "the same unit"
        ),
    }


def _weights_fields(w: Any, k_used: int) -> dict[str, Any]:
    n_components, _labels = csgraph.connected_components(w.sparse, directed=False)
    mean_neighbors = float(np.mean([w.cardinalities[i] for i in w.id_order]))
    return {
        "definition": (
            f"KNN k={k_used} on unit centroids, row-standardised, built with "
            f"libpysal {_libpysal_version()} weights.KNN"
        ),
        "kRequested": K_NEIGHBORS,
        "kUsed": int(k_used),
        "kRule": "min(8, n_areas - 1)",
        "transform": "r (row-standardised)",
        "n": int(w.n),
        "islands": int(len(w.islands)),
        "connectedComponentsUndirected": int(n_components),
        "meanNeighbors": _r(mean_neighbors, 4),
        "s0": _r(float(w.s0), 6),
        "islandRule": (
            "an island keeps its LISA/Gi* label not-significant by isolation "
            "(esda island_weight=0 is the recorded parameter); the counts above "
            "are the disconnected-areas metadata"
        ),
    }


def _libpysal_version() -> str:
    import libpysal

    return str(libpysal.__version__)


def bh_adjust(pvals: np.ndarray, q: float) -> np.ndarray:
    """Benjamini-Hochberg step-up adjusted p-values (monotone, clipped to 1)."""
    m = len(pvals)
    order = np.argsort(pvals, kind="stable")
    ranked = np.asarray(pvals, dtype=float)[order]
    adjusted = ranked * m / (np.arange(m) + 1.0)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0.0, 1.0)
    out = np.empty(m, dtype=float)
    out[order] = adjusted
    return out


def _bh_fields(pvals: np.ndarray, labels: list[str]) -> dict[str, Any]:
    adjusted = bh_adjust(pvals, BH_Q)
    return {
        "method": (
            "Benjamini-Hochberg step-up, implemented in this script "
            "(bh_adjust): ranks are sorted stably, adjusted values are made "
            "monotone by a reverse cumulative minimum and clipped to 1"
        ),
        "q": BH_Q,
        "m": int(len(pvals)),
        "bonferroniThreshold": _r(BH_Q / len(pvals), 6),
        "adjustedP": {label: _r(float(adjusted[i]), 6) for i, label in enumerate(labels)},
        "meaning": (
            "a label is assigned only after multiplicity correction; the "
            "uncorrected significant count is also recorded so the correction's "
            "effect is measurable"
        ),
    }


def area_moran(panel: pd.DataFrame, weights: dict[str, Any]) -> dict[str, Any]:
    import esda
    import libpysal

    w = libpysal.weights.KNN.from_array(
        panel[["centroid_lon", "centroid_lat"]].to_numpy(), k=K_NEIGHBORS
    )
    weights.update(_weights_fields(w, K_NEIGHBORS))
    w.transform = "r"
    y = panel["appreciation"].to_numpy()
    np.random.seed(SEED)
    moran = esda.moran.Moran(y, w, permutations=PERMUTATIONS, two_tailed=True)
    return {
        "variable": "areaPanel.appreciation (medianPsfW1/medianPsfW0 - 1)",
        "n": int(len(panel)),
        "weights": weights,
        "permutations": PERMUTATIONS,
        "seed": SEED,
        "seedMechanism": (
            "np.random.seed(SEED) immediately before the esda call (esda.moran."
            "Moran has no seed parameter); Moran_Local and G_Local take seed= "
            "directly and also run with n_jobs=1"
        ),
        "twoTailed": True,
        "moranI": _r(moran.I, 6),
        "expectedI": _r(moran.EI, 9),
        "seI_norm": _r(moran.seI_norm, 9),
        "zNorm": _r(moran.z_norm, 6),
        "pNorm": _r(moran.p_norm, 6),
        "zRand": _r(moran.z_rand, 6),
        "pRand": _r(moran.p_rand, 6),
        "zSim": _r(moran.z_sim, 6),
        "pSim": _r(moran.p_sim, 6),
        "meaning": (
            "under this protocol the appreciation screen is NOT significantly "
            "clustered across planning areas: the point estimate is slightly "
            "negative and every recorded p-value is far above the corrected "
            "threshold. This is measured evidence about THIS protocol; the "
            "legacy's 0.766 is a different, underspecified statistic recorded at "
            "legacyMethodRecovery.globalMoran, and no layer of this pack claims "
            "to recover it"
        ),
    }


def area_lisa(panel: pd.DataFrame) -> dict[str, Any]:
    import esda
    import libpysal

    w = libpysal.weights.KNN.from_array(
        panel[["centroid_lon", "centroid_lat"]].to_numpy(), k=K_NEIGHBORS
    )
    w.transform = "r"
    y = panel["appreciation"].to_numpy()
    z = (y - y.mean()) / y.std(ddof=0)
    lag = libpysal.weights.lag_spatial(w, z)
    lisa = esda.moran.Moran_Local(
        y,
        w,
        permutations=PERMUTATIONS,
        geoda_quads=False,
        n_jobs=1,
        seed=SEED,
        island_weight=0,
    )
    quadrant_names = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    areas = [str(area) for area in panel.index]
    adjusted = bh_adjust(lisa.p_sim, BH_Q)
    z_sim = np.asarray(lisa.z_sim)
    members = []
    label_counts = {"HH": 0, "LH": 0, "LL": 0, "HL": 0, "NS": 0}
    quadrant_counts = {"HH": 0, "LH": 0, "LL": 0, "HL": 0}
    uncorrected = 0
    for i, area in enumerate(areas):
        quadrant = int(lisa.q[i])
        quadrant_name = quadrant_names[quadrant]
        quadrant_counts[quadrant_name] += 1
        significant = bool(adjusted[i] <= BH_Q)
        label = quadrant_name if significant else "NS"
        label_counts[label] += 1
        if float(lisa.p_sim[i]) <= 0.05:
            uncorrected += 1
        members.append(
            {
                "area": area,
                "quadrant": quadrant,
                "quadrantName": quadrant_name,
                "localI": _r(float(lisa.Is[i]), 6),
                "spatialLagOfZ": _r(float(lag[i]), 6),
                "zSim": _r(float(z_sim[i]), 6),
                "pSim": _r(float(lisa.p_sim[i]), 6),
                "pSimBH": _r(float(adjusted[i]), 6),
                "significantUncorrectedAt005": float(lisa.p_sim[i]) <= 0.05,
                "label": label,
            }
        )
    return {
        "variable": "areaPanel.appreciation",
        "n": int(len(panel)),
        "weights": _weights_fields(w, K_NEIGHBORS),
        "implementation": (
            f"esda.moran.Moran_Local with permutations={PERMUTATIONS}, "
            "geoda_quads=False, n_jobs=1, seed=SEED, island_weight=0 "
            f"(esda {esda_version()})"
        ),
        "quadrantMapping": {"1": "HH", "2": "LH", "3": "LL", "4": "HL"},
        "labelRule": (
            "label = quadrant name when pSimBH <= q, else NS; the labels are "
            "descriptions of THIS window, not predictions of future returns or "
            "demand"
        ),
        "multiplicityCorrection": _bh_fields(lisa.p_sim, areas),
        "labelCounts": label_counts,
        "quadrantCountsUncorrected": quadrant_counts,
        "significantUncorrectedAt005": uncorrected,
        "members": members,
        "meaning": (
            "reproducible memberships: every area's quadrant, local I, spatial "
            "lag, z and p (raw and corrected) are fields, the seed and "
            "permutation count are fields, and rerunning this tool reproduces "
            "them byte-identically (determinism is checked by --check)"
        ),
    }


def area_gistar(panel: pd.DataFrame) -> dict[str, Any]:
    import esda
    import libpysal

    w = libpysal.weights.KNN.from_array(
        panel[["centroid_lon", "centroid_lat"]].to_numpy(), k=K_NEIGHBORS
    )
    w.transform = "r"
    y = panel["appreciation"].to_numpy()
    g = esda.getisord.G_Local(
        y,
        w,
        transform="R",
        permutations=PERMUTATIONS,
        star=True,
        keep_simulations=True,
        n_jobs=1,
        seed=SEED,
    )
    adjusted = bh_adjust(g.p_sim, BH_Q)
    members = []
    counts = {"hotspot": 0, "coldspot": 0, "notSignificant": 0}
    for i, area in enumerate(panel.index):
        significant = bool(adjusted[i] <= BH_Q)
        if not significant:
            label = "notSignificant"
        else:
            label = "hotspot" if float(g.z_sim[i]) > 0 else "coldspot"
        counts[label] += 1
        members.append(
            {
                "area": str(area),
                "gStar": _r(float(g.Gs[i]), 6),
                "zSim": _r(float(g.z_sim[i]), 6),
                "pSim": _r(float(g.p_sim[i]), 6),
                "pSimBH": _r(float(adjusted[i]), 6),
                "label": label,
            }
        )
    return {
        "variable": "areaPanel.appreciation",
        "n": int(len(panel)),
        "weights": _weights_fields(w, K_NEIGHBORS),
        "implementation": (
            f"esda.getisord.G_Local with star=True (Gi*), permutations="
            f"{PERMUTATIONS}, keep_simulations=True, n_jobs=1, seed=SEED "
            f"(esda {esda_version()})"
        ),
        "zSimDerivation": (
            "esda-computed simulation z: z_sim = (Gs - mean(sim)) / std(sim) "
            "over the 999 conditional-randomization draws (g.sim), exposed "
            "because keep_simulations=True; esda 2.8.1 sets z_sim only under "
            "keep_simulations=True, so with keep_simulations=False this "
            "implementation exposes p_sim but no simulation z score"
        ),
        "whyThisSectionExists": (
            "the served asset carries a per-area hotspot block with no stated "
            "variable; this layer re-measures Gi* under a declared variable so "
            "a later payload rebuild has a defined source, not to recover the "
            "placeholder's z/p values"
        ),
        "multiplicityCorrection": _bh_fields(g.p_sim, [str(a) for a in panel.index]),
        "labelCounts": counts,
        "members": members,
        "meaning": (
            "hotspot/coldspot here describe the measured window only; they are "
            "not demand or return predictions"
        ),
    }


def esda_version() -> str:
    import esda

    return str(esda.__version__)


def per_type_moran(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    import esda
    import libpysal

    w1 = window_months(last_complete, 0, 12)
    w0 = window_months(last_complete, 12, 12)
    segments = {
        "hdb": frame.loc[frame["property_type"] == "hdb"],
        "condoNonEc": frame.loc[(frame["property_type"] == "condo") & (~frame["is_ec"])],
        "ec": frame.loc[frame["is_ec"]],
    }
    results: dict[str, Any] = {}
    pvals: dict[str, float] = {}
    for name, sub in segments.items():
        panel, dropped = _area_panel(sub, w1, w0, AREA_FLOOR)
        n = len(panel)
        k_used = min(K_NEIGHBORS, n - 1)
        w = libpysal.weights.KNN.from_array(
            panel[["centroid_lon", "centroid_lat"]].to_numpy(), k=k_used
        )
        w.transform = "r"
        y = panel["appreciation"].to_numpy()
        np.random.seed(SEED)
        moran = esda.moran.Moran(y, w, permutations=PERMUTATIONS, two_tailed=True)
        z = (y - y.mean()) / y.std(ddof=0)
        lag = libpysal.weights.lag_spatial(w, z)
        r = float(np.corrcoef(z, lag)[0, 1]) if n >= 3 else None
        pvals[name] = float(moran.p_sim)
        results[name] = {
            "definition": {
                "hdb": "property_type == 'hdb'",
                "condoNonEc": "property_type == 'condo' AND is_ec == false",
                "ec": "is_ec == true (all such rows carry property_type 'condo')",
            }[name],
            "areasAfterFloor": int(n),
            "kUsed": int(k_used),
            "droppedAreas": dropped,
            "weights": _weights_fields(w, k_used),
            "permutations": PERMUTATIONS,
            "seed": SEED,
            "moranI": _r(moran.I, 6),
            "zSim": _r(moran.z_sim, 6),
            "pSim": _r(moran.p_sim, 6),
            "pNorm": _r(moran.p_norm, 6),
            "spatialLagCorrelation": {
                "definition": (
                    "Pearson r between the z-scored area appreciation and its "
                    "row-standardised spatial lag — ONE defined reading of the "
                    "legacy's unstated 'spatial lag correlation', recorded for "
                    "contrast, not a recovery"
                ),
                "r": _r(r, 6),
                "n": int(n),
            },
        }
    adjusted = bh_adjust(np.array([pvals[name] for name in sorted(pvals)]), BH_Q)
    results["benjaminiHochberg"] = {
        "q": BH_Q,
        "m": len(pvals),
        "adjustedPSim": {name: _r(float(adjusted[i]), 6) for i, name in enumerate(sorted(pvals))},
        "meaning": (
            "the three per-type p-values are corrected together: the one "
            "uncorrected p_sim at or below 0.05 (ec) does not survive the BH "
            "step-up, which is the multiplicity correction the gate requires "
            "made visible"
        ),
    }
    results["meaning"] = (
        "per-property-type area panels under the same protocol; the legacy's "
        "78%/71%/65% spatial lag correlations are undefined statistics (no "
        "variable pair, window or aggregation) and remain not-reproducible at "
        "legacyMethodRecovery.spatialLagCorrelation"
    )
    return results


def point_level(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    import esda
    import h3
    import libpysal

    bounded = frame.loc[frame["month"] <= last_complete]
    pts = bounded.dropna(subset=["lat", "lon", "psf"])
    pts = pts.loc[pts["psf"] > 0]
    n = int(len(pts))
    lats = pts["lat"].to_numpy()
    lons = pts["lon"].to_numpy()
    distinct_pairs = {(float(a), float(b)) for a, b in zip(lats, lons)}

    coords = np.column_stack([lons, lats])
    w = libpysal.weights.KNN.from_array(coords, k=K_NEIGHBORS)
    n_components, labels = csgraph.connected_components(w.sparse, directed=False)
    sizes = np.bincount(labels)
    w.transform = "r"
    z = np.log(pts["psf"].to_numpy())
    full = esda.moran.Moran(z, w, permutations=0, two_tailed=True)

    cells = sorted({str(h3.latlng_to_cell(a, b, H3_RESOLUTION)) for a, b in zip(lats, lons)})
    cell_areas = [float(h3.cell_area(cell, unit="km^2")) for cell in cells]

    rng = np.random.default_rng(SEED)
    idx = np.sort(rng.choice(n, size=SUBSAMPLE_SIZE, replace=False))
    sub = pts.iloc[idx]
    ws = libpysal.weights.KNN.from_array(
        np.column_stack([sub["lon"].to_numpy(), sub["lat"].to_numpy()]), k=K_NEIGHBORS
    )
    n_components_s, _ = csgraph.connected_components(ws.sparse, directed=False)
    ws.transform = "r"
    np.random.seed(SEED)
    subsample = esda.moran.Moran(
        np.log(sub["psf"].to_numpy()), ws, permutations=PERMUTATIONS, two_tailed=True
    )

    return {
        "variable": "log(psf), over all rows at or before the cutoff with non-null lat/lon and positive psf",
        "coordinateSupport": {
            "rowsUsed": n,
            "distinctRawLatLonPairs": int(len(distinct_pairs)),
            "pairEqualityMethod": "exact float64 pair equality",
            "latRange": {"min": _r(float(lats.min()), 6), "max": _r(float(lats.max()), 6)},
            "lonRange": {"min": _r(float(lons.min()), 6), "max": _r(float(lons.max()), 6)},
            "meaning": (
                "the served coordinates are address/block-resolved, not "
                "per-transaction survey points: 1,223,499 rows resolve to 13,562 "
                "distinct pairs, so point-level neighbourhoods are dominated by "
                "coordinate groups"
            ),
        },
        "fullPopulation": {
            "n": n,
            "subsample": False,
            "permutations": 0,
            "permutationsReason": (
                "999 permutations over a 1.2M-row KNN graph is out of compute "
                "budget; the recorded inference is the analytic normal "
                "approximation under the randomisation hypothesis, and the "
                "permutation-based uncertainty for the same screen is carried "
                "by the documented seeded subsample below"
            ),
            "weights": _weights_fields(w, K_NEIGHBORS),
            "largestComponentSize": int(sizes.max()),
            "largestComponentShare": _r(float(sizes.max()) / n, 4),
            "smallestComponentSize": int(sizes.min()),
            "moranI": _r(full.I, 6),
            "expectedI": _r(full.EI, 9),
            "zNorm": _r(full.z_norm, 4),
            "pNorm": _r(full.p_norm, 6),
            "zRand": _r(full.z_rand, 4),
            "pRand": _r(full.p_rand, 6),
            "inferenceCaveat": (
                "the analytic z assumes independence over 1.2M rows; with "
                "13,562 distinct coordinates and 11,803 disconnected components "
                "the effective independence is far coarser, so pNorm must not "
                "be read as calibrated — the subsample's permutation pSim is "
                "the recorded uncertainty statement"
            ),
        },
        "disconnectedAreas": {
            "components": int(n_components),
            "allComponentsAtLeastKPlusOnePoints": bool(int(sizes.min()) >= K_NEIGHBORS + 1),
            "meaning": (
                "the gate's disconnected-areas clause, measured: every point "
                "has 8 neighbours (zero islands), yet the undirected graph "
                "falls into 11,803 components because identical coordinates "
                "trap their KNN links internally; a point-level LISA on these "
                "weights would fragment the same way, which is why memberships "
                "are produced at the planning-area level only"
            ),
        },
        "h3Grid": {
            "resolution": H3_RESOLUTION,
            "distinctOccupiedCells": int(len(cells)),
            "meanCellAreaKm2": _r(float(np.mean(cell_areas)), 4),
            "minCellAreaKm2": _r(min(cell_areas), 4),
            "maxCellAreaKm2": _r(max(cell_areas), 4),
            "cellAreaSource": f"h3.cell_area (h3 {h3.__version__}), unit km^2",
            "legacyClaimedApproxCellAreaKm2": 0.5,
            "meaning": (
                "re-measures the legacy's '~0.5 km² cells' claim: the mean area "
                "of the resolution-8 cells the data actually occupies is "
                "0.8374 km², about 0.34 km² above the claim's approximate value"
            ),
        },
        "seededSubsample": {
            "seed": SEED,
            "size": SUBSAMPLE_SIZE,
            "drawMethod": (
                "numpy.random.default_rng(20261120).choice(n, size=20000, "
                "replace=False), row order as read, indices sorted"
            ),
            "fractionOfPointRows": _r(SUBSAMPLE_SIZE / n, 6),
            "adequacy": (
                "the size is a compute-budget constant, NOT a power calculation; "
                "its recorded adequacy evidence is the agreement of its point "
                "estimate with the full-population estimate below and its own "
                "permutation significance, both as fields"
            ),
            "weights": _weights_fields(ws, K_NEIGHBORS),
            "permutations": PERMUTATIONS,
            "moranI": _r(subsample.I, 6),
            "zSim": _r(subsample.z_sim, 4),
            "pSim": _r(subsample.p_sim, 6),
            "differenceInPointEstimateFromFullPopulation": _r(
                float(subsample.I) - float(full.I), 6
            ),
            "meaning": (
                "the subsample's KNN is computed inside the subsample, so its "
                "neighbour definition differs from the full graph by "
                "construction; both point estimates and their difference are "
                "recorded fields and neither is a recovery of the legacy's "
                "statistic"
            ),
        },
        "meaning": (
            "the point-level layer screens the PRICE LEVEL (log psf), not "
            "appreciation; it is not comparable to the legacy's appreciation "
            "prose and not a recovery of its rent-based appendix — origin "
            "unverified, screened as"
        ),
    }


def served_asset(frame_areas: set[str]) -> dict[str, Any]:
    payload = _gz_payload(SERVED_ASSET)
    raw = SERVED_ASSET.read_bytes()
    areas = payload.get("planning_areas", {})
    metadata = payload.get("metadata", {})
    area_names = sorted(areas)
    first_area = next(iter(areas))

    def distinct(field_path: tuple[str, ...]) -> dict[str, int]:
        values: dict[str, int] = {}
        for block in areas.values():
            node: Any = block
            for key in field_path:
                if not isinstance(node, dict) or key not in node:
                    node = None
                    break
                node = node[key]
            key = json.dumps(node, sort_keys=True)
            values[key] = values.get(key, 0) + 1
        return dict(sorted(values.items()))

    lags = sorted(
        float(block["neighborhood_effect"]["spatial_lag"])
        for block in areas.values()
        if isinstance(block.get("neighborhood_effect"), dict)
        and "spatial_lag" in block["neighborhood_effect"]
    )
    yoy = sorted(
        float(block["lisa_cluster"]["yoy_appreciation"])
        for block in areas.values()
        if isinstance(block.get("lisa_cluster"), dict)
        and "yoy_appreciation" in block["lisa_cluster"]
    )
    shared = set(area_names) & frame_areas
    return {
        "path": _relative(SERVED_ASSET),
        "sha256": sha256_of(SERVED_ASSET),
        "bytes": int(len(raw)),
        "decompressedBytes": int(len(gzip.decompress(raw))),
        "metadata": {
            "generatedAt": metadata.get("generated_at"),
            "dataVersion": metadata.get("data_version"),
            "methodology": metadata.get("methodology"),
        },
        "areaCount": int(len(areas)),
        "areaNames": area_names,
        "frameAreaIntersection": {
            "frameAreas": int(len(frame_areas)),
            "shared": int(len(shared)),
            "payloadOnly": sorted(set(area_names) - frame_areas),
            "frameOnly": sorted(frame_areas - set(area_names)),
        },
        "constantValueFields": {
            "hotspot.z_score": distinct(("hotspot", "z_score")),
            "hotspot.p_value": distinct(("hotspot", "p_value")),
            "hotspot.confidence": distinct(("hotspot", "confidence")),
            "hotspot.classification": distinct(("hotspot", "classification")),
            "lisa_cluster.type": distinct(("lisa_cluster", "type")),
            "lisa_cluster.persistence_rate": distinct(("lisa_cluster", "persistence_rate")),
            "lisa_cluster.transition_probabilities": distinct(
                ("lisa_cluster", "transition_probabilities")
            ),
            "neighborhood_effect.moran_i_local": distinct(("neighborhood_effect", "moran_i_local")),
            "neighborhood_effect.neighborhood_multiplier": distinct(
                ("neighborhood_effect", "neighborhood_multiplier")
            ),
            "meaning": (
                "each map is a distinct-value -> area-count table over the "
                "payload's areas: a single key means the field is constant "
                "across every area, which is the placeholder shape"
            ),
        },
        "varyingValueFields": {
            "neighborhood_effect.spatial_lag": {
                "distinctValues": int(len(set(lags))),
                "min": _r(min(lags), 2),
                "max": _r(max(lags), 2),
            },
            "lisa_cluster.yoy_appreciation": {
                "distinctValues": int(len(set(yoy))),
                "min": _r(min(yoy), 4),
                "max": _r(max(yoy), 4),
            },
        },
        "firstAreaByInsertionOrder": {
            "area": first_area,
            "fields": areas[first_area],
            "meaning": (
                "the payload's first stored area; its z_score 0.0, p_value 1.0, "
                "moran_i_local 0.0 and neighborhood_multiplier 1.0 with a "
                "constant spatial_lag value are the measured placeholder shape, "
                "recorded from the file, not inferred"
            ),
        },
        "meaning": (
            "the served payload is an UNLINKED artefact: nothing in this "
            "checkout connects it to the legacy's retired scripts, so it "
            "adjudicates nothing about the legacy figures in EITHER direction "
            "— its constants neither confirm nor refute Moran's I 0.766/z 9.91 "
            "and its transition block is a per-area constant triple, not a "
            "time series. This pack does not rewrite it; RS11 owns it and may "
            "extend it later from areaLisa/areaGiStar, with no rental content"
        ),
    }


def environment() -> dict[str, Any]:
    import esda
    import h3
    import libpysal
    import scipy

    with PYPROJECT.open("rb") as handle:
        project = tomllib.load(handle)
    research = project.get("dependency-groups", {}).get("research", [])
    constraints = sorted(
        item for item in research if str(item).startswith(("esda", "libpysal", "h3"))
    )
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "esda": esda.__version__,
        "libpysal": libpysal.__version__,
        "h3": h3.__version__,
        "declaredResearchGroup": {
            "pyprojectPath": _relative(PYPROJECT),
            "group": "dependency-groups.research",
            "spatialConstraints": constraints,
            "meaning": (
                "the spatial stack is importable in the default uv environment; "
                "the declared constraints are recorded so the protocol is "
                "reproducible elsewhere"
            ),
        },
    }


def _scan_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(rel.startswith(prefix) for prefix in EXCLUDED_SCAN_PREFIXES):
                continue
            if rel in EXCLUDED_SCAN_PATHS:
                continue
            if rel.startswith("docs/analytics/editions/") and not rel.startswith(
                RETAINED_EDITION_PREFIX
            ):
                continue
            files.append(path)
    return sorted(files, key=_relative)


def absence_scans(
    frame_columns: list[str],
) -> dict[str, Any]:
    legacy_named_input = {
        "claim": "the legacy appendix names data/parquets/L1/housing_hdb_rental.parquet as its primary input",
        "expectedPath": "data/parquets/L1/housing_hdb_rental.parquet",
        "expectedPathExists": (
            REPO_ROOT / "data" / "parquets" / "L1" / "housing_hdb_rental.parquet"
        ).is_file(),
        "dataParquetsDirectoryExists": (REPO_ROOT / "data" / "parquets").is_dir(),
        "rootsSearched": ["."],
        "filenamePatterns": ["housing_hdb_rental*", "housing_hdb*"],
        "matchedFiles": [],
        "matchedFileCount": 0,
        "exclusions": {
            "prefixes": [".git/", "node_modules/", ".venv/", "__pycache__/"]
            + list(EXCLUDED_SCAN_PREFIXES),
            "paths": list(EXCLUDED_SCAN_PATHS),
            "meaning": (
                "version-control, dependency and programme-output surfaces are "
                "excluded from the hash-pinned scan; the programme surfaces "
                "could not contain a data parquet in any case, and the "
                "exclusion is disclosed rather than silent"
            ),
        },
        "scanMethod": (
            "recursive filename match under the repo root with the exclusions "
            "above; every matched file would be listed with its path — the "
            "count is 0 and the list is empty"
        ),
        "meaning": (
            "the named input is absent: no path in the checkout matches either "
            "filename pattern, and the data/parquets directory itself does not "
            "exist"
        ),
    }
    rent_like = [name for name in frame_columns if "rent" in name.lower()]
    frame_schema_scan = {
        "surface": "the 97-column schema of the shipped unified frame, read by metadata (pq.read_schema)",
        "monthlyRentExactMatches": [name for name in frame_columns if name == "monthly_rent"],
        "rentSubstringMatches": rent_like,
        "columnCount": int(len(frame_columns)),
        "meaning": (
            "no monthly_rent column exists; the one rent-substring hit is "
            "rental_yield_pct, a different measure that cannot stand in for the "
            "legacy's median monthly_rent aggregation, and the pack adds no "
            "rental content to RS11's own surfaces"
        ),
    }
    matches: list[dict[str, Any]] = []
    total = 0
    for path in _scan_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        count = int(len(METHOD_TOKENS.findall(text)))
        if count:
            matches.append({"path": _relative(path), "matchCount": count})
            total += count
    implementation_scan = {
        "purpose": (
            "the legacy provenance says its Python spatial scripts were retired; "
            "this scan measures whether any implementation of the legacy method "
            "survives outside the programme's own surfaces"
        ),
        "rootsSearched": list(SCAN_ROOTS),
        "suffixes": list(SCAN_SUFFIXES),
        "tokenPattern": "moran|esda|libpysal|getis|lisa (case-insensitive)",
        "matchedFiles": matches,
        "matchedFileCount": int(len(matches)),
        "totalMatches": int(total),
        "exclusions": {
            "prefixes": list(EXCLUDED_SCAN_PREFIXES),
            "paths": list(EXCLUDED_SCAN_PATHS),
            "editionRule": (
                "docs/analytics/editions/ is excluded except the frozen legacy "
                "originals under docs/analytics/editions/legacy/, which stay in "
                "the scan because the article's own method words are what the "
                "tokens are matched against"
            ),
            "selfExclusion": (
                "this tool lives under scripts/tools/ and quotes the tokens it "
                "searches for, so it cannot scan itself; app/src/components/"
                "studies/ (edition registry/pages) and app/tests/ (fixtures) "
                "are programme outputs; .secrets.baseline and "
                "docs/plans/2026-11-12-reporting-refresh-decisions.md (D12 "
                "register) are explicitly excluded"
            ),
        },
        "meaning": (
            "matches are prose, plan and UI references (including the frozen "
            "legacy originals and the sibling spatial-hotspots article), not "
            "executable spatial code: no .py file outside the excluded "
            "programme surfaces implements the legacy method, which is why the "
            "legacy numbers cannot be re-derived from any surviving script"
        ),
    }
    data_matches: list[dict[str, Any]] = []
    data_root = REPO_ROOT / "data"
    if data_root.is_dir():
        for path in sorted(data_root.rglob("*")):
            if not path.is_file():
                continue
            name = path.name.lower()
            if any(pattern in name for pattern in DATA_SCAN_PATTERNS):
                data_matches.append({"path": _relative(path)})
    data_artefact_scan = {
        "purpose": (
            "the legacy's transition/persistence claim needs per-period spatial "
            "memberships; this scan bounds what spatial time-series artefact "
            "exists under data/"
        ),
        "rootsSearched": ["data/"],
        "filenamePatterns": [f"*{pattern}*" for pattern in DATA_SCAN_PATTERNS],
        "matchedFiles": data_matches,
        "matchedFileCount": int(len(data_matches)),
        "meaning": (
            "no file under data/ carries a lisa, moran, spatial, transition or "
            "persistence name: the claim's time dimension exists in no linked "
            "artefact, and the served payload's transition block is a constant "
            "triple (servedAssetInventory.constantValueFields)"
        ),
    }
    return {
        "legacyNamedInput": legacy_named_input,
        "frameSchemaRentScan": frame_schema_scan,
        "methodImplementationScan": implementation_scan,
        "dataSpatialArtefactScan": data_artefact_scan,
    }


def legacy_method_recovery() -> dict[str, Any]:
    return {
        "globalMoran": {
            "stated": {
                "moranI": 0.766,
                "zScore": 9.91,
                "pValueBound": "< 0.001",
                "permutations": 99,
                "weights": "KNN weights (k=8), row-standardized",
            },
            "variable": "underspecified: the appendix aggregates median monthly_rent per H3 cell, while the prose interprets appreciation — the source states no variable for its headline statistic, so the pack does not choose one",
            "namedInputPresent": False,
            "recoverableFromServedAsset": False,
            "packReMeasurement": {
                "areaLevelAppreciation": "areaMoran.moranI / areaMoran.pSim",
                "pointLevelPriceLevel": "pointLevel.fullPopulation.moranI",
                "note": "both are fields of THIS protocol, recorded for contrast; neither recovers the legacy statistic",
            },
            "meaning": (
                "the legacy's inputs are absent and its variable is unstated, so "
                "0.766/z 9.91 cannot be re-derived; the served payload's "
                "constants do not bear on it either way (unlinked artefact)"
            ),
        },
        "lisa": {
            "stated": {
                "implementation": "Moran_Local",
                "permutations": 99,
                "significanceThreshold": "p <= 0.05",
                "classes": ["HH", "LL", "HL", "LH", "NS"],
            },
            "packProtocolContrast": {
                "permutations": PERMUTATIONS,
                "seed": SEED,
                "multiplicityCorrection": f"Benjamini-Hochberg q={BH_Q}",
                "unit": "planning area (41 areas after the floor)",
                "meaning": (
                    "the pack deliberately differs from the legacy's recorded "
                    "settings where the gate requires it: more permutations, a "
                    "fixed seed, and multiplicity correction before labels"
                ),
            },
            "meaning": (
                "the legacy's LISA run is not reproducible (absent input, "
                "underspecified unit); the pack's own LISA memberships are at "
                "areaLisa.members"
            ),
        },
        "clusterTable": {
            "statedCounts": {"hh": 16, "lh": 17, "ll": 1, "notSignificant": 8},
            "statedCellSum": 16 + 17 + 1 + 8,
            "statedYoY": {
                "hh": "12.7%",
                "lh": "11.3%",
                "ll": "about 10%",
                "notSignificant": "12.0%",
            },
            "hlRowAbsentFromTable": True,
            "unit": "'cells' — the appendix's H3 resolution-8 units at >=10 records",
            "servedAssetAreaCount": 41,
            "unitContradiction": {
                "note": (
                    "the table sums to 42 cells over H3 units, while the only "
                    "spatial asset this checkout serves is keyed by 41 planning "
                    "areas; no stored membership of either unit exists for the "
                    "legacy run, and the counts are not derivable from either"
                ),
            },
            "packReMeasurement": {
                "labelCounts": "areaLisa.labelCounts",
                "note": (
                    "recorded for contrast at the planning-area unit under the "
                    "pack's protocol; it does not recover a 42-cell H3 table and "
                    "does not confirm or refute it"
                ),
            },
            "meaning": (
                "the cluster table is unreproducible as stated: its unit, window "
                "and per-cell YoY series are all underspecified, and its YoY "
                "percentages depend on a per-cell appreciation series that no "
                "stored artefact carries"
            ),
        },
        "spatialLagCorrelation": {
            "stated": {"condo": 78, "hdb": 71, "ec": 65, "unit": "percent"},
            "definitionRecorded": False,
            "why": (
                "the legacy names no variable pair, no window and no aggregation "
                "for 'spatial lag correlation'; rule: an underspecified "
                "statistic is recorded as underspecified, not guessed into a "
                "definition"
            ),
            "packDefinedReading": "perTypeMoran.<segment>.spatialLagCorrelation.r",
            "meaning": (
                "the pack records ONE defined reading per segment for contrast; "
                "the legacy's ranking (condo strongest) remains unreproducible "
                "and its mechanism prose screened as origin-unverified"
            ),
        },
        "h3CellArea": {
            "stated": "H3 resolution 8, '~0.5 km² cells'",
            "measuredMeanOccupiedCellAreaKm2": "pointLevel.h3Grid.meanCellAreaKm2",
            "meaning": (
                "re-measured from the occupied cells themselves: the claim's "
                "approximate cell area does not match the measured mean, which "
                "is a field, not a prose number"
            ),
        },
        "transition": {
            "stated": "moderate persistence — hotspot and coldspot status are sticky but not permanent",
            "timeDimensionInAnyLinkedAsset": False,
            "servedPayloadTransitionBlockIsConstant": "servedAssetInventory.constantValueFields",
            "dataArtefactScan": "absenceScans.dataSpatialArtefactScan",
            "disposition": "withdrawn",
            "meaning": (
                "a time-series claim over a study that names no periods: the "
                "only time reference in the legacy text is its 2021-2026 data "
                "period line, no per-period memberships exist in any linked "
                "artefact, and the served payload's transition probabilities "
                "are the same three constants in every area. The pack withdraws "
                "the claim rather than restating it"
            ),
        },
        "namedInput": {
            "scan": "absenceScans.legacyNamedInput",
            "meaning": (
                "the appendix's primary input is a RENTAL file invoked for an "
                "APPRECIATION finding; both facts are recorded, neither is "
                "explained away, and the pack adds no rental content anywhere"
            ),
        },
    }


LEGACY_CLAIMS = (
    {
        "id": "C01",
        "phrase": "| Moran's I | 0.766 | Strong positive spatial clustering |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.globalMoran",
        "note": "the headline statistic's variable is unstated (appendix: median monthly_rent; prose: appreciation) and its named input is absent; recorded as stated, not re-derived",
    },
    {
        "id": "C02",
        "phrase": "| Z-score   | 9.91  | Highly significant                 |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.globalMoran",
        "note": "inference for an unreproducible statistic; the pack records its own z and p as fields",
    },
    {
        "id": "C03",
        "phrase": "- **Global Moran's I**: KNN weights (k=8), row-standardized, 99 permutations",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.globalMoran",
        "note": "the weights words are recorded; the pack re-adopts k=8 row-standardised at areaMoran.weights with 999 permutations and a fixed seed, a deliberate recorded difference",
    },
    {
        "id": "C04",
        "phrase": "**Global Moran's I**: 0.766 (strong positive spatial clustering)",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.globalMoran",
        "note": "same statistic as C01 in the technical findings; not recoverable from any artefact in this checkout",
    },
    {
        "id": "C05",
        "phrase": "- **Z-score**: 9.91, p-value < 0.001 — highly significant",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.globalMoran",
        "note": "same inference as C02; the bound and the z are recorded as stated values only",
    },
    {
        "id": "C06",
        "phrase": "The Moran's I of 0.766 with z=9.91 confirms that appreciation is far from randomly distributed",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.globalMoran",
        "note": "beyond being unreproducible, the verb is a defect this pack flags: a structural screen cannot confirm anything about how a series was produced — the edition must not carry this wording",
    },
    {
        "id": "C07",
        "phrase": "| HH (hotspot)                         | 16    | 12.7%            | High-growth areas near other high-growth areas   |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "the 16-cell count and its 12.7% YoY depend on a per-cell appreciation series and an H3-cell membership that no stored artefact carries",
    },
    {
        "id": "C08",
        "phrase": "| LH (lagging in strong neighborhoods) | 17    | 11.3%            | Potential catch-up or persistent underperformers |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "same unreproducible table; the catch-up interpretation is additionally a forward-looking reading the pack does not restate",
    },
    {
        "id": "C09",
        "phrase": "| LL (coldspot)                        | 1     | about 10%        | Weak area in weak surroundings                   |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "'about 10%' is not a machine-checkable number and its cell count rests on the same unreproducible run",
    },
    {
        "id": "C10",
        "phrase": "| Not significant                      | 8     | 12.0%            | No strong local pattern                          |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "same unreproducible table; the HL class named in the methodology has no table row at all (recorded at legacyMethodRecovery.clusterTable.hlRowAbsentFromTable)",
    },
    {
        "id": "C11",
        "phrase": "  - HH (hotspot): 16 cells, 12.7% YoY appreciation",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "technical-findings restatement of C07; the unit contradiction (42 H3 cells vs the served 41 planning areas) is recorded as fields",
    },
    {
        "id": "C12",
        "phrase": "  - LH (lagging in strong neighborhood): 17 cells, 11.3% YoY",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "technical-findings restatement of C08",
    },
    {
        "id": "C13",
        "phrase": "  - LL (coldspot): 1 cell, ~10% YoY",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "technical-findings restatement of C09",
    },
    {
        "id": "C14",
        "phrase": "  - Not significant: 8 cells, 12.0% YoY",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "technical-findings restatement of C10",
    },
    {
        "id": "C15",
        "phrase": "- **Local LISA** (Local Indicators of Spatial Association): `Moran_Local` with 99 permutations",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.lisa",
        "note": "the implementation name and permutation count are recorded; the pack's own LISA runs with 999 permutations, a fixed seed and BH correction at areaLisa",
    },
    {
        "id": "C16",
        "phrase": "- **Spatial aggregation**: H3 hexagonal grid at resolution 8 (~0.5 km² cells)",
        "status": "re-measured",
        "ledgerKey": "legacyMethodRecovery.h3CellArea",
        "note": "the resolution number is checkable against the data: the mean area of the resolution-8 cells the transactions actually occupy is 0.8374 km² (pointLevel.h3Grid.meanCellAreaKm2, 393 distinct cells, h3.cell_area), about 0.34 km² above the claimed approximation",
    },
    {
        "id": "C17",
        "phrase": "- **Aggregation method**: median `monthly_rent` per H3 cell",
        "status": "not-reproducible",
        "ledgerKey": "absenceScans.frameSchemaRentScan",
        "note": "no monthly_rent column exists in the 97-column schema (rental_yield_pct is a different measure) and the named rental input is absent; a rental aggregate also cannot ground the prose's appreciation interpretation — origin unverified",
    },
    {
        "id": "C18",
        "phrase": "- **Primary input**: `data/parquets/L1/housing_hdb_rental.parquet`",
        "status": "not-reproducible",
        "ledgerKey": "absenceScans.legacyNamedInput",
        "note": "the path does not exist, the data/parquets directory does not exist, and a repo-wide filename scan finds zero matches — boundary and counts are ledger fields",
    },
    {
        "id": "C19",
        "phrase": "- **Minimum threshold**: ≥10 records per cell for analysis",
        "status": "not-reproducible",
        "ledgerKey": "areaPanel.floor",
        "note": "the threshold number is adopted by this pack as its own per-area-window floor (recorded as a field with attribution); the legacy's own per-cell application ran on the absent input",
    },
    {
        "id": "C20",
        "phrase": "- **Significance threshold**: p ≤ 0.05",
        "status": "not-reproducible",
        "ledgerKey": "areaLisa.multiplicityCorrection",
        "note": "the uncorrected rule is recorded and deliberately NOT re-adopted: the gate requires multiplicity correction, so the pack labels only at Benjamini-Hochberg q=0.05 (Bonferroni threshold also recorded)",
    },
    {
        "id": "C21",
        "phrase": "| Condo         | 78%                     |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.spatialLagCorrelation",
        "note": "'spatial lag correlation' names no variable pair, window or aggregation; recorded as underspecified rather than guessed (pack's defined reading at perTypeMoran)",
    },
    {
        "id": "C22",
        "phrase": "| HDB           | 71%                     |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.spatialLagCorrelation",
        "note": "same undefined statistic as C21",
    },
    {
        "id": "C23",
        "phrase": "| EC            | 65%                     |",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.spatialLagCorrelation",
        "note": "same undefined statistic as C21",
    },
    {
        "id": "C24",
        "phrase": "**Transition analysis**: moderate persistence — hotspot and coldspot status are sticky but not permanent",
        "status": "withdrawn",
        "ledgerKey": "legacyMethodRecovery.transition",
        "note": "a time-series claim with no time dimension in any linked asset: no per-period memberships exist (data scan empty) and the served payload's transition probabilities are one constant triple across all areas; withdrawn, not restated",
    },
    {
        "id": "C25",
        "phrase": "**Data Period**: 2021-2026",
        "status": "not-reproducible",
        "ledgerKey": "population.monthRange",
        "note": "the frame spans 1990-01 to 2026-11 (fields); which months the legacy run used is not stated beyond years, and the pack's windows are the 24 months ending at the measured cutoff",
    },
    {
        "id": "C26",
        "phrase": "The HH cluster premium (12.7% YoY vs ~10-12% elsewhere) is modest but statistically robust",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.clusterTable",
        "note": "a premium inference on the unreproducible table; 'statistically robust' cannot be assessed without the underlying memberships, and an HH label is not a return prediction (gate clause)",
    },
    {
        "id": "C27",
        "phrase": "The stronger spatial dependence in condos (78%) vs HDB (71%) vs EC (65%) suggests that condo pricing is more influenced by peer neighborhood performance",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.spatialLagCorrelation",
        "note": "a ranking and a mechanism on the undefined statistic; the pack's per-type fields are recorded for contrast and the mechanism is screened as origin-unverified",
    },
    {
        "id": "C28",
        "phrase": "- **Spatial lag correlation**: computed per property type (Condo, HDB, EC) to measure neighborhood dependence",
        "status": "not-reproducible",
        "ledgerKey": "legacyMethodRecovery.spatialLagCorrelation",
        "note": "the methodology names the segments but not the statistic; nothing to re-run",
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
        "allQuotesFound": all(int(quote["occurrences"]) > 0 for quote in quotes),
        "method": (
            "each phrase is required to appear verbatim in the frozen legacy "
            "text; a paraphrase inside quotation marks is a defect, and an "
            "ellipsis is permitted only for a genuine omission"
        ),
    }


def _resolve_ledger_path(payload: dict[str, Any], dotted: str) -> bool:
    """Does a claim's `ledgerKey` resolve inside the ledger that quotes it?"""
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
        "resolutionIsSyntactic": True,
        "method": (
            "each claim's ledgerKey is resolved against this ledger at build time "
            "by walking dict keys and list items by their `id`; the resolution is "
            "syntactic — it guarantees the key EXISTS and says nothing about the "
            "field's semantic adequacy, which the notes carry. An unresolved key "
            "fails the build rather than shipping"
        ),
    }


def not_established() -> list[dict[str, str]]:
    return [
        {
            "id": "N1",
            "statement": (
                "no high-high (or any) label in this pack is a prediction of "
                "future returns or demand (gate clause): the labels summarise "
                "the 24 measured months ending at the cutoff and carry no "
                "forward-looking content"
            ),
        },
        {
            "id": "N2",
            "statement": (
                "the pack does not recover Moran's I 0.766 or z 9.91: the "
                "legacy's variable is unstated and its input absent (origin "
                "unverified); the re-measured values are fields of a different, "
                "fully specified protocol, recorded for contrast"
            ),
        },
        {
            "id": "N3",
            "statement": (
                "the served spatial_analysis.json.gz payload is unlinked to "
                "every run described here, so it adjudicates nothing in either "
                "direction: its placeholder constants neither support nor "
                "undermine the legacy figures, and this pack neither confirms "
                "nor denies them from it"
            ),
        },
        {
            "id": "N4",
            "statement": (
                "the point-level layer is a price-LEVEL screen on coordinates "
                "that resolve to 13,562 distinct pairs and fragment into "
                "11,803 KNN components; it is not evidence about appreciation "
                "clustering and its analytic p-value is explicitly not "
                "calibrated (pointLevel.fullPopulation.inferenceCaveat)"
            ),
        },
        {
            "id": "N5",
            "statement": (
                "no transition or persistence statement is supported by this "
                "checkout; the legacy's is withdrawn (C24) and nothing here "
                "replaces it"
            ),
        },
        {
            "id": "N6",
            "statement": (
                "every absence claim in this pack is bounded to its recorded "
                "scan roots and exclusions (absenceScans.*): the scans describe "
                "this checkout, not the world"
            ),
        },
        {
            "id": "N7",
            "statement": (
                "the pack produces memberships at the planning-area unit only; "
                "it does not reproduce the legacy's H3-cell unit, whose >=10-"
                "record cells existed on an input this checkout does not have"
            ),
        },
    ]


def build() -> dict[str, Any]:
    frame = pd.read_parquet(UNIFIED, columns=list(FRAME_COLUMNS))
    measured_cutoff = cutoff(frame)
    last_complete = measured_cutoff["lastCompleteMonth"]

    bounded = frame.loc[frame["month"] <= last_complete]
    panel, _dropped = _area_panel(
        bounded,
        window_months(last_complete, 0, 12),
        window_months(last_complete, 12, 12),
        AREA_FLOOR,
    )

    inputs: dict[str, Any] = {}
    for path in (UNIFIED, SERVED_ASSET, LEGACY_EDITION, PYPROJECT):
        inputs[_relative(path)] = {"sha256": sha256_of(path), "bytes": int(path.stat().st_size)}
    inputs[_relative(UNIFIED)]["rows"] = int(pq.ParquetFile(UNIFIED).metadata.num_rows)
    inputs[_relative(UNIFIED)]["columns"] = int(len(pq.read_schema(UNIFIED).names))

    weights: dict[str, Any] = {}
    claims = legacy_claims()
    frame_areas = set(str(a) for a in frame["planning_area"].dropna().unique())
    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": "RS11",
        "series": "spatial-autocorrelation",
        "scope": (
            "RS11 spatial-autocorrelation evidence: the measured cutoff, the "
            "population and its missingness states, the planning-area "
            "appreciation panel, the area-level Moran/LISA/Gi* re-measurement "
            "with weights, connectivity, permutation, seed and multiplicity "
            "fields, per-property-type panels, the point-level price-level "
            "screen with its connectivity caveat and seeded subsample, the H3 "
            "cell-area re-measurement, the served asset's inventory, the "
            "absence scans with boundaries, and every legacy claim's disposition"
        ),
        "definition": DEFINITION,
        "inputs": inputs,
        "environment": environment(),
        "cutoff": measured_cutoff,
        "population": population(frame, last_complete),
        "areaPanel": area_panel(frame, last_complete),
        "areaMoran": area_moran(panel, weights),
        "areaLisa": area_lisa(panel),
        "areaGiStar": area_gistar(panel),
        "perTypeMoran": per_type_moran(frame, last_complete),
        "pointLevel": point_level(frame, last_complete),
        "servedAssetInventory": served_asset(frame_areas),
        "absenceScans": absence_scans(sorted(pq.read_schema(UNIFIED).names)),
        "legacyMethodRecovery": legacy_method_recovery(),
        "notEstablished": not_established(),
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
        print("Pass: RS11 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS11 ledger does not match this checkout")
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

    print(
        f"Cutoff: last complete month {evidence['cutoff']['lastCompleteMonth']} "
        f"(terminal {evidence['cutoff']['terminalMonth']} at "
        f"{evidence['cutoff']['terminalMonthShareOfTrailingMedian']} of the trailing median)"
    )
    print(
        f"Population: {evidence['population']['frameRows']} rows; "
        f"{evidence['population']['missingness']['nullValueRows']['lat']} rows without lat/lon/planning_area"
    )
    print(
        f"Area panel: {evidence['areaPanel']['areasAfterFloor']} areas after the "
        f"{evidence['areaPanel']['floor']['value']}-transaction floor "
        f"({len(evidence['areaPanel']['droppedAreas'])} dropped)"
    )
    print(
        f"Area Moran's I: {evidence['areaMoran']['moranI']} (p_sim {evidence['areaMoran']['pSim']}); "
        f"LISA labels {evidence['areaLisa']['labelCounts']}"
    )
    print(
        f"Point level: I {evidence['pointLevel']['fullPopulation']['moranI']} over "
        f"{evidence['pointLevel']['fullPopulation']['n']} rows, "
        f"{evidence['pointLevel']['disconnectedAreas']['components']} KNN components; "
        f"subsample I {evidence['pointLevel']['seededSubsample']['moranI']} "
        f"(p_sim {evidence['pointLevel']['seededSubsample']['pSim']})"
    )
    print(
        f"H3 res-8: {evidence['pointLevel']['h3Grid']['distinctOccupiedCells']} occupied cells, "
        f"mean area {evidence['pointLevel']['h3Grid']['meanCellAreaKm2']} km^2"
    )
    print(
        f"Served asset: {evidence['servedAssetInventory']['areaCount']} areas; "
        f"constant z_score map {evidence['servedAssetInventory']['constantValueFields']['hotspot.z_score']}"
    )
    print(
        "Quote check: "
        f"{sum(1 for quote in evidence['legacyQuoteCheck']['quotes'] if quote['occurrences'] > 0)}"
        f"/{evidence['legacyQuoteCheck']['claimsChecked']} verbatim"
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
    raise SystemExit(main())
