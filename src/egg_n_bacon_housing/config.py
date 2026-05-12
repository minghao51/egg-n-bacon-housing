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
    bronze: str = "data/01_bronze"
    silver: str = "data/02_silver"
    gold: str = "data/03_gold"
    platinum: str = "data/04_platinum"


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
    ura_ec_files: list[str] = [
        "ECResidentialTransaction20260121003532",
        "ECResidentialTransaction20260121003707",
    ]
    ura_condo_files: list[str] = [
        "ResidentialTransaction20260121003944",
        "ResidentialTransaction20260121004101",
        "ResidentialTransaction20260121004213",
        "ResidentialTransaction20260121004407",
        "ResidentialTransaction20260121004517",
        "ResidentialTransaction20260121005130",
        "ResidentialTransaction20260121005233",
        "ResidentialTransaction20260121005346",
        "ResidentialTransaction20260121005450",
        "ResidentialTransaction20260121005601",
        "ResidentialTransaction20260121005715",
        "ResidentialTransaction20260121005734",
    ]

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        return self.base_dir / self.data_path.lstrip("./")

    @property
    def bronze_dir(self) -> Path:
        return self.base_dir / self.layer_dirs.bronze

    @property
    def silver_dir(self) -> Path:
        return self.base_dir / self.layer_dirs.silver

    @property
    def gold_dir(self) -> Path:
        return self.base_dir / self.layer_dirs.gold

    @property
    def platinum_dir(self) -> Path:
        return self.base_dir / self.layer_dirs.platinum


settings = Settings()
