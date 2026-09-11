#!/usr/bin/env python3
"""Scheduled rolling-source refresh (WS18, local scheduling).

One-command refresh for the rolling-window bronze datasets (URA condo
transactions serve a rolling ~5-year window; the data.gov.sg HDB resale API
serves Jan 2017+ only) whose windows freeze unless periodically re-fetched,
plus an optional pipeline rerun so downstream layers pick up the new data.
See docs/guides/ops-scheduling.md for cron/launchd recipes.

Usage (URA key optional; OneMap credentials are only needed on geocode cache
misses; credentials come from the local ignored .env or process environment):

    uv run python scripts/40_refresh_rolling.py                # refresh both rolling sources
    uv run python scripts/40_refresh_rolling.py --stale-only --run   # idempotent cron target
    uv run python scripts/40_refresh_rolling.py --dry-run      # report without deleting
    uv run python scripts/40_refresh_rolling.py --all          # nuclear: refresh everything

Behavior:
- default: ``refresh_bronze`` for every rolling pattern, derived from the
  ``STALE_WARN_DAYS`` keys so the source list stays single-sourced in
  ``src/egg_n_bacon_housing/utils/bronze.py``.
- ``--stale-only``: consult ``bronze_manifest.json`` and refresh only the
  datasets already past their ``STALE_WARN_DAYS`` threshold. With ``--run``,
  the pipeline rerun is skipped when nothing was stale (idempotent no-op).
- ``--all``: full ``refresh_all`` — ALL bronze parquets + Hamilton DAG cache +
  API response cache. Nuclear: every source is re-fetched on the next run.
- ``--run``: rerun the pipeline afterwards via the supported entrypoint
  ``run_pipeline(stage="all")`` in-process (mirrors ``main.py``; no shell-out).
- ``--dry-run``: report what would be refreshed (matching bronze files,
  manifest ages) without deleting anything.

Exit codes: 0 success, 1 refresh/pipeline failure, 2 CLI usage error.
"""

import argparse
import fnmatch
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from egg_n_bacon_housing.config import Settings
from egg_n_bacon_housing.config import settings as app_settings
from egg_n_bacon_housing.pipeline import run_pipeline

# _load_manifest/_parse_fetched_at are the same manifest readers warn_if_stale
# uses, so --stale-only selection can never drift from the warnings the
# pipeline itself emits.
from egg_n_bacon_housing.utils.bronze import (  # noqa: E402
    STALE_WARN_DAYS,
    _load_manifest,
    _parse_fetched_at,
    refresh_all,
    refresh_bronze,
)
from egg_n_bacon_housing.utils.logging_config import LEVEL_MAP, get_logger, setup_logging

_SECONDS_PER_DAY = 86400.0

logger = get_logger(__name__)


def rolling_patterns() -> list[str]:
    """Bronze patterns for the rolling-window sources.

    Derived from ``STALE_WARN_DAYS`` keys (bronze parquet stems, which are
    valid ``clear_bronze`` globs) so the script and the staleness warnings
    always cover the same sources. Add a source by adding it to
    ``STALE_WARN_DAYS`` in ``src/egg_n_bacon_housing/utils/bronze.py`` — never
    by hard-coding a pattern here.
    """
    return list(STALE_WARN_DAYS)


def is_stale(bronze_dir: Path, name: str, max_age_days: int) -> bool:
    """Whether ``name`` is past its staleness threshold, mirroring warn_if_stale.

    A missing manifest entry counts as stale only when the parquet exists
    (fetched before the manifest tracked metadata — warn_if_stale warns for
    exactly this case); an unreadable ``fetched_at`` counts as stale so the
    next refresh re-records it.
    """
    entry = _load_manifest(bronze_dir).get(name)
    if entry is None:
        return (bronze_dir / f"{name}.parquet").exists()
    fetched_at = _parse_fetched_at(str(entry.get("fetched_at", "")))
    if fetched_at is None:
        return True
    age_days = (datetime.now(UTC) - fetched_at).total_seconds() / _SECONDS_PER_DAY
    return age_days > max_age_days


def stale_names(bronze_dir: Path) -> list[str]:
    """Rolling sources whose last fetch is past their STALE_WARN_DAYS threshold."""
    return [
        name
        for name, max_age_days in STALE_WARN_DAYS.items()
        if is_stale(bronze_dir, name, max_age_days)
    ]


def _matching_files(bronze_dir: Path, pattern: str) -> list[Path]:
    """Bronze parquets matching ``pattern`` (same matching rules as clear_bronze)."""
    return [
        path
        for path in sorted(bronze_dir.rglob("*.parquet"))
        if fnmatch.fnmatch(path.relative_to(bronze_dir).with_suffix("").as_posix(), pattern)
    ]


def _age_description(bronze_dir: Path, name: str) -> str:
    entry = _load_manifest(bronze_dir).get(name)
    if entry is None:
        return "no manifest entry (fetched before fetch metadata was tracked)"
    fetched_at = _parse_fetched_at(str(entry.get("fetched_at", "")))
    if fetched_at is None:
        return "unreadable manifest fetched_at"
    age_days = (datetime.now(UTC) - fetched_at).total_seconds() / _SECONDS_PER_DAY
    source = entry.get("source", "unknown")
    return f"fetched {age_days:.0f} day(s) ago from '{source}'"


def log_refresh_plan(bronze_dir: Path, *, stale_only: bool, everything: bool) -> None:
    """Log what a real run would refresh, without deleting anything."""
    if everything:
        logger.info(
            "Dry run (--all): refresh_all would clear ALL bronze parquets, the "
            "Hamilton DAG cache, and the API response cache."
        )
    elif stale_only:
        selection = stale_names(bronze_dir)
        if selection:
            logger.info("Dry run (--stale-only): would refresh: %s", ", ".join(selection))
        else:
            logger.info(
                "Dry run (--stale-only): nothing is past its STALE_WARN_DAYS "
                "threshold; nothing would be refreshed and --run would be a no-op."
            )
    else:
        logger.info("Dry run: would refresh rolling patterns: %s", ", ".join(rolling_patterns()))
    for pattern in rolling_patterns():
        threshold = STALE_WARN_DAYS.get(pattern)
        for path in _matching_files(bronze_dir, pattern):
            logger.info(
                "  %s (stale threshold: %s) — %s",
                path.relative_to(bronze_dir),
                f"{threshold} days" if threshold is not None else "n/a",
                _age_description(bronze_dir, path.stem),
            )


def run_refresh(settings: Settings, *, stale_only: bool, everything: bool) -> list[Path]:
    """Invalidate caches for the selected rolling sources (or everything).

    Returns the removed bronze paths. An empty return with ``stale_only``
    means nothing was past its threshold.
    """
    removed: list[Path]
    if everything:
        removed = refresh_all(settings)
        logger.info("refresh_all: cleared all caches (%d bronze parquets)", len(removed))
        return removed

    if stale_only:
        selection = stale_names(settings.bronze_dir)
        if not selection:
            logger.info(
                "No stale rolling datasets (thresholds: %s); nothing to refresh", STALE_WARN_DAYS
            )
            return []
        removed = []
        for name in selection:
            removed.extend(refresh_bronze(settings, pattern=name))
        logger.info("Refreshed stale rolling datasets: %s", ", ".join(selection))
        return removed

    patterns = rolling_patterns()
    removed = []
    for pattern in patterns:
        removed.extend(refresh_bronze(settings, pattern=pattern))
    logger.info("Refreshed rolling patterns: %s", ", ".join(patterns))
    return removed


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="scripts/40_refresh_rolling.py",
        description=(
            "Refresh the rolling-window bronze sources (URA condo transactions, "
            "HDB resale) and optionally rerun the pipeline."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--stale-only",
        action="store_true",
        help=(
            "Only refresh datasets whose manifest fetched_at is past "
            "STALE_WARN_DAYS (idempotent scheduling target)"
        ),
    )
    mode.add_argument(
        "--all",
        dest="everything",
        action="store_true",
        help="Nuclear: refresh_all (all bronze parquets + DAG cache + API cache)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Rerun the pipeline (stage=all) after the refresh via run_pipeline",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be refreshed (matching files, manifest ages) without deleting",
    )
    parser.add_argument(
        "--log-level",
        choices=list(LEVEL_MAP),
        default="INFO",
        help="Logging level",
    )
    args = parser.parse_args(argv)

    setup_logging(level=LEVEL_MAP[args.log_level])
    resolved = settings if settings is not None else app_settings

    try:
        if args.dry_run:
            log_refresh_plan(
                resolved.bronze_dir, stale_only=args.stale_only, everything=args.everything
            )
            logger.info("Dry run: nothing was deleted.")
            return 0

        removed = run_refresh(resolved, stale_only=args.stale_only, everything=args.everything)
        logger.info("Refresh complete: %d bronze parquet(s) removed", len(removed))

        if args.run:
            if args.stale_only and not removed:
                logger.info("Nothing was stale — skipping pipeline rerun (idempotent no-op).")
                return 0
            logger.info("Running pipeline (stage=all)…")
            run_pipeline(resolved, stage="all")
            logger.info("Pipeline complete.")
        return 0
    except Exception:
        logger.exception("Rolling refresh failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
