"""Centralized configuration using pydantic-settings."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineConfig(BaseSettings):
    parquet_compression: str = "snappy"
    parquet_index: bool = False
    use_caching: bool = True
    cache_duration_hours: int = 24
    allow_legacy_pickle_cache: bool = False


class GeocodingConfig(BaseSettings):
    max_workers: int = 5
    api_delay_seconds: float = 1.2
    timeout_seconds: int = 30
    cache_duration_hours: int = 24
    min_coordinate_coverage: float = 0.7


class MetricsConfig(BaseSettings):
    median_household_income: int = 85000
    affordability_thresholds: dict[str, float] = {
        "affordable": 5.0,
        "moderate": 7.0,
        "expensive": 9.0,
    }


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    format: str = "%(asctime)s - %(levelname)s - %(message)s"
    verbose: bool = True


class LayerDirs(BaseSettings):
    bronze: str = "data/pipeline/01_bronze"
    silver: str = "data/pipeline/02_silver"
    gold: str = "data/pipeline/03_gold"
    platinum: str = "data/pipeline/04_platinum"


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
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    layer_dirs: LayerDirs = Field(default_factory=LayerDirs)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    onemap_email: SecretStr = Field(default="", alias="ONEMAP_EMAIL")
    onemap_password: SecretStr = Field(default="", alias="ONEMAP_EMAIL_PASSWORD")
    google_api_key: SecretStr = Field(default="", alias="GOOGLE_API_KEY")
    supabase_url: SecretStr = Field(default="", alias="SUPABASE_URL")
    supabase_key: SecretStr = Field(default="", alias="SUPABASE_KEY")
    jina_ai: SecretStr = Field(default="", alias="JINA_AI")

    r2_account_id: str = Field(default="", alias="R2_ACCOUNT_ID")
    r2_access_key_id: SecretStr = Field(default="", alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: SecretStr = Field(default="", alias="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="egg-bacon-housing-data", alias="R2_BUCKET")
    r2_endpoint: str = Field(default="", alias="R2_ENDPOINT")

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent

    def resolve_data_path(self, data_path: str | Path | None = None) -> Path:
        if data_path is None:
            data_path = self.data_path

        path = Path(data_path)
        return path if path.is_absolute() else self.base_dir / path

    def layer_dir(self, layer: str, data_path: str | Path | None = None) -> Path:
        pipeline_root = self.resolve_data_path(data_path) / "pipeline"
        layer_name = Path(getattr(self.layer_dirs, layer)).name
        return pipeline_root / layer_name

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

    @property
    def webapp_data_dir(self) -> Path:
        return self.base_dir / "app" / "public" / "data"

    @property
    def manual_ura_dir(self) -> Path:
        return self.data_dir / "manual" / "csv" / "ura"

    @property
    def ura_ec_files(self) -> list[str]:
        return _discover_ura_csv_stems(self.manual_ura_dir, "ECResidentialTransaction")

    @property
    def ura_condo_files(self) -> list[str]:
        return _discover_ura_csv_stems(self.manual_ura_dir, "ResidentialTransaction")


def _discover_ura_csv_stems(ura_dir: Path, prefix: str) -> list[str]:
    return sorted(path.stem for path in ura_dir.glob(f"{prefix}*.csv"))


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None


settings = get_settings()
