# Sol / housing field guide

**Decision: substantially redesign the existing Astro/React application. Do not start a framework rebuild.** Retain the data pipeline and valuable exploration, research, map and catalog capabilities. Reorganize the public experience around comparable evidence.

## Review order and asset index

All screens are **proposed interfaces using existing aggregate values**, not screenshots of working new functionality. Amber labels identify new workflows; teal labels identify existing data. Those implementation-status labels are design-review annotations, not permanent production UI.

| Asset                                                                              | Viewport    | Purpose                                                                 |
| ---------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------- |
| [00-design-system.svg](00-design-system.svg)                                       | 1440 × 1420 | Original “Fieldnotes” identity, tokens, chart grammar, controls         |
| [01-overview-desktop.svg](01-overview-desktop.svg)                                 | 1440 × 1520 | Editorial entry: national 2025 property-type comparison                 |
| [02-explorer-desktop.svg](02-explorer-desktop.svg)                                 | 1440 × 1260 | Joint year/type area comparison, sample gate, optional map              |
| [03-detail-desktop.svg](03-detail-desktop.svg)                                     | 1440 × 1290 | Proposed Tampines evidence route                                        |
| [04-overview-mobile.svg](04-overview-mobile.svg)                                   | 390 × 1540  | Reflowed overview, not a scaled desktop canvas                          |
| [05-explorer-mobile.svg](05-explorer-mobile.svg)                                   | 390 × 1280  | Readable mobile rows, shared scales and filter summary                  |
| [06-interaction-and-states.svg](06-interaction-and-states.svg)                     | 1440 × 1460 | Failure states, small samples, selected area and mobile filter sheet    |
| [07-information-architecture.svg](07-information-architecture.svg)                 | 1440 × 1180 | Four primary destinations, journeys and migration                       |
| [08-data-methods-desktop.svg](08-data-methods-desktop.svg)                         | 1440 × 1340 | Essential provenance guide: observation, export and source clocks       |
| [09-map-and-overlays-desktop.svg](09-map-and-overlays-desktop.svg)                 | 1440 × 1440 | Actual planning-area geometry, observed map and research-layer handoff  |
| [10-trends-desktop.svg](10-trends-desktop.svg)                                     | 1440 × 1370 | Twelve actual monthly medians and aligned sales counts                  |
| [11-segment-discovery-desktop.svg](11-segment-discovery-desktop.svg)               | 1440 × 1380 | Six actual research archetypes, constraints and comparison set          |
| [12-segment-investigation-comparison.svg](12-segment-investigation-comparison.svg) | 1440 × 1520 | Linked area inspection and separate comparison state                    |
| [13-tools-desktop.svg](13-tools-desktop.svg)                                       | 1440 × 1540 | Financing arithmetic with explicit illustrative assumptions; four tools |
| [14-research-library-and-article.svg](14-research-library-and-article.svg)         | 1440 × 1510 | Library and article reading states, units review, method disclosure     |
| [15-catalog-lineage-desktop.svg](15-catalog-lineage-desktop.svg)                   | 1440 × 1330 | Schema, lineage and differing catalog/pipeline snapshots                |
| [16-trends-and-research-mobile.svg](16-trends-and-research-mobile.svg)             | 390 × 1500  | Discoverable research capabilities and mobile trends                    |
| [17-research-map-controls.svg](17-research-map-controls.svg)                       | 1440 × 1470 | Nine layer controls, historical metadata and model-validation gate      |
| [18-lease-and-mrt-model-tools.svg](18-lease-and-mrt-model-tools.svg)               | 1440 × 1490 | Actual lease intervals, MRT inputs/units and spatial contract repair    |
| [19-tools-mobile.svg](19-tools-mobile.svg)                                         | 390 × 1550  | Full mobile financing inputs/results, assumptions and privacy           |
| [20-segment-investigation-mobile.svg](20-segment-investigation-mobile.svg)         | 390 × 1560  | Mobile linked-area selection, evidence context and comparison set       |

**Revision 2: 21 SVGs.** Audit broadened feature coverage rather than just adding cosmetic variants.
Suggested order: **01 → 02/09 → 03 → 10 → 11/12 → 13/18 → 14/15/17 → mobile → 06/08/07 → 00**.

## Supporting specifications

- [Repository findings](repository-findings.md): verified architecture, data and limitations.
- [Design rationale](design-rationale.md): evidence, references and redesign/rebuild tradeoffs.
- [Screen data map](screen-data-map.md): field-level contracts and proposed dependencies.
- [Interaction specification](interaction-spec.md): behavior beyond static images.
- [Audit and disposition](audit-review.md): Luna 6.0 review, critical rechecks and revisions.
- [Per-feature specifications](feature-specifications.md): exact contracts, controls, state and evidence gates.
- [Implementation handoff](implementation-handoff.md): phase brief.
- [Detailed implementation plan](implementation-plan.md): next-stage plan, dependencies, ownership and gates.
- [Data evidence](data-evidence.json): aggregate snapshot values, checksums and arithmetic.
- [Validation record](validation.md): checks actually run and remaining limits.

## Using the files

Open each SVG directly in a browser at its natural width; these are long-page compositions, not fixed-height application viewports. Text remains selectable. Groups have semantic IDs; colors and font stacks are embedded. No scripts, raster images, external fonts or foreignObject.

Use semantic HTML for navigation, headings, controls, tables, sources and disclosures. Recharts/React can render charts; Leaflet can render the optional map. **Do not implement the web app as a giant SVG.** Platform fonts intentionally fall back to local serif/sans-serif; validate typography again on target operating systems.

2025 is a verified, supported fixed complete-year snapshot, not a claim to be the newest available year forever. Price comparisons are nominal SGD, not forecasts or causal premiums. Primary market values are actual repository aggregates. Archived research fields are explicitly labeled. The financing screen combines an observed price with clearly illustrative user assumptions and verified arithmetic; it is not a recorded household or loan offer. State cards are scenario examples.

Scope: assets and documentation only, on branch `design/sol-editorial-spec`. No production rewrite, deploy, pipeline refresh or commit.
