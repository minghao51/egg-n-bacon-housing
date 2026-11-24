"""Tests for scripts/00_sync_data.py (R2 manual + geocache sync).

Mocked-transport unit tests: no live S3/R2 access. The fake client mimics
the boto3 surface the script uses (paginator, upload_file, download_file,
head_object).
"""

import hashlib
import importlib.util
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load_sync_module():
    """Load 00_sync_data.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("sync_data", _SCRIPTS / "00_sync_data.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
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
        self.contents: dict[str, bytes] = {}
        self.metadata: dict[str, dict[str, str]] = {}
        self.uploaded: list[str] = []
        self.downloaded: list[str] = []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return _FakePaginator(self._keys)

    def upload_file(self, path, bucket, key, ExtraArgs=None):  # noqa: N803 (boto3 signature)
        self.uploaded.append(key)
        size = os.path.getsize(path)
        self._keys[key] = size
        data = Path(path).read_bytes()
        self.contents[key] = data
        extra = ExtraArgs or {}
        self.metadata[key] = dict(extra.get("Metadata", {}))

    def download_file(self, bucket, key, path):
        self.downloaded.append(key)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        # Default keeps the original restore sentinel for pre-existing tests;
        # divergence tests set ``contents`` explicitly.
        Path(path).write_bytes(self.contents.get(key, b"restored"))

    def head_object(self, Bucket, Key):  # noqa: N803 (boto3 signature)
        return {"Metadata": dict(self.metadata.get(Key, {}))}


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
        # Size equality is reported as SIZE-OK (CONTENT-UNVERIFIED), never "OK".
        assert (
            "Summary: 1 SIZE-OK (CONTENT-UNVERIFIED), 1 missing locally, "
            "1 missing in R2, 0 rejected key(s)" in out
        )
        assert "0 size mismatches" not in out
        assert "Content was NOT compared" in out


class TestContainment:
    """A remote key must never write outside its sync root."""

    def _manual(self, sync, monkeypatch, tmp_path):
        manual = tmp_path / "manual"
        (manual / "csv").mkdir(parents=True)
        monkeypatch.setattr(sync, "MANUAL_DATA_DIR", manual)
        monkeypatch.setattr(sync, "CACHE_DIR", tmp_path / "cache")
        return manual

    @pytest.mark.parametrize(
        "key",
        [
            "manual/../escaped.txt",  # traversal
            "manual//etc/passwd",  # absolute remainder
            "manualx/evil.csv",  # prefix sibling (no trailing slash)
        ],
    )
    def test_manual_unsafe_keys_rejected_without_download(
        self, sync, tmp_path, monkeypatch, fake_s3, capsys, key
    ):
        manual = self._manual(sync, monkeypatch, tmp_path)
        fake_s3._keys = {key: 8}

        sync.download(only="manual")

        out = capsys.readouterr().out
        assert fake_s3.downloaded == []
        assert "REJECTED KEY:" in out
        assert key in out
        # Nothing outside the root was created.
        assert not (tmp_path / "escaped.txt").exists()
        assert not (manual.parent / "escaped.txt").exists()

    def test_nested_geocache_key_rejected(self, sync, tmp_path, monkeypatch, fake_s3, capsys):
        cache = tmp_path / "cache"
        cache.mkdir()
        monkeypatch.setattr(sync, "CACHE_DIR", cache)
        monkeypatch.setattr(sync, "MANUAL_DATA_DIR", tmp_path / "manual")
        fake_s3._keys = {"geocache/hamilton/injected.json": 8}

        sync.download(only="geocache")

        out = capsys.readouterr().out
        assert fake_s3.downloaded == []
        assert "REJECTED KEY:" in out
        assert not (cache / "hamilton" / "injected.json").exists()

    def test_escaping_symlink_rejected(self, sync, tmp_path, monkeypatch, fake_s3, capsys):
        manual = self._manual(sync, monkeypatch, tmp_path)
        outside = tmp_path / "outside"
        outside.mkdir()
        (manual / "escape").symlink_to(outside, target_is_directory=True)
        fake_s3._keys = {"manual/escape/evil.txt": 8}

        sync.download(only="manual")

        out = capsys.readouterr().out
        assert fake_s3.downloaded == []
        assert "REJECTED KEY:" in out
        assert not (outside / "evil.txt").exists()

    def test_verify_rejects_without_downloading(self, sync, tmp_path, monkeypatch, fake_s3, capsys):
        manual = self._manual(sync, monkeypatch, tmp_path)
        fake_s3._keys = {"manual/../escaped.txt": 8}

        sync.verify(only="manual", check_content=True)

        out = capsys.readouterr().out
        assert fake_s3.downloaded == []
        assert "REJECTED KEY:" in out
        assert not (manual.parent / "escaped.txt").exists()


class TestContentDivergence:
    """Size-only equality must never be reported as unchanged content."""

    def _setup(self, sync, tmp_path, monkeypatch, fake_s3, local_bytes, remote_bytes):
        manual = tmp_path / "manual"
        (manual / "csv").mkdir(parents=True)
        (manual / "csv" / "f.csv").write_bytes(local_bytes)
        monkeypatch.setattr(sync, "MANUAL_DATA_DIR", manual)
        monkeypatch.setattr(sync, "CACHE_DIR", tmp_path / "cache")
        key = "manual/csv/f.csv"
        fake_s3._keys = {key: len(remote_bytes)}
        if remote_bytes is not None:
            fake_s3.contents[key] = remote_bytes
        return key

    @pytest.mark.parametrize("delta", [1, 99, 100])
    def test_size_mode_reports_any_byte_difference(
        self, sync, tmp_path, monkeypatch, fake_s3, capsys, delta
    ):
        local = b"a" * 100
        remote = b"a" * (100 + delta)
        self._setup(sync, tmp_path, monkeypatch, fake_s3, local, remote)

        sync.verify(only="manual")

        out = capsys.readouterr().out
        assert "SIZE MISMATCH:    manual/csv/f.csv" in out
        assert "SIZE-OK (CONTENT-UNVERIFIED): manual/csv/f.csv" not in out

    @pytest.mark.parametrize(
        ("local_bytes", "remote_bytes"),
        [
            (b"a" * 100, b"a" * 101),  # +1 byte
            (b"a" * 100, b"a" * 199),  # +99 bytes
            (b"a" * 100, b"a" * 200),  # +100 bytes
            (b"a" * 100, b"b" * 100),  # equal size, different content
        ],
    )
    def test_content_mode_never_calls_divergence_unchanged(
        self, sync, tmp_path, monkeypatch, fake_s3, capsys, local_bytes, remote_bytes
    ):
        self._setup(sync, tmp_path, monkeypatch, fake_s3, local_bytes, remote_bytes)

        sync.verify(only="manual", check_content=True)

        out = capsys.readouterr().out
        assert "CONTENT MISMATCH: manual/csv/f.csv" in out
        assert "CONTENT-OK:       manual/csv/f.csv" not in out

    def test_equal_size_different_content_is_not_size_ok_as_content(
        self, sync, tmp_path, monkeypatch, fake_s3, capsys
    ):
        # Size mode cannot see this; it must still refuse to imply content equality.
        self._setup(sync, tmp_path, monkeypatch, fake_s3, b"a" * 100, b"b" * 100)

        sync.verify(only="manual")

        out = capsys.readouterr().out
        assert "SIZE-OK (CONTENT-UNVERIFIED)" in out
        assert "0 size mismatches" not in out
        assert "Content was NOT compared" in out


class TestContentHashing:
    def test_upload_records_sha256_metadata(self, sync, tmp_path, monkeypatch, fake_s3):
        cache = tmp_path / "cache"
        cache.mkdir()
        payload = b"payload"
        (cache / "a.parquet").write_bytes(payload)
        monkeypatch.setattr(sync, "CACHE_DIR", cache)

        sync.upload(only="geocache")

        key = "geocache/a.parquet"
        assert fake_s3.uploaded == [key]
        assert fake_s3.metadata[key]["sha256"] == hashlib.sha256(payload).hexdigest()

    def test_verify_content_uses_recorded_sha256_without_download(
        self, sync, tmp_path, monkeypatch, fake_s3, capsys
    ):
        manual = tmp_path / "manual"
        (manual / "csv").mkdir(parents=True)
        payload = b"a" * 100
        (manual / "csv" / "f.csv").write_bytes(payload)
        monkeypatch.setattr(sync, "MANUAL_DATA_DIR", manual)
        monkeypatch.setattr(sync, "CACHE_DIR", tmp_path / "cache")
        key = "manual/csv/f.csv"
        fake_s3._keys = {key: len(payload)}
        fake_s3.metadata[key] = {"sha256": hashlib.sha256(payload).hexdigest()}

        sync.verify(only="manual", check_content=True)

        out = capsys.readouterr().out
        assert "CONTENT-OK:" in out
        assert fake_s3.downloaded == []
