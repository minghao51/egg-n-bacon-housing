# Coding Conventions

**Analysis Date:** 2026-02-02

## Naming Patterns

**Files:**
- PascalCase for class files (e.g., `Config`, `ValidationError`)
- snake_case for function and variable files
- test_ prefix for test files (e.g., `test_config.py`, `test_data_helpers.py`)
- L0_, L1_, L2_, L3_ prefixes for pipeline stage files

**Functions:**
- snake_case for all functions (e.g., `load_parquet`, `save_parquet`, `validate_coordinates`)
- verb-noun pattern for descriptive names (e.g., `fetch_data_cached`, `apply_unified_filters`)

**Variables:**
- snake_case for all variables
- UPPER_SNAKE_CASE for constants and configuration values
- descriptive names that clearly indicate purpose

**Types:**
- Classes use PascalCase (e.g., `Config`, `ValidationError`)
- Type hints use modern Python syntax (e.g., `str | None`, `list[str]`)
- Optional typing with Union alternatives for older Python versions

## Code Style

**Formatting:**
- Tool: Ruff for linting and formatting
- Line length: 100 characters (configured in pyproject.toml)
- Target Python version: 3.11+
- Quote style: Double quotes for strings

**Linting:**
- Tool: Ruff with configuration in pyproject.toml
- Key rules: ["E", "F", "W", "I", "N", "UP"] (Errors, Pyflakes, Warnings, Isort, Numpy, Pyupgrade)
- Ignored: E501 (line length handled by formatter)
- Per-file ignores: E402 for notebook imports

## Import Organization

**Order:**
1. Standard library imports (e.g., `os`, `sys`, `json`)
2. Third-party imports (e.g., `pandas`, `pytest`, `streamlit`)
3. Local imports (e.g., `from scripts.core.config import Config`)

**Path Aliases:**
- Uses absolute imports from scripts root
- Path manipulation through `pathlib.Path`
- Config-based directory constants (e.g., `Config.BASE_DIR`, `Config.DATA_DIR`)

## Error Handling

**Patterns:**
- Custom exception classes (e.g., `ValidationError`)
- Comprehensive error messages with context
- Graceful degradation for missing data (returns empty DataFrames instead of failing)
- Logging for debugging and monitoring
- Streamlit error handling for user-facing applications

**Validation Patterns:**
- Input validation at function boundaries
- Type checking and NaN handling for data processing
- Coordinate validation for Singapore geographic bounds
- File existence checks before operations

## Logging

**Framework:** Python standard logging
- Configured at module level with `logger = logging.getLogger(__name__)`
- No basicConfig in modules (configured at application level)
- Detailed logging for data operations and debugging

**Patterns:**
- Info messages for successful operations (e.g., "Loaded 1,234 rows")
- Warning messages for recoverable issues
- Error messages with stack traces for debugging
- Structured logging for data lineage tracking

## Comments

**When to Comment:**
- Complex business logic (e.g., coordinate calculations)
- Data processing pipelines with multiple steps
- API integration specifics
- Configuration and setup logic
- Todo items and future improvements

**Documentation:**
- Comprehensive docstrings for all public functions
- Args and Returns sections clearly documented
- Type hints used consistently
- Examples provided for complex functions

## Function Design

**Size:**
- Functions typically 10-50 lines
- Single responsibility principle
- Composition over inheritance for complex operations

**Parameters:**
- Limited number of parameters (prefer < 7)
- Optional parameters with sensible defaults
- Type hints for all parameters
- Keyword arguments where appropriate

**Return Values:**
- Consistent return types
- None for operations that don't return data
- DataFrames for data operations
- Tuple patterns for multiple return values (e.g., (success, message))

## Module Design

**Exports:**
- Clear module-level functions
- Configuration classes with class methods
- Data processing utilities with consistent interfaces
- Error handling utilities for shared functionality

**Barrel Files:**
- `__init__.py` files for package organization
- Explicit imports from submodules
- Version and metadata management in core modules

## Design Patterns

**Configuration Pattern:**
- Centralized `Config` class with path constants
- Environment variable loading with `.env` support
- Validation methods for required settings
- Feature flags and API settings in one place

**Data Processing Pattern:**
- Pipeline stages (L0, L1, L2, L3) with clear separation
- Parquet file format for intermediate data
- Metadata tracking for data lineage
- Caching for expensive operations

**Error Handling Pattern:**
- Custom exceptions for different error types
- Graceful degradation in user-facing code
- Comprehensive logging for debugging
- User-friendly error messages in UI code

---

*Convention analysis: 2026-02-02*
