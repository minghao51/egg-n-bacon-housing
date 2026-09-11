# WS6 — Cache + Adapter Hygiene (Batch 1)

## Context

Confirmed issues across the cache layer and adapters:

- `utils/cache.py`: versionless keys; non-atomic writes (crash → permanently corrupt entry that reads as miss forever); expired entries never unlinked; json↔parquet sibling shadowing; `cached_call` silently no-ops when unconfigured (:230-233) while `get_cache_manager` raises (:212); `allow_legacy_pickle_cache` is a read-side no-op (flag admits `.pkl` paths at :83-87 but `get()` (:124-127) never loads pickle).
- `adapters/ura.py:50`: token cached under fixed key `ura_api_token` regardless of access key → key rotation serves a wrong-key token.
- `adapters/onemap.py` + `adapters/datagovsg.py`: bare `requests.get` per call → fresh TLS handshake per geocode call (geocoder runs 5 threads).
- `adapters/onemap.py:57`: `ONEMAP_TOKEN` read via `os.environ`, bypassing `Settings` (all other credentials are SecretStr fields).
- `adapters/onemap.py:186`: missing `results` key leaks raw `KeyError`.
- Test gaps: 413 page-shrink path (`datagovsg.py:216-232`), corrupt-JWT-payload decode path.

## Read first

- `.agents/skills/change-data-ingestion/SKILL.md` (mandatory — transport/retry/caching conventions live there)

## Decisions locked (D7a + judgment calls)

- Versioning = caller-embedded version in cache identifiers, as a GO-FORWARD convention (documented in cache.py docstring). Do NOT rename existing identifiers (mass invalidation without behavioral change is not justified). The ONE key that changes is the URA token key (fix below).
- Sessions: `threading.local()` session in `onemap.py` (geocoder uses ThreadPoolExecutor — a shared module Session is not thread-safe); plain module-level `_SESSION` in `datagovsg.py` (single-threaded node calls).
- `allow_legacy_pickle_cache`: remove the flag + the pkl branch entirely (it never worked on read). Removing the `config.py` field is in-scope (owned).

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/utils/cache.py`
- `src/egg_n_bacon_housing/adapters/onemap.py`
- `src/egg_n_bacon_housing/adapters/ura.py`
- `src/egg_n_bacon_housing/adapters/datagovsg.py`
- `src/egg_n_bacon_housing/config.py`
- `tests/test_cache.py`, `tests/test_onemap.py`, `tests/test_ura.py`, `tests/test_datagovsg.py` (extend)

## Forbidden

Everything else, incl. `utils/geocoding.py`, `pipeline.py`, `components/*`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. `utils/cache.py`

- Atomic writes (:131-146): write to `path.with_name(path.name + ".tmp")` then `os.replace`.
- `set()`: unlink the sibling-format path (json↔parquet) for the same key to prevent stale shadowing.
- `get()` on expiry (:106-108): best-effort `unlink` (swallow `OSError`).
- `cached_call` unconfigured (:230-233): `logger.warning` once per process (module flag) that caching is disabled, then execute uncached.
- Docstring: document the versioning convention (e.g. `cached_call("datagovsg:v2:{dataset_id}", ...)` — bump version when parse/transform behavior changes).
- Remove `allow_legacy_pickle_cache` handling + the `.pkl` branch; remove `PipelineConfig.allow_legacy_pickle_cache` from `config.py` (check `.env.example` / docs mentions — report-only if docs are outside ownership; edit `.env.example` only if it references the flag... it's not owned: REPORT instead).

### 2. `adapters/ura.py`

- Token cache keyed by access key (:45-50, :88-101): `cache_id = f"ura_api_token:{hashlib.sha256(access_key.encode()).hexdigest()[:12]}"`.
- Session lifecycle: wrap `fetch_all_resi_transactions` session usage in `contextlib.closing(...)`; hoist the per-call retry decorator in `_ura_request` to module level if trivially possible.

### 3. `adapters/onemap.py`

- `ONEMAP_TOKEN` → `Settings`: add `onemap_token: SecretStr | None = Field(default=None, alias="ONEMAP_TOKEN")` to `Settings` (config.py); `setup_onemap_headers` reads `settings.onemap_token` (via `.get_secret_value()` when set) — remove the `os.environ` read (:57). Keep behavior: token valid → use it; else email/password flow.
- Thread-local sessions: `_thread_local = threading.local()` + `_get_session()` helper returning a per-thread `requests.Session`; use in `fetch_data` (and auth POST).
- `fetch_data` (:186): `response.json().get("results", [])` + `logger.warning` on missing key instead of raw `KeyError` leak.
- Base64 padding fix (:68-69): `"=" * (-len(segment) % 4)` (current form appends 4 redundant `=` when aligned).
- Rename lowercase module constants `initial_backoff`/`max_backoff` (:131-132) → UPPER_CASE.

### 4. `adapters/datagovsg.py`

- Module-level `_SESSION = requests.Session()` used by all request paths (:52, :87, :121, :181).

### 5. Tests

- 413 page-shrink: mock first page → 413, second → 200 with halved limit; assert offset preserved and final df complete (pins the recently-shipped hardening).
- Corrupt JWT: 3-part token with invalid base64 payload → falls through to email/password path without crashing.
- URA token: two different access keys → two distinct cache entries.
- Atomicity: after `set`, no `.tmp` remnants; sibling-format stale json removed after parquet `set` for same key.
- Expired entry: file unlinked after expired `get`.
- Unconfigured `cached_call`: warns once, still executes (two calls → one warning).

## Verification

```
dotenvx run -- uv run pytest tests/test_cache.py tests/test_onemap.py tests/test_ura.py tests/test_datagovsg.py -x -q
uv run ruff check src/egg_n_bacon_housing/utils/cache.py src/egg_n_bacon_housing/adapters/ src/egg_n_bacon_housing/config.py
uv run ruff format --check <same>
uv run mypy src/egg_n_bacon_housing/utils/cache.py src/egg_n_bacon_housing/adapters/ src/egg_n_bacon_housing/config.py
```

## Constraints

- NO commits. Owned files only. Do not alter retry/backoff semantics, error hierarchies, or API contracts beyond the listed items.
- If existing tests assert the pickle flag or `os.environ` token path, update them (in owned test files) and report.

## Definition of done

All changes in; tests (incl. new 413 + JWT + cache-key tests) green; lint/mypy clean.

## Report back

Edits (file:line), tests added, any `.env.example`/docs mentions of removed flags (report-only), verification tail.
