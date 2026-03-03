# Data Quality Monitoring Handoff

**Date:** 2026-03-04
**Status:** Ready for next agent
**Scope:** Follow-up work after data quality framework verification

## Current State

The data quality monitoring framework is now active for:

- `save_parquet()` writes via `@monitor_data_quality`
- non-`save_parquet()` DataFrame writes via `record_dataframe_quality()`
- `L0` `raw_*` datasets
- `L0_macro` `raw_macro_*` datasets
- `L1`, `L2`, `L3`, and `L5` datasets that use `save_parquet()`
- `L3_housing_unified`

Verified on 2026-03-03 and 2026-03-04:

- targeted data quality tests pass
- `uv run ruff check` passes on the modified data-quality files
- `data/quality_metrics.db` now records snapshots for:
  - `raw_macro_sora_rates_monthly`
  - `raw_macro_singapore_cpi_monthly`
  - `raw_macro_sgdp_quarterly`
  - `raw_macro_unemployment_rate_monthly`
  - `raw_macro_property_price_index_quarterly`
  - `raw_macro_housing_policy_dates`
  - `L3_housing_unified`

Primary implementation files already updated:

- [scripts/core/data_quality.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/data_quality.py)
- [scripts/utils/data_quality_report.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/utils/data_quality_report.py)
- [scripts/data/fetch_macro_data.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/data/fetch_macro_data.py)
- [scripts/core/stages/L3_export.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/stages/L3_export.py)
- [tests/unit/test_data_quality.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/tests/unit/test_data_quality.py)
- [tests/unit/test_data_quality_report.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/tests/unit/test_data_quality_report.py)
- [tests/integration/test_data_quality_integration.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/tests/integration/test_data_quality_integration.py)
- [tests/integration/test_data_quality_e2e.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/tests/integration/test_data_quality_e2e.py)

## Remaining Opportunities

### 1. Reduce duplicate-warning noise for intentionally denormalized datasets

Current problem:

- the quality report flags any dataset with `duplicate_count > 0` as warning
- some outputs are expected to contain many duplicate rows because they are expanded/joined tables

Examples seen in the report:

- `L3_property_nearby_facilities`
- `L3_private_property_facilities`
- `L3_property`
- `L3_property_transactions_sales`
- `L3_property_listing_sales`
- `L2_housing_per_type_amenity_features`

Recommended approach:

- add dataset-specific duplicate policies in [scripts/core/data_quality.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/data_quality.py)
- keep the raw metric, but suppress or downgrade warnings for known-expanded datasets
- avoid hiding real anomalies for datasets where duplicates are supposed to be near zero

Suggested implementation:

1. Add a small config map, for example:
   - `STRICT` for datasets that should not duplicate
   - `ALLOW_ANY` for intentionally denormalized outputs
   - `ALLOW_THRESHOLD` for datasets that tolerate some duplicates
2. Use that policy in `_log_quality_summary()` so status is not automatically warning just because duplicates exist.
3. Optionally use the same policy in anomaly checks if duplicate-based anomalies are later added.

Acceptance criteria:

- the report still shows duplicate counts
- expected duplicate-heavy datasets no longer flood the summary with low-signal warnings
- genuinely duplicate-sensitive datasets still warn when duplicates appear

### 2. Bring L3 precomputed tables under monitoring

Current problem:

The main unified dataset is monitored, but the precomputed tables in [scripts/core/stages/L3_export.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/stages/L3_export.py) still write directly with `to_parquet()` in `save_precomputed_tables()`.

Tables currently bypassing the framework:

- `market_summary`
- `tier_thresholds_evolution`
- `planning_area_metrics`
- `lease_decay_stats`
- `rental_yield_top_combos`

Recommended approach:

- convert those writes to monitored saves
- preserve current output paths under `data/pipeline/L3/`

Suggested implementation:

1. Import and use `save_parquet()` inside `save_precomputed_tables()`.
2. Map each file to a stable dataset name:
   - `L3_market_summary`
   - `L3_tier_thresholds_evolution`
   - `L3_planning_area_metrics`
   - `L3_lease_decay_stats`
   - `L3_rental_yield_top_combos`
3. Keep the current file names and locations unchanged.

Acceptance criteria:

- rerunning `uv run python scripts/run_pipeline.py --stage L3` creates new `run_snapshots` rows for all five tables
- the files still exist at their current paths in `data/pipeline/L3/`

### 3. Add a minimum baseline sample count before anomaly alerts

Current problem:

- anomaly thresholds start evaluating immediately after the first historical records exist
- early-run baselines are noisy and can produce low-confidence alerts

Recommended approach:

- require a minimum baseline size before anomaly detection becomes active
- keep recording snapshots and updating baselines from run 1

Suggested implementation:

1. Add a constant in [scripts/core/data_quality.py](/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/data_quality.py), for example `MIN_BASELINE_SAMPLES = 3`.
2. In `check_anomaly()`, return no anomalies until `baseline.sample_count >= MIN_BASELINE_SAMPLES`.
3. Keep existing row-count/null-percentage logic unchanged after the threshold is met.
4. Update the guide in [docs/guides/data-quality-monitoring.md](/Users/minghao/Desktop/personal/egg-n-bacon-housing/docs/guides/data-quality-monitoring.md) to document the warm-up behavior.

Acceptance criteria:

- first and second runs build history silently
- alerts only begin once sufficient history exists
- tests cover the warm-up threshold

## Recommended Execution Order

1. Implement duplicate-warning policy first.
2. Instrument L3 precomputed tables.
3. Add the minimum baseline sample threshold.
4. Update documentation last.

This order reduces report noise early, then expands coverage, then refines anomaly sensitivity.

## Verification Commands

Run after each change set:

```bash
uv run ruff check \
  scripts/core/data_quality.py \
  scripts/core/stages/L3_export.py \
  scripts/utils/data_quality_report.py \
  tests/unit/test_data_quality.py \
  tests/unit/test_data_quality_report.py
```

```bash
uv run pytest \
  tests/unit/test_data_quality.py \
  tests/unit/test_data_quality_report.py \
  tests/integration/test_data_quality_integration.py \
  tests/integration/test_data_quality_e2e.py \
  -v \
  --override-ini addopts=''
```

Focused pipeline checks:

```bash
uv run python scripts/run_pipeline.py --stage L3
uv run python scripts/utils/data_quality_report.py --summary --limit 20
```

Useful DB inspection:

```bash
uv run python -c "import sqlite3; conn=sqlite3.connect('data/quality_metrics.db'); print(conn.execute('SELECT dataset_name, stage, timestamp FROM run_snapshots ORDER BY id DESC LIMIT 20').fetchall()); conn.close()"
```

## Known Caveats

- The repo may already be in a dirty git state. Do not revert unrelated user changes.
- `L0` and `L0_macro` may hit external API instability or fall back to mock data. That is separate from data-quality instrumentation.
- `L3_export` currently logs a school-feature warning (`Failed to add school features: 2`) and continues. That warning is unrelated to the data-quality framework.
- The current summary output still treats any duplicate count as a warning. This is expected until opportunity 1 is implemented.

## Definition Of Done For This Handoff

The handoff is complete when the next agent delivers:

- lower-noise quality summaries for expected duplicate-heavy datasets
- monitored snapshots for all L3 precomputed tables
- anomaly detection that waits for a minimum history window
- matching test coverage and updated docs
