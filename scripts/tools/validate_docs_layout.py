#!/usr/bin/env python3
"""Validate active docs layout and path references.

Checks:
- Active docs and script READMEs only reference existing `docs/` and `scripts/` paths.
- Naming conventions for files in `docs/guides`, `docs/analytics`, and `docs/plans`.
- `docs/` root contains only approved top-level markdown files.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

ACTIVE_REFERENCE_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "scripts" / "README.md",
    REPO_ROOT / "scripts" / "PIPELINE_GUIDE.md",
    REPO_ROOT / "docs" / "README.md",
    REPO_ROOT / "docs" / "guides" / "README.md",
]

ACTIVE_REFERENCE_GLOBS: list[str] = []

ALLOWED_DOCS_ROOT_MD = {
    "README.md",
    "architecture.md",
}

PATH_PATTERN = re.compile(r"(?P<path>(?:docs|scripts)/[A-Za-z0-9_./-]+\.(?:md|py|sh))")

KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
DATED_KEBAB_CASE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$")


@dataclass
class ValidationResults:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def iter_active_reference_files() -> list[Path]:
    files = [p for p in ACTIVE_REFERENCE_FILES if p.exists()]
    for glob_pattern in ACTIVE_REFERENCE_GLOBS:
        files.extend(sorted(REPO_ROOT.glob(glob_pattern)))
    return files


def check_referenced_paths(results: ValidationResults) -> None:
    for file_path in iter_active_reference_files():
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for match in PATH_PATTERN.finditer(text):
            rel = match.group("path")
            target = REPO_ROOT / rel
            if not target.exists():
                results.error(f"Broken path reference in {file_path.relative_to(REPO_ROOT)}: {rel}")


def check_docs_root(results: ValidationResults) -> None:
    for md_file in sorted(DOCS_DIR.glob("*.md")):
        if md_file.name not in ALLOWED_DOCS_ROOT_MD:
            results.warn(
                "Non-foundational markdown at docs root: "
                f"{md_file.relative_to(REPO_ROOT)} (consider moving to guides/ or archive/)"
            )


def check_naming_conventions(results: ValidationResults) -> None:
    for md_file in sorted((DOCS_DIR / "guides").glob("*.md")):
        if not KEBAB_CASE.match(md_file.name):
            results.warn(f"Guide filename is not kebab-case: {md_file.relative_to(REPO_ROOT)}")

    for md_file in sorted((DOCS_DIR / "analytics").glob("*.md")):
        if not KEBAB_CASE.match(md_file.name):
            results.warn(f"Analytics filename is not kebab-case: {md_file.relative_to(REPO_ROOT)}")

    for md_file in sorted((DOCS_DIR / "plans").glob("*.md")):
        if md_file.name == "README.md":
            continue
        if DATED_KEBAB_CASE.match(md_file.name):
            continue
        results.warn(
            "Plan filename does not use preferred dated kebab-case format: "
            f"{md_file.relative_to(REPO_ROOT)}"
        )


def main() -> int:
    results = ValidationResults()
    check_referenced_paths(results)
    check_docs_root(results)
    check_naming_conventions(results)

    if results.errors:
        print("Errors:")
        for err in results.errors:
            print(f"  - {err}")

    if results.warnings:
        print("Warnings:")
        for warning in results.warnings:
            print(f"  - {warning}")

    if not results.errors and not results.warnings:
        print("Validation passed with no findings.")
        return 0

    if results.errors:
        return 1

    print("Validation passed with warnings only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
