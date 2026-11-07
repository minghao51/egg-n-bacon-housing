# S8 implementation report — four-tool workspace with safe output states

`/research/tools` is the research destination for the four decision tools; `/dashboard/trends` stays as a compatibility wrapper over the same island and keeps working with its query state. The slice replaces the old calculator panel, which read a separate period-unknown affordability extract, called an average of area medians a national figure, hid a ×1,000 floor-area assumption, and printed persona "recommendations". **No commit**; no published asset modified; no model, scoring or eligibility change.

## 1. What shipped

**New route + wrapper**

- `app/src/pages/research/tools.astro` (new) — Fieldnotes shell, one `h1`, the four-contract intro, a JS-off block naming the archive assets.
- `app/src/pages/dashboard/trends.astro` — three-line wrapper over the shared shell with an explicit compatibility note; `/dashboard/trends` remains valid.
- `app/src/components/tools/ToolsSurface.astro` — shared shell. Reads the three archive payloads, `map_metrics.json.gz` and `dashboard-release.json` at **build time**, builds the observed reference table, and passes `baseUrl` + props to the island (no `import.meta` and no asset fetch in the island).
- `app/src/constants/dashboard-nav.ts` — the `tools` nav item now points at `research/tools` (the S4/S7 pattern). The overview capability strip follows the same constant, so it moved automatically.

**Pure modules (unit-tested)**

- `lib/tool-amortization.ts` — standard amortization `P×r/(1−(1+r)^−n)`, the `r = 0` branch `P/n`, documented UI bounds (price > 0, income > 0, down 0–100%, term 1–50, rate 0–20) and a fail-closed result that names every invalid field. Unrounded values; rounding is display-only.
- `lib/tool-url-state.ts` — parse/serialise for `tool` and the named reference (`ref`, `rt`, versioned by `rv=1`). A partial or unversioned reference is ignored rather than importing the wrong area's price. Loan and income inputs are never serialised.
- `lib/tool-assets.ts` — runtime schema checks for `lease_decay_analysis`, `mrt_cbd_impact` and `spatial_hotspots`. Each returns a typed asset or an explicit unavailable reason. `spatial` reads `towns[]` only; `portfolio_allocation` is discarded at this boundary.
- `lib/tool-evidence.ts` — the single evidence contract: archive status against the release manifest, every caveat string, the archive's first-match lease lookup with shared-endpoint exposure, coverage gaps, stored-label conflicts, town-key normalisation and the stored (withheld) MRT formula terms.
- `lib/tool-reference.ts` — the observed reference table, built from joint `map_metrics.year_2025_{hdb,ec,condo}` sections through the S1 adapter. Property-only (`hdb`) and period-only (`whole`) blocks are never a fallback; an exporter-empty block is omitted.
- `lib/tool-format.ts` — `S$` / multiple / signed-percent formatting; missing values stay `N/A`.

**Workspace**

- `ToolsWorkspace.tsx` — state is read from the address bar **before the first commit** (client-only island), written back with `replaceState` only for keys it owns, and re-applied on `popstate`. Desktop uses a keyboard-navigable tablist (arrow/Home/End, roving tabindex); mobile uses a native `<select>` exposing all four tools (SVG19). Each tool renders inside its own `ToolErrorBoundary`, so one malformed asset cannot unmount the workspace.
- Financing — editable price, annual income, down payment, term and rate; the reference import is named (`map_metrics.year_2025_hdb · Tampines · S$710,000 · 1,921 sales · release 0e1013…`) and can be re-imported after a manual edit. Defaults reproduce the plan's example: **S$497,000 principal → S$2,356.830…/month (S$2,357), S$213,000 down, 23.6% payment/income, 5.92× price/income, sensitivity 2,107 / 2,357 / 2,623 / 2,905 / 3,202**. Invalid/blank inputs withhold every output and list each invalid field.
- Lease — 40–99-year lookup against stored bands (75 → **74–79, +19.1%, 29,913 rows, 0.25%/year stored field**). Signed SVG interval marks plus an accessible table sorted by remaining lease; the archive's inclusive first-match endpoint rule is preserved and named (94 → `0-5` selected, `5-10` also contains it); the stored-domain gap (10–38 years) and the stored-label conflicts are surfaced; no projection, loss or safe/cliff advice.
- MRT/CBD — controls retained plus the S8 explicit floor-area input; the supplied coefficients, town key (`Bishan` → `BISHAN`, no fallback) and the stored formula with this scenario's numbers are disclosed, including the 500 m stop and the ×1,000 implicit floor-area assumption. **Total-dollar output is withheld.**
- Spatial — schema-validated label inspection of the 40 published town records, cluster filter, stored fields labelled as archive values. No cluster aggregate, allocation, BUY/SELL prompt or simulated return.

**Removed deliberately**

The four superseded components (`AffordabilityCalculator`, `LeaseDecayAnalyzer`, `MrtCbdCalculator`, `SpatialHotspotExplorer`), their panel and tabs (`InteractiveToolsPanel`, `ToolTabs`), the pass-through `TrendsDashboard`, and `TrendsMap` (only the deleted tools used it) are gone. Their replacement removes the unverified "national average", the "70-80 years = peak decay / avoid entry" advice, the ×1,000 hidden scaling and the `7×/15×` prose.

## 2. Evidence boundary

- The financing reference is one **joint 2025 section** of `map_metrics.json.gz`, resolved at build time. It is the only dashboard asset this surface reads, so no cross-asset comparison is made; the footer names the section, generation and published month.
- The three research assets are **not** in `dashboard-release.json`. `tests/unit/tool-evidence.test.ts` reads the published manifest and asserts `unverified-archive` for each, that listing them would flip the gate, and that archive labels state the missing period/sample.
- `affordability_metrics.json.gz` is no longer read by the application. It stays published (exporter/catalogue ownership); retiring it is a data-boundary decision, not a UI one.

## 3. Verification

| Check                                                     | Result                                                                                                                                                                             |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bun run test:unit`                                       | **286 pass, 0 fail, 18 files** (+53: amortization 14, URL state 10, evidence 22, reference 7 — baseline 233)                                                                       |
| `bun run astro check`                                     | **20 errors / 0 warnings / 30 hints / 173 files** — no finding in any S8 file; errors fell 26 → 20 and hints 35 → 30 because the deleted tool components carried pre-existing debt |
| `bun run validate-data`                                   | passes: 19 assets, release `0e1013ee485f` (7 assets)                                                                                                                               |
| `bun run build`                                           | passes: **200 pages** (was 199; `/research/tools` added); `catalog.jsonl.gz` unchanged by the build                                                                                |
| Playwright (preview, full suite)                          | **163 pass, 0 fail** (baseline 151: +13 new `research/tools.spec.ts`; the 6 old Decision-Tools tests became 5 wrapper tests = 163)                                                 |
| `uv run pytest tests/test_export_app_data.py --no-cov -q` | **44 pass** (no exporter change)                                                                                                                                                   |
| `uv run ruff check`                                       | clean                                                                                                                                                                              |
| Prettier                                                  | `bunx prettier@3.4.2 --write` on every changed TS/TSX file (astro excluded by the hook's `types_or`)                                                                               |
| `git status` after verification                           | no published asset modified; no `bun.lock` change; `catalog.jsonl.gz` restored/unchanged                                                                                           |

Behaviour proven in the browser: default financing exit values; reference switch to Queenstown condominium (S$2,088,000, section `year_2025_condo`) round-trips through `ref`/`rt`/`rv` and a deep link restores it; a manual price edit removes the "imported" label and the import button restores it; blank/`abc`/`0` income withholds the results and names the field; 0% uses `P/n` (S$1,657) while the sensitivity table keeps its 3% row; lease 75/94/blank; MRT cap disclosure and Condominium coefficient (63 per 100 m); spatial 40 towns and `HH` filter; the legacy wrapper keeps `?tool=mrt`; the nav link points at `/research/tools` with `aria-current="page"`; 390 px uses the native select with no horizontal overflow; no console or page errors on either route.

## 4. Gaps deliberately left open

- **~~Inputs are intentionally volatile.~~ Resolved (S8-F1).** Price, income, down payment, term and rate now live in `ToolsWorkspace`, which stays mounted across tabs, so selecting Lease/MRT/Spatial and returning keeps every value. The draft is plain React memory inside the island: never the URL, `localStorage`, `sessionStorage`, telemetry or the console, and a reload still starts from the defaults. The import-on-remount trap is handled by `lib/financing-draft.ts`: the observed median is applied only when the resolved reference key (`area:property`) changes, so a manual price stays manual while a deep link or back/forward to another area still imports that area's median. See §7.
- **The lease input is 40–99 years** as the plan specifies, while the archive also stores a 4–9-year band. The chart displays every stored band and the table lists them; the out-of-input band cannot be selected. Changing the input range is a product decision.
- **Spatial allocation stays discarded.** `portfolio_allocation` is dropped by the schema check; surfacing it needs a reviewed model contract.
- **The MRT floor-area input is inert by design.** It records the basis the archive never declared and no total is computed from it.
- **`affordability_metrics.json.gz` is published but unused.** Removing it from the export list is a data-boundary change.
- **`PersonaHeader.tsx` remains unreferenced** (pre-existing) and still carries two `astro check` errors; it is S10 cleanup.
- **No new chart dependency**: the lease chart is a small inline SVG with a table equivalent, and the financing sensitivity table is plain HTML.

## 5. Next

**S9** (research map, studies, catalog) is next per the plan. It must keep the nine layer IDs and query state, never relabel historical forecasts as current, keep chart markers opt-in and preserve catalog IDs/slugs/schema links. S8 leaves the tools surface independent of it.

## 6. Environment note

`bun run astro check` baseline for this branch is now **20 errors / 0 warnings / 30 hints** on 173 files (was 26/0/35 before the dead tool components were deleted). `pi-lens`'s TypeScript server still reports `import.meta`/`clsx` errors on unmodified files in this checkout; `bunx tsc -p tsconfig.json --noEmit` and `astro check` are the project-accurate signals, and neither reports an S8 file.

## 7. Follow-up — S8-F1 persistence (resolved)

The five financing inputs used to be `useState` strings inside `FinancingScenario`, so switching tool unmounted the component and reset them. They now live in `ToolsWorkspace`, above the per-tool error boundary, as a `FinancingDraft` (`lib/financing-draft.ts`, pure: `DEFAULT`, `mergeDraft`, `createFinancingDraftState`, `applyReferenceToDraft`). `resolveReference` and `referenceKey` moved to `lib/tool-reference.ts` so the workspace owns the import decision.

- **Import only on a reference change.** The workspace stores `{ draft, appliedReferenceKey }` and applies an entry's median only when `referenceKey(entry)` differs. A remount, a tool switch or an unchanged deep link resolves the same key and is a no-op (it returns the same state object), so a manual price survives. A different area, or a hash-less `pushState` + `popstate` reference change, changes the key and imports the new observed median (Queenstown condo → `2088000`) while leaving the other four inputs untouched.
- **Reset** (`Reset scenario`) is handled by the workspace: it clears the reference and rebuilds the default draft, so it cannot race the import effect.
- **Privacy is unchanged**, and now covers persistence: the draft is memory-only — no URL keys beyond `tool`/`ref`/`rt`/`rv`, no `localStorage`/`sessionStorage`, no telemetry or console output. A reload starts again from the documented defaults (verified, and recorded here as intended behaviour, not a bug).

Evidence: `tests/unit/financing-draft.test.ts` (17 tests: defaults, partial/blank/`undefined` merges, immutability, same-key no-op with a new entry object, changed-key import, manual-price survival, `null` reference, resolution and key stability). `tests/e2e/research/tools.spec.ts` adds four tests: all five inputs edited then retained across Lease/MRT/Spatial and back with "Price entered manually" still shown; a Queenstown condo import retained across a tool switch; a `popstate` reference change importing `2088000` over a manual price; and a reload returning to `710000`/`120000`. `tests/e2e/integration.spec.ts` now edits income **and** price, switches tabs, and asserts neither value reaches the URL (only the four allowed keys), request URLs, request bodies, console or local/session storage. No scoring, eligibility, model or published-data boundary changed.
