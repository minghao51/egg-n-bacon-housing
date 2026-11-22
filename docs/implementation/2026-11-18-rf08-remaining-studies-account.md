# RF08 remaining-studies account — the 10 `historical` series

- **Measured:** 2026-11-18 by the orchestrator (producer role, [runbook §2.1](../../prompts/rf08-remaining-studies-runbook.md))
- **State:** 5 of 15 approved/published (`data-sources`, `rental-yields`, `temporal-evolution`,
  `amenity-impact`, `facility-premiums`); **10 remain**, all still `historical`/`archived`.
- **Status:** **accounting only.** No evidence pack, no edition text, no client-side change.
  A signature packet is **not** presented for any study here — the D12 reviewer row is absent (§0).
- **Method:** every "present"/"absent" below was read from the checkout today: parquet
  **schemas and row counts** (metadata only where the claim is about the schema), the JSON
  payloads actually served from `app/public/data/`, and the legacy texts under
  `docs/analytics/editions/legacy/2026-11-12/`. No number here is quoted from a legacy
  article as fact; legacy figures are listed only as **claims at risk**.

---

## 0. Blocker: the D12 named-reviewer row does not exist

`grep D12 docs/plans/2026-11-12-reporting-refresh-decisions.md` returns rows for RS01–RS05
and line 85 (`"Research method approvals — RS06/RS07 (units), RS08/RS13 (causal
identification), RS14 (forecast), RS10/RS11/RS12 …"`), which says a reviewer **is needed**
and names none. **No row names a scientific reviewer for RS06–RS15.**

Consequence, per runbook §0: measure and draft is permitted; **presenting a signature packet
for a model-, causal-, spatial-, forecast- or segment-gated study is not.** That covers 9 of
the 10 (RS15 inherits its gate from them). A reviewer must not be substituted or invented.

The row the owner records, in the ledger's own "Recorded decisions" form:

```
| D12 / RF08 — **named scientific reviewer** for RS06–RS15 | 2026-11-DD | `howt` (repo owner, release authority) | Names `openai-codex/gpt-6-luna (xhigh)` (`codex-luna-reviewer`) as the independent scientific reviewer for RS06–RS15, including the model, causal/RDD, spatial-method and forecast seats, on the same terms as RS01–RS05: every verdict is recorded with model identity, `automated: true`, and the owner retains both signatures (source/cutoff and publication). |
```

That string (`openai-codex/gpt-6-luna (xhigh)`, `automated: true`) is what lands in
`signoffs[]`. Until it exists, the pipeline below runs to **`ready-for-signature` and stops**.

---

## 1. The ten, accounted

Legend — **seat** is the register gate named in runbook §6. **Inputs present** were verified in
this checkout. **Outcome shape** is what the gate most plausibly permits, not what will be shipped.

| Row  | Series                      | Edition ID                         | Seat            | Inputs present                                                                      | Inputs absent                                         | Waves    |
| ---- | --------------------------- | ---------------------------------- | --------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------- | -------- |
| RS06 | `lease-decay`               | `lease-decay-<date>`               | model/units     | lease + price + PSF + PSM columns; bands asset                                      | original band definition; the fitted model            | B        |
| RS07 | `mrt-impact`                | `mrt-impact-<date>`                | model           | `dist_to_nearest_mrt` (+tier/interchange/score); town multipliers asset             | station opening/status vintages; the model            | B        |
| RS08 | `school-quality`            | `school-quality-<date>`            | causal/RDD      | 6 school-distance feature columns; 337-row school directory                         | quality score, tiers, coords, admission boundary, RDD | D        |
| RS09 | `macro-sensitivity`         | `macro-sensitivity-<date>`         | model/vintage   | 8 macro bronze series + 8 gold columns                                              | release vintages, revision history, policy-date table | A        |
| RS10 | `market-segments`           | `market-segments-<date>`           | segment/scoring | 6-segment asset with cohort counts + version 1.0.0                                  | feature scaling, K, model version, membership         | A        |
| RS11 | `spatial-autocorrelation`   | `spatial-autocorrelation-<date>`   | spatial         | coordinates; `esda`/`libpysal`/`h3` installed; per-area asset                       | weights as executed, seed, cell memberships           | C        |
| RS12 | `spatial-hotspots`          | `spatial-hotspots-<date>`          | spatial         | rent panel + **99.76%** geo-join to sale-side block coords                          | `search_result` flag, Gi\* code, cell memberships     | C        |
| RS13 | `causal-inference-overview` | `causal-inference-overview-<date>` | causal          | transactions + region labels (private only)                                         | policy dates, DiD/RDiT code, estimand, Bala schedule  | D        |
| RS14 | `price-forecasts`           | `price-forecasts-<date>`           | forecast        | 41-area stored forecasts (`forecast_date 2025-07-01`); realized outcomes to 2026-10 | training splits, features, per-segment model outputs  | E        |
| RS15 | `findings`                  | `findings-<date>`                  | inherits all    | 5 approved editions; 10 pending                                                     | every pending edition                                 | F (last) |

### RS06 `lease-decay` — unit reconciliation before any fit

- **Present:** `data/pipeline/04_platinum/unified_dataset.parquet` (1,236,310 × 97) carries
  `lease_commence_date`, `remaining_lease`, `price`, `area_sqm`, `psf`, `Unit Price ($ PSF)`,
  `Unit Price ($ PSM)`, `town`, `floor_level`, `dist_to_nearest_mrt`.
  `app/public/data/interactive_tools/lease_decay_analysis.json.gz` has 13 bands + 3 insights
  (`maturity_cliff` 21.9%, `best_value` 23.8%, `safe_zone` 5.2%) and 30 `town_decay_rates`.
- **Absent:** the legacy band definition as _executed_ (`data/parquets/L1/housing_hdb_transaction.parquet`,
  223,634 rows 2017-2026, lease 30-99, bins `[0,60,70,80,90,100]`) is retired; the hedonic
  model has no artefact. The interactive asset records bands, not a definition.
- **Claims at risk:** `+$54.75 PSF per extra year` — the appendix calls the response
  `price_per_sqm` while the sentence says PSF (exactly the "never convert a coefficient
  without confirming its original response/unit" gate); the `Discount vs 90+ yrs` column mixes
  median **price** (80-90: −13.2%) with PSF discounts elsewhere; `PASIR RIS −20.2%` is the
  inverse of its own row (fresh $4,676 < short $5,621) and is unlabelled; Bala-curve ±5%
  BUY/SELL arbitrage; the 60-year "liquidity tax" (Mann-Whitney).
- **Producer:** `scripts/tools/lease_decay_evidence.py`. **Outcome shape:** unit reconciliation
  plus a refit on one stated response, or explicit unit-withdrawal of the coefficient.

### RS07 `mrt-impact` — metres/km, response variable, and no marketing multiple

- **Present:** `dist_to_nearest_mrt`, `nearest_mrt_station`, `nearest_mrt_tier`,
  `nearest_mrt_is_interchange`, `nearest_mrt_score` (RS03 already re-measured the distance as
  reproducing exactly from the sha-pinned 188-row bronze frame, 20,000/20,000);
  `interactive_tools/mrt_cbd_impact.json.gz` (`property_type_multipliers{3}`,
  `town_multipliers{32}`, `cbd_coefficients{3}`, `town_premiums[32]`, `town_impacts[32]`).
- **Absent:** `raw_mrt_stations.parquet` is `name, lat, lon, line` — **188 rows, no opening
  date, no status** (the same finding RS03 recorded for temporal-evolution). No XGBoost/SHAP
  artefact, no OLS output, no CBD definition asset (the article's point is hard-coded prose).
- **Claims at risk:** `Condo … roughly 15x higher than HDB` (explicitly banned); the SHAP
  importance table (hawker 27.4%, lease 14.1%, park 7.2%, MRT 5.5%) — no model artefact exists,
  the same withdrawal shape as RS04; `OLS R² 0.52` / `0.4977` / `ΔR² +0.0078`; `$1.28 per 100m`;
  the town table's sign spread (+$59.19 Central Area to −$38.54 Marine Parade).
- **Producer:** `scripts/tools/mrt_impact_evidence.py`. **Outcome shape:** a stated
  response/log/PSF + standardized-effect comparison the checkout can re-measure; withdraw the
  multiple and the ranking.

### RS08 `school-quality` — the input the coefficients name does not exist

- **Present:** `nearest_schoolPRIMARY_dist`, `nearest_schoolSECONDARY_dist`,
  `dist_to_nearest_school`, `nearest_top_primary_school_dist`,
  `nearest_top_secondary_school_dist`, `school_accessibility_score`;
  `raw_school_directory.parquet` = 337 rows × `school_name, url_address, address, postal_code,
zone_code, type_code, nature_code, mainlevel_code, sap_ind, autonomous_ind, gifted_ind,
ip_ind, …`.
- **Absent:** `school_primary_quality_score`, `school_primary_dist_score`,
  `school_secondary_dist_score` — **none of the three feature names the legacy coefficients
  use exists in any layer** (the 97-column schema was read; §4 of the defect canon: read the
  schema, do not assume it). Also absent: school coordinates, tier provenance, the 1 km
  admission boundary as a dated artefact, and the RDD itself.
- **Claims at risk:** `+$9.66 / +$6.27 / +$3.52 PSF` and the `≈$29,000` worked example;
  RDD `−$79.47 PSF` on 52,881 near-boundary rows with covariate balance "Failed" (so the
  headline number is a failed-design estimate, not a premium); the regional split
  (`+$9.63 / −$23.67 / ≈$0`, R² 0.53/0.80/0.87) — note RCR's −$23.67 is a **flipped sign the
  article treats as a finding**; the spatial-CV generalisation-gap claim.
- **Producer:** `scripts/tools/school_quality_evidence.py`. **Outcome shape:** identification
  audit; a distance-based association with the tier proxy named explicitly, and withdrawal of
  causal/RDD language — nothing in the checkout supports re-running the RDD.

### RS09 `macro-sensitivity` — the fallback series is identifiable, and there are two SORAs

- **Present (measured today):**

  | Bronze series                    | Rows   | Span                  |
  | -------------------------------- | ------ | --------------------- |
  | `cpi.parquet`                    | 789    | 1961-01 → 2026-09     |
  | `gdp.parquet`                    | 202    | 1976Q1 → 2026Q2       |
  | `sora_rates.parquet`             | **60** | **2021-01 → 2025-12** |
  | `bank_rates.parquet` (`sora_3m`) | 465 file rows / **252 with a value** | file 1988-01 → 2026-09; **values 2005-10 → 2026-09** |
  | `unemployment.parquet`           | 139    | 1992Q1 → 2026Q3       |
  | `hdb_rpi.parquet`                | 147    | 1990Q1 → 2026Q3       |
  | `ura_ppi.parquet`                | 207    | 1975Q1 → 2026Q3       |
  | `wage_growth.parquet`            | 100    | 2001Q1 → 2025Q4       |

- **The conflict the gate is aimed at:** two SORA series with different spans (`sora_rates`
  60 monthly rows ending 2025-12 vs `bank_rates.sora_3m` 465 rows ending 2026-09), and **both**
  are carried into gold as separate columns (`sora_rate`, `sora_3m`). The legacy appendix's
  `60 monthly observations (2021-2025)` matches the short one exactly. The article also states
  in its own conclusion that collection "relies on SingStat API with **fallback to generated
  data** when API calls fail" — the fallback is not marked in any file (`pandas` metadata only,
  no vintage/release/extraction stamp on any of the eight).
- **Absent:** release lags, revision history, `housing_policy_dates.parquet` (the 5 policy
  events behind §5), stationarity tests, and any uncertainty.
- **Claims at risk:** the three-regime table, the correlation matrix (`Weak`/`Moderate` with no
  coefficient), the nominal/real CAGR table (point ranges with no n), the policy-date
  market-impact table, and `confirms that interest rates are the most actionable macro
indicator` (§4 canon 11: "confirms that" is banned for a descriptive correlation).
- **Producer:** `scripts/tools/macro_sensitivity_evidence.py`. **Outcome shape:** a measured
  vintage/fallback audit that names each series' provenance and span, then exclusion of the
  unidentified series from claims or a labelled simulation.

### RS10 `market-segments` — the segments are hand-written literals, and only area-level membership exists

- **Present:** `app/public/data/segments_enhanced.json.gz` — 6 segments, `version "1.0.0"`,
  `lastUpdated 2026-04-19T23:23:07`, each with `id` (e.g. `large_size_stable`),
  `clusterClassification`, `metrics{avgPricePsf, avgYield, yoyGrowth, transactionCount,
marketShare}`, `persistenceProbability`, and a `planningAreas` **name list**;
  `dashboard_segments.json.gz`; gold `market_segment`, `property_segment`, `price_stratum`.
- **Absent:** K, the scaler/log-transform parameters the article describes, the model version,
  silhouette/elbow outputs, and **any per-transaction membership**. The article says five
  segments; the asset has six.
- **Correction to this account's first version:** there **is** a stored membership mapping, at
  planning-area granularity, and it is many-to-many — the asset's top-level `planningAreas` dict
  holds 31 areas each with a `segments` list (51 area→segment pairs, 0–4 segments per area, 6
  areas with none). It is symmetric with each segment's own `planningAreas` name list and joins
  to the frame's 44 `planning_area` values for 1,185,397 rows. So "no joinable membership" was
  too strong: per-**transaction** membership is what does not exist (zero segment-id matches in
  any shipped column), and an area can belong to several segments at once, so the mapping
  assigns no transaction to one segment. Measured in RS10's ledger at
  `membershipRecovery.areaLevelJoin`; it was found by the study, not by this account.
- **Measured hard finding:** the segment literals are **hand-written in a plan document**, not
  produced by a model — `docs/plans/2026-02-22-interactive-market-segments-dashboard-implementation.md:457`
  carries the six dicts verbatim with a `# 12.6% of ~910K` comment, and
  `scripts/generate_segments_data.py` does not exist. The "model version" here is a document
  revision, which changes what the gate can ever be satisfied by.
- **Measured hard finding:** gold's `market_segment` is **not** the behavioural segmentation —
  it is a region label, and only for private rows:
  `None 990,655 · Outside Central Region 132,795 · Rest of Central Region 74,161 ·
Core Central Region 38,699`. There is no ID→population mapping to recover, so
  "do not reuse a segment ID for a different population" resolves to: reuse is **impossible**
  here, and cohort counts can only be quoted as the asset's own unverified figures.
- **Claims at risk:** the five-segment profile table, the CAGR-by-planning-area table
  (a `2015-2025` window the data cannot match — private data starts 2021-01), the composite
  scoring bands (50% appreciation z + 50% yield z, never defined as code), `>85% agreement`
  hierarchical validation, `r ~ -0.3`.
- **Producer:** `scripts/tools/market_segments_evidence.py`. **Outcome shape:** recovered
  cohorts/IDs/version recorded as **inspection-only**, plus either a fresh clustering under new
  IDs or withdrawal of the segment taxonomy.

### RS11 `spatial-autocorrelation` — the served asset is degenerate

- **Present:** `lat`/`lon` on every transaction; `esda>=2.8.1`, `libpysal>=4.14.1`, `h3==4.1.0b2`
  in the `research` dependency group (so the method is runnable in this environment);
  `app/public/data/analytics/spatial_analysis.json.gz` with `metadata{generated_at:
2026-02-19T17:23:01, data_version: "L3_unified_dataset", methodology: "Getis-Ord Gi* hotspot
analysis, LISA clustering, Moran's I"}` and 41 planning areas each holding
  `hotspot{z_score,p_value,confidence,classification}`, `lisa_cluster{type,yoy_appreciation,
persistence_rate,transition_probabilities}`, `neighborhood_effect{moran_i_local,spatial_lag,
neighborhood_multiplier}`.
- **Measured hard finding:** the payload is a placeholder, not a run — the first area (ANG MO
  KIO) returns `z_score 0.0`, `p_value 1.0`, `classification NOT_SIGNIFICANT`,
  `moran_i_local 0.0`, `spatial_lag 295000.0`, `neighborhood_multiplier 1.0`; `295000.0` is
  also the `theoretical_value_30yr` in the lease asset, i.e. a constant, not a measurement.
  **Moran's I 0.766 / z 9.91 are therefore not recoverable from any served asset.**
- **Lineage defect inside the article:** the appendix names the primary input as
  `L1/housing_hdb_rental.parquet` (rent levels) while every finding is about **appreciation**.
- **Claims at risk:** Moran's I 0.766, z 9.91; the cluster table (HH 16 cells 12.7%,
  LH 17 cells 11.3%, LL 1 cell ~10%, NS 8 cells 12.0%); spatial-lag correlations
  (Condo 78% / HDB 71% / EC 65%); "transition analysis: moderate persistence" — a time-series
  claim with no time dimension in the asset.
- **Producer:** `scripts/tools/spatial_autocorrelation_evidence.py` (h3 r8 cells, KNN k=8
  row-standardised, 99 permutations with the **seed recorded**, multiplicity correction stated).
  **Outcome shape:** reproducible weights + memberships + significance metadata; withdraw the
  transition and persistence claims.

### RS12 `spatial-hotspots` — feasible today, and the join is measured

- **Present:** `raw_hdb_rental.parquet` = 215,469 rows, `rent_approval_date` 2021-01 → 2026-10,
  columns `_id, rent_approval_date, town, block, street_name, flat_type, monthly_rent`
  (**no coordinates**). Sale-side `02_silver/geocoded_validated.parquet` yields 11,637 distinct
  `(block, street_name)` keys with `lat`/`lon`.
- **Measured today:** for the gate's own window (2024-01 → 2025-01), **39,385 of 39,478 rental
  rows join to a sale-side block geocode = 99.76%**. The legacy's `search_result == 0` flag
  (`L2/housing_unique_searched.parquet`) is retired, so this join replaces it — and the 0.24%
  unmatched rows are a disclosable population, not silently dropped.
- **Absent:** the Gi\* implementation, the H3 cell tables (legacy: 847 cells, 623 sufficient),
  transition probabilities.
- **Claims at risk:** `12 H3 cells at 99% confidence`; Gi\* values 4.21 / 3.89 / 3.45 / −3.21 /
  −2.98 / −2.67; the `$1,350/month` gap; persistence 58-62% / coldspot 55-60% /
  NS→hotspot 8-10%; `Orchard $3,200 median` from `monthly_rent` whose observed range is
  1,000–980 (a data defect to check before quoting any level).
- **Producer:** `scripts/tools/spatial_hotspots_evidence.py`, window pinned to
  **2024-01 – 2025-01**. **Outcome shape:** rerun of the stated method on the measured
  population + instability disclosure, written to a **new** rental-only asset (the gate keeps
  rental hotspots separate from the transaction-activity product; RA04 stays RS11's).

### RS13 `causal-inference-overview` — no policy artefact exists

- **Present:** 1,236,310 transactions 1990-01 → 2026-11 (cutoff 2026-10); `property_type`,
  `planning_area`, `region`; `market_segment` for the private rows only
  (so CCR/RCR/OCR is defined **only** where the legacy DiD needs it, and is null for all
  990,655 HDB rows); `analysis/causal_did_analysis.png`.
- **Absent:** `housing_policy_dates.parquet`, the DiD/RDiT code, the estimand, the treatment/
  control construction, the bandwidth grid (3/6/9/12 months claimed), pretrend evidence, and
  the Bala depreciation schedule behind the "lease mispricing" table.
- **Claims at risk:** `−$137,743` DiD (CCR vs OCR condos, Sep 2022 ABSD) and `+$13,118` HDB
  RDiT jump (Dec 2023) — both are point estimates with no uncertainty and no pretrends;
  the lease-mispricing bands (30-50 richly priced, 80-84 mild undervaluation, 97-98 large
  discount); `robustness … confirms direction is stable`.
- **Producer:** `scripts/tools/causal_inference_evidence.py`. **Outcome shape:** identification
  audit. Expect the same shape as RS05 — an edition that publishes an **absence** — unless the
  owner supplies the policy dates as a dated input.

### RS14 `price-forecasts` — expired on purpose, scorable for real

- **Present:** `app/public/data/analytics/predictive_analytics.json.gz`, metadata
  `{generated_at 2026-02-19T17:23:03, forecast_horizon "6_months", model_r2 0.89,
last_training_date "2025-01-01"}`, 41 planning areas each with
  `price_forecast{projected_change_pct, confidence_interval_lower/upper, model_r2,
forecast_date "2025-07-01", signal "BUY"}` (sample: ANG MO KIO +27.2% [+19.1, +35.4], R² 0.85,
  BUY), plus `policy_risk` and `lease_arbitrage` blocks.
- **Absent:** `price_appreciation_train/test.parquet`, the feature list, per-segment model
  outputs, and any provenance for the article's per-segment R²/CI table
  (79.8/98.5/85.6/72.6/30.1 with ±18.58% to ±1877.88%).
- **Gate is directly actionable:** realized outcomes now exist through 2026-10, so the stored
  `2025-07-01` projections **can be scored** — rolling-origin + naïve baseline + empirical PI
  coverage. `signal: "BUY"` on an expired forecast is exactly the "never reuse BUY/SELL prompts
  as current advice" clause.
- **Claims at risk:** the five-segment reliability table; `74% vs 47%`; top features 51.14% /
  65.50%; ARIMA on 20 planning areas; `model_r2 0.89` (an in-sample fit statistic, not forecast
  accuracy — "name R² correctly").
- **Producer:** `scripts/tools/price_forecasts_evidence.py`. **Outcome shape:** lineage
  reconciliation + an accuracy table scoring the expired projections, R² named correctly.

### RS15 `findings` — last, and legitimately narrower

- **Present:** the 19 KB legacy text; the 5 approved editions; RA01
  `app/src/data/persona-content.json` still carrying unsupported promises.
- **Constraint:** every quantitative sentence must link to a reviewed edition with its
  population/window/unit; unresolved dependencies are omitted or flagged. With 5 of 10
  dependencies unresolved, `findings` is **blocked by design** until those resolve.
- **Register permits narrowing:** "The whole register need not be completed to publish an
  honest, narrower summary." So a 5-edition summary is publishable _before_ the other nine —
  as an explicit narrower scope, never as "programme complete".

---

## 2. What the account changed

Six facts measured today reframe five of the ten gates, and none of them were known at handoff:

1. **RS08's three named model features do not exist in any layer** — the coefficients cannot be
   re-derived; only _distance_ features survive. This is a stronger prior than "likely withdrawal".
2. **RS10's segments are hand-written literals with only area-level membership** — the six dicts
   sit in a plan document, gold's `market_segment` is a region label (990,655 nulls), the asset
   carries six segments to the article's five, and the only stored mapping is many-to-many at
   planning-area granularity. Reuse of an old ID is not merely discouraged, it is impossible; a
   taxonomy is either rebuilt or withdrawn.
3. **RS11's served asset is degenerate** (`z_score 0.0`, `spatial_lag 295000.0` constant,
   `moran_i_local 0.0`), so **Moran's I 0.766 is not recoverable** — the edition must re-measure
   it, not cite it.
4. **RS12 is feasible today**: 99.76% of the gate's own window joins to a block geocode, so the
   retired `search_result == 0` lineage is replaceable with a disclosable join.
5. **RS09 has a concrete fallback target**: two SORA series with different spans carried as two
   gold columns, and a self-declared "fallback to generated data" with no provenance stamp
   anywhere.
6. **RS14's stored forecast is expired but scorable** (`forecast_date 2025-07-01`, realized
   outcomes to 2026-10), which turns the forecast gate from an audit into a measurement.

---

## 3. Parallel execution plan

Measure and draft **in parallel**; materialise signatures **serially**. Nothing in a producer
touches a shared file, and no producer writes a medallion layer.

### 3.1 Waves

| Wave  | Studies    | Why together                                                      | Independence                                                              |
| ----- | ---------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **A** | RS09, RS10 | source/vintage archaeology — cheap, mechanical, highest certainty | read bronze/asset only; no model seat exercised beyond D12                |
| **B** | RS06, RS07 | unit/response decisions the register defers to the owner          | disjoint frames and assets (RA06 vs RA07)                                 |
| **C** | RS11, RS12 | same method family (`esda`/`libpysal`/`h3`), runnable in this env | **RA04 is RS11's alone**; RS12 writes a new rental-only asset             |
| **D** | RS08, RS13 | identification audits, most likely to withdraw                    | RS13 needs the private-only region split; RS08 needs school distance only |
| **E** | RS14       | needs realized outcomes to be final (cutoff 2026-10)              | RA02 alone                                                                |
| **F** | RS15       | gates on A–E                                                      | —                                                                         |

Within a wave the two studies can run concurrently because their owned files are disjoint
(§3.2). Waves are not a barrier: a finished Wave-A study can sign while Wave B measures, since
signing touches only the shared state files, which are then taken one at a time.

### 3.2 File ownership

**Owned per study, never shared (safe to write concurrently):**

- `scripts/tools/<series>_evidence.py` (+ its `--check` mode)
- `docs/implementation/artifacts/rs<NN>-<series>-evidence.json` (canonical ledger, <500 KB)
- `docs/implementation/<date>-rs<NN>-<series>-evidence.md` (the pack)
- `docs/analytics/editions/<series>/<date>/<series>.md` (the frozen text — a **new** path; the
  legacy file under `editions/legacy/2026-11-12/` is never edited)
- `docs/implementation/<date>-rs<NN>-<series>-editions-signoff.md` (doc-writer)

**Shared — serialised, signature-time only:** one study at a time, in this order:

1. `app/src/components/studies/lib/edition-registry.ts` — one entry per edition; the file is the
   single identity source for both the series page and the archive route.
2. `app/tests/unit/edition-registry.test.ts` — the approved-list guard (it asserts
   `mrt-impact`, `lease-decay`, `price-forecasts` are unapproved today, so it fails until the
   list is extended: that is the guard working).
3. `docs/plans/2026-11-12-reporting-refresh-decisions.md` — three D12 rows per study.
4. `docs/implementation/README.md`, `prompts/handoffs.md`, the continuation brief status row
   (doc-writer).
5. `app/public/data/catalog.jsonl.gz` — rewritten by `bun run build`; restore or pin
   deliberately, never as a side effect of a parallel run.

**Data assets — one owning study each, always a new path, never overwritten:**
RA06→RS06, RA07→RS07, RA05→RS10, RA02→RS14, RA04→RS11. RS12 gets a new rental-only asset.
RA03 (`feature_impact`) and RA08 (`spatial_hotspots`) stay inspection-only unless a study's
gate explicitly claims them.

**Never written by a producer:** `data/pipeline/**` (read-only — the DAG is not re-run by any
of these ten gates; gold already holds every column they need). A refit lives in the producer
script's memory and, if it must persist, under a study-scoped path outside the medallion.

### 3.3 Cost estimate, from the programme's own record

RS03 needed 3 review rounds, RS04 5, RS05 4 — 12 rounds over 3 studies, 4 per study. Ten studies
is therefore ~40 independent review rounds plus 10 producer/verify passes. Parallelism shortens
wall-clock on measurement and drafting; it does not shorten review, because one reviewer
re-derives one text per dispatch.

---

## 4. What does not change

- **Baselines stay as recorded** in runbook §3 (unit 534/0/34 files, astro-check 0/0/22,
  build 224 pages, e2e 237+9, python 1136, baseline 15 sources/72 assets, data boundary
  v1 `0e1013ee485f` / v2 `2c30e2aa836c` / 47,104 month cells).
- **The defect canon applies unchanged** — RS03–RS05 produced 28 defects, one of them a wrong
  measurement (RS05's HC1 SEs, 12–17× understated). Every item in §1's "claims at risk" is
  already a prose-outruns-ledger candidate; assume the ratio holds.
- **Signature discipline is unchanged:** per study, never delegated, never pre-filled; the
  orchestrator authors the text it would ask to be signed, so it never writes `approved`,
  `signoffs` or `editionSha256`, and never reviews its own text.
- **Escalation is unchanged** (runbook §7) — and RS09's two-SORA conflict, RS13's missing
  policy dates and RS06/RS07's unit decisions are all owner-facing (§7 bullets 1 and 2), not
  agent-decidable.
