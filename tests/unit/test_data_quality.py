import tempfile
from pathlib import Path

import pytest
import sqlite3

from scripts.core.data_quality import DataQualityCollector, QualityBaseline, QualitySnapshot


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


def test_get_baseline_returns_none_when_no_data():
    """Test that get_baseline returns None for new datasets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = DataQualityCollector(db_path)

        baseline = collector.get_baseline("nonexistent_dataset", "L1")
        assert baseline is None


def test_get_baseline_returns_existing_baseline():
    """Test retrieving existing baseline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = DataQualityCollector(db_path)

        # Insert a baseline manually
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO historical_baselines
            (dataset_name, stage, mean_rows, std_rows, mean_null_pct,
             std_null_pct, sample_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            ("test_dataset", "L1", 1000.0, 50.0, 2.5, 0.5, 10, "2026-03-03 12:00:00"),
        )
        conn.commit()
        conn.close()

        baseline = collector.get_baseline("test_dataset", "L1")

        assert baseline is not None
        assert baseline.dataset_name == "test_dataset"
        assert baseline.mean_rows == 1000.0
        assert baseline.std_rows == 50.0
