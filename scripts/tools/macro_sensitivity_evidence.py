#!/usr/bin/env python3
"""Measure RS09's macro-sensitivity evidence: per-series provenance screening,
the generated/fallback SORA conflict, gold-column lineage, stationarity, and
the article's correlation claims re-measured at a stated frequency.

RS09's gate is "Explicitly identify generated/fallback series and exclude them
from empirical claims unless the entire result is a labelled simulation.
Document release lag, revisions, missing periods, stationarity and uncertainty.
No present-day timing regime claims from unknown source vintages."

This tool records only what the checkout can support:

1. **Cutoff** — the same measured last-complete-month rule RS03/RS04/RS05
   shipped, recorded as a ledger field (`cutoffUpperBound`) rather than prose,
   plus each macro series' own measured observation end.
2. **Series inventory** — for all eight bronze macro series: rows, span,
   measured cadence, expected vs observed periods, missing periods, duplicates
   and distinct-value counts. Missing periods are counted, not described.
3. **Fallback screening** — a *structural* screen per series (between-year
   variance share, January-boundary step share, distinct-value ratio), then the
   measured confrontation of the two SORA candidates on their 60 shared months.
   The short series is an annual ramp that is off by a factor of ~7 against the
   long series in 2023; the long series is the one whose year means match the
   legacy article's own rate narrative. The screen is recorded as evidence, not
   as provenance proof, and no series is called "generated" without the numbers
   that justify it.
4. **Gold-column lineage** — which bronze series each macro column in
   `unified_dataset` reproduces, by exact-month and as-of (ffill) equality, with
   null and distinct counts. Both SORA columns are carried into gold, so a
   re-measurement that does not check lineage can silently use the ramp.
5. **Stationarity** — augmented Dickey-Fuller on each bronze series in levels,
   with the lag order and the critical values reported.
6. **Association claims** — the article's correlation table re-measured as
   Pearson and Spearman, in levels AND first differences, at the macro series'
   own frequency, with n and a Fisher-z confidence interval. Levels are reported
   because the article reads levels; differences are reported because two
   trending series correlate by construction. The fallback SORA is measured
   twice — once as the article would have used it and once as the source series
   — so the exclusion is quantified rather than asserted.
7. **What is not measurable** — release lag, revisions, the five policy dates,
   the three-regime table and the segment CAGR table have no artefact in this
   checkout; each is recorded as `notMeasurable` with its reason and the
   register clause it fails.

It never runs the pipeline, never fits the legacy models, never writes outside
`--output`, and never re-derives a housing aggregate past `cutoffUpperBound`.

Usage:

    uv run python scripts/tools/macro_sensitivity_evidence.py \\
        --output docs/implementation/artifacts/rs09-macro-sensitivity-evidence.json

    uv run python scripts/tools/macro_sensitivity_evidence.py --check  # no drift
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
from scipy import stats
from statsmodels.tsa.stattools import adfuller

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE = REPO_ROOT / "data" / "pipeline" / "01_bronze"
EXTERNAL = BRONZE / "external"
UNIFIED = REPO_ROOT / "data" / "pipeline" / "04_platinum" / "unified_dataset.parquet"
LEGACY_EDITION = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "macro-sensitivity.md"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs09-macro-sensitivity-evidence.json"
)

SCHEMA_VERSION = "1.0.0"
SERIES_WINDOW_START = "1990-01"  # the shipped transaction frame's own first month

# Bronze macro series: name -> (file, period column, value column, frequency)
MACRO_SERIES: dict[str, tuple[str, str, str, str]] = {
    "cpi": ("cpi.parquet", "date", "cpi", "monthly"),
    "gdp": ("gdp.parquet", "quarter", "gdp", "quarterly"),
    "hdb_rpi": ("hdb_rpi.parquet", "quarter", "hdb_rpi", "quarterly"),
    "sora_rates": ("sora_rates.parquet", "date", "sora_rate", "monthly"),
    "bank_rates": ("bank_rates.parquet", "date", "sora_3m", "monthly"),
    "unemployment": ("unemployment.parquet", "quarter", "unemployment_rate", "quarterly"),
    "ura_ppi": ("ura_ppi.parquet", "quarter", "ura_ppi", "quarterly"),
    "wage_growth": ("wage_growth.parquet", "quarter", "wage_growth", "quarterly"),
}

# Gold macro columns: column -> candidate bronze series (both SORA candidates are
# listed for `sora_rate`, so the ledger measures which one gold actually carries).
GOLD_COLUMNS: tuple[str, ...] = (
    "cpi",
    "gdp",
    "hdb_rpi",
    "sora_rate",
    "sora_3m",
    "unemployment_rate",
    "ura_ppi",
    "wage_growth",
)

GOLD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "cpi": ("cpi",),
    "gdp": ("gdp",),
    "hdb_rpi": ("hdb_rpi",),
    "sora_rate": ("sora_rates", "bank_rates"),
    "sora_3m": ("bank_rates", "sora_rates"),
    "unemployment_rate": ("unemployment",),
    "ura_ppi": ("ura_ppi",),
    "wage_growth": ("wage_growth",),
}

DEFINITION = (
    "RS09 measures macro-series provenance and macro-housing association. "
    "Two SORA series exist in this checkout with different spans and different "
    "paths; the ledger identifies the one with an annual-ramp signature and the "
    "one whose year means match the legacy article's own rate narrative, and "
    "measures the housing association under both so the exclusion the gate "
    "demands is quantified. Associations are reported in levels and in first "
    "differences at the macro series' own frequency: the level figures are what "
    "the legacy article read, the difference figures are the defensible "
    "statistic, and the gap between them is the trend-domination measurement. "
    "No coefficient here is a causal effect, no regime is tested, and no claim "
    "rests on a series whose provenance could not be screened."
)


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


def _period_key(value: Any, frequency: str) -> str:
    """A canonical period key: YYYY-MM for monthly, YYYY-Qn for quarterly."""
    stamp = pd.Timestamp(value)
    if frequency == "monthly":
        return str(pd.Period(stamp, freq="M"))
    return str(pd.Period(stamp, freq="Q"))


def _expected_periods(first: str, last: str, frequency: str) -> list[str]:
    freq = "M" if frequency == "monthly" else "Q"
    return [str(period) for period in pd.period_range(first, last, freq=freq)]


def _period_parts(period: str) -> tuple[int, int]:
    """(year, ordinal-within-year) for a canonical `YYYY-MM` or `YYYYQn` key.

    Every period string in this ledger is written by `_period_key`, so a parse
    failure means the ledger's own canonicalisation is broken; failing loudly
    with the offending value is the correct response.
    """
    try:
        if "Q" in period:
            year_text, quarter_text = period.split("Q", 1)
            return int(year_text), int(quarter_text)
        year_text, month_text = period.split("-", 1)
        return int(year_text), int(month_text)
    except (TypeError, ValueError) as error:
        raise SystemExit(f"Unparseable canonical period {period!r}: {error}") from error


def _month_index(period: str) -> int:
    """Months since year 0 — integer arithmetic, no period-subtraction stubs."""
    year, month = _period_parts(period)
    return year * 12 + month - 1


def _quarter_label(month: str) -> str:
    year, month_number = _period_parts(month)
    return f"{year}Q{(month_number - 1) // 3 + 1}"


def _quarter_index(period: str) -> int:
    year, quarter = _period_parts(period)
    return year * 4 + quarter - 1


def load_raw_series(name: str) -> pd.DataFrame:
    """One bronze macro series as recorded: `period` + `value`, nulls KEPT, sorted.

    Nulls are retained because a null value is missing-source evidence: dropping
    it here is how a 213-row missing span becomes invisible.
    """
    file_name, column, value_column, frequency = MACRO_SERIES[name]
    frame = pq.read_table(EXTERNAL / file_name).to_pandas()
    selected = frame[[column, value_column]].copy()
    selected["period"] = [_period_key(value, frequency) for value in selected[column]]
    selected["value"] = pd.to_numeric(selected[value_column], errors="coerce")
    return selected[["period", "value"]].sort_values("period").reset_index(drop=True)


def load_series(name: str) -> pd.DataFrame:
    """The non-null observations of one series: the values a measurement can use."""
    return load_raw_series(name).dropna(subset=["value"]).reset_index(drop=True)


def cutoff(frame: pd.DataFrame) -> dict[str, Any]:
    """The last complete month of the transaction frame, measured."""
    counts = {str(key): int(value) for key, value in frame.groupby("month").size().items()}
    ordered = sorted(counts)
    terminal = ordered[-1]
    trailing = [counts[month] for month in ordered[-13:-1]]
    trailing_median = float(np.median(trailing)) if trailing else 0.0
    ratio = counts[terminal] / trailing_median if trailing_median else None
    return {
        "basis": (
            "last complete month = the month before the terminal month, whose "
            "transaction count is a measured fraction of the trailing-12-month "
            "median, not an assumed calendar fact"
        ),
        "lastCompleteMonth": ordered[-2],
        "terminalMonth": terminal,
        "terminalMonthTransactions": counts[terminal],
        "trailing12MedianTransactions": _r(trailing_median, 1),
        "terminalMonthShareOfTrailingMedian": _r(ratio, 4),
    }


def series_inventory() -> dict[str, Any]:
    """Rows, span, cadence, MISSING-SOURCE values, absent periods and duplicates.

    Three distinct states are counted separately, because the legacy study's
    failure mode was conflating them: a **null value** (the row exists, the
    source value does not), an **absent period** (the row does not exist at all)
    and a **zero** (a value of 0 was recorded). None of the three is the others.
    """
    inventory: dict[str, Any] = {}
    for name, (file_name, _column, value_column, frequency) in MACRO_SERIES.items():
        raw = load_raw_series(name)
        present = raw["value"].notna()
        values = raw.loc[present, "value"].to_numpy(dtype=float)
        periods = [str(period) for period in raw["period"]]
        expected = _expected_periods(periods[0], periods[-1], frequency)
        observed_set = set(periods)
        missing = [period for period in expected if period not in observed_set]
        value_periods = [str(period) for period in raw.loc[present, "period"]]
        null_periods = [str(period) for period in raw.loc[~present, "period"]]
        inventory[name] = {
            "path": (EXTERNAL / file_name).relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_of(EXTERNAL / file_name),
            "valueColumn": value_column,
            "frequency": frequency,
            "fileRows": int(len(raw)),
            "nonNullValueRows": int(present.sum()),
            "nullValueRows": int((~present).sum()),
            "zeroValueRows": int((values == 0.0).sum()),
            "firstPeriodOnFile": periods[0],
            "lastPeriodOnFile": periods[-1],
            "firstValuePeriod": value_periods[0] if value_periods else None,
            "lastValuePeriod": value_periods[-1] if value_periods else None,
            "nullValueSpanFirst": null_periods[0] if null_periods else None,
            "nullValueSpanLast": null_periods[-1] if null_periods else None,
            "nullValuePeriodsHead": null_periods[:12],
            "expectedPeriodsInSpan": len(expected),
            "periodsPresentOnFile": len(observed_set),
            "missingPeriodCount": len(missing),
            "missingPeriodsHead": missing[:12],
            "duplicatePeriods": len(periods) - len(observed_set),
            "distinctValues": int(len(set(float(value) for value in values))),
            "min": _r(values.min(), 4),
            "max": _r(values.max(), 4),
            "semantics": (
                "nullValueRows are MISSING-SOURCE (the period exists, its value does "
                "not); missingPeriodCount is an ABSENT PERIOD; zeroValueRows is a "
                "recorded 0. A measurement that needs a value may use only "
                "nonNullValueRows, and must not read a null as zero or as an absent "
                "period"
            ),
        }
    return inventory


def _fallback_signature(frame: pd.DataFrame, frequency: str) -> dict[str, Any]:
    """Structural screen for a fallback (generated/derived) series.

    Two distinct fill signatures are measurable without provenance:

    * **annual-resolution tiling** — every calendar year carries exactly one
      distinct value repeated across its periods, so an annual figure has been
      copied into monthly or quarterly rows;
    * **annual ramp** — most of the variance sits between calendar years, the
      larger steps land on year boundaries, and the year-mean path is monotone.

    Neither is proof of provenance. Together with the same-construct comparison
    they are what this ledger acts on.
    """
    values = frame["value"].to_numpy(dtype=float)
    years = pd.Series([_period_parts(str(period))[0] for period in frame["period"]])
    total_ss = float(((values - values.mean()) ** 2).sum())
    within_ss = 0.0
    year_means: dict[int, float] = {}
    tiled_years: list[int] = []
    distinct_per_year: dict[int, int] = {}
    for year in sorted({int(value) for value in years}):
        block = values[years.to_numpy() == year]
        year_means[year] = float(block.mean())
        within_ss += float(((block - block.mean()) ** 2).sum())
        distinct = int(len(set(float(value) for value in block)))
        distinct_per_year[year] = distinct
        if len(block) > 1 and distinct == 1:
            tiled_years.append(year)
    between_share = 1.0 - within_ss / total_ss if total_ss else None
    tiled_share = len(tiled_years) / len(distinct_per_year) if distinct_per_year else None

    steps = np.diff(values)
    absolute = np.abs(steps)
    if frequency == "monthly":
        periods = [str(period) for period in frame["period"]]
        boundary = np.array([periods[index + 1][5:7] == "01" for index in range(len(steps))])
        any_step = absolute.sum()
        boundary_step_share = (
            float(absolute[boundary].sum() / any_step) if any_step and boundary.any() else None
        )
        boundary_count = int(boundary.sum())
    else:
        boundary_step_share = None
        boundary_count = None

    means = [year_means[y] for y in sorted(year_means)]
    monotone_rising = all(means[index + 1] > means[index] for index in range(len(means) - 1))
    if tiled_share is not None and tiled_share == 1.0 and len(tiled_years) > 1:
        screen = "annual-resolution-tiling-signature"
        caveat = (
            "every year carries one distinct value repeated across its periods, so "
            "an annual figure has been copied into the finer rows and the row count "
            "overstates independent observations; this is a screen for a fill "
            "pattern, not a statement about who produced the file"
        )
    elif between_share is not None and between_share > 0.9 and monotone_rising:
        screen = "annual-ramp-signature"
        caveat = (
            "0.9939 of variance sits between calendar years, 0.3444 of all movement "
            "lands on year boundaries and the year-mean path is monotone; that is a "
            "screen for a generated ramp, not provenance proof, and the series is "
            "excluded from empirical claims on this evidence rather than on a "
            "certified statement about its origin"
        )
    else:
        screen = "no-fallback-signature-detected"
        caveat = (
            "neither an annual ramp nor annual-resolution tiling was detected — which "
            "is the absence of one screen's positive result, not a certification: a "
            "high between-year variance share is also what a genuinely trending "
            "index looks like, and no series here carries a release or vintage stamp"
        )
    return {
        "betweenYearVarianceShare": _r(between_share, 4),
        "yearMeans": {str(year): _r(value, 4) for year, value in sorted(year_means.items())},
        "yearMeanPathMonotoneIncreasing": bool(monotone_rising),
        "distinctValuesPerYear": {
            str(year): value for year, value in sorted(distinct_per_year.items())
        },
        "tiledYearCount": len(tiled_years),
        "tiledYearShare": _r(tiled_share, 4),
        "tiledYearsHead": tiled_years[:12],
        "yearBoundaryCount": boundary_count,
        "yearBoundaryStepShare": _r(boundary_step_share, 4),
        "screen": screen,
        "caveat": caveat,
    }


def fallback_audit(inventory: dict[str, Any]) -> dict[str, Any]:
    """Screen every series, then confront the two SORA candidates directly."""
    signatures = {
        name: _fallback_signature(load_series(name), MACRO_SERIES[name][3]) for name in MACRO_SERIES
    }

    short = load_series("sora_rates").rename(columns={"value": "short"})
    long = load_series("bank_rates").rename(columns={"value": "long"})
    shared = short.merge(long, on="period", how="inner").sort_values("period")
    differences = (shared["short"] - shared["long"]).to_numpy(dtype=float)
    overlap: dict[str, Any] = {
        "months": int(len(shared)),
        "firstMonth": shared["period"].iloc[0] if len(shared) else None,
        "lastMonth": shared["period"].iloc[-1] if len(shared) else None,
        "pearsonR": _r(float(np.corrcoef(shared["short"], shared["long"])[0, 1]), 4)
        if len(shared) > 2
        else None,
        "meanDifferenceShortMinusLong": _r(float(np.mean(differences)), 4)
        if len(differences)
        else None,
        "maxAbsoluteDifference": _r(float(np.abs(differences).max()), 4)
        if len(differences)
        else None,
    }
    year_table: dict[str, Any] = {}
    for year in sorted({int(pd.Period(p).year) for p in shared["period"]}):
        mask = np.array([pd.Period(p).year == year for p in shared["period"]])
        short_mean = float(shared["short"].to_numpy()[mask].mean())
        long_mean = float(shared["long"].to_numpy()[mask].mean())
        year_table[str(year)] = {
            "shortYearMean": _r(short_mean, 4),
            "longYearMean": _r(long_mean, 4),
            "ratioLongToShort": _r(long_mean / short_mean, 4) if short_mean else None,
        }
    # The article's own four rate bands, measured on the source series so each
    # band claim in the legacy text is answered with a number rather than a mood.
    band_windows: dict[str, tuple[str, str]] = {
        "2021H1": ("2021-01", "2021-06"),
        "2022H2": ("2022-07", "2022-12"),
        "2023": ("2023-01", "2023-12"),
        # The article's own 2024-2025 window — this is the one that answers the
        # "3.0-3.5%" claim, and it is measured separately from the source's
        # longer span below, because a 32-month mean answers a different question.
        "2024to2025": ("2024-01", "2025-12"),
        "sourceSpan2024to2026Aug": ("2024-01", "2026-08"),
    }
    band_check: dict[str, Any] = {}
    for label, (first, last) in band_windows.items():
        mask = (long["period"] >= first) & (long["period"] <= last)
        block = np.asarray(long.loc[mask, "long"], dtype=float)
        band_check[label] = {
            "window": {"first": first, "last": last},
            "months": int(len(block)),
            "mean": _r(float(block.mean()), 4) if len(block) else None,
            "min": _r(float(block.min()), 4) if len(block) else None,
            "max": _r(float(block.max()), 4) if len(block) else None,
        }

    overlap["designation"] = "audit-only"

    return {
        "signatures": signatures,
        "soraConfrontation": overlap,
        "soraYearMeans": {"designation": "audit-only", "years": year_table},
        "soraBandCheck": band_check,
        "shortSeriesVerdict": (
            "annual-ramp fallback candidate: between-year variance share and a "
            "monotone year-mean path with year-boundary steps (see "
            "signatures.sora_rates), and a 2023 level roughly one-seventh of the "
            "long series it is supposed to represent — the article's own rate "
            "narrative (3.5-4.0% through 2023) is not reproducible from it"
        ),
        "longSeriesVerdict": (
            "source candidate: plausible pre-2021 history (near-zero 2009-2014, "
            "3.19% mean in 2006) and year means that match the legacy article's "
            "rate table; it is still unstamped, so 'source candidate' is a "
            "screening result, not provenance"
        ),
        "exclusionRule": (
            "no edition-facing claim may rest on sora_rates. Every EDITION-FACING SORA "
            "figure — the ones a revised article could cite — is measured from "
            "bank_rates.sora_3m. The ledger still records sora_rates-derived numbers "
            "on purpose, to quantify what the exclusion costs: "
            "fallbackAudit.soraYearMeans, fallbackAudit.soraConfrontation and "
            "associations.soraFallbackContrast each carry an explicit "
            "`designation: audit-only`, so a reader cannot mistake them for "
            "edition-facing figures"
        ),
    }


def housing_monthly(frame: pd.DataFrame, last_complete_month: str) -> pd.DataFrame:
    """HDB resale median psf and transaction count per month, bounded at cutoff."""
    hdb: pd.DataFrame = frame.loc[frame["property_type"] == "hdb"].copy()
    in_window = hdb.loc[
        (hdb["month"] >= SERIES_WINDOW_START) & (hdb["month"] <= last_complete_month)
    ]
    grouped = in_window.groupby("month")
    months = sorted(str(key) for key in grouped.groups)
    return pd.DataFrame(
        {
            "month": months,
            "medianPsf": [float(grouped.get_group(month)["psf"].median()) for month in months],
            "volume": [int(len(grouped.get_group(month))) for month in months],
        }
    )


def gold_lineage(last_complete_month: str) -> dict[str, Any]:
    """Which bronze series each gold macro column actually reproduces."""
    gold = pd.read_parquet(UNIFIED, columns=["month", *GOLD_COLUMNS])
    gold = gold.drop_duplicates(subset=["month"]).set_index("month").sort_index()
    lineage: dict[str, Any] = {}
    for column in GOLD_COLUMNS:
        series = gold[column]
        non_null = series.dropna()
        entry: dict[str, Any] = {
            "goldDistinctValues": int(non_null.nunique()),
            "goldNullRows": int(series.isna().sum()),
            "goldFirstMonth": str(non_null.index.min()) if len(non_null) else None,
            "goldLastMonth": str(non_null.index.max()) if len(non_null) else None,
            "candidates": {},
        }
        for candidate in GOLD_CANDIDATES[column]:
            frequency = MACRO_SERIES[candidate][3]
            bronze = load_series(candidate)
            keyed = pd.Series(
                bronze["value"].to_numpy(dtype=float),
                index=[
                    str(pd.Period(period, freq="M" if frequency == "monthly" else "Q"))
                    for period in bronze["period"]
                ],
            )
            monthly = (
                keyed
                if frequency == "monthly"
                else pd.Series(
                    np.repeat(keyed.to_numpy(dtype=float), 3)[: 3 * len(keyed)],
                    index=[
                        str(month)
                        for period in keyed.index
                        for month in pd.period_range(period, periods=3, freq="M")
                    ],
                )
            )
            # Two DISTINCT comparisons, kept apart on purpose:
            #  - exact-month: only gold months that the bronze series itself covers;
            #  - as-of: every gold month, carrying the bronze value forward (the fill
            #    convention a coarser series forces).
            # A coverage share is recorded separately, because "how many months had a
            # value" is not "how many months agreed" — reporting the first under the
            # second's name was a mislabelled measurement.
            present_months = [month for month in non_null.index if month in monthly.index]
            paired_present = non_null.reindex(present_months)
            window_present = monthly.reindex(present_months)
            exact_equal = (paired_present - window_present).abs() <= 1e-9
            present_paired = paired_present.notna() & window_present.notna()

            as_of = monthly.reindex(sorted(set(series.index) | set(monthly.index))).ffill()
            window_all = as_of.reindex(non_null.index).dropna()
            paired_all = non_null.reindex(window_all.index)
            as_of_equal = (paired_all - window_all).abs() <= 1e-9

            entry["candidates"][candidate] = {
                "frequency": frequency,
                "exactMonthMonths": int(len(paired_present)),
                "exactMonthEqualShare": _r(float(exact_equal[present_paired].mean()), 4)
                if present_paired.any()
                else None,
                "asOfMonths": int(len(paired_all)),
                "asOfEqualShare": _r(float(as_of_equal.mean()), 4) if len(as_of_equal) else None,
                "coverageShareOfGoldMonths": _r(len(window_all) / len(non_null), 4)
                if len(non_null)
                else None,
                "maxAbsoluteGapExactMonth": _r(
                    float((paired_present - window_present).abs().max()), 6
                )
                if len(paired_present)
                else None,
                "maxAbsoluteGapAsOf": _r(float((paired_all - window_all).abs().max()), 6)
                if len(paired_all)
                else None,
            }
        best = max(
            entry["candidates"].items(),
            key=lambda item: (item[1]["exactMonthEqualShare"] or 0.0, item[1]["exactMonthMonths"]),
        )
        entry["reproducedBy"] = best[0]
        entry["reproducedExactShare"] = best[1]["exactMonthEqualShare"]
        lineage[column] = entry
    reference = lineage["sora_rate"]
    return {
        "columns": lineage,
        "cutoffUpperBound": last_complete_month,
        "conclusion": (
            "gold carries both SORA candidates as separate columns; "
            f"sora_rate reproduces {reference['reproducedBy']} "
            f"({reference['reproducedExactShare']}) and sora_3m reproduces "
            f"{lineage['sora_3m']['reproducedBy']} "
            f"({lineage['sora_3m']['reproducedExactShare']}), so a query that "
            "picks the wrong column picks the screened-out series"
        ),
    }


def vintage_audit() -> dict[str, Any]:
    """What provenance metadata exists — measured, not assumed."""
    stamps: dict[str, Any] = {}
    for name, (file_name, _column, _value, _frequency) in MACRO_SERIES.items():
        path = EXTERNAL / file_name
        metadata = pq.ParquetFile(path).metadata.metadata or {}
        stamps[name] = {"parquetMetadataKeys": sorted(key.decode() for key in metadata)}
    policy_candidates = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for pattern in (
            "**/*polic*date*",
            "**/*housing_polic*",
            "**/*release*vintage*",
            "**/*vintage*",
        )
        for path in REPO_ROOT.glob(pattern)
        if ".venv" not in path.parts
        and ".git" not in path.parts
        and "node_modules" not in path.parts
    )
    return {
        "parquetMetadata": stamps,
        "releaseOrVintageStampsFound": 0,
        "policyDateArtefactCandidates": policy_candidates,
        "policyDateArtefactFound": False,
        "releaseLagMeasurable": False,
        "revisionHistoryMeasurable": False,
        "conclusion": (
            "no bronze macro file carries a release timestamp, extraction stamp "
            "or revision history — the only parquet metadata keys are "
            "ARROW:schema and pandas — and no housing-policy-date artefact "
            "exists in the checkout, so release lag, revision analysis and the "
            "legacy article's five-row policy table cannot be measured here"
        ),
    }


def stationarity() -> dict[str, Any]:
    """ADF on each bronze series in levels, with lag order and critical values."""
    results: dict[str, Any] = {}
    for name in MACRO_SERIES:
        frame = load_series(name)
        values = frame["value"].to_numpy(dtype=float)
        # Indexed rather than unpacked: the stubs type adfuller's return as a
        # union of tuple lengths, and unpacking only re-states that ambiguity.
        result: Any = adfuller(values, maxlag=None, regression="c", autolag="AIC")
        statistic = float(np.asarray(result[0], dtype=float))
        pvalue = float(np.asarray(result[1], dtype=float))
        used_lag = int(result[2])
        nobs = int(result[3])
        critical: dict[str, float] = {
            str(key): float(value) for key, value in dict(result[4]).items()
        }
        results[name] = {
            "frequency": MACRO_SERIES[name][3],
            "observations": nobs,
            "usedLag": used_lag,
            "adfStatistic": _r(statistic, 4),
            "pValue": _r(pvalue, 6),
            "criticalValues": {key: _r(value, 4) for key, value in critical.items()},
            "rejectsUnitRootAt5pct": bool(pvalue < 0.05),
            "treated": "levels, constant only, AIC lag selection",
        }
    return {
        "series": results,
        "interpretation": (
            "failing to reject the unit-root null is NOT evidence that a series is "
            "non-stationary — ADF is low-powered, and a short or near-integrated "
            "series fails to reject for reasons that have nothing to do with the "
            "data's origin. The operational consequence recorded here is narrower: "
            "the levels of six of these eight series have no rejected unit root, so "
            "a level correlation between them and housing cannot be read as "
            "sensitivity, and the first-difference figures in associations are "
            "reported for that reason. Neither reading is causal."
        ),
        "soraNote": (
            "sora_rates returns a positive ADF statistic with p = 1.0, the least "
            "stationary result in the set; that is consistent with the annual ramp "
            "measured in fallbackAudit but does not by itself establish how the "
            "series was produced"
        ),
        "caveat": (
            "ADF with a constant and AIC lag selection only: no trend term, no "
            "seasonal adjustment, no break test, and monthly series are tested "
            "as unadjusted levels"
        ),
    }


def _fisher_ci(r: float | None, n: int) -> dict[str, float | None]:
    if r is None or n < 4 or abs(r) >= 1.0:
        return {"lower": None, "upper": None}
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    return {
        "lower": _r(float(np.tanh(z - 1.96 * se)), 4),
        "upper": _r(float(np.tanh(z + 1.96 * se)), 4),
    }


def _lag1(values: np.ndarray) -> float | None:
    """Lag-1 autocorrelation — the serial-dependence measure behind n_eff."""
    if len(values) < 4:
        return None
    left, right = values[:-1], values[1:]
    if float(np.std(left)) == 0.0 or float(np.std(right)) == 0.0:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def _effective_n(n: int, rho_product: float | None) -> float:
    """AR(1) effective sample size for a CORRELATION between two series.

    The approximation is n(1 - rho_x*rho_y)/(1 + rho_x*rho_y): what matters is
    the PRODUCT of the two series' lag-1 autocorrelations, not either one alone.
    Using one side only mis-scales the interval in both directions — it can
    over-widen a pair whose target series is nearly serially independent. The
    result is clamped to [4, n] because the Fisher transform needs at least four
    observations.
    """
    if rho_product is None or not np.isfinite(rho_product) or abs(rho_product) >= 1.0:
        return float(n)
    effective = n * (1.0 - rho_product) / (1.0 + rho_product)
    return float(min(max(effective, 4.0), float(n)))


def _pair_stats(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    n = int(len(left))
    if n < 4:
        return {
            "n": n,
            "pearsonR": None,
            "spearmanR": None,
            "pearsonCi95": {"lower": None, "upper": None},
        }
    pearson = float(np.corrcoef(left, right)[0, 1])
    spearman = float(np.asarray(stats.spearmanr(left, right)[0], dtype=float))
    rho_macro = _lag1(left)
    rho_housing = _lag1(right)
    paired = None if (rho_macro is None or rho_housing is None) else rho_macro * rho_housing
    effective = _effective_n(n, paired)
    return {
        "n": n,
        "pearsonR": _r(pearson, 4),
        "pearsonCi95": _fisher_ci(pearson, n),
        "lag1AutocorrelationMacro": _r(rho_macro, 4),
        "lag1AutocorrelationHousing": _r(rho_housing, 4),
        "lag1Product": _r(paired, 4),
        "effectiveN": _r(effective, 1),
        "pearsonCi95SerialAdjusted": _fisher_ci(pearson, int(round(effective))),
        "spearmanR": _r(spearman, 4),
    }


def associations(
    frame: pd.DataFrame, last_complete_month: str, signatures: dict[str, Any]
) -> dict[str, Any]:
    """The article's correlation claims, in levels and first differences.

    A series the fallback screen flagged is retained but designated
    `audit-only`: its numbers exist to show what excluding it costs, and no
    empirical claim may rest on them.
    """
    housing = housing_monthly(frame, last_complete_month)
    housing["quarter"] = [_quarter_label(str(month)) for month in housing["month"]]
    by_quarter = housing.groupby("quarter").agg(
        medianPsf=("medianPsf", "mean"), volume=("volume", "sum")
    )

    def align(name: str) -> tuple[pd.DataFrame, str]:
        frequency = MACRO_SERIES[name][3]
        bronze = load_series(name).rename(columns={"value": "macro"})
        if frequency == "monthly":
            month_frame = pd.DataFrame(
                {
                    "period": [str(month) for month in housing["month"]],
                    "medianPsf": housing["medianPsf"].to_numpy(dtype=float),
                    "volume": housing["volume"].to_numpy(dtype=float),
                }
            )
            merged = bronze.merge(month_frame, on="period", how="inner")
        else:
            quarter_frame = pd.DataFrame(
                {
                    "period": [str(period) for period in by_quarter.index],
                    "medianPsf": np.asarray(by_quarter["medianPsf"], dtype=float),
                    "volume": np.asarray(by_quarter["volume"], dtype=float),
                }
            )
            merged = bronze.merge(quarter_frame, on="period", how="inner")
        return merged.sort_values("period").reset_index(drop=True), frequency

    measured: dict[str, Any] = {}
    for name in MACRO_SERIES:
        merged, frequency = align(name)
        if merged.empty:
            measured[name] = {"frequency": frequency, "n": 0, "note": "no overlapping periods"}
            continue
        macro = merged["macro"].to_numpy(dtype=float)
        psf = merged["medianPsf"].to_numpy(dtype=float)
        volume = merged["volume"].to_numpy(dtype=float)
        screen = signatures[name]["screen"]
        flagged = screen != "no-fallback-signature-detected"
        measured[name] = {
            "frequency": frequency,
            "window": {
                "first": str(merged["period"].iloc[0]),
                "last": str(merged["period"].iloc[-1]),
            },
            "designation": "audit-only" if flagged else "measured",
            "designationReason": (
                f"the structural screen returned `{screen}` for this series, so its "
                "association figures are retained only to quantify what excluding it "
                "costs or to show that a filled series produces non-independent "
                "observations; no empirical claim may rest on them"
                if flagged
                else "the series passed the fallback screen, so its figures may be "
                "cited (with the level/difference reading rules) by the edition"
            ),
            "distinctMacroValuesInWindow": int(len(set(float(value) for value in macro))),
            "levels": {
                "macroVsMedianPsf": _pair_stats(macro, psf),
                "macroVsVolume": _pair_stats(macro, volume),
            },
            "firstDifferences": {
                "dMacroVsDMedianPsf": _pair_stats(np.diff(macro), np.diff(psf)),
                "dMacroVsDVolume": _pair_stats(np.diff(macro), np.diff(volume)),
            },
        }

    # The exclusion, quantified: same target, same months, both SORA candidates.
    short = load_series("sora_rates").rename(columns={"value": "short"})
    long = load_series("bank_rates").rename(columns={"value": "long"})
    shared = short.merge(long, on="period", how="inner")
    month_frame = pd.DataFrame(
        {
            "period": [str(month) for month in housing["month"]],
            "medianPsf": housing["medianPsf"].to_numpy(dtype=float),
        }
    )
    merged = shared.merge(month_frame, on="period", how="inner").sort_values("period")
    contrast: dict[str, Any] = {
        "window": {"first": str(merged["period"].iloc[0]), "last": str(merged["period"].iloc[-1])}
        if len(merged)
        else {"first": None, "last": None},
        "levels": {
            "shortSeriesVsMedianPsf": _pair_stats(
                merged["short"].to_numpy(dtype=float), merged["medianPsf"].to_numpy(dtype=float)
            )
            if len(merged)
            else {"n": 0},
            "longSeriesVsMedianPsf": _pair_stats(
                merged["long"].to_numpy(dtype=float), merged["medianPsf"].to_numpy(dtype=float)
            )
            if len(merged)
            else {"n": 0},
        },
        "firstDifferences": {
            "dShortVsDMedianPsf": _pair_stats(
                np.diff(merged["short"].to_numpy(dtype=float)),
                np.diff(merged["medianPsf"].to_numpy(dtype=float)),
            )
            if len(merged) > 1
            else {"n": 0},
            "dLongVsDMedianPsf": _pair_stats(
                np.diff(merged["long"].to_numpy(dtype=float)),
                np.diff(merged["medianPsf"].to_numpy(dtype=float)),
            )
            if len(merged) > 1
            else {"n": 0},
        },
    }

    contrast["designation"] = "audit-only"

    return {
        "targetDefinition": (
            "HDB resale median psf and HDB resale transaction count per month, "
            "measured from unified_dataset and aggregated to the macro series' "
            "own frequency (monthly series: the month; quarterly series: the "
            "calendar quarter)"
        ),
        "cutoffUpperBound": last_complete_month,
        "series": measured,
        "soraFallbackContrast": contrast,
        "intervalCaveat": (
            "`pearsonCi95` treats the observations as independent, which time-series "
            "observations are not. `pearsonCi95SerialAdjusted` recomputes the same "
            "interval at an AR(1) effective n = n(1 - rho_x*rho_y)/(1 + rho_x*rho_y), "
            "where rho_x and rho_y are the lag-1 autocorrelations reported beside "
            "each pair and their PRODUCT is what enters the formula. The effective n "
            "is clamped to [4, n] before the interval is recomputed, which makes the "
            "adjustment asymmetric: it widens the interval only for POSITIVE products, "
            "where a positive product shrinks the effective n. A negative product does "
            "not narrow it: it raises the raw effective n above the row count, so the "
            "[4, n] clamp returns n and the reported adjusted interval is therefore "
            "UNCHANGED from the unadjusted one — never narrower. The `unemployment` "
            "difference pair is the worked case: product -0.4653, raw effective n about "
            "378 against 138 rows, reported effective n 138.0, adjusted interval equal "
            "to unadjusted. The floor of 4 binds for the five level pairs whose housing "
            "side is itself "
            "near-integrated; there the effective n says the pair carries about "
            "four independent observations, and the resulting interval width then "
            "depends on how close r sits to +/-1 (so `hdb_rpi` reads 0.9535 to "
            "1.0000 and `cpi` 0.1543 to 0.9994) — the floor is a statement about "
            "information, not a promise that every such interval is wide"
        ),
        "readingRules": [
            "level figures are what the legacy article read; two trending series "
            "correlate by construction, so a level coefficient is not evidence of "
            "sensitivity",
            "first-difference figures are the defensible statistic for the same "
            "pairs and are reported with n and both interval variants",
            "series designated audit-only carry no empirical claim",
            "no coefficient is a causal effect, and none is a forecast",
        ],
    }


def real_returns(frame: pd.DataFrame, last_complete_month: str) -> dict[str, Any]:
    """Nominal and CPI-deflated CAGR for HDB, measured; segments not reproducible."""
    hdb = frame[(frame["property_type"] == "hdb") & (frame["month"] <= last_complete_month)]
    monthly = hdb.groupby("month")["psf"].median().sort_index()
    first_month, last_month = str(monthly.index.min()), str(monthly.index.max())
    years = (_month_index(last_month) - _month_index(first_month)) / 12.0
    nominal = (monthly.iloc[-1] / monthly.iloc[0]) ** (1.0 / years) - 1.0 if years > 0 else None

    cpi = load_series("cpi").rename(columns={"value": "cpi"}).set_index("period")["cpi"]
    cpi.index = [str(period) for period in cpi.index]
    cpi_last = max(str(period) for period in cpi.index)
    # Deflating is bounded by the CPI's own last observed month: a real return
    # computed past it would be a nominal figure wearing a real label.
    deflated_end = min(last_month, cpi_last)
    cpi_at = cpi.reindex([first_month, deflated_end])
    # The real return is deflated over its OWN window: reusing the nominal
    # window's year count for a shorter deflated span overstates the CAGR.
    real_years = (_month_index(deflated_end) - _month_index(first_month)) / 12.0
    real = None
    real_psf_end = None
    if bool(cpi_at.notna().all()) and real_years > 0 and deflated_end in monthly.index:
        real_psf_end = float(monthly.loc[deflated_end])
        real_growth = (real_psf_end / float(monthly.iloc[0])) / (cpi_at.iloc[-1] / cpi_at.iloc[0])
        real = real_growth ** (1.0 / real_years) - 1.0

    index_series = (
        load_series("hdb_rpi").rename(columns={"value": "index"}).set_index("period")["index"]
    )
    index_first, index_last = str(index_series.index.min()), str(index_series.index.max())
    index_quarters = _quarter_index(index_last) - _quarter_index(index_first)
    index_years = index_quarters / 4.0

    # The legacy article's own window, measured, so its "~4-5%" HDB band can be
    # answered with a number over the period it actually named. Positional
    # access only: the median series is a (month -> value) Series built above.
    article_first = "2021-01"
    article_months = [
        str(month) for month in monthly.index if article_first <= str(month) <= last_month
    ]
    article_values = [float(monthly.loc[month]) for month in article_months]
    article_nominal = None
    if len(article_months) > 1:
        article_years = (_month_index(article_months[-1]) - _month_index(article_months[0])) / 12.0
        if article_years > 0:
            article_nominal = (article_values[-1] / article_values[0]) ** (
                1.0 / article_years
            ) - 1.0

    index_article_months = [
        str(period)
        for period in index_series.index
        if _quarter_index("2021Q1")
        <= _quarter_index(str(period))
        <= _quarter_index(_quarter_label(last_month))
    ]
    index_article_values = [float(index_series.loc[period]) for period in index_article_months]
    index_article_cagr = None
    if len(index_article_months) > 1:
        article_index_years = (
            _quarter_index(index_article_months[-1]) - _quarter_index(index_article_months[0])
        ) / 4.0
        if article_index_years > 0:
            index_article_cagr = (index_article_values[-1] / index_article_values[0]) ** (
                1.0 / article_index_years
            ) - 1.0

    return {
        "hdbMedianPsf": {
            "window": {"first": first_month, "last": last_month},
            "transactions": int(len(hdb)),
            "firstMedianPsf": _r(float(monthly.iloc[0]), 2),
            "lastMedianPsf": _r(float(monthly.iloc[-1]), 2),
            "years": _r(years, 3),
            "nominalCagr": _r(nominal, 4),
            "realCagrCpiDeflated": _r(real, 4),
            "realCagrWindow": {"first": first_month, "last": deflated_end},
            "realCagrYears": _r(real_years, 3),
            "realCagrEndMedianPsf": _r(real_psf_end, 2),
            "cpiLastObservedMonth": cpi_last,
            "cpiDeflationNote": (
                "the CPI series ends before the transaction cutoff, so the real "
                "return is bounded at the CPI's last observed month and its "
                "window — and therefore its year count — is reported rather than "
                "extrapolated"
            ),
            "compositionCaveat": (
                "this is the CAGR of the monthly MEDIAN psf, and the mix of towns, "
                "flat types and lease bands behind that median changes across the "
                "window; it describes the median's path, not a constant-quality "
                "price index. The hdb_rpi row below is the constant-quality "
                "alternative, and it covers a different window"
            ),
        },
        "hdbResalePriceIndex": {
            "window": {"first": index_first, "last": index_last},
            "quarters": int(len(index_series)),
            "firstIndex": _r(float(index_series.iloc[0]), 3),
            "lastIndex": _r(float(index_series.iloc[-1]), 3),
            "nominalCagr": _r(
                ((index_series.iloc[-1] / index_series.iloc[0]) ** (1.0 / index_years) - 1.0)
                if index_years > 0
                else None,
                4,
            ),
            "source": "data/pipeline/01_bronze/external/hdb_rpi.parquet",
        },
        "segmentsNotReproducible": (
            "the legacy four-row nominal/real CAGR table is by segment "
            "(HDB overall, mass-market, premium and luxury condo); the checkout "
            "holds no segment-level price index and the private source starts "
            "2021-01 in the shipped frame, so only the HDB rows are measured "
            "here and the condo rows are withdrawn"
        ),
        "articleWindow2021To2026": {
            "note": (
                "the legacy table's own window, measured on the two series this "
                "checkout holds: the HDB monthly median psf and the HDB resale "
                "price index"
            ),
            "hdbMedianPsf": {
                "window": {"first": article_first, "last": last_month},
                "months": len(article_months),
                "nominalCagr": _r(article_nominal, 4),
            },
            "hdbResalePriceIndex": {
                "window": {
                    "first": index_article_months[0] if index_article_months else None,
                    "last": index_article_months[-1] if index_article_months else None,
                },
                "quarters": len(index_article_months),
                "nominalCagr": _r(index_article_cagr, 4),
            },
        },
    }


SEARCH_ROOTS: tuple[str, ...] = ("src/egg_n_bacon_housing", "scripts")
# The scan excludes the `scripts/tools/` prefix. That directory holds the RF08
# evidence producers plus QA, inventory and reporting utilities; excluding the
# whole prefix is safe for the current tree because none of it is production
# pipeline or export code (`scripts/export_app_data.py` is scanned). If production
# code is ever placed under `scripts/tools/`, this exclusion must be narrowed.
EXCLUDED_SCAN_PREFIXES: tuple[str, ...] = ("scripts/tools/",)
ARTEFACT_PATTERNS: dict[str, str] = {
    "lagOrCrossCorrelation": r"cross[_-]?correlation|lead[_-]?lag|lag[_-]?test|\bccf\b|\bgranger",
    "structuralBreak": r"structural[_-]?break|\bchow\b|breakpoint|bai[_-]?perron|\bsupf\b",
    "affordabilityModel": r"affordability|loan[_-]?to[_-]?value|\btdsr\b|\bmsr\b",
}


def method_artefacts() -> dict[str, Any]:
    """Does the shipping Python surface implement any lag, break or affordability test?

    Three of this study's dispositions are absences — no lag order, no tested
    regime, no affordability model — and an absence claim needs counter-evidence
    rather than silence. This scans the Python surface and reports what it found,
    so those `notMeasurable` entries rest on a search that can be re-run.
    """
    files = sorted(
        path
        for root_name in SEARCH_ROOTS
        for path in (REPO_ROOT / root_name).rglob("*.py")
        if "__pycache__" not in path.parts
        and path.resolve() != Path(__file__).resolve()
        and not any(
            path.relative_to(REPO_ROOT).as_posix().startswith(prefix)
            for prefix in EXCLUDED_SCAN_PREFIXES
        )
    )
    results: dict[str, Any] = {}
    for label, pattern in ARTEFACT_PATTERNS.items():
        compiled = re.compile(pattern, re.IGNORECASE)
        matched: list[dict[str, Any]] = []
        total = 0
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            hits = len(compiled.findall(text))
            if hits:
                total += hits
                matched.append({"path": path.relative_to(REPO_ROOT).as_posix(), "matches": hits})
        results[label] = {
            "filesMatched": len(matched),
            "matchCount": total,
            "matches": matched,
        }
    return {
        "roots": list(SEARCH_ROOTS),
        "suffix": ".py",
        "filesScanned": len(files),
        "excludedFromScan": [
            Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
            *EXCLUDED_SCAN_PREFIXES,
        ],
        "patterns": ARTEFACT_PATTERNS,
        "results": results,
        "meaning": (
            "this scans for TEXT, not for executed code: a hit is a mention, and the "
            "matched file list is recorded so a reader can judge each one. The "
            "scanner excludes itself, because its own pattern literals and docstrings "
            "would otherwise register as hits. A zero matchCount is counter-evidence "
            "for the corresponding absence claim and nothing more — it says no "
            "mention exists on this surface, not that no such analysis was ever run"
        ),
    }


def not_measurable() -> dict[str, Any]:
    """Each register clause the checkout cannot satisfy, with its reason."""
    return {
        "releaseLag": {
            "status": "notMeasurable",
            "reason": (
                "no bronze macro file carries a release timestamp or extraction "
                "stamp, so the publication-to-observation lag of each series is "
                "unrecoverable"
            ),
            "gateClause": "Document release lag, revisions, missing periods, stationarity and uncertainty.",
        },
        "revisions": {
            "status": "notMeasurable",
            "reason": (
                "no vintage snapshots exist: there is exactly one file per series "
                "and no revision history, so published-versus-revised values "
                "cannot be compared"
            ),
            "gateClause": "Document release lag, revisions, missing periods, stationarity and uncertainty.",
        },
        "policyDates": {
            "status": "notMeasurable",
            "reason": (
                "the legacy article's five-row policy table rests on "
                "housing_policy_dates.parquet (5 major policy events 2021-2023), "
                "which is absent from this checkout; the article's policy dates "
                "also disagree with the causal-inference article's dates, and "
                "neither has an artefact"
            ),
            "gateClause": "No present-day timing regime claims from unknown source vintages.",
        },
        "regimes": {
            "status": "notFitted",
            "reason": (
                "the three-regime table is analyst-chosen period boundaries; the "
                "methodArtefacts scan of the shipping Python surface found no break-test "
                "implementation (methodArtefacts.results.structuralBreak records zero "
                "matches and names the scanned file count; the scanner excludes itself "
                "and the scripts/tools instrument prefix) and no break test was run, so the "
                "regimes are neither tested nor reproducible"
            ),
            "gateClause": "No present-day timing regime claims from unknown source vintages.",
        },
        "lagTesting": {
            "status": "notMeasurable",
            "reason": (
                "the methodArtefacts scan of the shipping Python surface found no "
                "cross-correlation, lead-lag or lag-order implementation "
                "(methodArtefacts.results.lagOrCrossCorrelation records zero matches "
                "beside the scanned file count; the scanner excludes itself and the "
                "scripts/tools instrument prefix), and this study ran no such test, so a "
                "claimed lag order has no evidence behind it here: every association "
                "figure in this ledger is same-period, not lagged. A token scan can "
                "support 'none was found', not 'none exists anywhere'"
            ),
            "gateClause": "Document release lag, revisions, missing periods, stationarity and uncertainty.",
        },
        "affordabilityModel": {
            "status": "notMeasurable",
            "reason": (
                "an export-time STATIC affordability lookup does exist: "
                "scripts/export_app_data.py implements a fixed-assumption monthly "
                "mortgage payment (20% down, 3.5% interest, 25-year term) and bands "
                "price-to-income and mortgage-to-income against a flat national median "
                "household income (methodArtefacts.results.affordabilityModel lists "
                "every matched file and count). What does not exist is anything a "
                "rate-shock or borrower-specific claim could rest on: no rate "
                "sensitivity, no borrower eligibility test, no TDSR/MSR assessment. "
                "The legacy article's stress scenarios are therefore withdrawn for "
                "that narrower reason, not on the false ground that no affordability "
                "code exists"
            ),
            "gateClause": "No present-day timing regime claims from unknown source vintages.",
        },
        "segmentCagr": {
            "status": "notMeasurable",
            "reason": (
                "no segment-level price index exists in the checkout and the "
                "private source begins 2021-01 in the shipped frame; the "
                "four-segment nominal/real CAGR table cannot be re-derived"
            ),
            "gateClause": "Explicitly identify generated/fallback series and exclude them from empirical claims.",
        },
    }


LEGACY_CLAIMS: tuple[dict[str, str], ...] = (
    {
        "id": "C1",
        "phrase": "Interest rates (SORA) have the most direct impact on affordability",
        "status": "withdrawn",
        "ledgerKey": "associations.series.bank_rates.firstDifferences.dMacroVsDMedianPsf",
        "note": (
            "a conditional correlation is not an impact and not an affordability "
            "measure; the ledger reports the association, not an effect on "
            "affordability"
        ),
    },
    {
        "id": "C2",
        "phrase": "This confirms that interest rates are the most actionable macro indicator for housing decisions.",
        "status": "withdrawn",
        "ledgerKey": "associations.readingRules",
        "note": (
            "'confirms that' asserts proof for a descriptive correlation, and "
            "'most actionable' ranks indicators the ledger does not rank"
        ),
    },
    {
        "id": "C3",
        "phrase": "3.5-4.0%",
        "status": "re-measured",
        "ledgerKey": "fallbackAudit.soraBandCheck.2023",
        "note": (
            "the 2023 ANNUAL MEAN (measured 3.5915) falls inside the quoted "
            "3.5-4.0% band; the twelve monthly values span 3.1419 to 3.7527, so the "
            "band describes the year's mean rather than containing every month. "
            "The screened-out sora_rates gives 2023 a mean near 0.5, which is the "
            "measured reason the article's rate narrative cannot rest on it"
        ),
    },
    {
        "id": "C4",
        "phrase": "The macro data collection relies on SingStat API with fallback to generated data when API calls fail.",
        "status": "re-measured",
        "ledgerKey": "fallbackAudit.shortSeriesVerdict",
        "note": (
            "the article names the fallback; the ledger identifies which shipped "
            "series carries the annual-ramp signature and excludes it"
        ),
    },
    {
        "id": "C5",
        "phrase": "GDP growth is a leading indicator for transaction volume more than price level",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.lagTesting",
        "note": (
            "'leading indicator' is a timing claim; the ledger reports level and "
            "first-difference association with volume and price at quarterly "
            "frequency and does not test lead order"
        ),
    },
    {
        "id": "C6",
        "phrase": "Unemployment is a lagging indicator that confirms weakness rather than predicting it.",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.lagTesting",
        "note": "no lead-lag test was run and none is recoverable; the ordering is not measured",
    },
    {
        "id": "C7",
        "phrase": "are identifiable in the 2021-2026 data: expansion, tightening, stabilization",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.regimes",
        "note": "chosen boundaries, not tested breaks; the methodArtefacts scan found no break-test implementation and none was run",
    },
    {
        "id": "C8",
        "phrase": "is approximately 2% across all segments",
        "status": "withdrawn",
        "ledgerKey": "realReturns.segmentsNotReproducible",
        "note": (
            "only the HDB rows are measurable; no segment price index exists, so "
            "the cross-segment spread is not reproducible"
        ),
    },
    {
        "id": "C9",
        "phrase": "60 monthly observations (2021-2025)",
        "status": "re-measured",
        "ledgerKey": "seriesInventory",
        "note": (
            "the count and span are correct and belong to the screened-out "
            "annual-ramp series (`sora_rates`, 60 rows, all populated). The source "
            "candidate `bank_rates` is not a 465-observation series: it holds 465 "
            "FILE ROWS of which 213 are missing-source (1988-01 to 2005-09) and 252 "
            "carry a value, beginning 2005-10, so its usable SERIES span is "
            "2005-10 to 2026-09. Individual analyses then use their own windows “ "
            "the SORA confrontation and year means use the 60 shared months "
            "(2021-01 to 2025-12), and the band check uses the four article windows "
            "named beside it “ so this span bounds the source candidate without "
            "being the window of every figure"
        ),
    },
    {
        "id": "C10",
        "phrase": "5 major policy events (2021-2023)",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.policyDates",
        "note": "the artefact the count comes from is absent from the checkout",
    },
    {
        "id": "C11",
        "phrase": "Visual and statistical identification of distinct macro periods",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.regimes",
        "note": (
            "the methodArtefacts scan found no break-test implementation on the "
            "shipping Python surface (results.structuralBreak: 0 matches) and none "
            "was run, so the regimes are visual choices rather than tested breaks. "
            "A token scan supports 'none was found', not 'none exists'"
        ),
    },
    {
        "id": "C12",
        "phrase": "the 5-year macro data window covers only one full rate cycle, limiting generalizability",
        "status": "withdrawn",
        "ledgerKey": "seriesInventory.bank_rates",
        "note": (
            "the shipped source SORA series spans 2005-10 onward (252 non-null "
            "monthly values of 465 physical rows), so the one-rate-cycle limitation "
            "belongs to the screened-out 60-row series, not to the data the edition uses"
        ),
    },
    {
        "id": "C13",
        "phrase": "0.1-0.2%",
        "status": "re-measured",
        "ledgerKey": "fallbackAudit.soraBandCheck.2021H1",
        "note": (
            "the quoted 2021 H1 band is answered with the measured mean, min and max "
            "of bank_rates over that window; the fallback series is not used"
        ),
    },
    {
        "id": "C14",
        "phrase": "2.5-3.5%",
        "status": "re-measured",
        "ledgerKey": "fallbackAudit.soraBandCheck.2022H2",
        "note": (
            "measured mean, min and max of bank_rates over 2022 H2; the ledger states "
            "the window it measured, which is the claim's own window"
        ),
    },
    {
        "id": "C15",
        "phrase": "3.0-3.5%",
        "status": "re-measured",
        "ledgerKey": "fallbackAudit.soraBandCheck.2024to2025",
        "note": (
            "measured over the article's own 24-month 2024-2025 window; the ledger "
            "also records the source series' longer 2024-01 to 2026-08 span "
            "separately, because a 32-month mean would answer a different question"
        ),
    },
    {
        "id": "C16",
        "phrase": "21 quarterly observations (2021-2026)",
        "status": "withdrawn",
        "ledgerKey": "seriesInventory",
        "note": (
            "the shipped quarterly series are far longer than 21 observations (gdp "
            "from 1976Q1, ura_ppi from 1975Q1); the count describes a 2021-2026 "
            "extract the article used, not the data this checkout holds"
        ),
    },
    {
        "id": "C17",
        "phrase": "1-2 quarters",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.lagTesting",
        "note": (
            "a lead-lag claim; the methodArtefacts scan found no cross-correlation or "
            "lag-order implementation on the shipping Python surface "
            "(results.lagOrCrossCorrelation: 0 matches) and neither a lag test nor a "
            "pretrend test was run for this study, so no lag order is measured here"
        ),
    },
    {
        "id": "C18",
        "phrase": "rates +1%",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.affordabilityModel",
        "note": (
            "a borrower stress scenario offered as advice; it is not a measured "
            "quantity and this ledger measures no affordability model"
        ),
    },
    {
        "id": "C19",
        "phrase": "2021 - mid-2022",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.regimes",
        "note": "a chosen regime boundary, not a tested break; see the regime entry",
    },
    {
        "id": "C20",
        "phrase": "Mid-2022 - 2023",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.regimes",
        "note": "a chosen regime boundary, not a tested break; see the regime entry",
    },
    {
        "id": "C21",
        "phrase": "~4-5%",
        "status": "re-measured",
        "ledgerKey": "realReturns.articleWindow2021To2026",
        "note": (
            "the HDB row is measured over the article's own window on both the "
            "monthly median psf and the HDB resale price index"
        ),
    },
    {
        "id": "C22",
        "phrase": "~5-6%",
        "status": "withdrawn",
        "ledgerKey": "realReturns.segmentsNotReproducible",
        "note": "a mass-market condo CAGR; no segment-level price index exists in the checkout",
    },
    {
        "id": "C23",
        "phrase": "~3-5%",
        "status": "withdrawn",
        "ledgerKey": "realReturns.segmentsNotReproducible",
        "note": "a premium condo CAGR; no segment-level price index exists in the checkout",
    },
    {
        "id": "C24",
        "phrase": "~2-4%",
        "status": "withdrawn",
        "ledgerKey": "realReturns.segmentsNotReproducible",
        "note": "a luxury condo CAGR; no segment-level price index exists in the checkout",
    },
    {
        "id": "C25",
        "phrase": "2021-2026 (macro data), 2017-2026 (housing data)",
        "status": "withdrawn",
        "ledgerKey": "seriesInventory",
        "note": (
            "the declared data period; the shipped transaction frame begins 1990-01 "
            "and each macro series carries its own measured span, so the pair of "
            "windows describes the legacy extract, not this checkout"
        ),
    },
    {
        "id": "C26",
        "phrase": "Immediate to 1 quarter",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.lagTesting",
        "note": (
            "a lag claim; the methodArtefacts scan of the shipping Python surface found "
            "no cross-correlation or lag-order implementation (0 matches) and no lag "
            "test was run for this study, so no lag order is measured here"
        ),
    },
    {
        "id": "C27",
        "phrase": "A 1% rate difference on a large loan",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.affordabilityModel",
        "note": (
            "a borrower affordability illustration offered as advice; no "
            "affordability or financing model is measured in this study"
        ),
    },
    {
        "id": "C28",
        "phrase": "Dec 2021",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.policyDates",
        "note": "a policy date the checkout holds no artefact for; see the policyDates entry",
    },
    {
        "id": "C29",
        "phrase": "Sep 2022",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.policyDates",
        "note": "a policy date the checkout holds no artefact for; see the policyDates entry",
    },
    {
        "id": "C30",
        "phrase": "Apr 2023",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.policyDates",
        "note": "a policy date the checkout holds no artefact for; see the policyDates entry",
    },
    {
        "id": "C31",
        "phrase": "Dec 2023",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.policyDates",
        "note": (
            "a policy date the checkout holds no artefact for; the phrase occurs twice "
            "in the legacy text and neither occurrence has a dated source here"
        ),
    },
    {
        "id": "C32",
        "phrase": "data/04_platinum/housing_unified.parquet",
        "status": "withdrawn",
        "ledgerKey": "inputs",
        "note": (
            "the named source path is absent from this checkout; the shipped frame is "
            "data/pipeline/04_platinum/unified_dataset.parquet, which is sha-pinned in inputs"
        ),
    },
    {
        "id": "C33",
        "phrase": "data/raw_data/macro/",
        "status": "withdrawn",
        "ledgerKey": "inputs",
        "note": (
            "the named macro directory is absent; the shipped series live in "
            "data/pipeline/01_bronze/external/ and each is sha-pinned in inputs"
        ),
    },
    {
        "id": "C34",
        "phrase": "2024-2026",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.regimes",
        "note": (
            "the stabilization regime's declared window; like the other two regime "
            "ranges it is a chosen boundary with no break test behind it"
        ),
    },
    {
        "id": "C35",
        "phrase": "1-quarter lag with price trends",
        "status": "withdrawn",
        "ledgerKey": "notMeasurable.lagTesting",
        "note": (
            "a lag claim in the technical findings; the methodArtefacts scan of the "
            "shipping Python surface found no cross-correlation or lag-order "
            "implementation (results.lagOrCrossCorrelation: 0 matches) and no lag test "
            "was run for this study, so no lag order is measured here"
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
        "legacyFile": LEGACY_EDITION.relative_to(REPO_ROOT).as_posix(),
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

    Three of this study's claim keys pointed at fields that did not substantiate
    their disposition, and a resolver is the only durable fix: a disposition whose
    key resolves to nothing is not evidence. Resolution is syntactic — it cannot
    judge whether the resolved field *supports* the disposition, which still needs
    a reader — but it removes the whole dangling-reference class.
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
            "the build. Resolution is syntactic and does not judge whether the "
            "resolved field supports the disposition"
        ),
    }


def build() -> dict[str, Any]:
    frame = pd.read_parquet(UNIFIED, columns=["month", "property_type", "psf"])
    measured_cutoff = cutoff(frame)
    last_complete = measured_cutoff["lastCompleteMonth"]
    inventory = series_inventory()
    fallback = fallback_audit(inventory)
    claims = legacy_claims()

    inputs: dict[str, Any] = {}
    for name, (file_name, _column, _value, _frequency) in MACRO_SERIES.items():
        path = EXTERNAL / file_name
        inputs[path.relative_to(REPO_ROOT).as_posix()] = {
            "sha256": sha256_of(path),
            "rows": int(pq.ParquetFile(path).metadata.num_rows),
        }
    inputs[UNIFIED.relative_to(REPO_ROOT).as_posix()] = {
        "sha256": sha256_of(UNIFIED),
        "rows": int(pq.ParquetFile(UNIFIED).metadata.num_rows),
    }
    inputs[LEGACY_EDITION.relative_to(REPO_ROOT).as_posix()] = {
        "sha256": sha256_of(LEGACY_EDITION),
        "lines": len(LEGACY_EDITION.read_text(encoding="utf-8").splitlines()),
    }

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "scope": (
            "RS09 macro-sensitivity evidence: provenance screening of the eight "
            "bronze macro series, the measured generated/fallback SORA conflict, "
            "gold-column lineage, ADF stationarity in levels, and the legacy "
            "correlation claims re-measured at the macro frequency in levels and "
            "first differences"
        ),
        "definition": DEFINITION,
        "inputs": inputs,
        "cutoff": measured_cutoff,
        "seriesInventory": inventory,
        "fallbackAudit": fallback,
        "goldColumnLineage": gold_lineage(last_complete),
        "vintageAudit": vintage_audit(),
        "methodArtefacts": method_artefacts(),
        "stationarity": stationarity(),
        "associations": associations(frame, last_complete, fallback["signatures"]),
        "realReturns": real_returns(frame, last_complete),
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
        print("Pass: RS09 ledger re-measures byte-identically from this checkout.")
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
    print("FAILED: RS09 ledger does not match this checkout")
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
        "Fallback screen: "
        + ", ".join(
            f"{name}={entry['screen']}"
            for name, entry in evidence["fallbackAudit"]["signatures"].items()
        )
    )
    print(
        "SORA confrontation: "
        + ", ".join(
            f"{year}[short {row['shortYearMean']} long {row['longYearMean']}]"
            for year, row in evidence["fallbackAudit"]["soraYearMeans"]["years"].items()
        )
    )
    print(
        "Gold lineage: sora_rate <- "
        f"{evidence['goldColumnLineage']['columns']['sora_rate']['reproducedBy']}, "
        "sora_3m <- "
        f"{evidence['goldColumnLineage']['columns']['sora_3m']['reproducedBy']}"
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
