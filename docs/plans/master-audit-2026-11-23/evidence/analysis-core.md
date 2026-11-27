Agent: 8684b06a-e5c1-453
Type: Agent | Status: steered (wrapped up at the turn limit — output may be partial) | Tool uses: 66 | 124.5k token | Context: 24% | Duration: 251.8s
Model: openai-codex/gpt-6.1-sol, thinking: high
Description: Audit pipeline correctness and state

## Scope and evidence

- Verified HEAD: `449b921d499a8c55ec1eacb1a423baa7632456d3`.
- Read both repository pipeline/ingestion skills. No production edits, commits, delegation, live requests, or secret-file reads.
- Executed hermetic probes from a fresh `/tmp` working directory with cleared environment and blocked live transport.
- Reproducer: `/tmp/master-audit-core-poc.py`
- Results: `/tmp/master-audit-core-results.json`
- Six provisional findings below. Scores use impact × likelihood; no critical finding.

### CORE-1 — Cached geocodes bypass condo project-plausibility checks

**HIGH — impact 4, likelihood 4, score 16 — CONFIRMED**
**Category:** correctness / cache-contract violation
**Paths:** `src/egg_n_bacon_housing/utils/geocoding.py:190-410` (`_empty_row`, `_geocode_via_api`); `components/cleaning.py:419-454` (`_accept_plausible_project_coords`).

**Evidence:** The warm-cache branch retrieves coordinates only, then supplies `_empty_row(addr)` metadata. Its `address` is the original query—not OneMap’s matched address. Condo validation consequently checks project/street tokens against its own query.

The probe returned an unrelated project result:

- Cold run: project result rejected; street fallback produced `(1.33, 103.83)`.
- Warm run: the same rejected project coordinates `(1.31, 103.81)` were accepted.
- Warm metadata: `matched_name=null`, `address="ORCHID RESIDENCES EXAMPLE ROAD Singapore"`.

**Reachability/conditions:** A project-aware query receives a coordinate-bearing but implausible result, which the adapter caches. Recomputing geocoding while that entry remains valid triggers the bypass; no concurrent execution is required.

**Impact:** Repeat runs change spatial attribution and proximity features, accepting a match deliberately rejected on the first run. Coordinate coverage still passes.

**Minimal fix:** Return cached response metadata through the same `_row_from_result` conversion used for fetched results. Never substitute query text for matched-address evidence.

**Focused test:** Run `geocoded_properties` twice with a real temporary `CacheManager` and mocked unrelated OneMap result. Assert both runs reject that project result and produce identical fallback coordinates. Current cache tests assert coordinates, not metadata/plausibility equivalence.

### CORE-2 — Successful malformed pagination publishes and permanently caches partial datasets

**HIGH — impact 4, likelihood 3, score 12 — CONFIRMED**
**Category:** ingestion integrity
**Paths:** `src/egg_n_bacon_housing/adapters/datagovsg.py` — `fetch_datagovsg_dataset`, missing-records `break` and terminal concatenation; `components/ingestion/datagov.py:109-125`.

**Evidence:** After collecting a page, a subsequent HTTP-200 payload without `result.records` exits pagination normally. The adapter returns accumulated rows instead of raising `IncompleteDatasetFetchError`.

Probe:

- Page one advertised four records and supplied two plus a next link.
- Page two returned `{"success":false,"error":…}`.
- Required ingestion returned two rows, persisted two rows, and recorded a fresh two-row manifest.
- The next invocation served those two rows directly from bronze.

**Reachability/conditions:** A paginated source returns an application-level error/malformed success response after at least one valid page. Missing terminal links also lack a final advertised-total reconciliation. Existing tests cover HTTP failures after pagination and missing records on the _first_ page, not this combination.

**Impact:** Incomplete transaction/reference populations become ordinary non-expiring bronze cache hits. Required-source and empty-response guards do not catch nonempty partial data.

**Minimal fix:** Treat malformed page envelopes as fetch failures, including after accumulated pages. Reconcile fetched count against the source’s applicable total before returning; reject non-progressing pagination.

**Focused test:** Valid first page followed by HTTP-200 error envelope must raise and create no bronze parquet/manifest. Add advertised-total/early-terminal and repeated-next-link cases.

### CORE-3 — Size tolerance silently suppresses real changes in both sync directions

**HIGH — impact 4, likelihood 4, score 16 — CONFIRMED**
**Category:** persistence / integrity
**Paths:** `scripts/00_sync_data.py:121-127,170-179,226-239`.

**Evidence:** Upload/download skip differences below 100 bytes; verification reports differences up to 100 bytes as OK. Content is never compared.

Probe:

- Local: `"price\n1\n"` — 8 bytes.
- Remote: `"price\n2\n3\n"` — 10 bytes.
- Download: zero transfers.
- Upload: zero transfers.
- Verify: `1 OK … 0 size mismatches`.

Thus even a detectable size change containing an added record is ignored. Equal-length corrections are also undetectable.

**Reachability/conditions:** Any source/cache correction preserving size or changing it by fewer than 100 bytes. This requires neither corruption nor concurrency.

**Impact:** Corrected manual inputs or geocodes fail to propagate; verification provides false reassurance, and backups can retain superseded values indefinitely.

**Minimal fix:** Remove size tolerance. For content integrity, compare a stored checksum or trustworthy object checksum, not size alone. Offer explicit overwrite/repair behavior.

**Focused test:** Different-size changes of 1/99/100 bytes and equal-size differing contents must not be classified unchanged/verified.

### CORE-4 — R2 object names escape local roots and violate flat-geocache exclusion

**MEDIUM — impact 4, likelihood 2, score 8 — CONFIRMED**
**Category:** security / path containment
**Paths:** `scripts/00_sync_data.py:103-111,165-172,191-194`.

**Evidence:** Object keys are converted directly to local paths after `removeprefix`, without validating the prefix boundary, relative components, resolved containment, or flat-geocache shape.

Safe probe, entirely inside a disposable directory:

- `manual/../escaped.txt` wrote outside the manual root.
- `geocache/hamilton/injected.json` wrote inside the explicitly excluded Hamilton subtree.

**Reachability/conditions:** A malformed/malicious object exists under the listed prefix and an operator downloads it. Exploitation requires influence over bucket contents; no unauthenticated bucket access was established. Existing local symlinks provide another containment concern, not separately reproduced.

**Impact:** Remote data synchronization can overwrite files outside its intended data root with the operator’s permissions. Geocache download accepts paths excluded by upload.

**Minimal fix:** Require exact `prefix/`; reject absolute paths and `..`; resolve and enforce root containment, including symlink handling. For geocache, allow only a single filename with an approved suffix.

**Focused test:** Reject traversal, absolute remainder, prefix siblings, nested geocache/Hamilton keys, and escaping symlinks before submitting any transfer.

### CORE-5 — Failed scheduled refresh becomes a successful no-op instead of retrying

**MEDIUM — impact 3, likelihood 3, score 9 — CONFIRMED**
**Category:** operational recovery
**Paths:** `scripts/40_refresh_rolling.py:157-166,235-242`; `src/egg_n_bacon_housing/utils/bronze.py:379-429`.

**Evidence:** `--stale-only --run` uses the number of deleted parquets to decide whether work is needed, rather than selected stale/missing datasets.

Probe:

1. A 40-day-old HDB parquet was selected and deleted.
2. Mocked pipeline failed before rewriting it: exit 1.
3. Repeating the identical scheduled command returned exit 0 without invoking the pipeline.
4. The parquet remained missing and `stale_names()` still selected it.

**Reachability/conditions:** Refresh invalidation succeeds, but fetching fails before bronze replacement. The old manifest remains, so subsequent selection remains stale; deletion returns an empty list.

**Impact:** The documented scheduled recovery command stops retrying the failed refresh and falsely reports success. Missing source data persists until manual intervention or another source happens to trigger a run.

**Minimal fix:** Separate selected work from removed-file reporting. Run when any selected dataset needs recovery, even if its parquet is already absent.

**Focused test:** Execute the scheduled command twice: first mocked fetch failure, second mocked success. Assert two pipeline invocations and recovered bronze.

### CORE-6 — Parallel geocoder pacing releases a burst rather than spaced requests

**MEDIUM — impact 2, likelihood 4, score 8 — CONFIRMED**
**Category:** concurrency / external-service reliability
**Path:** `src/egg_n_bacon_housing/utils/geocoding.py:190-227` (`_RateLimiter.wait`).

**Evidence:** Each caller assigns `_next_slot = now + interval`, discarding reservations made by previous waiting callers.

Five simultaneous callers with an 80 ms interval returned at:
`0.00000, 0.08008, 0.08013, 0.08016, 0.08019` seconds.

The last four were separated by approximately 30–50 microseconds, not 80 ms.

**Reachability/conditions:** Multiple cold-cache requests use `max_workers > 1`; defaults are five workers and 1.2-second pacing. This is supported in-process concurrency, not unsupported overlapping pipeline runs.

**Impact:** Configured request spacing is violated, increasing burst/rate-limit risk and potentially degrading geocode coverage. Actual upstream throttling was not tested.

**Minimal fix:** Reserve `slot = max(now, _next_slot)`, advance from `slot`, and sleep until the reserved slot.

**Focused test:** Assert actual release spacing with a deterministic clock/reservation model. The current parallel pacing test replaces `wait()` and checks invocation count only.

## Rejected or insufficient candidates

- **Cross-process bronze atomic writes:** Fixed `.tmp` parquet/manifest names and a process-local manifest lock are unsafe under overlapping processes. Not promoted: no supported overlapping execution was established; documented serial operation must not be relabeled accidental.
- **LayerWriter atomic writes:** Uses UUID sibling temporary files; no equivalent collision established.
- **`99_cleanup.py`:** Full flat-cache deletion and age-based quarantine removal are intentional/documented. No independently demonstrated defect.
- **Sample validation:** Warn-only vectorized diagnostics and unvalidated nonsampled rows are explicit policy. Not a finding.
- **Required fields/time:** Traced required-null quarantine, Pydantic fallback, month/date agreement, and injected freshness date. No sufficiently reachable additional defect established.
- **Spatial memory scaling:** Traced unique-location reduction, BallTree/KDTree nearest-neighbour computation, and batched polygon joins. No dense property×amenity allocation or measured memory failure established.
- **Architecture:** Confirmed registry-driven materialization and six terminal outputs. No measured cycle, harmful fanout, or three-copy implementation justified a structural finding.

## Coverage limits

- Existing focused test bodies were inspected, but the test suite was **not rerun**; the six standalone probes executed successfully.
- Not exhaustively read: macro/GeoJSON/URA-CSV ingestion bodies, rental/profile nodes, all adapter tests, quality-monitoring internals, and cache-fingerprint implementation.
- No claims about live bucket keys, upstream incident frequency, real-data corruption, or end-to-end pipeline performance.
