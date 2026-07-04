from __future__ import annotations

from typing import Annotated
from dataclasses import dataclass

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


@dataclass(frozen=True, slots=True)
class ConfiguredAdminUser:
    email: str
    password_hash: str
    display_name: str


def build_display_name(email: str) -> str:
    local_part = email.split("@", 1)[0].replace(".", " ").replace("_", " ").replace("-", " ").strip()
    return " ".join(chunk.capitalize() for chunk in local_part.split()) or email


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
    ADMIN_EMAILS: str = ""
    ADMIN_PASSWORD_HASHES: str = ""

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

    @model_validator(mode="after")
    def guard_non_local_secrets(self) -> "Settings":
        configured_users = self.configured_admin_users

        if self.APP_ENV.lower() == "local":
            return self

        if self.JWT_SECRET_KEY in ("", "change_this_secret_key") or len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("JWT_SECRET_KEY is not secure enough for non-local environments.")

        for user in configured_users:
            if user.password_hash in ("", "replace_with_bcrypt_hash"):
                raise ValueError("All configured admin password hashes must be set for non-local environments.")

        return self

    @property
    def configured_admin_users(self) -> list[ConfiguredAdminUser]:
        emails = self._parse_csv(self.ADMIN_EMAILS) or self._parse_csv(self.ADMIN_EMAIL)
        password_hashes = self._parse_csv(self.ADMIN_PASSWORD_HASHES) or self._parse_csv(self.ADMIN_PASSWORD_HASH)

        if len(emails) != len(password_hashes):
            raise ValueError("ADMIN_EMAILS and ADMIN_PASSWORD_HASHES must contain the same number of values.")

        normalized_emails = [email.lower() for email in emails]
        if len(set(normalized_emails)) != len(normalized_emails):
            raise ValueError("Configured admin emails must be unique.")

        return [
            ConfiguredAdminUser(
                email=email,
                password_hash=password_hash,
                display_name=build_display_name(email),
            )
            for email, password_hash in zip(emails, password_hashes, strict=True)
        ]

    def find_configured_admin_user(self, email: str) -> ConfiguredAdminUser | None:
        normalized_email = email.strip().lower()
        for user in self.configured_admin_users:
            if user.email.lower() == normalized_email:
                return user
        return None

    def other_user_emails(self, current_email: str) -> list[str]:
        normalized_email = current_email.strip().lower()
        return [user.email for user in self.configured_admin_users if user.email.lower() != normalized_email]

    @staticmethod
    def _parse_csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cookie_secure(self) -> bool:
        return self.APP_ENV.lower() != "local"

    @property
    def cookie_samesite(self) -> str:
        return "lax" if self.APP_ENV.lower() == "local" else "none"

    @property
    def docs_enabled(self) -> bool:
        return self.APP_ENV.lower() == "local"

    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.docs_enabled else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.docs_enabled else None

    @property
    def openapi_url(self) -> str | None:
        return f"{self.API_V1_PREFIX}/openapi.json" if self.docs_enabled else None


settings = Settings()
