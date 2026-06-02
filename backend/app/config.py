"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Typed application configuration.

    Values are read from environment variables (and an optional .env file at the
    project root). All fields have sensible defaults so the app boots out of
    the box in development.
    """

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
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

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
