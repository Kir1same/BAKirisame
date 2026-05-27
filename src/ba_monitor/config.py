from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    qq_app_id: str
    qq_app_secret: str
    qq_sandbox: bool = True
    data_source: str = "barmory"
    ba_api_base_url: str | None = None
    ba_api_key: str | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
