from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    databricks_server_hostname: str
    databricks_http_path: str
    databricks_token: str
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
