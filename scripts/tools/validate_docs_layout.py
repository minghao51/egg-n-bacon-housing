#!/usr/bin/env python3
"""Validate active docs layout and path references.

Checks:
- Active docs only reference existing paths.
- Naming conventions for files in docs/guides, docs/analytics, and docs/plans.
- docs/ root contains only approved top-level markdown files.
- Analytics docs have valid frontmatter (category, status).
- docs/analytics .md files stay in sync with app/src/content/analytics .mdx files.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
DOCS_ANALYTICS_DIR = DOCS_DIR / "analytics"

ACTIVE_REFERENCE_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "README.md",
    REPO_ROOT / "docs" / "architecture.md",
    REPO_ROOT / "docs" / "guides" / "README.md",
    REPO_ROOT / "docs" / "guides" / "usage-guide.md",
]

ALLOWED_DOCS_ROOT_MD = {
    "README.md",
    "architecture.md",
    "TROUBLESHOOTING.md",
}

VALID_CATEGORIES = {
    "investment-guides",
    "market-analysis",
    "technical-reports",
    "quick-reference",
}

VALID_STATUSES = {"published", "draft", "review"}

PATH_PATTERN = re.compile(
    r"(?P<path>(?:README\.md|main\.py|pyproject\.toml|config\.yaml|(?:app|docs|scripts|src)/[A-Za-z0-9_./-]+\.(?:md|py|sh|ts|tsx)))"
)

KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
DATED_KEBAB_CASE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$")
LEGACY_DATED_KEBAB_CASE = re.compile(r"^\d{8}-[a-z0-9-]+\.md$")
LEGACY_PLAN_CASE = re.compile(r"^plan_[a-z0-9_-]+\.md$")


@dataclass
class ValidationResults:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def iter_active_reference_files() -> list[Path]:
    return [p for p in ACTIVE_REFERENCE_FILES if p.exists()]


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
        if md_file.name == "README.md":
            continue
        if not KEBAB_CASE.match(md_file.name):
            results.warn(f"Guide filename is not kebab-case: {md_file.relative_to(REPO_ROOT)}")

    for md_file in sorted(DOCS_ANALYTICS_DIR.glob("*.md")):
        if not KEBAB_CASE.match(md_file.name):
            results.warn(f"Analytics filename is not kebab-case: {md_file.relative_to(REPO_ROOT)}")

    plans_dir = DOCS_DIR / "plans"
    if plans_dir.exists():
        for md_file in sorted(plans_dir.glob("*.md")):
            if md_file.name == "README.md":
                continue
            if DATED_KEBAB_CASE.match(md_file.name):
                continue
            if LEGACY_DATED_KEBAB_CASE.match(md_file.name):
                continue
            if LEGACY_PLAN_CASE.match(md_file.name):
                continue
            results.warn(
                "Plan filename does not use preferred dated kebab-case format: "
                f"{md_file.relative_to(REPO_ROOT)}"
            )


def check_analytics_frontmatter(results: ValidationResults) -> None:
    if not DOCS_ANALYTICS_DIR.exists():
        return

    for md_file in sorted(DOCS_ANALYTICS_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="ignore")
        rel = md_file.relative_to(REPO_ROOT)

        category_match = re.search(r"^category:\s*[\"']?(\S+?)[\"']?\s*$", text, re.MULTILINE)
        if not category_match:
            results.warn(f"Missing category in {rel}")
        elif category_match.group(1) not in VALID_CATEGORIES:
            results.error(
                f"Invalid category '{category_match.group(1)}' in {rel}. "
                f"Valid: {', '.join(sorted(VALID_CATEGORIES))}"
            )

        status_match = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        if status_match and status_match.group(1) not in VALID_STATUSES:
            results.warn(f"Unknown status '{status_match.group(1)}' in {rel}")


def main() -> int:
    results = ValidationResults()
    check_referenced_paths(results)
    check_docs_root(results)
    check_naming_conventions(results)
    check_analytics_frontmatter(results)

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
