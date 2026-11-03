# Design rationale

## Chosen product direction

**A housing field guide: question → comparable evidence → area fieldnote → method.**

The strongest available data is not a feed of current listings. It is observed historical transactions, precomputed group medians and a body of research. The design should teach a reader what can be compared before asking them to choose a “best” investment.

Primary editorial question: **“What does a home cost here?”** The overview separates housing types; the explorer keeps period and type coupled; area detail compares with a national baseline of the same type/year. This is an evidence-led replacement for interchangeable KPI cards and unqualified growth leaderboards.

Audience hypothesis: curious buyers/upgraders first, then researchers and investors. No user research was available; validate comprehension with these groups before release. Success means users can name the selected period/type, find an area, interpret the sample, and distinguish a median from a valuation.

## Reference research and limits

Browsing was available, but original FiveThirtyEight article/project URLs redirected to ABC Politics rather than their original graphics:
- [How to Read 2020 Polls Like a FiveThirtyEighter](https://fivethirtyeight.com/features/how-to-read-2020-polls-like-a-fivethirtyeighter/)
- [How Our Polling Averages Work](https://fivethirtyeight.com/methodology/how-our-polling-averages-work/)
- [2024 election forecast](https://projects.fivethirtyeight.com/2024-election-forecast/)

Search results surfaced their methodology themes, but full original pages were **not accessible**. Do not treat those search summaries as a visual audit.

Accessible references actually inspected:
1. [FiveThirtyEight public data repository](https://github.com/fivethirtyeight/data): story-linked datasets/code, explicit update cessation for sports forecasts, license and attribution.
2. [College majors data README](https://raw.githubusercontent.com/fivethirtyeight/data/master/college-majors/readme.md): source vintage, cohort definitions, samples and field-level documentation accompanying an editorial question.
3. [Matplotlib's FiveThirtyEight-inspired style](https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/mpl-data/stylelib/fivethirtyeight.mplstyle): readable 14pt default, strong lines, subdued background, solid grid and restrained categorical color. This is a **third-party interpretation**, not an official branding source.

Accordingly, the editorial/visual direction is an original interpretation of the requested principles, grounded in accessible data publishing/style references, **not a copy of inaccessible archived layouts**.

Adopt:
- An explanatory headline and chart title, not only a metric name.
- Source, denominator/sample and definitions next to the claim.
- Restrained color, visible shared scales, strong direct labels.
- Explicit distinctions between observed results, derived/model outputs and uncertainty.
- Methodology as part of reading, not a hidden modal afterthought.

Do not adopt political/sports branding, logo, exact color system, probability charts without probability data, or invented uncertainty bands.

## Options considered

| Option | Benefits | Costs / migration | Decision |
|---|---|---|---|
| Incremental enhancement | Small patches to typography, sidebar and cards; low route risk | Leaves duplicated workflows and incorrect cross-filter semantics; weak trust improvement | Insufficient: data meaning, not just cosmetics, is the main issue |
| Substantial redesign within Astro/React | New shell, evidence-first overview, consolidated explorer and detail; reuse static assets, research/catalog, chart/map libraries | Moderate UI/test migration; joint-subset adapter and metadata work required; legacy links need adapters | **Recommended and executed in these assets** |
| Frontend rebuild | Freedom to replace state/routing/rendering architecture | High framework/content migration cost, static-hosting and BASE_URL risk, research/catalog regressions; does not fix source semantics | No evidence of a framework blocker justifies it |

Retain Python Hamilton and maintenance export. There is no need to invent a server API to filter 31 area aggregates. Revisit transport architecture only after measuring payload/hydration costs and identifying a real need for finer-grain data.

## Major decisions and evidence

### 1. Show a complete supported year first
2025 has joint national/property and area/property data. Showing an all-history median as “today's market” is misleading, and a blended trend spanning HDB's 1990 start and private property's 2021 start is composition-sensitive. Keep historical views discoverable, labeled literally.

The year must eventually become a generated supported-period contract. Until that work exists, use the verified fixed year rather than silently claiming an arbitrary rolling range.

### 2. Make comparison the default, map optional
The existing map occupies most of the first comparison viewport and relies on external tiles; local runtime displayed a provider-key warning. A compact ordered chart/list is readable without tile service or spatial expertise. Preserve Leaflet's area interaction behind Map with a list equivalent, honest legend and attribution.

### 3. Replace ranking authority with visible evidence
“Lowest observed median” is defensible; “best town” is not. 150 sales is an explicit proposed caution threshold for the selected subset, not a statistical guarantee. Show exactly how many areas are hidden; allow revealing them with a warning. Sorting is a task, not an investment recommendation.

### 4. Keep source metrics on the same sample
Use `map_metrics[period_type][AREA]` for median price, PSF and volume. Do not adapt the existing leaderboard's property-first/period-second fallback to this workflow. Do not present all-time affordability or modeled private yield as selected-year facts.

### 5. Add area fieldnotes rather than property valuations
A new static area route can explain Tampines using existing aggregate numbers without exposing addresses or promising a new valuation engine. The national comparison is a level difference, not appreciation or an adjusted location premium. No missing distributions or confidence bands are fabricated.

### 6. Demote unqualified research claims, preserve the research
Keep the Markdown collection, opt-in charts, math and detailed analyses. Replace sensational home teasers with neutral questions and surface each report's vintage/assumptions. Investors still reach yield/segment tools; modeled/fallback values must first be labeled or withheld.

### 7. Make provenance a destination and an inline component
Added [08-data-methods-desktop.svg](08-data-methods-desktop.svg), because export time, observation period and source freshness differ. This workflow is essential to the product's credibility. The current missing provenance pointer and mixed research vintages make a generic “updated today” badge unacceptable.

## Revision 2 / broader functionality, not more KPI cards

The audit showed that preservation in prose was insufficient. Added actual polygon exploration (09), monthly medians with aligned volume (10/16), six-segment discovery and investigation/comparison (11/12/20), explicit financing and model-tool states (13/18/19), article/library reading (14), catalog schema/lineage (15), and all nine research layers (17). Overview now exposes these pathways directly.

Separate observed map and research map contexts prevent mixing a fixed 2025 aggregate with a historical or placeholder model. Retention means discoverability, stable state/URLs and safe archive inspection—not promoting unreliable numeric outputs. Model gates and runtime defects are documented in [audit-review.md](audit-review.md); the next-stage work is specified in [implementation-plan.md](implementation-plan.md).

## Original identity and design tokens

“Fieldnotes” is an internal visual-direction name, not a proposed corporate rename. Retain Egg n Bacon Housing recognition.
- Paper `#F6F3EC`; surface `#FFFEFA`; ink `#172E33`.
- HDB teal `#006B65`; EC rust `#B64426`; condominium plum `#66508A`.
- Secondary text `#526368`; control boundary `#7A8583`; separators `#CDD2CA`.
- Selected fill `#E5EFEB`; review/proposal note `#F8E8CC`; error `#A42E36`.
- Georgia/serif editorial headings; Arial/Helvetica/sans-serif controls and data. Local fallbacks only.
- 48px desktop H1 / 33–34px mobile; 24–30px sections; 16–18px body; 12–14px sources/labels. Small uppercase review tags are not body text.
- 56px desktop and 20px mobile gutters; 24/16px gaps, mostly 4px radius, no decorative shadow system.
- Zero-based bars; source-period sample labels; numeric axis and direct values. Teal national marker has a textual label and dashed/solid encoding.

Accessibility and responsive details live in [interaction-spec.md](interaction-spec.md). Contrast checks and visual-inspection limits live in [validation.md](validation.md).

## Consequential tradeoffs

- Fixed 2025 examples prioritize reliable comparison over a false sense of real-time currency.
- Removing yields from the primary plot reduces investor immediacy but avoids comparing observations with undocumented formulas.
- No regional filter until administrative vs market-segment taxonomy is resolved.
- Navigation consolidation must not retire working segment/tools/catalog capabilities; migrate them incrementally.
- No inter-area shortlist/personal accounts, mortgage recommendation, new forecasts, address search or raw transaction download is promised by this phase.
