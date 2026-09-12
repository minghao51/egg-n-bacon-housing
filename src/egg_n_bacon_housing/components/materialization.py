"""Explicit, non-cached persistence nodes for published datasets.

Every entry in ``utils/output_registry.PUBLISHED_OUTPUTS`` is persisted by
exactly two Hamilton nodes, expanded by ``@parameterize`` straight from the
registry so the materialization surface can never drift from it:

- ``materialize_<dataset>`` (``spec.materializer``): writes the computing
  node's frame into ``spec.layer`` through the injected ``LayerWriter``.
- ``materialize_<boundary>_quarantine`` (``spec.quarantine_materializer``):
  writes that boundary's rejected rows under
  ``<layer>/_quarantine/<dataset>/<pipeline_run_id>`` (excluded from quality
  tracking), or nothing at all when the frame is empty.

Adding a published output means adding one registry spec; both companions
follow automatically. The per-output names are DAG node *names* (graph
metadata), not module-level functions — the decorated functions keep their
generic names — and tests/test_materialization.py pins the emitted names
byte-for-byte.

For callers that invoke a materializer directly (node-level tests), module
``__getattr__`` resolves the per-output names to one-shot callables bound to
the same shared write bodies — a compatibility surface only; the DAG nodes
above remain the single production persistence path.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd
from hamilton.function_modifiers import parameterize, source, value

from egg_n_bacon_housing.utils.layer_writer import LayerWriter
from egg_n_bacon_housing.utils.output_registry import PUBLISHED_OUTPUTS, PublishedOutputSpec

logger = logging.getLogger(__name__)

# Per-node expansion for published outputs: the frame comes from the
# same-named computing node, the write target from the registry spec.
_MATERIALIZER_PARAMS = {
    spec.materializer: {
        "frame": source(spec.name),
        "dataset_name": value(spec.name),
        "layer": value(spec.layer),
    }
    for spec in PUBLISHED_OUTPUTS
}

# Companion expansion for rejected rows: the upstream quarantine frame is
# named after the validation boundary (hdb_validated -> hdb_quarantine), the
# quarantine directory after the published dataset.
_QUARANTINE_PARAMS = {
    spec.quarantine_materializer: {
        "frame": source(f"{spec.name.removesuffix('_validated')}_quarantine"),
        "dataset_name": value(spec.name),
        "layer": value(spec.layer),
    }
    for spec in PUBLISHED_OUTPUTS
}

_DIRECT_CALL_MATERIALIZERS: dict[str, PublishedOutputSpec] = {
    spec.materializer: spec for spec in PUBLISHED_OUTPUTS
}
_DIRECT_CALL_QUARANTINE_MATERIALIZERS: dict[str, PublishedOutputSpec] = {
    spec.quarantine_materializer: spec for spec in PUBLISHED_OUTPUTS
}


def _write_published(
    frame: pd.DataFrame, dataset_name: str, layer: str, writer: LayerWriter
) -> Path:
    """Persist one published output under its registry name and layer.

    The single write body behind the ``materialize_published`` @parameterize
    family and the direct-call compat surface below.
    """
    return writer.write(frame, dataset_name, layer)


def _write_quarantine(
    frame: pd.DataFrame,
    dataset_name: str,
    layer: str,
    writer: LayerWriter,
    pipeline_run_id: str,
) -> Path | None:
    """Persist one run's rejected rows without quality-baseline tracking.

    The single write body behind the ``materialize_quarantine`` @parameterize
    family and the direct-call compat surface below; a no-op (``None``) when
    the frame is empty, so a clean run quarantines nothing.
    """
    if frame.empty:
        return None
    return writer.write(
        frame,
        f"_quarantine/{dataset_name}/{pipeline_run_id}",
        layer,
        track_quality=False,
    )


@parameterize(**_MATERIALIZER_PARAMS)
def materialize_published(
    frame: pd.DataFrame, dataset_name: str, layer: str, writer: LayerWriter
) -> Path:
    """Persist one published output through the injected writer.

    Emitted once per ``PUBLISHED_OUTPUTS`` entry as ``materialize_<dataset>``.
    """
    return _write_published(frame, dataset_name, layer, writer)


@parameterize(**_QUARANTINE_PARAMS)
def materialize_quarantine(
    frame: pd.DataFrame,
    dataset_name: str,
    layer: str,
    writer: LayerWriter,
    pipeline_run_id: str,
) -> Path | None:
    """Persist one run's rejected rows without quality-baseline tracking.

    Emitted once per ``PUBLISHED_OUTPUTS`` entry as
    ``materialize_<boundary>_quarantine``; a no-op (``None``) when the frame
    is empty, so a clean run quarantines nothing.
    """
    return _write_quarantine(frame, dataset_name, layer, writer, pipeline_run_id)


def __getattr__(name: str) -> Callable[..., Path | None]:
    """Resolve per-output materializer names to direct-call bound writers.

    PEP 562 compatibility surface: the parameterized families emit
    ``materialize_<dataset>`` / ``materialize_<boundary>_quarantine`` as DAG
    node names only, so importers that call a materializer directly get a
    one-shot callable bound to the same spec (name + layer) and write body.
    """
    spec = _DIRECT_CALL_MATERIALIZERS.get(name)
    if spec is not None:

        def _materialize(frame: pd.DataFrame, writer: LayerWriter) -> Path:
            return _write_published(frame, spec.name, spec.layer, writer)

        _materialize.__name__ = name
        _materialize.__doc__ = (
            f"Direct-call form of ``{name}``: persist ``{spec.name}`` to the "
            f"{spec.layer} layer (the DAG node comes from the @parameterize family)."
        )
        return _materialize

    quarantine_spec = _DIRECT_CALL_QUARANTINE_MATERIALIZERS.get(name)
    if quarantine_spec is not None:

        def _materialize_quarantine(
            frame: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
        ) -> Path | None:
            return _write_quarantine(
                frame, quarantine_spec.name, quarantine_spec.layer, writer, pipeline_run_id
            )

        _materialize_quarantine.__name__ = name
        _materialize_quarantine.__doc__ = (
            f"Direct-call form of ``{name}``: persist rejected ``{quarantine_spec.name}`` "
            f"rows under the {quarantine_spec.layer} quarantine path (the DAG node comes "
            "from the @parameterize family)."
        )
        return _materialize_quarantine

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
