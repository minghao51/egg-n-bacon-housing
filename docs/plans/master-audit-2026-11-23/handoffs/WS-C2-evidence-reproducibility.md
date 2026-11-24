# WS-C2 — Evidence reproducibility and artifact integrity (REL-2, REL-3)

**Severity:** MEDIUM 6 + MEDIUM 9. **Effort:** M. **Wave:** 3 (sole owner of `.github/workflows/ci.yml` in this wave).

## Problem

1. **Sign-off hashes are never checked against evidence bytes.** `app/src/components/studies/lib/edition-registry.ts:983-985` validates only the *shape* of `artifactSha256`; `:1023-1029` requires the three sign-offs to agree with each other; `:1103-1130` hashes only `edition.frozenSource`. The archive route (`app/src/pages/analytics/archive/[year]/[edition]/[slug].astro:55-74`) therefore verifies prose bytes and publishes "approved" regardless of the cited evidence artifact.
2. **Evidence-producer checks never run in CI.** `.github/workflows/ci.yml` has lint, typecheck, security, catalog, test, frontend and e2e jobs — no evidence job. At this baseline, five safe producers fail their `--check` (`lease_decay`, `mrt_impact`, `school_quality`, `price_forecasts`, `findings`); `school_quality` drifts in more keys than `docs/implementation/2026-11-22-dependency-audit.md:132-148` records. `spatial_hotspots` was not run because its check rewrites a tracked rental asset (`:150-153`).

Neither finding claims any current scientific conclusion is wrong. They claim the *control* is missing.

## Required change

### Part A — artifact integrity (REL-2)

1. Give each approved edition an explicit evidence-artifact path (the registry already carries `evidencePath` on each sign-off). Verify its canonical content hash at build time in the archive route's `getStaticPaths`, alongside the existing prose pin.
2. Keep the two pins distinct in error messages: "edition prose hash" vs "evidence artifact hash".
3. Missing artifact and stale hash must both fail the build with an actionable message naming the edition and the path.
4. Do **not** re-hash the ledger inside the browser bundle; this is build-time only, like the existing frozen-source check.
5. If a current edition's evidence artifact genuinely cannot be located, fail closed and report it — do not add a silent skip.

### Part B — producer checks (REL-3)

6. Convert the one write-side-effect check (`spatial_hotspots`) to compare-only: it must produce the same derived bytes in memory and compare, never rewrite a tracked asset. If that is not feasible without a redesign, gate it behind an explicit flag and document why it stays out of CI.
7. Add a CI job that runs the read-only `--check` producers and fails on drift. Give it a bounded runtime; list the exact producer commands in the job, not a glob that silently skips one.
8. **Owner decision required** for the five currently-drifting producers: re-pin the ledger with a reviewed diff, or narrow the drifting scan and record the reason. Do not paper over drift by regenerating ledgers without review, and do not delete the check. If no decision is available, wire the job with the drifting producers in a documented, named allowlist that fails on any *new* drift — and record the outstanding debt.

## Tests

- `app/tests/unit/edition-registry.test.ts`: a synthetic-but-wrong evidence hash fails; a missing artifact fails; a correct hash passes; prose-pin behaviour unchanged.
- A test asserting the archive route's error message distinguishes the two hash kinds.
- Workflow proof: run the new CI job's command list locally against HEAD and record which producers pass/fail and the allowlisted set.

## Verification

```bash
uv run python scripts/tools/<producer>.py --check   # for each producer you enable
cd app && PATH="$HOME/.bun/bin:$PATH" bun run test:unit && bun run astro check
cd app && PATH="$HOME/.bun/bin:$PATH" bun run build   # archive route must fail on a mutated artifact
git checkout -- app/public/data/catalog.jsonl.gz
```

## Owns

`app/src/components/studies/lib/edition-registry.ts`, `app/src/pages/analytics/archive/**`, `app/tests/unit/edition-registry.test.ts`, `.github/workflows/ci.yml`, the relevant `scripts/tools/*_evidence.py` (read-only/compare-only changes only), `data/catalog/descriptions.yml` only if a producer needs it.

## Do not touch

`docs/analytics/editions/**` bytes (frozen sources), published app assets, `uv.lock`, the edition prose.

## Done when

An approved edition cannot publish with an unverifiable evidence artifact, the producer checks are automated with no silent skips, every drift is either fixed, re-pinned with review, or explicitly allowlisted and recorded, and the full gate passes.
