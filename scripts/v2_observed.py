#!/usr/bin/env python3
"""Build the v2 observed-period release pack from platinum outputs.

The v1 release (`dashboard-release.json` + seven assets) keeps its exact names,
schema and period meanings. This script adds a **separate** immutable pack that
describes concrete periods and the observations behind them, so a reader can
tell which months, property type and population a number refers to.

Emitted layout (all written atomically, manifest last):

    <output-dir>/observed/<generation>/periods.json.gz
    <output-dir>/observed/<generation>/summary.json.gz
    <output-dir>/dashboard-release-v2.json      discovery manifest

Contract notes:

- Periods derive from the declared cutoff month, never from the wall clock.
- Aggregates are computed from transactions for the whole period. A period
  median is the median of the underlying transactions, never an average of
  monthly medians.
- A scope with no transactions is `no-sales` with null medians and a count of
  0; an unknown/absent input is `missing-source`. Null and zero stay distinct.
- Payload bytes never contain their own generation or path: the generation is
  derived from schema/method/input identities plus the role-keyed payload
  hashes, so verification cannot be circular.
- gzip output is deterministic (mtime 0), so identical inputs yield identical
  bytes.

Usage:

    uv run python scripts/v2_observed.py --last-complete-month 2026-10 \
        --output-dir /tmp/v2-pack --scope-status hdb=publish ec=limited
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATINUM = REPO_ROOT / "data" / "pipeline" / "04_platinum"
UNIFIED_NAME = "unified_dataset.parquet"

SCHEMA_VERSION = "2.1.0"
METHOD_VERSION = "observed-aggregates-2"
NATIONAL_ID = "SG"

PROPERTY_TYPES: tuple[str, ...] = ("all", "hdb", "ec", "condo")
METRICS: tuple[str, ...] = ("transactionCount", "medianPrice", "medianPsf")

# RF09: per-property monthly history payloads, one asset per property type.
MONTHLY_ROLE_PREFIX = "area-monthly"

# Transactions the pipeline could not assign to a planning area. They are real
# rows, so they stay in the national scope and get their own series, but they
# are not an area: a consumer that enumerates areas must exclude them. The
# payload declares them instead of leaving a reader to infer it from the id.
UNASSIGNED_GEOGRAPHY_IDS: tuple[str, ...] = ("NONE", "NAN", "NULL", "UNKNOWN")

# Positional meaning of one monthly cell. The arrays are aligned to the
# payload's `months` grid so the history stays compact; the field names are
# declared in the payload rather than implied by the reader.
CELL_FIELDS: tuple[str, ...] = (
    "transactionCount",
    "medianPrice",
    "priceObservations",
    "medianPsf",
    "psfObservations",
)

MONTHLY_COVERAGE_RULE = (
    "A month listed in `months` is covered by the release; a covered month with "
    "zero transactions is a verified no-sales month, not missing data. A month "
    "absent from `months` is not covered by the release and stays missing-source."
)

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Dashboard property-type id -> value in the `property_label` column.
PROPERTY_LABELS: dict[str, str] = {
    "hdb": "HDB",
    "ec": "EC",
    "condo": "Condominium",
}

# Disposition vocabulary shared with the parent plan (D11).
VALID_DISPOSITIONS = ("publish", "limited-display", "withhold")

# A scope may only be published when every property type inside it is cleared.
_DISPOSITION_STRENGTH = {"publish": 0, "limited-display": 1, "withhold": 2}
DEFAULT_DISPOSITION = "limited-display"


class ContractError(ValueError):
    """Raised when a period or payload would violate the release contract."""


# --------------------------------------------------------------------------- #
# Periods
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PeriodDescriptor:
    """One concrete observation window."""

    id: str
    kind: str
    start_month: str
    end_month: str
    label: str
    comparator_id: str | None
    months: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "startMonth": self.start_month,
            "endMonth": self.end_month,
            "months": list(self.months),
            "label": self.label,
            "comparatorId": self.comparator_id,
        }


def _month_index(month: str) -> int:
    """Convert 'YYYY-MM' to a comparable integer."""
    if not isinstance(month, str) or not MONTH_PATTERN.match(month):
        raise ContractError(f"Invalid month {month!r}; expected YYYY-MM")
    year, mon = month.split("-")
    return int(year) * 12 + int(mon) - 1


def shift_month(month: str, delta: int) -> str:
    """Shift a YYYY-MM string by `delta` months, crossing years correctly."""
    total = _month_index(month) + delta
    year, mon = divmod(total, 12)
    return f"{year:04d}-{mon + 1:02d}"


def month_range(start_month: str, end_month: str) -> list[str]:
    """Inclusive list of months; raises when the bounds are reversed."""
    start = _month_index(start_month)
    end = _month_index(end_month)
    if end < start:
        raise ContractError(f"Reversed period bounds: {start_month} → {end_month}")
    return [shift_month(start_month, offset) for offset in range(end - start + 1)]


def _year_of(month: str) -> int:
    return int(month[:4])


def monthly_role(property_type: str) -> str:
    """Manifest role of the monthly history payload for one property type."""
    if property_type not in PROPERTY_TYPES:
        raise ContractError(f"Unknown property type {property_type!r}")
    return f"{MONTHLY_ROLE_PREFIX}-{property_type}"


def _period_for(kind: str, end_month: str) -> PeriodDescriptor:
    """Build one concrete period of `kind` ending at `end_month`."""
    _month_index(end_month)  # validate before any string slicing
    slug = end_month.replace("-", "_")
    if kind == "month":
        return PeriodDescriptor(
            id=f"month_{slug}",
            kind="month",
            start_month=end_month,
            end_month=end_month,
            label=f"{end_month} (one month)",
            comparator_id=f"month_{shift_month(end_month, -12).replace('-', '_')}",
            months=tuple(month_range(end_month, end_month)),
        )
    if kind == "ytd":
        start = f"{end_month[:4]}-01"
        return PeriodDescriptor(
            id=f"ytd_{slug}",
            kind="ytd",
            start_month=start,
            end_month=end_month,
            label=f"{end_month[:4]} January to {end_month} (partial year)",
            comparator_id=f"ytd_{shift_month(end_month, -12).replace('-', '_')}",
            months=tuple(month_range(start, end_month)),
        )
    if kind == "ttm":
        start = shift_month(end_month, -11)
        return PeriodDescriptor(
            id=f"ttm_{slug}",
            kind="ttm",
            start_month=start,
            end_month=end_month,
            label=f"12 months to {end_month}",
            comparator_id=f"ttm_{shift_month(end_month, -12).replace('-', '_')}",
            months=tuple(month_range(start, end_month)),
        )
    if kind == "rolling3":
        start = shift_month(end_month, -2)
        return PeriodDescriptor(
            id=f"rolling3_{slug}",
            kind="rolling3",
            start_month=start,
            end_month=end_month,
            label=f"3 months to {end_month}",
            comparator_id=f"rolling3_{shift_month(end_month, -12).replace('-', '_')}",
            months=tuple(month_range(start, end_month)),
        )
    if kind == "year":
        start = f"{end_month[:4]}-01"
        end = f"{end_month[:4]}-12"
        return PeriodDescriptor(
            id=f"year_{end_month[:4]}",
            kind="year",
            start_month=start,
            end_month=end,
            label=f"calendar year {end_month[:4]}",
            comparator_id=f"year_{int(end_month[:4]) - 1}",
            months=tuple(month_range(start, end)),
        )
    raise ContractError(f"Unknown period kind {kind!r}")


def build_periods(
    cutoff_month: str,
    *,
    completed_years: tuple[int, ...] | None = None,
    trailing_years: int = 1,
    covered_months: set[str] | None = None,
) -> list[PeriodDescriptor]:
    """Build the concrete period set for one declared cutoff.

    `completed_years` defaults to every year strictly before the cutoff year;
    the last `trailing_years` completed years are described individually.
    """
    _month_index(cutoff_month)  # validate
    cutoff_year = _year_of(cutoff_month)

    years: tuple[int, ...]
    if completed_years is None:
        candidates = list(range(cutoff_year - trailing_years, cutoff_year))
        # A December cutoff closes that calendar year; a partial December is
        # the caller's problem, not a reason to withhold a completed year.
        if cutoff_month.endswith("-12"):
            candidates.append(cutoff_year)
        years = tuple(sorted(set(candidates)))
    else:
        years = completed_years

    periods: list[PeriodDescriptor] = [
        _period_for("month", cutoff_month),
        _period_for("rolling3", cutoff_month),
        _period_for("ytd", cutoff_month),
        _period_for("ttm", cutoff_month),
    ]
    periods.extend(_period_for("year", f"{year:04d}-12") for year in sorted(years))

    # Comparators are observation windows in their own right. Publish one only
    # when every month it needs is covered, so a comparison is never computed
    # from a partially published window.
    if covered_months is not None:
        for base in list(periods):
            comparator = base.comparator_id
            if comparator is None:
                continue
            kind = comparator.split("_", 1)[0]
            end_month = comparator.split("_", 1)[1].replace("_", "-")
            if kind == "year" and comparator.startswith("year_"):
                end_month = f"{comparator.split('_', 1)[1]}-12"
            candidate = _period_for(kind, end_month)
            if candidate.id in {period.id for period in periods}:
                continue
            if all(month in covered_months for month in candidate.months):
                periods.append(candidate)

    _validate_periods(periods)
    return periods


def _validate_periods(periods: list[PeriodDescriptor]) -> None:
    seen: set[str] = set()
    for period in periods:
        if period.id in seen:
            raise ContractError(f"Duplicate period id {period.id}")
        seen.add(period.id)
        month_range(period.start_month, period.end_month)


def period_ids(periods: list[PeriodDescriptor]) -> set[str]:
    return {period.id for period in periods}


def resolve_comparator(period: PeriodDescriptor, available: set[str]) -> str | None:
    """Return the comparator id when it is part of the published set."""
    comparator = period.comparator_id
    return comparator if comparator in available else None


def cutoff_from_last_complete_month(
    declared: str | None, *, today: date | None = None
) -> tuple[str, str]:
    """Resolve the cutoff, recording how it was decided.

    Returns `(cutoff_month, source)` where source is `declared` or
    `utc-clock`. An omitted boundary is recorded honestly rather than being
    silently treated as declared.
    """
    if declared is not None:
        _month_index(declared)
        return declared, "declared"

    today = today or date.today()
    month = f"{today.year:04d}-{today.month:02d}"
    return shift_month(month, -1), "utc-clock"


# --------------------------------------------------------------------------- #
# Aggregates
# --------------------------------------------------------------------------- #


def property_label_frame(df: pd.DataFrame) -> pd.Series:
    """Map the pipeline's property columns onto the dashboard vocabulary."""
    prop_lower = df["property_type"].astype(str).str.lower()
    is_ec = df["is_ec"].astype("boolean").fillna(False).astype(bool)
    return pd.Series(
        np.select(
            condlist=[
                is_ec,
                prop_lower.isin({"hdb", "hdb flat"}),
                prop_lower.isin({"executive condominium", "ec"}),
            ],
            choicelist=["EC", "HDB", "EC"],
            default="Condominium",
        ),
        index=df.index,
    )


def _median_or_none(values: pd.Series) -> float | None:
    if len(values) == 0:
        return None
    try:
        median = float(values.median())
    except (TypeError, ValueError):
        return None
    return median if math.isfinite(median) else None


def _observation(
    subset: pd.DataFrame,
    *,
    geography_id: str,
    property_type: str,
    period: PeriodDescriptor,
    disposition: str,
    months_covered: list[str],
) -> dict[str, object]:
    prices = pd.Series(subset["price"]).dropna()
    psf = pd.Series(subset["psf"]).dropna()
    psf = pd.Series(psf[psf > 0])

    count = int(len(subset))
    status = "available" if count > 0 else "no-sales"

    return {
        "geographyId": geography_id,
        "propertyType": property_type,
        "periodId": period.id,
        "status": status,
        "disposition": disposition,
        "coverage": {
            "months": months_covered,
            "requestedMonths": len(period.months),
        },
        "metrics": {
            "transactionCount": {
                "value": count,
                "unit": "transactions",
                "observations": count,
            },
            "medianPrice": {
                "value": _median_or_none(prices),
                "unit": "SGD",
                "observations": int(len(prices)),
            },
            "medianPsf": {
                "value": _median_or_none(psf),
                "unit": "SGD_per_sqft",
                "observations": int(len(psf)),
            },
        },
    }


def _resolve_dispositions(given: Mapping[str, str]) -> dict[str, str]:
    """Fill in every property type, defaulting to the cautious disposition.

    `all` combines every constituent, so it is only as publishable as its
    weakest member; a caller cannot publish the combined scope while a
    constituent is limited or withheld.
    """
    for value in given.values():
        if value not in VALID_DISPOSITIONS:
            raise ContractError(f"Unknown disposition {value!r}; expected {VALID_DISPOSITIONS}")
    resolved = {
        property_type: given.get(property_type, DEFAULT_DISPOSITION)
        for property_type in PROPERTY_TYPES
        if property_type != "all"
    }
    if "all" in given:
        resolved["all"] = given["all"]
    else:
        resolved["all"] = max(
            (resolved[property_type] for property_type in resolved),
            key=lambda value: _DISPOSITION_STRENGTH[value],
        )
    return {property_type: resolved[property_type] for property_type in PROPERTY_TYPES}


def _select_period_rows(
    frame: pd.DataFrame, period: PeriodDescriptor, covered_months: set[str]
) -> tuple[pd.DataFrame, list[str]]:
    wanted = [month for month in period.months if month in covered_months]
    if not wanted:
        return frame.iloc[0:0], []
    selected = frame.loc[frame["month"].isin(wanted)]
    assert isinstance(selected, pd.DataFrame)
    return selected, wanted


def build_observations(
    frame: pd.DataFrame,
    periods: list[PeriodDescriptor],
    *,
    category_column: str = "planning_area",
    dispositions: Mapping[str, str] | None = None,
    include_areas: bool = True,
    covered_months: set[str] | None = None,
) -> tuple[list[dict[str, object]], list[str]]:
    """Build observations for the national scope and every area.

    `frame` needs `month` (YYYY-MM), `property_label`, `price`, `psf` and the
    category column. Returns `(observations, months_present)`.
    """
    given = dict(dispositions or {})
    for value in given.values():
        if value not in VALID_DISPOSITIONS:
            raise ContractError(f"Unknown disposition {value!r}; expected {VALID_DISPOSITIONS}")
    dispositions = _resolve_dispositions(given)

    present = (
        covered_months if covered_months is not None else set(frame["month"].dropna().unique())
    )

    areas = sorted(
        str(value) for value in frame[category_column].dropna().unique() if str(value).strip() != ""
    )
    geographies: list[tuple[str, pd.DataFrame | None]] = [(NATIONAL_ID, None)]
    if include_areas:
        geographies.extend((area, None) for area in areas)

    observations: list[dict[str, object]] = []
    for period in periods:
        period_rows, covered = _select_period_rows(frame, period, present)
        for geography_id in [geo for geo, _ in geographies]:
            if geography_id == NATIONAL_ID:
                scope_rows = period_rows
            else:
                scope_rows = period_rows.loc[
                    period_rows[category_column].astype(str) == geography_id
                ]
                assert isinstance(scope_rows, pd.DataFrame)
            for property_type in PROPERTY_TYPES:
                if property_type == "all":
                    subset = scope_rows
                else:
                    label = PROPERTY_LABELS[property_type]
                    labels = scope_rows["property_label"].astype(str)
                    subset = scope_rows.loc[labels == label]
                    assert isinstance(subset, pd.DataFrame)
                observations.append(
                    _observation(
                        subset,
                        geography_id=geography_id,
                        property_type=property_type,
                        period=period,
                        disposition=dispositions[property_type],
                        months_covered=covered,
                    )
                )

    return observations, sorted(present)


def build_monthly_history(
    frame: pd.DataFrame,
    *,
    cutoff_month: str,
    category_column: str = "planning_area",
    dispositions: Mapping[str, str] | None = None,
    include_areas: bool = True,
    property_types: tuple[str, ...] = PROPERTY_TYPES,
) -> dict[str, dict[str, object]]:
    """Build one `(area, property type, calendar month)` history payload per type.

    Grain is the month cell, and coverage is declared per property type: the
    `months` grid is every month in which that property type appears in the
    bounded input, so private types do not inherit HDB's 1990 start. A month
    inside the grid with no area rows is a covered no-sales month; a month
    outside it is missing source. Cells are positional arrays (`cellFields`)
    aligned to `months` to keep the assets small enough to lazy-load.
    """
    given = dict(dispositions or {})
    resolved = _resolve_dispositions(given)

    area_ids: list[str] = []
    unassigned_ids: list[str] = []
    if include_areas and category_column in frame.columns:
        present_ids = {str(value).strip() for value in frame[category_column].dropna().unique()}
        unassigned_ids = sorted(
            value
            for value in present_ids
            if value == "" or value.upper() in UNASSIGNED_GEOGRAPHY_IDS
        )
        area_ids = sorted(value for value in present_ids if value and value not in unassigned_ids)

    payloads: dict[str, dict[str, object]] = {}
    for property_type in property_types:
        if property_type == "all":
            subset = frame
        else:
            labels = frame["property_label"].astype(str)
            subset = frame.loc[labels == PROPERTY_LABELS[property_type]]
        assert isinstance(subset, pd.DataFrame)

        months = sorted(str(month) for month in subset["month"].dropna().unique())
        positions = {month: index for index, month in enumerate(months)}

        series: list[dict[str, object]] = []
        for geography_id in [NATIONAL_ID, *unassigned_ids, *area_ids]:
            if geography_id == NATIONAL_ID:
                scope = subset
            else:
                scope = subset.loc[subset[category_column].astype(str) == geography_id]
            assert isinstance(scope, pd.DataFrame)

            cells: list[list[object]] = [[0, None, 0, None, 0] for _ in months]
            if months:
                for month, block in scope.groupby("month", sort=False):
                    index = positions.get(str(month))
                    if index is None:
                        continue
                    prices = pd.Series(block["price"]).dropna()
                    psf = pd.Series(block["psf"]).dropna()
                    psf = pd.Series(psf[psf > 0])
                    cells[index] = [
                        int(len(block)),
                        _median_or_none(prices),
                        int(len(prices)),
                        _median_or_none(psf),
                        int(len(psf)),
                    ]

            series.append(
                {
                    "geographyId": geography_id,
                    "noSalesMonths": sum(1 for cell in cells if cell[0] == 0),
                    "cells": cells,
                }
            )

        payloads[monthly_role(property_type)] = {
            "schemaVersion": SCHEMA_VERSION,
            "methodVersion": METHOD_VERSION,
            "cutoffMonth": cutoff_month,
            "propertyType": property_type,
            "disposition": resolved[property_type],
            "cellFields": list(CELL_FIELDS),
            "geographies": {
                "national": NATIONAL_ID,
                "unassigned": unassigned_ids,
                "areaCount": len(area_ids),
            },
            "months": months,
            "coverage": {
                "firstMonth": months[0] if months else None,
                "lastMonth": months[-1] if months else None,
                "monthCount": len(months),
                "rule": MONTHLY_COVERAGE_RULE,
            },
            "series": series,
        }

    return payloads


# --------------------------------------------------------------------------- #
# Serialization and identity
# --------------------------------------------------------------------------- #


def sanitize(value: object) -> object:
    """Recursively normalise to JSON-safe Python types.

    Mirrors the v1 exporter's sanitizer: NaN/Inf become null, numpy scalars
    become Python scalars, and booleans stay booleans (never integers).
    """
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, (np.ndarray,)):
        return [sanitize(item) for item in value.tolist()]
    return value


def canonical_json_bytes(payload: object) -> bytes:
    """Canonical UTF-8 JSON used for hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def deterministic_gzip(payload: bytes) -> bytes:
    """gzip with a fixed mtime so identical payloads give identical bytes."""
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=9, mtime=0) as handle:
        handle.write(payload)
    return buffer.getvalue()


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def compute_generation(
    *,
    schema_version: str,
    method_version: str,
    cutoff_month: str,
    inputs: dict[str, str],
    role_hashes: dict[str, str],
) -> str:
    """Derive the pack identity from inputs plus payload hashes.

    Payloads must not embed the generation, so this is never circular.
    """
    identity = {
        "schemaVersion": schema_version,
        "methodVersion": method_version,
        "cutoffMonth": cutoff_month,
        "inputs": dict(sorted(inputs.items())),
        "roles": dict(sorted(role_hashes.items())),
    }
    return sha256_hex(canonical_json_bytes(identity))


# --------------------------------------------------------------------------- #
# Pack emission
# --------------------------------------------------------------------------- #


@dataclass
class PackResult:
    output_dir: Path
    generation: str
    manifest_path: Path
    roles: dict[str, dict[str, object]]


def emit_pack(
    *,
    output_dir: Path,
    summary: Mapping[str, object],
    periods_payload: Mapping[str, object],
    cutoff_month: str,
    cutoff_source: str,
    inputs: dict[str, str],
    scope_status: Mapping[str, object] | None = None,
    monthly_payloads: Mapping[str, Mapping[str, object]] | None = None,
) -> PackResult:
    """Write the immutable pack, then the discovery manifest last.

    RF09 requires one complete pack: the period descriptors, the period
    summary and every declared monthly history payload share one generation.
    """
    payload_bytes: dict[str, bytes] = {
        "periods": deterministic_gzip(canonical_json_bytes(sanitize(dict(periods_payload)))),
        "summary": deterministic_gzip(canonical_json_bytes(sanitize(dict(summary)))),
    }
    for role in sorted(monthly_payloads or {}):
        payload_bytes[role] = deterministic_gzip(
            canonical_json_bytes(sanitize(dict((monthly_payloads or {})[role])))
        )

    role_hashes = {role: sha256_hex(payload) for role, payload in payload_bytes.items()}
    generation = compute_generation(
        schema_version=SCHEMA_VERSION,
        method_version=METHOD_VERSION,
        cutoff_month=cutoff_month,
        inputs=inputs,
        role_hashes=role_hashes,
    )

    pack_dir = output_dir / "observed" / generation
    pack_dir.mkdir(parents=True, exist_ok=True)

    ordered_roles = [
        "periods",
        "summary",
        *sorted(role for role in payload_bytes if role not in {"periods", "summary"}),
    ]
    roles: dict[str, dict[str, object]] = {}
    for role in ordered_roles:
        payload = payload_bytes[role]
        relative = f"observed/{generation}/{role}.json.gz"
        target = output_dir / relative
        _atomic_write(target, payload)
        roles[role] = {
            "role": role,
            "path": relative,
            "bytes": len(payload),
            "sha256": role_hashes[role],
        }

    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "methodVersion": METHOD_VERSION,
        "generation": generation,
        "cutoffMonth": cutoff_month,
        "cutoffSource": cutoff_source,
        "identity": {
            "schemaVersion": SCHEMA_VERSION,
            "methodVersion": METHOD_VERSION,
            "cutoffMonth": cutoff_month,
            "inputs": dict(sorted(inputs.items())),
            "roles": dict(sorted(role_hashes.items())),
        },
        "assets": [roles[role] for role in ordered_roles],
        "scopeStatus": scope_status or {},
        "generatedAt": None,
    }

    manifest_path = output_dir / "dashboard-release-v2.json"
    _atomic_write(manifest_path, canonical_json_bytes(manifest) + b"\n")

    return PackResult(
        output_dir=output_dir,
        generation=generation,
        manifest_path=manifest_path,
        roles=roles,
    )


def _atomic_write(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, target)


def verify_pack(manifest_path: Path) -> list[str]:
    """Re-verify a written pack; returns a list of problems (empty = pass)."""
    problems: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"unreadable manifest: {exc}"]

    identity = manifest.get("identity") or {}
    declared = manifest.get("generation")
    recomputed = compute_generation(
        schema_version=str(identity.get("schemaVersion")),
        method_version=str(identity.get("methodVersion")),
        cutoff_month=str(identity.get("cutoffMonth")),
        inputs={str(k): str(v) for k, v in (identity.get("inputs") or {}).items()},
        role_hashes={str(k): str(v) for k, v in (identity.get("roles") or {}).items()},
    )
    if declared != recomputed:
        problems.append(f"generation mismatch: manifest {declared} != recomputed {recomputed}")

    root = manifest_path.parent
    for asset in manifest.get("assets", []):
        path = root / str(asset["path"])
        if not path.is_file():
            problems.append(f"missing asset {asset['path']}")
            continue
        payload = path.read_bytes()
        if len(payload) != asset["bytes"]:
            problems.append(f"size mismatch for {asset['path']}")
        if sha256_hex(payload) != asset["sha256"]:
            problems.append(f"hash mismatch for {asset['path']}")
        try:
            decoded = gzip.decompress(payload)
        except (OSError, EOFError) as exc:
            problems.append(f"unreadable payload {asset['path']}: {exc}")
            continue
        if declared and declared.encode() in decoded:
            problems.append(f"{asset['path']} embeds its own generation")
    return problems


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def load_unified(platinum_dir: Path) -> pd.DataFrame:
    path = platinum_dir / UNIFIED_NAME
    if not path.is_file():
        raise SystemExit(f"Missing platinum input: {path}")
    columns = ["property_type", "is_ec", "transaction_date", "price", "psf"]
    frame = pd.read_parquet(path)
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise SystemExit(f"{path} lacks required columns: {missing}")
    return frame


def prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    prepared["transaction_date"] = pd.to_datetime(prepared["transaction_date"])
    prepared["month"] = prepared["transaction_date"].dt.strftime("%Y-%m")
    prepared["property_label"] = property_label_frame(prepared)
    if "planning_area" in prepared.columns:
        prepared["planning_area"] = prepared["planning_area"].astype(str).str.strip().str.upper()
    return prepared


def _parse_scope_status(values: list[str]) -> dict[str, str]:
    status: dict[str, str] = {}
    for value in values:
        key, _, disposition = value.partition("=")
        key = key.strip().lower()
        disposition = disposition.strip()
        if key not in PROPERTY_TYPES:
            raise SystemExit(f"Unknown property type in --scope-status: {key}")
        if disposition not in VALID_DISPOSITIONS:
            raise SystemExit(f"Unknown disposition {disposition!r}; expected {VALID_DISPOSITIONS}")
        status[key] = disposition
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Build the v2 observed release pack.").splitlines()[0]
    )
    parser.add_argument("--last-complete-month", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--platinum-dir", type=Path, default=DEFAULT_PLATINUM)
    parser.add_argument(
        "--scope-status",
        action="append",
        default=[],
        metavar="TYPE=DISPOSITION",
        help="Property-type disposition, e.g. hdb=publish ec=limited-display",
    )
    parser.add_argument("--no-areas", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)

    manifest_path = args.output_dir / "dashboard-release-v2.json"
    if args.verify_only:
        problems = verify_pack(manifest_path)
        for problem in problems:
            print(f"  - {problem}")
        print("Pass: v2 pack verified." if not problems else "FAILED")
        return 1 if problems else 0

    cutoff_month, cutoff_source = cutoff_from_last_complete_month(args.last_complete_month)

    frame = prepare_frame(load_unified(args.platinum_dir))
    bounded = frame.loc[frame["month"] <= cutoff_month]
    assert isinstance(bounded, pd.DataFrame)
    frame = bounded

    present_months = months_present_of(frame)
    periods = build_periods(cutoff_month, covered_months=set(present_months))
    available = period_ids(periods)
    descriptors = []
    for period in periods:
        payload = period.as_dict()
        payload["comparatorId"] = resolve_comparator(period, available)
        descriptors.append(payload)

    dispositions = _resolve_dispositions(_parse_scope_status(args.scope_status))
    observations, months_present = build_observations(
        frame,
        periods,
        dispositions=dispositions,
        include_areas=not args.no_areas,
        covered_months=set(present_months),
    )
    monthly_payloads = build_monthly_history(
        frame,
        cutoff_month=cutoff_month,
        dispositions=dispositions,
        include_areas=not args.no_areas,
    )

    periods_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "methodVersion": METHOD_VERSION,
        "cutoffMonth": cutoff_month,
        "periods": descriptors,
        "propertyTypes": list(PROPERTY_TYPES),
        "metrics": list(METRICS),
    }
    summary = {
        "schemaVersion": SCHEMA_VERSION,
        "methodVersion": METHOD_VERSION,
        "cutoffMonth": cutoff_month,
        "cutoffSource": cutoff_source,
        "monthsPresent": months_present,
        "observations": observations,
    }

    inputs = {}
    unified_path = args.platinum_dir / UNIFIED_NAME
    if unified_path.is_file():
        inputs["unified_dataset"] = sha256_hex(unified_path.read_bytes())

    result = emit_pack(
        output_dir=args.output_dir,
        summary=summary,
        periods_payload=periods_payload,
        cutoff_month=cutoff_month,
        cutoff_source=cutoff_source,
        inputs=inputs,
        scope_status=dispositions,
        monthly_payloads=monthly_payloads,
    )

    problems = verify_pack(result.manifest_path)
    print(f"Generation: {result.generation}")
    print(f"Observations: {len(observations)}")
    for role in sorted(monthly_payloads):
        payload = monthly_payloads[role]
        months = payload.get("months")
        series = payload.get("series")
        month_count = len(months) if isinstance(months, list) else 0
        geo_count = len(series) if isinstance(series, list) else 0
        print(
            f"History {role}: {result.roles[role]['bytes']} bytes, "
            f"{month_count} months, {geo_count} geographies"
        )
    print(f"Manifest: {result.manifest_path}")
    if problems:
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("Pass: v2 pack verified.")
    return 0


def months_present_of(frame: pd.DataFrame) -> list[str]:
    return sorted(str(month) for month in frame["month"].dropna().unique())


if __name__ == "__main__":
    sys.exit(main())
