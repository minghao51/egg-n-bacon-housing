# Screen → data → implementation map

## Reading key

- **E**: existing data or capability, verified in repository.
- **R**: existing implementation needs semantic correction/refactoring.
- **P**: proposed UI/route/contract; not currently working end to end.
- Every entire screen layout is **P**. An E next to a value does not imply that the redesigned feature exists.

No new network API is assumed. Current application data is static gzip/GeoJSON under [app/public/data](../../app/public/data), loaded at build time or by browser islands. `DATA_URLS` ([data-urls.ts](../../app/src/constants/data-urls.ts):7–24) and `BASE_URL` remain authoritative for paths.

## Exact screen mappings

| Screen / component | Existing source and transformation | State / missing work |
|---|---|---|
| 00 palette, typography, states | No data dependency; examples use national 2025 medians | P design tokens/components. S$710,000/1,921/+13.1% refer to the area detail, not price growth |
| 01 editorial title, reading note | Product framing; factual median definition, different source coverage | P editorial copy; E aggregate semantics |
| 01 national bars and counts | `dashboard_overview.json.gz → stats.year_2025_hdb/ec/condo`; `get_stats` and `generate_overview_data` in exporter:524,536 | E values, P bar composition. 628,000 / 1,578,000 / 1,938,952; counts 25,084 / 6,209 / 47,503 |
| 01 78,796 / nominal SGD / 2025 | `stats.year_2025.count`; nominal prices from transaction records | E. Do not call this count all Singapore sales |
| 01 export and coverage note | `metadata.generated_at`, `metadata.date_range`; trends first/last dates | E national export 24 Oct 2026; overview ends Oct, trends ends Sep. P source-aware freshness status |
| 01 Explore HDB action | Current map/leaderboard each offer parts of area exploration | P `/explore?type=hdb&period=2025&minSales=150` |
| 01 research teaser | Existing `/analytics/lease-decay`, Markdown collection | E route, P neutral title; no numerical lease-discount finding asserted |
| 02 filter combinations | `map_metrics.json.gz → year_2025_hdb`, other `whole_*`, `pre_covid_*`, `recent_*` sections; exporter `generate_map_data`:622 | E joint subsets, R adapter. Must not use leaderboard's independent breakdown fallbacks |
| 02 sample toggle / hidden counts | Each area `volume`; filter selected subset at ≥150 | P UI rule; E 31 areas, 25 eligible and 6 hidden for 2025 HDB. Existing 150-sale ranking gate uses a different trailing-12-month denominator |
| 02 chart/list rows | `median_price`, `volume`, planning-area object key; ascending price, alphabetical tie break | E values. P sorting/pagination/joint adapter. See full aggregate extract in data-evidence.json |
| 02 baseline | `dashboard_overview.stats.year_2025_hdb.median_price = 628000` | E. Cannot calculate national median by averaging area medians |
| 02 search/sort controls | Current leaderboard search/sort infrastructure and TanStack patterns | E pattern, P unified state. Search area names only. Proposed options: price, PSF, sample; both directions |
| 02 Map tab | `planning_areas.geojson` + same map-metric section; [PriceMap.tsx](../../app/src/components/dashboard/PriceMap.tsx), leaderboard map | E polygons/map capability, P shared filters/selection; audit join keys, tiles, licensing and units. Actual geometry and split research workspace illustrated in SVGs 09/17 |
| 02 Table tab | Same exact subset, with price, PSF and sample fields | E data, P shared semantic table; not a second independent data loader |
| 02 area links | Uppercase planning-area keys, catalog slug patterns are reusable examples | P `/areas/[slug]`; reversible slug/area mapping required |
| 03 headline / area values | `map_metrics.year_2025_hdb.TAMPINES`: median_price 710000, median_psf 620, volume 1921 | E aggregates; P area route, textual explanation |
| 03 national row | `dashboard_overview.stats.year_2025_hdb`: median_price 628000, median_psf 603, count 25084 | E; 2025 HDB national includes 2 Sungei Kadut sales excluded from the area map; no missing 2025 HDB planning areas |
| 03 difference annotation | `710000 - 628000 = 82000`; `(710000/628000 - 1)*100 = 13.0573…` | P new derived presentation using E inputs. Round to 13.1%. Not YoY, not adjusted premium |
| 03 limitations/source block | Actual absence of flat-type/floor/lease/size dimensions and intervals from these assets | E limitations, P always-visible method block; no individual-flat inference |
| 04 mobile overview | Identical sources/values to 01; mobile direct values sit above bars | P responsive composition, no new dataset |
| 05 mobile explorer | Same selected subset and ordering as 02; first four areas of twelve-row desktop page | P responsive pagination; E Ang Mo Kio 499000/971, Jurong East 524000/482, Marine Parade 539750/162, Yishun 547000/1703 |
| 06 state cards | Loading/error/reload behavior partly in `useGzipJson`; Changi 2025 HDB 360000/8 is E | P scenario UI, draft/apply sheet and focus behavior. “Refresh failed” is illustrative, not a detected outage |
| 06 empty EC scenario | Property/type may have no rows; no specified entity/result is invented | P hypothetical empty-state wording, not a verified missing dataset at a named area |
| 07 four destinations + journeys | Existing routes listed in repository-findings; no actual new routing in this phase | P shell, area route, /explore and /data. Retain legacy links |
| 08 evidence ledger | National metadata, trend dates, 31 area subsets, separately generated analytics JSON metadata | E values/vintages; P unified provenance guide and cross-file metadata. Area/trends files do not embed export timestamp |
| 08 lineage / catalog | Existing pipeline and `/catalog/*` routes | E capability, P cross-link guide. Do not expose local file paths as public download URLs |

## Source to browser lineage

`sources/manual/API → bronze → cleaning + schema/quarantine → gold enriched transactions → platinum unified + monthly metrics → scripts/export_app_data.py → gzip assets → Astro/React`.

The seven-file maintenance exporter is not the Hamilton runtime. Its inputs are the unified and planning-area metrics parquets and planning boundaries. Research/interactive tool assets, enhanced segments, reference geometry and catalog have separate workflows. Preserve that separation and label it in the UI.

The existing [manifest](../../app/public/data/manifest.json) verifies required paths/shape but has no release-wide generation guarantee, complete provenance timestamps or statistical consistency checks.

## Proposed UI data contract (adaptation, not a new production API)

```ts
type Selection = {
  period: "2025" | "through-2021" | "from-2022" | "all";
  property: "hdb" | "ec" | "condo";
  minSales: 150 | 0;
  metric: "median_price" | "median_psf" | "volume";
  direction: "asc" | "desc";
};
type AreaObservation = {
  planningArea: string;         // canonical uppercase source key
  period: Selection["period"];
  property: Selection["property"];
  medianPriceSgd: number | null;
  medianPsfSgd: number | null;
  transactionCount: number;
  evidenceKind: "observed-aggregate";
  sourceAsset: string;
  sourceSection: string;
};
type Provenance = {
  observationStart: string | null;
  observationEnd: string | null;
  exportedAt: string | null;
  sourcePublishedAt: string | null;
  generationId: string | null;
  caveats: string[];
};
```

Map literal period IDs to existing sections: 2025→year_2025, through-2021→pre_covid, from-2022→recent, all→whole; append _hdb/_ec/_condo. “All housing” is not part of the primary single-type explorer; preserve mixed-type historical analysis under Research with composition caveats.

- Missing section/property must produce unavailable data, **not fallback to another period/type**.
- Fields in the selected section are not all temporally aligned: only price/PSF/volume are approved for the primary adapter.
- National baseline must come from the exact matching overview block. If asset compatibility cannot be verified, omit the baseline/difference and show why.
- Nulls, missing rows and zero counts are distinct. Do not treat a sentinel zero for an empty exporter block as a meaningful S$0 market price.
- Provenance fields are nullable on purpose. Do not copy national exportedAt onto area/research sources.
- A later exporter revision should attach generation IDs and supported-period metadata; acceptance tests must prove compatibility before claiming one consistent release.

## Features intentionally not promised

No live listings, property valuation, BTO eligibility, grants, address search, new income-prediction/eligibility model, tax advice, individual mortgage recommendation, adjusted price index, new confidence interval, new forecasting model, or transaction-level export. Existing affordability functionality is retained as explicit scenario arithmetic, not a lender decision. No invented data fields or private rental observations.

Research tools and segment matching remain available, but their modeled yields, fixed assumptions, matching scores and vintage must be audited before styling them as decision evidence. That is migration work, not a feature established by these SVGs.

## Revision 2 expanded screens

| Screen | Source / transformation | Proposed changes / gate |
|---|---|---|
| 09 observed map | Actual 55-feature planning_areas geometry + year_2025_hdb; selected-subset count gate; five declared price bins | Shared state, tile-independent geometry, explicit research handoff |
| 10 / 16 trends | dashboard_trends, HDB Price/HDB Volume, twelve 2025 months; sum count 25,084 | Range/type controls, aligned price line and count bars, null gaps, calendar-lag rules and table |
| 11 discovery | segments_enhanced.segments, six names / stored avgPricePsf / planningAreas; lastUpdated 19 Apr 2026 | Explained weighted fit, persona presets, comparison slots; do not imply current filtered statistics |
| 12 investigate / compare | planningAreas title-case keys; Bishan stored avgPricePsf 644; segment Large Size Stable / High Growth Recent averages 570 / 509 | Explicit separate workflow states; cohort-count overlap caveat; gate unverifiable forecast/yield fields |
| 13 scenario | Actual selected 2025 HDB price 710000 + illustrative income120000/down30%/25yr/3%; standard amortization | New editable assumptions and sensitivity chart. S$2,357 payment; 23.6% income; not affordability/approval advice |
| 14 library / article | Existing Markdown/frontmatter and persona/category fields; lease article dated 4 Feb 2026 | Search filters, source/method disclosure, unit-review gate; no mislabeled PSM→PSF chart |
| 15 catalog | catalog.jsonl.gz unified_dataset row_count1233405 / 97 columns vs current local platinum1234928 | Separate snapshot labels, schema search and lineage links; no raw-record download |
| 17 research map | analytics/* 41 area entries, metadata19Feb2026; predictive train1Jan2025 / target1Jul2025; nine existing LayerIds | Canonical-key adapter, per-layer status, inspectable archive, current analytical fill withheld pending validation |
| 18 model tools | lease bands at75→74–79/19.1/.25/29913; MRT tool inputs and existing problematic distance×coefficient×1000 formula; towns[] spatial asset | Non-overlapping-bin decision, signed interval marks, explicit floor-area proposal, model/contract gates |
| 19 mobile tools | Same observed price and illustrative assumptions as 13; same exact amortization | Proposed responsive full form/result; keep income local; open sensitivity inline |
| 20 mobile segment inspection | Same research segment and Bishan644 / Serangoon566 / Bukit Timah500 stored PSF values as 12 | Research-aware filter sheet, selected-area evidence and comparison-set handoff |

Detailed contracts and responsive behavior: [feature-specifications.md](feature-specifications.md). Rechecked example inputs, arithmetic and source metadata: [expanded-data-evidence.json](expanded-data-evidence.json).

### Design-snapshot reconciliation versus publication compatibility
Sol independently recalculated national and Tampines 2025 HDB price/count pairs from the same local platinum frame; both match the public asset values. Exported PSF values are truncated integers: national raw median 603.870… →603 and Tampines620.843… →620. These figures are approved as an explicitly reconciled **design snapshot**, not proof of a release-wide generation contract.

Production must still require matching generation identity or an independently verified publication manifest that records source snapshot hashes, approved metric scopes and national/area inclusion rules. Otherwise withhold national reference/difference (SVG06) while preserving the area's own values. No amount of matching timestamp text alone proves compatibility.
