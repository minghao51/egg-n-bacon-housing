"""Data quality monitoring framework for pipeline stages.

This module provides automatic quality metric capture through decorators,
SQLite storage for historical baselines, and adaptive anomaly detection.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_collector = None

MIN_BASELINE_SAMPLES = 3

# Full-row duplicate detection hashes every row across every column, so its
# cost grows with rows x cols (the large fact tables are ~1M x 60). Above
# this deterministic row limit the duplicate scan samples the head of the
# frame instead of hashing all of it; frames at or below the limit keep the
# exact full-frame count. ``QualitySnapshot.duplicate_count_sampled`` flags
# which kind of count a snapshot carries (not persisted to run_snapshots).
_DUPLICATE_SCAN_ROW_LIMIT = 50_000


@dataclass
class QualitySnapshot:
    """Single data quality snapshot."""

    timestamp: str
    dataset_name: str
    input_rows: int
    output_rows: int
    duplicate_count: int
    null_percentage: float
    columns: list[str]
    data_types: dict[str, str]
    source: str
    stage: str
    # True when duplicate_count was measured on a deterministic head sample
    # (frames above _DUPLICATE_SCAN_ROW_LIMIT) instead of the full frame.
    # Companion flag for the duplicate_count metric.
    duplicate_count_sampled: bool = False


@dataclass
class QualityBaseline:
    """Historical baseline for adaptive thresholds.

    The ``std_rows``/``std_null_pct`` fields hold the sample *standard
    deviation* (matching their names and the database columns).
    """

    dataset_name: str
    stage: str
    mean_rows: float
    std_rows: float
    mean_null_pct: float
    std_null_pct: float
    sample_count: int
    last_updated: str


def get_collector(db_path: Path) -> "DataQualityCollector":
    """Get or create global collector instance.

    Reuses the current collector only when it points at the same database.
    This keeps tests isolated when they override the data directory.
    """
    global _collector
    if _collector is None:
        _collector = DataQualityCollector(db_path)
    elif Path(_collector.db_path) != Path(db_path):
        _collector = DataQualityCollector(db_path)
    return _collector


def record_dataframe_quality(
    df: pd.DataFrame,
    dataset_name: str,
    db_path: Path,
    source: str = "unknown",
    stage: str = "unknown",
    input_rows: int | None = None,
) -> QualitySnapshot:
    """Record quality metrics for an already-persisted DataFrame."""
    # Null scan: isnull().sum().sum() is a single vectorized pass per column
    # (each column's isna runs once in C; the only intermediate is the bool
    # frame) — no cheaper exact formulation exists, so this stays as-is.
    null_percentage = 0.0
    if df.size > 0:
        null_percentage = round((df.isnull().sum().sum() / df.size) * 100, 2)

    if len(df) <= _DUPLICATE_SCAN_ROW_LIMIT:
        duplicate_count = int(df.duplicated().sum())
        duplicate_count_sampled = False
    else:
        # Deterministic head sample (no RNG): duplicate_count reflects the
        # scanned prefix only, flagged via duplicate_count_sampled so
        # baselines and anomaly reads can tell sampled from exact counts.
        duplicate_count = int(df.iloc[:_DUPLICATE_SCAN_ROW_LIMIT].duplicated().sum())
        duplicate_count_sampled = True

    snapshot = QualitySnapshot(
        timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
        dataset_name=dataset_name,
        input_rows=len(df) if input_rows is None else input_rows,
        output_rows=len(df),
        duplicate_count=duplicate_count,
        null_percentage=null_percentage,
        columns=df.columns.tolist(),
        data_types={col: str(dtype) for col, dtype in df.dtypes.items()},
        source=source,
        stage=stage,
        duplicate_count_sampled=duplicate_count_sampled,
    )

    collector = get_collector(db_path)
    anomalies = collector.check_anomaly(snapshot)
    collector.record_snapshot(snapshot)
    _log_quality_summary(snapshot, anomalies)

    return snapshot


def _log_quality_summary(snapshot: QualitySnapshot, anomalies: list[str]) -> None:
    """Log quality summary to terminal."""

    row_change = snapshot.output_rows - snapshot.input_rows
    row_change_pct = (row_change / snapshot.input_rows * 100) if snapshot.input_rows > 0 else 0

    if anomalies:
        status = "⚠️  ANOMALIES DETECTED"
        level = logger.warning
    elif snapshot.duplicate_count > 0:
        sample_note = " (head-sampled)" if snapshot.duplicate_count_sampled else ""
        status = f"⚠️  {snapshot.duplicate_count} duplicates{sample_note}"
        level = logger.warning
    else:
        status = "✅ OK"
        level = logger.info

    message = "Data Quality: {} | {} rows ({} ({}%)) | {} duplicates | {}% nulls | {}".format(
        snapshot.dataset_name,
        f"{snapshot.output_rows:,}",
        f"{row_change:+,}",
        f"{row_change_pct:+.1f}",
        snapshot.duplicate_count,
        f"{snapshot.null_percentage:.2f}",
        status,
    )

    level(message)

    for anomaly in anomalies:
        logger.warning("  ⚠️  %s", anomaly)


class DataQualityCollector:
    """Collects and analyzes data quality metrics."""

    def __init__(self, db_path: Path):
        """Initialize collector with SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS run_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                dataset_name TEXT NOT NULL,
                stage TEXT NOT NULL,
                input_rows INTEGER NOT NULL,
                output_rows INTEGER NOT NULL,
                duplicate_count INTEGER NOT NULL,
                null_percentage REAL NOT NULL,
                column_count INTEGER NOT NULL,
                source TEXT
            )
        """
        )

        columns = {row[1] for row in cursor.execute("PRAGMA table_info(run_snapshots)").fetchall()}
        if "duplicate_count_sampled" not in columns:
            cursor.execute(
                "ALTER TABLE run_snapshots ADD COLUMN duplicate_count_sampled INTEGER NOT NULL DEFAULT 0"
            )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dataset_stage ON run_snapshots(dataset_name, stage)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON run_snapshots(timestamp)")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_name TEXT NOT NULL,
                stage TEXT NOT NULL,
                mean_rows REAL NOT NULL,
                std_rows REAL NOT NULL,
                mean_null_pct REAL NOT NULL,
                std_null_pct REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                last_updated TEXT NOT NULL,
                UNIQUE(dataset_name, stage)
            )
        """
        )

        conn.commit()
        conn.close()

        logger.info("Data quality database initialized: %s", self.db_path)

    def record_snapshot(self, snapshot: QualitySnapshot) -> None:
        """Save snapshot to database and update baseline."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO run_snapshots
            (timestamp, dataset_name, stage, input_rows, output_rows,
             duplicate_count, duplicate_count_sampled, null_percentage, column_count, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                snapshot.timestamp,
                snapshot.dataset_name,
                snapshot.stage,
                snapshot.input_rows,
                snapshot.output_rows,
                snapshot.duplicate_count,
                int(snapshot.duplicate_count_sampled),
                snapshot.null_percentage,
                len(snapshot.columns),
                snapshot.source,
            ),
        )

        self._update_baseline(cursor, snapshot)

        conn.commit()
        conn.close()

        logger.debug("Recorded quality snapshot for %s", snapshot.dataset_name)

    def _update_baseline(self, cursor: sqlite3.Cursor, snapshot: QualitySnapshot) -> None:
        """Update baseline using Welford's incremental method.

        The recurrence runs on the sample *variance*; the ``std_rows`` and
        ``std_null_pct`` columns store its square root, so they hold the
        sample standard deviation directly (consumed as-is by
        ``check_anomaly``).
        """
        cursor.execute(
            "SELECT mean_rows, std_rows, mean_null_pct, std_null_pct, sample_count "
            "FROM historical_baselines "
            "WHERE dataset_name = ? AND stage = ?",
            (snapshot.dataset_name, snapshot.stage),
        )

        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                """
                INSERT INTO historical_baselines
                (dataset_name, stage, mean_rows, std_rows, mean_null_pct,
                 std_null_pct, sample_count, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    snapshot.dataset_name,
                    snapshot.stage,
                    float(snapshot.output_rows),
                    0.0,
                    snapshot.null_percentage,
                    0.0,
                    1,
                    snapshot.timestamp,
                ),
            )
        else:
            mean_rows, std_rows, mean_null_pct, std_null_pct, n = row

            n_new = n + 1
            delta = snapshot.output_rows - mean_rows
            mean_rows_new = mean_rows + delta / n_new
            var_rows_new = (
                std_rows**2 * (n - 1) / n + (delta * (snapshot.output_rows - mean_rows_new)) / n
            )

            delta_null = snapshot.null_percentage - mean_null_pct
            mean_null_pct_new = mean_null_pct + delta_null / n_new
            var_null_pct_new = (
                std_null_pct**2 * (n - 1) / n
                + (delta_null * (snapshot.null_percentage - mean_null_pct_new)) / n
            )

            cursor.execute(
                """
                UPDATE historical_baselines
                SET mean_rows = ?, std_rows = ?, mean_null_pct = ?,
                    std_null_pct = ?, sample_count = ?, last_updated = ?
                WHERE dataset_name = ? AND stage = ?
            """,
                (
                    mean_rows_new,
                    var_rows_new**0.5,
                    mean_null_pct_new,
                    var_null_pct_new**0.5,
                    n_new,
                    snapshot.timestamp,
                    snapshot.dataset_name,
                    snapshot.stage,
                ),
            )

    def get_baseline(self, dataset_name: str, stage: str) -> QualityBaseline | None:
        """Get historical baseline for comparison."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT dataset_name, stage, mean_rows, std_rows, mean_null_pct,
                   std_null_pct, sample_count, last_updated
            FROM historical_baselines
            WHERE dataset_name = ? AND stage = ?
        """,
            (dataset_name, stage),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return QualityBaseline(
            dataset_name=row[0],
            stage=row[1],
            mean_rows=row[2],
            std_rows=row[3],
            mean_null_pct=row[4],
            std_null_pct=row[5],
            sample_count=row[6],
            last_updated=row[7],
        )

    def check_anomaly(self, snapshot: QualitySnapshot) -> list[str]:
        """Check if metrics deviate >3σ from historical baseline."""
        baseline = self.get_baseline(snapshot.dataset_name, snapshot.stage)

        if baseline is None:
            return []

        if baseline.sample_count < MIN_BASELINE_SAMPLES:
            return []

        anomalies = []

        if baseline.std_rows > 0.01:
            std_dev = baseline.std_rows
            z_score = abs(snapshot.output_rows - baseline.mean_rows) / std_dev
            if z_score > 3:
                anomalies.append(
                    f"Row count: {snapshot.output_rows} "
                    f"(baseline: {baseline.mean_rows:.0f}±{std_dev:.0f})"
                )
        else:
            if baseline.mean_rows > 0:
                pct_change = abs(snapshot.output_rows - baseline.mean_rows) / baseline.mean_rows
                if pct_change > 0.5:
                    anomalies.append(
                        f"Row count: {snapshot.output_rows} "
                        f"(baseline: {baseline.mean_rows:.0f}, change: {pct_change * 100:.0f}%)"
                    )

        if baseline.std_null_pct > 0.01:
            std_dev_null = baseline.std_null_pct
            z_score = abs(snapshot.null_percentage - baseline.mean_null_pct) / std_dev_null
            if z_score > 3:
                anomalies.append(
                    f"Null %: {snapshot.null_percentage:.2f}% "
                    f"(baseline: {baseline.mean_null_pct:.2f}±{std_dev_null:.2f})"
                )

        return anomalies
