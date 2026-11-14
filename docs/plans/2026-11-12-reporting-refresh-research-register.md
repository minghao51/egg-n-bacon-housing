# Reporting refresh — research and asset work register

- **Date:** 2026-11-12
- **Status:** Draft — planning only; no report rerun, data refresh or model approval.
- **Parent:** [Implementation map](2026-11-12-reporting-refresh-implementation-map.md)
- **Execution packet:** [RF08 in the handoffs](2026-11-12-reporting-refresh-handoffs.md#rf08--refresh-research-one-registered-job-at-a-time)
- **Evidence:** [Reporting audit](../implementation/2026-reporting-refresh-audit.md)

## Operating contract

This is the work list for **all 15 study series**, three persona pages and the non-dashboard asset families. Every entry starts **Not started**. A listed generator is not presumed to exist: most historical Python analytics scripts have been retired.

For each job, first identify its real inputs, business grain, code/method version, units, dependencies, observation cutoff and figure lineage. If these cannot be established, finish an explicit **blocked/reconstruction proposal**, not a new analysis or a revised freshness claim. An old article's “2017–2026” label is a declaration to investigate, not a verified training interval.

### Required result per study

1. Historical source/figure/data references preserved with hashes before edits.
2. Reproducible acquisition/analysis instructions and input identities; secrets excluded.
3. Observation and source-publication cutoffs, extraction time and publication edition kept separate; unknowns remain null with a reason.
4. Metric dictionary: grain, population, denominator, units, time window, excluded/missing data, uncertainty and limitations.
5. Tables, chart source data and rendered figures agree. Static PNGs get an edition-specific path and provenance, not merely a new filename date.
6. Scientific/method sign-off by a reviewer who did not author/fit the result; separate source/cutoff approval by a data steward other than the evidence preparer, and publication approval by the release authority. The data steward may also be release authority if documented; the scientific reviewer cannot be publication approver for that edition. Frontend/schema acceptance substitutes for none of these.
7. New edition and changelog describing source revisions, population/method changes and non-comparable results.
8. Archive-only or under-review status until acceptance; series “latest approved” pointer changes only in a release gate.

New reusable production metrics must use the supported Hamilton DAG and materialization contracts. Do not revive the retired standalone analytics package or introduce a parallel production runner. A research notebook may be an auditable research artifact, but is not automatically an approved production dependency. Each reconstruction proposal must state how accepted outputs will be reproducibly generated and maintained.

## Study jobs

`RF03` means source reconciliation, `RF07` means edition/archive infrastructure. All jobs depend on both before publication. Additional scientific approval is called out below. Job identifiers are stable even if a study is blocked or retired.

| ID | Series / canonical source | Required inputs and additional dependency | Work and acceptance beyond the shared contract |
| --- | --- | --- | --- |
| RS01 | Data Sources — `docs/analytics/data-sources.md` | RF03 source inventory; reference/crosswalk vintages | Replace inferred ranges with measured source-specific coverage, cadence, business keys and acquisition/fallback status. Distinguish unavailable files from absent published assets. Reconcile macro/rental lags; no secret values. |
| RS02 | Rental Yields — `docs/analytics/rental-yields.md` | Aligned rentals and sales, property types, geography and date windows | Define gross proxy versus matched-unit yield; quantify unmatched populations. Explicitly exclude vacancy, tax, fees, maintenance and financing from gross figures. No “yield above mortgage rate means viable” or downside-floor conclusion. Validate denominators and zero/missing handling. |
| RS03 | Temporal Evolution — `docs/analytics/temporal-evolution.md` | Comparable historical transactions and period-correct feature/reference vintages | State changing sample composition and feature definitions. Recompute like-window estimates with uncertainty; do not interpret changing coefficients as causal market shifts. A descriptive baseline may ship separately from model-derived premiums. |
| RS04 | Amenity Impact — `docs/analytics/amenity-impact.md` | Transactions, amenity snapshot/operating status, coordinate and distance quality | Refit documented associations with units and controls. Contemporary amenity presence must not imply historical presence; disclose snapshot join limitations. No causal premiums without identification. |
| RS05 | Facility Premiums — `docs/analytics/facility-premiums.md` | Matched project facilities and transaction population | Recover facility ownership/date and join keys; assess missing facilities, correlated amenities and project effects. Publish uncertainty and sample sizes; no isolated causal-premium claim from unadjusted comparisons. |
| RS06 | Lease Decay — `docs/analytics/lease-decay.md` | Lease dates, transaction price, sqm/sqft, sample construction; **model/unit approval** | Resolve PSF/PSM and total-price versus per-area response before fitting. Validate lease age as of transaction date. Reconcile article versus interactive-band lineage. Keep chart/model gates until repaired coefficients and wording are reviewed. Never convert a coefficient without confirming its original response/unit. |
| RS07 | MRT Impact — `docs/analytics/mrt-impact.md` | Station opening/status vintages, distances, CBD definition, transactions; **model approval** | Confirm metres/km and total-price/log/PSF response. Compare standardized effects or state non-comparability; no raw coefficient “15×” or “4×” marketing. Separate predictive association from causation. Do not automatically unlock the MRT calculator. |
| RS08 | School Quality — `docs/analytics/school-quality.md` | Dated schools/tiers/admission geography, distances and transactions; **causal/RDD review** | Recheck tier provenance, bandwidth, treatment assignment, covariate balance and multiple-testing policy. School-quality model fit does not establish a causal admissions premium. Keep policy eligibility outside model outputs. |
| RS09 | Macro Sensitivity — `docs/analytics/macro-sensitivity.md` | Real macro release vintages and housing series at aligned frequencies; **model review** | Explicitly identify generated/fallback series and exclude them from empirical claims unless the entire result is a labelled simulation. Document release lag, revisions, missing periods, stationarity and uncertainty. No present-day timing regime claims from unknown source vintages. |
| RS10 | Market Segments — `docs/analytics/market-segments.md` | Stable features/sample, preprocessing and stored segment membership; **segment/scoring owner approval** | Recover feature scaling, clustering/model version and cohort counts; assess stability and map old/new segment identities. Do not reuse a segment ID for a different population. App matching weights remain unchanged unless separately approved. |
| RS11 | Neighborhood Clusters — `docs/analytics/spatial-autocorrelation.md` | Geography version, time/property-specific observations and spatial weights; **spatial method review** | Record weights/neighbour definition, disconnected areas, permutation settings, sample adequacy and multiplicity correction. High-high labels are not future return or demand predictions. Produce reproducible memberships and uncertainty/significance metadata. |
| RS12 | Rental Hotspots — `docs/analytics/spatial-hotspots.md` | Current rental population aligned to geography/property/time; **spatial method review** | Retain January 2024–January 2025 as its own historical window. Rerun the stated hotspot method, disclose persistence/instability and sample changes. Keep rental hotspot results separate from the transaction-activity product. |
| RS13 | Policy Impact — `docs/analytics/causal-inference-overview.md` | Treatment dates, pre/post coverage, explicit controls and outcomes; **causal identification approval** | Recover estimand, treatment/control construction and assumptions. Check pretrends, confounding concurrent policies, anticipation and robustness/placebos. A new observation year does not by itself validate an old causal estimate. |
| RS14 | Price Forecasts — `docs/analytics/price-forecasts.md` | Frozen training/feature vintages, held-out realized outcomes, forecast issue/target dates; **forecast/model approval** | Reconcile article and predictive asset lineage first. Use rolling-origin validation, leakage checks, naïve trend/seasonal baselines, error metrics and empirical prediction-interval coverage. Name R² correctly. Score expired 2025 forecasts where comparable outcomes exist. Never advance a stored forecast date or reuse BUY/SELL prompts as current advice. |
| RS15 | Key Investment Findings — `docs/analytics/findings.md` | RS01 plus every study whose claim is cited | Refresh last. Every quantitative sentence links to a reviewed edition and exact population/window/unit. Omit or explicitly flag blocked dependencies; never summarize unresolved models as settled conclusions. Keep editorial date distinct from observation cutoff. |

### Suggested research waves

1. **Inventory and descriptive evidence:** RS01, then RS02 and descriptive portions of RS03.
2. **Feature studies:** RS04/RS05; RS06/RS07 only after unit/model approvals; RS08 with its own causal review.
3. **Macro, segments and spatial:** RS09–RS12 once inputs/methods are recovered and approved.
4. **Causal/forecast validation:** RS13/RS14; may remain archived without blocking the observed dashboard.
5. **Synthesis:** RS15 after its actual dependencies are approved. The whole register need not be completed to publish an honest, narrower summary.

These waves describe dependency/risk order, not authorization to run every model or a commitment that every retired analysis will be rebuilt. Run disjoint study investigations concurrently only when input/output ownership is explicit.

## Non-study jobs and asset ownership

| ID | Family / current entry point | Owning slice | Required disposition |
| --- | --- | --- | --- |
| RA01 | `app/src/data/persona-content.json`; three persona routes | RF02 safety, RF07 metadata propagation, RF08 refreshed recommendations | First remove unsupported investment promises; then use approved-edition evidence/status in recommendations. Archived studies can remain discoverable as historical research, not current opportunity signals. |
| RA02 | `app/public/data/analytics/predictive_analytics.json.gz` | RF07 archive, RS14 for replacement | Preserve original issue/training/target dates and expired status. New model output gets its own version and validation manifest. Article/model equivalence must be demonstrated. |
| RA03 | `app/public/data/analytics/feature_impact.json.gz` | RF07 archive; relevant feature-study jobs for replacement | Recover per-layer method, units and source vintage. Uniform or unresolved fields remain inspection-only. A new feature study does not unlock every archived layer. |
| RA04 | `app/public/data/analytics/spatial_analysis.json.gz` | RF07 archive; RS11/RS12 for replacement | Resolve each field's meaning and layer lineage separately; no global “current” flag for the whole file. |
| RA05 | `app/public/data/segments_enhanced.json.gz` | RF07 archive; RS10 for replacement | Separate stored research membership from the observed dashboard's `dashboard_segments`. Preserve IDs/links or supply reviewed migration mappings. |
| RA06 | `app/public/data/interactive_tools/lease_decay_analysis.json.gz` | RF06 preserves tool contract; RS06 proposes changes | Dated stored-band lookup remains dated; no undefined compounding, hidden floor-area scaling or fitted-decay claim. |
| RA07 | `app/public/data/interactive_tools/mrt_cbd_impact.json.gz` | RF06 preserves tool contract; RS07 proposes changes | Continue coefficient inspection/withheld total until model units/combination semantics are independently approved. |
| RA08 | `app/public/data/interactive_tools/spatial_hotspots.json.gz` | RF06 preserves tool contract; relevant spatial jobs propose changes | Preserve label inspection only; reconcile conflicting risk prose before any allocation/recommendation view. |
| RA09 | `app/public/data/interactive_tools/affordability_metrics.json.gz` | RF11 disposition, RF12 publication integration | Verify it remains unused. Deprecate/remove only with data-boundary approval and manifest/consumer migration; otherwise label its separate provenance. It is not a verified eligibility calculator. |
| RA10 | `app/public/data/analysis/**/*.png` | RF00 hash/preserve; RF07 edition paths; individual research jobs | Freeze existing bytes/paths used by historical reports. New figures use new edition-specific paths and data/method manifests; never overwrite old figures with a fresh date. |
| RA11 | `app/public/data/catalog.jsonl.gz`; catalog audit constants | RF11 | Recompute catalog plus inspected observation together; preserve previous snapshot evidence and distinguish catalog-generation presence from current local presence. |
| RA12 | `app/public/data/planning_areas.geojson` and `.gz`; reference/crosswalk inputs | RF03 inventory, RF11 reconciliation | Record geography version, provenance, canonical IDs and exclusions. No unreviewed boundary change disguised as a transaction refresh. |
| RA13 | Seven dashboard payloads and `dashboard-release.json` | RF04 observed contract, RF09 activity extension, RF12 promotion | Maintain v1 compatibility and archive its baseline; current observation data belongs to the exporter release, not to a research model edition. |

## Per-job handoff/result form

Use this form for any RS/RA job; attach the RF08 common handoff and its exact register row.

```text
Job ID / owner / status:
Parent slice and required approvals:
Claim to refresh (not merely the requested calendar year):
Historical edition, source paths and original hashes:
Actual inputs, business grain, observation/source-publication cutoffs:
Known absent inputs / credentials required (names only):
Generator recovered or reconstruction proposal:
Target/response, units, methods, assumptions and review questions:
Approved production/research persistence path:
New edition paths, source/figure hashes and code/method version:
Tests and scientific validation, exact commands/results:
Changes versus historical edition and comparability limits:
Source-policy disposition / data-steward sign-off:
Independent scientific reviewer / evidence / sign-off:
Publication decision / release approver / unresolved blockers:
Next owner and smallest safe next step:
```

A completed frontend wrapper, a new extraction timestamp or a passing schema check is **not** evidence that a research result has been scientifically refreshed.
