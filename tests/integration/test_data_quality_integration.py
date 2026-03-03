"""Integration tests for data quality monitoring."""

import sqlite3

import pandas as pd
import pytest

from scripts.core.data_helpers import save_parquet
from scripts.core.data_quality import get_collector, reset_collector
from scripts.core.stages.L3_export import save_precomputed_tables


@pytest.mark.integration
def test_save_parquet_with_quality_monitoring(mock_config, tmp_path):
    """Test that save_parquet triggers quality monitoring."""
    db_path = tmp_path / "quality_metrics.db"
    reset_collector()
    get_collector(db_path)

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
    assert row[3] == "unknown"
    assert row[4] == 3  # input_rows

    reset_collector()


@pytest.mark.integration
def test_save_precomputed_tables_with_quality_monitoring(mock_config, tmp_path):
    """Test that L3 precomputed tables are saved and monitored."""
    db_path = tmp_path / "quality_metrics.db"
    reset_collector()
    get_collector(db_path)

    table = pd.DataFrame({"metric": ["value"], "score": [1.0]})
    l3_dir = mock_config.PARQUETS_DIR / "L3"

    save_precomputed_tables(
        market_summary=table,
        tier_thresholds=table,
        pa_metrics=table,
        lease_decay=table,
        rental_combos=table,
        l3_dir=l3_dir,
    )

    expected_files = [
        l3_dir / "market_summary.parquet",
        l3_dir / "tier_thresholds_evolution.parquet",
        l3_dir / "planning_area_metrics.parquet",
        l3_dir / "lease_decay_stats.parquet",
        l3_dir / "rental_yield_top_combos.parquet",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected precomputed table at {path}"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT dataset_name
        FROM run_snapshots
        WHERE dataset_name LIKE 'L3_%'
        ORDER BY dataset_name
        """
    )
    dataset_names = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert dataset_names == [
        "L3_lease_decay_stats",
        "L3_market_summary",
        "L3_planning_area_metrics",
        "L3_rental_yield_top_combos",
        "L3_tier_thresholds_evolution",
    ]

    reset_collector()
