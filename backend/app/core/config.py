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
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    csrf_secret_key: str = "local-development-only-csrf-change-me"
    refresh_cookie_name: str = "campuscycle_refresh"
    csrf_cookie_name: str = "campuscycle_csrf"
    auth_cookie_path: str = Field(default="/api/v1/auth", min_length=1)
    csrf_cookie_path: str = Field(default="/", min_length=1)
    cookie_domain: str | None = None
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    @model_validator(mode="after")
    def require_non_development_secret(self) -> "Settings":
        if (not self.auth_cookie_path.startswith("/") or ";" in self.auth_cookie_path or
                not self.csrf_cookie_path.startswith("/") or ";" in self.csrf_cookie_path):
            raise ValueError("Cookie paths must be absolute paths without semicolons")
        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not permitted with credentialed requests")
        example_secrets = {
            "local-development-only-change-me",
            "replace-with-a-long-random-secret-before-use",
            "local-compose-development-only-change-me",
        }
        csrf_example_secrets = {
            "local-development-only-csrf-change-me",
            "replace-with-a-long-random-csrf-secret-before-use",
        }
        if self.environment.lower() != "development" and self.jwt_secret_key in example_secrets:
            raise ValueError("Development/example JWT secrets may only be used in development")
        if self.environment.lower() == "production" and len(self.jwt_secret_key) < 32:
            raise ValueError(
                "CC_JWT_SECRET_KEY must be at least 32 characters in production"
            )
        if self.environment.lower() != "development" and self.csrf_secret_key in csrf_example_secrets:
            raise ValueError("Development/example CSRF secrets may only be used in development")
        if self.csrf_secret_key == self.jwt_secret_key:
            raise ValueError("CC_CSRF_SECRET_KEY must be independent from CC_JWT_SECRET_KEY")
        if self.environment.lower() == "production":
            if len(self.csrf_secret_key) < 32:
                raise ValueError("CC_CSRF_SECRET_KEY must be at least 32 characters in production")
            if not self.cookie_secure:
                raise ValueError("CC_COOKIE_SECURE must be enabled in production")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                raise ValueError("SameSite=None cookies require Secure")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
