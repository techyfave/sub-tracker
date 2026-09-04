from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Subscription Optimization API"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+asyncpg://sub_tracker:sub_tracker_local@localhost:5432/sub_tracker"
    )
    redis_url: str = "redis://localhost:6379/0"

    # Auth (issue #5). Provisional pending the team's formal ADR on issue #1;
    # see docs/architecture/decisions/0001-authentication-approach.md.
    secret_key: str = "dev-secret-change-me-please-at-least-32-bytes-long"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    auth_rate_limit: str = "5/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
