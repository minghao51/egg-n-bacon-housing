"""One authoritative layer-path resolver (ARCH-2).

``Settings.layer_dir``/``Settings.layer_paths`` and
``utils.layer_writer.resolve_layer_paths`` used to duplicate the same
resolution logic, kept in sync by a docstring that claimed one "mirrors" the
other. They now share a single implementation in ``config.resolve_layer_path``.
These tests pin that equivalence so the two entry points cannot drift apart
again, across both relative and absolute layer overrides.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from egg_n_bacon_housing.config import (
    LAYER_KEYS,
    LayerDirs,
    Settings,
    resolve_layer_path,
    resolve_layer_paths,
)
from egg_n_bacon_housing.utils.layer_writer import (
    resolve_layer_paths as writer_resolve_layer_paths,
)

pytestmark = pytest.mark.unit


def _settings(tmp_path: Path, **layer_dirs: str) -> Settings:
    # Pydantic would coerce a plain dict at runtime, but the field is typed
    # ``LayerDirs``; build the real object so the call site is type-correct.
    if layer_dirs:
        return Settings(data_path=str(tmp_path), layer_dirs=LayerDirs(**layer_dirs))
    return Settings(data_path=str(tmp_path))


# ``platinum_metrics`` is not a LayerDirs field: LayerDirs.relative_path derives
# it as platinum / "metrics" (config.py). An override of that layer therefore
# means overriding ``platinum`` and expecting the "metrics" suffix.
_OVERRIDE_FIELD = {
    "bronze": "bronze",
    "silver": "silver",
    "gold": "gold",
    "platinum": "platinum",
    "platinum_metrics": "platinum",
}


def _expected_override(layer: str, configured: str) -> tuple[dict[str, str], Path]:
    """Return the LayerDirs kwarg and the path it must resolve to."""
    field = _OVERRIDE_FIELD[layer]
    expected = Path(configured)
    if layer == "platinum_metrics":
        expected = expected / "metrics"
    return {field: configured}, expected


def test_single_implementation_is_shared() -> None:
    """layer_writer must re-export config's resolver, not reimplement it."""
    assert writer_resolve_layer_paths is resolve_layer_paths


def test_layer_keys_match_published_layers() -> None:
    from egg_n_bacon_housing.utils.layer_writer import PUBLISHED_LAYERS

    assert set(PUBLISHED_LAYERS.values()) <= set(LAYER_KEYS)


@pytest.mark.parametrize("layer", LAYER_KEYS)
def test_settings_and_helper_agree_for_relative_override(tmp_path: Path, layer: str) -> None:
    """Relative override: Settings, module helper, and writer all agree."""
    kwargs, relative = _expected_override(layer, f"custom/{_OVERRIDE_FIELD[layer]}")
    settings = _settings(tmp_path, **kwargs)
    pipeline_root = tmp_path / "pipeline"

    expected = pipeline_root / relative
    assert settings.layer_dir(layer) == expected
    assert settings.layer_paths()[layer] == expected
    assert resolve_layer_path(settings.layer_dirs, layer, pipeline_root) == expected
    assert resolve_layer_paths(settings.layer_dirs, pipeline_root)[layer] == expected
    assert writer_resolve_layer_paths(settings.layer_dirs, pipeline_root)[layer] == expected


@pytest.mark.parametrize("layer", LAYER_KEYS)
def test_settings_and_helper_agree_for_absolute_override(tmp_path: Path, layer: str) -> None:
    """Absolute override: every entry point yields the path unchanged."""
    external = tmp_path / "external" / layer
    kwargs, expected = _expected_override(
        layer, str(external) if layer != "platinum_metrics" else str(external.parent)
    )
    settings = _settings(tmp_path, **kwargs)
    pipeline_root = tmp_path / "pipeline"

    assert settings.layer_dir(layer) == expected
    assert settings.layer_paths()[layer] == expected
    assert resolve_layer_path(settings.layer_dirs, layer, pipeline_root) == expected
    assert resolve_layer_paths(settings.layer_dirs, pipeline_root)[layer] == expected
    assert writer_resolve_layer_paths(settings.layer_dirs, pipeline_root)[layer] == expected


@pytest.mark.parametrize("layer", LAYER_KEYS)
def test_layer_paths_equals_per_layer_layer_dir(tmp_path: Path, layer: str) -> None:
    """The bulk resolver and the single-layer resolver cannot disagree."""
    settings = _settings(tmp_path)
    assert settings.layer_paths()[layer] == settings.layer_dir(layer)


def test_absolute_override_does_not_affect_other_layers(tmp_path: Path) -> None:
    """One absolute override leaves the remaining layers anchored normally."""
    external = tmp_path / "external-gold"
    settings = _settings(tmp_path, gold=str(external))
    paths = settings.layer_paths()

    assert paths["gold"] == external
    assert paths["silver"] == tmp_path / "pipeline" / "02_silver"
    assert paths["platinum_metrics"] == tmp_path / "pipeline" / "04_platinum" / "metrics"


def test_writer_paths_match_settings_paths_end_to_end(tmp_path: Path) -> None:
    """A builder-produced writer resolves each layer exactly like Settings."""
    from egg_n_bacon_housing.utils.layer_writer import build_writer

    settings = _settings(tmp_path)
    pipeline_root = tmp_path / "pipeline"
    writer = build_writer(settings, pipeline_root)

    for layer in LAYER_KEYS:
        assert writer.resolve_path("x", layer, pipeline_root) == (
            settings.layer_dir(layer) / "x.parquet"
        )


def test_relative_paths_are_never_reanchored(tmp_path: Path) -> None:
    """Relative resolutions always sit beneath the pipeline root, never outside."""
    settings = _settings(tmp_path, bronze="relative/bronze")
    resolved = settings.layer_dir("bronze")

    assert resolved.is_relative_to(tmp_path / "pipeline")
    assert resolved == tmp_path / "pipeline" / "relative" / "bronze"


def test_default_layer_dirs_round_trip(tmp_path: Path) -> None:
    """Defaults carry the data/pipeline prefix and round-trip cleanly."""
    settings = _settings(tmp_path)
    paths = settings.layer_paths()

    assert paths["bronze"] == tmp_path / "pipeline" / "01_bronze"
    assert paths["silver"] == tmp_path / "pipeline" / "02_silver"
    assert paths["gold"] == tmp_path / "pipeline" / "03_gold"
    assert paths["platinum"] == tmp_path / "pipeline" / "04_platinum"
    assert paths["platinum_metrics"] == tmp_path / "pipeline" / "04_platinum" / "metrics"


def test_layer_dirs_relative_path_contract_is_unchanged() -> None:
    """LayerDirs.relative_path still strips the data/pipeline prefix."""
    dirs = LayerDirs()
    assert dirs.relative_path("bronze") == Path("01_bronze")
    assert dirs.relative_path("platinum_metrics") == Path("04_platinum") / "metrics"
