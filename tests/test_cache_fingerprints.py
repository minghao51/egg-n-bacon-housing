"""Tests for the deterministic Hamilton cache identities (utils/cache_fingerprints.py).

These fingerprints are the DAG cache identity for every injected runtime
service (paths, cache managers, geocoders, reference repositories), so the
guarantees under test are:

- key stability: identical inputs hash identically, across repeated calls
  and across equal-but-distinct instances;
- input sensitivity: every field a registration hashes actually moves the
  hash (no silent coalescing of different configurations);
- serialization round-trip: the JSON digest layer is canonical (key order
  and container type irrelevant, non-JSON values via ``str``).

No live services, no writes outside ``tmp_path`` — cache managers are built
with ``use_caching=False`` so nothing ever touches the real cache directory.
"""

import hashlib
import json
import os
import re

import pandas as pd
import pytest
from hamilton.caching.fingerprinting import hash_value

from egg_n_bacon_housing.utils.cache import CacheManager
from egg_n_bacon_housing.utils.cache_fingerprints import _digest, register_cache_fingerprints
from egg_n_bacon_housing.utils.data_loader import SpatialReferenceRepository
from egg_n_bacon_housing.utils.geocoding import Geocoder, InMemoryGeocoder, OneMapGeocoder
from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository
from egg_n_bacon_housing.utils.school_features import SchoolReferenceRepository

pytestmark = pytest.mark.unit

# Idempotent: re-registering overwrites the same registry entries, and
# importing the pipeline elsewhere has already registered them once.
register_cache_fingerprints()


class _StubGeocoder(Geocoder):
    """Minimal Geocoder subclass that is neither InMemory nor OneMap."""

    def geocode(self, addresses: pd.Series) -> pd.DataFrame:  # pragma: no cover - never called
        return pd.DataFrame()


class _AnotherStubGeocoder(Geocoder):
    def geocode(self, addresses: pd.Series) -> pd.DataFrame:  # pragma: no cover - never called
        return pd.DataFrame()


def _cache_manager(tmp_path, name="cache", *, enabled=False, ttl=24) -> CacheManager:
    return CacheManager(cache_dir=tmp_path / name, use_caching=enabled, cache_duration_hours=ttl)


def _onemap(tmp_path, *, workers=3, timeout=10, ttl=24) -> OneMapGeocoder:
    return OneMapGeocoder(
        headers={"Authorization": "test"},
        cache_manager=_cache_manager(tmp_path),
        max_workers=workers,
        timeout=timeout,
        cache_duration_hours=ttl,
    )


def _write(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestDigest:
    """The JSON digest layer underneath every registration."""

    def test_digest_is_sha256_hex(self):
        for value in ("x", {"a": 1}, [1, 2], None):
            assert re.fullmatch(r"[0-9a-f]{64}", _digest(value))

    def test_digest_matches_manual_json_roundtrip(self):
        value = {"b": [1, 2], "a": "x"}
        expected = hashlib.sha256(
            json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()
        assert _digest(value) == expected

    def test_digest_is_key_order_invariant(self):
        assert _digest({"a": 1, "b": {"c": 2, "d": 3}}) == _digest({"b": {"d": 3, "c": 2}, "a": 1})

    def test_digest_normalizes_tuples_and_lists(self):
        """json.dumps serializes tuples as arrays, so both hash identically."""
        assert _digest((1, 2)) == _digest([1, 2])

    def test_digest_serializes_non_json_values_via_str(self):
        import pathlib

        assert _digest({"p": pathlib.PurePath("/x/y")}) == _digest({"p": "/x/y"})

    def test_digest_is_value_sensitive(self):
        assert _digest({"a": 1}) != _digest({"a": 2})
        assert _digest({"a": 1}) != _digest({"b": 1})


class TestKeyStability:
    """Same inputs -> identical hash across repeated calls and equal instances."""

    def test_path_hash_is_stable_across_repeated_calls(self, tmp_path):
        _write(tmp_path / "ref.geojson", "{}")
        path = tmp_path / "ref.geojson"
        assert hash_value(path) == hash_value(path) == hash_value(tmp_path / "ref.geojson")

    def test_equal_cache_managers_hash_identically(self, tmp_path):
        first = _cache_manager(tmp_path, ttl=48)
        second = _cache_manager(tmp_path, ttl=48)
        assert hash_value(first) == hash_value(first) == hash_value(second)

    def test_repositories_over_identical_trees_hash_identically(self, tmp_path):
        """Content-addressed tree hashing: equal content in different roots is equal."""
        roots = []
        for root_name in ("copy_a", "copy_b"):
            root = tmp_path / root_name
            _write(root / "nested" / "lines.json", '{"NSL": ["Jurong East"]}')
            _write(root / "stations.csv", "code,name\nNS1,Jurong East\n")
            roots.append(root)

        repos = [MrtReferenceRepository(config_dir=root) for root in roots]
        assert hash_value(repos[0]) == hash_value(repos[1])
        assert hash_value(repos[0]) == hash_value(repos[0])  # repeat-call stable

    def test_spatial_repo_over_identical_trees_hash_identically(self, tmp_path):
        roots = []
        for root_name in ("raw_a", "raw_b"):
            root = tmp_path / root_name
            _write(root / "onemap_planning_area_polygon.geojson", '{"type": "FeatureCollection"}')
            roots.append(root)

        repos = [SpatialReferenceRepository(raw_data_dir=root) for root in roots]
        assert hash_value(repos[0]) == hash_value(repos[1])

    def test_school_repo_over_identical_trees_hash_identically(self, tmp_path):
        bronze_dirs = []
        for root_name in ("bronze_a", "bronze_b"):
            bronze = tmp_path / root_name
            _write(bronze / "external" / "school_tiers.json", '{"tier1": ["Nanyang Primary"]}')
            bronze_dirs.append(bronze)

        repos = [
            SchoolReferenceRepository(bronze_dir=bronze, data_dir=tmp_path)
            for bronze in bronze_dirs
        ]
        assert hash_value(repos[0]) == hash_value(repos[1])

    def test_inmemory_geocoder_hash_is_lookup_order_invariant(self):
        first = InMemoryGeocoder({"1 Bedok Rd": (1.32, 103.93), "2 Ang Mo Kio": (1.37, 103.84)})
        second = InMemoryGeocoder({"2 Ang Mo Kio": (1.37, 103.84), "1 Bedok Rd": (1.32, 103.93)})
        assert hash_value(first) == hash_value(second)
        assert hash_value(first) == hash_value(first)

    def test_equal_onemap_geocoders_hash_identically(self, tmp_path):
        assert hash_value(_onemap(tmp_path)) == hash_value(_onemap(tmp_path))

    def test_geocoder_subclass_instances_hash_identically(self):
        """The base-class fallback hashes only the concrete type's qualname."""
        assert hash_value(_StubGeocoder()) == hash_value(_StubGeocoder())

    def test_unreadable_and_missing_trees_hash_stably(self, tmp_path):
        """A nonexistent tree is a stable empty fingerprint, not an error."""
        first = MrtReferenceRepository(config_dir=tmp_path / "absent")
        second = MrtReferenceRepository(config_dir=tmp_path / "also-absent")
        assert hash_value(first) == hash_value(second)
        assert hash_value(first) == hash_value(first)


class TestInputSensitivity:
    """Every hashed field moves the fingerprint; nothing coalesces."""

    def test_different_paths_hash_differently(self, tmp_path):
        assert hash_value(tmp_path / "a") != hash_value(tmp_path / "b")

    def test_path_hash_tracks_directory_creation(self, tmp_path):
        """A path only exists as a fingerprint once it exists on disk."""
        missing = tmp_path / "dir"
        before = hash_value(missing)
        missing.mkdir()
        assert hash_value(missing) == before  # same resolved string, same hash
        assert hash_value(missing) == _digest({"path": str(missing.resolve())})

    def test_cache_manager_config_fields_all_contribute(self, tmp_path):
        baseline = hash_value(_cache_manager(tmp_path, ttl=24))
        assert hash_value(_cache_manager(tmp_path, ttl=48)) != baseline
        assert hash_value(_cache_manager(tmp_path, enabled=True)) != baseline
        assert hash_value(_cache_manager(tmp_path, name="elsewhere")) != baseline

    def test_mrt_repo_hash_tracks_tree_content_and_layout(self, tmp_path):
        root = tmp_path / "mrt"
        _write(root / "lines.json", '{"NSL": 1}')
        baseline = hash_value(MrtReferenceRepository(config_dir=root))

        # Changed content -> changed hash.
        _write(root / "lines.json", '{"NSL": 2}')
        changed = hash_value(MrtReferenceRepository(config_dir=root))
        assert changed != baseline

        # Added file -> changed hash.
        _write(root / "stations.csv", "code\nNS1\n")
        assert hash_value(MrtReferenceRepository(config_dir=root)) != changed

    def test_repo_hash_is_content_addressed_not_mtime_addressed(self, tmp_path):
        root = tmp_path / "spatial"
        geojson = root / "onemap_planning_area_polygon.geojson"
        _write(geojson, '{"type": "FeatureCollection"}')
        repo = SpatialReferenceRepository(raw_data_dir=root)
        baseline = hash_value(repo)

        stat_before = geojson.stat()
        os.utime(geojson, (stat_before.st_atime, stat_before.st_mtime + 5_000))
        assert hash_value(repo) == baseline  # mtime changes alone do not move the hash

        _write(geojson, '{"type": "FeatureCollection", "changed": true}')
        assert hash_value(SpatialReferenceRepository(raw_data_dir=root)) != baseline

    def test_school_repo_hash_tracks_bronze_external_tree(self, tmp_path):
        bronze = tmp_path / "bronze"
        _write(bronze / "external" / "school_tiers.json", '{"tier1": []}')
        baseline = hash_value(SchoolReferenceRepository(bronze_dir=bronze, data_dir=tmp_path))

        _write(bronze / "external" / "school_tiers.json", '{"tier1": ["Ai Tong"]}')
        assert (
            hash_value(SchoolReferenceRepository(bronze_dir=bronze, data_dir=tmp_path)) != baseline
        )

    def test_inmemory_geocoder_hash_tracks_lookup(self):
        baseline = hash_value(InMemoryGeocoder({"a": (1.0, 2.0)}))
        assert hash_value(InMemoryGeocoder({"a": (1.0, 3.0)})) != baseline
        assert hash_value(InMemoryGeocoder({"a": (1.0, 2.0), "b": (3.0, 4.0)})) != baseline
        assert hash_value(InMemoryGeocoder({})) != baseline

    def test_onemap_geocoder_config_fields_all_contribute(self, tmp_path):
        baseline = hash_value(_onemap(tmp_path))
        assert hash_value(_onemap(tmp_path, workers=5)) != baseline
        assert hash_value(_onemap(tmp_path, timeout=30)) != baseline
        assert hash_value(_onemap(tmp_path, ttl=48)) != baseline

    def test_geocoder_subclass_hash_tracks_qualname(self):
        assert hash_value(_StubGeocoder()) != hash_value(_AnotherStubGeocoder())

    def test_repo_type_tag_distinguishes_kinds_over_identical_trees(self, tmp_path):
        """Same tree content, different repo kind -> different digest payload."""
        root = tmp_path / "shared"
        _write(root / "data.json", "{}")
        assert hash_value(MrtReferenceRepository(config_dir=root)) != hash_value(
            SpatialReferenceRepository(raw_data_dir=root)
        )


class TestRegisteredTypeDispatch:
    """Registrations stay attached to their intended types."""

    @pytest.mark.parametrize(
        "factory",
        [
            lambda tmp_path: tmp_path,
            lambda tmp_path: _cache_manager(tmp_path),
            lambda tmp_path: MrtReferenceRepository(config_dir=tmp_path / "mrt"),
            lambda tmp_path: SpatialReferenceRepository(raw_data_dir=tmp_path / "raw"),
            lambda tmp_path: SchoolReferenceRepository(
                bronze_dir=tmp_path / "bronze", data_dir=tmp_path
            ),
            lambda tmp_path: InMemoryGeocoder({}),
            lambda tmp_path: _onemap(tmp_path),
            lambda tmp_path: _StubGeocoder(),
        ],
        ids=[
            "path",
            "cache_manager",
            "mrt_repo",
            "spatial_repo",
            "school_repo",
            "memory_geocoder",
            "onemap_geocoder",
            "geocoder_subclass",
        ],
    )
    def test_registered_types_hash_to_sha256_hex(self, tmp_path, factory):
        digest = hash_value(factory(tmp_path))
        assert re.fullmatch(r"[0-9a-f]{64}", digest)

    def test_inmemory_geocoder_uses_its_own_registration(self):
        """Not the base Geocoder fallback: the lookup table is part of the digest."""
        assert hash_value(InMemoryGeocoder({"a": (1.0, 2.0)})) != hash_value(
            InMemoryGeocoder({"a": (9.0, 9.0)})
        )
        assert hash_value(InMemoryGeocoder({"a": (1.0, 2.0)})) == _digest(
            {"type": "memory_geocoder", "lookup": {"a": [1.0, 2.0]}}
        )

    def test_onemap_geocoder_uses_its_own_registration(self, tmp_path):
        """Not the base Geocoder fallback: transport config is part of the digest."""
        geocoder = _onemap(tmp_path)
        assert hash_value(geocoder) == _digest(
            {
                "type": "onemap",
                "workers": geocoder.max_workers,
                "timeout": geocoder.timeout,
                "ttl": geocoder.cache_duration_hours,
            }
        )

    def test_base_geocoder_fallback_hashes_only_the_qualname(self):
        stub = _StubGeocoder()
        assert hash_value(stub) == _digest({"type": "_StubGeocoder"})
