# RS01 evidence pack — measured source inventory

- **Date:** 2026-11-14
- **Status:** **Prepared for review, not signed off.** This is the evidence artifact RS01's gate asks for: a _measured_ inventory of every acquisition file, its grain, coverage, counts and acquisition record — plus the claims it cannot support. The three D12 sign-offs (§7) are **not** recorded yet; the edition stays historical until they are.
- **Register row:** RS01 — `docs/analytics/data-sources.md`. Gate: "measured source-specific coverage/cadence/business keys; unavailable files vs absent assets; macro/rental lags reconciled."
- **Prepared by:** `repo-agent/session-2026-11-14` (automated preparation, recorded so it can be excluded from sign-off).
- **Machine-readable ledger:** [`artifacts/rs01-source-inventory.json`](artifacts/rs01-source-inventory.json) — sha256 `65ce7a10c257d13fd4250b2e8fd1519f8c35718497379aa103effc5594bfe8ae`. Sign-offs attach to this hash; `--check` fails if the tree no longer matches it.
- **Producer:** `scripts/tools/source_inventory.py` (`--check` re-measures and fails on drift).

## 1. What was measured, and how

| Step            | Method                                                                                                                                                                                                                                                                                                                                                                                                            |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Inventory       | Every file under `data/pipeline/01_bronze/` (excluding `external/`), `…/external/` and `data/manual/` is measured once: kind, detected format, bytes, sha256, row/feature count, columns, and coverage bounds from the temporal column that file actually carries.                                                                                                                                                |
| Acquisition     | Each bronze/external file is joined to `bronze_manifest.json` by **file name or bare stem**, because the manifest uses both forms (external layers are keyed `BusStops.parquet`, pipeline sources `raw_hdb_resale`). The matched key is recorded per file. `not-recorded` means neither form matches — not that the file is unused. `rowsMatch` compares the manifest's recorded row count with the measured one. |
| Derived counts  | `unified_dataset`, `rental_yield`, `planning_area_360`, `town_360`, `block_profile` and `_quarantine` are measured from the platinum/gold outputs.                                                                                                                                                                                                                                                                |
| Reproducibility | The ledger is canonical JSON (sorted keys, no timestamps) and `--check` re-hashes every recorded file, so a drifted checkout fails loudly instead of silently re-labelling an old approval.                                                                                                                                                                                                                       |

**Numbers measured from this checkout:** 89 acquisition files — **14 bronze**, **28 external**, **47 manual**; **30 carry a `bronze_manifest` entry** (17 `datagov_api`, 9 `r2_external`, 1 `ura_api+manual_csv`, 1 `onemap_geocode`, 1 `datagov_api+manual_csv`, 1 `lta_api`) and **59 do not** (0 bronze, 12 external — 10 GeoJSON, 1 MRT JSON, 1 SORA parquet — and 47 manual). One manifest row count is stale: `raw_green_mark_buildings_geocoded.parquet` is recorded as 4,015 rows and measures 4,145. Derived: `unified_dataset` 1,236,310 rows (1990-01 → 2026-11), `rental_yield` 1,749 rows (after the RS02 regeneration), `planning_area_360` 44, `town_360` 28, `block_profile` 10,031.

## 2. Transaction and rental sources (the load-bearing ones)

| Source                             |    Rows | Coverage                | Acquisition                          |
| ---------------------------------- | ------: | ----------------------- | ------------------------------------ |
| `raw_hdb_resale.parquet`           | 990,860 | 1990-01 → 2026-11       | `datagov_api+manual_csv`, rows match |
| `raw_hdb_rental.parquet`           | 215,469 | 2021-01 → 2026-10       | `datagov_api`, rows match            |
| `raw_condo_transactions.parquet`   | 245,655 | 2021-01-01 → 2026-11-01 | `ura_api+manual_csv`, rows match     |
| `raw_rental_index.parquet`         |     525 | 2004-01 → 2026-07       | `datagov_api`, rows match            |
| `raw_hdb_property_info.parquet`    |  13,392 | —                       | `datagov_api`, rows match            |
| `raw_school_directory.parquet`     |     337 | —                       | `datagov_api`, rows match            |
| `raw_green_mark_buildings.parquet` |   4,145 | —                       | `datagov_api`, rows match            |

Three findings follow directly, and none of them is a guess:

1. **The article's "36 years of HDB resale" is supported** (1990-01 → 2026-11, 990,860 rows) — but the newest month is a _partial_ month at the declared cutoff, which is why exports use `--last-complete-month 2026-10`.
2. **Private coverage starts 2021-01** (condo 245,655 rows, 2021-01-01 → 2026-11-01). Any study that treats private data as history-length is wrong; EC/condo 2026 also remains the unresolved RF03 volume question.
3. **Rental data starts 2021-01 and ends 2026-10**, while sales run to 2026-11. RS02's yield join can only exist from 2021-01 and must drop the unpaired terminal month — see the [RS02 pack](2026-11-14-rs02-rental-yield-evidence.md).

## 3. Macro and reference sources

| Source                 | Rows | Coverage                | Notes                                            |
| ---------------------- | ---: | ----------------------- | ------------------------------------------------ |
| `cpi.parquet`          |  789 | 1961-01 → 2026-09       | monthly; one-month lag behind the 2026-10 cutoff |
| `gdp.parquet`          |  202 | 1976-Q1 → 2026-Q2       | quarterly                                        |
| `unemployment.parquet` |  139 | 1992-Q1 → 2026-Q3       | quarterly                                        |
| `ura_ppi.parquet`      |  207 | 1975-Q1 → 2026-Q3       | quarterly                                        |
| `hdb_rpi.parquet`      |  147 | 1990-Q1 → 2026-Q3       | quarterly                                        |
| `bank_rates.parquet`   |  465 | 1988-01-01 → 2026-09-01 | monthly                                          |
| `sora_rates.parquet`   |   60 | 2021-01-31 → 2025-12-31 | **stale**: ends 2025-12, no manifest entry       |
| `wage_growth.parquet`  |  100 | 2001-Q1 → 2025-12-31    | annual, ends 2025                                |

**Lag reconciliation (the gate's second clause):** at the 2026-10 cutoff the macro family is _not_ synchronous — CPI and bank rates are monthly to 2026-09, GDP/unemployment/URA PPI/HDB RPI are quarterly to 2026-Q2/Q3, wage growth is annual to 2025, and `sora_rates` stops at 2025-12. Any claim that pairs a monthly observation with a macro series must carry the macro series' own last date, and `sora_rates` must be labelled stale rather than current.

## 4. Availability status (the gate's third clause)

| Status                                  | Count | Meaning                                                                                                                                                                                                                                    |
| --------------------------------------- | ----: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Acquisition files with a manifest entry |    30 | acquisition recorded, fetched 2026-11-13 (17 `datagov_api`, 9 `r2_external`, 1 URA, 1 OneMap, 1 datagov+manual, 1 LTA)                                                                                                                     |
| With no manifest entry                  |    59 | present on disk, acquisition **not recorded** — 0 bronze, **12 external** (10 facility `.geojson` layers, `mrt_stations.json`, `sora_rates.parquet`), 47 manual files. The inventory is evidence of contents, not of how/when they arrived |
| Manifest row-count mismatch             | **1** | `raw_green_mark_buildings_geocoded.parquet`: manifest 4,015 vs measured 4,145                                                                                                                                                              |
| Format mismatch                         | **1** | `data/manual/csv/datagov/Kindergartens.geojson` contains **CSV**, not GeoJSON (920,177 bytes). Recorded, not repaired: the ingestion path must not assume the extension.                                                                   |

Two caveats a reader must not round off. First, **this is an inventory of files present**, not a completeness certificate: no expected-asset list is checked, so it cannot support "nothing is missing". Second, `sora_rates.parquet` is present but stale (ends 2025-12) and the `Kindergartens` file is present but mis-extended — both are recorded so "file exists" cannot be mistaken for "usable as labelled".

## 5. Business keys and grain

| Family         | Grain / key                                                                                              | Evidence                                                   |
| -------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| HDB resale     | one row per registered resale application; `month + town + block + flat_type` is not unique (no unit id) | 990,860 rows, `unified_dataset` 1,236,310 rows after joins |
| HDB rental     | one row per approved rental application; `rent_approval_date` is `YYYY-MM`                               | 215,469 rows, coverage 2021-01 → 2026-10                   |
| URA private    | one row per transaction record, `sale_date` daily                                                        | 245,655 rows                                               |
| Amenity layers | one row/feature per facility                                                                             | 45–5,205 rows per layer                                    |
| Macro          | one row per period (`date` or `quarter`)                                                                 | see §3                                                     |

**No unit-level key exists** in any source: block+flat_type+month is the finest joint grain. That is why RS02 cannot produce a matched-unit yield and RS05 cannot claim unit-level facility effects.

## 6. What this pack does **not** establish

- It does not verify the article's sentence-level claims. It measures the inputs behind them; §2–§5 are the reconciliation a reviewer can check.
- It does not certify completeness of any month: coverage bounds are "the file contains this range", not "the source published every record in it".
- It does not resolve the RF03 EC/condo 2026 discontinuity; it records the coverage that question lives in.
- It does not authorize a rerun. Reading local files is not a research rerun; any refit still needs its own D10 grant.

## 7. Sign-off record

The three D12 attestations attach to the ledger's sha256. They live in the edition registry (`app/src/components/studies/lib/edition-registry.ts`), which now rejects an `approved` edition unless all three roles are present, distinct, non-preparer, and pin **one** artifact hash.

| Role            | Signatory                                              | Attests                                                                                                              | Recorded                |
| --------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| Source / cutoff | repo owner                                             | the measured ledger matches the tree and the cutoff/dispositions it implies                                          | **pending**             |
| Scientific      | recorded review run (`openai-codex/gpt-6-luna`, xhigh) | §1–§6 are accurate, the coverage claims are supported by the ledger, and §6's limits are stated — **recorded** below | **recorded 2026-11-14** |
| Publication     | repo owner (release authority, ≠ scientific reviewer)  | the exact artifacts to be published                                                                                  | **pending**             |

Until all three are entered and `bun run test:unit` passes `validateEditionRegistry`, no registry entry may claim `approved`, and every series continues to say "No approved current edition".

### Recorded scientific review (2026-11-14)

Run: `openai-codex/gpt-6-luna`, reasoning `xhigh`, four passes (the first three refused attestation; each refusal became a fixed defect). Verdict on the final artifact: **PASS WITH NOTES**.

> I reviewed RS01 at ledger hash `65ce7a10c257d13fd4250b2e8fd1519f8c35718497379aa103effc5594bfe8ae` and verified its source measurements, acquisition records, and derived row counts against this checkout; the derived-drift check passes. Note that §1's '12 external sidecar/geojson' shorthand is inaccurate; §4 gives the correct breakdown. This attests to the measured inventory, not completeness, cutoff authority, or article claims.

The note was resolved after the review (`§1` now reads "10 GeoJSON, 1 MRT JSON, 1 SORA parquet"); the ledger it pins did not change. This attestation is a **scientific review of the evidence pack**, not a publication approval, and it does not certify the article's sentences.
