"""Application settings loaded from environment / .env file."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Mapping from legacy unprefixed env var names to Settings field names.
_LEGACY_ENV_MAP: dict[str, str] = {
    "APP_NAME": "app_name",
    "APP_ENV": "app_env",
    "DEBUG": "debug",
    "DATABASE_URL": "database_url",
    "DEFAULT_CURRENCY": "default_currency",
    "CURRENCY_SYMBOL": "currency_symbol",
    "FORECAST_HISTORY_DAYS": "forecast_history_days",
    "FORECAST_CACHE_TTL_SECONDS": "forecast_cache_ttl_seconds",
}


class Settings(BaseSettings):
    """Typed application configuration.

    Values are read from environment variables (and an optional .env file at the
    project root). All fields have sensible defaults so the app boots out of
    the box in development.

    Environment variables should be prefixed with ``FF_`` (e.g. ``FF_APP_ENV``).
    Legacy unprefixed variables are still accepted for backward compatibility
    but will be removed in a future release.
    """

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="FF_",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Filoos", description="Display name.")
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = True
    log_level: str = Field(
        default="DEBUG",
        description="Root log level. DEBUG in dev, INFO in prod (override via FF_LOG_LEVEL).",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _default_log_level(cls, v: object, info: Any) -> object:
        """Use INFO when the user hasn't set FF_LOG_LEVEL and we're in production."""
        if v in (None, ""):
            env = info.data.get("app_env", "development")
            return "DEBUG" if env == "development" else "INFO"
        return v

    # Database
    database_url: str = Field(
        default=f"sqlite:///{(BACKEND_DIR.parent / 'data' / 'expenses.db').as_posix()}",
        description="SQLAlchemy database URL.",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, v: object) -> object:
        """Translate a bare ``postgresql://`` scheme to ``postgresql+psycopg://``.

        SQLAlchemy defaults a URL with the ``postgresql`` (or
        ``postgres``) scheme to the psycopg2 driver, which we do not
        install — we ship psycopg v3 only (see C7 in deployment.md).
        Managed-database dashboards (Neon, Supabase, RDS, etc.) hand
        out connection strings in this bare form, so we rewrite the
        scheme automatically when no driver is explicitly specified.
        This applies to both ``FF_DATABASE_URL`` and the legacy
        ``DATABASE_URL`` env var, since the model validator that maps
        legacy names runs after field validation in pydantic-settings
        v2. (If the user already wrote ``postgresql+psycopg://`` or
        ``postgresql+psycopg2://``, leave the URL untouched.)
        """
        if not isinstance(v, str):
            return v
        lowered = v.lower()
        if (
            "+psycopg" in lowered
            or "+psycopg2" in lowered
            or "+pg8000" in lowered
            or "+asyncpg" in lowered
        ):
            return v  # driver already specified — don't touch it
        if v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v[len("postgresql://"):]
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v[len("postgres://"):]
        return v

    # Currency
    default_currency: str = Field(default="INR", description="ISO 4217 code.")
    currency_symbol: str = Field(default="\u20b9", description="Display symbol.")

    # Forecasting
    forecast_history_days: int = 180
    forecast_cache_ttl_seconds: int = 300

    # Sessions / Auth
    session_secret: str | None = Field(
        default=None, description="Secret key for signing session cookies"
    )
    session_max_age_seconds: int = Field(
        default=60 * 60 * 24 * 14, description="Session max age (seconds)"
    )
    session_cookie_secure: bool = Field(
        default=True, description="Set secure flag on session cookie in production"
    )

    # Google OAuth
    google_client_id: str | None = Field(default=None)
    google_client_secret: str | None = Field(default=None)
    google_redirect_uri: str | None = Field(default=None)

    # Security
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated allowed hosts for TrustedHostMiddleware",
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_env(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Accept legacy unprefixed env vars for backward compatibility.

        If a legacy var (e.g. ``APP_ENV``) is set but the corresponding
        prefixed var (e.g. ``FF_APP_ENV``) is not, copy the value over.
        """
        prefix = "FF_"
        for legacy_key, field_name in _LEGACY_ENV_MAP.items():
            prefixed_key = prefix + legacy_key
            # Only use legacy value if: (a) the FF_ var is NOT set, AND
            # (b) the legacy var IS set, AND (c) the field isn't already
            # provided in the values dict (i.e. FF_ var was parsed).
            if (
                prefixed_key not in os.environ
                and legacy_key in os.environ
                and field_name not in values
            ):
                values[field_name] = os.environ[legacy_key]
        return values

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
