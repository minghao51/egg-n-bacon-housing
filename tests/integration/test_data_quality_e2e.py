"""End-to-end integration tests for data quality monitoring."""

import sqlite3

import pandas as pd
import pytest

from scripts.core.data_helpers import save_parquet
from scripts.core.data_quality import get_collector
from scripts.utils.data_quality_report import generate_summary_report


def test_full_pipeline_quality_monitoring():
    """Test that full pipeline generates quality data."""
    collector = get_collector()
    db_path = collector.db_path

    # Create test data with known issues
    df1 = pd.DataFrame({"a": [1, 2, 2, None], "b": [4, 5, 5, 6]})  # Has duplicates and nulls

    # Save multiple times
    save_parquet(df1, "e2e_test_dataset", source="e2e_test")

    df2 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})  # Clean data
    save_parquet(df2, "e2e_test_dataset", source="e2e_test")

    # Generate report
    report = generate_summary_report(db_path, limit=10)

    # Verify our dataset appears in report
    e2e_runs = [r for r in report if r["dataset_name"] == "e2e_test_dataset"]
    assert len(e2e_runs) >= 2

    # Verify duplicates were detected
    first_run = e2e_runs[-1]
    assert first_run["duplicate_count"] == 1  # One duplicate row
    assert first_run["null_percentage"] > 0  # Has nulls
