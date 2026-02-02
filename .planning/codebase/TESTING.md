# Testing Patterns

**Analysis Date:** 2026-02-02

## Test Framework

**Runner:**
- pytest 7.0.0+
- Config: `pyproject.toml` with test paths and Python files
- Auto-discovery of test files matching `test_*.py`

**Assertion Library:**
- Standard Python assert statements
- No additional assertion libraries required

**Run Commands:**
```bash
uv run pytest              # Run all tests
uv run pytest -v          # Verbose output
uv run pytest --cov=.     # Run with coverage
```

## Test File Organization

**Location:**
- Dedicated `tests/` directory at project root
- Co-located with source code structure

**Naming:**
- All test files prefixed with `test_`
- Follow same naming conventions as source files
- e.g., `test_config.py`, `test_data_helpers.py`

**Structure:**
```
tests/
├── conftest.py           # Test configuration and fixtures
├── test_config.py        # Configuration module tests
├── test_data_helpers.py  # Data processing tests
├── test_pipeline.py      # Pipeline integration tests
├── test_geocoding.py     # Geocoding module tests
└── test_cache.py         # Caching functionality tests
```

## Test Structure

**Suite Organization:**
```python
class TestModuleName:
    """Test class for module functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Fixture providing test data."""
        return pd.DataFrame({'col': [1, 2, 3]})
    
    def test_function_name(self, sample_data):
        """Test specific function."""
        # Arrange
        input_data = sample_data
        
        # Act
        result = target_function(input_data)
        
        # Assert
        assert result is not None
        assert len(result) == 3
```

**Patterns:**
- pytest fixtures for reusable test data
- Test classes organized by module
- Descriptive test names using `test_` prefix
- Arrange-Act-Assert pattern consistently applied
- Type hints used in test function signatures

## Mocking

**Framework:** unittest.mock (built into Python)

**Patterns:**
```python
from unittest.mock import Mock, patch, MagicMock

@patch('module.target_function')
def test_with_mock(self, mock_function):
    """Test with mocked dependency."""
    # Setup mock behavior
    mock_function.return_value = expected_result
    
    # Call function
    result = function_using_mock()
    
    # Verify interactions
    mock_function.assert_called_once_with(expected_args)
    assert result == expected_result
```

**What to Mock:**
- External API calls (OneMap, data.gov.sg)
- File system operations
- Database connections
- Time-dependent functions
- Expensive operations

**What NOT to Mock:**
- Core Python functions and libraries
- Simple utility functions
- Data validation logic
- Business logic that's being tested

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return pd.DataFrame({
        'month': ['2024-01', '2024-02'],
        'town': ['BISHAN', 'ANG MO KIO'],
        'resale_price': [500000, 600000],
        'flat_type': ['4 ROOM', '5 ROOM']
    })

@pytest.fixture
def mock_api_response():
    """Mock API response data."""
    return {
        "result": {
            "records": [{"quarter": "2024-Q1", "value": 100}],
            "total": 1
        }
    }
```

**Location:**
- Fixtures defined in `conftest.py` for shared fixtures
- Module-specific fixtures in individual test files
- Test data factories for complex data structures

## Coverage

**Requirements:** No specific coverage target enforced
- Tests focus on critical functionality
- Integration tests cover main data pipelines
- Unit tests cover edge cases and error conditions

**View Coverage:**
```bash
uv run pytest --cov=. --cov-report=html  # Generate HTML coverage report
uv run pytest --cov=scripts              # Coverage for scripts only
```

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Approach: Mock external dependencies
- Focus: Input/output behavior, edge cases, error handling
- Examples: `test_config_paths()`, `test_save_and_load()`

**Integration Tests:**
- Scope: Multiple modules working together
- Approach: Real data and minimal mocking
- Focus: Data flow, API integrations, file operations
- Examples: `test_full_l0_collection_workflow()`, `test_parallel_geocoding()`

**E2E Tests:**
- Framework: Not explicitly used
- Approach: Manual testing for Streamlit applications
- Focus: User interaction workflows in dashboard

## Common Patterns

**Async Testing:**
- Limited async patterns in codebase
- Synchronous operations for data processing

**Error Testing:**
```python
def test_error_handling():
    """Test error handling scenarios."""
    # Test file not found
    with pytest.raises(FileNotFoundError):
        load_parquet("nonexistent_dataset")
    
    # Test validation error
    with pytest.raises(ValueError):
        save_parquet(pd.DataFrame(), "empty_dataset")
```

**Parameterized Testing:**
```python
@pytest.mark.parametrize("input,expected", [
    ("61 years 04 months", 736),
    ("60 years", 720),
    ("05 months", 5),
    (None, None)
])
def test_lease_conversion(self, input, expected):
    """Test lease conversion with various inputs."""
    result = _convert_lease_to_months(input)
    assert result == expected
```

**API Testing:**
```python
@patch('requests.get')
def test_api_call(self, mock_get):
    """Test external API integration."""
    # Mock response
    mock_response = Mock()
    mock_response.json.return_value = mock_api_data()
    mock_get.return_value = mock_response
    
    # Test API call
    result = fetch_data_from_api()
    
    # Verify
    assert len(result) > 0
    mock_get.assert_called_once()
```

---

*Testing analysis: 2026-02-02*
