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


_DEFAULT_URA_EC_FILES = [
    "ECResidentialTransaction20260121003532",
    "ECResidentialTransaction20260121003707",
]

_DEFAULT_URA_CONDO_FILES = [
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

    r2_account_id: str = Field(default="", alias="R2_ACCOUNT_ID")
    r2_access_key_id: SecretStr = Field(default="", alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: SecretStr = Field(default="", alias="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="egg-bacon-housing-data", alias="R2_BUCKET")
    r2_endpoint: str = Field(default="", alias="R2_ENDPOINT")
    ura_ec_files: list[str] = _DEFAULT_URA_EC_FILES
    ura_condo_files: list[str] = _DEFAULT_URA_CONDO_FILES

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        return self.base_dir / self.data_path.removeprefix("./")

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
