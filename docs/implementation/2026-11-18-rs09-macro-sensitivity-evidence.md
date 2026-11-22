# RS09 evidence pack — macro-sensitivity: the fallback SORA is identified, the source series is named, and the regime claims are withdrawn

- **Date:** 2026-11-18
- **Status:** **Prepared for review, not signed off.** The ledger is measured and `--check`-able; no macro model is fitted and the legacy article's rate-band, regime, policy-timing and segment-return claims are withdrawn or re-measured with a stated reason. No signature in this pack is an approval. Register row: RS09. Gate (research register, quoted): _"Explicitly identify generated/fallback series and exclude them from empirical claims unless the entire result is a labelled simulation. Document release lag, revisions, missing periods, stationarity and uncertainty. No present-day timing regime claims from unknown source vintages."_
- **Prepared by:** `repo-agent/session-2026-11-18`.
- **Machine-readable ledger:** [`artifacts/rs09-macro-sensitivity-evidence.json`](artifacts/rs09-macro-sensitivity-evidence.json) — sha256 `ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b`, 96,351 bytes (canonical JSON, sorted keys, no timestamps, no absolute paths).
- **Producer:** `scripts/tools/macro_sensitivity_evidence.py`. Run twice → byte-identical (`cmp` clean); `uv run python scripts/tools/macro_sensitivity_evidence.py --check` re-measures the checkout and passes.
- **Frozen legacy text this pack checks against:** `docs/analytics/editions/legacy/2026-11-12/macro-sensitivity.md` — sha256 `8af923420706a072c1b8e6287b4d54b70bdfbad3afcd65dce1a9e7cce41a7a88`, 157 lines (recorded at `legacyQuoteCheck.legacyFileSha256`; all **35** legacy quotes verified verbatim at `legacyQuoteCheck.quotes`).
- **Review history:** round 1 **FAIL** (seven defects: hidden missing-source rows, an unenforced exclusion, an overstated ADF reading, a real-return denominator reusing the nominal window, a Fisher interval with no serial-dependence caveat, an incomplete claim inventory, a caveat contradicting its own label). Round 2 **FAIL** (a rate band measured over the wrong window, an effective-n formula that used one side of the pair, nine more missing claims). Rounds 3–6 **FAIL** (prose lagging code; claim keys that did not substantiate their dispositions; an absence claim contradicted by the exporter's own affordability code; C9 conflating file rows with observations). Round 7 **FAIL** on the measurement recorded in §4 — `asOfEqualShare` computed coverage rather than equality — which is fixed. See §12.
- **Upstream:** the cutoff rule and the "measured, never cited" lineage discipline from [RS03](2026-11-15-rs03-temporal-evolution-evidence.md); the gold-column lineage method mirrors [RS05](2026-11-17-rs05-facility-premiums-evidence.md) §6's response-lineage check. `unified_dataset.parquet` sha256 `39d234f703c9d6e098acc885eaadfdc965a6ac217189277c066676b3b117cefe` is the same platinum dataset RS04/RS05 pinned.

## 1. What was measured, and the cutoff

The observation cutoff is the same measured rule RS03/RS04/RS05 shipped (`cutoff`): the last complete month is **2026-10**, because the terminal month **2026-11 holds 1,211 transactions — 0.264 of the trailing-12-month median of 4,587.5** (`terminalMonthTransactions`, `terminalMonthShareOfTrailingMedian`, `trailing12MedianTransactions`) and is partial.

| Field                                       | Value                                                           |
| ------------------------------------------- | --------------------------------------------------------------- |
| `cutoff.lastCompleteMonth`                  | `2026-10`                                                       |
| `cutoff.terminalMonth` / transactions       | `2026-11` / 1,211                                               |
| `cutoff.terminalMonthShareOfTrailingMedian` | 0.264                                                           |
| Population the cutoff was measured on       | `unified_dataset`, 1,236,310 rows (HDB 990,655 + condo 245,655) |

Every **housing-side** aggregate below (the HDB monthly series in §6 and the return figures in §7) is bounded at `2026-10`. The **macro** series have their own measured observation ends, reported per series in §2; a macro figure may end earlier than the housing bound, and each table names the window it used.

## 2. The series inventory: what is missing, and how little provenance exists

All eight bronze macro series (`seriesInventory`). Three states are counted separately because the legacy study's characteristic failure was conflating them: a **null value** (the period row exists, its source value does not), an **absent period** (no row at all), and a **recorded zero**.

| Series           | File rows | Non-null values | Null values (missing source) | Null-value span       | Absent periods | Recorded zeros | Non-null span         | Distinct values |
| ---------------- | --------: | --------------: | ---------------------------: | --------------------- | -------------: | -------------: | --------------------- | --------------: |
| `cpi`            |       789 |             789 |                            0 | —                     |              0 |              0 | 1961-01 → 2026-09     |             780 |
| `gdp`            |       202 |             202 |                            0 | —                     |              0 |              0 | 1976Q1 → 2026Q2       |             109 |
| `hdb_rpi`        |       147 |             147 |                            0 | —                     |              0 |              0 | 1990Q1 → 2026Q3       |             133 |
| `sora_rates`     |        60 |              60 |                            0 | —                     |              0 |              0 | 2021-01 → 2025-12     |              55 |
| **`bank_rates`** |   **465** |         **252** |                      **213** | **1988-01 → 2005-09** |          **0** |          **0** | **2005-10** → 2026-09 |             245 |
| `unemployment`   |       139 |             139 |                            0 | —                     |              0 |              0 | 1992Q1 → 2026Q3       |              31 |
| `ura_ppi`        |       207 |             207 |                            0 | —                     |              0 |              0 | 1975Q1 → 2026Q3       |             177 |
| `wage_growth`    |       100 |             100 |                            0 | —                     |              0 |              0 | 2001Q1 → 2025Q4       |              19 |

Two facts here are easy to get wrong from a file listing, and both change a measurement:

- **`bank_rates` holds 465 monthly rows of which only 252 carry a value.** The other **213 are missing-source rows spanning 1988-01 → 2005-09** — the period exists, the `sora_3m` value does not. Any statement of the form "SORA runs from 1988" describes the file, not the series: the series starts **2005-10**. No period is absent from the grid and no zero was recorded.
- **No series has an interior gap.** Every series is complete between its first and last non-null period; the differences between series are start and end dates, not holes. This matters for §6, where first differences would otherwise be taken across a gap.

Provenance (`vintageAudit`), measured rather than assumed:

| Question                      | Measured answer                                                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Release timestamp per series? | none — the only parquet metadata keys on all eight files are `ARROW:schema` and `pandas`                                |
| Extraction/observation stamp? | none                                                                                                                    |
| Revision history / vintages?  | none — exactly one file per series, no snapshot set                                                                     |
| Housing-policy-date artefact? | none — a checkout-wide glob for policy/vintage artefacts returns **no candidates** (`policyDateArtefactCandidates: []`) |

The gate's "document release lag, revisions" cannot be satisfied from this checkout, and §8 records that as a first-class result rather than approximating it.

## 3. The generated/fallback series: identified, band-checked, and the exclusion quantified

The legacy article states in its own conclusion that collection "relies on SingStat API with **fallback to generated data when API calls fail**". The gate asks which shipped series that fallback is.

### 3a. The structural screen (`fallbackAudit.signatures`)

Two fill patterns are measurable without provenance — **annual-resolution tiling** (each year carries one distinct value repeated across its periods) and an **annual ramp** (most variance between years, larger steps on year boundaries, monotone year-mean path):

| Series            | Between-year variance share | Year-boundary step share | Tiled years | Distinct values per year | Screen                                   |
| ----------------- | --------------------------: | -----------------------: | ----------: | ------------------------ | ---------------------------------------- |
| **`wage_growth`** |                  **1.0000** |                        — | **25 / 25** | **{1}**                  | **`annual-resolution-tiling-signature`** |
| **`sora_rates`**  |                  **0.9939** |               **0.3444** |       0 / 5 | {10, 11, 12}             | **`annual-ramp-signature`**              |
| `cpi`             |                      0.9992 |                   0.0939 |      0 / 66 | {9, 11, 12}              | `no-fallback-signature-detected`         |
| `hdb_rpi`         |                      0.9952 |                        — |      0 / 37 | {2, 3, 4}                | `no-fallback-signature-detected`         |
| `ura_ppi`         |                      0.9961 |                        — |      0 / 52 | {2, 3, 4}                | `no-fallback-signature-detected`         |
| `bank_rates`      |                      0.9324 |                   0.0945 |      0 / 22 | {3, 9, 11, 12}           | `no-fallback-signature-detected`         |
| `gdp`             |                      0.7547 |                        — |      0 / 51 | {2, 3, 4}                | `no-fallback-signature-detected`         |
| `unemployment`    |                      0.5722 |                        — |      0 / 35 | {2, 3, 4}                | `no-fallback-signature-detected`         |

Each label carries its own caveat (recorded per series). Read with them: a high between-year variance share is **also what a genuinely trending index looks like** — `cpi`, `hdb_rpi` and `ura_ppi` are trending indices, and their 0.995–0.999 shares are expected, not suspicious. What separates `sora_rates` is a **0.3444 year-boundary step share** (four boundaries carrying a third of all movement; the trending indices sit at 0.09) _plus_ a monotone year-mean path. What separates `wage_growth` is that **every one of its 25 years holds exactly one distinct value across four quarterly rows** — no series with genuine quarterly variation looks like that, and the file's 100 rows therefore carry 19 distinct values, not 100 independent observations.

**Both flagged series are designated `audit-only` in the association section** (§6): their numbers are reported to show what excluding them costs, and no claim in the refreshed edition may rest on them. The designation is a ledger field per series, not a prose promise (`associations.series.<name>.designation`).

### 3b. The article's own four rate bands, measured on the source series (`fallbackAudit.soraBandCheck`)

| Article band  | Claimed    | Measured window       | Months |   Mean |    Min |    Max |
| ------------- | ---------- | --------------------- | -----: | -----: | -----: | -----: |
| 2021 (H1)     | `0.1-0.2%` | 2021-01 → 2021-06     |      6 | 0.1796 | 0.1326 | 0.2216 |
| 2022 (H2)     | `2.5-3.5%` | 2022-07 → 2022-12     |      6 | 2.2247 | 1.2712 | 3.0294 |
| 2023          | `3.5-4.0%` | 2023-01 → 2023-12     |     12 | 3.5915 | 3.1419 | 3.7527 |
| 2024-2025     | `3.0-3.5%` | **2024-01 → 2025-12** | **24** | 2.7390 | 1.1857 | 3.6829 |
| _source span_ | —          | _2024-01 → 2026-08_   |   _32_ | 2.3303 | 1.0298 | 3.6829 |

Two of the four bands reproduce and two do not. The 2021 H1 mean (0.1796) sits inside the quoted 0.1–0.2%, and 2023 (3.5915) sits inside 3.5–4.0%. The 2022 H2 mean (**2.2247**) is below the quoted 2.5–3.5%, and the 2024-2025 mean (**2.7390**) is below the quoted 3.0–3.5%. The last row is context only, and it exists to keep two questions apart: a 32-month mean answers _what the source averaged after 2025_, while the article's claim is about 2024-2025 — the 24-month row is the one that answers it.

### 3c. The two SORA candidates, confronted on their shared months (`fallbackAudit.soraConfrontation`, `soraYearMeans`)

On the **60 months they share (2021-01 → 2025-12)**:

| Year | `sora_rates` year mean | `bank_rates` year mean | Ratio long : short |
| ---- | ---------------------: | ---------------------: | -----------------: |
| 2021 |                 0.1953 |                 0.1648 |             0.8441 |
| 2022 |                 0.2914 |                 1.3085 |             4.4902 |
| 2023 |             **0.4957** |             **3.5915** |         **7.2459** |
| 2024 |                 0.8037 |                 3.5213 |             4.3811 |
| 2025 |                 1.1953 |                 1.9568 |             1.6371 |

Across the overlap: Pearson r **0.4067**, mean difference (short − long) **−1.5123** percentage points, max absolute difference **3.2704** points. A 2023 disagreement of **7.2×** between two series claiming to measure the same rate is not a vintage artefact; they are different constructs, and §3b shows the article's own bands belong to the long one. The long series also has a plausible pre-2021 history (year means 2006 3.19, 2009 0.21, 2013 0.05, 2020 0.40), whereas the short series begins mid-cycle in 2021-01 with the ramp of §3a.

### 3d. The exclusion, and what choosing the wrong column would have cost (`associations.soraFallbackContrast`)

Same 60 months, same target (HDB resale median psf per month):

| Statistic                                           | `sora_rates` (fallback) | `bank_rates` (source candidate) |
| --------------------------------------------------- | ----------------------: | ------------------------------: |
| Levels: Pearson r vs monthly HDB median psf, n = 60 |              **0.9422** |                      **0.5870** |
| Levels: unadjusted 95% CI                           |         0.9047 → 0.9652 |                 0.3914 → 0.7318 |
| Levels: Spearman ρ                                  |                  0.9604 |                          0.5263 |
| First differences: Pearson r, n = 59                |                  0.0646 |                          0.1445 |
| First differences: unadjusted 95% CI                |        −0.1947 → 0.3155 |                −0.1159 → 0.3863 |
| First differences: serial-adjusted CI               |        −0.2067 → 0.3267 |                −0.1440 → 0.1050 |

The ramp correlates **0.9422** with HDB median psf in levels while the source series correlates **0.5870** on the same months. Both level figures are trend-dominated and neither is evidence of sensitivity (§6); the gap between them is the quantified cost of taking the wrong column, which is one query away because both columns ship (§4).

**The rule this pack applies and the edition inherits:** no claim uses `sora_rates`. Every SORA figure is measured from `bank_rates.sora_3m`, whose usable span is 2005-10 → 2026-09.

## 4. Both SORAs are shipped into the gold layer (`goldColumnLineage`)

`unified_dataset` carries **both** candidates as separate columns, and each reproduces its bronze source **exactly** (max absolute gap 0.0):

| Gold column         | Reproduced by                       | Exact-month equality | Months compared | Null month-rows in gold | Distinct values |
| ------------------- | ----------------------------------- | -------------------: | --------------: | ----------------------: | --------------: |
| `sora_rate`         | **`sora_rates`** (the ramp)         |                  1.0 |              60 |                     383 |              55 |
| `sora_3m`           | **`bank_rates`** (source candidate) |                  1.0 |             252 |                     191 |             245 |
| `cpi`               | `cpi`                               |                  1.0 |             441 |                       2 |             434 |
| `gdp`               | `gdp`                               |                  1.0 |             438 |                       5 |              91 |
| `hdb_rpi`           | `hdb_rpi`                           |                  1.0 |             441 |                       2 |             133 |
| `unemployment_rate` | `unemployment`                      |                  1.0 |             417 |                      26 |              31 |
| `ura_ppi`           | `ura_ppi`                           |                  1.0 |             441 |                       2 |             139 |
| `wage_growth`       | `wage_growth`                       |                  1.0 |             300 |                     143 |              19 |

Lineage is measured, never inferred from a column name. The consequence is a trap a fresh query walks into by default: `sora_rate` — the shorter, friendlier-named column — **is the screened-out ramp**, populated for exactly 60 months and null for the other 383. The table also exposes the fill convention (a quarterly series written into monthly rows), which is why `cpi` reproduces on 441 months from 789 monthly source rows and `wage_growth` on 300 from 100 quarterly rows.

Two comparisons are recorded per candidate and are deliberately kept apart, because reporting one under the other's name was a defect the review caught: **exact-month** equality counts only gold months the bronze series itself covers, **as-of** equality carries the bronze value forward across every gold month, and a separate `coverageShareOfGoldMonths` says how many months had a value at all. "How many months had a value" is not "how many months agreed". The consequence is decisive for the rejected candidate: against `sora_rate`, `bank_rates` agrees on **0 of 60** months exactly and **0 of 60** as-of (coverage 1.0), while `sora_rates` agrees on **60 of 60** both ways — so the lineage is a measurement, not a similarity judgement.

## 5. Stationarity (`stationarity`)

Augmented Dickey-Fuller, levels, constant only, AIC lag selection, per series over its own span:

| Series           | ADF statistic |    p-value | Lags used |   n | Rejects unit root at 5% |
| ---------------- | ------------: | ---------: | --------: | --: | ----------------------- |
| `gdp`            |       −3.4891 |     0.0083 |         8 | 193 | **yes**                 |
| `bank_rates`     |       −3.2503 |     0.0173 |        10 | 241 | **yes**                 |
| `unemployment`   |       −2.0348 |     0.2713 |        13 | 125 | no                      |
| `wage_growth`    |       −2.4660 |     0.1240 |         8 |  91 | no                      |
| `hdb_rpi`        |       −1.0192 |     0.7462 |        10 | 136 | no                      |
| `ura_ppi`        |        0.0080 |     0.9592 |         2 | 204 | no                      |
| `cpi`            |        0.6084 |     0.9878 |        21 | 767 | no                      |
| **`sora_rates`** |   **+5.1627** | **1.0000** |        11 |  48 | no                      |

**What this does not say.** Failing to reject the unit-root null is _not_ evidence that a series is non-stationary — ADF is low-powered, and a short or near-integrated series fails to reject for reasons unrelated to its origin. The operational consequence recorded in the ledger is narrower: six of the eight series have no rejected unit root in levels, so a level correlation between them and housing cannot be read as sensitivity, and §6 reports first differences for that reason. Neither reading is causal.

`sora_rates` returns a **positive** ADF statistic with p = 1.0, the least stationary result in the set. That is consistent with §3a's ramp; it does not by itself establish how the file was produced, and the ledger says so in the same field (`stationarity.soraNote`).

Caveat (`stationarity.caveat`): one specification only — constant, AIC lags, no trend term, no seasonal adjustment, no break test, monthly series unadjusted.

## 6. The article's correlation claims, re-measured (`associations`)

Targets (`associations.targetDefinition`): **HDB resale median psf** and **HDB resale transaction count** per month, measured from `unified_dataset` and aggregated to the macro series' own frequency (monthly series: the month; quarterly series: the calendar quarter). Housing side bounded at 2026-10 in every row.

`designation` is a ledger field: `audit-only` marks a series the fallback screen flagged, whose figures exist only to quantify the cost of excluding it. The three autocorrelation columns are the macro side, the housing side and their product — the product is what the effective n uses.

| Series         | Designation    | Window            | n (levels) | ρ macro | ρ housing | ρ product | Effective n | Levels: r vs psf | Unadjusted 95% CI | Serial-adjusted 95% CI | Δ: r vs Δpsf | Δ n | Δ effective n | Δ: r vs Δvolume |
| -------------- | -------------- | ----------------- | ---------: | ------: | --------: | --------: | ----------: | ---------------: | ----------------- | ---------------------- | -----------: | --: | ------------: | --------------: |
| `bank_rates`   | measured       | 2005-10 → 2026-09 |        252 |  0.9953 |    0.9992 |    0.9945 |         4.0 |          +0.1014 | −0.0224 → 0.2222  | −0.9525 → 0.9681       |      −0.0198 | 251 |         248.3 |         +0.0668 |
| `sora_rates`   | **audit-only** | 2021-01 → 2025-12 |         60 |  0.9777 |    0.9963 |    0.9740 |         4.0 |          +0.9422 | +0.9047 → +0.9652 | −0.2002 → 0.9988       |      +0.0646 |  59 |          53.5 |         +0.3285 |
| `cpi`          | measured       | 1990-01 → 2026-09 |        441 |  0.9997 |    0.9996 |    0.9993 |         4.0 |          +0.9713 | +0.9655 → +0.9762 | +0.1543 → +0.9994      |      +0.1496 | 440 |         440.0 |         −0.1771 |
| `gdp`          | measured       | 1990Q1 → 2026Q2   |        146 |  0.7380 |    0.9984 |    0.7368 |        22.1 |          −0.2636 | −0.4086 → −0.1057 | −0.6167 → +0.1777      |      +0.1174 | 145 |         137.0 |         +0.0777 |
| `hdb_rpi`      | measured       | 1990Q1 → 2026Q3   |        147 |  0.9984 |    0.9984 |    0.9968 |         4.0 |          +0.9991 | +0.9987 → +0.9993 | +0.9535 → +1.0000      |      +0.9236 | 146 |          32.8 |         −0.0750 |
| `unemployment` | measured       | 1992Q1 → 2026Q3   |        139 |  0.4564 |    0.9980 |    0.4555 |        52.0 |          −0.1860 | −0.3419 → −0.0201 | −0.4368 → +0.0915      |      −0.0539 | 138 |         138.0 |         +0.0480 |
| `ura_ppi`      | measured       | 1990Q1 → 2026Q3   |        147 |  0.9957 |    0.9984 |    0.9941 |         4.0 |          +0.9697 | +0.9583 → +0.9781 | +0.1271 → +0.9994      |      +0.4965 | 146 |          46.0 |         −0.1013 |
| `wage_growth`  | **audit-only** | 2001Q1 → 2025Q4   |        100 |  0.7539 |    0.9982 |    0.7525 |        14.1 |          +0.3382 | +0.1519 → +0.5013 | −0.2344 → +0.7366      |      +0.1402 |  99 |          99.0 |         −0.0739 |

Per-series Spearman values, difference-level intervals and the full contrast blocks are in the ledger (`associations.series.<name>`).

**The intervals, stated honestly** (`associations.intervalCaveat`): a Fisher-z interval assumes independent observations, which time-series observations are not. The unadjusted column is therefore an **optimistic floor** on uncertainty, not a 95% claim. The serial-adjusted column recomputes the same interval at an AR(1) effective n = n(1−ρ*xρ_y)/(1+ρ_xρ_y) — the **product**, because a correlation between two series inherits dependence from both. An earlier version of the producer used the macro side alone, which mis-scales the interval in both directions: it reported an effective n of 34.7 for the `bank_rates` difference pair where the paired form gives **248.3** (ρ macro 0.7574 × ρ housing 0.0071), narrowing that interval from −0.3507 → 0.3155 to −0.1440 → 0.1050. The effective n is clamped to a floor of 4 because the Fisher transform needs it, and **the floor binds for the five level pairs whose housing side is itself near-integrated** (`bank_rates`, `cpi`, `hdb_rpi`, `ura_ppi`, `sora_rates` — ρ housing 0.996–0.9996). Those adjusted level intervals span most of [−1, 1] and should be read as \_this pair carries almost no independent observations*: that is the finding, not a defect in it, and it is why the level column is decorative while the difference column is the one to read.

Reading rules (`associations.readingRules`), binding on the edition:

1. **Level figures are what the legacy article read.** Two trending series correlate by construction. The clearest demonstration is `hdb_rpi` at **+0.9991** in levels — a price index against a price level, which is a definition, not a finding. `cpi` at +0.9713 and `ura_ppi` at +0.9697 are the same artefact.
2. **First-difference figures are the defensible statistic.** They are reported with n and both interval variants.
3. **A series designated `audit-only` carries no empirical claim.**
4. **No coefficient is a causal effect and none is a forecast.**

What the differences show: nothing demonstrates the article's qualitative labels. The largest difference-correlation is `ura_ppi` at **+0.4965** (n = 146, serial-adjusted CI +0.1726 → +0.7236) — another price index, and therefore the least interesting pair in the set. `cpi` is **+0.1496**, `gdp` **+0.1174**, `bank_rates` **−0.0198**, `unemployment` **−0.0539**. On the volume side no series exceeds ±0.18 in differences (`sora_rates` reaches +0.3285 and is audit-only). The article's "moderate negative" for SORA, "moderate positive" for GDP and "strong negative" for SORA-vs-volume are not reproducible at these numbers.

## 7. Returns, measured (`realReturns`)

| Measure                                             | Window            |               Years | Value                                         |
| --------------------------------------------------- | ----------------- | ------------------: | --------------------------------------------- |
| HDB median psf, nominal CAGR                        | 1990-01 → 2026-10 |               36.75 | **0.0624**                                    |
| HDB median psf, nominal: first → last               | —                 |                   — | 64.93 → 600.77 psf (989,865 HDB transactions) |
| HDB median psf, CPI-deflated CAGR                   | 1990-01 → 2026-09 |          **36.667** | **0.0433**                                    |
| HDB resale price index, nominal CAGR                | 1990Q1 → 2026Q3   | 36.5 (147 quarters) | **0.0598**                                    |
| HDB resale price index: first → last                | —                 |                   — | 24.3 → 202.5                                  |
| Article window, HDB median psf nominal CAGR         | 2021-01 → 2026-10 |           70 months | **0.0601**                                    |
| Article window, HDB resale price index nominal CAGR | 2021Q1 → 2026Q3   |         23 quarters | **0.0664**                                    |

The real return is deflated over **its own** window: the CPI series ends at 2026-09, one month before the transaction cutoff, so the deflated CAGR runs 36.667 years, not the nominal 36.75 — using the nominal denominator here would overstate the real figure.

Two disclosures this table needs (`realReturns.hdbMedianPsf.compositionCaveat`):

- **The median is not a constant-quality index.** The mix of towns, flat types and lease bands behind the monthly median changes across 36.75 years, so the figure describes the median's path; the `hdb_rpi` row is the constant-quality alternative and covers a different window.
- **The article's `~4-5%` HDB band is re-measured, not confirmed.** Over the article's own 2021-2026 window the two available series give **6.01%** (median psf) and **6.64%** (price index) — above the quoted band, not inside it. The three condo rows of that table (`~5-6%`, `~3-5%`, `~2-4%`) are **withdrawn**: no segment-level price index exists in this checkout (`realReturns.segmentsNotReproducible`).

## 8. What the gate asks for and this checkout cannot supply (`notMeasurable`)

| Gate clause                                                              | Status          | Reason                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------ | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Document release lag                                                     | `notMeasurable` | no release timestamp or extraction stamp on any series                                                                                                                                                                                           |
| Document revisions                                                       | `notMeasurable` | one file per series, no vintage snapshots; published-vs-revised cannot be compared                                                                                                                                                               |
| No present-day timing regime claims from unknown vintages — policy dates | `notMeasurable` | the article's five-row policy table rests on `housing_policy_dates.parquet`, absent here; its dates also disagree with the causal-inference article's, and neither has an artefact                                                               |
| No regime claims from unknown vintages                                   | `notFitted`     | the three-regime table is analyst-chosen period boundaries; no break-test implementation exists on the shipping Python surface and none was run                                                                                                  |
| Exclude fallback series from empirical claims — segment CAGR             | `notMeasurable` | no segment-level price index; the private source starts 2021-01 in the shipped frame                                                                                                                                                             |
| Document uncertainty — lag order of any indicator                        | `notMeasurable` | no cross-correlation, lead-lag or lag-order implementation on the shipping Python surface, and this study ran none; every association here is same-period                                                                                        |
| Any affordability or financing claim                                     | `notMeasurable` | an export-time **static** affordability lookup exists (`scripts/export_app_data.py`: fixed 20%-down / 3.5% / 25-year payment, price-to-income and mortgage-to-income bands); no rate sensitivity, borrower eligibility or TDSR assessment exists |

The last two dispositions rest on `methodArtefacts`, a measured scan of the shipping Python surface (**66** `.py` files) that records **every** matched file and its count rather than asserting silence. It scans for **text, not executed code**, and it **excludes itself** — its own pattern literals and docstrings would otherwise register as hits, which on the first attempt they did, making both absence claims false. With the scanner excluded: `lagOrCrossCorrelation` **0 files / 0 matches**, `structuralBreak` **0 / 0**, `affordabilityModel` **7 files / 49 matches** (`scripts/export_app_data.py`, `scripts/generate_catalog.py`, `src/egg_n_bacon_housing/components/metrics.py`, the RS10 producer among them) — plumbing, not a model, and the matched list is in the ledger so that judgement can be checked.

## 9. Every legacy claim, disposed (`legacyClaims`, 35 entries)

| #   | Legacy phrase (verbatim)                                                                              | Status      | Ledger key                               |
| --- | ----------------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------- |
| C1  | Interest rates (SORA) have the most direct impact on affordability                                    | withdrawn   | `associations.series.bank_rates`         |
| C2  | This confirms that interest rates are the most actionable macro indicator for housing decisions.      | withdrawn   | `associations.readingRules`              |
| C3  | 3.5-4.0%                                                                                              | re-measured | `fallbackAudit.soraBandCheck.2023`       |
| C4  | The macro data collection relies on SingStat API with fallback to generated data when API calls fail. | re-measured | `fallbackAudit.shortSeriesVerdict`       |
| C5  | GDP growth is a leading indicator for transaction volume more than price level                        | withdrawn   | `associations.series.gdp`                |
| C6  | Unemployment is a lagging indicator that confirms weakness rather than predicting it.                 | withdrawn   | `associations.series.unemployment`       |
| C7  | are identifiable in the 2021-2026 data: expansion, tightening, stabilization                          | withdrawn   | `notMeasurable.regimes`                  |
| C8  | is approximately 2% across all segments                                                               | withdrawn   | `realReturns.segmentsNotReproducible`    |
| C9  | 60 monthly observations (2021-2025)                                                                   | re-measured | `seriesInventory.sora_rates`             |
| C10 | 5 major policy events (2021-2023)                                                                     | withdrawn   | `notMeasurable.policyDates`              |
| C11 | Visual and statistical identification of distinct macro periods                                       | withdrawn   | `notMeasurable.regimes`                  |
| C12 | the 5-year macro data window covers only one full rate cycle, limiting generalizability               | withdrawn   | `seriesInventory.bank_rates`             |
| C13 | 0.1-0.2%                                                                                              | re-measured | `fallbackAudit.soraBandCheck.2021H1`     |
| C14 | 2.5-3.5%                                                                                              | re-measured | `fallbackAudit.soraBandCheck.2022H2`     |
| C15 | 3.0-3.5%                                                                                              | re-measured | `fallbackAudit.soraBandCheck.2024to2025` |
| C16 | 21 quarterly observations (2021-2026)                                                                 | withdrawn   | `seriesInventory`                        |
| C17 | 1-2 quarters                                                                                          | withdrawn   | `notMeasurable.regimes`                  |
| C18 | rates +1%                                                                                             | withdrawn   | `notMeasurable.regimes`                  |
| C19 | 2021 - mid-2022                                                                                       | withdrawn   | `notMeasurable.regimes`                  |
| C20 | Mid-2022 - 2023                                                                                       | withdrawn   | `notMeasurable.regimes`                  |
| C21 | ~4-5%                                                                                                 | re-measured | `realReturns.articleWindow2021To2026`    |
| C22 | ~5-6%                                                                                                 | withdrawn   | `realReturns.segmentsNotReproducible`    |
| C23 | ~3-5%                                                                                                 | withdrawn   | `realReturns.segmentsNotReproducible`    |
| C24 | ~2-4%                                                                                                 | withdrawn   | `realReturns.segmentsNotReproducible`    |
| C25 | 2021-2026 (macro data), 2017-2026 (housing data)                                                      | withdrawn   | `seriesInventory`                        |
| C26 | Immediate to 1 quarter                                                                                | withdrawn   | `notMeasurable.regimes`                  |
| C27 | A 1% rate difference on a large loan                                                                  | withdrawn   | `notMeasurable.regimes`                  |
| C28 | Dec 2021                                                                                              | withdrawn   | `notMeasurable.policyDates`              |
| C29 | Sep 2022                                                                                              | withdrawn   | `notMeasurable.policyDates`              |
| C30 | Apr 2023                                                                                              | withdrawn   | `notMeasurable.policyDates`              |
| C31 | Dec 2023                                                                                              | withdrawn   | `notMeasurable.policyDates`              |
| C32 | data/04_platinum/housing_unified.parquet                                                              | withdrawn   | `inputs`                                 |
| C33 | data/raw_data/macro/                                                                                  | withdrawn   | `inputs`                                 |
| C34 | 2024-2026                                                                                             | withdrawn   | `notMeasurable.regimes`                  |
| C35 | 1-quarter lag with price trends                                                                       | withdrawn   | `notMeasurable.regimes`                  |

All 35 phrases are verified character-for-character against the frozen legacy file (`legacyQuoteCheck`); a drifting quote fails `--check`. Of the 35, **seven are re-measured and twenty-eight are withdrawn**. Re-measured does not mean confirmed: C14, C15 and C21 are re-measured onto numbers that **do not match** their claim, and C32/C33 record that both source paths the legacy appendix names are absent from this checkout — the shipped equivalents are sha-pinned in `inputs` instead.

## 10. What this pack does not establish

- **No causal effect, no sensitivity coefficient, no affordability model.** The word "impact" does not appear in this pack's findings, and correlations here are associations at a stated frequency.
- **No regime, timing or policy-effect claim.** The three regimes, the five policy dates and the lag orders are all withdrawn as unmeasurable (§8).
- **No claim resting on `sora_rates` or `wage_growth`.** Both are `audit-only`; they appear to show what exclusion costs.
- **No release-lag or revision statement.** The provenance does not exist in the checkout; the ledger records the absence rather than estimating it.
- **No constant-quality return for the condo segments.** Only the HDB rows of the legacy CAGR table are measurable.
- **No provenance certification of any series.** `no-fallback-signature-detected` is the absence of one screen's positive result. Every series lacks a release stamp, and this pack does not claim otherwise.
- **No pre-registration credential.** One specification was measured and only that one; specification search cannot be ruled out.

## 11. Sign-off record

| Role          | Signatory         | Attests | Recorded |
| ------------- | ----------------- | ------- | -------- |
| source/cutoff | — not yet given — |         |          |
| scientific    | — not yet given — |         |          |
| publication   | — not yet given — |         |          |

Sign-offs belong to the owner and an independent reviewer, never to the preparer (`repo-agent/session-2026-11-18`), and they attach to the **ledger** sha256 `8ddf8b2d609d658e0f178dabecb41ae233adc6b37699e4afcaceec696312839c`. A later re-run that changes a byte changes that hash and voids any signature recorded against it — re-run, diff, and re-attest only. The registry entry stays `evidenceStatus: "historical"`, `editorialStatus: "draft"`, `editionSha256: null`, `signoffs: []` until those signatures exist.

## 12. Review history and the fix pass

Round 1 (independent reviewer, `openai-codex/gpt-6-luna`, effort xhigh) returned **FAIL** on ledger sha256 `d84876b5…`, naming seven defects. All seven were fixed in the producer and the ledger re-measured; the round-1 attestation is void in the D12 trap-#4 sense, because it pinned bytes that no longer exist.

Round 2 returned **FAIL** on `8ddf8b2d…`, naming three more. Two were genuine measurement defects in material added during the round-1 fix:

| #   | Round-2 defect                                                                                                                 | Fix                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 8   | `soraBandCheck.2024to2026Aug` measured a 32-month span, so it answered a different question than the article's 2024-2025 claim | the article's own 24-month window is now the measured key (`2024to2025`, mean 2.7390); the 32-month span is kept separately and labelled context                     |
| 9   | effective n used only the macro side's lag-1 autocorrelation                                                                   | paired AR(1) form n(1−ρ_xρ_y)/(1+ρ_xρ_y); the `bank_rates` difference pair moved from n_eff 34.7 to 248.3 and its interval from −0.3507 → 0.3155 to −0.1440 → 0.1050 |
| 10  | claim inventory still omitted quantitative claims                                                                              | nine claims added (C25-C33); **33/33** verified verbatim                                                                                                             |

Numbers that moved in round 2: the 2024-2025 band mean (wrong window → correct window) and every serial-adjusted interval (wrong formula → paired formula). Both moved because the first version was wrong, which is the only acceptable reason.

Round 3 returned **FAIL** on `ffb8d33e…`, naming two defects — one of them a leftover from the round-2 fix: the ledger's `associations.intervalCaveat` still described the _superseded_ single-series formula while the code and the pack had moved to the paired one, and its blanket claim that serial correlation "widens" an interval was too strong, since a negative product raises the effective n (clamped at n); and two more legacy phrases were still missing (`2024-2026`, the stabilization regime's window, and `1-quarter lag with price trends`). Both fixed: the caveat now states the paired formula and that the adjustment moves in whichever direction the dependence implies, and the claim inventory is 35 entries, 35/35 verbatim.

| #   | Defect                                                                  | Fix                                                                                                                                                                                     |
| --- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `bank_rates`' 213 null values hidden by dropping nulls before inventory | `load_raw_series` keeps nulls; inventory now separates `fileRows` / `nonNullValueRows` / `nullValueRows` / `zeroValueRows` with the null span, and states the three-state semantics     |
| 2   | The exclusion was asserted, not enforced                                | per-series `designation: audit-only` for both flagged series, plus a stated reason; `wage_growth`'s non-independence now recorded as `distinctMacroValuesInWindow` = 19 against n = 100 |
| 3   | ADF interpretation claimed failure-to-reject proves non-stationarity    | rewritten to state low power explicitly and narrow the operational consequence; `sora_rates` note added                                                                                 |
| 4   | Real CAGR reused the nominal window's 36.75 years                       | deflated CAGR now computed over its own 36.667-year window → **0.0433** (was 0.0432); composition caveat added                                                                          |
| 5   | Fisher intervals ignored serial dependence                              | lag-1 ρ, AR(1) effective n and a serial-adjusted interval per pair, with the binding-floor disclosure                                                                                   |
| 6   | Claim inventory omitted claims                                          | 12 claims added (C13-C24); 24/24 verified verbatim                                                                                                                                      |
| 7   | Per-series caveat contradicted its own label                            | the caveat is now label-specific, one text per screen result                                                                                                                            |

Numbers that moved in this pass: the deflated CAGR (a measurement correction, defect 4) and the raw/non-null row counts for `bank_rates` (a reporting correction, defect 1). Every other measured value is unchanged, and the ledger diff is structural elsewhere.

Rounds 4 and 5 added four more, and the pattern across them is worth recording: **every one was a prose field or a claim reference, never a measurement.**

| Round          | Defect                                                                                                                                                            | Fix                                                                                                                                              |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 4              | the caveat described the clamp wrongly — a negative product clamped at _n_ leaves the interval unchanged, not narrower                                            | caveat now states the clamp behaviour and names the `unemployment` case (product −0.4653, raw ≈378 against 138 rows → 138.0, interval unchanged) |
| 4              | "the adjusted interval spans most of [−1, 1]" was false for `hdb_rpi` (0.9535→1.0000) and `cpi` (0.1543→0.9994)                                                   | blanket claim removed; the caveat now says the floor means ≈4 independent observations and that width then depends on how near r is to ±1        |
| 4              | `C35`'s key did not substantiate a lag disposition                                                                                                                | new `notMeasurable.lagTesting`; `C17`/`C26`/`C5`/`C6` repointed, `C18`/`C27` to `notMeasurable.affordabilityModel`                               |
| 5 (self-found) | those three claim notes asserted an absence nothing had measured — and the first `methodArtefacts` scan was self-contradicting, counting its own literals as hits | `methodArtefacts` added, scanner excluded, and both reasons rewritten to describe the matches found instead of asserting silence                 |

The sweep that found the last one is the reusable part: enumerate every prose string in the ledger, flag blanket quantifiers, then check every `legacyClaims[].ledgerKey` actually resolves to a field that supports its disposition. Three of the 35 keys were wrong and no measurement was.
