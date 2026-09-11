"""Declarative registry for published Hamilton outputs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PublishedOutputSpec:
    """Metadata shared by execution, materialization, and documentation."""

    name: str
    layer: str
    stage: str
    materializer: str
    terminal: bool

    @property
    def quarantine_materializer(self) -> str:
        """Companion materializer name for rejected rows at this boundary."""
        boundary = self.name.removesuffix("_validated")
        return f"materialize_{boundary}_quarantine"


PUBLISHED_OUTPUTS: tuple[PublishedOutputSpec, ...] = (
    PublishedOutputSpec("hdb_validated", "silver", "clean", "materialize_hdb_validated", False),
    PublishedOutputSpec("condo_validated", "silver", "clean", "materialize_condo_validated", False),
    PublishedOutputSpec(
        "geocoded_validated", "silver", "clean", "materialize_geocoded_validated", False
    ),
    PublishedOutputSpec("rental_yield", "gold", "features", "materialize_rental_yield", False),
    PublishedOutputSpec("location_dim", "gold", "features", "materialize_location_dim", False),
    PublishedOutputSpec(
        "transactions_enriched", "gold", "features", "materialize_transactions_enriched", False
    ),
    PublishedOutputSpec(
        "unified_dataset", "platinum", "export", "materialize_unified_dataset", True
    ),
    PublishedOutputSpec(
        "planning_area_360", "gold", "features", "materialize_planning_area_360", True
    ),
    PublishedOutputSpec("town_360", "gold", "features", "materialize_town_360", True),
    PublishedOutputSpec("block_profile", "gold", "features", "materialize_block_profile", True),
    PublishedOutputSpec(
        "pa_monthly_metrics", "platinum_metrics", "metrics", "materialize_pa_monthly_metrics", True
    ),
    PublishedOutputSpec(
        "appreciation_hotspots",
        "platinum_metrics",
        "metrics",
        "materialize_appreciation_hotspots",
        True,
    ),
)

PUBLISHED_LAYERS: dict[str, str] = {spec.name: spec.layer for spec in PUBLISHED_OUTPUTS}
MATERIALIZER_MAP: dict[str, str] = {spec.name: spec.materializer for spec in PUBLISHED_OUTPUTS}
QUARANTINE_MATERIALIZER_MAP: dict[str, str] = {
    spec.name: spec.quarantine_materializer for spec in PUBLISHED_OUTPUTS
}
PUBLISHED_NAMES = frozenset(PUBLISHED_LAYERS)
TERMINAL_OUTPUTS = tuple(spec.name for spec in PUBLISHED_OUTPUTS if spec.terminal)


def outputs_for_stage(stage: str) -> list[str]:
    """Return published outputs owned by ``stage`` in declaration order."""
    return [spec.name for spec in PUBLISHED_OUTPUTS if spec.stage == stage]
