from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CC_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CampusCycle API"
    environment: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    database_url: str = "sqlite:///./campuscycle.db"
    jwt_secret_key: str = "local-development-only-change-me"
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "campuscycle-api"
    jwt_audience: str = "campuscycle-client"
    access_token_expire_minutes: int = Field(default=15, ge=1)

    @model_validator(mode="after")
    def require_non_development_secret(self) -> "Settings":
        example_secrets = {
            "local-development-only-change-me",
            "replace-with-a-long-random-secret-before-use",
            "local-compose-development-only-change-me",
        }
        if self.environment.lower() != "development" and self.jwt_secret_key in example_secrets:
            raise ValueError("Development/example JWT secrets may only be used in development")
        if self.environment.lower() == "production" and len(self.jwt_secret_key) < 32:
            raise ValueError(
                "CC_JWT_SECRET_KEY must be at least 32 characters in production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
