# Design audit / revision 2

## Model-routing correction

The original session successfully tested only the standalone Codex account route for Luna 6.0, which rejected `gpt-6-luna`. It was incorrect to generalize that failure to every available integration.

This review explicitly invoked the available **luna-reviewer** subagent, configured as **`openai-codex/gpt-6-luna:xhigh`**. It completed a read-only design/feature audit with no substitution. Standalone Codex still rejected the model; OpenCode's listed `opencode-go/gpt-6-luna` endpoint still failed with an expired-key error. These are different access routes. No credentials were inspected or changed.

DeepSeek V4.1 Flash independently reviewed model/tool contracts through OpenCode's available free endpoint. Sol independently verified critical numbers, runtime failure and source contracts, resolved contradictory findings, and authored all revisions. Neither investigator edited deliverables.

## Audit verdict

**The first edition was visually coherent but functionally too narrow.** It overrepresented observed HDB price comparisons and relegated trends, nine map layers, segment investigation/comparison, calculators and catalog to prose. The edition was not yet a lossless implementation brief.

Revision 2 retains the original visual direction but expands to **21 SVGs**, with actual geometry, monthly price/volume, six stored segments, investigation/comparison, all four tools, model-specific gates, research reading and dataset lineage.

## Findings and disposition

| Priority / issue | Evidence | Revision / remaining gate |
|---|---|---|
| P1: Cross-asset baseline was shown while compatibility remained unverified | Initial SVG 03 vs fail-closed screen-data-map requirement | Independently recalculated both 2025 HDB medians/counts from one local platinum frame; matched current public assets. SVGs 02/03/05 say reconciled **design snapshot**, not a production generation guarantee. SVG 06 shows incompatible-generation state. Production manifest/hash compatibility remains a release gate |
| P1: Observed map migration could erase existing research layers | PriceMap.tsx:92–110,158–180; analytics.ts:152–186; initial IA | SVGs 09/17 separate observed map from research archive. Preserve old map route, metric/time/type/area/layers parameters; add research alias without dropping state |
| P2: Trends had no actual destination screen | MarketOverviewDashboard.tsx:425–430; dashboard/trends.astro:21–49 renders tools | SVGs 10/16 explicitly specify price + volume trends. New /research/trends is not the old tools route |
| P2: Segment workflow/shortlist was only named | SegmentsDashboard.tsx:44–108,184–201,281–310 | SVGs 11/12 specify six actual archetypes, selected research area, two/four comparison limits, independent states and source status |
| P2: Tools retention was ambiguous | InteractiveToolsPanel.tsx:149–177; initial “no buyer income model” phrasing | SVGs 13/18 retain four named tool paths. Financing is explicit amortization with illustrative user inputs, not a new eligibility/income model |
| P2: Generic median definition was too literal | Initial SVGs 01/04/08; even HDB national sample | Corrected ordered midpoint / mean of two central values if even. Median PSF means median of transaction-level ratios |
| P2: Baseline inclusion difference not visible | 2025 local recalculation and exporter residential exclusion | Exact cohort check: national 25,084; area map 25,082; 2 Sungei Kadut sales excluded from map; no missing planning areas in 2025 HDB. SVG 03 states the difference |
| P2: Reused reload hook cannot meet proposed stale-state semantics unchanged | useGzipJson.ts:47–56,98–100,123 | Explicit refactor in plan: distinguish foreground retry from forced background revalidation, preserve cached snapshot on refresh failure |
| P2: Retained research index has undefined “11 Years” coverage | analytics/index.astro:138–140 | Remove or replace with per-study/source coverage, not one global timer |
| P3: Mobile pagination omitted position | Initial SVG 05 vs interaction spec | Added Page 1 of 7 |
| P2: Catalog values were assumed to match pipeline generation | catalog.jsonl.gz unified_dataset vs current platinum | SVG 15 shows catalog 1,233,405 vs current local 1,234,928, with source-labeled discrepancy rather than silently changing catalog values |

## Additional backend/tool audit findings

### Runtime-confirmed failure
Selecting **Spatial Hotspots** on the existing Decision Tools page throws `Cannot read properties of undefined (reading 'flatMap')`. Sol reproduced it in Chromium. The asset has `towns[]`; SpatialHotspotExplorer.tsx:93 expects `clusters[]`; dashboard/trends.astro passes the decompressed object without adapting that shape. MRT/CBD, lease and affordability tabs produced no captured page exception in the same short test. This is not proof their results are correct.

### Verified source-level defects and risks
- Overlay components read lowercase `pln_area_n` ([SpatialAnalysisOverlay.tsx](../../app/src/components/dashboard/map/overlays/SpatialAnalysisOverlay.tsx):35; [FeatureImpactOverlay.tsx](../../app/src/components/dashboard/map/overlays/FeatureImpactOverlay.tsx):37; [PredictiveAnalyticsOverlay.tsx](../../app/src/components/dashboard/map/overlays/PredictiveAnalyticsOverlay.tsx):40), while the uncompressed reference used by the map has uppercase `PLN_AREA_N`. Main PriceMap handles both, overlays do not. Normalize once before reuse; gray is not a validated neutral result.
- Analytics assets contain 41 area entries; geometry has 55 polygons. Stored spatial z-scores/p-values are uniformly 0/1 and LISA is uniformly STABLE. Uniform school/amenity defaults and historical forecasts also need validation. SVG 17 exposes stored archive fields without active/current analytical shading.
- MRT/CBD formula caps distance at 500m, increases its positive term with distance and multiplies by 1,000 without an explicit floor-area input ([MrtCbdCalculator.tsx](../../app/src/components/dashboard/tools/MrtCbdCalculator.tsx):45–60). Default `Bishan` is not canonical `BISHAN`, so the default multiplier can fall back to 1 rather than the stored 1.8. Do not reproduce a purported default +45,000 result without correcting the case mismatch.
- Affordability All Towns is an unweighted average of town medians, not a national median; income changes do not change the HDB-only map source ([AffordabilityCalculator.tsx](../../app/src/components/dashboard/tools/AffordabilityCalculator.tsx):98–133,166–177). Tool defaults/thresholds differ from current published metric config.
- Lease uses inclusive endpoints and first-match lookup ([LeaseDecayAnalyzer.tsx](../../app/src/components/dashboard/tools/LeaseDecayAnalyzer.tsx):63–68). At 75, stored interval 74–79 returns 19.1% / 0.25% annual-rate field; hardcoded prose instead promotes a different 70–80 statistic. Negative “discounts” require signed labels; stored safe/cliff labels are inconsistent.
- The lease article's table labels a statistic “Median PSF” while its appendix calls the same 6,205 value median PSM. Its discount claims do not all follow directly from the displayed price medians ([lease-decay.md](../../docs/analytics/lease-decay.md):39–45 and technical appendix). Do not increase authority by auto-charting the mislabeled unit.

### Findings deliberately not accepted uncritically
DeepSeek's summary said 60–90 remaining years were absent; inspection disproved that: the stored intervals cover slider values 40–99, with shared endpoints. Its missing lease-*age* bands were being confused with remaining years. Descending x order also does not itself prove a chart zig-zags. These assertions were excluded from the design and plan.

Likewise, the 11,637 all-history missing-area count cannot be applied to 2025 HDB. Recalculation found zero missing 2025 HDB areas and identified the actual two-record exclusion difference. Independent verification materially refined the audit.

## Luna 6.0 follow-up / revised plan

A second read-only Luna 6.0 review accepted the explicit baseline-compatibility gate, exact two-record cohort disclosure and preserved map-query contract. It identified a concrete remaining implementation blocker: PriceMap.tsx:156–220 serializes defaults before its later effect reads incoming metric/timeBasis/propertyType/area. Sol reproduced it in Chromium: a median_psf / year_2025 / hdb / TAMPINES link becomes median_price / whole / all with area removed; the spatial.lisa layer survives. S0/S1 now explicitly require the first-load parse-before-serialize fix and regression test. This production bug is not claimed fixed by SVG edits.

## Not fixed in this phase

All production defects above remain **implementation work**. This phase changes design assets/specifications and produces the next-stage plan; it does not repair application code, models, data or infrastructure.

`cd app && bun run astro check` was executed as a baseline: **109 errors, 0 warnings, 45 hints across 112 files**. This is pre-existing application debt, not a successful type-check or a design regression. Full build/E2E/pipeline and assistive-technology testing remain outstanding.

## Follow-up

Use [implementation-plan.md](implementation-plan.md) for the next phase, [feature-specifications.md](feature-specifications.md) for per-feature contracts, and [validation.md](validation.md) for checks actually performed. The revised design is implementation-plan ready **with explicit data/model release gates**, not certified production-ready.
