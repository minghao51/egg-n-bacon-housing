# Inject `Settings` at the seam — do not import the global singleton

**Status:** accepted

`Settings` (in `src/egg_n_bacon_housing/config.py`) is currently constructed at import time as a
module global (`settings = get_settings()`) and imported directly by 11 modules — the pipeline
driver, one DAG component, eight `utils/`, and both adapters. We are removing that global import
from every site except the program root (`main.py`), and threading `Settings` (or a narrow
sub-config) through the seam instead: as a Hamilton `inputs` value for DAG nodes, and as a
constructor / function argument for utils and adapters.

The trade-off is verbosity at call sites and a one-time wide refactor (11 modules + their tests)
in exchange for locality — each module's interface declares what it needs, and tests inject a fake
instead of monkeypatching shared global state. `LayerWriter` already follows this shape
(`TrackedWriter(data_dir, settings)`); we are standardising on it.

We considered keeping the global singleton (status quo) and rejected it: it destroys locality,
forces tests to reach past the interface (`test_pipeline.py` mutates private `_get_components._cache`
and `settings.pipeline.use_caching`), and leaves 12 `utils/` modules effectively untestable in
isolation. We sequenced this as the **last** phase (after the geocoding, dead-code, and persistence
work) to minimise churn-on-churn — recorded in
`docs/plans/2026-06-17-architecture-deepening-plan.md`.
