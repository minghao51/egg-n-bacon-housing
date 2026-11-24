#!/usr/bin/env python3
"""Measure RS10's market-segments evidence: the stored segment asset, its cohort
arithmetic, what membership (if any) can be joined, and what of the legacy
method is recorded anywhere in this checkout.

RS10's gate is "Recover feature scaling, clustering/model version and cohort
counts; assess stability and map old/new segment identities. Do not reuse a
segment ID for a different population. App matching weights remain unchanged
unless separately approved." This tool measures from the local checkout, and
only what the checkout can support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04/RS05/RS09
   shipped (terminal month's transaction count as a fraction of the trailing
   twelve-month median), plus the all-property-types cross-check.
2. **Segment asset inventory** — full read of `segments_enhanced.json.gz`:
   version, lastUpdated, segment count, per-segment id/classification/metrics/
   persistence/planning-area count, the sha256 of the gz, id uniqueness, the
   asset's own planning-area membership block, and the two things the block
   makes measurable: persistence is a per-class constant lookup, and the stored
   area panel's internal correlations.
3. **Cohort reconciliation** — the arithmetic that can actually be run on the
   asset's own figures: do `marketShare` values sum to 1, does each share equal
   its `transactionCount` over the asset's total, and does that total (or any
   per-segment count) reproduce a measured population — the shipped frame, the
   article's stated windows, or the rows inside the segment's own declared
   planning areas. The asset's counts are reproduced from its own totals; what
   is measured is that no shipped population reproduces them.
4. **Membership recovery** — the distinct values of `market_segment`,
   `property_segment` and `price_stratum`, and the exact-match count of the
   asset's six ids against every value of those columns (zero matches: a count
   of matches between the asset's ids and the shipped columns, not a claim of
   absent data). It also measures the one join that does exist: the asset's 31
   planning areas against the frame's 44 `planning_area` values, and the 51
   stored area→segment pairs, which are many-to-many and therefore assign no
   per-transaction segment.
5. **Dashboard asset contrast** — the dashboard asset's keys, identifiers and
   counts, and the id intersection with the segment asset (0 shared ids; the
   dashboard carries no segment id at all). An intersection, never a resemblance.
6. **Method recovery** — K, the scaler and log-transform settings, silhouette
   and elbow outputs, the model version string, the article's derived feature
   names, and where the asset's literals actually come from. Each is recorded
   with the path/key where it appears, or `notRecorded`.
7. **CAGR window** — the observed window per property type, whether a
   2015-2025 window is available, and the legacy's own area-CAGR definition
   applied to the only rows that span it.
8. **App matching weights** — recorded and sha256-pinned, unchanged: this study
   must not change them.

It never runs the pipeline, never re-fits a clustering, never writes outside
`--output`, and never touches `app/public/data/**` or `data/pipeline/**`.

Usage:

    uv run python scripts/tools/market_segments_evidence.py \\
        --output docs/implementation/artifacts/rs10-market-segments-evidence.json

    uv run python scripts/tools/market_segments_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import gzip
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
SEGMENT_ASSET = REPO_ROOT / "app" / "public" / "data" / "segments_enhanced.json.gz"
DASHBOARD_ASSET = REPO_ROOT / "app" / "public" / "data" / "dashboard_segments.json.gz"
LEGACY_EDITION = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "market-segments.md"
)
SEGMENTED_PANEL = (
    REPO_ROOT / "data" / "analysis" / "market_segmentation" / "housing_unified_segmented.parquet"
)
TIER_PANEL = REPO_ROOT / "data" / "analysis" / "market_segmentation" / "tier_performance.parquet"
TIER_THRESHOLDS = REPO_ROOT / "data" / "analysis" / "market_segmentation" / "tier_thresholds.csv"
SEG_V2_DIR = REPO_ROOT / "data" / "analysis" / "market_segmentation_2.0"
SEG_PERIOD_DIR = REPO_ROOT / "data" / "analysis" / "market_segmentation_period"
ARCHIVE_DOC = REPO_ROOT / "docs" / "archive" / "20260124-market-insights-fixes-complete.md"
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "plans"
    / "2026-02-22-interactive-market-segments-dashboard-implementation.md"
)
HANDOFF_DOC = (
    REPO_ROOT
    / ".claude"
    / "handoffs"
    / "2026-02-23-interactive-segments-dashboard-implementation.md"
)
SEGMENT_EVIDENCE_TS = (
    REPO_ROOT
    / "app"
    / "src"
    / "components"
    / "dashboard"
    / "segments"
    / "lib"
    / "segment-evidence.ts"
)
MATCHING_HOOK = REPO_ROOT / "app" / "src" / "hooks" / "useSegmentMatching.ts"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs10-market-segments-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

# The scan is bounded to these roots and suffixes so the ledger is reproducible
# file-order-independently and cannot read itself.
SCAN_ROOTS = ("docs", "scripts", "src", "assets", "prompts", "app/src", ".claude/handoffs")
SCAN_SUFFIXES = (".md", ".py", ".ts", ".tsx")
# The exclusions are the RF08 programme's own output surfaces, not evidence of
# RS10's method: `docs/implementation/` holds the per-study records, `scripts/tools/`
# holds the evidence producers themselves, and `prompts/` holds the handoffs and
# runbooks. Their exclusion is disclosed at
# `methodRecovery.tokenScan.excludedFromScan`. A hash-pinned scan that counted
# them drifted the moment a sibling instrument appeared: the round-14 ledger
# recorded 348 scanned files and this checkout measured 349 (the +1 was
# `scripts/tools/check_edition_lexicon.py`) with an unchanged token match list.
# If production code is ever placed under `scripts/tools/`, narrow this again.
EXCLUDED_SCAN_PREFIXES = (
    "docs/implementation/",
    "docs/plans/",
    "docs/guides/",
    "scripts/tools/",
    "prompts/",
)
# `docs/plans/` is the planning/spec surface: plan and audit prose ABOUT the
# method, not an implementation of it. It holds the D12 decision register this
# scan already excluded by path, so the prefix generalises that same intent — a
# plan that describes a KMeans/StandardScaler block is an illustration in a
# plan, and pinning it made this ledger drift whenever a plan or audit pack
# restated the method's vocabulary.
# `docs/guides/` is the operational surface and is excluded on the same
# principle: runbooks, setup notes and CI descriptions are prose about operating
# the programme, not an implementation of RS10's method and not evidence about
# it. A guide that names the study is not a counter-example to an absence claim,
# because these scans establish absence FROM CODE.
# Published edition texts are programme outputs too: a study that signs after
# RS10 must not drift this ledger. The frozen legacy originals stay IN the scan,
# because the article's own method claims are what these tokens are matched
# against.
EDITION_PREFIX = "docs/analytics/editions/"
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
# This tool quotes the tokens it searches for; scanning itself would make the
# ledger its own evidence and drift on every wording change.
#
# The D12 decision register is excluded for the same reason: it records what
# reviewers found, in their own vocabulary. Recording a verdict that mentions an
# "elbow" marker or a "silhouette" maximum must not move a pinned count — that is
# exactly how this ledger stopped re-measuring on 2026-11-20, when the RS10
# sign-off rows were written into it. Every other RF08 programme record already
# lives under an excluded prefix (`docs/implementation/`, `prompts/`).
EXCLUDED_SCAN_PATHS = (
    "scripts/tools/market_segments_evidence.py",
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
)

METHOD_TOKENS = (
    "Silhouette",
    "elbow",
    "StandardScaler",
    "MiniBatchKMeans",
    "AgglomerativeClustering",
    "log1p",
    "n_clusters",
)

LEGACY_SEGMENT_NAMES = (
    "High-Growth HDB",
    "Stable Mid-Tier",
    "Premium Condo (Low Yield)",
    "High-Yield Apartments",
    "Luxury Segment",
)

# The article's six area rows (planning area, CAGR band, PSF band, segment label).
LEGACY_AREA_BANDS = (
    ("BUKIT TIMAH", "~5-7%", "Luxury"),
    ("QUEENSTOWN", "~4-6%", "High-Growth HDB"),
    ("JURONG EAST", "~4-6%", "High-Growth HDB"),
    ("PUNGGOL", "~3-5%", "High-Growth HDB"),
    ("SENGKANG", "~2-4%", "Stable Mid-Tier"),
    ("WOODLANDS", "~1-3%", "Stable Mid-Tier"),
)

# The article's own stated derived-feature names (technical appendix).
LEGACY_DERIVED_FEATURES = (
    "price_psm",
    "rental_yield_pct",
    "yoy_change_pct",
    "mom_change_pct",
    "remaining_lease_months",
    "floor_area_sqm",
)

CAGR_WINDOW_START_YEAR = 2015
CAGR_WINDOW_END_YEAR = 2025
CAGR_ENDPOINT_YEAR = CAGR_WINDOW_END_YEAR
CAGR_AREA_YEAR_FLOOR = 50  # the legacy's own "minimum 50 transactions per area"
MAX_LISTED = 12

SHARE_ROUNDING_TOLERANCE = 0.0005

DEFINITION = (
    "A measured inventory and reconciliation of the stored research segment "
    "asset, with an explicit list of what cannot be recovered. The asset "
    "(`segments_enhanced.json.gz`, version 1.0.0) is read in full: its six "
    "segments, their stored metrics, their persistence probabilities and their "
    "declared planning areas. Three things are measured, not assumed. (1) The "
    "asset's own arithmetic: `marketShare` sums to 1 and each share equals its "
    "`transactionCount` over the asset's own total, so the six counts are "
    "internally consistent. (2) Whether that total or any per-segment count "
    "reproduces a shipped population: it does not — no measured window of "
    "`unified_dataset` equals the asset's 911,454, and no segment's stored count "
    "equals the rows inside its own declared planning areas. The counts are "
    "therefore the asset's own unverified figures, recorded as inspection-only. "
    "(3) Membership: the frame's `market_segment` column holds three CCR/RCR/OCR "
    "region labels and is populated only on the 245,655 private rows; the six "
    "asset ids occur zero times as a value in `market_segment`, "
    "`property_segment` or `price_stratum`. The one mapping the RS10 ASSET "
    "itself stores is at planning-area granularity (31 areas, 51 area→segment "
    "pairs) and it is many-to-many, so it assigns no transaction to a segment. "
    "That statement is about the asset's six segments, not about the checkout: a "
    "separate per-transaction segmented panel exists under "
    "data/analysis/market_segmentation/ with three price tiers assigned per row "
    "(recorded at adjacentSegmentedPanel), and it carries none of the six ids. "
    "Feature scaling and K are not recorded "
    "FOR THE ARTICLE'S METHOD, and the asset's segment literals are "
    "hard-coded in a January-February 2026 plan document's generator body. That is "
    "NOT the whole provenance story, and this definition must not imply it is: "
    "data/analysis/market_segmentation_2.0/ holds a PSF-based KMeans profile set "
    "whose six segment names map 1:1 onto the asset's ids and whose cluster "
    "percentages reproduce the asset's marketShare values at three decimals "
    "(clusteringArtefacts), while the plot artefacts in that same directory record "
    "an elbow at K=7 and a silhouette maximum at K=2 — not the stored six-cluster "
    "solution. The exact lineage between those profiles and the plan document's "
    "literals is UNPROVEN, and the asset's counts are not the profile counts nor a "
    "constant multiple of them. No clustering is re-fitted "
    "here and no segment is re-identified: the ledger supports withdrawing the "
    "legacy taxonomy and its per-segment bands, not restating them."
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _select(frame: pd.DataFrame, mask: Any) -> pd.DataFrame:
    return pd.DataFrame(frame.loc[mask]).reset_index(drop=True)


def _number(value: Any, label: str) -> float:
    """A float parsed from an asset/derived value, failing loudly with the value.

    Every numeric value in this ledger is written by the asset or by a pandas
    count, so an unparseable one means the source changed shape; naming the
    offending value is the correct response and is what keeps a silent NaN from
    entering a measured figure.
    """
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise SystemExit(f"Unparseable {label} value {value!r}: {error}") from error


def _integer(value: Any, label: str) -> int:
    """An int parsed from an asset value, failing loudly with the offending value."""
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise SystemExit(f"Unparseable {label} value {value!r}: {error}") from error


def _r(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    number = _number(value, "metric")
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


def _pearson(first: np.ndarray, second: np.ndarray) -> dict[str, Any]:
    mask = np.isfinite(first) & np.isfinite(second)
    x = first[mask]
    y = second[mask]
    if x.size < 3 or x.std() == 0 or y.std() == 0:
        return {"n": int(x.size), "r": None}
    return {"n": int(x.size), "r": _r(np.corrcoef(x, y)[0, 1], 4)}


def _column(rows: list[dict[str, Any]], key: str) -> np.ndarray:
    values: list[float] = []
    for row in rows:
        raw = row.get(key)
        values.append(
            _number(raw, f"asset field {key}") if isinstance(raw, (int, float)) else np.nan
        )
    return np.array(values, dtype=float)


def _column_series(frame: pd.DataFrame, name: str) -> pd.Series:
    """One frame column as a Series, narrowed explicitly for the column key."""
    return pd.Series(np.asarray(frame[name]))


def _value_counts(series: Any) -> dict[str, Any]:
    """Deterministic value counts with an explicit null bucket."""
    values = pd.Series(series)
    counts = Counter(str(value) for value in values.dropna())
    ordered = {key: int(counts[key]) for key in sorted(counts)}
    return {
        "nullKey": "(null)",
        "nullCount": int(values.isna().sum()),
        "valueCounts": ordered,
        "distinctNonEmptyValues": len(ordered),
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
            if any(relative.startswith(prefix) for prefix in EXCLUDED_SCAN_PREFIXES):
                continue
            if relative.startswith(EDITION_PREFIX) and not relative.startswith(
                RETAINED_EDITION_PREFIX
            ):
                continue
            if relative in EXCLUDED_SCAN_PATHS:
                continue
            paths.append(path)
    return sorted(paths)


def _token_scan(paths: list[Path]) -> dict[str, Any]:
    """Where each method token appears (case-insensitive), capped per token."""
    hits: dict[str, Any] = {}
    for token in METHOD_TOKENS:
        needle = token.lower()
        matches: list[dict[str, Any]] = []
        for path in paths:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if needle in line.lower():
                    matches.append(
                        {
                            "path": _relative(path),
                            "line": number,
                            "quote": line.strip()[:160],
                        }
                    )
        hits[token] = {
            "occurrences": len(matches),
            "files": len({match["path"] for match in matches}),
            "firstMatches": matches[:8],
        }
    return hits


def _code_quote(path: Path, needle: str, label: str) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    position = next((number for number, line in enumerate(lines, start=1) if needle in line), None)
    if position is None:
        raise SystemExit(
            f"{label} marker {needle!r} not found in {_relative(path)}; the ledger's citation is stale"
        )
    return {
        "path": _relative(path),
        "line": position,
        "quote": lines[position - 1].strip(),
    }


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    months = frame["month"].astype(str)
    condo = _select(frame, frame["property_type"] == "condo")
    counts = {str(k): int(v) for k, v in condo.groupby("month").size().items()}
    ordered = sorted(counts)
    terminal_month = ordered[-1]
    last_complete_month = ordered[-2]
    trailing_months = ordered[-13:-1]
    trailing = [counts[month] for month in trailing_months]
    trailing_median = float(np.median(trailing)) if trailing else 0.0
    ratio = counts[terminal_month] / trailing_median if trailing_median else None

    all_counts = {str(k): int(v) for k, v in frame.groupby("month").size().items()}
    all_ordered = sorted(all_counts)
    all_trailing = [all_counts[month] for month in all_ordered[-13:-1]]
    all_median = float(np.median(all_trailing)) if all_trailing else 0.0

    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact (the same rule RS03/RS04/"
            "RS05/RS09 shipped, computed on the private rows so the bound is "
            "identical across the studies)"
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
        "allPropertyTypesTerminalMonth": all_ordered[-1],
        "allPropertyTypesTerminalMonthTransactions": all_counts[all_ordered[-1]],
        "allPropertyTypesTrailing12MedianTransactions": _r(all_median, 1),
        "allPropertyTypesTerminalShareOfTrailingMedian": _r(
            all_counts[all_ordered[-1]] / all_median if all_median else None, 4
        ),
        "frameFirstMonth": str(months.min()),
        "frameLastMonth": str(months.max()),
        "meaning": (
            "every window, count and share in this ledger that touches the frame "
            "stops at lastCompleteMonth"
        ),
    }


def segment_asset() -> dict[str, Any]:
    payload = _gz_payload(SEGMENT_ASSET)
    segments = list(payload["segments"])
    areas = dict(payload["planningAreas"])
    ids = [str(segment["id"]) for segment in segments]

    inventory: list[dict[str, Any]] = []
    for segment in segments:
        metrics = segment.get("metrics") or {}
        named_areas = [str(area) for area in segment.get("planningAreas") or []]
        if len(named_areas) > MAX_LISTED:
            raise SystemExit(
                f"segment {segment['id']} declares {len(named_areas)} planning areas, more "
                f"than the ledger lists ({MAX_LISTED}); the declared-area reconciliation "
                "would otherwise silently use a truncated list"
            )
        inventory.append(
            {
                "id": str(segment["id"]),
                "name": str(segment.get("name")),
                "clusterClassification": str(segment.get("clusterClassification")),
                "metricsPresent": bool(metrics),
                "transactionCount": _integer(metrics["transactionCount"], "transactionCount"),
                "marketShare": _number(metrics["marketShare"], "marketShare"),
                "avgPricePsf": _r(metrics.get("avgPricePsf"), 4),
                "avgYield": _r(metrics.get("avgYield"), 4),
                "yoyGrowth": _r(metrics.get("yoyGrowth"), 4),
                "persistenceProbability": _r(segment.get("persistenceProbability"), 4),
                "planningAreaCount": len(named_areas),
                "planningAreasFirst": named_areas[:MAX_LISTED],
            }
        )

    pairs: set[tuple[str, str]] = set()
    for area, info in areas.items():
        for segment_id in info.get("segments") or []:
            pairs.add((str(area), str(segment_id)))
    reverse_pairs = {
        (str(area), str(segment["id"]))
        for segment in segments
        for area in segment.get("planningAreas") or []
    }
    per_area = Counter(len(info.get("segments") or []) for info in areas.values())
    pairs_per_segment = Counter(segment_id for _, segment_id in pairs)

    area_rows = list(areas.values())
    persistence_by_class: dict[str, Any] = {}
    for segment in segments:
        classification = str(segment.get("clusterClassification"))
        persistence_by_class.setdefault(
            classification,
            {
                "persistenceProbability": _r(segment.get("persistenceProbability"), 4),
                "segments": [],
            },
        )["segments"].append(str(segment["id"]))

    return {
        "path": _relative(SEGMENT_ASSET),
        "sha256": sha256_of(SEGMENT_ASSET),
        "bytes": int(SEGMENT_ASSET.stat().st_size),
        "topLevelKeys": sorted(str(key) for key in payload),
        "version": str(payload.get("version")),
        "lastUpdated": str(payload.get("lastUpdated")),
        "segmentCount": len(segments),
        "segmentIds": ids,
        "segmentIdsUnique": len(set(ids)) == len(ids),
        "metricsPresentForEverySegment": all(entry["metricsPresent"] for entry in inventory),
        "insightCount": len(payload.get("insights") or []),
        "planningAreaCount": len(areas),
        "planningAreaNames": sorted(str(area) for area in areas),
        "segments": inventory,
        "planningAreaMembership": {
            "sourceKey": "planningAreas",
            "areas": len(areas),
            "pairCount": len(pairs),
            "pairsPerSegment": {
                key: int(pairs_per_segment[key]) for key in sorted(pairs_per_segment)
            },
            "areasBySegmentCount": {str(key): int(per_area[key]) for key in sorted(per_area)},
            "areasWithNoSegment": sorted(
                str(area) for area, info in areas.items() if not (info.get("segments") or [])
            ),
            "segmentListsAgreeWithAreaLists": pairs == reverse_pairs,
            "symmetricDifference": sorted(
                f"{area}->{segment_id}" for area, segment_id in (pairs ^ reverse_pairs)
            ),
            "meaning": (
                "the asset's only stored membership is this area→segments block: "
                "an area maps to zero to four segments, so the pairs are "
                "many-to-many and not a partition of any population"
            ),
        },
        "persistenceByClassification": {
            key: persistence_by_class[key] for key in sorted(persistence_by_class)
        },
        "persistenceRule": (
            "persistenceProbability is constant within each clusterClassification "
            "(see persistenceByClassification), i.e. a per-label lookup, not a "
            "measured transition rate; the generator body cited in "
            "methodRecovery.generatorProvenance assigns it from the label"
        ),
        "areaPanelFields": sorted({str(key) for row in area_rows for key in row}),
        "internalCorrelations": {
            "segmentsYieldVsYoyGrowth": _pearson(
                np.array(
                    [_number(segment["metrics"]["avgYield"], "avgYield") for segment in segments]
                ),
                np.array(
                    [_number(segment["metrics"]["yoyGrowth"], "yoyGrowth") for segment in segments]
                ),
            ),
            "areasYieldVsPricePsf": _pearson(
                _column(area_rows, "avgYield"), _column(area_rows, "avgPricePsf")
            ),
            "areasYieldVsForecast6m": _pearson(
                _column(area_rows, "avgYield"), _column(area_rows, "forecast6m")
            ),
            "areasPricePsfVsForecast6m": _pearson(
                _column(area_rows, "avgPricePsf"), _column(area_rows, "forecast6m")
            ),
            "meaning": (
                "Pearson r over the asset's own stored fields only (six segment "
                "rows, 31 area rows) — an internal-consistency measurement, not a "
                "re-measurement of any market correlation"
            ),
        },
    }


def cohort_reconciliation(
    frame: pd.DataFrame, asset: dict[str, Any], last_complete: str
) -> dict[str, Any]:
    segments = asset["segments"]
    total = int(sum(entry["transactionCount"] for entry in segments))
    share_sum = float(sum(entry["marketShare"] for entry in segments))
    months = frame["month"].astype(str)

    per_segment: list[dict[str, Any]] = []
    for entry in segments:
        stored = _integer(entry["transactionCount"], "transactionCount")
        share = _number(entry["marketShare"], "marketShare")
        implied_share = stored / total if total else None
        residual = share - implied_share if implied_share is not None else None
        declared = {str(area).upper() for area in entry["planningAreasFirst"]}
        declared_rows = int(
            frame["planning_area"].astype(str).str.strip().str.upper().isin(declared).sum()
        )
        per_segment.append(
            {
                "id": entry["id"],
                "transactionCount": stored,
                "marketShare": share,
                "shareImpliedByCounts": _r(implied_share, 6),
                "shareResidual": _r(residual, 6),
                "impliedDenominator": _r(stored / share if share else None, 1),
                "shareArithmetic": (
                    "internallyConsistent"
                    if residual is not None and abs(residual) <= SHARE_ROUNDING_TOLERANCE
                    else "inconsistent"
                ),
                "declaredPlanningAreaRows": declared_rows,
                "declaredAreaRowsMinusStoredCount": declared_rows - stored,
                "declaredAreasReproduceStoredCount": declared_rows == stored,
            }
        )

    candidates = (
        ("fullFrame", "0000-00", "9999-99"),
        ("articleEmphasisWindow", "2021-01", last_complete),
        ("articleStatedDataPeriod", "2017-01", last_complete),
        ("assetLastUpdatedMonthCap", "2021-01", "2026-04"),
        ("privateRowsOnly", "0000-00", "9999-99"),
    )
    population: list[dict[str, Any]] = []
    for label, start, end in candidates:
        window = (months >= start) & (months <= end)
        if label == "privateRowsOnly":
            window = window & (frame["property_type"] == "condo")
        rows = int(window.sum())
        population.append(
            {
                "label": label,
                "months": f"{start}..{end}",
                "rows": rows,
                "equalsAssetTotal": rows == total,
                "differenceFromAssetTotal": rows - total,
            }
        )

    panel_rows = int(pq.ParquetFile(SEGMENTED_PANEL).metadata.num_rows)
    population.append(
        {
            "label": "adjacentSegmentedPanel",
            "months": "1990-01..2026-01",
            "rows": panel_rows,
            "equalsAssetTotal": panel_rows == total,
            "differenceFromAssetTotal": panel_rows - total,
            "note": (
                "a per-transaction segmented panel under data/analysis with three "
                "price tiers per row and none of the six asset ids; the closest "
                "candidate to the asset total, still not an exact match, and a "
                "different taxonomy — listed here so the near-match is visible "
                "beside the other candidates rather than only in its own block"
            ),
        }
    )

    return {
        "assetTotalTransactions": total,
        "marketShareSum": _r(share_sum, 6),
        "marketShareSumResidual": _r(share_sum - 1.0, 6),
        "shareRoundingTolerance": SHARE_ROUNDING_TOLERANCE,
        "perSegment": per_segment,
        "candidatePopulations": population,
        "anyPopulationEqualsAssetTotal": any(item["equalsAssetTotal"] for item in population),
        "anySegmentCountReproducedByItsDeclaredAreas": any(
            item["declaredAreasReproduceStoredCount"] for item in per_segment
        ),
        "recordedDenominator": {
            **_code_quote(
                PLAN_DOC,
                '"transactionCount": 114700',
                "plan-doc-denominator",
            ),
            "meaning": (
                "the only recorded denominator for these counts is this "
                "generator comment ('~910K'), hard-coded beside the literal; no "
                "measured population in this checkout equals it, and the comment "
                "is not an extraction of the frame"
            ),
        },
        "verdict": (
            "internallyConsistent arithmetic, unreproducible cohorts: the six "
            "marketShare values sum to one and each equals its count over the "
            "asset's own total within three-decimal rounding, but the total "
            "reproduces no measured population and no per-segment count "
            "reproduces the rows inside its own declared planning areas"
        ),
    }


def membership_recovery(frame: pd.DataFrame, asset: dict[str, Any]) -> dict[str, Any]:
    columns = {}
    for column in ("market_segment", "property_segment", "price_stratum"):
        columns[column] = _value_counts(_column_series(frame, column))

    asset_ids = set(asset["segmentIds"])
    matches: dict[str, int] = {}
    total_matches = 0
    for column in ("market_segment", "property_segment", "price_stratum"):
        values = {str(value) for value in _column_series(frame, column).dropna().unique()}
        count = len(values & asset_ids)
        matches[column] = count
        total_matches += count

    segment = frame["market_segment"]
    private_rows = int((frame["property_type"] == "condo").sum())
    hdb_rows = int((frame["property_type"] == "hdb").sum())
    region_labels = {str(value) for value in segment.dropna().unique()}

    area_names = [str(area) for area in asset["planningAreaNames"]]
    area_keys = {name.strip().upper() for name in area_names}
    frame_area = frame["planning_area"].astype(str).str.strip().str.upper()
    has_area = frame["planning_area"].notna()
    covered = frame_area.isin(area_keys) & has_area
    frame_areas = {str(value) for value in frame["planning_area"].dropna().unique()}
    frame_area_keys = {value.strip().upper() for value in frame_areas}
    uncovered_names = sorted(frame_area_keys - area_keys)
    uncovered_rows = int((~covered).sum())
    null_area_rows = int((~has_area).sum())

    return {
        "columnsExamined": columns,
        "segmentIdMatchesInColumns": {
            "perColumn": {key: matches[key] for key in sorted(matches)},
            "total": total_matches,
            "method": (
                "exact string equality between each of the asset's six segment "
                "ids and every distinct non-null value of the three columns"
            ),
            "meaning": (
                "zero matches between the asset's ids and the shipped columns — "
                "this is a count of matches, not a claim that data is missing"
            ),
        },
        "marketSegmentIsARegionLabel": {
            "distinctValues": sorted(region_labels),
            "nonNullRows": int(segment.notna().sum()),
            "nullRows": int(segment.isna().sum()),
            "privateRowsInFrame": private_rows,
            "hdbRowsInFrame": hdb_rows,
            "nonNullEqualsPrivateRows": int(segment.notna().sum()) == private_rows,
            "nullEqualsHdbRows": int(segment.isna().sum()) == hdb_rows,
            "distinctValueCount": len(region_labels),
            "meaning": (
                "the column holds the three national region labels (CCR/RCR/OCR "
                "expanded), is populated on the private rows only, and carries no "
                "segment-id-shaped value; it is a region label, not a behavioural "
                "segment assignment"
            ),
        },
        "areaLevelJoin": {
            "assetAreas": len(area_names),
            "assetAreasPresentInFramePlanningArea": len(area_keys & frame_area_keys),
            "framePlanningAreaValues": len(frame_area_keys),
            "framePlanningAreasAbsentFromAsset": {
                "count": len(uncovered_names),
                "names": uncovered_names,
            },
            "rowsCoveredByAssetAreas": int(covered.sum()),
            "rowsNotCovered": uncovered_rows,
            "rowsWithNullPlanningArea": null_area_rows,
            "rowsInNonAssetAreas": uncovered_rows - null_area_rows,
            "storedAreaToSegmentPairs": asset["planningAreaMembership"]["pairCount"],
            "maxSegmentsPerArea": max(
                int(key) for key in asset["planningAreaMembership"]["areasBySegmentCount"]
            ),
            "meaning": (
                "an area→segments mapping does join to the frame on planning_area, "
                "but it is many-to-many (up to four segments per area, six areas "
                "with none), so it assigns no transaction to a single segment; it "
                "cannot serve as per-transaction membership"
            ),
        },
        "perTransactionMembership": {
            "available": False,
            "reason": (
                "no column in the 97-column frame carries a stored segment id "
                "(zero id matches measured above), and the RS10 asset's own stored "
                "membership is many-to-many at planning-area granularity. A "
                "per-transaction segmented panel DOES exist elsewhere in the "
                "checkout (data/analysis/market_segmentation/, three price tiers per "
                "row) — see adjacentSegmentedPanel; it carries none of the six ids "
                "and is a different taxonomy, so this claim is about the six stored "
                "segments only"
            ),
        },
    }


def dashboard_contrast(asset: dict[str, Any]) -> dict[str, Any]:
    payload = _gz_payload(DASHBOARD_ASSET)
    keys: dict[str, Any] = {}
    names: set[str] = set()
    categories: set[str] = set()
    has_id = False
    for key in sorted(payload):
        rows = list(payload[key])
        for row in rows:
            names.add(str(row.get("name")))
            categories.add(str(row.get("category")))
            if "id" in row:
                has_id = True
        keys[key] = {
            "rows": len(rows),
            "categories": sorted({str(row.get("category")) for row in rows}),
            "countSum": int(sum(int(row.get("z") or 0) for row in rows)),
        }
    field_names = sorted({str(field) for rows in payload.values() for row in rows for field in row})
    asset_ids = set(asset["segmentIds"])
    dashboard_names = {name for name in names if name and name != "None"}
    fingerprints: dict[str, list[str]] = {}
    for key in sorted(payload):
        rows = payload[key]
        if not rows:
            continue
        fingerprint = json.dumps(rows, sort_keys=True)
        fingerprints.setdefault(fingerprint, []).append(key)
    identical_payloads = sorted(group for group in fingerprints.values() if len(group) > 1)
    return {
        "path": _relative(DASHBOARD_ASSET),
        "sha256": sha256_of(DASHBOARD_ASSET),
        "bytes": int(DASHBOARD_ASSET.stat().st_size),
        "topLevelKeys": sorted(str(key) for key in payload),
        "keyCount": len(payload),
        "rowFields": field_names,
        "hasSegmentIdField": has_id,
        "segmentIds": [],
        "identifierFields": ["name", "category"],
        "distinctNames": len(dashboard_names),
        "distinctCategories": sorted(categories),
        "emptyKeys": sorted(key for key, entry in keys.items() if entry["rows"] == 0),
        "identicalPayloads": identical_payloads,
        "keys": keys,
        "idIntersectionWithSegmentAsset": {
            "sharedIds": 0,
            "assetIdsOnly": sorted(asset_ids),
            "dashboardIdsOnly": [],
            "namesMatchingAssetIds": len(dashboard_names & asset_ids),
            "method": (
                "set intersection of the segment asset's six ids with the "
                "dashboard asset's identifier values; the dashboard has no id "
                "field, so its identifiers are planning-area × property-type "
                "composite names and the intersection is empty by construction "
                "as well as by measurement"
            ),
        },
        "countPopulation": {
            "wholeCountSum": keys["whole"]["countSum"] if "whole" in keys else None,
            "assetTotalTransactions": sum(entry["transactionCount"] for entry in asset["segments"]),
            "frameRows": int(pq.ParquetFile(UNIFIED).metadata.num_rows),
            "matchesAssetTotal": (
                ("whole" in keys)
                and keys["whole"]["countSum"]
                == sum(entry["transactionCount"] for entry in asset["segments"])
            ),
            "meaning": (
                "the dashboard's z is a count per planning-area × property-type "
                "point; its total matches neither the frame nor the asset's cohort "
                "total, so it cannot be used to reconcile either"
            ),
        },
        "verdict": (
            "no old/new segment identity mapping exists in the served assets: the "
            "segment asset carries six ids, the dashboard asset carries none, and "
            "the intersection is zero — recorded as an intersection, not as a "
            "resemblance between similarly named surfaces"
        ),
    }


def method_recovery(paths: list[Path], asset: dict[str, Any]) -> dict[str, Any]:
    schema = {str(name) for name in pq.read_schema(UNIFIED).names}
    renamed = {"price_psm": "Unit Price ($ PSM)"}
    feature_map: dict[str, Any] = {}
    for feature in LEGACY_DERIVED_FEATURES:
        if feature in schema:
            feature_map[feature] = {"status": "presentVerbatim", "column": feature}
        elif feature in renamed and renamed[feature] in schema:
            feature_map[feature] = {
                "status": "presentUnderDifferentName",
                "column": renamed[feature],
            }
        else:
            feature_map[feature] = {"status": "absent", "column": None}

    items: dict[str, Any] = {
        "k": {
            "status": "recorded",
            "where": {
                "asset": {"path": _relative(SEGMENT_ASSET), "key": "segments[] length"},
                "generator": {
                    "path": _relative(PLAN_DOC),
                    "key": "load_investment_clusters()",
                },
            },
            "detail": (
                "the cluster count is recorded twice — as six segment objects in "
                "the asset and as six hard-coded list literals in the plan "
                "document's generator body — but the selection SWEEP that exists in the "
                "same directory (clusteringArtefacts.visibleAnnotations: elbow marked "
                "K=7, maximum silhouette marked K=2) is unlinked to the six-row profile "
                "run, and nothing records which K that run's fitting selected, "
                "so this is a count, not evidence that K was chosen"
            ),
        },
        "featureScaling": {
            "status": "notRecorded",
            "where": None,
            "detail": (
                "no scaler object, mean/scale vector or fitted transformer exists for "
                "the article's six-segment method. The token scan records every file "
                "that mentions a scaler at "
                "methodRecovery.tokenScan.tokens.StandardScaler — including the "
                "pipeline-improvements plan's `StandardScaler()` / `fit_transform` "
                "code EXAMPLE — and none of them is a persisted fitted object for "
                "this method. Preprocessing artefacts DO exist as data elsewhere in "
                "the checkout, so none may be called the only one: the three-tier "
                "cut-point file at adjacentSegmentedPanel.tierThresholds, and the two "
                "threshold files recorded at "
                "clusteringArtefacts.periodDirectory — all of a different taxonomy, "
                "and none recovers this study's scaling"
            ),
        },
        "logTransform": {
            "status": "notRecorded",
            "where": None,
            "detail": (
                "no log/offset parameter or list of transformed columns is stored for "
                "the article's six-segment method. A RELATED transformation IS "
                "documented: docs/archive/20260124-market-insights-fixes-complete.md "
                "(sha-pinned at clusteringArtefacts.documentedVersion) records "
                "`scripts/quick_cluster_profiles.py` updating the log transformation "
                "to a square-foot basis, alongside the label 'Cluster Version 2.0 "
                "(PSF-based)'. The script itself is not in the checkout and its "
                "parameters are not recoverable, so this is documented intent, not a "
                "stored setting"
            ),
        },
        "silhouetteOutputs": {
            "status": "notRecorded",
            "where": None,
            "detail": "a silhouette curve IS stored — optimal_clusters.png is annotated 'Max Silhouette at K=2', recorded as a human visual read at clusteringArtefacts.visibleAnnotations, on a sweep covering K=2 through K=10. What is absent is any link between that sweep and the six-row profile run; and no silhouette score is LINKED OR ATTRIBUTABLE to the article's five-cluster claim — the sweep does plot a K=5 point, but its relationship to that method is unknown. The token scan finds no silhouette implementation on the shipping Python surface (tokenScan.tokens.Silhouette lists the mentions)",
        },
        "elbowOutputs": {
            "status": "notRecorded",
            "where": None,
            "detail": "an elbow curve IS stored — optimal_clusters.png is annotated 'Elbow at K=7', recorded at clusteringArtefacts.visibleAnnotations. What is absent is any link between that sweep and the six-row profile run, and any elbow implementation on the shipping Python surface (tokenScan.tokens.elbow lists the mentions)",
        },
        "compositeScore": {
            "status": "notRecorded",
            "where": None,
            "detail": (
                "the legacy composite investment score (50% appreciation z-score + "
                "50% yield z-score, normalized to 0-100) has no implementation, no "
                "score vector and no normalisation parameters FOR THE ARTICLE'S "
                "POPULATION; the band tables cannot be "
                "recomputed for that population, and the score is not one of the "
                "register's separately-approved app matching weights, which are "
                "recorded and sha256-pinned unchanged at appMatchingWeights"
            ),
            "relatedPrecedent": (
                "docs/archive/20260123-hdb-comprehensive-investment-analysis.md "
                "records a 50/50 appreciation/yield composite with per-town score "
                "vectors (ANG MO KIO 100.0, PUNGGOL 94.3) over 785,395 HDB "
                "transactions, 1990-2026 with a 2015-2025 focus. It states the same "
                "procedure the legacy article states (z-scores for CAGR and yield, "
                "50/50 weights, scaled 0-100), and it records too few parameters to "
                "establish that its normalisation is equivalent, so no difference in "
                "normalisation is claimed. What does differ, measurably, is the "
                "population and period: HDB resale only and 1990-2026 there, against "
                "the article's all-property-type framing and 2017-2026 window. "
                "Precedent, therefore, but not evidence for this article's score"
            ),
        },
        "riskAdjustedMomentum": {
            "status": "notRecorded",
            "where": None,
            "detail": (
                "the legacy risk-adjusted momentum ratio (YoY change divided by "
                "rolling price volatility) has no implementation, no defined rolling "
                "window and no artefact FOR THE ARTICLE'S POPULATION; the archived "
                "2026-01-23 document does publish a per-area Risk-Adjusted Score "
                "table (TANGLIN 0.822 on a sample of 10, SEMBAWANG 0.526 on 1,457), "
                "which shows such a measure was produced elsewhere — on HDB resale "
                "over 1990-2026 rather than the article's all-property 2017-2026 "
                "framing, and without recording its volatility window — so those "
                "values cannot stand in for the article's measure"
            ),
        },
        "modelVersion": {
            "status": "notRecorded",
            "where": None,
            "detail": (
                "the asset's own version field is the payload's schema label, not a "
                "model version. A clustering artefact DOES exist elsewhere in the "
                "checkout: data/analysis/market_segmentation_2.0/ holds a PSF-based "
                "KMeans whose six segment names and shares are the asset's "
                "(clusteringArtefacts records every file, sha-pinned, with the "
                "six-row mapping) — so the version question is answered by that "
                "directory rather than by the asset. A documented version LABEL does "
                "exist and is recorded at clusteringArtefacts.documentedVersion "
                "('Cluster Version: 2.0 (PSF-based)', quoted from the archive with its "
                "hash); what that label is not: a model-library version, or the "
                "identity of the fitted run behind the stored profiles"
            ),
        },
        "clusteringImplementation": {
            "status": "notRecorded",
            "where": None,
            "detail": (
                "the article names MiniBatchKMeans, AgglomerativeClustering and "
                "PCA; no call site for any of them exists under scripts/ or src/ "
                "(tokenScan below). Clustering OUTPUT exists as stored artefacts "
                "under data/analysis/market_segmentation_2.0/ "
                "(clusteringArtefacts) — profiles, PCA scatter and a K-selection "
                "plot — so what is absent is the implementation and its fitted "
                "parameters, not the clustering's products"
            ),
        },
        "featureSet": {
            "status": "recorded",
            "where": {
                "legacy": {"path": _relative(LEGACY_EDITION), "key": "Derived features"},
                "schema": {"path": _relative(UNIFIED), "key": "parquet schema"},
            },
            "detail": (
                "the article's six derived-feature names are recorded, so they can "
                "be matched against the shipped schema: present verbatim, present "
                "under a different name, or absent (featureMap)"
            ),
            "featureMap": feature_map,
        },
        "persistenceRule": {
            "status": "recorded",
            "where": {
                "asset": {"path": _relative(SEGMENT_ASSET), "key": "persistenceProbability"},
                "generator": {
                    "path": _relative(PLAN_DOC),
                    "key": "get_persistence(clusterClassification)",
                },
            },
            "detail": (
                "persistenceProbability takes one value per clusterClassification "
                "(see segmentAsset.persistenceByClassification); the generator "
                "assigns it from the label, so it is a lookup rather than a "
                "measured transition probability"
            ),
        },
    }

    return {
        "items": items,
        "tokenScan": {
            "roots": list(SCAN_ROOTS),
            "suffixes": list(SCAN_SUFFIXES),
            "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
            "excludedPaths": list(EXCLUDED_SCAN_PATHS),
            "excludedEditionTexts": (
                "published edition texts under "
                f"{EDITION_PREFIX} are excluded except the frozen legacy "
                f"originals under {RETAINED_EDITION_PREFIX}, so a study that "
                "signs after RS10 cannot drift this count"
            ),
            "matchCase": False,
            "filesScanned": len(paths),
            "tokens": _token_scan(paths),
            "meaning": (
                "no RS10 implementation or evidence was found in the scanned roots: "
                "no call site that fits, scales or validates a segment model exists "
                "there, and the records that produce the asset are hand-written "
                "literals. Hits are NOT claimed to be uniformly prose or false "
                "positives: the token scan counts code hits under app/src (see the "
                "files lists below), and nothing connects any of them to the shipped "
                "values. The planning/spec surface docs/plans/ is excluded and "
                "disclosed here (excludedPrefixes): it is plan and audit prose "
                "ABOUT the method, including "
                "docs/plans/2026-02-19-pipeline-improvements-plan.md, whose "
                "KMeans/StandardScaler block is a code EXAMPLE in a plan. That "
                "example is no longer counted, which is why the counts below are "
                "narrower than the round-14 ledger's — the exclusion is a scan "
                "boundary, not a change to any RS10 claim. The operational "
                "surface docs/guides/ is excluded for the same reason "
                "(runbooks and setup/CI documentation about the programme; a "
                "guide that names a method is not an implementation of it, and "
                "this scan establishes absence FROM CODE)"
            ),
        },
        "generatorProvenance": {
            "generatorScriptExists": (REPO_ROOT / "scripts" / "generate_segments_data.py").exists(),
            "planDocument": {
                "path": _relative(PLAN_DOC),
                "sha256": sha256_of(PLAN_DOC),
                "outcomeKeys": [
                    _code_quote(PLAN_DOC, '"transactionCount": 114700', "plan-doc-literals"),
                    _code_quote(
                        PLAN_DOC,
                        "output_path = Path('app/public/data/segments_enhanced.json.gz')",
                        "plan-doc-output",
                    ),
                ],
            },
            "handoff": {
                "path": _relative(HANDOFF_DOC),
                "sha256": sha256_of(HANDOFF_DOC),
                "quote": _code_quote(
                    HANDOFF_DOC, "6 segments, 31 planning areas", "handoff-counts"
                ),
            },
            "segmentNamesInAsset": [entry["name"] for entry in asset["segments"]],
            "meaning": (
                "the asset's six segment objects are literal dicts in the plan "
                "document's generator body (values and a '~910K' denominator "
                "comment), and the handoff records running that generator against "
                "hand-written loaders; the deliverables are therefore hand-authored "
                "constants, not the output of a fitted model in this checkout"
            ),
        },
        "legacyIdentityRecovery": _legacy_identity_recovery(paths, asset),
    }


def _legacy_identity_recovery(paths: list[Path], asset: dict[str, Any]) -> dict[str, Any]:
    """Measure where the legacy segment names occur, and whether any id exists.

    "No legacy id exists" is a measurement, not an assertion: each of the five
    names is located in the scanned files, and every line that pairs a name with
    an `id`-shaped field is counted. Zero such lines is the measurement behind
    "there is no legacy id set to map from".
    """
    mentions: dict[str, Any] = {}
    id_pairing_lines = 0
    for name in LEGACY_SEGMENT_NAMES:
        files: list[str] = []
        occurrences = 0
        for path in paths:
            hits = 0
            for line in path.read_text(encoding="utf-8").splitlines():
                if name in line:
                    hits += 1
                    if '"id"' in line or "'id'" in line:
                        id_pairing_lines += 1
            if hits:
                files.append(_relative(path))
                occurrences += hits
        mentions[name] = {
            "occurrences": occurrences,
            "fileCount": len(files),
            "filesFirst": files[:MAX_LISTED],
        }
    article_files = {
        _relative(LEGACY_EDITION),
        "docs/analytics/market-segments.md",
    }
    return {
        "legacyNames": list(LEGACY_SEGMENT_NAMES),
        "mentions": mentions,
        "legacyNamesInAsset": [
            legacy
            for legacy in LEGACY_SEGMENT_NAMES
            if any(legacy.lower() in str(entry["name"]).lower() for entry in asset["segments"])
        ],
        "namesMentionedOutsideTheArticleCopies": sorted(
            name
            for name, entry in mentions.items()
            if entry["fileCount"] > 0 and not set(entry["filesFirst"]).issubset(article_files)
        ),
        "linesPairingANameWithAnIdField": id_pairing_lines,
        "assetIdCount": len(asset["segmentIds"]),
        "meaning": (
            "the article's five segment names occur only as prose or table text "
            "(in the article and its live twin, plus the two findings texts for "
            "the two names the findings repeats); no line pairs a name with an id "
            "field, so no legacy id set exists to map onto the asset's six ids, "
            "and the asset's six names are different names"
        ),
    }


def _parse_band(band: str) -> tuple[float, float] | None:
    match = re.fullmatch(r"~(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)%", band)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def cagr_window(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    months = frame["month"].astype(str)
    year = months.str[:4].astype(int)
    window_months = [
        f"{year_value}-{month_value:02d}"
        for year_value in range(CAGR_WINDOW_START_YEAR, CAGR_WINDOW_END_YEAR + 1)
        for month_value in range(1, 13)
    ]

    per_type: dict[str, Any] = {}
    for property_type in sorted(frame["property_type"].unique()):
        mask = frame["property_type"] == property_type
        observed = sorted(set(months[mask]))
        in_window = [month for month in observed if month in set(window_months)]
        missing = sorted(set(window_months) - set(in_window))
        per_type[str(property_type)] = {
            "rows": int(mask.sum()),
            "firstMonth": observed[0],
            "lastMonth": observed[-1],
            "distinctMonths": len(observed),
            "windowMonthsObserved": len(in_window),
            "windowMonthsExpected": len(window_months),
            "windowMonthsMissing": len(missing),
            "windowMonthsMissingFirst": missing[:MAX_LISTED],
            "rowsInWindow": int((mask & months.isin(window_months)).sum()),
            "cagrWindowAvailable": len(missing) == 0,
        }

    hdb = frame[frame["property_type"] == "hdb"].assign(year=year[frame["property_type"] == "hdb"])
    areas: list[dict[str, Any]] = []
    for area, band, legacy_segment in LEGACY_AREA_BANDS:
        rows = hdb[hdb["planning_area"].astype(str).str.strip().str.upper() == area]
        years: list[int] = []
        year_rows: list[int] = []
        year_psf: list[float | None] = []
        for year_value in range(CAGR_WINDOW_START_YEAR, CAGR_WINDOW_END_YEAR + 1):
            values = rows.loc[rows["year"] == year_value, "psf"].dropna()
            years.append(year_value)
            year_rows.append(int(values.size))
            year_psf.append(_r(values.median(), 2) if values.size else None)
        yearly = [
            {"year": years[index], "rows": year_rows[index], "medianPsf": year_psf[index]}
            for index in range(len(years))
        ]
        start_rows = year_rows[0]
        end_rows = year_rows[-1]
        start_psf = year_psf[0]
        end_psf = year_psf[-1]
        floor_ok = bool(start_rows >= CAGR_AREA_YEAR_FLOOR and end_rows >= CAGR_AREA_YEAR_FLOOR)
        cagr_pct = None
        if floor_ok and start_psf is not None and end_psf is not None and start_psf > 0:
            cagr_pct = _r(
                ((end_psf / start_psf) ** (1 / (CAGR_ENDPOINT_YEAR - CAGR_WINDOW_START_YEAR)) - 1)
                * 100,
                2,
            )
        bounds = _parse_band(band)
        areas.append(
            {
                "area": area,
                "legacyCagrBand": band,
                "legacySegmentLabel": legacy_segment,
                "endpointRows": {
                    "startYear": CAGR_WINDOW_START_YEAR,
                    "startRows": start_rows,
                    "endYear": CAGR_ENDPOINT_YEAR,
                    "endRows": end_rows,
                },
                "endpointMedianPsf": {
                    "startYear": start_psf,
                    "endYear": end_psf,
                },
                "yearRows": yearly,
                "minRowsPerAreaYear": CAGR_AREA_YEAR_FLOOR,
                "floorSatisfied": floor_ok,
                "hdbCagrPct": cagr_pct,
                "withinLegacyBand": (
                    None
                    if (cagr_pct is None or bounds is None)
                    else bool(bounds[0] <= cagr_pct <= bounds[1])
                ),
                "status": (
                    "measured"
                    if cagr_pct is not None
                    else "notMeasurableUnderLegacyFloor"
                    if not floor_ok
                    else "notMeasurable"
                ),
            }
        )

    return {
        "frame": {
            "firstMonth": str(months.min()),
            "lastMonth": str(months.max()),
            "rows": int(len(frame)),
            "propertyTypeValues": {
                str(key): int(value)
                for key, value in sorted(Counter(frame["property_type"]).items())
            },
            "cutoffUpperBound": last_complete,
        },
        "perPropertyType": per_type,
        "window2015to2025": {
            "monthsExpected": len(window_months),
            "availableForHdb": per_type["hdb"]["cagrWindowAvailable"],
            "availableForCondo": per_type["condo"]["cagrWindowAvailable"],
            "meaning": (
                "a 2015-2025 window is available for the HDB rows and not for the "
                "private rows, which begin in the source's own first month; the "
                "article's all-property-type CAGR table therefore cannot be "
                "re-measured as stated"
            ),
        },
        "areaCagr": {
            "definition": (
                "the legacy's own stated definition — 10-year compound annual "
                "growth rate by planning area, minimum 50 transactions per area — "
                "applied to HDB rows only, on median PSF per area-year, with the "
                "floor required at BOTH endpoint years"
            ),
            "minRowsPerAreaYear": CAGR_AREA_YEAR_FLOOR,
            "startYear": CAGR_WINDOW_START_YEAR,
            "endYear": CAGR_ENDPOINT_YEAR,
            "propertyType": "hdb",
            "areas": areas,
            "rowsSatisfyingFloor": sum(1 for area in areas if area["floorSatisfied"]),
            "meaning": (
                "the six planning areas the legacy table names, measured on the "
                "only property type that spans the window; this is a re-measurement "
                "of the HDB subset, not of the legacy's mixed-property-type table"
            ),
        },
    }


def app_matching_weights() -> dict[str, Any]:
    text = MATCHING_HOOK.read_text(encoding="utf-8")
    block = re.search(r"SEGMENT_MATCH_WEIGHTS\s*=\s*\{(?P<body>[^}]*)\}", text)
    if block is None:
        raise SystemExit(
            f"SEGMENT_MATCH_WEIGHTS not found in {_relative(MATCHING_HOOK)}; the weights moved"
        )
    weights: dict[str, int] = {}
    for name, value in re.findall(r"(\w+)\s*:\s*(\d+)", block.group("body")):
        weights[name] = int(value)
    if not weights:
        raise SystemExit("SEGMENT_MATCH_WEIGHTS parsed empty; the weights moved")
    return {
        "path": _relative(MATCHING_HOOK),
        "sha256": sha256_of(MATCHING_HOOK),
        "weights": {key: weights[key] for key in sorted(weights)},
        "weightSum": int(sum(weights.values())),
        "hardFilter": "spatialClassification",
        "changedByThisStudy": False,
        "gateClause": "App matching weights remain unchanged unless separately approved.",
        "meaning": (
            "the app's segment matching weights are recorded and sha256-pinned so "
            "a later change is visible as drift; this study does not change them "
            "and no approval for a change is recorded anywhere"
        ),
    }


def not_measurable(
    asset: dict[str, Any], cohort: dict[str, Any], method: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "id": "featureScaling",
            "gateClause": "Recover feature scaling",
            "status": "notRecorded",
            "reason": (
                "no scaler, log-transform parameter or fitted preprocessing parameter "
                "exists FOR THE ARTICLE'S SIX-SEGMENT METHOD: the asset stores results "
                "only. The scan records every mention of a scaler or a log transform "
                "(methodRecovery.tokenScan.tokens.StandardScaler) — the legacy prose "
                "AND the pipeline-improvements plan's `StandardScaler()` / "
                "`fit_transform` code example — and none of them is a persisted fitted "
                "parameter for this method. Preprocessing artefacts DO exist as data "
                "elsewhere: the three-tier cut-point file at "
                "adjacentSegmentedPanel.tierThresholds and the two threshold files in "
                "clusteringArtefacts.periodDirectory, all of a different taxonomy"
            ),
            "ledgerKey": "methodRecovery.items.featureScaling",
        },
        {
            "id": "clusteringModelVersionAndK",
            "gateClause": "Recover clustering/model version",
            "status": "notRecorded",
            "reason": (
                "no clustering CALL SITE exists under scripts/ or src/ and no fitted "
                "parameters are stored, BUT a clustering artefact does exist: "
                "data/analysis/market_segmentation_2.0/cluster_profiles.csv holds six "
                "KMeans clusters whose names map 1:1 to the six asset ids and whose "
                "cluster_percentage values reproduce the asset's marketShare values "
                "exactly at three decimals (clusteringArtefacts: 6/6 names, 6/6 "
                "shares). The profile counts total 95,531 against the asset's 911,454, "
                "and the per-segment ratios run 9.502 to 9.5831, so the asset's counts "
                "are neither the profile counts nor a constant multiple of them "
                "(clusteringArtefacts.countRatios). A documented version LABEL exists — "
                "'Cluster Version: 2.0 (PSF-based)' — but it is not a model-library "
                "version and not the identity of the fitted run behind the profiles"
            ),
            "ledgerKey": "methodRecovery.items.modelVersion",
        },
        {
            "id": "stabilityEvidence",
            "gateClause": "assess stability",
            "status": "notRecorded",
            "reason": (
                "no STABILITY evidence links to the article's method or to the stored "
                "six-cluster run: a K-selection sweep does exist in the same directory "
                "(clusteringArtefacts.visibleAnnotations records the printed elbow at "
                "K=7 and silhouette maximum at K=2, as a human visual read), but "
                "nothing links that sweep to the six-row profile run and no "
                "per-cluster stability or cross-validation measure is stored; the only "
                "stability-shaped field in the asset is persistenceProbability, "
                "which is constant within each clusterClassification and therefore "
                "a label lookup rather than a measured transition rate"
            ),
            "ledgerKey": "segmentAsset.persistenceByClassification",
        },
        {
            "id": "cohortCountsAsVerifiedPopulations",
            "gateClause": "and cohort counts",
            "status": "notReproducible",
            "reason": (
                "the six transactionCount values are internally consistent with "
                "their own marketShare values, but their total (and every "
                "per-segment count) reproduces no measured population in the "
                "checkout, and no segment's count equals the rows inside its own "
                "declared planning areas; the counts stand only as the asset's own "
                "figures"
            ),
            "ledgerKey": "cohortReconciliation.perSegment",
        },
        {
            "id": "perTransactionMembership",
            "gateClause": "map old/new segment identities",
            "status": "notRecorded",
            "reason": (
                "no shipped column in the 97-column frame carries a stored segment id: "
                "the six ids match zero values in market_segment, property_segment and "
                "price_stratum, and the asset's own stored membership is a "
                "many-to-many planning-area block that assigns no transaction to one "
                "segment. This claim is about THE SIX STORED SEGMENTS and must not be "
                "widened: a per-transaction segmented panel DOES exist under "
                "data/analysis/market_segmentation/ (911,797 rows, three price tiers "
                "assigned per row, plus a tier-threshold file), it carries none of "
                "the six ids, and it is a different taxonomy — recorded at "
                "adjacentSegmentedPanel"
            ),
            "ledgerKey": "adjacentSegmentedPanel",
        },
        {
            "id": "oldToNewIdentityMapping",
            "gateClause": "map old/new segment identities. Do not reuse a segment ID for a different population.",
            "status": "notReproducible",
            "reason": (
                "the legacy five segment names carry no id and no stored membership "
                "in the frame or either asset — methodRecovery.legacyIdentityRecovery "
                "records 0 lines anywhere in the scanned roots that pair one of those "
                "names with an id field — and the asset's six names are different "
                "names, so there is no legacy id set to map onto the new ids; "
                "reusing an old id is not merely prohibited, it has no source"
            ),
            "ledgerKey": "methodRecovery.legacyIdentityRecovery",
        },
        {
            "id": "appMatchingWeights",
            "gateClause": "App matching weights remain unchanged unless separately approved.",
            "status": "notChangedByThisStudy",
            "reason": (
                "the weights are recorded and sha256-pinned for audit; this study "
                "changes no app code and no approval for a weight change is "
                "recorded in the checkout"
            ),
            "ledgerKey": "appMatchingWeights.weights",
        },
    ]


LEGACY_CLAIMS: tuple[dict[str, str], ...] = (
    {
        "id": "C1",
        "phrase": "Five behavioral segments emerge from clustering",
        "status": "withdrawn",
        "ledgerKey": "segmentAsset.segmentCount",
        "note": (
            "the shipped asset holds six segments, not five; the count alone "
            "contradicts the heading, and the five names do not appear in it"
        ),
    },
    {
        "id": "C2",
        "phrase": "| High-Growth HDB           | Newer HDBs in developing towns   | $450-550     | 4-5%         | 8-15%            |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": (
            "no membership exists to compute a PSF/yield/appreciation band for any "
            "named segment, and this name has no counterpart id in the asset"
        ),
    },
    {
        "id": "C3",
        "phrase": "| Stable Mid-Tier           | Mature town HDBs and mass condos | $500-700     | 3-4.5%       | 3-7%             |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": "same as C2: a stored band with no segment population behind it and no matching id",
    },
    {
        "id": "C4",
        "phrase": "| Premium Condo (Low Yield) | Central/RCR condos               | $1,200-2,000 | 2-3%         | 4-8%             |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": "same as C2; the phrase 'Premium Condo' resembles no asset name and no asset id",
    },
    {
        "id": "C5",
        "phrase": "| High-Yield Apartments     | OCR condos near transport hubs   | $800-1,200   | 4-6%         | 5-10%            |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": "same as C2; no membership, no id, no population",
    },
    {
        "id": "C6",
        "phrase": "| Luxury Segment            | CCR condos and landed            | $2,000+      | 1-2.5%       | Variable         |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": "same as C2; 'Variable' is an open-ended band that no measurement can confirm or refute",
    },
    {
        "id": "C7",
        "phrase": "CAGR by planning area (2015-2025)",
        "status": "not-reproducible",
        "ledgerKey": "cagrWindow.window2015to2025",
        "note": (
            "the HDB rows span 2015-2025 and the private rows begin in 2021-01, so "
            "an all-property-type 2015-2025 area CAGR is not measurable from this "
            "frame"
        ),
    },
    {
        "id": "C8",
        "phrase": "10-year compound annual growth rate by planning area, minimum 50 transactions per area",
        "status": "re-measured",
        "ledgerKey": "cagrWindow.areaCagr",
        "note": (
            "the stated definition is adopted verbatim as this ledger's areaCagr "
            "definition and applied to the HDB rows, with the floor required at "
            "both endpoint years"
        ),
    },
    {
        "id": "C9",
        "phrase": "| Bukit Timah   | ~5-7% | $1,800+          | Luxury          |",
        "status": "not-reproducible",
        "ledgerKey": "cagrWindow.areaCagr.areas",
        "note": (
            "the HDB-only measurement of this row is recorded in cagrWindow; the "
            "row's PSF level and its 'Luxury' segment label are not reproducible "
            "from any stored membership"
        ),
    },
    {
        "id": "C10",
        "phrase": "| Queenstown    | ~4-6% | $700-900         | High-Growth HDB |",
        "status": "not-reproducible",
        "ledgerKey": "cagrWindow.areaCagr.areas",
        "note": "the HDB-only measurement is recorded; the row mixes property types and labels a segment with no membership",
    },
    {
        "id": "C11",
        "phrase": "| Jurong East   | ~4-6% | $550-650         | High-Growth HDB |",
        "status": "not-reproducible",
        "ledgerKey": "cagrWindow.areaCagr.areas",
        "note": "same as C10",
    },
    {
        "id": "C12",
        "phrase": "| Punggol       | ~3-5% | $500-600         | High-Growth HDB |",
        "status": "not-reproducible",
        "ledgerKey": "cagrWindow.areaCagr.areas",
        "note": "same as C10",
    },
    {
        "id": "C13",
        "phrase": "| Sengkang      | ~2-4% | $450-550         | Stable Mid-Tier |",
        "status": "not-reproducible",
        "ledgerKey": "cagrWindow.areaCagr.areas",
        "note": "same as C10",
    },
    {
        "id": "C14",
        "phrase": "| Woodlands     | ~1-3% | $400-500         | Stable Mid-Tier |",
        "status": "not-reproducible",
        "ledgerKey": "cagrWindow.areaCagr.areas",
        "note": "same as C10",
    },
    {
        "id": "C15",
        "phrase": "50% appreciation z-score + 50% yield z-score, normalized to 0-100",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.compositeScore",
        "note": (
            "no composite-score artefact or implementation exists for this article's "
            "score; the weights are stated only in prose, and the segment surface "
            "explicitly disclaims computing an investment score"
        ),
    },
    {
        "id": "C16",
        "phrase": "| 0-19        | Weak           | Depreciating or oversupplied areas            |",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.compositeScore",
        "note": "the score bands have no definition, no artefact and no area list behind them",
    },
    {
        "id": "C17",
        "phrase": "with >85% agreement on cluster assignments",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.silhouetteOutputs",
        "note": "no hierarchical validation run, agreement table or assignment artefact is stored for this study's method (methodRecovery.tokenScan.tokens.AgglomerativeClustering lists the files that mention it; none is an RS10 artefact)",
    },
    {
        "id": "C18",
        "phrase": "(r ~ -0.3)",
        "status": "not-reproducible",
        "ledgerKey": "segmentAsset.internalCorrelations",
        "note": (
            "the article's cited sentence — 'Yield and appreciation are weakly "
            "negatively correlated (r ~ -0.3)' — DOES NOT SPECIFY the observational "
            "unit: it could be within clusters, across transaction records, or across "
            "segment summaries. The statistic is therefore UNDESPECIFIED and cannot be "
            "reproduced from this evidence, and this note must not prescribe what its "
            "unit was. What can be stated is separate: no per-transaction membership "
            "for the six stored segments exists, and a correlation across the six "
            "aggregate profile rows is computable and recorded at "
            "segmentAsset.internalCorrelations — unlinked to the article's method, so "
            "it is neither the article's statistic nor evidence about it"
        ),
    },
    {
        "id": "C19",
        "phrase": "~288K records (2021-2026 emphasis)",
        "status": "not-reproducible",
        "ledgerKey": "cohortReconciliation.candidatePopulations",
        "note": (
            "the measured row counts for the article's own windows are recorded "
            "there; none equals the stated volume, and none equals the asset's "
            "cohort total either"
        ),
    },
    {
        "id": "C20",
        "phrase": "provides the best balance of interpretability and granularity based on silhouette analysis",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.silhouetteOutputs",
        "note": (
            "no silhouette result is LINKED OR ATTRIBUTABLE to the article's "
            "five-cluster claim. Silhouette EVIDENCE does exist in the checkout and "
            "is recorded rather than denied: "
            "clusteringArtefacts.visibleAnnotations reports the K-selection plot's "
            "printed maximum at K=2, on a sweep that plots K=2 through K=10 including "
            "a K=5 point whose relationship to the article's method is unknown. That "
            "plot is NOT evidence for the five-cluster claim and equally not evidence "
            "against it; because the sweep is unlinked, it establishes neither that a "
            "five-cluster selection output exists for the article's method, nor that "
            "none exists. Separately, the shipped asset holds six segments while the "
            "claim names five"
        ),
    },
    {
        "id": "C21",
        "phrase": "Log-transform for skewed variables, StandardScaler normalization",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.featureScaling",
        "note": (
            "no scaler parameters, offset or transformed-column list is stored FOR THE "
            "ARTICLE'S METHOD. Related clustering does exist — the PSF-based KMeans "
            "profiles and the archive's 'Cluster Version 2.0 (PSF-based)' label — but "
            "that run is UNLINKED to the article's method and its own scaling is "
            "UNKNOWN, so it bears neither for nor against the article's scaler claim. "
            "Preprocessing "
            "artefacts DO exist as data elsewhere (tier thresholds in data/analysis, "
            "two files in the period directory), which is why this is scoped to the "
            "article's method rather than to the checkout"
        ),
    },
    {
        "id": "C22",
        "phrase": "Cluster assignments per transaction with segment labels",
        "status": "withdrawn",
        "ledgerKey": "membershipRecovery.segmentIdMatchesInColumns",
        "note": (
            "no per-transaction assignment OF THE SIX STORED SEGMENTS exists in any "
            "column of the 97-column frame: the six ids match zero column values, and "
            "the asset's own stored membership is a many-to-many planning-area block. "
            "A different, three-tier per-row segmentation does exist under "
            "data/analysis (adjacentSegmentedPanel); it is not this taxonomy"
        ),
    },
    {
        "id": "C23",
        "phrase": "**Data Period**: 2017-2026, with emphasis on 2021-2026",
        "status": "withdrawn",
        "ledgerKey": "cagrWindow.perPropertyType",
        "note": (
            "the private rows begin in 2021-01, so 2017-only coverage exists for "
            "the HDB rows; the period cannot describe the asset's mixed population"
        ),
    },
    {
        "id": "C24",
        "phrase": "clusters are defined on 2021-2026 data and may shift as market conditions change",
        "status": "not-reproducible",
        "ledgerKey": "cohortReconciliation.candidatePopulations",
        "note": (
            "the stated window is measurable for the private rows, but the asset's "
            "cohort total reproduces no measured window, so the definition window "
            "cannot be confirmed for the stored clusters"
        ),
    },
    {
        "id": "C25",
        "phrase": "| 80-100      | Exceptional    | Emerging towns with new MRT lines             |",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.compositeScore",
        "note": (
            "the composite score is described only in prose (50% appreciation z + "
            "50% yield z, normalized to 0-100); no implementation or score vector "
            "exists FOR THE ARTICLE'S POPULATION, so the band cannot be recomputed. "
            "The archived 2026-01-23 HDB analysis does carry score vectors, which is "
            "recorded at methodRecovery.items.compositeScore.relatedPrecedent and is "
            "a different population and period, not this article's score"
        ),
    },
    {
        "id": "C26",
        "phrase": "| 60-79       | Strong         | Mature estates with good yield                |",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.compositeScore",
        "note": "same as C25: the score definition has no implementation to re-run",
    },
    {
        "id": "C27",
        "phrase": "| 40-59       | Average        | Most established areas                        |",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.compositeScore",
        "note": "same as C25: the score definition has no implementation to re-run",
    },
    {
        "id": "C28",
        "phrase": "| 20-39       | Below average  | Luxury areas (low yield offsets appreciation) |",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.compositeScore",
        "note": (
            "same as C25, and the interpretation itself is an unsupported "
            "explanation: no yield/appreciation decomposition supporting THIS band "
            "and population is available. The archived 2026-01-23 analysis does "
            "report area-level CAGR, rental yield and composite scores, which is a "
            "precedent for such a decomposition on a different population and period "
            "— not evidence for this explanation"
        ),
    },
    {
        "id": "C29",
        "phrase": "| Hold & Grow       | High yield + strong appreciation (>6% yield, >10% growth) | High            | Medium-High | Experienced investors    |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": (
            "a strategy screen defined against yield and growth thresholds. Six "
            "aggregate yield/growth pairs DO exist (the cluster-profile rows, one of "
            "which meets the stated >6% yield and >10% growth thresholds), but they "
            "are unlinked to the article's strategy populations, so they cannot "
            "identify the strategy's members; and with no per-transaction membership "
            "no population can be assigned to it"
        ),
    },
    {
        "id": "C30",
        "phrase": "| Yield Play        | High rental yield focus (>6%)                             | Medium          | Low-Medium  | Income-focused investors |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": "same as C29: the threshold is defined, the population it screens is not recoverable",
    },
    {
        "id": "C31",
        "phrase": "| Growth Play       | High appreciation potential (>15% YoY)                    | High            | High        | Speculative investors    |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": "same as C29: no membership means no YoY series can be attributed to a segment",
    },
    {
        "id": "C32",
        "phrase": "| Value Investing   | Affordable entry (<$5,000 PSF)                            | Medium          | Low         | First-time buyers        |",
        "status": "not-reproducible",
        "ledgerKey": "membershipRecovery.perTransactionMembership",
        "note": (
            "the only strategy whose screen could in principle be evaluated against "
            "transactions, but it is attributed to segments that have no membership, "
            "so the claim is about a population this checkout cannot build"
        ),
    },
    {
        "id": "C33",
        "phrase": "most areas cluster around 2-5%",
        "status": "not-reproducible",
        "ledgerKey": "cagrWindow.areaCagr",
        "note": (
            "a distributional claim over planning areas; the ledger measures CAGR only "
            "for the legacy's six named areas under its own 50-transaction floor, which "
            "is not enough to characterise a distribution, and one of the six is "
            "refused as below the floor"
        ),
    },
    {
        "id": "C34",
        "phrase": "A town with 4-5% CAGR and affordable entry is often a better long-term bet",
        "status": "withdrawn",
        "ledgerKey": "cagrWindow.areaCagr",
        "note": (
            "investment advice, not a measurement; the ledger reports the measured "
            "CAGR per named area without a return, risk or affordability comparison "
            "that could support the recommendation"
        ),
    },
    {
        "id": "C35",
        "phrase": "Risk-adjusted momentum (YoY change divided by price volatility)",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.riskAdjustedMomentum",
        "note": (
            "the ratio is defined in prose only; no rolling window, no numerator or "
            "denominator series and no per-area momentum value exists FOR THE "
            "ARTICLE'S POPULATION, so the measure cannot be recomputed. The archived "
            "2026-01-23 analysis publishes per-area Risk-Adjusted Scores on a different "
            "population and without its volatility window "
            "(methodRecovery.items.riskAdjustedMomentum)"
        ),
    },
    {
        "id": "C36",
        "phrase": "YoY change divided by rolling price volatility",
        "status": "not-reproducible",
        "ledgerKey": "methodRecovery.items.riskAdjustedMomentum",
        "note": (
            "the methodology restates the same ratio; the rolling window it names is "
            "never specified, and no fitted or stored momentum series exists"
        ),
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
    """Every claim's key must resolve, or the build fails.

    Two of this study's claim keys pointed at paths that did not exist, and RS09
    shipped three; a disposition whose key resolves to nothing is not evidence, and
    no reviewer should have to find that class twice. Lists are traversed by their
    items' `id`, so `notMeasurable.featureScaling` and `methodRecovery.items.
    featureScaling` are both resolvable forms.
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
        "method": (
            "each claim's ledgerKey is resolved against this ledger at build time by "
            "walking dict keys and list items by their `id`; an unresolved key fails "
            "the build rather than shipping"
        ),
    }


def adjacent_segmented_panel(asset: dict[str, Any], cohort: dict[str, Any]) -> dict[str, Any]:
    """A per-transaction segmented panel exists under `data/analysis`, and must be recorded.

    This study's first draft scanned `data/pipeline` and `app/public/data` and concluded
    that no per-transaction membership existed. That was true only of those roots: a
    61-column transaction panel under `data/analysis/market_segmentation/` carries
    per-row `market_tier` and `psf_tier` labels, a `Market Segment` region label, a
    month range and a price column. It is a DIFFERENT taxonomy from the asset's six
    segments (three price tiers, not six ids) and it carries none of the asset's ids,
    so the article's taxonomy still has no membership — but the absence claim has to be
    stated against the whole checkout, not against two directories.
    """
    panel = pd.read_parquet(SEGMENTED_PANEL)
    names = [str(name) for name in panel.columns]
    label_columns = [name for name in names if "tier" in name.lower() or "segment" in name.lower()]
    distributions: dict[str, Any] = {}
    for column in label_columns:
        counts = panel[column].value_counts(dropna=False)
        distributions[column] = {
            "distinctValues": int(len(counts)),
            "nullRows": int(panel[column].isna().sum()),
            "top": {str(key): int(value) for key, value in list(counts.items())[:6]},
        }
    asset_ids = [str(identifier) for identifier in asset["segmentIds"]]
    id_matches = {
        identifier: int(
            sum(int((panel[column].astype(str) == identifier).sum()) for column in names)
        )
        for identifier in asset_ids
    }
    asset_total = int(cohort["assetTotalTransactions"])
    thresholds = (
        {
            "path": _relative(TIER_THRESHOLDS),
            "sha256": sha256_of(TIER_THRESHOLDS),
            "content": TIER_THRESHOLDS.read_text(encoding="utf-8").strip(),
        }
        if TIER_THRESHOLDS.is_file()
        else None
    )
    # The annual tier panel is tier-level PRICE evidence, and the distinction
    # matters: it is not a planning-area observation table and not the asset's
    # six segments, so it cannot be read as a segment-level constant-quality
    # index and it does not enter cagrWindow.areaCagr.
    tier_frame = pd.read_parquet(TIER_PANEL)
    tier_columns = [str(name) for name in tier_frame.columns]
    tier_panel = {
        "path": _relative(TIER_PANEL),
        "sha256": sha256_of(TIER_PANEL),
        "rows": int(len(tier_frame)),
        "columns": tier_columns,
        "keyColumns": [
            name for name in ("property_type", "market_tier", "year") if name in tier_columns
        ],
        "measureColumns": [
            name
            for name in ("median_price", "median_psf", "transaction_count")
            if name in tier_columns
        ],
        "hasPlanningArea": "planning_area" in tier_columns,
        "yearRange": (
            {"first": int(tier_frame["year"].min()), "last": int(tier_frame["year"].max())}
            if "year" in tier_columns
            else None
        ),
        "propertyTypes": (
            {str(k): int(v) for k, v in tier_frame["property_type"].value_counts().items()}
            if "property_type" in tier_columns
            else None
        ),
        "meaning": (
            "annual tier-level price evidence keyed by property type, market tier and "
            "year, carrying median price, median psf and transaction count. It has no "
            "planning-area column and uses the three-tier taxonomy, so it neither "
            "reproduces the planning-area CAGR table (cagrWindow.areaCagr is "
            "unaffected) nor constitutes a segment-level constant-quality price "
            "index for the six stored segments"
        ),
    }
    return {
        "path": _relative(SEGMENTED_PANEL),
        "sha256": sha256_of(SEGMENTED_PANEL),
        "rows": int(len(panel)),
        "columns": int(len(names)),
        "monthRange": (
            {"first": str(panel["month"].min())[:7], "last": str(panel["month"].max())[:7]}
            if "month" in names
            else None
        ),
        "hasPlanningArea": "planning_area" in names,
        "hasPrice": "price" in names,
        "taxonomyColumns": label_columns,
        "taxonomyDistributions": distributions,
        "assetIdMatches": id_matches,
        "assetIdMatchTotal": int(sum(id_matches.values())),
        "assetCohortTotal": asset_total,
        "rowsMinusAssetCohortTotal": int(len(panel) - asset_total),
        "tierThresholds": thresholds,
        "tierPanel": tier_panel,
        "meaning": (
            "a per-transaction segmented panel DOES exist in this checkout, under "
            "data/analysis/market_segmentation/, with three price tiers assigned per "
            "row and a tier-threshold file defining the cut points. It is not the "
            "article's segmentation: it carries none of the six asset ids (0 matches "
            "measured across all 61 columns), its row count is "
            f"{int(len(panel)) - asset_total:+d} against the asset's cohort total, and "
            "its labels are price tiers rather than behavioural clusters. So 'the six "
            "stored segments have no membership' stands; 'no per-transaction "
            "segmentation exists in the checkout' would be false"
        ),
    }


def clustering_artefacts() -> dict[str, Any]:
    """The six segment names and shares ARE KMeans v2.0 output — measure the lineage.

    Three earlier versions of this ledger asserted that the six segments were
    hand-written literals with no model output behind them. That was wrong, and
    wrong in the way this study keeps being wrong: the evidence sits in a
    directory the producer never read. `data/analysis/market_segmentation_2.0/`
    holds a PSF-based KMeans clustering whose six `segment_name` values map one
    to one onto the asset's six ids, and whose `cluster_percentage` values
    reproduce the asset's `marketShare` values exactly at three decimals. What is
    *not* reproduced is the counts: the profile cluster counts total **95,531**
    against the asset's **911,454**, so the asset's `transactionCount` values are
    those counts scaled to a ~910K denominator, not the clustering's own sizes.
    """
    profiles = pd.read_csv(SEG_V2_DIR / "cluster_profiles.csv")
    try:
        asset_payload = json.loads(gzip.decompress(SEGMENT_ASSET.read_bytes()).decode("utf-8"))
    except (OSError, gzip.BadGzipFile, json.JSONDecodeError) as error:
        raise SystemExit(f"Unreadable segment asset {SEGMENT_ASSET}: {error}") from error
    asset_shares = {
        str(segment["id"]): segment.get("metrics", {}).get("marketShare")
        for segment in asset_payload.get("segments", [])
    }
    asset_ids = set(asset_shares)
    rows: list[dict[str, Any]] = []
    for _index, profile in profiles.iterrows():
        name = str(profile["segment_name"])
        slug = name.strip().lower().replace(" ", "_").replace("-", "_")
        share = asset_shares.get(slug)
        percentage = float(profile["cluster_percentage"])
        rows.append(
            {
                "segmentName": name,
                "derivedSlug": slug,
                "assetIdMatch": slug in asset_ids,
                "clusterCount": int(profile["cluster_kmeans_count"]),
                "clusterPercentage": _r(percentage, 6),
                "assetMarketShare": _r(share, 6) if share is not None else None,
                "shareMatchesAsset": (
                    share is not None and _r(percentage / 100.0, 3) == _r(float(share), 3)
                ),
                "pricePsfMean": _r(float(profile["price_psf_mean"]), 3),
                "yoyChangePctMean": _r(float(profile["yoy_change_pct_mean"]), 3),
            }
        )
    cluster_total = int(sum(row["clusterCount"] for row in rows))
    # Asset count divided by profile cluster count, per segment. These are NOT
    # constant, which is why no single scaling factor is claimed.
    asset_counts = {
        str(segment["id"]): int(segment["metrics"]["transactionCount"])
        for segment in asset_payload.get("segments", [])
        if segment.get("metrics", {}).get("transactionCount") is not None
    }
    ratios: dict[str, float] = {}
    for row in rows:
        asset_count = asset_counts.get(str(row["derivedSlug"]))
        cluster_count = int(row["clusterCount"])
        if asset_count is not None and cluster_count > 0:
            value = _r(asset_count / cluster_count, 4)
            if value is not None:
                ratios[str(row["derivedSlug"])] = value
    files = []
    for path in sorted(SEG_V2_DIR.iterdir()):
        if path.is_file():
            files.append(
                {
                    "path": _relative(path),
                    "bytes": int(path.stat().st_size),
                    "sha256": sha256_of(path),
                }
            )
    period_files = []
    if SEG_PERIOD_DIR.is_dir():
        for path in sorted(SEG_PERIOD_DIR.iterdir()):
            if path.is_file():
                period_files.append(
                    {
                        "path": _relative(path),
                        "bytes": int(path.stat().st_size),
                        "sha256": sha256_of(path),
                    }
                )
    return {
        "directory": _relative(SEG_V2_DIR),
        "files": files,
        "profileRows": rows,
        "nameSlugMatches": sum(1 for row in rows if row["assetIdMatch"]),
        "shareMatches": sum(1 for row in rows if row["shareMatchesAsset"]),
        "clusterCountTotal": cluster_total,
        "assetCohortTotal": int(
            sum(
                int(asset_payload["segments"][index]["metrics"]["transactionCount"])
                for index in range(len(asset_payload.get("segments", [])))
            )
        ),
        "profileCountsReproduceAssetCounts": False,
        "countRatios": {
            "definition": "asset transactionCount / profile clusterCount, per segment",
            "values": ratios,
            "min": _r(min(ratios.values()), 4) if ratios else None,
            "max": _r(max(ratios.values()), 4) if ratios else None,
            "isCommonScaleFactor": False,
            "meaning": (
                "the ratios are NOT constant, so the asset's counts are not the profile "
                "counts multiplied by one scale factor; each segment was rounded/"
                "approximated separately. The counts are approximately share-proportional "
                "on a ~910K base, which is what the plan document's comment records, and "
                "that is a weaker statement than a measured rescaling"
            ),
        },
        "meaning": (
            "the six segment NAMES and SHARES correspond to stored KMeans profile "
            "output: every segment_name maps to an asset id and every "
            "cluster_percentage reproduces the asset's marketShare at three decimals. "
            "That is a measured CORRESPONDENCE, not a proven lineage — nothing in the "
            "directory links these profiles to the code that wrote the asset, and the "
            "plot artefacts beside them are a K sweep and a K=2 visualisation, not the "
            "six-cluster run (see visibleAnnotations). The asset's COUNTS are neither "
            "the profile counts nor a constant multiple of them (countRatios), so the "
            "plan document's transactionCount literals are approximate share values on "
            "a ~910K base. No per-transaction membership for the six ids exists in the "
            "frame or in these files; the profiles are aggregate cluster summaries."
        ),
        "visibleAnnotations": {
            "method": (
                "HUMAN VISUAL READ of the two sha-pinned PNGs by the producer, recorded "
                "because the pixels are not machine-read. The hashes above pin exactly "
                "which images were read; the values below are what they visibly print, "
                "and are not a re-derived score"
            ),
            "optimal_clusters.png": {
                "title": "Elbow Method for Optimal K (left) and Silhouette Analysis for Optimal K (right)",
                "xAxis": "Number of Clusters (K), 2 through 10",
                "elbow": "a dashed rule labelled 'Elbow at K=7'",
                "silhouette": "a dashed rule labelled 'Max Silhouette at K=2', peak about 0.235 at K=2",
                "silhouetteAtK6": "about 0.156 at the plotted K=6 point — a point on the SAME unlinked sweep, not a score for the stored six-cluster profile run",
            },
            "clusters_pca.png": {
                "title": "Market Segments - PCA Visualization (K=2)",
                "implication": "the scatter is coloured for two clusters, so it is not a visualisation of the six-cluster solution",
            },
            "runLinkage": (
                "the plots record a K sweep (elbow marked K=7, maximum silhouette marked "
                "K=2) and a K=2 visualisation; the profile CSV holds six clusters. "
                "NOTHING in the directory links either plot to the same fitted run as "
                "the six-row profiles, and that limits what may be concluded in BOTH "
                "directions: the unlinked sweep marks K=2 as its own silhouette maximum "
                "and K=7 as its own elbow, and it does NOT establish what the profile "
                "run's K=6 scored, nor that K=6 was suboptimal. What can be said is "
                "narrower: a selection sweep exists whose annotations are K=2 "
                "(silhouette maximum) and K=7 (elbow); it does NOT annotate K=6 as "
                "either, and whether it is the same run as the stored profiles is "
                "unestablished"
            ),
        },
        "documentedVersion": {
            "value": "Cluster Version: 2.0 (PSF-based)",
            "source": {
                "path": "docs/archive/20260124-market-insights-fixes-complete.md",
                "line": 156,
                "sha256": sha256_of(ARCHIVE_DOC),
                "quote": "_Cluster Version: 2.0 (PSF-based)_",
            },
            "meaning": (
                "a documented version label does exist for the clustering, and the same "
                "archive names scripts/quick_cluster_profiles.py as the record that "
                "updated the log transformation to square-foot basis. What that label "
                "does NOT establish: a model-library version, the identity of the fitted "
                "run behind the stored profile CSV, or reproducible parameters — the "
                "script itself is not in the checkout"
            ),
        },
        "periodDirectory": {
            "directory": _relative(SEG_PERIOD_DIR),
            "files": period_files,
            "meaning": (
                "a second segmentation directory holding another 911,797-row "
                "period-labelled panel plus two tier-threshold files "
                "(recent_periods and evolution). It adds no asset ids and is not the "
                "article's six-segment taxonomy, but its threshold files are "
                "preprocessing artefacts that exist as data — so no claim may say "
                "the tier-threshold CSV is the only such artefact"
            ),
        },
    }


def build() -> dict[str, Any]:
    frame = pd.read_parquet(
        UNIFIED,
        columns=[
            "month",
            "property_type",
            "planning_area",
            "psf",
            "market_segment",
            "property_segment",
            "price_stratum",
        ],
    )
    measured_cutoff = cutoff(frame)
    last_complete = measured_cutoff["lastCompleteMonth"]
    asset = segment_asset()
    cohort = cohort_reconciliation(frame, asset, last_complete)
    method = method_recovery(_scan_files(), asset)
    claims = legacy_claims()

    inputs = {}
    for path in (
        UNIFIED,
        SEGMENT_ASSET,
        DASHBOARD_ASSET,
        LEGACY_EDITION,
        SEGMENTED_PANEL,
        TIER_PANEL,
        TIER_THRESHOLDS,
    ):
        inputs[_relative(path)] = {"sha256": sha256_of(path), "bytes": int(path.stat().st_size)}
    inputs[_relative(UNIFIED)]["rows"] = int(pq.ParquetFile(UNIFIED).metadata.num_rows)
    inputs[_relative(UNIFIED)]["columns"] = int(len(pq.read_schema(UNIFIED).names))
    for path in (SEGMENTED_PANEL, TIER_PANEL):
        inputs[_relative(path)]["rows"] = int(pq.ParquetFile(path).metadata.num_rows)
        inputs[_relative(path)]["columns"] = int(len(pq.read_schema(path).names))

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": "RS10",
        "series": "market-segments",
        "scope": (
            "RS10 market-segments evidence: the stored segment asset's inventory, "
            "its internal cohort arithmetic, what membership can and cannot be "
            "joined to the shipped frame, the dashboard asset's identity "
            "intersection, what of the legacy method is recorded anywhere, and the "
            "observed CAGR window per property type"
        ),
        "definition": DEFINITION,
        "inputs": inputs,
        "cutoff": measured_cutoff,
        "segmentAsset": asset,
        "cohortReconciliation": cohort,
        "membershipRecovery": membership_recovery(frame, asset),
        "adjacentSegmentedPanel": adjacent_segmented_panel(asset, cohort),
        "clusteringArtefacts": clustering_artefacts(),
        "dashboardAssetContrast": dashboard_contrast(asset),
        "methodRecovery": method,
        "cagrWindow": cagr_window(frame, last_complete),
        "appMatchingWeights": app_matching_weights(),
        "notMeasurable": not_measurable(asset, cohort, method),
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
        print("Pass: RS10 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS10 ledger does not match this checkout")
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

    asset = evidence["segmentAsset"]
    matches = evidence["membershipRecovery"]["segmentIdMatchesInColumns"]
    print(
        f"Cutoff: last complete month {evidence['cutoff']['lastCompleteMonth']} "
        f"(terminal {evidence['cutoff']['terminalMonth']} at "
        f"{evidence['cutoff']['terminalMonthShareOfTrailingMedian']} of the trailing median)"
    )
    print(
        f"Segment asset: {asset['segmentCount']} segments, version {asset['version']}, "
        f"ids unique={asset['segmentIdsUnique']}"
    )
    print("Segment ids: " + ", ".join(asset["segmentIds"]))
    print(
        "Cohort total: "
        f"{evidence['cohortReconciliation']['assetTotalTransactions']} "
        f"(shares sum {evidence['cohortReconciliation']['marketShareSum']}), "
        f"reproduces a shipped population="
        f"{evidence['cohortReconciliation']['anyPopulationEqualsAssetTotal']}"
    )
    print(
        "Membership: segment-id matches in shipped columns = "
        f"{matches['total']}; "
        f"rows covered by the asset's planning areas = "
        f"{evidence['membershipRecovery']['areaLevelJoin']['rowsCoveredByAssetAreas']}"
    )
    print(
        "Dashboard asset: "
        f"{evidence['dashboardAssetContrast']['keyCount']} keys, "
        f"has segment id field={evidence['dashboardAssetContrast']['hasSegmentIdField']}, "
        f"shared ids with the segment asset="
        f"{evidence['dashboardAssetContrast']['idIntersectionWithSegmentAsset']['sharedIds']}"
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
    sys.exit(main())
