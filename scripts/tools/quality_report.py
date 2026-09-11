"""Read-only data-quality report over the quality DB, quarantine dirs, and bronze manifest.

Surfaces what ``utils/data_quality.py`` accumulates in ``data/quality_metrics.db``
(per-write ``run_snapshots``, Welford ``historical_baselines``) plus on-disk
quarantine files and bronze freshness — none of which have a summary view today.
The report is strictly read-only: it never writes to the database, the layer
directories, or the bronze manifest.

Sections:
1. Snapshot trends — per dataset+stage: latest snapshot (rows, null %,
   duplicates, when) vs the stored baseline mean/σ, flagging datasets where
   ``DataQualityCollector.check_anomaly`` would fire (3σ or >50% row change
   against the stored baseline).
2. Row-count deltas — latest vs previous snapshot per dataset+stage; catches
   collapse-to-zero (empty 0-row writes are visible post-WS5).
3. Quarantine summary — walks ``<layer>/_quarantine/`` dirs, parses
   ``<entity>_<YYYYMMDD>_<HHMMSS>.parquet`` filenames (as written by the
   validation gateway with ``track_quality=False``), and counts files + rows
   per entity, newest first (top N).
4. Bronze freshness — ages every ``bronze_manifest.json`` entry and flags
   entries older than ``utils.bronze.STALE_WARN_DAYS``, plus known rolling
   datasets whose manifest entry is missing.

Usage:
    uv run python scripts/tools/quality_report.py
    uv run python scripts/tools/quality_report.py --dataset hdb --top 5
    uv run python scripts/tools/quality_report.py --json | jq .

Flags:
    --db PATH      Quality SQLite DB (default: <data>/quality_metrics.db,
                   matching ``build_writer``).
    --data PATH    Data root holding the ``pipeline/`` layer dirs (default
                   from ``Settings`` resolution).
    --dataset STR  Substring filter (case-insensitive) applied to dataset
                   names, quarantine entities, and manifest entries.
    --top N        Quarantine entities to list (default 10).
    --json         Machine-readable JSON instead of human-readable text.

Exit code: 0 always, except 1 when the DB file exists but cannot be read.
This is a reporting tool, not a gate — a future CI quality gate could be
built on top of the ``--json`` output without changing this script.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[2]

# The package is not installed in the venv (pytest injects src/ via pythonpath;
# scripts bootstrap it the same way, see scripts/generate_catalog.py).
sys.path.insert(0, str(REPO_ROOT / "src"))

from egg_n_bacon_housing.config import Settings  # noqa: E402
from egg_n_bacon_housing.utils.bronze import MANIFEST_FILENAME, STALE_WARN_DAYS  # noqa: E402
from egg_n_bacon_housing.utils.data_quality import (  # noqa: E402
    DataQualityCollector,
    QualitySnapshot,
)

QUARANTINE_DIR = "_quarantine"
# Validation-gateway quarantine names: <entity>_<YYYYMMDD>_<HHMMSS>.parquet
# (the gateway may also insert a `_sample` tag before the timestamp, which
# stays part of the parsed entity name).
_QUARANTINE_TS = re.compile(r"^(?P<entity>.+)_(?P<ts>\d{8}_\d{6})$")

_SECONDS_PER_DAY = 86400.0
_LAYER_ORDER = ("bronze", "silver", "gold", "platinum", "platinum_metrics")


# ---------------------------------------------------------------------------
# Read-only DB access
# ---------------------------------------------------------------------------


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    """Open the quality DB in SQLite read-only mode; no file is ever created."""
    uri = db_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _load_run_snapshots(db_path: Path) -> list[dict[str, Any]]:
    """All snapshots ordered per (dataset, stage) by insertion id (id = time order)."""
    if not db_path.exists():
        return []
    conn = _connect_readonly(db_path)
    try:
        rows = conn.execute(
            "SELECT id, timestamp, dataset_name, stage, input_rows, output_rows, "
            "duplicate_count, null_percentage, column_count, source "
            "FROM run_snapshots ORDER BY dataset_name, stage, id"
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(row) for row in rows]


def _load_baselines(db_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Stored Welford baselines keyed by (dataset_name, stage)."""
    if not db_path.exists():
        return {}
    conn = _connect_readonly(db_path)
    try:
        rows = conn.execute(
            "SELECT dataset_name, stage, mean_rows, std_rows, mean_null_pct, "
            "std_null_pct, sample_count, last_updated FROM historical_baselines"
        ).fetchall()
    finally:
        conn.close()
    return {
        (row["dataset_name"], row["stage"]): _row_to_dict(row)  # type: ignore[index]
        for row in rows
    }


def _read_only_collector(db_path: Path) -> DataQualityCollector:
    """Collector shim that reuses the exact production anomaly logic read-only.

    ``__new__`` skips ``_init_db`` (which would create the file/tables when
    missing). ``check_anomaly``/``get_baseline`` only run SELECTs against the
    existing DB, so reporting never mutates anything.
    """
    collector = DataQualityCollector.__new__(DataQualityCollector)
    collector.db_path = db_path
    return collector


def _snapshot_from_row(row: dict[str, Any]) -> QualitySnapshot:
    """Rebuild the snapshot dataclass the anomaly check expects (schema-free)."""
    return QualitySnapshot(
        timestamp=str(row["timestamp"]),
        dataset_name=str(row["dataset_name"]),
        input_rows=int(row["input_rows"]),
        output_rows=int(row["output_rows"]),
        duplicate_count=int(row["duplicate_count"]),
        null_percentage=float(row["null_percentage"]),
        columns=[],  # column names are not persisted; check_anomaly ignores them
        data_types={},
        source=str(row["source"] or "unknown"),
        stage=str(row["stage"]),
    )


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------


def _group_snapshots(
    snapshots: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in snapshots:  # already sorted by (dataset, stage, id)
        groups.setdefault((str(row["dataset_name"]), str(row["stage"])), []).append(row)
    return groups


def _selected(name: str, dataset_filter: str | None) -> bool:
    return dataset_filter is None or dataset_filter.lower() in name.lower()


def _build_trends(
    groups: dict[tuple[str, str], list[dict[str, Any]]],
    baselines: dict[tuple[str, str], dict[str, Any]],
    db_path: Path,
    dataset_filter: str | None,
) -> list[dict[str, Any]]:
    """Latest snapshot per dataset+stage vs baseline, with anomaly flags."""
    collector = _read_only_collector(db_path)
    trends: list[dict[str, Any]] = []
    for (name, stage), snaps in sorted(groups.items()):
        if not _selected(name, dataset_filter):
            continue
        latest = snaps[-1]
        baseline = baselines.get((name, stage))
        anomalies: list[str] = []
        if baseline is not None:
            # Same evaluation the pipeline runs on write (3σ or >50% row change).
            anomalies = collector.check_anomaly(_snapshot_from_row(latest))
        trends.append(
            {
                "dataset": name,
                "stage": stage,
                "snapshot_count": len(snaps),
                "latest": {
                    "timestamp": latest["timestamp"],
                    "rows": latest["output_rows"],
                    "input_rows": latest["input_rows"],
                    "null_pct": latest["null_percentage"],
                    "duplicates": latest["duplicate_count"],
                    "columns": latest["column_count"],
                    "source": latest["source"],
                },
                "baseline": baseline,
                "anomalies": anomalies,
                "flagged": bool(anomalies),
            }
        )
    return trends


def _build_deltas(
    groups: dict[tuple[str, str], list[dict[str, Any]]],
    dataset_filter: str | None,
) -> list[dict[str, Any]]:
    """Latest vs previous snapshot per dataset+stage; catches collapse-to-zero."""
    deltas: list[dict[str, Any]] = []
    for (name, stage), snaps in sorted(groups.items()):
        if not _selected(name, dataset_filter):
            continue
        latest = snaps[-1]
        latest_out = int(latest["output_rows"])
        if len(snaps) < 2:
            deltas.append(
                {
                    "dataset": name,
                    "stage": stage,
                    "previous_rows": None,
                    "previous_at": None,
                    "latest_rows": latest_out,
                    "latest_at": latest["timestamp"],
                    "row_delta": None,
                    "pct_change": None,
                    "collapse_to_zero": False,
                }
            )
            continue
        previous = snaps[-2]
        previous_rows = int(previous["output_rows"])
        row_delta = latest_out - previous_rows
        pct = row_delta / previous_rows * 100 if previous_rows else None
        deltas.append(
            {
                "dataset": name,
                "stage": stage,
                "previous_rows": previous_rows,
                "previous_at": previous["timestamp"],
                "latest_rows": latest_out,
                "latest_at": latest["timestamp"],
                "row_delta": row_delta,
                "pct_change": round(pct, 1) if pct is not None else None,
                "collapse_to_zero": latest_out == 0 and previous_rows > 0,
            }
        )
    return deltas


def _parquet_rows(path: Path) -> int | None:
    """Row count from parquet metadata only (no data read); None when unreadable."""
    try:
        return pq.ParquetFile(path).metadata.num_rows
    except Exception:  # unreadable quarantine file must not kill the report
        return None


def _scan_quarantine_layer(
    layer: str, layer_dir: Path, dataset_filter: str | None
) -> list[dict[str, Any]]:
    """Group one layer's ``_quarantine/`` parquets per parsed entity."""
    quarantine_dir = layer_dir / QUARANTINE_DIR
    if not quarantine_dir.is_dir():
        return []
    groups: dict[str, dict[str, Any]] = {}
    for path in sorted(quarantine_dir.glob("*.parquet")):
        match = _QUARANTINE_TS.match(path.stem)
        if match:
            entity, newest = match.group("entity"), match.group("ts")
        else:
            entity, newest = path.stem, ""
        if not _selected(entity, dataset_filter):
            continue
        group = groups.setdefault(
            entity, {"layer": layer, "entity": entity, "files": 0, "rows": 0, "newest": ""}
        )
        group["files"] += 1
        rows = _parquet_rows(path)
        if rows is None:
            group["unreadable_files"] = group.get("unreadable_files", 0) + 1
        else:
            group["rows"] += rows
        group["newest"] = max(group["newest"], newest)
    return list(groups.values())


def _scan_quarantine(
    layer_paths: dict[str, Path], dataset_filter: str | None, top: int
) -> dict[str, Any]:
    """Quarantine summary across all layers: totals plus the top-N newest entities."""
    entries: list[dict[str, Any]] = []
    for layer in _LAYER_ORDER:
        entries.extend(_scan_quarantine_layer(layer, layer_paths[layer], dataset_filter))
    # Newest first; unparsed timestamps sort last.
    entries.sort(key=lambda e: (e["newest"], e["entity"]), reverse=True)
    shown = entries[: max(top, 0)]
    return {
        "total_entities": len(entries),
        "total_files": sum(e["files"] for e in entries),
        "total_rows": sum(e["rows"] for e in entries),
        "total_unreadable_files": sum(e.get("unreadable_files", 0) for e in entries),
        "shown": len(shown),
        "entities": shown,
    }


def _parse_iso_utc(raw: str) -> datetime | None:
    """Parse an ISO-8601 timestamp, assuming UTC when naive (mirrors utils.bronze)."""
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _scan_freshness(bronze_dir: Path, dataset_filter: str | None) -> dict[str, Any]:
    """Age every manifest entry, flagging stale / missing ones per STALE_WARN_DAYS."""
    manifest_path = bronze_dir / MANIFEST_FILENAME
    notes: list[str] = []
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            notes.append(f"manifest unreadable ({exc})")
            loaded = {}
        if not isinstance(loaded, dict) or not all(isinstance(v, dict) for v in loaded.values()):
            notes.append("manifest has an unexpected shape — ignored")
            loaded = {}
        manifest = loaded
    else:
        notes.append("manifest not found — no bronze fetch metadata recorded yet")

    now = datetime.now(UTC)
    entries: list[dict[str, Any]] = []
    for name in sorted(set(manifest) | set(STALE_WARN_DAYS)):
        if not _selected(name, dataset_filter):
            continue
        threshold: int | None = STALE_WARN_DAYS.get(name)
        entry: dict[str, Any] | None = manifest.get(name)
        row: dict[str, Any] = {"name": name, "threshold_days": threshold}
        if entry is None:
            parquet_present = (bronze_dir / f"{name}.parquet").exists()
            row.update(
                fetched_at=None,
                age_days=None,
                flagged=parquet_present,
                status=(
                    "missing manifest entry (parquet present)"
                    if parquet_present
                    else "never fetched"
                ),
            )
        else:
            fetched_at = entry.get("fetched_at")
            fetched = _parse_iso_utc(str(fetched_at or ""))
            if fetched is None:
                row.update(
                    fetched_at=fetched_at,
                    age_days=None,
                    flagged=True,
                    status="unreadable fetched_at",
                )
            else:
                age_days = (now - fetched).total_seconds() / _SECONDS_PER_DAY
                stale = threshold is not None and age_days > threshold
                row.update(
                    fetched_at=fetched_at,
                    age_days=round(age_days, 1),
                    flagged=stale,
                    status="stale" if stale else "ok",
                )
        entries.append(row)
    # Flagged entries first, then alphabetical.
    entries.sort(key=lambda e: (not e["flagged"], str(e["name"])))
    return {
        "manifest_path": str(manifest_path),
        "manifest_exists": manifest_path.exists(),
        "notes": notes,
        "entries": entries,
    }


def build_report(
    db_path: Path,
    layer_paths: dict[str, Path],
    dataset: str | None = None,
    top: int = 10,
) -> dict[str, Any]:
    """Assemble the full report dict (all sections + a flat flag summary)."""
    snapshots = _load_run_snapshots(db_path)
    baselines = _load_baselines(db_path)
    groups = _group_snapshots(snapshots)

    trends = _build_trends(groups, baselines, db_path, dataset)
    deltas = _build_deltas(groups, dataset)
    quarantine = _scan_quarantine(layer_paths, dataset, top)
    freshness = _scan_freshness(layer_paths["bronze"], dataset)

    timestamps = [str(s["timestamp"]) for s in snapshots if s["timestamp"]]
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "quality_db": {
            "path": str(db_path),
            "exists": db_path.exists(),
            "snapshot_count": len(snapshots),
            "dataset_count": len({name for name, _ in groups}),
            "first_snapshot_at": min(timestamps) if timestamps else None,
            "last_snapshot_at": max(timestamps) if timestamps else None,
        },
        "trends": trends,
        "deltas": deltas,
        "quarantine": quarantine,
        "freshness": freshness,
        "flags": {
            "anomalous_datasets": [
                f"{t['dataset']} [{t['stage']}]" for t in trends if t["flagged"]
            ],
            "collapsed_datasets": [
                f"{d['dataset']} [{d['stage']}]" for d in deltas if d["collapse_to_zero"]
            ],
            "stale_bronze": [e["name"] for e in freshness["entries"] if e["flagged"]],
            "quarantine_files": quarantine["total_files"],
            "quarantine_rows": quarantine["total_rows"],
        },
    }
    return report


# ---------------------------------------------------------------------------
# Human-readable formatting
# ---------------------------------------------------------------------------


def _fmt_int(value: Any) -> str:
    return f"{int(value):,}"


def _format_trends(trends: list[dict[str, Any]]) -> list[str]:
    lines = ["── Snapshot trends (latest vs baseline) " + "─" * 30]
    if not trends:
        lines.append("  (no snapshots found)")
    for trend in trends:
        latest = trend["latest"]
        lines.append(f"{trend['dataset']} [{trend['stage']}]  snapshots={trend['snapshot_count']}")
        lines.append(
            f"  latest : {latest['timestamp']} | rows={_fmt_int(latest['rows'])}"
            f" | input={_fmt_int(latest['input_rows'])} | nulls={latest['null_pct']}%"
            f" | dups={latest['duplicates']} | cols={latest['columns']}"
        )
        baseline = trend["baseline"]
        if baseline is None:
            lines.append("  baseline: (none)")
        else:
            lines.append(
                f"  baseline: rows={baseline['mean_rows']:,.1f} ±{baseline['std_rows']:,.1f}"
                f" | nulls={baseline['mean_null_pct']:.2f}% ±{baseline['std_null_pct']:.2f}"
                f" | samples={baseline['sample_count']} | updated {baseline['last_updated']}"
            )
        if trend["flagged"]:
            for anomaly in trend["anomalies"]:
                lines.append(f"  ⚠ ANOMALY: {anomaly}")
        else:
            lines.append("  ✓ no anomalies")
    return lines


def _format_deltas(deltas: list[dict[str, Any]]) -> list[str]:
    lines = ["── Row-count deltas (latest vs previous) " + "─" * 28]
    if not deltas:
        lines.append("  (no snapshots found)")
    for delta in deltas:
        label = f"{delta['dataset']} [{delta['stage']}]"
        if delta["previous_rows"] is None:
            lines.append(f"  {label}: (single snapshot; rows={_fmt_int(delta['latest_rows'])})")
            continue
        arrow = (
            f"{_fmt_int(delta['latest_rows'])} ← {_fmt_int(delta['previous_rows'])}"
            f" ({delta['row_delta']:+,}, {delta['pct_change']:+.1f}%)"
        )
        marker = "  ⚠ COLLAPSE TO ZERO" if delta["collapse_to_zero"] else ""
        lines.append(f"  {label}: {arrow}{marker}")
    return lines


def _format_quarantine(quarantine: dict[str, Any], top: int) -> list[str]:
    lines = [f"── Quarantine (top {top} entities by newest file) " + "─" * 20]
    if quarantine["total_files"] == 0:
        lines.append("  (no quarantine files found under the layer dirs)")
    for entry in quarantine["entities"]:
        unreadable = entry.get("unreadable_files", 0)
        rows = "?" if unreadable and unreadable == entry["files"] else _fmt_int(entry["rows"])
        newest = entry["newest"] or "(unparsed name)"
        lines.append(
            f"  {entry['layer']:<16} {entry['entity']:<40} files={entry['files']}"
            f"  rows={rows}  newest={newest}"
        )
    if quarantine["total_entities"] > quarantine["shown"]:
        lines.append(f"  … {quarantine['total_entities'] - quarantine['shown']} more entity(ies)")
    totals = (
        f"  total: {quarantine['total_files']} file(s), {_fmt_int(quarantine['total_rows'])} row(s)"
    )
    if quarantine["total_unreadable_files"]:
        totals += f", {quarantine['total_unreadable_files']} unreadable"
    lines.append(totals)
    return lines


def _format_freshness(freshness: dict[str, Any]) -> list[str]:
    lines = [f"── Bronze freshness ({freshness['manifest_path']}) " + "─" * 18]
    for note in freshness["notes"]:
        lines.append(f"  note: {note}")
    if freshness["manifest_exists"] and not freshness["entries"]:
        lines.append("  (manifest is empty)")
    for entry in freshness["entries"]:
        name = str(entry["name"])
        if entry["status"] == "stale":
            lines.append(
                f"  ⚠ {name}: {entry['age_days']}d old (threshold {entry['threshold_days']}d)"
                f" — STALE; refresh with: main.py --refresh {name}"
            )
        elif entry["status"] == "ok":
            suffix = (
                ""
                if entry["threshold_days"] is None
                else f" (threshold {entry['threshold_days']}d)"
            )
            lines.append(f"  {name}: {entry['age_days']}d old{suffix}")
        else:
            lines.append(f"  ⚠ {name}: {entry['status']}")
    return lines


def _format_report(report: dict[str, Any]) -> str:
    db = report["quality_db"]
    flags = report["flags"]
    lines = [
        "═" * 72,
        f"Data Quality Report — generated {report['generated_at']}",
        f"DB: {db['path']} ({'found' if db['exists'] else 'NOT FOUND'};"
        f" {db['snapshot_count']} snapshot(s), {db['dataset_count']} dataset(s)"
        + (
            f", {db['first_snapshot_at']} → {db['last_snapshot_at']}"
            if db["snapshot_count"]
            else ""
        )
        + ")",
        "═" * 72,
        *_format_trends(report["trends"]),
        *_format_deltas(report["deltas"]),
        *_format_quarantine(report["quarantine"], top=10),
        *_format_freshness(report["freshness"]),
        "── Summary " + "─" * 58,
        f"  anomalous datasets : {', '.join(flags['anomalous_datasets']) or '(none)'}",
        f"  collapsed datasets : {', '.join(flags['collapsed_datasets']) or '(none)'}",
        f"  stale bronze       : {', '.join(flags['stale_bronze']) or '(none)'}",
        f"  quarantine         : {flags['quarantine_files']} file(s) / "
        f"{_fmt_int(flags['quarantine_rows'])} row(s)",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_against_repo(raw: str) -> Path:
    """Expand a CLI path; relative paths anchor at the repository root."""
    path = Path(raw).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else "",
        epilog="Read-only: never writes to the DB, layer dirs, or manifest. "
        "Exit 0 unless the quality DB exists but is unreadable.",
    )
    parser.add_argument(
        "--db", default=None, help="Quality SQLite DB path (default: <data>/quality_metrics.db)"
    )
    parser.add_argument(
        "--data",
        default=None,
        help="Data root holding pipeline/ layer dirs (default from Settings)",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Substring filter on dataset names/entities/manifest entries",
    )
    parser.add_argument(
        "--top", type=int, default=10, help="Quarantine entities to list (default: 10)"
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint; returns the process exit code (0, or 1 on unreadable DB)."""
    args = _parse_args(argv)
    settings = Settings()
    data_root = _resolve_against_repo(args.data) if args.data else settings.data_dir
    db_path = _resolve_against_repo(args.db) if args.db else data_root / "quality_metrics.db"
    layer_paths = settings.layer_paths(data_root)

    try:
        report = build_report(db_path, layer_paths, dataset=args.dataset, top=args.top)
    except sqlite3.DatabaseError as exc:
        print(f"error: quality DB unreadable: {db_path} ({exc})", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
