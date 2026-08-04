#!/usr/bin/env python3
"""Validate required repository-local agent skills and AGENTS.md routing."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SKILLS = {
    "change-hamilton-pipeline",
    "change-data-ingestion",
}


def _frontmatter_value(metadata: str, field: str) -> str | None:
    match = re.search(rf"^{field}:\s*(.+?)\s*$", metadata, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def _skills_section(agents_text: str) -> str:
    match = re.search(
        r"^## Repository Agent Skills\n(?P<section>.*?)(?=^## |\Z)",
        agents_text,
        re.DOTALL | re.MULTILINE,
    )
    return match.group("section") if match else ""


def validate(repo_root: Path = REPO_ROOT) -> list[str]:
    """Return validation errors for required skills and their AGENTS.md routes."""
    errors: list[str] = []
    agents_path = repo_root / "AGENTS.md"
    if not agents_path.exists():
        return ["Missing AGENTS.md"]

    agents_text = agents_path.read_text(encoding="utf-8")
    skills_section = _skills_section(agents_text)
    skills_dir = repo_root / ".agents" / "skills"

    for skill_name in REQUIRED_SKILLS:
        skill_file = skills_dir / skill_name / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"Missing required skill: {skill_file.relative_to(repo_root)}")
            continue

        text = skill_file.read_text(encoding="utf-8")
        frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
        if not frontmatter:
            errors.append(f"Missing frontmatter: {skill_file.relative_to(repo_root)}")
            continue

        metadata = frontmatter.group(1)
        name = _frontmatter_value(metadata, "name")
        description = _frontmatter_value(metadata, "description")
        if name != skill_name:
            errors.append(f"Skill name must match directory: {skill_name}")
        if description is None or len(description) < 20:
            errors.append(f"Skill description is missing or too short: {skill_name}")

        route = f".agents/skills/{skill_name}/SKILL.md"
        if route not in skills_section:
            errors.append(f"AGENTS.md does not route to {route} in Repository Agent Skills")

    return errors


def main() -> int:
    errors = validate()

    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Validated {len(REQUIRED_SKILLS)} required agent skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
