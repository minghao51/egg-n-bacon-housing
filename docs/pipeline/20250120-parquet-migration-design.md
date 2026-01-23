# Parquet Migration & Project Improvements Design

**Date**: 2025-01-20
**Status**: Approved
**Author**: Generated via brainstorming session

## Overview

Migrate from DVC + S3 to local parquet files with git-friendly metadata tracking, plus comprehensive project improvements prioritized by impact.

## Motivation

- **Performance**: Local parquet access is faster than DVC+S3
- **Simplicity**: Remove AWS/S3 dependency for local development
- **Data size**: Small (GB range) makes local storage practical
- **Update frequency**: Infrequent (weekly/monthly) reduces need for complex versioning

---

## Part 1: Parquet Migration Design

### 1.1 Directory Structure

```
data/
├── parquets/                    # All parquet files (gitignored)
│   ├── raw_data/
│   │   └── raw_data.parquet
│   ├── L1/
│   │   ├── ura_transactions.parquet
│   │   └── utilities.parquet
│   ├── L2/
│   │   └── sales_facilities.parquet
│   └── L3/
│       └── final_dataset.parquet
├── metadata.json                # Git-tracked data registry
└── raw_documents/               # Existing markdown docs (unchanged)
```

### 1.2 Metadata Structure

`data/metadata.json` tracks all datasets:

```json
{
  "last_updated": "2025-01-20T10:30:00Z",
  "datasets": {
    "raw_data": {
      "path": "parquets/raw_data/raw_data.parquet",
      "version": "2025-01-20",
      "rows": 15000,
      "created": "2025-01-20T10:00:00Z",
      "source": "data.gov.sg API",
      "checksum": "abc123...",
      "mode": "overwrite"
    },
    "L1_ura_transactions": {
      "path": "parquets/L1/ura_transactions.parquet",
      "version": "2025-01-20",
      "rows": 12500,
      "created": "2025-01-20T10:15:00Z",
      "source": "raw_data",
      "checksum": "def456...",
      "mode": "overwrite"
    }
  }
}
```

**Benefits**:
- **Reproducibility**: Track when data was created and source
- **Lineage**: See dataset dependencies
- **Verification**: Checksums detect accidental changes
- **Git-friendly**: Small JSON file committed to git

### 1.3 Helper Functions

**New file: `src/data_helpers.py`**

Key functions:
- `load_parquet(dataset_name, version=None)` - Load dataset
- `save_parquet(df, dataset_name, source, version, mode)` - Save with overwrite/append
- `list_datasets()` - List all datasets
- `verify_metadata()` - Validate all checksums

**Features**:
- Simple, consistent API
- Automatic metadata tracking
- Overwrite and append modes
- Comprehensive error handling
- Logging for visibility

### 1.4 Notebook Migration

**Migration order** (incremental to avoid breaks):
1. Create `src/data_helpers.py`
2. Migrate L0 notebooks to SAVE to parquet
3. Migrate L1 notebooks to READ/WRITE parquet
4. Migrate L2 notebooks
5. Migrate L3 notebooks
6. Remove old CSV references and `.dvc` files

**Example transformation**:

```python
# Before
df = pd.read_csv("data/raw_data/file.csv")
processed = process(df)
processed.to_csv("data/L1/output.csv")

# After
from src.data_helpers import load_parquet, save_parquet

df = load_parquet("raw_data")
processed = process(df)
save_parquet(processed, "L1_ura_transactions", source="raw_data")
```

### 1.5 DVC Cleanup

**Remove**:
- `.dvc/` directory
- `.dvcignore` file
- All `data/*.dvc` files
- `dvc` and `dvc-s3` from dependencies

**Update `.gitignore`**:
```
/data/parquets/
/data/*.parquet
```

**Commit**:
```bash
git add .gitignore environment.yml
git rm -r .dvc .dvcignore data/*.dvc
git commit -m "Remove DVC, migrate to parquet + metadata"
```

---

## Part 2: Project Improvements (Prioritized)

### Priority: HIGH

#### 2.1 Migrate to uv + pyproject.toml

**Why**: Much faster than conda/pip, modern standard

**Actions**:
1. Install uv
2. Create `pyproject.toml` with all dependencies
3. Migrate from `environment.yml`
4. Update CLAUDE.md to use `uv run` commands

**Dependencies to migrate**:
```toml
[project]
name = "egg-n-bacon-housing"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "seaborn",
    "scikit-learn",
    "python-dotenv",
    "geopandas",
    "requests",
    "ipywidgets",
    "langchain>=0.3.0",
    "langchain-google-genai==2.0.0",
    "langchain-experimental==0.3.0",
    "langgraph==0.2.32",
    "langgraph-checkpoint==2.0.0",
    "langchain-community",
    "beautifulsoup4",
    "h3==4.1.0b2",
    "boto3",
    "streamlit",
    "pygwalker",
    "supabase",
    "tabulate==0.9.0",
]

[tool.uv]
dev-dependencies = [
    "jupyter>=1.0.0",
    "ipykernel>=6.0.0",
    "pytest>=7.0.0",
    "ruff>=0.1.0",
]
```

#### 2.2 Centralized Configuration

**Create `src/config.py`**:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    PARQUETS_DIR = DATA_DIR / "parquets"

    # API Keys
    ONEMAP_EMAIL = os.getenv("ONEMAP_EMAIL")
    ONEMAP_PASSWORD = os.getenv("ONEMAP_EMAIL_PASSWORD")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # Feature flags
    USE_CACHING = True
    LOG_LEVEL = "INFO"

    @classmethod
    def validate(cls):
        """Validate required config is present."""
        required = ["ONEMAP_EMAIL", "GOOGLE_API_KEY"]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"Missing required config: {missing}")
```

**Benefits**:
- Single source of truth for configuration
- Validation prevents runtime errors
- Easy to test with different configs

### Priority: MEDIUM

#### 2.3 Restructure src/ Directory

**Current structure**:
```
src/
└── agent/
    └── general_agent.py
```

**Target structure**:
```
src/
├── __init__.py
├── config.py                      # NEW: centralized config
├── data_helpers.py                # NEW: parquet management
├── agent/
│   └── general_agent.py
└── pipeline/                      # NEW: extracted pipeline logic
    ├── __init__.py
    ├── L0_collect.py
    ├── L1_process.py
    ├── L2_features.py
    └── L3_export.py
```

**Benefits**:
- Clear separation of concerns
- Reusable pipeline functions
- Easier to test

#### 2.4 Add Basic Tests

**Create `tests/` directory**:

```python
# tests/test_data_helpers.py
import pytest
from src.data_helpers import save_parquet, load_parquet
import pandas as pd

def test_save_and_load():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    save_parquet(df, "test_dataset", source="test")

    loaded = load_parquet("test_dataset")
    assert loaded.equals(df)

def test_metadata_tracking():
    from src.data_helpers import list_datasets
    datasets = list_datasets()
    assert "test_dataset" in datasets
```

**Add to `pyproject.toml`**:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Run tests**:
```bash
uv run pytest
uv run ruff check .
```

### Priority: LOW

#### 2.5 Refactor Notebooks to Scripts

**Extract stable pipeline logic** from notebooks to `src/pipeline/*.py`:
- L0 notebooks → `pipeline/L0_collect.py`
- L1 notebooks → `pipeline/L1_process.py`
- L2 notebooks → `pipeline/L2_features.py`
- L3 notebooks → `pipeline/L3_export.py`

**Notebooks become**:
- Visualization tools
- Debugging/inspection tools
- Exploratory analysis

**Benefits**:
- Version control for pipeline code
- Easier to test
- Can run via CLI or scripts

#### 2.6 Consolidate Streamlit Apps

**Current**:
```
apps/
├── single_agent.py
├── single_agent2.py
├── spiral.py
├── spiral3.py
streamlit_app.py (at root)
```

**Target**:
```
apps/
└── streamlit/
    ├── main.py              # Multi-page app
    ├── pages/
    │   ├── 1_Data_Explorer.py
    │   ├── 2_Property_Analysis.py
    │   └── 3_Agent_Chat.py
    └── components/
        ├── charts.py
        └── data_loader.py
```

**Benefits**:
- Multi-page Streamlit app
- Reusable components
- Organized by feature

#### 2.7 Comprehensive Documentation

**Create documentation structure**:
```
docs/
├── architecture.md           # System architecture
├── data_pipeline.md          # How data flows
├── migration_guide.md        # This document
└── api_reference.md          # API documentation
```

**Update README.md**:
- Quick start (5 min setup)
- Project structure overview
- How to run the pipeline
- Common issues/troubleshooting

---

## Implementation Plan

### Phase 1: Parquet Migration (Week 1)
1. ✅ Design complete (this document)
2. Create `src/data_helpers.py`
3. Update `.gitignore`
4. Migrate L0 notebooks
5. Migrate L1 notebooks
6. Migrate L2 notebooks
7. Migrate L3 notebooks
8. Remove DVC files and configs
9. Test full pipeline

### Phase 2: High Priority Improvements (Week 2)
1. Install uv, create `pyproject.toml`
2. Migrate all dependencies
3. Create `src/config.py`
4. Update code to use Config
5. Test everything still works

### Phase 3: Medium Priority (Week 3)
1. Restructure `src/` directory
2. Create `src/pipeline/` structure
3. Add basic tests
4. Setup ruff linting
5. Run tests in CI/CD

### Phase 4: Low Priority (Ongoing)
1. Extract notebook logic to scripts
2. Consolidate Streamlit apps
3. Write comprehensive docs
4. Add more tests

---

## Success Criteria

- [ ] All data stored in local parquet files
- [ ] No DVC/S3 dependencies remaining
- [ ] `metadata.json` tracks all datasets
- [ ] Full pipeline (L0→L3) runs successfully
- [ ] All dependencies managed via uv
- [ ] Centralized configuration working
- [ ] Basic tests passing
- [ ] Documentation updated

---

## Risks & Mitigations

**Risk**: Breaking existing pipeline during migration
**Mitigation**: Incremental migration, keep CSV reads until all parquet writes complete

**Risk**: Data loss during DVC removal
**Mitigation**: Keep S3 backup initially, verify parquet files before deleting

**Risk**: Team not familiar with uv
**Mitigation**: Update documentation, provide quick start guide

---

## Next Steps

1. **Get approval** on this design document
2. **Create implementation branch**: `git checkout -b feature/parquet-migration`
3. **Start Phase 1**: Create `data_helpers.py` and begin notebook migration
4. **Test incrementally**: Run pipeline after each notebook migration
5. **Merge to main** once all phases complete and tests pass

---

**Questions?** Refer to:
- CLAUDE.md for development principles
- This document for design decisions
- GitHub issues for tracking progress
