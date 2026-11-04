# Per-feature specification / revision 2

This document closes the first edition's feature-depth gaps. Every layout is proposed. “Stored” means a value exists in an asset, not that its analytical derivation is verified.

## Routing and capability map

| Capability            | Canonical proposed destination   | Existing path to preserve                                                   | Visual  |
| --------------------- | -------------------------------- | --------------------------------------------------------------------------- | ------- |
| Annual overview       | /                                | /dashboard compatibility entry                                              | 01 / 04 |
| Joint area comparison | /explore                         | /dashboard/leaderboard                                                      | 02 / 05 |
| Observed price map    | /explore?view=map                | New joint-selection map; not a complete legacy-map replacement              | 09      |
| Area fieldnote        | /areas/[slug]                    | New route                                                                   | 03      |
| Monthly trends        | /research/trends                 | Move current overview chart capability here; old /dashboard/trends is tools | 10 / 16 |
| Research segments     | /research/segments               | /dashboard/segments                                                         | 11 / 12 |
| Decision tools        | /research/tools                  | /dashboard/trends                                                           | 13 / 18 |
| Research map          | /research/map                    | /dashboard/map, including existing metric/layer query                       | 17      |
| Studies and personas  | /analytics and existing children | All existing article/persona URLs                                           | 14      |
| Methods               | /data                            | New guide, not a catalog replacement                                        | 08      |
| Catalog / lineage     | /catalog and existing children   | Keep current nested external dataset URLs                                   | 15      |

Research secondary nav is always visible on desktop: **Studies / Trends / Segments / Tools / Research map**. On mobile, Menu exposes every destination and the Research hub supplies named entry links (16). New route names are proposals; implement aliases sharing one workspace, not divergent copies.

## Observed map / 09

Data: `map_metrics.year_2025_hdb` and actual `planning_areas.geojson` geometry. SVG polygons are simplified vectors from all 55 features, not an illustrative Singapore silhouette.

- Exact canonical join is `PLN_AREA_N` or normalized lowercase equivalent. Missing join ≠ zero.
- 2025 HDB: 31 areas, 25 ≥150 selected-subset sales, 6 thin. Selected Tampines is S$710,000 / 1,921 / S$620 PSF.
- Five bins: <550k; 550–<650k; 650–<750k; 750–<850k; ≥850k. Lower-inclusive except unbounded first bin. No-data/thin regions are neutral and explained.
- Thin-sample and no-data are combined visually in the desktop example; inspection/list must distinguish their reason. Allow revealing thin samples explicitly.
- Zoom/pan never changes analytical filters. Selected outline and accessible row remain synchronized. Enter on named area action opens fieldnote; selection itself does not navigate.
- Geometry-only mode works without external tiles. Add provider tiles only with correct attribution/licensing/configuration. Accessible table is equivalent, not a fallback with different filters.
- Research overlays are a separate evidence context; do not merge their vintage into a 2025 transaction legend.

## Research layers / 17

Retain exact nine IDs:

- Spatial: `spatial.hotspot`, `spatial.lisa`, `spatial.neighborhood`.
- Features: `feature.mrt`, `feature.school`, `feature.amenity`.
- Predictive: `predictive.policy`, `predictive.lease`, `predictive.forecast`.

Preserve `metric`, `timeBasis`, `propertyType`, `area`, `layers` legacy query semantics and unknown-layer warnings. Do not discard the query on a legacy route redirect.

Units: hotspot z dimensionless / p 0–1; LISA categorical; local Moran I dimensionless; spatial lag SGD; neighborhood multiplier ×. MRT coefficients S$/sq ft/100m, CBD km; school/amenity indices 0–10. Predictive projected changes/intervals %, six-month target date, policy sensitivity SGD, lease values SGD.

Current 41-entry research extracts differ from 55-feature geometry. Spatial zero/one/STABLE defaults and historical forecasts are **not validated current model evidence**. Default archive state keeps underlying stored fields inspectable but analytical fills/recommendations gated. A layer may become active only after source owner, model/generator, period, units, validity status and tests are recorded. Failure in one layer must not erase working observed data.

Show per-layer loading/error/unavailable status, legend and metadata. Preserve multiple layer selections but avoid multiple competing polygon fills: choose one active fill plus independently meaningful outlines/markers; if quantities conflict, ask the user to choose a fill rather than silently overpaint. Clear removes layers, not selected area or unrelated settings.

## Monthly trends / 10 and 16

Existing source: `dashboard_trends`, fields `date`, `HDB Price`, `HDB Volume` and equivalent EC/Condominium. Values are monthly medians/counts, not average prices.

Illustrated selection: Jan–Dec 2025 HDB, all 12 months. Jan 612,888; Sep 645,000; Dec 635,000; annual sum of monthly counts 25,084; Dec count 2,024. Never sum price medians or average them into an annual median.

- Single housing type first, range within actual source dates; optional multi-series comparison only with visibly separate coverage and legend.
- Price line uses explicit zoomed 600k–660k axis. Volume bars share month alignment and zero–3,000 scale. Never apply the zoom to volume bars.
- Null months break lines; missing volume stays missing rather than inferred zero. Exact calendar lag required for MoM/YoY.
- Mouse/focus month detail includes date, price, sales and source. Arrow-key chart interaction is optional if a complete adjacent table provides equivalent access.
- Mobile keeps all points, reduces tick density, and links to the complete month table. No scroll/zoom gesture is required to obtain exact values.
- Keep the global series-end date separate from the selected range. No current timestamp is embedded in this asset.

## Segments / 11, 12 and 20

Source: `segments_enhanced`, version 1.0.0, lastUpdated 19 Apr 2026; six archetypes. Stored avgPricePsf, cohort counts, yields and forecasts are **research fields of incompletely specified scope**, not joint year/property transaction medians.

- Retain persona choices all/investor/first-time-buyer/upgrader. Choosing a persona applies existing preset constraints; explain changes, and keep a Reset to persona action.
- Budget control is price **per square foot**, not total spending capacity. Property types are multi-select; CCR/RCR/OCR are research market segments, not administrative regions.
- Existing weighted matching is retained initially: budget 25, type overlap 20, region overlap 15; optional goal 30 / horizon 10; normalize by active weight sum; spatial class is hard. Expose the contributing criteria. A 100 match is not 100% probability, and partial matches do not promise every constraint is satisfied.
- Discover renders six actual names, stored averages, evidence status, Investigate and Add/remove comparison. Never claim the word “Recent” means current.
- Investigate requires a selected segment. Build linked rows from the segment's planningAreas, then use buildSegmentAreaRows semantics for area PSF, region and class constraints. No invented property-specific area average.
- Selected Bishan research average is S$644 PSF; primary observed 2025 HDB Bishan median is a different quantity. Context-switch action must name type/year and never overwrite the archive value.
- Existing query state: persona, tab, segment, segments (up to four IDs), area. Add serialization for visible constraint fields deliberately; currently those are not all persisted.
- Compare unlocks with 2 segments, caps at 4, independent from selected investigation segment. Removing/replacing a segment leaves the others intact; fifth add gives a named limit explanation.
- Research cohort counts can overlap. Do not sum counts/market shares or interpret differences as causal returns.
- Forecast/yield/persistence outputs stay definition-gated; show availability explanations rather than investment advice. Preserve existing capabilities as archive inspection until validated.

## Tools / 13, 18 and 19

### Financing / existing affordability capability, proposed aligned scenario

Reference price can be copied explicitly from the observed explorer/detail selection. Inputs are user-specified assumptions, not private household records. Default example: S$710,000; annual income S$120,000; 30% down; 25 years; 3% nominal annual interest.

Formula: principal = price × (1−downPayment); monthly r = annualRate/12; n = years×12; payment = P×r/[1−(1+r)^−n]. At r=0 use P/n. Compute with unrounded values, round only display.

Outputs: down S$213,000, loan S$497,000, payment S$2,357, monthly income S$10,000, payment/income 23.6%, price/annual income 5.92×. Sensitivity 2/3/4/5/6%: S$2,107 / 2,357 / 2,623 / 2,905 / 3,202.

Proposed editable validation: price >0, income >0, down 0–100%, years >0 within a documented mathematical UI range, rate ≥0; blank/invalid input withholds outputs and names the invalid field. Browser state only; do not log income/values in analytics or copy them into URL by default. Do not claim these ranges determine lender eligibility.

The current calculator instead reads a separate period-unknown extract, uses fixed 30%/25yr/3%, calls the average of area medians a national average, and has different thresholds from published pipeline affordability. Do not carry those automatic categories/loan-approval assertions into the new scenario.

### Lease bands

Retain 40–99 remaining-year input and source-band inspection. At 75: stored remaining interval 74–79, discount_percent 19.1, annual_decay_rate .25, transaction_count 29,913. Display as a stored statistic with unknown extract date/period, not a forecasted loss.

SVG 18 uses signed interval marks, sorted by remaining years, not a smoothed fitted curve. Negative discount means premium. Existing inclusive shared endpoints require a documented half-open bin policy after source reconciliation; do not silently change outcomes during UI migration. Preserve archive lookup behavior if needed, with disclosure. Inconsistent safe/cliff labels and fixed advice remain withheld.

### MRT/CBD

Retain type, canonical town, MRT metres, CBD km; propose explicit square feet instead of hidden ×1,000. Withhold total-price output until coefficient units, baseline/proximity direction and the 500m cap are resolved. The new floor-area control is **P**, not an existing input.

Normalize title-case/uppercase keys; do not allow fallback coefficients to masquerade as matched area data. Show the supplied coefficient and formula with units. No 7×/15× boilerplate or unsupported causal assertions.

### Spatial patterns

Current towns[] vs expected clusters[] crashes; isolate with runtime schema validation and a tool-specific error boundary. Do not fabricate missing five-year or PSF fields from total prices. Initially permit dated label inspection only; return simulations and allocation recommendations require a reviewed source/model contract. Do not compound an undefined-period change as annual appreciation.

### Responsive tool and segment states

SVG19 shows the complete financing form/result on mobile; fields retain units, no hidden desktop-only assumptions, income stays local, and the sensitivity table opens inline. Tool selection is a native dropdown exposing all four tools. On narrow screens, model-review panels follow inputs/results in reading order rather than floating to the side.

SVG20 shows selected-segment investigation with readable area cards, selected-area evidence, an explicit observed-context handoff and comparison-set status. Constraints open an accessible draft/apply sheet using the same lifecycle as Explorer, but with research PSF/type/market-segment/class controls—not the observed 150-sale gate. Mobile comparison shows one named metric row across two selected cohorts or stacked definition groups; source labels and independent remove controls remain available. At three/four cohorts a labeled local table scroller is permitted with a two-cohort comparison alternative, never body-wide overflow.

## Studies and article reading / 14

Retain all article/persona URLs and source Markdown. Proposed search filters title/description/category; audience filter uses persona frontmatter. Do not invent readership scores or global coverage KPIs.

Article provides one H1, publication/observation/model dates when known, TOC, key findings, readable source tables, methodology/limitations and related explorer links. On mobile TOC becomes an inline disclosure; no fixed sidebar over text.

Opt-in chart markers remain adjacent to their tables. Do not auto-chart dictionaries or combine unlike units on one axis. The lease article contains a PSM/PSF discrepancy; show a review warning and withhold that misleading chart until repaired. No new lease finding is asserted.

## Catalog / 15

Keep catalog overview/layer/dataset routes, table search, DAG, schema fields and upstream/downstream links. IDs/slugs for external sources retain their nesting rules.

Show distinct concepts: storage dtype, declared schema requiredness/ranges, observed null count and snapshot age. “Available” is artifact presence, not correctness. Current catalog says 1,233,405 unified rows, while local platinum has 1,234,928. A discrepancy banner must not rewrite either number or expose raw records.

Field search filters names/descriptions; graph has pan/zoom and a named dependency-list alternative. Click a dependency opens its dataset page; loading/unavailable catalog data leaves research/observed exploration usable. No raw address-level download button is added.
