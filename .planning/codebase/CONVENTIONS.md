# Code Conventions

## Python

### Linting & Formatting

- **Tool**: Ruff
- **Config**: `pyproject.toml` [tool.ruff]
- Line length: 100
- Target version: py312
- Rules: E, F, W, I, N, UP

### Naming Conventions

- **Files**: snake_case (`data_helpers.py`, `01_ingestion.py` for pipeline stages)
- **Classes**: PascalCase (`PipelineConfig`, `LayerDirs`)
- **Functions/Variables**: snake_case
- **Constants**: SCREAMING_SNAKE_CASE at module level

### Imports

- Standard library first, then third-party, then local
- Local imports: `from egg_n_bacon_housing.config import settings`
- Ruff enforces import sorting (I rule)

### Error Handling

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

```python
from egg_n_bacon_housing.utils.logging_config import get_logger, setup_logging_from_env

logger = get_logger(__name__)
setup_logging_from_env()
```

### Configuration

```python
from egg_n_bacon_housing.config import settings

# Access sub-configs: settings.pipeline, settings.geocoding, settings.metrics
# Access layer dirs: settings.bronze_dir, settings.silver_dir, etc.
```

### Path Management

Use `pathlib.Path` throughout. Config's `base_dir` property returns project root.

### Per-file Ruff Ignores

- `components/*.py`: N999 (numbered stage files like `01_ingestion.py`)
- `analytics/**/*.py`: E402, N806, N803, F401, F821, F841, I001
- `notebooks/*.py`: E402, E722, F821, F841

## TypeScript/Astro

### Type Checking

- Extends `astro/tsconfigs/strict`
- Path aliases: `@/*` → `./src/*`, `@components/*`, `@hooks/*`, `@utils/*`

### Naming

- **Files**: kebab-case (`page-health.ts`)
- **Components**: PascalCase (`.tsx`)
- **Hooks**: camelCase with `use` prefix
- **Types**: PascalCase (`interface SegmentData`)

### Patterns

- Functional components with hooks
- `useCallback`/`useMemo` for performance
- Error state pattern: `{ data, error, loading }` from hooks
