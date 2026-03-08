from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str | None = None  # required in production
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: Literal["development", "production"] = "development"


settings = Settings()
