"""Data quality monitoring framework for pipeline stages.

This module provides automatic quality metric capture through decorators,
SQLite storage for historical baselines, and adaptive anomaly detection.
"""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from scripts.core.config import Config

logger = logging.getLogger(__name__)


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


class DataQualityCollector:
    """Collects and analyzes data quality metrics."""

    def __init__(self, db_path: Path | None = None):
        """Initialize collector with SQLite database."""
        self.db_path = db_path or (Config.DATA_DIR / "quality_metrics.db")
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create run_snapshots table
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

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dataset_stage ON run_snapshots(dataset_name, stage)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON run_snapshots(timestamp)")

        # Create historical_baselines table
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

        # Insert snapshot
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

        # Update baseline using Welford's online algorithm
        self._update_baseline(cursor, snapshot)

        conn.commit()
        conn.close()

        logger.debug(f"Recorded quality snapshot for {snapshot.dataset_name}")

    def _update_baseline(
        self, cursor: sqlite3.Cursor, snapshot: QualitySnapshot
    ) -> None:
        """Update baseline using incremental algorithm (Welford's method)."""
        # Check if baseline exists
        cursor.execute(
            "SELECT mean_rows, std_rows, mean_null_pct, std_null_pct, sample_count "
            "FROM historical_baselines "
            "WHERE dataset_name = ? AND stage = ?",
            (snapshot.dataset_name, snapshot.stage),
        )

        row = cursor.fetchone()

        if row is None:
            # Create new baseline
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
                    0.0,  # No variance yet
                    snapshot.null_percentage,
                    0.0,  # No variance yet
                    1,
                    snapshot.timestamp,
                ),
            )
        else:
            # Update using Welford's online algorithm
            mean_rows, std_rows, mean_null_pct, std_null_pct, n = row

            # Update mean and std for rows
            n_new = n + 1
            delta = snapshot.output_rows - mean_rows
            mean_rows_new = mean_rows + delta / n_new
            std_rows_new = std_rows * (n - 1) / n + (delta * (snapshot.output_rows - mean_rows_new)) / n

            # Update mean and std for null percentage
            delta_null = snapshot.null_percentage - mean_null_pct
            mean_null_pct_new = mean_null_pct + delta_null / n_new
            std_null_pct_new = (
                std_null_pct * (n - 1) / n
                + (delta_null * (snapshot.null_percentage - mean_null_pct_new)) / n
            )

            # Update database
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
            return []  # First run, no baseline

        anomalies = []

        # Check row count
        if baseline.std_rows > 0.01:
            # Use z-score when we have variance
            z_score = abs(snapshot.output_rows - baseline.mean_rows) / baseline.std_rows
            if z_score > 3:
                anomalies.append(
                    f"Row count: {snapshot.output_rows} "
                    f"(baseline: {baseline.mean_rows:.0f}±{baseline.std_rows:.0f})"
                )
        else:
            # No variance: check for large percentage changes (>50%)
            if baseline.mean_rows > 0:
                pct_change = abs(snapshot.output_rows - baseline.mean_rows) / baseline.mean_rows
                if pct_change > 0.5:  # 50% change
                    anomalies.append(
                        f"Row count: {snapshot.output_rows} "
                        f"(baseline: {baseline.mean_rows:.0f}, change: {pct_change*100:.0f}%)"
                    )

        # Check null percentage
        if baseline.std_null_pct > 0.01:
            # Use z-score when we have variance
            z_score = abs(snapshot.null_percentage - baseline.mean_null_pct) / baseline.std_null_pct
            if z_score > 3:
                anomalies.append(
                    f"Null %: {snapshot.null_percentage:.2f}% "
                    f"(baseline: {baseline.mean_null_pct:.2f}±{baseline.std_null_pct:.2f})"
                )

        return anomalies
