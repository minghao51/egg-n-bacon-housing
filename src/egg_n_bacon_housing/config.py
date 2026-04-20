"""Centralized configuration using pydantic-settings."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class PipelineConfig(BaseSettings):
    parquet_compression: str = "snappy"
    parquet_index: bool = False
    use_caching: bool = True
    cache_duration_hours: int = 24


class GeocodingConfig(BaseSettings):
    max_workers: int = 5
    api_delay_seconds: float = 1.2
    timeout_seconds: int = 30


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
        yaml_file="config.yaml",
        extra="ignore",
    )

    app_name: str = "egg-n-bacon-housing"
    data_path: str = "./data"

    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    geocoding: GeocodingConfig = Field(default_factory=GeocodingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    layer_dirs: LayerDirs = Field(default_factory=LayerDirs)

    onemap_email: SecretStr = Field(default="", alias="ONEMAP_EMAIL")
    onemap_password: SecretStr = Field(default="", alias="ONEMAP_EMAIL_PASSWORD")
    google_api_key: SecretStr = Field(default="", alias="GOOGLE_API_KEY")
    supabase_url: SecretStr = Field(default="", alias="SUPABASE_URL")
    supabase_key: SecretStr = Field(default="", alias="SUPABASE_KEY")
    jina_ai: SecretStr = Field(default="", alias="JINA_AI")

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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )


settings = Settings()
