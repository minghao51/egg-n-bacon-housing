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

# Use custom database path
uv run python scripts/utils/data_quality_report.py --summary --db-path /path/to/quality_metrics.db
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
- The first 2 snapshots for a dataset are warm-up runs; alerts start on the 3rd snapshot

Anomalies are logged with WARNING level during pipeline runs.

### Detection Logic

**With variance (std > 0.01)**: Uses z-score (3-sigma rule)
```
z_score = |current_value - mean| / std
if z_score > 3: FLAG AS ANOMALY
```

**Without variance (std ≤ 0.01)**: Uses percentage change
```
if pct_change > 50%: FLAG AS ANOMALY
```

### Warm-up Period

Baseline history is recorded from the first run, but anomaly checks stay silent until at
least 3 snapshots exist for the same `dataset_name` and `stage`. This prevents low-signal
alerts while the baseline is still being established.

## Database Schema

Quality data is stored in `data/quality_metrics.db`:

### run_snapshots Table
Individual run records with:
- timestamp, dataset_name, stage
- input_rows, output_rows, duplicate_count
- null_percentage, column_count, source

### historical_baselines Table
Aggregated statistics for anomaly detection:
- dataset_name, stage (UNIQUE constraint)
- mean_rows, std_rows, mean_null_pct, std_null_pct
- sample_count, last_updated

Query directly with SQLite:
```bash
sqlite3 data/quality_metrics.db "SELECT * FROM run_snapshots ORDER BY timestamp DESC LIMIT 5"
```

## How It Works

### Automatic Metric Capture

The `@monitor_data_quality` decorator wraps `save_parquet()`:
```python
@monitor_data_quality
def save_parquet(df, dataset_name, source=None, ...):
    # Save parquet file
    # Decorator automatically:
    # 1. Captures metrics (rows, duplicates, nulls)
    # 2. Records snapshot to database
    # 3. Updates historical baseline
    # 4. Checks for anomalies
    # 5. Logs quality summary
```

### Welford's Online Algorithm

Baselines are updated incrementally without storing all history:
```python
# For each new snapshot with value x:
n_new = n + 1
delta = x - mean
mean_new = mean + delta / n_new
std_new = std * (n - 1) / n + (delta * (x - mean_new)) / n
```

This provides O(1) space complexity for baseline tracking.

## Troubleshooting

**No quality data found:**
- Run the pipeline first to generate data
- Check that `data/quality_metrics.db` exists
- Verify decorator is applied to save_parquet

**Too many anomalies:**
- After the warm-up period, check if data source has changed
- Review EXPECTED_REDUCTIONS in Config for valid drop rates
- Historical baselines stabilize after ~10 runs

**Duplicate detection not working:**
- Duplicates are detected using pandas `df.duplicated()`
- All columns must match to be considered duplicate
- Check for hidden columns with different values

## Examples

### Check quality during development
```python
from scripts.core.data_helpers import save_parquet
import pandas as pd

df = pd.DataFrame({"a": [1, 2, 3]})
save_parquet(df, "my_dataset", source="test")

# Output:
# Data Quality: my_dataset | 3 rows (+0 (+0.0%)) | 0 duplicates | 0.00% nulls | ✅ OK
```

### View baseline statistics
```python
from scripts.core.data_quality import get_collector

collector = get_collector()
baseline = collector.get_baseline("L2_housing_unique_searched", "L2")
print(f"Mean rows: {baseline.mean_rows:.0f} ± {baseline.std_rows:.0f}")
print(f"Mean nulls: {baseline.mean_null_pct:.2f}% ± {baseline.std_null_pct:.2f}%")
```

### Manually check for anomalies
```python
from scripts.core.data_quality import get_collector, QualitySnapshot
from datetime import datetime

collector = get_collector()

snapshot = QualitySnapshot(
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    dataset_name="my_dataset",
    input_rows=1000,
    output_rows=1000,
    duplicate_count=0,
    null_percentage=2.0,
    columns=["col1", "col2"],
    data_types={"col1": "int64", "col2": "float64"},
    source="test",
    stage="L2",
)

anomalies = collector.check_anomaly(snapshot)
if anomalies:
    print("Anomalies detected:")
    for anomaly in anomalies:
        print(f"  ⚠️  {anomaly}")
```

## Performance Impact

The decorator adds minimal overhead:
- ~1-2ms per save_parquet call
- SQLite writes are fast (<10ms)
- No impact on pipeline throughput

## Future Enhancements

Out of scope for MVP but planned for future:
- Comprehensive statistical profiling (min/max/mean/std per column)
- Load-side decorator for input tracking
- Key-based duplicate detection
- HTML dashboard
- ML-based anomaly detection
- Configurable expected reduction thresholds per stage
