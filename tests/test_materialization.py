"""Tests for components/materialization.py — companion persistence nodes.

Every published output (PUBLISHED_LAYERS key) must have exactly one companion
materializer that writes the registry's name/layer pair; the computing nodes
themselves stay side-effect-free.
"""

import pandas as pd
import pytest

from egg_n_bacon_housing.components import materialization
from egg_n_bacon_housing.pipeline import _MATERIALIZER_MAP
from egg_n_bacon_housing.utils.layer_writer import PUBLISHED_LAYERS, SimpleWriter

pytestmark = pytest.mark.unit


def test_materializer_map_covers_every_published_layer_exactly_once():
    """Wiring invariant: every published output has exactly one materializer."""
    assert set(_MATERIALIZER_MAP) == set(PUBLISHED_LAYERS)
    assert len(_MATERIALIZER_MAP) == len(PUBLISHED_LAYERS)


def test_every_registered_materializer_exists_as_a_node():
    """Map values must resolve to materialization functions (Hamilton nodes)."""
    for materializer_name in _MATERIALIZER_MAP.values():
        assert callable(getattr(materialization, materializer_name))


@pytest.mark.parametrize("node_name", sorted(PUBLISHED_LAYERS))
def test_materializer_writes_published_name_and_layer(node_name, tmp_path):
    """Each materializer persists its node under the PUBLISHED_LAYERS name/layer."""
    materializer = getattr(materialization, _MATERIALIZER_MAP[node_name])
    writer = SimpleWriter(tmp_path)
    df = pd.DataFrame([{"value": 1}])

    path = materializer(df, writer)

    layer = PUBLISHED_LAYERS[node_name]
    assert path == writer.resolve_path(node_name, layer, tmp_path)
    assert path.exists()
    assert pd.read_parquet(path).to_dict(orient="records") == [{"value": 1}]


@pytest.mark.parametrize("node_name", sorted(PUBLISHED_LAYERS))
def test_materializer_persists_empty_frame_as_zero_row_parquet(node_name, tmp_path):
    """Empty outputs persist as 0-row schema-only parquets (a missing file means recompute)."""
    materializer = getattr(materialization, _MATERIALIZER_MAP[node_name])
    writer = SimpleWriter(tmp_path)

    path = materializer(pd.DataFrame(), writer)

    assert path.exists()
    persisted = pd.read_parquet(path)
    assert len(persisted) == 0
