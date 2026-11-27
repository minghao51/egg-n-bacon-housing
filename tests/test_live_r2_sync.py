"""Live validation of the R2 sync integrity contract (WS-A3).

The fix under test replaced a size-only skip with an exact size pre-filter plus
``--verify-content``/``--check-content``, recorded ``sha256`` object metadata and
the containment resolver. Two things can only be proven against the real bucket:

1. **Content mode works with a real R2 object** — recorded-metadata compare, and
   the download-and-hash fallback for objects uploaded before metadata existed.
2. **The new enumerated ``evidence/`` scope** maps exactly the pipeline
   artifacts the evidence producers read, and refuses anything else — the CI
   provisioning path.

Everything here is skipped unless ``EGG_LIVE=1``; the R2 tests additionally skip
when R2 credentials are absent. Every test is **read-only**: no upload, no
download into the repo, no bucket mutation. The one transfer is a single small
object into a temporary directory, for the content comparison.

Run them:

    EGG_LIVE=1 uv run pytest tests/ -m live -q --no-cov

Provisioning the evidence scope (the CI path, an owner decision because it
uploads ~110MB of regenerable pipeline data):

    uv run python scripts/00_sync_data.py --upload --only evidence
    uv run python scripts/00_sync_data.py --verify-content --only evidence
"""

import importlib.util
import os
import tempfile
from pathlib import Path

import pytest

from egg_n_bacon_housing.config import settings

_LIVE = os.environ.get("EGG_LIVE") == "1"

pytestmark = [
    pytest.mark.live,
    pytest.mark.api,
    pytest.mark.skipif(
        not _LIVE, reason="live network tests are opt-in: set EGG_LIVE=1 to run against R2"
    ),
]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

# The pipeline artifacts the evidence producers re-measure. Kept as literal
# paths (not imported) so this test fails if the script's enumerated scope
# drifts from what .github/workflows/evidence.yml requires.
REQUIRED_EVIDENCE_FILES: tuple[str, ...] = (
    "04_platinum/unified_dataset.parquet",
    "01_bronze/raw_hdb_rental.parquet",
    "02_silver/geocoded_validated.parquet",
    "01_bronze/raw_hdb_resale.parquet",
    "01_bronze/raw_condo_transactions.parquet",
    "01_bronze/raw_school_directory.parquet",
    "01_bronze/raw_mrt_stations.parquet",
)


def _load_sync_module():
    """Load scripts/00_sync_data.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("sync_data_live", _SCRIPTS / "00_sync_data.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sync():
    return _load_sync_module()


def _r2_configured() -> bool:
    return bool(
        settings.r2_account_id
        and settings.r2_access_key_id.get_secret_value().strip()
        and settings.r2_secret_access_key.get_secret_value().strip()
        and settings.r2_bucket
    )


requires_r2 = pytest.mark.skipif(
    not _r2_configured(),
    reason="R2 credentials not configured (R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY)",
)


class TestEvidenceScope:
    """The enumerated scope is exactly the producers' input list — nothing more."""

    def test_scope_matches_the_evidence_workflow_input_list(self, sync):
        assert set(sync.EVIDENCE_FILES) == set(REQUIRED_EVIDENCE_FILES)
        # Order is the workflow's check order; duplicates would silently double
        # an upload.
        assert len(sync.EVIDENCE_FILES) == len(set(sync.EVIDENCE_FILES))

    def test_every_scope_key_is_contained_in_the_pipeline_root(self, sync):
        keys = sync._evidence_keys()
        assert set(keys) == {f"evidence/{rel}" for rel in REQUIRED_EVIDENCE_FILES}
        for key, local_path in keys.items():
            resolved = sync._resolve_local_target(key, sync.EVIDENCE_PREFIX, sync.PIPELINE_DATA_DIR)
            assert resolved == local_path
            assert resolved.is_relative_to(sync.PIPELINE_DATA_DIR)

    def test_unenumerated_remote_keys_are_out_of_scope(self, sync):
        enumerated = next(iter(sync._evidence_keys()))
        remote = {enumerated: 1, "evidence/03_gold/experiment.parquet": 1}
        assert sync._out_of_scope_keys(sync.EVIDENCE_PREFIX, remote) == [
            "evidence/03_gold/experiment.parquet"
        ]
        # The whole-directory scopes never filter.
        assert sync._out_of_scope_keys(sync.MANUAL_PREFIX, {"manual/anything.csv": 1}) == []
        assert sync._out_of_scope_keys(sync.GEOCACHE_PREFIX, {"geocache/a.parquet": 1}) == []

    def test_default_run_does_not_enumerate_pipeline_artifacts(self, sync):
        # A routine sync must never start moving ~110MB of pipeline parquet.
        assert [prefix for prefix, _ in sync._sync_sets()] == [
            sync.MANUAL_PREFIX,
            sync.GEOCACHE_PREFIX,
        ]
        assert [prefix for prefix, _ in sync._sync_sets(sync.EVIDENCE_PREFIX)] == [
            sync.EVIDENCE_PREFIX
        ]

    def test_scope_rejects_traversal_keys(self, sync):
        for bad in ("evidence/../manual/x.parquet", "evidence//etc/passwd", "evidence/"):
            with pytest.raises(sync.KeyRejectedError):
                sync._resolve_local_target(bad, sync.EVIDENCE_PREFIX, sync.PIPELINE_DATA_DIR)


@requires_r2
class TestLiveBucket:
    """Read-only checks against the real bucket."""

    def test_content_mode_matches_a_real_object(self, sync):
        """``--verify-content``'s comparison, against a real R2 object."""
        s3 = sync._s3_client()
        bucket = settings.r2_bucket
        remote = sync._list_remote(s3, bucket, sync.MANUAL_PREFIX)
        assert remote, (
            f"no objects under {sync.MANUAL_PREFIX}/ in bucket {bucket!r}: upload the manual "
            "set first (uv run python scripts/00_sync_data.py --upload --only manual)"
        )

        # Smallest object present locally too — the comparison is on real bytes,
        # so keep the download to one small file.
        candidates = []
        for key, size in remote.items():
            try:
                local_path = sync._resolve_local_target(
                    key, sync.MANUAL_PREFIX, sync.MANUAL_DATA_DIR
                )
            except sync.KeyRejectedError:
                continue
            if local_path.is_file():
                candidates.append((size, key, local_path))
        if not candidates:
            pytest.skip("no object is present both in R2 and locally to compare")
        size, key, local_path = min(candidates)

        with tempfile.TemporaryDirectory() as tmpdir:
            matches = sync._local_content_matches(s3, bucket, key, local_path, Path(tmpdir))

        assert matches, (
            f"CONTENT MISMATCH against the real bucket for {key} ({size} bytes): the local copy "
            "differs from the uploaded object"
        )
        # And a deliberately wrong local file must not be reported as matching.
        with tempfile.TemporaryDirectory() as tmpdir:
            scratch = Path(tmpdir) / "s2"
            scratch.mkdir()  # boto3 does not create the scratch parent itself
            wrong = Path(tmpdir) / "wrong"
            wrong.write_bytes(b"not the uploaded bytes")
            assert not sync._local_content_matches(s3, bucket, key, wrong, scratch)

    def test_evidence_scope_is_listable_and_consistent(self, sync, capsys):
        """The provisioning path runs against the real bucket without raising."""
        s3 = sync._s3_client()
        remote = sync._list_remote(s3, settings.r2_bucket, sync.EVIDENCE_PREFIX)
        out_of_scope = sync._out_of_scope_keys(sync.EVIDENCE_PREFIX, remote)
        assert out_of_scope == [], (
            f"objects under {sync.EVIDENCE_PREFIX}/ are outside the enumerated scope: {out_of_scope}"
        )

        sync.verify(only=sync.EVIDENCE_PREFIX)

        output = capsys.readouterr().out
        for key in sync._evidence_keys():
            # Each enumerated artifact is reported one way or the other; a
            # silently missing line would hide an unprovisioned layer.
            assert f"MISSING LOCALLY:  {key}" in output or key in output, (
                f"{key} was not reported by --verify --only evidence:\n{output}"
            )
