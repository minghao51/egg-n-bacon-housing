#!/usr/bin/env python3
"""Mechanical lexicon gate for an RF08 edition text.

This exists because one defect shape recurred **seven times** in RS09 and twice in
RS10, always written by a competent author who was not being careless:

    a *screen* stated as a finding about origin.

The ledger can establish "this series carries an annual-ramp signature". It can
never establish "this series was generated". The words that convert the first
into the second are few, ordinary, and irresistible to prose — `generated`,
`fallback`, `identifies`, `is a` — so this gate makes them visible instead of
leaving them to whichever reviewer reads most carefully that round.

Two tiers, deliberately:

* **FORBIDDEN** — phrasings that are defects wherever they appear, because no
  verbatim legacy quotation contains them in a legitimate form: asserting the
  series *was* generated, provenance as fact, proof language, chronology
  claims, and the three registry tokens a draft must never carry.
* **REVIEW** — occurrences that are legitimate inside a verbatim quotation or a
  gate citation but must be read in context. Reported with line numbers and
  never fatal, because a gate that cries wolf gets switched off.

Usage:

    uv run python scripts/tools/check_edition_lexicon.py docs/analytics/editions/<series>/<date>/<series>.md
    uv run python scripts/tools/check_edition_lexicon.py --quiet <path>   # exit code only

Exit codes: 0 clean, 1 forbidden phrasing found, 2 usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FORBIDDEN: tuple[tuple[str, str], ...] = (
    (
        r"\b(?:is|was|are|were)\s+(?:an?\s+)?generated\b",
        "asserts a series WAS generated — a screen cannot establish origin",
    ),
    (
        r"\b(?:is|was|are|were)\s+(?:an?\s+)?generated\s+\w+",
        "calls a series 'a generated <thing>' as fact",
    ),
    (
        r"\bthe\s+generated\s+(?:\w+\s+)?series\b",
        "calls a series 'the generated series' as fact",
    ),
    (
        r"\bidentifies?\s+the\s+generated\b",
        "says a screen identifies a generated series — it identifies a pattern",
    ),
    (
        r"\bgenerated\s+fallback\s+series\b",
        "treats 'generated fallback series' as an established object",
    ),
    (r"\bproven\s+to\s+be\b", "proof language"),
    (r"\bproves?\b", "proof language"),
    (r"\bconfirms?\s+that\b", "proof language ('confirms that')"),
    (r"\bshows?\s+how\b", "proof language ('shows how')"),
    (r"\bdemonstrat(?:es|ed)\b", "proof language"),
    (r"\bpre-?registered\b", "chronology claim without a dated protocol"),
    (r"\bdeclared\s+before\b", "chronology claim without a dated protocol"),
    (r"\bplanned\s+before\b", "chronology claim without a dated protocol"),
    (r"\beditionSha256\b", "registry token a draft must not carry"),
    (r"\bsignoffs?\b", "registry token a draft must not carry"),
    (r"\bapproved\b", "registry token a draft must not carry"),
)

REVIEW: tuple[tuple[str, str], ...] = (
    (r"\bgenerat(?:ed|es|ion)\b", "check: pattern or origin?"),
    (r"\bfallback\b", "check: quoted claim or edition finding?"),
    (r"\bidentif(?:y|ies|ied)\b", "check: identifies a pattern or a provenance fact?"),
    (r"\bcauses?\b", "check: causal vocabulary in own voice?"),
    (r"\bdrives?\b", "check: causal vocabulary in own voice?"),
    (r"\bleads?\s+to\b", "check: causal vocabulary in own voice?"),
    (r"\bimpact\b", "check: causal vocabulary in own voice?"),
    (r"\bbecause\s+of\b", "check: explanatory causal phrasing?"),
)

# A quoted span is where legacy wording legitimately appears. This gate does not
# try to parse quotations — that is what the ledger's legacyQuoteCheck is for —
# it only reports, so a human still sees the line.
QUOTE_HINT = re.compile(r"\"[^\"\n]{20,}\"|_[^_\n]{20,}_|\*[^*\n]{20,}\*")


def _quoted_spans(line: str) -> list[tuple[int, int, str]]:
    """Spans in this line that are quoted or italicised, with their content."""
    spans: list[tuple[int, int, str]] = []
    for pattern in (r'"([^"\n]{8,})"', r"\*([^*\n]{8,})\*", r"_([^_\n]{8,})_", r"“([^”\n]{8,})”"):
        for match in re.finditer(pattern, line):
            spans.append((match.start(1), match.end(1), match.group(1)))
    return spans


def _inside_quotation(line: str, start: int, end: int, quoted_phrases: tuple[str, ...]) -> bool:
    """Is this match genuinely inside a verbatim legacy quotation?

    The earlier version asked only whether the matched *token* appeared inside any
    legacy phrase, which excused own-voice sentences wholesale: the phrase list
    contains "confirms that", so "This confirms that X is a generated fallback"
    passed. Exemption now requires both conditions on the occurrence itself — the
    match sits inside a quoted span on this line, AND that span's content is one of
    the ledger's legacy phrases (compared on whitespace-normalised text). Without
    `--ledger` there are no exemptions at all.
    """
    spans = _quoted_spans(line)
    inside = [
        (span_start, span_end, content)
        for span_start, span_end, content in spans
        if span_start <= start and end <= span_end
    ]
    if not inside:
        return False

    def normalise(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().lower()

    for _span_start, _span_end, content in inside:
        candidate = normalise(content)
        for phrase in quoted_phrases:
            reference = normalise(phrase)
            if candidate == reference or candidate in reference or reference in candidate:
                return True
    return False


def scan(
    path: Path, quoted_phrases: tuple[str, ...] = ()
) -> tuple[list[tuple[int, str, str]], list[tuple[int, str, str]]]:
    """Forbidden and review-required hits, with verbatim legacy quotations exempted."""
    forbidden: list[tuple[int, str, str]] = []
    review: list[tuple[int, str, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for pattern, why in FORBIDDEN:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                if not _inside_quotation(line, match.start(), match.end(), quoted_phrases):
                    forbidden.append((number, why, pattern))
                    break
        for pattern, why in REVIEW:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                if not _inside_quotation(line, match.start(), match.end(), quoted_phrases):
                    review.append((number, why, pattern))
                    break
    return forbidden, review


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("paths", type=Path, nargs="+")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=None,
        help="evidence ledger whose legacyClaims phrases are exempt as verbatim quotations",
    )
    parser.add_argument("--quiet", action="store_true", help="print only forbidden findings")
    args = parser.parse_args(argv)

    quoted: tuple[str, ...] = ()
    if args.ledger is not None:
        try:
            payload = json.loads(args.ledger.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"ERROR: unreadable ledger {args.ledger}: {error}", file=sys.stderr)
            return 2
        quoted = tuple(str(claim["phrase"]) for claim in payload.get("legacyClaims", []))

    failed = False
    for path in args.paths:
        if not path.is_file():
            print(f"ERROR: no such file: {path}", file=sys.stderr)
            return 2
        forbidden, review = scan(path, quoted)
        if forbidden:
            failed = True
        print(f"== {path} ==")
        print(f"  forbidden: {len(forbidden)}   review-required: {len(review)}")
        for number, why, pattern in forbidden:
            print(f"  FAIL line {number}: {why}  (/{pattern}/)")
        if not args.quiet:
            for number, why, _pattern in review:
                print(f"  check line {number}: {why}")

    if failed:
        print("\nFAILED: forbidden phrasing present. A screen is not a provenance finding.")
        return 1
    print("\nPass: no forbidden phrasing. Review-required lines still need a reader.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
