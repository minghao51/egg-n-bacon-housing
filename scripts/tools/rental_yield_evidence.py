#!/usr/bin/env python3
"""Measure RS02's rental-yield evidence: definition, coverage and denominators.

RS02's gate is "gross proxy vs matched-unit yield defined; denominators and
zero/missing handling validated". This tool measures the two things that gate
needs from local data and nothing more:

1. **Join coverage** — for each month, how many `(town, flat_type)` groups have a
   sale median, a rent median, or both. The pipeline's inner join drops the
   unmatched groups, which is a population-defining cut and must be quantified.
2. **Block overlap** — whether a matched *block* proxy is even computable
   (rentals and sales both carry block/street). Unit-level matching is not
   possible: no source carries a unit identifier.

It also measures the published `rental_yield` output's distribution and sample
sizes, so the evidence pack can state the denominator behind every yield.

Usage:

    uv run python scripts/tools/rental_yield_evidence.py \
        --output docs/implementation/artifacts/rs02-rental-yield-evidence.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from egg_n_bacon_housing.utils.hdb_lookups import normalize_hdb_flat_type

REPO_ROOT = Path(__file__).resolve().parents[2]
SALES = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_hdb_resale.parquet"
RENTALS = REPO_ROOT / "data" / "pipeline" / "01_bronze" / "raw_hdb_rental.parquet"
YIELDS = REPO_ROOT / "data" / "pipeline" / "03_gold" / "rental_yield.parquet"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs02-rental-yield-evidence.json"
)

SCHEMA_VERSION = "1.0.0"
RECENT_MONTHS = 24
BLOCK_WINDOW_MONTHS = 12

# The pipeline normalises flat types before joining; the raw strings do not
# match each other (e.g. "3-ROOM" vs "3 ROOM"), so both rates are reported.
DEFINITION = (
    "Gross proxy (as implemented in feature_rental.py): per month and "
    "(town, flat_type), median_rent x 12 / median_sale_price x 100 over two "
    "independent transaction populations, then a sale-count-weighted mean "
    "across flat types for each (town, month). It is a mean of ratios, not a "
    "ratio of sums, and it is not a matched-unit yield."
)


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    """Uppercase and trim the join keys this frame actually carries."""
    frame = frame.copy()
    for column in ("town", "flat_type", "block", "street_name"):
        if column in frame.columns:
            frame[column] = frame[column].astype(str).str.upper().str.strip()
    return frame


def _quantiles(values: Any) -> dict[str, float | None]:
    clean = pd.Series(values).dropna().astype(float)
    if clean.empty:
        return {"min": None, "p10": None, "p50": None, "p90": None, "max": None}
    return {
        "min": float(clean.min()),
        "p10": float(clean.quantile(0.10)),
        "p50": float(clean.quantile(0.50)),
        "p90": float(clean.quantile(0.90)),
        "max": float(clean.max()),
    }


def join_coverage() -> dict[str, Any]:
    sales = _normalise(
        pd.read_parquet(SALES, columns=["month", "town", "flat_type", "resale_price"])
    )
    rents = _normalise(
        pd.read_parquet(
            RENTALS, columns=["rent_approval_date", "town", "flat_type", "monthly_rent"]
        )
    )
    rents["month"] = rents["rent_approval_date"].astype(str).str.slice(0, 7)

    # Source columns arrive as strings; a median over objects raises rather than
    # silently coercing, so convert explicitly and keep only positive prices —
    # the same rule `feature_rental.py` applies.
    sales["resale_price"] = pd.to_numeric(sales["resale_price"], errors="coerce")
    sales = pd.DataFrame(sales.loc[sales["resale_price"] > 0])
    rents["monthly_rent"] = pd.to_numeric(rents["monthly_rent"], errors="coerce")
    rents = pd.DataFrame(rents.loc[rents["monthly_rent"] > 0])

    def grouped(frame: pd.DataFrame, value: str) -> pd.DataFrame:
        result = frame.groupby(["month", "town", "flat_type"], as_index=False)[value].median()
        return pd.DataFrame(result)

    raw_sale_groups = grouped(sales, "resale_price")
    raw_rent_groups = grouped(rents, "monthly_rent")

    sales["flat_type"] = normalize_hdb_flat_type(pd.Series(sales["flat_type"]))
    rents["flat_type"] = normalize_hdb_flat_type(pd.Series(rents["flat_type"]))
    sale_groups = grouped(sales, "resale_price")
    rent_groups = grouped(rents, "monthly_rent")

    month_rows: list[dict[str, Any]] = []
    months = sorted(set(sale_groups["month"]) | set(rent_groups["month"]))
    for month in months:
        sales_at = sale_groups[sale_groups["month"] == month]
        rents_at = rent_groups[rent_groups["month"] == month]
        sale_keys = set(zip(sales_at["town"], sales_at["flat_type"], strict=True))
        rent_keys = set(zip(rents_at["town"], rents_at["flat_type"], strict=True))
        matched = sale_keys & rent_keys
        month_rows.append(
            {
                "month": str(month),
                "saleGroups": len(sale_keys),
                "rentGroups": len(rent_keys),
                "matchedGroups": len(matched),
                "matchedShareOfSaleGroups": (
                    round(len(matched) / len(sale_keys), 4) if sale_keys else None
                ),
            }
        )

    overlap = [row for row in month_rows if row["saleGroups"] and row["rentGroups"]]
    recent = overlap[-RECENT_MONTHS:]

    def share_summary(rows: list[dict[str, Any]]) -> dict[str, float | None]:
        shares = [row["matchedShareOfSaleGroups"] for row in rows]
        if not shares:
            return {"median": None, "min": None, "max": None}
        series = pd.Series(shares, dtype="float64")
        return {
            "median": round(float(series.median()), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
        }

    def raw_recent_share() -> dict[str, float | None]:
        """Matched share without the flat-type normaliser, for contrast."""
        shares: list[float] = []
        for month in [row["month"] for row in recent]:
            sales_at = raw_sale_groups[raw_sale_groups["month"] == month]
            rents_at = raw_rent_groups[raw_rent_groups["month"] == month]
            sale_keys = set(zip(sales_at["town"], sales_at["flat_type"], strict=True))
            rent_keys = set(zip(rents_at["town"], rents_at["flat_type"], strict=True))
            if sale_keys:
                shares.append(len(sale_keys & rent_keys) / len(sale_keys))
        if not shares:
            return {"median": None, "min": None, "max": None}
        series = pd.Series(shares)
        return {
            "median": round(float(series.median()), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
        }

    return {
        "flatTypeNormalisation": "normalize_hdb_flat_type (pipeline helper) applied to both sides",
        "recentMatchedShareRawFlatTypes": raw_recent_share(),
        "grain": "(town, flat_type, month)",
        "months": len(month_rows),
        "firstMonth": month_rows[0]["month"] if month_rows else None,
        "lastMonth": month_rows[-1]["month"] if month_rows else None,
        "recentWindowMonths": len(recent),
        "fullPeriodMonths": len(overlap),
        "fullPeriodMatchedShare": share_summary(overlap),
        "recentMatchedShare": {
            "median": (
                round(
                    float(pd.Series([row["matchedShareOfSaleGroups"] for row in recent]).median()),
                    4,
                )
                if recent
                else None
            ),
            "min": min((row["matchedShareOfSaleGroups"] for row in recent), default=None),
            "max": max((row["matchedShareOfSaleGroups"] for row in recent), default=None),
        },
        "monthsWithoutRentals": [row["month"] for row in month_rows if row["rentGroups"] == 0],
        "monthsWithoutSales": [row["month"] for row in month_rows if row["saleGroups"] == 0],
        "byMonth": month_rows[-RECENT_MONTHS:],
    }


def _block_key(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["town"].astype(str)
        + "|"
        + frame["block"].astype(str).str.upper().str.strip()
        + "|"
        + frame["street_name"].astype(str).str.upper().str.strip()
    )


def block_overlap() -> dict[str, Any]:
    sales = _normalise(pd.read_parquet(SALES, columns=["month", "town", "block", "street_name"]))
    rents = _normalise(
        pd.read_parquet(RENTALS, columns=["rent_approval_date", "town", "block", "street_name"])
    )
    rents["month"] = rents["rent_approval_date"].astype(str).str.slice(0, 7)
    months = sorted(set(sales["month"]) & set(rents["month"]))[-BLOCK_WINDOW_MONTHS:]
    window_sales = sales[sales["month"].isin(months)]
    window_rents = rents[rents["month"].isin(months)]
    sale_blocks = set(_block_key(pd.DataFrame(window_sales)))
    rent_blocks = set(_block_key(pd.DataFrame(window_rents)))
    return {
        "windowMonths": len(months),
        "firstMonth": months[0] if months else None,
        "lastMonth": months[-1] if months else None,
        "saleBlocks": len(sale_blocks),
        "rentBlocks": len(rent_blocks),
        "matchedBlocks": len(sale_blocks & rent_blocks),
        "matchedShareOfSaleBlocks": (
            round(len(sale_blocks & rent_blocks) / len(sale_blocks), 4) if sale_blocks else None
        ),
        "unitLevelMatching": "impossible: no source carries a unit identifier",
    }


def published_yields() -> dict[str, Any]:
    yields = pd.read_parquet(YIELDS)
    sample = pd.Series(pd.to_numeric(yields["sample_size"], errors="coerce"), dtype="float64")
    values = pd.Series(pd.to_numeric(yields["rental_yield_pct"], errors="coerce"), dtype="float64")
    deduped = yields.drop_duplicates(["town", "month"])
    duplicated = yields.duplicated(["town", "month"], keep=False)
    multiplicity = yields.groupby(["town", "month"]).size().value_counts().to_dict()
    # Which columns actually agree across a duplicated pair? Checking one column
    # is not enough: rental_index differs inside pairs whose yields agree.
    value_columns = [str(column) for column in yields.columns if column not in {"town", "month"}]
    distinct_per_pair = yields.groupby(["town", "month"])[value_columns].nunique().max()
    differing = [column for column in value_columns if int(distinct_per_pair[column]) > 1]
    deduped_values = pd.Series(
        pd.to_numeric(deduped["rental_yield_pct"], errors="coerce"), dtype="float64"
    )
    deduped_sample = pd.Series(
        pd.to_numeric(deduped["sample_size"], errors="coerce"), dtype="float64"
    )
    return {
        "rows": int(len(yields)),
        "uniqueTownMonths": int(len(deduped)),
        "duplicateRows": int(duplicated.sum()),
        "townMonthMultiplicity": {int(key): int(value) for key, value in multiplicity.items()},
        "duplicateRowsValueIdentical": len(differing) == 0,
        "duplicateColumnsDiffering": differing,
        "duplicateColumnsChecked": value_columns,
        "sampleSizeSumRaw": int(pd.Series(sample).fillna(0).sum()),
        "sampleSizeSumDeduped": int(
            pd.Series(pd.to_numeric(deduped["sample_size"], errors="coerce")).fillna(0).sum()
        ),
        "towns": int(yields["town"].nunique()),
        "grain": "town x month (flat_type aggregated, property_type HDB)",
        "coverage": {
            "firstMonth": str(pd.Series(yields["month"]).min()),
            "lastMonth": str(pd.Series(yields["month"]).max()),
        },
        "yieldPct": _quantiles(values),
        "yieldPctDeduped": _quantiles(deduped_values),
        "rowsBelow20SalesDeduped": int((deduped_sample < 20).sum()),
        "sampleSize": _quantiles(sample),
        "rowsBelow20Sales": int((sample < 20).sum()),
        "rowsAtOrBelowZero": int((values <= 0).sum()),
        "rowsNonFinite": int((~values.notna()).sum()),
        "implausibleAbove20Pct": int((values > 20).sum()),
        "rentalIndex": _index_coverage(yields),
    }


def _index_coverage(yields: pd.DataFrame) -> dict[str, Any]:
    """Coverage of the contextual rental-index column (one series, RS02 fix)."""
    if "rental_index" not in yields.columns:
        return {"present": False, "nonNull": 0, "firstMonth": None, "lastMonth": None}
    index = pd.to_numeric(yields["rental_index"], errors="coerce")
    populated = yields.loc[index.notna()]
    return {
        "present": True,
        "nonNull": int(index.notna().sum()),
        "rows": int(len(yields)),
        "firstMonth": str(populated["month"].min()) if not populated.empty else None,
        "lastMonth": str(populated["month"].max()) if not populated.empty else None,
    }


def macro_lag() -> dict[str, Any]:
    """The rental family's own lag relative to the sales cutoff."""
    sales = pd.read_parquet(SALES, columns=["month"])
    rents = pd.read_parquet(RENTALS, columns=["rent_approval_date"])
    return {
        "salesLastMonth": str(pd.Series(sales["month"]).max()),
        "rentalsLastMonth": str(
            pd.Series(rents["rent_approval_date"]).astype(str).str.slice(0, 7).max()
        ),
        "rentalIndexLastObservation": "2026-07 (raw_rental_index.parquet)",
    }


def build() -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "scope": "RS02 rental-yields evidence: definition, join coverage, denominators",
        "definition": DEFINITION,
        "joinCoverage": join_coverage(),
        "blockOverlap": block_overlap(),
        "publishedYields": published_yields(),
        "lag": macro_lag(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    evidence = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    coverage = evidence["joinCoverage"]
    print(
        f"Join coverage: {coverage['months']} months, recent matched share median "
        f"{coverage['recentMatchedShare']['median']}"
    )
    print(
        f"Block overlap: {evidence['blockOverlap']['matchedBlocks']} blocks in both "
        f"({evidence['blockOverlap']['matchedShareOfSaleBlocks']})"
    )
    print(f"Ledger: {args.output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
