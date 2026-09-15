"""Tests for scripts/00_sync_data.py (R2 manual + geocache sync).

Mocked-transport unit tests: no live S3/R2 access. The fake client mimics
the boto3 surface the script uses (paginator, upload_file, download_file).
"""

import importlib.util
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load_sync_module():
    """Load 00_sync_data.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("sync_data", _SCRIPTS / "00_sync_data.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def sync():
    return _load_sync_module()


class _FakePaginator:
    def __init__(self, keys: dict[str, int]):
        self._keys = keys

    def paginate(self, Bucket, Prefix):  # noqa: N803 (boto3 signature)
        matching = {k: v for k, v in self._keys.items() if k.startswith(Prefix)}
        contents = [{"Key": k, "Size": s} for k, s in sorted(matching.items())]
        return [{"Contents": contents}]


class _FakeS3:
    """In-memory stand-in for the boto3 client surface used by the script."""

    def __init__(self, keys: dict[str, int] | None = None):
        self._keys = dict(keys or {})
        self.uploaded: list[str] = []
        self.downloaded: list[str] = []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return _FakePaginator(self._keys)

    def upload_file(self, path, bucket, key):
        self.uploaded.append(key)
        self._keys[key] = os.path.getsize(path)

    def download_file(self, bucket, key, path):
        self.downloaded.append(key)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"restored")


@pytest.fixture
def fake_s3(monkeypatch, sync):
    """Patch the script's client factory; the fake instance is the fixture value."""
    fake = _FakeS3()
    monkeypatch.setattr(sync, "_s3_client", lambda: fake)
    return fake


class TestCollectGeocacheFiles:
    def test_flat_entries_only_hamilton_and_tmp_excluded(self, sync, tmp_path, monkeypatch):
        cache = tmp_path / "cache"
        (cache / "hamilton").mkdir(parents=True)
        (cache / "a.parquet").write_bytes(b"a")
        (cache / "b.json").write_bytes(b"b")
        (cache / "a.parquet.123-456.tmp").write_bytes(b"tmp")
        (cache / "hamilton" / "node.parquet").write_bytes(b"h")
        monkeypatch.setattr(sync, "CACHE_DIR", cache)

        files = sync._collect_geocache_files()

        assert [key for _, key in files] == ["geocache/a.parquet", "geocache/b.json"]
        assert all(p.parent == cache for p, _ in files)

    def test_missing_cache_dir_is_empty(self, sync, tmp_path, monkeypatch):
        monkeypatch.setattr(sync, "CACHE_DIR", tmp_path / "nonexistent")
        assert sync._collect_geocache_files() == []


class TestCollectManualFiles:
    def test_skip_dirs_and_ds_store(self, sync, tmp_path, monkeypatch):
        manual = tmp_path / "manual"
        (manual / "csv").mkdir(parents=True)
        (manual / "ura_backup_20260122").mkdir()
        (manual / "__pycache__").mkdir()
        (manual / "csv" / "keep.csv").write_bytes(b"k")
        (manual / "ura_backup_20260122" / "old.csv").write_bytes(b"o")
        (manual / "__pycache__" / "x.pyc").write_bytes(b"x")
        (manual / ".DS_Store").write_bytes(b"d")
        monkeypatch.setattr(sync, "MANUAL_DATA_DIR", manual)

        files = sync._collect_manual_files()

        assert [key for _, key in files] == ["manual/csv/keep.csv"]


class TestUpload:
    def test_matching_remote_sizes_skipped(self, sync, tmp_path, monkeypatch, fake_s3):
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "same.parquet").write_bytes(b"x" * 100)
        (cache / "new.parquet").write_bytes(b"y" * 100)
        monkeypatch.setattr(sync, "CACHE_DIR", cache)
        fake_s3._keys = {"geocache/same.parquet": 100}

        sync.upload(only="geocache")

        assert fake_s3.uploaded == ["geocache/new.parquet"]

    def test_only_scopes_sync_set(self, sync, tmp_path, monkeypatch, fake_s3):
        manual = tmp_path / "manual"
        (manual / "csv").mkdir(parents=True)
        (manual / "csv" / "keep.csv").write_bytes(b"k")
        monkeypatch.setattr(sync, "MANUAL_DATA_DIR", manual)
        monkeypatch.setattr(sync, "CACHE_DIR", tmp_path / "cache")

        sync.upload(only="manual")

        assert fake_s3.uploaded == ["manual/csv/keep.csv"]


class TestDownload:
    def test_geocache_restores_flat_into_cache_root(self, sync, tmp_path, monkeypatch, fake_s3):
        cache = tmp_path / "cache"
        monkeypatch.setattr(sync, "CACHE_DIR", cache)
        monkeypatch.setattr(sync, "_collect_geocache_files", lambda: [])  # nothing local yet
        fake_s3._keys = {
            "geocache/abc.parquet": 8,
            "geocache/def.json": 8,
            "manual/csv/other.csv": 8,  # different prefix: must not leak in
        }

        sync.download(only="geocache")

        # Completion order across the transfer pool is non-deterministic.
        assert sorted(fake_s3.downloaded) == ["geocache/abc.parquet", "geocache/def.json"]
        assert (cache / "abc.parquet").read_bytes() == b"restored"
        assert (cache / "def.json").read_bytes() == b"restored"

    def test_existing_matching_local_files_skipped(self, sync, tmp_path, monkeypatch, fake_s3):
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "abc.parquet").write_bytes(b"x" * 8)
        monkeypatch.setattr(sync, "CACHE_DIR", cache)
        monkeypatch.setattr(sync, "_collect_geocache_files", lambda: [])
        fake_s3._keys = {"geocache/abc.parquet": 8}

        sync.download(only="geocache")

        assert fake_s3.downloaded == []


class TestVerify:
    def test_summary_across_prefixes(self, sync, tmp_path, monkeypatch, fake_s3, capsys):
        manual = tmp_path / "manual"
        (manual / "csv").mkdir(parents=True)
        (manual / "csv" / "keep.csv").write_bytes(b"k" * 50)
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "local_only.parquet").write_bytes(b"z" * 50)
        monkeypatch.setattr(sync, "MANUAL_DATA_DIR", manual)
        monkeypatch.setattr(sync, "CACHE_DIR", cache)
        fake_s3._keys = {
            "manual/csv/keep.csv": 50,  # OK
            "geocache/remote_only.parquet": 50,  # missing locally
        }  # geocache/local_only.parquet -> missing in R2

        sync.verify()

        out = capsys.readouterr().out
        assert "MISSING LOCALLY:  geocache/remote_only.parquet" in out
        assert "MISSING IN R2:    geocache/local_only.parquet" in out
        assert "Summary: 1 OK, 1 missing locally, 1 missing in R2, 0 size mismatches" in out
