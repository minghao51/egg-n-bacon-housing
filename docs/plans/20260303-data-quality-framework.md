# Data Quality Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a decorator-based data quality monitoring system that captures metrics at every `save_parquet()` call, stores them in SQLite, and alerts on anomalies using adaptive thresholds.

**Architecture:**
- Decorator pattern on `save_parquet()` for automatic metric capture
- SQLite database for time-series quality metrics
- Adaptive thresholds using statistical process control (3σ)
- CLI reporter for viewing quality summaries and trends

**Tech Stack:**
- Python 3.11+
- pandas (DataFrames)
- SQLite3 (built-in)
- pytest (testing)

---

## Task 1: Create Data Quality Module Structure

**Files:**
- Create: `scripts/core/data_quality.py`

**Step 1: Create module with dataclasses**

```python
"""Data quality monitoring framework for pipeline stages.

This module provides automatic quality metric capture through decorators,
SQLite storage for historical baselines, and adaptive anomaly detection.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import sqlite3

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
        # Implementation in next task
        pass
```

**Step 2: Run linter to verify syntax**

Run: `uv run ruff check scripts/core/data_quality.py`
Expected: PASS (or warnings about empty methods)

**Step 3: Commit**

```bash
git add scripts/core/data_quality.py
git commit -m "feat(data-quality): add module structure with dataclasses"
```

---

## Task 2: Implement Database Initialization

**Files:**
- Modify: `scripts/core/data_quality.py`

**Step 1: Write test for database initialization**

```python
# tests/unit/test_data_quality.py
import tempfile
from pathlib import Path

import pytest

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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_data_quality.py::test_database_initialization -v`
Expected: FAIL - tables don't exist yet

**Step 3: Implement _init_db method**

```python
# In DataQualityCollector class

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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_data_quality.py::test_database_initialization -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/core/data_quality.py tests/unit/test_data_quality.py
git commit -m "feat(data-quality): implement database initialization with schema"
```

---

## Task 3: Implement Snapshot Recording

**Files:**
- Modify: `scripts/core/data_quality.py`
- Modify: `tests/unit/test_data_quality.py`

**Step 1: Write test for recording snapshots**

```python
# tests/unit/test_data_quality.py

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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_data_quality.py::test_record_snapshot -v`
Expected: FAIL - method not implemented

**Step 3: Implement record_snapshot method**

```python
# In DataQualityCollector class, add imports at top
import sqlite3
from typing import Any


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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_data_quality.py::test_record_snapshot -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/core/data_quality.py tests/unit/test_data_quality.py
git commit -m "feat(data-quality): implement snapshot recording"
```

---

## Task 4: Implement Baseline Retrieval

**Files:**
- Modify: `scripts/core/data_quality.py`
- Modify: `tests/unit/test_data_quality.py`

**Step 1: Write test for baseline retrieval**

```python
# tests/unit/test_data_quality.py

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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_data_quality.py::test_get_baseline_returns_none_when_no_data -v`
Run: `uv run pytest tests/unit/test_data_quality.py::test_get_baseline_returns_existing_baseline -v`
Expected: FAIL - method not implemented

**Step 3: Implement get_baseline method**

```python
# In DataQualityCollector class

def get_baseline(self, dataset_name: str, stage: str) -> QualityBaseline | None:
    """Get historical baseline for comparison."""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT dataset_name, stage, mean_rows, std_rows, mean_null_pct,
               std_null_pct, sample_count, last_updated
        FROM historical_baselines
        WHERE dataset_name = ? AND stage = ?
    """,
        (dataset_name, stage),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return QualityBaseline(
        dataset_name=row[0],
        stage=row[1],
        mean_rows=row[2],
        std_rows=row[3],
        mean_null_pct=row[4],
        std_null_pct=row[5],
        sample_count=row[6],
        last_updated=row[7],
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_data_quality.py::test_get_baseline -v`
Expected: PASS for both tests

**Step 5: Commit**

```bash
git add scripts/core/data_quality.py tests/unit/test_data_quality.py
git commit -m "feat(data-quality): implement baseline retrieval"
```

---

## Task 5: Implement Baseline Update Logic

**Files:**
- Modify: `scripts/core/data_quality.py`
- Modify: `tests/unit/test_data_quality.py`

**Step 1: Write test for baseline update**

```python
# tests/unit/test_data_quality.py

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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_data_quality.py::test_update_baseline -v`
Expected: FAIL - baseline update not implemented

**Step 3: Implement baseline update in record_snapshot**

```python
# In DataQualityCollector class

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

    # Update baseline using Welford's online algorithm
    self._update_baseline(cursor, snapshot)

    conn.commit()
    conn.close()

    logger.debug(f"Recorded quality snapshot for {snapshot.dataset_name}")


def _update_baseline(
    self, cursor: sqlite3.Cursor, snapshot: QualitySnapshot
) -> None:
    """Update baseline using incremental algorithm (Welford's method)."""
    # Check if baseline exists
    cursor.execute(
        "SELECT mean_rows, std_rows, mean_null_pct, std_null_pct, sample_count "
        "FROM historical_baselines "
        "WHERE dataset_name = ? AND stage = ?",
        (snapshot.dataset_name, snapshot.stage),
    )

    row = cursor.fetchone()

    if row is None:
        # Create new baseline
        cursor.execute(
            """
            INSERT INTO historical_baselines
            (dataset_name, stage, mean_rows, std_rows, mean_null_pct,
             std_null_pct, sample_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                snapshot.dataset_name,
                snapshot.stage,
                float(snapshot.output_rows),
                0.0,  # No variance yet
                snapshot.null_percentage,
                0.0,  # No variance yet
                1,
                snapshot.timestamp,
            ),
        )
    else:
        # Update using Welford's online algorithm
        mean_rows, std_rows, mean_null_pct, std_null_pct, n = row

        # Update mean and std for rows
        n_new = n + 1
        delta = snapshot.output_rows - mean_rows
        mean_rows_new = mean_rows + delta / n_new
        std_rows_new = std_rows * (n - 1) / n + (delta * (snapshot.output_rows - mean_rows_new)) / n

        # Update mean and std for null percentage
        delta_null = snapshot.null_percentage - mean_null_pct
        mean_null_pct_new = mean_null_pct + delta_null / n_new
        std_null_pct_new = (
            std_null_pct * (n - 1) / n
            + (delta_null * (snapshot.null_percentage - mean_null_pct_new)) / n
        )

        # Update database
        cursor.execute(
            """
            UPDATE historical_baselines
            SET mean_rows = ?, std_rows = ?, mean_null_pct = ?,
                std_null_pct = ?, sample_count = ?, last_updated = ?
            WHERE dataset_name = ? AND stage = ?
        """,
            (
                mean_rows_new,
                std_rows_new,
                mean_null_pct_new,
                std_null_pct_new,
                n_new,
                snapshot.timestamp,
                snapshot.dataset_name,
                snapshot.stage,
            ),
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_data_quality.py::test_update_baseline -v`
Expected: PASS for both tests

**Step 5: Commit**

```bash
git add scripts/core/data_quality.py tests/unit/test_data_quality.py
git commit -m "feat(data-quality): implement baseline update with Welford's algorithm"
```

---

## Task 6: Implement Anomaly Detection

**Files:**
- Modify: `scripts/core/data_quality.py`
- Modify: `tests/unit/test_data_quality.py`

**Step 1: Write test for anomaly detection**

```python
# tests/unit/test_data_quality.py

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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_data_quality.py::test_check_anomaly -v`
Expected: FAIL - method not implemented

**Step 3: Implement check_anomaly method**

```python
# In DataQualityCollector class

def check_anomaly(self, snapshot: QualitySnapshot) -> list[str]:
    """Check if metrics deviate >3σ from historical baseline."""
    baseline = self.get_baseline(snapshot.dataset_name, snapshot.stage)

    if baseline is None:
        return []  # First run, no baseline

    anomalies = []

    # Check row count (skip if variance is too low)
    if baseline.std_rows > 1.0:
        z_score = abs(snapshot.output_rows - baseline.mean_rows) / baseline.std_rows
        if z_score > 3:
            anomalies.append(
                f"Row count: {snapshot.output_rows} "
                f"(baseline: {baseline.mean_rows:.0f}±{baseline.std_rows:.0f})"
            )

    # Check null percentage (skip if variance is too low)
    if baseline.std_null_pct > 0.1:
        z_score = abs(snapshot.null_percentage - baseline.mean_null_pct) / baseline.std_null_pct
        if z_score > 3:
            anomalies.append(
                f"Null %: {snapshot.null_percentage:.2f}% "
                f"(baseline: {baseline.mean_null_pct:.2f}±{baseline.std_null_pct:.2f})"
            )

    return anomalies
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_data_quality.py::test_check_anomaly -v`
Expected: PASS for both tests

**Step 5: Commit**

```bash
git add scripts/core/data_quality.py tests/unit/test_data_quality.py
git commit -m "feat(data-quality): implement anomaly detection with 3-sigma thresholds"
```

---

## Task 7: Implement Decorator

**Files:**
- Modify: `scripts/core/data_quality.py`
- Modify: `tests/unit/test_data_quality.py`

**Step 1: Write test for decorator**

```python
# tests/unit/test_data_quality.py

def test_monitor_data_quality_decorator():
    """Test that decorator captures metrics and saves to DB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create a simple function to decorate
        def dummy_save(df, dataset_name, source=None):
            """Dummy save function."""
            return True

        # Apply decorator
        from scripts.core.data_quality import monitor_data_quality

        # Patch the collector's db_path
        import scripts.core.data_quality as dq_module

        original_collector = dq_module._collector
        dq_module._collector = DataQualityCollector(db_path)

        try:
            decorated_save = monitor_data_quality(dummy_save)

            # Call with test data
            df = pd.DataFrame({"a": [1, 2, None], "b": [1, 1, 2]})
            result = decorated_save(df, "test_dataset", source="test")

            assert result is True

            # Verify snapshot was saved
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM run_snapshots WHERE dataset_name = 'test_dataset'")
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[4] == 3  # input_rows
            assert row[6] == 1  # duplicate_count
        finally:
            dq_module._collector = original_collector
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_data_quality.py::test_monitor_data_quality_decorator -v`
Expected: FAIL - decorator not implemented

**Step 3: Implement decorator and logging helper**

```python
# In data_quality.py, add at module level
from functools import wraps

# Global collector instance
_collector = None


def get_collector() -> DataQualityCollector:
    """Get or create global collector instance."""
    global _collector
    if _collector is None:
        _collector = DataQualityCollector()
    return _collector


def monitor_data_quality(func):
    """Decorator for save_parquet to capture quality metrics."""

    @wraps(func)
    def wrapper(df: pd.DataFrame, dataset_name: str, *args, **kwargs):
        # Capture input state
        input_rows = len(df)
        stage = dataset_name.split("_")[0]  # L0, L1, L2...

        # Get source from kwargs
        source = kwargs.get("source", "unknown")

        # Run original save_parquet
        result = func(df, dataset_name, *args, **kwargs)

        # Calculate metrics
        duplicate_count = int(df.duplicated().sum())
        null_pct = round((df.isnull().sum().sum() / df.size) * 100, 2)

        # Create snapshot
        snapshot = QualitySnapshot(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            dataset_name=dataset_name,
            input_rows=input_rows,
            output_rows=len(df),
            duplicate_count=duplicate_count,
            null_percentage=null_pct,
            columns=df.columns.tolist(),
            data_types={col: str(dtype) for col, dtype in df.dtypes.items()},
            source=source,
            stage=stage,
        )

        # Save snapshot
        collector = get_collector()
        collector.record_snapshot(snapshot)

        # Check anomalies and log
        anomalies = collector.check_anomaly(snapshot)
        _log_quality_summary(snapshot, anomalies)

        return result

    return wrapper


def _log_quality_summary(snapshot: QualitySnapshot, anomalies: list[str]) -> None:
    """Log quality summary to terminal."""

    # Calculate data change
    row_change = snapshot.output_rows - snapshot.input_rows
    row_change_pct = (
        (row_change / snapshot.input_rows * 100) if snapshot.input_rows > 0 else 0
    )

    # Base log message
    if anomalies:
        status = "⚠️  ANOMALIES DETECTED"
        level = logger.warning
    else:
        status = "✅ OK"
        level = logger.info

    message = (
        f"Data Quality: {snapshot.dataset_name} | "
        f"{snapshot.output_rows:,} rows "
        f"({row_change:+,} ({row_change_pct:+.1f}%)) | "
        f"{snapshot.duplicate_count} duplicates | "
        f"{snapshot.null_percentage:.2f}% nulls | "
        f"{status}"
    )

    level(message)

    # Log anomalies separately
    for anomaly in anomalies:
        logger.warning(f"  ⚠️  {anomaly}")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_data_quality.py::test_monitor_data_quality_decorator -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/core/data_quality.py tests/unit/test_data_quality.py
git commit -m "feat(data-quality): implement decorator for automatic metric capture"
```

---

## Task 8: Integrate Decorator into data_helpers.py

**Files:**
- Modify: `scripts/core/data_helpers.py`

**Step 1: Read current save_parquet function**

Run: `uv run python -c "from scripts.core.data_helpers import save_parquet; help(save_parquet)"`
Note: Check function signature and current implementation

**Step 2: Apply decorator to save_parquet**

```python
# At top of data_helpers.py, add import
from scripts.core.data_quality import monitor_data_quality

# Apply decorator to save_parquet function
@monitor_data_quality
def save_parquet(
    df: pd.DataFrame,
    dataset_name: str,
    source: str | None = None,
    version: str | None = None,
    mode: str = "overwrite",
    partition_cols: list[str] | None = None,
    compression: str | None = None,
    calculate_checksum: bool = False,
) -> None:
    # Existing implementation unchanged
```

**Step 3: Run existing tests to ensure no breakage**

Run: `uv run pytest tests/unit/test_data_helpers.py -v`
Expected: All existing tests still pass

**Step 4: Write integration test**

```python
# tests/integration/test_data_quality_integration.py

def test_save_parquet_with_quality_monitoring():
    """Test that save_parquet triggers quality monitoring."""
    from scripts.core.data_helpers import save_parquet
    from scripts.core.data_quality import get_collector

    collector = get_collector()
    db_path = collector.db_path

    # Clear existing data for this dataset
    import sqlite3

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
```

**Step 5: Run integration test**

Run: `uv run pytest tests/integration/test_data_quality_integration.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add scripts/core/data_helpers.py tests/integration/test_data_quality_integration.py
git commit -m "feat(data-quality): integrate decorator with save_parquet"
```

---

## Task 9: Create CLI Reporter

**Files:**
- Create: `scripts/utils/data_quality_report.py`
- Create: `tests/unit/test_data_quality_report.py`

**Step 1: Write test for CLI reporter**

```python
# tests/unit/test_data_quality_report.py

import tempfile
from pathlib import Path

from scripts.utils.data_quality_report import generate_summary_report


def test_generate_summary_report():
    """Test generating summary report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create test data
        from scripts.core.data_quality import DataQualityCollector, QualitySnapshot

        collector = DataQualityCollector(db_path)

        # Add some snapshots
        for i in range(5):
            snapshot = QualitySnapshot(
                timestamp=f"2026-03-03 12:0{i}:00",
                dataset_name=f"test_dataset_{i}",
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

        # Generate report
        report = generate_summary_report(db_path, limit=5)

        assert len(report) == 5
        assert "dataset_name" in report[0]
        assert "output_rows" in report[0]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_data_quality_report.py::test_generate_summary_report -v`
Expected: FAIL - reporter not implemented

**Step 3: Implement CLI reporter**

```python
#!/usr/bin/env python3
"""CLI reporter for data quality metrics.

Usage:
    python scripts/utils/data_quality_report.py --summary
    python scripts/utils/data_quality_report.py --dataset L2_housing_unique_searched
    python scripts/utils/data_quality_report.py --anomalies
    python scripts/utils/data_quality_report.py --trend L2_housing_unique_searched 30
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def generate_summary_report(db_path: Path, limit: int = 10) -> list[dict]:
    """Generate summary of recent runs.

    Args:
        db_path: Path to quality_metrics.db
        limit: Number of recent runs to show

    Returns:
        List of run dictionaries
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT timestamp, dataset_name, output_rows, duplicate_count,
               null_percentage, input_rows
        FROM run_snapshots
        ORDER BY timestamp DESC
        LIMIT ?
    """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "timestamp": row[0],
            "dataset_name": row[1],
            "output_rows": row[2],
            "duplicate_count": row[3],
            "null_percentage": row[4],
            "input_rows": row[5],
        }
        for row in rows
    ]


def format_summary_report(report: list[dict]) -> str:
    """Format summary report as table."""
    if not report:
        return "No quality data found."

    lines = []
    lines.append("Recent Data Quality Summary")
    lines.append("=" * 80)
    lines.append(
        f"{'Timestamp':<19} | {'Dataset':<25} | {'Rows':>10} | "
        f"{'Dups':>5} | {'Nulls':>6} | {'Status'}"
    )
    lines.append("-" * 80)

    for row in report:
        # Calculate change
        input_rows = row["input_rows"]
        output_rows = row["output_rows"]
        change = output_rows - input_rows
        change_pct = (change / input_rows * 100) if input_rows > 0 else 0

        # Status
        if row["duplicate_count"] > 0:
            status = f"⚠️  {row['duplicate_count']} duplicates"
        else:
            status = "✅ OK"

        lines.append(
            f"{row['timestamp']:<19} | {row['dataset_name']:<25} | "
            f"{output_rows:>10,} | {row['duplicate_count']:>5} | "
            f"{row['null_percentage']:>5.1f}% | {status}"
        )

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Data quality report CLI")
    parser.add_argument("--summary", action="store_true", help="Show last N runs summary")
    parser.add_argument("--limit", type=int, default=10, help="Number of runs to show")
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to quality_metrics.db (default: data/quality_metrics.db)",
    )

    args = parser.parse_args()

    # Determine DB path
    if args.db_path:
        db_path = Path(args.db_path)
    else:
        from scripts.core.config import Config

        db_path = Config.DATA_DIR / "quality_metrics.db"

    if not db_path.exists():
        print(f"❌ Quality database not found: {db_path}")
        print("Run the pipeline first to generate quality data.")
        return

    if args.summary:
        report = generate_summary_report(db_path, limit=args.limit)
        print(format_summary_report(report))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_data_quality_report.py::test_generate_summary_report -v`
Expected: PASS

**Step 5: Test CLI manually**

Run: `uv run python scripts/utils/data_quality_report.py --summary`
Expected: Table showing recent runs (may be empty if no data yet)

**Step 6: Commit**

```bash
git add scripts/utils/data_quality_report.py tests/unit/test_data_quality_report.py
git commit -m "feat(data-quality): add CLI reporter for quality summaries"
```

---

## Task 10: End-to-End Testing

**Files:**
- Create: `tests/integration/test_data_quality_e2e.py`

**Step 1: Write end-to-end test**

```python
# tests/integration/test_data_quality_e2e.py

def test_full_pipeline_quality_monitoring():
    """Test that full pipeline generates quality data."""
    from scripts.core.data_helpers import save_parquet, load_parquet
    from scripts.core.data_quality import get_collector
    from scripts.utils.data_quality_report import generate_summary_report

    collector = get_collector()
    db_path = collector.db_path

    # Create test data with known issues
    import pandas as pd

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
```

**Step 2: Run end-to-end test**

Run: `uv run pytest tests/integration/test_data_quality_e2e.py -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

**Step 4: Manual verification**

Run: `uv run python scripts/utils/data_quality_report.py --summary --limit 5`
Verify output shows the e2e test data

**Step 5: Commit**

```bash
git add tests/integration/test_data_quality_e2e.py
git commit -m "test(data-quality): add end-to-end integration test"
```

---

## Task 11: Documentation

**Files:**
- Modify: `CLAUDE.md`
- Create: `docs/guides/data-quality-monitoring.md`

**Step 1: Add reference to CLAUDE.md**

Add to "## Project Architecture" section:
```markdown
### Data Quality Monitoring

The pipeline includes automatic data quality monitoring:
- Metrics captured at every `save_parquet()` call
- SQLite storage at `data/quality_metrics.db`
- Adaptive anomaly detection (3σ thresholds)
- CLI reporting: `uv run python scripts/utils/data_quality_report.py --summary`

See `docs/guides/data-quality-monitoring.md` for details.
```

**Step 2: Create usage guide**

```markdown
# Data Quality Monitoring Guide

## Overview

The data quality framework automatically monitors pipeline health by capturing metrics at every data persistence point.

## Viewing Quality Reports

### Quick Summary
```bash
uv run python scripts/utils/data_quality_report.py --summary
```

Output:
```
Recent Data Quality Summary
================================================================================
Timestamp           | Dataset                  | Rows      | Dups | Nulls | Status
2026-03-03 14:23:01 | L2_housing_unique_searched| 17,724   | 0    | 2.3%  | ✅ OK
2026-03-03 14:22:45 | L1_housing_hdb_transaction| 969,748  | 0    | 0.1%  | ✅ OK
```

### Customizing Output
```bash
# Show last 20 runs
uv run python scripts/utils/data_quality_report.py --summary --limit 20
```

## Understanding Metrics

- **Rows**: Number of rows in the dataset
- **Dups**: Number of duplicate rows detected
- **Nulls**: Percentage of null values in the dataset
- **Status**: ✅ OK or ⚠️ ANOMALIES DETECTED

## Anomaly Detection

The system uses adaptive thresholds (3σ) to detect anomalies:
- Significant changes in row count
- Significant changes in null percentage
- Baselines are learned from historical data

Anomalies are logged with WARNING level during pipeline runs.

## Database Schema

Quality data is stored in `data/quality_metrics.db`:
- `run_snapshots`: Individual run records
- `historical_baselines`: Aggregated statistics for anomaly detection

Query directly with SQLite:
```bash
sqlite3 data/quality_metrics.db "SELECT * FROM run_snapshots ORDER BY timestamp DESC LIMIT 5"
```

## Troubleshooting

**No quality data found:**
- Run the pipeline first to generate data
- Check that `data/quality_metrics.db` exists

**Too many anomalies:**
- Normal for first few runs (baseline still learning)
- Check if data source has changed
- Review `EXPECTED_REDUCTIONS` in Config for valid drop rates
```

**Step 3: Commit documentation**

```bash
git add CLAUDE.md docs/guides/data-quality-monitoring.md
git commit -m "docs(data-quality): add usage guide and CLAUDE.md reference"
```

---

## Task 12: Final Verification and Cleanup

**Step 1: Run full test suite**

Run: `uv run pytest tests/ -v --cov=scripts/core/data_quality`
Expected: All tests pass, coverage >80%

**Step 2: Lint and format**

Run: `uv run ruff check scripts/core/data_quality.py scripts/utils/data_quality_report.py`
Run: `uv run ruff format scripts/core/data_quality.py scripts/utils/data_quality_report.py`
Expected: No errors

**Step 3: Verify pipeline integration**

Run a small pipeline stage to ensure decorator works:
```bash
uv run python -c "
from pandas import DataFrame
from scripts.core.data_helpers import save_parquet

df = DataFrame({'a': [1,2,3]})
save_parquet(df, 'final_test', source='test')
"
```

Run: `uv run python scripts/utils/data_quality_report.py --summary | grep final_test`
Expected: Shows the final_test run

**Step 4: Final commit**

```bash
git add .
git commit -m "feat(data-quality): complete MVP implementation

- Decorator on save_parquet for automatic metric capture
- SQLite storage with adaptive thresholds (3σ)
- CLI reporter for quality summaries
- Comprehensive test coverage
- Documentation

Closes design doc: docs/plans/20260303-data-quality-framework-design.md"
```

---

## Success Criteria

- [x] Decorator captures accurate metrics
- [x] SQLite storage works correctly
- [x] Adaptive thresholds detect anomalies
- [x] CLI provides useful reports
- [x] Pipeline runs without performance degradation
- [x] Unit tests achieve >80% coverage
- [x] Integration tests pass
- [x] Documentation complete

---

## Future Enhancements (Out of Scope for MVP)

- Comprehensive statistical profiling (min/max/mean/std per column)
- Load-side decorator for input tracking
- Key-based duplicate detection
- HTML dashboard
- ML-based anomaly detection
- Configurable expected reduction thresholds per stage
