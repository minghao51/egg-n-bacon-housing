#!/usr/bin/env python3
"""Measure RS13's causal-inference-overview evidence: an identification audit of
the frozen policy-impact article, run against what this checkout actually holds.

RS13's gate is "Recover estimand, treatment/control construction and assumptions.
Check pretrends, confounding concurrent policies, anticipation and robustness/
placebos. A new observation year does not by itself validate an old causal
estimate." This tool measures from the local checkout, and only what the
checkout can support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04/RS05/RS09/
   RS10 shipped, computed on the private rows (the DiD cohort's population) with
   all-rows and HDB cross-checks. Every aggregation in this ledger stops there.
2. **Frame inventory** — metadata-first parquet read (rows/columns from the
   footer, then the columns actually used): property types, the `market_segment`
   region label and its nulls, `region`, `planning_area`, the EC flag, month
   spans, and the four missingness states kept apart (null value, recorded zero,
   absent row, absent column). The frame has NO policy-date column.
3. **Cohort screens** — the two sample definitions the frozen text states,
   measured as screens of cohort sizes inside the cutoff: the condo post-2021
   CCR-vs-OCR DiD window and the HDB Jun 2022 - Jun 2025 RDiT window, plus each
   stated floor (100 transactions per group) screened against the measured
   group sizes. A screen says what a cohort looks like; it is not the estimator
   and not a finding about how the retired analysis assigned treatment.
4. **Identification audit** — estimand, treatment/control construction,
   assumptions, pretrends, concurrent policies, anticipation, placebos,
   robustness/bandwidth grid and multiplicity, each recorded absent or
   unmeasurable with its scan boundary.
5. **Absence scans** — a file-name scan over the data roots (every match
   listed with its count; `housing_policy_dates` matches zero files), a
   case-sensitive token scan over the documentation roots, and a Python-code
   scan (zero scan-eligible .py files carry DiD/RDiT tokens). Programme
   surfaces are excluded from the hash-pinned scans and the exclusions are
   disclosed here.
6. **The unlinked artefact** — `causal_did_analysis.png`, sha-pinned, listed in
   the frozen edition's own manifest, visually read by the producer. A manifest
   listing is an asset record, not a run record: the pixels adjudicate nothing
   about the two headline numbers, in either direction.
7. **The two withdrawals** — the CCR-vs-OCR DiD -$137,743 and the HDB RDiT
   +$13,118, withdrawn per the recorded D12/RF08 disposition (2026-11-18) as
   unreconstructable identification, with the reason. Not re-estimated here.
8. **Reconstruction requirements** — what would make the two numbers
   reconstructable (a dated policy artefact with a bandwidth rule and an
   estimator record), recorded as requirements, not a plan.

It never re-fits any model, never re-runs any estimator, never writes outside
`--output`, and never touches `data/pipeline/**` (read-only) or
`app/public/data/**` (read-only).

Usage:

    uv run python scripts/tools/causal_inference_evidence.py \\
        --output docs/implementation/artifacts/rs13-causal-inference-overview-evidence.json

    uv run python scripts/tools/causal_inference_evidence.py --check  # no drift
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

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
LEGACY_EDITION = (
    REPO_ROOT
    / "docs"
    / "analytics"
    / "editions"
    / "legacy"
    / "2026-11-12"
    / "causal-inference-overview.md"
)
LEGACY_LIVE_COPY = REPO_ROOT / "docs" / "analytics" / "causal-inference-overview.md"
LEGACY_MANIFEST = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "manifest.json"
)
POLICY_PLAN_DOC = REPO_ROOT / "docs" / "plans" / "2026-02-04-analyze-policy-impact.md"
DID_PNG_PUBLIC = REPO_ROOT / "app" / "public" / "data" / "analysis" / "causal_did_analysis.png"
DID_PNG_DIST = REPO_ROOT / "app" / "dist" / "data" / "analysis" / "causal_did_analysis.png"
EDITION_TEXT = (
    REPO_ROOT
    / "docs"
    / "analytics"
    / "editions"
    / "causal-inference-overview"
    / "2026-11-20"
    / "causal-inference-overview.md"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "artifacts"
    / "rs13-causal-inference-overview-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

# The token/code scans are hash-pinned, so the ledger is reproducible
# file-order-independently and cannot read itself.
SCAN_ROOTS = ("docs", "scripts", "src", "assets", "prompts", "app/src", ".claude/handoffs")
SCAN_SUFFIXES = (".md", ".py", ".ts", ".tsx")
# The exclusions are the programme's own surfaces, not evidence of the retired
# causal analysis: `docs/implementation/` holds the per-study evidence records,
# `scripts/tools/` holds the evidence producers themselves, and `prompts/` holds
# the handoffs and runbooks. Published edition texts are programme output too: a
# study signed after RS13 must not drift this ledger. The frozen legacy
# originals stay IN the scan, because the article's own method prose is what
# this audit audits.
EXCLUDED_SCAN_PREFIXES = (
    "docs/implementation/",
    "scripts/tools/",
    "prompts/",
    "app/src/components/studies/",
    "app/tests/",
)
EDITION_PREFIX = "docs/analytics/editions/"
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
# The two RF08 programme decision files are excluded for the RS10 round-19
# reason: they record verdicts in the programme's own vocabulary, and this
# study's gate vocabulary ("pretrend", "estimand", "anticipation", "bandwidth",
# "placebo") IS the register's vocabulary — recording an RS13 review row in
# either file must not move a pinned count. Every other programme record already
# lives under an excluded prefix. The register's RS13 gate text is quoted in the
# pack prose from the file directly, not via this scan.
EXCLUDED_SCAN_PATHS = (
    "scripts/tools/causal_inference_evidence.py",
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
    "docs/plans/2026-11-12-reporting-refresh-research-register.md",
    ".secrets.baseline",
)

# Tokens: matched case-sensitively when the token carries uppercase (so "DiD"
# cannot match the English word "did"), case-insensitively otherwise.
AUDIT_TOKENS = (
    "housing_policy_dates",
    "RDiT",
    "DiD",
    "difference-in-differences",
    "pretrend",
    "parallel trend",
    "Bala",
    "bandwidth",
    "estimand",
    "ABSD",
    "anticipation",
    "placebo",
    "multiple-testing",
    "137,743",
    "13,118",
)
CODE_TOKENS = ("DiD", "RDiT", "difference-in-differences")

# The file-name absence scan walks these roots and matches these substrings
# case-insensitively against file names only. .venv, node_modules, .git and
# __pycache__ are skipped and disclosed.
NAME_SCAN_ROOTS = ("data", "app/public/data", "app/dist/data")
NAME_SCAN_TOKENS = (
    "policy",
    "did",
    "rdit",
    "bala",
    "bandwidth",
    "pretrend",
    "placebo",
    "housing_policy_dates",
)
NAME_SCAN_SKIPPED_PREFIXES = (".git/", ".venv/", "node_modules/", "__pycache__/")

# The visual annotation record below is keyed to exactly these bytes; a
# different PNG fails the build rather than serving a stale visual read.
DID_PNG_SHA256 = "7f5732e6c77711e95278a7c38d2f9d5ea47c81bc542610b0e27eb79514a30177"  # pragma: allowlist secret — sha256 of the public asset app/public/data/analysis/causal_did_analysis.png (also printed in the frozen manifest), pinned so a changed PNG fails the build; not a credential

REGION_LABELS = ("Core Central Region", "Rest of Central Region", "Outside Central Region")

DEFINITION = (
    "An identification audit of the frozen policy-impact article, measured "
    "against this checkout. Every gate input is recorded in one of two states: "
    "ABSENT (the artefact that would carry it matches zero files in a stated "
    "scan) or UNMEASURABLE (the quantity needs a run or an artefact this "
    "checkout does not hold). The two headline numbers — the CCR-vs-OCR "
    "condominium DiD estimate of about -$137,743 and the HDB RDiT jump of about "
    "+$13,118 — are WITHDRAWN as unreconstructable identification per the "
    "recorded D12/RF08 disposition of 2026-11-18, and the reason is published "
    "with them. What is measured here is the frame the two cohorts would be "
    "drawn from (screend for size inside the measured cutoff), the shipped "
    "region labels' planning-area spans, and the absences. A screen is not a "
    "finding about origin: nothing here says how the retired analysis assigned "
    "treatment or produced its numbers, and no estimate is reconstructed. What "
    "WOULD make the two numbers reconstructable — a dated policy artefact with "
    "a bandwidth rule and an estimator record — is recorded as a requirement, "
    "not a plan."
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


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial.

    Primary basis: the private rows (`market_segment` non-null), the population
    both stated cohorts draw on, so the bound is identical across the studies.
    All-rows and HDB cross-checks are recorded beside it.
    """
    private = _select(frame, frame["market_segment"].notna())
    hdb = _select(frame, frame["property_type"] == "hdb")

    def measure(sub: pd.DataFrame) -> dict[str, Any]:
        counts = {str(k): int(v) for k, v in sub.groupby("month").size().items()}
        ordered = sorted(counts)
        terminal_month = ordered[-1]
        last_complete_month = ordered[-2]
        trailing_months = ordered[-13:-1]
        trailing = [counts[month] for month in trailing_months]
        trailing_median = float(np.median(trailing)) if trailing else 0.0
        ratio = counts[terminal_month] / trailing_median if trailing_median else None
        return {
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
        }

    private_measured = measure(private)
    all_measured = measure(frame)
    hdb_measured = measure(hdb)
    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact (the same rule RS03/RS04/"
            "RS05/RS09/RS10 shipped, computed on the private rows so the bound "
            "is identical across the studies)"
        ),
        "populationBasis": "private rows (market_segment non-null)",
        **private_measured,
        "allRowsCrossCheck": all_measured,
        "hdbRowsCrossCheck": hdb_measured,
        "frameFirstMonth": str(frame["month"].min()),
        "frameLastMonth": str(frame["month"].max()),
        "meaning": (
            "every row-level aggregation in this ledger - frame inventory, "
            "label spans, cohort screens, every count and share - stops at "
            "lastCompleteMonth; the only full-frame facts recorded are the "
            "parquet footer file facts (frameInventory.rows and "
            "frameInventory.columns), the monthSpans bounds that locate the "
            "terminal month, and this section's own measurement of that "
            "terminal month, which defines the bound"
        ),
    }


def frame_inventory(
    frame: pd.DataFrame, schema_names: list[str], last_complete: str
) -> dict[str, Any]:
    """What the frame holds inside the measured cutoff, with the four
    missingness states kept apart.

    Rule 8 (cutoff discipline): every row-level aggregation in this ledger
    stops at `lastCompleteMonth`, including this inventory's value counts.
    The full-frame facts that remain are file metadata (footer `rows` and
    `columns`), the `monthSpans` bounds that locate the terminal month, and
    the cutoff section's own measurement of that month.
    """
    bounded = _select(frame, frame["month"] <= last_complete)
    property_counts = {str(k): int(v) for k, v in bounded["property_type"].value_counts().items()}
    segment_counts = {str(k): int(v) for k, v in bounded["market_segment"].value_counts().items()}
    segment_nulls = int(bounded["market_segment"].isna().sum())
    region_counts = {
        ("(null)" if k is None or (isinstance(k, float) and np.isnan(k)) else str(k)): int(v)
        for k, v in bounded["region"].value_counts(dropna=False).items()
    }
    planning_nulls = int(bounded["planning_area"].isna().sum())
    null_area_types = pd.Series(bounded.loc[bounded["planning_area"].isna(), "property_type"])
    planning_nulls_by_type = {str(k): int(v) for k, v in null_area_types.value_counts().items()}
    ec = _select(bounded, bounded["is_ec"])
    ec_by_type = {str(k): int(v) for k, v in ec["property_type"].value_counts().items()}
    policy_tokens = [name for name in schema_names if "policy" in name.lower()]

    hdb = _select(frame, frame["property_type"] == "hdb")
    return {
        "rows": int(len(frame)),
        "columns": len(schema_names),
        "basis": (
            "every row-level value count in this section is computed on rows "
            "with month <= lastCompleteMonth (cutoff.meaning); `rows` and "
            "`columns` are parquet footer file facts; `monthSpans` are frame "
            "bounds that locate the terminal month the cutoff rule measures"
        ),
        "readBasis": (
            "row and column counts from the parquet footer metadata "
            "(pyarrow ParquetFile metadata), then the six named working columns "
            "this ledger reads (month, property_type, planning_area, region, "
            "market_segment, is_ec); no full-frame column sweep"
        ),
        "propertyTypes": property_counts,
        "ecFlag": {
            "column": "is_ec",
            "trueRows": int(len(ec)),
            "propertyTypesOfTrueRows": ec_by_type,
            "ecAsPropertyTypeValue": any("ec" == name.lower() for name in property_counts),
            "meaning": (
                "EC exists in the frame as a boolean flag on condominium rows, "
                "not as a property_type value; the frozen text's EC coverage can "
                "only be screened against the flag"
            ),
        },
        "marketSegment": {
            "valueCounts": segment_counts,
            "nonNullRows": int(bounded["market_segment"].notna().sum()),
            "nullRows": segment_nulls,
            "nullsEqualHdbRowCount": segment_nulls == property_counts.get("hdb"),
            "nonNullEqualsCondoRowCount": (
                int(bounded["market_segment"].notna().sum()) == property_counts.get("condo")
            ),
            "meaning": (
                "a region label populated only on the private rows; the null "
                "bucket is a null VALUE on present rows, not absent rows and not "
                "a stored zero"
            ),
        },
        "region": {"valueCounts": region_counts},
        "planningArea": {
            "distinctNonNullValues": int(bounded["planning_area"].nunique()),
            "nullRows": planning_nulls,
            "nullRowsByPropertyType": planning_nulls_by_type,
        },
        "monthSpans": {
            "meaning": (
                "frame bounds, not a cutoff-bounded aggregation: they locate "
                "the terminal month the cutoff rule measures; every row-level "
                "count in this ledger stops at lastCompleteMonth (cutoff.meaning)"
            ),
            "allRows": {"first": str(frame["month"].min()), "last": str(frame["month"].max())},
            "hdbRows": {"first": str(hdb["month"].min()), "last": str(hdb["month"].max())},
            "privateRows": {
                "first": str(frame[frame["market_segment"].notna()]["month"].min()),
                "last": str(frame[frame["market_segment"].notna()]["month"].max()),
            },
        },
        "missingnessStates": {
            "nullValue": {
                "marketSegmentNullRows": segment_nulls,
                "planningAreaNullRows": planning_nulls,
                "regionNullRows": region_counts.get("(null)", 0),
                "meaning": "present columns carrying null values on present rows",
            },
            "recordedZero": {
                "count": 0,
                "meaning": (
                    "no figure in this ledger is a stored zero read from a "
                    "source; every zero here (0 matches, 0 files) is a MEASURED "
                    "count of absence and is labelled as one"
                ),
            },
            "absentRow": {
                "housingPolicyDatesFileMatches": 0,
                "meaning": (
                    "the dated-policy artefact matches zero files in the name "
                    "scan (artefactNameScan), so there are no rows of it to "
                    "count — an absence of the file, not a zero-valued column "
                    "in it"
                ),
            },
            "absentColumn": {
                "framePolicyDateColumns": policy_tokens,
                "meaning": (
                    "the frame's 97-column schema holds no policy-date column "
                    "at all: the treatment date is not a column that is null, "
                    "it is absent from the schema"
                ),
            },
        },
    }


def segment_area_spans(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """The shipped region labels' planning-area spans, measured inside the
    cutoff.

    This says what the frame's `market_segment` labels look like. It does NOT
    say how the retired analysis assigned treatment: the assignment code is
    absent (identificationAudit.treatmentControlConstruction), and a label's
    measured span is a screen of the shipped column, not a reconstruction of
    the legacy mapping.
    """
    bounded = _select(frame, frame["month"] <= last_complete)
    private = _select(bounded, bounded["market_segment"].notna())
    areas_by_label: dict[str, set[str]] = {}
    rows_by_label: dict[str, int] = {}
    nulls_by_label: dict[str, int] = {}
    for label in REGION_LABELS:
        sub = _select(private, private["market_segment"] == label)
        rows_by_label[label] = int(len(sub))
        nulls_by_label[label] = int(sub["planning_area"].isna().sum())
        areas_by_label[label] = set(sub["planning_area"].dropna().unique().tolist())

    overlaps: dict[str, list[str]] = {}
    for label in REGION_LABELS:
        others = [name for name in REGION_LABELS if name != label]
        shared: set[str] = set()
        for other in others:
            shared |= areas_by_label[label] & areas_by_label[other]
        overlaps[label] = sorted(shared)
    return {
        "sourceColumn": "market_segment",
        "labels": {
            label: {
                "rows": rows_by_label[label],
                "distinctPlanningAreas": len(areas_by_label[label]),
                "planningAreas": sorted(areas_by_label[label]),
                "nullPlanningAreaRows": nulls_by_label[label],
                "planningAreasAlsoUnderAnotherLabel": overlaps[label],
            }
            for label in REGION_LABELS
        },
        "distinctPlanningAreasAnyLabel": len(
            set().union(*areas_by_label.values())  # type: ignore[arg-type]
        ),
        "labelsAreNotAPartitionOfPlanningAreas": any(overlaps[label] for label in REGION_LABELS),
        "meaning": (
            "the shipped labels' measured spans overlap (the same planning area "
            "appears under more than one label), so the labels are not a clean "
            "area partition inside the measured cutoff; every count here is "
            "computed on rows with month <= lastCompleteMonth (cutoff.meaning), "
            "and this screens the shipped column without reconstructing the "
            "retired analysis's treatment assignment, which is absent as code"
        ),
    }


def cohort_screens(frame: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """The two stated sample definitions, screened as cohort sizes inside the cutoff.

    A screen measures what a named cohort looks like. It is not the estimator,
    it re-runs nothing, and it is not evidence about how the retired analysis
    built its treatment and control groups.
    """
    condo = _select(frame, frame["property_type"] == "condo")
    did = _select(condo, condo["month"] <= last_complete)
    did_by_segment = {str(k): int(v) for k, v in did["market_segment"].value_counts().items()}
    did_ccr = int(did_by_segment.get("Core Central Region", 0))
    did_ocr = int(did_by_segment.get("Outside Central Region", 0))
    hdb = _select(frame, frame["property_type"] == "hdb")
    rdit = _select(hdb, (hdb["month"] >= "2022-06") & (hdb["month"] <= "2025-06"))
    rdit_counts = {str(k): int(v) for k, v in rdit.groupby("month").size().items()}
    rdit_min_month = min(rdit_counts, key=lambda m: (rdit_counts[m], m))
    rdit_max_month = max(rdit_counts, key=lambda m: (rdit_counts[m], m))
    rdit_first, rdit_last = sorted(rdit_counts)[0], sorted(rdit_counts)[-1]
    rdit_first_year, rdit_first_month = int(rdit_first[:4]), int(rdit_first[5:7])
    rdit_last_year, rdit_last_month = int(rdit_last[:4]), int(rdit_last[5:7])
    calendar_months = (
        (rdit_last_year - rdit_first_year) * 12 + (rdit_last_month - rdit_first_month) + 1
    )
    return {
        "diD": {
            "statedDefinition": (
                "frozen text, technical appendix: Condominium transactions post-2021, CCR vs OCR"
            ),
            "windowMonths": {"first": "2021-01", "last": last_complete},
            "rows": int(len(did)),
            "monthsPresent": int(did["month"].nunique()),
            "rowsByShippedLabel": did_by_segment,
            "statedTreatmentRows": did_ccr,
            "statedControlRows": did_ocr,
            "statedGroupFloor": 100,
            "floorSatisfiedByStatedGroups": did_ccr >= 100 and did_ocr >= 100,
            "meaning": (
                "a screen of cohort sizes against the stated floor, inside the "
                "measured cutoff. The condominium source starts 2021-01, so "
                "'post-2021' is the whole private panel up to the cutoff. No "
                "regression is run and no treatment assignment is reconstructed"
            ),
        },
        "rdit": {
            "statedDefinition": (
                "frozen text, technical appendix: HDB transactions, Jun 2022 - "
                "Jun 2025 (18 months before/after policy)"
            ),
            "windowMonths": {"first": rdit_first, "last": rdit_last},
            "rows": int(len(rdit)),
            "monthsPresent": int(rdit["month"].nunique()),
            "calendarMonthsInWindow": calendar_months,
            "monthsPresentEqualsCalendarMonths": int(rdit["month"].nunique()) == calendar_months,
            "fullyBeforeCutoff": rdit_last < last_complete,
            "minMonthTransactions": rdit_counts[rdit_min_month],
            "minMonth": rdit_min_month,
            "maxMonthTransactions": rdit_counts[rdit_max_month],
            "maxMonth": rdit_max_month,
            "statedGroupFloor": 100,
            "floorSatisfiedByEveryWindowMonth": all(v >= 100 for v in rdit_counts.values()),
            "meaning": (
                "a screen of the stated window's row and month coverage. The "
                "event date the window is anchored on is prose, not a dated "
                "artefact (identificationAudit.concurrentPolicies), so the "
                "window itself is screened, not verified"
            ),
        },
        "statedWindows": {
            "legacyDataPeriod": {
                "statedPeriod": "2017-2026",
                "frameFirstMonth": str(frame["month"].min()),
                "frameLastMonth": str(frame["month"].max()),
                "privateRowsFirstMonth": "2021-01",
                "meaning": (
                    "the stated data period is the retired analysis's own "
                    "filter, recorded in prose only; the frame spans wider than "
                    "it and the private rows start later than it. The filter is "
                    "not recorded as an artefact and is not reproduced here"
                ),
            },
        },
        "legacyInputPath": {
            "claimedPath": "data/parquets/L3/housing_unified.parquet",
            "pathExistsInCheckout": (
                REPO_ROOT / "data" / "parquets" / "L3" / "housing_unified.parquet"
            ).is_file(),
            "shippedUnifiedDataset": "data/pipeline/04_platinum/unified_dataset.parquet",
            "meaning": (
                "the frozen text names a primary input path this checkout does "
                "not hold; the shipped platinum dataset is at a different path "
                "and no artefact ties the two"
            ),
        },
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


def scan_declaration() -> dict[str, Any]:
    return {
        "roots": list(SCAN_ROOTS),
        "suffixes": list(SCAN_SUFFIXES),
        "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
        "editionRule": (
            "docs/analytics/editions/ excludes everything except editions/legacy/, "
            "so later signed editions cannot drift this ledger; the frozen legacy "
            "originals stay in the scan"
        ),
        "excludedPaths": {
            path: reason
            for path, reason in (
                (
                    "scripts/tools/causal_inference_evidence.py",
                    "this producer quotes the tokens it searches for; scanning itself would make the ledger its own evidence",
                ),
                (
                    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
                    "the D12 decision register records verdicts in the programme's vocabulary, which overlaps this study's gate vocabulary",
                ),
                (
                    "docs/plans/2026-11-12-reporting-refresh-research-register.md",
                    "the research register holds the gate text itself (pretrend, estimand, anticipation, bandwidth, placebo); a future register amendment must not move a pinned count (the RS10 round-19 lesson)",
                ),
                (
                    ".secrets.baseline",
                    "secret-scanner baseline is security tooling, not study evidence",
                ),
            )
        },
        "meaning": (
            "the token and code scans are hash-pinned over these declarations; "
            "app/src/components/studies/ (edition registry/pages) and app/tests/ (fixtures) are programme outputs and excluded; .secrets.baseline and docs/plans/2026-11-12-reporting-refresh-decisions.md (D12 register) are excluded explicitly; a count can only move if a scanned file changes"
        ),
    }


def _token_matches(token: str, path: Path) -> list[dict[str, Any]]:
    case_sensitive = token != token.lower()
    needle = token if case_sensitive else token.lower()
    matches: list[dict[str, Any]] = []
    for number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        haystack = line if case_sensitive else line.lower()
        if needle in haystack:
            matches.append({"path": _relative(path), "line": number, "quote": line.strip()[:160]})
    return matches


def token_scan(paths: list[Path]) -> dict[str, Any]:
    """Where each audit token appears: per-token counts, a complete per-file
    occurrence breakdown (uncapped, sorted by path), and up to eight
    first-match line samples."""
    hits: dict[str, Any] = {}
    for token in AUDIT_TOKENS:
        matches: list[dict[str, Any]] = []
        for path in paths:
            matches.extend(_token_matches(token, path))
        matches.sort(key=lambda m: (m["path"], m["line"]))
        per_file: dict[str, int] = {}
        for match in matches:
            per_file[match["path"]] = per_file.get(match["path"], 0) + 1
        hits[token] = {
            "caseSensitive": token != token.lower(),
            "occurrences": len(matches),
            "files": len({match["path"] for match in matches}),
            "firstMatches": matches[:8],
            "perFile": [{"path": path, "occurrences": per_file[path]} for path in sorted(per_file)],
        }
    return hits


def code_scan(paths: list[Path]) -> dict[str, Any]:
    """Scan-eligible Python files carrying DiD/RDiT tokens: the code absence."""
    python_files = [path for path in paths if path.suffix == ".py"]
    matching: dict[str, list[dict[str, Any]]] = {}
    for token in CODE_TOKENS:
        token_matches: list[dict[str, Any]] = []
        for path in python_files:
            token_matches.extend(_token_matches(token, path))
        matching[token] = token_matches
    files_with_hits = sorted({match["path"] for hits_ in matching.values() for match in hits_})
    return {
        "pythonFilesScanned": len(python_files),
        "tokens": list(CODE_TOKENS),
        "pythonFilesWithTokenMatches": files_with_hits,
        "diDRditPythonFileCount": len(files_with_hits),
        "meaning": (
            "a count of scan-eligible .py files whose text carries DiD/RDiT "
            "tokens, under the declared roots and exclusions. Zero here "
            "supports the frozen text's own retirement sentence for THIS "
            "checkout's supported surface; it is not a claim about any other "
            "machine, history or branch"
        ),
    }


def artefact_name_scan() -> dict[str, Any]:
    """File-NAME scan over the data roots: what the dated-policy artefact scan covers."""
    matches: dict[str, list[str]] = {token: [] for token in NAME_SCAN_TOKENS}
    files_walked = 0
    for root in NAME_SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            relative = _relative(path)
            if any(relative.startswith(prefix) for prefix in NAME_SCAN_SKIPPED_PREFIXES):
                continue
            files_walked += 1
            name = path.name.lower()
            for token in NAME_SCAN_TOKENS:
                if token in name:
                    matches[token].append(relative)
    return {
        "roots": list(NAME_SCAN_ROOTS),
        "matchBasis": "case-insensitive substring match on file NAMES only; contents are not read",
        "skippedPrefixes": list(NAME_SCAN_SKIPPED_PREFIXES),
        "tokens": list(NAME_SCAN_TOKENS),
        "filesWalked": files_walked,
        "matches": {
            token: {"count": len(files), "files": sorted(files)} for token, files in matches.items()
        },
        "housingPolicyDatesFileMatches": len(matches["housing_policy_dates"]),
        "meaning": (
            "the dated-policy artefact absence: housing_policy_dates matches "
            "zero file names across the three data roots. The two 'did' matches "
            "are the unlinked plot PNG and its build copy (unlinkedArtefact). "
            "This scan bounds what it claims: names in these roots, not file "
            "contents, not other roots, not history"
        ),
    }


def unlinked_artefact() -> dict[str, Any]:
    """The one causal artefact in the checkout, and what linking it would mean."""
    public_sha = sha256_of(DID_PNG_PUBLIC)
    if public_sha != DID_PNG_SHA256:
        raise SystemExit(
            f"causal_did_analysis.png sha256 changed ({public_sha}); the visual "
            "annotation record is keyed to the old bytes and must be re-read "
            "by a human before this ledger can ship"
        )
    dist_sha = sha256_of(DID_PNG_DIST)
    manifest = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    entry = next(
        (
            item
            for item in manifest.get("assets", [])
            if item.get("path", "").endswith("causal_did_analysis.png")
        ),
        None,
    )
    manifest_pin = (
        {
            "manifestPath": _relative(LEGACY_MANIFEST),
            "entryPresent": True,
            "pinnedSha256": entry.get("sha256"),
            "pinnedBytes": entry.get("bytes"),
            "mutable": entry.get("mutable"),
            "pinMatchesMeasuredBytes": bool(entry) and entry.get("sha256") == public_sha,
        }
        if entry
        else {"manifestPath": _relative(LEGACY_MANIFEST), "entryPresent": False}
    )
    return {
        "path": _relative(DID_PNG_PUBLIC),
        "buildCopyPath": _relative(DID_PNG_DIST),
        "sha256": public_sha,
        "bytes": int(DID_PNG_PUBLIC.stat().st_size),
        "copiesByteIdentical": public_sha == dist_sha,
        "manifestPin": manifest_pin,
        "visibleAnnotations": {
            "method": (
                "HUMAN VISUAL READ of the sha-pinned PNG by the producer, "
                "recorded because the pixels are not machine-read. The hash "
                "above pins exactly which image was read; the values below are "
                "what it visibly prints, and are not a re-derived score"
            ),
            "title": ("DiD Analysis: Sep 2022 ABSD Changes / Condominium CCR vs OCR"),
            "leftPanel": (
                "bar chart of median price by pre/post period, CCR labelled "
                "Treatment and OCR labelled Control, annotated 'DiD Estimate: "
                "~-$138K (p = 0.017 **)'"
            ),
            "rightPanel": ("'Price Change (Pre -> Post)': CCR +15.2%, OCR +22.2%"),
            "notPrinted": (
                "no sample windows, no n, no bandwidth and no run identifier "
                "appear anywhere on the plot"
            ),
        },
        "linkage": {
            "runLinkage": (
                "nothing in the checkout links the pixels to the runs behind the "
                "two headline numbers: no run id, no estimator output and no "
                "code accompanies it. The frozen manifest lists the file — that "
                "is an asset listing, not a run record"
            ),
            "adjudication": (
                "an unlinked artefact adjudicates nothing, symmetrically: it is "
                "evidence neither FOR nor AGAINST the withdrawn estimates. The "
                "plot's printed estimate (~-$138K) resembles the withdrawn "
                "figure's rounding, and the resemblance establishes nothing "
                "about either"
            ),
        },
    }


def withdrawals() -> dict[str, Any]:
    """The two headline numbers, withdrawn per the recorded D12 disposition."""
    reason = (
        "D12 / RF08, 2026-11-18, repo owner (release authority): 'RS13 has no "
        "dated housing_policy_dates artefact in the checkout, so its two "
        "headline causal numbers (the CCR-vs-OCR DiD estimate and the HDB RDiT "
        "jump) are withdrawn as unreconstructable identification, and the "
        "edition publishes that absence with the reason. The withdrawal is a "
        "finding, not a programme failure.'"
    )
    return {
        "decisionSource": {
            "register": "docs/plans/2026-11-12-reporting-refresh-decisions.md",
            "row": "D12 / RF08 — RS06/RS07/RS13 disposition when a gate input is absent",
            "decidedOn": "2026-11-18",
            "quotedReason": reason,
            "registerExcludedFromScan": True,
        },
        "condoDid": {
            "claimIds": ["C03", "C27"],
            "statedValue": "-$137,743",
            "statedUnit": (
                "SGD, relative effect, CCR condominiums vs OCR condominiums, "
                "Sep 2022 ABSD event — as stated in the frozen text; the unit "
                "and window are the text's own and are not independently "
                "verifiable here"
            ),
            "disposition": "withdrawn",
            "withdrawnAs": "unreconstructable identification",
            "reconstructedHere": False,
            "dependentInterpretations": {
                "claimIds": ["C04", "C33"],
                "meaning": (
                    "'Prime condos were meaningfully suppressed' and the "
                    "conclusion's 'measurable price suppression (~$138K)' "
                    "restate the withdrawn estimate and are withdrawn with it"
                ),
            },
        },
        "hdbRdit": {
            "claimIds": ["C05", "C28"],
            "statedValue": "+$13,118",
            "statedUnit": (
                "SGD, immediate level jump, HDB, Dec 2023 event — as stated in "
                "the frozen text; the unit and window are the text's own and "
                "are not independently verifiable here"
            ),
            "disposition": "withdrawn",
            "withdrawnAs": "unreconstructable identification",
            "reconstructedHere": False,
            "dependentInterpretations": {
                "claimIds": ["C06", "C09", "C34"],
                "meaning": (
                    "'HDB did not show the intended cooling response', the "
                    "takeaway's 'moved higher after a major policy event' and "
                    "the conclusion's 'upward movement (+$13K)' restate the "
                    "withdrawn jump and are withdrawn with it"
                ),
            },
        },
        "conclusionRounding": {
            "claimIds": ["C33", "C34"],
            "meaning": (
                "the conclusion's (~$138K) and (+$13K) are the frozen text's "
                "own roundings of the two withdrawn numbers; they are "
                "withdrawn with them and no rounding residual is computed here"
            ),
        },
    }


def reconstruction_requirements() -> dict[str, Any]:
    """What WOULD make the withdrawn numbers reconstructable. A requirement, not a plan."""
    return {
        "datedPolicyArtefact": {
            "requirement": (
                "a machine-readable dated policy artefact (the frozen text's "
                "own housing_policy_dates name or equivalent) whose rows pin "
                "event identifier, event date, and the segment/population "
                "scope each event applies to"
            ),
            "presentInCheckout": False,
            "scan": "artefactNameScan.housingPolicyDatesFileMatches",
        },
        "bandwidthRule": {
            "requirement": (
                "the estimator's bandwidth rule recorded with that artefact or "
                "with the code: the default bandwidth and the robustness grid "
                "as executed, not as prose"
            ),
            "presentInCheckout": False,
            "scan": "identificationAudit.robustness",
        },
        "estimatorRecord": {
            "requirement": (
                "the DiD/RDiT code, or a stored estimator output carrying its "
                "sample windows and group sizes, so the specification prose in "
                "the frozen text could be tied to an executed run"
            ),
            "presentInCheckout": False,
            "scan": "codeScan.diDRditPythonFileCount",
        },
        "pretrendAndPlaceboRecord": {
            "requirement": (
                "stored pretrend and placebo outputs (or the code that "
                "produced them) for the same windows, so the checks the gate "
                "names could be re-run rather than asserted"
            ),
            "presentInCheckout": False,
            "scan": "identificationAudit.pretrends",
        },
        "status": (
            "requirements, not a plan: this pack records what a reconstruction "
            "would need to exist in the checkout; it does not schedule one, "
            "and no estimate is reconstructed here"
        ),
    }


def identification_audit(tokens: dict[str, Any]) -> dict[str, Any]:
    """Each gate clause, recorded absent or unmeasurable with its scan boundary."""

    def boundary(token_list: list[str]) -> dict[str, Any]:
        return {
            "tokenScan": {
                token: {
                    "occurrences": tokens[token]["occurrences"],
                    "files": tokens[token]["files"],
                    "perFile": tokens[token]["perFile"],
                }
                for token in token_list
            },
            "scanBoundary": (
                "token scan over the declared documentation roots with the "
                "programme surfaces excluded (scanDeclaration); the token "
                "counts are over that bounded set and claim nothing beyond it"
            ),
        }

    return {
        "estimand": {
            "status": "unmeasurable",
            "specificationProse": (
                "the only estimand-shaped record is the frozen text's own "
                "formula prose: 'price ~ treatment + post + treatment × post' "
                "for the DiD and the jump/kink formulas for the RDiT. No "
                "estimand statement, estimand token or estimator output "
                "exists outside that prose"
            ),
            **boundary(["estimand"]),
        },
        "treatmentControlConstruction": {
            "status": "unmeasurable",
            "specificationProse": (
                "the frozen text states treatment = CCR condos, control = OCR "
                "condos, and a CCR/RCR/OCR planning-area classification. No "
                "scan-eligible .py file carries the DiD/RDiT tokens "
                "(codeScan.diDRditPythonFileCount) - a token measure that "
                "does not search for assignment or run-linkage logic, so "
                "whether any assignment code exists outside the scan's "
                "boundary is unmeasurable; the shipped frame's region labels "
                "are screens, not the assignment "
                "(cohortScreens.segmentAreaSpans)"
            ),
            "rditRunningVariable": (
                "the frozen text's running-variable prose ('months since "
                "policy') cannot be constructed without a dated event "
                "artefact, which matches zero files"
            ),
            **boundary(["DiD", "RDiT", "difference-in-differences"]),
        },
        "assumptions": {
            "status": "unmeasurable",
            "recordedInLegacy": (
                "the frozen text's limitations sentence records two "
                "assumptions itself: DiD comparability of CCR and OCR condo "
                "segments, and no confounding events at the RDiT cutoff. Both "
                "are prose acknowledgments; nothing in the checkout tests them"
            ),
            **boundary(["parallel trend"]),
        },
        "pretrends": {
            "status": "unmeasurable",
            "meaning": (
                "no pretrend test output and no parallel-trends artefact "
                "exists in the scan; the token appears nowhere outside the "
                "programme's own register vocabulary"
            ),
            **boundary(["pretrend", "parallel trend"]),
        },
        "concurrentPolicies": {
            "status": "unmeasurable",
            "nearestRecord": {
                "path": "docs/plans/2026-02-04-analyze-policy-impact.md",
                "sha256": sha256_of(POLICY_PLAN_DOC),
                "bytes": int(POLICY_PLAN_DOC.stat().st_size),
                "whatItHolds": (
                    "a prose policy-event timeline (April 2023, September "
                    "2023, December 2023) in a February 2026 investigation "
                    "document, plus an explicit 'Traditional DiD not "
                    "applicable to HDB' limitation. It is prose, not a dated "
                    "artefact, it names no September 2022 event, and nothing "
                    "links it to the retired analysis"
                ),
                "whatItDoesNotDo": (
                    "it cannot pin an event date, cannot enumerate concurrent "
                    "policies, and adjudicates nothing about the frozen "
                    "text's event dating in either direction"
                ),
            },
            **boundary(["ABSD", "housing_policy_dates"]),
        },
        "anticipation": {
            "status": "unmeasurable",
            "meaning": (
                "no anticipation window is recorded anywhere; the token "
                "appears only in the programme's own register vocabulary, and "
                "an anticipation check needs the dated events anyway"
            ),
            **boundary(["anticipation"]),
        },
        "placebos": {
            "status": "unmeasurable",
            "meaning": (
                "the placebo token matches only the school-quality study's "
                "own surfaces and the programme register — a different "
                "study's RDD placebo, not a policy-study placebo. The token "
                "scan is a text measure over the declared suffixes and the "
                "filename scan (artefactNameScan.placebo) covers data-root "
                "file names: together they find no policy-study placebo "
                "surface; neither is an inventory of stored output files in "
                "other formats"
            ),
            **boundary(["placebo"]),
        },
        "robustness": {
            "status": "unmeasurable",
            "statedGrid": (
                "frozen text prose only: ±6 months default, robustness tested "
                "at 3, 6, 9, 12 months. Within the bounded scans - the token "
                "scan over the declared suffixes and the filename scan over "
                "the data roots (artefactNameScan.bandwidth) - no bandwidth-"
                "grid output surface exists; these scans are not an inventory "
                "of stored output files in other formats. The bandwidth token "
                "matches school-quality and edition surfaces, not a "
                "policy-study artefact"
            ),
            **boundary(["bandwidth"]),
        },
        "multiplicity": {
            "status": "unmeasurable",
            "meaning": (
                "no multiple-testing policy is recorded for this study; the "
                "multiple-testing token matches the school-quality register "
                "row, which governs a different study"
            ),
            **boundary(["multiple-testing"]),
        },
    }


def lease_mispricing(tokens: dict[str, Any], name_scan: dict[str, Any]) -> dict[str, Any]:
    """The lease-mispricing basis: the Bala schedule is absent as data."""
    return {
        "balaSchedule": {
            "status": "absent",
            "meaning": (
                "the theoretical schedule the frozen text compares against "
                "exists as prose only. No data artefact named Bala matches in "
                "the data roots (artefactNameScan.bala), and the token's "
                "documentation matches are prose references, not the schedule"
            ),
            "fileNameMatches": name_scan["matches"]["bala"]["count"],
            "tokenScan": {
                "occurrences": tokens["Bala"]["occurrences"],
                "files": tokens["Bala"]["files"],
            },
        },
        "deviationThreshold": {
            "statedThreshold": "≥5% deviation flagged — frozen text prose only",
            "status": "not-reproducible",
            "meaning": (
                "the threshold is a rule for flagging deviations; with no "
                "schedule and no stored deviation output, no deviation was "
                "recomputed and none is reported here"
            ),
        },
        "bands": {
            "band3050": {
                "statedBand": "30-50 years",
                "status": "not-reproducible",
                "meaning": "the band's direction claim ('richly priced') has no stored output behind it in this checkout",
            },
            "band8084": {
                "statedBand": "80-84 years",
                "status": "not-reproducible",
                "meaning": "the band's direction claim ('mild undervaluation') has no stored output behind it in this checkout",
            },
            "band9798": {
                "statedBand": "97-98 years",
                "status": "not-reproducible",
                "meaning": "the band's direction claim ('large discount') has no stored output behind it in this checkout",
            },
        },
        "meaning": (
            "the lease claims are recorded as not-reproducible, not as false: "
            "the checkout cannot recompute them, and nothing here measures "
            "lease pricing against any schedule"
        ),
    }


def not_measurable(
    audit: dict[str, Any], name_scan: dict[str, Any], code: dict[str, Any]
) -> dict[str, Any]:
    """The rollup of what this pack does not establish."""
    return {
        "theEstimand": audit["estimand"]["status"],
        "treatmentAssignment": audit["treatmentControlConstruction"]["status"],
        "pretrendTests": audit["pretrends"]["status"],
        "concurrentPolicyConfounds": audit["concurrentPolicies"]["status"],
        "anticipation": audit["anticipation"]["status"],
        "placebos": audit["placebos"]["status"],
        "bandwidthGridOutputs": audit["robustness"]["status"],
        "multiplicity": audit["multiplicity"]["status"],
        "datedPolicyArtefactFileMatches": name_scan["housingPolicyDatesFileMatches"],
        "didRditPythonFiles": code["diDRditPythonFileCount"],
        "theTwoHeadlineNumbers": (
            "withdrawn (withdrawals.condoDid, withdrawals.hdbRdit); not "
            "re-estimated, not bounded, not replaced"
        ),
        "meaning": (
            "each entry above is a statement about THIS checkout under the "
            "stated scans; none is a claim that the retired analysis did or "
            "did not do these things"
        ),
    }


LEGACY_CLAIMS: tuple[dict[str, str], ...] = (
    {
        "id": "C01",
        "phrase": "Data Period**: 2017-2026",
        "status": "not-reproducible",
        "ledgerKey": "cohortScreens.statedWindows.legacyDataPeriod",
        "note": (
            "the stated period is the retired analysis's own filter, recorded "
            "in prose only; the frame spans 1990-01 to 2026-11 and the private "
            "rows start 2021-01, so the filter is neither reproduced nor "
            "refuted here (cohortScreens.statedWindows.legacyDataPeriod)"
        ),
    },
    {
        "id": "C02",
        "phrase": "Coverage**: HDB, condominium, and EC market dynamics",
        "status": "re-measured",
        "ledgerKey": "frameInventory.propertyTypes",
        "note": (
            "screened against the frame: property_type holds exactly two "
            "values, hdb (989,865 rows) and condo (245,234 rows) inside the "
            "measured cutoff; EC exists only as the is_ec flag on 30,385 "
            "condominium rows "
            "(frameInventory.ecFlag), not as a property_type value"
        ),
    },
    {
        "id": "C03",
        "phrase": "about -$137,743 relative effect",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.condoDid",
        "note": (
            "withdrawn per the recorded D12/RF08 disposition of 2026-11-18 as "
            "unreconstructable identification; no dated policy artefact, no "
            "estimator record (withdrawals.condoDid)"
        ),
    },
    {
        "id": "C04",
        "phrase": "Prime condos were meaningfully suppressed",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.condoDid.dependentInterpretations",
        "note": (
            "an interpretation cell of the same table row as C03; it restates "
            "the withdrawn estimate and is withdrawn with it "
            "(withdrawals.condoDid.dependentInterpretations)"
        ),
    },
    {
        "id": "C05",
        "phrase": "about +$13,118 immediate jump",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.hdbRdit",
        "note": (
            "withdrawn per the recorded D12/RF08 disposition of 2026-11-18 as "
            "unreconstructable identification (withdrawals.hdbRdit)"
        ),
    },
    {
        "id": "C06",
        "phrase": "HDB did not show the intended cooling response",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.hdbRdit.dependentInterpretations",
        "note": (
            "the interpretation cell of the same table row as C05; withdrawn "
            "with it (withdrawals.hdbRdit.dependentInterpretations)"
        ),
    },
    {
        "id": "C07",
        "phrase": "Sep 2022 ABSD changes",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.concurrentPolicies.nearestRecord",
        "note": (
            "the event date exists as prose in the frozen text and as ABSD "
            "token matches elsewhere; no dated artefact pins it, and the "
            "checkout's nearest prose timeline (the February 2026 plan doc) "
            "names no September 2022 event. Prose cannot pin a date in either "
            "direction (identificationAudit.concurrentPolicies.nearestRecord)"
        ),
    },
    {
        "id": "C08",
        "phrase": "Dec 2023 cooling measures",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.concurrentPolicies.nearestRecord",
        "note": (
            "the nearest prose timeline does name a December 2023 package, "
            "but it is prose in an unlinked document, not a dated artefact; "
            "it cannot pin the date and cannot enumerate concurrent policies "
            "(identificationAudit.concurrentPolicies.nearestRecord)"
        ),
    },
    {
        "id": "C09",
        "phrase": "HDB prices remained resilient and in this sample even moved higher after a major policy event",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.hdbRdit.dependentInterpretations",
        "note": (
            "the takeaway restates the withdrawn RDiT jump's direction; "
            "withdrawn with it (withdrawals.hdbRdit.dependentInterpretations)"
        ),
    },
    {
        "id": "C10",
        "phrase": "Market appears richly priced relative to theory",
        "status": "not-reproducible",
        "ledgerKey": "leaseMispricing.bands.band3050",
        "note": (
            "the 30-50 year band's direction claim; the Bala schedule and any "
            "deviation output are absent from this checkout "
            "(leaseMispricing.bands.band3050)"
        ),
    },
    {
        "id": "C11",
        "phrase": "Mild undervaluation in some cases",
        "status": "not-reproducible",
        "ledgerKey": "leaseMispricing.bands.band8084",
        "note": (
            "the 80-84 year band's direction claim; underspecified (which "
            "cases, which window) as well as unbacked by stored output "
            "(leaseMispricing.bands.band8084)"
        ),
    },
    {
        "id": "C12",
        "phrase": "Large discount relative to theoretical schedule",
        "status": "not-reproducible",
        "ledgerKey": "leaseMispricing.bands.band9798",
        "note": (
            "the 97-98 year band's direction claim; no schedule, no stored "
            "deviation output (leaseMispricing.bands.band9798)"
        ),
    },
    {
        "id": "C13",
        "phrase": "Coverage**: 2017-2026, split by property type (Condominium, HDB)",
        "status": "not-reproducible",
        "ledgerKey": "cohortScreens.statedWindows.legacyDataPeriod",
        "note": (
            "the appendix restates the header's period claim with the two "
            "named property types; the same disposition as C01 applies "
            "(cohortScreens.statedWindows.legacyDataPeriod)"
        ),
    },
    {
        "id": "C14",
        "phrase": "Condominium transactions post-2021, CCR vs OCR",
        "status": "re-measured",
        "ledgerKey": "cohortScreens.diD",
        "note": (
            "screened as a cohort size inside the measured cutoff: 245,234 "
            "condominium rows across 70 months to 2026-10, 38,653 under the "
            "CCR label and 132,620 under the OCR label. A screen of the named "
            "population, not the estimator (cohortScreens.diD)"
        ),
    },
    {
        "id": "C15",
        "phrase": "HDB transactions, Jun 2022 - Jun 2025 (18 months before/after policy)",
        "status": "re-measured",
        "ledgerKey": "cohortScreens.rdit",
        "note": (
            "screened as a cohort: 82,417 HDB rows across 37 months, every "
            "month before the cutoff. The window's anchor date is prose, not "
            "a dated artefact, so the window is screened, not verified "
            "(cohortScreens.rdit)"
        ),
    },
    {
        "id": "C16",
        "phrase": "CCR (10 planning areas",
        "status": "re-measured",
        "ledgerKey": "cohortScreens.segmentAreaSpans.labels.Core Central Region",
        "note": (
            "the shipped CCR label spans 15 distinct planning areas (one row "
            "with null area), not the claimed 10, and CCR areas also appear "
            "under other labels. This screens the shipped column; it does not "
            "reconstruct how the retired analysis classified areas "
            "(cohortScreens.segmentAreaSpans)"
        ),
    },
    {
        "id": "C17",
        "phrase": "RCR (12 planning areas",
        "status": "re-measured",
        "ledgerKey": "cohortScreens.segmentAreaSpans.labels.Rest of Central Region",
        "note": (
            "the shipped RCR label spans 19 distinct planning areas, not the "
            "claimed 12, with overlap into other labels; same screen "
            "semantics as C16 (cohortScreens.segmentAreaSpans)"
        ),
    },
    {
        "id": "C18",
        "phrase": "OCR (remainder)",
        "status": "re-measured",
        "ledgerKey": "cohortScreens.segmentAreaSpans.labels.Outside Central Region",
        "note": (
            "the shipped OCR label spans 28 distinct planning areas; "
            "'remainder' is not a clean partition in the shipped frame "
            "because areas overlap across labels; same screen semantics as "
            "C16 (cohortScreens.segmentAreaSpans)"
        ),
    },
    {
        "id": "C19",
        "phrase": "Sep 2022 ABSD changes for foreigners",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.concurrentPolicies.nearestRecord",
        "note": (
            "the appendix adds an eligibility dimension ('for foreigners') "
            "that no artefact records; the same absence as C07 "
            "(identificationAudit.concurrentPolicies.nearestRecord)"
        ),
    },
    {
        "id": "C20",
        "phrase": "Regression: `price ~ treatment + post + treatment × post`",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.estimand.specificationProse",
        "note": (
            "the DiD specification exists only as this prose formula; no code "
            "or output executes or stores it "
            "(identificationAudit.estimand.specificationProse)"
        ),
    },
    {
        "id": "C21",
        "phrase": "Minimum 100 transactions per group",
        "status": "re-measured",
        "ledgerKey": "cohortScreens.diD",
        "note": (
            "screened: the stated groups' measured sizes inside the cutoff "
            "(38,653 CCR-label and 132,620 OCR-label rows) exceed the stated "
            "floor. This screens cohort sizes against a stated rule; it does "
            "not run the regression the rule governs (cohortScreens.diD)"
        ),
    },
    {
        "id": "C22",
        "phrase": "Running variable: months since policy (negative = before, positive = after)",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.treatmentControlConstruction.rditRunningVariable",
        "note": (
            "the running variable needs a dated event to count months from; "
            "the dated artefact matches zero files "
            "(identificationAudit.treatmentControlConstruction.rditRunningVariable)"
        ),
    },
    {
        "id": "C23",
        "phrase": "Jump test: `price ~ post`; Kink test: `price ~ months_since + post + post × time`",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.estimand.specificationProse",
        "note": (
            "the RDiT test specifications exist only as prose formulas; no "
            "code or output executes or stores them "
            "(identificationAudit.estimand.specificationProse)"
        ),
    },
    {
        "id": "C24",
        "phrase": "Bandwidth: ±6 months (default), robustness tested at 3, 6, 9, 12 months",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.robustness.statedGrid",
        "note": (
            "the grid is stated in prose; no stored grid output exists in the "
            "scan (identificationAudit.robustness.statedGrid)"
        ),
    },
    {
        "id": "C25",
        "phrase": "Minimum 100 transactions for analysis",
        "status": "re-measured",
        "ledgerKey": "cohortScreens.rdit",
        "note": (
            "screened: every one of the stated window's 37 measured months "
            "holds at least 1,837 HDB rows, above the stated floor; a screen "
            "of window months, not the estimator (cohortScreens.rdit)"
        ),
    },
    {
        "id": "C26",
        "phrase": "theoretical Bala depreciation schedule, ≥5% deviation flagged",
        "status": "not-reproducible",
        "ledgerKey": "leaseMispricing.balaSchedule",
        "note": (
            "the schedule the threshold compares against is absent as data "
            "(zero Bala-named files in the data roots); the threshold is "
            "prose only (leaseMispricing.balaSchedule)"
        ),
    },
    {
        "id": "C27",
        "phrase": "~-$137,743 relative effect (CCR vs OCR, Sep 2022 ABSD)",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.condoDid",
        "note": (
            "the technical-findings restatement of C03; withdrawn with it (withdrawals.condoDid)"
        ),
    },
    {
        "id": "C28",
        "phrase": "~+$13,118 immediate jump after Dec 2023 measures",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.hdbRdit",
        "note": (
            "the technical-findings restatement of C05; withdrawn with it (withdrawals.hdbRdit)"
        ),
    },
    {
        "id": "C29",
        "phrase": "market appears richly priced relative to Bala theory",
        "status": "not-reproducible",
        "ledgerKey": "leaseMispricing.bands.band3050",
        "note": (
            "the findings bullet restating C10; same disposition (leaseMispricing.bands.band3050)"
        ),
    },
    {
        "id": "C30",
        "phrase": "mild undervaluation in some cases",
        "status": "not-reproducible",
        "ledgerKey": "leaseMispricing.bands.band8084",
        "note": (
            "the findings bullet restating C11; same disposition (leaseMispricing.bands.band8084)"
        ),
    },
    {
        "id": "C31",
        "phrase": "large discount relative to theoretical schedule",
        "status": "not-reproducible",
        "ledgerKey": "leaseMispricing.bands.band9798",
        "note": (
            "the findings bullet restating C12; same disposition (leaseMispricing.bands.band9798)"
        ),
    },
    {
        "id": "C32",
        "phrase": "bandwidth sensitivity (3-12 months) confirms direction is stable, magnitude varies",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.robustness.statedGrid",
        "note": (
            "the robustness claim's word 'confirms' has no stored grid "
            "output behind it in this checkout; the sentence is recorded, "
            "not corroborated (identificationAudit.robustness.statedGrid)"
        ),
    },
    {
        "id": "C33",
        "phrase": "measurable price suppression (~$138K)",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.condoDid.dependentInterpretations",
        "note": (
            "the conclusion's rounding of C03; withdrawn with it "
            "(withdrawals.condoDid.dependentInterpretations)"
        ),
    },
    {
        "id": "C34",
        "phrase": "upward movement (+$13K)",
        "status": "withdrawn",
        "ledgerKey": "withdrawals.hdbRdit.dependentInterpretations",
        "note": (
            "the conclusion's rounding of C05; withdrawn with it "
            "(withdrawals.hdbRdit.dependentInterpretations)"
        ),
    },
    {
        "id": "C35",
        "phrase": "DiD relies on comparability of CCR and OCR condo segments",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.assumptions.recordedInLegacy",
        "note": (
            "the frozen text's own recorded assumption; comparability is "
            "acknowledged in prose and tested nowhere in the checkout "
            "(identificationAudit.assumptions.recordedInLegacy)"
        ),
    },
    {
        "id": "C36",
        "phrase": "RDiT assumes no confounding events at the cutoff",
        "status": "not-reproducible",
        "ledgerKey": "identificationAudit.assumptions.recordedInLegacy",
        "note": (
            "the frozen text's own recorded assumption; with no dated policy "
            "artefact the confounding-event check is unmeasurable, so the "
            "assumption can be neither verified nor violated here "
            "(identificationAudit.assumptions.recordedInLegacy)"
        ),
    },
    {
        "id": "C37",
        "phrase": "the canonical assets for this page now live under `app/public/data/analysis/`",
        "status": "re-measured",
        "ledgerKey": "unlinkedArtefact.manifestPin",
        "note": (
            "the directory exists and holds causal_did_analysis.png "
            "(sha-pinned, 91,244 bytes), which the frozen manifest lists as a "
            "mutable=false asset. That is an asset listing, not a run record; "
            "the plot adjudicates nothing about the estimates in either "
            "direction (unlinkedArtefact)"
        ),
    },
    {
        "id": "C38",
        "phrase": "The historical Python causal-analysis scripts were retired from the supported repo surface",
        "status": "not-reproducible",
        "ledgerKey": "codeScan.diDRditPythonFileCount",
        "note": (
            "not reproducible from this checkout: the code scan shows zero "
            "scan-eligible .py files carrying DiD/RDiT tokens - a token "
            "measure that cannot establish a claim about historical "
            "retirement; whether the scripts were retired, moved or renamed "
            "outside the scan's boundary is unmeasurable here (codeScan)"
        ),
    },
    {
        "id": "C39",
        "phrase": "data/parquets/L3/housing_unified.parquet",
        "status": "re-measured",
        "ledgerKey": "cohortScreens.legacyInputPath",
        "note": (
            "the named primary input path does not exist in this checkout; "
            "the shipped platinum dataset is at "
            "data/pipeline/04_platinum/unified_dataset.parquet and no "
            "artefact ties the two (cohortScreens.legacyInputPath)"
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
    verified = sum(1 for quote in quotes if quote["occurrences"] > 0)
    if verified != len(claims):
        missing = [q["id"] for q in quotes if q["occurrences"] == 0]
        raise SystemExit(f"legacy phrases not found verbatim: {missing}")
    return {
        "legacyFile": _relative(LEGACY_EDITION),
        "legacyFileSha256": sha256_of(LEGACY_EDITION),
        "legacyFileBytes": int(LEGACY_EDITION.stat().st_size),
        "legacyFileLines": len(text.splitlines()),
        "liveCopyPath": _relative(LEGACY_LIVE_COPY),
        "liveCopyByteIdentical": sha256_of(LEGACY_LIVE_COPY) == sha256_of(LEGACY_EDITION),
        "claimsChecked": len(claims),
        "phrasesVerifiedVerbatim": verified,
        "method": (
            "each phrase is a verbatim substring test (str.count) against the "
            "frozen file's bytes decoded as UTF-8; a count of zero fails the "
            "build. Markdown emphasis markers are part of the verbatim text "
            "where the source has them"
        ),
        "quotes": quotes,
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

    Resolution is syntactic: each `ledgerKey` is walked against this ledger at
    build time — dict keys by name, list items by their `id` — and an
    unresolved key fails the build rather than shipping. Resolution says the
    path exists in the ledger; it does not judge whether the disposition is
    right.
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
        "resolution": "syntactic",
        "method": (
            "each claim's ledgerKey is resolved against this ledger at build "
            "time by walking dict keys and list items by their `id`; an "
            "unresolved key fails the build rather than shipping. Resolution "
            "is syntactic and carries no judgement about the disposition"
        ),
    }


def build() -> dict[str, Any]:
    parquet_file = pq.ParquetFile(UNIFIED)
    schema_names = list(pq.read_schema(UNIFIED).names)
    frame = pd.read_parquet(
        UNIFIED,
        columns=[
            "month",
            "property_type",
            "planning_area",
            "region",
            "market_segment",
            "is_ec",
        ],
    )
    measured_cutoff = cutoff(frame)
    last_complete = measured_cutoff["lastCompleteMonth"]

    screens = cohort_screens(frame, last_complete)
    screens["segmentAreaSpans"] = segment_area_spans(frame, last_complete)

    scanned_files = _scan_files()
    tokens = token_scan(scanned_files)
    code = code_scan(scanned_files)
    name_scan = artefact_name_scan()
    artefact = unlinked_artefact()
    audit = identification_audit(tokens)
    lease = lease_mispricing(tokens, name_scan)

    claims = legacy_claims()

    inputs: dict[str, Any] = {}
    for path in (
        UNIFIED,
        LEGACY_EDITION,
        LEGACY_LIVE_COPY,
        LEGACY_MANIFEST,
        POLICY_PLAN_DOC,
        DID_PNG_PUBLIC,
        DID_PNG_DIST,
    ):
        inputs[_relative(path)] = {"sha256": sha256_of(path), "bytes": int(path.stat().st_size)}
    inputs[_relative(UNIFIED)]["rows"] = int(parquet_file.metadata.num_rows)
    inputs[_relative(UNIFIED)]["columns"] = len(schema_names)
    edition_text = EDITION_TEXT.read_text(encoding="utf-8")
    edition_entry = {
        "sha256": sha256_of(EDITION_TEXT),
        "bytes": int(EDITION_TEXT.stat().st_size),
    }
    inputs[_relative(EDITION_TEXT)] = dict(edition_entry)

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": "RS13",
        "series": "causal-inference-overview",
        "scope": (
            "RS13 causal-inference-overview evidence: an identification audit "
            "of the frozen policy-impact article — the frame the two stated "
            "cohorts would draw on, cohort-size screens inside the measured "
            "cutoff, the shipped region labels' planning-area spans, the "
            "absence scans (dated policy artefact, estimator code, pretrend/"
            "placebo/anticipation records, Bala schedule), the unlinked plot "
            "artefact, and the two recorded withdrawals with their reason"
        ),
        "definition": DEFINITION,
        "editionText": {
            "path": _relative(EDITION_TEXT),
            "sha256": edition_entry["sha256"],
            "bytes": edition_entry["bytes"],
            "wordCount": len(edition_text.split()),
            "readingTimeMinutes": -(-len(edition_text.split()) // 200),
            "readingTimeBasis": (
                "wordCount / 200 words per minute, rounded up; measured at "
                "build time from the same bytes the sha256 pins"
            ),
            "revisions": [
                {
                    "label": "round-0",
                    "sha256": (
                        "7bb33bafeda4377146930cd35cfbcaa600be59e3a60d4601205d"  # pragma: allowlist secret — superseded round-0 edition revision hash, not a credential
                        "3c2ff60adb38"  # pragma: allowlist secret — continuation of the superseded round-0 revision hash, not a credential
                    ),
                    "bytes": 47784,
                    "disposition": (
                        "superseded review object; its bytes were overwritten "
                        "before any snapshot existed and are not retained "
                        "(disclosed in the evidence pack review history)"
                    ),
                },
                {
                    "label": "round-1",
                    "sha256": (
                        "131350caaa11be6455fef62908522e0091e616c1578e513c1595"  # pragma: allowlist secret — superseded round-1 edition revision hash, not a credential
                        "ff6d84084ca2"  # pragma: allowlist secret — continuation of the superseded round-1 revision hash, not a credential
                    ),
                    "bytes": 48776,
                    "disposition": (
                        "superseded review-fix text; retained verbatim at "
                        "docs/implementation/artifacts/superseded/"
                        "causal-inference-overview.revedition-131350ca.md"
                    ),
                },
                {
                    "label": "current",
                    "sha256": edition_entry["sha256"],
                    "bytes": edition_entry["bytes"],
                    "disposition": (
                        "the reviewable object; --check fails if the "
                        "checked-out text is not exactly these bytes"
                    ),
                },
            ],
            "meaning": (
                "pins the exact edition-text bytes this ledger describes; the "
                "producer reads the file at build time, so any edit to the "
                "edition text must be followed by a producer re-run or "
                "--check fails. A review hand-off citing a sha256 in "
                "`revisions` identifies a superseded revision, not the "
                "reviewable object: the current reviewable bytes are "
                "`sha256`/`bytes` above. The edition text carries no "
                "self-hash (a file cannot contain its own sha256); the pack "
                "and the review hand-off cite this field for the edition's "
                "identity"
            ),
        },
        "inputs": inputs,
        "cutoff": measured_cutoff,
        "frameInventory": frame_inventory(frame, schema_names, last_complete),
        "cohortScreens": screens,
        "identificationAudit": audit,
        "codeScan": code,
        "artefactNameScan": name_scan,
        "tokenScan": tokens,
        "scanDeclaration": scan_declaration(),
        "unlinkedArtefact": artefact,
        "withdrawals": withdrawals(),
        "reconstructionRequirements": reconstruction_requirements(),
        "leaseMispricing": lease,
        "notMeasurable": not_measurable(audit, name_scan, code),
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
        print("Pass: RS13 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS13 ledger does not match this checkout")
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
        f"{evidence['cutoff']['terminalMonthShareOfTrailingMedian']} of the trailing median, "
        f"private rows)"
    )
    print(
        "DiD screen: "
        f"{evidence['cohortScreens']['diD']['rows']} condominium rows to cutoff, "
        f"treatment-label {evidence['cohortScreens']['diD']['statedTreatmentRows']} / "
        f"control-label {evidence['cohortScreens']['diD']['statedControlRows']}, "
        f"floor satisfied={evidence['cohortScreens']['diD']['floorSatisfiedByStatedGroups']}"
    )
    print(
        "RDiT screen: "
        f"{evidence['cohortScreens']['rdit']['rows']} HDB rows across "
        f"{evidence['cohortScreens']['rdit']['monthsPresent']} months, "
        f"min month {evidence['cohortScreens']['rdit']['minMonthTransactions']} rows"
    )
    print(
        "Absences: housing_policy_dates file matches "
        f"{evidence['artefactNameScan']['housingPolicyDatesFileMatches']}; "
        f"DiD/RDiT python files {evidence['codeScan']['diDRditPythonFileCount']}"
    )
    print(
        "Withdrawals: condo DiD and HDB RDiT headline numbers withdrawn "
        f"({evidence['withdrawals']['decisionSource']['decidedOn']})"
    )
    print(
        "Quote check: "
        f"{evidence['legacyQuoteCheck']['phrasesVerifiedVerbatim']}"
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
