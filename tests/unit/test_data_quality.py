import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from scripts.core.data_quality import (
    MIN_BASELINE_SAMPLES,
    DataQualityCollector,
    QualitySnapshot,
    get_collector,
    get_duplicate_status,
    infer_quality_stage,
    monitor_data_quality,
    record_dataframe_quality,
    reset_collector,
)


def test_database_initialization():
    """Test that database and tables are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        DataQualityCollector(db_path)

        # Verify tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='run_snapshots'")
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


def test_update_baseline_creates_new_baseline():
    """Test that first snapshot creates a new baseline."""
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
            columns=["col1"],
            data_types={"col1": "int64"},
            source="test",
            stage="L1",
        )

        collector.record_snapshot(snapshot)

        # Verify baseline was created
        baseline = collector.get_baseline("test_dataset", "L1")
        assert baseline is not None
        assert baseline.mean_rows == 950.0
        assert baseline.std_rows == 0.0  # No variance yet
        assert baseline.sample_count == 1


def test_update_baseline_updates_existing():
    """Test that subsequent snapshots update baseline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = DataQualityCollector(db_path)

        # Record first snapshot
        snapshot1 = QualitySnapshot(
            timestamp="2026-03-03 12:00:00",
            dataset_name="test_dataset",
            input_rows=1000,
            output_rows=1000,
            duplicate_count=0,
            null_percentage=2.0,
            columns=["col1"],
            data_types={"col1": "int64"},
            source="test",
            stage="L1",
        )
        collector.record_snapshot(snapshot1)

        # Record second snapshot
        snapshot2 = QualitySnapshot(
            timestamp="2026-03-03 12:01:00",
            dataset_name="test_dataset",
            input_rows=1000,
            output_rows=1100,
            duplicate_count=0,
            null_percentage=3.0,
            columns=["col1"],
            data_types={"col1": "int64"},
            source="test",
            stage="L1",
        )
        collector.record_snapshot(snapshot2)

        # Verify baseline was updated
        baseline = collector.get_baseline("test_dataset", "L1")
        assert baseline.mean_rows == 1050.0  # (1000 + 1100) / 2
        assert baseline.sample_count == 2


def test_check_anomaly_no_baseline():
    """Test that no anomalies detected when no baseline exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = DataQualityCollector(db_path)

        snapshot = QualitySnapshot(
            timestamp="2026-03-03 12:00:00",
            dataset_name="new_dataset",
            input_rows=1000,
            output_rows=100,
            duplicate_count=0,
            null_percentage=50.0,  # Extreme values
            columns=["col1"],
            data_types={"col1": "int64"},
            source="test",
            stage="L1",
        )

        anomalies = collector.check_anomaly(snapshot)
        assert anomalies == []  # No baseline = no anomalies


def test_check_anomaly_detects_spike():
    """Test that anomalies are detected when values deviate >3σ."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = DataQualityCollector(db_path)

        # Create baseline with 1000 rows, 2% nulls
        for i in range(10):
            snapshot = QualitySnapshot(
                timestamp=f"2026-03-03 12:0{i}:00",
                dataset_name="test_dataset",
                input_rows=1000,
                output_rows=1000,
                duplicate_count=0,
                null_percentage=2.0,
                columns=["col1"],
                data_types={"col1": "int64"},
                source="test",
                stage="L1",
            )
            collector.record_snapshot(snapshot)

        # Anomalous snapshot: 5000 rows (5x normal)
        anomalous_snapshot = QualitySnapshot(
            timestamp="2026-03-03 12:10:00",
            dataset_name="test_dataset",
            input_rows=5000,
            output_rows=5000,
            duplicate_count=0,
            null_percentage=2.0,
            columns=["col1"],
            data_types={"col1": "int64"},
            source="test",
            stage="L1",
        )

        anomalies = collector.check_anomaly(anomalous_snapshot)
        assert len(anomalies) > 0
        assert any("Row count" in a for a in anomalies)


def test_check_anomaly_respects_baseline_warmup_threshold():
    """Test that anomaly checks stay silent until enough baseline samples exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        collector = DataQualityCollector(db_path)

        for i in range(MIN_BASELINE_SAMPLES - 1):
            snapshot = QualitySnapshot(
                timestamp=f"2026-03-03 12:0{i}:00",
                dataset_name="warmup_dataset",
                input_rows=100,
                output_rows=100,
                duplicate_count=0,
                null_percentage=1.0,
                columns=["col1"],
                data_types={"col1": "int64"},
                source="test",
                stage="L1",
            )
            collector.record_snapshot(snapshot)

        anomalous_snapshot = QualitySnapshot(
            timestamp="2026-03-03 12:10:00",
            dataset_name="warmup_dataset",
            input_rows=1000,
            output_rows=1000,
            duplicate_count=0,
            null_percentage=1.0,
            columns=["col1"],
            data_types={"col1": "int64"},
            source="test",
            stage="L1",
        )

        assert collector.check_anomaly(anomalous_snapshot) == []


def test_get_duplicate_status_allows_expected_duplicate_heavy_datasets():
    """Test that known denormalized datasets do not trigger duplicate warnings."""
    status, should_warn = get_duplicate_status("L3_property_nearby_facilities", 25)

    assert status == "✅ OK (expected duplicates)"
    assert should_warn is False


def test_get_duplicate_status_warns_for_strict_datasets():
    """Test that strict datasets still warn when duplicates are present."""
    status, should_warn = get_duplicate_status("L3_housing_unified", 2)

    assert status == "⚠️  2 duplicates"
    assert should_warn is True


@pytest.mark.parametrize(
    ("dataset_name", "expected_stage"),
    [
        ("raw_datagov_resale_flat_all", "L0"),
        ("L1_housing_hdb_transaction", "L1"),
        ("L3_housing_unified", "L3"),
        ("test_dataset", "unknown"),
    ],
)
def test_infer_quality_stage(dataset_name, expected_stage):
    """Test stage inference for common dataset naming patterns."""
    assert infer_quality_stage(dataset_name) == expected_stage


def test_get_collector_recreates_for_override_path():
    """Test that an explicit db_path replaces a stale global collector."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_db_path = Path(tmpdir) / "original.db"
        override_db_path = Path(tmpdir) / "override.db"

        reset_collector()

        collector = get_collector(original_db_path)
        assert collector.db_path == original_db_path

        overridden = get_collector(override_db_path)
        assert overridden.db_path == override_db_path
        assert overridden is not collector

        reset_collector()


def test_record_dataframe_quality_supports_arbitrary_saves():
    """Test direct quality capture for non-save_parquet write paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        df = pd.DataFrame({"a": [1, 2], "b": [3, None]})

        reset_collector()
        snapshot = record_dataframe_quality(
            df,
            dataset_name="raw_macro_sora_rates_monthly",
            source="macro test",
            db_path=db_path,
        )

        assert snapshot.stage == "L0"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT dataset_name, stage, input_rows, output_rows FROM run_snapshots ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()

        assert row == ("raw_macro_sora_rates_monthly", "L0", 2, 2)

        reset_collector()


def test_record_dataframe_quality_handles_zero_sized_frames():
    """Test direct quality capture does not divide by zero for empty frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        df = pd.DataFrame(columns=["a", "b"])

        reset_collector()
        snapshot = record_dataframe_quality(
            df,
            dataset_name="L2_empty_snapshot",
            source="unit test",
            db_path=db_path,
        )

        assert snapshot.input_rows == 0
        assert snapshot.output_rows == 0
        assert snapshot.null_percentage == 0.0

        reset_collector()


def test_monitor_data_quality_decorator():
    """Test that decorator captures metrics and saves to DB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create a simple function to decorate
        def dummy_save(df, dataset_name, source=None):
            """Dummy save function."""
            return True

        reset_collector()
        get_collector(db_path)

        decorated_save = monitor_data_quality(dummy_save)

        # Call with test data
        df = pd.DataFrame({"a": [1, 2, 2], "b": [1, 1, 1]})
        result = decorated_save(df, "test_dataset", source="test")

        assert result is True

        # Verify snapshot was saved
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM run_snapshots WHERE dataset_name = 'test_dataset'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[3] == "unknown"  # stage
        assert row[4] == 3  # input_rows
        assert row[6] == 1  # duplicate_count

        reset_collector()
