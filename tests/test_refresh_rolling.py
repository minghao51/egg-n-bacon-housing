"""Tests for scripts/40_refresh_rolling.py (scheduled rolling-source refresh).

Hermetic: every test runs against a tmp data tree via ``Settings(data_path=...)``
and monkeypatches the pipeline entrypoint — no live APIs, no real ``data/``.
"""

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from egg_n_bacon_housing.config import Settings
from egg_n_bacon_housing.utils.bronze import MANIFEST_FILENAME, STALE_WARN_DAYS

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "40_refresh_rolling.py"


def _load_script():
    """Load 40_refresh_rolling.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("refresh_rolling", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def script():
    """Shared script module instance."""
    return _load_script()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetched_at(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


def _write_manifest(bronze_dir: Path, manifest: dict[str, Any]) -> None:
    bronze_dir.mkdir(parents=True, exist_ok=True)
    (bronze_dir / MANIFEST_FILENAME).write_text(json.dumps(manifest), encoding="utf-8")


def _read_manifest(bronze_dir: Path) -> dict[str, Any]:
    return json.loads((bronze_dir / MANIFEST_FILENAME).read_text(encoding="utf-8"))


def _make_bronze_tree(
    tmp_path: Path,
    *,
    condo_age_days: int | None = 40,
    resale_age_days: int | None = 1,
) -> tuple[Settings, Path]:
    """Tmp settings + bronze tree with both rolling parquets and caches.

    Manifest entries are injected per ``*_age_days`` (``None`` = no entry).
    Includes a static bystander parquet, the Hamilton DAG cache, and an API
    cache entry so tests can assert exactly what each mode invalidates.
    """
    settings = Settings(data_path=str(tmp_path))
    bronze_dir = settings.bronze_dir
    bronze_dir.mkdir(parents=True, exist_ok=True)
    (bronze_dir / "raw_condo_transactions.parquet").touch()
    (bronze_dir / "raw_hdb_resale.parquet").touch()
    (bronze_dir / "raw_school_directory.parquet").touch()  # static bystander

    manifest: dict[str, Any] = {}
    if condo_age_days is not None:
        manifest["raw_condo_transactions"] = {
            "fetched_at": _fetched_at(condo_age_days),
            "source": "ura_api+manual_csv",
            "rows": 10,
        }
    if resale_age_days is not None:
        manifest["raw_hdb_resale"] = {
            "fetched_at": _fetched_at(resale_age_days),
            "source": "datagov_api",
            "rows": 20,
        }
    if manifest:
        _write_manifest(bronze_dir, manifest)

    hamilton = settings.data_dir / "cache" / "hamilton"
    hamilton.mkdir(parents=True, exist_ok=True)
    (hamilton / "cache.db").touch()
    api_entry = settings.data_dir / "cache" / "api-entry.json"
    api_entry.parent.mkdir(parents=True, exist_ok=True)
    api_entry.write_text("{}", encoding="utf-8")
    return settings, bronze_dir


# ---------------------------------------------------------------------------
# Pattern derivation (single-sourced from STALE_WARN_DAYS)
# ---------------------------------------------------------------------------


class TestRollingPatterns:
    def test_patterns_match_stale_warn_days_keys(self, script):
        """The script must not carry its own source list."""
        assert STALE_WARN_DAYS, "STALE_WARN_DAYS unexpectedly empty"
        assert script.rolling_patterns() == list(STALE_WARN_DAYS)

    def test_derivation_tracks_constant_drift(self, script, monkeypatch, tmp_path):
        """Fails if the script hard-codes patterns instead of deriving them."""
        monkeypatch.setattr(script, "STALE_WARN_DAYS", {"raw_future_source": 7})
        assert script.rolling_patterns() == ["raw_future_source"]
        assert script.stale_names(tmp_path) == []  # selection follows the constant too

    def test_stale_names_uses_per_source_thresholds(self, script, tmp_path):
        settings, bronze_dir = _make_bronze_tree(tmp_path, condo_age_days=40, resale_age_days=1)

        assert script.stale_names(bronze_dir) == ["raw_condo_transactions"]
        assert settings.data_dir.exists()  # sanity: tmp tree in place


# ---------------------------------------------------------------------------
# --dry-run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_lists_matches_and_ages_without_deleting(self, script, tmp_path, capsys):
        settings, bronze_dir = _make_bronze_tree(tmp_path, condo_age_days=40, resale_age_days=1)

        rc = script.main(["--dry-run"], settings=settings)

        assert rc == 0
        out = capsys.readouterr().out
        assert "raw_condo_transactions" in out
        assert "raw_hdb_resale" in out
        assert "40 day" in out
        assert "ura_api+manual_csv" in out
        # Nothing deleted, manifest untouched.
        assert (bronze_dir / "raw_condo_transactions.parquet").exists()
        assert (bronze_dir / "raw_hdb_resale.parquet").exists()
        assert (bronze_dir / "raw_school_directory.parquet").exists()
        assert (settings.data_dir / "cache" / "hamilton" / "cache.db").exists()
        assert len(_read_manifest(bronze_dir)) == 2

    def test_dry_run_stale_only_reports_selection(self, script, tmp_path, capsys):
        settings, bronze_dir = _make_bronze_tree(tmp_path, condo_age_days=40, resale_age_days=1)

        rc = script.main(["--dry-run", "--stale-only"], settings=settings)

        assert rc == 0
        out = capsys.readouterr().out
        assert "would refresh: raw_condo_transactions" in out
        assert (bronze_dir / "raw_condo_transactions.parquet").exists()

    def test_dry_run_all_reports_nuclear_scope(self, script, tmp_path, capsys):
        settings, bronze_dir = _make_bronze_tree(tmp_path)

        rc = script.main(["--dry-run", "--all"], settings=settings)

        assert rc == 0
        assert "refresh_all" in capsys.readouterr().out
        assert list(bronze_dir.rglob("*.parquet"))  # untouched

    def test_dry_run_nothing_stale_is_reported(self, script, tmp_path, capsys):
        settings, _bronze_dir = _make_bronze_tree(tmp_path, condo_age_days=1, resale_age_days=1)

        rc = script.main(["--dry-run", "--stale-only"], settings=settings)

        assert rc == 0
        assert "nothing" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# --stale-only
# ---------------------------------------------------------------------------


class TestStaleOnly:
    def test_refreshes_only_entries_past_threshold(self, script, tmp_path):
        settings, bronze_dir = _make_bronze_tree(tmp_path, condo_age_days=40, resale_age_days=1)

        rc = script.main(["--stale-only"], settings=settings)

        assert rc == 0
        assert not (bronze_dir / "raw_condo_transactions.parquet").exists()
        assert (bronze_dir / "raw_hdb_resale.parquet").exists()  # fresh → kept
        assert (bronze_dir / "raw_school_directory.parquet").exists()
        # refresh_bronze semantics: DAG cache cleared, API cache retained.
        assert not (settings.data_dir / "cache" / "hamilton").exists()
        assert (settings.data_dir / "cache" / "api-entry.json").exists()

    def test_missing_manifest_entry_with_parquet_counts_as_stale(self, script, tmp_path):
        """Mirrors warn_if_stale: parquet without fetch metadata → refresh once."""
        settings, bronze_dir = _make_bronze_tree(tmp_path, condo_age_days=None, resale_age_days=1)

        rc = script.main(["--stale-only"], settings=settings)

        assert rc == 0
        assert not (bronze_dir / "raw_condo_transactions.parquet").exists()
        assert (bronze_dir / "raw_hdb_resale.parquet").exists()

    def test_missing_parquet_is_skipped(self, script, tmp_path):
        """No cached dataset → nothing frozen; --stale-only is a no-op."""
        settings = Settings(data_path=str(tmp_path))
        bronze_dir = settings.bronze_dir
        _write_manifest(
            bronze_dir,
            {"raw_hdb_resale": {"fetched_at": _fetched_at(1), "source": "datagov_api", "rows": 5}},
        )
        hamilton = settings.data_dir / "cache" / "hamilton"
        hamilton.mkdir(parents=True, exist_ok=True)
        (hamilton / "cache.db").touch()

        rc = script.main(["--stale-only"], settings=settings)

        assert rc == 0
        assert not list(bronze_dir.rglob("raw_condo_transactions.parquet"))
        assert (hamilton / "cache.db").exists()  # refresh_bronze never ran

    def test_nothing_stale_skips_refresh_and_pipeline(self, script, tmp_path, monkeypatch):
        settings, bronze_dir = _make_bronze_tree(tmp_path, condo_age_days=1, resale_age_days=1)
        calls: list[tuple[Settings, str]] = []
        monkeypatch.setattr(script, "run_pipeline", lambda s, stage: calls.append((s, stage)))

        rc = script.main(["--stale-only", "--run"], settings=settings)

        assert rc == 0
        assert calls == []  # idempotent no-op: no refresh, no rerun
        assert (bronze_dir / "raw_condo_transactions.parquet").exists()
        assert (settings.data_dir / "cache" / "hamilton" / "cache.db").exists()


# ---------------------------------------------------------------------------
# Default refresh
# ---------------------------------------------------------------------------


class TestDefaultRefresh:
    def test_clears_rolling_patterns_and_hamilton_cache_only(self, script, tmp_path):
        """Mirrors refresh_bronze: rolling parquets + DAG cache; static + API cache kept."""
        settings, bronze_dir = _make_bronze_tree(tmp_path)

        rc = script.main([], settings=settings)

        assert rc == 0
        assert not (bronze_dir / "raw_condo_transactions.parquet").exists()
        assert not (bronze_dir / "raw_hdb_resale.parquet").exists()
        assert (bronze_dir / "raw_school_directory.parquet").exists()
        assert not (settings.data_dir / "cache" / "hamilton").exists()
        assert (settings.data_dir / "cache" / "api-entry.json").exists()

    def test_does_not_run_pipeline_without_flag(self, script, tmp_path, monkeypatch):
        settings, _bronze_dir = _make_bronze_tree(tmp_path)
        calls: list[tuple[Settings, str]] = []
        monkeypatch.setattr(script, "run_pipeline", lambda s, stage: calls.append((s, stage)))

        rc = script.main([], settings=settings)

        assert rc == 0
        assert calls == []


# ---------------------------------------------------------------------------
# --all
# ---------------------------------------------------------------------------


class TestAllFlag:
    def test_clears_everything_including_api_cache(self, script, tmp_path):
        settings, bronze_dir = _make_bronze_tree(tmp_path)

        rc = script.main(["--all"], settings=settings)

        assert rc == 0
        assert not list(bronze_dir.rglob("*.parquet"))
        assert not (settings.data_dir / "cache" / "hamilton").exists()
        assert not (settings.data_dir / "cache" / "api-entry.json").exists()

    def test_stale_only_and_all_are_mutually_exclusive(self, script, tmp_path):
        settings, _bronze_dir = _make_bronze_tree(tmp_path)

        with pytest.raises(SystemExit) as excinfo:
            script.main(["--stale-only", "--all"], settings=settings)

        assert excinfo.value.code == 2  # argparse usage error


# ---------------------------------------------------------------------------
# --run (pipeline rerun via the supported entrypoint)
# ---------------------------------------------------------------------------


class TestRunFlag:
    def test_run_invokes_run_pipeline_stage_all(self, script, tmp_path, monkeypatch):
        settings, _bronze_dir = _make_bronze_tree(tmp_path)
        calls: list[tuple[Settings, str]] = []
        monkeypatch.setattr(script, "run_pipeline", lambda s, stage: calls.append((s, stage)))

        rc = script.main(["--run"], settings=settings)

        assert rc == 0
        assert calls == [(settings, "all")]

    def test_pipeline_failure_returns_nonzero(self, script, tmp_path, monkeypatch):
        settings, _bronze_dir = _make_bronze_tree(tmp_path)

        def _boom(s, stage):
            raise RuntimeError("pipeline exploded")

        monkeypatch.setattr(script, "run_pipeline", _boom)

        rc = script.main(["--run"], settings=settings)

        assert rc == 1

    def test_run_after_all_still_runs(self, script, tmp_path, monkeypatch):
        settings, _bronze_dir = _make_bronze_tree(tmp_path)
        calls: list[tuple[Settings, str]] = []
        monkeypatch.setattr(script, "run_pipeline", lambda s, stage: calls.append((s, stage)))

        rc = script.main(["--all", "--run"], settings=settings)

        assert rc == 0
        assert calls == [(settings, "all")]
