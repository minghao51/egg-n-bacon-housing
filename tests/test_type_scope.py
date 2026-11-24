"""Guard the mypy file scope so it cannot silently shrink again.

``[tool.mypy].files`` in ``pyproject.toml`` is the only thing that decides
which modules mypy actually checks. Adding a module to that list is invisible
in code review, but *removing* one quietly drops type coverage while ``mypy``
still prints "Success" — so whole-project coverage can appear to exist when it
does not. This test enumerates every module under ``src/egg_n_bacon_housing``
and fails when one is neither covered by an entry in ``[tool.mypy].files`` nor
listed as an explicit, justified exemption below.

When adding a module, add it to ``[tool.mypy].files``. Only add an exemption
when the module is genuinely not type-checkable/relevant, and record why.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src" / "egg_n_bacon_housing"
PYPROJECT = REPO_ROOT / "pyproject.toml"

#: Modules deliberately left out of ``[tool.mypy].files``.
#:
#: Each entry is a path relative to ``src/egg_n_bacon_housing`` (POSIX form),
#: mapped to the reason. Keep this list tiny: an entry here means "mypy does
#: not look at this file", which is exactly the failure mode this test guards.
EXEMPT_MODULES: dict[str, str] = {
    "__init__.py": (
        "Package marker; only a docstring plus __version__ literal. No functions to type-check."
    ),
    "utils/__init__.py": ("Package marker; only a module docstring. No functions to type-check."),
}


def _mypy_files() -> list[str]:
    """Return the raw ``[tool.mypy].files`` entries from pyproject.toml."""
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    entries = config["tool"]["mypy"]["files"]
    assert isinstance(entries, list), "[tool.mypy].files must be a list"
    return entries


def _covered_by_scope(rel_path: str, entries: list[str]) -> bool:
    """True when ``rel_path`` falls inside any configured mypy entry.

    An entry is either a single module (``.../utils/geo.py``) or a package
    directory (``.../components``), which covers its whole subtree.
    """
    src_prefix = f"{SRC_ROOT.as_posix().split('src/')[-1]}/"
    wanted = f"src/{src_prefix}{rel_path}" if not rel_path.startswith("src/") else rel_path
    for entry in entries:
        normalized = entry.rstrip("/")
        if wanted == normalized or wanted.startswith(f"{normalized}/"):
            return True
    return False


def _all_modules() -> list[str]:
    """Every ``.py`` module under the package, as POSIX paths."""
    return sorted(path.relative_to(SRC_ROOT).as_posix() for path in SRC_ROOT.rglob("*.py"))


def test_every_module_is_type_checked_or_explicitly_exempt() -> None:
    """No module may silently sit outside both the scope and the exemptions."""
    entries = _mypy_files()
    uncovered = [
        rel
        for rel in _all_modules()
        if rel not in EXEMPT_MODULES and not _covered_by_scope(rel, entries)
    ]
    assert not uncovered, (
        "These modules are outside [tool.mypy].files and not in "
        "EXEMPT_MODULES, so mypy does not check them:\n  "
        + "\n  ".join(uncovered)
        + "\n\nAdd them to [tool.mypy].files in pyproject.toml (preferred), or "
        "add a justified exemption in tests/test_type_scope.py."
    )


def test_scope_actually_covers_the_risk_modules() -> None:
    """Pin the modules the audit found untyped so they cannot regress."""
    entries = _mypy_files()
    must_be_covered = [
        "schemas/clean_models.py",
        "schemas/feature_models.py",
        "schemas/platinum_models.py",
        "utils/validation.py",
        "utils/bronze.py",
        "utils/output_registry.py",
        "utils/data_loader.py",
        "utils/school_features.py",
        "utils/geo.py",
        "utils/runtime.py",
        "utils/data_quality.py",
        "config.py",
        "utils/layer_writer.py",
    ]
    missing = [rel for rel in must_be_covered if not _covered_by_scope(rel, entries)]
    assert not missing, "Previously-untyped modules dropped out of mypy's scope: " + ", ".join(
        missing
    )


def test_exemptions_are_minimal_and_justified() -> None:
    """Every exemption must still exist on disk and carry a real reason."""
    for rel, reason in EXEMPT_MODULES.items():
        assert (SRC_ROOT / rel).is_file(), f"exempt module no longer exists: {rel}"
        assert reason.strip(), f"exempt module {rel} has no justification"

    # Packaging markers only — if this list grows, the reason must be reviewed.
    unexpected = set(EXEMPT_MODULES) - {"__init__.py", "utils/__init__.py"}
    assert not unexpected, (
        "New mypy exemptions need review; add the module to "
        f"[tool.mypy].files instead unless it truly cannot be typed: {sorted(unexpected)}"
    )


def test_scope_entries_all_exist() -> None:
    """A stale entry means mypy checks less than the config claims."""
    for entry in _mypy_files():
        assert (REPO_ROOT / entry).exists(), (
            f"[tool.mypy].files entry does not exist on disk: {entry}"
        )
