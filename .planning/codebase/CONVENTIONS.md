# Code Conventions

## Python (Backend/Data Pipeline)

### Linting & Formatting

- **Tool**: Ruff
- **Config**: `pyproject.toml` [lines 64-80]
  ```toml
  [tool.ruff]
  line-length = 100
  target-version = "py311"
  
  [tool.ruff.lint]
  select = ["E", "F", "W", "I", "N", "UP"]
  ignore = ["E501"]  # Line length handled by formatter
  ```
- **CI runs**: `ruff format --check` and `ruff check` on push to main/develop

### Naming Conventions

- **Files**: snake_case (`L0_collect.py`, `test_utils.py`)
- **Classes**: PascalCase (`Config`, `CSVLoader`)
- **Functions/Variables**: snake_case
- **Constants**: SCREAMING_SNAKE_CASE for module-level constants
- **Type aliases**: PascalCase (e.g., `PriceTier`, `RiskLevel`)

### Error Handling

- Use try/except with specific exception types when possible
- Pattern: `except Exception as e:` with logging
- Re-raise exceptions after logging when appropriate
- Use `raise ValueError(...)` or `raise Exception(...)` for validation failures

```python
try:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
except requests.HTTPError as e:
    logger.error(f"HTTP error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### Logging

- Use centralized logging from `scripts.core.logging_config`
- Get logger per module: `logger = logging.getLogger(__name__)`
- Setup root logging in main scripts: `setup_logging(level=logging.INFO)`
- Log levels: DEBUG for detail, INFO for progress, WARNING for recoverable, ERROR for failures

```python
from scripts.core.logging_config import get_logger, setup_logging

logger = get_logger(__name__)
setup_logging(level=logging.INFO)
```

### Code Patterns

**Path management**:
```python
from scripts.core.utils import add_project_to_path
add_project_to_path(Path(__file__))
```

**Configuration**:
```python
from scripts.core.config import Config
# Use Config.DATA_DIR, Config.PIPELINE_DIR, etc.
```

**Type hints**: Use for function signatures
```python
def fetch_datagovsg_dataset(url: str, dataset_id: str, use_cache: bool = True) -> pd.DataFrame:
```

### Per-file Ignores

Notebooks and certain files have specific ignores in ruff:
- `notebooks/*.py`: E402, E722, F821, F841
- `scripts/core/stages/*.py`: N999 (allow non-compliant stage file names)

---

## TypeScript/Astro (Frontend)

### Type Checking

- **Config**: `astro/tsconfigs/strict` extended
- **Path aliases** in `tsconfig.json`:
  ```json
  {
    "@/*": ["./src/*"],
    "@components/*": ["./src/components/*"],
    "@hooks/*": ["./src/hooks/*"],
    "@utils/*": ["./src/utils/*"]
  }
  ```

### Naming Conventions

- **Files**: kebab-case (`page-health.ts`, `use-gzip-json.ts`)
- **Components**: PascalCase (`.tsx` files)
- **Hooks**: camelCase with `use` prefix (`useGzipJson.ts`, `useFilterState.ts`)
- **Utilities/Constants**: camelCase

### Type Exports

- Export types alongside implementations
- Use `export type` for type-only exports when appropriate

```typescript
export interface TableData { ... }
export function extractTables(markdown: string): TableData[] { ... }
```

### React Patterns

- Use functional components with hooks
- Prefer `useCallback` and `useMemo` for performance
- Use `clsx` or `tailwind-merge` for className composition

### Error Handling

- Use error state in hooks: `error: string | null`
- Clear errors on successful load
- Log errors to console for debugging

```typescript
const [error, setError] = useState<string | null>(null);
// ...
if (err instanceof Error) {
  if (err.name === 'AbortError') return;
  setError(err.message);
} else {
  setError('Failed to load data');
}
```

---

## Shared Patterns

### Data Processing

- Use pandas DataFrames for tabular data
- Use pathlib for path operations
- Parquet compression: snappy (default)

### API Calls

- Use requests for Python HTTP calls
- Implement retry logic with tenacity
- Cache API responses where appropriate
