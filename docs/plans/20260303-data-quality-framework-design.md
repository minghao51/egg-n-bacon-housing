# Data Quality Framework Design

**Date:** 2026-03-03
**Author:** Data Quality Brainstorming Session
**Status:** Approved

## Overview

A data quality monitoring system that provides **comprehensive visibility** into data changes through the ETL pipeline using **decorators**, **SQLite storage**, and **adaptive thresholds**.

### Problem Statement

The current pipeline (L0 → L1 → L2 → L3 → L4 → L5) has limited visibility into:
- Records being silently dropped during transformations (e.g., geocoding filters)
- Duplicate records being introduced (e.g., concat operations, spatial joins)
- Data quality degradation over time

### Solution

A non-intrusive decorator-based framework that:
- **Automatically captures** quality metrics at every data persistence point
- **Tracks historical baselines** for adaptive anomaly detection
- **Never breaks the pipeline** - failures are logged, data is still saved
- **Provides visibility** through CLI reports and direct SQLite access

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Quality Framework                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │ @monitor_data    │         │ DataQuality      │          │
│  │ _quality         │────────▶│ Collector         │          │
│  │ (decorator)      │         │                  │          │
│  └──────────────────┘         └────────┬─────────┘          │
│                                       │                      │
│                                       ▼                      │
│                              ┌─────────────────┐            │
│                              │ quality_metrics  │            │
│                              │ .db (SQLite)     │            │
│                              └─────────────────┘            │
│                                       │                      │
│                                       ▼                      │
│                              ┌─────────────────┐            │
│                              │ CLI Reporter     │            │
│                              │ (for viewing)    │            │
│                              └─────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
save_parquet(df, "L2_housing_...", source="...")
         │
         ▼
@monitor_data_quality captures:
  - input_rows, output_rows
  - duplicate_count
  - null_percentage
  - column_schema, data_types
  - timestamp, dataset_name, stage
         │
         ▼
SQLite INSERT → update baseline
         │
         ▼
Check anomalies (>3σ from baseline)
         │
         ▼
Log summary to terminal (continue pipeline)
```

---

## Core Components

### 1. Data Structures

**File:** `scripts/core/data_quality.py`

```python
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
    stage: str  # L0, L1, L2, etc.

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
    """Main quality monitoring class."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def record_snapshot(self, snapshot: QualitySnapshot) -> None:
        """Save snapshot and update baseline."""

    def get_baseline(self, dataset_name: str, stage: str) -> QualityBaseline | None:
        """Get historical baseline for comparison."""

    def check_anomaly(self, snapshot: QualitySnapshot) -> list[str]:
        """Return list of anomalies (>3σ from baseline)."""
```

### 2. Decorator Pattern

```python
def monitor_data_quality(func):
    """Decorator for save_parquet to capture quality metrics."""
    @wraps(func)
    def wrapper(df, dataset_name, *args, **kwargs):
        # Capture input state
        input_rows = len(df)
        stage = dataset_name.split('_')[0]  # L0, L1, L2...

        # Run original save_parquet
        result = func(df, dataset_name, *args, **kwargs)

        # Calculate metrics
        duplicate_count = df.duplicated().sum()
        null_pct = (df.isnull().sum().sum() / df.size) * 100

        # Create snapshot and save
        snapshot = QualitySnapshot(...)
        collector.record_snapshot(snapshot)

        # Check anomalies and log
        anomalies = collector.check_anomaly(snapshot)
        _log_quality_summary(snapshot, anomalies)

        return result
    return wrapper
```

### 3. Integration

**Single-line change to `data_helpers.py`:**
```python
from scripts.core.data_quality import monitor_data_quality

@monitor_data_quality
def save_parquet(df, dataset_name, ...):
    # Existing implementation unchanged
```

---

## SQLite Schema

### Tables

```sql
-- run_snapshots: One row per save_parquet() call
CREATE TABLE run_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    stage TEXT NOT NULL,
    input_rows INTEGER NOT NULL,
    output_rows INTEGER NOT NULL,
    duplicate_count INTEGER NOT NULL,
    null_percentage REAL NOT NULL,
    column_count INTEGER NOT NULL,
    source TEXT,
    INDEX idx_dataset_stage (dataset_name, stage),
    INDEX idx_timestamp (timestamp)
);

-- historical_baselines: Aggregated stats for adaptive thresholds
CREATE TABLE historical_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_name TEXT NOT NULL UNIQUE,
    stage TEXT NOT NULL,
    mean_rows REAL NOT NULL,
    std_rows REAL NOT NULL,
    mean_null_pct REAL NOT NULL,
    std_null_pct REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    last_updated TEXT NOT NULL,
    UNIQUE(dataset_name, stage)
);
```

### Adaptive Threshold Logic

```python
def check_anomaly(self, snapshot: QualitySnapshot) -> list[str]:
    """Check if metrics deviate >3σ from historical baseline."""
    baseline = self.get_baseline(snapshot.dataset_name, snapshot.stage)
    if not baseline:
        return []  # First run, no baseline

    anomalies = []

    # Check row count
    if baseline.std_rows > 0:
        z_score = abs(snapshot.output_rows - baseline.mean_rows) / baseline.std_rows
        if z_score > 3:
            anomalies.append(f"Row count: {snapshot.output_rows} (baseline: {baseline.mean_rows:.0f}±{baseline.std_rows:.0f})")

    # Check null percentage
    if baseline.std_null_pct > 0:
        z_score = abs(snapshot.null_percentage - baseline.mean_null_pct) / baseline.std_null_pct
        if z_score > 3:
            anomalies.append(f"Null %: {snapshot.null_percentage:.2f}% (baseline: {baseline.mean_null_pct:.2f}±{baseline.std_null_pct:.2f})")

    return anomalies
```

### Baseline Update (Online Algorithm)

```python
def _update_baseline(self, snapshot: QualitySnapshot) -> None:
    """Update baseline using incremental algorithm (Welford's method)."""
    # New mean = old mean + (new_value - old_mean) / n
    # New variance = old_var * (n-1)/n + (new_value - new_mean)^2 / n
    # This allows incremental updates without storing all history
```

---

## Error Handling & Edge Cases

### 1. First Run (No Baseline)
- Returns `None` from `get_baseline()`
- No anomalies possible on first run
- Baseline created after first snapshot

### 2. Low Variance (std ≈ 0)
- If `std_rows < 1`, skip anomaly check
- Log: "Skipping row check - low variance"

### 3. Expected Data Loss
Certain pipeline stages are expected to drop records:
```python
# In Config class
EXPECTED_REDUCTIONS = {
    "L2_housing_unique_searched": 0.95,  # Expected to keep 95% of L1
    "L3_property": 0.80,                 # Expected to keep 80% of L2
}
```
These use a **5σ threshold** instead of 3σ for anomaly detection.

### 4. Decorator Failures Never Break Pipeline
```python
try:
    collector.record_snapshot(snapshot)
except Exception as e:
    logger.warning(f"Quality monitoring failed: {e}")
    # Continue - don't break save_parquet()
```

---

## CLI Reporter

**File:** `scripts/utils/data_quality_report.py`

### Usage

```bash
# Quick summary of last 10 runs
uv run python scripts/utils/data_quality_report.py --summary

# Check specific dataset history
uv run python scripts/utils/data_quality_report.py --dataset L2_housing_unique_searched

# Show only anomalous runs
uv run python scripts/utils/data_quality_report.py --anomalies

# 30-day trend for a dataset
uv run python scripts/utils/data_quality_report.py --trend L2_housing_unique_searched 30
```

### Sample Output

```bash
$ uv run python scripts/utils/data_quality_report.py --summary

Recent Data Quality Summary
============================
Timestamp           | Dataset                  | Rows    | Dups | Nulls | Status
2026-03-03 14:23:01 | L2_housing_unique_searched| 17,724  | 0    | 2.3%  | ✅ OK
2026-03-03 14:22:45 | L1_housing_hdb_transaction| 969,748 | 0    | 0.1%  | ✅ OK
2026-03-03 14:22:30 | L1_housing_condo_transaction| 110,089| 12   | 1.8%  | ⚠️  12 duplicates
2026-03-03 14:22:15 | L0_hdb_resale            | 969,748 | 0    | 0.0%  | ✅ OK
```

---

## Implementation Plan (MVP)

### Files to Create

```
scripts/core/
├── data_quality.py          # Core quality monitoring framework
├── __init__.py              # Export DataQualityCollector

scripts/utils/
├── data_quality_report.py   # CLI reporter

tests/unit/
├── test_data_quality.py     # Unit tests

data/
├── quality_metrics.db       # SQLite DB (auto-created)
```

### Steps

1. **Create `data_quality.py`**
   - Implement `QualitySnapshot`, `QualityBaseline` dataclasses
   - Implement `DataQualityCollector` class
   - Implement `@monitor_data_quality` decorator
   - Add unit tests

2. **Modify `data_helpers.py`**
   - Import decorator
   - Apply to `save_parquet()` function (1-line change)
   - No other code changes needed

3. **Create CLI reporter**
   - Implement `data_quality_report.py`
   - Add arguments: `--summary`, `--dataset`, `--anomalies`, `--trend`

4. **Integration testing**
   - Run full pipeline
   - Verify SQLite populated
   - Check CLI output

### Testing

```python
def test_decorator_captures_metrics():
    df = pd.DataFrame({"a": [1, 2, None], "b": [1, 1, 2]})
    # Call decorated save_parquet
    # Verify snapshot in SQLite
    # Assert duplicate_count = 1, null_pct = 8.33%

def test_adaptive_thresholds():
    # Insert 100 normal snapshots
    # Insert 1 anomalous snapshot (10σ from mean)
    # Verify anomaly detected
```

---

## Future Extensions (Architected For)

The framework is designed to support these features with minimal changes:

### Comprehensive Profiling
- Statistical metrics: min/max/mean/std for each column
- Value range validation
- Distribution shift detection (KL divergence)

### Load-Side Monitoring
- Decorator on `load_parquet()` for input tracking
- Full input→output lineage per stage

### Key-Based Duplicate Detection
- Configurable key columns per dataset
- Fuzzy matching for near-duplicates

### HTML Dashboard
- Web interface for visual exploration
- Real-time anomaly alerts

### ML-Based Anomaly Detection
- Isolation Forest for multivariate outliers
- Time-series forecasting for trend prediction

---

## Success Criteria

- [x] Design approved by stakeholders
- [ ] Decorator captures accurate metrics
- [ ] SQLite storage works correctly
- [ ] Adaptive thresholds detect anomalies
- [ ] CLI provides useful reports
- [ ] Pipeline runs without performance degradation (<5% overhead)
- [ ] Unit tests achieve >80% coverage
- [ ] Documentation complete

---

## References

- Current codebase: `/scripts/core/data_helpers.py`
- Existing validation: `/scripts/utils/validate_ura_data.py`
- Pipeline stages: `/scripts/core/stages/`
