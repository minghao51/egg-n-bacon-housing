"""Centralized configuration using pydantic-settings."""

import logging
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

AFFORDABILITY_THRESHOLD_DEFAULTS: dict[str, float] = {
    "affordable": 5.0,
    "moderate": 7.0,
    "expensive": 9.0,
}


class PipelineConfig(BaseSettings):
    parquet_compression: str = "snappy"
    use_caching: bool = True
    cache_duration_hours: int = 24
    large_table_validation_policy: Literal["sample", "full", "fail"] = "full"
    max_transaction_age_days: int | None = Field(default=120, ge=0)
    quarantine_retention_days: int = Field(default=90, ge=1)


class GeocodingConfig(BaseSettings):
    max_workers: int = 5
    api_delay_seconds: float = 1.2
    timeout_seconds: int = 30
    cache_duration_hours: int = 24
    # Legacy single-threshold coverage gate. Retained as the fallback for
    # property-type segments without a dedicated threshold (env:
    # GEOCODING__MIN_COORDINATE_COVERAGE).
    min_coordinate_coverage: float = Field(default=0.7, ge=0, le=1)
    # Per-property-type coverage gates. HDB addresses (block + street_name +
    # postal substrate) geocode reliably, so the strict bar holds; condo
    # addresses are street-only and legitimately geocode worse (env:
    # GEOCODING__MIN_COORDINATE_COVERAGE_HDB / GEOCODING__MIN_COORDINATE_COVERAGE_CONDO).
    min_coordinate_coverage_hdb: float = Field(default=0.7, ge=0, le=1)
    min_coordinate_coverage_condo: float = Field(default=0.3, ge=0, le=1)
    coordinate_coverage_policy: Literal["fail", "warn"] = "fail"


class MetricsConfig(BaseSettings):
    median_household_income: int = 85000
    # Volume floor for appreciation-hotspot ranking (env: METRICS__MIN_TRANSACTIONS_FOR_HOTSPOT).
    min_transactions_for_hotspot: int = Field(default=5, ge=1)
    affordability_thresholds: dict[str, float] = Field(
        default_factory=lambda: AFFORDABILITY_THRESHOLD_DEFAULTS.copy()
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> "MetricsConfig":
        value = self.affordability_thresholds
        keys = ("affordable", "moderate", "expensive")
        if set(value) != set(keys) or not all(value[a] < value[b] for a, b in zip(keys, keys[1:])):
            raise ValueError(
                "affordability_thresholds must contain strictly increasing affordable, moderate, expensive values"
            )
        return self


_NONSTANDARD_LAYER_WARNED: set[tuple[str, str]] = set()


def _warn_nonstandard_layer_path(layer: str, configured: Path) -> None:
    """Warn once per unique (layer, path) pair about non-standard layer paths."""
    key = (layer, str(configured))
    if key in _NONSTANDARD_LAYER_WARNED:
        return
    _NONSTANDARD_LAYER_WARNED.add(key)
    logger.warning(
        "Layer %s is configured as %r, which does not start with 'data/pipeline'. "
        "It resolves relative to the pipeline root; custom layouts are supported, "
        "but this may indicate a misconfiguration.",
        layer,
        str(configured),
    )


class LayerDirs(BaseSettings):
    bronze: str = "data/pipeline/01_bronze"
    silver: str = "data/pipeline/02_silver"
    gold: str = "data/pipeline/03_gold"
    platinum: str = "data/pipeline/04_platinum"

    def relative_path(self, layer: str) -> Path:
        """Resolve a layer key to its path relative to the runtime pipeline root.

        Configured paths conventionally carry a ``data/pipeline`` prefix
        (matching the repository layout and ``LAYER_DIRS__*`` env overrides),
        while callers anchor layers under the resolved data root's
        ``pipeline/`` directory. To keep that round-trip consistent, a leading
        ``data/pipeline`` prefix is stripped here and re-added by the caller
        (``Settings.layer_dir`` joins the pipeline root beneath the data
        root). Absolute configured paths bypass this normalization and are
        returned unchanged. Relative paths without the ``data/pipeline``
        prefix are kept as-is (still resolved against the pipeline root) and
        warned about once, since they usually indicate a misconfiguration.
        """
        if layer == "platinum_metrics":
            return self.relative_path("platinum") / "metrics"
        if layer not in {"bronze", "silver", "gold", "platinum"}:
            raise ValueError(f"Unknown layer {layer!r}")
        configured = Path(getattr(self, layer))
        if configured.is_absolute():
            return configured
        parts = configured.parts
        if parts[:2] == ("data", "pipeline"):
            parts = parts[2:]
        else:
            _warn_nonstandard_layer_path(layer, configured)
        return Path(*parts)


LayerName = Literal["bronze", "silver", "gold", "platinum", "platinum_metrics"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "egg-n-bacon-housing"
    data_path: str = "./data"

    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    geocoding: GeocodingConfig = Field(default_factory=GeocodingConfig)
    layer_dirs: LayerDirs = Field(default_factory=LayerDirs)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    tracking_enabled: bool = False
    tracking_project_id: int | None = None
    tracking_username: str | None = None
    tracking_environment: str | None = None

    onemap_email: SecretStr = Field(default=SecretStr(""), alias="ONEMAP_EMAIL")
    onemap_password: SecretStr = Field(default=SecretStr(""), alias="ONEMAP_EMAIL_PASSWORD")
    # Optional pre-issued JWT; when absent or expired the email/password flow runs.
    onemap_token: SecretStr | None = Field(default=None, alias="ONEMAP_TOKEN")

    r2_account_id: str = Field(default="", alias="R2_ACCOUNT_ID")
    r2_access_key_id: SecretStr = Field(default=SecretStr(""), alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: SecretStr = Field(default=SecretStr(""), alias="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="egg-bacon-housing-data", alias="R2_BUCKET")
    r2_endpoint: str = Field(default="", alias="R2_ENDPOINT")

    # Optional: enables live URA private-residential transaction fetch.
    # Absent = condo bronze falls back to the manual R2 CSVs.
    ura_api_access_key: SecretStr = Field(default=SecretStr(""), alias="URA_API_ACCESS_KEY")

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent

    def resolve_data_path(self, data_path: str | Path | None = None) -> Path:
        if data_path is None:
            data_path = self.data_path

        path = Path(data_path)
        return path if path.is_absolute() else self.base_dir / path

    def layer_dir(self, layer: str, data_path: str | Path | None = None) -> Path:
        configured = self.layer_dirs.relative_path(layer)
        root = self.resolve_data_path(data_path)
        if configured.is_absolute():
            return configured
        return root / "pipeline" / configured

    def layer_paths(self, data_path: str | Path | None = None) -> dict[str, Path]:
        """Return the authoritative runtime paths for every output layer."""
        layers: tuple[LayerName, ...] = (
            "bronze",
            "silver",
            "gold",
            "platinum",
            "platinum_metrics",
        )
        return {layer: self.layer_dir(layer, data_path) for layer in layers}

    @model_validator(mode="after")
    def validate_tracking_configuration(self) -> "Settings":
        if self.tracking_enabled and (
            self.tracking_project_id is None
            or not self.tracking_username
            or not self.tracking_environment
        ):
            raise ValueError(
                "tracking_project_id, tracking_username, and tracking_environment "
                "are required when tracking_enabled=True"
            )
        return self

    @property
    def data_dir(self) -> Path:
        return self.resolve_data_path()

    @property
    def bronze_dir(self) -> Path:
        return self.layer_dir("bronze")

    @property
    def silver_dir(self) -> Path:
        return self.layer_dir("silver")

    @property
    def gold_dir(self) -> Path:
        return self.layer_dir("gold")

    @property
    def platinum_dir(self) -> Path:
        return self.layer_dir("platinum")


settings = Settings()
