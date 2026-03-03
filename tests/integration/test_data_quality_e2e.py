"""End-to-end integration tests for data quality monitoring."""

import pandas as pd
import pytest

from scripts.core.data_helpers import save_parquet
from scripts.core.data_quality import get_collector, reset_collector
from scripts.utils.data_quality_report import generate_summary_report


@pytest.mark.integration
@pytest.mark.slow
def test_full_pipeline_quality_monitoring(mock_config, tmp_path):
    """Test that full pipeline generates quality data."""
    db_path = tmp_path / "quality_metrics.db"
    reset_collector()
    get_collector(db_path)

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

    # Verify the historical row with issues still appears in the ordered report.
    problematic_run = max(
        (r for r in e2e_runs if r["duplicate_count"] == 1),
        key=lambda row: row["id"],
    )
    assert problematic_run["null_percentage"] > 0  # Has nulls

    latest_run = max(e2e_runs, key=lambda row: row["id"])
    assert latest_run["duplicate_count"] == 0
    assert latest_run["null_percentage"] == 0

    reset_collector()
