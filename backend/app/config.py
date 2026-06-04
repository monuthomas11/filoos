"""Application settings loaded from environment / .env file."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
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
    "RECURRING_AUTO_MATERIALIZE": "recurring_auto_materialize",
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
    app_name: str = Field(default="FutureFunds", description="Display name.")
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = True

    # Database
    database_url: str = Field(
        default=f"sqlite:///{(BACKEND_DIR.parent / 'data' / 'expenses.db').as_posix()}",
        description="SQLAlchemy database URL.",
    )

    # Currency
    default_currency: str = Field(default="INR", description="ISO 4217 code.")
    currency_symbol: str = Field(default="₹", description="Display symbol.")

    # Forecasting
    forecast_history_days: int = 180
    forecast_cache_ttl_seconds: int = 300

    # Recurring
    recurring_auto_materialize: bool = True

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
