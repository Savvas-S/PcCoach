from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Sensitive secrets — accessed via .get_secret_value(), never logged directly
    anthropic_api_key: SecretStr | None = None  # required in production
    database_url: SecretStr | None = None  # required when DB is wired up

    # Arize AX — LLM observability (optional; tracing disabled when unset)
    arize_api_key: SecretStr | None = None
    arize_space_id: str | None = None

    claude_model: str = "claude-sonnet-4-6"
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: Literal["development", "production"] = "development"

    # Agentic tool-use loop
    max_tool_turns: int = 20  # max tool calls per request
    agentic_loop_timeout: float = 120.0  # wall-clock timeout (seconds)

    # Build engine — deterministic selection (bypasses agentic loop)
    use_build_engine: bool = False

    # Rate limits — slowapi format: "N/period" (second/minute/hour/day)
    # AI endpoints (POST /build and POST /search share a single pool)
    rate_limit_ai: str = "2/day"
    # Read endpoint (GET /build/{id})
    rate_limit_read: str = "60/minute"


settings = Settings()
