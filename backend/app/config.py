from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Sensitive secrets — accessed via .get_secret_value(), never logged directly
    anthropic_api_key: SecretStr | None = None  # required in production
    database_url: SecretStr | None = None        # required when DB is wired up

    claude_model: str = "claude-sonnet-4-6"
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: Literal["development", "production"] = "development"

    # Rate limit for AI endpoints (build + search share this pool)
    # slowapi format: "N/period" where period is second/minute/hour/day
    rate_limit_ai: str = "2/hour"


settings = Settings()
