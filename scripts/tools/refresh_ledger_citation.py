#!/usr/bin/env python3
"""Refresh a study's ledger citations after a regeneration.

The programme keeps hitting one defect class: a study's ledger is regenerated,
its hash moves, and the edition text (and the evidence pack header) still cite
the old hash and byte count. Every regeneration therefore turns the provenance
paragraph into unverifiable prose, and a reviewer is right to block it.

This rewrites exactly the ledger citation - the 64-hex sha256 and the byte count
next to it - in the places that carry it, and prints a unified diff so the change
is reviewable rather than silent.

Usage:
    uv run python scripts/tools/refresh_ledger_citation.py --series lease-decay
    uv run python scripts/tools/refresh_ledger_citation.py --series mrt-impact --date 2026-11-20
    uv run python scripts/tools/refresh_ledger_citation.py --series lease-decay --dry-run
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DATE = "2026-11-20"
# <rs-prefix>-<series>-evidence.json
LEDGER_GLOB = "rs*"

# The series slug and date become path components, so they are validated rather
# than trusted: a slug is a lowercase dash-separated token and a date is ISO.
SERIES_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

HEX = re.compile(r"\b[0-9a-f]{64}\b")
# The byte count is only rewritten when it sits beside the hash this tool just
# wrote. A bare count elsewhere on the line may describe a DIFFERENT artefact
# (a superseded ledger, a frozen source), and rewriting that would make a true
# sentence false - which this tool already did once, to a stage-1 ledger size.
HASH_THEN_BYTES = re.compile(
    r"(?P<head>(?:sha256|SHA-256)?[^0-9a-f]{0,12})(?P<hash>[0-9a-f]{64})"
    r"(?P<mid>[`\"',;:()\]\s]*)(?P<size>\d[\d,]*\s*bytes)"
)


def ledger_path(series: str) -> Path:
    candidates = sorted(
        p
        for p in (REPO / "docs/implementation/artifacts").glob(
            f"{LEDGER_GLOB}-{series}-evidence.json"
        )
        if p.is_file()
    )
    if len(candidates) != 1:
        raise SystemExit(f"expected exactly one ledger for {series}, found {candidates}")
    return candidates[0]


def pack_path(series: str, date: str) -> Path | None:
    matches = sorted((REPO / "docs/implementation").glob(f"{date}-rs*-{series}-evidence.md"))
    return matches[0] if len(matches) == 1 else None


def edition_path(series: str, date: str) -> Path:
    path = REPO / "docs/analytics/editions" / series / date / f"{series}.md"
    if not path.is_file():
        raise SystemExit(f"no edition text at {path}")
    return path


def rewrite(
    text: str, ledger_name: str, sha: str, size: str, mode: str = "ledger-line"
) -> tuple[str, list[str], list[str]]:
    """Refresh the ledger hash on lines naming this ledger.

    The byte count changes only when it follows the hash in the recognized
    hash-then-bytes form. A line with multiple different hashes is ambiguous
    unless it already contains the current ledger hash, and is left untouched.
    """
    changed: list[str] = []
    reviews: list[str] = []
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        if ledger_name not in line:
            out.append(line)
            continue
        hashes = list(HEX.finditer(line))
        if not hashes or any(match.group(0) == sha for match in hashes):
            out.append(line)
            continue
        if len(hashes) != 1:
            reviews.append(line.strip()[:160])
            out.append(line)
            continue

        def _sub(match: re.Match[str]) -> str:
            return f"{match.group('head')}{sha}{match.group('mid')}{size}"

        new, count = HASH_THEN_BYTES.subn(_sub, line, count=1)
        if count == 0:
            if mode == "hash-then-bytes":
                reviews.append(line.strip()[:160])
                out.append(line)
                continue
            new = HEX.sub(sha, line, count=1)
        if new != line:
            changed.append(line.strip()[:120])
        out.append(new)
    return "".join(out), changed, reviews


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--series", required=True)
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("ledger-line", "hash-then-bytes"),
        default="ledger-line",
        help=(
            "ledger-line (default) refreshes a lone hash on any line naming "
            "the ledger; hash-then-bytes limits refreshes to hash/count pairs"
        ),
    )
    args = parser.parse_args(argv)

    ledger = ledger_path(args.series)
    if not SERIES_PATTERN.match(args.series):
        raise SystemExit(f"not a series slug: {args.series!r}")
    if not DATE_PATTERN.match(args.date):
        raise SystemExit(f"not an ISO date: {args.date!r}")
    raw = ledger.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    size = f"{len(raw):,} bytes"
    name = ledger.name
    print(f"ledger: {ledger.relative_to(REPO)}  sha256 {sha}  {size}")

    targets = [edition_path(args.series, args.date)]
    pack = pack_path(args.series, args.date)
    if pack:
        targets.append(pack)

    for target in targets:
        original = target.read_text(encoding="utf-8")
        updated, changed, reviews = rewrite(original, name, sha, size, args.mode)
        rel = target.relative_to(REPO)
        for line in reviews:
            print(f"  NEEDS REVIEW (not rewritten): {line}", file=sys.stderr)
        if updated == original:
            if reviews:
                print(f"  {rel}: unchanged; citation needs review")
            elif any(name in line and sha in line for line in original.splitlines()):
                print(f"  {rel}: already current")
            else:
                print(f"  {rel}: no stale ledger hash found")
            continue
        diff = "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=str(rel),
                tofile=str(rel) + " (refreshed)",
                n=0,
            )
        )
        print(diff, end="")
        print(f"  {rel}: {len(changed)} line(s) updated")
        if not args.dry_run:
            target.write_text(updated, encoding="utf-8")
        remaining = [
            line.strip()[:160]
            for line in updated.splitlines()
            if name in line and HEX.search(line) and sha not in line
        ]
        for line in remaining:
            print(f"  STALE ledger hash remains: {line}", file=sys.stderr)

    unresolved = False
    for target in targets:
        content = (
            target.read_text(encoding="utf-8")
            if not args.dry_run
            else rewrite(target.read_text(encoding="utf-8"), name, sha, size, args.mode)[0]
        )
        unresolved |= any(
            name in line and HEX.search(line) and sha not in line for line in content.splitlines()
        )
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
