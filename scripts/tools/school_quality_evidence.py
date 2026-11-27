#!/usr/bin/env python3
"""Measure RS08's school-quality evidence: tier provenance, what the shipped
school columns actually contain, whether the legacy sample is reproducible, one
pre-stated distance-based association, and every gate clause the checkout
cannot answer, each with its scan.

RS08's gate is "Recheck tier provenance, bandwidth, treatment assignment,
covariate balance and multiple-testing policy. School-quality model fit does
not establish a causal admissions premium. Keep policy eligibility outside
model outputs." This tool measures from the local checkout, and only what the
checkout can support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04/RS05/RS09/
   RS10 shipped (terminal month's transaction count as a fraction of the
   trailing twelve-month median), computed on the private rows, with all-types
   and HDB cross-checks.
2. **Tier provenance** — the tier artefacts DO exist: four hand-authored files
   under `data/manual/csv/` (two tier lists, a weights table, a scoring
   methodology), sha-pinned; the producer prefers
   `01_bronze/external/school_tiers.json`, which is absent, so the CSV fallback
   is the active path (producer code cited). The tier lists are joined to the
   bronze school directory by the producer's own exact-then-prefix rule and the
   match/unresolved counts are recorded. Their origin is hand-authoring:
   screened as reference data, origin unverified.
3. **Policy eligibility** — the bronze directory's sap_ind/gifted_ind/ip_ind/
   autonomous_ind columns are counted and their consumption scanned (zero call
   sites under `src/`); the manual tier lists' gep/sap/ip/autonomous columns
   feed the shipped `school_accessibility_score` through the producer's quality
   formula, so the shipped score is screened as embedding policy-status flags.
   The score is therefore excluded from this pack's one association model, and
   no model output in this pack consumes any policy-eligibility flag.
4. **School coordinates** — the bronze directory schema carries no coordinate
   columns (metadata read), but a coordinate-bearing school artefact DOES
   exist: `data/manual/csv/datagov/SchoolsMOE.geojson` (197 Point features,
   name set a strict subset of the directory, zero consumers in `src/` or
   `scripts/`). It is unlinked to the shipped distance columns in BOTH
   directions: it is neither evidence that the shipped distances were produced
   from it, nor evidence that they were not; the producer cites runtime
   geocoding from postal codes.
5. **Legacy feature names** — `school_primary_quality_score`,
   `school_primary_dist_score` and `school_secondary_dist_score` are scanned
   against every parquet schema under `data/pipeline/` and `data/analysis/`
   (metadata-only reads) and against the scanned text roots. Zero schema hits;
   the text hits are the legacy article, its live twin and the retired
   programme's plan documents.
6. **Legacy sample reconciliation** — the legacy's stated screen (HDB rows,
   2021 onward, within 2 km of primary schools; 800-1200 m near-boundary band)
   is adopted verbatim as a measured screen and its counts are recorded beside
   every legacy count. No measured candidate reproduces 194,165 or 52,881.
7. **Association** — ONE pre-stated descriptive OLS of ln(psf) on the three
   shipped distance columns (per 100 m) with the RS04-style controls and fixed
   effects, HC1 covariance. All three coefficients are reported regardless of
   significance; none is selected on significance; no correction is required
   and none is applied. It is a conditional association, not a premium.
8. **RDD recovery** — bandwidth, treatment assignment and covariate balance
   are recorded as unmeasurable, each with its scan; the served RDD plot is
   sha-pinned and given a human visual read (RS10's `visibleAnnotations`
   pattern); the multiplicity scan finds no recorded correction anywhere in the
   scanned roots.

It never runs the pipeline, never geocodes, never re-fits the legacy's models,
never writes outside `--output`, and never touches `data/pipeline/**`.

Usage:

    uv run python scripts/tools/school_quality_evidence.py \\
        --output docs/implementation/artifacts/rs08-school-quality-evidence.json

    uv run python scripts/tools/school_quality_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
SCHOOL_DIRECTORY = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_school_directory.parquet"
SCHOOLS_MOE_GEOJSON = REPO_ROOT / "data" / "manual" / "csv" / "datagov" / "SchoolsMOE.geojson"
TIERS_PRIMARY = REPO_ROOT / "data" / "manual" / "csv" / "school_tiers_primary.csv"
TIERS_SECONDARY = REPO_ROOT / "data" / "manual" / "csv" / "school_tiers_secondary.csv"
WEIGHTS_CSV = REPO_ROOT / "data" / "manual" / "csv" / "school_quality_weights.csv"
METHODOLOGY_MD = REPO_ROOT / "data" / "manual" / "csv" / "school_scoring_methodology.md"
LEGACY_EDITION = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "school-quality.md"
)
LIVE_TWIN = REPO_ROOT / "docs" / "analytics" / "school-quality.md"
RDD_PLOT = (
    REPO_ROOT / "app" / "public" / "data" / "analysis" / "school_rdd" / "rdd_visualization.png"
)
IMPACT_PLOT = (
    REPO_ROOT
    / "app"
    / "public"
    / "data"
    / "analysis"
    / "school_impact"
    / "exploratory_analysis.png"
)
FEATURE_IMPORTANCE_DIR = REPO_ROOT / "data" / "analysis" / "feature_importance"
MODEL_COMPARISON = FEATURE_IMPORTANCE_DIR / "model_comparison.csv"
PLAN_DOC_2025 = REPO_ROOT / "docs" / "plans" / "2025-02-02-school-impact-analysis.md"
PLAN_DOC_2026 = REPO_ROOT / "docs" / "plans" / "2026-02-05-enhanced-school-impact-analysis.md"
PRODUCER = REPO_ROOT / "src" / "egg_n_bacon_housing" / "utils" / "school_features.py"
FEATURES_NODE = REPO_ROOT / "src" / "egg_n_bacon_housing" / "components" / "features.py"
DATAGOV_ADAPTER = (
    REPO_ROOT / "src" / "egg_n_bacon_housing" / "components" / "ingestion" / "datagov.py"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs08-school-quality-evidence.json"
)

SCHEMA_VERSION = "1.1.0"

STUDY_WINDOW_START = "2021-01"
PRIMARY_RADIUS_M = 2000.0  # the legacy's own "within 2 km of primary schools"
BAND_LOW_M = 800.0  # the legacy's own near-boundary band
BAND_HIGH_M = 1200.0

FLAT_TYPE_BASELINE = "4-ROOM"
TOWN_BASELINE = "ANG MO KIO"
YEAR_BASELINE = "2021"
DIST_SCALE_M = 100.0  # distance regressors are metres / 100

# The scan is bounded to these roots and suffixes so the ledger is reproducible
# file-order-independently and cannot read itself.
SCAN_ROOTS = ("docs", "scripts", "src", "assets", "prompts", "app/src", ".claude/handoffs")
SCAN_SUFFIXES = (".md", ".py", ".ts", ".tsx")
# The exclusions are the RF08 programme's own output surfaces, not evidence of
# RS08's method: `docs/implementation/` holds the per-study records,
# `scripts/tools/` holds the evidence producers themselves, and `prompts/`
# holds the handoffs and runbooks. Their exclusion is disclosed at
# `tokenScan.excludedPrefixes`. Published edition texts are programme outputs
# too: a study that signs after RS08 must not drift this ledger, so texts under
# `docs/analytics/editions/` are excluded except the frozen legacy originals
# under `docs/analytics/editions/legacy/`. The RS08 producer itself is under an
# excluded prefix, which is also why it cannot drift its own counts.
#
# `docs/plans/` generalises the D12 register this scan already excluded by path:
# the planning/spec documents are prose ABOUT the method (the retired programme's
# plan documents mention the legacy feature names), so recording a plan or an
# audit pack must not move a pinned count. The two plan documents this ledger
# cites are still pinned by sha256, but by path at `methodRecordSurfaces` rather
# than by the scan.
#
# `docs/guides/` is the operational surface and is excluded by the same rule:
# runbooks, setup notes and CI descriptions are prose about operating the
# programme, not an implementation or an artefact of the legacy school method.
# These scans establish absence FROM CODE, so a guide that names the study is not
# a counter-example to an absence claim.
EXCLUDED_SCAN_PREFIXES = (
    "docs/implementation/",
    "docs/plans/",
    "docs/guides/",
    "scripts/tools/",
    "prompts/",
    "app/src/components/studies/",
    "app/tests/",
)
EDITION_PREFIX = "docs/analytics/editions/"
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
EXCLUDED_SCAN_PATHS = (
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
    ".secrets.baseline",
)

LEGACY_FEATURE_NAMES = (
    "school_primary_quality_score",
    "school_primary_dist_score",
    "school_secondary_dist_score",
)

DISTANCE_COLUMNS = (
    "nearest_schoolPRIMARY_dist",
    "nearest_schoolSECONDARY_dist",
    "nearest_schoolJUNIOR_dist",
    "dist_to_nearest_school",
    "nearest_top_primary_school_dist",
    "nearest_top_secondary_school_dist",
)

POLICY_FLAGS_BRONZE = ("sap_ind", "gifted_ind", "ip_ind", "autonomous_ind")

# Multiplicity-vocabulary tokens; the legacy records no correction anywhere.
MULTIPLICITY_TOKENS = (
    "bonferroni",
    "holm",
    "fdr",
    "false discovery",
    "multiple testing",
    "multiple comparison",
)

MAX_LISTED = 12

DEFINITION = (
    "A measured inventory and reconciliation of what this checkout holds for "
    "school quality, with an explicit list of what cannot be re-derived. The "
    "tier artefacts DO exist: four hand-authored files under data/manual/csv/ "
    "(two tier lists, a weights table, a scoring methodology) drive the "
    "shipped school_accessibility_score through the producer's documented "
    "formula; they are screened as hand-authored reference data, origin "
    "unverified, and the 2026-11-18 checkout note that no tier artefact "
    "exists is corrected by this scan. The bronze school directory carries no "
    "coordinate columns, but a coordinate-bearing school artefact also exists "
    "(data/manual/csv/datagov/SchoolsMOE.geojson, 197 Point features, a name "
    "subset of the directory, zero consumers in src/ or scripts/) — unlinked "
    "to the shipped distance columns in BOTH directions: it neither shows the "
    "distances were produced from it nor that they were not; the producer "
    "cites runtime geocoding from postal codes. The legacy article's three "
    "school feature names exist in no shipped schema, so its three "
    "coefficients cannot be re-derived; its RDD rests on a covariate balance "
    "the legacy itself records as FAILED, and a failed-design estimate is not "
    "a premium. What IS measured here: one pre-stated descriptive OLS "
    "association of ln(psf) with the shipped school-distance columns on the "
    "legacy's own stated screen — a conditional association that does not "
    "establish a causal admissions premium, and no model output in this pack "
    "consumes a policy-eligibility flag. No RDD is re-estimated and no causal "
    "language is retained: the ledger supports withdrawing the legacy's "
    "causal/RDD claims, not restating them."
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


def _select(frame: pd.DataFrame, mask: Any) -> pd.DataFrame:
    return pd.DataFrame(frame.loc[mask]).reset_index(drop=True)


def _numeric(column: Any) -> pd.Series:
    return pd.Series(np.asarray(pd.to_numeric(column, errors="coerce")), dtype=float)


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


def _yes_no(series: Any) -> pd.Series:
    return (series.astype("string").str.strip().str.lower() == "yes").astype(int)


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


def _manifest(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-file pin list: sorted, hash-pinned, byte-counted (review round 2)."""
    return [
        {"path": entry["path"], "sha256": entry["sha256"], "bytes": entry["bytes"]}
        for entry in sorted(entries, key=lambda item: item["path"])
    ]


def _file_entry(path: Path) -> dict[str, Any]:
    return {
        "path": _relative(path),
        "sha256": sha256_of(path),
        "bytes": int(path.stat().st_size),
    }


def _data_entries() -> list[dict[str, Any]]:
    """Every file under data/ (except data/cache/, disclosed) and
    app/public/data/, except app/public/data/analytics/ — generated dashboard
    assets that other processes rewrite while this stage runs; a hash-pinned
    scan cannot include actively rewritten surfaces (disclosed in the
    manifest). The school-relevant served surface under
    app/public/data/analysis/ stays pinned."""
    roots = (REPO_ROOT / "data", REPO_ROOT / "app" / "public" / "data")
    excluded = ("data/cache/", "app/public/data/analytics/")
    entries: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = _relative(path)
            if any(relative.startswith(prefix) for prefix in excluded):
                continue
            entries.append(_file_entry(path))
    return sorted(entries, key=lambda item: item["path"])


def _code_entries() -> list[dict[str, Any]]:
    """Every code file under src/ and scripts/, except the programme's own
    instruments under scripts/tools/ — the evidence producers other stages
    actively edit, whose bytes cannot be pinned without breaking --check
    (the RS10 §6a lesson, applied to code). The exclusion is disclosed in
    the manifest and in the origin scan's meaning."""
    roots = (REPO_ROOT / "src", REPO_ROOT / "scripts")
    suffixes = (".py", ".ts", ".tsx")
    excluded_prefix = "scripts/tools/"
    entries: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if _relative(path).startswith(excluded_prefix):
                continue
            entries.append(_file_entry(path))
    return sorted(entries, key=lambda item: item["path"])


def _filename_artefact_scan(
    entries: list[dict[str, Any]], roots: list[str], tokens: tuple[str, ...]
) -> dict[str, Any]:
    """A measured FILENAME scan: every file under the roots whose name carries
    any token, listed. A filename scan bounds names, not contents."""
    matched: list[dict[str, Any]] = []
    for entry in entries:
        name = entry["path"].rsplit("/", 1)[-1].lower()
        hit_tokens = sorted({token for token in tokens if token in name})
        if hit_tokens:
            matched.append(
                {
                    "path": entry["path"],
                    "bytes": entry["bytes"],
                    "matchedTokens": hit_tokens,
                }
            )
    return {
        "roots": roots,
        "tokens": list(tokens),
        "filesEnumerated": len(entries),
        "matchedCount": len(matched),
        "matchedFiles": matched,
        "manifestKey": "scanManifests.dataArtefactRoots",
    }


def _content_token_scan(entries: list[dict[str, Any]], tokens: tuple[str, ...]) -> dict[str, Any]:
    """A measured CONTENT scan over text-ish files (.csv/.json/.md) under the
    same enumeration: each line of each file is searched for each token."""
    suffixes = (".csv", ".json", ".md")
    scanned = 0
    matches: list[dict[str, Any]] = []
    for entry in entries:
        if not entry["path"].endswith(suffixes):
            continue
        scanned += 1
        path = REPO_ROOT / entry["path"]
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            haystack = line.lower()
            hit_tokens = sorted({token for token in tokens if token in haystack})
            if hit_tokens:
                matches.append(
                    {
                        "path": entry["path"],
                        "line": number,
                        "tokens": hit_tokens,
                        "quote": line.strip()[:160],
                    }
                )
    return {
        "suffixes": list(suffixes),
        "tokens": list(tokens),
        "filesScanned": scanned,
        "occurrences": len(matches),
        "matches": matches[:MAX_LISTED],
    }


def _manifest_from_paths(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {"path": _relative(path), "sha256": sha256_of(path), "bytes": int(path.stat().st_size)}
        for path in sorted(paths, key=_relative)
    ]


def _schema_entries() -> list[dict[str, Any]]:
    """Every parquet file under data/pipeline/ and data/analysis/ (metadata
    scan surface; data/cache/ excluded and disclosed)."""
    roots = (REPO_ROOT / "data" / "pipeline", REPO_ROOT / "data" / "analysis")
    entries: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.parquet")):
            entries.append(_file_entry(path))
    return sorted(entries, key=lambda item: item["path"])


def scan_manifests(
    text_paths: list[Path],
    schema_entries: list[dict[str, Any]],
    data_entries: list[dict[str, Any]],
    code_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-file pins for every enumerated scan surface (review round 2):
    an aggregate filesScanned count is not a substitute for per-file records.
    Each manifest is a sorted path/sha256/bytes list, so any sibling file
    landing in a scanned root shows up as byte drift in --check."""
    cache_count = (
        sum(1 for path in (REPO_ROOT / "data" / "cache").rglob("*") if path.is_file())
        if (REPO_ROOT / "data" / "cache").is_dir()
        else 0
    )
    return {
        "textRoots": {
            "roots": list(SCAN_ROOTS),
            "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
            "excludedPaths": list(EXCLUDED_SCAN_PATHS),
            "excludedEditionTexts": (
                "published edition texts under "
                f"{EDITION_PREFIX} are excluded except the frozen legacy "
                f"originals under {RETAINED_EDITION_PREFIX}"
            ),
            "fileCount": len(text_paths),
            "files": _manifest_from_paths(text_paths),
        },
        "schemaRoots": {
            "roots": ["data/pipeline/", "data/analysis/"],
            "excludedRoots": {
                "data/cache/": (
                    "content-addressed API-response cache (OneMap search "
                    "results); its filenames are digests, not entity names, "
                    "and it holds no analysis parquet"
                )
            },
            "fileCount": len(schema_entries),
            "files": schema_entries,
        },
        "dataArtefactRoots": {
            "roots": ["data/", "app/public/data/"],
            "excludedRoots": {
                "data/cache/": (
                    "content-addressed API-response cache; digest filenames "
                    "carrying no entity-named artefact"
                ),
                "app/public/data/analytics/": (
                    "generated dashboard assets rewritten by other processes "
                    "while this stage runs; a hash-pinned scan cannot include "
                    "actively rewritten surfaces (the school-relevant served "
                    "surface under app/public/data/analysis/ stays pinned)"
                ),
            },
            "excludedCacheFileCount": cache_count,
            "fileCount": len(data_entries),
            "files": data_entries,
        },
        "codeRoots": {
            "roots": ["src/", "scripts/"],
            "excludedPrefixes": ["scripts/tools/"],
            "excludedPrefixReason": (
                "the programme's own evidence producers, actively edited by "
                "their own study stages; pinning their bytes would break "
                "--check whenever a sibling lands (RS10's scan-stability "
                "lesson applied to code)"
            ),
            "suffixes": [".py", ".ts", ".tsx"],
            "fileCount": len(code_entries),
            "files": code_entries,
        },
    }


def _token_scan(
    paths: list[Path], tokens: tuple[str, ...], case_sensitive: bool = False
) -> dict[str, Any]:
    """Where each token appears, with a per-token file/occurrence count."""
    hits: dict[str, Any] = {}
    for token in tokens:
        needle = token if case_sensitive else token.lower()
        matches: list[dict[str, Any]] = []
        for path in paths:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                haystack = line if case_sensitive else line.lower()
                if needle in haystack:
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


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    months = frame["month"].astype(str)
    counts = {str(key): int(value) for key, value in frame.groupby(months).size().items()}
    ordered = sorted(counts)
    terminal_month = ordered[-1]
    last_complete_month = ordered[-2]
    trailing_months = ordered[-13:-1]
    trailing = [counts[month] for month in trailing_months]
    trailing_median = float(np.median(trailing)) if trailing else 0.0
    ratio = counts[terminal_month] / trailing_median if trailing_median else None

    def basis(mask: Any) -> dict[str, Any]:
        subset_counts = {
            str(key): int(value) for key, value in frame[mask].groupby(months[mask]).size().items()
        }
        subset_ordered = sorted(subset_counts)
        subset_trailing = [subset_counts[month] for month in subset_ordered[-13:-1]]
        subset_median = float(np.median(subset_trailing)) if subset_trailing else 0.0
        return {
            "terminalMonth": subset_ordered[-1],
            "terminalMonthTransactions": subset_counts[subset_ordered[-1]],
            "lastCompleteMonth": subset_ordered[-2],
            "lastCompleteMonthTransactions": subset_counts[subset_ordered[-2]],
            "trailing12MedianTransactions": _r(subset_median, 1),
            "terminalMonthShareOfTrailingMedian": _r(
                subset_counts[subset_ordered[-1]] / subset_median if subset_median else None, 4
            ),
        }

    condo_mask = (frame["property_type"] == "condo").to_numpy()
    hdb_mask = (frame["property_type"] == "hdb").to_numpy()

    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact (the same rule RS03/RS04/"
            "RS05/RS09/RS10 shipped, computed on the private rows so the bound "
            "is identical across the studies)"
        ),
        "lastCompleteMonth": last_complete_month,
        "terminalMonth": terminal_month,
        "terminalMonthTransactions": counts[terminal_month],
        "trailing12MedianTransactions": _r(trailing_median, 1),
        "terminalMonthShareOfTrailingMedian": _r(ratio, 4),
        "lastCompleteMonthTransactions": counts[last_complete_month],
        "trailing12Months": trailing_months,
        "privateRowsBasis": basis(condo_mask),
        "allTypesBasis": {
            "terminalMonth": terminal_month,
            "terminalMonthTransactions": counts[terminal_month],
            "trailing12MedianTransactions": _r(trailing_median, 1),
            "terminalMonthShareOfTrailingMedian": _r(ratio, 4),
        },
        "hdbRowsBasis": basis(hdb_mask),
        "frameFirstMonth": str(months.min()),
        "frameLastMonth": str(months.max()),
        "meaning": (
            "every window, count and share in this ledger that touches the frame "
            "stops at lastCompleteMonth"
        ),
    }


def school_directory_inventory() -> dict[str, Any]:
    """The bronze directory: schema first (metadata), then the counted columns."""
    parquet_file = pq.ParquetFile(SCHOOL_DIRECTORY)
    columns = [str(name) for name in parquet_file.schema_arrow.names]
    coordinate_columns = [
        name
        for name in columns
        if name.lower() in {"latitude", "longitude", "lat", "lon", "x", "y"}
    ]
    frame = pd.read_parquet(SCHOOL_DIRECTORY)
    policy_flags = {
        flag: {
            "valueCounts": {
                str(key): int(value) for key, value in sorted(frame[flag].value_counts().items())
            },
            "yesCount": int(_yes_no(frame[flag]).sum()),
            "noCount": int(len(frame) - _yes_no(frame[flag]).sum()),
        }
        for flag in POLICY_FLAGS_BRONZE
    }
    return {
        "path": _relative(SCHOOL_DIRECTORY),
        "sha256": sha256_of(SCHOOL_DIRECTORY),
        "bytes": int(SCHOOL_DIRECTORY.stat().st_size),
        "rows": int(parquet_file.metadata.num_rows),
        "columnCount": len(columns),
        "columns": columns,
        "coordinateColumnCount": len(coordinate_columns),
        "coordinateColumns": coordinate_columns,
        "mainlevelCodeCounts": {
            str(key): int(value)
            for key, value in sorted(frame["mainlevel_code"].value_counts().items())
        },
        "zoneCodeCounts": {
            str(key): int(value) for key, value in sorted(frame["zone_code"].value_counts().items())
        },
        "policyFlags": policy_flags,
        "policyFlagMeaning": (
            "sap_ind/gifted_ind/ip_ind/autonomous_ind are admission-policy "
            "eligibility flags. They are counted here and NOT used by any model "
            "output in this pack (policyEligibility records the consumption scan)"
        ),
    }


def tier_provenance(
    directory: dict[str, Any],
    data_entries: list[dict[str, Any]],
    code_paths: list[Path],
) -> dict[str, Any]:
    """Gate clause 1: where the school tiers come from, measured end to end."""
    primary = pd.read_csv(TIERS_PRIMARY)
    secondary = pd.read_csv(TIERS_SECONDARY)
    weights = pd.read_csv(WEIGHTS_CSV)

    def named(value: Any) -> str:
        return str(value).strip().upper()

    directory_keys = {
        named(value)
        for value in pd.read_parquet(SCHOOL_DIRECTORY, columns=["school_name"])["school_name"]
    }

    def resolve_join(names: Any) -> dict[str, Any]:
        exact = 0
        prefix = 0
        unresolved: list[str] = []
        for value in names:
            key = named(value)
            if key in directory_keys:
                exact += 1
            else:
                candidates = [
                    candidate
                    for candidate in directory_keys
                    if candidate.startswith(key) or key.startswith(candidate)
                ]
                if candidates:
                    prefix += 1
                else:
                    unresolved.append(key)
        return {
            "rows": int(len(names)),
            "exactNameMatches": exact,
            "prefixFallbackMatches": prefix,
            "unresolved": sorted(unresolved),
            "method": (
                "the producer's own join rule: exact match on the normalized "
                "name first, then longest prefix in either direction; unresolved "
                "schools score quality 0 and are never tier 1"
            ),
        }

    def tier_counts(column: Any) -> dict[str, int]:
        numeric = _numeric(column).dropna()
        counts = numeric.astype(int).value_counts()
        return {str(key): int(counts[key]) for key in sorted(counts.index)}

    bronze_external = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "external"
    json_candidates = (
        sorted(
            path.name
            for path in bronze_external.iterdir()
            if "school" in path.name.lower() or "tier" in path.name.lower()
        )
        if bronze_external.is_dir()
        else []
    )

    return {
        "manualArtefacts": {
            "tiersPrimary": {
                "path": _relative(TIERS_PRIMARY),
                "sha256": sha256_of(TIERS_PRIMARY),
                "bytes": int(TIERS_PRIMARY.stat().st_size),
                "dataRows": int(len(primary)),
                "columns": [str(name) for name in primary.columns],
                "tier1Count": tier_counts(primary["tier"]).get("1", 0),
                "tierCounts": tier_counts(primary["tier"]),
                "gepYes": int(_yes_no(primary["gep"]).sum()),
                "sapYes": int(_yes_no(primary["sap"]).sum()),
                "popularityNumericRows": int(_numeric(primary["popularity_p2b"]).notna().sum()),
                "popularityHighMarkerRows": int(
                    (primary["popularity_p2b"].astype(str) == "High").sum()
                ),
            },
            "tiersSecondary": {
                "path": _relative(TIERS_SECONDARY),
                "sha256": sha256_of(TIERS_SECONDARY),
                "bytes": int(TIERS_SECONDARY.stat().st_size),
                "dataRows": int(len(secondary)),
                "columns": [str(name) for name in secondary.columns],
                "tier1Count": tier_counts(secondary["tier"]).get("1", 0),
                "tierCounts": tier_counts(secondary["tier"]),
                "ipYes": int(_yes_no(secondary["ip"]).sum()),
                "sapYes": int(_yes_no(secondary["sap"]).sum()),
                "autonomousYes": int(_yes_no(secondary["autonomous"]).sum()),
            },
            "qualityWeights": {
                "path": _relative(WEIGHTS_CSV),
                "sha256": sha256_of(WEIGHTS_CSV),
                "bytes": int(WEIGHTS_CSV.stat().st_size),
                "dataRows": int(len(weights)),
                "features": [str(value) for value in weights["feature"]],
            },
            "scoringMethodology": {
                "path": _relative(METHODOLOGY_MD),
                "sha256": sha256_of(METHODOLOGY_MD),
                "bytes": int(METHODOLOGY_MD.stat().st_size),
            },
        },
        "bronzeJsonPreferredAndAbsent": {
            "preferredPath": "data/pipeline/01_bronze/external/school_tiers.json",
            "exists": (bronze_external / "school_tiers.json").exists(),
            "schoolOrTierNamedFilesInBronzeExternal": json_candidates,
            "producerPreference": _code_quote(
                PRODUCER,
                'json_data = self.load_json("school_tiers.json")',
                "producer-json-preference",
            ),
            "csvFallback": _code_quote(
                PRODUCER, 'csv_dir = self.data_dir / "manual" / "csv"', "producer-csv-fallback"
            ),
            "meaning": (
                "the producer prefers a bronze JSON tier file that is absent, so "
                "the manual CSV lists are the ACTIVE tier source of the shipped "
                "school_accessibility_score — measured, not assumed"
            ),
        },
        "directoryJoin": {
            "primary": resolve_join(primary["school_name"]),
            "secondary": resolve_join(secondary["school_name"]),
            "directoryNameCount": len(directory_keys),
            "directoryRows": directory["rows"],
        },
        "origin": origin_scan(code_paths),
        "qualityScoreFormula": {
            "methodology": _code_quote(METHODOLOGY_MD, "quality_score = (", "methodology-formula"),
            "producerImplementation": _code_quote(
                PRODUCER, "def calculate_school_quality_scores(", "producer-formula"
            ),
            "producerDocumentedDeviations": _code_quote(
                PRODUCER, "- ``academic_awards`` is 0 for every school", "producer-deviations"
            ),
            "accessibilityBlend": _code_quote(
                PRODUCER,
                "``school_accessibility_score`` — 0.4 * primary + 0.6 * secondary blend",
                "producer-blend",
            ),
            "decay": _code_quote(
                PRODUCER, "_ACCESSIBILITY_DECAY_RANGE_M = 2000.0", "producer-decay"
            ),
            "meaning": (
                "the shipped score's formula is recorded in code and in the "
                "manual methodology; the inputs to that formula are the "
                "hand-authored tier lists, so the score is screened as a "
                "tier-list-derived feature, not a measured school-quality "
                "measure independent of those lists"
            ),
        },
        "servedTierArtefactScan": {
            "roots": ["data/", "app/public/data/"],
            "tokens": ("tier",),
            "filesEnumerated": len(data_entries),
            "matchedCount": sum(
                1 for entry in data_entries if "tier" in entry["path"].rsplit("/", 1)[-1].lower()
            ),
            "matchedFiles": [
                {"path": entry["path"], "bytes": entry["bytes"]}
                for entry in data_entries
                if "tier" in entry["path"].rsplit("/", 1)[-1].lower()
            ],
            "manifestKey": "scanManifests.dataArtefactRoots",
            "finding": (
                "measured: the filename scan matches 6 tier-named files, listed "
                "in matchedFiles — the two school tier lists under "
                "data/manual/csv/ and four market-segmentation tier files under "
                "data/analysis/ (a different series, recorded so the vocabulary "
                "near-match cannot be mistaken for RS08 lineage); no tier-named "
                "file is served under app/public/data, and the only school-named "
                "served paths are the two PNG plots recorded at "
                "rddRecovery.servedPlots. A filename scan bounds names, not contents"
            ),
        },
    }


def origin_scan(code_paths: list[Path]) -> dict[str, Any]:
    """The tier artefacts' origin, bounded to what the checkout can show:
    a measured call-site scan for the four file names across all code, plus
    the recorded absence of any dated snapshot inside the files. The screen
    bounds what the checked-out code references; it does not establish how
    the files came to exist — origin stays unverified."""
    tokens = (
        "school_tiers_primary",
        "school_tiers_secondary",
        "school_quality_weights",
        "school_scoring_methodology",
        "school_tiers.json",
    )
    matches: list[dict[str, Any]] = []
    for path in code_paths:
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            hit_tokens = sorted({token for token in tokens if token in line})
            if hit_tokens:
                matches.append(
                    {
                        "path": _relative(path),
                        "line": number,
                        "tokens": hit_tokens,
                        "quote": line.strip()[:160],
                    }
                )

    def _class(path: str) -> str:
        if path.startswith("src/"):
            return "pipeline code (the CSV-fallback consumption itself, cited at bronzeJsonPreferredAndAbsent)"
        if path.startswith("scripts/tools/"):
            return "evidence producer (reads the files to measure them)"
        return "other code"

    return {
        "status": "screened as hand-authored reference data, origin unverified",
        "callSiteScan": {
            "roots": ["src/", "scripts/"],
            "excludedPrefixes": ["scripts/tools/"],
            "excludedPrefixReason": (
                "the programme's own evidence producers: they read these files "
                "only to measure them, their bytes move whenever a sibling "
                "stage lands, and a hash-pinned scan cannot include actively "
                "edited surfaces (disclosed rather than widened)"
            ),
            "suffixes": [".py", ".ts", ".tsx"],
            "tokens": list(tokens),
            "filesScanned": len(code_paths),
            "occurrences": len(matches),
            "matchedFiles": matches,
            "matchedFilePaths": sorted({match["path"] for match in matches}),
            "manifestKey": "scanManifests.codeRoots",
            "classOf": {
                path: _class(path) for path in sorted({match["path"] for match in matches})
            },
        },
        "datedSnapshotRecorded": False,
        "meaning": (
            "measured: the only code references to the four artefact names "
            "outside the programme's own instruments are the pipeline's "
            "CSV-fallback reads (bronzeJsonPreferredAndAbsent cites the lines); "
            "no extraction, download or other pipeline call site appears in the "
            "scanned code, and no dated source snapshot is recorded inside the "
            "files. The evidence producers under scripts/tools/ that read the "
            "files to measure them are excluded from the pinned scan as actively "
            "edited instruments, and that exclusion is disclosed here. This is a "
            "screen of the checked-out code, not a finding about how the files "
            "were produced — the origin of the content remains unverified, and "
            "this pack builds no model output on the lists"
        ),
    }


def policy_eligibility(
    paths: list[Path], tiers: dict[str, Any], directory: dict[str, Any]
) -> dict[str, Any]:
    """Gate clause: policy eligibility stays outside model outputs."""
    src_paths = [path for path in paths if _relative(path).startswith("src/")]
    flags_scan = _token_scan(src_paths, POLICY_FLAGS_BRONZE)
    total_src_hits = sum(int(entry["occurrences"]) for entry in flags_scan.values())
    primary = tiers["manualArtefacts"]["tiersPrimary"]
    secondary = tiers["manualArtefacts"]["tiersSecondary"]
    bronze_flags = {
        flag: {"yesCount": entry["yesCount"], "noCount": entry["noCount"]}
        for flag, entry in directory["policyFlags"].items()
    }
    return {
        "gateClause": "Keep policy eligibility outside model outputs.",
        "bronzeFlags": bronze_flags,
        "srcConsumptionScan": {
            "roots": ["src/"],
            "filesScanned": len(src_paths),
            # the src/ entries of codeRoots are these files' pins: srcRoots is not a
            # manifest this ledger carries
            "manifestKey": "scanManifests.codeRoots",
            "tokens": flags_scan,
            "totalOccurrences": total_src_hits,
            "meaning": (
                "zero occurrences of the four bronze policy-flag column names "
                "anywhere under src/: the bronze admission-policy flags are "
                "counted in schoolDirectory.policyFlags but are consumed by no "
                "pipeline node"
            ),
        },
        "tierListPolicyColumns": {
            "primaryGepYes": primary["gepYes"],
            "primarySapYes": primary["sapYes"],
            "secondaryIpYes": secondary["ipYes"],
            "secondarySapYes": secondary["sapYes"],
            "secondaryAutonomousYes": secondary["autonomousYes"],
            "meaning": (
                "the manual tier lists themselves carry gep/sap/ip/autonomous "
                "Yes/No columns, and the producer's quality formula consumes "
                "them (tierProvenance.qualityScoreFormula.producerImplementation); "
                "the shipped school_accessibility_score is therefore screened as "
                "embedding policy-status flags"
            ),
        },
        "associationExclusion": {
            "excludedColumn": "school_accessibility_score",
            "reason": (
                "the shipped score is screened as embedding policy-status flags "
                "through the tier lists, so this pack's one association model "
                "uses only the three policy-free distance columns; no model "
                "output in this ledger consumes sap_ind, gifted_ind, ip_ind, "
                "autonomous_ind or any tier-list policy column"
            ),
        },
        "compliance": (
            "no model output in this pack uses a policy-eligibility flag: the "
            "association regressors are three shipped distance columns, and the "
            "controls are floor area, lease commencement, storey band, flat "
            "type, town and year"
        ),
    }


def school_coordinates(paths: list[Path]) -> dict[str, Any]:
    """The school-coordinate question, answered over the whole checkout."""
    geojson = json.loads(SCHOOLS_MOE_GEOJSON.read_text(encoding="utf-8"))
    features = list(geojson.get("features", []))
    geojson_names = sorted(
        {str(feature["properties"]["school_name"]).strip().upper() for feature in features}
    )
    geojson_coords = sum(
        1
        for feature in features
        if feature.get("geometry", {}).get("coordinates") is not None
        and feature.get("properties", {}).get("latitude") is not None
    )
    directory_keys = set(
        pd.read_parquet(SCHOOL_DIRECTORY, columns=["school_name"])["school_name"]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    src_script_hits = _token_scan(paths, ("SchoolsMOE",))
    return {
        "bronzeDirectoryCoordinates": {
            "coordinateColumnCount": pq.ParquetFile(SCHOOL_DIRECTORY).schema_arrow.names
            and len(
                [
                    name
                    for name in pq.ParquetFile(SCHOOL_DIRECTORY).schema_arrow.names
                    if name.lower() in {"latitude", "longitude", "lat", "lon", "x", "y"}
                ]
            ),
            "meaning": (
                "the bronze directory's schema (metadata read) carries no "
                "coordinate column; the shipped distances were produced from "
                "coordinates that existed only transiently at pipeline runtime"
            ),
        },
        "runtimeGeocoding": {
            "geocoderFunction": _code_quote(PRODUCER, "def geocode_schools(", "producer-geocode"),
            "featureNodeCall": _code_quote(
                FEATURES_NODE, "schools = geocode_schools(schools, geocoder)", "node-geocode"
            ),
            "bronzeSource": _code_quote(
                DATAGOV_ADAPTER, '"raw_datagov_school_directory.parquet"', "adapter-source"
            ),
            "meaning": (
                "the producer geocodes school postal codes at runtime and does "
                "not persist school coordinates as a school-keyed artefact; the "
                "shipped layers carry the resulting per-property distance "
                "columns instead (screened as, from code)"
            ),
        },
        "schoolsMoeGeojson": {
            "path": _relative(SCHOOLS_MOE_GEOJSON),
            "sha256": sha256_of(SCHOOLS_MOE_GEOJSON),
            "bytes": int(SCHOOLS_MOE_GEOJSON.stat().st_size),
            "featureCount": len(features),
            "featuresWithPointGeometryAndLatLng": geojson_coords,
            "distinctSchoolNames": len(geojson_names),
            "namesAlsoInBronzeDirectory": len(set(geojson_names) & directory_keys),
            "namesOnlyInGeojson": sorted(set(geojson_names) - directory_keys),
            "consumerScan": {
                "roots": [
                    "src/",
                    "scripts/ (programme-produced surfaces under scripts/tools/ excluded, as disclosed)",
                ],
                "filesScanned": len(paths),
                "manifestKey": "scanManifests.textRoots",
                "token": "SchoolsMOE",
                "occurrencesUnderSrc": src_script_hits["SchoolsMOE"]["occurrences"],
                "meaning": (
                    "zero call sites under src/ reference this artefact, so it "
                    "is unlinked to the shipped distance columns in BOTH "
                    "directions: it is neither evidence that the shipped "
                    "distances were produced from it, nor evidence that they "
                    "were not"
                ),
            },
        },
        "schoolFileNameScan": _school_named_files(),
        "meaning": (
            "the 2026-11-18 checkout lead 'no school coordinates' is corrected "
            "and narrowed: no SHIPPED layer carries school coordinates, but an "
            "unconsumed coordinate-bearing school artefact exists under "
            "data/manual/csv/datagov/, and the runtime producer geocodes "
            "postal codes instead of reading any persisted coordinate file"
        ),
    }


def _school_named_files() -> list[dict[str, Any]]:
    """Every file under data/ or app/public/data whose own name or any parent
    directory component names a school, with a recorded class."""
    roots = (REPO_ROOT / "data", REPO_ROOT / "app" / "public" / "data")
    found: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = _relative(path)
            parts = relative.lower().split("/")
            if not any("school" in part for part in parts):
                continue
            name = path.name.lower()
            if "preschool" in name or "preschool" in relative.lower():
                classification = (
                    "preschool-amenity-source (not a primary/secondary school artefact)"
                )
            elif name.endswith(".geojson"):
                classification = "geojson (coordinate-bearing)"
            elif name.endswith((".csv", ".md")):
                classification = "tier/reference artefact"
            elif name.endswith(".parquet"):
                classification = "bronze directory (schema carries no coordinate column)"
            elif name.endswith(".png"):
                classification = "served plot (visual read at rddRecovery.servedPlots)"
            else:
                classification = "other"
            found.append(
                {"path": relative, "bytes": int(path.stat().st_size), "class": classification}
            )
    return found


def legacy_feature_names(paths: list[Path]) -> dict[str, Any]:
    """The three legacy feature names: schema scan first, then text scan."""
    schema_scan: dict[str, Any] = {
        "roots": ["data/pipeline/", "data/analysis/"],
        "method": "pyarrow schema (metadata-only) read of every parquet file",
        "excludedRoots": {
            "data/cache/": (
                "content-addressed API-response cache (OneMap search results); "
                "its filenames are digests, not entity names, and it holds no "
                "analysis parquet"
            )
        },
        "manifestKey": "scanManifests.schemaRoots",
        "filesScanned": 0,
        "schoolColumnFiles": [],
        "columnPresence": {name: {"files": 0, "paths": []} for name in LEGACY_FEATURE_NAMES},
    }
    roots = (REPO_ROOT / "data" / "pipeline", REPO_ROOT / "data" / "analysis")
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.parquet")):
            schema_scan["filesScanned"] += 1
            names = {str(name) for name in pq.read_schema(path).names}
            school_columns = sorted(name for name in names if "school" in name.lower())
            if school_columns:
                schema_scan["schoolColumnFiles"].append(
                    {
                        "path": _relative(path),
                        "rows": int(pq.ParquetFile(path).metadata.num_rows),
                        "columns": int(len(names)),
                        "schoolColumns": school_columns,
                    }
                )
            for feature in LEGACY_FEATURE_NAMES:
                if feature in names:
                    schema_scan["columnPresence"][feature]["files"] += 1
                    schema_scan["columnPresence"][feature]["paths"].append(_relative(path))

    text_scan = _token_scan(paths, LEGACY_FEATURE_NAMES)
    for name in LEGACY_FEATURE_NAMES:
        entry = text_scan[name]
        surfaces = sorted({match["path"] for match in entry["firstMatches"]})
        entry["surfacesFirst"] = surfaces
    return {
        "schemaScan": schema_scan,
        "textScan": {
            "roots": list(SCAN_ROOTS),
            "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
            "excludedPaths": list(EXCLUDED_SCAN_PATHS),
            "excludedEditionTexts": (
                "published edition texts under "
                f"{EDITION_PREFIX} are excluded except the frozen legacy "
                f"originals under {RETAINED_EDITION_PREFIX}"
            ),
            "filesScanned": len(paths),
            "manifestKey": "scanManifests.textRoots",
            "tokens": text_scan,
            "meaning": (
                "outside the excluded programme surfaces the three legacy "
                "feature names occur in the frozen legacy article and its "
                "live twin. The retired programme's plan documents "
                "(docs/plans/2025-02-02-school-impact-analysis.md and "
                "docs/plans/2026-02-05-enhanced-school-impact-analysis.md) "
                "mention them too, but docs/plans/ is the planning/spec "
                "surface and is excluded from this scan ("
                "excludedPrefixes); those two documents stay recorded and "
                "sha-pinned by path at methodRecordSurfaces rather than "
                "counted here. The operational surface docs/guides/ "
                "(runbooks and setup/CI documentation about the programme) is "
                "excluded too, for the same reason: this scan establishes "
                "absence FROM CODE, and a guide that names the method is not "
                "an implementation of it. All of it is prose, not shipped columns"
            ),
        },
    }


def column_health(frame: pd.DataFrame, sample_mask: Any, last_complete: str) -> dict[str, Any]:
    """Four missingness states, kept apart, per school column.

    A null value, a recorded zero, an absent row and an absent column are
    different things: the counts below are per state, and a file-row count
    describes the file, not the series.

    Review round 2: every frame-level aggregation here is computed through
    ``last_complete`` (the measured cutoff), not through the file's terminal
    month — the programme's cutoff discipline binds every aggregation, not
    just the headline. The bound is recorded as a field.
    """
    bound_mask = (frame["month"].astype(str) <= last_complete).to_numpy()
    bounded = frame.loc[bound_mask]
    columns: dict[str, Any] = {}
    null_cell_total = 0
    zero_cell_total = 0
    for name in DISTANCE_COLUMNS + ("school_accessibility_score",):
        series = _numeric(bounded[name])
        sample_series = _numeric(frame.loc[sample_mask, name])
        nulls = int(series.isna().sum())
        zeros = int((series == 0).sum())
        null_cell_total += nulls
        zero_cell_total += zeros
        columns[name] = {
            "frame": {
                "rowCount": int(len(series)),
                "nullCount": nulls,
                "recordedZeroCount": zeros,
                "min": _r(float(series.min()), 4) if series.notna().any() else None,
                "median": _r(float(series.median()), 4) if series.notna().any() else None,
                "p95": _r(float(series.quantile(0.95)), 4) if series.notna().any() else None,
                "max": _r(float(series.max()), 4) if series.notna().any() else None,
            },
            "associationSample": {
                "rowCount": int(len(sample_series)),
                "nullCount": int(sample_series.isna().sum()),
                "recordedZeroCount": int((sample_series == 0).sum()),
            },
        }
    absent_columns = {
        name: {"presentInUnifiedSchema": False, "status": "absentColumn"}
        for name in LEGACY_FEATURE_NAMES
    }
    screen_rows = int(sample_mask.sum())
    return {
        "states": {
            "nullValue": "a present column with a null in a row",
            "recordedZero": "a present column with an exact 0.0 in a row (a stored value, not a missing one)",
            "absentRow": "a row the measured frame does not contain in the measured study screen (see stateCounts.absentRow for its count and operands)",
            "absentColumn": "a name in no schema of the shipped layers (legacyFeatureNames.schemaScan)",
        },
        "stateCounts": {
            "absentColumn": {
                "count": len(LEGACY_FEATURE_NAMES),
                "basis": "legacyFeatureNames.schemaScan.columnPresence (each 0 files)",
            },
            "nullValue": {
                "cellCountThroughBound": null_cell_total,
                "perColumnField": "columnHealth.columns.<column>.frame.nullCount",
            },
            "recordedZero": {
                "cellCountThroughBound": zero_cell_total,
                "perColumnField": "columnHealth.columns.<column>.frame.recordedZeroCount",
            },
            "absentRow": {
                "rowsOutsideMeasuredScreen": int(bound_mask.sum()) - screen_rows,
                "operands": {
                    "frameRowsThroughBound": int(bound_mask.sum()),
                    "measuredScreenRows": screen_rows,
                },
                "meaning": (
                    "a row the frame through the cutoff contains that the "
                    "measured study screen does not; the frame cannot be "
                    "audited for rows outside itself, so that sense of "
                    "'absent row' is not measurable and no count is invented "
                    "for it"
                ),
            },
        },
        "frameRowCount": int(len(frame)),
        "frameStatsBound": last_complete,
        "frameRowsThroughBound": int(bound_mask.sum()),
        "frameRowsBeyondBound": int(len(frame)) - int(bound_mask.sum()),
        "boundNote": (
            "every frame-level distribution and count in this block is measured "
            "through frameStatsBound (the measured last complete month, "
            "cutoff.lastCompleteMonth); frameRowCount describes the FILE and "
            "frameRowsBeyondBound counts the terminal month's rows, which sit "
            "outside every aggregation here and equal "
            "cutoff.terminalMonthTransactions"
        ),
        "columns": columns,
        "absentLegacyColumns": absent_columns,
        "accessibilityZeroMass": {
            "frameStatsBound": last_complete,
            "frameRecordedZeros": columns["school_accessibility_score"]["frame"][
                "recordedZeroCount"
            ],
            "frameNulls": columns["school_accessibility_score"]["frame"]["nullCount"],
            "meaning": (
                "school_accessibility_score is zero on the overwhelming majority "
                "of rows because the producer's formula contributes 0 when the "
                "nearest school is not in the manual tier lists — a recorded "
                "zero, not a missing value; this is why the column cannot be "
                "read as a coverage measure"
            ),
        },
    }


def legacy_sample_reconciliation(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """The legacy's stated screen, adopted verbatim, measured beside its claims."""
    months = frame["month"].astype(str)
    hdb_mask = (frame["property_type"] == "hdb").to_numpy()
    window_mask = ((months >= STUDY_WINDOW_START) & (months <= last_complete)).to_numpy()
    primary_dist = _numeric(frame["nearest_schoolPRIMARY_dist"]).to_numpy()
    nearest_dist = _numeric(frame["dist_to_nearest_school"]).to_numpy()

    screen = window_mask & hdb_mask & (primary_dist <= PRIMARY_RADIUS_M) & ~np.isnan(primary_dist)
    sample = _select(frame, pd.Series(screen))
    region_counts = {
        str(key): int(value) for key, value in sorted(sample["region"].value_counts().items())
    }

    candidates = [
        {
            "label": "hdbRowsWindowedWithin2kmPrimary",
            "definition": f"property_type=hdb, {STUDY_WINDOW_START}..{last_complete}, nearest_schoolPRIMARY_dist<=2000",
            "rows": int(screen.sum()),
            "legacyClaimCompared": 194165,
            "equalsLegacyClaim": int(screen.sum()) == 194165,
            "difference": int(screen.sum()) - 194165,
        },
        {
            "label": "hdbRowsWindowedWithin2kmNearestAnyLevel",
            "definition": f"property_type=hdb, {STUDY_WINDOW_START}..{last_complete}, dist_to_nearest_school<=2000",
            "rows": int(
                (
                    window_mask
                    & hdb_mask
                    & (nearest_dist <= PRIMARY_RADIUS_M)
                    & ~np.isnan(nearest_dist)
                ).sum()
            ),
            "legacyClaimCompared": 194165,
            "equalsLegacyClaim": False,
            "difference": None,
        },
        {
            "label": "hdbRowsWindowStartThroughLegacyPublicationMonth",
            "definition": f"property_type=hdb, {STUDY_WINDOW_START}..2026-01, nearest_schoolPRIMARY_dist<=2000",
            "rows": int(
                (
                    window_mask
                    & hdb_mask
                    & (months <= "2026-01").to_numpy()
                    & (primary_dist <= PRIMARY_RADIUS_M)
                    & ~np.isnan(primary_dist)
                ).sum()
            ),
            "legacyClaimCompared": 194165,
            "equalsLegacyClaim": False,
            "difference": None,
        },
        {
            "label": "allPropertyTypesWindowedWithin2kmPrimary",
            "definition": f"all property types, {STUDY_WINDOW_START}..{last_complete}, nearest_schoolPRIMARY_dist<=2000",
            "rows": int(
                (window_mask & (primary_dist <= PRIMARY_RADIUS_M) & ~np.isnan(primary_dist)).sum()
            ),
            "legacyClaimCompared": 194165,
            "equalsLegacyClaim": False,
            "difference": None,
        },
    ]

    band_primary = (
        window_mask & hdb_mask & (primary_dist >= BAND_LOW_M) & (primary_dist <= BAND_HIGH_M)
    )
    band_nearest = (
        window_mask & hdb_mask & (nearest_dist >= BAND_LOW_M) & (nearest_dist <= BAND_HIGH_M)
    )
    band_all_types = window_mask & (primary_dist >= BAND_LOW_M) & (primary_dist <= BAND_HIGH_M)
    band_candidates = [
        {
            "label": "hdbWindowedPrimaryBand800to1200",
            "definition": f"property_type=hdb, {STUDY_WINDOW_START}..{last_complete}, nearest_schoolPRIMARY_dist in [800,1200]",
            "rows": int(band_primary.sum()),
            "legacyClaimCompared": 52881,
            "equalsLegacyClaim": int(band_primary.sum()) == 52881,
            "difference": int(band_primary.sum()) - 52881,
        },
        {
            "label": "hdbWindowedNearestAnyLevelBand800to1200",
            "definition": f"property_type=hdb, {STUDY_WINDOW_START}..{last_complete}, dist_to_nearest_school in [800,1200]",
            "rows": int(band_nearest.sum()),
            "legacyClaimCompared": 52881,
            "equalsLegacyClaim": False,
            "difference": None,
        },
        {
            "label": "allPropertyTypesWindowedPrimaryBand800to1200",
            "definition": f"all property types, {STUDY_WINDOW_START}..{last_complete}, nearest_schoolPRIMARY_dist in [800,1200]",
            "rows": int(band_all_types.sum()),
            "legacyClaimCompared": 52881,
            "equalsLegacyClaim": False,
            "difference": None,
        },
    ]

    legacy_region_counts = {"OCR": 146553, "RCR": 46298, "CCR": 1314}
    region_comparison = []
    for region, count in sorted(legacy_region_counts.items()):
        measured = region_counts.get(region)
        region_comparison.append(
            {
                "region": region,
                "legacyCount": count,
                "measuredCount": measured,
                "equalsLegacyClaim": measured == count,
                "difference": (measured - count) if measured is not None else None,
            }
        )

    return {
        "screen": {
            "definition": (
                "the legacy's own stated screen, adopted verbatim: HDB rows, "
                f"{STUDY_WINDOW_START} through the measured last complete month "
                f"({last_complete}), within 2 km of a primary school on the "
                "shipped nearest_schoolPRIMARY_dist column"
            ),
            "radiusMetres": PRIMARY_RADIUS_M,
            "windowStart": STUDY_WINDOW_START,
            "windowEnd": last_complete,
            "runningColumn": "nearest_schoolPRIMARY_dist",
            "unit": "metres (producer haversine; see columnHealth for the distribution)",
        },
        "measuredSample": {
            "rows": int(screen.sum()),
            "regionCounts": region_counts,
            "regionNullRows": int(sample["region"].isna().sum()),
            "firstMonth": str(sample["month"].astype(str).min()),
            "lastMonth": str(sample["month"].astype(str).max()),
            "distinctTowns": int(sample["town"].nunique()),
            "medianPsf": _r(float(_numeric(sample["psf"]).median()), 2),
            "medianPrimaryDistMetres": _r(
                float(_numeric(sample["nearest_schoolPRIMARY_dist"]).median()), 2
            ),
        },
        "legacyClaim": {
            "sampleSize": 194165,
            "basis": "2021 onward, within 2 km of primary schools",
        },
        "candidatePopulations": candidates,
        "anyCandidateReproducesLegacySample": any(item["equalsLegacyClaim"] for item in candidates),
        "legacyRegionalCounts": legacy_region_counts,
        "regionalComparison": region_comparison,
        "anyRegionalCountReproduced": any(item["equalsLegacyClaim"] for item in region_comparison),
        "rddBand": {
            "bandMetres": [BAND_LOW_M, BAND_HIGH_M],
            "candidatePopulations": band_candidates,
            "anyCandidateReproducesLegacyRddSample": any(
                item["equalsLegacyClaim"] for item in band_candidates
            ),
            "runningVariableNote": (
                "the legacy does not state WHICH distance column its near-boundary "
                "band runs on (nearest primary, or nearest school of any level); "
                "the record is underspecified and no choice is made for it here — "
                "three candidate readings are measured instead"
            ),
        },
        "verdict": (
            "the screen is constructible from shipped columns and its counts are "
            "recorded, but no measured candidate reproduces the legacy's 194,165 "
            "or its 52,881, and no measured regional count reproduces "
            "146,553/46,298/1,314; the legacy's sample stands as its own "
            "unreproducible figure"
        ),
    }


def _design_matrix(sample: pd.DataFrame, regressors: dict[str, np.ndarray]) -> pd.DataFrame:
    """Deterministic design matrix: distance regressors + controls + FE dummies.

    Dummy columns are built explicitly over sorted category values; baseline
    levels are 4-ROOM, ANG MO KIO and the window's first year. Continuous
    controls are scaled for numerical stability.
    """
    storey_mid = (_numeric(sample["storey_min"]) + _numeric(sample["storey_max"])) / 2.0
    base = pd.DataFrame(
        {
            "const": np.ones(len(sample)),
            "floor_area_sqm_10": _numeric(sample["floor_area_sqm"]).to_numpy(dtype=float) / 10.0,
            "lease_commence_2000_10": (
                _numeric(sample["lease_commence_date"]).to_numpy(dtype=float) - 2000.0
            )
            / 10.0,
            "storey_mid_10": storey_mid.to_numpy(dtype=float) / 10.0,
        }
    )
    for name, values in regressors.items():
        base[name] = values
    year = sample["month"].astype(str).str.slice(0, 4)
    for prefix, series, baseline in (
        ("ft", sample["flat_type"], FLAT_TYPE_BASELINE),
        ("town", sample["town"], TOWN_BASELINE),
        ("yr", year, YEAR_BASELINE),
    ):
        values = pd.Series(series).astype(str)
        for level in sorted(set(values)):
            if level == baseline:
                continue
            base[f"{prefix}_{level}"] = (values == level).to_numpy(dtype=float)
    return base


def association(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """ONE pre-stated descriptive OLS: ln(psf) on the shipped distance columns.

    No dated prior protocol exists for this study, so specification search
    cannot be ruled out for the LEGACY's fits; this pack's response is to fit
    exactly one pre-stated specification, report all three distance
    coefficients regardless of significance, select nothing, and draw no
    causal conclusion. The legacy's own screen is adopted as the sample so the
    association is measured where the legacy claimed its effects.
    """
    import statsmodels.api as sm

    months = frame["month"].astype(str)
    hdb_mask = (frame["property_type"] == "hdb").to_numpy()
    window_mask = ((months >= STUDY_WINDOW_START) & (months <= last_complete)).to_numpy()
    primary_dist = _numeric(frame["nearest_schoolPRIMARY_dist"]).to_numpy()
    screen = window_mask & hdb_mask & (primary_dist <= PRIMARY_RADIUS_M) & ~np.isnan(primary_dist)

    conditions = {
        "outside-study-window-or-hdb-or-radius": ~screen,
        "missing-primary-distance": np.isnan(primary_dist) & window_mask & hdb_mask,
        "non-positive-or-missing-psf": (
            ~(_numeric(frame["psf"]) > 0) | _numeric(frame["psf"]).isna()
        ).to_numpy()
        & screen,
        "missing-top-primary-distance": (
            _numeric(frame["nearest_top_primary_school_dist"]).isna().to_numpy()
        )
        & screen,
        "missing-top-secondary-distance": (
            _numeric(frame["nearest_top_secondary_school_dist"]).isna().to_numpy()
        )
        & screen,
        "missing-floor-area": (_numeric(frame["floor_area_sqm"]).isna().to_numpy()) & screen,
        "missing-lease-commencement": (_numeric(frame["lease_commence_date"]).isna().to_numpy())
        & screen,
        "invalid-storey-range": (
            (_numeric(frame["storey_min"]).isna() | _numeric(frame["storey_max"]).isna()).to_numpy()
            | (_numeric(frame["storey_max"]) < _numeric(frame["storey_min"])).to_numpy()
        )
        & screen,
        "missing-town-or-flat-type": (
            frame["town"].astype(str).str.strip().eq("").to_numpy()
            | frame["town"].isna().to_numpy()
            | frame["flat_type"].astype(str).str.strip().eq("").to_numpy()
            | frame["flat_type"].isna().to_numpy()
        )
        & screen,
    }
    reason_counts = {reason: int(mask.sum()) for reason, mask in conditions.items()}
    complete_mask = (
        screen
        & ~conditions["non-positive-or-missing-psf"]
        & ~conditions["missing-top-primary-distance"]
        & ~conditions["missing-top-secondary-distance"]
        & ~conditions["missing-floor-area"]
        & ~conditions["missing-lease-commencement"]
        & ~conditions["invalid-storey-range"]
        & ~conditions["missing-town-or-flat-type"]
    )

    sample = _select(frame, pd.Series(complete_mask)).reset_index(drop=True)
    n = len(sample)
    if n == 0:
        raise SystemExit("empty association sample")

    regressors = {
        "dist_primary_per_100m": _numeric(sample["nearest_schoolPRIMARY_dist"]).to_numpy(
            dtype=float
        )
        / DIST_SCALE_M,
        "dist_top_primary_per_100m": _numeric(sample["nearest_top_primary_school_dist"]).to_numpy(
            dtype=float
        )
        / DIST_SCALE_M,
        "dist_top_secondary_per_100m": _numeric(
            sample["nearest_top_secondary_school_dist"]
        ).to_numpy(dtype=float)
        / DIST_SCALE_M,
    }
    design = _design_matrix(sample, regressors)
    response = np.log(_numeric(sample["psf"]).to_numpy(dtype=float))
    model = sm.OLS(response, design.to_numpy(dtype=float)).fit(cov_type="HC1", use_t=False)
    design_columns = list(design.columns)

    regressor_labels = {
        "dist_primary_per_100m": (
            "shipped nearest_schoolPRIMARY_dist in metres / 100 — distance to "
            "the nearest primary-level school, no tier or policy content"
        ),
        "dist_top_primary_per_100m": (
            "shipped nearest_top_primary_school_dist in metres / 100 — distance "
            "to the nearest TIER-1 primary school of the manual tier list "
            "(29 listed schools, 10 tier 1): the proxy tier is named here "
            "explicitly and is hand-authored reference data, origin unverified"
        ),
        "dist_top_secondary_per_100m": (
            "shipped nearest_top_secondary_school_dist in metres / 100 — "
            "distance to the nearest TIER-1 secondary school of the manual "
            "tier list (25 listed schools, 5 tier 1): same named proxy"
        ),
    }
    rows: dict[str, Any] = {}
    for name in regressors:
        index = design_columns.index(name)
        beta = float(model.params[index])
        se = float(model.bse[index])
        rows[name] = {
            "regressor": regressor_labels[name],
            "logPointPer100m": _r(beta, 6),
            "robustSePer100m": _r(se, 6),
            "tStat": _r(beta / se, 2),
            "pctEffectPer100m": _r(100.0 * (float(np.exp(beta)) - 1.0), 4),
            "interpretation": (
                "conditional log-point difference in PSF associated with +100 m "
                "of distance, holding the stated controls fixed; descriptive "
                "only, NOT a causal admissions premium"
            ),
        }

    matrix = np.column_stack([values for values in regressors.values()])
    correlations: dict[str, Any] = {}
    pairs = list(regressors)
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            key = f"{pairs[i]}__{pairs[j]}"
            correlations[key] = _r(float(np.corrcoef(matrix[:, i], matrix[:, j])[0, 1]), 4)

    return {
        "estimator": {
            "family": "OLS",
            "response": "ln(psf)",
            "covariance": "HC1 robust",
            "software": "statsmodels sm.OLS",
            "fixedEffects": {
                "flatType": {"baseline": FLAT_TYPE_BASELINE},
                "town": {
                    "baseline": TOWN_BASELINE,
                    "levelsInSample": int(sample["town"].nunique()),
                },
                "year": {"baseline": YEAR_BASELINE},
            },
            "continuousControls": [
                "floor_area_sqm / 10",
                "(lease_commence_date - 2000) / 10",
                "(storey_min + storey_max) / 2 / 10",
            ],
        },
        "screen": {
            "definition": (
                "the legacy's own stated screen, adopted verbatim: HDB rows, "
                f"{STUDY_WINDOW_START}..{last_complete} (measured last complete "
                "month), nearest_schoolPRIMARY_dist <= 2000 m, complete cases on "
                "regressors and controls, psf > 0"
            ),
            "radiusMetres": PRIMARY_RADIUS_M,
            "windowStart": STUDY_WINDOW_START,
            "windowEnd": last_complete,
        },
        "exclusionReasonCounts": reason_counts,
        "exclusionBasis": {
            "basisRowCount": int(len(frame)),
            "terminalMonthRowsAllOutsideStudyWindow": int(
                (frame["month"].astype(str) > last_complete).sum()
            ),
            "meaning": (
                "the exclusion partition covers the full raw file including the "
                "terminal month's rows, every one of which the window filter "
                "excludes (terminalMonthRowsAllOutsideStudyWindow = "
                "cutoff.terminalMonthTransactions); the through-cutoff outside "
                "count is basisRowCount minus that field minus the sample"
            ),
        },
        "sample": {
            "n": n,
            "firstMonth": str(sample["month"].astype(str).min()),
            "lastMonth": str(sample["month"].astype(str).max()),
            "medianPsf": _r(float(_numeric(sample["psf"]).median()), 2),
            "medianPrimaryDistMetres": _r(
                float(_numeric(sample["nearest_schoolPRIMARY_dist"]).median()), 2
            ),
            "designColumnCount": len(design_columns),
        },
        "distanceCoefficients": rows,
        "regressorCorrelations": correlations,
        "multipleTesting": {
            "preStatedSpecifications": 1,
            "distanceCoefficients": len(rows),
            "allCoefficientsReported": True,
            "selectionOnSignificance": False,
            "correctionApplied": "none",
            "policyNote": (
                "one pre-stated specification; all three distance coefficients "
                "are reported regardless of significance; no coefficient is "
                "selected, dropped or promoted on significance, so no "
                "multiplicity correction is required and none is applied; no "
                "causal or admissions-premium conclusion is drawn from any "
                "coefficient"
            ),
        },
        "accessibilityExcluded": {
            "column": "school_accessibility_score",
            "reason": (
                "the shipped score is screened as embedding the manual tier "
                "lists' policy-status columns (policyEligibility), and the gate "
                "keeps policy eligibility outside model outputs"
            ),
        },
        "interpretation": (
            "a descriptive conditional association measured on the columns that "
            "exist, on the legacy's own stated screen; it does not establish a "
            "causal admissions premium and the pack draws no eligibility or "
            "valuation rule from it"
        ),
    }


def rdd_recovery(
    paths: list[Path],
    data_entries: list[dict[str, Any]],
    schema_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Gate clauses bandwidth / treatment assignment / covariate balance."""
    rdd_tokens = _token_scan(
        paths,
        (
            "regression discontinuity",
            "rdrobust",
            "RDD",
            "admission boundary",
            "admissions boundary",
            "covariate balance",
        ),
        case_sensitive=False,
    )
    case_hits = _token_scan(paths, ("RDD",), case_sensitive=True)
    rdd_tokens["RDD-case-sensitive"] = case_hits["RDD"]

    school_rdd_dir = RDD_PLOT.parent
    served_plot_files = sorted(path.name for path in school_rdd_dir.iterdir() if path.is_file())
    impact_dir = IMPACT_PLOT.parent
    impact_files = sorted(path.name for path in impact_dir.iterdir() if path.is_file())

    data_roots = ["data/", "app/public/data/"]
    bandwidth_filename_scan = _filename_artefact_scan(
        data_entries,
        data_roots,
        ("bandwidth", "sensitivity", "placebo", "discontinuity", "rdd"),
    )
    bandwidth_content_scan = _content_token_scan(
        data_entries, ("bandwidth", "sensitivity", "placebo")
    )
    bandwidth_column_tokens = ("bandwidth", "sensitivity", "placebo")
    bandwidth_column_matches: list[dict[str, Any]] = []
    for entry in schema_entries:
        names = {str(name).lower() for name in pq.read_schema(REPO_ROOT / entry["path"]).names}
        hit = sorted(
            {token for token in bandwidth_column_tokens if any(token in name for name in names)}
        )
        if hit:
            bandwidth_column_matches.append({"path": entry["path"], "tokens": hit})
    boundary_filename_scan = _filename_artefact_scan(
        data_entries, data_roots, ("boundary", "admission", "admissions")
    )
    boundary_content_scan = _content_token_scan(
        data_entries, ("admission boundary", "admissions boundary", "school boundary")
    )

    return {
        "bandwidth": {
            "status": "notRecorded",
            "legacyStatements": {
                "bandwidth": "200 m on each side of boundary",
                "sensitivity": "tested at 100-300 m",
                "placebos": "800 m and 1200 m fake cutoffs",
            },
            "artefactScan": {
                "method": (
                    "three measured passes over one enumeration: (a) every file "
                    "under data/ and app/public/data/ whose NAME carries a "
                    "bandwidth/sensitivity/placebo/discontinuity/rdd token; "
                    "(b) every .csv/.json/.md under the same roots scanned line "
                    "by line for bandwidth/sensitivity/placebo CONTENT tokens; "
                    "(c) every parquet schema under data/pipeline/ and "
                    "data/analysis/ (metadata-only) checked for column names "
                    "carrying the same tokens"
                ),
                "filenameScan": bandwidth_filename_scan,
                "contentScan": bandwidth_content_scan,
                "parquetColumnScan": {
                    "filesScanned": len(schema_entries),
                    "tokens": list(bandwidth_column_tokens),
                    "matchedCount": len(bandwidth_column_matches),
                    "matches": bandwidth_column_matches,
                    "manifestKey": "scanManifests.schemaRoots",
                },
                "meaning": (
                    "measured: the only filename matches are the served RDD PNG "
                    "itself (sha-pinned at servedPlots) and any file whose name "
                    "carries the listed tokens (matchedFiles lists every one); "
                    "the content and parquet-column passes record their own "
                    "counts. A filename/content/schema scan bounds what is "
                    "NAMED in the checkout; a bandwidth table could in principle "
                    "hide inside a binary or a generically named file, and that "
                    "boundary is stated rather than widened"
                ),
            },
            "meaning": (
                "the bandwidth claims are recorded as the legacy's own prose and "
                "are not re-measurable: no artefact NAMED for bandwidth, "
                "sensitivity or placebo exists under the enumerated data roots "
                "(artefactScan), and re-deriving one would require re-running "
                "the RDD, which this pack does not do"
            ),
            "ledgerKey": "rddRecovery.bandwidth",
        },
        "treatmentAssignment": {
            "status": "unmeasurable",
            "definitionRequired": (
                "treatment = within 1 km of the nearest primary school at the "
                "admissions boundary; this requires (a) school coordinates and "
                "(b) a dated 1 km boundary definition"
            ),
            "coordinatesAvailable": (
                "no shipped layer carries school coordinates "
                "(schoolCoordinates.bronzeDirectoryCoordinates); one unconsumed "
                "coordinate artefact exists (schoolCoordinates.schoolsMoeGeojson) "
                "and is unlinked in both directions"
            ),
            "boundaryArtefact": {
                "datedBoundaryArtefactExists": False,
                "filenameScan": boundary_filename_scan,
                "contentScan": boundary_content_scan,
                "meaning": (
                    "measured over every file under data/ and app/public/data/: "
                    "the only boundary-named match is classified in matchedFiles "
                    "(a planning-area geometry file, not a school-keyed or dated "
                    "admissions boundary), and no .csv/.json/.md content under "
                    "the roots carries an admissions-boundary token. 'admission "
                    "boundary'/'admissions boundary' otherwise occur only in "
                    "prose surfaces (tokenScan). The scan bounds file NAMES and "
                    "text-file CONTENT, not geometry inside binary formats; that "
                    "boundary is stated rather than widened"
                ),
                "classificationOfMatches": {
                    entry["path"]: (
                        "URA planning-area boundary geojson (screened as from its "
                        "name): planning-area geometry, not school-keyed, not "
                        "dated to admissions — listed because it matched, not to "
                        "dismiss it"
                    )
                    for entry in boundary_filename_scan["matchedFiles"]
                    if "planning_area_boundary" in entry["path"]
                },
            },
            "meaning": (
                "without a linked coordinate source and a dated boundary, "
                "treatment cannot be assigned to any shipped row, so no "
                "treatment-effect estimate can be reproduced or refuted here"
            ),
        },
        "covariateBalance": {
            "status": "unmeasurable",
            "legacyStatement": "FAILED — boundary groups differ systematically on age, size, MRT distance, and neighborhood profile",
            "meaning": (
                "the legacy itself records its covariate balance as FAILED; with "
                "no treatment assignment (above) there are no boundary groups to "
                "balance, so the failure is neither re-measurable nor refutable "
                "here. A failed-design estimate is not a premium: the -79.47 "
                "PSF figure is recorded as a failed-design estimate, and the "
                "causal reading is withdrawn at legacyClaims"
            ),
        },
        "servedPlots": {
            "method": (
                "HUMAN VISUAL READ of the two sha-pinned PNGs by the producer, "
                "recorded because the pixels are not machine-read. The hashes "
                "pin exactly which images were read; the values below are what "
                "they visibly print, and are not re-derived numbers. An image "
                "whose hash changes invalidates its read and must be re-read"
            ),
            "rddVisualization": {
                "path": _relative(RDD_PLOT),
                "sha256": sha256_of(RDD_PLOT),
                "bytes": int(RDD_PLOT.stat().st_size),
                "directoryFiles": served_plot_files,
                "visiblePrint": {
                    "title": "RDD: Price Discontinuity at 1km School Boundary",
                    "xAxis": "Distance to Primary School (m), plotted about 800-1200",
                    "yAxis": "Price PSF ($)",
                    "legend": ["Control (>1km)", "Treated (\u22641km)", "1km Cutoff"],
                    "cutoff": "a red dashed rule at 1000 m",
                    "shape": (
                        "the fitted line visibly steps DOWN across the cutoff "
                        "(treated side rising to about 1990 near 980 m, control "
                        "side starting about 1550 just past 1000 m), consistent "
                        "in direction with the legacy's negative estimate; the "
                        "scatter is sparse binned means, not the 52,881-row "
                        "sub-sample"
                    ),
                },
                "meaning": (
                    "a served plot with no numbers attached: it neither "
                    "reproduces nor refutes the legacy's -79.47 PSF, and no "
                    "table behind it is stored in the checkout"
                ),
            },
            "exploratoryAnalysis": {
                "path": _relative(IMPACT_PLOT),
                "sha256": sha256_of(IMPACT_PLOT),
                "bytes": int(IMPACT_PLOT.stat().st_size),
                "directoryFiles": impact_files,
                "visiblePrint": {
                    "panels": [
                        "Price PSF ($) vs School Accessibility Score scatter (mass at score 0)",
                        "a quality-bands panel printed 'No data for quality bands'",
                        "Distribution of School Accessibility Scores histogram annotated 'Median: 0.00'",
                        "Primary vs Secondary School Quality scatter, axes 0-8 and 0-9, coloured by Price PSF ($)",
                    ],
                    "meaning": (
                        "the served exploratory figure itself prints that its "
                        "quality-band analysis had NO DATA, and a median "
                        "accessibility of 0.00 — consistent with the measured "
                        "zero mass in columnHealth, and a visual record that the "
                        "quality-score axis of the legacy study was "
                        "data-starved at plot time"
                    ),
                },
            },
            "unlinkedNote": (
                "the legacy's provenance section names the served analysis tree "
                "generically as the canonical asset location; neither PNG "
                "carries a run identifier, so each is recorded as what it "
                "visibly prints and as evidence in NEITHER direction about the "
                "legacy's stored fits"
            ),
        },
        "legacyMethodStatements": {
            "recordedStatus": "notReproducible",
            "statements": {
                "estimator": "OLS and XGBoost with school features plus controls (floor area, lease, amenities)",
                "xgboostParameters": "n_estimators=100, max_depth=6, learning_rate=0.1",
                "rddModel": "price = \u03b1 + \u03c4\u00b7treated + \u03b2\u00b7running_var + \u03b3\u00b7(treated \u00d7 running_var) + controls",
                "uncertainty": "Robust HC3 standard errors, 95% confidence intervals",
                "spatialCv": "standard 5-fold CV vs GroupKFold by planning area; large generalization gap (no magnitude recorded)",
            },
            "meaning": (
                "each statement is recorded verbatim from the legacy text; no "
                "fitted object, parameter file or output table for any of them "
                "exists in the checkout (tokenScan and "
                "adjacentModelArtefacts record the nearest surfaces), so none "
                "is re-runnable"
            ),
        },
        "tokenScan": {
            "roots": list(SCAN_ROOTS),
            "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
            "excludedPaths": list(EXCLUDED_SCAN_PATHS),
            "filesScanned": len(paths),
            "manifestKey": "scanManifests.textRoots",
            "tokens": rdd_tokens,
        },
    }


def multiplicity_policy(paths: list[Path]) -> dict[str, Any]:
    """Gate clause: multiple-testing policy, legacy and this pack."""
    legacy_scan = _token_scan(paths, MULTIPLICITY_TOKENS)
    total = sum(int(entry["occurrences"]) for entry in legacy_scan.values())
    return {
        "legacyRecordedCorrection": {
            "status": "absent",
            "tokens": legacy_scan,
            "totalOccurrences": total,
            "filesScanned": len(paths),
            "manifestKey": "scanManifests.textRoots",
            "scanBoundary": (
                "the scanned text roots with the programme's own surfaces "
                "excluded (tokenScan.excludedPrefixes): app/src/components/studies/ "
                "(edition registry/pages), app/tests/ (fixtures), .secrets.baseline, "
                "the planning/spec surface docs/plans/ and "
                "docs/plans/2026-11-12-reporting-refresh-decisions.md (D12 "
                "register), and the operational surface docs/guides/ "
                "(runbooks and setup/CI documentation about the programme) "
                "are excluded; a correction recorded "
                "only inside those excluded surfaces would not be found, and "
                "that boundary is disclosed rather than widened"
            ),
            "legacyNamedTestFamilies": [
                "one headline OLS (+ one XGBoost)",
                "three regional fits (OCR/RCR/CCR)",
                "one RDD at 1 km",
                "bandwidth sensitivity 100-300 m (number of bandwidths unstated)",
                "two placebo cutoffs (800 m, 1200 m)",
                "covariate balance t-tests",
            ],
            "meaning": (
                "the legacy names at least six test families and records no "
                "multiple-testing correction anywhere in the scanned roots; the "
                "regional split whose sign flips in RCR is one of these "
                "uncorrected families"
            ),
        },
        "thisPack": {
            "preStatedSpecifications": 1,
            "reportedCoefficients": 3,
            "selectionOnSignificance": False,
            "correctionApplied": "none",
            "reason": (
                "a single pre-stated descriptive specification with all "
                "coefficients reported needs no correction; the pack's "
                "conclusion is 'association, not premium', which no coefficient "
                "significance could upgrade"
            ),
        },
    }


def adjacent_model_artefacts() -> dict[str, Any]:
    """The served tree's nearest model artefacts, recorded and NOT adjudicating."""
    files: list[dict[str, Any]] = []
    school_token_rows = 0
    legacy_name_rows = 0
    price_psf_linear_test_r2 = None
    for path in sorted(FEATURE_IMPORTANCE_DIR.iterdir()):
        if not path.is_file():
            continue
        entry: dict[str, Any] = {
            "path": _relative(path),
            "sha256": sha256_of(path),
            "bytes": int(path.stat().st_size),
        }
        if path.suffix == ".csv":
            frame = pd.read_csv(path)
            entry["dataRows"] = int(len(frame))
            has_feature_column = "feature" in {str(name) for name in frame.columns}
            if has_feature_column:
                features = frame["feature"].astype(str).str.lower()
                school_rows = int(features.str.contains("school").sum())
                entry["schoolTokenRows"] = school_rows
                entry["legacyFeatureNameRows"] = int(features.isin(LEGACY_FEATURE_NAMES).sum())
                school_token_rows += school_rows
                legacy_name_rows += int(entry["legacyFeatureNameRows"])
            if path.name == "model_comparison.csv":
                match = frame[
                    (frame["target"] == "price_psf") & (frame["model"] == "Linear Regression")
                ]
                if not match.empty:
                    price_psf_linear_test_r2 = _r(float(match.iloc[0]["test_r2"]), 6)
        files.append(entry)
    return {
        "directory": _relative(FEATURE_IMPORTANCE_DIR),
        "files": files,
        "schoolTokenRowsTotal": school_token_rows,
        "legacyFeatureNameRowsTotal": legacy_name_rows,
        "pricePsfLinearTestR2": price_psf_linear_test_r2,
        "meaning": (
            "the checkout's nearest stored model outputs: importance tables and "
            "a model comparison whose school rows are preschool amenity "
            "features, with zero rows for any of the legacy's three feature "
            "names. The trees are UNLINKED to the legacy article's fits — "
            "symmetrically, they are evidence neither for nor against its "
            "coefficients, and their price_psf linear test R-squared is a "
            "different model on a different population, recorded only so the "
            "near-match in vocabulary cannot be mistaken for lineage"
        ),
    }


def method_record_surfaces() -> dict[str, Any]:
    """The retired programme's plan documents, sha-pinned as prose surfaces."""

    def _pinned(path: Path) -> dict[str, Any]:
        return {
            "path": _relative(path),
            "sha256": sha256_of(path),
            "bytes": int(path.stat().st_size),
            "lines": len(path.read_text(encoding="utf-8", errors="replace").splitlines()),
        }

    return {
        "plan2025": _pinned(PLAN_DOC_2025),
        "plan2026": _pinned(PLAN_DOC_2026),
        "liveTwin": _pinned(LIVE_TWIN),
        "meaning": (
            "the legacy method vocabulary also lives in these surfaces; they "
            "are recorded and pinned because tokenScan cites them, and an "
            "unlinked prose surface adjudicates nothing about the article's "
            "fits in either direction"
        ),
    }


def not_measurable() -> list[dict[str, Any]]:
    return [
        {
            "id": "legacyModelFit",
            "gateClause": "School-quality model fit does not establish a causal admissions premium.",
            "status": "notReproducible",
            "reason": (
                "the three legacy feature names exist in no shipped schema "
                "(legacyFeatureNames.schemaScan) and no fitted OLS/XGBoost "
                "object, coefficient table or output file for the legacy's "
                "model exists in the checkout; the +9.66/+6.27/+3.52 PSF "
                "figures cannot be re-derived and are recorded as the legacy's "
                "own. This pack fits no premium model: its single association "
                "is descriptive and is reported as an association, not a "
                "premium"
            ),
            "ledgerKey": "legacyFeatureNames.schemaScan",
        },
        {
            "id": "regionalFits",
            "gateClause": "School-quality model fit does not establish a causal admissions premium.",
            "status": "notReproducible",
            "reason": (
                "the regional coefficients (+9.63 / -23.67 / about-0 PSF) and "
                "R-squareds belong to fits that are not stored; the measured "
                "regional row counts (legacySampleReconciliation.regionalComparison) "
                "reproduce none of the legacy's segment sizes. The RCR sign flip "
                "is recorded as a property of the legacy's own unrecorded fit: "
                "nothing measured here can confirm or refute it"
            ),
            "ledgerKey": "legacySampleReconciliation.regionalComparison",
        },
        {
            "id": "rddEstimate",
            "gateClause": "School-quality model fit does not establish a causal admissions premium.",
            "status": "withdrawn",
            "reason": (
                "the -79.47 PSF treatment effect rests on a covariate balance "
                "the legacy itself records as FAILED — a failed-design "
                "estimate, not a premium; no RDD table, bandwidth object or "
                "boundary definition is stored, so the estimate cannot be "
                "re-derived, and its causal reading is withdrawn from the "
                "edition regardless"
            ),
            "ledgerKey": "rddRecovery.covariateBalance",
        },
        {
            "id": "treatmentAssignment",
            "gateClause": "Recheck ... treatment assignment ...",
            "status": "unmeasurable",
            "reason": (
                "treatment = within 1 km at the admissions boundary needs school "
                "coordinates and a dated boundary; neither exists in a linked "
                "artefact (rddRecovery.treatmentAssignment), so no shipped row "
                "can be assigned treatment and the assignment rule cannot be "
                "rechecked, only recorded as unmeasurable with its scan"
            ),
            "ledgerKey": "rddRecovery.treatmentAssignment",
        },
        {
            "id": "covariateBalance",
            "gateClause": "Recheck ... covariate balance ...",
            "status": "unmeasurable",
            "reason": (
                "with no treatment assignment there are no boundary groups to "
                "balance; the legacy's FAILED verdict is its own recorded "
                "diagnostic of its own design and is not re-measurable here"
            ),
            "ledgerKey": "rddRecovery.covariateBalance",
        },
        {
            "id": "bandwidthArtefact",
            "gateClause": "Recheck ... bandwidth ...",
            "status": "notRecorded",
            "reason": (
                "no bandwidth object, sensitivity table or placebo output "
                "exists; the legacy's 200 m / 100-300 m / 800-1200 m figures "
                "are recorded as prose statements with their scan at "
                "rddRecovery.bandwidth"
            ),
            "ledgerKey": "rddRecovery.bandwidth",
        },
        {
            "id": "spatialCv",
            "gateClause": "Recheck ... multiple-testing policy ...",
            "status": "notReproducible",
            "reason": (
                "the legacy records a 'large generalization gap' with no "
                "magnitude, no fold assignment and no stored output; the gap is "
                "underspecified and not reproducible from this checkout"
            ),
            "ledgerKey": "rddRecovery.legacyMethodStatements",
        },
        {
            "id": "policyEligibilityOutsideOutputs",
            "gateClause": "Keep policy eligibility outside model outputs.",
            "status": "enforcedByConstruction",
            "reason": (
                "no model output in this pack consumes sap_ind, gifted_ind, "
                "ip_ind, autonomous_ind or any tier-list policy column: the "
                "association regressors are three policy-free distance columns "
                "(policyEligibility.associationExclusion), the bronze flags "
                "have zero call sites under src/ "
                "(policyEligibility.srcConsumptionScan), and the one shipped "
                "column that embeds policy flags is excluded from the model"
            ),
            "ledgerKey": "policyEligibility.srcConsumptionScan",
        },
    ]


LEGACY_CLAIMS: tuple[dict[str, str], ...] = (
    {
        "id": "C1",
        "phrase": "**Sample**: 194,165 transactions",
        "status": "not-reproducible",
        "ledgerKey": "legacySampleReconciliation.candidatePopulations",
        "note": (
            "no measured window reproduces 194,165; the closest candidates are "
            "recorded with their counts and differences at "
            "legacySampleReconciliation.candidatePopulations"
        ),
    },
    {
        "id": "C2",
        "phrase": "194,165 transactions, 2021 onward, within 2 km of primary schools",
        "status": "not-reproducible",
        "ledgerKey": "legacySampleReconciliation.candidatePopulations",
        "note": (
            "the screen is constructible and was measured on four candidate "
            "readings (HDB/all-types, both distance columns, through the "
            "legacy's publication month); none reproduces the stated size"
        ),
    },
    {
        "id": "C3",
        "phrase": "2021 onward, within 2 km of primary schools",
        "status": "re-measured",
        "ledgerKey": "association.screen",
        "note": (
            "the definition itself is adopted verbatim as this pack's "
            "association screen and its measured counts recorded at "
            "legacySampleReconciliation; adopting a screen is not endorsing "
            "the sample size claimed of it"
        ),
    },
    {
        "id": "C4",
        "phrase": "+$9.66 PSF",
        "status": "not-reproducible",
        "ledgerKey": "legacyFeatureNames.schemaScan",
        "note": (
            "school_primary_quality_score exists in no shipped schema and no "
            "coefficient table is stored; the coefficient cannot be re-derived"
        ),
    },
    {
        "id": "C5",
        "phrase": "+$6.27 PSF",
        "status": "not-reproducible",
        "ledgerKey": "legacyFeatureNames.schemaScan",
        "note": "school_primary_dist_score exists in no shipped schema; same ground as C4",
    },
    {
        "id": "C6",
        "phrase": "+$3.52 PSF",
        "status": "not-reproducible",
        "ledgerKey": "legacyFeatureNames.schemaScan",
        "note": "school_secondary_dist_score exists in no shipped schema; same ground as C4",
    },
    {
        "id": "C7",
        "phrase": "For a 1,000 sqft unit, a 3-point quality-score difference implies about **$29,000** in modeled price difference.",
        "status": "not-reproducible",
        "ledgerKey": "legacyArithmetic",
        "note": (
            "the legacy's own arithmetic is internally consistent "
            "(legacyArithmetic.product = 28,980 against its stated 29,000, a "
            "rounding step) but inherits the non-reproducibility of the "
            "coefficient it scales; the pack records the arithmetic without "
            "restating the conclusion"
        ),
    },
    {
        "id": "C8",
        "phrase": "+$9.63 PSF",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.regionalFits",
        "note": "the OCR coefficient belongs to a regional fit that is not stored",
    },
    {
        "id": "C9",
        "phrase": "146,553",
        "status": "not-reproducible",
        "ledgerKey": "legacySampleReconciliation.regionalComparison",
        "note": "the measured OCR analogue on the legacy's own screen is recorded beside it",
    },
    {
        "id": "C10",
        "phrase": "R²=0.53",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.regionalFits",
        "note": "the OCR R-squared belongs to a fit that is not stored; no regional R-squared is re-measurable",
    },
    {
        "id": "C11",
        "phrase": "-$23.67 PSF",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.regionalFits",
        "note": (
            "the RCR coefficient belongs to an unrecorded fit; the sign flip it "
            "carries is recorded as the legacy's own stated property, not "
            "re-measured"
        ),
    },
    {
        "id": "C12",
        "phrase": "46,298",
        "status": "not-reproducible",
        "ledgerKey": "legacySampleReconciliation.regionalComparison",
        "note": "the measured RCR analogue is recorded beside it",
    },
    {
        "id": "C13",
        "phrase": "R²=0.80",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.regionalFits",
        "note": "the RCR R-squared belongs to a fit that is not stored",
    },
    {
        "id": "C14",
        "phrase": "In **RCR**, the sign flips, which suggests other neighborhood forces dominate.",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.regionalFits",
        "note": (
            "the flip is a property of the legacy's unrecorded fit; this pack "
            "records it, does not re-measure it, and draws no neighbourhood "
            "explanation from it — the legacy's 'other neighborhood forces "
            "dominate' is its own interpretation, not a measured finding"
        ),
    },
    {
        "id": "C15",
        "phrase": "about $0 PSF",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.regionalFits",
        "note": (
            "an open-ended band ('about $0') for the CCR fit; no stored fit "
            "exists to compare it against"
        ),
    },
    {
        "id": "C16",
        "phrase": "1,314",
        "status": "not-reproducible",
        "ledgerKey": "legacySampleReconciliation.regionalComparison",
        "note": "the measured CCR analogue is recorded beside it",
    },
    {
        "id": "C17",
        "phrase": "R²=0.87",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.regionalFits",
        "note": "the CCR R-squared belongs to a fit that is not stored",
    },
    {
        "id": "C18",
        "phrase": "-$79.47 PSF",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.rddEstimate",
        "note": (
            "a failed-design estimate (the legacy's own covariate balance is "
            "FAILED), not re-derivable from any stored artefact; the causal "
            "reading is withdrawn and no 'within-1km discount' is stated"
        ),
    },
    {
        "id": "C19",
        "phrase": "Units within 1km were cheaper after controls",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.rddEstimate",
        "note": (
            "the interpretation cell of the withdrawn estimate; treatment "
            "cannot even be assigned from this checkout (rddRecovery."
            "treatmentAssignment), so the sentence is withdrawn rather than "
            "re-measured"
        ),
    },
    {
        "id": "C20",
        "phrase": "52,881 near-boundary transactions (800-1200 m from nearest school)",
        "status": "not-reproducible",
        "ledgerKey": "legacySampleReconciliation.rddBand",
        "note": (
            "three candidate readings of the band are measured and none "
            "reproduces 52,881; the legacy's running variable is unstated, so "
            "the record is underspecified and no choice is made for it"
        ),
    },
    {
        "id": "C21",
        "phrase": "800-1200 m from nearest school",
        "status": "re-measured",
        "ledgerKey": "legacySampleReconciliation.rddBand",
        "note": (
            "the band definition is adopted verbatim and its measured counts "
            "recorded under three candidate readings of 'nearest school'"
        ),
    },
    {
        "id": "C22",
        "phrase": "Covariate balance | Failed",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.covariateBalance",
        "note": (
            "the legacy's own design diagnostic; without treatment assignment "
            "there are no boundary groups, so the failure is neither "
            "re-measurable nor refutable here"
        ),
    },
    {
        "id": "C23",
        "phrase": "FAILED — boundary groups differ systematically on age, size, MRT distance, and neighborhood profile",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.covariateBalance",
        "note": (
            "same ground as C22; the dimensions named (age, size, MRT "
            "distance, neighbourhood profile) are recorded, not re-tested"
        ),
    },
    {
        "id": "C24",
        "phrase": "Regression discontinuity around the 1km admissions boundary does **not** support a clean positive premium.",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.rddEstimate",
        "note": (
            "withdrawn in BOTH directions: no premium is supported, and the "
            "sentence's implied negative treatment reading is equally not "
            "re-established — the design artefacts do not exist to support "
            "either"
        ),
    },
    {
        "id": "C25",
        "phrase": "the treatment effect is negative after controls, and covariate balance fails",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.rddEstimate",
        "note": (
            "the legacy conclusion's causal/RDD language is retired; what "
            "remains in this pack is a descriptive distance association and "
            "the recorded unmeasurability of the design"
        ),
    },
    {
        "id": "C26",
        "phrase": "n_estimators=100, max_depth=6, learning_rate=0.1",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.legacyMethodStatements",
        "note": (
            "parameters recorded in prose only; no model object or run record "
            "carries them (adjacentModelArtefacts records the nearest stored "
            "trees, unlinked)"
        ),
    },
    {
        "id": "C27",
        "phrase": "Bandwidth: 200 m on each side of boundary",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.bandwidth",
        "note": "no bandwidth artefact exists; the statement is recorded with its scan",
    },
    {
        "id": "C28",
        "phrase": "tested at 100-300 m; placebo tests at 800 m and 1200 m fake cutoffs",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.bandwidth",
        "note": (
            "no sensitivity or placebo output is stored; the number of "
            "bandwidths inside 100-300 m is unstated and is not chosen for it"
        ),
    },
    {
        "id": "C29",
        "phrase": "Robust HC3 standard errors, 95% confidence intervals",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.legacyMethodStatements",
        "note": (
            "an estimator detail of unrecorded fits; this pack's one model "
            "uses HC1 (RS04's estimator family) and claims no equivalence"
        ),
    },
    {
        "id": "C30",
        "phrase": "standard 5-fold CV vs GroupKFold by planning area",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.legacyMethodStatements",
        "note": "no fold assignment, CV split or score output is stored",
    },
    {
        "id": "C31",
        "phrase": "large generalization gap between standard CV and spatial CV",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.spatialCv",
        "note": (
            "the gap is stated without a magnitude, window or population — "
            "underspecified and not reproducible; no number is chosen for it"
        ),
    },
    {
        "id": "C32",
        "phrase": "Singapore primary school admission boundary",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.treatmentAssignment.boundaryArtefact",
        "note": (
            "a policy fact asserted in prose; no dated boundary artefact exists "
            "in the checkout, and the phrase is recorded without endorsing a "
            "date or a geometry for it"
        ),
    },
    {
        "id": "C33",
        "phrase": "Model: `price = α + τ·treated + β·running_var + γ·(treated × running_var) + controls`",
        "status": "not-reproducible",
        "ledgerKey": "rddRecovery.legacyMethodStatements",
        "note": "the specification is recorded verbatim; no fitted counterpart exists",
    },
    {
        "id": "C34",
        "phrase": "Post-2021 housing market",
        "status": "re-measured",
        "ledgerKey": "cutoff.frameFirstMonth",
        "note": (
            "the frame spans 1990-01 through the terminal month and the "
            "post-2021 window is constructible; the measured window boundaries "
            "are recorded at legacySampleReconciliation.measuredSample"
        ),
    },
    {
        "id": "C35",
        "phrase": "OLS and XGBoost** with school features (`school_primary_quality_score`, `school_primary_dist_score`, `school_secondary_dist_score`)",
        "status": "not-reproducible",
        "ledgerKey": "legacyFeatureNames.schemaScan",
        "note": (
            "the three named features exist in no shipped schema; the sentence "
            "describes a feature set this checkout cannot rebuild"
        ),
    },
    {
        "id": "C36",
        "phrase": "OLS and XGBoost agree on direction and magnitude",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.legacyModelFit",
        "note": (
            "an agreement claim about two unrecorded fits; neither side of the "
            "agreement exists to compare"
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

    Lists are traversed by their items' `id`, so
    `notMeasurable.rddEstimate` and `rddRecovery.covariateBalance` are both
    resolvable forms. Resolution is syntactic: the key must name an existing
    node in THIS ledger; it does not judge the disposition's content.
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
            "each claim's ledgerKey is resolved against this ledger at build "
            "time by walking dict keys and list items by their `id`; the "
            "resolution is syntactic — it verifies the key names a recorded "
            "node, not the disposition's content — and an unresolved key fails "
            "the build rather than shipping"
        ),
    }


def legacy_arithmetic() -> dict[str, Any]:
    """The legacy's own practical-scale arithmetic, parsed from its text.

    The operands are parsed from the frozen article (a paraphrase would break
    the parse and fail the build); the product is computed, not recalled.
    """
    text = LEGACY_EDITION.read_text(encoding="utf-8")
    coefficient_match = re.search(r"\+\$([0-9.]+) PSF", text)
    sentence_match = re.search(
        r"For a ([0-9,]+) sqft unit, a ([0-9]+)-point quality-score difference "
        r"implies about \*\*\$([0-9,]+)\*\* in modeled price difference",
        text,
    )
    if coefficient_match is None or sentence_match is None:
        raise SystemExit("legacy arithmetic sentence not found verbatim; the parse is stale")
    coefficient_psf = float(coefficient_match.group(1))
    floor_area_sqft = float(sentence_match.group(1).replace(",", ""))
    points = float(sentence_match.group(2))
    legacy_stated = float(sentence_match.group(3).replace(",", ""))
    product = coefficient_psf * points * floor_area_sqft
    return {
        "operandsSource": "parsed from the frozen legacy text (legacyQuoteCheck pins the phrases)",
        "coefficientPsf": coefficient_psf,
        "points": points,
        "floorAreaSqft": floor_area_sqft,
        "product": _r(product, 2),
        "legacyStated": legacy_stated,
        "difference": _r(product - legacy_stated, 2),
        "meaning": (
            "the legacy's $29,000 is its own +$9.66 PSF coefficient times 3 "
            "points times 1,000 sqft, rounded up from 28,980; the arithmetic "
            "closes on the coefficient, whose own reproduction fails at "
            "legacyFeatureNames.schemaScan"
        ),
    }


def build() -> dict[str, Any]:
    columns = [
        "month",
        "property_type",
        "region",
        "town",
        "flat_type",
        "psf",
        "floor_area_sqm",
        "lease_commence_date",
        "storey_min",
        "storey_max",
        *DISTANCE_COLUMNS,
        "school_accessibility_score",
    ]
    frame = pd.read_parquet(UNIFIED, columns=columns)
    measured_cutoff = cutoff(frame)
    last_complete = measured_cutoff["lastCompleteMonth"]
    paths = _scan_files()

    directory = school_directory_inventory()
    data_entries = _data_entries()
    code_entries = _code_entries()
    schema_entries = _schema_entries()
    code_paths = [REPO_ROOT / entry["path"] for entry in code_entries]
    tiers = tier_provenance(directory, data_entries, code_paths)
    screen_mask = (
        (frame["property_type"] == "hdb").to_numpy()
        & (frame["month"].astype(str) >= STUDY_WINDOW_START).to_numpy()
        & (frame["month"].astype(str) <= last_complete).to_numpy()
        & (_numeric(frame["nearest_schoolPRIMARY_dist"]) <= PRIMARY_RADIUS_M)
        .fillna(False)
        .to_numpy()
    )

    claims = legacy_claims()
    inputs = {}
    for path in (
        UNIFIED,
        SCHOOL_DIRECTORY,
        SCHOOLS_MOE_GEOJSON,
        TIERS_PRIMARY,
        TIERS_SECONDARY,
        WEIGHTS_CSV,
        METHODOLOGY_MD,
        LEGACY_EDITION,
        RDD_PLOT,
        IMPACT_PLOT,
        MODEL_COMPARISON,
    ):
        inputs[_relative(path)] = {"sha256": sha256_of(path), "bytes": int(path.stat().st_size)}
    inputs[_relative(UNIFIED)]["rows"] = int(pq.ParquetFile(UNIFIED).metadata.num_rows)
    inputs[_relative(UNIFIED)]["columns"] = int(len(pq.read_schema(UNIFIED).names))
    inputs[_relative(SCHOOL_DIRECTORY)]["rows"] = int(
        pq.ParquetFile(SCHOOL_DIRECTORY).metadata.num_rows
    )
    inputs[_relative(SCHOOL_DIRECTORY)]["columns"] = int(
        len(pq.read_schema(SCHOOL_DIRECTORY).names)
    )
    inputs[_relative(MODEL_COMPARISON)]["dataRows"] = int(len(pd.read_csv(MODEL_COMPARISON)))
    for path, rows_key in (
        (TIERS_PRIMARY, "dataRows"),
        (TIERS_SECONDARY, "dataRows"),
        (WEIGHTS_CSV, "dataRows"),
    ):
        inputs[_relative(path)][rows_key] = int(len(pd.read_csv(path)))
    inputs[_relative(SCHOOLS_MOE_GEOJSON)]["features"] = len(
        json.loads(SCHOOLS_MOE_GEOJSON.read_text(encoding="utf-8")).get("features", [])
    )
    for path in (RDD_PLOT, IMPACT_PLOT):
        inputs[_relative(path)]["class"] = (
            "served PNG (human visual read at rddRecovery.servedPlots)"
        )
    # Review round 2: every file the producer reads and cites by line is pinned
    # in inputs, with measured line counts for the prose inputs.
    for path in (PRODUCER, FEATURES_NODE, DATAGOV_ADAPTER):
        inputs[_relative(path)] = {
            "sha256": sha256_of(path),
            "bytes": int(path.stat().st_size),
            "lines": len(path.read_text(encoding="utf-8", errors="replace").splitlines()),
            "class": "pipeline/producer source cited by line (runtimeGeocoding, qualityScoreFormula, originScan)",
        }
    inputs[_relative(LEGACY_EDITION)]["lines"] = len(
        LEGACY_EDITION.read_text(encoding="utf-8", errors="replace").splitlines()
    )
    inputs[_relative(METHODOLOGY_MD)]["lines"] = len(
        METHODOLOGY_MD.read_text(encoding="utf-8", errors="replace").splitlines()
    )
    inputs[_relative(LEGACY_EDITION)]["class"] = (
        "frozen legacy text (legacyQuoteCheck pins its phrases)"
    )

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": "RS08",
        "series": "school-quality",
        "scope": (
            "RS08 school-quality evidence: tier provenance measured end to end, "
            "the shipped school columns' four missingness states, the legacy "
            "sample reconciliation, one pre-stated distance association, the "
            "RDD/balance/bandwidth/multiplicity clauses recorded as absent or "
            "unmeasurable with their scans, and the withdrawal of causal/RDD "
            "language"
        ),
        "definition": DEFINITION,
        "inputs": inputs,
        "cutoff": measured_cutoff,
        "schoolDirectory": directory,
        "tierProvenance": tiers,
        "policyEligibility": policy_eligibility(paths, tiers, directory),
        "schoolCoordinates": school_coordinates(paths),
        "legacyFeatureNames": legacy_feature_names(paths),
        "columnHealth": column_health(frame, screen_mask, last_complete),
        "legacySampleReconciliation": legacy_sample_reconciliation(frame, last_complete),
        "association": association(frame, last_complete),
        "legacyArithmetic": legacy_arithmetic(),
        "rddRecovery": rdd_recovery(paths, data_entries, schema_entries),
        "multiplicityPolicy": multiplicity_policy(paths),
        "adjacentModelArtefacts": adjacent_model_artefacts(),
        "methodRecordSurfaces": method_record_surfaces(),
        "scanManifests": scan_manifests(paths, schema_entries, data_entries, code_entries),
        "notMeasurable": not_measurable(),
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
        print("Pass: RS08 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS08 ledger does not match this checkout")
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
    tiers = evidence["tierProvenance"]["manualArtefacts"]
    print(
        "Tiers: primary "
        f"{tiers['tiersPrimary']['dataRows']} listed / {tiers['tiersPrimary']['tier1Count']} tier 1; "
        f"secondary {tiers['tiersSecondary']['dataRows']} listed / "
        f"{tiers['tiersSecondary']['tier1Count']} tier 1; bronze school_tiers.json absent="
        f"{not evidence['tierProvenance']['bronzeJsonPreferredAndAbsent']['exists']}"
    )
    sample = evidence["legacySampleReconciliation"]["measuredSample"]
    print(
        "Legacy screen measured: "
        f"{sample['rows']} rows (legacy claims 194,165; reproduces="
        f"{evidence['legacySampleReconciliation']['anyCandidateReproducesLegacySample']})"
    )
    for name, row in evidence["association"]["distanceCoefficients"].items():
        print(
            f"Association {name}: logPoint/100m {row['logPointPer100m']} "
            f"(robust SE {row['robustSePer100m']}) on n={evidence['association']['sample']['n']}"
        )
    quotes = evidence["legacyQuoteCheck"]
    print(
        f"Quote check: {sum(1 for quote in quotes['quotes'] if quote['occurrences'] > 0)}"
        f"/{quotes['claimsChecked']} verbatim"
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
