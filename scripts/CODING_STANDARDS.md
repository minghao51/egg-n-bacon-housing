# Script Migration Guide

This guide shows how to migrate existing scripts to use the new centralized utilities.

## Overview

Two new utility modules have been created to reduce code duplication:

1. **`scripts/core/logging_config.py`** - Centralized logging configuration
2. **`scripts/core/script_base.py`** - Common script patterns and utilities

## Quick Migration Patterns

### Pattern 1: Simple Scripts (Most Common)

**Before:**
```python
import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.config import Config

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Your code here
```

**After:**
```python
import sys
from pathlib import Path

from scripts.core.script_base import setup_script_environment
from scripts.core.logging_config import setup_logging_from_env, get_logger
from scripts.core.config import Config


def main():
    """Main script logic."""
    logger = get_logger(__name__)
    logger.info("Starting script")

    # Your code here


if __name__ == "__main__":
    setup_script_environment()
    setup_logging_from_env()

    try:
        Config.validate()
    except ValueError as e:
        logger = get_logger(__name__)
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    main()
```

### Pattern 2: Scripts with Arguments

**Before:**
```python
import sys
import argparse
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting...")

    # Your code here

if __name__ == "__main__":
    main()
```

**After (Option A - Simple):**
```python
import sys
import argparse
from pathlib import Path

from scripts.core.script_base import setup_script_environment
from scripts.core.logging_config import setup_logging_from_env, get_logger
from scripts.core.config import Config


def main():
    """Main script logic."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    logger = get_logger(__name__)
    logger.info(f"Processing {args.input}")

    # Your code here


if __name__ == "__main__":
    setup_script_environment()
    setup_logging_from_env()

    try:
        Config.validate()
    except ValueError as e:
        logger = get_logger(__name__)
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    main()
```

**After (Option B - Using ScriptBase Class):**
```python
from scripts.core.script_base import ScriptBase


class ProcessDataScript(ScriptBase):
    """Script to process data."""

    def add_arguments(self, parser):
        """Add script-specific arguments."""
        parser.add_argument("--input", required=True, help="Input file")
        parser.add_argument("--output", required=True, help="Output file")

    def run(self, args):
        """Main script logic."""
        logger = self.get_logger()
        logger.info(f"Processing {args.input}")

        # Your code here


if __name__ == "__main__":
    script = ProcessDataScript(
        description="Process data file"
    )
    script.execute()
```

### Pattern 3: Modules/Helper Functions

For modules that don't have `if __name__ == "__main__"`, just use the logger:

```python
from scripts.core.logging_config import get_logger

logger = get_logger(__name__)

def process_data(data):
    """Process data."""
    logger.info("Processing data")
    # Your code here
```

## Benefits of Migration

✅ **Consistency** - All scripts use the same logging format and configuration
✅ **Environment-based control** - Set `LOG_LEVEL` in .env to control verbosity
✅ **Less boilerplate** - Remove repetitive setup code
✅ **Better error handling** - Standardized error handling patterns
✅ **Easier testing** - Centralized setup makes scripts easier to test

## Environment Variables

Add to your `.env` file:

```bash
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

## Examples of Refactored Scripts

See these scripts for examples:
- `scripts/prepare_webapp_data.py` - Simple script pattern
- `scripts/utils/refresh_onemap_token.py` - Script with error handling
- `scripts/run_pipeline.py` - To be updated (complex pipeline orchestration)

## Migration Checklist

- [ ] Replace `sys.path.insert(...)` with `setup_script_environment()`
- [ ] Replace `logging.basicConfig(...)` with `setup_logging_from_env()`
- [ ] Replace `logging.getLogger(__name__)` with `get_logger(__name__)`
- [ ] Add config validation with `Config.validate()`
- [ ] Test script runs correctly after migration
- [ ] Remove unused imports

## Testing After Migration

After migrating a script, test it:

```bash
# Test with default logging
uv run python scripts/your_script.py

# Test with verbose logging
LOG_LEVEL=DEBUG uv run python scripts/your_script.py

# Test with environment variable set
export LOG_LEVEL=DEBUG
uv run python scripts/your_script.py
```

## Questions?

See the module documentation:
- `scripts/core/logging_config.py` - Full logging API
- `scripts/core/script_base.py` - Script base classes and utilities
