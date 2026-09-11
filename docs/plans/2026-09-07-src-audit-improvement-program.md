# src/ Audit → Improvement Program

Three parallel read-only audits (pipeline core, ingestion, cross-cutting) were run against the
current tree. All Critical/Warning findings below were independently re-verified against code
(file:line checked, not trusted from docs). No code was modified during the audit.

Scope: `src/egg_n_bacon_housing/**` (8.3k lines), `main.py`, cross-checked against
`.agents/skills/*`, `tests/`, `scripts/`, `app/`.

---

> **STATUS — PROGRAM COMPLETE (not committed).** All work orders landed and
> verified: WO-1…WO-8, WO-9, WO-10, WO-11, WO-12, FU-1, FU-2. Final merged
> state `pytest -q` → 793 passed (baseline ~700) · ruff/format/mypy/skill
> validators clean.
>
> Owner decisions applied in the final round:
> - **WO-9** kept FULL per-row pydantic at both boundaries — pure vectorization
>   only (null-scrub 3.4× faster: 27.8s→8.3s on 500k×60; validate_schema 500k
>   mixed rows in 24.4s; flat-type .map equal on the canonical production path).
> - **WO-11** rewired the school-tier machinery into location_dim via the
>   `school_reference` DI seam (historical intent — catalog lineage already
>     carried it). Quality scores per data/manual/csv/school_scoring_methodology.md;
>   new optional fields `nearest_top_primary_school_dist`,
>   `nearest_top_secondary_school_dist`, `school_accessibility_score`
>   (0.4/0.6 blend, 2km decay); NA-degradation with WARNING when R2 tier files
>   are absent. Dead fields: `h3_cell` dropped (no h3 dependency),
>   `price_stratum` populated (population quintile Q1–Q5), `search_confidence`
>   dropped (OneMap exposes no confidence signal).
> - **FU-1** (landed): `regional_mapping.py` values normalized to exactly
>   `"CCR"|"RCR"|"OCR"` (app `Region` parity, `app/src/types/segments.ts:15`);
>   former OCR sub-region groupings kept as comments only. Coarsens
>   `location_dim.region` / `PlanningArea360.region` from 8 distinct values to 3 —
>   formerly fine-grained rows now match the app's region filter.
>
> **Follow-up (operational) — COMPLETE.** Live pipeline run executed
> 2026-09-07/08 (`main.py --stage all` → `--stage features` → `--stage all`;
> warm caches, OneMap token auto-refresh exercised). All layers
> re-materialized with the new columns: unified_dataset 1,205,504×97;
> location_dim 11,454×48. Verified on real data: `annual_value`/
> `property_tax` 80.8% notna (C2 fix — was silently 0%), `price_stratum`
> 100%, region ∈ {CCR,RCR,OCR} (FU-1), school quality columns 100% populated
> with sane geography (top PAs: Bukit Timah, Newton, Marine Parade). Catalog
> regenerated (`scripts/generate_catalog.py`) — schema, lineage, and fresh
> parquet stats in sync; `check_catalog.py` green.
>
> Two latent bugs found & fixed during the live run:
> - `generate_catalog.py` crashed on datetime-bounded constraints
>   (`Field(ge=Timestamp("1990-01-01"))`) — `_extract_constraints` now
>   stringifies datetime bounds to ISO format.
> - MOE directory codes IP schools as `MIXED LEVEL (S1-JC2)` and girls'
>   schools as `SECONDARY (S1-S4)` (not `SECONDARY (S1-S5)`), and appends
>   `SCHOOL`/`(SECONDARY)` to some names — the secondary pool now spans all
>   S1-admitting codes and tier-name matching falls back to longest-prefix
>   (`utils/school_features.py:_resolve_tier`). Without this,
>   `nearest_top_secondary_school_dist` was all-NA and RI/NYGH/RGS/ACS(I)/HCI
>   scored quality 0.
>
> Known benign signal: unified_dataset carries ~3.7k full-row duplicate rows
> (0.3%), all 1990-01 epoch records — legitimate same-day same-price
> transactions at identical addresses in early-90s HDB data; do not dedupe.
>
> Remaining deferred item: quarantine-only persist mode for the validation
> gateway (decision 4) — still awaiting owner input; no action taken.

## Findings register (verified)

### Critical

| ID | Location | Finding |
|----|----------|---------|
| C1 | `components/features.py:230-237`, `components/feature_transactions.py:255-263` | `validate_and_quarantine(...)` called **without `persist=False`** (gateway default is `persist=True`, `utils/validation_gateway.py:95`). Only two nodes in the DAG still do this. Consequences: gold parquet written twice per run (gateway inline write + companion materializer), duplicate quality-DB snapshots per run (skews Welford baselines in `utils/data_quality.py`), cached replays carry write side effects. Violates the skill contract "computing nodes are side-effect-free — every published output persisted by exactly one materializer". |
| C2 | `components/feature_transactions.py:109-112` vs `:234`, `:269-277` | `flat_type` normalization (`normalize_hdb_flat_type`) runs **only inside the rental-yield branch**. When `rental_yield` is empty, `_map_flat_type_for_annual_value("4 ROOM")` (spaced form) matches no dashed branch → merge on `type_of_hdb` matches nothing → `annual_value`/`property_tax` silently all-NaN for every row. Feature availability coupled to an unrelated input. |
| C3 | `adapters/datagovsg.py:239` | `int(e.response.headers.get("Retry-After", "0") or 0)` raises `ValueError` on a legal HTTP-date `Retry-After`. The exception escapes the `except HTTPError` block and crashes `_fetch_from_api` with a bare `ValueError` instead of the designed retry/degrade path (`macro.py:33` catches `ValueError` and silently degrades to empty data). OneMap already has a correct parser (`adapters/onemap.py:66-84`). |

### Warning — correctness / validity

| ID | Location | Finding |
|----|----------|---------|
| W1 | `utils/regional_mapping.py:10-71` | Covers only 42/55 OneMap planning areas (verified against `data/manual/geojsons/onemap_planning_area_polygon.geojson`). 13 PAs unmapped → `region=None` downstream: CENTRAL WATER CATCHMENT, LIM CHU KANG, MARINA EAST, NORTH-EASTERN ISLANDS, PAYA LEBAR, PIONEER, SELETAR, SIMPANG, SOUTHERN ISLANDS, SUNGEI KADUT, TUAS, WESTERN ISLANDS, WESTERN WATER CATCHMENT. PAYA LEBAR + SELETAR carry real transactions. Additionally ~21 keys can never match (not PAs: "Downtown", "Marina Bay", "Alexandra", "Lavender", "Farrer Park", "Little India", "Jalan Besar", "Bugis", …). Affects `location_dim.region` and the app's region filter (`app/src/components/dashboard/segments/lib/buildSegmentAreaRows.ts:21`). |
| W2 | `components/ingestion/datagov.py:96-100, 178-182, 554` | Inconsistent empty-cache semantics: 0-row bronze parquet returned as a valid hit for `raw_rental_index`, `raw_hdb_rental`, `raw_school_directory`, `raw_hdb_resale`, wiki malls — while `macro.py:227` and `geojson.py:446` correctly treat empty as a miss. One corrupted 0-row file permanently zeroes a required dataset with only an info log. |
| W3 | `components/ingestion/datagov.py:106-110` | `cached_call` 24h API layer sits **under** the bronze cache for the three parameterized nodes. `main.py --refresh raw_hdb_rental` (uses `refresh_bronze`, which keeps the API cache by design) re-serves ≤24h-old API data **and** stamps a fresh `fetched_at` into `bronze_manifest.json` — the manifest lies and the staleness tripwire resets. All other ingestion nodes correctly pass `use_cache=False` with no wrapper. |
| W4 | `adapters/ura.py:179`, `:112-125` | On `URAAuthError`, refresh calls `fetch_ura_token(use_cache=False)` which bypasses `cached_call` entirely — the fresh token is never cached; the rejected one stays cached for its 8h TTL. Every run within 8h repeats: read bad token → batch 1 fails → refresh → retry. |
| W5 | `utils/geocoding.py:172-183` | No single-flight on auth refresh: mid-run token expiry with `max_workers=5` causes up to 5 serialized full token round trips (each with 3-attempt tenacity retry), burning OneMap auth quota. |
| W6 | `utils/geocoding.py:123-131` vs `adapters/onemap.py:247-260` | Split-brain TTL: geocoder reads `onemap_search:{addr}` with `geocoding.cache_duration_hours` but `fetch_data_cached`→`cached_call` writes with **no** `duration_hours` (pipeline TTL). Effective TTL = max of knobs; `GEOCODING__CACHE_DURATION_HOURS` silently ineffective when shorter. |
| W7 | `utils/proximity.py:134-140` | Empty-valid-coordinate branch omits `nearest_mrt_score` (non-empty path always emits it, `proximity.py:185-196`); breaks the frame column contract (`tests/test_proximity.py:89-96`). |
| W8 | `utils/mrt_line_mapping.py:279-284` vs `utils/proximity.py:166-185` | `station_score` arithmetic duplicated (proximity inlines the formula instead of calling the repository method). Tier-weight changes in one place silently diverge the other. |
| W9 | `components/features.py:148-171` | Broad `except (OSError, ValueError, KeyError, RuntimeError)` around proximity degrades **all 14 proximity columns to NA** with one warning; all schema-optional → invisible downstream. |
| W10 | `components/features.py:30-31` | `_add_planning_area` skips derivation when `planning_area.notna().any()` — a partially populated column permanently blocks derivation for the null rows. |
| W11 | `utils/hdb_lookups.py:118-135` | `merge_median_income` uppercases the published `planning_area` column **only when income source is non-empty** (early return at :119). Output casing depends on an optional source's presence. |
| W12 | `components/export.py:19`, `feature_transactions.py:71` | Node default `large_table_validation_policy="sample"` vs config/gateway default `"full"` (`config.py:26`). A caller that forgets DI silently downgrades validation of 1M-row tables. |
| W13 | `components/feature_rental.py:104-113` | Inner sales×rent merge drops town/flat-type/month groups with sales but no rents; counts only logged at INFO. |
| W14 | `adapters/onemap.py:232-235` | Malformed OneMap response missing `results` is converted to empty success **and cached** for full TTL → address silently un-geocodable for 24h. |
| W15 | Silent-loss logging gaps (population shrinkage with no count): `components/metrics.py:75`, `components/feature_profiles.py:36,67`, `components/features.py:96`, `components/ingestion/geojson.py:110-126` (coord drops), `components/ingestion/datagov.py:351-355` (blank postal), `components/ingestion/ura_csv.py:126-128` (unparseable dates), `utils/proximity.py:99-100,250-253` (POI coord drops). |
| W16 | `utils/validation_gateway.py:225-241` | Production quarantines unrecoverable: every node runs `persist=False`, so dropped rows are only a warning count in logs. No `_quarantine/` artifact at gold/platinum boundaries. |
| W17 | `components/feature_profiles.py:95` | `latest_value = ...iloc[-1]` without `dropna` — one trailing null macro row broadcasts NaN for a whole column. |
| W18 | `utils/school_features.py:178-181` | No-geocoded-schools path returns frame without the 3 distance columns; `features.py:127-139` then never sets `dist_to_nearest_school` → field silently disappears from `location_dim`. |

### Perf hotspots (Warning)

| ID | Location | Finding |
|----|----------|---------|
| P1 | `utils/validation.py:101-105` | Per-cell Python null-scrub (`for record: for key,value:`) over every row × column under the default `"full"` policy ≈ 10⁸ `pd.isna` calls per run across silver/gold/platinum. Vectorize once before chunking. |
| P2 | `utils/validation.py` + gateway | `transactions_enriched` (~1M × ~60 fields) pydantic-validated **twice** (gold `HFeatureTransaction`, then platinum `HUnifiedRecord` thin subclass). |
| P3 | `utils/data_quality.py:82-84` | `df.isnull().sum().sum()` + `df.duplicated()` full scans (row-hash of 1M×60) on every persisted frame — currently **twice** per run for the C1 nodes. |
| P4 | `components/feature_transactions.py:234` | Row-wise `.apply(_map_flat_type_for_annual_value)` over ~1M rows for a pure mapping → `.map(dict)`. Same pattern: `features.py:226-228` (region), `metrics.py:98-99` (affordability `np.select`). |
| P5 | `components/ingestion/macro.py:345-346` | 8 macro sources fetched strictly serially; `ThreadPoolExecutor(3-4)` is low-risk. |

### Dead surfaces (grep-verified)

| ID | Location | Finding |
|----|----------|---------|
| D1 | `utils/school_features.py:23-123`, `utils/runtime.py:53-57` | Entire school-tier machinery (~100 lines + `SchoolReference` protocol + `school_tiers.json` load path) has no production caller. |
| D2 | `utils/cache.py:295-304` | Module-level `clear_cache()`/`get_cache_stats()` — zero callers (99_cleanup uses the method). |
| D3 | `utils/data_loader.py:105-108,174-180` | `load_planning_areas()`/`get_planning_areas_for_points()` wrappers — tests-only. |
| D4 | `adapters/datagovsg.py:295-297` | `use_cache=True` branch / `datagovsg:*` cache-key family never taken in production. |
| D5 | `schemas/feature_models.py:144,146` | `h3_cell`, `price_stratum` declared on `HFeatureTransaction`, produced nowhere. `schemas/clean_models.py:87` `search_confidence` same. |
| D6 | `components/materialization.py:34-41` | `L5_appreciation_hotspots` alias file written outside `PUBLISHED_LAYERS`, untracked quality baseline. |
| D7 | `components/feature_rental.py:108` | `flat_type_count` persisted, consumed nowhere. |
| D8 | `schemas/__init__.py:3-9` | Re-exports with no importers. |

### Test gaps (highest-leverage)

- `tests/test_features.py`: no test of the annual-value merge with raw spaced flat types (every existing test passes `raw_median_annual_value=pd.DataFrame()` — would have caught C2). No node-write-isolation tests for `location_dim`/`transactions_enriched` (would have caught C1). No partial-`planning_area` test (W10). No PA-case coupling regression through the real `merge_median_income` (W11).
- `tests/test_datagovsg.py`: no HTTP-date `Retry-After` test (C3); no mid-pagination 413; no relative `_links.next` prefixing.
- `tests/test_ingestion.py`: no empty-bronze-cache refetch test for the datagov nodes (W2); no geocode-failure malls branch.
- `tests/test_ura.py`: no token-refresh cache-repair test (W4).
- `tests/test_geocoding.py` / `tests/test_onemap.py`: no single-flight auth test (W5); no TTL-knob pin (W6).
- Missing files: `tests/test_regional_mapping.py` (W1), `tests/test_logging_config.py`, `tests/test_mrt_line_mapping.py` extensions (tier/score/`<NULL>` handling).
- `tests/test_validation_gateway.py`: no test pinning small-table `"fail"`-behaves-like-`"full"` divergence (`validation_gateway.py:126-130`).

---

## Dispatch program

Work orders are sized for single worker subagents, with skills to read first, files to touch,
and acceptance criteria (tests + checks). Phases are dependency-ordered; within a phase WOs are
parallelizable unless they share files.

Verification for every WO: `dotenvx run -- uv run pytest -q`, `uv run ruff check`, `uv run mypy`
(confirm commands with owner). No commits.

### Phase 0 — Data-correctness hotfixes (dispatch now)

**WO-1 · Gateway persist drift + policy defaults** (skill: `change-hamilton-pipeline`)
- `components/features.py:230-237` and `components/feature_transactions.py:255-263`: add `persist=False` to both `validate_and_quarantine` calls.
- `components/export.py:19`, `components/feature_transactions.py:71`: change node default `large_table_validation_policy` `"sample"` → `"full"`.
- Tests: add node-write-isolation tests (`assert not list(tmp_path.rglob("*.parquet"))` happy path) for both nodes in `tests/test_features.py`, mirroring `test_metrics.py:392`.
- Acceptance: only materializers write gold; single quality snapshot per dataset per run; `test_materialization.py` + `test_pipeline.py` green.

**WO-2 · Annual-value join correctness** (skill: `change-hamilton-pipeline`; same files as WO-1 — run after it or merge into one worker)
- `components/feature_transactions.py`: normalize `flat_type` unconditionally when column exists (move out of the rental branch at :109-112), or make `_map_flat_type_for_annual_value` call `normalize_hdb_flat_type` first.
- Test: `test_transactions_enriched_merges_annual_value_with_raw_flat_types` — spaced `"4 ROOM"` input, **empty** `rental_yield`, non-empty `raw_median_annual_value`; assert non-null `annual_value`.
- Acceptance: annual_value populated with and without rental data.

**WO-3 · data.gov.sg Retry-After + pagination hardening** (skill: `change-data-ingestion`)
- `adapters/datagovsg.py:239`: extract/share `_parse_retry_after` (reuse `onemap.py:66-84` logic via a shared adapter util); fall back to exponential sleep when unparseable.
- Tests in `tests/test_datagovsg.py`: HTTP-date `Retry-After` (no ValueError, honors delay); mid-pagination 413 shrink; relative `_links.next` prefixing.
- Acceptance: no exception path can escape `HTTPError` handling as `ValueError`.

**WO-4 · Regional mapping completion** (skill: `change-hamilton-pipeline`)
- `utils/regional_mapping.py`: re-key by the 55 official `pln_area_n` values; add the 13 missing PAs (Central Water Catchment→CCR?, verify region assignment per URA CCR/RCR/OCR definitions — decide per-area, e.g. PAYA LEBAR RCR, SELETAR OCR, TUAS OCR); delete the ~21 dead keys.
- New `tests/test_regional_mapping.py`: full coverage test against the OneMap polygon names (read the GeoJSON in the test), spot-check regions.
- Acceptance: zero `None` regions for all 55 official PAs; app region filter unaffected for existing keys.

### Phase 1 — Cache/validity semantics

**WO-5 · Empty-cache + refresh correctness** (skill: `change-data-ingestion`)
- `components/ingestion/datagov.py` (3 `_load_or_fetch_dataset` sites, `raw_hdb_resale_transactions`, wiki malls): treat `cached.empty` as miss (warn + fetch), mirroring `macro.py:227`.
- Remove the `cached_call` layer under bronze for the parameterized nodes (bronze is the cache) **or** make `refresh_bronze` clear matching `cache_id`s — pick one; document in the skill's bronze section.
- Test: mirror `test_raw_macro_data_ignores_empty_cache_and_refetches` for rental_index/hdb_rental/school_directory/resale; test that `--refresh` actually re-fetches past the API cache.
- Acceptance: no path where a 0-row parquet or 24h API cache can masquerade as fresh bronze.

**WO-6 · Token/auth cache repairs** (skill: `change-data-ingestion`)
- `adapters/ura.py:179`: persist refreshed token (`cache_manager.set(_token_cache_id(...))` or clear+re-enter).
- `utils/geocoding.py:172-183`: single-flight refresh (compare headers/token inside the lock; skip network call if already replaced).
- `adapters/onemap.py`: add `duration_hours` param to `fetch_data_cached`; pass `self.cache_duration_hours` from `_geocode_via_api`; on missing `results` key, raise retryable instead of caching empty success (or skip caching).
- Tests: T5 (URA token repair), T6 (single refresh across workers), T7 (TTL knob pin).
- Acceptance: second URA run within TTL needs no re-auth; exactly one refresh under concurrent expiry; geocoding TTL knob effective.

**WO-7 · Silent-loss observability** (skill: `change-hamilton-pipeline`)
- Add dropped/kept count logging (WARNING where populations are defined) at all W15 sites: `metrics.py:75`, `feature_profiles.py:36,67`, `features.py:96`, `geojson.py:110-126`, `datagov.py:351-355`, `ura_csv.py:126-128`, `proximity.py:99-100,250-253`.
- `feature_rental.py:110-113`: raise merge-drop log to WARNING; record matched-vs-total coverage metric.
- Tests: assert logged counts at the metrics/profiles boundaries.
- Acceptance: no population-shrinking filter without a count in logs.

**WO-8 · Proximity/feature edge hardening** (skill: `change-hamilton-pipeline`)
- `utils/proximity.py:134-140`: add `nearest_mrt_score = 0.0` to the empty branch; use haversine metric for MRT nearest-neighbour selection (or k>1 + min-haversine tiebreak) for metric consistency.
- Extract shared `station_score_basis(lines, tier)` used by both `mrt_line_mapping.py` and `proximity.py` (fixes W8).
- `components/features.py:148-171`: narrow the except; record a "proximity degraded" quality snapshot.
- `features.py:127-139`: set `dist_to_nearest_school = pd.NA` explicitly on the no-schools path; `features.py:30`: derive planning_area for null rows via anti-join.
- `feature_profiles.py:95`: `dropna(subset=[value_col])` before `iloc[-1]`.
- Tests: extend `test_proximity.py` (empty-branch column contract, brute-force nearest selection), `test_features.py` (partial PA, degraded-proximity contract, no-schools column).
- Acceptance: column contracts stable across empty/degraded paths.

### Phase 2 — Performance

**WO-9 · Validation fast path** (skill: `change-hamilton-pipeline`; measure first)
- `utils/validation.py:101-105`: vectorize null-scrub — `df_validate.astype(object).where(df_validate.notna(), None)` once, then `iloc` chunk slices; delete the per-cell loop.
- Strategy: validate gold fully; make the platinum pass on `HUnifiedRecord` structural (columns/dtype/count) instead of per-row pydantic — requires schema-owner sign-off since it weakens a validation boundary; alternatively extend `vectorized_precheck` and pydantic-validate only flagged rows.
- `feature_transactions.py:234`: `df["flat_type"].map(_AV_TYPE_MAP).fillna(df["flat_type"])`; `features.py:226-228` region via `.map`; `metrics.py:98-99` via `np.select`.
- `utils/data_quality.py:82-84`: per-column null counts during write; sampled duplicate estimation.
- Acceptance: benchmark before/after on `transactions_enriched` (target: >2× on the validation stage); identical quarantine counts on a fixed fixture.

**WO-10 · Ingestion concurrency** (skill: `change-data-ingestion`)
- `components/ingestion/macro.py:345-346`: `ThreadPoolExecutor(3-4)` over `_MACRO_SOURCES` with per-future failure collection.
- Keep datagovsg pagination serial (documented TLS/rate-limit tradeoff) unless wall time proves otherwise.
- Acceptance: macro stage wall time ↓ ~2-3×; failure list behavior unchanged.

### Phase 3 — Hygiene

**WO-11 · Dead surface removal** (needs one decision, see below)
- Delete school-tier machinery + `runtime.SchoolReference` protocol (or re-wire into `location_dim` if roadmap).
- Delete `utils/cache.py:295-304`, `utils/data_loader.py` test-only wrappers (update the two test files), `adapters/ura.py:150` session param (make required), `schemas/__init__.py` re-exports, `feature_rental.py:108` `flat_type_count`.
- `materialization.py:34-41`: date or de-register the `L5_appreciation_hotspots` alias (`track_quality=False` interim).
- Schema dead fields (`h3_cell`, `price_stratum`, `search_confidence`): drop or populate — decision required.

**WO-12 · Docs/skill realignment**
- `change-hamilton-pipeline/SKILL.md`: stage table lists only `components/features.py` for features; actual wiring is four modules (`pipeline.py:57-67`).
- `utils/validation_gateway.py:63` docstring (layer values); route `"fail"` policy through the strict branch regardless of size (`:126-130`) + test.
- `utils/logging_config.py:44`: stderr handler for ≥WARNING.
- `geojson.py:134,402`: `encoding="utf-8"` on bare `open()`.
- `datagov.py:36` / `macro.py:38`: import `DATAGOVSG_BASE_URL` from the adapter instead of duplicating.
- New `tests/test_logging_config.py`.

### Decisions needed from owner

1. **WO-9 platinum validation**: accept structural-only platinum pass (perf) vs keep full pydantic (strictness)?
2. **WO-11 school tiers**: delete (~100 lines + protocol + JSON path) or re-wire as a feature?
3. **WO-11 schema dead fields**: populate `h3_cell`/`price_stratum`/`search_confidence` or drop them?
4. **WO-16 quarantine persistence**: add `persist="quarantine_only"` gateway mode so gold/platinum boundaries persist dropped-row artifacts (small scope, big observability win)?
5. **Region assignment** for the 13 missing PAs (WO-4) — confirm CCR/RCR/OCR classification per area.

---

## Suggested next steps

1. Dispatch Phase 0 as four parallel workers (WO-3, WO-4 fully independent; WO-1 → WO-2 chained
   since both edit `feature_transactions.py`/`features.py`). Each worker must read the matching
   skill first and make no commits.
2. Answer the five decisions above (unblocks WO-9, WO-11, WO-16).
3. Run Phase 1 as WO-5 + WO-6 in parallel, then WO-7 + WO-8 in parallel.
4. Phase 2 only after a timing baseline is captured (`refresh_run.log` exists; re-capture per
   stage before WO-9).
5. Regression guard for the whole program: every WO lands with its named test; the C2 test and
   the C1 write-isolation tests are the two highest-value additions in the suite.
