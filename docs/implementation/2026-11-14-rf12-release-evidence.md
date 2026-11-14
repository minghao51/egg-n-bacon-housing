# RF12 release evidence — candidate identity, disposition, verification and rollback

- **Date:** 2026-11-14
- **Status:** **Deployed and probed 2026-11-14** on the owner's instruction. `bb42fa8` (the programme) and `7862b5d` (formatters, validation, secrets audit) are on `main`; `deploy.yml` run 43620352855 succeeded and the live site was probed in a browser (7/7). CI is green except the pre-existing `security` job (`pip-audit` findings in transitive dependencies, also red on the previous `main` run).
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §4 (milestones) · [handoff](../plans/2026-11-12-reporting-refresh-handoffs.md) RF12
- **Upstream identity records:** [RF04 pack](2026-11-13-rf04-v2-period-pack.md) · [RF09 history](2026-11-14-rf09-area-type-month-history.md) · [RF11 catalog](2026-11-13-rf11-catalog-report.md) · [RF08 editions](2026-11-14-rf08-editions-signoff.md)

## 1. What this candidate is, and is not

| Included                                                       | Identity                                                      |
| -------------------------------------------------------------- | ------------------------------------------------------------- |
| Observed dashboard on the v2 period pack (shipped build mode)  | `PUBLIC_OBSERVED_RELEASE=v2`; pack generation `2c30e2aa836c…` |
| Rolling-quarter periods + per-property monthly history (RF09)  | same generation, six roles                                    |
| Frozen edition archive + **two approved editions** (RF07/RF08) | `data-sources-2026-11-14`, `rental-yields-2026-11-14`         |
| Area activity on fieldnotes and in the explorer list (RF10)    | derived at build/runtime from the same generation             |

| Explicitly **not** in this candidate                 | Why                                                                                              |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 13 of 15 studies as current research                 | Still `historical` with no sign-offs; each needs its own evidence pack, text and reviewer (D12). |
| Directional activity labels, map colouring by change | Owner decision pending; RF09 §3.4 is a proposal, not a decision.                                 |
| EC/condo growth or ranking headlines                 | RF03 volume discontinuity unresolved; both scopes stay `limited-display`.                        |
| Per-area fieldnote slices deferred from RF06         | Not built; the activity block and on-request history cover the reader need.                      |
| Any deployment                                       | Requires separate permission (D10). No host was touched.                                         |

A reader of a partial delivery must be able to tell it is partial: every series without an
approved edition says **"No approved current edition"** on its own page, and the archive
renders its status panel from the registry.

## 2. Candidate identity (measured in this tree)

### 2.1 v1 release — frozen, served unchanged

- Generation `0e1013ee485fe085874f2ef53ece8eb5f4f47305985ba991eda5fc753e4e0c27`, `generatedAt 2026-11-03T14:27:33Z`
- Manifest `app/public/data/dashboard-release.json`, sha256 `8ef738a59aa1e1b5…`, 8,125 bytes
- Observation range 1990-01 → 2026-10, complete year 2025, `trailingMonth.resolvedFrom: declared`
- 7 assets, 31,418 bytes total:

| Asset                           |  Bytes | sha256 (first 12) |
| ------------------------------- | -----: | ----------------- |
| `dashboard_overview.json.gz`    |    718 | `022471a97e4b`    |
| `dashboard_trends.json.gz`      |  5,728 | `b47ac8b5f436`    |
| `dashboard_segments.json.gz`    |  6,080 | `69d7a3d26645`    |
| `dashboard_leaderboard.json.gz` |  4,720 | `be99ba6b610b`    |
| `map_metrics.json.gz`           | 11,293 | `8cc21cb3af69`    |
| `hotspots.json.gz`              |  1,090 | `7b68e505f174`    |
| `amenity_summary.json.gz`       |  1,789 | `80530f355a14`    |

### 2.2 v2 observed pack — the shipped current-period contract

- Generation `2c30e2aa836c140a619883c94a0eb8b54d8812f931380b40426b9bf4c82a6fb6`
- Schema `2.1.0`, method `observed-aggregates-2`, cutoff `2026-10`, 10 periods, 1,840 observations
- Manifest `app/public/data/dashboard-release-v2.json`, sha256 `d91857e3351225d0…`, 2,359 bytes
- 6 assets, **570,224 bytes** total:

| Role                 |   Bytes | sha256 (first 12) |
| -------------------- | ------: | ----------------- |
| `periods`            |     560 | `fac8170fd9e7`    |
| `summary`            |  49,635 | `e1abd607d684`    |
| `area-monthly-hdb`   | 217,320 | `8d9bd5af61ae`    |
| `area-monthly-all`   | 233,722 | `6cb06163009a`    |
| `area-monthly-condo` |  49,887 | `ac743afd5c09`    |
| `area-monthly-ec`    |  19,100 | `22ef2c8108ae`    |

Only `periods` + `summary` (50,195 bytes) are verified eagerly; a monthly payload is fetched
and hashed on demand (fieldnote history is opt-in per reader — RF10 §6).

### 2.3 Catalog — pin the **post-build** artefact

`bun run build` runs `sync-catalog.mjs`, whose gzip encoder differs from
`generate_catalog.py`, so a pre-build pin would not describe what ships (RF11 §7).

| Artefact                                        |   Bytes | sha256              |
| ----------------------------------------------- | ------: | ------------------- |
| `app/public/data/catalog.jsonl.gz` (post-build) |  30,414 | `a67f2f6807f32c31…` |
| `data/catalog/catalog.jsonl` (generator output) | 482,236 | `b1b135a075cd266b…` |

RF11 recorded the generator's `7f75527f…` for the pre-build artefact; that record stands
for what it measured. Release evidence pins the post-build bytes above.

### 2.4 Approved editions

| Series          | Edition                    | Frozen text sha256                                                 | Evidence ledger       |
| --------------- | -------------------------- | ------------------------------------------------------------------ | --------------------- |
| `data-sources`  | `data-sources-2026-11-14`  | `bde11c61b720c2504cdf78bde9238c5e57925e319457d52356cde0bcdeeafb81` | RS01 `65ce7a10…e8ae`  |
| `rental-yields` | `rental-yields-2026-11-14` | `f6b0bd9d811bb9b348b0e897b66a482add281e38f2803c61193978c97ca0ab67` | RS02 `db134525…f0313` |

Each carries three distinct attestations (source/cutoff, scientific, publication) on one
evidence hash, and the archive route re-hashes the frozen text at build time — a drifted
edition fails `bun run build`.

## 3. Asset disposition

| Asset                                             | Disposition                                                                 | Evidence                                                                                                        |
| ------------------------------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| v1 payloads (7)                                   | **frozen**, served unchanged                                                | generation `0e1013ee485f…`; `verify_reporting_baseline.py --assets` → 72 pinned files pass                      |
| RF00 frozen studies + manifest                    | **frozen**                                                                  | `docs/analytics/editions/legacy/2026-11-12/`, 15 sources byte-identical                                         |
| v2 pack generation `2c30e2aa…`                    | **published** (replaced `6cd4510f…` at RF09)                                | `validate-data` verifies 6 roles + 47,104 month cells                                                           |
| RF04 generation `observed/6cd4510f26ec…/`         | **retained, unreferenced**                                                  | still on disk; retained for bookmark/rollback review                                                            |
| `catalog.jsonl(.gz)`                              | **regenerated** (authorized RF11 output, post-build bytes pinned above)     | RF11 §6/§7                                                                                                      |
| `unified_dataset.parquet`                         | inspected source, unchanged                                                 | sha256 `39d234f703c9d6e0…` (matches the v2 pack's recorded input)                                               |
| `interactive_tools/affordability_metrics.json.gz` | **retained, unused**, outside every manifest (2,282 bytes, `c9addb2711a3…`) | owner confirmed retention on 2026-11-14; removal still needs a data-boundary decision and was **not** performed |
| `planning_areas.geojson(.gz)` + reference assets  | unchanged                                                                   | not re-pinned here; RF11 records the provenance review                                                          |
| Edition frozen texts                              | **new immutable paths**                                                     | legacy originals untouched                                                                                      |

## 4. Verification performed (this tree, this date)

```bash
uv run python scripts/tools/validate_docs_layout.py                          # no findings
uv run python scripts/tools/source_inventory.py --check                      # Pass: RS01 ledger matches the tree
uv run python scripts/tools/rental_yield_evidence.py                          # re-measured; ledger hash unchanged
uv run python scripts/tools/verify_reporting_baseline.py --assets             # 15 frozen sources, 72 pinned assets, bytes match
uv run pytest tests/test_research_evidence_tools.py tests/test_rental_yield_metrics.py --no-cov -q   # 25 passed
uv run ruff check && uv run ruff format --check scripts/                       # clean / 14 formatted

cd app && bun run test:unit            # 534 passed, 0 failed (34 files)
cd app && bun run astro check          # 0 errors, 0 warnings, 22 hints
cd app && bun run validate-data        # v1 0e1013ee485f (7 assets); v2 2c30e2aa836c (10 periods, 1,840 observations); 4 monthly payloads, 47,104 cells
cd app && bun run build                # 221 pages
cd app && bunx playwright test tests/e2e --workers=4   # 237 passed / 9 skipped
cd app && bun run build:pages          # 221 pages, repository base prefix
cd app && bunx playwright test tests/e2e/pages-base.spec.ts   # 9 passed (raw .gz bytes under /egg-n-bacon-housing/)
```

No test was skipped silently: the 9 skips are the pre-existing conditional group (documented
in the handoff), not failures. No command above was reported without being run.

### 4a. `Content-Encoding` on the pinned `.gz` payloads — measured, not assumed

A `.gz` file on disk is _compressed bytes_, and the v2 manifest pins the sha256 of exactly
those bytes. What a browser hands to `fetch(...).arrayBuffer()` depends on the response
headers, not on the file name:

| Server                                        | Headers on `periods.json.gz`                                   | Body the browser hashes                               | Matches the pin?                                                 |
| --------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------- |
| `bun run preview` (Vite)                      | `Content-Type: application/json`, **`Content-Encoding: gzip`** | 2,465 bytes decompressed JSON, sha256 `58e4b4dcc11b…` | **No** — `/explore` shows the fail-closed "did not verify" state |
| `scripts/serve-pages-base.mjs` (Pages-shaped) | `Content-Type: application/gzip`, **no** `Content-Encoding`    | 560 raw gzip bytes, sha256 `fac8170fd9e7…`            | **Yes**                                                          |
| **`https://minghao51.github.io`** (live)      | `content-type: application/gzip`, **no `Content-Encoding`**    | 560 raw gzip bytes, sha256 `fac8170fd9e7…`            | **Yes**                                                          |

`Content-Encoding: gzip` tells the browser "this is a gzip-encoded _representation_", so it
inflates the body transparently; `curl` without `--compressed` shows the raw bytes and hides
the difference, which is why this is easy to miss. The comparison in the table is the same
URL fetched both ways: raw bytes hash to the pinned value, the decompressed body does not.

**Measured on the deployed host (2026-11-14):** GitHub Pages returns the raw bytes with
`content-type: application/gzip` and no `Content-Encoding`, so the browser hashes exactly what
the manifest pins. The contract holds in production and **no hash-basis change is needed**; the
only divergence is the local preview server, which is why pack-path tests keep using
`tests/e2e/utils/servePackBytes.ts` (handoff trap #12).

A browser probe of the live site confirmed the consequence rather than assuming it: `/explore`
verifies the pack and opens on `ttm_2026_10`, a rolling-quarter window shows its prior-year
sentence, `/areas/punggol` renders the activity table and loads its monthly history through the
manifest, `/analytics/data-sources` offers the approved edition, its archive route renders with
three sign-offs, and `/dashboard` (v1) is unchanged.

Original reasoning, kept because it explains the pin: consequences, if the deploy host behaved like preview: the fix is **not** to loosen the hash.
Either the host must stop re-labelling `.gz` assets, or the manifest must pin a hash of the
_decoded payload_ (an RF04/RF12 contract change with its own migration). Until that is
measured on the host, this stays an open release gate rather than a passed one.

## 5. Rollback

| Layer       | Rollback identity                                                                   | Exercised?                                                    |
| ----------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| v1 payloads | unchanged (`0e1013ee485f…`) — nothing to roll back                                  | n/a                                                           |
| v2 pack     | previous generation `observed/6cd4510f26ec…/` and its manifest are still on disk    | **Not exercised in production** — no deployment has been made |
| Ship mode   | `bun run build:legacy` reproduces the pre-flip build (verified during RF05)         | Verified locally at RF05                                      |
| Catalog     | regenerate with `uv run python scripts/generate_catalog.py`, then rebuild           | Verified at RF11                                              |
| Editions    | registry entries can be reverted to `historical`; the frozen texts stay addressable | Verified by unit tests (validator rejects partial records)    |

A rollback that has never been executed against the real host is not evidence of a working
rollback. This table records identities, not a rehearsal.

## 6. Open items blocking a _deployed_ release

| #   | Item                                                                                                                                                                                          | Owner / gate                                                             |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 1   | ~~Confirm the **deploy host** serves `observed/**/*.json.gz` without `Content-Encoding`~~ — **measured live 2026-11-14**: raw bytes, no `Content-Encoding`, sha256 matches the pin. Resolved. | done                                                                     |
| 2   | Exercise the rollback path against the live host (identities recorded in §5; the exercise has not been run)                                                                                   | Owner; needs a maintenance window                                        |
| 3   | Decide the RF04 generation `6cd4510f…` retention horizon                                                                                                                                      | Owner; no deletion without a reference review                            |
| 4   | ~~Decide `interactive_tools/affordability_metrics.json.gz` retain/remove~~ — **retained** on owner instruction 2026-11-14                                                                     | any future removal needs a data-boundary approval and a reference review |
| 5   | 13 remaining studies need evidence + text + reviewer                                                                                                                                          | RF08 continuation                                                        |
| 6   | Directional activity labels / map colouring                                                                                                                                                   | Owner decision on RF09 §3.4                                              |
| 7   | Recurring refresh + auto-deploy runbook execution                                                                                                                                             | Separate approval                                                        |

## 7. Deploy gate

Deployment was authorised by the owner on 2026-11-14 and executed: the build artefacts,
manifests, editions and evidence hashes above are what is now published at
`https://minghao51.github.io/egg-n-bacon-housing/`, and the live probe confirmed the pinned
bytes are what the host serves. Rollback has **not** been rehearsed in production (§5), and
any further deployment (including a rollback) is a separate authorisation.
