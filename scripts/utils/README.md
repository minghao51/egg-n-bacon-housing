# Utility Scripts

This directory contains utility scripts for validation, checking, and auxiliary tasks.

## Scripts

### `check_geocoding_progress.py`
Monitor and report geocoding progress.

**Features:**
- Check percentage of properties geocoded
- Identify missing or failed geocodes
- Generate progress reports

**Usage:**
```bash
# Check geocoding progress
uv run python scripts/utils/check_geocoding_progress.py
```

**Output:**
- Console report with statistics
- Lists of properties needing geocoding

### `validate_ura_data.py`
Validate URA (Urban Redevelopment Authority) data integrity.

**Features:**
- Check for missing required fields
- Validate data types and ranges
- Identify duplicate records
- Generate validation reports

**Usage:**
```bash
# Validate URA data
uv run python scripts/utils/validate_ura_data.py
```

**Output:**
- Validation report in `data/logs/`
- List of validation failures

### `detect_anomalies.py`
Detect anomalies and outliers in transaction data.

**Features:**
- Statistical outlier detection
- Price anomaly identification
- Geographic outlier detection
- Generate anomaly reports

**Usage:**
```bash
# Detect anomalies
uv run python scripts/utils/detect_anomalies.py
```

**Output:**
- Anomaly report in `data/analytics/`
- Flagged records for review

### `town_leaderboard.py`
Generate town/area rankings and leaderboards.

**Features:**
- Rank towns by various metrics (price, volume, growth)
- Generate leaderboards for different property types
- Create comparison tables

**Usage:**
```bash
# Generate town leaderboard
uv run python scripts/utils/town_leaderboard.py
```

**Output:**
- Leaderboard tables in `data/analytics/`
- CSV exports for reporting

## Common Patterns

### Command-Line Arguments
Utility scripts typically accept command-line arguments:

```python
import argparse

parser = argparse.ArgumentParser(description="Script description")
parser.add_argument('--input', required=True, help='Input file path')
parser.add_argument('--output', help='Output file path')
parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
args = parser.parse_args()
```

**Usage:**
```bash
uv run python scripts/utils/script_name.py --input data.csv --output results.csv --verbose
```

### Logging
All utility scripts use consistent logging:

```python
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/script_name.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

### Configuration
Load configuration from `core/config.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.core.config import Config

# Use configuration
data_dir = Config.DATA_DIR
verbose = Config.VERBOSE_LOGGING
```

## Use Cases

### Data Quality Checks
Run validation scripts before analysis:

```bash
# 1. Check geocoding coverage
uv run python scripts/utils/check_geocoding_progress.py

# 2. Validate URA data
uv run python scripts/utils/validate_ura_data.py

# 3. Detect anomalies
uv run python scripts/utils/detect_anomalies.py
```

### Progress Monitoring
Track pipeline progress:

```bash
# Monitor geocoding (run during pipeline execution)
uv run python scripts/utils/check_geocoding_progress.py
```

### Reporting
Generate summary reports:

```bash
# Create town rankings
uv run python scripts/utils/town_leaderboard.py
```

## Integration with Pipeline

Utility scripts can be integrated into pipeline workflows:

```python
from scripts.utils.check_geocoding_progress import check_progress

def validate_stage():
    """Validate data before proceeding to next stage."""
    progress = check_progress()
    if progress < 0.95:
        raise ValueError(f"Geocoding coverage too low: {progress:.1%}")
```

## Scheduling

Recommended utility script schedules:

| Script | Frequency | Trigger |
|--------|-----------|---------|
| check_geocoding_progress | On-demand | During pipeline runs |
| validate_ura_data | After download | Post data download |
| detect_anomalies | Weekly | Automated QA |
| town_leaderboard | Monthly | Reporting cycle |

## Dependencies

- `pandas` - Data manipulation
- `numpy` - Statistical operations
- `scipy` - Statistical tests
- `logging` - Output management

## Output Locations

Utility scripts save outputs to:
- **Reports**: `data/analytics/`
- **Logs**: `data/logs/`
- **Validation results**: `data/validation/`

## Error Handling

Utility scripts handle errors gracefully:

```python
try:
    result = process_data(data)
except Exception as e:
    logger.error(f"Processing failed: {e}")
    if args.verbose:
        import traceback
        traceback.print_exc()
    sys.exit(1)
```

## Best Practices

1. **Run validation** before major analyses
2. **Check logs** for warnings and errors
3. **Review reports** for data quality issues
4. **Automate checks** in CI/CD pipeline
5. **Document findings** from anomaly detection

## Troubleshooting

### Low Geocoding Coverage
- Check OneMap API quota
- Verify address formats
- Review failed geocodes in logs

### Validation Failures
- Check data source for schema changes
- Verify required columns exist
- Update validation rules if needed

### Anomaly Detection Issues
- Adjust thresholds for your use case
- Review distribution of values
- Consider domain-specific patterns

## Extending Utility Scripts

Add new utility scripts following these patterns:

1. **Place in `scripts/utils/`**
2. **Use argument parser** for CLI interface
3. **Include logging** for operations
4. **Generate reports** for outputs
5. **Update this README** with new script details

## Related Documentation

- [Architecture Documentation](../../docs/architecture.md)
- [Configuration Reference](../../core/config.py)
- [Pipeline Documentation](../pipeline/README.md)
