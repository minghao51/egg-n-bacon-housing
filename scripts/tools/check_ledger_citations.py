#!/usr/bin/env python3
"""Resolve every ledger path an edition text cites.

Three review rounds on RF08 found the same defect shape: a sentence printing a
field path that does not resolve in the ledger it cites. The claim was supported;
the pointer was wrong or stale. A reader cannot check such a claim, and a reviewer
spends a round finding it.

This walks the backticked dotted paths in an edition text and resolves each one
against that study's ledger using the programme's own rule:

- dicts by key, with a case-insensitive fallback;
- lists by the item's ``id`` (the rule ``claimKeyCheck`` already applies);
- ``X[]`` means "every element of X", so a field must exist on all of them;
- ``[0]`` / ``[3]`` index a list positionally;
- ``key["1.96"]`` / ``key['1.96']`` address a dict key that contains dots, so a
  key such as ``1.96`` is not mistaken for a two-segment path.

Paths whose first segment is not a top-level ledger key are ignored: prose also
backticks code identifiers, SQL-ish names and file paths, and none of those are
claims about the ledger.

Usage
    uv run python scripts/tools/check_ledger_citations.py            # every edition
    uv run python scripts/tools/check_ledger_citations.py --series lease-decay
    uv run python scripts/tools/check_ledger_citations.py --quiet    # exit code only

Exit codes: 0 every cited path resolves, 1 unresolved paths found, 2 usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "docs/implementation/artifacts"
EDITIONS = REPO / "docs/analytics/editions"
DEFAULT_DATE = "2026-11-20"

# A backticked ledger path: dotted names, `X[]`, positional `[0]`, and bracket
# keys that carry dots or spaces, e.g. `tokens["1.96"]`. A bracket key is a
# single segment, so `tokens["1.96"]` is not read as `tokens` -> `1` -> `96`.
_SEGMENT = r"""(?:\.[A-Za-z0-9_]+|\[\s*\d+\s*\]|\[\]|\["[^"`]*"\]|\['[^'`]*'\])"""
CITATION = re.compile(r"`([A-Za-z][A-Za-z0-9_]*" + _SEGMENT + r"+)`")

# The same segment grammar, anchored, for turning a path into resolve steps.
_SEG_RE = re.compile(r"""\.([A-Za-z0-9_]+)|\[\s*(\d+)\s*\]|\["([^"]*)"\]|\['([^']*)'\]|\[\]""")


Step = tuple[str, object]


def split_path(path: str) -> list[Step] | None:
    """Turn a ledger path into the steps ``resolve`` applies.

    Returns ``None`` when ``path`` is not a form this tool understands.
    """
    head = re.match(r"[A-Za-z][A-Za-z0-9_]*", path)
    if head is None:
        return None
    steps: list[Step] = [("key", head.group(0))]
    pos = head.end()
    while pos < len(path):
        match = _SEG_RE.match(path, pos)
        if match is None:
            return None
        pos = match.end()
        if match.group(1) is not None:
            steps.append(("key", match.group(1)))
        elif match.group(2) is not None:
            steps.append(("index", int(match.group(2))))
        elif match.group(3) is not None:
            steps.append(("key", match.group(3)))
        elif match.group(4) is not None:
            steps.append(("key", match.group(4)))
        else:
            steps.append(("each", None))
    return steps


def resolve(doc: object, steps: list[Step]) -> bool:
    """True when ``steps`` resolves against ``doc`` under the programme's rule."""
    if not steps:
        return True
    kind, value = steps[0]
    rest = steps[1:]

    if kind == "each":
        # `X[]`: the field must exist on every element of the list.
        return isinstance(doc, list) and bool(doc) and all(resolve(item, rest) for item in doc)

    if kind == "index":
        assert isinstance(value, int)
        return isinstance(doc, list) and value < len(doc) and resolve(doc[value], rest)

    assert isinstance(value, str)
    key = value

    if isinstance(doc, list):
        if key.isdigit():
            index = int(key)
            return index < len(doc) and resolve(doc[index], rest)
        members = [x for x in doc if isinstance(x, dict) and str(x.get("id")) == key]
        return bool(members) and all(resolve(item, rest) for item in members)

    if isinstance(doc, dict):
        if key in doc:
            return resolve(doc[key], rest)
        lowered = {name.lower(): name for name in doc}
        if key.lower() in lowered:
            return resolve(doc[lowered[key.lower()]], rest)

    return False


def ledger_for(series: str) -> Path | None:
    matches = sorted(ARTIFACTS.glob(f"rs*-{series}-evidence.json"))
    return matches[0] if matches else None


def text_for(series: str, date: str) -> Path | None:
    path = EDITIONS / series / date / f"{series}.md"
    return path if path.is_file() else None


def series_dirs(date: str) -> list[str]:
    return sorted(
        path.parent.parent.name
        for path in EDITIONS.glob(f"*/{date}/*.md")
        if path.parent.parent.name != "legacy"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--series", nargs="*", help="limit to these series slugs")
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    targets = args.series or series_dirs(args.date)
    total_unresolved = 0
    for series in targets:
        ledger_path = ledger_for(series)
        text_path = text_for(series, args.date)
        if ledger_path is None or text_path is None:
            print(f"{series}: no ledger or no edition text — skipped", file=sys.stderr)
            continue
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        text = text_path.read_text(encoding="utf-8")
        top_level = set(ledger)

        cited: list[tuple[str, list[Step]]] = []
        for match in sorted(set(CITATION.findall(text))):
            steps = split_path(match)
            if steps is not None and steps[0][1] in top_level:
                cited.append((match, steps))
        unresolved = [match for match, steps in cited if not resolve(ledger, steps)]
        total_unresolved += len(unresolved)
        status = "ok" if not unresolved else f"{len(unresolved)} UNRESOLVED"
        print(f"{series:30} cited={len(cited):3}  {status}")
        for path in unresolved:
            print(f"    unresolved: {path}")

    if total_unresolved:
        print(f"\nFAILED: {total_unresolved} cited ledger path(s) do not resolve.")
        return 1
    if not args.quiet:
        print("\nPass: every cited ledger path resolves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
