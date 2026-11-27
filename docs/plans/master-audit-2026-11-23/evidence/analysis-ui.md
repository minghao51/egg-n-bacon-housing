Agent: 424b7ac2-6da0-413
Type: Agent | Status: steered (wrapped up at the turn limit — output may be partial) | Tool uses: 75 | 119.3k token | Context: 23% | Duration: 155.5s
Model: openai-codex/gpt-6.1-sol, thinking: high
Description: Audit frontend trust and behavior

## Scope and limits

Read-only frontend audit; no source edits, installs, commits, servers, browser runs or suite duplication. One hermetic Bun 1.2.23 arithmetic PoC executed. Findings are provisional.

Scoring: impact × likelihood; critical ≥20, high ≥12, medium ≥6. No high/critical finding established.

## Findings

### UI-1 — Legacy verification does not cover the responses actually displayed

**Medium — impact 3 × likelihood 3 = 9. Confidence: high.**

- **Evidence:** `app/src/utils/release-manifest.ts:395` downloads and verifies assets, but returns only status/manifest—not their decoded contents. `app/src/components/explorer/ExplorerWorkspace.tsx:172` runs that verifier; `:278` subsequently loads the same URLs through separate `useGzipJson` calls. `app/src/hooks/useGzipJson.ts:127` fetches and parses those responses without checking their hashes.
- The second responses feed `buildExplorerDataset`, while the earlier `releaseStatus === "verified"` enables national comparison. The footer explicitly claims the two compared assets were generation-verified (`ExplorerWorkspace.tsx:630`).
- **Trigger/path:** A deployment or cache transition between verification and display requests can supply different generations. Likewise, a later successful data reload is not reverified. No malicious public input is necessary.
- **Impact:** Mixed or changed values can appear under a verified-generation claim. A generation-qualified cache key labels the second response; it does not authenticate it.
- **Boundary:** This is release-consistency failure, not evidence of an Internet attacker bypassing HTTPS. Control of the same-origin publication would already permit replacing the application.
- **Minimal fix:** Return decoded verified payloads from the release loader and render/cache those exact objects. Revalidate replacement payloads before refreshing comparisons.
- **Regression:** Serve valid manifest/assets for verification, different valid JSON for subsequent requests, and assert that changed values cannot appear as verified. Repeat through refresh.

**Positive contrast:** `app/src/utils/observed-pack-loader.ts:357` and `:481` hash the response bytes and decode those same buffers. `useObservedPack` consumers receive the resulting parsed pack, not a second unverified asset fetch.

### UI-2 — Research-map selection/inspection is pointer-only

**Medium — impact 3 × likelihood 3 = 9. Confidence: high from source; browser verification outstanding.**

- **Evidence:** `app/src/components/dashboard/PriceMap.tsx:464` registers polygon mouseover, mouseout and click handlers, but no keyboard activation or focus mechanism. The inspector instructs users to click an area (`:741`). The complete component contains no alternate area selector or table.
- Its metric selector has adjacent visual text rather than an associated label (`:593`); period/type button selection is represented by styling without `aria-pressed` (`:621`, `:658`).
- **Reachability:** `app/src/components/research-map/ResearchMapSurface.astro:129` mounts this component on `/research/map` and the `/dashboard/map` compatibility route.
- **Trigger/user path:** Keyboard-only or screen-reader users navigate the loaded research map and attempt to select an area to inspect its metrics/archive layers. A preconstructed `?area=` link is not an equivalent discoverable control.
- **Impact:** Area-dependent inspection is unavailable through the UI keyboard path; control names/current filter states are also inadequately exposed.
- **Minimal fix:** Add a labelled native planning-area selector driving the same state, associate the metric label, and expose selected filter states. Provide a metric table/link alternative.
- **Regression:** Complete area selection and archive inspection with keyboard only; assert accessible selector name and current filter state.

**Rejected extension:** `/explore` is not affected by this same claim: its SVG supplies focusable area links and accessible names, and its workspace offers list/table alternatives (`app/src/components/explorer/ExplorerMap.tsx:375–461`).

### UI-3 — Research-map handoff silently changes the comparison scope

**Medium — impact 3 × likelihood 3 = 9. Confidence: high.**

- **Evidence:** `app/src/components/dashboard/PriceMap.tsx:294` selects metrics using both temporal and property filters. Its “Open observed comparison” link (`:788`) serializes only `area` and `metric`, omitting both selected period and property.
- `app/src/components/explorer/ExplorerWorkspace.tsx:80` adopts the build’s observed default when no period parameter exists; the explorer independently initializes its property selection.
- **Trigger/user path:** Select condominium and a historical period on `/research/map`, select an area, then follow “Open observed comparison.”
- **Impact:** The destination compares a different property/window instead of preserving the inspected scope. Unsupported research-map metrics can also be passed to an explorer whose supported metric set differs.
- **Minimal fix:** Use a shared handoff serializer translating temporal/property/metric selections into supported explorer parameters. Explicitly disclose any unsupported metric substitution.
- **Regression:** Follow the handoff for each property and historical period; assert the destination’s selected controls, source section and displayed figures preserve scope.

### UI-4 — Financing accepts inputs whose arithmetic contradicts its validation contract

**Medium — impact 2 × likelihood 3 = 6. Confidence: high; hermetically reproduced.**

- **Evidence:** `app/src/components/tools/lib/tool-amortization.ts:37` allows down payment through 100%. `:169` computes zero principal for 100%; `monthlyPayment` rejects that principal (`:92`), and `:178` incorrectly reports the valid price as invalid.
- The positive-rate formula (`:108`) suffers cancellation when `1 + monthlyRate` rounds to `1`. Output finiteness is not checked.
- **Executed PoC:** Using the default S$710,000 scenario:
  - `downPaymentPercent: 100` → `{ok:false, invalidFields:["price"]}`.
  - `annualRatePercent: 1e-14` → `{ok:true, monthlyPayment:Infinity, paymentToIncomePercent:Infinity}`.
- **Reachability:** `FinancingScenario.tsx:80` uses `Number` parsing; its text inputs accept these strings. Both public tools routes mount this scenario.
- **Impact:** A legitimate cash-purchase boundary falsely blames price; tiny accepted positive rates yield an internally successful but non-finite scenario. This is illustrative arithmetic, not an eligibility decision or demonstrated financial loss.
- **Minimal fix:** Handle zero principal explicitly; use stable `log1p`/`expm1` arithmetic and reject non-finite derived results.
- **Regression:** Add 100%-down, tiny-positive-rate, and finite-output property tests.
- **Tests inspected:** `app/tests/unit/tool-amortization.test.ts` covers ordinary defaults, exactly zero interest and invalid inputs—but not these boundaries. `app/tests/e2e/research/tools.spec.ts` likewise covers defaults/zero rate, not these cases.

## Privacy and injection outcomes actually inspected

- **Financing inputs:** The five editable strings remain in `ToolsWorkspace` React state. The URL serializer accepts only tool/reference selection—not the draft (`app/src/components/tools/ToolsWorkspace.tsx:106–168`; `lib/tool-url-state.ts:119`). The inspected scenario/merge/arithmetic path performs no fetch, storage write or logging. Inputs set `autoComplete="off"`. This supports the local-state privacy claim for this path; it does not establish browser-extension or whole-site privacy.
- **Privacy tests:** Tools E2E assertions inspect URL exclusion for edited price/income, persistence across tool switches and reset on reload. They do **not** instrument network/storage/console to prove non-exfiltration.
- **Third parties:** The reachable research map loads Carto tiles (`PriceMap.tsx:699`), exposing ordinary IP/request metadata and requested map coordinates to that service. The explorer map is tile-free. No financing input is appended to tile URLs.
- **HTML sink:** `PriceMap.tsx:388–459` interpolates asset-provided area names, affordability labels and momentum strings into Leaflet tooltip HTML without escaping. Similar sinks exist in the inspected leaderboard map. This is a real unsafe rendering boundary, but no public-user-controlled source was established: current inputs are static published assets. **Not promoted to public reflected/stored XSS.** Escape strings/use DOM text nodes as hardening.
- **Markdown:** Current analytics routes render repository content at build time (`app/src/pages/analytics/[slug].astro:24,185`), not submitted public markdown. Raw trusted repository HTML is a publisher boundary, not a demonstrated public server injection surface.
- `MarkdownContent.tsx` sanitizes via DOMPurify, but that does not protect the separate Astro article path. The inspected source search found no callers of `MarkdownContent` or `PlotlyEmbed`; this is bounded reference evidence, not proof excluding every possible indirect use.

## Architecture/scale observations

- Phase-1 census—not newly remeasured here—records 156 `app/src` files, 19 route sources, 33,485 source lines and 891 lines across four app scripts.
- The explorer mounts the v2 loader and legacy verifier concurrently, then fetches legacy display assets again even when the selected window uses v2. Its legacy verifier fetches its two assets sequentially. This is verified redundant work, but no fresh network timings justify a separate performance severity.
- V2 core loading deliberately excludes the four property-specific monthly-history assets; history uses on-demand, same-byte verification.
- Fully read app scripts: `serve-pages-base.mjs`, `sync-catalog.mjs`, `measure-payload.mjs`. The preview helper binds only to `127.0.0.1` and performs path containment checks. It is not evidence of a shipped public Node server.
- `measure-payload.mjs` reports build artifacts but explicitly excludes runtime data downloads; its numbers alone cannot establish total page cost.

## Rejected candidates and remaining gaps

- No demonstrated public financing-data exfiltration, arbitrary external fetch from URL parameters, public markdown upload surface or production SSR endpoint.
- V2 hash/size mismatch handling rejects payloads; transport-decoded gzip is explicitly rejected rather than silently trusted.
- **Unresolved candidate, not a finding:** `parseObservation` accepts `withhold` observations with numeric metrics, while `packMetricValue` returns values without checking disposition. Current published occurrence, complete consumer behavior and relevant regression tests were not verified.
- Full reads covered the principal explorer lifecycle, gzip hook/request model, v2 browser loader, financing implementation/tests and reachable research-map implementation. Overview implementation was only partially read; leaderboard hook/map reads were not a complete dashboard audit.
- Unread/incomplete: area/history implementations, remaining charts/segments/catalog, edition registry/artifact validation, v2 loader/parser test bodies, release-manifest tests, most accessibility E2E tests, and the latter portion of `validate-data.mjs`.
- No browser/a11y-tree validation, build, E2E or fresh bundle measurements performed; main-agent results remain necessary. CI, dependency-advisory triage and Python were excluded.
