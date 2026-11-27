# Phase 2 findings register — master audit 2026-11-23

Baseline `449b921`. Discovery: [01-discovery.md](01-discovery.md). Every row below was re-checked against the cited lines by the lead auditor; probe outputs are in `evidence/` and were re-executed independently of the agent that first proposed them.

**Scoring.** Severity = impact (1–5) × likelihood (1–5). CRITICAL ≥ 20, HIGH 12–19, MEDIUM 6–11, LOW 1–5. Impact is what breaks for whom; likelihood is how often the trigger occurs in supported operation, not theoretical reachability.

**Verdict headline:** no CRITICAL finding. Three HIGH findings are all data-integrity defects in the offline pipeline/operations path. The published static site is independently green (1,136 Python tests, 534 frontend tests, 237 E2E, 9 Pages-base E2E, build 234 pages, validators, frozen-asset baseline).

| ID     | Sev    | Score    | Category                       | Confidence                                      |
| ------ | ------ | -------- | ------------------------------ | ----------------------------------------------- |
| CORE-1 | HIGH   | 16 (4×4) | Correctness / cache contract   | CONFIRMED (PoC ×2)                              |
| CORE-2 | HIGH   | 12 (4×3) | Ingestion integrity            | CONFIRMED (PoC ×2)                              |
| CORE-3 | HIGH   | 16 (4×4) | Persistence / backup integrity | CONFIRMED (PoC ×2)                              |
| CORE-4 | MEDIUM | 8 (4×2)  | Path containment               | CONFIRMED (PoC, requires bucket influence)      |
| CORE-5 | MEDIUM | 9 (3×3)  | Operational recovery           | CONFIRMED (PoC ×2)                              |
| CORE-6 | MEDIUM | 8 (2×4)  | Concurrency / external service | CONFIRMED (PoC ×2)                              |
| UI-1   | MEDIUM | 9 (3×3)  | Data trust boundary            | CONFIRMED (code path)                           |
| UI-2   | MEDIUM | 9 (3×3)  | Accessibility                  | CONFIRMED (code + browser)                      |
| UI-3   | MEDIUM | 9 (3×3)  | Correctness / handoff          | CONFIRMED (browser)                             |
| UI-4   | MEDIUM | 6 (2×3)  | Correctness / UI arithmetic    | CONFIRMED (PoC ×2)                              |
| REL-1  | MEDIUM | 6 (3×2)  | Release gate                   | CONFIRMED (workflow + skip behaviour)           |
| REL-2  | MEDIUM | 6 (3×2)  | Evidence integrity             | CONFIRMED (code path)                           |
| REL-3  | MEDIUM | 9 (3×3)  | Reproducibility control        | CONFIRMED (5 checks reproduced failing)         |
| REL-4  | MEDIUM | 9 (3×3)  | Supply-chain control           | CONFIRMED (no job; audits non-empty)            |
| ARCH-1 | MEDIUM | 6 (2×3)  | Type-safety coverage           | CONFIRMED (measured list)                       |
| ARCH-2 | LOW    | 4 (2×2)  | Duplication                    | CONFIRMED (two implementations)                 |
| DEP-1  | LOW    | 3 (1×3)  | Dependency hygiene             | LIKELY (no reference found; removal unverified) |
| DOC-1  | MEDIUM | 6 (2×3)  | Documentation drift            | CONFIRMED (contradictions read)                 |

---

## HIGH

### CORE-1 — Warm geocode cache bypasses condo project-plausibility checks

- **Paths:** `src/egg_n_bacon_housing/utils/geocoding.py:340-345` (cache hit path), `:299-317` (`_row_from_result` vs `_empty_row`); `src/egg_n_bacon_housing/components/cleaning.py:418-444` (`_accept_plausible_project_coords`, `plausible_project_match`).
- **Evidence:** the cache-hit branch returns `{**self._empty_row(addr), "lat": cached[0], "lon": cached[1]}`. `_empty_row` sets `matched_name=None` and `address=str(addr)` — the _query_, not OneMap's matched address. `_accept_plausible_project_coords` decides acceptance from `matched_name` and `address`, so on the warm path it compares the query with itself. Cold path uses `_row_from_result`, which keeps the real `SEARCHVAL`/`ADDRESS`.
- **Probe (`evidence/core-poc-results.json`, `cache_plausibility`):** a project-aware query whose OneMap hit is an unrelated project is rejected cold and produces the street-fallback coordinate `(1.33, 103.83)`; the same run re-executed warm accepts the rejected project coordinate `(1.31, 103.81)` with `matched_name=null`.
- **Impact:** repeated pipeline runs can change which coordinate a condominium transaction receives, silently moving proximity/amenity features and spatial aggregates. Coverage gates still pass, so nothing reports the change. Published data already produced from a cold run is not retroactively wrong — the defect is run-to-run instability.
- **Fix:** carry the cached response's metadata, not just coordinates (cache the full row set or re-derive via `_row_from_result` from a cached frame). Never substitute query text for matched-address evidence.
- **Test:** real temporary `CacheManager`, mocked unrelated OneMap result, run `geocoded_properties` twice; assert identical coordinates and identical rejection on both passes.

### CORE-2 — A malformed later page publishes and permanently caches a partial dataset

- **Paths:** `src/egg_n_bacon_housing/adapters/datagovsg.py:222-226` (missing `result.records` → `break`), `:229`, `:336` (concat without completeness check); reconciliation exists only in the exception branches at `:294-298`, `:313-317`, `:323-327`. Consumer: `src/egg_n_bacon_housing/components/ingestion/datagov.py:109-125`.
- **Evidence:** an HTTP-200 envelope without `result.records` after at least one valid page exits pagination normally and returns the accumulated rows. `IncompleteDatasetFetchError` is raised only from `except` handlers.
- **Probe (`partial_fetch`):** page one advertises `total: 4` and returns 2 rows plus a next link; page two returns `{"success": false, ...}`. Required ingestion returned 2 rows, persisted 2 rows, wrote a fresh 2-row manifest, and the next invocation served those 2 rows from bronze without touching the API.
- **Impact:** non-expiring bronze caches hold incomplete transaction/reference populations. Every downstream gold/platinum figure and every published app asset derived from them is understated with no error, warning, or manifest signal.
- **Fix:** treat a malformed page envelope as a fetch failure at any pagination offset; reconcile returned rows against the advertised total before returning; reject non-progressing pagination.
- **Test:** valid page then HTTP-200 error envelope must raise and write no parquet/manifest. Add advertised-total shortfall and repeated-next-link cases.

### CORE-3 — R2 sync tolerates 100-byte differences, so real corrections never propagate

- **Paths:** `scripts/00_sync_data.py:42` (`_SIZE_TOLERANCE_BYTES = 100`), `:121-127` (upload skip), `:170-179` (download skip), `:232-239` (verify reports differences up to 100 bytes as OK).
- **Evidence:** every direction compares only `st_size`; content is never compared, and even a detectable size change under the tolerance is ignored.
- **Probe (`size_integrity`):** local `price\n1\n` (8 bytes) vs remote `price\n2\n3\n` (10 bytes) → 0 downloads, 0 uploads, `Summary: 1 OK … 0 size mismatches`. The same applies to equal-length corrections, which are undetectable by size at all.
- **Impact:** corrected manual inputs and geocode caches do not propagate between operator and bucket in either direction, and `verify` reports false reassurance. The bucket is the documented recovery path for ≈100 MB of gitignored source data, so a stale backup can be restored believing it is current.
- **Fix:** stage it — keep size as a fast pre-filter but add a content-verification mode (per-object SHA-256 recorded at upload, or download-and-compare), and make `verify` report "size-equal, content unverified" instead of "OK". Do not simply delete the tolerance: a naive removal would re-transfer the full bucket on first run.
- **Test:** differences of 1/99/100 bytes and equal-size differing content must not be classified unchanged; content mode must detect all four.

---

## MEDIUM

### CORE-4 — R2 object keys can escape the local data roots

- **Paths:** `scripts/00_sync_data.py:167`, `:216` (`key.removeprefix(prefix + "/")` → `MANUAL_DATA_DIR / rel` or `CACHE_DIR / rel`), write at `:191-194`.
- **Evidence/probe (`containment`):** inside a disposable root, remote key `manual/../escaped.txt` wrote outside the manual directory, and `geocache/hamilton/injected.json` wrote into the subtree that upload explicitly excludes. No prefix-boundary, `..`, absolute-path, resolve-containment or flat-geocache-shape check exists.
- **Reachability:** requires influence over bucket contents (compromised credentials, mistaken upload, shared bucket) plus an operator download. No unauthenticated bucket access was established.
- **Fix:** require an exact `prefix/` boundary, reject absolute remainders and `..`, resolve and enforce containment (including symlinks), and allow only single-segment files with approved extensions for `geocache/`.
- **Test:** reject traversal, absolute remainder, prefix siblings, nested `hamilton/` keys and escaping symlinks before any transfer is submitted.

### CORE-5 — A failed scheduled refresh becomes a successful no-op

- **Paths:** `scripts/40_refresh_rolling.py:240-242` (`if args.stale_only and not removed: return 0`), decision input `:236`; `src/egg_n_bacon_housing/utils/bronze.py` refresh helpers.
- **Evidence:** the rerun decision counts _deleted parquets_, not _selected stale/missing datasets_. When invalidation succeeds but the fetch fails before bronze is rewritten, the next identical invocation deletes nothing, so it returns 0 without running the pipeline.
- **Probe (`refresh_retry`):** 40-day-old parquet selected and deleted → mocked failure → exit 1; identical second run → exit 0, `pipeline_calls=1`, parquet still missing, dataset still selected by `stale_names`.
- **Impact:** the documented cron target reports success while the source stays missing, until manual intervention.
- **Fix:** separate "work selected" from "files removed"; run when any selected dataset is stale _or absent_.
- **Test:** two invocations (failure then success) must both invoke the pipeline and end with restored bronze.

### CORE-6 — Geocoder pacing releases a burst instead of spaced requests

- **Path:** `src/egg_n_bacon_housing/utils/geocoding.py:190-197`.
- **Evidence:** each caller sets `_next_slot = now + interval`, discarding reservations taken by previous waiting callers; a waiter's own reservation is never respected.
- **Probe (`rate_limiter`):** five simultaneous callers at an 80 ms interval released at `0.00000, 0.08011, 0.08019, 0.08021, 0.08029` s — gaps of 20–80 µs between the last four, not 80 ms. Reproduced independently at 30–50 µs.
- **Impact:** configured spacing is violated whenever `max_workers > 1` on cold-cache runs, raising upstream rate-limit/quota risk and degrading geocode coverage. Upstream throttling was not tested.
- **Fix:** `slot = max(now, _next_slot); _next_slot = slot + interval; sleep(slot - now)`.
- **Test:** deterministic clock assertion on actual release spacing; the current parallel test replaces `wait()` and only counts invocations.

### UI-1 — Legacy release verification does not cover the responses actually displayed

- **Paths:** `app/src/utils/release-manifest.ts:446-473` (fetches and hashes asset bytes), `:484-507` (returns `status`/`manifest`/`mismatches` only — the verified buffers are discarded); `app/src/components/explorer/ExplorerWorkspace.tsx:164-188` (verify pass), `:265-271` (independent `useGzipJson` fetch of the same URLs), disclosure at `:630`.
- **Evidence:** verification downloads the assets, then the UI downloads them again through `useGzipJson`, which parses without comparing hashes. The verified bytes and the displayed bytes are different responses.
- **Trigger:** a deployment in progress, CDN/cookie/cache skew, or any later successful data reload between the two request sets. No malicious input required.
- **Impact:** values from mixed generations can appear under an explicit "generation-verified" claim. This is not an HTTPS-bypass claim: same-origin publication control already implies app control.
- **Fix:** return decoded verified payloads from the release loader and render/cache exactly those objects; re-verify before replacing displayed data on refresh.
- **Test:** serve valid manifest/assets for verification and different valid JSON afterwards; assert changed values can never render as verified, including after a refresh.

### UI-2 — Research-map area selection is pointer-only

- **Paths:** `app/src/components/dashboard/PriceMap.tsx:464-489` (mouseover/mouseout/click only), `:593-607` (metric `<select>` has adjacent text, no `<label>`/`aria-label`), `:619-621`, `:657-659` (selected state by class only, no `aria-pressed`), `:741` ("click an area").
- **Browser observation (`evidence/browser-map.log`):** on `/research/map/?area=TAMPINES`, 55 polygon paths, **0** focusable, metric select with `aria-label=null` and `labels=[]`, no `aria-pressed` on the CONDO button. Route mounted at `app/src/components/research-map/ResearchMapSurface.astro:129`.
- **Impact:** keyboard and screen-reader users cannot select an area to inspect archive layers; filter state and control names are not exposed. A pre-built `?area=` link is not a discoverable equivalent control.
- **Fix:** add a labelled native area selector driving the same state, associate the metric label, expose pressed state, and offer a table/link alternative.
- **Test:** select an area and inspect a layer using keyboard only; assert accessible names and current filter state.
- **Not affected:** `/explore`, whose SVG provides focusable, named area links and list/table alternatives (`app/src/components/explorer/ExplorerMap.tsx:375-461`).

### UI-3 — Research-map handoff silently changes comparison scope

- **Paths:** `app/src/components/dashboard/PriceMap.tsx:294-295` (metric key composed from temporal + property), `:777` (handoff href serialises only `area` and `metric`); `app/src/components/explorer/ExplorerWorkspace.tsx:86-92` (falls back to the build's observed default period and its own property default).
- **Browser observation:** with `?area=TAMPINES&metric=median_price&timeBasis=pre_covid&propertyType=condo`, the rendered handoff was `/explore?area=TAMPINES&metric=median_price` — period and property dropped. Confirmed by activating the CONDO and Pre-COVID controls with the keyboard first (`evidence/browser-map.log`).
- **Impact:** "Open observed comparison" compares a different property and window than the one just inspected; users can read the result as the same scope.
- **Fix:** one shared handoff serializer translating temporal/property/metric into supported explorer parameters, with explicit disclosure when a metric is unsupported downstream.
- **Test:** follow the handoff for each property and historical period; assert destination controls, source section and figures preserve scope.

### UI-4 — Financing arithmetic accepts inputs it then contradicts

- **Paths:** `app/src/components/tools/lib/tool-amortization.ts:37` (down payment allowed to 100 %), `:96` (payment formula), `:156` (principal), `:161-163` (null payment reported as `invalidFields: ["price"]`).
- **Evidence (`evidence/financing-poc.log`, reproduced by the lead auditor):** default S$710,000 scenario with `downPaymentPercent: 100` → `{ok:false, invalidFields:["price"]}`; `annualRatePercent: 1e-14` → `ok:true` with `monthlyPayment` and `paymentToIncomePercent` both `Infinity`.
- **Impact:** a valid cash-purchase boundary blames the price field, and tiny accepted positive rates produce a "successful" scenario with non-finite outputs. Illustrative arithmetic only — no eligibility advice, no demonstrated financial loss.
- **Fix:** handle zero principal explicitly; use `log1p`/`expm1` stable form; reject non-finite derived values.
- **Test:** 100 %-down, tiny-positive-rate, and finite-output property tests; extend `app/tests/unit/tool-amortization.test.ts`.

### REL-1 — Pages-base browser checks are not a release gate

- **Paths:** `.github/workflows/ci.yml:142-151` (default build + `astro preview` at `/`), `app/tests/e2e/pages-base.spec.ts:21-24` (skips without `PAGES_ORIGIN`), `.github/workflows/deploy.yml:52-67` (heading greps), `:85-121` (one base-prefixed CSS asset).
- **Evidence:** the fresh audit E2E run skipped exactly those 9 tests at root; re-running with `PAGES_ORIGIN`/`PAGES_BASE_PATH` and the prefixed build produced 9 passed. Neither workflow invokes that combination, and deploy does not depend on CI.
- **Impact:** a prefix, hydration, deep-link or data-fetch regression can pass CI and deploy smoke greps, then fail on the real Pages site.
- **Fix:** add a workflow job that builds with `ASTRO_PAGES=true`, serves `app/scripts/serve-pages-base.mjs`, and requires `pages-base.spec.ts` to pass; make deploy depend on it.
- **Test:** job must fail when a base-prefixed asset/link is deliberately broken.

### REL-2 — Edition sign-off hashes are never checked against evidence bytes

- **Paths:** `app/src/components/studies/lib/edition-registry.ts:983-985` (`artifactSha256` shape only), `:1023-1029` (sign-offs must agree with each other), `:1103-1130` (`verifyEditionArtifacts` hashes only `edition.frozenSource`); consumer `app/src/pages/analytics/archive/[year]/[edition]/[slug].astro:55-74`.
- **Evidence:** registry validation accepts any well-formed, mutually-equal hash; the build verifies prose bytes, not the evidence artifact named by `evidencePath`/`artifactSha256`. Unit tests accept a synthetic hash (`app/tests/unit/edition-registry.test.ts:257-304`).
- **Impact:** an "approved" edition can cite a stale or never-matching evidence hash and still publish. This weakens the documented attestation contract; it does not show any current scientific conclusion is wrong.
- **Fix:** give each approved edition an explicit evidence-artifact path and verify its canonical hash at build time (or an equivalent mandatory release validation), keeping the prose pin separate.
- **Test:** stale hash and missing artifact must fail the build; prose-pin behaviour unchanged.

### REL-3 — Evidence-producer reproducibility checks are never run by CI

- **Paths:** `.github/workflows/ci.yml:11-159` (jobs: lint, typecheck, security, catalog, test, frontend, e2e — no evidence job); drift record `docs/implementation/2026-11-22-dependency-audit.md:132-148`.
- **Evidence:** re-running five safe producers failed at this baseline (`lease_decay`, `mrt_impact`, `school_quality`, `price_forecasts`, `findings`); `school_quality` drifted in more keys than the record lists. `spatial_hotspots` was deliberately not run because its check rewrites a tracked asset (`:150-153`).
- **Impact:** approved editions' reproducibility decays silently between audits; nothing fails until someone re-runs a producer by hand. Distinguish scan/source-hash drift from changed measured values — no conclusion about scientific validity is drawn here.
- **Fix:** decide per producer (re-pin with review, or scope the scan), then add a CI job for the read-only checks and make the one write-side-effect check non-mutating.
- **Test:** CI fails when a producer ledger no longer matches; the write-side-effect check is converted to compare-only.

### REL-4 — No frontend/supply-chain advisory gate, and the research group is outside the audited environment

- **Paths:** `.github/workflows/ci.yml:34-42` (`pip-audit --skip-editable` in a `--dev`-only environment); no `bun audit` step anywhere.
- **Evidence (`evidence/dependency-*.txt`):** core+dev = 165 deps, 0 advisories; all groups = 303 deps, 238 raw advisory records across 23 packages; `bun audit` = 110 raw records across 24 names (Astro 14, DOMPurify 21, KaTeX 1, Sharp 3). Raw records include duplicate/alias representations — not unique CVEs, and no reachability was established. No `astro:assets`/`<Image>`/AVIF usage found, so the Astro AVIF RCE advisory (`GHSA-26w7-cxv4-gfx2`) is not claimed reachable.
- **Impact:** advisories can accumulate unnoticed in the two scopes CI never audits. The Astro remediation crosses a major version and needs coordinated validation, so an unconditional gate would simply go red.
- **Fix:** add scoped audit jobs with a documented, reviewed exception list and a lockfile-upgrade runbook; keep the CI-parity gate as-is.
- **Test:** the new job reports the locked findings and fails on an unlisted one.

### ARCH-1 — Type checking covers 11 entries; 19 source modules are outside it

- **Paths:** `pyproject.toml:149-161` (`files = [...]`, `# strict = true` still commented).
- **Evidence:** measured against `src/egg_n_bacon_housing/**`: 19 modules are untyped-checked, including every `schemas/*`, `utils/validation.py`, `utils/bronze.py`, `utils/output_registry.py`, `utils/data_loader.py`, `utils/school_features.py`.
- **Impact:** the schema/validation/bronze boundary — exactly where CORE-1/CORE-2 live — receives no static checking. `mypy` currently reports success on 29 files, which can be misread as whole-project coverage.
- **Fix:** add modules in batches (schemas → validation/bronze → remaining utils), keeping `mypy` green per batch; then raise strictness.
- **Test:** `uv run mypy` must still pass and must include the new files; add a guard test that every module under `src/` is listed or explicitly exempted.

### DOC-1 — The implementation ledger contradicts the shipped code

- **Paths:** `docs/implementation/README.md:7-8` (RF05 both in progress and complete), `:47` (RF00–RF12 "not started" while v2 loaders/defaults and the archive route ship), `:79` (catalog discrepancy described as shown while the page renders it only when counts differ); `app/src/pages/areas/[slug].astro:5` (comment claims no client island; two islands at `:213`, `:393`).
- **Impact:** a new engineer reading the ledger first will mis-scope work. No runtime effect.
- **Fix:** reconcile the ledger to the code, delete resolved chronology claims, and add the "status is evidence-backed" rule to the docs validator's scope.
- **Test:** `validate_docs_layout.py` extended, or a short checklist in the ledger's own header.

---

## LOW

### ARCH-2 — Two implementations of layer-path resolution

- **Paths:** `src/egg_n_bacon_housing/config.py:178-194`; `src/egg_n_bacon_housing/utils/layer_writer.py:49-59` ("mirrors `Settings.layer_paths`").
- **Impact:** a future layer or override rule must be changed twice; divergence silently writes a layer outside its registry path.
- **Fix:** one function; the other delegates. Add an equivalence test over all `_LAYER_KEYS` with relative and absolute overrides.

### DEP-1 — Declared dependencies with no executable reference

- **Paths:** `pyproject.toml:18` (`rapidfuzz`), `:35` (`pytest-mock`), `:36` (`pytest-asyncio`), `:50` (`cachetools`).
- **Evidence:** zero matches in `src/`, `scripts/`, `tests/`, `app/src/` for `rapidfuzz`/`fuzz`, `mocker`, `asyncio`, `cachetools`. Scan caveat: absence of a textual reference is not proof of unusedness.
- **Impact:** extra install surface and maintenance; `pytest-mock`/`pytest-asyncio` also imply fixtures that no test uses.
- **Fix:** confirm with the owning team, remove, run the full suite and the lock diff.

---

## Rejected candidates (checked, not filed)

- Cross-process bronze atomic writes and the manifest lock: unsafe only under overlapping runs, and serial execution is a documented decision (`docs/guides/operations-runbook.md:66-95`).
- `LayerWriter` atomic writes: UUID sibling temporaries; no collision established.
- `scripts/99_cleanup.py` cache clearing and quarantine retention: intentional and documented.
- Sample validation policy (warn-only precheck, unsampled rows not pydantic-validated): explicit, documented policy with a `full`/`fail` escape hatch and tests (`tests/test_validation_gateway.py:49-140`).
- Spatial memory scaling: unique-location reduction and batched joins; no measured failure.
- Astro/DOMPurify advisories as exploitable here: static output, no `astro:assets`, trusted repository markdown; no reachable path established.
- Leaflet tooltip HTML interpolation (`app/src/components/dashboard/PriceMap.tsx:388-459`): real unsafe sink, but every current input is a static published asset. Hardening recommended inside UI-2's workstream; not filed as XSS.
- Optional/financing input exfiltration: inputs stay in React state, the URL serializer omits them, no fetch/storage/log in the inspected path.

## Gaps for this phase

Exhaustive per-entry semantic review of all 2,596 entry-point rows and 596 error-surface rows was not performed. No live provider, bucket, CI-settings or deployment access. No load test, no runtime profiling, no assistive-technology matrix, no penetration test. Dependency maintenance/licence and other-platform audit results are incomplete. `spatial_hotspots` producer check not run (write side effect).
