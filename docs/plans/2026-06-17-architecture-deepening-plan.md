# Architecture Deepening Plan

**Created:** 2026-06-17
**Status:** Design — ready for execution
**Baseline:** 188 tests passing, ruff/mypy clean
**Predecessor:** `docs/plans/2026-04-28-code-audit-findings.md` (point-bugs, largely resolved)

## Context

A depth-and-seams review (see the accompanying HTML report) surfaced eight deepening
opportunities. The five **Strong** candidates are designed here. The codebase is mid-migration:
three consolidation modules (`geocoding.py`, `proximity.py`, `layer_writer.py`) were written to
absorb older ones, but the predecessors were never deleted and several callers still reach past the
new seams. This plan finishes those migrations and then removes the global-config coupling that
blocks testability across the rest.

Vocabulary: **module, interface, seam, adapter, depth, locality, leverage.** The **interface is the
test surface** — tests that reach past it are treated as a smell to fix, not preserve.

## Decisions (from grilling)

| #   | Decision                   | Choice                                                                                         |
| --- | -------------------------- | ---------------------------------------------------------------------------------------------- |
| D1  | Execution order            | **Low-risk first:** A (geocoding) → B (dead code + persistence) → C (config + ingestion split) |
| D2  | Bronze error contract      | **Core raises, optional empties** — encoded as a param, not the body                           |
| D3  | Persistence seam scope     | **Parquet-only** — `LayerWriter` owns parquet; JSON export stays separate                      |
| D4  | Macro indicators           | **`MacroIndicator` adapter family** behind `fetch_or_load_macro`                               |
| D5  | Record the config decision | **ADR-0001** (`docs/adr/0001-inject-settings-do-not-import-global.md`)                         |

---

## Phase A — Finish the geocoding migration (candidate 1)

**Lowest risk, highest leverage.** The deep module and both adapters already exist; this phase is
purely rewiring four callers through the existing seam and deleting four bespoke loops.

### Target seam

`utils/geocoding.py` `Geocoder` becomes the real seam (today it has two adapters and zero callers).

- `geocode(addresses: pd.Series) -> pd.DataFrame` — unchanged, already correct.
- `geocode_dataframe(df, address_column) -> pd.DataFrame` — unchanged.
- `OneMapGeocoder.__init__` absorbs the hand-rolled rate limit (`time.sleep(0.3)` in
  `school_features._geocode_schools`) as a constructor param `rate_limit_seconds`, sourced from
  `settings.geocoding.api_delay_seconds`.
- New method on the seam: `query_geocode_cache(address) -> tuple[float, float] | None` — so
  `02_cleaning` stops re-hashing the onemap cache key format (kills the leak across that seam).

### Construction

A factory `build_default_geocoder(settings) -> Geocoder` reads `settings` **once** at the wiring
point. During Phase A it is called from the four sites; in Phase C it moves to the pipeline wiring
and is injected. `InMemoryGeocoder` is the test adapter.

### Wiring (4 call sites)

| Site                                              | Today                                             | After                                                     |
| ------------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------- |
| `01_ingestion._geocode_shopping_malls:535`        | bespoke loop + `setup_onemap_headers`             | `geocoder.geocode_dataframe(malls, "…")`                  |
| `01_ingestion.geocoded_green_mark_buildings:1007` | bespoke loop, bare `except` returns `(None,None)` | `geocoder.geocode_dataframe(...)`                         |
| `02_cleaning._build_geocode_lookup:28`            | recomputes onemap SHA-256 cache key               | `geocoder.query_geocode_cache(...)` + `geocode_dataframe` |
| `school_features._geocode_schools:272`            | raw `requests.get` to `/elastic/search`           | `geocoder.geocode_dataframe(schools, "postal_code")`      |

### Test surface

- New `tests/test_geocoding.py` exercises `geocode_dataframe` through `InMemoryGeocoder` — the
  interface is the test surface.
- `school_features` geocoding is removed entirely; `test_school_features.py` injects an
  `InMemoryGeocoder`.
- Delete any test that reached into a deleted loop's internals.

### Verify

`grep -rn "setup_onemap_headers\|requests.get" src/` returns only the onemap adapter transport.
`uv run pytest --no-cov` green at ≥188.

---

## Phase B — Delete tested-dead modules + collapse persistence (candidates 2 + 3)

One sweep: finish the two half-migrations and make `LayerWriter` the single, real parquet seam.

### B1 — Delete tested-but-dead code

- `utils/mrt_distance.py` — absorbed by `utils/proximity.py` (`proximity.py:3` says so). Delete the
  module. **Re-home** any still-meaningful assertion from `tests/test_mrt_distance.py` into
  `tests/test_proximity.py` against proximity's interface; drop assertions that tested internals
  (e.g. the inline haversine that drifted from `geo.haversine_distance`).
- `utils/data_helpers.py` — replaced by `layer_writer.py`. Zero pipeline callers. Delete the module
  and `tests/test_data_helpers.py`. Confirm the quality-recording capability it carried
  (`@monitor_data_quality`) is alive via `layer_writer.TrackedWriter → record_dataframe_quality`.

> A test with no production caller cannot catch a real bug. Keeping it is false confidence.

### B2 — Consolidate persistence onto `LayerWriter` (parquet-only, D3)

`LayerWriter` is the only persistence module with a real seam — `TrackedWriter` (prod) +
`SimpleWriter` (tests), and `LAYER_PATH_MAP` already covers the `webapp` layer.

- Route every parquet write through `LayerWriter.write(df, name, layer)`:
  - `02_cleaning`, `04_export`, `05_metrics`, `utils/validation_gateway.py` stop calling
    `io_helpers.save_parquet`.
  - `io_helpers.save_parquet` is deleted if it has no remaining callers; otherwise reduced to the
    one narrow case that justifies it.
- `04_export`/`05_metrics` keep their **JSON** export functions as-is (`dashboard_json`,
  `segments_data`) — JSON serialization is a separate concern, not part of the parquet seam (D3).
- Construct the writer once at the wiring point: `build_writer(settings, data_dir) -> LayerWriter`
  → `TrackedWriter`; tests use `SimpleWriter(tmp_path)`.
- Remove the cache-key hashlib coupling from `02_cleaning` (now handled by Phase A's
  `query_geocode_cache`).

### Test surface

- Persistence tests target `LayerWriter.write` with `SimpleWriter` against a `tmp_path` — one
  interface, no real disk policy in the test.
- Delete tests of deleted modules.

### Verify

`grep -rn "save_parquet" src/` shows only `LayerWriter.write`. No `hashlib.sha256` in
`02_cleaning`. `uv run pytest --no-cov` green.

---

## Phase C — Inject `Settings` + split ingestion (candidates 4 + 5)

The wide phase. Done **together** so the ingestion package is built against injected config from
the start rather than retrofitted. Sequenced last to minimise churn-on-churn (D1). See **ADR-0001**.

### C1 — Kill the global `settings` (candidate 4)

- Remove `from egg_n_bacon_housing.config import settings` from every site except `main.py`.
  Affected: `pipeline.py`, `02_cleaning.py`, eight `utils/` modules, both adapters.
- `build_pipeline(settings: Settings, ...)` and `run_pipeline(settings, ...)` take `Settings`
  explicitly (this folds in candidate 8). Every Hamilton `inputs` value is derived from the
  argument, not the global.
- Utils/adapters receive `Settings` (or a narrow sub-config) as a constructor/function arg. Models
  to follow: `TrackedWriter(data_dir, settings)` from Phase B.
- Lazy-init the `CacheManager` singleton to kill its import side-effect (it `mkdir`s on import):
  `get_cache_manager(settings)`, or `@lru_cache`. No module-level instance.
- Thread `02_cleaning`'s geocode node config (`geocode_cache_dir`, `max_workers`) as Hamilton
  `inputs` instead of reading the global — the node's interface stops lying about its dependencies.
- Re-enable mypy on `config.py` (`pyproject.toml` currently sets `ignore_errors = true` for it).

### C2 — Replace string module list (candidate 8, folded in)

`pipeline.py:_STAGE_MODULES` becomes imported module objects:

```python
from .components.ingestion import datagov, geojson, ura_csv, macro
from .components import cleaning_02 as cleaning  # etc.
```

A rename then fails at import time, not runtime, and the ruff `N999` override
(`pyproject.toml:90`) is retired.

### C3 — Split `01_ingestion.py` into a package (candidate 5)

Convert the 1156-line module into `components/ingestion/`:

```
components/ingestion/
├── __init__.py     # aggregates nodes: from .datagov import *; from .geojson import *; …
├── datagov.py      # raw_dataset (deep) + @parameterize variants + _bronze_fetch helper
├── geojson.py      # the 9 GeoJSON named-node wrappers (shallow but mandated by Hamilton)
├── ura_csv.py      # URA CSV loaders + merge
├── macro.py        # MacroIndicator adapter family + fetch_or_load_macro orchestrator
└── transforms.py   # PURE melt/pivot helpers — the test surface for macro
```

Hamilton imports one module (the package's `__init__`) and discovers all nodes in its namespace,
so `pipeline.py`'s module list needs only the package name.

**The deep fetch helper (D2 error contract):**

```python
def _bronze_fetch(bronze_dir, filename, resource_id, *, required, transform=None) -> pd.DataFrame:
    """Cache-or-fetch one datagovsg dataset. required=True raises on empty (core);
    required=False returns empty + warns (optional). Encodes the contract in the param."""
```

The 7 hand-rolled cache-or-fetch blocks collapse onto `_bronze_fetch` / extended `@parameterize`.
`required` is set per node, not buried in the body.

**Macro indicators (D4):**

```python
@dataclass(frozen=True)
class MacroIndicator:
    name: str
    resource_id: str
    frequency: Literal["monthly", "quarterly", "annual"]
    melt: Callable[[pd.DataFrame], pd.DataFrame]   # references pure fns in transforms.py

REGISTRY: dict[str, MacroIndicator] = { "sora": …, "cpi": …, … }  # 9 indicators

def fetch_or_load_macro(name, bronze_dir) -> pd.DataFrame: …   # orchestrator
```

The 8 bare `except Exception` branches in today's `raw_macro_data` become one `required=False`
path in `_bronze_fetch`. Pure melt/pivot functions move to `transforms.py` and become testable
without the network.

### Test surface

- `transforms.py` gets pure-function tests (no files, no network) — the macro logic finally has a
  test surface.
- `test_pipeline.py` stops monkeypatching private `_get_components._cache` and
  `settings.pipeline.use_caching`; it injects a fake `Settings` / `SimpleWriter`.
- Existing component tests (test_ingestion, test_export, …) run unchanged against the package's
  `__init__` namespace — the DAG node names don't move.
- The 12 currently-untested `utils/` modules become testable in isolation once config is injected;
  add interface-level tests for `cache`, `data_quality`, `proximity`, `io_helpers`/`layer_writer`
  first (highest leverage).

### Verify

`grep -rn "from egg_n_bacon_housing.config import settings" src/` returns only `main.py`.
`uv run python main.py --stage all` completes (integration smoke). `uv run ruff check . &&
uv run pytest --no-cov` green. `mypy` runs on `config.py` with no `ignore_errors`.

---

## Out of scope (Worth-exploring candidates — separate plans)

- **6** — Extract pure school-quality scorers from `school_features.py` (772 lines). Depends on
  Phase A (geocoding leaves the file) and Phase C (config injected); tackle after C as its own
  pass.
- **7** — Put `onemap`/`datagovsg` behind one retry/cache port. Touches both adapters; natural
  follow-up to C1.

## Risk

Phase C is the only wide-blast-radius work. Mitigations: (a) C1 and C3 land together so the
ingestion package is born injected; (b) run `pytest --no-cov` after each task; (c) the
`--stage all` integration smoke after C3. Phases A and B are independently shippable and can be
reviewed/merged before C begins.
