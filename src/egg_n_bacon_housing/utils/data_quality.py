"""Data quality monitoring framework for pipeline stages.

This module provides automatic quality metric capture through decorators,
SQLite storage for historical baselines, and adaptive anomaly detection.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)

_collector = None

STRICT_DUPLICATES = "STRICT"
ALLOW_ANY_DUPLICATES = "ALLOW_ANY"
ALLOW_THRESHOLD_DUPLICATES = "ALLOW_THRESHOLD"
MIN_BASELINE_SAMPLES = 3

DATASET_DUPLICATE_POLICIES = {
    "L3_property_nearby_facilities": {
        "mode": ALLOW_ANY_DUPLICATES,
    },
    "L3_private_property_facilities": {
        "mode": ALLOW_ANY_DUPLICATES,
    },
    "L3_property": {
        "mode": ALLOW_ANY_DUPLICATES,
    },
    "L3_property_transactions_sales": {
        "mode": ALLOW_ANY_DUPLICATES,
    },
    "L3_property_listing_sales": {
        "mode": ALLOW_ANY_DUPLICATES,
    },
    "L2_housing_per_type_amenity_features": {
        "mode": ALLOW_ANY_DUPLICATES,
    },
}


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


@dataclass
class QualityBaseline:
    """Historical baseline for adaptive thresholds."""

    dataset_name: str
    stage: str
    mean_rows: float
    std_rows: float
    mean_null_pct: float
    std_null_pct: float
    sample_count: int
    last_updated: str


def get_collector(db_path: Path | None = None) -> "DataQualityCollector":
    """Get or create global collector instance.

    If ``db_path`` is provided, reuse the current collector only when it points
    at the same database. This keeps tests isolated when they override the data
    directory.
    """
    global _collector
    if _collector is None:
        _collector = DataQualityCollector(db_path)
    elif db_path is not None and Path(_collector.db_path) != Path(db_path):
        _collector = DataQualityCollector(db_path)
    return _collector


def reset_collector() -> None:
    """Reset the global collector instance.

    Intended for tests that need a fresh collector after monkeypatching
    configuration paths.
    """
    global _collector
    _collector = None


def infer_quality_stage(dataset_name: str) -> str:
    """Infer pipeline stage from the dataset name."""
    stage_prefixes = {"L0", "L1", "L2", "L3", "L4", "L5"}
    prefix = dataset_name.split("_", 1)[0]
    if prefix in stage_prefixes:
        return prefix
    if dataset_name.startswith("raw_"):
        return "L0"
    return "unknown"


def record_dataframe_quality(
    df: pd.DataFrame,
    dataset_name: str,
    source: str = "unknown",
    stage: str | None = None,
    db_path: Path | None = None,
    input_rows: int | None = None,
) -> QualitySnapshot:
    """Record quality metrics for an already-persisted DataFrame."""
    null_percentage = 0.0
    if df.size > 0:
        null_percentage = round((df.isnull().sum().sum() / df.size) * 100, 2)

    snapshot = QualitySnapshot(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        dataset_name=dataset_name,
        input_rows=len(df) if input_rows is None else input_rows,
        output_rows=len(df),
        duplicate_count=int(df.duplicated().sum()),
        null_percentage=null_percentage,
        columns=df.columns.tolist(),
        data_types={col: str(dtype) for col, dtype in df.dtypes.items()},
        source=source,
        stage=stage or infer_quality_stage(dataset_name),
    )

    collector = get_collector(db_path)
    collector.record_snapshot(snapshot)

    anomalies = collector.check_anomaly(snapshot)
    _log_quality_summary(snapshot, anomalies)

    return snapshot


def monitor_data_quality(func):
    """Decorator for save_parquet to capture quality metrics."""

    @wraps(func)
    def wrapper(df: pd.DataFrame, dataset_name: str, *args, **kwargs):
        input_rows = len(df)
        stage = infer_quality_stage(dataset_name)

        source = kwargs.get("source", "unknown")

        result = func(df, dataset_name, *args, **kwargs)

        record_dataframe_quality(
            df,
            dataset_name=dataset_name,
            source=source,
            stage=stage,
            input_rows=input_rows,
        )

        return result

    return wrapper


def get_duplicate_status(dataset_name: str, duplicate_count: int) -> tuple[str, bool]:
    """Return a human-readable duplicate status and whether it should warn."""
    if duplicate_count == 0:
        return "✅ OK", False

    policy = DATASET_DUPLICATE_POLICIES.get(dataset_name, {"mode": STRICT_DUPLICATES})
    mode = policy["mode"]

    if mode == ALLOW_ANY_DUPLICATES:
        return "✅ OK (expected duplicates)", False

    if mode == ALLOW_THRESHOLD_DUPLICATES:
        threshold = policy.get("threshold", 0)
        if duplicate_count <= threshold:
            return f"✅ OK (<= {threshold} duplicates expected)", False
        return f"⚠️  {duplicate_count} duplicates (> {threshold} expected)", True

    return f"⚠️  {duplicate_count} duplicates", True


def _log_quality_summary(snapshot: QualitySnapshot, anomalies: list[str]) -> None:
    """Log quality summary to terminal."""

    row_change = snapshot.output_rows - snapshot.input_rows
    row_change_pct = (row_change / snapshot.input_rows * 100) if snapshot.input_rows > 0 else 0

    duplicate_status, duplicate_warning = get_duplicate_status(
        snapshot.dataset_name, snapshot.duplicate_count
    )

    if anomalies:
        status = "⚠️  ANOMALIES DETECTED"
        level = logger.warning
    elif duplicate_warning:
        status = duplicate_status
        level = logger.warning
    else:
        status = duplicate_status
        level = logger.info

    message = (
        f"Data Quality: {snapshot.dataset_name} | "
        f"{snapshot.output_rows:,} rows "
        f"({row_change:+,} ({row_change_pct:+.1f}%)) | "
        f"{snapshot.duplicate_count} duplicates | "
        f"{snapshot.null_percentage:.2f}% nulls | "
        f"{status}"
    )

    level(message)

    for anomaly in anomalies:
        logger.warning(f"  ⚠️  {anomaly}")


class DataQualityCollector:
    """Collects and analyzes data quality metrics."""

    def __init__(self, db_path: Path | None = None):
        """Initialize collector with SQLite database."""
        self.db_path = db_path or (settings.data_dir / "quality_metrics.db")
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

        logger.info(f"Data quality database initialized: {self.db_path}")

    def record_snapshot(self, snapshot: QualitySnapshot) -> None:
        """Save snapshot to database and update baseline."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO run_snapshots
            (timestamp, dataset_name, stage, input_rows, output_rows,
             duplicate_count, null_percentage, column_count, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                snapshot.timestamp,
                snapshot.dataset_name,
                snapshot.stage,
                snapshot.input_rows,
                snapshot.output_rows,
                snapshot.duplicate_count,
                snapshot.null_percentage,
                len(snapshot.columns),
                snapshot.source,
            ),
        )

        self._update_baseline(cursor, snapshot)

        conn.commit()
        conn.close()

        logger.debug(f"Recorded quality snapshot for {snapshot.dataset_name}")

    def _update_baseline(self, cursor: sqlite3.Cursor, snapshot: QualitySnapshot) -> None:
        """Update baseline using incremental algorithm (Welford's method)."""
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
            std_rows_new = (
                std_rows * (n - 1) / n + (delta * (snapshot.output_rows - mean_rows_new)) / n
            )

            delta_null = snapshot.null_percentage - mean_null_pct
            mean_null_pct_new = mean_null_pct + delta_null / n_new
            std_null_pct_new = (
                std_null_pct * (n - 1) / n
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
                    std_rows_new,
                    mean_null_pct_new,
                    std_null_pct_new,
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
            z_score = abs(snapshot.output_rows - baseline.mean_rows) / baseline.std_rows
            if z_score > 3:
                anomalies.append(
                    f"Row count: {snapshot.output_rows} "
                    f"(baseline: {baseline.mean_rows:.0f}±{baseline.std_rows:.0f})"
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
            z_score = abs(snapshot.null_percentage - baseline.mean_null_pct) / baseline.std_null_pct
            if z_score > 3:
                anomalies.append(
                    f"Null %: {snapshot.null_percentage:.2f}% "
                    f"(baseline: {baseline.mean_null_pct:.2f}±{baseline.std_null_pct:.2f})"
                )

        return anomalies
