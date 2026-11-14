# RF04 report — v2 observed period pack (pipeline side)

- **Date:** 2026-11-13
- **Status:** **Complete for RF04.** Pipeline side, client resolver, verified-byte loader, `validate-data` v2 checks and the rollout selector are implemented and tested. The pack itself is **not published**; the shipped release is still v1 (`PUBLIC_OBSERVED_RELEASE` defaults to `legacy`).
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §5 · [handoff](../plans/2026-11-12-reporting-refresh-handoffs.md) RF04
- **Decisions:** D01 (v2 sidecar), D02 (cutoff 2026-10), D11 (coverage disposition)
- **Inputs:** [RF03 candidate](2026-11-13-rf03-source-reconciliation.md) `9605fceca35c…`

## 1. What exists now

`scripts/v2_observed.py` — separate supported exporter over the platinum outputs; the v1 path is untouched.

| Piece                   | Behaviour                                                                                                                                                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `build_periods(cutoff)` | Concrete `month`, `ytd`, `ttm` and completed-`year` descriptors with inclusive bounds, explicit month lists and comparator IDs. A December cutoff closes that year; a January cutoff never invents a new-year YTD. |
| Comparator publication  | A comparator period is published only when **every** month it needs is covered, so no comparison is computed from a partial window.                                                                                |
| `build_observations`    | National (`SG`) + every planning area × 4 property types × every period. Counts and medians are computed from transactions for the whole window — never from monthly medians.                                      |
| Null/zero contract      | `transactionCount` counts rows; `medianPrice` uses its own price-observation count; `medianPsf` drops null/non-positive values and reports its own count. Zero rows → `no-sales` with null medians.                |
| Dispositions            | Default `limited-display`. `all` inherits the weakest constituent, so EC/condo limits cannot be laundered through the combined scope.                                                                              |
| Pack emission           | `observed/<generation>/periods.json.gz`, `observed/<generation>/summary.json.gz`, then `dashboard-release-v2.json` last. Payloads are deterministic gzip (mtime 0) and canonical JSON.                             |
| Identity                | `generation = sha256(schema + method + cutoff + input hash + role hashes)`. Payloads never embed their own generation, so verification is not circular.                                                            |
| `verify_pack`           | Recomputes the generation, re-hashes every asset, detects size/hash/corrupt-gzip tampering and any payload that embeds its own generation.                                                                         |

CLI:

```bash
uv run python scripts/v2_observed.py --last-complete-month 2026-10 \
  --output-dir /tmp/rf04-v2 --scope-status hdb=publish \
  --scope-status ec=limited-display --scope-status condo=limited-display
uv run python scripts/v2_observed.py --output-dir /tmp/rf04-v2 --verify-only
```

## 2. Real candidate result

Generation `6cd4510f26eca3fd…`, cutoff `2026-10`, **1,472 observations**, 8 periods, 60 KB total.

| Period                                                        | Window            | Comparator      |
| ------------------------------------------------------------- | ----------------- | --------------- |
| `month_2026_10`                                               | 2026-10           | `month_2025_10` |
| `ytd_2026_10`                                                 | 2026-01 → 2026-10 | `ytd_2025_10`   |
| `ttm_2026_10`                                                 | 2025-11 → 2026-10 | `ttm_2025_10`   |
| `year_2025`                                                   | 2025-01 → 2025-12 | `year_2024`     |
| `month_2025_10` · `ytd_2025_10` · `ttm_2025_10` · `year_2024` | comparators       | —               |

Spot checks against independent numbers:

- `SG / hdb / month_2026_10` → **2,173 sales, S$650,000, 600.8 psf** (matches RF03 trends)
- `SG / condo / month_2026_10` → 2,392 sales, S$2,341,750, 2,508 psf, disposition `limited-display`
- `PUNGGOL / hdb / year_2025` → **1,538 sales, S$672,000, 686.7 psf** (matches the RF01 regression fixture)
- `SG / all / ttm_2026_10` → 52,053 vs `ttm_2025_10` 84,261 — the unresolved EC/condo volume question from RF03 is visible rather than smoothed away.

`all` is `limited-display` because a constituent is; HDB alone is `publish`.

## 3. Verification

```bash
uv run pytest tests/test_v2_observed.py tests/test_reporting_baseline.py tests/test_export_app_data.py --no-cov -q   # 84 passed
uv run mypy scripts/v2_observed.py scripts/tools/verify_reporting_baseline.py    # clean
uv run ruff check && uv run ruff format --check scripts/                          # clean
uv run python scripts/tools/verify_reporting_baseline.py --assets                # 72 pinned assets unchanged
```

30 new tests cover: October/January/December/leap boundaries, comparator-only-when-covered, invalid months, reversed bounds, duplicate IDs, transaction-level medians vs monthly medians, null PSF exclusion, zero-sales vs missing windows, disposition defaults and `all` inheritance, deterministic bytes, generation sensitivity, non-circular payloads, tamper detection and sanitizer bool/null handling.

v1 is unchanged: no file under `app/public/data/` was modified, and the exporter's 44 existing tests still pass.

## 3b. Client resolver (added)

`app/src/utils/observed-periods.ts` — pure, no fetch/DOM/React:

| Export                                                 | Purpose                                                                                                                                                                                                                                                                             |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `parsePeriodPack(periods, summary)`                    | Validates both payloads and indexes them. Rejects wrong schema, disagreeing cutoff, duplicate period ids, months that disagree with bounds, observations pointing at unpublished periods, and `no-sales` carrying a price. Returns `{ok:false, errors}` rather than a partial pack. |
| `resolvePeriodAlias(pack, "latest" \| "ytd" \| "ttm")` | Resolves through the loaded pack only — never the browser clock.                                                                                                                                                                                                                    |
| `DEFAULT_ALIAS_BY_SURFACE`                             | The ratified D03 defaults: dashboard `ytd`, trends/explorer/rankings `ttm`.                                                                                                                                                                                                         |
| `findObservation`                                      | Keyed lookup; `null` when the scope is not published.                                                                                                                                                                                                                               |
| `compareWithComparator`                                | Returns per-metric absolute/percent change plus a `skipped` list with reasons (not observed, value unavailable, unit mismatch, zero denominator). Returns `null` when the period declares no comparator or the comparator observation is absent.                                    |
| `isPublishable` / `scopeNote`                          | Disposition gating and reader-facing explanations.                                                                                                                                                                                                                                  |
| `coveredMonths` / `cutoffUnobserved`                   | Freshness derived from the pack, not from a timestamp.                                                                                                                                                                                                                              |

Fixture: `app/tests/fixtures/v2-pack/` is a trimmed real pack (generation `6cd4510f…`, national + 3 areas, 128 observations). 26 unit tests cover parsing, rejection paths, alias resolution, comparisons, dispositions and coverage. The resolver reads Punggol HDB 2025 as **1,538 sales / S$672,000**, matching the Python emitter and the RF01 fixture.

```bash
cd app && bun run test:unit        # 389 pass (334 baseline + 55 since)
cd app && bun run astro check      # 0 errors, 0 warnings, 22 hints
```

## 3c. Verified-byte loader and rollout switch (added)

`app/src/utils/observed-pack-loader.ts`:

| Piece                                   | Behaviour                                                                                                                                                                       |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `parseV2Manifest`                       | Validates schema, 64-hex generation, safe relative paths, exactly the required roles, and that `identity.roles[role]` equals the asset hash.                                    |
| `computeV2Generation` / `canonicalJson` | Reimplements the Python canonical identity hash in TS; a golden vector from `scripts/v2_observed.py` is asserted in tests, so the two sides cannot drift.                       |
| `loadObservedPack`                      | Fetches the **exact** bytes, checks length + sha256, decodes _those_ bytes, then parses. Returns `ready` / `absent` (404) / `invalid` (anything else). No refetch, no fallback. |
| `sha256Hex`                             | Web Crypto digest over an ArrayBuffer-backed copy; throws rather than skipping verification when Web Crypto is unavailable.                                                     |

`app/scripts/validate-data.mjs` now also verifies a published v2 pack when the manifest exists: generation recomputation, per-payload size/hash, gunzip+JSON parse, period bounds/uniqueness/comparators, observation→period references, and the `no-sales` ⇒ zero-count/no-price rule. When the pack is absent it prints `v2 observed pack: not published (legacy release only)` and does not fail.

`app/src/config/observed-release.ts` holds the build-time switch `PUBLIC_OBSERVED_RELEASE` (default `legacy`) plus `resolveObservedReleaseMode()` so the rollout order in plan §5.5 is explicit rather than implied.

```bash
cd app && bun run test:unit      # 403 pass (26 resolver + 14 loader + 363 prior)
cd app && bun run astro check    # 0 errors, 0 warnings, 22 hints
cd app && bun run validate-data   # 19 assets, v1 release verified, v2 reported absent
```

## 4. Not done (deferred on purpose)

| Item                                        | Why it is separate                                                                                                          |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Publishing the pack into `app/public/data/` | A publication step (RF12), not code: copy `observed/<generation>/…` + `dashboard-release-v2.json`, then run `validate-data` |
| Wiring surfaces to the loader               | RF05; the loader, resolver and switch are ready                                                                             |
| `manifest.json` entry for v2 assets         | Only needed when the pack is published; `validate-data` already verifies it standalone                                      |
| `generatedAt` in the manifest               | Deliberately null: a timestamp inside the identity would break reproducible hashes; it belongs in the deployment record     |

The pack lives in `/tmp/rf04-v2` and is **not** part of `app/public/data/`; nothing is published and v1 remains the served release.

## 5. Suggested next step

RF04b: freeze the TS types against this payload and write the resolver + parity tests (Python-generated golden vectors), then wire `validate-data` to verify a v2 pack when present. That keeps RF05 startup to wiring rather than schema discovery.
