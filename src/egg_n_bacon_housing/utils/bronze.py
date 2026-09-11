"""Bronze layer management: external seeding and cache invalidation.

Two responsibilities:
- ``seed_bronze_external``: materialize the static reference files the DAG
  expects under ``01_bronze/external/`` (amenity GeoJSONs, MRT config JSONs,
  school tiers, SORA parquet) from local source directories (R2-synced
  ``data/manual/`` and git-tracked ``data/raw/``). A fresh clone without this
  step would silently produce empty amenity/macro frames.
- ``clear_bronze`` / ``refresh_bronze`` / ``refresh_all``: invalidate bronze outputs and pipeline
  caches so a run actually re-fetches instead of short-circuiting on
  never-expiring bronze parquets.
- Bronze fetch metadata: every fetch-and-write point upserts into a single
  ``bronze_manifest.json`` per bronze directory (``record_bronze_fetch``), and
  rolling-window datasets warn on the cache-hit path when their last fetch is
  too old (``warn_if_stale`` + ``STALE_WARN_DAYS``). Observability only — the
  manifest never invalidates anything; ``--refresh`` stays the only mechanism.
- Shared bronze cache I/O (``read_bronze_cache`` / ``write_bronze_cache``):
  the single choke point every ingestion node uses for its parquet cache.
  Writes are empty-guarded (an empty or partial source response must never
  replace a valid cache), atomic (tmp + os.replace), and manifest-integrated.
"""

import fnmatch
import json
import logging
import os
import shutil
import threading
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import Settings

logger = logging.getLogger(__name__)

# Static reference files required under bronze/external/ by ingestion and
# feature nodes. Keep in sync with components/ingestion/geojson.py and
# components/ingestion/macro.py. MRT station/line JSONs and school_tiers.json
# are intentionally absent: they have in-code fallbacks (mrt_line_mapping.py,
# school_features.py CSV path), and the malls source is fetched at runtime via
# the datagovsg GeoJSON adapter (see components/ingestion/datagov.py).
EXPECTED_EXTERNAL_FILES: tuple[str, ...] = (
    # Amenity GeoJSONs (components/ingestion/geojson.py)
    "MRTStations.geojson",
    "HawkerCentresGEOJSON.geojson",
    "SupermarketsGEOJSON.geojson",
    "NParksParksandNatureReserves.geojson",
    "ChildCareServices.geojson",
    "PreSchoolsLocation.geojson",
    "BusStops.geojson",
    "CHASClinics.geojson",
    "SportSGFacilities.geojson",
    "CommunityClubs.geojson",
    # Macro (components/ingestion/macro.py)
    "sora_rates.parquet",
)

# Single JSON manifest per bronze directory recording when each dataset was
# last fetched-and-written, from where, and with how many rows.
MANIFEST_FILENAME = "bronze_manifest.json"

# Serializes the manifest's read-modify-write cycle in ``record_bronze_fetch``:
# fetch-and-write points can run concurrently (e.g. macro's bounded fetch
# pool), and an unlocked overlapping upsert could lose one source's entry.
_MANIFEST_LOCK = threading.Lock()

# Opt-in staleness warnings for rolling-window bronze datasets. Keys are
# bronze parquet stems (not node names) so each warning's `main.py --refresh
# <name>` hint matches what clear_bronze actually deletes:
# - raw_condo_transactions: URA API serves a rolling ~5-year window
#   (node raw_condo_transactions).
# - raw_hdb_resale: data.gov.sg API serves Jan 2017+ only (node
#   raw_hdb_resale_transactions; parquet stem differs from the node name).
# Everything else is a static reference and never warns.
STALE_WARN_DAYS: dict[str, int] = {
    "raw_condo_transactions": 35,
    "raw_hdb_resale": 35,
}

_SECONDS_PER_DAY = 86400.0


def record_bronze_fetch(bronze_dir: Path, name: str, source: str, rows: int) -> None:
    """Upsert fetch metadata for one bronze dataset into the bronze manifest.

    Called at fetch-and-write points only (never the cache-hit path). Writes
    ``{name: {"fetched_at": <iso8601-utc>, "source": <id>, "rows": N}}`` into
    ``bronze_dir / bronze_manifest.json`` atomically (tmp file + os.replace).
    A missing or corrupt manifest is tolerated: a warning is logged and the
    manifest is recreated with just this entry. Observability only — a failure
    to update the manifest must never fail the data write, so OS errors are
    logged and swallowed.

    Args:
        bronze_dir: Bronze directory holding the dataset (the manifest lives there).
        name: Bronze artifact name (parquet stem, or the external filename for
            seeded static files).
        source: Short source id, e.g. "datagov_api", "ura_api+manual_csv".
        rows: Row count of the fetched frame.
    """
    with _MANIFEST_LOCK:
        manifest = _load_manifest(bronze_dir)
        manifest[name] = {
            "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "source": source,
            "rows": rows,
        }
        path = bronze_dir / MANIFEST_FILENAME
        try:
            bronze_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_name(f"{MANIFEST_FILENAME}.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp_path, path)
        except OSError as exc:
            logger.warning("Could not update bronze manifest %s: %s", path, exc)


def warn_if_stale(bronze_dir: Path, name: str, max_age_days: int) -> None:
    """Warn (observability only) when a bronze dataset was fetched too long ago.

    Reads ``bronze_manifest.json`` in ``bronze_dir``: if ``fetched_at`` is
    older than ``max_age_days``, or the entry is missing while the parquet
    exists (data predates the manifest), logs a single warning with the name,
    age, source, and the refresh command. Never invalidates anything.

    Args:
        bronze_dir: Bronze directory holding ``<name>.parquet`` and the manifest.
        name: Bronze parquet stem.
        max_age_days: Staleness threshold in days.
    """
    entry = _load_manifest(bronze_dir).get(name)
    if entry is None:
        if (bronze_dir / f"{name}.parquet").exists():
            logger.warning(
                "Bronze dataset '%s' exists but has no manifest entry (fetched before "
                "%s tracked fetch metadata) — refresh once to record it: main.py --refresh %s",
                name,
                MANIFEST_FILENAME,
                name,
            )
        return

    fetched_at = _parse_fetched_at(str(entry.get("fetched_at", "")))
    if fetched_at is None:
        logger.warning(
            "Bronze dataset '%s' has an unreadable fetched_at in %s — refresh to "
            "re-record: main.py --refresh %s",
            name,
            MANIFEST_FILENAME,
            name,
        )
        return

    age_days = (datetime.now(UTC) - fetched_at).total_seconds() / _SECONDS_PER_DAY
    if age_days > max_age_days:
        logger.warning(
            "Bronze dataset '%s' is stale: last fetched %.0f day(s) ago from '%s' "
            "(threshold %d days) — rolling-window data may be frozen at first run; "
            "refresh with: main.py --refresh %s",
            name,
            age_days,
            entry.get("source", "unknown"),
            max_age_days,
            name,
        )


def _bronze_cache_path(bronze_dir: Path, name: str, subdir: str | None = None) -> Path:
    """Resolve a bronze cache parquet path from its manifest name.

    ``name`` is the parquet stem for root-level datasets (``raw_hdb_resale``)
    or the full filename for datasets under ``external/`` (``cpi.parquet``);
    the ``.parquet`` suffix is appended when absent. Existing filenames ARE
    the cache contract (``clear_bronze`` patterns and manifest keys are built
    on them) and must never change.
    """
    filename = name if name.endswith(".parquet") else f"{name}.parquet"
    return bronze_dir / subdir / filename if subdir else bronze_dir / filename


def read_bronze_cache(
    bronze_dir: Path, name: str, subdir: str | None = None
) -> pd.DataFrame | None:
    """Read one bronze cache parquet; ``None`` when the file does not exist.

    Pure existence check + read: a present file is returned as-is (even when
    it holds 0 rows), so cache-eligibility semantics (e.g. treating empty
    caches as misses in macro/MRT nodes) stay exactly where they were before
    centralization. Never writes anything and never records anything.

    Args:
        bronze_dir: Bronze directory holding the cache.
        name: Parquet stem (``raw_hdb_resale``) or full filename
            (``cpi.parquet``); see :func:`_bronze_cache_path`.
        subdir: Optional directory under ``bronze_dir`` (e.g. ``"external"``).
    """
    cache_path = _bronze_cache_path(bronze_dir, name, subdir)
    if not cache_path.exists():
        return None
    return pd.read_parquet(cache_path)


def write_bronze_cache(
    bronze_dir: Path,
    df: pd.DataFrame,
    name: str,
    source: str,
    subdir: str | None = None,
    *,
    allow_empty: bool = False,
    rows: int | None = None,
) -> bool:
    """Persist one bronze cache parquet atomically and record the fetch.

    The bronze immutability rule in one place: an empty frame is never cached
    unless ``allow_empty`` is explicitly True — a valid existing cache must
    not be replaceable by an empty or partial source response. The write is
    atomic (tmp file + ``os.replace``), so a crash mid-write cannot leave a
    truncated parquet that later reads would treat as a cache hit.

    On a successful write, ``record_bronze_fetch`` upserts the manifest entry.
    Cache-hit paths never call this function, so the manifest keeps meaning
    "when was this file fetched-and-written".

    Args:
        bronze_dir: Bronze directory holding the cache.
        df: Fetched-and-normalized frame to persist.
        name: Parquet stem or full filename; becomes the manifest key.
        source: Short source id, e.g. "datagov_api", "ura_api+manual_csv".
        subdir: Optional directory under ``bronze_dir`` (e.g. ``"external"``).
        allow_empty: Write 0-row frames instead of refusing them (opt-in).
        rows: Override the manifest row count for sources whose recorded rows
            mean something other than ``len(df)`` (e.g. geocode hit counts).

    Returns:
        Whether the frame was written (False = empty-guard refused it).
    """
    if df.empty and not allow_empty:
        logger.warning("Not caching empty bronze frame: %s (in %s)", name, bronze_dir)
        return False
    cache_path = _bronze_cache_path(bronze_dir, name, subdir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_name(f"{cache_path.name}.tmp")
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, cache_path)
    record_bronze_fetch(bronze_dir, name, source, len(df) if rows is None else rows)
    return True


def _load_manifest(bronze_dir: Path) -> dict[str, dict]:
    """Read the bronze manifest; {} when missing, corrupt, or malformed."""
    path = bronze_dir / MANIFEST_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Unreadable %s (%s) — recreating it", path, exc)
        return {}
    if not isinstance(data, dict) or not all(isinstance(entry, dict) for entry in data.values()):
        logger.warning("%s has an unexpected shape — recreating it", path)
        return {}
    return data


def _parse_fetched_at(raw: str) -> datetime | None:
    """Parse an ISO-8601 fetched_at timestamp, assuming UTC when naive."""
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


# Directories searched, in order, when seeding a missing bronze/external file.
# data/manual/ is populated by scripts/00_sync_data.py (Cloudflare R2);
# data/raw/ holds git-tracked copies of a subset of the sources.
_SEED_SOURCE_DIRS: tuple[str, ...] = (
    "manual/csv/datagov",
    "raw/external/datagov",
    "manual/geojsons",
    "manual/crosswalks",
    "manual/csv",
    "raw/macro",
)


def seed_bronze_external(bronze_dir: Path, data_dir: Path) -> list[str]:
    """Copy known local sources into ``bronze/external/`` (idempotent).

    Files already present in ``bronze/external/`` are left untouched. For each
    expected file missing from bronze, the first matching file found in the
    seed source directories is copied in.

    Returns:
        Sorted list of expected files that could not be seeded (missing from
        bronze AND from every seed source directory).
    """
    external_dir = bronze_dir / "external"
    external_dir.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    for filename in EXPECTED_EXTERNAL_FILES:
        target = external_dir / filename
        if target.exists():
            continue
        source = _find_seed_source(data_dir, filename)
        if source is None:
            missing.append(filename)
            continue
        shutil.copy2(source, target)
        logger.info("Seeded bronze/external/%s from %s", filename, source.relative_to(data_dir))

    if missing:
        logger.error(
            "Missing %d bronze/external input(s) after seeding: %s — "
            "affected nodes will degrade to empty data. Remediation: run "
            "`uv run python scripts/00_sync_data.py` to fetch "
            "data/manual/ from R2; for files absent from R2, export them into "
            "data/manual/ and re-run sync (--upload).",
            len(missing),
            ", ".join(missing),
        )
    return missing


def _find_seed_source(data_dir: Path, filename: str) -> Path | None:
    """Locate ``filename`` in the seed source directories, or None."""
    for rel_dir in _SEED_SOURCE_DIRS:
        candidate = data_dir / rel_dir / filename
        if candidate.is_file():
            return candidate
    return None


def clear_bronze(bronze_dir: Path, pattern: str = "*") -> list[Path]:
    """Delete bronze parquet outputs whose path matches ``pattern``.

    Matches against the path relative to ``bronze_dir`` using fnmatch, so
    both exact stems (``raw_hdb_resale``) and globs (``raw_macro_*``,
    ``external/*``) work. Only ``.parquet`` files are removed; seeded static
    sources under ``external/`` can be targeted explicitly (``external/*``)
    and are re-seeded at the next startup.

    Returns:
        Sorted list of removed paths.
    """
    removed: list[Path] = []
    for path in sorted(bronze_dir.rglob("*.parquet")):
        rel = path.relative_to(bronze_dir).with_suffix("")
        if fnmatch.fnmatch(rel.as_posix(), pattern):
            path.unlink()
            removed.append(path)
    if removed:
        logger.info("Cleared %d bronze parquet(s) matching '%s'", len(removed), pattern)
    else:
        logger.info("No bronze parquets matched '%s'", pattern)
    return removed


def refresh_bronze(settings: Settings, pattern: str) -> list[Path]:
    """Invalidate matching bronze outputs and all dependent Hamilton results."""
    removed = clear_bronze(settings.bronze_dir, pattern=pattern)
    hamilton_cache = settings.data_dir / "cache" / "hamilton"
    if hamilton_cache.exists():
        shutil.rmtree(hamilton_cache)
        logger.info("Cleared Hamilton DAG cache: %s", hamilton_cache)
    return removed


def refresh_all(settings: Settings) -> list[Path]:
    """Invalidate every cache layer that can suppress a fresh fetch.

    Clears: (1) all bronze parquets (ingestion nodes short-circuit on file
    existence and never expire), (2) the Hamilton DAG result cache, and
    (3) the API response cache (24h TTL, also caches empty responses).

    Returns:
        Removed bronze paths (informational).
    """
    removed = refresh_bronze(settings, pattern="*")

    from egg_n_bacon_housing.utils.cache import CacheManager

    cache_manager = CacheManager(
        cache_dir=settings.data_dir / "cache",
        use_caching=settings.pipeline.use_caching,
        cache_duration_hours=settings.pipeline.cache_duration_hours,
    )
    cache_manager.clear()

    return removed
