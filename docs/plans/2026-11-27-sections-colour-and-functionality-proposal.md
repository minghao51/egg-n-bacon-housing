# Sections, colour and functionality — proposal

- **Status:** proposal. No code, route or content changed. Every number below was measured on the deployed `main` (`cca4865`).
- **Owner complaints this answers:** pages are too long, colours are unclear, sections are hard to find.
- **Design inputs of record:** [assets/svg](../../assets/svg/README.md) — 21 SVGs plus [design-rationale.md](../../assets/svg/design-rationale.md), [interaction-spec.md](../../assets/svg/interaction-spec.md), [screen-data-map.md](../../assets/svg/screen-data-map.md), [implementation-plan.md](../../assets/svg/implementation-plan.md).
- **What was already built:** [s3-report.md](../implementation/s3-report.md) (§3 records the deferrals this proposal closes).

## 1. The three complaints are three documented deferrals

None of this is a new diagnosis. Each complaint maps to work the design pack specified and the implementation explicitly deferred.

| Complaint             | Measured today                                                      | Root cause                                                                                                                                | Where it was already specified                                                                              |
| --------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Sections too long     | `/analytics/findings` = **16 screens**; 7 tables are ~3.4k px of it | Articles never got the pack's **library / article split**; evidence tables stay inline in the narrative                                   | [14-research-library-and-article.svg](../../assets/svg/14-research-library-and-article.svg)                 |
| Colours unclear       | Dashboard renders **#3b82f6 / #10b981 / #f59e0b / #ef4444**         | Fieldnotes tokens landed in `globals.css`; the charts still use four unrelated component palettes                                         | [s3-report.md](../implementation/s3-report.md) §3: "editorial chrome around legacy chart colours"           |
| Sections hard to find | **31** sidebar links in **1,948 px** of a 720 px viewport           | The pack's **four-destination nav + research subnav** was never built; the legacy flat sidebar was only made accessible, not restructured | [07-information-architecture.svg](../../assets/svg/07-information-architecture.svg), implementation-plan S3 |

## 2. Measurements behind §1

### 2.1 Length — viewport heights at 1280×720

| Page                     | Screens  | Words | H2  | Tables | Notes                                              |
| ------------------------ | -------- | ----- | --- | ------ | -------------------------------------------------- |
| `/analytics/findings`    | **16.0** | 2,557 | 4   | 7      | tables: 165/165/206/278/124/**1,000**/**1,496** px |
| `/analytics/lease-decay` | 6.9      | 1,192 | 4   | 3      |                                                    |
| `/dashboard/`            | 4.6      | 750   | 5   | 0      | 5 stacked sections + 2 charts                      |
| `/analytics/`            | 4.1      | 858   | 2   | 0      | library state, reasonable                          |
| `/research/map`          | 3.2      | 741   | 4   | 0      |                                                    |
| `/explore`               | 3.0      | 753   | 3   | 0      | the only page already near the target              |
| `/research/tools`        | 2.8      | 633   | 1   | 1      |                                                    |

Two tables are 22% of the findings page; seven are ~30% of total height. The prose is not the problem — **the evidence tables are**.

### 2.2 Colour — four palettes are in play

| Palette                                   | Where                                                                                                               | Matches Fieldnotes?    |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `#3b82f6 #10b981 #f59e0b #ef4444 #8b5cf6` | `charts/ComparisonChart.tsx`, `TimeSeriesChart.tsx`, `StatisticalPlot.tsx`, `dashboard/MarketOverviewDashboard.tsx` | ✗ Tailwind, not tokens |
| `#0088FE #00C49F #FFBB28 #FF8042 #8884d8` | `dashboard/MarketOverviewDashboard.tsx:57` (recharts defaults)                                                      | ✗                      |
| YlOrRd (`#FFEDA0 #FD8D3C #800026`, …)     | `dashboard/PriceMap.tsx`, `LeaderboardMap.tsx`, `ExplorerMap.tsx`                                                   | ✗                      |
| paper / ink / teal / rust / plum          | `styles/globals.css`                                                                                                | ✓ the only correct one |

Verified live on `/dashboard/`: 443 nodes `rgb(16,185,129)`, 71 `rgb(239,68,68)`, 71 `rgb(245,158,11)`, 10 `rgb(59,130,246)`. **The documented property-type encoding — teal = HDB, rust = EC, plum = condo — is used nowhere in the shipped charts.**

Three further ambiguities:

1. **`--primary` is ink, not an accent.** `--accent` and `--secondary` are both the selected fill `#E5EFEB`, so hover, selected and active collapse into one appearance; the only differentiator is a 2 px ink left border.
2. **One hue carries two meanings.** Red is a category series _and_ a negative delta; amber is a series _and_ a caution. Colour alone then cannot be read.
3. **Dead intent.** `prose prose-slate dark:prose-invert` (`analytics/[slug].astro:181`) — `tailwind.config` has `plugins: []`, so the typography plugin is absent and those classes do nothing. Dark mode is explicitly unreviewed (s3-report §3).

### 2.3 Navigation — 31 links, 2.7 viewports tall

Sidebar groups today: Dashboard (7) · Personas (3) · Analytics (index + 15 studies) · Data Catalog (5).

- A reader who lands on a study must scroll the sidebar past 20 links to reach the catalog; on mobile that is inside a modal drawer.
- The **research subnav exists on 2 of 7 research screens** — `pages/analytics/index.astro` and `components/research-map/ResearchMapSurface.astro` — implemented twice, independently.
- The Destination that the pack calls **Data & methods** has no route: `/data` is a 404, and `/data-sources` is not a route either.

## 3. Proposed section model

### 3.1 Four destinations, two subnavs, one shell

```
Overview        /            national annual answer + 3 pathways
Explore         /explore     one comparison workspace (list · map · table)
Research        /research/*  5 subnav: Studies · Trends · Segments · Tools · Research map
Data & methods  /data         provenance guide + definitions → /catalog/*
```

Rules that make it stay short:

- **Nav lists destinations, not datasets.** Studies, areas and catalog tables are reached from their section's own library/list page, never from the global nav.
- **One shell component** (`app/src/components/shell/`) owns primary nav, the research subnav and the footer. The two local subnav implementations are deleted.
- **The sidebar becomes a "section menu", not the product map.** On a study page it shows that section's own pages; global destinations live in the header.
- Sections keep exact `aria-current="page"` behaviour already proven in S3 — no accessibility regression.

### 3.2 Route map — no content churn

| Route today                                                  | Nav home                 | Action                                                   |
| ------------------------------------------------------------ | ------------------------ | -------------------------------------------------------- |
| `/`                                                          | Overview                 | Keep                                                     |
| `/dashboard`, `/dashboard/{leaderboard,trends,map,segments}` | —                        | Keep as compatibility redirect entries                   |
| `/explore`, `/dashboard/leaderboard`                         | Explore                  | Keep                                                     |
| `/areas/[slug]`                                              | (from Explore/Research)  | Keep; add to the map/table row actions only              |
| `/analytics/`, `/analytics/[slug]`, `/analytics/archive/**`  | Research › Studies       | Keep URLs; reshell                                       |
| `/analytics/personas/*`                                      | Research › Studies       | Keep; demote from a global nav group to a library filter |
| `/research/{trends,segments,tools,map}`                      | Research                 | Keep; add the shared subnav                              |
| `/catalog/**`                                                | Data & methods › Catalog | Keep                                                     |
| **new** `/data`                                              | Data & methods           | Build the guide from 08's freshness table                |

`/analytics/*` URLs are pinned by the edition registry and the archive verification, so **the section is renamed in navigation only** — no URL churn.

### 3.3 What the sidebar loses

Personas as a top-level group (3 links for 3 filters), the 15-study flat list (→ the Studies library with its existing category filter) and the 5 catalog links (→ the catalog index). That is 31 → about 8 visible links plus the current section's own pages.

## 4. Proposed functionality taxonomy

The app has **eight interaction archetypes** that today appear as peer nav items. Grouping them by the question they answer is what makes the shape legible.

| Family          | Archetype             | Question it answers                     | Canonical implementation (use this one)         | Currently duplicated by                                               |
| --------------- | --------------------- | --------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------- |
| **Answer**      | 1 · Snapshot          | "What is true nationally, this period?" | `dashboard/MarketOverviewDashboard.tsx`         | `pages/index.astro`, `analytics/index.astro`                          |
|                 | 2 · Library           | "What has been written about X?"        | `studies/StudiesLibrary.tsx`                    | sidebar flat list; personas as nav                                    |
| **Compare**     | 3 · Filtered explorer | "How does area A compare with B?"       | `explorer/ExplorerWorkspace.tsx`                | `dashboard/leaderboard`, `research/trends` controls                   |
|                 | 4 · Map workspace     | "Where, and what is adjacent?"          | `research-map/ResearchMapSurface.astro`         | `dashboard/map`, `explorer/ExplorerMap`, `leaderboard/LeaderboardMap` |
| **Investigate** | 5 · Guided flow       | "Which segment should I look at?"       | `segments/*` (discover → investigate → compare) | `dashboard/segments` wrapper                                          |
|                 | 6 · Calculator        | "What does this do to my numbers?"      | `tools/*`                                       | —                                                                     |
| **Read**        | 7 · Long-form study   | "Why does this happen, and how sure?"   | `analytics/[slug].astro` + new article shell    | `analytics/archive/**` (should reuse the shell)                       |
| **Trust**       | 8 · Provenance        | "Where did this number come from?"      | **new** `/data` + `catalog/*`                   | 08's freshness table exists only as an SVG                            |

Consequences worth stating plainly:

- Archetype 4 (map) has **four** implementations; 3 has three; 1 and 2 have two each. Consolidating to the canonical one is the cheapest real reduction in surface area, because the state, legend and colour fixes then land once instead of four times.
- Archetypes 5–8 are the ones that make this a product rather than a dashboard. They are also the least discoverable today, because they compete with 15 study links at equal visual weight.
- **Each family gets one colour and one motion contract**, so a reader can tell "this is a calculator, not a finding" before reading a word (see §5.1).

## 5. Colour system — one source of truth

### 5.1 Semantic roles (single module: `app/src/constants/palette.ts`)

| Role                 | Token                       | Value                 | Never used for   |
| -------------------- | --------------------------- | --------------------- | ---------------- |
| Surface              | paper / card                | `#F6F3EC` / `#FFFEFA` | —                |
| Text                 | ink / muted-ink             | `#172E33` / `#526368` | series           |
| **HDB**              | teal                        | `#006B65`             | anything else    |
| **EC**               | rust                        | `#B64426`             | anything else    |
| **Condo**            | plum                        | `#66508A`             | anything else    |
| Observed vs modelled | ink solid / ink 40% + hatch | —                     | never a hue      |
| Positive / negative  | ink + ▲/▼ + sign            | — (not red/green)     | series colours   |
| Withheld / review    | note                        | `#F8E8CC`             | success or error |
| Error                | error                       | `#A42E36`             | negative deltas  |

Two rules make it unambiguous:

1. **A hue means a property type or nothing.** Direction of change is encoded by arrow + sign + text, so it survives colour-blindness and greyscale printing — the pack's "selected states use text/icon, not colour alone" rule applied to data.
2. **Sequential scales get one ramp**: a single teal ramp for the map, with a visually distinct "no observed value" fill (hairline + diagonal hatch, already used in 09/17).

### 5.2 Kill list (each is a one-line deletion, verifiable by grep)

- The four local palette arrays in `charts/{ComparisonChart,TimeSeriesChart,StatisticalPlot}.tsx` and `dashboard/MarketOverviewDashboard.tsx:57`.
- Hardcoded `#3b82f6` (7 occurrences), `#10b981` (7), `#f59e0b` (6), `#ef4444` (6), `#8b5cf6` (4).
- YlOrRd stops in `PriceMap.tsx`, `LeaderboardMap.tsx`, `ExplorerMap.tsx`.
- `prose prose-slate dark:prose-invert` — dead classes (`tailwind.config` `plugins: []`); either install `@tailwindcss/typography` and theme it to Fieldnotes, or delete the classes and keep the explicit `.prose` rules.

### 5.3 Token defects to fix in `globals.css`

- `--primary` currently equals ink, so "primary action" and "body text" are the same colour. Introduce `--brand` (teal) for action and leave `--primary` for text-scale use, or invert.
- `--accent` and `--secondary` are identical (`#E5EFEB`). Separate **hover** (`paper` −6%) from **selected** (`#E5EFEB` + ink left border), so the three states in S3's accessibility work become visually distinct too.
- Dark mode: either tokenize it against the Fieldnotes ramp and verify contrast, or set `color-scheme` explicitly and stop offering a toggle that yields unreviewed charts. The current middle state is the worst option.

### 5.4 Acceptance for the colour slice

- `grep -rn "#[0-9a-fA-F]\{6\}" app/src/components` returns only `palette.ts` and SVG/logo assets.
- Every chart's legend, tooltip and table use the same property-type colour for the same series (spot-check HDB in `/dashboard`, `/explore`, `/research/trends`, `/areas/*`).
- Greyscale screenshot of `/explore` and one study still distinguishes series by labels.
- No pair fails WCAG AA contrast (ink on paper 12.85:1 already measured in S3).

## 6. Report length — the three-tier page

### 6.1 Tiers

| Tier | Content                                                                                                | Length budget        |
| ---- | ------------------------------------------------------------------------------------------------------ | -------------------- |
| 1    | The question, 3 headline numbers, evidence status, "what this is not"                                  | **≤ 1 screen**       |
| 2    | One finding per block: claim → chart → sample/source line                                              | ≤ 1 screen each      |
| 3    | Evidence tables, method detail, technical appendix — inside a disclosure, or the page's own table view | unbounded, collapsed |

Today `findings.md` already opens with `## Key Takeaways` — the narrative instinct is right; the failure is that tiers 2 and 3 are interleaved, so 7 raw tables sit inside the argument.

### 6.2 Budgets that make "too long" testable

1. Every page states its question and answer within the **first screen**.
2. **No table taller than 600 px renders inline.** Anything larger becomes `<details>` "Evidence table" or moves to the page's Table view (the pattern `/explore` already uses).
3. Any page over **6 screens** must either be split or have its tier-3 content collapsed — enforced by a viewport-height assertion in the existing Playwright suite rather than by taste.
4. **In-page nav from `md` up**, not `xl` only. `TableOfContents.astro` is `hidden xl:block`, so 768–1279 px readers have no in-page navigation at all.

### 6.3 Where the length goes

- `/analytics/findings` 16 → **≤ 7 screens**: keep Key Takeaways, collapse the two 1,000 px+ tables, and let each remaining table link to the catalog dataset it came from.
- `/analytics/data-sources` (8 H2s) is not a study — it is the **Data & methods guide**. Move it to `/data`, and keep a `Sources` appendix link in studies that use it. This also retires one of the 15 flat study links.
- `/dashboard/` 4.6 → ~2.5 screens: it duplicates the proposed Overview. The Overview keeps the national answer + 3 pathways; "Market Snapshot" and "Monthly series" belong to `Research › Trends`.

## 7. Status — S9–S12 landed, owner decisions applied (uncommitted)

Every slice below is implemented in the working tree, reviewed by an independent reviewer, and gated as a whole.

| Gate                                          | Result                                                          |
| --------------------------------------------- | --------------------------------------------------------------- |
| `test:unit`                                   | **575 pass**, 0 fail, 36 files                                  |
| `astro check`                                 | **0 errors / 0 warnings / 21 hints**, 234 files (from 227)      |
| Root E2E                                      | **254 passed / 9 skipped** (241 baseline + 13 new budget tests) |
| Pages-prefixed E2E                            | **9 passed / 0 skipped**                                        |
| docs validators, prettier, `git diff --check` | clean                                                           |
| `app/public/data/catalog.jsonl.gz`            | restored                                                        |

**S9a — chart palette.** `app/src/constants/palette.ts` is the only source of chart colour: teal = HDB, rust = EC, plum = condo, ink = aggregate, plus a neutral `CATEGORICAL` and a `SINGLE_SERIES`. Seven components consume it. Measured on `/dashboard`: 454 nodes teal `rgb(0,107,101)`, 72 plum, 72 rust — the blue/emerald/amber set is gone. `--accent` now differs from `--secondary` (warm hover vs cool selected).

**S9b — map ramps.** One 7-step teal ramp (`#F1F7F5` → `#006B65`) replaces five map palettes; `sequentialStep(index, stepCount)` spreads any bin count across it with **no two bins colliding** (the first attempt collapsed PriceMap's 7 thresholds onto 6 steps and the reviewer blocked it). Signed metrics use one odd-length rust→neutral→teal ramp whose legend names the direction in words. Selection and focus are **ink** — solid vs dashed — so no interaction state borrows a property hue. `utils/geo-projection.ts` now owns no colour at all. Verified by reading computed fills per map (7 distinct on `/dashboard/map`, 5 on `/explore`, neutral no-data `rgb(236,231,219)`).

**S10 — shell.** Four destinations (Overview · Explore · Research · Data & methods) in a fixed header; the sidebar is a per-section menu. Sidebar links on `/` went **31 → 11**; 9 on research and catalog routes. Exactly one `aria-current="page"` per route, with the containing destination marked `"location"`. The two duplicate research subnavs collapsed into one.

**S11 — three-tier article.** A `rehypeWrapTables` plugin (inline in `app/astro.config.mjs`, beside the existing remark helpers) wraps every markdown table in a focusable, labelled scroll region capped at 600 px with a sticky opaque header; chart-paired tables are exempt because the chart marker must stay adjacent to its table. The two status cards became one strip (every fact retained). The in-page nav is **one element**: a sticky bar from `md` to `xl`, the right rail above it. A new 13-test spec pins screen-height ceilings.

Measured at 1280×720: `findings` **16.04 → 14.09**, `lease-decay` 6.93 → 6.72, `data-sources` 6.43 → 6.25, `causal-inference-overview` 6.30 → 6.11.

**S12 — `/data`.** The provenance guide exists and the fourth destination points at it. Its thesis is that there is no single "last updated", so each asset shows **observation period, coverage and export clock separately**, and a missing clock says so in words. Every figure is derived at build time. Building it exposed how stale the design mock's numbers were: the mocks carry 78,796 transactions / 441 months / "24 Oct 2026"; the shipped assets say **78,799 / 442 / 2026-11-03**, and `dashboard-release-v2.json` has `generatedAt: null` while the area and trends assets embed no export clock at all.

**Owner decisions applied (2026-11-28):**

- **D1(a) — findings length accepted and ratcheted.** The E2E budget for
  `/analytics/findings` is now **14.1 screens** (measured 14.05); raising it must
  be a deliberate edit to `app/tests/e2e/analytics/layout-budget.spec.ts`. A split
  was rejected because the live text and the approved edition would diverge — the
  page reports the registry, it does not hash what it renders, so editing the
  study is an **evidence action**, not a layout one.
- **D2(a) — `/` is the editorial Overview.** The marketing hero is gone;
  `app/src/components/overview/OverviewSurface.astro` renders the same surface for
  `/` and `/dashboard`, which keeps a base-aware `rel=canonical` and a
  compatibility note. A derived provenance line restored the two facts the hero
  carried: `2025 complete year · 78,799 transactions · 1,234,854 rows in all
history · 1990–2026 (36 years) · nominal SGD · repository snapshot · exported
3 Nov 2026 · from dashboard_overview`.
- **D3(a) — no more chart-paired exemption.** `InlineChartRenderer` now inserts the
  chart after the table's scroll region, so all 15 previously-uncapped tables are
  capped and every markdown table in the tree obeys the same rule. Verified in the
  browser: chart top 2964 > table bottom 2931, `closest('.table-scroll') === null`.
- **D4(b) — light only.** `DarkModeToggle` and the `.dark` token block are deleted,
  `color-scheme: light` is set on `:root`, and the header comment records that the
  66 remaining `dark:` utilities are inert. The cross-page spec that asserted the
  toggle was replaced with a light-only assertion rather than deleted.
- **D5(a)** — the `data-sources` study and `/data` guide both stay; the guide links
  to the study.
- **Mobile overflow fixed** as well: `/explore` no longer scrolls horizontally
  (718 px → 390 at a 390 px viewport) after `grid-cols-1` on the workspace grid and
  `break-words` on the release-status digest.

**Known gaps, in priority order:**

1. **`/analytics/findings` stays at ~14 screens** by decision. Reaching the original
   ≤7 target needs a signed edition (D1(c)), not a layout change.
2. **Rollback has no practised fast path.** Rehearsed 2026-11-28: dispatching a
   commit SHA fails (`422 No ref found`), and a tag at the old commit fails at
   `deploy` because the `github-pages` environment allows `main` only. Revert-on-main
   works but costs a CI cycle; see the audit handoff §2.3.
3. **A study page exposes no `aria-current="page"` leaf** — the nav lists
   destinations, not documents, so `/analytics/findings` marks Research `location`
   only. Accepted.
4. **The `data-sources` study and the `/data` guide overlap** (D5(a) keeps both).
5. **66 inert `dark:` utilities** remain across `.astro`/`.tsx`; harmless, not swept.

## 8. Sequencing

Each slice is independently shippable and verifiable; none requires a route rename.

| Slice                 | Work                                                                                                               | Acceptance                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| **S9 — palette**      | `constants/palette.ts`; kill list §5.2; token fixes §5.3                                                           | §5.4 checklist; no visual regression in 575 unit tests                                                           |
| **S10 — shell**       | `components/shell/`; four destinations + research subnav; delete the 2 local subnav copies; sidebar → section menu | 31 → ≤8 global links; `aria-current` still exactly one per page; drawer focus trap unchanged; Pages-base E2E 9/9 |
| **S11 — article**     | Tier 1/2/3 shell for `analytics/[slug]`; `md`-up TOC; table disclosures                                            | findings ≤ 7 screens; budget assertions in Playwright                                                            |
| **S12 — `/data`**     | Build 08: three clocks (observations / coverage / export), definitions, catalog entry                              | study pages link to it and stop restating provenance                                                             |
| **S13 — consolidate** | Maps: pick the canonical workspace, make the other three wrappers                                                  | one implementation per archetype in §4                                                                           |

Do them in that order: S9 before S10 (the shell should not adopt new colours and new structure at once), S11 before S12 (collapse first, then move what remains).

## 8. Not proposed

- No framework change, no new data pipeline, no new analytics content.
- No URL churn: `/analytics/*` stays because the edition registry and archive verification pin it.
- No dark-mode redesign beyond choosing one of the two honest options.
- No network search/index service; if the study list still feels unfindable after S10, revisit with a build-time index rather than a hosted one.

## 9. Owner decisions

| #   | Decision                                                                         | Default if silent                  |
| --- | -------------------------------------------------------------------------------- | ---------------------------------- |
| 1   | Rename the Studies section in navigation while keeping `/analytics/*`            | Rename in nav only                 |
| 2   | Dark mode: tokenize + verify, or remove the toggle                               | Tokenize, verified                 |
| 3   | `/dashboard/*` compatibility routes: keep indefinitely or retire after one cycle | Keep indefinitely                  |
| 4   | Report budget enforcement in CI (screen-height assertions)                       | Enforce from S11                   |
| 5   | Build the `/data` guide from `docs/analytics/data-sources.md`, or author fresh   | Move and reshape `data-sources.md` |
