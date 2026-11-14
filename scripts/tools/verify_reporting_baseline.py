#!/usr/bin/env python3
"""Verify the preserved reporting baseline (RF00).

The baseline manifest pins the bytes of the historical research sources and the
published v1 dashboard assets that the 2026 reporting refresh must not silently
rewrite. This tool reports drift; it never edits, downloads or regenerates data.

Usage:
    uv run python scripts/tools/verify_reporting_baseline.py
    uv run python scripts/tools/verify_reporting_baseline.py --sources
    uv run python scripts/tools/verify_reporting_baseline.py --assets
    uv run python scripts/tools/verify_reporting_baseline.py --json

Exit codes:
    0  every requested check passed
    1  drift, a missing file or an invalid manifest
    2  usage error (bad manifest path or arguments)

`--sources` compares the *current* `docs/analytics/*.md` sources with the
baseline. It is the RF02 pre-edit gate: run it before editing report text. After
an approved correction lands it is expected to fail, because the frozen copies
under `docs/analytics/editions/legacy/<edition>/` are the preserved originals.
`--assets` compares assets marked immutable. If an approved source revision
intentionally changes one, update the manifest in a reviewed change instead of
ignoring the failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    REPO_ROOT / "docs" / "analytics" / "editions" / "legacy" / "2026-11-12" / "manifest.json"
)


@dataclass(frozen=True)
class Entry:
    """One pinned file in the baseline manifest."""

    kind: str
    path: str
    sha256: str
    bytes: int
    mutable: bool
    frozen_path: str | None


@dataclass
class VerificationResult:
    """Outcome of one verification run."""

    manifest: str
    edition: object
    checked: dict[str, int]
    problems: list[str]

    def as_json(self) -> dict[str, object]:
        return {
            "manifest": self.manifest,
            "edition": self.edition,
            "checked": self.checked,
            "problems": self.problems,
        }


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_entries(manifest_path: Path) -> tuple[dict[str, object], list[Entry]]:
    if not manifest_path.is_file():
        raise SystemExit(f"Baseline manifest not found: {manifest_path}")

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unreadable baseline manifest {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Baseline manifest is not a JSON object: {manifest_path}")

    entries: list[Entry] = []
    for kind, key in (("source", "sources"), ("asset", "assets")):
        items = payload.get(key, [])
        if not isinstance(items, list):
            raise SystemExit(f"Manifest field '{key}' must be a list")
        for item in items:
            if not isinstance(item, dict):
                raise SystemExit(f"Manifest entry in '{key}' is not an object")
            missing = {"path", "sha256", "bytes"} - set(item)
            if missing:
                raise SystemExit(f"Manifest entry in '{key}' lacks fields: {sorted(missing)}")
            try:
                declared_bytes = int(item["bytes"])
            except (TypeError, ValueError) as exc:
                raise SystemExit(
                    f"Manifest entry in '{key}' has a non-integer byte count: {item['bytes']!r}"
                ) from exc
            entries.append(
                Entry(
                    kind=kind,
                    path=str(item["path"]),
                    sha256=str(item["sha256"]),
                    bytes=declared_bytes,
                    mutable=bool(item.get("mutable", False)),
                    frozen_path=item.get("frozenPath"),
                )
            )
    return payload, entries


def check_entry(entry: Entry, display_path: str) -> str | None:
    target = REPO_ROOT / display_path
    if not target.is_file():
        return f"missing {entry.kind}: {display_path}"
    actual_bytes = target.stat().st_size
    actual_hash = sha256_of(target)
    if actual_bytes != entry.bytes or actual_hash != entry.sha256:
        return (
            f"{entry.kind} drift: {display_path} "
            f"expected {entry.bytes}B/{entry.sha256[:12]}… "
            f"found {actual_bytes}B/{actual_hash[:12]}…"
        )
    return None


def verify(manifest_path: Path, check_sources: bool, check_assets: bool) -> VerificationResult:
    payload, entries = load_entries(manifest_path)
    problems: list[str] = []
    checked: dict[str, int] = {"frozen": 0, "source": 0, "asset": 0}

    for entry in entries:
        if entry.frozen_path:
            checked["frozen"] += 1
            problem = check_entry(entry, entry.frozen_path)
            if problem:
                problems.append(problem)

    if check_sources:
        for entry in entries:
            if entry.kind != "source":
                continue
            checked["source"] += 1
            problem = check_entry(entry, entry.path)
            if problem:
                problems.append(problem)

    if check_assets:
        skipped = 0
        for entry in entries:
            if entry.kind != "asset":
                continue
            if entry.mutable:
                skipped += 1
                continue
            checked["asset"] += 1
            problem = check_entry(entry, entry.path)
            if problem:
                problems.append(problem)
        checked["asset_skipped_mutable"] = skipped

    return VerificationResult(
        manifest=str(manifest_path.relative_to(REPO_ROOT)),
        edition=payload.get("edition"),
        checked=checked,
        problems=problems,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Verify the preserved reporting baseline.").splitlines()[0]
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Baseline manifest to verify (default: the preserved legacy edition).",
    )
    parser.add_argument(
        "--sources",
        action="store_true",
        help="Also compare current docs/analytics sources with the baseline.",
    )
    parser.add_argument(
        "--assets",
        action="store_true",
        help="Also compare pinned immutable assets with the baseline.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output.")
    args = parser.parse_args(argv)

    result = verify(args.manifest.resolve(), args.sources, args.assets)
    problems = result.problems

    if args.json:
        json.dump(result.as_json(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        checked = result.checked
        print(
            f"Baseline {result.edition}: verified {checked.get('frozen', 0)} frozen sources, "
            f"{checked.get('source', 0)} live sources, "
            f"{checked.get('asset', 0)} pinned assets."
        )
        if problems:
            print(f"DRIFT ({len(problems)}):")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print("Pass: baseline bytes match.")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
