#!/usr/bin/env python3
"""Measure RS06's lease-decay evidence: the response/unit decision, lease-age
validation, the legacy band table re-measured, the article-versus-interactive
band lineage, and every quantitative claim of the frozen legacy text disposed.

RS06's gate is "Resolve PSF/PSM and total-price versus per-area response before
fitting. Validate lease age as of transaction date. Reconcile article versus
interactive-band lineage. Keep chart/model gates until repaired coefficients and
wording are reviewed. Never convert a coefficient without confirming its
original response/unit." This tool measures from the local checkout, and only
what the checkout can support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04/RS05/RS09/
   RS10 shipped, computed on the HDB rows this study analyses.
2. **Response decision** — the D12/RF08 disposition of 2026-11-18 makes the
   PSF/PSM and total-price-versus-per-area choice the producer's, stated in the
   ledger as an explicit decision with its evidence. The evidence is measured:
   which per-area columns are populated on HDB rows, which column the frame's
   `psf` reproduces exactly, and which unit the article's own per-area column
   holds. No model is fitted and no coefficient is converted.
3. **Lease-age validation** — lease age as of transaction month, derived from
   `lease_commence_date`, validated against the frame's stored
   `remaining_lease` on the only rows that carry it, with every exception
   counted (negative-age rows included).
4. **Band table** — the article's stated bins re-measured on the window, each
   article value compared field by field, and the two stored CSV artefacts
   compared beside it.
5. **Town table** — the stated short-vs-fresh comparison re-measured for the
   six article towns, with the sign conventions of the article's two surfaces
   (table and technical findings) reconciled arithmetically.
6. **Interactive asset** — the 13 stored bands, their age coverage, the
   insights block cross-checked against both the article and the stored CSV,
   and the lineage between the two bandings stated symmetrically: nothing in
   the checkout links the asset's producer to the article's computation, so
   the asset is evidence neither for nor against the article's numbers.
7. **Regression inputs** — the availability of each regressor the legacy
   specification names, and the coefficient's unit problem recorded without a
   conversion: the sentence says PSF, the appendix names `price_per_sqm`, the
   stored chart's axis says SGD/PSM per year, and the fitted model is absent.
8. **Absence scans** — the retired L1/L3 parquet paths, any fitted-model or
   lease-named artefact, and a token scan over the shipping text roots with
   the programme's own surfaces excluded and the exclusion disclosed.
9. **Gates** — the chart gate the app already encodes, sha-pinned and quoted;
   the model gate recorded as in force; no edition text written by this pack.

It never runs the pipeline, never re-fits the legacy models and never writes
outside `--output`.

Usage:

    uv run python scripts/tools/lease_decay_evidence.py \\
        --output docs/implementation/artifacts/rs06-lease-decay-evidence.json

    uv run python scripts/tools/lease_decay_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
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
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "lease-decay.md"
)
INTERACTIVE_ASSET = (
    REPO_ROOT / "app" / "public" / "data" / "interactive_tools" / "lease_decay_analysis.json.gz"
)
CSV_ANALYSIS = REPO_ROOT / "data" / "analysis" / "lease_decay" / "lease_decay_analysis.csv"
CSV_PRICE_STATS = REPO_ROOT / "data" / "analysis" / "lease_decay" / "lease_price_statistics.csv"
PNG_PRICE_DISTRIBUTION = (
    REPO_ROOT / "data" / "analysis" / "lease_decay" / "lease_decay_price_distribution.png"
)
PNG_PSM_BY_BAND = REPO_ROOT / "data" / "analysis" / "lease_decay" / "lease_decay_psm_by_band.png"
PNG_TRANSACTION_VOLUME = (
    REPO_ROOT / "data" / "analysis" / "lease_decay" / "lease_decay_transaction_volume.png"
)
PNG_ADVANCED = (
    REPO_ROOT
    / "app"
    / "public"
    / "data"
    / "analysis"
    / "lease_decay_advanced"
    / "lease_decay_advanced_analysis.png"
)
STUDIES_TS = REPO_ROOT / "app" / "src" / "components" / "studies" / "lib" / "studies.ts"
RESEARCH_REGISTER = (
    REPO_ROOT / "docs" / "plans" / "2026-11-12-reporting-refresh-research-register.md"
)
LEGACY_L1_PATH = "data/parquets/L1/housing_hdb_transaction.parquet"
LEGACY_L3_PATH = "data/parquets/L3/housing_unified.parquet"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs06-lease-decay-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

# The conversion factor the frame's own psf column reproduces exactly on every
# HDB row (measured below, and asserted before the ledger is written).
SQFT_PER_SQM = 10.7639104167
# The HDB tenure the lease-age derivation assumes. It is an assumption, and it
# is validated: the 37,153 rows that carry a stored remaining_lease agree with
# 99 minus lease age within one year on all but one row (leaseAgeValidation).
TENURE_YEARS = 99.0

# The article's stated data period, capped at the measured cutoff for every
# aggregation in this ledger.
STUDY_WINDOW_START = "2017-01"
CANDIDATE_TERMINAL_MONTHS = tuple(
    [f"{year}-{month:02d}" for year in (2025, 2026) for month in range(1, 13)]
)

GATE_CLAUSE = (
    "Resolve PSF/PSM and total-price versus per-area response before fitting. "
    "Validate lease age as of transaction date. Reconcile article versus "
    "interactive-band lineage. Keep chart/model gates until repaired coefficients "
    "and wording are reviewed. Never convert a coefficient without confirming "
    "its original response/unit."
)

# The scan is bounded to these roots and suffixes so the ledger is reproducible
# file-order-independently and cannot read itself. The exclusions are the RF08
# programme's own surfaces (the rule RS10 shipped at its round-15 scan-boundary
# fix): `docs/implementation/` holds the per-study records and this ledger,
# `scripts/tools/` holds the evidence producers themselves, `prompts/` holds the
# handoffs and runbooks, published edition texts would drift every time a later
# study signs (the frozen legacy originals stay IN the scan, because the
# article's own method claims are what these tokens are matched against), and
# the D12 decision register records reviewers' verdicts in their own vocabulary.
SCAN_ROOTS = ("docs", "scripts", "src", "app/src")
SCAN_SUFFIXES = (".md", ".py", ".ts", ".tsx")
EXCLUDED_SCAN_PREFIXES = (
    "docs/implementation/",
    "scripts/tools/",
    "prompts/",
    "docs/analytics/editions/",
    "app/src/components/studies/",
    "app/tests/",
)
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
EXCLUDED_SCAN_PATHS = (
    "scripts/tools/lease_decay_evidence.py",
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
    ".secrets.baseline",
)
FILENAME_SCAN_ROOTS = ("data", "app/public/data", "scripts", "src", "docs")
# Same programme-surface exclusion the token scan declares: a hash-pinned
# filename scan cannot read this programme's own output (sibling evidence
# tools, runbooks, records, published editions land and drift the count),
# while the frozen legacy corpus stays IN the scan.
FILENAME_SCAN_EXCLUDED_PREFIXES = (
    "docs/implementation/",
    "scripts/tools/",
    "prompts/",
    "docs/analytics/editions/",
)
FILENAME_SCAN_RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
FILENAME_SCAN_EXCLUDED_PATHS = (
    "scripts/tools/lease_decay_evidence.py",
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
)
FILENAME_TOKEN = "lease"
# The two legacy frames the article names, each as the filename token its own
# ledger field is labelled with. `absenceScans.l1Frame.filenameMatchesUnderData`
# and `.l3Frame.filenameMatchesUnderData` enumerate files under data/ whose NAME
# carries these tokens; they are NOT derived from the `lease` filename scan, whose
# matches are this series' artefacts and would be mislabelled as the frame's
# namesakes.
LEGACY_L1_FILENAME_TOKEN = "housing_hdb_transaction"
LEGACY_L3_FILENAME_TOKEN = "housing_unified"

METHOD_TOKENS = (
    ("54.75", False),
    ("bins [0, 60, 70, 80, 90, 100]", False),
    ("remaining_lease_months", False),
    ("Mann-Whitney", True),
    ("Bala", True),
    ("lease_decay", False),
)

# The article's band table, exactly as published (frozen text). `perAreaValue`
# is the column the table labels "Median PSF"; the ledger measures which unit
# those values hold.
ARTICLE_BAND_ROWS: tuple[dict[str, Any], ...] = (
    {
        "id": "90+",
        "avgRemainingYears": 93.5,
        "medianPrice": 558000,
        "perAreaValue": 6205,
        "discountLabel": "baseline",
        "transactions": 50912,
    },
    {
        "id": "80-90",
        "avgRemainingYears": 84.6,
        "medianPrice": 520000,
        "perAreaValue": 5389,
        "discountLabel": "-13.2%",
        "transactions": 29562,
    },
    {
        "id": "70-80",
        "avgRemainingYears": 75.4,
        "medianPrice": 548000,
        "perAreaValue": 4845,
        "discountLabel": "-21.9%",
        "transactions": 47044,
    },
    {
        "id": "60-70",
        "avgRemainingYears": 64.6,
        "medianPrice": 446000,
        "perAreaValue": 4730,
        "discountLabel": "-23.8%",
        "transactions": 54521,
    },
    {
        "id": "<60",
        "avgRemainingYears": 54.5,
        "medianPrice": 390000,
        "perAreaValue": 5274,
        "discountLabel": "-15.0%",
        "transactions": 41595,
    },
)
ARTICLE_STATED_SAMPLE = 223634
ARTICLE_STATED_LEASE_RANGE = (30, 99)
ARTICLE_TRADEOFF_SHARE = 24.4
ARTICLE_COEFFICIENT = 54.75

# The article's town table (short <70 yr vs fresh 90+ yr, as the appendix
# states it; the published values are per-area at the article's own scale).
ARTICLE_TOWN_ROWS: tuple[dict[str, Any], ...] = (
    {"id": "CLEMENTI", "short": 5224, "fresh": 8796, "discountLabel": "40.6%"},
    {"id": "TOA PAYOH", "short": 4939, "fresh": 8182, "discountLabel": "39.6%"},
    {"id": "QUEENSTOWN", "short": 5526, "fresh": 9048, "discountLabel": "38.9%"},
    {"id": "WOODLANDS", "short": 4262, "fresh": 4544, "discountLabel": "6.2%"},
    {"id": "JURONG WEST", "short": 4496, "fresh": 4516, "discountLabel": "0.4%"},
    {"id": "PASIR RIS", "short": 5621, "fresh": 4676, "discountLabel": "-20.2%"},
)
# The technical findings' restatement of four of the six towns (sign-flipped).
FINDINGS_TOWN_SIGNS: tuple[dict[str, Any], ...] = (
    {"id": "CLEMENTI", "value": -40.6},
    {"id": "TOA PAYOH", "value": -39.6},
    {"id": "WOODLANDS", "value": -6.2},
    {"id": "PASIR RIS", "value": 20.2},
)

BAND_BINS = (0, 60, 70, 80, 90, 100)
BAND_LABELS = ("<60", "60-70", "70-80", "80-90", "90+")
SHORT_LEASE_MAX_YEARS = 70.0
FRESH_LEASE_MIN_YEARS = 90.0

TOWN_TABLE_ARTICLE_TOWNS = (
    "CLEMENTI",
    "TOA PAYOH",
    "QUEENSTOWN",
    "WOODLANDS",
    "JURONG WEST",
    "PASIR RIS",
)

PNG_VISUAL_READS = {
    "lease_decay_price_distribution.png": (
        "HUMAN VISUAL READ: title 'HDB Resale Price Distribution by Remaining "
        "Lease Band'; five boxplots of resale price (SGD, axis to about 1.6e6) "
        "by the article's five remaining-lease bands."
    ),
    "lease_decay_psm_by_band.png": (
        "HUMAN VISUAL READ: title 'Median Price per SQM by Remaining Lease "
        "Band'; y-axis 'Median Price per SQM (SGD)'; five bars at about 5,274 / "
        "4,730 / 4,845 / 5,389 / 6,205, the article's per-area column values."
    ),
    "lease_decay_transaction_volume.png": (
        "HUMAN VISUAL READ: title 'Transaction Volume by Remaining Lease Band'; "
        "five bars at about 41.6k / 54.5k / 47.0k / 29.6k / 50.9k, the article's "
        "transaction counts, 60-70 the highest."
    ),
    "lease_decay_advanced_analysis.png": (
        "HUMAN VISUAL READ: four panels. (1) 'Bala's Curve Validation: Empirical "
        "vs Theoretical', empirical value as % of fresh lease against remaining "
        "lease 40-97 years with a red dashed theoretical line and a green "
        "'Overvaluation' fill. (2) 'Town-Normalized Lease Discount (Short vs "
        "Fresh Lease)', 22 town bars, CLEMENTI highest at about +40%, PASIR RIS "
        "lowest at about -20%, dashed rule at about 20%; the town names include "
        "KALLANG/WHAMPOA and CENTRAL AREA. (3) 'Lease Decay Scatter Plot', Price "
        "PSM (SGD) against remaining lease 30-100 years. (4) 'Hedonic "
        "Regression: Isolated Lease Effect (Controlled for floor, MRT, town)', "
        "one bar labelled Lease Effect, y-axis 'Coefficient (SGD/PSM per year)', "
        "height about 54-55 with a small error bar."
    ),
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_lines(path: Path) -> int:
    """Lines of a text file — the count the ledger records for text inputs."""

    return len(path.read_text(encoding="utf-8").splitlines())


def _csv_data_rows(path: Path) -> int:
    """Data records of a CSV file, the header row excluded."""

    with path.open(newline="", encoding="utf-8") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _select(frame: pd.DataFrame, mask: Any) -> pd.DataFrame:
    """Boolean-mask a frame, keeping the result explicitly a DataFrame."""
    return pd.DataFrame(frame.loc[mask]).reset_index(drop=True)


def _numeric(column: Any) -> pd.Series:
    """A float64 view of a column, for comparisons that must tolerate NaN."""
    series = pd.Series(column)
    return pd.Series(pd.to_numeric(series, errors="coerce"), index=series.index)


def _series(column: Any) -> pd.Series:
    """A Series view of a column or accessor result, keeping types explicit."""
    return pd.Series(column)


def _storage_form(column: Any) -> str:
    """The column's storage form, measured rather than assumed.

    A price column stored as text with thousands separators is not a column of
    missing values: `_numeric` cannot read `'16,496'`, so the raw non-null count
    and the numerically parsed count differ because of the storage, and the
    ledger records both instead of letting one stand for the other.
    """
    series = _series(column)
    dtype = str(series.dtype)
    if dtype != "object":
        return dtype
    values = _series(series.dropna().astype(str))
    if len(values) and bool(values.str.contains(",", regex=False).any()):
        return "string, thousands separators"
    return "string"


def _column_evidence(
    frame: pd.DataFrame, hdb: pd.DataFrame, name: str, unit: str
) -> dict[str, Any]:
    """One column's measured population: the raw column and its numeric parse."""
    raw = _series(frame[name])
    return {
        "frameNonNull": int(raw.notna().sum()),
        "hdbNonNull": int(_series(hdb[name]).notna().sum()),
        "storage": _storage_form(raw),
        "numericParsedNonNull": int(_numeric(raw).notna().sum()),
        "unit": unit,
    }


def _number(value: Any, label: str) -> float:
    try:
        return float(value)
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
    try:
        text = gzip.decompress(path.read_bytes()).decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SystemExit(f"Unreadable gzip payload {_relative(path)}: {error}") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise SystemExit(f"Unparseable gzip JSON {_relative(path)}: {error}") from error


def _code_quote(path: Path, needle: str, label: str) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    position = next((number for number, line in enumerate(lines, start=1) if needle in line), None)
    if position is None:
        raise SystemExit(
            f"{label} marker {needle!r} not found in {_relative(path)}; the ledger's citation is stale"
        )
    return {"path": _relative(path), "line": position, "quote": lines[position - 1].strip()}


def _lease_variables(hdb: pd.DataFrame) -> dict[str, pd.Series]:
    """The derived lease variables, computed once from the measured columns."""
    months = _series(hdb["month"]).astype(str)
    year = _series(months.str[:4]).astype(int)
    month_num = _series(months.str[5:7]).astype(int)
    lcd = _numeric(hdb["lease_commence_date"])
    age_years = (year - lcd) + ((month_num - 1) / 12.0)
    remaining = TENURE_YEARS - age_years
    return {"months": months, "ageYears": age_years, "remaining": remaining}


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial."""
    hdb = _select(frame, frame["property_type"] == "hdb")
    counts = {str(k): int(v) for k, v in hdb.groupby("month").size().items()}
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
            "median, not an assumed calendar fact (the same rule RS03/RS04/RS05/"
            "RS09/RS10 shipped, here computed on the HDB rows this study analyses)"
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
        "frameFirstMonth": ordered[0],
        "frameLastMonth": ordered[-1],
        "distinctHdbMonths": len(ordered),
        "hdbRowsTotal": int(len(hdb)),
        "meaning": (
            "every window, count and share in this ledger that touches the frame "
            "stops at lastCompleteMonth"
        ),
    }


def response_decision(
    frame: pd.DataFrame, hdb: pd.DataFrame, last_complete_month: str, frame_first_month: str
) -> dict[str, Any]:
    """The explicit unit/response decision the D12 disposition assigns to the producer.

    Measured evidence, then the decision. The four-states rule applies to the
    per-area price columns, and every count in `columnsExamined` is measured on
    the shipped frame rather than assumed: `Unit Price ($ PSM)` is a present
    column, populated on the private rows and stored as text with thousands
    separators, so `frameNonNull` counts the raw column, `hdbNonNull` the HDB
    rows, and `numericParsedNonNull` the subset a numeric read can parse; it is
    null on every HDB row. `area_sqm`/`area_sqft`/`Unit Price ($ PSF)` are
    populated on the private rows only, and `floor_level` is the absent-VALUE
    column on HDB rows (present column, all null there).
    """
    price = _numeric(hdb["price"])
    fa_sqm = _numeric(hdb["floor_area_sqm"])
    psf = _numeric(hdb["psf"])
    ok = fa_sqm.notna() & (fa_sqm > 0) & price.notna() & (price > 0) & psf.notna()
    implied_psf = _series(price[ok] / (fa_sqm[ok] * SQFT_PER_SQM))
    dev = (implied_psf - psf[ok]).abs()
    max_dev = float(dev.max())
    if max_dev > 1.0:
        raise SystemExit(
            "psf no longer reproduces price/(floor_area_sqm * SQFT_PER_SQM) "
            f"(max deviation {max_dev}); the response decision's evidence is stale"
        )
    psm = price / fa_sqm
    in_window = ok & (_series(hdb["month"]).astype(str) <= last_complete_month)
    per_area = {
        "area_sqm": _column_evidence(frame, hdb, "area_sqm", "square metres (private rows only)"),
        "area_sqft": _column_evidence(frame, hdb, "area_sqft", "square feet (private rows only)"),
        "Unit Price ($ PSF)": _column_evidence(
            frame, hdb, "Unit Price ($ PSF)", "SGD per square foot (private rows only)"
        ),
        "Unit Price ($ PSM)": _column_evidence(
            frame, hdb, "Unit Price ($ PSM)", "SGD per square metre (private rows only)"
        ),
    }
    stored_psm = per_area["Unit Price ($ PSM)"]
    frame_rows = int(len(frame))
    return {
        "decision": (
            "response = psf, the frame's measured $-per-square-foot column, "
            "populated and exact on every HDB row; secondary per-area measure = "
            "derivedPsm = price / floor_area_sqm, exact arithmetic on two "
            "measured columns; total-price measure = price, used only where a "
            "field is named medianPrice. Any future fitting uses one of these "
            "stated responses with its unit named in the same sentence. No "
            "coefficient is converted between units in this ledger (gate clause), "
            "and no model is fitted by this pack."
        ),
        "fitPerformed": False,
        "columnsExamined": {
            "price": {"hdbNonNull": int(price.notna().sum()), "unit": "SGD total price"},
            "floor_area_sqm": {
                "hdbNonNull": int(fa_sqm.notna().sum()),
                "unit": "square metres",
            },
            "psf": {
                "hdbNonNull": int(psf.notna().sum()),
                "unit": "SGD per square foot (measured, see identityCheck)",
            },
            **per_area,
        },
        "fourStatesNote": (
            "The four states remain distinct: null, recorded zero, absent row, and absent column. A sentinel string is a fifth distinct state: a present value that encodes missingness; `remaining_lease` value `'nan'` is this example and is not an Arrow null or zero. `Unit Price ($ PSM)` is a present, populated column, not an absent "
            "one: it exists in the parquet schema (97 columns), stored as a "
            f"{stored_psm['storage']}, and holds {stored_psm['frameNonNull']:,} "
            f"non-null values across all {frame_rows:,} rows, of which "
            f"{stored_psm['hdbNonNull']:,} fall on the HDB rows this study "
            "analyses. Its storage, not missingness, is what limits a numeric "
            "read: `_numeric` parses "
            f"{stored_psm['numericParsedNonNull']:,} of those values against "
            f"the {stored_psm['frameNonNull']:,} the column holds, and the "
            "ledger records both counts (`frameNonNull`, "
            "`numericParsedNonNull`). The absent-VALUE example on HDB rows is "
            "`floor_level` (present column, all null on HDB rows); "
            "`area_sqm`, `area_sqft` and `Unit Price ($ PSF)` are populated on "
            "the private rows only. The absent-column state is counted and "
            "enumerated separately (responseDecision.absentColumns)."
        ),
        "identityCheck": {
            "statement": "psf == price / (floor_area_sqm * SQFT_PER_SQM)",
            "sqftPerSqm": SQFT_PER_SQM,
            "rowsChecked": int(ok.sum()),
            "rowsWithin1": int((dev <= 1.0).sum()),
            "maxAbsDeviation": _r(max_dev, 6),
            "meaning": (
                "the frame's psf column is exactly the per-square-foot price on "
                "every HDB row; per-square-metre prices are not stored for HDB "
                "rows and are used here only as the derived measure price/"
                "floor_area_sqm"
            ),
        },
        "derivedPsm": {
            "definition": "price / floor_area_sqm (SGD per square metre)",
            "note": (
                "derived arithmetic on two measured columns, never read from a "
                "stored per-square-metre column, because none is populated for "
                "HDB rows"
            ),
            "sampleMedian": _r(float(np.median(psm[in_window])), 2),
            "sampleMedianRows": int(in_window.sum()),
            "sampleMedianWindow": {
                "start": frame_first_month,
                "end": last_complete_month,
            },
            "sampleMedianBasis": (
                "cutoff rule: every aggregation stops at lastCompleteMonth, so "
                "the sample median excludes the terminal month's rows; the "
                "full-frame median is not reported"
            ),
        },
        "unitInvarianceOfBandDiscounts": (
            "psf = derivedPsm / SQFT_PER_SQM row-exactly, so medians and "
            "discount ratios computed on psf equal those computed on derivedPsm "
            "up to rounding; the band table records both and the measured "
            "maximum difference between them"
        ),
        "legacyResponseStatement": {
            "appendixSentence": (
                "- **Price statistics**: median `resale_price` and `price_per_sqm` by band"
            ),
            "coefficientSentence": (
                "| Pure lease effect     | +$54.75 PSF per extra year | Lease "
                "still has measurable pricing power |"
            ),
            "meaning": (
                "the frozen text names price_per_sqm as the fitted response in "
                "its appendix and PSF in its coefficient sentence; the two "
                "statements contradict each other, and the contradiction is "
                "recorded, not resolved by choosing for the legacy author"
            ),
        },
        "gateClause": (
            "Never convert a coefficient without confirming its original response/unit."
        ),
        "conversionPerformed": False,
    }


def absent_columns() -> dict[str, Any]:
    """Columns the frozen text names that the shipped schema does not carry.

    Column presence is measured against the shipped parquet schema read from
    metadata (programme rule 6); an absent column is a different missingness
    state from a null value in a present column (programme rule 7).
    """

    schema_names = set(pq.read_schema(UNIFIED).names)
    named = (
        (
            "remaining_lease_months",
            "the frozen appendix's derivation: `- **Remaining lease years**: "
            "`remaining_lease_months / 12``",
        ),
        (
            "resale_price",
            "the frozen appendix's statistics line: `- **Price statistics**: "
            "median `resale_price` and `price_per_sqm` by band`",
        ),
        (
            "price_per_sqm",
            "the same appendix statistics line — the fitted-response name the "
            "coefficient sentence's PSF contradicts",
        ),
    )
    columns = [
        {"name": name, "namedBy": named_by, "inShippedSchema": name in schema_names}
        for name, named_by in named
    ]
    absent = [column for column in columns if not column["inShippedSchema"]]
    return {
        "count": len(absent),
        "columns": columns,
        "shippedSchemaColumns": len(schema_names),
        "basis": (
            "column presence measured against the shipped parquet schema read "
            "from metadata; the names are the frozen text's own column names, "
            "machine-checked verbatim in legacyQuoteCheck"
        ),
        "meaning": (
            "the absent-column state of the four missingness states is counted "
            "and enumerated here: these frozen-text column names exist in no "
            "shipped frame's schema — a different state from a null value in a "
            "present column (responseDecision.fourStatesNote) and from the "
            "retired L1/L3 frames' missing files (absenceScans.l1Frame/.l3Frame)"
        ),
    }


def lease_age_validation(hdb: pd.DataFrame) -> dict[str, Any]:
    """Parse all documented remaining-lease strings and validate lease age.

    Accepted values are the exact sentinel ``nan``, integer year strings,
    ``N years``, and ``N years M months``. Arrow nulls remain null; the
    sentinel is explicitly treated as encoded missingness, never as zero.
    """
    raw = _series(hdb["remaining_lease"]).astype("string")
    sentinel = raw.eq("nan").fillna(False)
    bare = raw.str.fullmatch(r"\d+", na=False)
    years_only = raw.str.fullmatch(r"\d+ years", na=False)
    years_months = raw.str.fullmatch(r"\d+ years \d+ month(?:s)?", na=False)
    parsed = pd.Series(np.nan, index=hdb.index, dtype="float64")
    parsed.loc[bare] = raw.loc[bare].astype(float)
    parsed.loc[years_only] = raw.loc[years_only].str.extract(r"(\d+)", expand=False).astype(float)
    parts = raw.loc[years_months].str.extract(r"(\d+) years (\d+) month(?:s)?")
    parsed.loc[years_months] = parts[0].astype(float) + parts[1].astype(float) / 12.0
    present = raw.notna()
    unparsed = present & ~sentinel & ~bare & ~years_only & ~years_months
    formats = {
        "sentinelString": int(sentinel.sum()),
        "bareYears": int(bare.sum()),
        "yearsOnly": int(years_only.sum()),
        "yearsMonths": int(years_months.sum()),
        "unparsed": int(unparsed.sum()),
    }
    if formats["unparsed"]:
        examples = raw.loc[unparsed].drop_duplicates().head(10).tolist()
        raise SystemExit(f"Unparsed remaining_lease formats ({formats['unparsed']}): {examples}")

    months = _series(hdb["month"]).astype(str)
    transaction_year = _series(months.str[:4]).astype(float)
    lcd = _numeric(hdb["lease_commence_date"])
    age_years = _series(transaction_year - lcd)
    derived_remaining = _series(TENURE_YEARS - age_years)
    stored = parsed
    has_stored = stored.notna()
    dev_full = (stored - derived_remaining).abs()
    dev = dev_full[has_stored]
    worst_mask = has_stored & (dev_full > 1.0)
    worst_rows = []
    for index in hdb.index[worst_mask.to_numpy()]:
        worst_rows.append(
            {
                "month": str(hdb.at[index, "month"]),
                "storedRemainingLease": _r(stored.at[index], 4),
                "derivedRemaining": _r(derived_remaining.at[index], 4),
                "leaseCommenceDate": _r(lcd.at[index], 0),
            }
        )
    negative_age = age_years < 0
    negative_by_year = {
        str(k): int(v)
        for k, v in sorted(year_counts(_series(hdb["month"]).astype(str), negative_age).items())
    }

    stored_years = _series(_series(months[has_stored]).str[:4])
    stored_by_year = {str(k): int(v) for k, v in sorted(stored_years.value_counts().items())}

    return {
        "derivation": {
            "formula": (
                "leaseAgeYears = (transactionYear + (transactionMonth-1)/12) - "
                "lease_commence_date; derivedRemainingYears = 99 - leaseAgeYears"
            ),
            "tenureAssumedYears": TENURE_YEARS,
            "tenureAssumptionStatus": (
                "an assumption, validated against the stored column below: the "
                "stored remaining_lease plus the derived age clusters at 99"
            ),
            "precision": (
                "month precision — the HDB resale source dates transactions to "
                "the month (transaction_date carries day 01), so 'as of "
                "transaction date' is as of transaction month"
            ),
        },
        "storedColumn": {
            "parseRule": "exact `nan` sentinel; bare integer years; `N years`; or `N years M month(s)` converted to years as N + M/12; Arrow null remains null",
            "formatCounts": formats,
            "nonNullRows": int(raw.notna().sum()),
            "nullRows": int(raw.isna().sum()),
            "realParsedRows": int(has_stored.sum()),
            "sentinelRows": int(sentinel.sum()),
            "nonNullByTransactionYear": stored_by_year,
            "numericMin": _r(stored.min(), 4),
            "numericMax": _r(stored.max(), 4),
            "rowsEqualToZero": int((stored == 0).sum()),
            "units": (
                "years (numeric range 48-97); the legacy methodology's "
                "`remaining_lease_months / 12` names a months-scale column of "
                "the retired L1 frame, which no shipped frame carries (see "
                "absenceScans); the archived L2/L3 schema documents record "
                "remaining_lease_months for those retired frames"
            ),
        },
        "agreement": {
            "comparison": "stored remaining_lease years versus 99 - (transaction_year - lease_commence_date), using transaction year (not month fraction)",
            "rowsCompared": int(has_stored.sum()),
            "rowsComparable": int(has_stored.sum()),
            "shareWithin1Year": _r(float((dev <= 1.0).sum()) / int(has_stored.sum()), 6),
            "deviationBandCounts": {
                "within1Year": int((dev <= 1.0).sum()),
                "over1To2Years": int(((dev > 1.0) & (dev <= 2.0)).sum()),
                "over2To5Years": int(((dev > 2.0) & (dev <= 5.0)).sum()),
                "over5Years": int((dev > 5.0).sum()),
            },
            "within0_02Years": int((dev <= 0.02).sum()),
            "within0_5Years": int((dev <= 0.5).sum()),
            "within1_0Years": int((dev <= 1.0).sum()),
            "over1_0Years": int((dev > 1.0).sum()),
            "meanAbsDeviationYears": _r(float(dev.mean()), 4),
            "medianAbsDeviationYears": _r(float(dev.median()), 4),
            "maxAbsDeviationYears": _r(float(dev.max()), 4),
            "maxAbsDeviation": _r(float(dev.max()), 4),
            "rowsOverOneYear": worst_rows,
            "meaning": (
                "on the only rows that carry a stored remaining_lease (2015-2016 "
                "transactions), the stored value equals 99 minus the derived "
                "lease age within one year on all but one row — the derivation "
                "is validated, and the validation window is the stored column's "
                "own coverage, not the study window"
            ),
        },
        "exceptions": {
            "rowsWithNegativeLeaseAge": int(negative_age.sum()),
            "negativeAgeByTransactionYear": negative_by_year,
            "maxDerivedRemainingYears": _r(float(derived_remaining[negative_age].max()), 4)
            if int(negative_age.sum())
            else None,
            "meaning": (
                "transactions (1991-2011) carry a transaction month earlier than "
                "lease_commence_date under the 99-year tenure assumption, so "
                "their derived remaining lease exceeds 99; they are counted, "
                "not silently excluded, and they sit outside the study window"
            ),
        },
        "derivedRange": {
            "frameMin": _r(float(derived_remaining.min()), 4),
            "frameMax": _r(float(derived_remaining.max()), 4),
            "fromWindowStartMin": _r(
                float(derived_remaining[months >= STUDY_WINDOW_START].min()), 4
            ),
            "atOrBelowZeroRows": int((derived_remaining <= 0).sum()),
            "below30YearsRows": int((derived_remaining < 30).sum()),
        },
    }


def year_counts(months: pd.Series, mask: pd.Series) -> pd.Series:
    """Transaction-year counts over the rows a boolean mask selects."""
    years = _series(_series(months[mask]).str[:4])
    return years.value_counts()


def band_table(hdb: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """The article's stated bins, re-measured, with every article value compared."""
    variables = _lease_variables(hdb)
    months = variables["months"]
    remaining = variables["remaining"]
    price = _numeric(hdb["price"])
    fa_sqm = _numeric(hdb["floor_area_sqm"])
    psf = _numeric(hdb["psf"])
    psm = price / fa_sqm
    window = (months >= STUDY_WINDOW_START) & (months <= last_complete)

    band = _series(pd.cut(remaining, bins=list(BAND_BINS), labels=list(BAND_LABELS), right=True))
    in_band = (
        window & remaining.notna() & price.notna() & fa_sqm.notna() & (fa_sqm > 0) & psf.notna()
    )
    window_rows = int(in_band.sum())

    base_psm = float(np.median(psm[in_band & (band == "90+")]))
    base_psf = float(np.median(psf[in_band & (band == "90+")]))
    base_price = float(np.median(price[in_band & (band == "90+")]))

    measured: list[dict[str, Any]] = []
    for label in BAND_LABELS:
        mask = in_band & (band == label)
        med_psm = float(np.median(psm[mask]))
        med_psf = float(np.median(psf[mask]))
        med_price = float(np.median(price[mask]))
        measured.append(
            {
                "id": label,
                "count": int(mask.sum()),
                "shareOfWindow": _r(int(mask.sum()) / window_rows, 4),
                "medianPrice": _r(med_price, 1),
                "medianDerivedPsm": _r(med_psm, 2),
                "medianMeasuredPsf": _r(med_psf, 2),
                "meanRemainingYears": _r(float(remaining[mask].mean()), 2),
                "discountPsmVs90Plus": _r((base_psm - med_psm) / base_psm * 100, 2),
                "discountPsfVs90Plus": _r((base_psf - med_psf) / base_psf * 100, 2),
                "discountMedianPriceVs90Plus": _r((base_price - med_price) / base_price * 100, 2),
            }
        )
    unit_invariance = max(
        abs(entry["discountPsmVs90Plus"] - entry["discountPsfVs90Plus"]) for entry in measured
    )

    article_by_id = {row["id"]: row for row in ARTICLE_BAND_ROWS}
    comparison: list[dict[str, Any]] = []
    baseline = article_by_id["90+"]
    for entry in measured:
        article = article_by_id[entry["id"]]
        article_per_area_discount = (
            (baseline["perAreaValue"] - article["perAreaValue"]) / baseline["perAreaValue"] * 100
        )
        article_price_discount = (
            (baseline["medianPrice"] - article["medianPrice"]) / baseline["medianPrice"] * 100
        )
        comparison.append(
            {
                "id": entry["id"],
                "article": article,
                "measured": entry,
                "measuredMinusArticle": {
                    "count": entry["count"] - article["transactions"],
                    "medianPrice": _r(entry["medianPrice"] - article["medianPrice"], 1),
                    "medianDerivedPsm": _r(entry["medianDerivedPsm"] - article["perAreaValue"], 2),
                    "medianMeasuredPsf": _r(
                        entry["medianMeasuredPsf"] - article["perAreaValue"], 2
                    ),
                    "meanRemainingYears": _r(
                        entry["meanRemainingYears"] - article["avgRemainingYears"], 2
                    ),
                },
                "articleOwnArithmetic": {
                    "perAreaDiscountVs90Plus": _r(
                        article_per_area_discount if entry["id"] != "90+" else 0.0,
                        2,
                    ),
                    "medianPriceDiscountVs90Plus": _r(
                        article_price_discount if entry["id"] != "90+" else 0.0, 2
                    ),
                    "meaning": (
                        "the article's discount column reproduces from its own "
                        "PER-AREA column, not from its own Median Price column "
                        "(e.g. 80-90: per-area arithmetic gives -13.15 against "
                        "the published -13.2%, median-price arithmetic gives "
                        "-6.81) — the published column mixes a per-area "
                        "discount with a table headed Median Price"
                    ),
                },
                "perAreaUnitIdentification": {
                    "absMeasuredPsmMinusArticle": _r(
                        abs(entry["medianDerivedPsm"] - article["perAreaValue"]), 2
                    ),
                    "absMeasuredPsfMinusArticle": _r(
                        abs(entry["medianMeasuredPsf"] - article["perAreaValue"]), 2
                    ),
                    "nearestMeasuredUnit": (
                        "psm"
                        if abs(entry["medianDerivedPsm"] - article["perAreaValue"])
                        <= abs(entry["medianMeasuredPsf"] - article["perAreaValue"])
                        else "psf"
                    ),
                },
            }
        )

    stored_csv = _read_csv_analysis()
    csv_rows = stored_csv["rows"]
    csv_matches: list[dict[str, Any]] = []
    label_variants = {
        "90+": "90+ years",
        "80-90": "80-90 years",
        "70-80": "70-80 years",
        "60-70": "60-70 years",
        "<60": "<60 years",
    }
    for article in ARTICLE_BAND_ROWS:
        key = label_variants[article["id"]]
        csv_row = next((row for row in csv_rows if row["lease_band"] == key), None)
        if csv_row is None:
            raise SystemExit(f"stored CSV has no row for band {key}")
        csv_matches.append(
            {
                "id": article["id"],
                "csvMedianPsm": _r(csv_row["median_psm"], 4),
                "csvTransactionCount": int(csv_row["transaction_count"]),
                "csvMedianPrice": _r(csv_row["median_price"], 1),
                "csvAvgRemainingYears": _r(csv_row["avg_remaining_lease_years"], 4),
                "matchesArticleCount": int(csv_row["transaction_count"]) == article["transactions"],
                "matchesArticlePerAreaAt0dp": _r(csv_row["median_psm"], 0)
                == _r(article["perAreaValue"], 0),
                "matchesArticleMedianPrice": _r(csv_row["median_price"], 1)
                == _r(article["medianPrice"], 1),
            }
        )
    csv_count_sum = sum(entry["csvTransactionCount"] for entry in csv_matches)

    edge_counts = {
        str(edge): int((window & (remaining == float(edge))).sum()) for edge in (60, 70, 80, 90)
    }
    cheapest = min(measured, key=lambda entry: entry["medianDerivedPsm"])
    highest_volume = max(measured, key=lambda entry: entry["count"])

    return {
        "definition": {
            "bins": list(BAND_BINS),
            "labels": list(BAND_LABELS),
            "edgeConvention": "right-closed (a, b] (pandas cut default for the stated bins)",
            "edgeConventionStatus": (
                "the legacy states the bins but not the edge handling; the "
                "stored CSV's rounded min/max per band cannot distinguish edge "
                "handling, so this ledger states its own convention and records "
                "the window's row counts sitting exactly on each interior edge"
            ),
            "edgeRowCountsInWindow": edge_counts,
            "bandVariable": (
                "derivedRemainingYears = 99 - lease age as of transaction month "
                "(leaseAgeValidation.derivation); the stored remaining_lease "
                "column covers only 2015-2016 and cannot band the study window"
            ),
            "sourceOfBins": (
                "- **Lease bands**: bins [0, 60, 70, 80, 90, 100], labels [<60, "
                "60-70, 70-80, 80-90, 90+] (the frozen appendix, adopted "
                "verbatim; the definition-as-executed code is retired — see "
                "absenceScans.bandDefinitionAsExecuted)"
            ),
        },
        "window": {
            "start": STUDY_WINDOW_START,
            "end": last_complete,
            "endBasis": "the article's stated data period start, capped at the measured cutoff",
            "rowsBandedInWindow": window_rows,
        },
        "bands": measured,
        "unitInvarianceMaxAbsDiffPsmVsPsfDiscount": _r(unit_invariance, 4),
        "articleRowsVsMeasured": comparison,
        "unitIdentification": {
            "articleColumnLabel": "Median PSF",
            "measuredNearestUnitByRow": {
                entry["id"]: entry["perAreaUnitIdentification"]["nearestMeasuredUnit"]
                for entry in comparison
            },
            "storedCsvColumnName": "median_psm",
            "storedCsvMatchesArticle": {
                "countMatches": sum(1 for entry in csv_matches if entry["matchesArticleCount"]),
                "perAreaMatchesAt0dp": sum(
                    1 for entry in csv_matches if entry["matchesArticlePerAreaAt0dp"]
                ),
                "medianPriceMatches": sum(
                    1 for entry in csv_matches if entry["matchesArticleMedianPrice"]
                ),
                "meaning": (
                    "the article's per-area column values equal the stored CSV's "
                    "median_psm column at integer rounding on all five bands "
                    "(the CSV's unrounded medians are 5,273.97 / 4,729.73 / "
                    "4,844.90 / 5,388.62 / 6,205.30; the article prints 5,274 / "
                    "4,730 / 4,845 / 5,389 / 6,205), and the stored per-band "
                    "chart is titled 'Median Price per SQM' — a measured "
                    "correspondence that identifies the published 'Median PSF' "
                    "column as per-square-metre values; it is a correspondence "
                    "between stored artefacts, not a proven lineage, because no "
                    "producer links them"
                ),
            },
        },
        "storedCsv": stored_csv,
        "storedCsvCountSum": csv_count_sum,
        "storedCsvCountSumMinusArticleSample": csv_count_sum - ARTICLE_STATED_SAMPLE,
        "measuredFacts": {
            "highestVolumeBandMeasured": highest_volume["id"],
            "highestVolumeBandCount": highest_volume["count"],
            "cheapestBandMeasuredByDerivedPsm": cheapest["id"],
            "cheapestBandMedianDerivedPsm": cheapest["medianDerivedPsm"],
            "notCheapestBand60Minus": next(entry for entry in measured if entry["id"] == "<60")[
                "medianDerivedPsm"
            ],
        },
        "shareArithmetic": {
            "articleStated": ARTICLE_TRADEOFF_SHARE,
            "articleOwnArithmetic": _r(54521 / ARTICLE_STATED_SAMPLE * 100, 4),
            "measured": next(entry for entry in measured if entry["id"] == "60-70")[
                "shareOfWindow"
            ],
            "meaning": (
                "the article's 24.4% equals 54,521 over 223,634 from its own "
                "table; the measured window share is recorded beside it"
            ),
        },
    }


def _read_csv_analysis() -> dict[str, Any]:
    text = CSV_ANALYSIS.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = list(csv.DictReader(io.StringIO(text)))
    parsed: list[dict[str, Any]] = []
    for row in rows:
        parsed.append(
            {
                "lease_band": row["lease_band"],
                "avg_remaining_lease_years": _number(
                    row["avg_remaining_lease_years"], "csv avg remaining"
                ),
                "median_price": _number(row["median_price"], "csv median price"),
                "median_psm": _number(row["median_psm"], "csv median psm"),
                "transaction_count": int(row["transaction_count"]),
                "discount_to_baseline": _number(row["discount_to_baseline"], "csv discount"),
                "annual_decay_pct": _number(row["annual_decay_pct"], "csv annual decay"),
            }
        )
    return {
        "path": _relative(CSV_ANALYSIS),
        "sha256": sha256_of(CSV_ANALYSIS),
        "bytes": int(CSV_ANALYSIS.stat().st_size),
        "columns": list(parsed[0].keys()) if parsed else [],
        "rows": parsed,
        "origin": (
            "unverified — a stored artefact whose producer code is retired (the "
            "article's own provenance says the legacy scripts were removed); "
            "its values are compared, not attributed"
        ),
    }


def town_table(hdb: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """The stated short-vs-fresh town comparison, re-measured for the six towns."""
    variables = _lease_variables(hdb)
    months = variables["months"]
    remaining = variables["remaining"]
    price = _numeric(hdb["price"])
    fa_sqm = _numeric(hdb["floor_area_sqm"])
    psm = price / fa_sqm
    town = _series(hdb["town"]).astype(str).str.strip().str.upper()
    window = (months >= STUDY_WINDOW_START) & (months <= last_complete)
    short_mask = window & remaining.notna() & (remaining < SHORT_LEASE_MAX_YEARS)
    fresh_mask = window & remaining.notna() & (remaining >= FRESH_LEASE_MIN_YEARS)

    rows: list[dict[str, Any]] = []
    article_by_id = {row["id"]: row for row in ARTICLE_TOWN_ROWS}
    for name in TOWN_TABLE_ARTICLE_TOWNS:
        town_mask = town == name
        short_rows = int((short_mask & town_mask).sum())
        fresh_rows = int((fresh_mask & town_mask).sum())
        med_short = float(np.median(psm[short_mask & town_mask])) if short_rows else None
        med_fresh = float(np.median(psm[fresh_mask & town_mask])) if fresh_rows else None
        article = article_by_id[name]
        article_arithmetic = (article["fresh"] - article["short"]) / article["fresh"] * 100
        rows.append(
            {
                "id": name,
                "measured": {
                    "shortMedianDerivedPsm": _r(med_short, 2),
                    "freshMedianDerivedPsm": _r(med_fresh, 2),
                    "shortRows": short_rows,
                    "freshRows": fresh_rows,
                    "discountFreshMinusShortOverFresh": _r(
                        (med_fresh - med_short) / med_fresh * 100
                        if med_short and med_fresh
                        else None,
                        2,
                    ),
                },
                "article": article,
                "articleOwnArithmetic": {
                    "discountFreshMinusShortOverFresh": _r(article_arithmetic, 2),
                    "inverseShortMinusFreshOverFresh": _r(-article_arithmetic, 2),
                    "meaning": (
                        "the article's published discount reproduces from its own "
                        "row values under (fresh - short) / fresh for every row, "
                        "including PASIR RIS at -20.21; the inverse of that same "
                        "quantity is what the technical findings print as "
                        "'Pasir Ris +20.2% (inverted)'"
                    ),
                },
                "measuredMinusArticleShort": _r(med_short - article["short"], 2)
                if med_short
                else None,
                "measuredMinusArticleFresh": _r(med_fresh - article["fresh"], 2)
                if med_fresh
                else None,
            }
        )

    pasir_ris = next(entry for entry in rows if entry["id"] == "PASIR RIS")
    pasir_measured = pasir_ris["measured"]
    sign_rows = []
    for entry in FINDINGS_TOWN_SIGNS:
        article = article_by_id[entry["id"]]
        article_value = _number(str(article["discountLabel"]).rstrip("%"), "article discount")
        sign_rows.append(
            {
                "id": entry["id"],
                "tableValue": article_value,
                "findingsValue": entry["value"],
                "findingsIsExactNegativeOfTable": _r(-entry["value"], 1) == _r(article_value, 1),
            }
        )

    return {
        "definition": {
            "shortLease": "derivedRemainingYears < 70",
            "freshLease": "derivedRemainingYears >= 90",
            "perAreaMeasure": "derivedPsm = price / floor_area_sqm (SGD per square metre)",
            "source": (
                "- **Town-level comparison**: short lease (<70 yr) vs fresh "
                "lease (90+ yr) median PSM within same town (the frozen "
                "appendix, adopted verbatim)"
            ),
            "windowStatus": (
                "the frozen text states NO window for the town table — recorded "
                "as underspecified and not chosen for it; this ledger re-measures "
                "under the article's stated data period start capped at the "
                "measured cutoff, and the window is a field"
            ),
            "window": {"start": STUDY_WINDOW_START, "end": last_complete},
        },
        "towns": rows,
        "pasirRisInversion": {
            "articleRowShort": article_by_id["PASIR RIS"]["short"],
            "articleRowFresh": article_by_id["PASIR RIS"]["fresh"],
            "articleRowDiscountLabel": article_by_id["PASIR RIS"]["discountLabel"],
            "articleRowOwnArithmetic": pasir_ris["articleOwnArithmetic"],
            "findingsValue": 20.2,
            "measuredShortMedianDerivedPsm": pasir_measured["shortMedianDerivedPsm"],
            "measuredFreshMedianDerivedPsm": pasir_measured["freshMedianDerivedPsm"],
            "measuredShortBelowFresh": (
                pasir_measured["shortMedianDerivedPsm"] is not None
                and pasir_measured["freshMedianDerivedPsm"] is not None
                and pasir_measured["shortMedianDerivedPsm"]
                < pasir_measured["freshMedianDerivedPsm"]
            ),
            "meaning": (
                "the article's own row shows short-lease PSM ABOVE fresh-lease "
                "PSM; the table prints that as a -20.2% 'Discount' and the "
                "technical findings print the SAME row as +20.2% '(inverted)' — "
                "exact sign flips of one quantity computed on the row's own "
                "values with the fresh PSM as denominator. The measured window "
                "does NOT reproduce the inversion: short-lease median PSM sits "
                "BELOW fresh-lease median PSM for Pasir Ris here"
            ),
        },
        "signConventions": {
            "rows": sign_rows,
            "meaning": (
                "the table prints the six discounts as (fresh - short)/fresh; "
                "the technical findings restate four of them with the opposite "
                "sign; each restatement is the exact negative of the table "
                "value (findingsIsExactNegativeOfTable), so the two surfaces "
                "disagree on convention, not on magnitude"
            ),
        },
    }


def sample_claim(hdb: pd.DataFrame, last_complete: str) -> dict[str, Any]:
    """The stated 223,634 sample and 30-99 lease range, measured."""
    variables = _lease_variables(hdb)
    months = variables["months"]
    remaining = variables["remaining"]
    window = (months >= STUDY_WINDOW_START) & (months <= last_complete)
    window_rows = int(window.sum())

    frame_last_month = str(months.max())
    candidate_months = tuple(
        terminal
        for terminal in CANDIDATE_TERMINAL_MONTHS
        if terminal <= frame_last_month and bool((months == terminal).any())
    )
    candidates = []
    for terminal in candidate_months:
        mask = (months >= STUDY_WINDOW_START) & (months <= terminal)
        rows = int(mask.sum())
        candidates.append(
            {
                "terminalMonth": terminal,
                "rows": rows,
                "differenceFromStatedSample": rows - ARTICLE_STATED_SAMPLE,
                "equalsStatedSample": rows == ARTICLE_STATED_SAMPLE,
            }
        )
    return {
        "articleStatement": (
            "- **Sample**: 223,634 HDB transactions, 2017-2026, lease range 30-99 years"
        ),
        "statedSample": ARTICLE_STATED_SAMPLE,
        "statedLeaseRangeYears": list(ARTICLE_STATED_LEASE_RANGE),
        "measuredWindowRows": window_rows,
        "measuredMinusStated": window_rows - ARTICLE_STATED_SAMPLE,
        "measuredLeaseRangeYearsWindow": {
            "min": _r(float(remaining[window].min()), 4),
            "max": _r(float(remaining[window].max()), 4),
        },
        "candidateWindows": candidates,
        "candidateCount": len(candidates),
        "anyCandidateEqualsStatedSample": any(c["equalsStatedSample"] for c in candidates),
        "meaning": (
            "no month-capped window starting 2017-01 with a terminal month from "
            "2025-01 through 2026-11 reproduces the stated 223,634 (the "
            "candidate count is recorded explicitly), and the window's measured remaining-lease "
            "range differs from the stated 30-99; the stated sample stands as "
            "the legacy's own figure, unreproduced"
        ),
    }


def interactive_asset(town_values: Any, window_rows: int) -> dict[str, Any]:
    """The stored interactive tool asset, inventoried and cross-checked."""
    payload = _gz_payload(INTERACTIVE_ASSET)
    bands = list(payload["bands"])
    insights = dict(payload["insights"])
    town_rates = dict(payload["town_decay_rates"])

    age_bins_expected = [f"{lo}-{lo + 5}" for lo in range(0, 100, 5)]
    present_age_bins = [str(band["lease_age_band"]) for band in bands]
    absent_age_bins = [one_bin for one_bin in age_bins_expected if one_bin not in present_age_bins]
    count_sum = sum(int(band["transaction_count"]) for band in bands)

    band_rows = []
    for band in bands:
        band_rows.append(
            {
                "leaseAgeBand": str(band["lease_age_band"]),
                "minLeaseYears": _r(band["min_lease_years"], 1),
                "maxLeaseYears": _r(band["max_lease_years"], 1),
                "transactionCount": int(band["transaction_count"]),
                "discountPercent": _r(band["discount_percent"], 3),
                "annualDecayRate": _r(band["annual_decay_rate"], 4),
                "riskZone": str(band["risk_zone"]),
                "volumeCategory": str(band["volume_category"]),
            }
        )

    csv_rows = {row["lease_band"]: row for row in _read_csv_analysis()["rows"]}
    article_by_id = {row["id"]: row for row in ARTICLE_BAND_ROWS}
    insight_keys = {
        "60-70 years remaining": "60-70",
        "70-80 years remaining": "70-80",
        "90+ years remaining": "90+",
    }
    insight_rows = []
    for key in sorted(insights):
        entry = dict(insights[key])
        band_label = str(entry.get("band"))
        article_id = insight_keys.get(band_label)
        article = article_by_id.get(article_id) if article_id else None
        csv_row = csv_rows.get(f"{article_id} years") if article_id else None
        insight_rows.append(
            {
                "key": key,
                "stored": {
                    "band": band_label,
                    "discount": _r(entry.get("discount"), 3),
                    "annualRate": _r(entry.get("annual_rate"), 3),
                    "description": str(entry.get("description")),
                },
                "articleComparison": {
                    "articleDiscountLabel": article["discountLabel"] if article else None,
                    "discountEqualsAbsArticleDiscount": (
                        _r(entry.get("discount"), 1)
                        == _r(
                            abs(
                                _number(
                                    str(article["discountLabel"]).rstrip("%"), "article discount"
                                )
                            ),
                            1,
                        )
                        if article and article["discountLabel"] != "baseline"
                        else _r(entry.get("discount"), 1) == 0.0
                    ),
                    "meaning": (
                        "for 60-70 and 70-80 the stored insight discount equals "
                        "the magnitude of the article's published discount; for "
                        "90+ the article's own table calls the band the "
                        "BASELINE (0.0) while the insight stores 5.2 — the "
                        "insight block is not on the article's baseline "
                        "convention"
                    )
                    if key == "safe_zone"
                    else (
                        "the stored insight discount equals the magnitude of "
                        "the article's published discount for this band"
                    ),
                },
                "storedCsvComparison": {
                    "csvAnnualDecayPct": _r(csv_row["annual_decay_pct"], 3) if csv_row else None,
                    "annualRateMatchesCsv": (
                        _r(entry.get("annual_rate"), 2) == _r(csv_row["annual_decay_pct"], 2)
                        if csv_row
                        else None
                    ),
                    "differenceFromCsvAnnualDecay": _r(
                        entry.get("annual_rate") - csv_row["annual_decay_pct"], 3
                    )
                    if csv_row
                    else None,
                },
            }
        )

    frame_towns = sorted({str(value).strip().upper() for value in town_values})
    town_rows = []
    for name in TOWN_TABLE_ARTICLE_TOWNS:
        town_rows.append({"id": name, "stored": town_rates.get(name)})

    return {
        "path": _relative(INTERACTIVE_ASSET),
        "sha256": sha256_of(INTERACTIVE_ASSET),
        "bytes": int(INTERACTIVE_ASSET.stat().st_size),
        "topLevelKeys": sorted(str(key) for key in payload),
        "bands": band_rows,
        "bandCount": len(bands),
        "ageCoverage": {
            "expectedAgeBins0To99": len(age_bins_expected),
            "presentBins": present_age_bins,
            "absentBins": absent_age_bins,
            "absentBinCount": len(absent_age_bins),
            "meaning": (
                "the asset bands LEASE AGE in five-year bins; seven of the "
                "twenty bins 0-99 are absent rows in the asset (ages 60-90 and "
                "95-99, i.e. remaining lease of about 4-39 years has no band "
                "row) — an absence inside the asset, counted, not a claim "
                "about the market"
            ),
        },
        "countSum": count_sum,
        "countSumVersus": {
            "articleStatedSample": ARTICLE_STATED_SAMPLE,
            "differenceFromArticleSample": count_sum - ARTICLE_STATED_SAMPLE,
            "measuredWindowRows": window_rows,
            "differenceFromMeasuredWindow": count_sum - window_rows,
            "meaning": (
                "three populations, none equal: the asset's 13 band counts sum "
                "to their own total, which reproduces neither the article's "
                "stated sample nor the measured window"
            ),
        },
        "discountBaseline": {
            "zeroDiscountBand": "0-5",
            "note": (
                "screened as: the only band storing discount 0.0 is the "
                "freshest age band (0-5), so the stored discounts are "
                "relative to the freshest band, not to the article's 90+ "
                "remaining-years baseline; origin unverified (no producer "
                "linked). Two bands store NEGATIVE discounts (5-10 at -11.02, "
                "10-15 at -18.58, i.e. above the stored baseline), and the "
                "90-95 age band is the only one labelled risk_zone 'safe' "
                "(twelve store 'cliff')"
            ),
        },
        "insights": insight_rows,
        "townDecayRates": {
            "townCount": len(town_rates),
            "articleTownEntries": town_rows,
            "labelPattern": "Avg Decay (Lease: NNy)",
            "frameTownCount": len(frame_towns),
            "intersectionCount": len(set(frame_towns) & set(town_rates)),
            "assetOnlyTowns": sorted(set(town_rates) - set(frame_towns)),
            "frameOnlyTowns": sorted(set(frame_towns) - set(town_rates)),
            "meaning": (
                "the asset's 30 towns and the frame's HDB towns overlap in 23 "
                "names; seven asset towns (e.g. DOWNTOWN CORE, ROCHOR) are not "
                "HDB resale towns in the frame and four frame towns "
                "(BUKIT BATOK, CENTRAL AREA, KALLANG/WHAMPOA, LIM CHU KANG) "
                "are absent from the asset — including the KALLANG naming "
                "split — so the asset's town universe is not the frame's"
            ),
        },
        "lineage": {
            "statement": (
                "screened as, origin unverified: nothing in this checkout links "
                "the asset's producer to the article's computation (the legacy "
                "scripts are retired per the article's own provenance, and the "
                "token scan finds no lease-decay implementation on the shipping "
                "surface). Because the asset is UNLINKED, it is evidence "
                "neither for nor against the article's numbers — the "
                "correspondences below are recorded in both directions"
            ),
            "insightsMatchArticleDiscounts": {
                "matches": [
                    entry["key"]
                    for entry in insight_rows
                    if entry["articleComparison"]["discountEqualsAbsArticleDiscount"]
                    and entry["key"] != "safe_zone"
                ],
                "disagreements": [
                    entry["key"] for entry in insight_rows if entry["key"] == "safe_zone"
                ],
                "meaning": (
                    "two of three insight discounts equal the magnitudes of the "
                    "article's published discounts; the third (safe_zone 5.2) "
                    "disagrees with the article's own baseline convention "
                    "(90+ is the baseline, 0.0). A match of stored numbers is a "
                    "correspondence, not a proven lineage"
                ),
            },
            "bandingIsADifferentTaxonomy": (
                "the article bands REMAINING YEARS into five bands [0,60,70,80,"
                "90,100]; the asset bands LEASE AGE into thirteen five-year bins "
                "with a freshest-band discount baseline and seven absent age "
                "bins — both bandings exist in the checkout, they are not the "
                "same definition, and neither is derived from the other here"
            ),
            "provenancePathCheck": {
                "articleProvenanceSays": (
                    "the current canonical assets for this page are the markdown "
                    "plus 'the precomputed files served from "
                    "app/public/data/analysis/'"
                ),
                "interactiveAssetPath": _relative(INTERACTIVE_ASSET),
                "leaseDecayAssetsUnderAnalysis": _relative(PNG_ADVANCED.parent),
                "meaning": (
                    "the interactive asset the tool serves lives under "
                    "app/public/data/interactive_tools/, not under "
                    "app/public/data/analysis/; the analysis directory holds "
                    "only the lease_decay_advanced PNG for this series — a "
                    "location discrepancy between the article's provenance "
                    "sentence and the checkout, recorded as measured"
                ),
            },
        },
    }


def stored_artefacts() -> dict[str, Any]:
    """The two CSVs and four PNGs beside the article, sha-pinned, reads recorded."""
    csv_price_text = CSV_PRICE_STATS.read_text(encoding="utf-8")
    price_rows: list[dict[str, Any]] = [
        {
            "lease_band": row["lease_band"],
            "resale_price_count": int(row["resale_price_count"]),
            "resale_price_median": _number(row["resale_price_median"], "csv median"),
            "resale_price_mean": _number(row["resale_price_mean"], "csv mean"),
            "resale_price_std": _number(row["resale_price_std"], "csv std"),
            "price_per_sqm_median": _number(row["price_per_sqm_median"], "csv psm median"),
            "price_per_sqm_mean": _number(row["price_per_sqm_mean"], "csv psm mean"),
            "remaining_lease_years_min": _number(row["remaining_lease_years_min"], "csv rem min"),
            "remaining_lease_years_max": _number(row["remaining_lease_years_max"], "csv rem max"),
            "remaining_lease_years_mean": _number(
                row["remaining_lease_years_mean"], "csv rem mean"
            ),
        }
        for row in csv.DictReader(io.StringIO(csv_price_text))
    ]
    pngs = {}
    for key, path in (
        ("lease_decay_price_distribution.png", PNG_PRICE_DISTRIBUTION),
        ("lease_decay_psm_by_band.png", PNG_PSM_BY_BAND),
        ("lease_decay_transaction_volume.png", PNG_TRANSACTION_VOLUME),
        ("lease_decay_advanced_analysis.png", PNG_ADVANCED),
    ):
        pngs[key] = {
            "path": _relative(path),
            "sha256": sha256_of(path),
            "bytes": int(path.stat().st_size),
            "visualRead": PNG_VISUAL_READS[key],
        }
    return {
        "leaseAnalysisCsv": _read_csv_analysis(),
        "leasePriceStatisticsCsv": {
            "path": _relative(CSV_PRICE_STATS),
            "sha256": sha256_of(CSV_PRICE_STATS),
            "bytes": int(CSV_PRICE_STATS.stat().st_size),
            "rows": price_rows,
            "meaning": (
                "the same five bands with rounded statistics; its "
                "price_per_sqm_median column repeats the article's per-area "
                "values (5274/4730/4845/5389/6205), its remaining_lease_years "
                "min/max are integers consistent with right-closed bins at "
                "month-integer precision, and its resale_price_count column "
                "repeats the article's counts — recorded as stored artefacts "
                "whose producer is retired; origin unverified"
            ),
        },
        "pngs": pngs,
        "visualReadMethod": (
            "HUMAN VISUAL READ of the sha-pinned PNGs by the producer, "
            "recorded because the pixels are not machine-read; the hashes pin "
            "exactly which images were read. Each PNG is an UNLINKED artefact: "
            "evidence neither for nor against the article's computation"
        ),
        "coefficientAxisLabel": {
            "value": "Coefficient (SGD/PSM per year)",
            "where": "lease_decay_advanced_analysis.png, panel 4",
            "meaning": (
                "screened as: the only unit label anywhere in the checkout for "
                "the legacy lease coefficient is this chart axis, and it says "
                "PSM per year while the article sentence says PSF. The chart is "
                "unlinked, so this is recorded as a screen, not as the "
                "coefficient's confirmed unit — the unit stays UNCONFIRMED and "
                "no conversion is performed"
            ),
        },
    }


def regression_inputs(hdb: pd.DataFrame) -> dict[str, Any]:
    """What the legacy specification needs, measured on the HDB rows."""
    floor_level_non_null = int(_series(hdb["floor_level"]).notna().sum())
    mrt = _numeric(hdb["dist_to_nearest_mrt"])
    town = _series(hdb["town"]).astype(str).str.strip()
    town_non_empty = int((town != "").sum())
    return {
        "regressors": {
            "leaseTerm": {
                "available": True,
                "measure": "derivedRemainingYears (leaseAgeValidation.derivation)",
            },
            "floorLevel": {
                "available": False,
                "hdbNonNullRows": floor_level_non_null,
                "hdbRowTotal": int(len(hdb)),
                "status": (
                    "four-states: the column exists in the 97-column schema and "
                    "is null on ALL 990,655 HDB rows (it belongs to the private "
                    "rows), so the stated FloorLevel term is not measurable on "
                    "HDB rows from this frame"
                ),
            },
            "distToMrt": {
                "available": True,
                "hdbNonNullRows": int(mrt.notna().sum()),
                "hdbNullRows": int(mrt.isna().sum()),
            },
            "town": {
                "available": True,
                "hdbNonEmptyRows": town_non_empty,
                "distinctTowns": int(town.nunique()),
            },
        },
        "coefficient": {
            "sentenceValue": ARTICLE_COEFFICIENT,
            "sentenceUnit": "PSF per extra year",
            "appendixResponse": "price_per_sqm",
            "unitConfirmable": False,
            "conversionPerformed": False,
            "fittedModelPresent": False,
            "status": "withdrawn",
            "reason": (
                "the frozen text contradicts itself on the response unit (the "
                "appendix names price_per_sqm, the sentence says PSF, and the "
                "only unit label in the checkout — an unlinked chart axis — "
                "says SGD/PSM per year); the fitted model is absent (see "
                "absenceScans.fittedModel), so the coefficient's original "
                "response/unit cannot be confirmed and the gate forbids "
                "converting it. The number is not restated in any unit"
            ),
            "ledgerKey": "regressionInputs.coefficient",
        },
        "hedonicSpecification": {
            "specification": (
                "Price = beta0 + beta1(Lease) + beta2(FloorLevel) + "
                "beta3(DistToMRT) + beta4(Town) + epsilon"
            ),
            "status": "withdrawn",
            "reason": (
                "no fitted model exists in this checkout "
                "(absenceScans.fittedModel) and the stated FloorLevel term is "
                "null on every HDB row, so the specification is not runnable as "
                "stated on the shipped frame; no coefficients exist to convert "
                "and none are estimated here"
            ),
            "ledgerKey": "absenceScans.fittedModel",
        },
        "policyThreshold": {
            "method": "Mann-Whitney U tests at the 60-yr and 30-yr marks",
            "status": "notReproducible",
            "reason": (
                "no implementation or stored result exists on the shipping "
                "surface (tokenScan token 'Mann-Whitney' matches prose only), "
                "and the test populations, window and alternative are unstated "
                "in the frozen text — underspecified, and not chosen for it"
            ),
            "ledgerKey": "absenceScans.tokenScan.tokens.Mann-Whitney",
        },
        "balaCurve": {
            "method": "empirical vs theoretical depreciation, >=5% deviation flagged",
            "status": "notReproducible",
            "reason": (
                "the Bala curve's parameters are unstated in the frozen text "
                "and no implementation or stored result exists on the shipping "
                "surface (tokenScan token 'Bala' matches prose only). An "
                "unlinked PNG depicts a Bala validation "
                "(storedArtefacts.pngs.lease_decay_advanced_analysis.png) — "
                "recorded symmetrically: it neither confirms nor refutes the "
                "legacy computation"
            ),
            "ledgerKey": "absenceScans.tokenScan.tokens.Bala",
        },
        "splineArbitrage": {
            "method": "BUY/SELL/HOLD signals where the market deviates >=5% from the Bala curve",
            "status": "notReproducible",
            "reason": (
                "no implementation, signal table or threshold artefact exists "
                "for this method; it inherits the Bala curve's unstated "
                "parameters"
            ),
            "ledgerKey": "regressionInputs.balaCurve",
        },
        "annualDecayApproximation": {
            "method": "linear approximation from discount vs years elapsed",
            "status": "notReproducible",
            "reason": (
                "the approximation is underspecified in the frozen text: no "
                "formula for 'years elapsed', no baseline band named. A stored "
                "CSV carries annual_decay_pct values and the interactive asset "
                "carries annual_decay_rate values that disagree with the CSV at "
                "two of three insight points (interactiveAsset.insights) — both "
                "unlinked, so neither is adopted as the legacy's rate"
            ),
            "ledgerKey": "storedArtefacts.leaseAnalysisCsv.rows",
        },
        "fitPerformedByThisPack": False,
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
            if any(
                relative.startswith(prefix) and not relative.startswith(RETAINED_EDITION_PREFIX)
                for prefix in EXCLUDED_SCAN_PREFIXES
            ):
                continue
            if relative in EXCLUDED_SCAN_PATHS:
                continue
            paths.append(path)
    return sorted(paths)


def _token_scan(paths: list[Path]) -> dict[str, Any]:
    tokens: dict[str, Any] = {}
    for token, case_sensitive in METHOD_TOKENS:
        needle = token if case_sensitive else token.lower()
        matches: list[dict[str, Any]] = []
        for path in paths:
            lines = path.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, start=1):
                haystack = line if case_sensitive else line.lower()
                if needle in haystack:
                    matches.append(
                        {
                            "path": _relative(path),
                            "line": number,
                            "quote": line.strip()[:160],
                        }
                    )
        tokens[token] = {
            "matchCase": case_sensitive,
            "occurrences": len(matches),
            "files": sorted({match["path"] for match in matches}),
            "fileCount": len({match["path"] for match in matches}),
            "firstMatches": matches[:8],
        }
    return tokens


def _filenames_under_data(token: str) -> list[str]:
    """Every file under data/ whose name carries `token`, case-insensitively.

    The field this feeds is labelled `filenameMatchesUnderData`, so it must come
    from a filename scan of that root for that token. Filtering another token's
    match list by `path.startswith("data/")` produced lease-decay artefacts under
    a label naming the retired housing_hdb_transaction frame; enumerating the
    labelled token is the only way the field can enumerate the files it names.
    """
    base = REPO_ROOT / "data"
    if not base.exists():
        return []
    return sorted(
        _relative(path) for path in base.rglob("*") if path.is_file() and token in path.name.lower()
    )


def _filename_scan() -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for root in FILENAME_SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            relative = _relative(path)
            if any(
                relative.startswith(prefix)
                and not relative.startswith(FILENAME_SCAN_RETAINED_EDITION_PREFIX)
                for prefix in FILENAME_SCAN_EXCLUDED_PREFIXES
            ):
                continue
            if relative in FILENAME_SCAN_EXCLUDED_PATHS:
                continue
            if FILENAME_TOKEN in path.name.lower():
                matches.append(
                    {
                        "path": relative,
                        "bytes": int(path.stat().st_size),
                        "substringNote": (
                            "filename contains 'release', not the lease-decay "
                            "series — recorded, not filtered"
                        )
                        if "release" in path.name.lower()
                        else None,
                    }
                )
    return {
        "token": FILENAME_TOKEN,
        "roots": list(FILENAME_SCAN_ROOTS),
        "excludedPrefixes": list(FILENAME_SCAN_EXCLUDED_PREFIXES),
        "retainedEditionPrefix": FILENAME_SCAN_RETAINED_EDITION_PREFIX,
        "excludedPaths": list(FILENAME_SCAN_EXCLUDED_PATHS),
        "matches": matches,
        "matchCount": len(matches),
        "seriesMatches": [m["path"] for m in matches if m["substringNote"] is None],
    }


def absence_scans() -> dict[str, Any]:
    """Every absence with its boundary: roots, matched files, counts."""
    l1_named = REPO_ROOT / LEGACY_L1_PATH
    l3_named = REPO_ROOT / LEGACY_L3_PATH
    parquets_root = REPO_ROOT / "data" / "parquets"
    filename_scan = _filename_scan()
    l1_filename_matches = _filenames_under_data(LEGACY_L1_FILENAME_TOKEN)
    l3_filename_matches = _filenames_under_data(LEGACY_L3_FILENAME_TOKEN)
    token_scan_files = _scan_files()
    scanned_files = [
        {
            "path": _relative(path),
            "sha256": sha256_of(path),
            "bytes": int(path.stat().st_size),
        }
        for path in sorted(token_scan_files, key=_relative)
    ]
    return {
        "l1Frame": {
            "namedPath": LEGACY_L1_PATH,
            "namedPathExists": l1_named.is_file(),
            "dataParquetsRootExists": parquets_root.exists(),
            "filenameMatchesUnderData": l1_filename_matches,
            "status": "absent",
            "meaning": (
                "the article's primary input does not exist in this checkout: "
                "the data/parquets root is absent and no data/ file name "
                "carries housing_hdb_transaction (zero matches). The legacy "
                "producer that read it is retired — an absence with a boundary, "
                "not a claim about the source's history"
            ),
        },
        "l3Frame": {
            "namedPath": LEGACY_L3_PATH,
            "namedPathExists": l3_named.is_file(),
            "filenameMatchesUnderData": l3_filename_matches,
            "meaning": (
                "the article's advanced regression input does not exist; the "
                "only data/ files whose names carry housing_unified are the two "
                "segmented panels under data/analysis/market_segmentation* "
                "(RS10's adjacent panels, a different subject), and "
                "filenameMatchesUnderData enumerates them"
            ),
        },
        "fittedModel": {
            "status": "absent",
            "filenameScan": {
                "token": filename_scan["token"],
                "roots": filename_scan["roots"],
                "excludedPrefixes": filename_scan["excludedPrefixes"],
                "retainedEditionPrefix": filename_scan["retainedEditionPrefix"],
                "excludedPaths": filename_scan["excludedPaths"],
                "exclusionMeaning": (
                    "the programme's own surfaces are excluded and disclosed "
                    "here: docs/implementation/ (this ledger and this study's "
                    "evidence prose, whose file names contain 'lease' — a "
                    "hash-pinned scan cannot read its own output), "
                    "scripts/tools/ (this producer and its sibling evidence "
                    "tools), prompts/ (the programme's runbooks), the D12 "
                    "decision register docs/plans/2026-11-12-reporting-refresh-"
                    "decisions.md, and published edition texts under "
                    "docs/analytics/editions/ except editions/legacy/ — the "
                    "frozen legacy corpus stays IN the scan"
                ),
                "matchCount": filename_scan["matchCount"],
                "matches": filename_scan["matches"],
            },
            "meaning": (
                "absence is supported among the filename scan's lease-named "
                "matches only — a filename-token scan, not an inventory of "
                "every file name or artefact content in the scanned roots. "
                "The matches are this series' stored CSV/PNG/JSON artefacts, "
                "the article texts, and two release-named files whose names "
                "merely contain the substring 'lease' (recorded, not "
                "filtered); no match is a fitted lease-decay model artefact "
                "(coefficients, pickle, joblib, parameter file). The "
                "coefficient therefore has no stored source located by this "
                "scan and no refit is attempted"
            ),
        },
        "bandDefinitionAsExecuted": {
            "status": "absent",
            "tokenScanReference": "absenceScans.tokenScan.tokens.bins [0, 60, 70, 80, 90, 100]",
            "meaning": (
                "the stated bins appear only in the frozen legacy text and its "
                "live twin (prose), and in no code file on the scanned surface; "
                "the L1 code that executed the banding is retired with its "
                "frame. The definition THIS ledger uses is the stated bins "
                "re-implemented in this producer (bandTable.definition)"
            ),
        },
        "tokenScan": {
            "roots": list(SCAN_ROOTS),
            "suffixes": list(SCAN_SUFFIXES),
            "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
            "retainedEditionPrefix": RETAINED_EDITION_PREFIX,
            "excludedPaths": list(EXCLUDED_SCAN_PATHS),
            "filesScanned": len(token_scan_files),
            "scannedFiles": scanned_files,
            "scannedFilesManifestSha256": hashlib.sha256(
                canonical_bytes(scanned_files)
            ).hexdigest(),
            "tokens": _token_scan(token_scan_files),
            "meaning": (
                "no lease-decay implementation was found on the scanned "
                "surface: every token match is prose (the frozen legacy texts, "
                "their live twins, plan/archive documents) or this series' "
                "stored-asset wiring in the app. Hits are NOT claimed to be "
                "uniformly prose or false positives — the files list records "
                "every one. The programme's own surfaces are excluded and the "
                "exclusion is disclosed here: app/src/components/studies/ "
                "(edition registry/pages), app/tests/ (fixtures), "
                ".secrets.baseline, and "
                "docs/plans/2026-11-12-reporting-refresh-decisions.md (D12 "
                "register) are excluded; the frozen legacy originals stay "
                "IN the scan because the article's method claims are what the "
                "tokens are matched against. Every scanned file is pinned by "
                "sha256 and byte count in scannedFiles; "
                "scannedFilesManifestSha256 binds the set, and filesScanned is "
                "its length"
            ),
        },
    }


def gates() -> dict[str, Any]:
    """Chart and model gates, recorded as in force with their sources."""
    chart_quote = _code_quote(STUDIES_TS, "Unit review required", "chart-gate note")
    return {
        "gateClause": GATE_CLAUSE,
        "gateClauseSource": _code_quote(
            RESEARCH_REGISTER,
            "Resolve PSF/PSM and total-price versus per-area",
            "research-register RS06 gate",
        ),
        "chartGate": {
            "status": "inForce",
            "encodedAt": {
                "path": _relative(STUDIES_TS),
                "sha256": sha256_of(STUDIES_TS),
                "unitReview": True,
                "chartsWithheld": True,
                "quote": chart_quote,
            },
            "meaning": (
                "the app already withholds lease-decay charts pending unit and "
                "discount-arithmetic reconciliation; this pack changes no app "
                "code, and the gate stays until repaired tables are reviewed"
            ),
        },
        "modelGate": {
            "status": "inForce",
            "fitPerformed": False,
            "repairedCoefficientExists": False,
            "meaning": (
                "no model is fitted by this pack and no repaired coefficient "
                "exists to review; the response decision "
                "(responseDecision.decision) binds any future fitting, and the "
                "model gate stays until a reviewed coefficient with a "
                "confirmed unit exists"
            ),
        },
        "editionText": {
            "writtenByThisPack": False,
            "meaning": (
                "this evidence pack is round 1 pending review; no edition text "
                "is drafted and no wording is repaired until the review chain "
                "records it"
            ),
        },
    }


LEGACY_CLAIMS: tuple[dict[str, str], ...] = (
    {
        "id": "C1",
        "phrase": (
            "it concentrates around the **70-80 year** lease band, where prices "
            "are about **21.9%** below the 90+ year baseline"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.articleRowsVsMeasured.70-80",
        "note": (
            "the sentence says PRICES; the article's own 21.9 reproduces from "
            "its PER-AREA column (21.92) and not from its Median Price column "
            "(1.79), and the measured window gives 21.72 on the per-area "
            "response and 2.65 on median price — the mixing is recorded in "
            "articleOwnArithmetic, not repaired by choosing a reading"
        ),
    },
    {
        "id": "C2",
        "phrase": (
            "| 90+ years   | 93.5 years          | $558,000     | $6,205     "
            "| baseline            | 50,912       |"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.articleRowsVsMeasured.90+",
        "note": (
            "every field re-measured on the window; the per-area value 6,205 "
            "measures as per-square-metre scale (median PSF 586.19, median "
            "derived PSM 6,309.73), and the stored CSV's median_psm column "
            "rounds to the article's exact value (6,205.30 -> 6,205)"
        ),
    },
    {
        "id": "C3",
        "phrase": (
            "| 80-90 years | 84.6 years          | $520,000     | $5,389     "
            "| -13.2%              | 29,562       |"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.articleRowsVsMeasured.80-90",
        "note": (
            "re-measured; the measured 80-90 per-area median sits far above the "
            "article's (measuredMinusArticle +848.0) — the article's U-shape "
            "does not reproduce in this window at this magnitude"
        ),
    },
    {
        "id": "C4",
        "phrase": (
            "| 70-80 years | 75.4 years          | $548,000     | $4,845     "
            "| -21.9%              | 47,044       |"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.articleRowsVsMeasured.70-80",
        "note": (
            "re-measured; the measured per-area discount 21.72 is the closest "
            "of the five bands to the article's figure, at a different level"
        ),
    },
    {
        "id": "C5",
        "phrase": (
            "| 60-70 years | 64.6 years          | $446,000     | $4,730     "
            "| -23.8%              | 54,521       |"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.articleRowsVsMeasured.60-70",
        "note": (
            "re-measured; the measured mean remaining years 64.6 equals the "
            "article's to one decimal, the other fields differ by the recorded "
            "amounts"
        ),
    },
    {
        "id": "C6",
        "phrase": (
            "| <60 years   | 54.5 years          | $390,000     | $5,274     "
            "| -15.0%              | 41,595       |"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.articleRowsVsMeasured.<60",
        "note": ("re-measured on the window; differences recorded field by field"),
    },
    {
        "id": "C7",
        "phrase": (
            "| Discount vs 90+ years | -23.8%                     | Large "
            "entry-price reduction              |"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.shareArithmetic",
        "note": (
            "the value reproduces from the article's own PER-AREA column "
            "(-23.77) and not from its Median Price column (-20.07); measured "
            "per-area discount 24.2 and median-price discount 18.05 are "
            "recorded beside it — a per-area discount quoted in a total-price "
            "column, the mixing the gate flags"
        ),
    },
    {
        "id": "C8",
        "phrase": (
            "| Share of transactions | 24.4%                      | Resale "
            "market remains active             |"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.shareArithmetic",
        "note": (
            "24.4 = 54,521 / 223,634 from the article's own table; the "
            "measured window share 0.2348 is recorded beside it"
        ),
    },
    {
        "id": "C9",
        "phrase": (
            "| Pure lease effect     | +$54.75 PSF per extra year | Lease still "
            "has measurable pricing power |"
        ),
        "status": "withdrawn",
        "ledgerKey": "regressionInputs.coefficient",
        "note": (
            "the gate forbids converting a coefficient whose original "
            "response/unit is unconfirmed; the frozen text contradicts itself "
            "(appendix response price_per_sqm vs sentence PSF), the fitted "
            "model is absent (absenceScans.fittedModel), and the only unit "
            "label in the checkout is an unlinked chart axis reading SGD/PSM "
            "per year. The number is not restated in any unit"
        ),
    },
    {
        "id": "C10",
        "phrase": "| CLEMENTI    | $5,224            | $8,796            | 40.6%      |",
        "status": "re-measured",
        "ledgerKey": "townTable.towns.CLEMENTI",
        "note": (
            "the published discount reproduces from the row's own values "
            "(40.61); the measured window gives 40.99 — one of the six towns "
            "whose measured figure is close to the article's"
        ),
    },
    {
        "id": "C11",
        "phrase": "| TOA PAYOH   | $4,939            | $8,182            | 39.6%      |",
        "status": "re-measured",
        "ledgerKey": "townTable.towns.TOA PAYOH",
        "note": "measured 52.13 against the article's 39.6; difference recorded",
    },
    {
        "id": "C12",
        "phrase": "| QUEENSTOWN  | $5,526            | $9,048            | 38.9%      |",
        "status": "re-measured",
        "ledgerKey": "townTable.towns.QUEENSTOWN",
        "note": "measured 42.59 against the article's 38.9; difference recorded",
    },
    {
        "id": "C13",
        "phrase": "| WOODLANDS   | $4,262            | $4,544            | 6.2%       |",
        "status": "re-measured",
        "ledgerKey": "townTable.towns.WOODLANDS",
        "note": "measured 18.62 against the article's 6.2; difference recorded",
    },
    {
        "id": "C14",
        "phrase": "| JURONG WEST | $4,496            | $4,516            | 0.4%       |",
        "status": "re-measured",
        "ledgerKey": "townTable.towns.JURONG WEST",
        "note": (
            "measured 27.44 against the article's 0.4; the table's small "
            "discount does not reproduce in this window"
        ),
    },
    {
        "id": "C15",
        "phrase": "| PASIR RIS   | $5,621            | $4,676            | -20.2%     |",
        "status": "re-measured",
        "ledgerKey": "townTable.pasirRisInversion",
        "note": (
            "the row's own values give -20.21 under (fresh-short)/fresh and "
            "+20.21 inverted, which is what the findings print; the measured "
            "window does NOT reproduce the inversion (short median PSM below "
            "fresh). The table and findings disagree on sign, not magnitude"
        ),
    },
    {
        "id": "C16",
        "phrase": ("- **90+ year band**: 50,912 transactions, median $558,000, median PSM $6,205"),
        "status": "re-measured",
        "ledgerKey": "bandTable.unitIdentification",
        "note": (
            "the findings label the SAME numbers PSM that the band table labels "
            "PSF — the legacy's own surfaces disagree, and the measured "
            "identification (stored CSV column median_psm; chart titled per "
            "SQM) resolves which unit the VALUES hold, not which label is right"
        ),
    },
    {
        "id": "C17",
        "phrase": ("- **70-80 yr band**: 47,044 transactions, -21.9% discount (steepest penalty)"),
        "status": "re-measured",
        "ledgerKey": "bandTable.articleRowsVsMeasured.70-80",
        "note": "same quantity as C4; measured value recorded beside it",
    },
    {
        "id": "C18",
        "phrase": (
            "- **60-70 yr band**: 54,521 transactions, -23.8% discount (deepest, highest volume)"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.articleRowsVsMeasured.60-70",
        "note": (
            "same quantity as C5; the 'highest volume' part is measured at "
            "bandTable.measuredFacts.highestVolumeBandMeasured (60-70, 57,267)"
        ),
    },
    {
        "id": "C19",
        "phrase": (
            "- **Town variation**: Clementi -40.6%, Toa Payoh -39.6%, Woodlands "
            "-6.2%, Pasir Ris +20.2% (inverted)"
        ),
        "status": "re-measured",
        "ledgerKey": "townTable.signConventions",
        "note": (
            "each findings value is the exact negative of the table's value for "
            "the same town (signConventions.rows); the measured window values "
            "are recorded in townTable.towns"
        ),
    },
    {
        "id": "C20",
        "phrase": (
            "- **60-yr policy threshold**: measurable “liquidity tax” between "
            "61-yr and 59-yr leases (CPF restriction)"
        ),
        "status": "not-reproducible",
        "ledgerKey": "regressionInputs.policyThreshold",
        "note": (
            "no Mann-Whitney implementation or stored result on the shipping "
            "surface, and the test population, window and alternative are "
            "unstated — underspecified, and not chosen for it"
        ),
    },
    {
        "id": "C21",
        "phrase": (
            "- **Spline-based arbitrage**: identifies BUY/SELL/HOLD signals at "
            "lease years where market deviates ≥5% from theoretical Bala curve"
        ),
        "status": "not-reproducible",
        "ledgerKey": "regressionInputs.splineArbitrage",
        "note": (
            "no signal table or implementation exists; it inherits the Bala "
            "curve's unstated parameters; the unlinked PNG's Bala panel is "
            "recorded without being attributed"
        ),
    },
    {
        "id": "C22",
        "phrase": ("- **Sample**: 223,634 HDB transactions, 2017-2026, lease range 30-99 years"),
        "status": "re-measured",
        "ledgerKey": "sampleClaim",
        "note": (
            "measured window rows recorded against the stated sample (+20,233); "
            "no candidate terminal month 2025-01..2026-11 reproduces 223,634 "
            "(all candidates recorded, with their count in sampleClaim.candidateCount); "
            "the measured remaining-lease range in the "
            "window differs from the stated 30-99 (fields at "
            "sampleClaim.measuredLeaseRangeYearsWindow)"
        ),
    },
    {
        "id": "C23",
        "phrase": "- **Primary input**: `data/parquets/L1/housing_hdb_transaction.parquet`",
        "status": "withdrawn",
        "ledgerKey": "absenceScans.l1Frame",
        "note": (
            "the named path does not exist (data/parquets root absent, zero "
            "housing_hdb_transaction matches under data/); the L1 producer is "
            "retired — the claim cannot stand and the pack derives everything "
            "from the shipped platinum frame instead"
        ),
    },
    {
        "id": "C24",
        "phrase": (
            "- **Advanced input**: `data/parquets/L3/housing_unified.parquet` "
            "for multivariate hedonic regression"
        ),
        "status": "withdrawn",
        "ledgerKey": "absenceScans.l3Frame",
        "note": (
            "the named path does not exist; the only housing_unified-named "
            "files under data/ are the two segmented panels, a different "
            "subject; the hedonic specification is withdrawn at "
            "regressionInputs.hedonicSpecification"
        ),
    },
    {
        "id": "C25",
        "phrase": (
            "- **Lease bands**: bins [0, 60, 70, 80, 90, 100], labels [<60, "
            "60-70, 70-80, 80-90, 90+]"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.definition",
        "note": (
            "the stated bins are adopted verbatim with the edge convention "
            "recorded; the definition-as-executed code is retired "
            "(absenceScans.bandDefinitionAsExecuted: the bins literal matches "
            "prose only)"
        ),
    },
    {
        "id": "C26",
        "phrase": "- **Remaining lease years**: `remaining_lease_months / 12`",
        "status": "not-reproducible",
        "ledgerKey": "leaseAgeValidation.storedColumn",
        "note": (
            "no shipped frame carries remaining_lease_months (the archived "
            "L2/L3 schema documents record it for the retired frames); the "
            "shipped frame's remaining_lease measures in years (48-97) and is "
            "null on 953,502 of 990,655 HDB rows, so the ledger derives "
            "remaining from lease_commence_date and validates it instead"
        ),
    },
    {
        "id": "C27",
        "phrase": ("- **Price statistics**: median `resale_price` and `price_per_sqm` by band"),
        "status": "re-measured",
        "ledgerKey": "responseDecision.legacyResponseStatement",
        "note": (
            "the named columns exist under no such names in the shipped frame "
            "(price and derived psm are measured instead); this sentence is "
            "the legacy's own response statement and the evidence the "
            "coefficient's PSF sentence contradicts"
        ),
    },
    {
        "id": "C28",
        "phrase": (
            "- **Discount to 90+ baseline**: `(baseline_psm - band_psm) / baseline_psm × 100`"
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.unitInvarianceMaxAbsDiffPsmVsPsfDiscount",
        "note": (
            "adopted verbatim, computed on derived PSM and on measured PSF "
            "(identical to two decimals, max difference recorded — psf = "
            "psm/10.7639104167 row-exactly) and on median price (which "
            "differs); the discount is per-area whatever the table's price "
            "column suggests"
        ),
    },
    {
        "id": "C29",
        "phrase": ("- **Annual decay rate**: linear approximation from discount vs years elapsed"),
        "status": "not-reproducible",
        "ledgerKey": "regressionInputs.annualDecayApproximation",
        "note": (
            "underspecified (no formula, no baseline band); the stored CSV's "
            "annual_decay_pct and the interactive asset's annual rates are "
            "unlinked to it and disagree with each other at two of three "
            "insight points"
        ),
    },
    {
        "id": "C30",
        "phrase": (
            "- **Town-level comparison**: short lease (<70 yr) vs fresh lease "
            "(90+ yr) median PSM within same town"
        ),
        "status": "re-measured",
        "ledgerKey": "townTable.definition",
        "note": (
            "adopted verbatim; the frozen text states NO window for this table "
            "(recorded as underspecified), so the ledger re-measures under the "
            "article's stated data period start capped at the measured cutoff, "
            "with the window a field"
        ),
    },
    {
        "id": "C31",
        "phrase": (
            "- **Hedonic regression** (advanced): `Price = β₀ + β₁(Lease) + "
            "β₂(FloorLevel) + β₃(DistToMRT) + β₄(Town) + ε`"
        ),
        "status": "withdrawn",
        "ledgerKey": "regressionInputs.hedonicSpecification",
        "note": (
            "no fitted model exists (absenceScans.fittedModel) and the "
            "FloorLevel term is null on all 990,655 HDB rows "
            "(regressionInputs.regressors.floorLevel), so the specification is "
            "not runnable as stated; no coefficient is estimated or converted"
        ),
    },
    {
        "id": "C32",
        "phrase": (
            "- **Policy threshold analysis**: Mann-Whitney U tests at 60-yr and 30-yr marks"
        ),
        "status": "not-reproducible",
        "ledgerKey": "regressionInputs.policyThreshold",
        "note": "the methodology line for the same absent analysis as C20",
    },
    {
        "id": "C33",
        "phrase": (
            "- **Bala's curve validation**: empirical vs theoretical "
            "depreciation, ≥5% deviation flagged"
        ),
        "status": "not-reproducible",
        "ledgerKey": "regressionInputs.balaCurve",
        "note": (
            "the Bala parameters are unstated and no implementation or stored "
            "result exists; the unlinked advanced PNG depicts such a validation "
            "and is recorded symmetrically (neither for nor against)"
        ),
    },
    {
        "id": "C34",
        "phrase": (
            "- **Buyers** can find meaningful value in the **60-70 year** band, "
            "which combines deep discounts with the highest transaction volume."
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.measuredFacts",
        "note": (
            "the volume half is measured: 60-70 has the highest measured band "
            "count (57,267); the value half inherits the discount claims' "
            "re-measurements"
        ),
    },
    {
        "id": "C35",
        "phrase": (
            "- The **<60 year** group is not the cheapest on a PSF basis, which "
            "suggests location mix still matters a lot."
        ),
        "status": "re-measured",
        "ledgerKey": "bandTable.measuredFacts",
        "note": (
            "measured on the per-area response: the cheapest band is 60-70 "
            "(4,782.61 derived PSM) and <60 (5,384.62) is not the cheapest — "
            "the claim's direction reproduces; its location-mix explanation is "
            "advice this ledger does not evaluate"
        ),
    },
    {
        "id": "C36",
        "phrase": (
            "The pure lease effect of +$54.75 PSF/year is robust after multivariate controls."
        ),
        "status": "withdrawn",
        "ledgerKey": "regressionInputs.coefficient",
        "note": (
            "the same coefficient as C9: unit unconfirmable, model absent, so "
            "the robustness claim is untestable and the number is not restated"
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
    missing = [quote for quote in quotes if quote["occurrences"] == 0]
    if missing:
        raise SystemExit(
            "legacy phrases not found verbatim in the frozen text: "
            + ", ".join(quote["id"] for quote in missing)
        )
    return {
        "legacyFile": _relative(LEGACY_EDITION),
        "legacyFileSha256": sha256_of(LEGACY_EDITION),
        "legacyFileBytes": int(LEGACY_EDITION.stat().st_size),
        "claimsChecked": len(claims),
        "verifiedVerbatim": len(claims) - len(missing),
        "quotes": quotes,
        "allQuotesFound": not missing,
        "method": (
            "each phrase is required to appear verbatim in the frozen legacy "
            "text; a paraphrase inside quotation marks is a defect, and the "
            "build fails on any zero-occurrence phrase"
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
            "time by walking dict keys and list items by their `id`; resolution "
            "is SYNTACTIC — it checks the key exists, not that the resolved "
            "field supports the disposition — and an unresolved key fails the "
            "build rather than shipping"
        ),
    }


def build() -> dict[str, Any]:
    columns = [
        "month",
        "property_type",
        "town",
        "price",
        "floor_area_sqm",
        "psf",
        "area_sqm",
        "area_sqft",
        "Unit Price ($ PSF)",
        "Unit Price ($ PSM)",
        "lease_commence_date",
        "remaining_lease",
        "floor_level",
        "dist_to_nearest_mrt",
    ]
    schema = pq.read_schema(UNIFIED)
    missing = [name for name in columns if name not in schema.names]
    if missing:
        raise SystemExit(f"unified_dataset schema lacks expected columns: {missing}")
    frame = pd.read_parquet(UNIFIED, columns=columns)
    hdb = _select(frame, frame["property_type"] == "hdb")

    measured_cutoff = cutoff(frame)
    last_complete = measured_cutoff["lastCompleteMonth"]

    response = response_decision(frame, hdb, last_complete, measured_cutoff["frameFirstMonth"])
    response["absentColumns"] = absent_columns()
    lease_age = lease_age_validation(hdb)
    bands = band_table(hdb, last_complete)
    towns = town_table(hdb, last_complete)
    sample = sample_claim(hdb, last_complete)
    window_rows = sample["measuredWindowRows"]
    interactive = interactive_asset(_series(hdb["town"]).astype(str), window_rows)
    artefacts = stored_artefacts()
    regression = regression_inputs(hdb)
    absences = absence_scans()
    gate_block = gates()
    claims = legacy_claims()

    inputs: dict[str, Any] = {}
    for path in (
        UNIFIED,
        LEGACY_EDITION,
        INTERACTIVE_ASSET,
        CSV_ANALYSIS,
        CSV_PRICE_STATS,
        PNG_PRICE_DISTRIBUTION,
        PNG_PSM_BY_BAND,
        PNG_TRANSACTION_VOLUME,
        PNG_ADVANCED,
        STUDIES_TS,
        RESEARCH_REGISTER,
    ):
        inputs[_relative(path)] = {"sha256": sha256_of(path), "bytes": int(path.stat().st_size)}
    inputs[_relative(UNIFIED)]["rows"] = int(pq.ParquetFile(UNIFIED).metadata.num_rows)
    inputs[_relative(UNIFIED)]["columns"] = int(len(schema.names))
    inputs[_relative(LEGACY_EDITION)]["lines"] = _text_lines(LEGACY_EDITION)
    inputs[_relative(LEGACY_EDITION)]["lineBasis"] = (
        "newline-terminated lines of the frozen text file"
    )
    for csv_path in (CSV_ANALYSIS, CSV_PRICE_STATS):
        inputs[_relative(csv_path)]["rows"] = _csv_data_rows(csv_path)
        inputs[_relative(csv_path)]["rowBasis"] = "data records; header row excluded"

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": "RS06",
        "series": "lease-decay",
        "gateClause": GATE_CLAUSE,
        "scope": (
            "RS06 lease-decay evidence: the measured unit/response decision, "
            "lease-age validation as of transaction month, the legacy band table "
            "re-measured against the article and the stored CSV artefacts, the "
            "short-vs-fresh town table re-measured with its two sign "
            "conventions reconciled, the interactive band asset inventoried and "
            "reconciled against the article by correspondence only, the legacy "
            "specification's regressor availability, the absence scans for the "
            "retired frames and the fitted model, and the chart/model gates "
            "recorded as in force"
        ),
        "definition": (
            "A measured inventory and reconciliation. One stated response "
            "(psf, $ per square foot, exact on every HDB row) with derived PSM "
            "as the secondary per-area measure and median price named only "
            "where a field says so; a lease variable derived from "
            "lease_commence_date as of transaction month and validated against "
            "the stored remaining_lease on its own 2015-2016 coverage. No "
            "model is fitted, no coefficient is converted, and every number is "
            "a ledger field or exact arithmetic on two ledger fields."
        ),
        "inputs": inputs,
        "cutoff": measured_cutoff,
        "responseDecision": response,
        "leaseAgeValidation": lease_age,
        "bandTable": bands,
        "townTable": towns,
        "sampleClaim": sample,
        "interactiveAsset": interactive,
        "storedArtefacts": artefacts,
        "regressionInputs": regression,
        "absenceScans": absences,
        "gates": gate_block,
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
        print("Pass: RS06 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS06 ledger does not match this checkout")
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

    cutoff_block = evidence["cutoff"]
    statuses: dict[str, int] = {}
    for claim in evidence["legacyClaims"]:
        statuses[claim["status"]] = statuses.get(claim["status"], 0) + 1
    print(
        f"Cutoff: last complete month {cutoff_block['lastCompleteMonth']} "
        f"(terminal {cutoff_block['terminalMonth']} at "
        f"{cutoff_block['terminalMonthShareOfTrailingMedian']} of the trailing median)"
    )
    print(
        "Lease age: "
        f"{evidence['leaseAgeValidation']['agreement']['within1_0Years']}/"
        f"{evidence['leaseAgeValidation']['agreement']['rowsComparable']} stored rows "
        f"within 1.0y; "
        f"{evidence['leaseAgeValidation']['exceptions']['rowsWithNegativeLeaseAge']} negative-age rows"
    )
    print(
        "Band table: measured window rows "
        f"{evidence['bandTable']['window']['rowsBandedInWindow']}; "
        f"cheapest band {evidence['bandTable']['measuredFacts']['cheapestBandMeasuredByDerivedPsm']}"
    )
    print(
        "Interactive asset: "
        f"{evidence['interactiveAsset']['bandCount']} bands, count sum "
        f"{evidence['interactiveAsset']['countSum']}, "
        f"{evidence['interactiveAsset']['ageCoverage']['absentBinCount']} age bins absent"
    )
    print(
        "Legacy claims: "
        + ", ".join(f"{count} {status}" for status, count in sorted(statuses.items()))
        + f" ({evidence['legacyQuoteCheck']['verifiedVerbatim']}/"
        f"{evidence['legacyQuoteCheck']['claimsChecked']} verbatim)"
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
