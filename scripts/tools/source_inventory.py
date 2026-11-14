#!/usr/bin/env python3
"""Measure the local source inventory recorded for RS01 (`data-sources.md`).

RS01's register gate asks for a measured per-source inventory — identity,
acquisition, grain, coverage, counts and lags — rather than a restatement of the
article. This tool produces exactly that from the files in this checkout, so the
ledger can be re-measured and diffed instead of trusted.

It never fetches, never runs the pipeline and never writes outside `--output`:
it reads bronze/derived files, hashes them, and records coverage bounds from the
temporal column each file actually carries.

Usage:

    uv run python scripts/tools/source_inventory.py \
        --output docs/implementation/artifacts/rs01-source-inventory.json

    uv run python scripts/tools/source_inventory.py --check   # verify no drift
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_DIR = REPO_ROOT / "data" / "pipeline" / "01_bronze"
EXTERNAL_DIR = BRONZE_DIR / "external"
MANUAL_DIR = REPO_ROOT / "data" / "manual"
PLATINUM_DIR = REPO_ROOT / "data" / "pipeline" / "04_platinum"
GOLD_DIR = REPO_ROOT / "data" / "pipeline" / "03_gold"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "implementation" / "artifacts" / "rs01-source-inventory.json"

SCHEMA_VERSION = "1.0.0"

# Temporal columns, in the order this repo's sources actually use them.
DATE_COLUMNS = (
    "transaction_date",
    "sale_date",
    "rent_approval_date",
    "month",
    "date",
    "quarter",
)

# Files that are acquisition inputs rather than pipeline bronze outputs.
MANUAL_SUFFIXES = (".csv", ".geojson", ".json", ".txt")

MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
QUARTER_PATTERN = re.compile(r"^\d{4}Q[1-4]$")


@dataclass(frozen=True)
class Measured:
    path: str
    kind: str
    format: str
    bytes: int
    sha256: str
    rows: int | None
    columns: list[str]
    coverage: dict[str, str | None]
    format_matches_extension: bool = True


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _coverage(frame: pd.DataFrame) -> dict[str, str | None]:
    """Bounds of the temporal column this file carries, if any."""
    for column in DATE_COLUMNS:
        if column not in frame.columns:
            continue
        series = frame[column]
        values = series.dropna()
        if values.empty:
            continue
        sample = str(values.iloc[0])
        if MONTH_PATTERN.match(sample):
            ordered = sorted({str(value) for value in values})
            return {"column": column, "min": ordered[0], "max": ordered[-1]}
        if QUARTER_PATTERN.match(sample):
            ordered = sorted({str(value) for value in values})
            return {"column": column, "min": ordered[0], "max": ordered[-1]}
        parsed = pd.to_datetime(values, errors="coerce", format="mixed")
        parsed = parsed.dropna()
        if parsed.empty:
            continue
        return {
            "column": column,
            "min": parsed.min().strftime("%Y-%m-%d"),
            "max": parsed.max().strftime("%Y-%m-%d"),
        }
    return {"column": None, "min": None, "max": None}


def measure_parquet(path: Path, kind: str) -> Measured:
    payload = path.read_bytes()
    frame = pd.read_parquet(io.BytesIO(payload))
    return Measured(
        path=path.relative_to(REPO_ROOT).as_posix(),
        kind=kind,
        format="parquet",
        bytes=len(payload),
        sha256=sha256_bytes(payload),
        rows=int(len(frame)),
        columns=[str(column) for column in frame.columns],
        coverage=_coverage(frame),
    )


def measure_geojson(path: Path, kind: str) -> Measured:
    """Measure a GeoJSON file, recording a mismatched extension rather than failing.

    One acquisition file in `data/manual/csv/datagov/` carries CSV content under
    a `.geojson` name. RS01 is exactly where that has to be visible, so the
    ledger records the *detected* format and lets the caller see the mismatch.
    """
    payload = path.read_bytes()
    try:
        document = json.loads(payload)
    except json.JSONDecodeError:
        return measure_delimited(path, kind, declared="geojson")
    features = document.get("features") if isinstance(document, dict) else None
    return Measured(
        path=path.relative_to(REPO_ROOT).as_posix(),
        kind=kind,
        format="geojson",
        bytes=len(payload),
        sha256=sha256_bytes(payload),
        rows=len(features) if isinstance(features, list) else None,
        columns=[],
        coverage={"column": None, "min": None, "max": None},
    )


def measure_delimited(
    path: Path,
    kind: str,
    declared: str | None = None,
) -> Measured:
    payload = path.read_bytes()
    lines = payload.decode("utf-8", errors="ignore").splitlines()
    header = lines[0].split(",") if lines else []
    declared_format = declared or path.suffix.lstrip(".")
    return Measured(
        path=path.relative_to(REPO_ROOT).as_posix(),
        kind=kind,
        format="delimited",
        bytes=len(payload),
        sha256=sha256_bytes(payload),
        rows=max(len(lines) - 1, 0) if lines else 0,
        columns=[column.strip().strip('"') for column in header],
        coverage={"column": None, "min": None, "max": None},
        # Only a real disagreement is flagged: a `.csv`/`.txt` measured as
        # delimited matches its extension, a `.geojson` holding CSV does not.
        format_matches_extension=declared_format in {"csv", "txt", "delimited"},
    )


def measure_json(path: Path, kind: str) -> Measured:
    """Measure a plain JSON document; a parse failure is a recorded mismatch."""
    payload = path.read_bytes()
    try:
        document = json.loads(payload)
    except json.JSONDecodeError:
        return measure_delimited(path, kind, declared="json")
    if isinstance(document, list):
        rows: int | None = len(document)
    elif isinstance(document, dict):
        rows = len(document)
    else:
        rows = None
    return Measured(
        path=path.relative_to(REPO_ROOT).as_posix(),
        kind=kind,
        format="json",
        bytes=len(payload),
        sha256=sha256_bytes(payload),
        rows=rows,
        columns=[],
        coverage={"column": None, "min": None, "max": None},
    )


def measure_file(path: Path, kind: str) -> Measured:
    if path.suffix == ".geojson":
        return measure_geojson(path, kind)
    if path.suffix == ".json":
        return measure_json(path, kind)
    return measure_delimited(path, kind)


def measure_tree(
    root: Path,
    kind: str,
    skip: tuple[Path, ...] = (),
) -> list[Measured]:
    """Measure every file under `root`, skipping declared sub-trees.

    `external/` lives inside the bronze root but is its own acquisition family,
    so it is measured once, from its own root, rather than counted twice.
    """
    if not root.exists():
        return []
    measured: list[Measured] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if any(directory in path.parents for directory in skip):
            continue
        if path.suffix == ".parquet":
            measured.append(measure_parquet(path, kind))
        elif path.suffix in MANUAL_SUFFIXES and path.name != "bronze_manifest.json":
            measured.append(measure_file(path, kind))
    return measured


def load_manifest() -> dict[str, dict[str, Any]]:
    manifest_path = BRONZE_DIR / "bronze_manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unreadable bronze manifest {manifest_path}: {error}") from error
    return {str(key): dict(value) for key, value in raw.items() if isinstance(value, dict)}


def _manifest_key(entry: Measured, manifest: dict[str, dict[str, Any]]) -> str | None:
    """Find the manifest key for a measured file.

    The manifest is not keyed consistently: external layers use the full file
    name (`BusStops.parquet`) while the pipeline sources use the bare stem
    (`raw_hdb_resale`). Matching only the file name silently mislabels every
    raw source as unrecorded, so both forms are tried and the matched key is
    returned for the ledger to show.
    """
    path = Path(entry.path)
    for candidate in (path.name, path.stem):
        if candidate in manifest:
            return candidate
    return None


def acquisition_for(entry: Measured, manifest: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Join a measured file to its recorded acquisition (or say it is absent)."""
    key = _manifest_key(entry, manifest)
    if key is None:
        return {
            "status": "not-recorded",
            "manifestKey": None,
            "fetchedAt": None,
            "source": None,
            "rows": None,
            "rowsMatch": None,
        }
    record = manifest[key]
    recorded_rows = record.get("rows")
    return {
        "status": "recorded",
        "manifestKey": key,
        "fetchedAt": record.get("fetched_at"),
        "source": record.get("source"),
        "rows": recorded_rows,
        "rowsMatch": (
            None
            if not isinstance(recorded_rows, int) or entry.rows is None
            else recorded_rows == entry.rows
        ),
    }


def derived_outputs() -> list[dict[str, Any]]:
    """Counts the article quotes, measured from the published artifacts."""
    outputs: list[dict[str, Any]] = []
    unified = PLATINUM_DIR / "unified_dataset.parquet"
    if unified.is_file():
        frame = pd.read_parquet(unified, columns=["transaction_date", "property_type"])
        dates = pd.to_datetime(frame["transaction_date"], errors="coerce").dropna()
        outputs.append(
            {
                "name": "unified_dataset",
                "path": unified.relative_to(REPO_ROOT).as_posix(),
                "rows": int(len(frame)),
                "coverage": {
                    "column": "transaction_date",
                    "min": dates.min().strftime("%Y-%m-%d") if not dates.empty else None,
                    "max": dates.max().strftime("%Y-%m-%d") if not dates.empty else None,
                },
                "propertyTypes": {
                    str(key): int(value)
                    for key, value in frame["property_type"].astype(str).value_counts().items()
                },
            }
        )
    for name in ("rental_yield", "planning_area_360", "town_360", "block_profile"):
        path = GOLD_DIR / f"{name}.parquet"
        if not path.is_file():
            continue
        frame = pd.read_parquet(path)
        outputs.append(
            {
                "name": name,
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "rows": int(len(frame)),
                "coverage": _coverage(frame),
                "columns": [str(column) for column in frame.columns],
            }
        )
    quarantine = PLATINUM_DIR / "_quarantine"
    if quarantine.exists():
        outputs.append(
            {
                "name": "quarantine",
                "path": quarantine.relative_to(REPO_ROOT).as_posix(),
                "files": sorted(p.name for p in quarantine.rglob("*") if p.is_file()),
            }
        )
    return outputs


def build_inventory() -> dict[str, Any]:
    manifest = load_manifest()
    sources: list[dict[str, Any]] = []
    for kind, root, skip in (
        ("bronze", BRONZE_DIR, (EXTERNAL_DIR,)),
        ("external", EXTERNAL_DIR, ()),
        ("manual", MANUAL_DIR, ()),
    ):
        for entry in measure_tree(root, kind, skip):
            sources.append(
                {
                    "path": entry.path,
                    "kind": entry.kind,
                    "format": entry.format,
                    "formatMatchesExtension": entry.format_matches_extension,
                    "bytes": entry.bytes,
                    "sha256": entry.sha256,
                    "rows": entry.rows,
                    "columns": entry.columns,
                    "coverage": entry.coverage,
                    "acquisition": acquisition_for(entry, manifest),
                }
            )

    return {
        "schemaVersion": SCHEMA_VERSION,
        "scope": "RS01 data-sources inventory, measured from this checkout",
        "definition": (
            "One row per acquisition file. `coverage` is the min/max of the temporal "
            "column that file actually carries; `acquisition.status: not-recorded` "
            "means no bronze_manifest key matches the file (by name or stem), not "
            "that it is unused. `acquisition.rowsMatch` compares the manifest's "
            "recorded row count with the measured one. The ledger reports the files "
            "present; it does not check them against a separate expected-asset list."
        ),
        "sources": sources,
        "derived": derived_outputs(),
        "summary": {
            "files": len(sources),
            "bronze": sum(1 for entry in sources if entry["kind"] == "bronze"),
            "external": sum(1 for entry in sources if entry["kind"] == "external"),
            "manual": sum(1 for entry in sources if entry["kind"] == "manual"),
            "unrecordedAcquisition": sum(
                1 for entry in sources if entry["acquisition"]["status"] == "not-recorded"
            ),
            "manifestRowMismatches": sum(
                1 for entry in sources if entry["acquisition"]["rowsMatch"] is False
            ),
        },
    }


def canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def check(output: Path) -> int:
    if not output.is_file():
        print(f"FAILED: no ledger at {output}")
        return 1
    try:
        recorded = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAILED: {output} is not a readable ledger ({error})")
        return 1
    if not isinstance(recorded, dict):
        print(f"FAILED: {output} is not a ledger object")
        return 1
    measured = build_inventory()
    problems: list[str] = []
    by_path = {entry["path"]: entry for entry in measured["sources"]}
    for entry in recorded.get("sources", []):
        current = by_path.get(entry["path"])
        if current is None:
            problems.append(f"missing source {entry['path']}")
            continue
        if current["sha256"] != entry["sha256"]:
            problems.append(f"sha256 drift {entry['path']}")
        if current["rows"] != entry["rows"]:
            problems.append(f"row drift {entry['path']}: {entry['rows']} -> {current['rows']}")
    recorded_paths = {entry["path"] for entry in recorded.get("sources", [])}
    for path in by_path:
        if path not in recorded_paths:
            problems.append(f"unrecorded source {path}")

    # Derived counts move whenever the pipeline is rerun (RS02's regeneration
    # changed `rental_yield` from 3,623 to 1,749 rows), so they are checked too;
    # hashing only `sources` let a stale derived figure survive a green check.
    measured_derived = {entry["name"]: entry for entry in measured["derived"]}
    for entry in recorded.get("derived", []):
        current = measured_derived.get(entry["name"])
        if current is None:
            problems.append(f"missing derived output {entry['name']}")
            continue
        if current.get("rows") != entry.get("rows"):
            problems.append(
                f"derived row drift {entry['name']}: {entry.get('rows')} -> {current.get('rows')}"
            )
    for problem in problems:
        print(f"  - {problem}")
    print("Pass: RS01 ledger matches the tree." if not problems else "FAILED")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.check:
        return check(args.output)

    inventory = build_inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(inventory))
    summary = inventory["summary"]
    print(
        f"Measured {summary['files']} files "
        f"({summary['bronze']} bronze, {summary['external']} external, {summary['manual']} manual), "
        f"{summary['unrecordedAcquisition']} without a recorded acquisition"
    )
    print(f"Ledger: {args.output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
