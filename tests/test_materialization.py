"""Tests for components/materialization.py — companion persistence nodes.

The module expands two ``@parameterize`` families from
``utils/output_registry.PUBLISHED_OUTPUTS``: one ``materialize_<dataset>``
node and one ``materialize_<boundary>_quarantine`` node per published output.
These tests pin:

- the emitted DAG node names byte-for-byte against the literal inventory
  captured from the pre-parameterization hand-written implementation
  (2026-09, roadmap item 16) — renames would break ``MATERIALIZER_MAP``,
  the Hamilton cache disable list, and ``run_pipeline``'s companion wiring;
- the registry maps and the emitted node set stay in lockstep;
- per-output write behavior through a real Hamilton driver over the
  materialization module alone (upstream frames arrive as runtime inputs):
  published outputs persist under the registry's name/layer pair, empty
  outputs persist as 0-row parquets, and quarantine companions write only
  non-empty frames under ``<layer>/_quarantine/<dataset>/<run_id>``.
"""

import pandas as pd
import pytest
from hamilton import driver

from egg_n_bacon_housing.components import materialization
from egg_n_bacon_housing.pipeline import _MATERIALIZER_MAP
from egg_n_bacon_housing.utils.layer_writer import PUBLISHED_LAYERS, SimpleWriter
from egg_n_bacon_housing.utils.output_registry import (
    PUBLISHED_OUTPUTS,
    QUARANTINE_MATERIALIZER_MAP,
)

pytestmark = pytest.mark.unit

# Literal inventory of all 24 materialization node names, captured by
# introspecting the hand-written implementation BEFORE the @parameterize
# refactor. The emitted DAG nodes must match this list exactly.
_PRE_REFACTOR_NODE_NAMES = [
    "materialize_appreciation_hotspots",
    "materialize_appreciation_hotspots_quarantine",
    "materialize_block_profile",
    "materialize_block_profile_quarantine",
    "materialize_condo_quarantine",
    "materialize_condo_validated",
    "materialize_geocoded_quarantine",
    "materialize_geocoded_validated",
    "materialize_hdb_quarantine",
    "materialize_hdb_validated",
    "materialize_location_dim",
    "materialize_location_dim_quarantine",
    "materialize_pa_monthly_metrics",
    "materialize_pa_monthly_metrics_quarantine",
    "materialize_planning_area_360",
    "materialize_planning_area_360_quarantine",
    "materialize_rental_yield",
    "materialize_rental_yield_quarantine",
    "materialize_town_360",
    "materialize_town_360_quarantine",
    "materialize_transactions_enriched",
    "materialize_transactions_enriched_quarantine",
    "materialize_unified_dataset",
    "materialize_unified_dataset_quarantine",
]


@pytest.fixture(scope="module")
def materialization_dag() -> driver.Driver:
    """Driver over the materialization module alone.

    The parameterized nodes' upstream frames (and ``writer`` /
    ``pipeline_run_id``) are not defined here, so Hamilton exposes them as
    runtime inputs — exactly how ``run_pipeline`` injects them in production.
    """
    return driver.Builder().with_modules(materialization).build()


def _emitted_node_names(dag: driver.Driver) -> set[str]:
    """Materialization node names emitted into the DAG.

    The module-only graph's other variables are external-input placeholders
    (dataset frames, ``writer``, ``pipeline_run_id``); none of those start
    with ``materialize_``, so the prefix filter is exact here.
    """
    return {v.name for v in dag.list_available_variables() if v.name.startswith("materialize_")}


def test_materializer_map_covers_every_published_layer_exactly_once():
    """Wiring invariant: every published output has exactly one materializer."""
    assert set(_MATERIALIZER_MAP) == set(PUBLISHED_LAYERS)
    assert len(_MATERIALIZER_MAP) == len(PUBLISHED_LAYERS)


def test_emitted_node_names_are_byte_identical_to_pre_refactor_inventory(materialization_dag):
    """The @parameterize expansion must not rename a single materialization node."""
    assert _emitted_node_names(materialization_dag) == set(_PRE_REFACTOR_NODE_NAMES)
    assert len(_PRE_REFACTOR_NODE_NAMES) == 2 * len(PUBLISHED_OUTPUTS)


def test_registry_maps_name_exactly_the_emitted_nodes(materialization_dag):
    """Registry companions and emitted DAG nodes stay in lockstep."""
    emitted = _emitted_node_names(materialization_dag)
    assert set(_MATERIALIZER_MAP.values()) | set(QUARANTINE_MATERIALIZER_MAP.values()) == emitted
    assert set(_MATERIALIZER_MAP.values()).isdisjoint(QUARANTINE_MATERIALIZER_MAP.values())


@pytest.mark.parametrize("node_name", sorted(PUBLISHED_LAYERS))
def test_materializer_writes_published_name_and_layer(materialization_dag, tmp_path, node_name):
    """Each materializer persists its node under the PUBLISHED_LAYERS name/layer."""
    writer = SimpleWriter(tmp_path)
    df = pd.DataFrame([{"value": 1}])

    result = materialization_dag.execute(
        [_MATERIALIZER_MAP[node_name]],
        inputs={node_name: df, "writer": writer},
    )

    layer = PUBLISHED_LAYERS[node_name]
    path = result[_MATERIALIZER_MAP[node_name]]
    assert path == writer.resolve_path(node_name, layer, tmp_path)
    assert path.exists()
    assert pd.read_parquet(path).to_dict(orient="records") == [{"value": 1}]


@pytest.mark.parametrize("node_name", sorted(PUBLISHED_LAYERS))
def test_materializer_persists_empty_frame_as_zero_row_parquet(
    materialization_dag, tmp_path, node_name
):
    """Empty outputs persist as 0-row schema-only parquets (a missing file means recompute)."""
    writer = SimpleWriter(tmp_path)

    result = materialization_dag.execute(
        [_MATERIALIZER_MAP[node_name]],
        inputs={node_name: pd.DataFrame(), "writer": writer},
    )

    path = result[_MATERIALIZER_MAP[node_name]]
    assert path.exists()
    persisted = pd.read_parquet(path)
    assert len(persisted) == 0


@pytest.mark.parametrize("node_name", sorted(PUBLISHED_LAYERS))
def test_quarantine_companion_writes_nonempty_frame_under_run_path(
    materialization_dag, tmp_path, node_name
):
    """Non-empty rejected rows land in <layer>/_quarantine/<dataset>/<run_id>.parquet."""
    writer = SimpleWriter(tmp_path)
    boundary = node_name.removesuffix("_validated")
    dataset_quarantine = f"{boundary}_quarantine"

    result = materialization_dag.execute(
        [QUARANTINE_MATERIALIZER_MAP[node_name]],
        inputs={
            dataset_quarantine: pd.DataFrame([{"row_id": 7}]),
            "writer": writer,
            "pipeline_run_id": "20260101T000000Z_deadbeef",
        },
    )

    layer = PUBLISHED_LAYERS[node_name]
    expected = writer.resolve_path(
        f"_quarantine/{node_name}/20260101T000000Z_deadbeef", layer, tmp_path
    )
    path = result[QUARANTINE_MATERIALIZER_MAP[node_name]]
    assert path == expected
    assert path.exists()
    assert pd.read_parquet(path).to_dict(orient="records") == [{"row_id": 7}]


@pytest.mark.parametrize("node_name", sorted(PUBLISHED_LAYERS))
def test_quarantine_companion_skips_empty_frame(materialization_dag, tmp_path, node_name):
    """An empty quarantine frame writes nothing and resolves to None."""
    writer = SimpleWriter(tmp_path)
    boundary = node_name.removesuffix("_validated")

    result = materialization_dag.execute(
        [QUARANTINE_MATERIALIZER_MAP[node_name]],
        inputs={
            f"{boundary}_quarantine": pd.DataFrame(),
            "writer": writer,
            "pipeline_run_id": "20260101T000000Z_deadbeef",
        },
    )

    assert result[QUARANTINE_MATERIALIZER_MAP[node_name]] is None
    assert list(tmp_path.rglob("*.parquet")) == []


# ---------------------------------------------------------------------------
# Direct-call compatibility surface (module __getattr__)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("node_name", sorted(PUBLISHED_LAYERS))
def test_direct_call_materializer_matches_dag_node_behavior(
    materialization_dag, tmp_path, node_name
):
    """__getattr__ binds registered materializers to the same write body the DAG uses."""
    direct = getattr(materialization, _MATERIALIZER_MAP[node_name])
    assert callable(direct)

    direct_writer = SimpleWriter(tmp_path / "direct")
    direct_path = direct(pd.DataFrame([{"value": 1}]), direct_writer)

    dag_writer = SimpleWriter(tmp_path / "dag")
    dag_result = materialization_dag.execute(
        [_MATERIALIZER_MAP[node_name]],
        inputs={node_name: pd.DataFrame([{"value": 1}]), "writer": dag_writer},
    )

    layer = PUBLISHED_LAYERS[node_name]
    assert direct_path == direct_writer.resolve_path(node_name, layer, tmp_path / "direct")
    assert dag_result[_MATERIALIZER_MAP[node_name]] == dag_writer.resolve_path(
        node_name, layer, tmp_path / "dag"
    )


def test_compat_surface_resolves_quarantine_names_and_rejects_unknown():
    """Every registry companion resolves; unknown attributes still raise."""
    for quarantine_name in QUARANTINE_MATERIALIZER_MAP.values():
        assert callable(getattr(materialization, quarantine_name))

    with pytest.raises(AttributeError, match="no attribute"):
        materialization.materialize_not_a_registered_output  # noqa: B018
