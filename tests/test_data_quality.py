"""Tests for data quality monitoring and TrackedWriter integration."""

import sqlite3

import pandas as pd
import pytest

from egg_n_bacon_housing.config import Settings
from egg_n_bacon_housing.utils import data_quality
from egg_n_bacon_housing.utils.layer_writer import TrackedWriter

pytestmark = pytest.mark.unit


def test_get_duplicate_status():
    # STRICT default policy
    status, warn = data_quality.get_duplicate_status("unknown_dataset", 0)
    assert not warn
    assert "OK" in status

    status, warn = data_quality.get_duplicate_status("unknown_dataset", 10)
    assert warn
    assert "duplicates" in status

    # ALLOW_ANY policy
    status, warn = data_quality.get_duplicate_status("L3_property", 50)
    assert not warn
    assert "expected" in status


def test_infer_quality_stage():
    assert data_quality.infer_quality_stage("L2_housing") == "L2"
    assert data_quality.infer_quality_stage("raw_mrt_stations") == "L0"
    assert data_quality.infer_quality_stage("something_else") == "unknown"


def test_collector_init_and_recording(tmp_path):
    db_path = tmp_path / "quality_metrics.db"
    collector = data_quality.get_collector(db_path)

    # Database is initialized on creation
    assert db_path.exists()

    # Check database tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    assert "run_snapshots" in tables
    assert "historical_baselines" in tables
    conn.close()

    # Record snapshot
    df = pd.DataFrame({"a": [1, 2, 3], "b": [None, 4, 5]})
    snapshot = data_quality.record_dataframe_quality(
        df,
        dataset_name="L1_test_dataset",
        db_path=db_path,
        source="test_runner",
        stage="L1",
        input_rows=3,
    )

    assert snapshot.output_rows == 3
    assert snapshot.null_percentage == pytest.approx(
        16.67, abs=0.1
    )  # 1 null out of 6 elements = 16.67%
    assert snapshot.duplicate_count == 0

    # Retrieve baseline
    baseline = collector.get_baseline("L1_test_dataset", "L1")
    assert baseline is not None
    assert baseline.sample_count == 1
    assert baseline.mean_rows == 3.0
    assert baseline.std_rows == 0.0


def test_welford_incremental_baseline(tmp_path):
    db_path = tmp_path / "quality_metrics.db"
    collector = data_quality.get_collector(db_path)

    # Record multiple snapshots to test welford incremental stats
    # Sample row counts: 100, 110, 90 (mean = 100)
    for rows in [100, 110, 90]:
        df = pd.DataFrame({"col": range(rows)})
        data_quality.record_dataframe_quality(
            df,
            dataset_name="L1_welford_test",
            db_path=db_path,
            stage="L1",
            input_rows=rows,
        )

    baseline = collector.get_baseline("L1_welford_test", "L1")
    assert baseline is not None
    assert baseline.sample_count == 3
    assert baseline.mean_rows == pytest.approx(100.0)
    # std deviation of sample: sqrt(((100-100)^2 + (110-100)^2 + (90-100)^2) / 2)
    # wait, sample variance/std or population? Welford computes sample stats.
    # Welford computes standard variance.
    assert baseline.std_rows > 0


def test_anomaly_detection(tmp_path):
    db_path = tmp_path / "quality_metrics.db"
    collector = data_quality.get_collector(db_path)

    # CASE 1: Low variance baseline (std_rows <= 0.01). Trigger via percentage change (> 50%).
    # Establish baseline with 4 identical stable snapshots
    for _ in range(4):
        df = pd.DataFrame({"col": range(100)})
        data_quality.record_dataframe_quality(
            df,
            dataset_name="L1_low_var_test",
            db_path=db_path,
            stage="L1",
            input_rows=100,
        )

    # Anomaly test: dramatic row count drift (300 rows) checked directly on the baseline
    from datetime import UTC, datetime

    snapshot_low_var = data_quality.QualitySnapshot(
        timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
        dataset_name="L1_low_var_test",
        input_rows=100,
        output_rows=300,
        duplicate_count=0,
        null_percentage=0.0,
        columns=["col"],
        data_types={"col": "int64"},
        source="test",
        stage="L1",
    )

    anomalies_low = collector.check_anomaly(snapshot_low_var)
    assert len(anomalies_low) > 0
    assert any("Row count: 300" in a for a in anomalies_low)
    assert any("change: 200%" in a for a in anomalies_low)

    # CASE 2: Baseline with variance (std_rows > 0.01). Trigger via Z-score (> 3).
    # Establish baseline with variance: 5 runs of 100, 5 runs of 102 (mean = 101, std ~ 1.05)
    for rows in [100] * 5 + [102] * 5:
        df = pd.DataFrame({"col": range(rows)})
        data_quality.record_dataframe_quality(
            df,
            dataset_name="L1_high_var_test",
            db_path=db_path,
            stage="L1",
            input_rows=rows,
        )

    # Anomaly test: 150 rows is ~46 standard deviations away
    snapshot_high_var = data_quality.QualitySnapshot(
        timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
        dataset_name="L1_high_var_test",
        input_rows=101,
        output_rows=150,
        duplicate_count=0,
        null_percentage=0.0,
        columns=["col"],
        data_types={"col": "int64"},
        source="test",
        stage="L1",
    )

    anomalies_high = collector.check_anomaly(snapshot_high_var)
    assert len(anomalies_high) > 0
    assert any("Row count: 150" in a for a in anomalies_high)
    assert any("baseline: 101" in a for a in anomalies_high)

    # CASE 3: Null percentage anomaly (std_null_pct > 0.01). Trigger via Z-score (> 3).
    # Establish baseline: 5 runs of 10.0%, 5 runs of 12.0% (mean = 11.0%, std ~ 1.05%)
    for pct in [10.0] * 5 + [12.0] * 5:
        snap = data_quality.QualitySnapshot(
            timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
            dataset_name="L1_null_var_test",
            input_rows=100,
            output_rows=100,
            duplicate_count=0,
            null_percentage=pct,
            columns=["col"],
            data_types={"col": "int64"},
            source="test",
            stage="L1",
        )
        collector.record_snapshot(snap)

    snapshot_null_anomaly = data_quality.QualitySnapshot(
        timestamp=datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
        dataset_name="L1_null_var_test",
        input_rows=100,
        output_rows=100,
        duplicate_count=0,
        null_percentage=50.0,  # ~37 standard deviations away
        columns=["col"],
        data_types={"col": "int64"},
        source="test",
        stage="L1",
    )

    anomalies_null = collector.check_anomaly(snapshot_null_anomaly)
    assert len(anomalies_null) > 0
    assert any("Null %: 50.00%" in a for a in anomalies_null)


def test_tracked_writer_integration(tmp_path):
    # Configure settings with temp directory as data_dir
    settings = Settings(data_path=str(tmp_path))
    settings.pipeline.parquet_compression = "snappy"

    writer = TrackedWriter(data_dir=tmp_path, settings=settings)

    df = pd.DataFrame({"col1": [1, 2, 2], "col2": [None, "foo", "bar"]})

    # Write df using TrackedWriter
    written_path = writer.write(df, "cleaned_test_hdb", "silver")
    assert written_path.exists()

    # The quality database should be initialized and have recorded the entry
    db_path = settings.data_dir / "quality_metrics.db"
    assert db_path.exists()

    collector = data_quality.get_collector(db_path)
    baseline = collector.get_baseline("cleaned_test_hdb", "L_silver")
    assert baseline is not None
    assert baseline.sample_count == 1
    assert baseline.mean_rows == 3
