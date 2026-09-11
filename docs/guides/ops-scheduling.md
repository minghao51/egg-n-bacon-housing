# Ops Guide — Local Scheduled Refresh of Rolling Sources

Two bronze datasets serve **rolling windows**: their APIs only return recent
data, so a bronze cache that is never invalidated freezes at whatever window
existed when it was first fetched.

- `raw_condo_transactions` — the URA API serves a rolling ~5-year window.
- `raw_hdb_resale` — the data.gov.sg API serves Jan 2017+ only.

`scripts/40_refresh_rolling.py` refreshes exactly these sources in one command
and optionally reruns the pipeline. This is **local scheduling** (DECISION #6):
cron/launchd on a machine that already has the repo and `uv` set up
— no GitHub Actions, no CI secrets.

## Usage

All commands run from the repo root. API-backed refreshes read credentials from
the local ignored `.env` or from environment variables (URA key optional;
OneMap credentials only needed on geocode cache misses).

```bash
# Refresh both rolling sources (clears their bronze parquets + the DAG cache)
uv run python scripts/40_refresh_rolling.py

# Idempotent scheduled target: refresh only what is past its staleness
# threshold, then rerun the pipeline. No-op when nothing is stale.
uv run python scripts/40_refresh_rolling.py --stale-only --run

# Inspect before acting: lists matching bronze files and manifest ages, deletes nothing
uv run python scripts/40_refresh_rolling.py --dry-run
uv run python scripts/40_refresh_rolling.py --dry-run --stale-only

# Nuclear: refresh_all — ALL bronze parquets + Hamilton DAG cache + API cache.
# Every source is re-fetched on the next run; use manually, do not schedule.
uv run python scripts/40_refresh_rolling.py --all
```

Flags: `--stale-only` and `--all` are mutually exclusive; `--run` composes with
both; `--log-level DEBUG` turns up logging. Exit codes: `0` success, `1`
refresh/pipeline failure, `2` CLI usage error. With `--stale-only --run`, the
pipeline rerun is skipped when nothing was stale, so a weekly job only spends
time when the data actually rolled over.

The pipeline rerun uses the supported entrypoints (`run_pipeline(stage="all")`,
same as `main.py`) in-process — the script never shells out.

## Cron recipe (Linux/macOS)

Weekly refresh every Monday 07:00 local time:

```cron
0 7 * * 1 cd /path/to/egg-n-bacon-housing && uv run python scripts/40_refresh_rolling.py --stale-only --run >> data/logs/refresh.log 2>&1
```

- Use `crontab -e` to install; keep the absolute repo path in the `cd`.
- `uv` must be on cron's `PATH` — if it is installed via a version manager, use
  its absolute path. The ignored root `.env` is loaded because the job changes
  to the repository directory first.
- Log redirection (`>> data/logs/refresh.log 2>&1`) keeps a run history;
  create `data/logs/` first. Rotate or trim the file occasionally.
- Monthly full-window rebuild instead: replace `--stale-only` with nothing
  (refreshes both rolling sources unconditionally). Avoid scheduling `--all`.

## launchd recipe (macOS)

Save as `~/Library/LaunchAgents/com.eggnbacon.housing-refresh.plist`, then run
`launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.eggnbacon.housing-refresh.plist`
(use `~/Library/LaunchAgents` with absolute home path inside the plist).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.eggnbacon.housing-refresh</string>
  <key>WorkingDirectory</key>
  <string>/Users/you/path/to/egg-n-bacon-housing</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/you/.local/bin/uv</string>
    <string>run</string>
    <string>python</string>
    <string>scripts/40_refresh_rolling.py</string>
    <string>--stale-only</string>
    <string>--run</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>7</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/you/path/to/egg-n-bacon-housing/data/logs/refresh.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/you/path/to/egg-n-bacon-housing/data/logs/refresh.err.log</string>
</dict>
</plist>
```

Adjust the `uv` absolute path (`command -v uv`) and `WorkingDirectory` to your
machine. The job loads the ignored root `.env` from that working directory;
alternatively add an `EnvironmentVariables` dictionary to the plist. Verify with
`launchctl kickstart gui/$UID/com.eggnbacon.housing-refresh`, then check the
log files.

## Staleness thresholds (`STALE_WARN_DAYS`)

The single source of truth for which sources roll and when they count as stale
is `STALE_WARN_DAYS` in `src/egg_n_bacon_housing/utils/bronze.py`:

| Key (bronze parquet stem) | Threshold (days) | Source                          | Why it rolls                        |
| ------------------------- | ---------------- | ------------------------------- | ----------------------------------- |
| `raw_condo_transactions`  | 35               | URA API (+ manual CSV fallback) | API serves a rolling ~5-year window |
| `raw_hdb_resale`          | 35               | data.gov.sg API                 | API serves Jan 2017+ only           |

The same keys drive:

- `warn_if_stale` cache-hit warnings in the pipeline (WS10);
- the script's default refresh patterns and `--stale-only` selection
  (`tests/test_refresh_rolling.py` fails if the script ever hard-codes them);
- the refresh hint in each warning (`main.py --refresh <name>`).

### Adding a source

1. Add `"<bronze_parquet_stem>": <max_age_days>` to `STALE_WARN_DAYS` in
   `src/egg_n_bacon_housing/utils/bronze.py`. The key must be the parquet stem
   the ingestion node writes through `write_bronze_cache` (e.g. note that the
   HDB resale node is `raw_hdb_resale_transactions` but its parquet stem — and
   therefore the key — is `raw_hdb_resale`).
2. That is all for this script: patterns, `--stale-only`, and dry-run output
   derive from the constant at runtime. The staleness warnings pick it up too.
3. Update the table above and keep the drift tests green:
   `uv run pytest tests/test_bronze.py tests/test_refresh_rolling.py -q`.

Thresholds slightly above the source's natural cadence (e.g. 35 days for
monthly-ish data) keep `--stale-only` runs infrequent and idempotent.
