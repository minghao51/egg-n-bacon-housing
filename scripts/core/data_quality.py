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

        conn.commit()
        conn.close()

        logger.debug(f"Recorded quality snapshot for {snapshot.dataset_name}")
