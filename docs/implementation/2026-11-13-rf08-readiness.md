# RF08 readiness — what a refreshed edition needs, job by job

- **Date:** 2026-11-13
- **Status:** **Not executed — by design.** RF08 refreshes research one registered job at a time and each refreshed edition needs three recorded sign-offs: source/cutoff by a data steward, **scientific validity by a reviewer who did not author or fit the result**, and publication by the release authority (D12). This session cannot supply the independent reviewer, so no refreshed numbers, charts or approved pointers were produced.
- **What this document is:** the RF08 step-1 deliverable — the reconstruction/proposal boundary for each job, derived from the [research register](../plans/2026-11-12-reporting-refresh-research-register.md). It names what must be established before a job may run, and which approval gate its claims need. It deliberately contains **no refreshed figures**.
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §7 · [handoff](../plans/2026-11-12-reporting-refresh-handoffs.md) RF08
- **Editions side:** [RF07 report](2026-11-13-rf07-editions.md) — the archive and register a new edition must join.

> **Update 2026-11-14:** RS01 (`data-sources`) and RS02 (`rental-yields`) are now signed,
> approved and published — the gate sequence that unblocked them is recorded in
> [the RF08 sign-off record](2026-11-14-rf08-editions-signoff.md). For the remaining 13
> studies, start from the [continuation brief](2026-11-14-rf08-continuation-brief.md): it
> supersedes the "what is ready to receive a job" section below with the mechanics as built.

## 1. Why this is blocked, precisely

| Requirement | Who can supply it | Status |
| --- | --- | --- |
| Frozen inputs + method/code version per job | named researcher/data owner | not assigned |
| Source/cutoff approval | data steward other than the preparer | not recorded |
| Scientific validity (identification, leakage, intervals, units) | reviewer who did not author/fit the result | **not available in this session** |
| Publication approval of the exact artifacts | release authority (not the scientific reviewer) | not recorded |
| New edition registration | RF07 register + this approval chain | register ready; entries intentionally absent |

The register's own rule applies: an old article's coverage label is "a declaration to investigate, not a verified training interval". Nothing in this document asserts a verification that did not happen.

## 2. Per-job gates (from the register)

Each row states the gate a refreshed edition must clear; "gate" is the specialised review named in the register, on top of the three sign-offs.

| Row | Article | Gate before any refreshed claim |
| --- | --- | --- |
| RS01 | `data-sources.md` | measured source-specific coverage/cadence/business keys; unavailable files vs absent assets; macro/rental lags reconciled |
| RS02 | `rental-yields.md` | gross proxy vs matched-unit yield defined; denominators and zero/missing handling validated |
| RS03 | `temporal-evolution.md` | period-correct feature/reference vintages; changing sample composition stated; no causal reading of coefficient drift |
| RS04 | `amenity-impact.md` | amenity snapshot/operating status and distance quality; no historical presence implied; identification for any causal claim |
| RS05 | `facility-premiums.md` | facility ownership/date and join keys recovered; correlated-amenity and project effects addressed |
| RS06 | `lease-decay.md` | **unit/model review**: PSF/PSM and total-vs-per-area response resolved before fitting; interactive-band lineage reconciled |
| RS07 | `mrt-impact.md` | **model review**: metres/km and total-price/log/PSF response confirmed; predictive-vs-causal separated; calculator stays locked |
| RS08 | `school-quality.md` | **causal/RDD review**: tier provenance, bandwidth, treatment assignment, balance, multiplicity |
| RS09 | `macro-sensitivity.md` | **model review**: real release vintages, revisions, stationarity, uncertainty; generated/fallback series excluded or labelled simulation |
| RS10 | `market-segments.md` | **segment/scoring owner approval**: feature scaling, clustering version, cohort counts, old/new segment identity mapping; app weights unchanged |
| RS11 | `spatial-autocorrelation.md` | **spatial method review**: weights/neighbour definition, disconnected areas, permutations, multiplicity |
| RS12 | `spatial-hotspots.md` | **spatial method review**: stated hotspot method rerun; Jan 2024–Jan 2025 kept as its own window; instability disclosed |
| RS13 | `causal-inference-overview.md` | **causal identification approval**: estimand, treatment/control construction, pretrends, concurrent policies, placebos |
| RS14 | `price-forecasts.md` | **forecast/model approval**: frozen training vintages, rolling-origin validation, leakage checks, interval coverage, expired forecasts scored |
| RS15 | `findings.md` | runs **last**; every quantitative sentence links to a reviewed edition, and blocked dependencies are flagged, not summarized |

## 3. Personas and archived assets

| Row | Asset / surface | Disposition |
| --- | --- | --- |
| RA01 | `persona-content.json`, three persona routes | RF02 safety copy keeps unsupported promises out; recommendations may cite only approved editions. The RF07 status panel is the current propagation point; per-card status is the follow-up once an approved edition exists. |
| RA02–RA05 | `predictive_analytics`, `feature_impact`, `spatial_analysis`, `segments_enhanced` | Archived as-is; replacement needs the corresponding RS job plus its own version/validation manifest. No global "current" flag. |
| RA06–RA08 | lease-decay / MRT-CBD / spatial-hotspots tool assets | RF06 preserved the tool contracts (dated bands, inspection-only coefficients, label inspection). Any change is proposed by RS06/RS07/RS11/R12 and independently approved; a new study does not unlock a tool. |

## 4. What is ready to receive a job

- **Edition register** (`src/components/studies/lib/edition-registry.ts`): adding an approved edition is a one-entry change — series, edition id, publication year, `evidenceStatus: "approved"`, frozen path, asset count. Validation rejects duplicates and reserved names; `approvedEditionFor()` then promotes it, and the series page stops saying "No approved current edition".
- **Archive route** renders any registered edition under `/analytics/archive/<year>/<edition>/<slug>`, with the gate carry-over (withheld charts stay withheld).
- **Provenance fields already in the contract**: per-job `publishedAt` vs observation scope, evidence status vs editorial status, frozen source path and pinned-asset count.
- **Approval record — now built (2026-11-14).** `AnalyticsEdition` carries `preparedBy` and `signoffs[]` (role, name, date, `artifactSha256`, statement, `automated`, evidence path). `validateEditionRegistry()` refuses `approved` unless all three D12 roles exist, are distinct, are not the preparer, and pin **one** artifact hash; the archive route renders the recorded attestations instead of a constant "independently reviewed" string. The repo owner accepted a recorded automated review as the scientific signatory, provided the run is recorded and the evidence path committed.
- **Still missing**: the attestations themselves. Two packs are prepared ([RS01](2026-11-14-rs01-source-inventory.md), [RS02](2026-11-14-rs02-rental-yield-evidence.md)); until all three signatures are entered, every series correctly reports "No approved current edition".

## 5. Suggested first job

RS01 (`data-sources.md`) is the only register row whose gate is a data-inventory exercise rather than a model/causal review, which makes it the cheapest way to validate the approval flow end-to-end before a modelling job runs. It still needs the independent reviewer for its own text claims, so even RS01 was not executed here.

**Correction (2026-11-14, independent review).** An earlier version of this section said RF03 "already produced the source evidence it needs". That was overstated. RF03 recorded an acquisition/pipeline/export run and a reconciliation of published scopes; it did **not** produce RS01's required per-source inventory (source identity, cadence, business keys, acquisition/fallback status, macro/rental lags) measured against this article's current claims. The v2 observed pack publishes dashboard aggregates, not those inventory measurements, so nothing may be inferred from it. RS01's first deliverable is therefore a measured inventory evidence pack that marks unmeasured and unavailable items explicitly — not a rewritten article.

## 6. Independent review record (2026-11-14)

Two independent reviews were run (requested `gpt-6.1-sol` at high reasoning; both runs resolved to `openai-codex/gpt-6-luna` at high reasoning because the model id was ambiguous across providers — recorded honestly, and neither reviewer authored or fitted any result). Both reached the same verdict on this readiness contract, the register, D10/D12, the edition registry, RF03's evidence and the current `data-sources.md`:

| Question | Reviewer's answer |
| --- | --- |
| Can any refreshed study be signed off today? | **No.** No measured source/cutoff inventory exists for RS01, and no D12 approval record exists for any row. |
| Is any gate purely an inventory check already satisfied? | **No.** RS01 is the only inventory-only gate and RF03's evidence does not cover the current article's claims. |
| Can the approval *mechanism* be demonstrated without a false claim? | Only by assembling the RS01 evidence pack first; flipping `evidenceStatus` to `approved` without attestations would make the series assert an approval that was never recorded. |
| Does the tree currently claim a refreshed edition exists? | No registry entry is `approved`; all 15 are `historical`. Risk noted: `app/src/pages/analytics/archive/[year]/[edition]/[slug].astro` renders an "independently reviewed" panel from registry status alone, so the registry must not be flipped before the attestations exist. The second review adds that RS01's claims (`docs/analytics/data-sources.md:25-130`) and the modelling articles (`mrt-impact.md`, `price-forecasts.md` point at retired scripts and precomputed assets) can only be checked against source-level evidence, not against the published packs. |

This is a **review record, not a sign-off**. It satisfies the "independent reviewer participated" precondition for whoever assembles RS01's evidence, and it explicitly attests nothing about refreshed numbers. The three D12 approvals remain outstanding, and D10 still requires separate permission for any research rerun.

**Smallest next action:** assemble the RS01 measured inventory pack (source identity, cadence, business keys, acquisition/fallback, macro/rental lags, unavailable items marked as such) from frozen sources and RF03 evidence; then obtain the three sign-offs on that exact artifact. Do not flip the registry first.
