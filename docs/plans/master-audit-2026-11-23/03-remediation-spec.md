# Phase 3 — remediation specification and next-agent handoffs

Baseline `449b921`. Findings: [02-findings.md](02-findings.md). Discovery and evidence: [01-discovery.md](01-discovery.md), [`evidence/`](evidence/). Handoffs: 11 work orders in [`handoffs/`](handoffs/README.md), dispatched in four waves.

## 1. Verdict

**CONCERNS — ship the site, gate the data plane.**

- The published static site is independently green at this baseline: 1,136 Python tests, 534 frontend unit tests, 237 E2E passed (9 skipped), 9 Pages-base E2E passed with the prefixed build, 234-page build, 95.53 % line coverage (no branch coverage), validators and the frozen 72-asset baseline all pass.
- No CRITICAL finding. No committed secret, no reachable public-server injection, no demonstrated auth surface — this repository ships a static site, not a server.
- Three HIGH findings (CORE-1, CORE-2, CORE-3) are data-integrity defects in the offline pipeline and R2 operations path. They do not affect what the site currently displays, but they do mean a future refresh can silently publish or restore wrong data. **They block the next authorised data refresh, not the site.**
- Thirteen MEDIUM findings are tracked debt of bounded blast radius: one path-containment gap, one recovery bug, one concurrency bug, one frontend trust-boundary gap, two accessibility/handoff gaps, one UI arithmetic bug, one release-gate gap, one evidence-integrity gap, one missing reproducibility control, one missing supply-chain control, one type-coverage gap, one documentation drift.

Why not PASS: CORE-1 and CORE-3 are silent, repeatable, and inside the path that produces every published number. Why not FAIL: none of them corrupts already-published output, and each has a small, testable fix.

## 2. Ship blockers (conditional)

No unconditional blocker exists. Two conditional gates:

| Gate                         | Condition                                                   | Minimal unblock                                                       |
| ---------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------- |
| Next authorised data refresh | Before any `--stage all` run whose output will be published | CORE-1 and CORE-2 fixed + their regression tests green (WS-A1, WS-A2) |
| Next R2 sync / data restore  | Before relying on the bucket as a backup or recovery path   | CORE-3 content verification and CORE-4 containment (WS-A3)            |
| Next Pages deploy            | Before the next production deploy                           | REL-1 Pages-base job required (WS-C1)                                 |

## 3. Quick wins (ordered by leverage ÷ effort)

| Rank | ID     | Change                                                                       | Effort | Why first                                                       |
| ---- | ------ | ---------------------------------------------------------------------------- | ------ | --------------------------------------------------------------- |
| 1    | CORE-6 | One-line reservation fix in `_RateLimiter.wait` + deterministic spacing test | S      | Stops burst traffic to OneMap on every cold run; near-zero risk |
| 2    | CORE-5 | Decide the rerun from "selected work", not "files removed"                   | S      | Makes the documented cron target actually retry                 |
| 3    | UI-4   | Zero-principal branch + stable rate arithmetic + finiteness guard            | S      | Removes a visible wrong error and `Infinity` output             |
| 4    | UI-3   | One handoff serializer sharing property/period/metric                        | S      | Fixes a scope-changing navigation that misleads readers         |
| 5    | ARCH-2 | Single layer-path resolver + equivalence test                                | S      | Removes a latent write-path divergence                          |
| 6    | REL-1  | Pages-base job in CI; deploy depends on it                                   | M      | Turns the one skipped suite into a real gate                    |
| 7    | UI-2   | Labelled area selector + metric label + pressed state                        | M      | Restores a whole keyboard path to the research map              |
| 8    | DEP-1  | Verify and drop unreferenced dependencies                                    | S      | Smaller install surface; needs owner confirmation               |

## 4. Phased roadmap

### Phase 0 — Immediate (this sprint)

| IDs            | Work package                 | Effort | Owner role        | Done when                                                           |
| -------------- | ---------------------------- | ------ | ----------------- | ------------------------------------------------------------------- |
| CORE-6, CORE-5 | Recovery and pacing fixes    | S      | Data engineer     | Spacing test asserts real gaps; two-invocation retry test passes    |
| UI-4           | Financing boundary hardening | S      | Frontend engineer | 100 % down and 1e-14 rate tests pass; no non-finite output possible |

### Phase 1 — Short term (2–4 weeks)

| IDs            | Work package                                 | Effort | Owner role        | Done when                                                                               |
| -------------- | -------------------------------------------- | ------ | ----------------- | --------------------------------------------------------------------------------------- |
| CORE-1         | Cached-geocode metadata contract             | M      | Data engineer     | Cold and warm runs produce identical coordinates and rejections                         |
| CORE-2         | Pagination completeness                      | M      | Data engineer     | Malformed later page raises; no parquet/manifest written; total reconciled              |
| CORE-3, CORE-4 | Sync integrity + containment                 | M      | Platform engineer | Content mode detects all four divergence cases; traversal keys rejected before transfer |
| UI-1           | Single verified-bytes load path              | M      | Frontend engineer | Displayed payload is the verified buffer; refresh re-verifies                           |
| UI-2, UI-3     | Map accessibility + scope-preserving handoff | M      | Frontend engineer | Keyboard-only inspection and scope-preserving navigation tests pass                     |
| REL-1          | Pages-base release gate                      | M      | Release engineer  | CI job fails on a broken prefix; deploy depends on it                                   |
| ARCH-1         | Extend type-check scope (schemas first)      | M      | Platform engineer | `mypy` green with schemas + validation + bronze included                                |

### Phase 2 — Medium term (next quarter)

| IDs   | Work package                            | Effort | Owner role                        | Done when                                                                                                   |
| ----- | --------------------------------------- | ------ | --------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| REL-2 | Evidence-artifact hash verification     | M      | Release engineer                  | Stale hash and missing artifact fail the build                                                              |
| REL-3 | Evidence-producer CI check              | M      | Release engineer + owner decision | Read-only producers gate CI; the mutating one is compare-only; drift either re-pinned with review or scoped |
| REL-4 | Scoped advisory gates + upgrade runbook | M      | Platform engineer                 | Frontend and all-group audits run with a reviewed exception list                                            |
| DOC-1 | Ledger reconciliation                   | S      | Tech writer                       | Ledger matches shipped code; stale chronology removed                                                       |
| DEP-1 | Dependency hygiene                      | S      | Platform engineer                 | Unreferenced packages removed, suite green                                                                  |

### Phase 3 — Long term (structural)

- **Data-contract versioning.** Bronze manifests carry `source`/`rows`/`fetched_at` only (`src/egg_n_bacon_housing/utils/bronze.py:118-128`). Add schema/source version + row-count reconciliation so CORE-2-class failures are detectable after the fact.
- **Pipeline observability.** No metrics endpoint or health signal exists; the only numeric telemetry is the SQLite quality DB. Add a run summary artifact (per-node row counts, validation policy, quarantine counts, durations) and surface freshness in `/catalog`.
- **Release-path unification.** One loader primitive for legacy + v2 packs (UI-1 is the first step) so verification and display cannot diverge again.
- **Onboarding.** Replace the chronological implementation ledger with a maintained map of surfaces → assets → invariants, keeping the ledger as history.

## 5. Work-package dependency graph

```
Phase 0 (parallel):  CORE-6 + UI-4 + CORE-5      [no shared files]
Phase 1 wave 1:      CORE-1 | CORE-2 | CORE-3+4 | REL-1 | ARCH-1
Phase 1 wave 2:      UI-1 -> UI-2+UI-3            [ExplorerWorkspace.tsx ordering]
Phase 2 wave 1:      REL-2 + REL-3 (same workflow file: one owner) | REL-4 | DOC-1 | DEP-1
```

File ownership is non-overlapping inside each wave; see each handoff's `Owns` block. `pyproject.toml` has exactly one owner (ARCH-1/DEP-1); `.github/workflows/ci.yml` has exactly one owner per wave (REL-1, then REL-2/REL-3/REL-4).

## 6. QoL and intuitiveness programme (cross-cutting)

These are the "make it obvious" items, each tied to a finding so they are verifiable rather than cosmetic:

1. **One command per task.** `scripts/00_sync_data.py` gains a documented `--verify` that means "check content, not size" (CORE-3), so operators stop guessing which flag proves the backup is good.
2. **Fail loudly, name the dataset.** CORE-2's error should carry dataset id, advertised total, fetched total and the offending URL — the pattern already used by `IncompleteDatasetFetchError`.
3. **One path resolver.** `Settings.layer_paths` and `resolve_layer_paths` collapse to one function (ARCH-2), so layer semantics have a single place to read.
4. **Honest verification labels.** `verify` must never print `OK` for unverified content; use `SIZE-OK / CONTENT-UNVERIFIED` (CORE-3).
5. **Ledger that matches reality.** DOC-1 removes the "not started" ceiling that no longer holds.
6. **Handoff parity.** The map→explore link keeps property and period (UI-3), so the UI stops silently re-scoping a reader's question.
7. **Type-check truthfulness.** `mypy`'s green must mean the schemas and validation boundary are covered (ARCH-1), not just 29 files.

## 7. Gap register

| Gap                                                                                                       | Why it exists                                                                                                                                                                                                                                                                                                                                          | Blocking?                              | How to close                                                                                                                                     |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| No live provider/bucket access                                                                            | Audit ran offline with mocks by design                                                                                                                                                                                                                                                                                                                 | No                                     | Staging credentials + a recorded contract test against data.gov.sg/OneMap                                                                        |
| No CI/branch-protection settings                                                                          | Outside repository                                                                                                                                                                                                                                                                                                                                     | No (REL-1 mitigated by job)            | Repo admin exports required-check configuration                                                                                                  |
| No live deployment verification                                                                           | Pages URL not exercised                                                                                                                                                                                                                                                                                                                                | No                                     | Run the deploy smoke block against the real URL after next deploy                                                                                |
| Static analysis only for performance                                                                      | No profiler/runtime metrics                                                                                                                                                                                                                                                                                                                            | No                                     | Instrument one warm + one cold pipeline run                                                                                                      |
| 2,596 entry rows / 596 error rows not semantically reviewed                                               | Bounded turn budget                                                                                                                                                                                                                                                                                                                                    | No                                     | Sample-read the top 20 by fan-in before the next audit                                                                                           |
| Dependency maintenance/licence, other platforms                                                           | Registry metadata incomplete                                                                                                                                                                                                                                                                                                                           | No                                     | Scheduled dependency review with `pip-audit`/`bun audit` + licence scan                                                                          |
| `spatial_hotspots` producer check not run                                                                 | Its check rewrites a tracked asset                                                                                                                                                                                                                                                                                                                     | No (REL-3 owns)                        | Convert to compare-only, then run                                                                                                                |
| Assistive-technology matrix                                                                               | No browser/AT rig                                                                                                                                                                                                                                                                                                                                      | No                                     | One manual NVDA/VoiceOver pass on `/research/map` and `/explore`                                                                                 |
| No penetration test / threat model                                                                        | Out of scope for a static site audit                                                                                                                                                                                                                                                                                                                   | No                                     | Re-evaluate if any SSR adapter or write endpoint is added                                                                                        |
| Pyright/pandas stub surface in `school_features.py`, `features.py`, `ingestion/datagov.py`, `pipeline.py` | Pyright has no repository config (`pyrightconfig.json` absent, `pyright` absent from `pyproject.toml`), so it runs generic defaults and reports stub-inference artifacts on 4 files that are byte-identical to `449b921`; `mypy` is clean on them. Recorded during wave-0/1 remediation, not fixed: the files are outside every work order's ownership | No (ARCH-1 covers the mypy-scope half) | Either add a pandas-aware `pyrightconfig.json` and gate it in CI, or state explicitly that Pyright is not a gate; do not silence it file-by-file |

## 7.1 Owner decisions taken (2026-11-24)

Recorded so the debt register above stays a live document rather than a snapshot.

| Decision                              | What was authorised                                                                                     | Result                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REL-4 / DEP-1: fix rather than accept | Upgrade `dompurify` and take the Astro **major** instead of renewing their exceptions                   | `dompurify` 21 → 0 records (needed the deprecated `@types/dompurify` stub removed, which pinned a nested 3.3.1); Astro 5.16.16 → 7.4.13 closed 14 astro records. Frontend scope 110 → 28 raw records, 24 → 10 → 8 names; register pruned 47 → 31 entries (23 Python + 8 frontend)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| REL-3: close the ledger drift         | Re-measure and re-pin the nine drifting ledgers, and re-derive the `artifactSha256` pins that hold them | Drift root cause was **prose, not science**: the absence/method scans hashed planning and operational documentation, so a doc edit moved a ledger. `docs/plans/**` and `docs/guides/**` are now excluded from those scans and disclosed inside each ledger's own scan metadata; the residue was code-hash drift, which a pin is supposed to follow. The `artifactSha256` re-derivation in `app/src/components/studies/lib/edition-registry.ts` was owner-authorised, then **independently reviewed and approved on 2026-11-24** ([record](../../implementation/2026-11-24-ledger-repin-review.md)): no coefficient, statistic, sample size, cutoff or disposition changed. The `source` and `publication` human attestations keep their original names, dates and statements |
| Live validation of the HIGH fixes     | Prove A1/A2/A3 against the real providers instead of mocks                                              | 3 env-gated suites (`tests/test_live_*.py`, skipped unless `EGG_LIVE=1`). A2's hard-fail is **safe on today's data**: all 18 ingested resources advertise exactly the rows obtainable by following `next` (e.g. `hdb_rental` 215,469/215,469, `hdb_resale` 245,441/245,441). A1 cold/warm rows identical on real OneMap responses; A3 content mode exercised read-only against the real bucket                                                                                                                                                                                                                                                                                                                                                                               |
| CI evidence provisioning              | Sync the pipeline artifacts the producers read instead of rebuilding them in CI                         | New opt-in `--only evidence` scope over exactly the 7 enumerated artifacts, reusing the containment resolver and content hashes. The `~105 MB` upload and flipping `evidence.yml` to `pull_request` remain owner actions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

## 8. Executive summary

- **Overall verdict: CONCERNS.** Score **7/10**: strong test depth, atomic writes, verified manifests and an honest evidence culture; the deductions are silent offline-integrity defects (CORE-1/2/3) and two verification gaps that let claims outrun their proof (UI-1, REL-2/3).
- **Top three risks:** (1) warm-cache geocoding can move condo coordinates between runs without any report; (2) a malformed later API page becomes a permanent partial bronze cache; (3) size-only R2 sync can neither propagate corrections nor detect corrupted backups.
- **Effort:** optimistic ~4 engineer-days (Phase 0 + quick wins); realistic ~12–15 days (Phases 0–1); pessimistic ~25–30 days if REL-2/REL-3 require re-signing editions and REL-4 forces an Astro major upgrade.

## 9. Machine-readable baseline

```yaml
audit: master-audit-2026-11-23
baseline_commit: 449b921d499a8c55ec1eacb1a423baa7632456d3
verdict: concerns
score: 7
findings:
  - {
      id: CORE-1,
      severity: high,
      score: 16,
      category: correctness-cache,
      path: src/egg_n_bacon_housing/utils/geocoding.py:343,
      status: open,
      effort: M,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: CORE-2,
      severity: high,
      score: 12,
      category: ingestion-integrity,
      path: src/egg_n_bacon_housing/adapters/datagovsg.py:222,
      status: open,
      effort: M,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: CORE-3,
      severity: high,
      score: 16,
      category: backup-integrity,
      path: scripts/00_sync_data.py:42,
      status: open,
      effort: M,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: CORE-4,
      severity: medium,
      score: 8,
      category: path-containment,
      path: scripts/00_sync_data.py:216,
      status: open,
      effort: M,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: CORE-5,
      severity: medium,
      score: 9,
      category: operational-recovery,
      path: scripts/40_refresh_rolling.py:240,
      status: open,
      effort: S,
      phase: 0,
      confidence: confirmed,
    }
  - {
      id: CORE-6,
      severity: medium,
      score: 8,
      category: concurrency,
      path: src/egg_n_bacon_housing/utils/geocoding.py:194,
      status: open,
      effort: S,
      phase: 0,
      confidence: confirmed,
    }
  - {
      id: UI-1,
      severity: medium,
      score: 9,
      category: data-trust,
      path: app/src/utils/release-manifest.ts:484,
      status: open,
      effort: M,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: UI-2,
      severity: medium,
      score: 9,
      category: accessibility,
      path: app/src/components/dashboard/PriceMap.tsx:464,
      status: open,
      effort: M,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: UI-3,
      severity: medium,
      score: 9,
      category: handoff-scope,
      path: app/src/components/dashboard/PriceMap.tsx:777,
      status: open,
      effort: S,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: UI-4,
      severity: medium,
      score: 6,
      category: ui-arithmetic,
      path: app/src/components/tools/lib/tool-amortization.ts:156,
      status: open,
      effort: S,
      phase: 0,
      confidence: confirmed,
    }
  - {
      id: REL-1,
      severity: medium,
      score: 6,
      category: release-gate,
      path: .github/workflows/ci.yml:142,
      status: open,
      effort: M,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: REL-2,
      severity: medium,
      score: 6,
      category: evidence-integrity,
      path: app/src/components/studies/lib/edition-registry.ts:1103,
      status: open,
      effort: M,
      phase: 2,
      confidence: confirmed,
    }
  - {
      id: REL-3,
      severity: medium,
      score: 9,
      category: reproducibility,
      path: .github/workflows/ci.yml:11,
      status: open,
      effort: M,
      phase: 2,
      confidence: confirmed,
    }
  - {
      id: REL-4,
      severity: medium,
      score: 9,
      category: supply-chain,
      path: .github/workflows/ci.yml:34,
      status: open,
      effort: M,
      phase: 2,
      confidence: confirmed,
    }
  - {
      id: ARCH-1,
      severity: medium,
      score: 6,
      category: type-coverage,
      path: pyproject.toml:149,
      status: open,
      effort: M,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: ARCH-2,
      severity: low,
      score: 4,
      category: duplication,
      path: src/egg_n_bacon_housing/utils/layer_writer.py:49,
      status: open,
      effort: S,
      phase: 1,
      confidence: confirmed,
    }
  - {
      id: DEP-1,
      severity: low,
      score: 3,
      category: dependency-hygiene,
      path: pyproject.toml:35,
      status: open,
      effort: S,
      phase: 2,
      confidence: likely,
    }
  - {
      id: DOC-1,
      severity: medium,
      score: 6,
      category: documentation,
      path: docs/implementation/README.md:47,
      status: open,
      effort: S,
      phase: 2,
      confidence: confirmed,
    }
gates:
  - { gate: next-data-refresh, requires: [CORE-1, CORE-2] }
  - { gate: next-r2-sync, requires: [CORE-3, CORE-4] }
  - { gate: next-deploy, requires: [REL-1] }
```
