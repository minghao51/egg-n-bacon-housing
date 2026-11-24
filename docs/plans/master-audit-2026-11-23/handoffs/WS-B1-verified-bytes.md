# WS-B1 — One verified-bytes load path (UI-1)

**Severity:** MEDIUM (3×3 = 9). **Effort:** M. **Wave:** 2 (first of the two frontend orders).

## Problem

Legacy release verification downloads and hashes the assets, then throws the bytes away. The UI then downloads the same URLs a second time and renders those responses without any hash check. Verified bytes and displayed bytes are different responses.

- `app/src/utils/release-manifest.ts:446-473` — fetches each target into `supplied`.
- `app/src/utils/release-manifest.ts:484-507` — verifies `supplied`, returns only `status`/`manifest`/`mismatches`.
- `app/src/components/explorer/ExplorerWorkspace.tsx:164-188` — verification pass (`verifyOnly: Object.keys(assetUrls)`).
- `app/src/components/explorer/ExplorerWorkspace.tsx:265-271` — independent `useGzipJson` fetch of the same assets.
- `:630` — user-facing "generation-verified" disclosure.

Contrast (do not regress): `app/src/utils/observed-pack-loader.ts` hashes response bytes and decodes those same buffers; v2 consumers receive the parsed pack.

## Required change

1. Extend the release loader so it returns the decoded payload for each verified asset (e.g. `assets: Record<string, unknown>` plus the raw bytes/digests it verified). Keep the existing `status`/`mismatches` shape so every current caller keeps working.
2. Have the explorer render and cache exactly those decoded payloads. Do not re-fetch the same URL through `useGzipJson` for display; if a refresh path is needed, refresh must re-verify before replacing displayed data.
3. Preserve the current failure semantics: `absent`, `unverified`, `mismatch` must still suppress the national comparison, and a fetch failure must stay `unverified` (not `mismatch`).
4. Keep one generation-qualified cache key per payload so a later generation cannot be confused with a verified one.
5. The disclosure text must remain true: only claim verification for bytes that were verified.

## Tests (`app/tests/unit/`)

- Loader returns decoded payloads for verified assets and preserves all four statuses.
- A mismatched asset yields `mismatch` and no payload is exposed.
- Explorer-level: verification returns payload A, a second response for the same URL carries payload B → B must never render as verified (mock `fetch` per request, including after a refresh trigger).
- Existing release-manifest and explorer tests stay green.

## Verification

```bash
cd app && PATH="$HOME/.bun/bin:$PATH" bun run test:unit
cd app && PATH="$HOME/.bun/bin:$PATH" bun run astro check
# then the E2E + Pages-prefixed suites from handoffs/README.md
```

## Owns

`app/src/utils/release-manifest.ts`, `app/src/hooks/useGzipJson.ts` (only if a verified-payload path needs a new hook), `app/src/components/explorer/ExplorerWorkspace.tsx`, `app/tests/unit/release-manifest.test.ts`, `app/tests/unit/` additions.

## Do not touch

`app/src/utils/observed-pack-*.ts` (already correct), `PriceMap.tsx` (WS-B2 owns it), workflows, Python.

## Done when

No displayed legacy figure can come from an unverified response, the four statuses behave as before, and the frontend gate — including the Pages-prefixed suite — is green.
