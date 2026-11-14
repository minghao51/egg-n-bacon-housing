---
title: Data Sources
category: "quick-reference"
description: A measured inventory of every acquisition file behind the platform — counts, coverage, grain, acquisition record and the claims the data cannot support
status: published
date: 2026-11-14
personas:
  - first-time-buyer
  - investor
  - upgrader
readingTime: "8 min read"
technicalLevel: intermediate
---

# Data Sources

**Edition:** `data-sources-2026-11-14` · **Measured:** 2026-11-14 · **Observation cutoff:** 2026-10 (last complete month)

This edition replaces the inventory published 2026-06-15. That text described the sources from project knowledge: record counts were rounded, several coverage ranges were inferred rather than read, and no acquisition record was cited. Every number below was measured from the files in this checkout by [`scripts/tools/source_inventory.py`](../../../../implementation/2026-11-14-rs01-source-inventory.md), whose canonical ledger is [`artifacts/rs01-source-inventory.json`](../../../../implementation/artifacts/rs01-source-inventory.json) — sha256 `65ce7a10c257d13fd4250b2e8fd1519f8c35718497379aa103effc5594bfe8ae`. Re-running `uv run python scripts/tools/source_inventory.py --check` re-hashes every recorded file and fails if this checkout no longer matches that ledger.

An edition date and an observation cutoff are different things: this page was written on 2026-11-14, and the transaction data it describes stops at the 2026-10 cutoff. Exports use `--last-complete-month 2026-10`, because the newest month present in some sources is a partial month.

## What the platform is built from

| Layer | Files | Recorded acquisition | Not recorded |
| --- | ---: | ---: | ---: |
| Bronze (`data/pipeline/01_bronze/`) | 14 | 14 | 0 |
| External sidecar (`…/external/`) | 28 | 16 | 12 |
| Manual (`data/manual/`) | 47 | 0 | 47 |
| **Total** | **89** | **30** | **59** |

"Not recorded" means no `bronze_manifest` entry matches the file by name or bare stem. It does **not** mean the file is unused — it means this ledger cannot say how or when the file arrived. The 30 recorded entries resolve to 17 `datagov_api`, 9 `r2_external`, 1 `ura_api+manual_csv`, 1 `datagov_api+manual_csv`, 1 `onemap_geocode` and 1 `lta_api`, all fetched 2026-11-13.

## Transaction and rental sources

These are the load-bearing files: everything else is enrichment.

| Source | Rows | Coverage (measured) | Acquisition |
| --- | ---: | --- | --- |
| `raw_hdb_resale.parquet` | 990,860 | 1990-01 → 2026-11 | `datagov_api+manual_csv`, recorded, row count matches |
| `raw_hdb_rental.parquet` | 215,469 | 2021-01 → 2026-10 | `datagov_api`, recorded, row count matches |
| `raw_condo_transactions.parquet` | 245,655 | 2021-01-01 → 2026-11-01 | `ura_api+manual_csv`, recorded, row count matches |
| `raw_rental_index.parquet` | 525 | 2004-01-01 → 2026-07-01 | `datagov_api`, recorded, row count matches |

Three consequences follow directly from those ranges, and each of them changes what a study may claim:

1. **HDB resale is genuinely 36 years deep.** 1990-01 → 2026-11, 990,860 rows, so the long-run statements about resale prices rest on a populated history. The terminal month is partial at this cutoff, which is why published windows stop at 2026-10.
2. **Private transactions start in 2021.** URA coverage is 2021-01-01 → 2026-11-01. Any analysis that treats private (condo and EC) data as history-length is wrong, and the EC/condo 2026 volume question is open.
3. **Rentals start in 2021 and end one month before sales.** 2021-01 → 2026-10 against sales to 2026-11: a rental-yield join can only exist from 2021-01 and must drop the unpaired terminal month. The [Rental Yields edition](../../rental-yields/2026-11-14/rental-yields.md) lives inside that constraint.

## Macro and reference series

| Series | Rows | Last observation | Cadence |
| --- | ---: | --- | --- |
| `cpi.parquet` | 789 | 2026-09-01 | monthly, from 1961-01 |
| `bank_rates.parquet` (3-month compounded SORA) | 465 | 2026-09-01 | monthly, from 1988-01-01 |
| `gdp.parquet` | 202 | 2026-06-30 | quarterly, from 1976-Q1 |
| `unemployment.parquet` | 139 | 2026-09-30 | quarterly, from 1992-Q1 |
| `ura_ppi.parquet` | 207 | 2026-09-30 | quarterly, from 1975-Q1 |
| `hdb_rpi.parquet` | 147 | 2026-09-30 | quarterly, from 1990-Q1 |
| `sora_rates.parquet` | 60 | 2025-12-31 | monthly, from 2021-01-31 — **stale** |
| `wage_growth.parquet` | 100 | 2025-12-31 | quarterly, from 2001-Q1 |

**The macro family is not synchronous with the housing cutoff, and this matters.** At a 2026-10 transaction cutoff, CPI and bank rates run to 2026-09, GDP stops at 2026-Q2, unemployment/URA PPI/HDB RPI stop at 2026-Q3, wage growth stops at 2025-Q4, and `sora_rates` stops at 2025-12 with no manifest entry at all. Any sentence pairing a monthly housing observation with a macro series must carry that series' own last date. `sora_rates` must be labelled stale rather than current; it is present on disk, and presence is not recency.

The previous edition listed "SORA 2007 – Apr 2026" and "Housing Supply Pipeline 2014 – 2026-Q1". Neither range survives measurement: `sora_rates.parquet` ends 2025-12, and no housing-supply-pipeline file exists in this inventory.

## Amenity layers

Feature counts measured per file. These are **counts of mapped locations**, not distances.

| Layer | Features | Recorded acquisition |
| --- | ---: | --- |
| Bus stops | 5,205 | `r2_external` |
| Childcare services | 1,925 | `r2_external` |
| Pre-schools | 2,290 | `r2_external` |
| Supermarkets | 526 | `r2_external` |
| Hawker centres | 129 | `r2_external` |
| Parks and nature reserves | 450 | `r2_external` |
| Community clubs | 128 | `r2_external` |
| CHAS clinics | 1,193 | `r2_external` |
| SportSG facilities | 45 | `r2_external` |
| Park connectors | 1,277 | not recorded |
| MRT stations (LTA, `raw_mrt_stations`) | 188 | `lta_api` |
| MRT station exits | 597 | not recorded |
| MOE schools | 337 | `datagov_api` |
| Green Mark buildings | 4,145 | `datagov_api`, geocoded via `onemap_geocode` |
| MP25 malls | 294 | `datagov_api` |

**Distance figures are not in this edition.** The previous text published a "median distance" column (childcare 126 m, supermarket 290 m, MRT 513 m, and so on). No artifact in this tree measures a national median distance from a transaction to an amenity; the derived per-area files carry per-planning-area medians, which are a different statistic. Those sentences are dropped rather than carried forward unmeasured — a median distance needs the distance computation and its population stated, and neither exists here.

Two GeoJSON layers are mid-migration: `ChildCareServices.geojson`, `SupermarketsGEOJSON.geojson` and their siblings sit beside the `.parquet` copies that actually load, and the two forms are counted separately above.

## Availability: what is present, and what "present" does not mean

| Finding | Detail |
| --- | --- |
| Acquisition recorded | 30 files, all fetched 2026-11-13 |
| Acquisition **not** recorded | 59 files (0 bronze, 12 external, 47 manual) — present on disk, provenance unrecorded |
| Manifest row-count mismatch | 1: `raw_green_mark_buildings_geocoded.parquet` is recorded as 4,015 rows and measures 4,145 |
| Format mismatch | 1: `data/manual/csv/datagov/Kindergartens.geojson` contains **CSV**, not GeoJSON (920,177 bytes, 10,000 rows measured) |

The format mismatch is recorded and not repaired: an ingestion path that trusts the extension will mis-read that file, so it must sniff the content. The row-count mismatch is recorded and not reconciled: the manifest is stale, not the data.

This is an inventory of **files present**, and that is a weaker claim than completeness. No expected-asset list is checked, so nothing here supports "nothing is missing". An acquisition file that cannot be read and a released app asset that is absent are different states, and this ledger measures only the first: it inventories the acquisition tree, so it cannot report an absent published asset. That check belongs to the release verification, not to this page.

## Grain and business keys

| Family | Grain | Consequence |
| --- | --- | --- |
| HDB resale | one row per registered resale application | `month + town + block + flat_type` is **not** unique — there is no unit identifier |
| HDB rental | one row per approved rental application, `rent_approval_date` as `YYYY-MM` | joins to resale only at town/flat-type/month level |
| URA private | one row per transaction record, daily `sale_date` | mix of land/strata and sale types is in-file, not normalised here |
| Amenity layers | one feature per facility | coordinates only; no opening/closing dates, so amenity presence is a snapshot |
| Macro | one row per period | release lag differs per series (see above) |

**No source carries a unit-level key.** Block + flat type + month is the finest joint grain anywhere in this tree. That single fact bounds several studies: a matched-unit rental yield cannot be computed, and a per-unit facility effect cannot be identified.

## What this edition does not establish

- It measures inputs, not article sentences. A study citing these sources is only supported where its own edition states its population and window.
- It does not certify completeness of any month. Coverage bounds say "the file contains this range", not "the source published every record in it".
- It does not resolve the EC/condo 2026 volume discontinuity; it records the coverage that question lives in.
- It does not authorize a rerun or a refit. Reading local files is not a research rerun.

## Superseded figures

Recorded so a reader of the 2026-06-15 text can see exactly what changed and why:

| Claim in the previous edition | Measured |
| --- | --- |
| HDB resale "~970,000" | 990,860 |
| HDB rental "200,000+" | 215,469 |
| Private transactions "~40,000" | 245,655 (and starting 2021, not historical) |
| URA rental index "515 quarters" | 525 rows, 2004-01 → 2026-07 |
| HDB property info "13,289 blocks" | 13,392 |
| Green Mark buildings "3,900+" | 4,145 (4,145 geocoded; manifest still says 4,015) |
| Shopping malls "112" | 294 in `raw_mp25_malls` |
| CPI "1961 – Apr 2026" | 1961-01 → 2026-09 |
| GDP "1976 – 2026-Q1" | 1976-Q1 → 2026-Q2 |
| "SORA 3M 2007 – Apr 2026" | 1988-01 → 2026-09 (`bank_rates`); the separate `sora_rates` file ends 2025-12 |
| "over 1 million transactions" (across "120+ feature columns", "12 amenity proximity types" and "8 macro economic indicators") | 1,236,310 rows in `unified_dataset`, 1990-01 → 2026-11. This ledger records row counts, not column, amenity-type or macro-indicator roll-ups, so those three counts are withdrawn rather than restated |
| Median-distance column | not measured in this tree; withdrawn |

## Evidence and sign-off

Whether this edition is current is decided by its entry in the edition registry (`app/src/components/studies/lib/edition-registry.ts`), which is the only place an edition sign-off may be recorded. `approvedEditionFor()` offers this edition as its series' current edition **only** when that entry is `approved` and carries three distinct attestations — source/cutoff, scientific and publication — that exclude the preparer, cover one evidence hash, and pin this file's own sha256 (`editionSha256`), which the archive route re-verifies against the frozen bytes at build time. Until that holds, the series page and every archive route render this edition as not approved. The D12 policy and the source/cutoff record for the evidence behind this edition are in the [decision ledger](../../../../plans/2026-11-12-reporting-refresh-decisions.md); the scientific and publication attestations belong to the registry entry, not to that ledger. The evidence they would cover is the [RS01 pack](../../../../implementation/2026-11-14-rs01-source-inventory.md).
