"""Tests for bronze layer management (seeding + invalidation + fetch metadata)."""

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from egg_n_bacon_housing.config import Settings
from egg_n_bacon_housing.utils.bronze import (
    EXPECTED_EXTERNAL_FILES,
    MANIFEST_FILENAME,
    STALE_WARN_DAYS,
    clear_bronze,
    record_bronze_fetch,
    refresh_all,
    refresh_bronze,
    seed_bronze_external,
    warn_if_stale,
)

pytestmark = pytest.mark.unit


class TestSeedBronzeExternal:
    """Test seeding of bronze/external static reference files."""

    def test_seeds_from_manual_dir(self, tmp_path):
        bronze_dir = tmp_path / "pipeline" / "01_bronze"
        manual = tmp_path / "manual" / "csv" / "datagov"
        manual.mkdir(parents=True)
        (manual / "BusStops.geojson").write_text('{"type": "FeatureCollection"}')

        missing = seed_bronze_external(bronze_dir, tmp_path)

        assert (bronze_dir / "external" / "BusStops.geojson").is_file()
        assert "BusStops.geojson" not in missing

    def test_prefers_manual_over_raw(self, tmp_path):
        bronze_dir = tmp_path / "pipeline" / "01_bronze"
        manual = tmp_path / "manual" / "csv" / "datagov"
        raw = tmp_path / "raw" / "external" / "datagov"
        manual.mkdir(parents=True)
        raw.mkdir(parents=True)
        (manual / "MRTStations.geojson").write_text('{"source": "manual"}')
        (raw / "MRTStations.geojson").write_text('{"source": "raw"}')

        seed_bronze_external(bronze_dir, tmp_path)

        content = (bronze_dir / "external" / "MRTStations.geojson").read_text()
        assert "manual" in content

    def test_does_not_overwrite_existing_bronze_files(self, tmp_path):
        bronze_dir = tmp_path / "pipeline" / "01_bronze"
        external = bronze_dir / "external"
        external.mkdir(parents=True)
        (external / "sora_rates.parquet").write_bytes(b"existing")

        raw = tmp_path / "raw" / "macro"
        raw.mkdir(parents=True)
        pd.DataFrame([{"rate": 1.0}]).to_parquet(raw / "sora_rates.parquet", index=False)

        seed_bronze_external(bronze_dir, tmp_path)

        assert (external / "sora_rates.parquet").read_bytes() == b"existing"

    def test_reports_missing_files(self, tmp_path):
        bronze_dir = tmp_path / "pipeline" / "01_bronze"

        missing = seed_bronze_external(bronze_dir, tmp_path)

        assert set(missing) == set(EXPECTED_EXTERNAL_FILES)

    def test_seeds_sora_from_raw_macro(self, tmp_path):
        bronze_dir = tmp_path / "pipeline" / "01_bronze"
        raw = tmp_path / "raw" / "macro"
        raw.mkdir(parents=True)
        pd.DataFrame([{"rate": 1.0}]).to_parquet(raw / "sora_rates.parquet", index=False)

        missing = seed_bronze_external(bronze_dir, tmp_path)

        assert (bronze_dir / "external" / "sora_rates.parquet").is_file()
        assert "sora_rates.parquet" not in missing


class TestClearBronze:
    """Test bronze parquet invalidation."""

    def test_clears_all_parquets(self, tmp_path):
        bronze_dir = tmp_path / "01_bronze"
        (bronze_dir / "external").mkdir(parents=True)
        (bronze_dir / "raw_a.parquet").touch()
        (bronze_dir / "raw_b.parquet").touch()
        (bronze_dir / "external" / "cpi.parquet").touch()

        removed = clear_bronze(bronze_dir)

        assert len(removed) == 3
        assert not list(bronze_dir.rglob("*.parquet"))

    def test_clears_by_stem_pattern(self, tmp_path):
        bronze_dir = tmp_path / "01_bronze"
        bronze_dir.mkdir(parents=True)
        (bronze_dir / "raw_hdb_resale.parquet").touch()
        (bronze_dir / "raw_condo_transactions.parquet").touch()

        removed = clear_bronze(bronze_dir, pattern="raw_hdb_*")

        assert [p.name for p in removed] == ["raw_hdb_resale.parquet"]
        assert (bronze_dir / "raw_condo_transactions.parquet").exists()

    def test_clears_external_subdir_pattern(self, tmp_path):
        bronze_dir = tmp_path / "01_bronze"
        (bronze_dir / "external").mkdir(parents=True)
        (bronze_dir / "raw_a.parquet").touch()
        (bronze_dir / "external" / "cpi.parquet").touch()

        removed = clear_bronze(bronze_dir, pattern="external/*")

        assert [p.name for p in removed] == ["cpi.parquet"]
        assert (bronze_dir / "raw_a.parquet").exists()

    def test_no_match_returns_empty(self, tmp_path):
        bronze_dir = tmp_path / "01_bronze"
        bronze_dir.mkdir(parents=True)

        assert clear_bronze(bronze_dir, pattern="nope") == []


class TestRefreshAll:
    """Test full cache invalidation across layers."""

    def test_clears_bronze_hamilton_and_api_cache(self, tmp_path):
        settings = Settings(data_path=str(tmp_path))

        bronze_dir = tmp_path / "pipeline" / "01_bronze"
        bronze_dir.mkdir(parents=True)
        (bronze_dir / "raw_a.parquet").touch()
        hamilton_cache = tmp_path / "cache" / "hamilton"
        hamilton_cache.mkdir(parents=True)
        (hamilton_cache / "entry.bin").touch()
        api_cache = tmp_path / "cache"
        api_cache.mkdir(exist_ok=True)
        (api_cache / "stale.json").write_text("{}")

        removed = refresh_all(settings)

        assert len(removed) == 1
        assert not list(bronze_dir.rglob("*.parquet"))
        assert not hamilton_cache.exists()
        assert list(api_cache.glob("*")) == []


class TestTargetedRefresh:
    def test_clears_matching_bronze_and_hamilton_but_keeps_api_cache(self, tmp_path):
        settings = Settings(data_path=str(tmp_path))
        bronze_dir = settings.bronze_dir
        bronze_dir.mkdir(parents=True)
        target = bronze_dir / "raw_condo_transactions.parquet"
        retained = bronze_dir / "raw_hdb_resale.parquet"
        target.touch()
        retained.touch()
        hamilton_cache = settings.data_dir / "cache" / "hamilton"
        hamilton_cache.mkdir(parents=True)
        (hamilton_cache / "cache.db").touch()
        api_entry = settings.data_dir / "cache" / "api-entry.json"
        api_entry.parent.mkdir(exist_ok=True)
        api_entry.write_text("{}")

        removed = refresh_bronze(settings, "raw_condo_transactions")

        assert removed == [target]
        assert not target.exists()
        assert retained.exists()
        assert not hamilton_cache.exists()
        assert api_entry.exists()


def _read_manifest(bronze_dir: Path) -> dict:
    return json.loads((bronze_dir / MANIFEST_FILENAME).read_text(encoding="utf-8"))


def _write_manifest(bronze_dir: Path, manifest: dict) -> None:
    bronze_dir.mkdir(parents=True, exist_ok=True)
    (bronze_dir / MANIFEST_FILENAME).write_text(json.dumps(manifest), encoding="utf-8")


class TestBronzeCacheHelpers:
    """The single bronze cache I/O choke point used by every ingestion node."""

    def test_round_trip(self, tmp_path):
        from egg_n_bacon_housing.utils.bronze import read_bronze_cache, write_bronze_cache

        df = pd.DataFrame([{"a": 1}, {"a": 2}])

        assert write_bronze_cache(tmp_path, df, "raw_demo", "datagov_api") is True

        cached = read_bronze_cache(tmp_path, "raw_demo")
        assert cached is not None
        pd.testing.assert_frame_equal(cached, df)

    def test_read_missing_cache_returns_none(self, tmp_path):
        from egg_n_bacon_housing.utils.bronze import read_bronze_cache

        assert read_bronze_cache(tmp_path, "raw_absent") is None

    def test_empty_frame_refused_no_file_no_manifest(self, tmp_path):
        from egg_n_bacon_housing.utils.bronze import read_bronze_cache, write_bronze_cache

        assert write_bronze_cache(tmp_path, pd.DataFrame(), "raw_demo", "datagov_api") is False

        assert not (tmp_path / "raw_demo.parquet").exists()
        assert read_bronze_cache(tmp_path, "raw_demo") is None
        assert not (tmp_path / MANIFEST_FILENAME).exists()

    def test_allow_empty_writes_zero_row_file_and_records(self, tmp_path):
        from egg_n_bacon_housing.utils.bronze import read_bronze_cache, write_bronze_cache

        df = pd.DataFrame({"a": pd.Series([], dtype="int64")})

        assert write_bronze_cache(tmp_path, df, "raw_demo", "datagov_api", allow_empty=True)

        cached = read_bronze_cache(tmp_path, "raw_demo")
        assert cached is not None
        assert len(cached) == 0
        assert _read_manifest(tmp_path)["raw_demo"]["rows"] == 0

    def test_write_records_manifest_entry(self, tmp_path):
        from egg_n_bacon_housing.utils.bronze import write_bronze_cache

        write_bronze_cache(tmp_path, pd.DataFrame([{"a": 1}]), "raw_demo", "ura_api+manual_csv")

        entry = _read_manifest(tmp_path)["raw_demo"]
        assert entry["source"] == "ura_api+manual_csv"
        assert entry["rows"] == 1
        assert datetime.fromisoformat(entry["fetched_at"]).tzinfo is not None

    def test_rows_override_preserves_nonstandard_manifest_semantics(self, tmp_path):
        """e.g. geocode writes record geocoded-coordinate counts, not len(df)."""
        from egg_n_bacon_housing.utils.bronze import write_bronze_cache

        df = pd.DataFrame([{"lat": 1.3}, {"lat": None}])

        write_bronze_cache(tmp_path, df, "raw_geo", "onemap_geocode", rows=1)

        assert _read_manifest(tmp_path)["raw_geo"]["rows"] == 1

    def test_subdir_external_filename_contract(self, tmp_path):
        """Macro-style caches live under external/ keyed by full filename."""
        from egg_n_bacon_housing.utils.bronze import read_bronze_cache, write_bronze_cache

        df = pd.DataFrame([{"date": "2026-01-01", "cpi": 101.0}])

        assert write_bronze_cache(tmp_path, df, "cpi.parquet", "datagov_api", subdir="external")

        assert (tmp_path / "external" / "cpi.parquet").exists()
        assert _read_manifest(tmp_path)["cpi.parquet"]["rows"] == 1
        cached = read_bronze_cache(tmp_path, "cpi.parquet", subdir="external")
        assert cached is not None
        pd.testing.assert_frame_equal(cached, df)

    def test_atomic_write_leaves_no_tmp_file(self, tmp_path):
        from egg_n_bacon_housing.utils.bronze import write_bronze_cache

        write_bronze_cache(tmp_path, pd.DataFrame([{"a": 1}]), "raw_demo", "datagov_api")

        assert list(tmp_path.rglob("*.tmp")) == []


class TestRecordBronzeFetch:
    """The bronze manifest upsert used at every fetch-and-write point."""

    def test_creates_manifest_with_entry(self, tmp_path):
        record_bronze_fetch(tmp_path, "raw_condo_transactions", "ura_api+manual_csv", 42)

        manifest = _read_manifest(tmp_path)
        assert set(manifest) == {"raw_condo_transactions"}
        entry = manifest["raw_condo_transactions"]
        assert entry["source"] == "ura_api+manual_csv"
        assert entry["rows"] == 42
        fetched_at = datetime.fromisoformat(entry["fetched_at"])
        assert fetched_at.tzinfo is not None  # ISO-8601 UTC
        assert abs(fetched_at - datetime.now(UTC)) < timedelta(minutes=1)

    def test_second_record_upserts_and_preserves_other_entries(self, tmp_path):
        record_bronze_fetch(tmp_path, "raw_hdb_resale", "datagov_api", 10)
        record_bronze_fetch(tmp_path, "cpi.parquet", "datagov_api", 5)

        record_bronze_fetch(tmp_path, "raw_hdb_resale", "datagov_api+manual_csv", 99)

        manifest = _read_manifest(tmp_path)
        assert set(manifest) == {"raw_hdb_resale", "cpi.parquet"}
        assert manifest["raw_hdb_resale"]["rows"] == 99
        assert manifest["raw_hdb_resale"]["source"] == "datagov_api+manual_csv"
        assert manifest["cpi.parquet"]["rows"] == 5  # untouched

    def test_tolerates_corrupt_manifest(self, tmp_path, caplog):
        (tmp_path / MANIFEST_FILENAME).write_text("{not json", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            record_bronze_fetch(tmp_path, "raw_condo_transactions", "ura_api", 1)

        assert "Unreadable" in caplog.text
        manifest = _read_manifest(tmp_path)
        assert set(manifest) == {"raw_condo_transactions"}  # recreated with just this entry

    def test_tolerates_malformed_manifest(self, tmp_path, caplog):
        _write_manifest(tmp_path, {"not": "a dict of dicts"})

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            record_bronze_fetch(tmp_path, "raw_condo_transactions", "ura_api", 1)

        assert "unexpected shape" in caplog.text
        assert set(_read_manifest(tmp_path)) == {"raw_condo_transactions"}

    def test_atomic_write_leaves_no_tmp_file(self, tmp_path):
        record_bronze_fetch(tmp_path, "raw_condo_transactions", "ura_api", 1)

        assert list(tmp_path.glob("*.tmp")) == []


class TestWarnIfStale:
    """Rolling-source staleness warnings (observability only)."""

    def test_stale_entry_warns_with_age_source_and_refresh_command(self, tmp_path, caplog):
        old = datetime.now(UTC) - timedelta(days=40)
        _write_manifest(
            tmp_path,
            {
                "raw_condo_transactions": {
                    "fetched_at": old.isoformat(),
                    "source": "ura_api+manual_csv",
                    "rows": 100,
                }
            },
        )

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            warn_if_stale(tmp_path, "raw_condo_transactions", max_age_days=35)

        stale_warnings = [r for r in caplog.records if "is stale" in r.getMessage()]
        assert len(stale_warnings) == 1
        message = stale_warnings[0].getMessage()
        assert "raw_condo_transactions" in message
        assert "40 day" in message
        assert "ura_api+manual_csv" in message
        assert "main.py --refresh raw_condo_transactions" in message

    def test_fresh_entry_is_silent(self, tmp_path, caplog):
        record_bronze_fetch(tmp_path, "raw_condo_transactions", "ura_api", 1)

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            warn_if_stale(tmp_path, "raw_condo_transactions", max_age_days=35)

        assert caplog.records == []

    def test_missing_entry_with_existing_parquet_warns_once(self, tmp_path, caplog):
        (tmp_path / "raw_hdb_resale.parquet").touch()
        _write_manifest(tmp_path, {"other_dataset": {"fetched_at": "2020-01-01T00:00:00+00:00"}})

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            warn_if_stale(tmp_path, "raw_hdb_resale", max_age_days=35)

        warnings = [r for r in caplog.records if "raw_hdb_resale" in r.getMessage()]
        assert len(warnings) == 1
        assert "no manifest entry" in warnings[0].getMessage()
        assert "main.py --refresh raw_hdb_resale" in warnings[0].getMessage()

    def test_missing_entry_and_no_parquet_is_silent(self, tmp_path, caplog):
        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            warn_if_stale(tmp_path, "raw_condo_transactions", max_age_days=35)

        assert caplog.records == []

    def test_unreadable_fetched_at_warns(self, tmp_path, caplog):
        _write_manifest(
            tmp_path,
            {"raw_condo_transactions": {"fetched_at": "not-a-date", "source": "ura_api"}},
        )

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            warn_if_stale(tmp_path, "raw_condo_transactions", max_age_days=35)

        assert any("unreadable fetched_at" in r.getMessage() for r in caplog.records)

    def test_stale_warn_days_maps_exactly_the_two_rolling_sources(self):
        import egg_n_bacon_housing.components.ingestion.datagov as datagov
        import egg_n_bacon_housing.components.ingestion.ura_csv as ura_csv

        # Keys are bronze parquet stems (what --refresh matches), not node names.
        assert STALE_WARN_DAYS == {"raw_condo_transactions": 35, "raw_hdb_resale": 35}
        # Every mapped name must correspond to a bronze parquet its ingestion
        # node actually reads/writes through the centralized bronze cache
        # helpers — keeps the warning's refresh hint actionable.
        ura_src = Path(ura_csv.__file__).read_text(encoding="utf-8")
        datagov_src = Path(datagov.__file__).read_text(encoding="utf-8")
        for source_text, name in (
            (ura_src, "raw_condo_transactions"),
            (datagov_src, "raw_hdb_resale"),
        ):
            assert re.search(rf"(?:read|write)_bronze_cache\([^()]*\"{name}\"", source_text), (
                f"{name} is no longer read/written via a bronze cache helper"
            )


class TestExternalFileRegistry:
    """EXPECTED_EXTERNAL_FILES must stay in sync with ingestion module references."""

    _AMENITY_CALL_RE = re.compile(r"_load_external_amenity\(\s*bronze_dir,\s*\"([^\"]+)\"")

    # Seeded external files referenced OUTSIDE the _load_external_amenity
    # wrapper. mrt_stations.json is deliberately absent: it is runtime-written
    # with an in-code fallback (see the comment on EXPECTED_EXTERNAL_FILES).
    _NON_AMENITY_EXTERNAL_FILES = {"MRTStations.geojson", "sora_rates.parquet"}

    @classmethod
    def _referenced_external_files(cls) -> set[str]:
        import egg_n_bacon_housing.components.ingestion.geojson as geojson

        source = Path(geojson.__file__).read_text(encoding="utf-8")
        return set(cls._AMENITY_CALL_RE.findall(source)) | cls._NON_AMENITY_EXTERNAL_FILES

    def test_expected_external_files_match_ingestion_references(self):
        referenced = self._referenced_external_files()
        expected = set(EXPECTED_EXTERNAL_FILES)
        assert expected == referenced, (
            "EXPECTED_EXTERNAL_FILES is out of sync with the external files the ingestion "
            "modules reference. Update BOTH sides: (1) EXPECTED_EXTERNAL_FILES in "
            "src/egg_n_bacon_housing/utils/bronze.py, and (2) the filename reference in "
            "src/egg_n_bacon_housing/components/ingestion/geojson.py or macro.py "
            "(_load_external_amenity call, MRTStations.geojson legacy read, or "
            "sora_rates.parquet in raw_macro_data). Only-in-registry: "
            f"{sorted(expected - referenced)}; only-in-modules: {sorted(referenced - expected)}."
        )

    def test_registry_check_fails_loudly_on_one_sided_addition(self):
        """A filename added to one side only must break the sync test above."""
        # Side 1: a new _load_external_amenity call in geojson.py is picked up
        # by extraction but is absent from EXPECTED_EXTERNAL_FILES.
        synthetic_call = (
            "return _load_external_amenity(\n"
            "        bronze_dir,\n"
            '        "NewAmenitySource.geojson",\n'
            '        ["NAME"],\n'
            '        "new_amenity",\n'
            "    )"
        )
        extracted = set(self._AMENITY_CALL_RE.findall(synthetic_call))
        assert extracted == {"NewAmenitySource.geojson"}
        assert extracted - set(EXPECTED_EXTERNAL_FILES) == {"NewAmenitySource.geojson"}

        # Side 2: adding to EXPECTED_EXTERNAL_FILES only leaves it absent from
        # the referenced set, which the equality assertion above also catches.
        assert "NewAmenitySource.geojson" not in self._referenced_external_files()
