from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "My Movies API"
    APP_ENV: str = "local"
    APP_DEBUG: bool = True
    SQL_ECHO: bool = False

    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    DATABASE_URL: str = "postgresql+psycopg://my_movies:my_movies@localhost:5433/my_movies"

    POSTGRES_DB: str = "my_movies"
    POSTGRES_USER: str = "my_movies"
    POSTGRES_PASSWORD: str = "my_movies"
    POSTGRES_PORT: int = 5433

    JWT_SECRET_KEY: str = "change_this_secret_key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    AUTH_COOKIE_NAME: str = "my_movies_access_token"

    ADMIN_EMAIL: str = "admin@mymovies.local"
    ADMIN_PASSWORD_HASH: str = "replace_with_bcrypt_hash"

    OMDB_PROVIDER_MODE: str = "mock"
    OMDB_API_BASE_URL: str = "https://www.omdbapi.com/"
    OMDB_API_KEY: str = ""

    DEFAULT_EPISODE_RUNTIME_MINUTES: int = 45

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def cookie_secure(self) -> bool:
        return self.APP_ENV.lower() != "local"


settings = Settings()
