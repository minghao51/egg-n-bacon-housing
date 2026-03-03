import tempfile
from pathlib import Path

import pytest
import sqlite3

from scripts.core.data_quality import DataQualityCollector, QualitySnapshot


def test_database_initialization():
    """Test that database and tables are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = DataQualityCollector(db_path)

        # Verify tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='run_snapshots'"
        )
        assert cursor.fetchone() is not None, "run_snapshots table not created"

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='historical_baselines'"
        )
        assert cursor.fetchone() is not None, "historical_baselines table not created"

        conn.close()


def test_record_snapshot():
    """Test recording a quality snapshot."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = DataQualityCollector(db_path)

        snapshot = QualitySnapshot(
            timestamp="2026-03-03 12:00:00",
            dataset_name="test_dataset",
            input_rows=1000,
            output_rows=950,
            duplicate_count=5,
            null_percentage=2.5,
            columns=["col1", "col2"],
            data_types={"col1": "int64", "col2": "float64"},
            source="test",
            stage="L1",
        )

        collector.record_snapshot(snapshot)

        # Verify snapshot was saved
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM run_snapshots WHERE dataset_name = 'test_dataset'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[2] == "test_dataset"  # dataset_name
        assert row[4] == 1000  # input_rows
        assert row[5] == 950  # output_rows
