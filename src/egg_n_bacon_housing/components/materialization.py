"""Explicit, non-cached persistence nodes for published datasets."""

import logging
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.utils.layer_writer import LayerWriter

logger = logging.getLogger(__name__)


def materialize_unified_dataset(unified_dataset: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist the unified platinum dataset and return its path."""
    return writer.write(unified_dataset, "unified_dataset", "platinum")


def materialize_pa_monthly_metrics(pa_monthly_metrics: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist planning-area monthly metrics."""
    return writer.write(pa_monthly_metrics, "pa_monthly_metrics", "platinum_metrics")


def materialize_appreciation_hotspots(
    appreciation_hotspots: pd.DataFrame, writer: LayerWriter
) -> Path:
    """Persist hotspots."""
    return writer.write(appreciation_hotspots, "appreciation_hotspots", "platinum_metrics")


def materialize_planning_area_360(planning_area_360: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist planning-area profile output."""
    return writer.write(planning_area_360, "planning_area_360", "gold")


def materialize_town_360(town_360: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist town profile output."""
    return writer.write(town_360, "town_360", "gold")


def materialize_block_profile(block_profile: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist block profile output."""
    return writer.write(block_profile, "block_profile", "gold")


def materialize_hdb_validated(hdb_validated: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist validated HDB transactions to the silver layer."""
    return writer.write(hdb_validated, "hdb_validated", "silver")


def materialize_condo_validated(condo_validated: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist validated condo transactions to the silver layer."""
    return writer.write(condo_validated, "condo_validated", "silver")


def materialize_geocoded_validated(geocoded_validated: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist validated geocoded properties to the silver layer."""
    return writer.write(geocoded_validated, "geocoded_validated", "silver")


def materialize_rental_yield(rental_yield: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist rental yield metrics to the gold layer."""
    return writer.write(rental_yield, "rental_yield", "gold")


def materialize_location_dim(location_dim: pd.DataFrame, writer: LayerWriter) -> Path:
    """Persist the location dimension table to the gold layer."""
    return writer.write(location_dim, "location_dim", "gold")


def materialize_transactions_enriched(
    transactions_enriched: pd.DataFrame, writer: LayerWriter
) -> Path:
    """Persist enriched transactions to the gold layer."""
    return writer.write(transactions_enriched, "transactions_enriched", "gold")


def _write_quarantine(
    frame: pd.DataFrame, dataset: str, layer: str, writer: LayerWriter, pipeline_run_id: str
) -> Path:
    """Persist one run's rejected rows without quality-baseline tracking."""
    return writer.write(
        frame,
        f"_quarantine/{dataset}/{pipeline_run_id}",
        layer,
        track_quality=False,
    )


def _materialize_quarantine(
    frame: pd.DataFrame, dataset: str, layer: str, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    if frame.empty:
        return None
    return _write_quarantine(frame, dataset, layer, writer, pipeline_run_id)


def materialize_hdb_quarantine(
    hdb_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        hdb_quarantine, "hdb_validated", "silver", writer, pipeline_run_id
    )


def materialize_condo_quarantine(
    condo_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        condo_quarantine, "condo_validated", "silver", writer, pipeline_run_id
    )


def materialize_geocoded_quarantine(
    geocoded_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        geocoded_quarantine, "geocoded_validated", "silver", writer, pipeline_run_id
    )


def materialize_rental_yield_quarantine(
    rental_yield_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        rental_yield_quarantine, "rental_yield", "gold", writer, pipeline_run_id
    )


def materialize_location_dim_quarantine(
    location_dim_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        location_dim_quarantine, "location_dim", "gold", writer, pipeline_run_id
    )


def materialize_transactions_enriched_quarantine(
    transactions_enriched_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        transactions_enriched_quarantine, "transactions_enriched", "gold", writer, pipeline_run_id
    )


def materialize_planning_area_360_quarantine(
    planning_area_360_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        planning_area_360_quarantine, "planning_area_360", "gold", writer, pipeline_run_id
    )


def materialize_town_360_quarantine(
    town_360_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(town_360_quarantine, "town_360", "gold", writer, pipeline_run_id)


def materialize_block_profile_quarantine(
    block_profile_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        block_profile_quarantine, "block_profile", "gold", writer, pipeline_run_id
    )


def materialize_unified_dataset_quarantine(
    unified_dataset_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        unified_dataset_quarantine, "unified_dataset", "platinum", writer, pipeline_run_id
    )


def materialize_pa_monthly_metrics_quarantine(
    pa_monthly_metrics_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        pa_monthly_metrics_quarantine,
        "pa_monthly_metrics",
        "platinum_metrics",
        writer,
        pipeline_run_id,
    )


def materialize_appreciation_hotspots_quarantine(
    appreciation_hotspots_quarantine: pd.DataFrame, writer: LayerWriter, pipeline_run_id: str
) -> Path | None:
    return _materialize_quarantine(
        appreciation_hotspots_quarantine,
        "appreciation_hotspots",
        "platinum_metrics",
        writer,
        pipeline_run_id,
    )
