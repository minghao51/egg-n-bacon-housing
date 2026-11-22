#!/usr/bin/env python3
"""Measure RS14's price-forecasts evidence: the lineage of the stored predictive
asset, a scoring of its expired 2025-07-01 projections against realised
outcomes, and an inventory of every quantitative claim of the frozen legacy
article.

RS14's gate is "Reconcile article and predictive asset lineage first. Use
rolling-origin validation, leakage checks, naive trend/seasonal baselines,
error metrics and empirical prediction-interval coverage. Name R-squared
correctly. Score expired 2025 forecasts where comparable outcomes exist. Never
advance a stored forecast date or reuse BUY/SELL prompts as current advice."
This tool measures from the local checkout, and only what the checkout can
support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04/RS05/RS09/
   RS10 shipped (terminal month's transaction count as a fraction of the
   trailing twelve-month median), plus the all-property-types cross-check.
2. **Predictive asset inventory** — full read of
   `app/public/data/analytics/predictive_analytics.json.gz`: metadata, the 41
   planning-area blocks, forecast dates, signals and interval widths.
3. **Lineage** — the four forecast-bearing artefact families in this checkout
   (the 2025 JSON asset, the 2026 `data/forecasts` CSV/parquet vintages, the
   `data/analysis/feature_importance` CSVs, and two plot panels under
   `app/public/data/analysis/price_forecasts/`), each sha-pinned, with the
   measured (absent) cross-references between them. An unlinked artefact
   adjudicates nothing, in both directions.
4. **Forecast scoring** — the stored `projected_change_pct` values are scored
   against realised planning-area median prices through the measured cutoff,
   under a stated producer convention plus two recorded alternative anchor
   readings, against naive baselines (zero-change, trailing-6-month trend,
   seasonal year-ago window), with MAE/RMSE/bias, MAPE on implied levels,
   directional hit rate and empirical interval coverage of the stored bounds.
5. **Rolling-origin validation** — of the naive baselines, across 23 monthly
   origins; the stored model itself has exactly one origin in the asset, so it
   enters the single-origin table only (recorded, not hidden).
6. **Second vintage scoring** — the 2026 `hdb_price_forecasts` 6-month rows,
   scored on implied levels against realised HDB medians, under both readable
   target-month readings; the 12-month rows target after the cutoff and are
   recorded as not scoreable.
7. **Feature-importance artefacts** — the seven CSVs, their train/test metrics
   (the only train/test numbers in the checkout; the split FILES are absent),
   and the screen of the asset's 0.89 against their XGBoost yoy mean.
8. **Absence scans** — train/test split filenames, the legacy primary-input
   path, producer scripts for the predictive asset, and the
   `yoy_change_pct` column (an absent column, distinct from a null value),
   each with its roots, file counts and exclusions disclosed.

It never runs the pipeline, never re-fits a model, never writes outside
`--output`, and never touches `app/public/data/**` or `data/pipeline/**`.

Usage:

    uv run python scripts/tools/price_forecasts_evidence.py \\
        --output docs/implementation/artifacts/rs14-price-forecasts-evidence.json

    uv run python scripts/tools/price_forecasts_evidence.py --check  # no drift
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
PREDICTIVE_ASSET = (
    REPO_ROOT / "app" / "public" / "data" / "analytics" / "predictive_analytics.json.gz"
)
LEGACY_EDITION = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "price-forecasts.md"
)
WORKING_EDITION = REPO_ROOT / "docs" / "analytics" / "price-forecasts.md"
PRICE_FORECASTS_CSV = REPO_ROOT / "data" / "forecasts" / "hdb_price_forecasts.csv"
PRICE_FORECASTS_PARQUET = REPO_ROOT / "data" / "forecasts" / "hdb_price_forecasts.parquet"
YIELD_FORECASTS_CSV = REPO_ROOT / "data" / "forecasts" / "hdb_yield_forecasts.csv"
YIELD_FORECASTS_PARQUET = REPO_ROOT / "data" / "forecasts" / "hdb_yield_forecasts.parquet"
FEATURE_IMPORTANCE_DIR = REPO_ROOT / "data" / "analysis" / "feature_importance"
PRICE_FORECAST_PANEL_DIR = REPO_ROOT / "app" / "public" / "data" / "analysis" / "price_forecasts"
MAP_ARCHIVE_TS = REPO_ROOT / "app" / "src" / "utils" / "map-archive.ts"
DATA_URLS_TS = REPO_ROOT / "app" / "src" / "constants" / "data-urls.ts"
TOOL_EVIDENCE_TS = REPO_ROOT / "app" / "src" / "components" / "tools" / "lib" / "tool-evidence.ts"
ARCHIVE_REORG_DOC = REPO_ROOT / "docs" / "archive" / "20260124-data-reorganization-complete.md"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs14-price-forecasts-evidence.json"
)

SCHEMA_VERSION = "1.0.0"

# The corroboration scan is bounded to these roots and suffixes so the ledger is
# reproducible file-order-independently and cannot read itself.
SCAN_ROOTS = (
    "docs",
    "scripts",
    "src",
    "assets",
    "prompts",
    "app/src",
    "app/public",
    ".claude/handoffs",
)
SCAN_SUFFIXES = (".md", ".py", ".ts", ".tsx", ".json", ".csv", ".txt", ".yml", ".yaml")
# The exclusions are the RF08 programme's own output surfaces, not evidence of
# RS14's method: `docs/implementation/` holds the per-study records,
# `scripts/tools/` holds the evidence producers themselves, and `prompts/` holds
# the handoffs and runbooks. A hash-pinned scan that counted them drifted the
# moment a sibling instrument appeared (the RS10 lesson, recorded in that
# study's pack §6a/§6b).
EXCLUDED_SCAN_PREFIXES = (
    "docs/implementation/",
    "scripts/tools/",
    "prompts/",
    "app/src/components/studies/",
    "app/tests/",
)
# Published edition texts are programme outputs too. The frozen legacy
# originals stay IN the scan except where noted: the frozen price-forecasts
# article is the CLAIM SOURCE for the article-value tokens, and is excluded
# from its own corroboration scan (a text cannot corroborate itself); its
# matches are reported separately as `ownCopies`.
EDITION_PREFIX = "docs/analytics/editions/"
RETAINED_EDITION_PREFIX = "docs/analytics/editions/legacy/"
TRANSIENT_SCAN_DIRS = (
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    ".astro",
)
FILENAME_SCAN_EXCLUDED_PREFIXES = tuple(f"{name}/" for name in TRANSIENT_SCAN_DIRS) + (
    "app/node_modules/",
    "scripts/tools/",
    "prompts/",
    "docs/implementation/",
)
# This tool quotes the tokens it searches for; scanning itself would make the
# ledger its own evidence. The D12 decision register records reviewer findings
# in reviewer vocabulary and must not move a pinned count (the RS10 §6b lesson).
EXCLUDED_SCAN_PATHS = (
    "scripts/tools/price_forecasts_evidence.py",
    "scripts/tools/market_segments_evidence.py",
    "scripts/tools/macro_sensitivity_evidence.py",
    "docs/plans/2026-11-12-reporting-refresh-decisions.md",
    "docs/analytics/editions/legacy/2026-11-12/price-forecasts.md",
    ".secrets.baseline",
)

# The article's own quantitative values, as tokens, to locate every surface
# that carries them. Percent signs and the ± prefix keep these specific.
ARTICLE_VALUE_TOKENS = (
    "79.8%",
    "±18.58%",
    "98.5%",
    "±50.15%",
    "85.6%",
    "±40.48%",
    "72.6%",
    "±1877.88%",
    "30.1%",
    "±1076.24%",
    "99.4%",
    "97.1%",
    "96.4%",
    "94.2%",
    "92.3%",
    "74% vs 47%",
    "51.14%",
    "65.50%",
    "n_estimators=100",
    "ARIMA(1,1,1)",
)

# Method/lineage tokens: where the checkout names the asset, the claimed
# split files, the second vintage, and the importance artefacts.
METHOD_TOKENS = (
    "predictive_analytics",
    "price_appreciation_train",
    "hdb_price_forecasts",
    "hdb_yield_forecasts",
    "feature_importance_yoy_change_pct",
    "model_comparison.csv",
)

# The five segment rows of the article's per-segment tables, as stored
# constants transcribed from the frozen rows (pinned verbatim by
# legacyQuoteCheck; the transcription is checkable against the quotes).
SEGMENT_ROWS: tuple[dict[str, Any], ...] = (
    {
        "id": "hdb",
        "label": "HDB flats",
        "r2PctStated": 79.8,
        "ciWidthPctStated": 18.58,
        "directionalPctStated": 99.4,
        "read": "Strong",
    },
    {
        "id": "ec",
        "label": "Executive Condos",
        "r2PctStated": 98.5,
        "ciWidthPctStated": 50.15,
        "directionalPctStated": 97.1,
        "read": "Strong but wider uncertainty",
    },
    {
        "id": "mass",
        "label": "Mass Market Condos",
        "r2PctStated": 85.6,
        "ciWidthPctStated": 40.48,
        "directionalPctStated": 96.4,
        "read": "Useful with caution",
    },
    {
        "id": "mid",
        "label": "Mid Market Condos",
        "r2PctStated": 72.6,
        "ciWidthPctStated": 1877.88,
        "directionalPctStated": 94.2,
        "read": "Direction only",
    },
    {
        "id": "lux",
        "label": "Luxury Condos",
        "r2PctStated": 30.1,
        "ciWidthPctStated": 1076.24,
        "directionalPctStated": 92.3,
        "read": "Magnitude unusable",
    },
)

FORECAST_DATE_STORED = "2025-07-01"
LAST_TRAINING_DATE_STORED = "2025-01-01"
HORIZON_MONTHS = 6
# Producer-chosen screening floor: a planning-area month must hold at least
# this many transactions in the scoring basis for its median to be used. The
# asset states no floor; this one is the producer's, stated here and applied
# identically to every method and origin.
MEDIAN_FLOOR = 10
CI_NOMINAL = 0.95  # producer assumption; the asset states no interval level
MAX_LISTED = 12

DEFINITION = (
    "A measured reconciliation of the lineage behind the RS14 price-forecasts "
    "article and a scoring of the stored 2025 forecasts against realised "
    "outcomes. The stored asset (predictive_analytics.json.gz, metadata "
    "model_r2 0.89, last_training_date 2025-01-01) holds 41 planning-area "
    "blocks whose price_forecast rows all carry forecast_date 2025-07-01 and "
    "signal BUY. That stored date is read, never advanced; the signals are "
    "withdrawn as current advice. The scoring anchors each projection at a "
    "stated producer convention (the month before the forecast month) plus two "
    "recorded alternative readings, because the asset defines no anchor for "
    "projected_change_pct, and scores it against realised area median prices "
    "through the measured cutoff against three naive baselines, with MAE, "
    "RMSE, bias, MAPE on implied levels, directional hit rate and empirical "
    "coverage of the stored interval bounds at an assumed 0.95 nominal level. "
    "Rolling-origin validation is applied to the baselines across 23 monthly "
    "origins; the stored model has exactly one origin, so it cannot be "
    "rolling-origin validated from this asset — recorded, not hidden. "
    "model_r2 is named as a fit statistic throughout, never as forecast "
    "accuracy. The article's per-segment R-squared table is withdrawn: the "
    "corroboration scan finds its values only in the article's own copies and "
    "sibling legacy articles, and the asset carries no per-segment outputs. "
    "Nothing here re-fits a model, produces a new forecast, or edits any "
    "stored artefact."
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _number(value: Any, label: str) -> float:
    """A float parsed from an asset/derived value, failing loudly with the value."""
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


def _add_months(month: str, offset: int) -> str:
    """YYYY-MM plus an integer month offset, calendar-aware."""
    year, mon = int(month[:4]), int(month[5:7])
    total = year * 12 + (mon - 1) + offset
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _month_of(day: str) -> str:
    return day[:7]


def _days_between(day_a: str, day_b: str) -> int:
    return (date.fromisoformat(day_b) - date.fromisoformat(day_a)).days


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


def _pin(path: Path) -> dict[str, Any]:
    return {"path": _relative(path), "sha256": sha256_of(path), "bytes": int(path.stat().st_size)}


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month, measured — the terminal month is partial.

    The same rule RS03/RS04/RS05/RS09/RS10 shipped: computed on the private
    (condo) rows so the bound is identical across the studies, with an
    all-property-types cross-check.
    """
    condo = frame[frame["property_type"] == "condo"]
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
    all_trailing = [all_counts[m] for m in all_ordered[-13:-1]]
    all_median = float(np.median(all_trailing)) if all_trailing else 0.0

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
        "frameFirstMonth": str(frame["month"].min()),
        "frameLastMonth": str(frame["month"].max()),
        "meaning": (
            "every window, count and share in this ledger that touches the frame "
            "stops at lastCompleteMonth"
        ),
    }


def predictive_asset() -> dict[str, Any]:
    """Full inventory of the stored predictive asset."""
    payload = _gz_payload(PREDICTIVE_ASSET)
    meta = payload.get("metadata", {})
    areas: dict[str, Any] = payload.get("planning_areas", {})
    area_ids = sorted(areas)

    rows: list[dict[str, Any]] = []
    signals: dict[str, int] = {}
    tags: dict[str, int] = {}
    recommendations: dict[str, int] = {}
    for area in area_ids:
        block = areas[area]
        fc = block.get("price_forecast", {})
        signal = str(fc.get("signal"))
        signals[signal] = signals.get(signal, 0) + 1
        policy = block.get("policy_risk", {})
        tag = str(policy.get("market_segment"))
        tags[tag] = tags.get(tag, 0) + 1
        lease = block.get("lease_arbitrage", {})
        rec = str(lease.get("recommendation"))
        recommendations[rec] = recommendations.get(rec, 0) + 1
        lower = _number(fc.get("confidence_interval_lower"), "ci_lower")
        upper = _number(fc.get("confidence_interval_upper"), "ci_upper")
        rows.append(
            {
                "id": area,
                "projectedChangePct": _r(fc.get("projected_change_pct"), 2),
                "ciLowerPct": _r(lower, 2),
                "ciUpperPct": _r(upper, 2),
                "ciWidthPct": _r(upper - lower, 2),
                "modelR2": _r(fc.get("model_r2"), 4),
                "forecastDate": str(fc.get("forecast_date")),
                "signal": signal,
                "policyMarketSegmentTag": tag,
                "leaseRecommendation": rec,
            }
        )

    forecast_dates = sorted({row["forecastDate"] for row in rows})
    model_r2_values = sorted({row["modelR2"] for row in rows})
    horizon_raw = str(meta.get("forecast_horizon"))

    return {
        "path": _relative(PREDICTIVE_ASSET),
        "sha256": sha256_of(PREDICTIVE_ASSET),
        "gzBytes": int(PREDICTIVE_ASSET.stat().st_size),
        "decompressedBytes": len(gzip.decompress(PREDICTIVE_ASSET.read_bytes()).decode("utf-8")),
        "topLevelKeys": sorted(payload.keys()),
        "generatedAt": str(meta.get("generated_at")),
        "forecastHorizonRaw": horizon_raw,
        "horizonMonths": _r(horizon_raw.split("_")[0], 0),
        "metadataModelR2": _r(meta.get("model_r2"), 4),
        "lastTrainingDate": str(meta.get("last_training_date")),
        "areaCount": len(area_ids),
        "areasAllInFramePlanningArea": None,  # set by caller
        "perArea": rows,
        "signalCounts": signals,
        "policyMarketSegmentTags": tags,
        "leaseRecommendationCounts": recommendations,
        "distinctForecastDates": forecast_dates,
        "distinctPerAreaModelR2": model_r2_values,
        "perAreaModelR2ConstantAcrossAreas": len(model_r2_values) == 1,
        "meaning": (
            "the stored asset is read in full and its dates are recorded as "
            "stored: forecast_date 2025-07-01 is read from every block and is "
            "never advanced by this pack. The metadata model_r2 is an in-sample/"
            "holdout fit statistic recorded by the asset, not a forecast-"
            "accuracy measure; forecast error is measured separately at "
            "forecastScoring"
        ),
    }


def article_vs_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """The article's per-segment claims against what the stored asset holds."""
    asset_text = gzip.decompress(PREDICTIVE_ASSET.read_bytes()).decode("utf-8")
    names_in_asset = {
        str(row["label"]): int(asset_text.count(str(row["label"]))) for row in SEGMENT_ROWS
    }
    reliability_rows = []
    technical_rows = []
    for row in SEGMENT_ROWS:
        common = {
            "id": row["id"],
            "segmentLabel": row["label"],
            "r2PctStated": row["r2PctStated"],
            "ciWidthPctStated": row["ciWidthPctStated"],
            "directionalPctStated": row["directionalPctStated"],
            "nameOccurrencesInStoredAsset": names_in_asset[row["label"]],
        }
        reliability_rows.append({**common, "practicalRead": row["read"]})
        technical_rows.append(dict(common))

    return {
        "reliabilityTable": {
            "frozenHeader": "Accuracy (R²)",
            "workingCopyHeader": "R² (magnitude fit)",
            "rows": reliability_rows,
            "meaning": (
                "the frozen table's header calls R-squared 'Accuracy'; R-squared "
                "is a fit statistic (the share of variance a fitted model "
                "explains on the data it was scored against), not forecast "
                "accuracy, and no train/test or holdout artefact for these five "
                "segment models exists in this checkout (corroborationScan). "
                "The working copy already renames the header; the frozen text "
                "is what this pack quotes and withdraws. The five rows are "
                "withdrawn, not re-measured: there is nothing in the checkout "
                "to re-measure them against"
            ),
        },
        "technicalTable": {
            "rows": technical_rows,
            "meaning": (
                "the appendix table repeats the same five triples; withdrawn for the same reason"
            ),
        },
        "featureClaims": {
            "hdbFeature": {
                "featureStated": "2-year YoY appreciation",
                "importancePctStated": 51.14,
            },
            "massFeature": {
                "featureStated": "2-year YoY appreciation",
                "importancePctStated": 65.50,
            },
            "combined": {
                "topFeatureStated": "2-year YoY appreciation",
                "hdbImportancePctStated": 51.14,
                "massImportancePctStated": 65.50,
            },
            "meaning": (
                "the checkout's feature-importance artefacts "
                "(featureImportanceArtefacts) carry six target/model feature "
                "lists, none containing a feature named like a 2-year YoY "
                "appreciation, and nothing links those artefacts to the "
                "article's per-segment models in either direction"
            ),
        },
        "ensembleAccuracyClaim": {
            "statedEnsemblePct": 74.0,
            "statedUnifiedPct": 47.0,
            "metricNameStated": "accuracy",
            "metricDefined": False,
            "meaning": (
                "'74% vs 47%' states no metric definition, population or "
                "window; withdrawn, not re-measured. No artefact in the "
                "corroboration scan outside the article's own copies carries "
                "either number"
            ),
        },
        "perSegmentModelOutputs": {
            "inStoredAsset": False,
            "assetBlockKeys": sorted(
                {
                    key
                    for block in _gz_payload(PREDICTIVE_ASSET)["planning_areas"].values()
                    for key in block
                }
            ),
            "segmentNameOccurrencesInStoredAsset": {
                row["label"]: names_in_asset[row["label"]] for row in SEGMENT_ROWS
            },
            "meaning": (
                "the stored asset's per-area blocks carry only price_forecast, "
                "policy_risk and lease_arbitrage keys; zero occurrences of any "
                "of the five segment labels; and the corroboration scan finds "
                "the table's values only in the article's own copies, sibling "
                "legacy articles and one plan document — so the per-segment "
                "model outputs the article's tables presuppose are absent from "
                "this checkout, and the table is withdrawn rather than "
                "re-estimated"
            ),
        },
        "granularity": {
            "articleStated": "per planning area (ARIMA) and per property type/segment (XGBoost)",
            "assetGranularity": "per planning area",
            "assetAreaCount": asset["areaCount"],
            "meaning": (
                "the one granularity the asset stores is per planning area; the "
                "per-segment granularity has no stored counterpart"
            ),
        },
    }


def lineage(asset: dict[str, Any]) -> dict[str, Any]:
    """The forecast-bearing artefact families, pinned, with measured links.

    An unlinked artefact adjudicates nothing, symmetrically: the absence of a
    reference between these files is recorded as a count of cross-references,
    and is used neither to credit nor to discredit any family.
    """
    price_csv = pd.read_csv(PRICE_FORECASTS_CSV)
    price_parquet_rows = int(pq.ParquetFile(PRICE_FORECASTS_PARQUET).metadata.num_rows)
    price_areas = sorted({str(v) for v in price_csv["planning_area"].dropna()})
    horizon_counts = {
        str(k): int(v) for k, v in price_csv["forecast_horizon"].value_counts().items()
    }
    dates_by_horizon = {
        h: sorted(
            {str(v) for v in price_csv.loc[price_csv["forecast_horizon"] == h, "forecast_date"]}
        )
        for h in sorted(horizon_counts)
    }
    train_dates = sorted({str(v) for v in price_csv["last_training_date"].dropna()})
    r2_min = _r(price_csv["model_r2"].min(), 4)
    r2_max = _r(price_csv["model_r2"].max(), 4)

    yield_csv = pd.read_csv(YIELD_FORECASTS_CSV)
    yield_areas = sorted({str(v) for v in yield_csv["planning_area"].dropna()})

    asset_areas = {row["id"] for row in asset["perArea"]}
    overlap_price = sorted(set(price_areas) & asset_areas)

    panels = []
    for path in sorted(PRICE_FORECAST_PANEL_DIR.iterdir()):
        if path.is_file():
            panels.append(_pin(path))

    return {
        "vintages": [
            {
                "id": "predictive-analytics-2025",
                "path": asset["path"],
                "sha256": asset["sha256"],
                "lastTrainingDate": asset["lastTrainingDate"],
                "forecastDate": FORECAST_DATE_STORED,
                "horizonMonths": asset["horizonMonths"],
                "areaCount": asset["areaCount"],
                "scoredInThisPack": True,
                "expiredAtCutoff": True,
                "meaning": "scored at forecastScoring; dates read as stored",
            },
            {
                "id": "hdb-price-forecasts-2026",
                "path": _relative(PRICE_FORECASTS_CSV),
                "csvSha256": sha256_of(PRICE_FORECASTS_CSV),
                "parquetSha256": sha256_of(PRICE_FORECASTS_PARQUET),
                "csvRows": int(len(price_csv)),
                "parquetRows": price_parquet_rows,
                "csvParquetRowsEqual": int(len(price_csv)) == price_parquet_rows,
                "lastTrainingDate": train_dates,
                "forecastDatesByHorizon": dates_by_horizon,
                "horizonCounts": horizon_counts,
                "areaCount": len(price_areas),
                "declaredPropertyType": "HDB",
                "declaredTarget": "median_price",
                "modelR2Range": {"min": r2_min, "max": r2_max},
                "areasOverlappingStoredAsset": len(overlap_price),
                "scoredInThisPack": True,
                "expiredAtCutoff": "6m rows: target within cutoff; 12m rows: target after cutoff",
                "meaning": (
                    "a second, newer forecast vintage the checkout holds under "
                    "data/forecasts/. It is a different generation: different "
                    "training date (2026-01-01), different forecast dates "
                    "(2026-06-01/2026-12-01), 30 areas against the stored "
                    "asset's 41, interval bounds in price LEVELS rather than "
                    "percentage points, and per-area model_r2 values in a "
                    "different range. Nothing in the scanned checkout links it "
                    "to the 2025 asset in either direction (corroborationScan)"
                ),
            },
            {
                "id": "hdb-yield-forecasts-2026",
                "path": _relative(YIELD_FORECASTS_CSV),
                "csvSha256": sha256_of(YIELD_FORECASTS_CSV),
                "parquetSha256": sha256_of(YIELD_FORECASTS_PARQUET),
                "csvRows": int(len(yield_csv)),
                "areaCount": len(yield_areas),
                "declaredTarget": "predicted_yield_pct",
                "scoredInThisPack": False,
                "meaning": (
                    "recorded for lineage completeness and NOT scored: its "
                    "target is rental yield, not price, so it has no comparable "
                    "price outcome in this pack. Not scored is not absent"
                ),
            },
        ],
        "plotPanels": {
            "directory": _relative(PRICE_FORECAST_PANEL_DIR),
            "panels": panels,
            "linkage": "unestablished",
            "meaning": (
                "two PNG panels under app/public/data/analysis/price_forecasts/ "
                "are sha-pinned so any later change shows. NOTHING in the "
                "checkout links either panel to either JSON/CSV vintage or to "
                "the article's models, so they are evidence for none of them "
                "and against none of them. A HUMAN VISUAL READ by the producer, "
                "recorded because pixels are not machine-read: the bar panel is "
                "titled 'Planning Area Housing Price Forecasts (24-Month) / Top "
                "15 Areas by Expected Growth' with appreciation values near 8-10 "
                "percent; the scatter is titled 'Current Price vs Forecast "
                "Appreciation / Identifying Undervalued Opportunities' with "
                "quadrant annotations including 'UNDERATED GEMS' (as printed) "
                "and 'MAY BE OVERVALUED'. Both are a THIRD representation: a "
                "24-month horizon that matches neither stored vintage (the 2025 "
                "asset is 6-month; the 2026 CSV is 6m/12m), and the scatter's "
                "advice-style quadrant labels are exactly the prompt genre the "
                "gate withholds from republication"
            ),
        },
        "archiveMentions": [
            {
                "path": _relative(ARCHIVE_REORG_DOC),
                "sha256": sha256_of(ARCHIVE_REORG_DOC),
                "quote": "forecasts/                   # 🔮 ML forecasts (KEPT as-is)",
                "meaning": (
                    "a January 2026 archive document lists data/forecasts/ as "
                    "'ML forecasts (KEPT as-is)' during a data reorganization — "
                    "a directory listing, not a run linkage to any model or to "
                    "the 2025 asset"
                ),
            }
        ],
        "meaning": (
            "four forecast-bearing families exist in the checkout: the 2025 "
            "JSON asset this study scores, the 2026 data/forecasts vintages "
            "(price scored as secondVintage; yield recorded, not scored), the "
            "feature-importance CSVs (featureImportanceArtefacts), and two "
            "unlinked plot panels. No scanned file references more than one "
            "family (corroborationScan.methodTokens), so lineage between them "
            "is unestablished in BOTH directions, and this pack scores the 2025 "
            "asset on its own stored values without inheriting anything from "
            "the others"
        ),
    }


class Medians:
    """Per-(area, month) medians and counts, computed once and reused."""

    def __init__(self) -> None:
        self.medianPrice: dict[tuple[str, str], float] = {}
        self.count: dict[tuple[str, str], int] = {}
        self.medianPsf: dict[tuple[str, str], float] = {}
        self.medianHdb: dict[tuple[str, str], float] = {}
        self.medianCondo: dict[tuple[str, str], float] = {}
        self.countHdb: dict[tuple[str, str], int] = {}
        self.countCondo: dict[tuple[str, str], int] = {}


def _medians(frame: pd.DataFrame, areas: list[str]) -> Medians:
    """Median price/psf per (area, month) for the given areas, all months.

    A deterministic lexsort walk rather than a multi-key groupby, so group
    order and iteration are fixed regardless of pandas internals.
    """
    sub = pd.DataFrame(frame.loc[frame["planning_area"].isin(list(areas))])
    area_arr = sub["planning_area"].to_numpy(dtype=str)
    month_arr = sub["month"].to_numpy(dtype=str)
    ptype_arr = sub["property_type"].to_numpy(dtype=str)
    price_arr = sub["price"].to_numpy(dtype=float)
    psf_arr = sub["psf"].to_numpy(dtype=float)

    out = Medians()
    order = np.lexsort((month_arr, area_arr))
    total = int(order.size)
    start = 0
    while start < total:
        first = int(order[start])
        key_area = str(area_arr[first])
        key_month = str(month_arr[first])
        end = start
        while (
            end < total
            and str(area_arr[int(order[end])]) == key_area
            and str(month_arr[int(order[end])]) == key_month
        ):
            end += 1
        idx = order[start:end]
        raw_prices = price_arr[idx]
        finite = np.isfinite(raw_prices)
        prices = raw_prices[finite]
        key = (key_area, key_month)
        if prices.size:
            out.medianPrice[key] = float(np.median(prices))
            out.count[key] = int(prices.size)
        hdb_prices = raw_prices[finite & (ptype_arr[idx] == "hdb")]
        if hdb_prices.size:
            out.medianHdb[key] = float(np.median(hdb_prices))
            out.countHdb[key] = int(hdb_prices.size)
        condo_prices = raw_prices[finite & (ptype_arr[idx] == "condo")]
        if condo_prices.size:
            out.medianCondo[key] = float(np.median(condo_prices))
            out.countCondo[key] = int(condo_prices.size)
        psf_values = psf_arr[idx]
        psf_values = psf_values[np.isfinite(psf_values)]
        if psf_values.size:
            out.medianPsf[key] = float(np.median(psf_values))
        start = end
    return out


def _pct_change(new: float | None, old: float | None) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return (new / old - 1.0) * 100.0


def _method_metrics(
    errors: list[float],
    implied_ratio_errors: list[float],
    directional_correct: int,
    directional_n: int,
) -> dict[str, Any]:
    arr = np.array(errors, dtype=float) if errors else np.array([])
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    if arr.size:
        mae = float(np.mean(np.abs(arr)))
        rmse = float(np.sqrt(np.mean(arr**2)))
        bias = float(np.mean(arr))
    ape = np.array(implied_ratio_errors, dtype=float) if implied_ratio_errors else np.array([])
    mape: float | None = None
    if ape.size:
        mape = float(np.mean(ape) * 100.0)
    hit: float | None = None
    if directional_n:
        hit = _r(directional_correct / directional_n * 100.0, 2)
    return {
        "n": int(arr.size),
        "maePct": _r(mae, 4),
        "rmsePct": _r(rmse, 4),
        "biasPct": _r(bias, 4),
        "mapeOnLevelsPct": _r(mape, 4),
        "directionalHitPct": hit,
        "directionalN": int(directional_n),
        "mapeDefinition": (
            "MAPE is computed on implied LEVELS: anchor median x (1 + pct/100) "
            "against the realised target median, |implied - realised| / "
            "realised, averaged and expressed in percent — a percentage-change "
            "forecast scored without dividing by a near-zero realised change"
        ),
    }


def _score_one_convention(
    anchor: str,
    target: str,
    area_rows: list[dict[str, Any]],
    med: Medians,
    basis: str,
    with_per_area_table: bool,
) -> dict[str, Any]:
    """Score the stored forecasts and the three baselines at one anchor.

    basis: "medianPriceAllRows" | "medianPricePerTag" | "medianPsfAllRows".
    The floor applies to the anchor and target months in the chosen basis;
    baseline months use the same basis without an additional floor (an area
    missing a baseline month is dropped from that baseline's metrics and the
    per-method n records it).
    """

    def basis_median(row_id: str, month: str) -> float | None:
        if basis == "medianPricePerTag":
            source = med.medianHdb if tag_by_id[row_id] == "HDB" else med.medianCondo
            return source.get((row_id, month))
        if basis == "medianPsfAllRows":
            return med.medianPsf.get((row_id, month))
        return med.medianPrice.get((row_id, month))

    def basis_count(row_id: str, month: str) -> int:
        if basis == "medianPricePerTag":
            source = med.countHdb if tag_by_id[row_id] == "HDB" else med.countCondo
            return int(source.get((row_id, month), 0))
        return int(med.count.get((row_id, month), 0))

    tag_by_id = {row["id"]: str(row["policyMarketSegmentTag"]) for row in area_rows}

    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in area_rows:
        n_anchor = basis_count(row["id"], anchor)
        n_target = basis_count(row["id"], target)
        m_anchor = basis_median(row["id"], anchor)
        m_target = basis_median(row["id"], target)
        if (
            n_anchor >= MEDIAN_FLOOR
            and n_target >= MEDIAN_FLOOR
            and m_anchor is not None
            and m_target is not None
        ):
            included.append(
                {
                    **row,
                    "nAnchor": n_anchor,
                    "nTarget": n_target,
                    "medianAnchor": m_anchor,
                    "medianTarget": m_target,
                    "realisedChangePct": _pct_change(m_target, m_anchor),
                }
            )
        else:
            excluded.append(
                {
                    "id": row["id"],
                    "policyMarketSegmentTag": row["policyMarketSegmentTag"],
                    "nAnchor": n_anchor,
                    "nTarget": n_target,
                    "reason": (
                        "below the producer floor of "
                        f"{MEDIAN_FLOOR} transactions in the basis population "
                        "in the anchor or target month, or no median"
                    ),
                }
            )

    stored_errors: list[float] = []
    stored_ratios: list[float] = []
    zero_errors: list[float] = []
    zero_ratios: list[float] = []
    trend_errors: list[float] = []
    trend_ratios: list[float] = []
    seasonal_errors: list[float] = []
    seasonal_ratios: list[float] = []
    stored_dir_correct = stored_dir_n = 0
    zero_dir_correct = zero_dir_n = 0
    trend_dir_correct = trend_dir_n = 0
    seasonal_dir_correct = seasonal_dir_n = 0
    within_ci = 0
    widths: list[float] = []
    table: list[dict[str, Any]] = []

    trend_window = (_add_months(anchor, -6), anchor)
    seasonal_window = (_add_months(anchor, -18), _add_months(anchor, -12))

    for row in included:
        realised = row["realisedChangePct"]
        projected = row["projectedChangePct"]
        if projected is not None and realised is not None:
            error = projected - realised
            stored_errors.append(error)
            implied = row["medianAnchor"] * (1.0 + projected / 100.0)
            stored_ratios.append(abs(implied - row["medianTarget"]) / row["medianTarget"])
            stored_dir_n += 1
            if (realised > 0) == (projected > 0):
                stored_dir_correct += 1
            lower = row["ciLowerPct"]
            upper = row["ciUpperPct"]
            if lower is not None and upper is not None:
                widths.append(upper - lower)
                if lower <= realised <= upper:
                    within_ci += 1
        if realised is not None:
            zero_errors.append(-realised)
            zero_ratios.append(abs(row["medianAnchor"] - row["medianTarget"]) / row["medianTarget"])
            zero_dir_n += 1
            if (realised > 0) == (0.0 > 0.0):
                zero_dir_correct += 1

        trend_anchor = med.medianPrice.get((row["id"], trend_window[1]))
        trend_start = med.medianPrice.get((row["id"], trend_window[0]))
        trend_fc: float | None = None
        if trend_anchor is not None and trend_start is not None:
            trend_fc = _pct_change(trend_anchor, trend_start)
        if trend_fc is not None and trend_anchor is not None and realised is not None:
            trend_errors.append(trend_fc - realised)
            implied = trend_anchor * (1.0 + trend_fc / 100.0)
            trend_ratios.append(abs(implied - row["medianTarget"]) / row["medianTarget"])
            trend_dir_n += 1
            if (realised > 0) == (trend_fc > 0):
                trend_dir_correct += 1

        seasonal_end = med.medianPrice.get((row["id"], seasonal_window[1]))
        seasonal_start = med.medianPrice.get((row["id"], seasonal_window[0]))
        seasonal_fc: float | None = None
        if seasonal_end is not None and seasonal_start is not None:
            seasonal_fc = _pct_change(seasonal_end, seasonal_start)
        if seasonal_fc is not None and seasonal_end is not None and realised is not None:
            seasonal_errors.append(seasonal_fc - realised)
            implied = seasonal_end * (1.0 + seasonal_fc / 100.0)
            seasonal_ratios.append(abs(implied - row["medianTarget"]) / row["medianTarget"])
            seasonal_dir_n += 1
            if (realised > 0) == (seasonal_fc > 0):
                seasonal_dir_correct += 1

        if with_per_area_table:
            table.append(
                {
                    "id": row["id"],
                    "policyMarketSegmentTag": row["policyMarketSegmentTag"],
                    "nAnchor": row["nAnchor"],
                    "nTarget": row["nTarget"],
                    "medianAnchor": _r(row["medianAnchor"], 2),
                    "medianTarget": _r(row["medianTarget"], 2),
                    "realisedChangePct": _r(realised, 4),
                    "projectedChangePct": row["projectedChangePct"],
                    "ciLowerPct": row["ciLowerPct"],
                    "ciUpperPct": row["ciUpperPct"],
                    "storedErrorPct": _r(
                        row["projectedChangePct"] - realised
                        if row["projectedChangePct"] is not None and realised is not None
                        else None,
                        4,
                    ),
                    "storedWithinCi": bool(
                        row["ciLowerPct"] is not None
                        and row["ciUpperPct"] is not None
                        and row["ciLowerPct"] <= realised <= row["ciUpperPct"]
                    )
                    if realised is not None
                    else None,
                    "zeroBaselineErrorPct": _r(-realised, 4) if realised is not None else None,
                    "trendBaselineProjectedPct": _r(trend_fc, 4),
                    "seasonalBaselineProjectedPct": _r(seasonal_fc, 4),
                }
            )

    result: dict[str, Any] = {
        "anchorMonth": anchor,
        "targetMonth": target,
        "basis": basis,
        "scoringPopulation": int(len(included)),
        "excludedAreas": sorted(excluded, key=lambda item: item["id"]),
        "methods": {
            "storedForecasts": _method_metrics(
                stored_errors, stored_ratios, stored_dir_correct, stored_dir_n
            ),
            "zeroChange": _method_metrics(zero_errors, zero_ratios, zero_dir_correct, zero_dir_n),
            "trend6m": _method_metrics(trend_errors, trend_ratios, trend_dir_correct, trend_dir_n),
            "seasonalNaive": _method_metrics(
                seasonal_errors, seasonal_ratios, seasonal_dir_correct, seasonal_dir_n
            ),
        },
        "baselineDefinitions": {
            "zeroChange": "projected change = 0 percentage points (last-value naive)",
            "trend6m": (
                "projected change = the realised change over the six months "
                f"ending at the anchor ({trend_window[0]} to {trend_window[1]}), "
                "trend persistence"
            ),
            "seasonalNaive": (
                "projected change = the realised change over the same six-month "
                "window one year earlier "
                f"({seasonal_window[0]} to {seasonal_window[1]})"
            ),
        },
    }
    if stored_errors:
        result["coverage"] = {
            "nominalLevel": CI_NOMINAL,
            "nominalLevelIsAssumed": True,
            "empiricalCoverage": _r(within_ci / len(stored_errors) * 100.0, 4),
            "nWithin": int(within_ci),
            "nScored": int(len(stored_errors)),
            "meanCiWidthPct": _r(float(np.mean(widths)), 4) if widths else None,
            "minCiWidthPct": _r(float(np.min(widths)), 4) if widths else None,
            "maxCiWidthPct": _r(float(np.max(widths)), 4) if widths else None,
            "meaning": (
                "cross-sectional empirical coverage: one stored forecast period, "
                "N planning areas — the share of areas whose realised change "
                "fell inside the stored bounds. It is NOT a time-series coverage "
                "rate over repeated forecast periods; the asset stores exactly "
                "one period"
            ),
        }
    if with_per_area_table:
        result["perArea"] = table
    return result


def forecast_scoring(
    frame: pd.DataFrame, asset: dict[str, Any], last_complete: str
) -> dict[str, Any]:
    """The core measurement: expired stored projections vs realised outcomes."""
    area_rows = asset["perArea"]
    areas = [row["id"] for row in area_rows]
    asset["areasAllInFramePlanningArea"] = bool(
        set(areas).issubset(set(frame["planning_area"].dropna().unique()))
    )
    med = _medians(frame, areas)

    forecast_month = _month_of(FORECAST_DATE_STORED)
    training_month = _month_of(LAST_TRAINING_DATE_STORED)
    primary_anchor = _add_months(forecast_month, -1)
    primary_target = _add_months(primary_anchor, HORIZON_MONTHS)
    alt_forecast_anchor = forecast_month
    alt_forecast_target = _add_months(forecast_month, HORIZON_MONTHS)
    alt_training_anchor = training_month
    alt_training_target = _add_months(training_month, HORIZON_MONTHS)

    primary = _score_one_convention(
        primary_anchor,
        primary_target,
        area_rows,
        med,
        "medianPriceAllRows",
        True,
    )
    convention_forecast_month = _score_one_convention(
        alt_forecast_anchor,
        alt_forecast_target,
        area_rows,
        med,
        "medianPriceAllRows",
        False,
    )
    convention_training_month = _score_one_convention(
        alt_training_anchor,
        alt_training_target,
        area_rows,
        med,
        "medianPriceAllRows",
        False,
    )
    sensitivity_per_tag = _score_one_convention(
        primary_anchor,
        primary_target,
        area_rows,
        med,
        "medianPricePerTag",
        False,
    )
    sensitivity_psf = _score_one_convention(
        primary_anchor,
        primary_target,
        area_rows,
        med,
        "medianPsfAllRows",
        False,
    )

    # Hindsight screen: does any stored projection equal a computed realised
    # change at one decimal? A match-count screen on the primary convention's
    # per-area table only; origin unverified.
    matches = 0
    scored = 0
    for row in primary["perArea"]:
        if row["projectedChangePct"] is not None and row["realisedChangePct"] is not None:
            scored += 1
            if round(row["projectedChangePct"], 1) == round(row["realisedChangePct"], 1):
                matches += 1
    hindsight: dict[str, Any] = {
        "primaryAnchor": {
            "matchesAtOneDecimal": int(matches),
            "nCompared": int(scored),
            "meaning": (
                "a count of equality matches between stored projections and "
                "realised outcomes, rounded to one decimal, on the primary "
                "convention's per-area table — a screen, not a finding about "
                "origin. Zero matches are weak counter-evidence of hindsight, "
                "never proof of its absence; origin unverified"
            ),
        }
    }

    target_before_cutoff = primary_target <= last_complete
    generated_day = asset["generatedAt"][:10]

    return {
        "conventions": {
            "primary": {
                "anchorMonth": primary_anchor,
                "targetMonth": primary_target,
                "rule": (
                    "anchor = the calendar month immediately before the stored "
                    "forecast_date's month (the last complete month at issue); "
                    "target = anchor + the stored 6-month horizon. This is the "
                    "PRODUCER'S stated convention: the asset defines no anchor "
                    "for projected_change_pct"
                ),
            },
            "forecastMonthAnchor": {
                "anchorMonth": alt_forecast_anchor,
                "targetMonth": alt_forecast_target,
                "rule": (
                    "anchor = the forecast_date's own month; target = anchor + "
                    "6. Recorded, not primary"
                ),
            },
            "trainingMonthAnchor": {
                "anchorMonth": alt_training_anchor,
                "targetMonth": alt_training_target,
                "rule": (
                    "anchor = the last_training_date's month (2025-01); "
                    "target = anchor + 6 = the forecast_date's month. Recorded "
                    "because the stored dates make training + horizon land on "
                    "the forecast date, so a training-anchored reading is "
                    "available"
                ),
            },
            "recordedBecause": (
                "projected_change_pct carries no anchor or base definition in "
                "the asset; all three readings are measured rather than one "
                "being chosen silently"
            ),
        },
        "basis": {
            "primary": "medianPriceAllRows",
            "definition": (
                "realised change = median transaction price of ALL property "
                "types in the planning area, target month over anchor month. "
                "The asset states no property-type basis for price_forecast "
                "(only policy_risk carries a market_segment tag of unstated "
                "semantics), so the primary basis filters nothing; per-tag and "
                "median-psf bases are recorded as sensitivities"
            ),
            "floor": MEDIAN_FLOOR,
            "floorIsProducerChosen": True,
        },
        "storedDateDiscipline": {
            "forecastDateAsStored": FORECAST_DATE_STORED,
            "forecastDateAdvanced": False,
            "targetMonthUnderPrimaryConvention": primary_target,
            "targetWithinCutoff": bool(target_before_cutoff),
            "cutoffMonth": last_complete,
            "monthsPastTargetAtCutoff": None if not target_before_cutoff else None,
            "generatedAt": asset["generatedAt"],
            "generatedAtDaysAfterForecastDate": _r(
                _days_between(FORECAST_DATE_STORED, generated_day), 0
            ),
            "trainingToForecastDays": _r(
                _days_between(LAST_TRAINING_DATE_STORED, FORECAST_DATE_STORED), 0
            ),
            "meaning": (
                "the stored forecast date is read and never advanced; scoring "
                "treats the 2025-07-01 projections as EXPIRED, and every "
                "comparable outcome exists only because the realised frame has "
                "moved past the target under the measured cutoff"
            ),
        },
        "leakageChecks": {
            "trainingPrecedesForecast": _days_between(
                LAST_TRAINING_DATE_STORED, FORECAST_DATE_STORED
            )
            > 0,
            "trainingToForecastDays": _r(
                _days_between(LAST_TRAINING_DATE_STORED, FORECAST_DATE_STORED), 0
            ),
            "generatedAtDaysAfterTarget": _r(
                _days_between(_add_months(primary_target, 1) + "-01", generated_day), 0
            ),
            "hindsightScreen": hindsight,
            "meaning": (
                "the measurable leakage surfaces are date orderings (training "
                "before forecast issue: consistent) and the hindsight screen "
                "(equality of stored projections with realised outcomes: zero "
                "matches at one decimal under the primary convention). A stored "
                "payload generated long after its own target "
                "(generatedAtDaysAfterTarget) is consistent with a post-hoc "
                "export and is recorded without adjudication — nothing in the "
                "checkout establishes when the forecasts were computed relative "
                "to what data"
            ),
        },
        "primary": primary,
        "conventionSensitivity": {
            "forecastMonthAnchor": convention_forecast_month,
            "trainingMonthAnchor": convention_training_month,
        },
        "basisSensitivity": {
            "medianPricePerTag": sensitivity_per_tag,
            "medianPsfAllRows": sensitivity_psf,
            "perTagDefinition": (
                "HDB-tagged areas scored on property_type=hdb medians; "
                "PRIVATE-tagged areas on property_type=condo medians — a "
                "producer-chosen mapping of the asset's unstated tag semantics"
            ),
        },
        "coverageSummary": {
            "primaryConventionEmpiricalCoverage": primary.get("coverage", {}).get(
                "empiricalCoverage"
            ),
            "nominalLevel": CI_NOMINAL,
            "nominalLevelIsAssumed": True,
            "meaning": (
                "the asset stores no interval level; 0.95 is the producer's "
                "assumption taken from the article's own '95% CI Width' header "
                "and is flagged wherever coverage is reported"
            ),
        },
        "modelR2Naming": {
            "assetField": "metadata.model_r2 = 0.89; per-area model_r2 = 0.85 x41",
            "correctName": (
                "R-squared: a fit statistic of a model against scored data "
                "(in-sample or holdout as the case may be); NOT forecast "
                "accuracy, which is measured here as MAE/RMSE/bias/MAPE on "
                "realised outcomes"
            ),
            "meaning": (
                "the gate's 'name R-squared correctly' clause: every appearance "
                "of model_r2 in this ledger is a stored fit statistic, and "
                "forecast skill is reported only through the error metrics of "
                "forecastScoring"
            ),
        },
    }


def rolling_origin(
    frame: pd.DataFrame, asset: dict[str, Any], last_complete: str
) -> dict[str, Any]:
    """Rolling-origin validation OF THE BASELINES across monthly origins.

    The stored asset carries exactly ONE forecast date, so the stored model
    cannot be rolling-origin validated from this checkout; it enters the
    single-origin table (forecastScoring.primary) only. This is recorded, not
    hidden.
    """
    area_rows = asset["perArea"]
    areas = [row["id"] for row in area_rows]
    med = _medians(frame, areas)

    first_origin = "2024-06"
    last_origin = _add_months(last_complete, -HORIZON_MONTHS)
    origins: list[dict[str, Any]] = []
    current = first_origin
    while current <= last_origin:
        target = _add_months(current, HORIZON_MONTHS)
        conv = _score_one_convention(
            current,
            target,
            area_rows,
            med,
            "medianPriceAllRows",
            False,
        )
        origins.append(
            {
                "id": current,
                "targetMonth": target,
                "scoringPopulation": conv["scoringPopulation"],
                "maePct": {
                    "zeroChange": conv["methods"]["zeroChange"]["maePct"],
                    "trend6m": conv["methods"]["trend6m"]["maePct"],
                    "seasonalNaive": conv["methods"]["seasonalNaive"]["maePct"],
                },
            }
        )
        current = _add_months(current, 1)

    usable = [o for o in origins if o["scoringPopulation"] > 0]

    def _mean_of_per_origin(method: str) -> float | None:
        values = [o["maePct"][method] for o in usable if o["maePct"][method] is not None]
        if not values:
            return None
        return _r(float(np.mean(np.array(values, dtype=float))), 4)

    mean_mae = {
        method: _mean_of_per_origin(method) for method in ("zeroChange", "trend6m", "seasonalNaive")
    }

    return {
        "scope": "naive baselines only",
        "basis": "medianPriceAllRows",
        "firstOrigin": first_origin,
        "lastOrigin": last_origin,
        "originCount": len(origins),
        "originsWithPopulation": len(usable),
        "horizonMonths": HORIZON_MONTHS,
        "cutoffRespected": last_origin <= last_complete,
        "storedModelIncluded": False,
        "storedModelExclusionReason": (
            "the asset stores exactly one forecast date (2025-07-01), so the "
            "stored model has one origin; rolling-origin validation of the "
            "MODEL is not possible from this checkout and is recorded as "
            "notMeasurable.modelRollingOrigin"
        ),
        "perOrigin": origins,
        "meanOfPerOriginMae": mean_mae,
        "meaning": (
            "rolling-origin validation is applied to the zero-change, trend and "
            "seasonal-naive baselines across monthly origins from 2024-06 to "
            f"{last_origin}, each with the stored 6-month horizon, stopping at "
            "the measured cutoff. It contextualises the stored forecasts' "
            "single-origin errors; it does not validate the stored model"
        ),
    }


def second_vintage(
    frame: pd.DataFrame, asset: dict[str, Any], last_complete: str
) -> dict[str, Any]:
    """The 2026 data/forecasts price vintage: inventory plus level scoring."""
    csv = pd.read_csv(PRICE_FORECASTS_CSV)
    rows_6m = pd.DataFrame(csv.loc[csv["forecast_horizon"] == "6m"]).reset_index(drop=True)
    rows_12m = pd.DataFrame(csv.loc[csv["forecast_horizon"] == "12m"]).reset_index(drop=True)

    vintage_areas = sorted({str(v) for v in csv["planning_area"].dropna()})
    med = _medians(frame, vintage_areas)
    counts = med.countHdb
    medians = med.medianHdb

    def score_levels(target_month: str) -> dict[str, Any]:
        errors: list[float] = []
        ratios: list[float] = []
        within = 0
        scored_rows: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        for _index, row in rows_6m.iterrows():
            area = str(row["planning_area"])
            n_target = counts.get((area, target_month), 0)
            realised = medians.get((area, target_month))
            if n_target < MEDIAN_FLOOR or realised is None:
                excluded.append({"id": area, "nTarget": n_target})
                continue
            predicted = _number(row["predicted_value"], "predicted_value")
            lower = _number(row["confidence_lower"], "ci_lower")
            upper = _number(row["confidence_upper"], "ci_upper")
            error = predicted - realised
            errors.append(error)
            ratios.append(abs(predicted - realised) / realised)
            if lower <= realised <= upper:
                within += 1
            scored_rows.append(
                {
                    "id": area,
                    "predictedValue": _r(predicted, 2),
                    "ciLower": _r(lower, 2),
                    "ciUpper": _r(upper, 2),
                    "realisedMedianHdbPrice": _r(realised, 2),
                    "nTarget": n_target,
                    "errorSgd": _r(error, 2),
                    "withinCi": bool(lower <= realised <= upper),
                }
            )
        arr = np.array(errors, dtype=float) if errors else np.array([])
        return {
            "targetMonth": target_month,
            "basis": "median price, property_type=hdb rows, floor 10 target-month transactions",
            "scoringPopulation": int(arr.size),
            "excludedAreas": sorted(excluded, key=lambda item: item["id"]),
            "maeSgd": _r(float(np.mean(np.abs(arr))), 2) if arr.size else None,
            "rmseSgd": _r(float(np.sqrt(np.mean(arr**2))), 2) if arr.size else None,
            "biasSgd": _r(float(np.mean(arr)), 2) if arr.size else None,
            "mapeOnLevelsPct": _r(float(np.mean(ratios) * 100.0), 4) if ratios else None,
            "coverage": {
                "nominalLevel": CI_NOMINAL,
                "nominalLevelIsAssumed": True,
                "empiricalCoverage": _r(within / arr.size * 100.0, 4) if arr.size else None,
                "nWithin": int(within),
                "nScored": int(arr.size),
            },
            "perArea": scored_rows,
        }

    target_a = _month_of(str(rows_6m["forecast_date"].iloc[0]))
    target_b = _add_months(target_a, 1)
    score_a = score_levels(target_a)
    score_b = score_levels(target_b)

    asset_areas = {row["id"] for row in asset["perArea"]}
    return {
        "path": _relative(PRICE_FORECASTS_CSV),
        "twinParquet": _pin(PRICE_FORECASTS_PARQUET),
        "csvRows": int(len(csv)),
        "rows6m": int(len(rows_6m)),
        "rows12m": int(len(rows_12m)),
        "areaCount": len(vintage_areas),
        "areasOverlappingStoredAsset": len(set(vintage_areas) & asset_areas),
        "lastTrainingDate": sorted({str(v) for v in csv["last_training_date"].dropna()}),
        "forecastDatesByHorizon": {
            h: sorted({str(v) for v in csv.loc[csv["forecast_horizon"] == h, "forecast_date"]})
            for h in ("6m", "12m")
        },
        "targetMonthReading": {
            "recordedBecause": (
                "for the 2025 asset, last_training_date + horizon lands exactly "
                "on forecast_date (2025-01 + 6m = 2025-07); for this vintage, "
                "2026-01 + 6m = 2026-07 while forecast_date reads 2026-06-01, "
                "so the two vintages cannot share one reading convention. Both "
                "target months are scored"
            ),
            "forecastDateMonth": score_a,
            "forecastDateMonthPlusOne": score_b,
        },
        "rows12mNotScoreable": {
            "rows": int(len(rows_12m)),
            "targetMonth": _month_of(str(rows_12m["forecast_date"].iloc[0])),
            "cutoffMonth": last_complete,
            "reason": "target month is after the measured cutoff; no comparable outcome exists yet",
        },
        "meaning": (
            "the 2026 vintage's 6-month rows are scored on LEVELS (its own "
            "declared target median_price and property type HDB) against "
            "realised HDB medians; the 12-month rows target 2026-12, after the "
            "cutoff, and are recorded as not scoreable — an absence of "
            "comparable outcome, not a forecast defect"
        ),
    }


def feature_importance_artefacts(asset: dict[str, Any]) -> dict[str, Any]:
    """The seven CSVs under data/analysis/feature_importance, pinned and read."""
    files = []
    model_rows: list[dict[str, Any]] = []
    top_features: dict[str, Any] = {}
    feature_names: set[str] = set()
    yoy_named = 0
    comparison = FEATURE_IMPORTANCE_DIR / "model_comparison.csv"
    for path in sorted(FEATURE_IMPORTANCE_DIR.iterdir()):
        if path.is_file() and path.suffix == ".csv":
            files.append(_pin(path))
    for path in sorted(FEATURE_IMPORTANCE_DIR.iterdir()):
        if not path.is_file() or path.name == "model_comparison.csv" or path.suffix != ".csv":
            continue
        csv = pd.read_csv(path)
        names = [str(v) for v in csv["feature"].dropna()]
        feature_names.update(names)
        yoy_named += sum(1 for n in names if "yoy" in n.lower())
        first = csv.iloc[0]
        top_features[path.name] = {
            "topFeature": str(first["feature"]),
            "topImportance": _r(first["importance"], 6),
            "target": str(first["target"]),
            "model": str(first["model"]),
            "rows": int(len(csv)),
        }
    if comparison.is_file():
        comp = pd.read_csv(comparison)
        for _index, row in comp.iterrows():
            model_rows.append(
                {
                    "model": str(row["model"]),
                    "target": str(row["target"]),
                    "trainR2": _r(row["train_r2"], 6),
                    "testR2": _r(row["test_r2"], 6),
                    "testMae": _r(row["test_mae"], 6),
                    "testRmse": _r(row["test_rmse"], 6),
                }
            )
    yoy_xgb = next(
        (
            row
            for row in model_rows
            if row["target"] == "yoy_change_pct" and row["model"] == "XGBoost"
        ),
        None,
    )
    mean_train_test = None
    rounds_to_asset = None
    if yoy_xgb is not None:
        mean_train_test = _r((yoy_xgb["trainR2"] + yoy_xgb["testR2"]) / 2.0, 4)
        asset_r2 = asset["metadataModelR2"]
        rounds_to_asset = (
            bool(round(mean_train_test, 2) == round(asset_r2, 2)) if mean_train_test else False
        )

    return {
        "directory": _relative(FEATURE_IMPORTANCE_DIR),
        "files": files,
        "perTargetModelFiles": top_features,
        "modelComparison": {
            "path": _relative(comparison),
            "sha256": sha256_of(comparison),
            "rows": model_rows,
            "targets": sorted({row["target"] for row in model_rows}),
            "models": sorted({row["model"] for row in model_rows}),
            "hasTestMetrics": all(row["testR2"] is not None for row in model_rows),
            "segmentColumnExists": False,
            "columns": [
                "model",
                "train_r2",
                "test_r2",
                "train_mae",
                "test_mae",
                "train_rmse",
                "test_rmse",
                "target",
                "target_name",
            ],
        },
        "distinctFeatureNames": len(feature_names),
        "featuresNamedLikeYoyLag": yoy_named,
        "assetModelR2Screen": {
            "assetMetadataModelR2": asset["metadataModelR2"],
            "yoyXgboostTrainR2": yoy_xgb["trainR2"] if yoy_xgb else None,
            "yoyXgboostTestR2": yoy_xgb["testR2"] if yoy_xgb else None,
            "meanOfTrainAndTestR2": mean_train_test,
            "meanRoundsToAssetValue": rounds_to_asset,
            "meaning": (
                "SCREENED AS consistent, origin unverified: the asset's 0.89 "
                "equals the mean of the unlinked comparison file's XGBoost "
                "yoy_change_pct train/test R-squared pair rounded to two "
                "decimals. This is evidence in NEITHER direction: nothing "
                "links model_comparison.csv to the asset's generator, and "
                "equality of one rounded statistic cannot establish lineage. "
                "Note also what the file DOES record: train/test metrics for "
                "some run — while the split FILES themselves are absent "
                "(absenceScans.trainTestSplitFiles); the two states are kept "
                "apart"
            ),
        },
        "meaning": (
            "the checkout holds per-target, per-model global feature-importance "
            "lists and one train/test comparison file, all unlinked to the "
            "article's per-segment models in either direction. No feature list "
            "contains a name matching the article's claimed top feature (a "
            "2-year YoY appreciation), the comparison file has no segment "
            "column, and yoy_change_pct — the article's stated target — is not "
            "a column of the shipped platinum frame at all "
            "(absenceScans.yoyChangePctColumn)"
        ),
    }


def _scan_paths() -> list[Path]:
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


def _token_scan(paths: list[Path], tokens: tuple[str, ...]) -> dict[str, Any]:
    hits: dict[str, Any] = {}
    for token in tokens:
        matches: list[dict[str, Any]] = []
        for path in paths:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if token in line:
                    matches.append(
                        {"path": _relative(path), "line": number, "quote": line.strip()[:160]}
                    )
        hits[token] = {
            "occurrences": len(matches),
            "files": len({match["path"] for match in matches}),
            "firstMatches": matches[:MAX_LISTED],
            "allMatches": matches,
        }
    return hits


def corroboration_scan(asset: dict[str, Any]) -> dict[str, Any]:
    """Where the article's values and the lineage tokens appear.

    The frozen article is EXCLUDED from its own value scan (a text cannot
    corroborate itself) and its occurrences are counted separately as
    ownCopies so the exclusion is measured, not silent.
    """
    scanned = _scan_paths()
    frozen_rel = _relative(LEGACY_EDITION)
    working_rel = _relative(WORKING_EDITION)

    value_hits = _token_scan(scanned, ARTICLE_VALUE_TOKENS)
    method_hits = _token_scan(scanned, METHOD_TOKENS)

    own_copies: dict[str, Any] = {}
    for token, block in value_hits.items():
        own = [match for match in block["allMatches"] if match["path"] in (frozen_rel, working_rel)]
        independent = [match for match in block["allMatches"] if match not in own]
        own_copies[token] = {
            "occurrences": block["occurrences"],
            "inArticleCopies": len(own),
            "outsideArticleCopies": len(independent),
            "outsideFiles": sorted({match["path"] for match in independent}),
        }

    independent_files = sorted(
        {
            match["path"]
            for block in value_hits.values()
            for match in block["allMatches"]
            if match["path"] not in (frozen_rel, working_rel)
        }
    )

    return {
        "roots": list(SCAN_ROOTS),
        "suffixes": list(SCAN_SUFFIXES),
        "excludedPrefixes": list(EXCLUDED_SCAN_PREFIXES),
        "excludedPaths": [path for path in EXCLUDED_SCAN_PATHS if path != frozen_rel],
        "excludedEditionTexts": "docs/analytics/editions/** except editions/legacy/**",
        "excludedClaimSource": frozen_rel,
        "excludedClaimSourceReason": (
            "the frozen article is the CLAIM SOURCE for these tokens; a text "
            "cannot corroborate itself. Its occurrences, and the working "
            "copy's, are counted separately as ownCopies"
        ),
        "filesScanned": len(scanned),
        "valueTokens": value_hits,
        "ownCopies": own_copies,
        "independentMatchFiles": independent_files,
        "meaning": (
            "outside the article's own two copies (the frozen text and the "
            "working copy docs/analytics/price-forecasts.md), the table values "
            "appear only in sibling legacy articles that quote the same numbers "
            "(findings.md for the segment table, school-quality.md for the "
            "XGBoost parameters) and one plan document (ARIMA(1,1,1) in "
            "docs/plans/2026-02-19-pipeline-improvements-plan.md) — cross-"
            "citation inside documents, never a data or code artefact. NO "
            "JSON, CSV or producer output in the scanned roots carries any of "
            "the table's values, which is the measured boundary of the "
            "per-segment table's provenance: absent, not merely unstated. "
            "Cross-citation between articles is corroboration of neither "
            "direction and is not claimed as any"
        ),
        "methodTokens": method_hits,
        "methodTokensMeaning": (
            "predictive_analytics appears in app/src consumers and plan/"
            "register documents but in NO script under scripts/; "
            "price_appreciation_train appears nowhere outside the frozen and "
            "working article copies; app/src/components/studies/ (edition "
            "registry/pages) and app/tests/ (fixtures) are excluded programme "
            "outputs; .secrets.baseline and docs/plans/2026-11-12-reporting-"
            "refresh-decisions.md (D12 register) are also excluded; "
            "hdb_price_forecasts appears only in the "
            "archive reorganization listing. These are counts of references in "
            "the scanned roots, disclosed file by file"
        ),
    }


def absence_scans(frame_schema_names: list[str]) -> dict[str, Any]:
    """Every absence with its boundary: roots, exclusions, matched counts."""
    # Filename scans cover the checkout while excluding transient caches,
    # generated build outputs, and the disclosed programme surfaces below.
    scan_roots_all = [p for p in sorted(REPO_ROOT.rglob("*")) if p.is_file()]
    scanned_names = 0
    train_matches: list[str] = []
    unified_matches: list[str] = []
    for path in scan_roots_all:
        relative = _relative(path)
        if relative.startswith(FILENAME_SCAN_EXCLUDED_PREFIXES) or any(
            part in TRANSIENT_SCAN_DIRS for part in path.relative_to(REPO_ROOT).parts
        ):
            continue
        if relative.startswith(EDITION_PREFIX) and not relative.startswith(RETAINED_EDITION_PREFIX):
            continue
        if relative == "docs/plans/2026-11-12-reporting-refresh-decisions.md":
            continue
        scanned_names += 1
        name = path.name
        if name in ("price_appreciation_train.parquet", "price_appreciation_test.parquet"):
            train_matches.append(relative)
        if name == "housing_unified.parquet":
            unified_matches.append(relative)

    scripts_predictive = [
        match
        for match in corroboration_scan_cache["methodTokens"]["predictive_analytics"]["allMatches"]
        if match["path"].startswith("scripts/")
    ]
    script_files_scanned = sum(
        1 for path in _scan_paths() if _relative(path).startswith("scripts/")
    )

    return {
        "trainTestSplitFiles": {
            "claimedFiles": [
                "price_appreciation_train.parquet",
                "price_appreciation_test.parquet",
            ],
            "roots": "whole checkout tree, excluding transient caches/build outputs, programme surfaces, the D12 register path, and docs/analytics/editions/** except editions/legacy/**",
            "exclusions": {
                "prefixes": list(FILENAME_SCAN_EXCLUDED_PREFIXES),
                "paths": ["docs/plans/2026-11-12-reporting-refresh-decisions.md"],
                "editionRule": "docs/analytics/editions/** excluded except docs/analytics/editions/legacy/**",
                "meaning": "any directory component matching the disclosed cache/build prefixes is excluded so filesScanned is independent of local test, type-check, lint and frontend build runs; programme surfaces and non-legacy editions are separately excluded",
            },
            "filesScanned": scanned_names,
            "matches": train_matches,
            "matchCount": len(train_matches),
            "boundaryNote": (
                "this is a FILENAME scan of the declared tree after the "
                "disclosed cache, build-output and programme-surface exclusions; "
                "it cannot see inside archives or untracked media that are not "
                "files on disk"
            ),
            "meaning": (
                "an ABSENT FILE state within the declared filename-scan "
                "boundary: the split datasets the article names have no "
                "matching filenames. What DOES exist is a comparison file "
                "recording train/test METRICS for an unlinked run "
                "(featureImportanceArtefacts.modelComparison) — metrics "
                "without their split files, kept as separate states"
            ),
        },
        "primaryInputPath": {
            "claimedPath": "data/parquets/L3/housing_unified.parquet",
            "pathExists": (
                REPO_ROOT / "data" / "parquets" / "L3" / "housing_unified.parquet"
            ).is_file(),
            "filenameMatches": unified_matches,
            "filenameMatchCount": len(unified_matches),
            "meaning": (
                "the claimed primary input path does not exist; no file named "
                "housing_unified.parquet exists in the tree. The shipped "
                "platinum frame this pack reads is "
                "data/pipeline/04_platinum/unified_dataset.parquet (inputs)"
            ),
        },
        "producerScripts": {
            "root": "scripts/",
            "filesScanned": script_files_scanned,
            "predictiveAnalyticsReferencesInScripts": len(scripts_predictive),
            "meaning": (
                "no script under the scanned scripts/ root references "
                "predictive_analytics: the producer of the stored asset is not "
                "in the checkout. A reference count of zero in a bounded root "
                "is counter-evidence for 'none was found', never proof that no "
                "producer ever existed"
            ),
        },
        "yoyChangePctColumn": {
            "state": "absent column",
            "frameColumnCount": len(frame_schema_names),
            "columnPresent": "yoy_change_pct" in frame_schema_names,
            "meaning": (
                "the article's stated modelling target yoy_change_pct is NOT a "
                "column of the shipped platinum frame — an ABSENT COLUMN, "
                "distinct from a null value, a recorded zero, or an absent row. "
                "The name survives only in unlinked artefacts "
                "(featureImportanceArtefacts) whose computation used some other "
                "input in some other run"
            ),
        },
    }


def app_consumption() -> dict[str, Any]:
    """How the shipped app surfaces the stored forecasts and signals."""
    return {
        "consumerFiles": [_pin(MAP_ARCHIVE_TS), _pin(DATA_URLS_TS)],
        "forecastLayer": {
            "id": "predictive.forecast",
            "label": _code_quote(
                MAP_ARCHIVE_TS, 'label: "Historical forecast"', "forecast layer label"
            ),
            "gate": _code_quote(
                MAP_ARCHIVE_TS,
                "The target date is in the past; this is not a forward forecast.",
                "forecast layer gate",
            ),
        },
        "signalPresentation": {
            "label": _code_quote(
                MAP_ARCHIVE_TS, 'label: "Stored signal (archive, not advice)"', "signal label"
            ),
        },
        "withheldPrompts": {
            "quote": _code_quote(
                TOOL_EVIDENCE_TS,
                "BUY/SELL prompts and return simulations are withheld",
                "withheld-prompts banner",
            ),
        },
        "gateClauseCheck": {
            "clause": "never reuse BUY/SELL prompts as current advice",
            "shippedSurfaceLabelsSignalArchiveNotAdvice": True,
            "thisPackChangesNoAppFile": True,
            "meaning": (
                "the shipped map-archive surface already presents the stored "
                "signal as archive material, not advice, and the tools "
                "workspace withholds BUY/SELL prompts outright; this pack "
                "records those labels with line citations and changes no app "
                "file. The WITHDRAWAL of the 41 BUY signals is a disposition of "
                "this pack applying to the edition text, not a state change"
            ),
        },
    }


def not_measurable(asset: dict[str, Any], last_complete: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "analysisWindow",
            "claim": "Data Period 2021-2026",
            "status": "notReproducible",
            "note": (
                "no artefact records the retired run's window selection; the "
                "frame spans 1990-01 to the terminal month and any 2021-2026 "
                "slice would be a producer choice, not a recovery"
            ),
        },
        {
            "id": "featureSelectionRule",
            "claim": "numeric only, max 20% missing values allowed",
            "status": "notRecorded",
            "note": "no preprocessing artefact states the feature universe or the missingness rule that was applied",
        },
        {
            "id": "xgboostParameters",
            "claim": "n_estimators=100, max_depth=6, learning_rate=0.1, subsample=0.8",
            "status": "notRecorded",
            "note": (
                "the parameter string appears only in the article's own copies "
                "and a sibling legacy article (corroborationScan); no config, "
                "log or code artefact records a run with these values"
            ),
        },
        {
            "id": "arimaSpec",
            "claim": "ARIMA(1,1,1) per planning area",
            "status": "notRecorded",
            "note": (
                "the order string appears in the article copies and one plan "
                "document; no fitted ARIMA output exists in the checkout"
            ),
        },
        {
            "id": "arimaCoverage",
            "claim": "20 planning areas with >=12 months of data",
            "status": "notReproducible",
            "note": (
                "the claim is about the retired run's input coverage; the "
                "stored asset covers 41 areas (predictiveAsset.areaCount), a "
                "different population recorded without adjudicating the "
                "article's number"
            ),
        },
        {
            "id": "smartEnsemble",
            "claim": "stacked model combining segment-specific predictions",
            "status": "notRecorded",
            "note": "no ensemble artefact, stack weights or per-segment predictions exist in the checkout",
        },
        {
            "id": "ciCalibration",
            "claim": "confidence intervals calibrated per segment using residual distributions",
            "status": "notRecorded",
            "note": (
                "no calibration artefact or residual dump exists; the stored "
                "interval level is itself unstated — this pack's 0.95 nominal "
                "coverage assumption is flagged at every use "
                "(forecastScoring.coverageSummary)"
            ),
        },
        {
            "id": "perSegmentOutputs",
            "claim": "the per-segment R-squared/CI/directional table",
            "status": "notReproducible",
            "note": (
                "the table's values exist only in the article's own copies and "
                "sibling legacy articles (corroborationScan); the stored asset "
                "carries no segment-keyed block; withdrawn, not re-estimated"
            ),
        },
        {
            "id": "modelRollingOrigin",
            "claim": "rolling-origin validation of the stored model itself",
            "status": "notMeasurableFromAsset",
            "note": (
                "the asset stores exactly one forecast date, so the model has "
                "one origin; rolling-origin validation was applied to the "
                "naive baselines instead (rollingOrigin), and the single-origin "
                "model errors are reported at forecastScoring.primary"
            ),
        },
        {
            "id": "projectedChangeSemantics",
            "claim": "the base/anchor of projected_change_pct",
            "status": "notRecorded",
            "note": (
                "the asset defines no anchor; three readings are measured "
                "(forecastScoring.conventions) rather than one being chosen "
                "silently"
            ),
        },
        {
            "id": "lineageEquivalence",
            "claim": "article/model equivalence (RA02 register requirement for any replacement)",
            "status": "notDemonstrated",
            "note": (
                "nothing in this checkout links the article's per-segment "
                "models to the stored per-area asset; equivalence must be "
                "demonstrated by a future producer, not assumed by this pack"
            ),
        },
        {
            "id": "secondVintageTargetMonth",
            "claim": "the 2026 vintage's target-month reading",
            "status": "notRecorded",
            "note": (
                "the vintage's forecast_date convention does not match the 2025 "
                "asset's training+horizon arithmetic; both readable target "
                "months are scored (secondVintage.targetMonthReading)"
            ),
        },
        {
            "id": "plotPanelLinkage",
            "claim": "the two forecast PNG panels' run linkage",
            "status": "notRecorded",
            "note": (
                "nothing in the checkout ties the panels to any vintage; they "
                "are pinned and described visually at lineage.plotPanels and "
                "adjudicate nothing in either direction"
            ),
        },
    ]


LEGACY_CLAIMS: list[dict[str, str]] = [
    {
        "id": "C01",
        "phrase": "**Analysis Date**: 2026-02-17",
        "status": "not-reproducible",
        "ledgerKey": "lineage.vintages.0.meaning",
        "note": (
            "the article's analysis date has no artefact behind it; the stored "
            "asset's generated_at (2026-02-19) is a different, later timestamp "
            "recorded at predictiveAsset.generatedAt — two dates, no linkage"
        ),
    },
    {
        "id": "C02",
        "phrase": "**Data Period**: 2021-2026",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.analysisWindow",
        "note": "the window selection of the retired run is unrecorded; recording a 2021-2026 slice of the frame would prescribe what the source does not state",
    },
    {
        "id": "C03",
        "phrase": "**Coverage**: HDB, condo, and EC segments",
        "status": "not-reproducible",
        "ledgerKey": "predictiveAsset.policyMarketSegmentTags",
        "note": (
            "the stored asset tags its 41 areas HDB(24)/PRIVATE(17) with no EC "
            "grouping; the article's three-segment coverage has no stored "
            "counterpart and the retired run's coverage is unverifiable"
        ),
    },
    {
        "id": "C04",
        "phrase": "| HDB flats          | 79.8%         | ±18.58%      | 99.4%           | Strong                       |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.reliabilityTable.rows.hdb",
        "note": "per-segment R-squared table row: withdrawn per the gate; no artefact carries these values outside the article's own copies",
    },
    {
        "id": "C05",
        "phrase": "| Executive Condos   | 98.5%         | ±50.15%      | 97.1%           | Strong but wider uncertainty |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.reliabilityTable.rows.ec",
        "note": "per-segment table row: withdrawn; values appear only in the article's own copies and sibling legacy articles (corroborationScan)",
    },
    {
        "id": "C06",
        "phrase": "| Mass Market Condos | 85.6%         | ±40.48%      | 96.4%           | Useful with caution          |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.reliabilityTable.rows.mass",
        "note": "per-segment table row: withdrawn",
    },
    {
        "id": "C07",
        "phrase": "| Mid Market Condos  | 72.6%         | ±1877.88%    | 94.2%           | Direction only               |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.reliabilityTable.rows.mid",
        "note": "per-segment table row: withdrawn; the ±1877.88% width is itself a red flag no artefact explains",
    },
    {
        "id": "C08",
        "phrase": "| Luxury Condos      | 30.1%         | ±1076.24%    | 92.3%           | Magnitude unusable           |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.reliabilityTable.rows.lux",
        "note": "per-segment table row: withdrawn",
    },
    {
        "id": "C09",
        "phrase": "| HDB               | 2-year YoY appreciation | 51.14%     |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.featureClaims.hdbFeature",
        "note": "per-segment feature-importance claim: withdrawn; no checkout feature list contains such a feature name (featureImportanceArtefacts.featuresNamedLikeYoyLag)",
    },
    {
        "id": "C10",
        "phrase": "| Mass market condo | 2-year YoY appreciation | 65.50%     |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.featureClaims.massFeature",
        "note": "per-segment feature-importance claim: withdrawn",
    },
    {
        "id": "C11",
        "phrase": "- **Primary input**: `data/parquets/L3/housing_unified.parquet` (2021-2026)",
        "status": "not-reproducible",
        "ledgerKey": "absenceScans.primaryInputPath",
        "note": "the named path does not exist in this checkout (0 filename matches); which input the retired run used is unverifiable",
    },
    {
        "id": "C12",
        "phrase": "- **Train/test split**: `price_appreciation_train.parquet` / `price_appreciation_test.parquet`",
        "status": "not-reproducible",
        "ledgerKey": "absenceScans.trainTestSplitFiles",
        "note": "0 filename matches in the whole tree; train/test metrics exist only in an unlinked comparison file",
    },
    {
        "id": "C13",
        "phrase": "- **Forecast horizon**: 6 months (ARIMA), annual (XGBoost ensemble)",
        "status": "not-reproducible",
        "ledgerKey": "lineage",
        "note": (
            "the claimed horizons describe the retired article workflow; the "
            "stored asset and 2026 vintage are separate, unlinked forecast "
            "families and cannot re-measure that workflow. Their own horizons "
            "are inventoried independently"
        ),
    },
    {
        "id": "C14",
        "phrase": "- **Feature selection**: numeric only, max 20% missing values allowed",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.featureSelectionRule",
        "note": "no preprocessing artefact states the rule as applied",
    },
    {
        "id": "C15",
        "phrase": "- **XGBoost models** were trained per property type (HDB, Condo, EC) in the historical research workflow",
        "status": "not-reproducible",
        "ledgerKey": "articleVsAsset.perSegmentModelOutputs",
        "note": "per-property-type model outputs are absent from the checkout; the asset's blocks carry no property-type model fields",
    },
    {
        "id": "C16",
        "phrase": "  - Parameters: n_estimators=100, max_depth=6, learning_rate=0.1, subsample=0.8",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.xgboostParameters",
        "note": "the parameter string exists only in article copies and a sibling legacy article; no run artefact",
    },
    {
        "id": "C17",
        "phrase": "- **Target variable**: `yoy_change_pct` (year-over-year appreciation)",
        "status": "not-reproducible",
        "ledgerKey": "absenceScans.yoyChangePctColumn",
        "note": (
            "the stated target is an ABSENT COLUMN of the shipped platinum "
            "frame; the name survives only in unlinked importance artefacts"
        ),
    },
    {
        "id": "C18",
        "phrase": "- **Smart ensemble**: stacked model combining segment-specific predictions",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.smartEnsemble",
        "note": "no ensemble artefact exists",
    },
    {
        "id": "C19",
        "phrase": "- **Confidence intervals**: calibrated per segment using residual distributions",
        "status": "not-reproducible",
        "ledgerKey": "forecastScoring.coverageSummary",
        "note": (
            "the calibration procedure is unrecorded; what this pack adds is "
            "the EMPIRICAL coverage of the stored bounds against realised "
            "outcomes, at an assumed and flagged 0.95 nominal level"
        ),
    },
    {
        "id": "C20",
        "phrase": "- **ARIMA(1,1,1)** for time-series forecasting per planning area",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.arimaSpec",
        "note": "the order string appears in article copies and one plan document; no fitted output exists",
    },
    {
        "id": "C21",
        "phrase": "for time-series forecasting per planning area",
        "status": "not-reproducible",
        "ledgerKey": "lineage",
        "note": (
            "the phrase describes the retired time-series workflow; the "
            "stored asset's planning-area granularity is independently "
            "inventoried but is unlinked and cannot re-measure the legacy "
            "method claim"
        ),
    },
    {
        "id": "C22",
        "phrase": "- **Condo sub-segmentation**: mass market, mid market, luxury",
        "status": "not-reproducible",
        "ledgerKey": "predictiveAsset.policyMarketSegmentTags",
        "note": "the asset's tags are HDB/PRIVATE only; no mass/mid/luxury grouping exists anywhere in the checkout",
    },
    {
        "id": "C23",
        "phrase": "| HDB                | 79.8% | 99.4%                | ±18.58%      |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.technicalTable.rows.hdb",
        "note": "appendix repeat of the segment table: withdrawn",
    },
    {
        "id": "C24",
        "phrase": "| Executive Condos   | 98.5% | 97.1%                | ±50.15%      |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.technicalTable.rows.ec",
        "note": "appendix repeat: withdrawn",
    },
    {
        "id": "C25",
        "phrase": "| Mass Market Condos | 85.6% | 96.4%                | ±40.48%      |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.technicalTable.rows.mass",
        "note": "appendix repeat: withdrawn",
    },
    {
        "id": "C26",
        "phrase": "| Mid Market Condos  | 72.6% | 94.2%                | ±1877.88%    |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.technicalTable.rows.mid",
        "note": "appendix repeat: withdrawn",
    },
    {
        "id": "C27",
        "phrase": "| Luxury Condos      | 30.1% | 92.3%                | ±1076.24%    |",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.technicalTable.rows.lux",
        "note": "appendix repeat: withdrawn",
    },
    {
        "id": "C28",
        "phrase": "- **Top feature**: 2-year YoY appreciation (51.14% importance for HDB, 65.50% for mass-market condo)",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.featureClaims.combined",
        "note": "combined feature-importance claim: withdrawn",
    },
    {
        "id": "C29",
        "phrase": "- **ARIMA**: 20 planning areas with ≥12 months of data, 6-month forecast horizon",
        "status": "not-reproducible",
        "ledgerKey": "notMeasurable.arimaCoverage",
        "note": (
            "the retired run's input coverage is unverifiable; the stored asset "
            "covers 41 areas (predictiveAsset.areaCount) with a 6-month horizon "
            "(predictiveAsset.horizonMonths) — recorded, not adjudicated"
        ),
    },
    {
        "id": "C30",
        "phrase": "- **Ensemble accuracy**: 74% vs 47% for a unified one-size-fits-all model",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.ensembleAccuracyClaim",
        "note": "'accuracy' is undefined (metric, population, window all unstated): withdrawn, not re-measured",
    },
    {
        "id": "C31",
        "phrase": "Segment-specific modeling dramatically outperforms unified approaches (74% vs 47% accuracy).",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.ensembleAccuracyClaim",
        "note": "conclusion repeat of C30: withdrawn",
    },
    {
        "id": "C32",
        "phrase": "luxury condos are essentially unpredictable in magnitude (R²=30.1%, CI width ±1076%).",
        "status": "withdrawn",
        "ledgerKey": "articleVsAsset.reliabilityTable.rows.lux",
        "note": "conclusion repeat of the luxury row (C08): withdrawn",
    },
]


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
            if part.isdigit():
                index = int(part)
                if index >= len(node):
                    return False
                node = node[index]
            else:
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
        "method": (
            "each claim's ledgerKey is resolved against this ledger at build "
            "time by walking dict keys and list items by index or by their "
            "`id`; an unresolved key fails the build rather than shipping. "
            "Resolution is SYNTACTIC: it certifies that the key addresses a "
            "field in this ledger, not that the field's content supports the "
            "disposition"
        ),
    }


# Populated by corroboration_scan for absence_scans' reuse without a re-read.
corroboration_scan_cache: dict[str, Any] = {
    "filesScanned": 0,
    "methodTokens": {"predictive_analytics": {"allMatches": []}},
}


def build() -> dict[str, Any]:
    frame = pd.read_parquet(
        UNIFIED,
        columns=["month", "property_type", "planning_area", "price", "psf"],
    )
    schema_names = list(pq.read_schema(UNIFIED).names)
    measured_cutoff = cutoff(frame)
    last_complete = measured_cutoff["lastCompleteMonth"]

    asset = predictive_asset()
    scoring = forecast_scoring(frame, asset, last_complete)
    rolling = rolling_origin(frame, asset, last_complete)
    second = second_vintage(frame, asset, last_complete)
    importance = feature_importance_artefacts(asset)
    global corroboration_scan_cache
    scanned_paths = _scan_paths()
    corroboration_scan_cache = {
        "filesScanned": len(scanned_paths),
        "methodTokens": _token_scan(scanned_paths, METHOD_TOKENS),
    }
    absences = absence_scans(schema_names)
    claims = legacy_claims()

    inputs: dict[str, Any] = {}
    pin_list = [
        UNIFIED,
        PREDICTIVE_ASSET,
        LEGACY_EDITION,
        WORKING_EDITION,
        PRICE_FORECASTS_CSV,
        PRICE_FORECASTS_PARQUET,
        YIELD_FORECASTS_CSV,
        YIELD_FORECASTS_PARQUET,
        MAP_ARCHIVE_TS,
        DATA_URLS_TS,
        TOOL_EVIDENCE_TS,
        ARCHIVE_REORG_DOC,
    ]
    pin_list.extend(sorted(FEATURE_IMPORTANCE_DIR.glob("*.csv")))
    pin_list.extend(sorted(PRICE_FORECAST_PANEL_DIR.glob("*.png")))
    for path in pin_list:
        entry = {"sha256": sha256_of(path), "bytes": int(path.stat().st_size)}
        inputs[_relative(path)] = entry
    inputs[_relative(UNIFIED)]["rows"] = int(pq.ParquetFile(UNIFIED).metadata.num_rows)
    inputs[_relative(UNIFIED)]["columns"] = len(schema_names)
    inputs[_relative(PRICE_FORECASTS_PARQUET)]["rows"] = int(
        pq.ParquetFile(PRICE_FORECASTS_PARQUET).metadata.num_rows
    )
    inputs[_relative(PRICE_FORECASTS_PARQUET)]["columns"] = int(
        len(pq.read_schema(PRICE_FORECASTS_PARQUET).names)
    )
    inputs[_relative(YIELD_FORECASTS_PARQUET)]["rows"] = int(
        pq.ParquetFile(YIELD_FORECASTS_PARQUET).metadata.num_rows
    )
    inputs[_relative(YIELD_FORECASTS_PARQUET)]["columns"] = int(
        len(pq.read_schema(YIELD_FORECASTS_PARQUET).names)
    )

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "study": "RS14",
        "series": "price-forecasts",
        "scope": (
            "RS14 price-forecasts evidence: lineage reconciliation of the "
            "stored predictive asset against the article and the checkout's "
            "other forecast-bearing artefacts, a scoring of the expired "
            "2025-07-01 projections against realised outcomes through the "
            "measured cutoff with naive baselines and interval coverage, "
            "rolling-origin validation of the baselines, and the disposition "
            "of every quantitative claim of the frozen legacy article"
        ),
        "definition": DEFINITION,
        "inputs": inputs,
        "cutoff": measured_cutoff,
        "predictiveAsset": asset,
        "articleVsAsset": article_vs_asset(asset),
        "lineage": lineage(asset),
        "forecastScoring": scoring,
        "rollingOrigin": rolling,
        "secondVintage": second,
        "featureImportanceArtefacts": importance,
        "corroborationScan": corroboration_scan(asset),
        "absenceScans": absences,
        "appConsumption": app_consumption(),
        "notMeasurable": not_measurable(asset, last_complete),
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
        print("Pass: RS14 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS14 ledger does not match this checkout")
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

    scoring = evidence["forecastScoring"]["primary"]
    print(
        f"Cutoff: last complete month {evidence['cutoff']['lastCompleteMonth']} "
        f"(terminal {evidence['cutoff']['terminalMonth']} at "
        f"{evidence['cutoff']['terminalMonthShareOfTrailingMedian']} of the trailing median)"
    )
    print(
        "Predictive asset: "
        f"{evidence['predictiveAsset']['areaCount']} areas, "
        f"forecast date {evidence['predictiveAsset']['distinctForecastDates'][0]}, "
        f"signals {evidence['predictiveAsset']['signalCounts']}"
    )
    print(
        f"Scoring window: {scoring['anchorMonth']} -> {scoring['targetMonth']}, "
        f"population {scoring['scoringPopulation']} areas "
        f"(excluded {len(scoring['excludedAreas'])})"
    )
    for method, metrics in scoring["methods"].items():
        print(
            f"  {method}: MAE {metrics['maePct']}pp, bias {metrics['biasPct']}pp, "
            f"directional {metrics['directionalHitPct']}% (n={metrics['n']})"
        )
    coverage = scoring.get("coverage")
    if coverage:
        print(
            f"  stored CI coverage (nominal {coverage['nominalLevel']}): "
            f"{coverage['empiricalCoverage']}% ({coverage['nWithin']}/{coverage['nScored']})"
        )
    print(
        "Rolling origin: "
        f"{evidence['rollingOrigin']['originCount']} origins, "
        f"mean per-origin MAE {evidence['rollingOrigin']['meanOfPerOriginMae']}"
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
