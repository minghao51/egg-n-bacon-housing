import tempfile
from pathlib import Path

import pytest
import sqlite3

from scripts.core.data_quality import DataQualityCollector


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
