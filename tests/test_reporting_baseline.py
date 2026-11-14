"""Tests for the preserved reporting baseline verifier."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "tools" / "verify_reporting_baseline.py"


@pytest.fixture(scope="module")
def verifier_module():
    spec = importlib.util.spec_from_file_location("verify_reporting_baseline", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve their module through sys.modules during class creation.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(root: Path, relative: str, content: str) -> Path:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _entry(path: Path, root: Path, **extra: object) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        **extra,
    }


def _write_repo(root: Path, *, asset_mutable: bool = False) -> Path:
    source = _write(root, "docs/analytics/study.md", "# Study\n\nOriginal text.\n")
    frozen = _write(
        root, "docs/analytics/editions/legacy/2026-11-12/study.md", "# Study\n\nOriginal text.\n"
    )
    asset = _write(root, "app/public/data/dashboard_overview.json.gz", "payload")
    manifest = {
        "edition": "legacy-2026-11-12",
        "sources": [_entry(source, root, frozenPath=str(frozen.relative_to(root)))],
        "assets": [_entry(asset, root, mutable=asset_mutable)],
    }
    return _write(
        root, "docs/analytics/editions/legacy/2026-11-12/manifest.json", json.dumps(manifest)
    )


def test_verify_passes_on_matching_bytes(tmp_path: Path, verifier_module, monkeypatch) -> None:
    monkeypatch.setattr(verifier_module, "REPO_ROOT", tmp_path)
    manifest = _write_repo(tmp_path)

    result = verifier_module.verify(manifest, check_sources=True, check_assets=True)

    assert result.problems == []
    assert result.checked["frozen"] == 1
    assert result.checked["source"] == 1
    assert result.checked["asset"] == 1


def test_verify_detects_frozen_copy_drift(tmp_path: Path, verifier_module, monkeypatch) -> None:
    monkeypatch.setattr(verifier_module, "REPO_ROOT", tmp_path)
    manifest = _write_repo(tmp_path)
    _write(
        tmp_path, "docs/analytics/editions/legacy/2026-11-12/study.md", "# Study\n\nRewritten.\n"
    )

    result = verifier_module.verify(manifest, check_sources=False, check_assets=False)

    assert any("source drift" in problem for problem in result.problems)


def test_source_drift_only_reported_when_requested(
    tmp_path: Path, verifier_module, monkeypatch
) -> None:
    monkeypatch.setattr(verifier_module, "REPO_ROOT", tmp_path)
    manifest = _write_repo(tmp_path)
    _write(tmp_path, "docs/analytics/study.md", "# Study\n\nCorrected text.\n")

    assert verifier_module.verify(manifest, check_sources=False, check_assets=False).problems == []
    assert verifier_module.verify(manifest, check_sources=True, check_assets=False).problems


def test_mutable_asset_is_skipped(tmp_path: Path, verifier_module, monkeypatch) -> None:
    monkeypatch.setattr(verifier_module, "REPO_ROOT", tmp_path)
    manifest = _write_repo(tmp_path, asset_mutable=True)
    _write(tmp_path, "app/public/data/dashboard_overview.json.gz", "regenerated")

    result = verifier_module.verify(manifest, check_sources=False, check_assets=True)

    assert result.problems == []
    assert result.checked["asset"] == 0
    assert result.checked["asset_skipped_mutable"] == 1


def test_missing_file_is_reported(tmp_path: Path, verifier_module, monkeypatch) -> None:
    monkeypatch.setattr(verifier_module, "REPO_ROOT", tmp_path)
    manifest = _write_repo(tmp_path)
    (tmp_path / "app/public/data/dashboard_overview.json.gz").unlink()

    result = verifier_module.verify(manifest, check_sources=False, check_assets=True)

    assert any("missing asset" in problem for problem in result.problems)


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        json.dumps({"sources": [{"path": "a.md", "sha256": "x"}]}),
        json.dumps({"assets": [{"path": "a", "sha256": "x", "bytes": "many"}]}),
    ],
)
def test_invalid_manifest_exits(tmp_path: Path, verifier_module, monkeypatch, payload: str) -> None:
    monkeypatch.setattr(verifier_module, "REPO_ROOT", tmp_path)
    manifest = _write(tmp_path, "manifest.json", payload)

    with pytest.raises(SystemExit):
        verifier_module.load_entries(manifest)


def test_default_manifest_points_at_preserved_edition(verifier_module) -> None:
    assert verifier_module.DEFAULT_MANIFEST.is_file()
    assert verifier_module.DEFAULT_MANIFEST.parent.name == "2026-11-12"
