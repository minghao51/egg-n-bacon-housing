"""Integration tests for data quality monitoring."""

import sqlite3

import pandas as pd
import pytest

from scripts.core.data_helpers import save_parquet
from scripts.core.data_quality import get_collector


def test_save_parquet_with_quality_monitoring():
    """Test that save_parquet triggers quality monitoring."""
    collector = get_collector()
    db_path = collector.db_path

    # Clear existing data for this dataset
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM run_snapshots WHERE dataset_name = 'integration_test'")
    cursor.execute("DELETE FROM historical_baselines WHERE dataset_name = 'integration_test'")
    conn.commit()
    conn.close()

    # Create test DataFrame
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

    # Save (should trigger quality monitoring)
    save_parquet(df, "integration_test", source="integration_test")

    # Verify snapshot was recorded
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM run_snapshots WHERE dataset_name = 'integration_test' ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[2] == "integration_test"
    assert row[4] == 3  # input_rows
