# RF03 report — source restoration and coverage reconciliation

- **Date:** 2026-11-13
- **Status:** Sources restored, pipeline green, candidate release built. **Nothing published.** Private/EC 2026 scopes remain **withheld** pending one open reconciliation item; HDB passes.
- **Grants used:** R2 download (manual + geocache), pipeline refresh, candidate export to `/tmp`. Deployment **not** authorised and not attempted.
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §5.6 · [handoffs](../plans/2026-11-12-reporting-refresh-handoffs.md) RF03
- **Decisions:** D02 (cutoff 2026-10), D10 (per-operation grants), D11 (coverage disposition) — [ledger](../plans/2026-11-12-reporting-refresh-decisions.md)

## 1. Restoration

| Step                                                                                | Result                                                                                                                                                   |
| ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `00_sync_data.py --download --only manual`                                          | 51 files (124 MB) of CSV/GeoJSON                                                                                                                         |
| `00_sync_data.py --download --only geocache`                                        | 18,032 parquet files (140 MB)                                                                                                                            |
| `00_sync_data.py --verify`                                                          | **18,084 OK, 0 missing locally, 0 missing in R2, 0 size mismatches**                                                                                     |
| `main.py --stage ingest --refresh`                                                  | 24 source nodes; HDB 990,860 · condo 245,655 · rental 215,469 · 23 reference layers                                                                      |
| `main.py --stage all`                                                               | 1,236,310 × 97 `unified_dataset`; `pa_monthly_metrics` 13,236; `planning_area_360` 44; `town_360` 28; `block_profile` 10,031; `appreciation_hotspots` 20 |
| `export_app_data.py --last-complete-month 2026-10 --output-dir /tmp/rf03-candidate` | 8 files, generation `9605fceca35c27e6`, 7 assets + release manifest                                                                                      |

Operational note: the first `--stage all` run was killed at the 55-minute tool budget while `condo_validated` was running (3,214 s in that node alone). The rerun completed in ~4 minutes because the validation-layer cache was warm. A cold refresh therefore costs roughly an hour, almost all of it in private-residential validation.

No credentials were read, printed or changed. `.env` keys (`R2_*`, `URA_API_ACCESS_KEY`, `ONEMAP_*`) were already present and are used by the scripts themselves.

## 2. Candidate versus published release

Candidate `9605fceca35c27e6` (exported 2026-11-13, cutoff 2026-10) vs published `0e1013ee485f` (2026-11-03). 442 monthly trend rows compared.

- **193 changed cells**, of which 164 are volumes.
- Pre-2026: 150 volume cells moved, **median absolute delta 1 row**. Two explainable revision clusters:
  - `2021-10`/`2021-11` — condo −66 / **−611**, EC −8 / **−71**. This is the edge of URA's rolling five-year window: the boundary advanced past those days, so rows fell out.
  - Everything else ≤ 4 rows (HDB 1995-11 3,163 → 3,159, etc.).
- 2026: eleven months moved by 1–19 rows, plus **2026-10**: condo 1,303 → **2,392**, EC 116 → **154**, HDB 2,176 → **2,173**. The published release was exported three days after October closed, so its newest month was still filling in.

So: history is reproducible to within a rounding of one transaction, with one documented window-edge revision and one completion of the latest month. This is not byte-identical (plan §5.1 allows a visible revision, not a silent one).

## 3. Open reconciliation item (blocks private/EC promotion)

The audit's Jan–Oct count gap **reproduces on freshly fetched data**, so it is not a stale-export artifact:

| Label       | Jan–Oct 2025 | Jan–Oct 2026 | Δ         |
| ----------- | ------------ | ------------ | --------- |
| HDB         | 21,402       | 21,801       | **+1.9%** |
| EC          | 5,560        | 2,353        | −57.7%    |
| Condominium | 42,413       | 18,477       | −56.4%    |
| All         | 69,375       | 42,631       | −38.5%    |

**Correction (2026-11-13, after the v2 pack was built):** an earlier revision of this table put 25,084 / 6,209 / 47,504 in the 2025 column. Those are **full-year 2025** totals, not January–October. Comparing ten months against twelve overstated the HDB change as −13.1%; the like-for-like figure is **+1.9%**, which matches the published release and the audit. The EC/condominium gap survives the correction (−57.7% / −56.4%), so that item stays open.

What the checks ruled out:

- **Duplicates:** 4,479 duplicate `(project, date, price, area, units)` rows in 245,655 (1.8%), spread evenly 2021–2026; zero rows duplicate on `(project, date, price, area, floor_level)`; zero fully identical rows.
- **Aggregation grain:** `number_of_units` is 1 for 245,578 rows, 2–4 for 40; units ≈ rows.
- **Sub-sales, sale-type mix, project spread:** 2025 has more New Sale rows (20,924) than 2024 (13,397) and 2026 (7,301), but Resale also halves, and unique projects per year are stable (~2,100–2,230).

What remains unexplained: whether 2025 private volume is genuinely ~2.5× 2026 (a launch-cycle peak — the top project-months are real launches: Springleaf Residence 1,436 in 2025-08, Skye at Holland 1,196 and Zyon Grand 1,130 in 2025-10) or whether the private/EC grain still over-counts some rows. Resolving it needs the URA source definition and an independent monthly check against published URA caveat counts — that is a data-owner task, not something a label change can settle.

**Disposition under D11:** HDB = _publish current_ (like-for-like +1.9%; full-year 2025 count identical at 25,084; monthly deltas ≤ 3; no joint-scope ambiguity). EC and Condominium 2026 = _limited historical/diagnostic display_ — raw counts may be shown with their dates, but no growth headline, no ranked comparison and no activity colour until this is settled.

## 4. Candidate asset hashes

| Asset                           | Bytes  | sha256          |
| ------------------------------- | ------ | --------------- |
| `dashboard_overview.json.gz`    | 716    | `c7cf56287202…` |
| `dashboard_trends.json.gz`      | 5,756  | `3e54547387e9…` |
| `dashboard_segments.json.gz`    | 6,093  | `c689286ff629…` |
| `dashboard_leaderboard.json.gz` | 4,757  | `2a58c7ff8683…` |
| `map_metrics.json.gz`           | 11,398 | `febb736c1537…` |
| `hotspots.json.gz`              | 1,086  | `6896116f71e6…` |
| `amenity_summary.json.gz`       | 1,782  | `8cf9e3a32c88…` |

Inputs: `unified_dataset` `39d234f703c9…` (1,236,310 rows), `pa_monthly_metrics` `6d4ed626ef08…` (13,236 rows). Published v1 assets are untouched: `verify_reporting_baseline.py --assets` still passes for all 72 pinned files.

## 5. What this unblocks

- **RF04** can now build v2 periods and payloads from a real release candidate, with HDB publishable and private/EC scoped to diagnostic display.
- **RF05/RF09** can implement against the candidate, with the EC/condo caveat surfaced rather than hidden.
- **RF11** catalog work must use this candidate's inputs, not the previous snapshot.

## 6. Not done

- No publication, no deployment, no research reruns (RS01–RS15 stay archived).
- No catalog regeneration (a `--help` probe of `generate_catalog.py` rewrote the catalog from an empty pipeline and was reverted; RF11 owns that step).
- The candidate lives in `/tmp/rf03-candidate`; it is disposable evidence, not a release.
