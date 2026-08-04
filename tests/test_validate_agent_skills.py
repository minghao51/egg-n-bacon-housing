"""Tests for repository-local agent-skill validation."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "tools" / "validate_agent_skills.py"
SKILL_NAMES = ("change-hamilton-pipeline", "change-data-ingestion")


@pytest.fixture(scope="module")
def validator_module():
    spec = importlib.util.spec_from_file_location("validate_agent_skills", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_repo(root: Path) -> None:
    routes = "\n".join(f".agents/skills/{name}/SKILL.md" for name in SKILL_NAMES)
    (root / "AGENTS.md").write_text(
        f"# Agent Notes\n\n## Repository Agent Skills\n\n{routes}\n",
        encoding="utf-8",
    )
    for name in SKILL_NAMES:
        skill_file = root / ".agents" / "skills" / name / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(
            f"---\nname: {name}\ndescription: A sufficiently descriptive required repository skill.\n---\n",
            encoding="utf-8",
        )


def test_validate_accepts_valid_skills(tmp_path: Path, validator_module) -> None:
    _write_repo(tmp_path)

    assert validator_module.validate(tmp_path) == []


def test_validate_rejects_missing_routed_skill(tmp_path: Path, validator_module) -> None:
    _write_repo(tmp_path)
    (tmp_path / ".agents" / "skills" / "change-data-ingestion" / "SKILL.md").unlink()

    assert "Missing required skill" in "\n".join(validator_module.validate(tmp_path))


def test_validate_rejects_invalid_frontmatter_and_missing_route(
    tmp_path: Path, validator_module
) -> None:
    _write_repo(tmp_path)
    skill_file = tmp_path / ".agents" / "skills" / "change-hamilton-pipeline" / "SKILL.md"
    skill_file.write_text("# no frontmatter\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "# Agent Notes\n\n## Repository Agent Skills\n\nNo routes here.\n",
        encoding="utf-8",
    )

    errors = "\n".join(validator_module.validate(tmp_path))
    assert "Missing frontmatter" in errors
    assert "does not route" in errors
