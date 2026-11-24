Agent: cf52a9d2-ac64-470
Type: reviewer | Status: completed | Tool uses: 29 | 103.7k token | Context: 36% | Duration: 208.3s
Model: openai-codex/gpt-6-luna, thinking: high
Description: Audit release and supply-chain gates

## Findings

### REL-1 — Pages-base browser checks are not part of the release gate  
**Medium (impact 3 × likelihood 2 = 6); confidence: high.**

- **Evidence:** CI’s E2E job builds the default site and runs Playwright against `astro preview` at `/` (`.github/workflows/ci.yml:142-151`). The Pages-base spec requires `PAGES_ORIGIN` and is skipped when it is absent (`app/tests/e2e/pages-base.spec.ts:17-27`). Deploy builds with `ASTRO_PAGES=true`, but checks routes mostly by grepping headings and checks only that one base-prefixed CSS asset loads (`.github/workflows/deploy.yml:37-41,52-67,85-121`).
- **Trigger/reachability:** A Pages-base URL, hydration, or deep-link regression can pass the CI E2E job and deploy’s smoke checks, then break the actual static Pages site. The dedicated browser spec covers hydration, data fetches, links, and routes under the prefix, but is not invoked by either workflow.
- **Minimal fix/test:** Run the Pages-base build and `pages-base.spec.ts` against the static mount in CI or the deploy build job; verify the deployment is gated on that job. Confirm the job fails on a deliberately broken base-prefixed asset/link in an isolated test environment.
- **Gap:** Branch-protection settings are outside repository access, so whether CI checks are required before merge is unknown. The deploy workflow itself has no dependency on CI.

### REL-2 — Edition “evidence” sign-off hashes are not checked against evidence bytes  
**Medium (impact 3 × likelihood 2 = 6); confidence: high.**

- **Evidence:** Registry validation checks that sign-off hashes are well-formed and equal to one another, but does not resolve or hash an evidence artifact (`app/src/components/studies/lib/edition-registry.ts:983-985,1023-1029`). At build time, the archive route verifies the frozen **edition text** hash, not the sign-off evidence hash (`app/src/pages/analytics/archive/[year]/[edition]/[slug].astro:34-62`). Registry unit tests accept a complete sign-off record with a synthetic hash (`app/tests/unit/edition-registry.test.ts:257-304`).
- **Trigger/reachability:** An approved entry can retain three equal, valid-looking hashes after the underlying ledger changes, or can cite a hash that never matched the reviewed ledger. The static build can still publish it as approved. This weakens the documented claim that attestations cover a specific evidence artifact; it does not establish that any current scientific conclusion is wrong.
- **Minimal fix/test:** Give each approved edition an explicit evidence-artifact path and verify its canonical content hash at build time, or add an equivalent mandatory release validation. Test a stale hash and missing artifact fail the build, while preserving the separate edition-text pin.
- **Scientific integrity note:** The text hash does bind the frozen prose, but it does not substitute for checking the ledger hash against the evidence bytes.

## Other verified observations

- **Dependency census:** I confirmed Bun’s audit contains **110 records across 24 package names** (including 14 Astro, 21 DOMPurify, 1 KaTeX, and 3 Sharp records). These are advisory records, not unique vulnerability counts. `GHSA-26w7-cxv4-gfx2` reports Astro AVIF image-optimization RCE for versions below 7.2.8; the lock has Astro 5.16.16 and Sharp 0.34.5. I found no `astro:assets`, `<Image>`, `<Picture>`, or AVIF usage in `app/src`, so I do **not** claim a reachable RCE in this static Pages app. The direct Astro upgrade path crosses a major version and requires coordinated integration compatibility testing; do not apply an automatic fix without build, unit, E2E, and Pages-base validation.
- **Dependency control gap:** CI runs `pip-audit` but has no frontend audit step (`.github/workflows/ci.yml:34-42,97-121`). The Bun findings therefore are not a frontend CI gate. Add an advisory audit step with a documented exception process; validate that it reports the locked Astro/DOMPurify findings and fails as intended. This is a preventive control gap, not a claim that every reported advisory is exploitable here.
- **Producer drift:** I inspected the `--check` paths before running them; they call `check()` and do not write ledgers. Five checks (RS06, RS07, RS08, RS14, RS15) all failed. The output confirms the documented drifts, but RS08 also reported `legacyFeatureNames`, `multiplicityPolicy`, `rddRecovery`, and `schoolCoordinates`, beyond the `scanManifests` drift described in `docs/implementation/2026-11-22-dependency-audit.md:141-145`. I did **not** run RS12: that document records that its check rewrites a tracked rental asset (`:150-153`). These failures are not, by themselves, evidence that the edition’s scientific claims are invalid; distinguish scan/source-hash drift from changed measured evidence and independently review the changed fields before relying on sign-off.
- **Not findings:** I make no public-server RCE claim: the audited frontend is built as static Pages output, and no reachable server operation was established. No privacy/GDPR compliance conclusion is drawn.

## Files Reviewed

- `.github/workflows/ci.yml` (1-159); `.github/workflows/deploy.yml` (1-125)
- `app/src/components/studies/lib/edition-registry.ts` (930-1158); archive route (1-100)
- `app/tests/e2e/pages-base.spec.ts` (1-200); `app/scripts/serve-pages-base.mjs` (1-90)
- `app/tests/unit/edition-registry.test.ts` (250-590); `app/package.json` (1-60); `app/astro.config.mjs` (1-80)
- `docs/implementation/2026-11-22-dependency-audit.md` (119-154); dependency audit evidence files

## Summary

The most actionable release gaps are that the Pages-base browser suite is not enforced and the edition gate verifies prose bytes but not the evidence bytes cited by sign-offs. Five safe producer checks reproduced drift; RS08’s observed drift exceeds the cited documentation, while RS12 was deliberately not run due to its documented write side effect. No files were edited; the working tree remained limited to the pre-existing untracked audit-plan directory.